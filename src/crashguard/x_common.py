"""Shared pieces of the Block 4 / 4b studies on the 176 NHTSA tests (docs/02_preregistration/PREREGISTRATION_V3.md).

``oof`` returns (and caches in data/processed/x_oof.pkl) the out-of-fold delta-V estimates of every method of Study A and of the lower-bound-anchored estimator (X6), on splits R (10 repeats), G, A and O,
at +-16, +-32 and +-64 g and 100 Hz. Everything fitted uses the training tests of its fold only; the combination (release fraction, family, level) is chosen on the training tests of the fold
(``saturation_splits.choose_combo`` for R, ``fixed_combo`` for G, A, O), exactly as in Study A. The only addition is the anchored estimator:
    dv_anchored = dv_plain x exp(max(0, g(x))),   g fitted on y+ = max(0, log(reference / dv_plain))
with g a gradient-boosting regression (the settings of Study A) on the Study A feature set; the output is clipped at zero from below, so the estimate cannot fall below the plain estimate.
A ridge variant of g is also kept (EXPLORATORY).
"""
from __future__ import annotations

import pickle

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge

from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard import v2_a_study as VA

CACHE = C.PROCESSED / "x_oof.pkl"
METHODS = VA.METHODS + ("ANC", "ANCR")
RANGES = SP.RANGES
GB = VA.GB


def anchored(cx: VA.Ctx, tr: np.ndarray, te: np.ndarray, rg: float, combo: dict) -> tuple[np.ndarray, np.ndarray]:
    """(GB-anchored, ridge-anchored) delta-V estimates for the rows ``te``."""
    fam, sf, rf = combo["M"]
    plain = cx.cells[("b", rg, combo["B"])]
    X = cx.X(rg, combo)
    y = np.maximum(0.0, np.log(cx.ref / np.maximum(plain, 1e-6)))
    g = GradientBoostingRegressor(loss="squared_error", **GB).fit(X[tr], y[tr])
    mu, sd = X[tr].mean(0), np.where(X[tr].std(0) > 1e-9, X[tr].std(0), 1.0)
    a = VA._logo_alpha(X[tr], y[tr], cx.gmm[tr], plain[tr], cx.ref[tr], np.ones(int(tr.sum()), bool)) if tr.sum() >= 8 else 1.0
    r = Ridge(alpha=a).fit((X[tr] - mu) / sd, y[tr])
    f1 = np.exp(np.maximum(0.0, g.predict(X[te])))
    f2 = np.exp(np.maximum(0.0, r.predict((X[te] - mu) / sd)))
    return plain[te] * f1, plain[te] * f2


def compute() -> dict:
    cx = VA.Ctx()
    n = cx.n
    held_G = np.array([t["role"] == "heldout" for t in cx.tests])
    held = {"O": SP.split_O(cx.meta), "G": held_G, "A": SP.split_by(cx.meta, "group_mm")}
    combo_fixed = SP.fixed_combo(cx.cells, cx.meta, ~held_G)
    out: dict = {"held": held, "n": n, "plain16": {}}
    for sp, h in held.items():
        out[sp] = {}
        for rg in RANGES:
            est, _ = VA.point_estimates(cx, ~h, h, rg, combo_fixed, "test")
            est["ANC"], est["ANCR"] = anchored(cx, ~h, h, rg, combo_fixed)
            out[sp][rg] = est
            print(sp, rg, flush=True)
    REP, NF = SP.N_REPEATS, SP.N_FOLDS
    ug = sorted(set(cx.gmm.tolist()))
    out["R"] = {rg: {m: np.zeros((REP, n)) for m in METHODS} for rg in RANGES}
    for rep in range(REP):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fold_of = {ug[j]: k % NF for k, j in enumerate(order)}
        fold = np.array([fold_of[g] for g in cx.gmm])
        for f in range(NF):
            te, tr = fold == f, fold != f
            combo = SP.choose_combo(cx.cells, cx.meta, tr)
            for rg in RANGES:
                est, _ = VA.point_estimates(cx, tr, te, rg, combo, "group")
                est["ANC"], est["ANCR"] = anchored(cx, tr, te, rg, combo)
                for m in METHODS:
                    out["R"][rg][m][rep, te] = est[m]
        print("R repeat", rep, flush=True)
    out["ref"] = cx.ref
    out["gmm"] = cx.gmm
    out["group"] = cx.meta.group.to_numpy()
    out["kind"] = cx.meta.kind.to_numpy()
    out["v"] = cx.meta.v.to_numpy()
    out["test_no"] = cx.meta.test_no.to_numpy()
    for rg in RANGES:
        out["plain16"][rg] = cx.cells[("b", rg, SP.RF0)]
    return out


def oof(force: bool = False) -> dict:
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    d = compute()
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(d))
    return d


if __name__ == "__main__":
    d = oof(force=True)
    e = np.abs(100 * (d["R"][16.0]["ANC"] - d["ref"]) / d["ref"])
    print("R 16 g anchored median/p90", np.median(e), np.quantile(e, 0.9))
