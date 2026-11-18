"""S13: the spaced-retry severity table (P1b) as the baseline for SCT (plan and decision rule: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S13, written before this was run). SIMULATED.

P1b = the severity table with exponentially spaced retries (spacing multiplier 2, no jitter, no reserve, no spreading-factor raise: the burst-tuned setting of S5). It is run on the held-out cells of
the UA-SCT study and paired by scenario seed with the stored P1 and P2 runs (``results/tables/s11_sct.csv``).
"""
from __future__ import annotations

import os

import pandas as pd

from crashguard import config as C
from crashguard import s11_sct as S
from crashguard.sct_sim import SctParams

SRC = "results/tables/s13_spaced_table.csv"
P1B = dict(rho=0.0, m=2.0, jitter=0.0, sf_raise=0)


def main() -> None:
    from crashguard.results import record_many

    workers = min(14, os.cpu_count() or 1)
    pools = S.load_pools()
    jobs = []
    for rg in S.RANGES:
        for mode, scen in (("steady", S.STEADY), ("burst", S.BURST)):
            for name, kw in scen:
                for h in range(S.EVAL_HOURS):
                    cfg = S.make_cfg("P1", rg, kw, mode == "burst", S.EVAL_SEED, h, pools, SctParams(), None, f"{mode}_{name}")
                    cfg.policy, cfg.sched = "scheduler", dict(P1B)
                    jobs.append((cfg, dict(range_g=rg, mode=mode, scen=name, pol="P1b")))
    X = S.run_jobs(jobs, workers)
    R = pd.concat([pd.read_csv(C.TABLES / "s11_sct.csv"), X], ignore_index=True)
    X.to_csv(C.TABLES / "s13_spaced_table.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"s13.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("p1b.spacing_multiplier", P1B["m"], "multiplier", "burst-tuned setting of S5; no jitter, no reserve, no spreading-factor raise")
    for rg in S.RANGES:
        for grp, modes in (("steady", ("steady",)), ("burst", ("burst",))):
            cells = [(rg, m, s) for m in modes for s in sorted(set(R[(R.range_g == rg) & (R["mode"] == m)].scen))]
            for a, b in (("P1", "P1b"), ("P1b", "P2"), ("P1b", "P3"), ("P1", "P2")):
                for met in ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "delivered_normal", "node_air_share"):
                    p, lo, hi, n = S.agg_diff(R, met, a, b, cells, ["range_g", "mode", "scen"])
                    if n:
                        t = f"diff.r{rg:g}.{grp}.{b}_minus_{a}.{met}"
                        u = "s" if "lat" in met else "fraction"
                        add(t, round(p, 5), u, f"mean over {n} cells of the paired seed-mean difference")
                        add(t + "_lo", round(lo, 5), u, "95% bootstrap interval (seeds resampled inside each cell)")
                        add(t + "_hi", round(hi, 5), u, "95% bootstrap interval (seeds resampled inside each cell)")
        bb = next(e for e in ent if e["name"] == f"s13.diff.r{rg:g}.burst.P2_minus_P1b.reach10_critical_lo")["value"]
        st = next(e for e in ent if e["name"] == f"s13.diff.r{rg:g}.steady.P2_minus_P1b.reach10_critical_lo")["value"]
        add(f"decision.r{rg:g}.sct_improves_on_spaced_table", int(bb > 0 and st > -0.02), "flag", "decision rule fixed in advance: burst interval of (P2 minus P1b) in reach within 10 s above zero AND steady lower end above -0.02")
    record_many(ent, purge_prefixes=("s13.",))
    g = R[(R["mode"] == "burst") & (R.scen == "base") & (R.range_g == 16.0)].groupby("pol")[["reach10_critical", "reach30_critical", "p95_lat_s_critical", "node_air_share"]].mean().round(3)
    print(g.to_string())
    for rg in S.RANGES:
        print(rg, [e["value"] for e in ent if e["name"].startswith(f"s13.decision.r{rg:g}")], [round(next(e["value"] for e in ent if e["name"] == f"s13.diff.r{rg:g}.burst.P2_minus_P1b.reach10_critical{s}"), 3) for s in ("", "_lo", "_hi")])


if __name__ == "__main__":
    main()
