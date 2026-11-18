"""X6 (docs/02_preregistration/PREREGISTRATION_V3.md): lower-bound-anchored delta-V estimator against fill + ridge, the tail-aware median model, the triangle fit and plain. MEASURED_SOFTWARE on 176 NHTSA tests.

dv_anchored = dv_plain x exp(max(0, g(x))) (see ``x_common``): it cannot fall below the plain (lower-bound) estimate. Out-of-fold estimates on splits R (10 repeats), G, A, O come from ``x_common.oof``.
Primary: +-16 g, 100 Hz, split R. Intervals resample make/model groups. The 'under-estimation share' is the share of tests whose estimate is below the reference by more than 10%.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard.jp_common import Entries
from crashguard.x_common import oof

RANGES = (16.0, 32.0, 64.0)
SPLITS = ("R", "G", "A", "O")
METHODS = ("B", "M+", "QR", "TRI", "GBR", "ANC", "ANCR")
NAMES = {"B": "plain", "M+": "fill + ridge", "QR": "tail-aware", "TRI": "triangle fit", "GBR": "gradient boosting on the log correction of the fill (not anchored; EXPLORATORY)", "ANC": "anchored (boosting)", "ANCR": "anchored (ridge, exploratory)"}
SRC = "results/tables/x6_anchored.csv"


def p90(a: np.ndarray) -> float:
    return float(np.quantile(a, 0.9, axis=-1 if a.ndim == 1 else 0).mean()) if a.ndim > 1 else float(np.quantile(a, 0.9))


def main() -> None:
    OO = oof()
    ref, gmm = OO["ref"], OO["gmm"]
    n = OO["n"]
    held = OO["held"]
    E = Entries("x.x6", SRC)
    rows = []
    paired_cache: dict = {}
    for sp in SPLITS:
        mask = np.ones(n, bool) if sp == "R" else held[sp]
        groups = gmm[mask]
        D = list(B._gidx(B.group_members(groups), B.N_BOOT, B.SEED))
        for rg in RANGES:
            est = {m: (OO["R"][rg][m][:, mask] if sp == "R" else OO[sp][rg][m]) for m in METHODS}
            r = ref[mask]
            err = {m: np.abs(100.0 * (est[m] - r) / r) for m in METHODS}
            under = {m: (est[m] < 0.9 * r).astype(float) for m in METHODS}

            def stat(a, fn):
                # a: (REP, n) for R or (n,) otherwise; fn over tests
                return (lambda i: float(np.mean([fn(a[k][i]) for k in range(a.shape[0])]))) if a.ndim == 2 else (lambda i: float(fn(a[i])))

            for m in METHODS:
                for nm, fn, a in (("median", np.median, err[m]), ("p90", lambda x: np.quantile(x, 0.9), err[m]), ("w10", lambda x: np.mean(x <= 10.0), err[m]), ("under", np.mean, under[m])):
                    f = stat(a, fn)
                    pt = float(f(np.arange(len(r))))
                    d = np.array([f(i) for i in D])
                    lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
                    E.ci(f"{sp}.r{rg:g}.{m}.{nm}", (pt, lo, hi), "fraction" if nm in ("w10", "under") else "percent", d=4)
                    rows.append(dict(split=sp, range_g=rg, method=m, metric=nm, value=pt, lo=lo, hi=hi))
            for ref_m, new_m in (("M+", "ANC"), ("QR", "ANC"), ("TRI", "ANC"), ("B", "ANC"), ("M+", "ANCR"), ("GBR", "ANC")):
                for nm, fn in (("p90", lambda x: np.quantile(x, 0.9)), ("median", np.median), ("w10", lambda x: np.mean(x <= 10.0))):
                    fa, fb = stat(err[ref_m], fn), stat(err[new_m], fn)
                    pt = fa(np.arange(len(r))) - fb(np.arange(len(r)))
                    d = np.array([fa(i) - fb(i) for i in D])
                    lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
                    sign = "reference minus new; positive = the anchored estimator has the lower error" if nm != "w10" else "reference minus new in the share within 10%; negative = the anchored estimator has the larger share"
                    E.ci(f"{sp}.r{rg:g}.paired.{ref_m}_minus_{new_m}.{nm}", (pt, lo, hi), "percent points" if nm != "w10" else "fraction", sign, d=4)
                    paired_cache[(sp, rg, ref_m, new_m, nm)] = (pt, lo, hi, d)
            fu_a, fu_b = stat(under["QR"], np.mean), stat(under["ANC"], np.mean)
            pt = fu_b(np.arange(len(r))) - fu_a(np.arange(len(r)))
            d = np.array([fu_b(i) - fu_a(i) for i in D])
            E.ci(f"{sp}.r{rg:g}.paired.under_ANC_minus_QR", (pt, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "fraction", "anchored minus tail-aware under-estimation share; negative = anchored under-estimates less", d=4)
            paired_cache[(sp, rg, "under")] = (pt, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975)), d)
    # ---- H-X6
    rg = 16.0
    pt, lo, hi, d = paired_cache[("R", rg, "M+", "ANC", "p90")]
    p_raw = float(max(np.mean(d <= 0.0), 1.0 / (len(d) + 1)))
    other = {sp: paired_cache[(sp, rg, "M+", "ANC", "p90")] for sp in ("G", "A", "O")}
    other_ok = [sp for sp, v in other.items() if v[1] > 0]
    u_pt, u_lo, u_hi, _ = paired_cache[("R", rg, "under")]
    crit = pt >= 5.0 and lo > 0 and len(other_ok) >= 1 and u_pt < 0
    E.add("hX6.p90_gain_R", round(pt, 4), "percent points", "p90(fill + ridge) minus p90(anchored), +-16 g, split R")
    E.add("hX6.p90_gain_R_lo", round(lo, 4), "percent points")
    E.add("hX6.p90_gain_R_hi", round(hi, 4), "percent points")
    E.add("hX6.p_raw", round(p_raw, 4), "probability", "share of grouped resamples with gain at or below 0; floor 0.001")
    E.add("hX6.other_splits_with_interval_above_zero", ",".join(other_ok) if other_ok else "none", "text", "among G, A, O")
    E.add("hX6.n_other_splits_with_interval_above_zero", len(other_ok), "splits")
    E.add("hX6.under_difference_point", round(u_pt, 4), "fraction", "anchored minus tail-aware under-estimation share, split R")
    E.add("hX6.criterion_met", int(crit), "flag", "gain at least 5 points with the interval above zero on R, interval above zero on at least one of G, A, O, and a lower under-estimation share than the tail-aware estimator (point)")
    # ---- lower bound violations (reference below the plain estimate)
    for rgv in RANGES:
        plain = OO["plain16"][rgv]
        viol = np.flatnonzero(plain > ref)
        E.add(f"lowerbound.r{rgv:g}.n_violations", int(len(viol)), "tests", "plain estimate above the reference (the lower-bound statement fails)")
        for k, i in enumerate(viol):
            anc = float(np.mean(OO["R"][rgv]["ANC"][:, i]))
            E.add(f"lowerbound.r{rgv:g}.case{k + 1}.test_no", int(OO["test_no"][i]), "test")
            E.add(f"lowerbound.r{rgv:g}.case{k + 1}.plain_over_ref", round(float(plain[i] / ref[i]), 4), "ratio")
            E.add(f"lowerbound.r{rgv:g}.case{k + 1}.anchored_over_ref", round(anc / ref[i], 4), "ratio", "mean over the repeats of split R; the anchored estimate is never below the plain one, so it is at least as far above the reference")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "x6_anchored.csv", index=False)
    pd.set_option("display.width", 250)
    d_ = pd.DataFrame(rows)
    print(d_[(d_.range_g == 16.0) & d_.metric.isin(["median", "p90", "w10", "under"])].pivot_table(index=["split", "method"], columns="metric", values="value").round(3).to_string())
    print("H-X6", round(pt, 3), round(lo, 3), round(hi, 3), "p", p_raw, "other ok", other_ok, "under diff", round(u_pt, 4), round(u_lo, 4), round(u_hi, 4), "crit", crit)


if __name__ == "__main__":
    main()
