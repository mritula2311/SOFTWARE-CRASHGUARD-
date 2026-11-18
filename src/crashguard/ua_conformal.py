"""UA-SCT B1 and B2: severity class from delta-V on the NHTSA tests and conformal intervals over the ordered classes (plan, scores and reading rules: docs/02_preregistration/PREREGISTRATION.md, sections 2 and 3, committed before this was run).

Point estimate: fill + ridge at 100 Hz (the N14 primary, named after earlier results were seen) fitted on tuning groups only. Calibration groups are disjoint from tuning and test groups
(outer: repeated grouped 5-fold cross-validation over make and model, identical-recording tests merged into one group; inside each outer training set 60% of the groups tune the estimator and 40% calibrate).
Scores: two-sided |c_true - c_hat|, one-sided max(0, c_true - c_hat). Split-conformal quantile = the ceil((n + 1)(1 - alpha))-th smallest score. Pooled and class-conditional (per predicted class, pooled
quantile where a class has fewer than 10 calibration tests). MEASURED_SOFTWARE on 176 NHTSA tests; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard import severity as S
from crashguard import severity_study as SS

REPEATS = 5
ALPHAS = (0.10, 0.05)
MIN_CLASS_N = 10
CAL_SHARE = 0.4
SRC = "results/tables/ua_conformal.csv"


def merged_groups(tests: list[dict], meta: pd.DataFrame) -> tuple[np.ndarray, int]:
    """Make-and-model groups, merged (union-find) when two tests have identical recordings, so that a duplicated recording cannot sit on both sides of a split."""
    g = meta.group_mm.to_numpy()
    parent = {x: x for x in set(g.tolist())}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seen: dict[str, str] = {}
    n_dup = 0
    for t, gg in zip(tests, g):
        h = hashlib.md5(np.asarray(t["sig"]["acc"]).tobytes()).hexdigest()
        if h in seen:
            n_dup += 1
            parent[find(gg)] = find(seen[h])
        else:
            seen[h] = gg
    return np.array([find(x) for x in g]), n_dup


def split_quantile(scores: np.ndarray, alpha: float) -> float:
    n = len(scores)
    k = math.ceil((n + 1) * (1 - alpha))
    return float(np.sort(scores)[k - 1]) if 1 <= k <= n else float("inf")


def intervals(c_hat_cal: np.ndarray, c_true_cal: np.ndarray, c_hat_te: np.ndarray, alpha: float, cond: bool) -> dict:
    """Two-sided interval and upper end for the test rows. ``cond``: one quantile per predicted class (pooled where a class has fewer than MIN_CLASS_N calibration tests)."""
    s2 = np.abs(c_true_cal - c_hat_cal).astype(float)
    s1 = np.maximum(0, c_true_cal - c_hat_cal).astype(float)
    q2_all, q1_all = split_quantile(s2, alpha), split_quantile(s1, alpha)
    q2, q1 = np.full(len(c_hat_te), q2_all), np.full(len(c_hat_te), q1_all)
    fallback = 0
    if cond:
        for k in range(4):
            m = c_hat_cal == k
            use = m.sum() >= MIN_CLASS_N
            tm = c_hat_te == k
            if tm.any():
                if use:
                    q2[tm], q1[tm] = split_quantile(s2[m], alpha), split_quantile(s1[m], alpha)
                else:
                    fallback += int(tm.sum())
    lo = np.maximum(0, c_hat_te - np.minimum(q2, 3)).astype(int)
    hi = np.minimum(3, c_hat_te + np.minimum(q2, 3)).astype(int)
    up = np.minimum(3, c_hat_te + np.minimum(q1, 3)).astype(int)
    return dict(lo=lo, hi=hi, up=up, fallback=fallback)


def run(cells, meta, tests, grp, asi_tab, ref_cls):
    n = len(meta)
    ug = sorted(set(grp.tolist()))
    keys = [(rg, a, cond) for rg in SP.RANGES for a in ALPHAS for cond in (False, True)]
    res = {k: {m: np.full((REPEATS, n), -1, int) for m in ("c_hat", "lo", "hi", "up")} for k in keys}
    fallback = {k: 0 for k in keys}
    ncal = {rg: np.zeros((REPEATS, 4)) for rg in SP.RANGES}
    for rep in range(REPEATS):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % SP.N_FOLDS for k, j in enumerate(order)}
        outer = np.array([fold_of[g] for g in grp])
        for f in range(SP.N_FOLDS):
            te, trn = outer == f, outer != f
            tr_groups = sorted(set(grp[trn].tolist()))
            rng2 = np.random.default_rng(C.SEED + 500 + rep * 10 + f)
            perm = rng2.permutation(len(tr_groups))
            n_cal = max(1, int(round(CAL_SHARE * len(tr_groups))))
            cal_groups = {tr_groups[i] for i in perm[:n_cal]}
            cal = np.array([g in cal_groups for g in grp]) & trn
            tune = trn & ~cal
            combo = SP.choose_combo(cells, meta, tune)
            want = cal | te
            for rg in SP.RANGES:
                est, _ = SP.estimates(cells, meta, tune, want, rg, combo, "group")
                dv = np.full(n, np.nan)
                dv[want] = est["M+"]
                c_hat = np.array([S.classify(float(d), float(a), False) if np.isfinite(d) else -1 for d, a in zip(dv, asi_tab[rg])])
                ncal[rg][rep] += np.array([int(((c_hat == j) & cal).sum()) for j in range(4)]) / SP.N_FOLDS  # mean over the 5 folds
                for a in ALPHAS:
                    for cond in (False, True):
                        r = intervals(c_hat[cal], ref_cls[cal], c_hat[te], a, cond)
                        key = (rg, a, cond)
                        res[key]["c_hat"][rep, te] = c_hat[te]
                        res[key]["lo"][rep, te], res[key]["hi"][rep, te], res[key]["up"][rep, te] = r["lo"], r["hi"], r["up"]
                        fallback[key] += r["fallback"]
    return res, fallback, ncal


def b1_plain_200hz(tests, meta, ref_cls, ref, ref_asi) -> list[dict]:
    """Plain (unrestored) estimate at 100 and 200 Hz for the three ranges: median error, class agreement, under- and over-estimation (descriptive)."""
    out = []
    groups = meta.group_mm.to_numpy()
    for fs in (100.0, 200.0):
        for rg in SP.RANGES:
            dv, asi = np.zeros(len(tests)), np.zeros(len(tests))
            for i, t in enumerate(tests):
                r = SS.estimate(t["sig"], range_g=rg, fs=fs)
                dv[i], asi[i] = r["dv_res_kmh"], r["asi"]
            cls = np.array([S.classify(float(d), float(a), False) for d, a in zip(dv, asi)])
            err = np.abs(100 * (dv - ref) / ref)
            row = dict(fs=fs, range_g=rg)
            for nm, arr, f in (("median_err_pct", err, np.median), ("within10", (err <= 10).astype(float), np.mean), ("class_agree", (cls == ref_cls).astype(float), np.mean),
                               ("class_under", (cls < ref_cls).astype(float), np.mean), ("class_over", (cls > ref_cls).astype(float), np.mean)):
                p, lo, hi = B.ci_grouped(arr, groups, f)
                row[nm], row[nm + "_lo"], row[nm + "_hi"] = p, lo, hi
            out.append(row)
    return out


def main() -> None:
    from crashguard.results import record_many

    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    cells = SP.build_cells(tests)
    tab = pd.read_csv(C.TABLES / "n14_per_test.csv")
    asi_tab = {}
    for rg in SP.RANGES:
        t = tab[tab.range_g == rg].reset_index(drop=True)
        assert np.allclose(t.ref.to_numpy(), meta.ref.to_numpy())
        asi_tab[rg] = t.m_asi.to_numpy(float)
    ref = meta.ref.to_numpy()
    ref_asi = tab[tab.range_g == 16.0].reset_index(drop=True).ref_asi.to_numpy(float)
    ref_cls = np.array([S.classify(float(d), float(a), False) for d, a in zip(ref, ref_asi)])
    grp, n_dup = merged_groups(tests, meta)
    gmm = meta.group_mm.to_numpy()
    res, fallback, ncal = run(cells, meta, tests, grp, asi_tab, ref_cls)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"ua.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("n_tests", len(meta), "tests", "NHTSA tests")
    add("n_groups_make_model", int(len(set(gmm.tolist()))), "groups", "make and model")
    add("n_groups_after_duplicate_merge", int(len(set(grp.tolist()))), "groups", "make and model groups merged where two tests have identical recordings")
    add("n_duplicate_recordings", n_dup, "tests", "tests whose recording is identical to an earlier test; merged into its group")
    for c in range(4):
        add(f"true_class_count.{c}", int((ref_cls == c).sum()), "tests", f"reference class {('Low', 'Moderate', 'Severe', 'Critical')[c]}")
    rows, pair_rows = [], []
    for (rg, a, cond), d in res.items():
        tag = f"r{rg:g}.a{int(round(a * 100))}.{'cc' if cond else 'pooled'}"
        ch, lo, hi, up = d["c_hat"], d["lo"], d["hi"], d["up"]
        truth = np.broadcast_to(ref_cls[None, :], ch.shape)
        cover = ((truth >= lo) & (truth <= hi)).astype(float)
        upper_ok = (truth <= up).astype(float)
        width = (hi - lo + 1).astype(float)
        up_above = (up > ch).astype(float)
        sev_true = truth >= 2
        mis_pt = ((ch < 2) & sev_true).astype(float)
        mis_up = ((up < 2) & sev_true).astype(float)
        esc_pt = ((ch >= 2) & ~sev_true).astype(float)
        esc_up = ((up >= 2) & ~sev_true).astype(float)
        under_pt, under_up = (ch < truth).astype(float), (up < truth).astype(float)

        def gci(x, mask=None):
            # mean over (test, repeat) cells where mask is true, resampling make-and-model groups; cells outside the mask carry nan and are dropped by the statistic
            arr = np.where(mask if mask is not None else True, x, np.nan)
            return B.ci_grouped(arr.T, grp, lambda z: float(np.nanmean(z)))

        stats = {"coverage": gci(cover), "upper_valid": gci(upper_ok), "width": gci(width), "upper_above_point": gci(up_above),
                 "mis_triage_point": gci(mis_pt, sev_true), "mis_triage_upper": gci(mis_up, sev_true), "escalation_point": gci(esc_pt, ~sev_true), "escalation_upper": gci(esc_up, ~sev_true),
                 "under_point": gci(under_pt), "under_upper": gci(under_up)}
        nom = 1 - a
        for k, (p, lo_, h) in stats.items():
            add(f"{tag}.{k}", round(p, 4), "classes" if k == "width" else "fraction", "mean over test rows and 5 repeats; interval: grouped (make and model) bootstrap, 1000 resamples")
            add(f"{tag}.{k}_lo", round(lo_, 4), "classes" if k == "width" else "fraction", "95% grouped bootstrap interval")
            add(f"{tag}.{k}_hi", round(h, 4), "classes" if k == "width" else "fraction", "95% grouped bootstrap interval")
        p, lo_, h = stats["coverage"]
        add(f"{tag}.coverage_holds", int(lo_ <= nom <= h), "flag", f"1 = the nominal {nom:.2f} lies inside the 95% interval of the empirical two-sided coverage")
        p, lo_, h = stats["upper_valid"]
        add(f"{tag}.upper_valid_holds", int(lo_ <= nom <= h or lo_ > nom), "flag", "1 = nominal inside the interval, or the one-sided bound is conservative (interval above nominal)")
        add(f"{tag}.class_conditional_fallback_rows", fallback[(rg, a, cond)], "rows", "test rows (summed over repeats) whose predicted class had fewer than 10 calibration tests, so the pooled quantile was used")
        rows.append(dict(range_g=rg, alpha=a, variant="cc" if cond else "pooled", **{k: v[0] for k, v in stats.items()}))
        if abs(a - 0.10) < 1e-9:
            for rep in range(REPEATS):
                for i in range(len(meta)):
                    if ch[rep, i] >= 0:
                        pair_rows.append((rg, a, "cc" if cond else "pooled", rep, i, int(grp[i] == grp[i]), int(ref_cls[i]), int(ch[rep, i]), int(up[rep, i]), int(lo[rep, i]), int(hi[rep, i])))
    pd.DataFrame(pair_rows, columns=["range_g", "alpha", "variant", "repeat", "test_idx", "_", "true", "c_hat", "upper", "lo", "hi"]).drop(columns="_").to_csv(C.TABLES / "ua_pairs.csv", index=False)
    pd.DataFrame(rows).to_csv(C.TABLES / "ua_conformal.csv", index=False)
    # paired differences used by H-a, H-b, H-c (class-conditional, alpha 0.10)
    for rg in SP.RANGES:
        d = res[(rg, 0.10, True)]
        ch, up = d["c_hat"], d["up"]
        truth = np.broadcast_to(ref_cls[None, :], ch.shape)
        sev_true = truth >= 2
        mis_pt = np.where(sev_true, (ch < 2).astype(float), np.nan)
        mis_up = np.where(sev_true, (up < 2).astype(float), np.nan)
        esc_pt = np.where(~sev_true, (ch >= 2).astype(float), np.nan)
        esc_up = np.where(~sev_true, (up >= 2).astype(float), np.nan)
        nm = lambda z: float(np.nanmean(z))  # noqa: E731
        for nmx, a_, b_ in (("mis_triage_upper_minus_point", mis_pt, mis_up), ("escalation_upper_minus_point", esc_pt, esc_up)):
            p, lo_, h = B.paired_diff_grouped(a_.T, b_.T, grp, nm)
            add(f"r{rg:g}.a10.cc.paired.{nmx}", round(p, 4), "fraction", "upper-end class minus point class; paired; grouped bootstrap")
            add(f"r{rg:g}.a10.cc.paired.{nmx}_lo", round(lo_, 4), "fraction", "95% grouped bootstrap interval")
            add(f"r{rg:g}.a10.cc.paired.{nmx}_hi", round(h, 4), "fraction", "95% grouped bootstrap interval")
    for rg in SP.RANGES:
        for c in range(4):
            add(f"r{rg:g}.calibration_tests_per_predicted_class.{c}", round(float(ncal[rg][:, c].mean()), 2), "tests", "mean number of calibration tests whose predicted class is c (mean over folds and repeats)")
    # H-c: difference between ranges (mis-triage reduction at 16 g minus at 64 g; width at 64 g minus at 16 g)
    d16, d64 = res[(16.0, 0.10, True)], res[(64.0, 0.10, True)]
    truth = np.broadcast_to(ref_cls[None, :], d16["c_hat"].shape)
    sev_true = truth >= 2

    def reduction(d):
        return np.where(sev_true, (d["c_hat"] < 2).astype(float) - (d["up"] < 2).astype(float), np.nan)

    p, lo_, h = B.paired_diff_grouped(reduction(d64).T, reduction(d16).T, grp, lambda z: float(np.nanmean(z)))
    add("hc.reduction_16_minus_64", round(p, 4), "fraction", "mis-triage reduction (point minus upper) at +-16 g minus that at +-64 g; positive = the gain is larger at +-16 g; paired, grouped bootstrap")
    add("hc.reduction_16_minus_64_lo", round(lo_, 4), "fraction", "95% grouped bootstrap interval")
    add("hc.reduction_16_minus_64_hi", round(h, 4), "fraction", "95% grouped bootstrap interval")
    w16, w64 = (d16["hi"] - d16["lo"] + 1).astype(float), (d64["hi"] - d64["lo"] + 1).astype(float)
    p, lo_, h = B.paired_diff_grouped(w16.T, w64.T, grp, lambda z: float(np.nanmean(z)))
    add("hc.width_64_minus_16", round(p, 4), "classes", "mean interval width at +-64 g minus at +-16 g (negative = narrower at +-64 g); paired, grouped bootstrap")
    add("hc.width_64_minus_16_lo", round(lo_, 4), "classes", "95% grouped bootstrap interval")
    add("hc.width_64_minus_16_hi", round(h, 4), "classes", "95% grouped bootstrap interval")
    # B1: 100 and 200 Hz plain estimate; fill + ridge at 200 Hz is NOT_RUN
    for r in b1_plain_200hz(tests, meta, ref_cls, ref, ref_asi):
        for k in ("median_err_pct", "within10", "class_agree", "class_under", "class_over"):
            for suf in ("", "_lo", "_hi"):
                add(f"b1.plain.f{int(r['fs'])}.r{r['range_g']:g}.{k}{suf}", round(float(r[k + suf]), 4), "percent" if k == "median_err_pct" else "fraction", "plain estimate (no restoration); grouped bootstrap 95% interval" if not suf else "95% grouped bootstrap interval")
    for rg in SP.RANGES:
        add(f"b1.fill_ridge.f200.r{rg:g}", "NOT_RUN", "", "the fill and ridge constants (pulse-fit offsets in samples, saturation level, ridge strength) were tuned at 100 Hz and are not re-tuned at 200 Hz; the plain estimate is reported at 200 Hz instead", "NOT_RUN")
    record_many(ent, purge_prefixes=("ua.",))
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(3).to_string())
    for rg in SP.RANGES:
        print(rg, "H-a mis-triage upper minus point:", [round(next(e["value"] for e in ent if e["name"] == f"ua.r{rg:g}.a10.cc.paired.mis_triage_upper_minus_point{s}"), 4) for s in ("", "_lo", "_hi")])


if __name__ == "__main__":
    main()
