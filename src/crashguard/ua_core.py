"""Shared core of the closing-block analyses (T1 to T4, T6, T7): the cross-validation fold records of the UA-SCT class-interval study, computed once and cached, and functions that turn them into classes
and conformal intervals under other thresholds, interval levels and variants. The fold structure, seeds, tuning and calibration split are exactly those of ``ua_conformal`` (docs/02_preregistration/PREREGISTRATION.md section 2 and 3);
``tests/test_closing_block.py`` checks that the baseline reproduces the stored ``ua.*`` numbers.

Classes: maximum of the delta-V class (limits in km/h) and the ASI class (levels in g). MEASURED_SOFTWARE on 176 NHTSA tests; NHTSA tests are mostly high-speed barrier tests and are not
representative of all real crashes; fill + ridge was named primary after earlier results were seen.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard import severity_study as SS
from crashguard import ua_conformal as UA

DV_LIMITS = (24.0, 40.0, 56.0)
ASI_LIMITS = (1.0, 1.4, 1.9)
CACHE = C.PROCESSED / "ua_folds.pkl"
REPEATS = UA.REPEATS


@dataclass
class Core:
    meta: pd.DataFrame
    grp: np.ndarray
    kind: np.ndarray
    ref: np.ndarray
    ref_asi: np.ndarray
    asi: dict  # range -> ASI of the filled window (point value)
    folds: list  # per (repeat, fold): dict(rep, te, cal, dv={range: array over tests, nan outside cal|te})


def classes(dv: np.ndarray, asi: np.ndarray, limits=DV_LIMITS, asi_limits=ASI_LIMITS) -> np.ndarray:
    """Severity class 0 to 3 = max(delta-V class, ASI class); nan delta-V gives -1."""
    dv, asi = np.asarray(dv, float), np.asarray(asi, float)
    c_dv = sum((dv >= lim).astype(int) for lim in limits)
    c_asi = sum((asi > lim).astype(int) for lim in asi_limits)
    out = np.maximum(c_dv, c_asi)
    return np.where(np.isfinite(dv), out, -1)


def build(force: bool = False) -> Core:
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    cells = SP.build_cells(tests)
    tab = pd.read_csv(C.TABLES / "n14_per_test.csv")
    asi = {}
    for rg in SP.RANGES:
        t = tab[tab.range_g == rg].reset_index(drop=True)
        assert np.allclose(t.ref.to_numpy(), meta.ref.to_numpy())
        asi[rg] = t.m_asi.to_numpy(float)
    ref = meta.ref.to_numpy()
    ref_asi = tab[tab.range_g == 16.0].reset_index(drop=True).ref_asi.to_numpy(float)
    grp, _ = UA.merged_groups(tests, meta)
    ug = sorted(set(grp.tolist()))
    n = len(meta)
    folds = []
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
            n_cal = max(1, int(round(UA.CAL_SHARE * len(tr_groups))))
            cal_groups = {tr_groups[i] for i in perm[:n_cal]}
            cal = np.array([g in cal_groups for g in grp]) & trn
            tune = trn & ~cal
            combo = SP.choose_combo(cells, meta, tune)
            want = cal | te
            dv = {}
            for rg in SP.RANGES:
                est, _info = SP.estimates(cells, meta, tune, want, rg, combo, "group")
                a = np.full(n, np.nan)
                a[want] = est["M+"]
                dv[rg] = a
            folds.append(dict(rep=rep, fold=f, te=te, cal=cal, dv=dv))
    core = Core(meta=meta, grp=grp, kind=meta.kind.to_numpy(), ref=ref, ref_asi=ref_asi, asi=asi, folds=folds)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(core))
    return core


def point_classes(core: Core, rg: float, limits=DV_LIMITS, scale: float = 1.0) -> np.ndarray:
    """(REPEATS, n) point class of every test row (the test rows of each fold), -1 elsewhere. ``scale`` divides every limit (delta-V and ASI): scale < 1 lowers the thresholds."""
    n = len(core.meta)
    out = np.full((REPEATS, n), -1, int)
    for r in core.folds:
        c = classes(r["dv"][rg] / scale, core.asi[rg] / scale, limits, ASI_LIMITS)
        out[r["rep"]][r["te"]] = c[r["te"]]
    return out


def ref_classes(core: Core, limits=DV_LIMITS) -> np.ndarray:
    return classes(core.ref, core.ref_asi, limits, ASI_LIMITS)


def interval_classes(core: Core, rg: float, alpha: float, variant: str = "cc", limits=DV_LIMITS, widen: int = 0) -> dict:
    """Class intervals for every test row. variant: 'pooled', 'cc' (per predicted class) or 'kind' (per test kind, frontal or side). ``widen`` adds classes to the upper end (a simple margin)."""
    n = len(core.meta)
    refc = ref_classes(core, limits)
    out = {k: np.full((REPEATS, n), -1, int) for k in ("c_hat", "lo", "hi", "up")}
    for r in core.folds:
        c = classes(r["dv"][rg], core.asi[rg], limits, ASI_LIMITS)
        cal, te = r["cal"], r["te"]
        if variant in ("pooled", "cc"):
            res = UA.intervals(c[cal], refc[cal], c[te], alpha, cond=(variant == "cc"))
            lo, hi, up = res["lo"], res["hi"], res["up"]
        else:  # group-wise calibration by test kind
            lo, hi, up = np.zeros(int(te.sum()), int), np.zeros(int(te.sum()), int), np.zeros(int(te.sum()), int)
            kte = core.kind[te]
            for k in set(core.kind.tolist()):
                mt, mc = kte == k, core.kind[cal] == k
                if mt.any():
                    if mc.sum() >= UA.MIN_CLASS_N:
                        res = UA.intervals(c[cal][mc], refc[cal][mc], c[te][mt], alpha, cond=False)
                    else:
                        res = UA.intervals(c[cal], refc[cal], c[te][mt], alpha, cond=False)
                    lo[mt], hi[mt], up[mt] = res["lo"], res["hi"], res["up"]
        up = np.minimum(3, up + widen)
        hi = np.minimum(3, hi + widen)
        out["c_hat"][r["rep"]][te] = c[te]
        out["lo"][r["rep"]][te], out["hi"][r["rep"]][te], out["up"][r["rep"]][te] = lo, hi, up
    return out


def mis_esc(assigned: np.ndarray, truth: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Row-level indicators: mis-triage (true Severe or Critical assigned below Severe; nan elsewhere) and escalation (true Low or Moderate assigned Severe or Critical; nan elsewhere). (REPEATS, n)."""
    t = np.broadcast_to(truth[None, :], assigned.shape)
    valid = assigned >= 0
    sev = (t >= 2) & valid
    non = (t < 2) & valid
    mis = np.where(sev, (assigned < 2).astype(float), np.nan)
    esc = np.where(non, (assigned >= 2).astype(float), np.nan)
    return mis, esc


def gmean(x: np.ndarray, groups: np.ndarray, n_boot: int = B.N_BOOT):
    """Mean of a (REPEATS, n) array over its non-nan cells with a grouped (make and model) bootstrap 95% interval. Returns (point, lo, hi)."""
    return B.ci_grouped(x.T, groups, lambda z: float(np.nanmean(z)), n_boot)


def auc(points_x: np.ndarray, points_y: np.ndarray) -> float:
    """Area under y(x) over [0, 1] by the trapezoid rule after sorting by x and closing the curve with (0, 1) and (1, 0)."""
    o = np.argsort(points_x, kind="stable")
    x = np.r_[0.0, points_x[o], 1.0]
    y = np.r_[1.0, points_y[o], 0.0]
    return float(np.trapezoid(y, x)) if hasattr(np, "trapezoid") else float(np.trapz(y, x))
