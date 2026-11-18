"""Firmware-style windowing and the 14 window features (docs/05_data_code/FEATURES.md).

Pipeline per event: drop corrupt events (raw peak > MPU_RANGE_G), clip to the sensor range,
find the first sample where |a| > trigger, cut PRE_S before and POST_S after (edge-repeat padding),
compute 14 features. A peak-centred window is made as a secondary comparison.
"""
from __future__ import annotations

import hashlib
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C

EPS = 1e-3
VARIANTS = tuple(f"trig_{g:g}" for g in C.TRIGGER_SWEEP_G) + ("peak",)
DS_BINS = 32  # downsampled |a| vector for the near-duplicate check (0.5 s bins)


def compute_features(acc: np.ndarray, gyro: np.ndarray) -> np.ndarray:
    """Features for k windows. acc: (k,N,3) in g; gyro: (k,N,3) in deg/s. Returns (k,14) in config.FEATURES order."""
    acc = acc.astype(np.float64)
    mag = np.linalg.norm(acc, axis=2)
    pk = mag.max(axis=1)
    pax, pay, paz = (np.abs(acc[:, :, i]).max(axis=1) for i in range(3))
    dev = mag - 1.0
    rms = np.sqrt((dev**2).mean(axis=1))
    jerk = (np.abs(np.diff(mag, axis=1)) / C.DT).max(axis=1)
    energy = (dev**2).sum(axis=1) * C.DT
    dur = (mag > 2.0).sum(axis=1) * C.DT * 1000.0
    horiz = np.linalg.norm(acc[:, :, :2], axis=2).max(axis=1)
    mu = mag.mean(axis=1, keepdims=True)
    m2 = ((mag - mu) ** 2).mean(axis=1)
    m4 = ((mag - mu) ** 4).mean(axis=1)
    kurt = m4 / (m2**2 + 1e-12) - 3.0
    post_n = round(0.8 * C.FS_HZ)
    quiet = mag[:, -post_n:].std(axis=1) / (mag.std(axis=1) + 1e-6)
    gpk = np.linalg.norm(gyro.astype(np.float64), axis=2).max(axis=1) * C.DEG2RAD
    out = np.stack(
        [pk, pax, pay, paz, rms, jerk, energy, dur, pax / (pay + EPS), horiz / pk, kurt, pk / (rms + EPS), quiet, gpk],
        axis=1,
    )
    return out.astype(np.float32)


def _cut(sig: np.ndarray, start: int, n: int) -> np.ndarray:
    """Slice [start, start+n) with edge-repeat padding."""
    idx = np.clip(np.arange(start, start + n), 0, len(sig) - 1)
    return sig[idx]


def _align_gyro(gyro: np.ndarray, n: int) -> np.ndarray:
    if len(gyro) == n:
        return gyro
    if len(gyro) > n:
        return gyro[:n]
    if len(gyro) == 0:
        return np.zeros((n, 3), np.float32)
    return _cut(gyro, 0, n)


def process_event(acc: np.ndarray, gyro: np.ndarray) -> dict:
    """Windows for every variant of one event. Pure function of the signals."""
    n = len(acc)
    raw_peak = float(np.linalg.norm(acc, axis=1).max()) if n else float("nan")
    res = {"n": n, "raw_peak": raw_peak, "gyro_mismatch": len(gyro) != n, "windows": {}}
    if n < 2 or not np.isfinite(raw_peak):
        res["unwindowable"] = True
        return res
    res["dropped"] = raw_peak > C.MPU_RANGE_G
    if res["dropped"]:
        return res
    a = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
    g = np.clip(_align_gyro(gyro, n), -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
    mag = np.linalg.norm(a, axis=1)
    edges = np.linspace(0, n, DS_BINS + 1).astype(int)
    res["ds"] = np.array([mag[edges[i] : edges[i + 1]].mean() for i in range(DS_BINS)], np.float32)
    res["hash"] = hashlib.md5(np.ascontiguousarray(acc, np.float32).tobytes()).hexdigest()
    for gthr in C.TRIGGER_SWEEP_G:
        hit = np.flatnonzero(mag > gthr)
        if len(hit) == 0:
            res["windows"][f"trig_{gthr:g}"] = None
            continue
        i0 = int(hit[0])
        s = i0 - C.PRE_N
        res["windows"][f"trig_{gthr:g}"] = (
            _cut(a, s, C.WIN_N), _cut(g, s, C.WIN_N), s < 0, s + C.WIN_N > n,
        )
    ip = int(mag.argmax())
    s = ip - C.WIN_N // 2
    res["windows"]["peak"] = (_cut(a, s, C.WIN_N), _cut(g, s, C.WIN_N), s < 0, s + C.WIN_N > n)
    return res


def _shard(path_str: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    from crashguard.data import iter_events

    meta_rows, feat_rows, wins_a, wins_g = [], [], [], []
    for split, eid, label, vs, hd, acc, gyro, _gps in iter_events(Path(path_str)):
        r = process_event(acc, gyro)
        meta_rows.append(
            dict(event_id=eid, split=split, label=label, vehiclesize=vs, gyro_is_hd=hd, n=r["n"], raw_peak=r["raw_peak"],
                 dropped=bool(r.get("dropped", False)), unwindowable=bool(r.get("unwindowable", False)),
                 gyro_mismatch=r["gyro_mismatch"], hash=r.get("hash", ""),
                 **{f"ds{i}": (float(r["ds"][i]) if "ds" in r else np.nan) for i in range(DS_BINS)})
        )
        for v, w in r["windows"].items():
            if w is None:
                feat_rows.append(dict(event_id=eid, variant=v, triggered=False, pad_before=False, pad_after=False))
            else:
                feat_rows.append(dict(event_id=eid, variant=v, triggered=True, pad_before=bool(w[2]), pad_after=bool(w[3])))
                wins_a.append(w[0])
                wins_g.append(w[1])
    feats = pd.DataFrame(feat_rows)
    if wins_a:
        fv = compute_features(np.stack(wins_a), np.stack(wins_g))
        fdf = pd.DataFrame(fv, columns=list(C.FEATURES))
        fdf.index = feats.index[feats.triggered]
        feats = feats.join(fdf)
    return pd.DataFrame(meta_rows), feats


def extract(raw_dir: Path = C.RAW_DIR, workers: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted((raw_dir / "data").glob("*.parquet"))
    workers = workers or min(8, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_shard, [str(f) for f in files]))
    meta = pd.concat([p[0] for p in parts], ignore_index=True)
    feats = pd.concat([p[1] for p in parts], ignore_index=True)
    for f in C.FEATURES:
        if f not in feats:
            feats[f] = np.nan
    return meta, feats


def window_stats(meta: pd.DataFrame, feats: pd.DataFrame) -> None:
    """Record dropped events, trigger rates and padding counts (MEASURED_SOFTWARE)."""
    from crashguard.data import LABELS
    from crashguard.results import record

    src = "data/processed/features.parquet"
    C.TABLES.mkdir(parents=True, exist_ok=True)
    dropped = meta[meta.dropped][["event_id", "split", "label", "raw_peak"]].copy()
    dropped["class"] = dropped.label.map(LABELS)
    dropped.rename(columns={"raw_peak": "peak_g"}).to_csv(C.TABLES / "dropped_events.csv", index=False)
    record("features.events_dropped_corrupt", int(len(dropped)), "events", "MEASURED_SOFTWARE", src,
           f"raw peak |a| above {C.MPU_RANGE_G:g} g")
    record("features.events_unwindowable", int(meta.unwindowable.sum()), "events", "MEASURED_SOFTWARE", src,
           "fewer than 2 accelerometer samples")
    record("features.events_not_1600_samples_kept", int(((meta.n != 1600) & ~meta.dropped).sum()), "events",
           "MEASURED_SOFTWARE", src, "windowed with the same rule")
    record("features.events_gyro_length_mismatch", int(meta.gyro_mismatch.sum()), "events", "MEASURED_SOFTWARE", src,
           "gyro truncated or edge-padded to accelerometer length")
    kept = meta[~meta.dropped & ~meta.unwindowable]
    f = feats.merge(kept[["event_id", "label"]], on="event_id")
    rows = []
    for (v, lab), g in f.groupby(["variant", "label"]):
        cls = LABELS[lab]
        rows.append(dict(variant=v, cls=cls, events=len(g), trigger_rate=g.triggered.mean(),
                         pad_before=int((g.pad_before & g.triggered).sum()), pad_after=int((g.pad_after & g.triggered).sum()),
                         triggered=int(g.triggered.sum())))
        record(f"trigger.{v}.{cls}.rate", round(float(g.triggered.mean()), 4), "fraction", "MEASURED_SOFTWARE", src)
        record(f"trigger.{v}.{cls}.events", int(len(g)), "events", "MEASURED_SOFTWARE", src)
        record(f"pad.{v}.{cls}.before_events", int((g.pad_before & g.triggered).sum()), "events", "MEASURED_SOFTWARE", src,
               "window starts before the event start; edge-repeat padding")
        record(f"pad.{v}.{cls}.after_events", int((g.pad_after & g.triggered).sum()), "events", "MEASURED_SOFTWARE", src,
               "window runs past the event end; edge-repeat padding")
    pd.DataFrame(rows).to_csv(C.TABLES / "trigger_rates.csv", index=False)


def main() -> None:
    meta, feats = extract()
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    meta.to_parquet(C.PROCESSED / "events_meta.parquet")
    feats.to_parquet(C.PROCESSED / "features.parquet")
    window_stats(meta, feats)
    print(f"events {len(meta)}, feature rows {len(feats)}")


if __name__ == "__main__":
    main()
