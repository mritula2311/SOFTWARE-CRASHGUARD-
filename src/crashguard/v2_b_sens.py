"""Study B5 (docs/02_preregistration/PREREGISTRATION_V2.md section 3, EXPLORATORY): one-at-a-time sweeps of the controller step, the bucket size and rate, the demotion k and the beacon period on the ten burst cells, each against its
matched fixed baseline, 40 seeds. SIMULATED; every value is an assumption of ``sct_sim``. Prefix ``v2.b.sens.``."""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import v2_b_study as VB
from crashguard import v2_pools as VP
from crashguard.sct_sim import SctParams
from crashguard.v2_common import Entries

GRID = {"V1": [dict(g=g) for g in (0.02, 0.05, 0.10)], "V2": [dict(b=b, r=r) for b in (1.0, 2.0) for r in (0.5, 1.0, 2.0, 4.0)], "V3": [dict(period_s=p) for p in (60.0, 120.0, 300.0)], "V5": [dict(k=k) for k in (1, 2, 3)]}


def main() -> None:
    workers = min(14, os.cpu_count() or 1)
    params = SctParams(h_s=float(VB.RES["s11.tuned.h_s"]), rho_f=float(VB.RES["s11.tuned.rho_f"]), sf_raise=bool(VB.RES["s11.tuned.sf_raise"]))
    pools = VP.default_pools()
    cl = [c for c in VB.cells() if c["group"] == "burst"]
    variants = {f"{v}:" + ",".join(f"{k}={x}" for k, x in par.items()): VB.dyn_of(v, par) for v, grid in GRID.items() for par in grid}
    R = VB.run_phase(cl, variants, VB.EVAL_SEED, VB.EVAL_HOURS, pools, params, "sens", workers, with_refs=False)
    R.to_csv(C.TABLES / "v2_b_sens_runs.csv", index=False)
    ent = Entries("v2.b.sens", "results/tables/v2_b_sens_runs.csv", "SIMULATED")
    rows = []
    for nm in variants:
        gains = []
        n_pos = 0
        for c in cl:
            g, dr, n = VB.gain_stats(R, c["name"], f"M[{nm}]", nm, "reach10_critical")
            gains.append(g)
            n_pos += int(np.nanquantile(dr, 0.025) > 0)
        key = nm.replace(":", ".").replace(",", ".").replace("=", "")
        ent.add(f"{key}.mean_gain_burst_cells", round(float(np.nanmean(gains)), 5), "fraction", "EXPLORATORY; critical reach within 10 s, variant minus matched baseline, mean over the 10 burst cells")
        ent.add(f"{key}.cells_with_interval_above_zero", n_pos, "cells", "EXPLORATORY; of 10")
        ent.add(f"{key}.max_cell_gain", round(float(np.nanmax(gains)), 5), "fraction", "EXPLORATORY")
        rows.append(dict(setting=nm, mean_gain=float(np.nanmean(gains)), max_cell_gain=float(np.nanmax(gains)), cells_above_zero=n_pos))
    ent.add("duty.runs_exceeding_limit", int(R.duty_exceeded.sum()), "runs", "independent scan; must be 0")
    ent.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "v2_b_sens.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string())


if __name__ == "__main__":
    main()
