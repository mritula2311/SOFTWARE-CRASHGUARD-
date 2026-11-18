"""S9 (N24): grouped CV+ conformal intervals for the delta-V estimate of fill + ridge (plan, decision rule and class rule: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S9, written before this was run).

Outer: repeated grouped 5-fold cross-validation over make and model (as split R). Inner: grouped 5-fold CV+ inside each outer training set, residual scale = relative error.
MEASURED_SOFTWARE on 176 NHTSA tests; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes; fill + ridge was named primary after earlier results were seen.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard import severity as S
from crashguard import severity_study as SS

REPEATS = 5
INNER = 5
NOMINALS = (0.8, 0.9)
SRC = "results/tables/s9_conformal_dv.csv"


def cvplus(f_test: np.ndarray, fold_of_cal: np.ndarray, resid_rel: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """CV+ interval for each test point.

    ``f_test`` (n_inner_folds, n_test): prediction of the model without inner fold k at each test point; ``fold_of_cal`` (n_cal): inner fold of each calibration test;
    ``resid_rel`` (n_cal): out-of-fold relative residual. Returns (lower, upper); lower is clipped at 0, upper may be inf.
    """
    n = len(resid_rel)
    f = f_test[fold_of_cal]  # (n_cal, n_test)
    lo_c = np.sort(f * (1.0 - resid_rel[:, None]), axis=0)
    up_c = np.sort(f * (1.0 + resid_rel[:, None]), axis=0)
    k_lo = math.floor(alpha * (n + 1))
    k_up = math.ceil((1.0 - alpha) * (n + 1))
    lower = lo_c[k_lo - 1] if k_lo >= 1 else np.full(f.shape[1], -np.inf)
    upper = up_c[k_up - 1] if k_up <= n else np.full(f.shape[1], np.inf)
    return np.maximum(lower, 0.0), upper


def sev_class(dv: np.ndarray, asi: np.ndarray) -> np.ndarray:
    return np.array([S.classify(float(d), float(a), False) for d, a in zip(dv, asi)])


def decision_class(dv_pt: np.ndarray, dv_lo: np.ndarray, asi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Class rule: k = class of the point estimate, k_lo = class of the lower bound; report k if equal, else the class below k, plus a flag. Final class includes the ASI class."""
    k = np.array([sum(d >= lim for lim in S.DEFAULT.dv_limits_kmh) for d in dv_pt])
    k_lo = np.array([sum(d >= lim for lim in S.DEFAULT.dv_limits_kmh) for d in dv_lo])
    flag = k_lo < k
    rep = np.where(flag, np.maximum(k - 1, 0), k)
    c_asi = np.array([sum(a > lim for lim in S.DEFAULT.asi_limits) for a in asi])
    return np.maximum(rep, c_asi), flag


def run(cells: dict, meta: pd.DataFrame, asi_tab: dict) -> dict:
    n = len(meta)
    ref = meta.ref.to_numpy()
    groups = meta.group_mm.to_numpy()
    ug = sorted(set(groups.tolist()))
    out = {rg: {nom: dict(lo=np.full((REPEATS, n), np.nan), hi=np.full((REPEATS, n), np.nan)) for nom in NOMINALS} for rg in SP.RANGES}
    pt = {rg: np.full((REPEATS, n), np.nan) for rg in SP.RANGES}
    for rep in range(REPEATS):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % SP.N_FOLDS for k, j in enumerate(order)}
        outer = np.array([fold_of[g] for g in groups])
        for f in range(SP.N_FOLDS):
            te, tr = outer == f, outer != f
            combo = SP.choose_combo(cells, meta, tr)
            tr_groups = sorted(set(groups[tr].tolist()))
            rng2 = np.random.default_rng(C.SEED + 1000 + rep * 10 + f)
            inner_of = {g: k % INNER for k, g in enumerate(rng2.permutation(tr_groups))}
            inner = np.array([inner_of.get(g, -1) for g in groups])
            for rg in SP.RANGES:
                est_full, _ = SP.estimates(cells, meta, tr, te, rg, combo, "group")
                pt[rg][rep, te] = est_full["M+"]
                cal_idx = np.flatnonzero(tr)
                f_test = np.zeros((INNER, int(te.sum())))
                oof = np.zeros(n)
                for k in range(INNER):
                    in_k = inner == k
                    tr_k = tr & ~in_k
                    combo_k = SP.choose_combo(cells, meta, tr_k)
                    want = te | in_k  # rows to predict: the outer test rows and the calibration rows of fold k
                    est_k, _ = SP.estimates(cells, meta, tr_k, want, rg, combo_k, "group")
                    pred = np.full(n, np.nan)
                    pred[want] = est_k["M+"]
                    f_test[k] = pred[te]
                    oof[in_k] = pred[in_k]
                resid = np.abs(ref[cal_idx] - oof[cal_idx]) / np.maximum(oof[cal_idx], 1e-6)
                for nom in NOMINALS:
                    lo, hi = cvplus(f_test, inner[cal_idx], resid, 1.0 - nom)
                    out[rg][nom]["lo"][rep, te] = lo
                    out[rg][nom]["hi"][rep, te] = hi
    return dict(out=out, pt=pt)


def main() -> None:
    from crashguard.results import record_many

    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    cells = SP.build_cells(tests)
    tab = pd.read_csv(C.TABLES / "n14_per_test.csv")
    asi_tab = {}
    for rg in SP.RANGES:
        t = tab[tab.range_g == rg].reset_index(drop=True)  # same order as the tests (checked: reference delta-V and test number agree row by row)
        assert np.allclose(t.ref.to_numpy(), meta.ref.to_numpy()) and (t.test_no.to_numpy() == meta.test_no.to_numpy()).all()
        asi_tab[rg] = t.m_asi.to_numpy(float)
    ref = meta.ref.to_numpy()
    ref_asi = tab[tab.range_g == 16.0].reset_index(drop=True).ref_asi.to_numpy(float)
    ref_cls = sev_class(ref, ref_asi)
    groups = meta.group_mm.to_numpy()
    res = run(cells, meta, asi_tab)
    ent: list[dict] = []
    rows = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"n24.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("n_tests", len(meta), "tests", "NHTSA tests; make and model groups: " + str(len(set(groups.tolist()))))
    add("repeats", REPEATS, "repeats", "outer repeats of the grouped 5-fold cross-validation")
    for rg in SP.RANGES:
        pt = res["pt"][rg]
        asi = asi_tab[rg]
        for nom in NOMINALS:
            lo, hi = res["out"][rg][nom]["lo"], res["out"][rg][nom]["hi"]
            tag = f"r{rg:g}.nom{int(nom * 100)}"
            cov = ((ref[None, :] >= lo) & (ref[None, :] <= hi)).astype(float)  # (rep, n)
            p, a, b = B.ci_grouped(cov.T, groups, lambda x: float(x.mean()))
            add(f"{tag}.coverage", round(p, 4), "fraction", "share of tests whose reference delta-V lies in the interval, mean over repeats; interval: grouped bootstrap")
            add(f"{tag}.coverage_lo", round(a, 4), "fraction", "95% grouped bootstrap interval")
            add(f"{tag}.coverage_hi", round(b, 4), "fraction", "95% grouped bootstrap interval")
            add(f"{tag}.nominal_inside_interval", int(a <= nom <= b), "flag", "1 = the nominal coverage lies inside the 95% interval of the empirical coverage")
            width_rel = np.where(np.isfinite(hi), (hi - lo) / np.maximum(pt, 1e-6), np.inf)
            width_abs = np.where(np.isfinite(hi), hi - lo, np.inf)
            for nm, w in (("width_rel_median", width_rel), ("width_kmh_median", width_abs)):
                p2, a2, b2 = B.ci_grouped(w.T, groups, lambda x: float(np.median(x)))
                add(f"{tag}.{nm}", round(p2, 3), "ratio" if "rel" in nm else "km/h", "median over tests (mean over repeats of the per-repeat median); infinite intervals count as infinite")
                add(f"{tag}.{nm}_lo", round(a2, 3), "ratio" if "rel" in nm else "km/h", "95% grouped bootstrap interval")
                add(f"{tag}.{nm}_hi", round(b2, 3), "ratio" if "rel" in nm else "km/h", "95% grouped bootstrap interval")
            add(f"{tag}.share_infinite_upper", round(float(np.isinf(hi).mean()), 4), "fraction", "intervals with no finite upper bound")
            # classes
            cls_pt = np.zeros_like(pt, dtype=int)
            cls_dec = np.zeros_like(pt, dtype=int)
            flagged = np.zeros_like(pt, dtype=bool)
            in_one = np.zeros_like(pt, dtype=bool)
            for r in range(REPEATS):
                cls_pt[r] = sev_class(pt[r], asi)
                cls_dec[r], flagged[r] = decision_class(pt[r], lo[r], asi)
                c_lo = sev_class(lo[r], asi)
                c_hi = sev_class(np.where(np.isfinite(hi[r]), hi[r], 1e6), asi)
                in_one[r] = c_lo == c_hi
            under_pt, under_dec = (cls_pt < ref_cls[None, :]).astype(float), (cls_dec < ref_cls[None, :]).astype(float)
            over_pt, over_dec = (cls_pt > ref_cls[None, :]).astype(float), (cls_dec > ref_cls[None, :]).astype(float)
            agree_pt, agree_dec = (cls_pt == ref_cls[None, :]).astype(float), (cls_dec == ref_cls[None, :]).astype(float)
            mean = lambda x: float(x.mean())  # noqa: E731
            for nm, arr in (("in_one_class_share", in_one.astype(float)), ("flagged_share", flagged.astype(float)), ("agree_point", agree_pt), ("agree_decision", agree_dec),
                            ("under_point", under_pt), ("under_decision", under_dec), ("over_point", over_pt), ("over_decision", over_dec)):
                p3, a3, b3 = B.ci_grouped(arr.T, groups, mean)
                add(f"{tag}.{nm}", round(p3, 4), "fraction", "mean over tests and repeats; grouped bootstrap interval")
                add(f"{tag}.{nm}_lo", round(a3, 4), "fraction", "95% grouped bootstrap interval")
                add(f"{tag}.{nm}_hi", round(b3, 4), "fraction", "95% grouped bootstrap interval")
            d = B.paired_diff_grouped(under_dec.T, under_pt.T, groups, mean)  # point minus decision: positive = decision rule under-estimates less
            add(f"{tag}.under_drop", round(d[0], 4), "fraction", "under-estimation share of the point class minus that of the decision-rule class (positive = fewer under-estimates), paired, grouped bootstrap")
            add(f"{tag}.under_drop_lo", round(d[1], 4), "fraction", "95% grouped bootstrap interval")
            add(f"{tag}.under_drop_hi", round(d[2], 4), "fraction", "95% grouped bootstrap interval")
            cov_ok = bool(a <= nom <= b)
            under_ok = bool(d[1] > 0)
            add(f"{tag}.improvement", int(cov_ok and under_ok), "flag", "decision rule fixed in advance: coverage nominal inside its interval AND the under-estimation drop interval above zero")
            rows.append(dict(range_g=rg, nominal=nom, coverage=p, cov_lo=a, cov_hi=b, width_rel_med=float(np.median(np.where(np.isfinite(width_rel), width_rel, np.nan)[np.isfinite(width_rel)])) if np.isfinite(width_rel).any() else np.nan,
                             in_one=float(in_one.mean()), flagged=float(flagged.mean()), agree_pt=float(agree_pt.mean()), agree_dec=float(agree_dec.mean()), under_pt=float(under_pt.mean()), under_dec=float(under_dec.mean()),
                             under_drop=d[0], under_drop_lo=d[1], under_drop_hi=d[2], improvement=int(cov_ok and under_ok)))
    pd.DataFrame(rows).to_csv(C.TABLES / "s9_conformal_dv.csv", index=False)
    record_many(ent, purge_prefixes=("n24.",))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string())


if __name__ == "__main__":
    main()
