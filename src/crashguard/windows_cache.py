"""Cache of the firmware-style windows (trigger variant ``trig_2``, 1.0 s before and 1.8 s after the trigger, clipped to the sensor range) of every triggered VZCrash event.

The feature pipeline keeps only features. The extra experiments (early classification, sensor-spoofing robustness, physical scaling) need the signal windows, so they are
cut once here with exactly the same rule as ``features.process_event`` and stored in ``data/processed/win_<split>.npz`` (git-ignored). Window arrays are float32.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import features as F
from crashguard.split import leaky_test_ids

VARIANT = f"trig_{C.TRIGGER_G:g}"
SPLITS = ("train", "validation", "test")


def _shard(path_str: str) -> dict:
    from crashguard.data import iter_events

    ids, labels, sizes, acc_w, gyro_w, _raw_n = [], [], [], [], [], []
    for _split, eid, label, vs, _hd, acc, gyro, _gps in iter_events(Path(path_str)):
        r = F.process_event(acc, gyro)
        w = r["windows"].get(VARIANT) if r.get("windows") else None
        if w is None or r.get("dropped") or r.get("unwindowable"):
            continue
        ids.append(eid)
        labels.append(label)
        sizes.append(str(vs))
        acc_w.append(w[0].astype(np.float32))
        gyro_w.append(w[1].astype(np.float32))
    n = len(ids)
    return dict(split=Path(path_str).name.split("-")[0], event_id=np.array(ids, np.int64), label=np.array(labels, np.int8), vehiclesize=np.array(sizes),
                acc=np.stack(acc_w) if n else np.zeros((0, C.WIN_N, 3), np.float32), gyro=np.stack(gyro_w) if n else np.zeros((0, C.WIN_N, 3), np.float32))


def path_for(split: str) -> Path:
    return C.PROCESSED / f"win_{split}.npz"


def build(workers: int | None = None, force: bool = False) -> None:
    if not force and all(path_for(s).exists() for s in SPLITS):
        return
    files = sorted((C.RAW_DIR / "data").glob("*.parquet"))
    workers = workers or min(8, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_shard, [str(f) for f in files]))
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    for s in SPLITS:
        ps = [p for p in parts if p["split"] == s]
        np.savez(path_for(s), event_id=np.concatenate([p["event_id"] for p in ps]), label=np.concatenate([p["label"] for p in ps]),
                 vehiclesize=np.concatenate([p["vehiclesize"] for p in ps]), acc=np.concatenate([p["acc"] for p in ps]), gyro=np.concatenate([p["gyro"] for p in ps]))


def load(split: str, dedup: bool = True) -> dict:
    """Windows of one split. For the test split the cross-split duplicates are removed (the primary test set). ``y`` = 1 for a crash."""
    build()
    z = np.load(path_for(split))
    d = {k: z[k] for k in z.files}
    if split == "test" and dedup:
        keep = ~np.isin(d["event_id"], list(leaky_test_ids()))
        d = {k: v[keep] for k, v in d.items()}
    d["y"] = (d["label"] == 0).astype(int)
    return d


def features_of(acc: np.ndarray, gyro: np.ndarray, post_n: int | None = None) -> pd.DataFrame:
    """The 14 features of windows, optionally truncated to ``post_n`` samples after the trigger (the first PRE_N + post_n samples are kept)."""
    if post_n is not None:
        n = C.PRE_N + int(post_n)
        acc, gyro = acc[:, :n], gyro[:, :n]
    return pd.DataFrame(F.compute_features(acc, gyro), columns=list(C.FEATURES))


if __name__ == "__main__":
    build()
    for s in SPLITS:
        d = load(s, dedup=False)
        print(s, len(d["event_id"]), int(d["y"].sum()))
