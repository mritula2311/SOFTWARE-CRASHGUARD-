"""Study A, part 1 (docs/02_preregistration/PREREGISTRATION_V2.md section 1): per test and sensor range, the clipping descriptors (A1), the deterministic lower and upper delta-V bounds (A2), the pulse-family fits and their disagreement (A3)
and the two "our implementation of the idea" baselines (triangle fit, Gaussian-process fill). MEASURED_SOFTWARE on 176 NHTSA tests (mostly high-speed barrier tests; not representative of all real crashes).

Everything here is a function of one test's sensor window and fixed constants (clip level 0.7 of the range, release fraction 0.1, admission factor 2.0 for the upper bound); nothing is fitted across tests.
"""
from __future__ import annotations

import pickle
import warnings

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import saturation_splits as SP
from crashguard import severity as S
from crashguard import severity_study as SS

RANGES = SP.RANGES
FS = float(C.FS_HZ)
FAMS4 = ("half_sine", "haversine", "triangle", "trapezoid")
CLIP_LEVEL = 0.7  # share of the range at which a sample counts as clipped (the level of the earlier study)
ADMIT = 2.0  # upper bound: grid points with cost at most this multiple of the minimum cost
ADMIT_FLOOR = 1e-6
MAX_ADMITTED = 60  # per family; the points with the largest amplitude x duration are kept (a stated approximation)
CACHE = C.PROCESSED / "v2_clip_features.pkl"
PARAMS = SP.sp_params(0.1)


def shape4(family: str, u: np.ndarray) -> np.ndarray:
    if family != "trapezoid":
        return SAT.shape(family, u)
    u = np.asarray(u, dtype=np.float64)
    inside = (u >= 0.0) & (u <= 1.0)
    uc = np.clip(u, 0.0, 1.0)
    return np.where(inside, np.minimum(1.0, np.minimum(4.0 * uc, 4.0 * (1.0 - uc))), 0.0)


def grid_fit(h: np.ndarray, start: int, end: int, sat: np.ndarray, family: str, range_g: float) -> list[tuple[float, float, float, float]] | None:
    """All grid points (amplitude, offset in samples, duration in s, cost) of the pulse-fit search of ``saturation.fit_pulse`` for one family (same grid, same amplitude rule, same cost)."""
    idx = np.arange(start, end + 1)
    is_sat = sat[idx]
    u_idx, s_idx = idx[~is_sat], idx[is_sat]
    if len(u_idx) < SAT.MIN_UNSAT or len(s_idx) == 0:
        return None
    hu, hs = h[u_idx], h[s_idx]
    pulse_len = max((end - start) / FS, 2.0 / FS)
    pts = []
    for off in SAT.T0_OFFSETS:
        for sc in SAT.T_SCALES:
            T = sc * pulse_len
            su = shape4(family, ((u_idx - start - off) / FS) / T)
            ss = shape4(family, ((s_idx - start - off) / FS) / T)
            den = float((su * su).sum())
            if den <= 0.0:
                continue
            a = float((hu * su).sum() / den)
            pos = ss > 1e-3
            if pos.any():
                a = max(a, float((hs[pos] / ss[pos]).max()))
            a = min(a, SAT.A_MAX_FACTOR * range_g)
            cost = float(((hu - a * su) ** 2).sum() + (np.maximum(0.0, hs - a * ss) ** 2).sum())
            pts.append((a, off, T, cost))
    return pts or None


def best_point(pts: list) -> tuple[float, float, float, float]:
    best = None
    for p in pts:  # the tie rule of fit_pulse: a later point must be better by more than 1e-12
        if best is None or p[3] < best[3] - 1e-12:
            best = p
    return best


def dv_of(w: np.ndarray, trig: int) -> float:
    """Resultant delta-V (km/h) of a window with the severity code's baseline removal, pulse end and integration."""
    a = S.remove_baseline(w, trig)
    h = np.hypot(a[:, 0], a[:, 1])
    e = S.pulse_end(h, trig, FS, PARAMS)
    if e <= trig:
        return 0.0
    dvx, dvy = S.trapz_total(a[trig : e + 1, :2] * C.G0, 1.0 / FS)
    return float(np.hypot(dvx, dvy) * 3.6)


def fill_target(w: np.ndarray, a: np.ndarray, h: np.ndarray, sat_idx: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Window with the clipped samples raised to ``target`` (resultant), direction kept; never lowered."""
    out = w.copy()
    for i, tg in zip(sat_idx, target):
        if h[i] > 0.0 and tg > h[i]:
            out[i, :2] += (tg / h[i] - 1.0) * a[i, :2]
    return out


def _gp_target(h: np.ndarray, s0: int, e: int, sat: np.ndarray, sat_idx: np.ndarray, range_g: float) -> np.ndarray | None:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel

    idx = np.arange(s0, e + 1)
    u_idx = idx[~sat[idx]]
    if len(u_idx) < SAT.MIN_UNSAT:
        return None
    t = ((u_idx - s0) / FS)[:, None]
    k = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(0.03, (0.01, 0.2)) + WhiteKernel(1e-3, (1e-6, 1.0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        gp = GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=0, random_state=C.SEED).fit(t, h[u_idx])
        mu = gp.predict(((sat_idx - s0) / FS)[:, None])
    return np.minimum(np.maximum(mu, h[sat_idx]), SAT.A_MAX_FACTOR * range_g)


def features_one(sig: dict, rg: float) -> dict:
    y = SS.sensor_signal(sig, rg, FS)
    w, trig = SS._window(y, FS)
    a = S.remove_baseline(w, trig)
    h = np.hypot(a[:, 0], a[:, 1])
    s0 = int(trig)
    e = S.pulse_end(h, s0, FS, PARAMS)
    dv_plain = dv_of(w, s0)
    sat = (np.abs(w[:, 0]) >= CLIP_LEVEL * rg) | (np.abs(w[:, 1]) >= CLIP_LEVEL * rg)
    sat_full = np.zeros(len(w), bool)
    sat_full[s0 : e + 1] = sat[s0 : e + 1]
    sat_idx = np.flatnonzero(sat_full)
    n_pulse = max(e - s0 + 1, 1)
    n_sat = len(sat_idx)
    f: dict = dict(range_g=rg, dv_plain=dv_plain, pulse_ms=(e - s0) / FS * 1000.0, n_sat=n_sat, clip_frac=n_sat / n_pulse, saturated=int(n_sat > 0))
    level = CLIP_LEVEL * rg
    if n_sat:
        j0, j1 = int(sat_idx[0]), int(sat_idx[-1])
        runs = 1 + int((np.diff(sat_idx) > 1).sum())
        k0 = max(j0 - 3, s0)
        k1 = min(j1 + 3, e)
        f.update(clip_ms=n_sat / FS * 1000.0, n_runs=runs, slope_in=(h[j0] - h[k0]) / max((j0 - k0) / FS, 1.0 / FS), slope_out=(h[k1] - h[j1]) / max((k1 - j1) / FS, 1.0 / FS),
                 rise_ms=(j0 - s0) / FS * 1000.0, area_unclipped=float(h[s0 : e + 1][~sat_full[s0 : e + 1]].sum() / FS), area_clip=float(n_sat * level / FS))
    else:
        f.update(clip_ms=0.0, n_runs=0, slope_in=0.0, slope_out=0.0, rise_ms=0.0, area_unclipped=float(h[s0 : e + 1].sum() / FS), area_clip=0.0)
    for fam in FAMS4:
        f[f"dv_{fam}"], f[f"cost_{fam}"], f[f"applied_{fam}"], f[f"dvmax_{fam}"] = dv_plain, 0.0, 0, dv_plain
    f.update(dv_gp=dv_plain, gp_applied=0, upper_fallback=0)
    upper = dv_plain
    any_fit = False
    for fam in FAMS4:
        pts = grid_fit(h, s0, e, sat_full, fam, rg) if n_sat else None
        if pts is None:
            continue
        any_fit = True
        a_, off, T, cost = best_point(pts)
        tg = np.maximum(h[sat_idx], a_ * shape4(fam, ((sat_idx - s0 - off) / FS) / T))
        f[f"dv_{fam}"], f[f"cost_{fam}"], f[f"applied_{fam}"] = dv_of(fill_target(w, a, h, sat_idx, tg), s0), cost, 1
        cmin = min(p[3] for p in pts)
        adm = [p for p in pts if p[3] <= max(ADMIT * cmin, cmin + ADMIT_FLOOR)]
        adm = sorted(adm, key=lambda p: -p[0] * p[2])[:MAX_ADMITTED]
        best = 0.0
        for a2, off2, T2, _c in adm:
            tg2 = np.maximum(h[sat_idx], a2 * shape4(fam, ((sat_idx - s0 - off2) / FS) / T2))
            best = max(best, dv_of(fill_target(w, a, h, sat_idx, tg2), s0))
        f[f"dvmax_{fam}"] = best
        upper = max(upper, best)
    if n_sat and not any_fit:  # no family could be fitted (fewer than 3 unclipped pulse samples): amplitude capped at 12 x range over the clipped samples
        add = (SAT.A_MAX_FACTOR * rg - level) * C.G0 * (n_sat / FS) * 3.6
        upper = dv_plain + add
        f["upper_fallback"] = 1
    f["dv_upper"] = upper
    if n_sat:
        tg = _gp_target(h, s0, e, sat_full, sat_idx, rg)
        if tg is not None:
            f["dv_gp"], f["gp_applied"] = dv_of(fill_target(w, a, h, sat_idx, tg), s0), 1
    dvs = np.array([f[f"dv_{fam}"] for fam in FAMS4])
    costs = np.array([f[f"cost_{fam}"] for fam in FAMS4])
    app = np.array([f[f"applied_{fam}"] for fam in FAMS4], bool)
    if app.any():
        d = dvs[app]
        c = costs[app]
        wgt = np.exp(-c / (np.median(c) + 1e-6))
        f.update(dv_mean=float(d.mean()), dv_median=float(np.median(d)), dv_best=float(d[np.argmin(c)]), dv_wmean=float((wgt * d).sum() / wgt.sum()), disagree=float(np.log(np.maximum(d, 1e-6)).std()))
    else:
        f.update(dv_mean=dv_plain, dv_median=dv_plain, dv_best=dv_plain, dv_wmean=dv_plain, disagree=0.0)
    return f


def build(force: bool = False) -> pd.DataFrame:
    """One row per (test, range): meta columns, reference delta-V, and every feature above. Cached."""
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    rows = []
    for i, t in enumerate(tests):
        for rg in RANGES:
            r = features_one(t["sig"], rg)
            r.update(test_idx=i, test_no=int(t["test_no"]), kind=t["kind"], ref=float(t["ref_dv"]), group_mm=meta.group_mm[i], group=meta.group[i])
            rows.append(r)
    df = pd.DataFrame(rows)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(df))
    return df


if __name__ == "__main__":
    d = build(force=True)
    print(d.groupby("range_g")[["saturated", "dv_plain", "dv_upper", "ref"]].mean())
