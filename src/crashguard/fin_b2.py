"""B2 (SIMULATED): do flash and hold, applied to the severity table (P1+), carry the gain? Design and hypothesis: docs/02_preregistration/PREREGISTRATION_V5.md section B2 (committed before this ran).
DESIGN = the existing UA-SCT scenario grid at +-16 g (seeds 3000 + h); HELD-OUT = 12 new cells (seeds 5000 + h). Revised after the negative: reported next to the original P0 to P4 results."""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import fin_sim as FS
from crashguard import s11_sct as S
from crashguard.fin_common import Entries

POLS = ("P0", "P1", "P1e", "P1+", "P1+e", "P3")
METS = ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "node_air_share", "fast_air_share_of_allowance", "escalation_used", "escalation", "mis_triage", "delivered_normal", "duty_exceeded", "max_window_airtime_s")
COMPARE = (("P0", "P1+"), ("P1", "P1+"), ("P1e", "P1+e"), ("P3", "P1+e"), ("P0", "P1"), ("P1+", "P3"))
HO_CELLS = [(n, p, b) for n in (75, 150) for p in (0.1, 0.3, 0.5) for b in (20, 45)]
SRC = "results/tables/f_b2.csv"


def design_jobs(pools, t, seeds=30):
    jobs = []
    for mode, scen in (("steady", S.STEADY), ("burst", S.BURST)):
        for name, kw in scen:
            for pol in POLS:
                for h in range(seeds):
                    jobs.append((FS.make_cfg(pol, 16.0, kw, mode == "burst", 3000, h, pools, t, f"{mode}_{name}"), dict(grid="design", cell=f"{mode}_{name}", mode=mode, pol=pol, hour=h)))
    return jobs


def heldout_jobs(pools, t, seeds=30):
    jobs = []
    for n, p, b in HO_CELLS:
        kw = dict(n=n, p_up=p, p_down=p, sf=8, burst_cars=b)
        for pol in POLS:
            for h in range(seeds):
                jobs.append((FS.make_cfg(pol, 16.0, kw, True, 5000, h, pools, t, f"ho_{n}_{p}_{b}"), dict(grid="heldout", cell=f"n{n}_p{int(p * 100)}_b{b}", mode="burst", pol=pol, hour=h)))
    return jobs


def summarise(R: pd.DataFrame, E: Entries, grid: str) -> None:
    sub = R[R.grid == grid]
    cells = sorted(sub.cell.unique())
    for cell in cells:
        for pol in POLS:
            g = sub[(sub.cell == cell) & (sub.pol == pol)]
            for m in METS:
                v = g[m].dropna().to_numpy(float) if m in g else np.array([])
                if len(v):
                    pt, lo, hi = B.ci(v, np.mean)
                    E.add(f"{grid}.cell.{cell}.{pol}.{m}", round(pt, 5), "fraction" if "lat" not in m else "s", "SIMULATED", "mean over 30 paired seeds; interval in the next two keys")
                    E.add(f"{grid}.cell.{cell}.{pol}.{m}_lo", round(lo, 5), "fraction", "SIMULATED", "95% bootstrap interval over seeds")
                    E.add(f"{grid}.cell.{cell}.{pol}.{m}_hi", round(hi, 5), "fraction", "SIMULATED", "95% bootstrap interval over seeds")
    for a, b in COMPARE:
        for met in ("reach10_critical", "reach30_critical", "node_air_share", "escalation_used"):
            st = [FS.cell_pair(sub, dict(cell=c), a, b, met) for c in cells]
            for c, s in zip(cells, st):
                for k in ("pt", "lo", "hi"):
                    E.add(f"{grid}.diff.{b}_minus_{a}.{met}.{c}.{k}", round(s[k], 5) if s[k] == s[k] else None, "fraction", "SIMULATED", f"{b} minus {a}, paired over seeds")
            E.add(f"{grid}.diff.{b}_minus_{a}.{met}.n_cells_gain5", int(sum(FS.gains(s) for s in st)), "cells", "SIMULATED", "cells with point difference >= 0.05 and interval above zero")
            E.add(f"{grid}.diff.{b}_minus_{a}.{met}.n_cells_lose2", int(sum(FS.loses(s) for s in st)), "cells", "SIMULATED", "cells with point difference below -0.02")
            E.add(f"{grid}.diff.{b}_minus_{a}.{met}.n_cells", len(cells), "cells", "SIMULATED", "")


def main() -> None:
    pools = FS.lowered_pools(16.0)
    t = FS.tuned()
    R = FS.run_jobs(design_jobs(pools, t) + heldout_jobs(pools, t))
    R.to_csv(C.TABLES / "f_b2.csv", index=False)
    E = Entries("f.b2", SRC)
    E.add("origin_note", "revised after the negative: P1+ was defined after the ablation and N28 negatives", "text", "SIMULATED", "docs/02_preregistration/PREREGISTRATION_V5.md B2")
    E.add("runs", int(len(R)), "runs", "SIMULATED", "all runs of B2")
    E.add("runs_exceeding_duty", int(R.duty_exceeded.sum()), "runs", "SIMULATED", "independent scan of logged transmissions; must be 0")
    E.add("p1plus.h_s", FS.tuned()["h_s"], "s", "SIMULATED", "stored tuned Severe hold (not re-tuned)")
    summarise(R, E, "design")
    summarise(R, E, "heldout")
    ho = R[R.grid == "heldout"]
    cells = [dict(cell=c) for c in sorted(ho.cell.unique())]
    v = FS.verdict_cells(ho, cells, "P0", "P1+", "reach10_critical")
    E.add("hB2.n_cells", v["n_cells"], "cells", "SIMULATED")
    E.add("hB2.n_cells_gain5", v["n_gain"], "cells", "SIMULATED", "P1+ minus P0 >= 0.05, interval above zero")
    E.add("hB2.n_cells_lose2", v["n_lose"], "cells", "SIMULATED", "P1+ minus P0 below -0.02")
    E.add("hB2.criterion_met", int(v["met"]), "flag", "SIMULATED", "at least 60% of cells gain and none loses by more than 2 points")
    E.add("hB2.p_raw", round(v["p"], 4), "p", "SIMULATED", "rule 5 of the preregistration")
    E.write()
    pd.set_option("display.width", 220)
    for grid in ("design", "heldout"):
        s = R[R.grid == grid].groupby(["cell", "pol"])["reach10_critical"].mean().unstack().round(3)
        print(grid, "\n", s[list(POLS)].to_string())
    print("H-B2", {k: v[k] for k in ("n_cells", "n_gain", "n_lose", "met", "p")}, "duty exceeded", int(R.duty_exceeded.sum()), "of", len(R))


if __name__ == "__main__":
    main()
