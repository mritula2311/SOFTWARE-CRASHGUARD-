"""T8: simulator assumption sweep for the UA-SCT policies (definitions: docs/02_preregistration/PREREGISTRATION.md, Addendum 1, section A1.6, committed before this was run). SIMULATED.

P0 to P4 at +-16 g, one factor at a time from the default (100 cars, SF7, heartbeat 600 s, 16 bytes, 10% loss, capture 6 dB, burst 30, duty 1%): capture none; burst 10 and 60; heartbeat payload 26 bytes;
cars 50 and 200; SF9; loss 0%, 20%, 40%, 60%; duty 0.1%. Steady and burst cells where the factor applies; 40 paired seeds. "P3 beats P1 (or P2)" in a cell for a metric only if the whole paired 95%
interval is on the favourable side (reach within 10 s or 30 s: above zero; mis-triage: below zero). Every value is an ASSUMPTION of ``sct_sim``; the duty limit is NOT verified for India.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import s11_sct as S

SRC = "results/tables/t8_sweep.csv"
SETTINGS = [("base", {}, ("steady", "burst")), ("capture_none", dict(capture="none"), ("steady", "burst")), ("burst10", dict(burst_cars=10), ("burst",)), ("burst60", dict(burst_cars=60), ("burst",)),
            ("hbpayload26", dict(hb_bytes=26), ("steady", "burst")), ("cars50", dict(n=50), ("steady", "burst")), ("cars200", dict(n=200), ("steady", "burst")), ("sf9", dict(sf=9), ("steady", "burst")),
            ("loss0", dict(p_up=0.0, p_down=0.0), ("steady", "burst")), ("loss20", dict(p_up=0.2, p_down=0.2), ("steady", "burst")), ("loss40", dict(p_up=0.4, p_down=0.4), ("steady", "burst")),
            ("loss60", dict(p_up=0.6, p_down=0.6), ("steady", "burst")), ("duty0p1", dict(duty=0.001), ("steady", "burst"))]
METRICS = ("mis_triage", "reach10_critical", "reach30_critical", "p95_lat_s_critical", "node_air_share", "delivered_normal", "escalation")


def main() -> None:
    from crashguard.results import record_many
    from crashguard.sct_sim import SctParams

    r = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    params = SctParams(h_s=float(r["s11.tuned.h_s"]), rho_f=float(r["s11.tuned.rho_f"]), sf_raise=bool(r["s11.tuned.sf_raise"]))
    phi = float(r["s11.tuned.phi"])
    pools = S.load_pools()
    jobs = []
    for name, kw, modes in SETTINGS:
        for mode in modes:
            for pol in S.POLICIES:
                for h in range(S.EVAL_HOURS):
                    cfg = S.make_cfg(pol, 16.0, kw, mode == "burst", S.EVAL_SEED, h, pools, params, phi, f"t8_{mode}_{name}")
                    cfg.capture = kw.get("capture", "db6")
                    jobs.append((cfg, dict(setting=name, mode=mode, pol=pol)))
    R = S.run_jobs(jobs, min(14, os.cpu_count() or 1))
    R.to_csv(C.TABLES / "t8_sweep.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"t8.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("seeds_per_cell", S.EVAL_HOURS, "seeds", "paired scenario seeds")
    add("runs", int(len(R)), "runs", "")
    add("duty.runs_exceeding_limit", int(R.duty_exceeded.sum()), "runs", "independent scan of the logged transmissions; must be 0")
    cnt: dict = {}
    where: dict = {}
    for (setting, mode), g in R.groupby(["setting", "mode"]):
        for pol in S.POLICIES:
            for met in METRICS:
                v = g[g.pol == pol][met].dropna().to_numpy(float)
                if len(v):
                    p = B.ci(v, np.mean)
                    u = "s" if "lat" in met else "fraction"
                    add(f"cell.{mode}.{setting}.{pol}.{met}", round(p[0], 5), u, "mean over seeds")
                    add(f"cell.{mode}.{setting}.{pol}.{met}_lo", round(p[1], 5), u, "95% bootstrap interval")
                    add(f"cell.{mode}.{setting}.{pol}.{met}_hi", round(p[2], 5), u, "95% bootstrap interval")
        for base in ("P1", "P2"):
            for met in ("reach10_critical", "reach30_critical", "mis_triage"):
                a = g[g.pol == base].sort_values("hour")[met].to_numpy(float)
                b = g[g.pol == "P3"].sort_values("hour")[met].to_numpy(float)
                m = ~(np.isnan(a) | np.isnan(b))
                if m.sum() < 3:
                    continue
                if np.allclose(a[m], b[m]):
                    d = (0.0, 0.0, 0.0)
                else:
                    d = B.paired_diff(a[m], b[m], np.mean)
                t = f"diff.{mode}.{setting}.P3_minus_{base}.{met}"
                add(t, round(d[0], 5), "fraction", f"paired seed-mean difference, P3 minus {base}")
                add(t + "_lo", round(d[1], 5), "fraction", "95% bootstrap interval")
                add(t + "_hi", round(d[2], 5), "fraction", "95% bootstrap interval")
                good = d[2] < 0 if met == "mis_triage" else d[1] > 0
                bad = d[1] > 0 if met == "mis_triage" else d[2] < 0
                k = (base, met)
                cnt.setdefault(k, dict(beats=0, tie=0, loses=0))
                cnt[k]["beats" if good else "loses" if bad else "tie"] += 1
                if not good:
                    where.setdefault(k, []).append(f"{mode}:{setting}")
    for (base, met), c in cnt.items():
        for kk, v in c.items():
            add(f"count.P3_vs_{base}.{met}.n_{kk}", int(v), "cells", "cells in which the whole paired interval of P3 against the baseline is on the favourable side (beats), contains zero (tie) or is on the unfavourable side (loses)")
        add(f"count.P3_vs_{base}.{met}.n_cells", int(sum(c.values())), "cells", "steady and burst cells of the sweep")
        add(f"count.P3_vs_{base}.{met}.cells_not_beating", ",".join(where.get((base, met), [])) or "none", "text", "cells where P3 does not beat the baseline on this metric")
    pd.DataFrame([dict(name=e["name"], value=e["value"]) for e in ent]).to_csv(C.TABLES / "t8_sweep_keys.csv", index=False)
    record_many(ent, purge_prefixes=("t8.",))
    g = {e["name"]: e["value"] for e in ent}
    for base in ("P1", "P2"):
        for met in ("reach10_critical", "reach30_critical", "mis_triage"):
            print(base, met, {k: g[f"t8.count.P3_vs_{base}.{met}.n_{k}"] for k in ("beats", "tie", "loses", "cells")}, g[f"t8.count.P3_vs_{base}.{met}.cells_not_beating"][:160])
    print("duty exceeded:", g["t8.duty.runs_exceeding_limit"], "of", g["t8.runs"])


if __name__ == "__main__":
    main()
