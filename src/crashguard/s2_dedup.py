"""S2: effect of the cross-split duplicates (N8) on the headline, and a near-duplicate scan (plan: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S2). N8 is a data-quality finding, not a performance finding.

Side by side: supplied test split against the de-duplicated test split, with the paired difference from one bootstrap over the supplied events
(the de-duplicated set is the drawn rows that are not flagged). Threshold = validation maximum-F1 threshold, as in the headline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import windows_cache as W
from crashguard.detector_extra import SEL, fit, score_all
from crashguard.models import PRIMARY, op_thresholds
from crashguard.neardup import CORR_MIN, MAXDIFF_G, scan
from crashguard.results import record_many
from crashguard.split import leaky_test_ids, load_variant

SRC = "results/tables/s2_headline_side_by_side.csv"
SEEDS = (C.SEED,) + C.SEEDS
MODELS = ("rf15", SEL)
SETS = ("supplied", "dedup", "dedup_nd")  # supplied; exact/NN de-duplicated (primary); also without the window-level near-duplicates
METRICS = ("sys_recall", "sys_fpr", "ap", "sys_ap")


def fast_ap(y: np.ndarray, s: np.ndarray) -> float:
    """Average precision with ties handled as sklearn does (one threshold per distinct score)."""
    if y.sum() == 0:
        return float("nan")
    o = np.argsort(-s, kind="stable")
    ys, ss = y[o], s[o]
    last = np.r_[np.flatnonzero(np.diff(ss) != 0), len(ss) - 1]
    tp = np.cumsum(ys)[last]
    prec = tp / (last + 1)
    rec = tp / ys.sum()
    return float(np.sum(np.diff(np.r_[0.0, rec]) * prec))


def metrics(y, s, trig, thr) -> dict:
    pred = s >= thr
    pos, neg = y == 1, y == 0
    return dict(sys_recall=float(pred[pos].mean()), sys_fpr=float(pred[neg].mean()), ap=fast_ap(y[trig], s[trig]), sys_ap=fast_ap(y, s))


def load_frames():
    df = load_variant(PRIMARY)
    df["triggered"] = df.triggered.fillna(False).astype(bool)
    tr = df[(df.split == "train") & df.triggered]
    va = df[df.split == "validation"]
    te = df[df.split == "test"].reset_index(drop=True)
    te["leaky"] = te.event_id.isin(leaky_test_ids())
    return tr, va, te


def neardup_test() -> pd.DataFrame:
    """Near-duplicate scan of every triggered test window against the train and validation windows."""
    te = W.load("test", dedup=False)
    ref = np.concatenate([W.load("train")["acc"], W.load("validation")["acc"]])
    r = scan(te["acc"], ref)
    df = pd.DataFrame(dict(event_id=te["event_id"], label=te["label"], **r))
    df["leaky"] = df.event_id.isin(leaky_test_ids())
    return df


def paired_side_by_side(model: str, seeds, tr, va, te, nd_ids: set[int]) -> dict:
    """Metrics of ``model`` on the three sets, averaged over ``seeds``, with bootstrap intervals and the paired difference (supplied minus dedup)."""
    va_trig = va[va.triggered]
    y = te.y.to_numpy()
    trig = te.triggered.to_numpy(bool)
    leaky = te.leaky.to_numpy(bool)
    nd = te.event_id.isin(nd_ids).to_numpy()
    masks = {"supplied": np.ones(len(te), bool), "dedup": ~leaky, "dedup_nd": ~leaky & ~nd}
    S, T = [], []
    for seed in seeds:
        scorer, _ = fit(model, seed, tr, va_trig)
        thr, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
        S.append(score_all(scorer, te))
        T.append(thr)

    def stat(idx: np.ndarray) -> dict:
        out = {}
        for k, m in masks.items():
            sel = idx[m[idx]]
            per = [metrics(y[sel], s[sel], trig[sel], t) for s, t in zip(S, T)]
            for met in METRICS:
                out[(k, met)] = float(np.mean([p[met] for p in per]))
        return out

    point = stat(np.arange(len(te)))
    draws = [stat(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
    res = {}
    for (k, met), v in point.items():
        d = np.array([x[(k, met)] for x in draws])
        res[(k, met)] = (v, float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975)))
    for k in ("dedup", "dedup_nd"):
        for met in METRICS:
            d = np.array([x[("supplied", met)] - x[(k, met)] for x in draws])
            res[(f"diff_supplied_minus_{k}", met)] = (point[("supplied", met)] - point[(k, met)], float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975)))
    res["n"] = {k: int(m.sum()) for k, m in masks.items()}
    res["n_pos"] = {k: int(y[m].sum()) for k, m in masks.items()}
    return res


def main() -> None:
    tr, va, te = load_frames()
    nd = neardup_test()
    nd.to_csv(C.TABLES / "s2_neardup_test.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes="", src=SRC):
        ent.append(dict(name=f"dupscan.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    nsrc = "results/tables/s2_neardup_test.csv"
    n = len(nd)
    flagged = nd.both.to_numpy()
    add("neardup.n_scanned", n, "events", src=nsrc, notes=f"triggered test windows scanned against train and validation windows; thresholds fixed in advance: correlation above {CORR_MIN}, maximum absolute difference below {MAXDIFF_G} g")
    add("neardup.n_not_triggered", int(len(te) - n), "events", src=nsrc, notes="test events with no window (trigger not passed); not scanned")
    add("neardup.n_both", int(flagged.sum()), "events", src=nsrc, notes="a single train or validation window meets both thresholds")
    add("neardup.n_corr_only", int((nd.corr_only & ~nd.diff_only).sum()), "events", src=nsrc, notes="correlation above the threshold but no pair within the maximum-difference threshold")
    add("neardup.n_diff_only", int((nd.diff_only & ~nd.corr_only).sum()), "events", src=nsrc, notes="maximum difference below the threshold but correlation not above it")
    add("neardup.n_both_and_in_leaky_set", int((flagged & nd.leaky).sum()), "events", src=nsrc, notes="near-duplicates that the exact-hash or 32-bin rule already removed from the primary test set")
    add("neardup.n_both_new", int((flagged & ~nd.leaky).sum()), "events", src=nsrc, notes="near-duplicates NOT removed from the primary test set")
    add("neardup.n_leaky_triggered", int(nd.leaky.sum()), "events", src=nsrc, notes="triggered test events removed from the primary test set by the exact-hash or nearest-neighbour rule")
    for lab, nm in ((0, "crash"), (1, "near_miss"), (2, "normal")):
        add(f"neardup.n_both_new.{nm}", int((flagged & ~nd.leaky & (nd.label == lab)).sum()), "events", src=nsrc, notes="class of the near-duplicate test events not removed")
    add("neardup.max_corr_median", round(float(np.median(nd.max_corr)), 5), "correlation", src=nsrc, notes="median over triggered test events of the best correlation to a train or validation window")
    fin = nd.min_maxdiff.replace(np.inf, np.nan)
    add("neardup.min_maxdiff_median_where_within_bound", round(float(np.nanmedian(fin)), 6) if fin.notna().any() else "NOT_RUN", "g", src=nsrc,
        notes="median over events that have a window within the exact L2 bound; the others have a maximum difference above the threshold" if fin.notna().any() else "no event has a window within the L2 bound")
    nd_ids = set(nd.event_id[flagged & ~nd.leaky])
    for model in MODELS:
        for tag, seeds in (("mean5", C.SEEDS), ("seed42", (C.SEED,))):
            res = paired_side_by_side(model, seeds, tr, va, te, nd_ids)
            for (k, met), (v, lo, hi) in ((a, b) for a, b in res.items() if isinstance(a, tuple)):
                p = f"{model}.{tag}.{k}.{met}"
                add(p, round(v, 5), "fraction" if "ap" not in met else "AP", notes=("mean over seeds 0 to 4; interval is for that mean" if tag == "mean5" else "seed 42 only") + "; threshold = validation F1 maximum; paired difference = supplied minus de-duplicated, same drawn rows")
                add(p + "_lo", round(lo, 5), "fraction", notes="95% bootstrap interval, 1000 resamples")
                add(p + "_hi", round(hi, 5), "fraction", notes="95% bootstrap interval, 1000 resamples")
            for k, v in res["n"].items():
                add(f"{model}.{tag}.n_events.{k}", v, "events", notes="test events in the set")
            for k, v in res["n_pos"].items():
                add(f"{model}.{tag}.n_crash.{k}", v, "events", notes="crash events in the set")
            rows = [dict(model=model, tag=tag, set=k, metric=met, value=res[(k, met)][0], lo=res[(k, met)][1], hi=res[(k, met)][2]) for k in SETS for met in METRICS]
            for k in ("dedup", "dedup_nd"):
                for met in METRICS:
                    kk = f"diff_supplied_minus_{k}"
                    rows.append(dict(model=model, tag=tag, set=kk, metric=met, value=res[(kk, met)][0], lo=res[(kk, met)][1], hi=res[(kk, met)][2]))
            pd.DataFrame(rows).to_csv(C.TABLES / f"s2_headline_{model}_{tag}.csv", index=False)
            print(model, tag, {k: tuple(round(x, 4) for x in res[(k, "sys_recall")]) for k in SETS + ("diff_supplied_minus_dedup",)})
    pd.DataFrame(ent).to_csv(SRC, index=False)
    record_many(ent, purge_prefixes=("dupscan.",))


if __name__ == "__main__":
    main()
