"""V1: independent re-derivation of the VZCrash duplicate audit from the raw supplied files (MEASURED_SOFTWARE).

This module does NOT import ``data``, ``split``, ``features``, ``windows_cache``, ``neardup`` or ``s2_dedup``. It reads the supplied parquet files directly and recomputes, from the definitions
written in docs/07_log/DECISIONS.md and docs/05_data_code/FEATURES.md:
(i) groups of events with the same hash of the full accelerometer array (also: of the full event, accelerometer + gyroscope + GPS speed), their counts per split and class, and the vehicle
    size labels each group spans;
(ii) window-level near-duplicates (the T5 rule): trigger-aligned 280-sample windows (1.0 s before and 1.8 s after the earliest sample whose |a| exceeds 2 g, each axis clipped to +-16 g first,
    edge-repeat padding), a test window is a near-duplicate if some train or validation window has correlation above 0.999 (per-axis mean removed, axes concatenated) AND maximum
    absolute difference below 0.01 g.
Only the stored numbers (results.json, results/tables/s2_neardup_test.csv) are read, for the comparison; nothing is taken from the earlier code paths. The output is written to
results/tables/vz_audit_*.csv and to results.json under ``vz.v1.``. No raw data is written outside data/processed/ (git-ignored).
"""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

RAW = Path("data/raw/data")
OUT = Path("results/tables")
TRIG_G, CLIP_G, PRE, POST = 2.0, 16.0, 100, 180
CORR_MIN, MAXDIFF_G = 0.999, 0.01
CLASS = {0: "crash", 1: "near_miss", 2: "normal_driving"}
SPLITS = ("train", "validation", "test")
CACHE = Path("data/processed/vz_audit_v1.npz")
EV_CACHE = Path("data/processed/vz_audit_v1_events.parquet")


def _flat(col) -> tuple[np.ndarray, np.ndarray]:
    off = col.offsets.to_numpy()
    v = col.values
    v = v.flatten() if hasattr(v, "flatten") else v
    return off, v.to_numpy(zero_copy_only=False)


def read_all() -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """One row per event (split, id, class, size, length, hashes, peaks) and the windows of the triggered events (float32, 280 x 3) per split."""
    rows, wins = [], {s: [] for s in SPLITS}
    win_owner = {s: [] for s in SPLITS}
    for f in sorted(glob.glob(str(RAW / "*.parquet"))):
        split = Path(f).name.split("-")[0]
        pf = pq.ParquetFile(f)
        for batch in pf.iter_batches(batch_size=1000):
            ids = batch.column("event_id").to_numpy()
            lab = batch.column("label").to_numpy()
            size = batch.column("vehiclesize").to_pylist()
            hd = batch.column("gyro_is_hd").to_pylist()
            go, gflat = _flat(batch.column("gsensor"))
            yo, yflat = _flat(batch.column("gyro"))
            so, sflat = _flat(batch.column("gps_speed"))
            for k in range(len(ids)):
                g = gflat[3 * go[k] : 3 * go[k + 1]].reshape(-1, 3)
                y = yflat[3 * yo[k] : 3 * yo[k + 1]]
                s = sflat[so[k] : so[k + 1]]
                gb = np.ascontiguousarray(g).tobytes()
                h_acc = hashlib.sha256(gb + len(g).to_bytes(4, "little")).hexdigest()
                h_full = hashlib.sha256(gb + np.ascontiguousarray(y).tobytes() + np.ascontiguousarray(s).tobytes()).hexdigest()
                mag_raw = float(np.linalg.norm(g, axis=1).max()) if len(g) else 0.0
                axis_raw = float(np.abs(g).max()) if len(g) else 0.0
                gc = np.clip(g, -CLIP_G, CLIP_G)
                mag = np.linalg.norm(gc, axis=1)
                hit = np.flatnonzero(mag > TRIG_G)
                trig = int(hit[0]) if len(hit) else -1
                rows.append(dict(split=split, event_id=int(ids[k]), label=int(lab[k]), cls=CLASS[int(lab[k])], vehiclesize=size[k], gyro_is_hd=bool(hd[k]), n=len(g), hash_acc=h_acc,
                                 hash_full=h_full, raw_peak_mag=mag_raw, raw_peak_axis=axis_raw, trig=trig))
                if trig >= 0:
                    idx = np.clip(np.arange(trig - PRE, trig + POST), 0, len(g) - 1)
                    wins[split].append(gc[idx].astype(np.float32))
                    win_owner[split].append(len(rows) - 1)
        print(split, f, len(rows), flush=True)
    ev = pd.DataFrame(rows)
    W = {s: (np.stack(wins[s]) if wins[s] else np.zeros((0, PRE + POST, 3), np.float32)) for s in SPLITS}
    for s in SPLITS:
        W[s + "_owner"] = np.array(win_owner[s])
    return ev, W


def load() -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    if CACHE.exists() and EV_CACHE.exists():
        z = np.load(CACHE)
        return pd.read_parquet(EV_CACHE), {k: z[k] for k in z.files}
    ev, W = read_all()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE, **W)
    ev.to_parquet(EV_CACHE)
    return ev, W


def unit(w: np.ndarray) -> np.ndarray:
    x = (w.astype(np.float64) - w.astype(np.float64).mean(axis=1, keepdims=True)).reshape(len(w), -1)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return np.divide(x, n, out=np.zeros_like(x), where=n > 1e-12).astype(np.float32)


def near_dups(q: np.ndarray, r: np.ndarray, chunk: int = 512) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """For each query window: the best correlation over the reference windows, whether some pair meets BOTH thresholds, whether some pair has correlation above the threshold, and the smallest
    maximum absolute difference among the pairs whose correlation is above the threshold (infinity if there is none)."""
    qu, ru = unit(q), unit(r)
    rf = r.reshape(len(r), -1).astype(np.float64)
    best = np.full(len(q), -1.0)
    both = np.zeros(len(q), bool)
    md_min = np.full(len(q), np.inf)
    for a in range(0, len(q), chunk):
        c = qu[a : a + chunk] @ ru.T
        best[a : a + chunk] = c.max(1)
        ii, jj = np.nonzero(c > CORR_MIN)
        for i, j in zip(ii, jj):
            md = float(np.abs(q[a + i].reshape(-1).astype(np.float64) - rf[j]).max())
            md_min[a + i] = min(md_min[a + i], md)
            if md < MAXDIFF_G:
                both[a + i] = True
    return best, both, best > CORR_MIN, md_min


def stored() -> dict:
    return {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}


def main() -> None:
    from crashguard.jp_common import Entries

    ev, W = load()
    OUT.mkdir(parents=True, exist_ok=True)
    st = stored()
    E = Entries("vz.v1", "results/tables/vz_audit_summary.csv")
    cmp_rows = []

    def compare(name: str, new, key: str | None, unit: str = "events") -> None:
        E.add(name, new, unit)
        if key is not None and key in st:
            old = st[key]
            E.add(f"{name}.stored", old, unit, notes=f"value stored in results.json under {key} before this audit")
            E.add(f"{name}.difference", float(new) - float(old), unit, notes="recomputed minus stored")
            cmp_rows.append(dict(quantity=name, recomputed=new, stored=old, difference=float(new) - float(old), stored_key=key))
        else:
            cmp_rows.append(dict(quantity=name, recomputed=new, stored=None, difference=None, stored_key=key))

    # ---- sizes of the splits and the dropped events
    for s in SPLITS:
        sub = ev[ev.split == s]
        E.add(f"events.{s}", len(sub), "events")
        for c in CLASS.values():
            E.add(f"events.{s}.{c}", int((sub.cls == c).sum()), "events")
    for name, col in (("magnitude", "raw_peak_mag"), ("axis", "raw_peak_axis")):
        for s in SPLITS:
            E.add(f"dropped_over_16g.{name}.{s}", int(((ev.split == s) & (ev[col] > CLIP_G)).sum()), "events", notes="raw peak above 16 g (the earlier pipeline dropped events by the magnitude rule)")
    drop = ev.raw_peak_mag > CLIP_G
    kept = ev[~drop]
    n_test_kept = int((kept.split == "test").sum())
    E.add("test_events_after_16g_drop", n_test_kept, "events")
    for c in CLASS.values():
        E.add(f"test_events_after_16g_drop.{c}", int(((kept.split == "test") & (kept.cls == c)).sum()), "events")
    compare("test_events_after_16g_drop.vs_stored", n_test_kept, "n15.test_events_before_exact_removal" if "n15.test_events_before_exact_removal" in st else None)
    # ---- (i) exact-hash groups
    for hname, col in (("acc", "hash_acc"), ("full", "hash_full")):
        g = ev.groupby(col)
        size = g.size()
        spl = g.split.nunique()
        multi = size[size > 1].index
        cross = spl[spl > 1].index
        E.add(f"exact.{hname}.groups_any_repeat", int(len(multi)), "groups", notes="hash shared by more than one event, any split")
        E.add(f"exact.{hname}.groups_across_splits", int(len(cross)), "groups")
        sub = ev[ev[col].isin(cross)]
        E.add(f"exact.{hname}.events_in_cross_split_groups", int(len(sub)), "events")
        for c in CLASS.values():
            E.add(f"exact.{hname}.events_in_cross_split_groups.{c}", int((sub.cls == c).sum()), "events")
        for s in SPLITS:
            E.add(f"exact.{hname}.events_in_cross_split_groups.{s}", int((sub.split == s).sum()), "events")
        # test events whose array also occurs in train or validation
        trv = set(ev[ev.split != "test"][col])
        tdup = ev[(ev.split == "test") & ev[col].isin(trv)]
        E.add(f"exact.{hname}.test_events_with_train_or_val_copy", int(len(tdup)), "events")
        for c in CLASS.values():
            E.add(f"exact.{hname}.test_events_with_train_or_val_copy.{c}", int((tdup.cls == c).sum()), "events")
        E.add(f"exact.{hname}.test_share_with_train_or_val_copy", round(len(tdup) / (ev.split == "test").sum(), 4), "fraction", notes="of all supplied test events")
        # labels and sizes inside groups
        lab_consistent = int((sub.groupby(col).label.nunique() == 1).sum())
        size_consistent = int((sub.groupby(col).vehiclesize.nunique() == 1).sum())
        E.add(f"exact.{hname}.cross_groups_label_consistent", lab_consistent, "groups", notes="all events of the group have the same class label")
        E.add(f"exact.{hname}.cross_groups_vehiclesize_consistent", size_consistent, "groups", notes="all events of the group have the same vehicle size label")
        if hname == "acc":
            compare("exact.acc.groups_across_splits.vs_stored", int(len(cross)), "leakage.exact_hash_groups_across_splits", "groups")
            compare("exact.acc.cross_events_total.vs_stored", int(len(sub)), "leakage.cross_split_group_events.total")
            for c, key in (("crash", "leakage.cross_split_group_events.crash"), ("near_miss", "leakage.cross_split_group_events.near_miss"), ("normal_driving", "leakage.cross_split_group_events.normal_driving")):
                compare(f"exact.acc.cross_events.{c}.vs_stored", int((sub.cls == c).sum()), key)
            first = ev.assign(order=range(len(ev))).sort_values("order")
            dup_total = int(first.duplicated(col).sum())
            compare("exact.acc.events_equal_to_an_earlier_event.vs_stored", dup_total, "leakage.exact_hash_duplicates_total")
            # group table (identifiers only)
            tab = []
            for gid, d in sub.groupby(col):
                tab.append(dict(group_hash=gid, n_events=len(d), splits=";".join(sorted(set(d.split))), classes=";".join(sorted(set(d.cls))), vehiclesizes=";".join(sorted(set(d.vehiclesize))),
                                event_ids=";".join(f"{r.split}:{r.event_id}" for r in d.itertuples()), full_hash_identical=int(d.hash_full.nunique() == 1), n_train=int((d.split == "train").sum()),
                                n_validation=int((d.split == "validation").sum()), n_test=int((d.split == "test").sum())))
            T = pd.DataFrame(tab).sort_values("group_hash")
            T.to_csv(OUT / "vz_audit_cross_split_groups.csv", index=False)
            E.add("exact.acc.cross_groups_with_test_member", int((T.n_test > 0).sum()), "groups")
            E.add("exact.acc.cross_groups_full_hash_identical", int(T.full_hash_identical.sum()), "groups", notes="accelerometer, gyroscope and GPS speed all identical")
            sz = pd.Series([len(v.split(";")) for v in T.vehiclesizes])
            E.add("exact.acc.cross_groups_spanning_several_vehiclesizes", int((sz > 1).sum()), "groups")
            vs = ev[ev.hash_acc.isin(cross)].vehiclesize.value_counts()
            for k_, v_ in vs.items():
                E.add(f"exact.acc.cross_events_by_vehiclesize.{k_}", int(v_), "events")
    # ---- (ii) window-level near-duplicates
    ev_idx = ev.reset_index(drop=True)
    keep_mask = ~(ev_idx.raw_peak_mag > CLIP_G).to_numpy()
    own = {s: W[s + "_owner"] for s in SPLITS}
    wk = {s: keep_mask[own[s]] for s in SPLITS}
    q = W["test"][wk["test"]]
    r = np.concatenate([W["train"][wk["train"]], W["validation"][wk["validation"]]])
    q_owner = own["test"][wk["test"]]
    E.add("near.test_windows_scanned", int(len(q)), "windows", notes="triggered test events (2 g trigger) that were not dropped for a raw peak above 16 g")
    E.add("near.reference_windows", int(len(r)), "windows", notes="triggered train and validation events")
    best, both, corr_only, md_min = near_dups(q, r)
    nt = int((ev_idx.split == "test").sum() - ((ev_idx.split == "test") & ~keep_mask).sum())
    compare("near.test_windows_scanned.vs_stored", int(len(q)), "dupscan.neardup.n_scanned", "windows")
    compare("near.test_events_not_triggered.vs_stored", nt - int(len(q)), "dupscan.neardup.n_not_triggered")
    compare("near.test_windows_both.vs_stored", int(both.sum()), "dupscan.neardup.n_both", "windows")
    compare("near.test_windows_corr_only.vs_stored", int((corr_only & ~both).sum()), "dupscan.neardup.n_corr_only", "windows")
    cls_q = ev_idx.cls.to_numpy()[q_owner]
    ids_q = ev_idx.event_id.to_numpy()[q_owner]
    for c in CLASS.values():
        E.add(f"near.test_windows_scanned.{c}", int((cls_q == c).sum()), "windows")
        E.add(f"near.test_windows_both.{c}", int((both & (cls_q == c)).sum()), "windows")
        n_c = int(((ev_idx.split == "test") & (ev_idx.cls == c) & keep_mask).sum())
        E.add(f"near.share_of_all_test_events_of_class.{c}", round(float((both & (cls_q == c)).sum() / n_c), 4), "fraction", notes=f"flagged windows of the class over all kept test events of the class ({n_c})")
    E.add("near.flagged_with_max_difference_exactly_0", int((both & (md_min == 0.0)).sum()), "windows", notes="flagged windows that equal a train or validation window sample for sample (after clipping and padding)")
    E.add("near.flagged_with_max_difference_below_0.001g", int((both & (md_min < 0.001)).sum()), "windows")
    E.add("near.share_of_triggered_test_windows", round(float(both.mean()), 4), "fraction", notes="flagged windows over triggered test windows scanned")
    E.add("near.share_of_all_test_events", round(float(both.sum() / nt), 4), "fraction", notes="flagged windows over all kept test events (the 'about 5%' figure of the tables is the flagged windows NOT already removed, over 24,022)")
    # compare with the stored per-event flags
    stored_tab = pd.read_csv(OUT / "s2_neardup_test.csv")
    s_both = set(stored_tab.event_id[stored_tab.both])
    mine = set(ids_q[both].tolist())
    E.add("near.event_set_agreement.only_recomputed", len(mine - s_both), "events", notes="flagged now, not flagged in results/tables/s2_neardup_test.csv")
    E.add("near.event_set_agreement.only_stored", len(s_both - mine), "events", notes="flagged in the stored table, not flagged now")
    E.add("near.event_set_agreement.both", len(mine & s_both), "events")
    # exact-duplicate test events that also have a triggered window flagged
    trv = set(ev_idx[ev_idx.split != "test"].hash_acc)
    exact_test_all = set(ev_idx[(ev_idx.split == "test") & ev_idx.hash_acc.isin(trv)].event_id)
    exact_test = exact_test_all
    E.add("near.flagged_events_also_exact_duplicates", len(mine & exact_test), "events")
    E.add("near.exact_duplicates_not_flagged_as_near", len(exact_test & set(ids_q.tolist()) - mine), "events", notes="exact copies with a window that the near-duplicate scan missed (expected 0)")
    pd.DataFrame(dict(event_id=sorted(exact_test_all))).to_csv(OUT / "vz_audit_test_exact_copy_ids.csv", index=False)
    pd.DataFrame(cmp_rows).to_csv(OUT / "vz_audit_comparison.csv", index=False)
    pd.DataFrame([dict(item=i["name"], value=i["value"]) for i in E.items]).to_csv(OUT / "vz_audit_summary.csv", index=False)
    pd.DataFrame(dict(event_id=ids_q, flagged_near_duplicate=both, best_corr=best)).to_csv(OUT / "vz_audit_test_near_dup_flags.csv", index=False)
    E.flush()
    for i in E.items:
        print(i["name"], i["value"])


if __name__ == "__main__":
    main()
