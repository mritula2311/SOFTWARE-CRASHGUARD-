"""Download and verify VZCrash (CC BY-NC 4.0, gated on Hugging Face).

Never falls back to fake data: if the download fails, stop with a clear message.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ID = "vzc-research-chapter/VZCrash"
RAW_DIR = Path("data/raw")


def download(raw_dir: Path = RAW_DIR) -> Path:
    """Download all parquet shards into ``raw_dir``. Returns the data folder."""
    from huggingface_hub import snapshot_download
    from huggingface_hub.utils import GatedRepoError, HfHubHTTPError

    try:
        snapshot_download(
            REPO_ID, repo_type="dataset", local_dir=raw_dir, allow_patterns=["data/*.parquet", "README.md"]
        )
    except GatedRepoError:
        sys.exit(
            f"STOP: {REPO_ID} is gated. Accept the terms on the dataset page, then run "
            "`huggingface-cli login` (or set HF_TOKEN) and re-run `make data`. No fake data is used."
        )
    except HfHubHTTPError as err:
        sys.exit(f"STOP: download failed ({err}). No fake data is used.")
    return raw_dir / "data"


LABELS = {0: "crash", 1: "near_miss", 2: "normal_driving"}


def _flat(col, width: int | None = None):
    """Flatten a (chunked) list column into (values, offsets); width reshapes the xyz triples."""

    arr = col.combine_chunks()
    offsets = arr.offsets.to_numpy()
    vals = arr.values
    if width:
        vals = vals.values  # fixed_size_list -> float
        values = vals.to_numpy(zero_copy_only=False).reshape(-1, width)
    else:
        values = vals.to_numpy(zero_copy_only=False)
    return values, offsets - offsets[0]


def profile(raw_dir: Path = RAW_DIR):
    """One row per event with quality statistics. Signals are not kept."""
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    rows = []
    for path in sorted((raw_dir / "data").glob("*.parquet")):
        split = path.name.split("-")[0]
        for batch in pq.ParquetFile(path).iter_batches(batch_size=1000):
            tab = pa.Table.from_batches([batch])
            g, go = _flat(tab["gsensor"], 3)
            w, wo = _flat(tab["gyro"], 3)
            s, so = _flat(tab["gps_speed"])
            meta = tab.select(["event_id", "label", "vehiclesize", "gyro_is_hd"]).to_pandas()
            for i in range(len(meta)):
                a = g[go[i] : go[i + 1]]
                gy = w[wo[i] : wo[i + 1]]
                sp = s[so[i] : so[i + 1]]
                mag = np.linalg.norm(a, axis=1) if len(a) else np.array([np.nan])
                rows.append(
                    (
                        split, int(meta.event_id[i]), int(meta.label[i]), meta.vehiclesize[i], bool(meta.gyro_is_hd[i]),
                        len(a), len(gy), len(sp),
                        bool(np.isnan(a).any()), bool(np.isnan(gy).any()), bool(np.isnan(sp).any()),
                        bool((a.std(axis=0) < 1e-6).all()) if len(a) else True,
                        float(np.nanmedian(mag)), float(np.nanmax(mag)), int(np.argmax(mag)),
                        float(np.nanmax(np.abs(gy))) if len(gy) else np.nan,
                    )
                )
    cols = ["split", "event_id", "label", "vehiclesize", "gyro_is_hd", "n_acc", "n_gyro", "n_gps",
            "nan_acc", "nan_gyro", "nan_gps", "const_acc", "median_mag", "peak_mag", "peak_idx", "gyro_peak_deg_s"]
    return pd.DataFrame(rows, columns=cols)


def iter_events(path: Path, batch_size: int = 1000):
    """Yield (split, event_id, label, vehiclesize, gyro_is_hd, acc[n,3] g, gyro[m,3] deg/s, gps[k]) per event."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    split = path.name.split("-")[0]
    for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_size):
        tab = pa.Table.from_batches([batch])
        g, go = _flat(tab["gsensor"], 3)
        w, wo = _flat(tab["gyro"], 3)
        s, so = _flat(tab["gps_speed"])
        meta = tab.select(["event_id", "label", "vehiclesize", "gyro_is_hd"]).to_pandas()
        for i in range(len(meta)):
            yield (
                split, int(meta.event_id[i]), int(meta.label[i]), meta.vehiclesize[i], bool(meta.gyro_is_hd[i]),
                g[go[i] : go[i + 1]], w[wo[i] : wo[i + 1]], s[so[i] : so[i + 1]],
            )


PEAK_G_LIMIT = 16.0  # IMU full-scale range is not stated on the card; 16 g is a flag threshold only
GYRO_LIMIT = 2000.0  # deg/s


def quality(prof) -> None:
    """Record quality facts in results.json and write docs/05_data_code/DATASET_FACTS_QUALITY.md."""
    from crashguard.results import record

    src = "data/processed/profile.parquet"
    facts: list[tuple[str, object, str, str]] = []

    def add(name: str, value: object, unit: str, note: str = "") -> None:
        record(f"vzcrash.{name}", value, unit, "MEASURED_SOFTWARE", src, note)
        facts.append((name, value, unit, note))

    add("events_total", int(len(prof)), "events")
    for split, g in prof.groupby("split"):
        for lab, n in g.label.value_counts().sort_index().items():
            add(f"events.{split}.{LABELS[lab]}", int(n), "events")
    for lab, n in prof.label.value_counts().sort_index().items():
        add(f"events.all.{LABELS[lab]}", int(n), "events")
        add(f"share.all.{LABELS[lab]}", round(n / len(prof), 4), "fraction")
    add("event_ids_duplicated", int(prof.event_id.duplicated().sum()), "events")
    add("event_ids_in_more_than_one_split", int((prof.groupby("event_id").split.nunique() > 1).sum()), "events")
    add("events_len_1600", int((prof.n_acc == 1600).sum()), "events", "1600 samples = 16 s at 100 Hz")
    add("events_len_not_1600", int((prof.n_acc != 1600).sum()), "events")
    add("len_min", int(prof.n_acc.min()), "samples")
    add("len_max", int(prof.n_acc.max()), "samples")
    add("events_gyro_len_differs_from_acc", int((prof.n_gyro != prof.n_acc).sum()), "events")
    add("events_with_nan", int((prof.nan_acc | prof.nan_gyro | prof.nan_gps).sum()), "events")
    add("events_constant_acc", int(prof.const_acc.sum()), "events")
    bad_g = prof.peak_mag > PEAK_G_LIMIT
    add(f"events_peak_acc_over_{PEAK_G_LIMIT:g}g", int(bad_g.sum()), "events", "likely sensor glitches; check before use")
    add("peak_acc_max", float(prof.peak_mag.max()), "g")
    add(f"events_peak_gyro_over_{GYRO_LIMIT:g}", int((prof.gyro_peak_deg_s > GYRO_LIMIT).sum()), "events", "deg/s")
    add("events_median_acc_outside_0.5_2g", int(((prof.median_mag < 0.5) | (prof.median_mag > 2)).sum()), "events")
    c = prof[prof.label == 0]
    for q in (0.05, 0.5, 0.95):
        add(f"crash_peak_index_q{int(q * 100):02d}", float(c.peak_idx.quantile(q)), "sample index", "position of max |a|")
    add("crash_peak_acc_median", float(c.peak_mag.median()), "g")
    add("crash_events_peak_below_2g", int((c.peak_mag < 2).sum()), "events")
    for vs, n in prof.vehiclesize.value_counts().items():
        add(f"vehiclesize.{vs}", int(n), "events")
    add("gyro_hd_events", int(prof.gyro_is_hd.sum()), "events")

    lines = ["# VZCrash data quality (generated by `make data`)", "",
             "Origin: MEASURED_SOFTWARE, computed from the downloaded parquet files. Same numbers are in `results/results.json` under `vzcrash.*`.", "",
             "| Item | Value | Unit | Note |", "|---|---|---|---|"]
    lines += [f"| {n} | {v} | {u} | {note} |" for n, v, u, note in facts]
    Path("docs/05_data_code/DATASET_FACTS_QUALITY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    download()
    prof = profile()
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    prof.to_parquet("data/processed/profile.parquet")
    quality(prof)
