"""Study A (docs/02_preregistration/PREREGISTRATION_V2.md section 1): tail-aware clipping estimator, deterministic bounds, adaptive conformal intervals and an abstention flag. MEASURED_SOFTWARE on 176 NHTSA crash tests
(mostly high-speed barrier tests; not representative of all real crashes). Splits R (repeated grouped 5-fold, 10 repeats), G, A, O as in ``saturation_splits``; everything fitted uses the training tests of the fold only.
Prefix ``v2.a.``.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard import severity_study as SS
from crashguard import ua_core as U
from crashguard import v2_clip as V
from crashguard.v2_common import Entries, holm

RANGES = SP.RANGES
METHODS = ("B", "SP", "M", "M+", "TRI", "GP", "AVG", "RIDGE", "GBR", "QR")
NAMES = {"B": "plain", "SP": "spline", "M": "fill", "M+": "fill + ridge", "TRI": "triangle fit (our implementation of the idea)", "GP": "Gaussian-process fill (our implementation of the idea)",
         "AVG": "cost-weighted pulse-family average", "RIDGE": "ridge on all features", "GBR": "gradient boosting", "QR": "tail-aware (median quantile model)"}
DESC = ("clip_ms", "n_runs", "clip_frac", "slope_in", "slope_out", "rise_ms", "area_unclipped", "area_clip")
FAMF = ("dv_mean", "dv_median", "dv_best", "dv_wmean", "disagree")
GB = dict(n_estimators=100, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=C.SEED)
ALPHA = 0.10
CAL_SHARE = 0.4
SRC = "results/tables/v2_a_metrics.csv"


def q_hi(scores: np.ndarray, alpha: float) -> float:
    n = len(scores)
    if n == 0:
        return float("inf")
    k = math.ceil((n + 1) * (1 - alpha))
    return float(np.sort(scores)[min(k, n) - 1]) if k <= n else float(np.sort(scores)[-1])


class Ctx:
    def __init__(self):
        self.tests = SS.load_tests()
        self.meta = SP.meta_of(self.tests)
        self.cells = SP.build_cells(self.tests)
        self.df = V.build()
        self.ref = self.meta.ref.to_numpy()
        self.gmm = self.meta.group_mm.to_numpy()
        self.n = len(self.meta)
        self.F = {rg: self.df[self.df.range_g == rg].sort_values("test_idx").reset_index(drop=True) for rg in RANGES}

    def X(self, rg: float, combo: dict) -> np.ndarray:
        fam, sf, rf = combo["M"]
        f = self.F[rg]
        base = np.stack([self.cells[("b", rg, rf)], self.cells[("sh", rg, fam, sf, rf)], self.cells[("pl", rg, rf)]], axis=1)
        return np.concatenate([base, f[list(DESC)].to_numpy(float), f[list(FAMF)].to_numpy(float), f[["dv_plain", "pulse_ms"]].to_numpy(float)], axis=1)


def _logo_alpha(X, y, g, m_tr, ref_tr, app_tr) -> float:
    best, best_a = None, None
    for a in SP.ALPHAS:
        pred = np.zeros(len(y))
        for gg in sorted(set(g.tolist())):
            te = g == gg
            m = ~te
            if m.sum() >= 4:
                mu, sd = X[m].mean(0), np.where(X[m].std(0) > 1e-9, X[m].std(0), 1.0)
                r = Ridge(alpha=a).fit((X[m] - mu) / sd, y[m])
                pred[te] = r.predict((X[te] - mu) / sd)
        corr = m_tr.copy()
        corr[app_tr] *= np.exp(pred)
        sc = round(float(np.median(SP.aerr(corr, ref_tr))), 9)
        if best is None or (sc, -a) < (best, -best_a):
            best, best_a = sc, a
    return best_a


def fit_models(X_use, y_use, g_use, m_tr, ref_tr, app_tr, X_pred) -> dict:
    """Predictions of log(reference / fill estimate) for the rows X_pred: ridge on all features, gradient boosting, quantile boosting (10, 50, 90)."""
    out = {}
    if len(y_use) < 8:
        z = np.zeros(len(X_pred))
        return dict(ridge=z, gbr=z, q10=z, q50=z, q90=z)
    a = _logo_alpha(X_use, y_use, g_use, m_tr, ref_tr, app_tr)
    mu, sd = X_use.mean(0), np.where(X_use.std(0) > 1e-9, X_use.std(0), 1.0)
    out["ridge"] = Ridge(alpha=a).fit((X_use - mu) / sd, y_use).predict((X_pred - mu) / sd)
    out["gbr"] = GradientBoostingRegressor(loss="squared_error", **GB).fit(X_use, y_use).predict(X_pred)
    for q, k in ((0.1, "q10"), (0.5, "q50"), (0.9, "q90")):
        out[k] = GradientBoostingRegressor(loss="quantile", alpha=q, **GB).fit(X_use, y_use).predict(X_pred)
    out["q10"], out["q90"] = np.minimum(out["q10"], out["q50"]), np.maximum(out["q90"], out["q50"])
    return out


def point_estimates(cx: Ctx, tr: np.ndarray, te: np.ndarray, rg: float, combo: dict, leave: str) -> tuple[dict, dict]:
    est, _info = SP.estimates(cx.cells, cx.meta, tr, te, rg, combo, leave)
    fam, sf, rf = combo["M"]
    m_all, ap = cx.cells[("m", rg, fam, sf, rf)], cx.cells[("ap", rg, fam, sf, rf)]
    X = cx.X(rg, combo)
    use = tr & ap
    y = np.log(cx.ref / np.maximum(m_all, 1e-6))
    g = cx.gmm[use]
    pr = fit_models(X[use], y[use], g, m_all[tr], cx.ref[tr], ap[tr], X[te])
    apte = ap[te]
    mte = m_all[te]
    for k, name in (("ridge", "RIDGE"), ("gbr", "GBR"), ("q50", "QR")):
        e = mte.copy()
        e[apte] = mte[apte] * np.exp(pr[k][apte])
        est[name] = e
    f = cx.F[rg]
    est["TRI"], est["GP"], est["AVG"] = f.dv_triangle.to_numpy()[te], f.dv_gp.to_numpy()[te], f.dv_wmean.to_numpy()[te]
    return est, dict(ap=apte, m=mte, pr=pr, X=X, use=use, y=y, ap_all=ap, m_all=m_all)


def intervals(cx: Ctx, tr: np.ndarray, te: np.ndarray, rg: float, combo: dict, rep: int, f: int) -> dict:
    """A5 on one fold: calibration groups = 40% of the training make/model groups; models fitted on the rest; the three interval variants for the test rows (log scale around the median-model estimate)."""
    fam, sf, rf = combo["M"]
    m_all, ap = cx.cells[("m", rg, fam, sf, rf)], cx.cells[("ap", rg, fam, sf, rf)]
    X = cx.X(rg, combo)
    y = np.log(cx.ref / np.maximum(m_all, 1e-6))
    tr_groups = sorted(set(cx.gmm[tr].tolist()))
    rng2 = np.random.default_rng(C.SEED + 500 + rep * 10 + f)
    perm = rng2.permutation(len(tr_groups))
    cal_groups = {tr_groups[i] for i in perm[: max(1, int(round(CAL_SHARE * len(tr_groups))))]}
    cal = np.array([g in cal_groups for g in cx.gmm]) & tr
    fit = tr & ~cal
    use = fit & ap
    pr_cal_te = fit_models(X[use], y[use], cx.gmm[use], m_all[fit], cx.ref[fit], ap[fit], X[cal | te])
    n_cal = int(cal.sum())
    idx_ct = np.flatnonzero(cal | te)
    pos = {int(i): k for k, i in enumerate(idx_ct)}
    cal_i, te_i = np.flatnonzero(cal), np.flatnonzero(te)
    q10 = np.array([pr_cal_te["q10"][pos[int(i)]] for i in np.concatenate([cal_i, te_i])])
    q50 = np.array([pr_cal_te["q50"][pos[int(i)]] for i in np.concatenate([cal_i, te_i])])
    q90 = np.array([pr_cal_te["q90"][pos[int(i)]] for i in np.concatenate([cal_i, te_i])])
    ycal, yte = y[cal_i], y[te_i]
    apc, apt = ap[cal_i], ap[te_i]
    q10c, q50c, q90c = q10[:n_cal], q50[:n_cal], q90[:n_cal]
    q10t, q50t, q90t = q10[n_cal:], q50[n_cal:], q90[n_cal:]
    # difficulty model: absolute residual of the median model on the fit rows
    d_te = np.ones(len(te_i))
    d_cal = np.ones(n_cal)
    if use.sum() >= 12:
        # cross-fitted residuals of the median model (inner grouped 4-fold on the fit rows): in-sample residuals are close to zero and make the difficulty model unstable (run 1 of this study; docs/07_log/DECISIONS.md)
        idx_use = np.flatnonzero(use)
        gu = sorted(set(cx.gmm[idx_use].tolist()))
        rng3 = np.random.default_rng(C.SEED + 900 + rep * 10 + f)
        pf = {g: k % 4 for k, g in enumerate(rng3.permutation(gu))}
        inner = np.array([pf[g] for g in cx.gmm[idx_use]])
        res_fit = np.zeros(len(idx_use))
        for k in range(4):
            m_in = inner != k
            if m_in.sum() < 8 or (~m_in).sum() == 0:
                res_fit[~m_in] = np.abs(y[idx_use][~m_in])
                continue
            g50 = GradientBoostingRegressor(loss="quantile", alpha=0.5, **GB).fit(X[idx_use][m_in], y[idx_use][m_in])
            res_fit[~m_in] = np.abs(y[idx_use][~m_in] - g50.predict(X[idx_use][~m_in]))
        gb = GradientBoostingRegressor(loss="squared_error", **GB).fit(X[use], res_fit)
        d_cal = np.maximum(gb.predict(X[cal_i]), 0.02)
        d_te = np.maximum(gb.predict(X[te_i]), 0.02)
    out = {}
    # not-applied (never clipped) events: one interval from their own calibration residuals
    nc = ~apc
    s_i = q_hi(np.abs(ycal[apc] - q50c[apc]), ALPHA)
    r_none = q_hi(np.abs(ycal[nc]), ALPHA) if nc.sum() >= 5 else s_i  # fewer than 5 never-clipped calibration events: the half-width of the clipped events
    s_ii = q_hi(np.maximum(q10c[apc] - ycal[apc], ycal[apc] - q90c[apc]), ALPHA)
    s_iii = q_hi(np.abs(ycal[apc] - q50c[apc]) / d_cal[apc], ALPHA)
    lo_i, hi_i = np.where(apt, q50t - s_i, -r_none), np.where(apt, q50t + s_i, r_none)
    lo_ii, hi_ii = np.where(apt, q10t - s_ii, -r_none), np.where(apt, q90t + s_ii, r_none)
    lo_iii, hi_iii = np.where(apt, q50t - s_iii * d_te, -r_none), np.where(apt, q50t + s_iii * d_te, r_none)
    mte = m_all[te_i]
    out["te_i"], out["apt"], out["m"], out["q50"] = te_i, apt, mte, q50t
    for k, (lo, hi) in {"i": (lo_i, hi_i), "ii": (lo_ii, hi_ii), "iii": (lo_iii, hi_iii)}.items():
        out[k] = dict(lo=mte * np.exp(lo), hi=mte * np.exp(hi), cover=(yte >= lo) & (yte <= hi))
    # difficulty percentile threshold for the abstention flag, from calibration rows
    out["w_iii_cal"] = (m_all[cal_i] * (np.exp(q50c + s_iii * d_cal) - np.exp(q50c - s_iii * d_cal)))[apc]
    out["clip_cal"] = cx.F[rg].clip_frac.to_numpy()[cal_i][apc]
    out["clip_train"] = cx.F[rg].clip_frac.to_numpy()[tr & ap]
    return out


def stats_block(e: np.ndarray, groups: np.ndarray, repeats: bool) -> dict:
    out = {}
    if repeats:  # e is (n, repeats)
        fs = {"median": lambda a: float(np.median(a, axis=0).mean()), "p90": lambda a: float(np.quantile(a, 0.9, axis=0).mean()), "p95": lambda a: float(np.quantile(a, 0.95, axis=0).mean()),
              "w10": lambda a: float((a <= SS.TOL10).mean())}
    else:
        fs = {"median": np.median, "p90": lambda a: float(np.quantile(a, 0.9)), "p95": lambda a: float(np.quantile(a, 0.95)), "w10": lambda a: float((a <= SS.TOL10).mean())}
    for k, f in fs.items():
        out[k] = B.ci_grouped(e, groups, f)
    return out, fs


def gdraws(groups: np.ndarray, fn, n_boot: int = B.N_BOOT, seed: int = B.SEED) -> tuple[float, np.ndarray]:
    mem = B.group_members(groups)
    draws = np.array([fn(i) for i in B._gidx(mem, n_boot, seed)], dtype=np.float64)
    return float(fn(np.arange(len(groups)))), draws


def pval_le(draws: np.ndarray, null: float = 0.0) -> float:
    """One-sided bootstrap p-value for the claim 'effect is above ``null``': share of draws at or below it."""
    return float(max(np.mean(draws <= null), 1.0 / (len(draws) + 1)))


def main() -> None:
    cx = Ctx()
    n = cx.n
    ent = Entries("v2.a", SRC, "MEASURED_SOFTWARE")
    held_G = np.array([t["role"] == "heldout" for t in cx.tests])
    held_O, held_A = SP.split_O(cx.meta), SP.split_by(cx.meta, "group_mm")
    combo_fixed = SP.fixed_combo(cx.cells, cx.meta, ~held_G)
    E: dict[str, dict[float, dict[str, np.ndarray]]] = {}
    EST: dict = {}
    # ---------------- fixed splits
    for sp, held in (("O", held_O), ("G", held_G), ("A", held_A)):
        E[sp], EST[sp] = {}, {}
        for rg in RANGES:
            est, _ = point_estimates(cx, ~held, held, rg, combo_fixed, "test")
            E[sp][rg] = {m: SP.aerr(est[m], cx.ref[held]) for m in METHODS}
            EST[sp][rg] = est
    # ---------------- split R with intervals
    REP, NF = SP.N_REPEATS, SP.N_FOLDS
    ug = sorted(set(cx.gmm.tolist()))
    E["R"] = {rg: {m: np.zeros((REP, n)) for m in METHODS} for rg in RANGES}
    EST["R"] = {rg: {m: np.zeros((REP, n)) for m in METHODS} for rg in RANGES}
    IV = {rg: {k: dict(cover=np.full((REP, n), np.nan), width=np.full((REP, n), np.nan), relw=np.full((REP, n), np.nan)) for k in ("i", "ii", "iii")} for rg in RANGES}
    BIN = {rg: np.full((REP, n), -1, int) for rg in RANGES}  # 0 none, 1 low, 2 mid, 3 high clipped-fraction tercile
    FLAG = {rg: np.zeros((REP, n), bool) for rg in RANGES}
    for rep in range(REP):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % NF for k, j in enumerate(order)}
        fold = np.array([fold_of[g] for g in cx.gmm])
        for f in range(NF):
            te, tr = fold == f, fold != f
            combo = SP.choose_combo(cx.cells, cx.meta, tr)
            for rg in RANGES:
                est, info = point_estimates(cx, tr, te, rg, combo, "group")
                for m in METHODS:
                    EST["R"][rg][m][rep, te] = est[m]
                    E["R"][rg][m][rep, te] = SP.aerr(est[m], cx.ref[te])
                iv = intervals(cx, tr, te, rg, combo, rep, f)
                te_i, apt = iv["te_i"], iv["apt"]
                clip = cx.F[rg].clip_frac.to_numpy()[te_i]
                ctr = iv["clip_train"]
                c1, c2 = (np.quantile(ctr, [1 / 3, 2 / 3]) if len(ctr) >= 3 else (0.0, 1.0))
                binv = np.where(~apt, 0, np.where(clip <= c1, 1, np.where(clip <= c2, 2, 3)))
                BIN[rg][rep, te_i] = binv
                for k in ("i", "ii", "iii"):
                    IV[rg][k]["cover"][rep, te_i] = iv[k]["cover"]
                    IV[rg][k]["width"][rep, te_i] = iv[k]["hi"] - iv[k]["lo"]
                    IV[rg][k]["relw"][rep, te_i] = (iv[k]["hi"] - iv[k]["lo"]) / np.maximum(iv["m"] * np.exp(iv["q50"]), 1e-6)
                wthr = np.quantile(iv["w_iii_cal"], 0.75) if len(iv["w_iii_cal"]) else np.inf
                cthr = np.quantile(ctr, 0.75) if len(ctr) else np.inf
                FLAG[rg][rep, te_i] = apt & ((clip > cthr) | ((iv["iii"]["hi"] - iv["iii"]["lo"]) > wthr))
    # ---------------- metrics
    p_h: dict[str, float] = {}
    exp_p: dict[str, float] = {}  # A4 family p-values (QR against the four earlier methods, p90)
    for sp in ("R", "G", "A", "O"):
        held = {"R": np.ones(n, bool), "G": held_G, "A": held_A, "O": held_O}[sp]
        groups = cx.gmm[held]
        for rg in RANGES:
            e_all = E[sp][rg]
            for m in METHODS:
                e = e_all[m].T if sp == "R" else e_all[m]
                blk, _fs = stats_block(e, groups, sp == "R")
                for k, tr_ in blk.items():
                    ent.ci(f"{sp}.r{rg:g}.{m}.{k}", tr_, "fraction" if k == "w10" else "percent", d=4)
                ent.add(f"{sp}.r{rg:g}.{m}.n", int(held.sum()), "tests")
            for ref_m in ("B", "SP", "M", "M+", "TRI", "GP"):
                for new_m in ("QR", "GBR", "RIDGE"):
                    ea = e_all[ref_m].T if sp == "R" else e_all[ref_m]
                    eb = e_all[new_m].T if sp == "R" else e_all[new_m]
                    for k, fn in (("p90", (lambda a: float(np.quantile(a, 0.9, axis=0).mean())) if sp == "R" else (lambda a: float(np.quantile(a, 0.9)))),
                                  ("median", (lambda a: float(np.median(a, axis=0).mean())) if sp == "R" else np.median)):
                        pt, draws = gdraws(groups, lambda i, ea=ea, eb=eb, fn=fn: fn(ea[i]) - fn(eb[i]))
                        lo, hi = float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))
                        nm = f"{sp}.r{rg:g}.paired.{ref_m}_minus_{new_m}.{k}"
                        ent.ci(nm, (pt, lo, hi), "percent", "reference minus new (positive = the new estimator is better)", d=3)
                        if k == "p90" and new_m == "QR" and ref_m in ("B", "SP", "M", "M+"):
                            exp_p[f"{sp}.r{rg:g}.{ref_m}"] = pval_le(draws, 0.0)
                            ent.add(nm + "_p", round(exp_p[f"{sp}.r{rg:g}.{ref_m}"], 4), "probability", "one-sided bootstrap p (reduction at or below 0)")
    adj = holm(exp_p)
    for k, v in adj.items():
        ent.add(f"holm_a4.{k}.p90_QR_better_than", round(v, 4), "probability", "Holm-adjusted over the 48 A4 baseline comparisons (EXPLORATORY family)")
    # ---------------- H-A1
    rg = 16.0
    ha1 = {}
    for sp in ("R", "G", "A", "O"):
        held = {"R": np.ones(n, bool), "G": held_G, "A": held_A, "O": held_O}[sp]
        ea = E[sp][rg]["M+"].T if sp == "R" else E[sp][rg]["M+"]
        eb = E[sp][rg]["QR"].T if sp == "R" else E[sp][rg]["QR"]
        fn = (lambda a: float(np.quantile(a, 0.9, axis=0).mean())) if sp == "R" else (lambda a: float(np.quantile(a, 0.9)))
        pt, draws = gdraws(cx.gmm[held], lambda i: fn(ea[i]) - fn(eb[i]))
        ha1[sp] = (pt, float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)), pval_le(draws, 0.0))
        ent.ci(f"hA1.{sp}.p90_reduction_Mplus_minus_QR", ha1[sp][:3], "percent points", "positive = the tail-aware estimator has the lower 90th-percentile error", d=3)
    p_h["H-A1"] = ha1["R"][3]
    ent.add("hA1.p_raw", round(p_h["H-A1"], 4), "probability", "split R, +-16 g, reduction at or below 0")
    ent.add("hA1.n_splits_with_5pt_gain", int(sum(v[0] >= 5.0 for v in ha1.values())), "splits", "point reductions of at least 5 points")
    ent.add("hA1.criterion_met", int(ha1["R"][0] >= 5.0 and ha1["R"][1] > 0 and sum(v[0] >= 5.0 for v in ha1.values()) >= 2), "flag", "R: reduction at least 5 and interval above zero, and at least two splits with a point reduction of at least 5")
    # ---------------- A5 coverage and width, H-A2
    for rg in RANGES:
        for k in ("i", "ii", "iii"):
            cov = IV[rg][k]["cover"]
            ent.ci(f"a5.r{rg:g}.{k}.coverage", B.ci_grouped(cov.T, cx.gmm, lambda a: float(np.nanmean(a))), "fraction", d=4)
            ent.ci(f"a5.r{rg:g}.{k}.width_kmh", B.ci_grouped(IV[rg][k]["width"].T, cx.gmm, lambda a: float(np.nanmean(a))), "km/h", d=3)
            ent.ci(f"a5.r{rg:g}.{k}.width_rel", B.ci_grouped(IV[rg][k]["relw"].T, cx.gmm, lambda a: float(np.nanmedian(a))), "fraction of the estimate", "median over events", d=4)
            for b, bn in ((0, "none"), (1, "low"), (2, "mid"), (3, "high")):
                msk = BIN[rg] == b
                if msk.sum() < 5:
                    continue
                ent.add(f"a5.r{rg:g}.{k}.bin_{bn}.n", int(msk.sum()), "event-repeats")
                ent.add(f"a5.r{rg:g}.{k}.bin_{bn}.coverage", round(float(np.nanmean(np.where(msk, cov, np.nan))), 4), "fraction")
                ent.add(f"a5.r{rg:g}.{k}.bin_{bn}.width_kmh", round(float(np.nanmean(np.where(msk, IV[rg][k]["width"], np.nan))), 3), "km/h")
                ent.add(f"a5.r{rg:g}.{k}.bin_{bn}.width_rel", round(float(np.nanmedian(np.where(msk, IV[rg][k]["relw"], np.nan))), 4), "fraction of the estimate")
    rg = 16.0
    low = BIN[rg] == 1
    dd = np.where(low, IV[rg]["iii"]["relw"] - IV[rg]["i"]["relw"], np.nan)
    stat = lambda a: float(np.nanmean(a))  # noqa: E731
    pt, draws = gdraws(cx.gmm, lambda i: stat(dd.T[i]))
    ent.ci("hA2.low_tercile.relwidth_iii_minus_i", (pt, float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))), "fraction of the estimate", "negative = adaptive interval narrower; lowest clipped-fraction tercile, +-16 g", d=4)
    p_ha2_w = float(max(np.mean(draws >= 0.0), 1.0 / (len(draws) + 1)))
    cov3 = float(np.nanmean(IV[rg]["iii"]["cover"]))
    ent.add("hA2.coverage_iii", round(cov3, 4), "fraction")
    ent.add("hA2.p_raw", round(p_ha2_w, 4), "probability", "width difference at or above 0")
    ent.add("hA2.criterion_met", int(pt < 0 and float(np.quantile(draws, 0.975)) < 0 and 0.88 <= cov3 <= 0.92), "flag", "narrower in the lowest tercile with the interval below zero and coverage in 0.88 to 0.92")
    p_h["H-A2"] = p_ha2_w
    # ---------------- A6 abstention
    for rg in RANGES:
        fl = FLAG[rg]
        qr = E["R"][rg]["QR"]
        ent.add(f"a6.r{rg:g}.share_flagged", round(float(fl.mean()), 4), "fraction", "events (over repeats) flagged by clipped fraction above the 75th training percentile or interval width above the 75th calibration percentile")
        for nm, msk in (("unflagged", ~fl), ("flagged", fl)):
            if msk.sum() >= 5:
                ent.add(f"a6.r{rg:g}.{nm}.median_err", round(float(np.median(qr[msk])), 3), "percent")
                ent.add(f"a6.r{rg:g}.{nm}.p90_err", round(float(np.quantile(qr[msk], 0.9)), 3), "percent")
        refc = U.classes(cx.ref, np.full(n, 0.0))  # delta-V class only; ASI is not needed for the share below
        sev = (refc >= 2)[None, :] & np.ones((REP, 1), bool)
        if fl.sum():
            ent.add(f"a6.r{rg:g}.flagged.share_severe_or_critical", round(float(sev[fl].mean()), 4), "fraction", "reference delta-V class Severe or Critical")
    # ---------------- bounds, H-A3
    for rgv in RANGES:
        f = cx.F[rgv]
        ref = f.ref.to_numpy()
        lo, up = f.dv_plain.to_numpy(), f.dv_upper.to_numpy()
        inside = (lo <= ref) & (ref <= up)
        pt, draws = gdraws(cx.gmm, lambda i: float(inside[i].mean()))
        ent.ci(f"a2.r{rgv:g}.containment", (pt, float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))), "fraction", "reference delta-V within [plain, upper bound], all 176 tests", d=4)
        sat = f.saturated.to_numpy().astype(bool)
        ent.add(f"a2.r{rgv:g}.n_saturated", int(sat.sum()), "tests", "tests with at least one clipped pulse sample (level 0.7 of the range)")
        if sat.any():
            ent.add(f"a2.r{rgv:g}.containment_saturated", round(float(inside[sat].mean()), 4), "fraction")
        ent.add(f"a2.r{rgv:g}.lower_exceeds_ref_1p00", int((lo > ref).sum()), "tests", "plain estimate above the reference (the lower-bound statement fails)")
        ent.add(f"a2.r{rgv:g}.lower_exceeds_ref_1p05", int((lo > 1.05 * ref).sum()), "tests", "plain estimate more than 5% above the reference")
        ent.add(f"a2.r{rgv:g}.width_kmh_mean", round(float((up - lo).mean()), 3), "km/h")
        ent.add(f"a2.r{rgv:g}.width_rel_median", round(float(np.median((up - lo) / ref)), 4), "fraction of the reference")
        ent.add(f"a2.r{rgv:g}.fallback_upper", int(f.upper_fallback.sum()), "tests", "no family could be fitted: amplitude capped at 12 x range")
        ent.add(f"a2.r{rgv:g}.upper_below_ref", int((up < ref).sum()), "tests")
        if rgv == 16.0:
            p_h["H-A3"] = pval_le(draws, 0.90)  # p that containment is at or below 0.90
            ent.add("hA3.p_raw", round(p_h["H-A3"], 4), "probability", "containment at or below 0.90")
            ent.add("hA3.criterion_met", int(pt >= 0.90), "flag", "point containment at +-16 g at least 0.90")
    # ---------------- A1 correlations on the tuning tests of split G
    from scipy.stats import spearmanr

    tune = ~held_G
    for rgv in RANGES:
        f = cx.F[rgv]
        y = np.log(np.maximum(f.dv_plain.to_numpy(), 1e-6) / cx.ref)
        for d in DESC + ("disagree",):
            x = f[d].to_numpy(float)
            if np.ptp(x[tune]) == 0:
                continue
            rho = float(spearmanr(x[tune], y[tune])[0])
            pt, draws = gdraws(cx.gmm[tune], lambda i, x=x[tune], y=y[tune]: float(spearmanr(x[i], y[i])[0]))
            ent.ci(f"a1.r{rgv:g}.{d}.spearman_with_plain_log_error", (rho, float(np.nanquantile(draws, 0.025)), float(np.nanquantile(draws, 0.975))), "correlation", "tuning tests of split G only", d=3)
    ent.add("holm_family.size", len(exp_p), "comparisons")
    ent.flush()
    pd.DataFrame([dict(h=k, p=v) for k, v in p_h.items()]).to_csv(C.TABLES / "v2_a_pvalues.csv", index=False)
    rows = []
    for sp in ("R", "G", "A", "O"):
        for rgv in RANGES:
            for m in METHODS:
                e = E[sp][rgv][m]
                rows.append(dict(split=sp, range_g=rgv, method=m, median=float(np.median(e)), p90=float(np.quantile(e, 0.9)), p95=float(np.quantile(e, 0.95)), w10=float((e <= SS.TOL10).mean())))
    pd.DataFrame(rows).to_csv(C.TABLES / "v2_a_metrics.csv", index=False)
    print(pd.DataFrame(rows).query("range_g == 16").round(3).to_string())
    print({k: [round(x, 3) for x in v] for k, v in ha1.items()})
    print("p", p_h)


if __name__ == "__main__":
    main()
