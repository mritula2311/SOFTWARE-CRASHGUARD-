"""S3: N20 re-run with a clean calibration set (plan and decision rule: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S3, written before this was run).

Calibration pool: the non-crash events of the validation split, with every event removed that matches a training or a test event (exact raw-array hash, or the window-level
near-duplicate rule of ``neardup``). The "dirty" pool is the full validation split, so the two can be compared under the same code. Test set: the de-duplicated test split.

Methods: conformal (split-conformal, k = ceil((n + 1)(1 - alpha))), validation (the existing smallest-threshold rule), weighted (EXPLORATORY: the calibration negatives are re-weighted
so that their vehicle-size mix matches the pooled test negatives; weighted (1 - alpha) quantile with the test point carrying the largest weight).

Decision rule, fixed before the run: the guarantee holds if the upper end of the 95% bootstrap interval for the mean test false-alarm rate is at or below alpha plus one binomial standard
error of the test set, sqrt(alpha (1 - alpha) / n_test_negatives). The interval is over (seed, calibration draw) pairs and does not include the test-set sampling error, which the
added standard error stands in for. The 95% bound (1.96 standard errors) is also recorded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import windows_cache as W
from crashguard.conformal import ALPHAS, CATS, DRAWS, SIZES, conformal_threshold, empirical_threshold
from crashguard.detector_extra import fit, frames_full, score_all
from crashguard.neardup import scan
from crashguard.results import record_many

SEEDS = (C.SEED,) + C.SEEDS
SRC = "results/tables/s3_conformal.csv"
METHODS = ("conformal", "validation", "weighted")


def weighted_threshold(scores: np.ndarray, weights: np.ndarray, alpha: float) -> float:
    """Weighted split-conformal threshold: smallest calibration score whose cumulative weight reaches (1 - alpha) of (sum of weights + the test point's weight, taken as the largest weight).

    inf if no score reaches it (no alarms). An event alarms if its score is strictly above this value.
    """
    o = np.argsort(scores, kind="stable")
    s, w = np.asarray(scores, float)[o], np.asarray(weights, float)[o]
    total = w.sum() + w.max()
    cum = np.cumsum(w) / total
    k = np.flatnonzero(cum >= 1.0 - alpha)
    return float(s[k[0]]) if k.size else float("inf")


def size_weights(cal_sizes: np.ndarray, test_sizes: np.ndarray) -> np.ndarray:
    """Per-event weight = share of the category among test negatives / share among calibration negatives (categories absent from the test mix get 0)."""
    cats = sorted(set(cal_sizes.tolist()) | set(test_sizes.tolist()))
    pt = {c: float((test_sizes == c).mean()) for c in cats}
    pc = {c: float((cal_sizes == c).mean()) for c in cats}
    return np.array([pt[c] / pc[c] if pc[c] > 0 else 0.0 for c in cal_sizes])


def duplicate_flags() -> tuple[pd.DataFrame, dict]:
    """Validation events matching a training or a test event: exact hash (all events) and window near-duplicate (triggered events). Returns (flags by event_id, counts)."""
    meta = pd.read_parquet(C.PROCESSED / "events_meta.parquet", columns=["event_id", "split", "label", "hash", "dropped"])
    meta = meta[~meta.dropped & (meta.hash != "")]
    va = meta[meta.split == "validation"][["event_id", "label", "hash"]].copy()
    h_tr, h_te = set(meta[meta.split == "train"].hash), set(meta[meta.split == "test"].hash)
    va["hash_train"] = va.hash.isin(h_tr)
    va["hash_test"] = va.hash.isin(h_te)
    wv = W.load("validation")
    wtr, wte = W.load("train")["acc"], W.load("test", dedup=False)["acc"]
    s_tr, s_te = scan(wv["acc"], wtr), scan(wv["acc"], wte)
    nd = pd.DataFrame(dict(event_id=wv["event_id"], nd_train=s_tr["both"], nd_test=s_te["both"]))
    va = va.merge(nd, on="event_id", how="left")
    for c in ("nd_train", "nd_test"):
        va[c] = va[c].fillna(False).astype(bool)
    va["flag"] = va.hash_train | va.hash_test | va.nd_train | va.nd_test
    cnt = {}
    neg = va.label != 0
    for nm, m in (("all", va.label >= 0), ("non_crash", neg), ("crash", va.label == 0)):
        cnt[nm] = dict(n=int(m.sum()), hash_train=int((va.hash_train & m).sum()), hash_test=int((va.hash_test & m).sum()), nd_train=int((va.nd_train & m).sum()), nd_test=int((va.nd_test & m).sum()),
                       nd_new=int(((va.nd_train | va.nd_test) & ~(va.hash_train | va.hash_test) & m).sum()), flagged=int((va.flag & m).sum()))
    return va, cnt


def runs(va, te, clean_ids: set[int], hash_ids: set[int], scorer_by_seed) -> tuple[pd.DataFrame, pd.DataFrame]:
    yv, yt = va.y.to_numpy(), te.y.to_numpy()
    sv_sizes, st_sizes = va.vehiclesize.to_numpy(), te.vehiclesize.to_numpy()
    clean = va.event_id.isin(clean_ids).to_numpy()
    hashclean = va.event_id.isin(hash_ids).to_numpy()
    rng = np.random.default_rng(C.SEED)
    rows, shift = [], []
    for seed in SEEDS:
        sv, st = scorer_by_seed[seed]
        for calib, pool_mask in (("dirty", np.ones(len(va), bool)), ("hashgroup", hashclean), ("clean", clean)):
            pool = np.flatnonzero((yv == 0) & pool_mask)
            for alpha in ALPHAS:
                for size in SIZES:
                    for _d in range(1 if size is None else DRAWS):
                        sel = pool if size is None else rng.choice(pool, size=min(size, len(pool)), replace=False)
                        cal, w = sv[sel], size_weights(sv_sizes[sel], st_sizes[yt == 0])
                        thr = {"conformal": ("gt", conformal_threshold(cal, alpha)), "validation": ("ge", empirical_threshold(cal, alpha)), "weighted": ("gt", weighted_threshold(cal, w, alpha))}
                        for meth, (op, t) in thr.items():
                            alarm = st > t if op == "gt" else st >= t
                            rows.append(dict(calib=calib, seed=seed, alpha=alpha, size="all" if size is None else size, method=meth, fa=float(alarm[yt == 0].mean()),
                                             recall=float(alarm[yt == 1].mean()), n_cal=len(sel)))
            for held in CATS:  # leave-one-category-out: calibrate on the other categories, test on the held-out one
                cal_mask = (yv == 0) & pool_mask & (sv_sizes != held)
                tm = st_sizes == held
                if cal_mask.sum() < 50 or (tm & (yt == 0)).sum() < 50:
                    continue
                for alpha in ALPHAS:
                    cal = sv[cal_mask]
                    w = size_weights(sv_sizes[cal_mask], st_sizes[(yt == 0) & ~tm])
                    for meth, (op, t) in {"conformal": ("gt", conformal_threshold(cal, alpha)), "validation": ("ge", empirical_threshold(cal, alpha)), "weighted": ("gt", weighted_threshold(cal, w, alpha))}.items():
                        alarm = st > t if op == "gt" else st >= t
                        shift.append(dict(calib=calib, seed=seed, alpha=alpha, category=held, method=meth, fa=float(alarm[tm & (yt == 0)].mean()), recall=float(alarm[tm & (yt == 1)].mean()),
                                          n_cal=int(cal_mask.sum()), n_test_neg=int((tm & (yt == 0)).sum())))
    return pd.DataFrame(rows), pd.DataFrame(shift)


def main() -> None:
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    flags, cnt = duplicate_flags()
    clean_ids = set(flags.event_id[~flags.flag])
    hash_ids = set(flags.event_id[~(flags.hash_train | flags.hash_test)])  # de-duplicated by recording group only: no validation event whose raw array is identical to a train or test event
    scorer_by_seed = {}
    for seed in SEEDS:
        scorer, _ = fit("rf15", seed, tr, va_trig)
        scorer_by_seed[seed] = (score_all(scorer, va), score_all(scorer, te))
    R, S = runs(va, te, clean_ids, hash_ids, scorer_by_seed)
    R.to_csv(C.TABLES / "s3_conformal.csv", index=False)
    S.to_csv(C.TABLES / "s3_conformal_shift.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes=""):
        ent.append(dict(name=f"n20c.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    for grp, d in cnt.items():
        for k, v in d.items():
            add(f"dup.val.{grp}.{k}", v, "events", notes={"n": "validation events in the group", "hash_train": "identical raw array to a training event", "hash_test": "identical raw array to a test event (supplied split)",
                                                         "nd_train": "window near-duplicate of a training window (triggered events)", "nd_test": "window near-duplicate of a test window (triggered events)",
                                                         "nd_new": "near-duplicate of a train or test window that is not an exact-hash match", "flagged": "any of the four"}[k])
    yv = va.y.to_numpy()
    cleanmask = va.event_id.isin(clean_ids).to_numpy()
    add("calib.n_negatives_hashgroup", int(((yv == 0) & va.event_id.isin(hash_ids).to_numpy()).sum()), "events", notes="validation non-crash events left after removing every event whose raw array (recording group) also occurs in a training or test event")
    add("calib.n_negatives_dirty", int((yv == 0).sum()), "events", notes="validation non-crash events (the original calibration pool)")
    add("calib.n_negatives_clean", int(((yv == 0) & cleanmask).sum()), "events", notes="after removing every exact-hash or near-duplicate match to a training or test event")
    yt = te.y.to_numpy()
    n_neg_t = int((yt == 0).sum())
    add("test.n_negatives", n_neg_t, "events", notes="non-crash events of the de-duplicated test split")
    for (calib, alpha, size, meth), g in R.groupby(["calib", "alpha", "size", "method"]):
        tag = f"{calib}.a{int(round(alpha * 100))}.n{size}.{meth}"
        fa = g.fa.to_numpy()
        m = B.ci(fa, np.mean)
        se = float(np.sqrt(alpha * (1 - alpha) / n_neg_t))
        add(f"{tag}.fa_mean", round(m[0], 5), "fraction", notes="mean test false-alarm rate over (seed, calibration draw) pairs")
        add(f"{tag}.fa_mean_lo", round(m[1], 5), "fraction", notes="95% bootstrap interval for the mean")
        add(f"{tag}.fa_mean_hi", round(m[2], 5), "fraction", notes="95% bootstrap interval for the mean")
        add(f"{tag}.share_above_alpha", round(float((fa > alpha).mean()), 4), "fraction", notes="share of (seed, draw) pairs whose test false-alarm rate is above alpha")
        add(f"{tag}.recall_mean", round(float(g.recall.mean()), 5), "fraction", notes="mean test system recall")
        add(f"{tag}.holds_1se", int(m[2] <= alpha + se), "bool", notes="decision rule: upper end of the interval at or below alpha plus one binomial standard error of the test negatives")
        add(f"{tag}.holds_196se", int(m[2] <= alpha + 1.96 * se), "bool", notes="same with 1.96 standard errors")
        add(f"{tag}.n_pairs", int(len(g)), "count", notes="(seed, draw) pairs")
    for (calib, alpha), g in R.groupby(["calib", "alpha"]):
        add(f"{calib}.a{int(round(alpha * 100))}.test_se", round(float(np.sqrt(alpha * (1 - alpha) / n_neg_t)), 5), "fraction", notes="binomial standard error of the test false-alarm rate")
    for (calib, alpha, cat, meth), g in S.groupby(["calib", "alpha", "category", "method"]):
        tag = f"shift.{calib}.a{int(round(alpha * 100))}.{cat}.{meth}"
        add(f"{tag}.fa_mean", round(float(g.fa.mean()), 5), "fraction", notes="mean over seeds; calibration on the other categories")
        add(f"{tag}.recall_mean", round(float(g.recall.mean()), 5), "fraction", notes="mean over seeds")
        add(f"{tag}.n_test_neg", int(g.n_test_neg.iloc[0]), "events", notes="non-crash test events of the held-out category")
    record_many(ent, purge_prefixes=("n20c.",))
    pd.set_option("display.width", 220)
    print(cnt)
    print(R[R["size"].isin([1000, "all"])].groupby(["calib", "alpha", "size", "method"]).agg(fa=("fa", "mean"), above=("fa", lambda x: 0), recall=("recall", "mean")).round(4).to_string())


if __name__ == "__main__":
    main()
