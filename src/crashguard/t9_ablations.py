"""T9: ablations of the SCT components (EXPLORATORY; not part of the preregistered hypotheses). SIMULATED.

One component removed at a time from the fast path: flash, no-hold (every class waits its full cancel window), quick retries (0.3 s spacing instead of 5 s and 10 s), reserved duty share, spreading-factor raise,
authenticated CANCEL. P2 (point class) and P3 (upper-end class) at +-16 g in six cells: steady, burst of 30, burst of 60, burst at SF9, burst with 30% loss, and steady with false alarms at the 5% target
(where CANCEL matters). Effect on critical reach within 10 s and 30 s, critical 95th-percentile latency (delivered alerts only), airtime and duty use, paired by seed with the full SCT. 40 seeds.
Every value is an ASSUMPTION of ``sct_sim``; the duty limit (1%) is NOT verified for India.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import s11_sct as S
from crashguard.sct_sim import SctParams

SRC = "results/tables/t9_ablations.csv"
CELLS = [("steady_base", {}, False), ("burst_base", {}, True), ("burst_b60", dict(burst_cars=60), True), ("burst_sf9", dict(sf=9), True), ("burst_loss30", dict(p_up=0.3, p_down=0.3), True),
         ("steady_fa5", dict(fa_per_car_h=0.25), False)]
VARIANTS = {"full": {}, "no_flash": dict(flash=False), "no_hold": dict(sev_hold=False), "quick_retries": dict(spacing_crit=0.3, spacing_sev=0.3), "no_reserve": dict(reserve=False),
            "no_sf_raise": dict(sf_raise=False), "no_cancel_msg": dict(cancel_msg=False)}
METRICS = ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "node_air_share", "fast_air_share_of_allowance", "cancel_tx", "fa_tx_fast", "max_window_airtime_s", "delivered_normal")


def main() -> None:
    from crashguard.results import record_many

    r = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    params = SctParams(h_s=float(r["s11.tuned.h_s"]), rho_f=float(r["s11.tuned.rho_f"]), sf_raise=bool(r["s11.tuned.sf_raise"]))
    pools = S.load_pools()
    jobs = []
    for cell, kw, burst in CELLS:
        for pol in ("P2", "P3"):
            for vn, ov in VARIANTS.items():
                sct = SctParams(**{**params.__dict__, **ov})
                for h in range(S.EVAL_HOURS):
                    jobs.append((S.make_cfg(pol, 16.0, kw, burst, S.EVAL_SEED, h, pools, sct, None, f"t9_{cell}"), dict(cell=cell, pol=pol, variant=vn)))
    R = S.run_jobs(jobs, min(14, os.cpu_count() or 1))
    R.to_csv(C.TABLES / "t9_ablations.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"t9.{name}", value=value, unit=unit, origin="SIMULATED", source_file=SRC, notes="EXPLORATORY; " + notes))

    add("seeds_per_cell", S.EVAL_HOURS, "seeds", "paired scenario seeds")
    add("duty.runs_exceeding_limit", int(R.duty_exceeded.sum()), "runs", "independent scan; must be 0")
    effect: dict = {}
    for (cell, pol, vn), g in R.groupby(["cell", "pol", "variant"]):
        for met in METRICS:
            v = g[met].dropna().to_numpy(float) if met in g else np.array([])
            if len(v):
                p = B.ci(v, np.mean)
                u = "s" if "lat" in met else "fraction"
                add(f"{cell}.{pol}.{vn}.{met}", round(p[0], 5), u, "mean over seeds")
                add(f"{cell}.{pol}.{vn}.{met}_lo", round(p[1], 5), u, "95% bootstrap interval")
                add(f"{cell}.{pol}.{vn}.{met}_hi", round(p[2], 5), u, "95% bootstrap interval")
        if vn == "full":
            continue
        full = R[(R.cell == cell) & (R.pol == pol) & (R.variant == "full")].sort_values("hour")
        this = g.sort_values("hour")
        for met in METRICS:
            if met not in g:
                continue
            a, b = full[met].to_numpy(float), this[met].to_numpy(float)
            m = ~(np.isnan(a) | np.isnan(b))
            if m.sum() < 3:
                continue
            d = (0.0, 0.0, 0.0) if np.allclose(a[m], b[m]) else B.paired_diff(a[m], b[m], np.mean)
            u = "s" if "lat" in met else "fraction"
            t = f"diff.{cell}.{pol}.{vn}_minus_full.{met}"
            add(t, round(d[0], 5), u, f"component removed minus full SCT, paired by seed ({vn})")
            add(t + "_lo", round(d[1], 5), u, "95% bootstrap interval")
            add(t + "_hi", round(d[2], 5), u, "95% bootstrap interval")
            if met == "reach10_critical":
                effect.setdefault((pol, vn), []).append("helps" if d[2] < 0 else "hurts" if d[1] > 0 else "none")
    for (pol, vn), lst in effect.items():
        for k in ("helps", "hurts", "none"):
            add(f"summary.{pol}.{vn}.n_cells_component_{k}", int(sum(x == k for x in lst)), "cells", "cells in which removing the component lowers (helps = the component helps), raises (hurts) or does not change critical reach within 10 s beyond the interval")
    pd.DataFrame([dict(name=e["name"], value=e["value"]) for e in ent]).to_csv(C.TABLES / "t9_ablations_keys.csv", index=False)
    record_many(ent, purge_prefixes=("t9.",))
    g = {e["name"]: e["value"] for e in ent}
    for pol in ("P2", "P3"):
        for vn in VARIANTS:
            if vn != "full":
                print(pol, vn, {k: g[f"t9.summary.{pol}.{vn}.n_cells_component_{k}"] for k in ("helps", "hurts", "none")}, "burst_base reach10 diff", g.get(f"t9.diff.burst_base.{pol}.{vn}_minus_full.reach10_critical"))


if __name__ == "__main__":
    main()
