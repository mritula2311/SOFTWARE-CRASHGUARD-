"""X1 (docs/02_preregistration/PREREGISTRATION_V3.md): fixed-point version of the 10-tree depth-9 forest (``rfsel``) for the microcontroller. MEASURED_SOFTWARE for AP and recalls, ANALYTICAL for the flash estimate.

Thresholds are rounded to a 2^b-level affine grid per feature (range of the feature in the training windows) and leaf values to 2^b levels on [0, 1]; inputs stay in floating point. b = 16 (primary) and 8.
Metrics: AP of triggered test events, system recall at the validation-F1 threshold and at the 1% and 5% system-level false-alarm targets (thresholds re-chosen on validation with the quantised scores),
largest probability difference to the float model. De-duplicated test set (primary) and strict set (sensitivity). 5 seeds; paired bootstrap over test events.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import SEL, fit, frames_full, threshold_for_fpr
from crashguard.jp_common import Entries
from crashguard.models import op_thresholds
from crashguard.s2_dedup import fast_ap

SRC = "results/tables/x1_fixedpoint.csv"
SEEDS = C.SEEDS
BITS = (16, 8)
VARIANTS = ("float", "q16", "q8")
NODE_BYTES = {"float": 9, "q16": 7, "q8": 6}  # primary layout: int8 feature + threshold field + two int16 children
NODE_BYTES_COMPACT = {"float": 7, "q16": 5, "q8": 4}  # EXPLORATORY: implicit left child, one stored child index


def quantise(model, lo: np.ndarray, hi: np.ndarray, bits: int | None) -> list[tuple]:
    """Per tree: (left, right, feature, threshold, leaf value). ``bits=None`` keeps float values."""
    levels = (2 ** bits - 1) if bits else None
    out = []
    for est in model.estimators_:
        t = est.tree_
        thr = t.threshold.copy()
        leaf = t.value[:, 0, 1] / t.value[:, 0, :].sum(axis=1)
        if bits:
            f = np.where(t.feature >= 0, t.feature, 0)
            span = np.maximum(hi[f] - lo[f], 1e-12)
            q = np.clip(np.round((thr - lo[f]) / span * levels), 0, levels)
            thr = np.where(t.feature >= 0, lo[f] + q * span / levels, thr)
            leaf = np.round(leaf * levels) / levels
        out.append((t.children_left, t.children_right, t.feature, thr, leaf))
    return out


def predict(trees: list[tuple], X: np.ndarray) -> np.ndarray:
    n = len(X)
    ar = np.arange(n)
    acc = np.zeros(n)
    for left, right, feat, thr, leaf in trees:
        idx = np.zeros(n, dtype=np.int64)
        while True:
            lf = left[idx] == -1
            if lf.all():
                break
            f = np.where(lf, 0, feat[idx])
            go_left = X[ar, f] <= thr[idx]
            nxt = np.where(go_left, left[idx], right[idx])
            idx = np.where(lf, idx, nxt)
        acc += leaf[idx]
    return acc / len(trees)


def main() -> None:
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    cols = list(C.FEATURES)
    Xtr = tr[cols].to_numpy(np.float32)
    lo, hi = Xtr.min(0).astype(np.float64), Xtr.max(0).astype(np.float64)
    flags = pd.read_csv(C.TABLES / "vz_audit_test_near_dup_flags.csv")
    near = set(flags.event_id[flags.flagged_near_duplicate])
    sets = {"dedup": np.ones(len(te), bool), "strict": ~te.event_id.isin(near).to_numpy()}
    y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
    E = Entries("x.x1", SRC)
    S_te, T_ = {v: [] for v in VARIANTS}, {v: [] for v in VARIANTS}
    maxdiff, changed, nodes = [], [], []
    for seed in SEEDS:
        scorer, m = fit(SEL, seed, tr, va_trig)
        nodes.append(int(sum(e.tree_.node_count for e in m.estimators_)))
        forests = {"float": quantise(m, lo, hi, None), "q16": quantise(m, lo, hi, 16), "q8": quantise(m, lo, hi, 8)}
        Xva, Xte = va[cols].to_numpy(np.float32), te[cols].to_numpy(np.float32)
        ref_check = scorer(te[te.triggered])
        for v, fo in forests.items():
            sva = np.full(len(va), -1.0)
            sva[va.triggered.to_numpy(bool)] = predict(fo, Xva[va.triggered.to_numpy(bool)].astype(np.float64))
            ste = np.full(len(te), -1.0)
            ste[trig] = predict(fo, Xte[trig].astype(np.float64))
            if v == "float":
                E.add(f"seed{seed}.float_traversal_vs_sklearn_max_abs_diff", float(np.abs(ste[trig] - ref_check).max()), "probability", "check: the explicit traversal reproduces predict_proba")
            vt = va_trig
            f1, _ = op_thresholds(vt.y.to_numpy(), sva[va.triggered.to_numpy(bool)])
            t1, t5 = threshold_for_fpr(va.y.to_numpy(), sva, 0.01), threshold_for_fpr(va.y.to_numpy(), sva, 0.05)
            S_te[v].append(ste)
            T_[v].append((f1, t1, t5))
        for v in ("q16", "q8"):
            d = np.abs(S_te[v][-1][trig] - S_te["float"][-1][trig])
            maxdiff.append((v, seed, float(d.max())))
            changed.append((v, seed, int(((S_te[v][-1] >= T_[v][-1][0]) != (S_te["float"][-1] >= T_["float"][-1][0])).sum())))
    for v, seed, d in maxdiff:
        E.add(f"max_prob_difference.{v}.seed{seed}", d, "probability", "largest absolute difference to the float model over the triggered test events")
    for v in ("q16", "q8"):
        E.add(f"max_prob_difference.{v}.max_over_seeds", max(d for vv, _s, d in maxdiff if vv == v), "probability")
        E.add(f"decisions_changed.{v}.mean_over_seeds", float(np.mean([c for vv, _s, c in changed if vv == v])), "events", "test events whose decision at the validation-F1 threshold differs from the float model")
    n_nodes = float(np.mean(nodes))
    for lay, tab in (("primary", NODE_BYTES), ("compact", NODE_BYTES_COMPACT)):
        for v in VARIANTS:
            E.add(f"flash.{lay}.{v}.bytes", n_nodes * tab[v], "bytes", "nodes x bytes per node; host estimate, not an ESP32 compile report" + ("; EXPLORATORY layout (implicit left child)" if lay == "compact" else ""), origin="ANALYTICAL")
            if v != "float":
                E.add(f"flash.{lay}.{v}.reduction", 1 - tab[v] / tab["float"], "fraction", "against the float32 node of the same layout", origin="ANALYTICAL")
        E.add(f"flash.{lay}.q16_vs_export_9byte.reduction", 1 - tab["q16"] / NODE_BYTES["float"], "fraction", "against the 9-byte node of the existing export", origin="ANALYTICAL")
    E.add("nodes.mean_over_seeds", n_nodes, "nodes")
    METS = ("ap", "sys_recall", "recall_at_1pct", "recall_at_5pct")

    def stat(idx: np.ndarray, which: np.ndarray) -> dict:
        sel = idx[which[idx]]
        yy, tt = y[sel], trig[sel]
        pos = yy == 1
        out = {}
        for v in VARIANTS:
            per = []
            for s, (a, b, c) in zip(S_te[v], T_[v]):
                ss = s[sel]
                per.append((fast_ap(yy[tt], ss[tt]), float((ss[pos] >= a).mean()), float((ss[pos] >= b).mean()), float((ss[pos] >= c).mean())))
            for k, mname in enumerate(METS):
                out[(v, mname)] = float(np.mean([p[k] for p in per]))
        return out

    res = {}
    for sname, which in sets.items():
        E.add(f"n_events.{sname}", int(which.sum()), "events")
        point = stat(np.arange(len(te)), which)
        dr = [stat(i, which) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
        for (v, mname), val in point.items():
            d = np.array([x[(v, mname)] for x in dr])
            E.ci(f"{sname}.{v}.{mname}", (val, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "AP" if mname == "ap" else "fraction", d=5)
        for v in ("q16", "q8"):
            for mname in METS:
                d = np.array([x[("float", mname)] - x[(v, mname)] for x in dr])
                pt = point[("float", mname)] - point[(v, mname)]
                E.ci(f"{sname}.diff_float_minus_{v}.{mname}", (pt, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "fraction", "positive = the quantised model is lower", d=5)
                res[(sname, v, mname)] = (pt, d)
    pt, d = res[("dedup", "q16", "ap")]
    hi = float(np.quantile(d, 0.975))
    p_raw = float(max(np.mean(d >= 0.005), 1.0 / (len(d) + 1)))
    red = 1 - NODE_BYTES["q16"] / NODE_BYTES["float"]
    E.add("hX1.ap_loss_q16", round(pt, 5), "AP", "float AP minus 16-bit AP, de-duplicated test set, 5-seed mean")
    E.add("hX1.ap_loss_q16_hi", round(hi, 5), "AP", "upper 95% bound")
    E.add("hX1.p_raw", round(p_raw, 4), "probability", "share of resamples with loss at or above 0.005; floor 0.001")
    E.add("hX1.ap_condition_met", int(hi <= 0.005), "flag")
    E.add("hX1.flash_reduction_primary", round(red, 4), "fraction", "16-bit against float32, primary layout (analytical)", origin="ANALYTICAL")
    E.add("hX1.flash_condition_met", int(red >= 0.30), "flag", origin="ANALYTICAL")
    E.add("hX1.criterion_met", int(hi <= 0.005 and red >= 0.30), "flag", "both conditions")
    E.flush()
    rows = [dict(set=s, variant=v, metric=m, **dict(zip(("diff", "lo", "hi"), (p, float(np.quantile(dd, 0.025)), float(np.quantile(dd, 0.975)))))) for (s, v, m), (p, dd) in res.items()]
    pd.DataFrame(rows).to_csv(C.TABLES / "x1_fixedpoint.csv", index=False)
    print(pd.DataFrame(rows).round(5).to_string())
    print("H-X1 loss", pt, hi, "p", p_raw, "flash red", red, "nodes", n_nodes, "maxdiff", maxdiff[:2])


if __name__ == "__main__":
    main()
