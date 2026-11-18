"""Class pools for the v2 simulator studies (docs/02_preregistration/PREREGISTRATION_V2.md section 3): at +-16 g, every cross-validated test row of the UA-SCT folds with its delta-V and ASI estimates, turned into the class
class(dv / s, ASI / s) for a grid of threshold scales s. Entry order is the order of the folds of ``ua_core``. MEASURED_SOFTWARE inputs; the simulations that use them are SIMULATED."""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import s11_sct as S11
from crashguard import ua_core as U

SCALES = np.round(np.arange(0.30, 1.0001, 0.0125), 4)
RG = 16.0
LOADED_NONSEVERE_REP = 11  # every true Low or Moderate entry is repeated this many times in the loaded pool (about 80% non-severe)


def scale_index(s: float) -> int:
    return int(np.argmin(np.abs(SCALES - s)))


def build(loaded: bool = False) -> dict:
    core = U.build()
    refc = U.ref_classes(core)
    dvs, asis, trues = [], [], []
    for r in core.folds:
        te = r["te"]
        dvs.append(r["dv"][RG][te])
        asis.append(core.asi[RG][te])
        trues.append(refc[te])
    dv, asi, true = np.concatenate(dvs), np.concatenate(asis), np.concatenate(trues)
    pcls = np.stack([U.classes(dv / s, asi / s) for s in SCALES], axis=1).astype(np.int8)
    if loaded:
        reps = np.where(true < 2, LOADED_NONSEVERE_REP, 1)
        idx = np.repeat(np.arange(len(true)), reps)
        pcls, true = pcls[idx], true[idx]
    base = S11.load_pools()
    return dict(true=true.astype(int), pcls=pcls, scales=SCALES, point=pcls[:, scale_index(1.0)].astype(int), crash_t=base["crash_t"], fa_t=base["fa_t"],
                share_nonsevere=float((true < 2).mean()))


def esc_pool(pool: dict, s: float) -> float:
    """Share of true Low or Moderate pool entries whose class at scale s is Severe or Critical."""
    j = scale_index(s)
    m = pool["true"] < 2
    return float((pool["pcls"][m, j] >= 2).mean())


def mis_pool(pool: dict, s: float) -> float:
    j = scale_index(s)
    m = pool["true"] >= 2
    return float((pool["pcls"][m, j] < 2).mean())


def default_pools() -> dict:
    return dict(unloaded=build(False), loaded=build(True))


if __name__ == "__main__":
    p = default_pools()
    for k, v in p.items():
        print(k, len(v["true"]), "non-severe share", round(v["share_nonsevere"], 3), "esc(s0)", round(esc_pool(v, 0.6375), 3), "esc(1)", round(esc_pool(v, 1.0), 3), "mis(s0)", round(mis_pool(v, 0.6375), 3), "mis(1)", round(mis_pool(v, 1.0), 3))
    import pandas as pd  # noqa: F401

    pairs = pd.read_csv(C.TABLES / "ua_pairs.csv")
    g = pairs[(pairs.alpha == 0.10) & (pairs.variant == "cc") & (pairs.range_g == 16.0)]
    print("ua_pairs rows", len(g), "point-class agreement", float((np.sort(g.c_hat.to_numpy()) == np.sort(p["unloaded"]["point"])).mean()))
