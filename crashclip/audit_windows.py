"""De-duplication audit for window datasets (hashes only; no raw data leaves the machine).

For a dataset of fixed-length sensor windows stored as one array of shape (n, length, channels) plus a split label per window, the audit reports
 1. exact groups: windows with the same SHA-256 hash of their bytes, and how many groups span more than one split;
 2. near-duplicate windows across splits: pairs of windows with correlation above 0.999 and maximum absolute difference below 0.01 (in the unit of the data), found among windows with the same
    rounded (peak, length-weighted mean) key, so the scan is linear in practice.
Output: a CSV of group hashes with split labels and counts, and a JSON summary. A window dataset can then be released or compared without redistributing samples.
Usage: python crashclip/audit_windows.py windows.npy splits.txt --out audit
(``splits.txt``: one label per line, the same order as the windows.)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

CORR, MAXDIFF = 0.999, 0.01


def exact_groups(W: np.ndarray, splits: np.ndarray) -> pd.DataFrame:
    h = [hashlib.sha256(np.ascontiguousarray(w).tobytes()).hexdigest() for w in W]
    df = pd.DataFrame(dict(hash=h, split=splits))
    g = df.groupby("hash").agg(n=("split", "size"), n_splits=("split", "nunique"), splits=("split", lambda s: ",".join(sorted(set(s)))))
    return g[g.n > 1].reset_index()


def near_duplicates(W: np.ndarray, splits: np.ndarray) -> list[tuple[int, int]]:
    """Index pairs in different splits that are near-identical. Windows are bucketed by (rounded peak, rounded sum) to keep the scan small, then compared within buckets (and the neighbouring bucket)."""
    flat = W.reshape(len(W), -1).astype(np.float64)
    key = [(int(np.round(np.abs(f).max() * 20)), int(np.round(f.sum() / 5))) for f in flat]
    buckets: dict = defaultdict(list)
    for i, k in enumerate(key):
        buckets[k].append(i)
    pairs = []
    for (a, b), idx in buckets.items():
        cand = list(idx)
        for da in (0, 1):
            for db in (-1, 0, 1):
                if (da, db) != (0, 0):
                    cand += buckets.get((a + da, b + db), [])
        for i in idx:
            for j in cand:
                if j <= i or splits[i] == splits[j]:
                    continue
                if np.abs(flat[i] - flat[j]).max() < MAXDIFF:
                    x, y = flat[i] - flat[i].mean(), flat[j] - flat[j].mean()
                    den = np.linalg.norm(x) * np.linalg.norm(y)
                    if den == 0 or float(x @ y / den) > CORR:
                        pairs.append((i, j))
    return sorted(set(pairs))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("windows")
    ap.add_argument("splits")
    ap.add_argument("--out", default="audit")
    a = ap.parse_args()
    W = np.load(a.windows)
    splits = np.array(Path(a.splits).read_text().split())
    g = exact_groups(W, splits)
    pairs = near_duplicates(W, splits)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    g.to_csv(Path(a.out) / "exact_groups.csv", index=False)
    s = dict(n_windows=int(len(W)), exact_groups=int(len(g)), exact_groups_crossing_splits=int((g.n_splits > 1).sum()), near_duplicate_pairs_across_splits=len(pairs),
             windows_with_cross_split_near_duplicate=len({i for p in pairs for i in p}))
    (Path(a.out) / "summary.json").write_text(json.dumps(s, indent=2))
    print(s)


if __name__ == "__main__":
    main()
