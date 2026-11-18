"""P2 (docs/02_preregistration/PREREGISTRATION_V4.md section 2): certified severity interval [plain, plain x q] from the physical lower bound, against the relative-residual split-conformal interval around fill + ridge.

``fit``: calibrate on the VALIDATION fold (q per variant and cell; clipping bins from development; the mode classifier of Z1 from the P1 freeze), write the freeze file.
``eval``: score the SEALED fold once (``sealed_gate``). Intervals resample whole make-and-model groups. MEASURED_SOFTWARE.
"""
from __future__ import annotations

import math
import sys

import joblib
import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import pp_models as PM
from crashguard.pp_ctx import Ctx
from crashguard.pp_p1 import CELLS, MODEL_DIR
from crashguard.s9_conformal_dv import cvplus

ALPHA = 0.10
SRC = "results/tables/p2_sealed.csv"
VARIANTS = ("global", "clipbin", "mode", "weighted")
FLOOR_RATIO = 0.1


def cq(scores: np.ndarray, alpha: float, w: np.ndarray | None = None) -> float:
    """Conformal quantile: the ceil((n + 1)(1 - alpha))-th smallest score (weighted version: smallest score whose cumulative weight reaches 1 - alpha of the total plus the largest weight)."""
    s = np.asarray(scores, float)
    if w is None:
        k = math.ceil((len(s) + 1) * (1.0 - alpha))
        return float("inf") if k > len(s) else float(np.sort(s)[k - 1])
    o = np.argsort(s, kind="stable")
    ws = np.asarray(w, float)[o]
    cum = np.cumsum(ws) / (ws.sum() + ws.max())
    j = np.flatnonzero(cum >= 1.0 - alpha)
    return float(s[o][j[0]]) if j.size else float("inf")


def alpha_eff(r_val: np.ndarray) -> float:
    return float(max(ALPHA - float(np.mean(r_val < 1.0)), 0.02))


def clip_bin(clip_ms: np.ndarray, edge: float) -> np.ndarray:
    return np.where(clip_ms <= 0, 0, np.where(clip_ms <= edge, 1, 2))


def fit_cal(cx: Ctx) -> dict:
    out = {}
    for rg, fs in CELLS:
        df, W = cx.cell(rg, fs)
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{fs}.joblib")
        plain = np.maximum(df.dv_plain.to_numpy(float), 1e-6)
        r = cx.ref / plain
        va = cx.val
        a = alpha_eff(r[va])
        cl = df.clip_ms.to_numpy(float)
        edge = float(np.median(cl[cx.dev & (cl > 0)]))
        cal = dict(alpha=a, q_global=max(cq(r[va], a), 1.0), edge=edge, n_val=int(va.sum()), share_val_below_plain=float(np.mean(r[va] < 1.0)))
        b = clip_bin(cl, edge)
        for k in (0, 1, 2):
            m = va & (b == k)
            cal[f"q_clipbin{k}"] = max(cq(r[m], alpha_eff(r[m]), None), 1.0) if m.sum() >= 10 else cal["q_global"]
            cal[f"n_clipbin{k}"] = int(m.sum())
        mi = z["modeclf"].predict(df)
        for k, mo in enumerate(PC.MODES):
            m = va & (mi == k)
            cal[f"q_mode{k}"] = max(cq(r[m], alpha_eff(r[m])), 1.0) if m.sum() >= 10 else cal["q_global"]
            cal[f"n_mode{k}"] = int(m.sum())
        gs = pd.Series(cx.group).map(pd.Series(cx.group[va]).value_counts()).fillna(1).to_numpy(float)
        cal["q_weighted"] = max(cq(r[va], a, 1.0 / gs[va]), 1.0)
        # existing interval: relative residual around fill + ridge
        f = z["models"]["b"].predict(df)
        rel = np.abs(cx.ref - f) / np.maximum(f, 1e-6)
        cal["r_existing"] = cq(rel[va], ALPHA)
        out[(rg, fs)] = cal
    return out


def intervals(cx: Ctx, df: pd.DataFrame, z: dict, cal: dict, idx: np.ndarray) -> dict:
    """Intervals of every variant for the rows ``idx``: name -> (lo, hi)."""
    plain = df.dv_plain.to_numpy(float)[idx]
    cl = df.clip_ms.to_numpy(float)[idx]
    mi = z["modeclf"].predict(df.iloc[idx])
    iv = {"global": (plain, plain * cal["q_global"]), "weighted": (plain, plain * cal["q_weighted"])}
    b = clip_bin(cl, cal["edge"])
    iv["clipbin"] = (plain, plain * np.array([cal[f"q_clipbin{k}"] for k in b]))
    iv["mode"] = (plain, plain * np.array([cal[f"q_mode{k}"] for k in mi]))
    f = z["models"]["b"].predict(df.iloc[idx])
    r = cal["r_existing"]
    iv["existing"] = (np.maximum(f * (1 - r), FLOOR_RATIO * f), f * (1 + r))
    return iv


def cvplus_interval(cx: Ctx, rg: float, fs: int, te_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """EXPLORATORY grouped CV+ (N24 form) around fill + ridge: inner grouped 5-fold on development + validation records."""
    df, _ = cx.cell(rg, fs)
    pool = np.flatnonzero(cx.dev | cx.val)
    ug = sorted(set(cx.group[pool].tolist()))
    rng = np.random.default_rng(C.SEED)
    fo = {g: k % 5 for k, g in enumerate(rng.permutation(ug))}
    inner = np.array([fo[g] for g in cx.group[pool]])
    f_test = np.zeros((5, len(te_idx)))
    oof = np.zeros(len(pool))
    for k in range(5):
        m = PM.RidgeEst().fit(df.iloc[pool[inner != k]], cx.ref[pool[inner != k]], cx.group[pool[inner != k]])
        f_test[k] = m.predict(df.iloc[te_idx])
        oof[inner == k] = m.predict(df.iloc[pool[inner == k]])
    resid = np.abs(cx.ref[pool] - oof) / np.maximum(oof, 1e-6)
    lo, hi = cvplus(f_test, inner, resid, ALPHA)
    return lo, hi


def fit_stage(cx: Ctx) -> None:
    cal = fit_cal(cx)
    files = [MODEL_DIR / f"p1_{rg:g}_{fs}.joblib" for rg, fs in CELLS]
    h = PC.freeze("P2", dict(calibration={f"{rg:g}_{fs}": v for (rg, fs), v in cal.items()}, note="q calibrated on validation only; sealed fold not used; the P1 model files are inputs (base fill + ridge and mode classifier)"), files)
    print("freeze", h)
    for (rg, fs), v in cal.items():
        print(rg, fs, {k: (round(x, 3) if isinstance(x, float) else x) for k, x in v.items() if k in ("alpha", "q_global", "q_weighted", "r_existing", "share_val_below_plain")})


def eval_stage(cx: Ctx) -> None:
    import json

    fz = json.loads((PC.FREEZE_DIR / "p_freeze_P2.json").read_text(encoding="utf-8"))
    for f, hsh in fz["model_files"].items():
        assert PC.sha256_file(f) == hsh, f"{f} changed after the freeze"
    h = PC.sealed_gate("P2")
    E = PC.PEntries("p2", SRC)
    E.add("freeze_commit", h, "commit", "commit of the freeze of P2")
    te = cx.test
    idx = np.flatnonzero(te)
    grp, ref, mode, v = cx.group[idx], cx.ref[idx], cx.mode[idx], cx.v[idx]
    g = PC.GBoot(grp)
    rows = []
    res = {}
    for rg, fs in CELLS:
        df, _ = cx.cell(rg, fs)
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{fs}.joblib")
        cal = fz["calibration"][f"{rg:g}_{fs}"]
        iv = intervals(cx, df, z, cal, idx)
        iv["cvplus"] = cvplus_interval(cx, rg, fs, idx)
        tag = f"r{rg:g}.f{fs}"
        for name, (lo, hi) in iv.items():
            cov = ((ref >= lo) & (ref <= hi)).astype(float)
            ratio = np.where(lo > 0, hi / np.maximum(lo, 1e-9), np.nan)
            ratio = np.where(np.isfinite(ratio), ratio, np.nan)
            width = hi - lo
            ex = name == "cvplus"
            nt = f"{tag}.{name}" + (".EXPLORATORY" if ex else "")
            E.ci(f"{nt}.coverage", g.ci(lambda i: float(cov[i].mean())), "fraction", "sealed fold; grouped bootstrap")
            E.ci(f"{nt}.width_ratio_mean", g.ci(lambda i: float(np.nanmean(ratio[i]))), "ratio", "mean upper-to-lower ratio (records with a positive lower end)")
            E.ci(f"{nt}.width_kmh_mean", g.ci(lambda i: float(np.nanmean(np.where(np.isfinite(width[i]), width[i], np.nan)))), "km/h")
            fb = mode == "frontal_barrier"
            inside = (lo >= v) & (hi <= 2 * v)
            E.add(f"{nt}.frontal_barrier.n", int(fb.sum()), "records")
            E.add(f"{nt}.frontal_barrier.share_inside_band", round(float(inside[fb].mean()), 4), "fraction", "interval inside v <= delta-V <= 2 v (both ends); few records, no interval")
            E.add(f"{nt}.frontal_barrier.share_upper_le_2v", round(float((hi[fb] <= 2 * v[fb]).mean()), 4), "fraction")
            E.add(f"{nt}.frontal_barrier.share_lower_ge_v", round(float((lo[fb] >= v[fb]).mean()), 4), "fraction")
            for mo in PC.MODES:
                m = mode == mo
                if m.sum() >= 5:
                    gm = PC.GBoot(grp[m])
                    E.ci(f"{nt}.mode.{mo}.coverage", gm.ci(lambda i, m=m: float(cov[m][i].mean())), "fraction", f"n = {int(m.sum())}" + ("" if m.sum() >= 50 else " (under 50 records: descriptive)"))
            rows.append(dict(range_g=rg, rate_hz=fs, variant=name, coverage=float(cov.mean()), width_ratio=float(np.nanmean(ratio)), width_kmh=float(np.nanmean(width))))
        # reduction of the width ratio against the existing interval, primary variant
        for name in ("global", "clipbin", "mode", "weighted"):
            lo, hi = iv[name]
            ro = np.where(iv["existing"][0] > 0, iv["existing"][1] / iv["existing"][0], np.nan)
            rn = np.where(lo > 0, hi / np.maximum(lo, 1e-9), np.nan)
            st = lambda i, rn=rn, ro=ro: 1.0 - float(np.nanmean(rn[i])) / float(np.nanmean(ro[i]))  # noqa: E731
            pt, d = g.stat(st)
            E.ci(f"{tag}.{name}.width_ratio_reduction_vs_existing", PC.summ(pt, d), "fraction", "(existing - new) / existing of the mean upper-to-lower ratio")
            res[(rg, fs, name)] = (pt, d)
        lo, hi = iv["global"]
        cov = ((ref >= lo) & (ref <= hi)).astype(float)
        pole = mode == "pole"
        res[(rg, fs, "cov")] = (g.stat(lambda i: float(cov[i].mean())), PC.GBoot(grp[pole]).stat(lambda i: float(cov[pole][i].mean())), int(pole.sum()))
    # H-P2
    rg, fs = 16.0, 100
    (c_pt, c_d), (p_pt, p_d), n_pole = res[(rg, fs, "cov")]
    w_pt, w_d = res[(rg, fs, "global")]
    c_lo, p_lo = float(np.quantile(c_d, 0.025)), float(np.quantile(p_d, 0.025))
    w_lo = float(np.quantile(w_d, 0.025))
    cov_ok = c_lo >= 0.85 and (n_pole < 50 or p_lo >= 0.85)
    wid_ok = w_pt >= 0.20 and w_lo > 0
    E.add("hP2.coverage_lower_overall", round(c_lo, 4), "fraction", "lower end of the 95% grouped interval, global q, +-16 g, 100 Hz")
    E.add("hP2.coverage_lower_pole", round(p_lo, 4), "fraction", f"pole (n = {n_pole}); the only mode with at least 50 sealed records")
    E.add("hP2.coverage_condition_met", int(cov_ok), "flag")
    E.add("hP2.width_reduction", round(w_pt, 4), "fraction")
    E.add("hP2.width_reduction_lo", round(w_lo, 4), "fraction")
    E.add("hP2.width_condition_met", int(wid_ok), "flag", "reduction at least 0.20 with the lower end above zero")
    E.add("hP2.criterion_met", int(cov_ok and wid_ok), "flag")
    p_cov = max(PC.p_below(c_d, 0.85), PC.p_below(p_d, 0.85) if n_pole >= 50 else 0.0)
    E.add("hP2.p_raw", round(max(p_cov, PC.p_below(w_d, 0.20)), 4), "probability", "larger of the coverage clause (share of resamples with coverage at or below 0.85) and the width clause (share with reduction at or below 0.20)")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "p2_sealed.csv", index=False)
    PC.time_log("P2 sealed", "sealed fold scored once for P2; freeze commit " + h[:8])
    print("H-P2 coverage lower", round(c_lo, 3), round(p_lo, 3), "reduction", round(w_pt, 3), round(w_lo, 3), "criterion", cov_ok and wid_ok)


if __name__ == "__main__":
    cx = Ctx()
    {"fit": lambda: fit_stage(cx), "eval": lambda: eval_stage(cx)}[sys.argv[1]]()
