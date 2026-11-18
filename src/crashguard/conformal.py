"""X4 (N20): split-conformal control of the false-alarm rate (docs/02_preregistration/EXPERIMENTS_EXTRA.md, written before this was run).

Calibration set: the non-crash events of the validation split (system level: events the trigger discards have score -1 and are non-alarms). For a target alpha the conformal
threshold is the k-th smallest calibration score with k = ceil((n + 1)(1 - alpha)); an event alarms if its score is ABOVE that value. If a new non-crash event is exchangeable with
the calibration events, P(false alarm) <= alpha (marginal over calibration sets). The baseline is the existing validation threshold (smallest threshold whose validation false-alarm
rate is at most alpha).

Interpretation fixed before the run, for the decision rule: "the interval" is a 95% bootstrap interval FOR THE MEAN false-alarm rate over (seed, draw) pairs; the spread of single draws
(2.5th to 97.5th percentile) is reported separately and is expected to exceed alpha in part of the draws.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import fit, frames_full, score_all

ALPHAS = (0.01, 0.05)
SIZES = (200, 500, 1000, 2000, None)  # None = the whole validation negative set
DRAWS = 200
CATS = ("Light", "Medium", "Heavy", "Unknown")
SEEDS = (C.SEED,) + C.SEEDS


def conformal_threshold(neg_scores: np.ndarray, alpha: float) -> float:
    """k-th smallest calibration score, k = ceil((n + 1)(1 - alpha)); an event alarms if its score is strictly above this value. inf if k > n (no alarms)."""
    s = np.sort(np.asarray(neg_scores, float))
    n = len(s)
    k = math.ceil((n + 1) * (1.0 - alpha))
    return float("inf") if k > n else float(s[k - 1])


def empirical_threshold(neg_scores: np.ndarray, alpha: float) -> float:
    """Validation-chosen threshold of the existing study: alarm if score >= this. The smallest threshold whose calibration false-alarm rate is at most alpha."""
    s = np.sort(np.asarray(neg_scores, float))[::-1]
    allowed = int(math.floor(alpha * len(s)))
    return float(np.nextafter(s[allowed], np.inf)) if allowed < len(s) else -np.inf


def rates(scores: np.ndarray, y: np.ndarray, alarm: np.ndarray) -> tuple[float, float]:
    return float(alarm[y == 0].mean()), float(alarm[y == 1].mean())  # false-alarm rate, recall


def main() -> None:
    from crashguard.results import record_many

    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    yv, yt = va.y.to_numpy(), te.y.to_numpy()
    ent: list[dict] = []
    src = "results/tables/x4_conformal.csv"

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes=""):
        ent.append(dict(name=f"x4.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    rng = np.random.default_rng(C.SEED)
    rows = []
    shift_rows = []
    for seed in SEEDS:
        scorer, _m = fit("rf15", seed, tr, va_trig)
        sv, st = score_all(scorer, va), score_all(scorer, te)
        neg_v, _neg_t = sv[yv == 0], st[yt == 0]
        sizes_v = va.vehiclesize.to_numpy()
        sizes_t = te.vehiclesize.to_numpy()
        for alpha in ALPHAS:
            for size in SIZES:
                n_draw = 1 if size is None else DRAWS
                for _d in range(n_draw):
                    cal = neg_v if size is None else rng.choice(neg_v, size=min(size, len(neg_v)), replace=False)
                    thr_c = conformal_threshold(cal, alpha)
                    thr_e = empirical_threshold(cal, alpha)
                    for meth, alarm in (("conformal", st > thr_c), ("validation", st >= thr_e)):
                        fa, rec = rates(st, yt, alarm)
                        rows.append(dict(seed=seed, alpha=alpha, size="all" if size is None else size, method=meth, fa=fa, recall=rec, n_cal=len(cal)))
            # (b) exchangeability broken on purpose: calibrate on other size categories, test on one (and the reverse)
            for held in CATS:
                for direction in ("leave_one_category_out", "single_category_calibration"):
                    if direction == "leave_one_category_out":
                        cal_mask = (yv == 0) & (sizes_v != held)
                        test_mask = sizes_t == held
                    else:
                        cal_mask = (yv == 0) & (sizes_v == held)
                        test_mask = sizes_t != held
                    if cal_mask.sum() < 50 or (test_mask & (yt == 0)).sum() < 50:
                        continue
                    for alpha in ALPHAS:
                        thr_c = conformal_threshold(sv[cal_mask], alpha)
                        thr_e = empirical_threshold(sv[cal_mask], alpha)
                        for meth, alarm in (("conformal", st > thr_c), ("validation", st >= thr_e)):
                            fa, rec = rates(st[test_mask], yt[test_mask], alarm[test_mask])
                            shift_rows.append(dict(seed=seed, alpha=alpha, direction=direction, category=held, method=meth, fa=fa, recall=rec, n_cal=int(cal_mask.sum()),
                                                   n_test_neg=int((test_mask & (yt == 0)).sum())))
    R = pd.DataFrame(rows)
    S = pd.DataFrame(shift_rows)
    R.to_csv(C.TABLES / "x4_conformal.csv", index=False)
    S.to_csv(C.TABLES / "x4_conformal_shift.csv", index=False)
    add("n_calibration_negatives", int((yv == 0).sum()), "events", notes="non-crash validation events, including those the trigger discards")
    add("n_test_negatives", int((yt == 0).sum()), "events")
    for (alpha, size, meth), g in R.groupby(["alpha", "size", "method"]):
        tag = f"a{int(round(alpha * 100))}.n{size}.{meth}"
        fa = g.fa.to_numpy()
        m = B.ci(fa, np.mean)
        add(f"{tag}.fa_mean", round(m[0], 5), "fraction", notes="mean over seeds and calibration draws")
        add(f"{tag}.fa_mean_lo", round(m[1], 5), "fraction", notes="95% bootstrap interval for the MEAN over (seed, draw) pairs")
        add(f"{tag}.fa_mean_hi", round(m[2], 5), "fraction")
        add(f"{tag}.fa_p025", round(float(np.quantile(fa, 0.025)), 5), "fraction", notes="spread of single draws")
        add(f"{tag}.fa_p975", round(float(np.quantile(fa, 0.975)), 5), "fraction")
        add(f"{tag}.share_exceeding_alpha", round(float((fa > alpha).mean()), 4), "fraction", notes="share of (seed, draw) pairs whose test false-alarm rate is above alpha")
        add(f"{tag}.recall_mean", round(float(g.recall.mean()), 5), "fraction")
        add(f"{tag}.n_pairs", int(len(g)), "count")
    # paired recall difference conformal minus validation at the same calibration set (per row order within the group)
    for (alpha, size), g in R.groupby(["alpha", "size"]):
        c = g[g.method == "conformal"].recall.to_numpy()
        v = g[g.method == "validation"].recall.to_numpy()
        d = B.paired_diff(v, c, np.mean)
        tag = f"a{int(round(alpha * 100))}.n{size}"
        add(f"{tag}.recall_diff_conformal_minus_validation", round(d[0], 5), "fraction")
        add(f"{tag}.recall_diff_conformal_minus_validation_lo", round(d[1], 5), "fraction")
        add(f"{tag}.recall_diff_conformal_minus_validation_hi", round(d[2], 5), "fraction")
    for (alpha, direction, cat, meth), g in S.groupby(["alpha", "direction", "category", "method"]):
        tag = f"shift.a{int(round(alpha * 100))}.{direction}.{cat}.{meth}"
        add(f"{tag}.fa_mean", round(float(g.fa.mean()), 5), "fraction", notes="mean over seeds; calibration on the other categories (leave_one_category_out) or on this one only (single_category_calibration)")
        add(f"{tag}.fa_std", round(float(g.fa.std(ddof=1)), 5), "fraction")
        add(f"{tag}.recall_mean", round(float(g.recall.mean()), 5), "fraction")
        add(f"{tag}.n_test_neg", int(g.n_test_neg.iloc[0]), "events")
        add(f"{tag}.n_cal", int(g.n_cal.iloc[0]), "events")
    record_many(ent, purge_prefixes=("x4.",))
    pd.set_option("display.width", 200)
    R["over"] = R.fa > R.alpha
    print(R.groupby(["alpha", "size", "method"]).agg(fa=("fa", "mean"), exceed=("over", "mean"), recall=("recall", "mean")).round(4).to_string())
    print(S.groupby(["alpha", "direction", "category", "method"]).fa.mean().round(4).to_string())


if __name__ == "__main__":
    main()
