"""CrashClip evaluation: severity-class predictions against the pooled NHTSA reference, mode-stratified, with grouped bootstrap intervals.

Input: a CSV with columns ``rid`` and ``pred_class`` (0 Low, 1 Moderate, 2 Severe, 3 Critical) for the records of the chosen fold (``records.csv`` lists them).
Usage: python crashclip/evaluate.py predictions.csv --fold test
Output: macro-F1, balanced accuracy, under-triage and over-triage rates (definitions in README.md) overall and per mode, each with a 95% interval from 1,000 resamples of whole make-and-model groups (seed 42).
Only numpy and pandas are needed.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MODES = ("frontal_barrier", "pole", "side", "other")


def macro_f1(y, p, k=4):
    f = []
    for c in range(k):
        if np.sum(y == c) == 0 and np.sum(p == c) == 0:
            continue
        tp, fp, fn = np.sum((y == c) & (p == c)), np.sum((y != c) & (p == c)), np.sum((y == c) & (p != c))
        f.append(2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0)
    return float(np.mean(f)) if f else float("nan")


def balanced_acc(y, p, k=4):
    r = [np.mean(p[y == c] == c) for c in range(k) if np.sum(y == c)]
    return float(np.mean(r)) if r else float("nan")


def under_triage(y, p):
    m = y >= 2
    return float(np.mean(p[m] < y[m])) if m.any() else float("nan")


def over_triage(y, p):
    m = y <= 1
    return float(np.mean(p[m] > y[m])) if m.any() else float("nan")


METRICS = {"macro_f1": macro_f1, "balanced_acc": balanced_acc, "under_triage": under_triage, "over_triage": over_triage}


def grouped_ci(y, p, groups, fn, n_boot=1000, seed=42):
    ug = sorted(set(groups.tolist()))
    members = [np.flatnonzero(groups == g) for g in ug]
    rng = np.random.default_rng(seed)
    d = []
    for _ in range(n_boot):
        idx = np.concatenate([members[j] for j in rng.integers(0, len(members), len(members))])
        d.append(fn(y[idx], p[idx]))
    d = np.array(d, float)
    return fn(y, p), float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))


def evaluate(pred: pd.DataFrame, fold: str = "test") -> pd.DataFrame:
    rec = pd.read_csv(HERE / "records.csv")
    rec = rec[rec.fold == fold].merge(pred[["rid", "pred_class"]], on="rid", how="left")
    if rec.pred_class.isna().any():
        raise SystemExit(f"{int(rec.pred_class.isna().sum())} records of fold '{fold}' have no prediction")
    y, p, g = rec.ref_class.to_numpy(int), rec.pred_class.to_numpy(int), rec.group_hash.to_numpy()
    rows = []
    for scope in ("all",) + MODES:
        m = np.ones(len(rec), bool) if scope == "all" else (rec["mode"] == scope).to_numpy()
        if m.sum() < 5:
            continue
        for name, fn in METRICS.items():
            pt, lo, hi = grouped_ci(y[m], p[m], g[m], fn)
            rows.append(dict(scope=scope, n=int(m.sum()), metric=name, value=pt, lo=lo, hi=hi))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("predictions")
    ap.add_argument("--fold", default="test", choices=["dev", "val", "test"])
    a = ap.parse_args()
    print(evaluate(pd.read_csv(a.predictions), a.fold).round(4).to_string(index=False))
