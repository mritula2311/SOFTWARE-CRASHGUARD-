"""T1: equal-escalation comparison (definitions and decision rule: docs/02_preregistration/PREREGISTRATION.md, Addendum 1, section A1.1, committed before this was run).

P1e and P2e use the point estimates of P1 and P2 with every class boundary divided by a factor f chosen per sensor range, on the pooled held-out rows, so that they escalate the same share of true non-severe
events as P3 (class-conditional upper end, alpha 0.10). No simulated outcome is used to choose f. Then P3 is compared with P1e and P2e on the held-out cells and seeds of the UA-SCT study.
MEASURED_SOFTWARE (pool level) and SIMULATED (cells; every channel and timing value is an assumption).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import s11_sct as S
from crashguard import ua_core as U
from crashguard.sct_sim import SctParams

SRC = "results/tables/t1_equal_escalation.csv"
F_GRID = np.round(np.arange(0.30, 1.0001, 0.0025), 4)
TOL = 0.005


def tuned_params() -> SctParams:
    r = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    return SctParams(h_s=float(r["s11.tuned.h_s"]), rho_f=float(r["s11.tuned.rho_f"]), sf_raise=bool(r["s11.tuned.sf_raise"]))


def find_f(core: U.Core, rg: float, target_esc: float) -> tuple[float, float]:
    refc = U.ref_classes(core)
    best = (None, 9.0)
    for f in F_GRID:
        _m, esc = U.mis_esc(U.point_classes(core, rg, scale=float(f)), refc)
        e = float(np.nanmean(esc))
        if abs(e - target_esc) < best[1]:
            best = (float(f), abs(e - target_esc))
    return best


def main() -> None:
    from crashguard.results import record_many

    core = U.build()
    refc = U.ref_classes(core)
    grp = core.grp
    pools = S.load_pools()
    pairs = pd.read_csv(C.TABLES / "ua_pairs.csv")
    pairs = pairs[(pairs.alpha == 0.10) & (pairs.variant == "cc")]
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"t1.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    pools_e = {"classes": {}, "crash_t": pools["crash_t"], "fa_t": pools["fa_t"]}
    fvals = {}
    for rg in S.RANGES:
        iv = U.interval_classes(core, rg, 0.10, "cc")
        up, point = iv["up"], iv["c_hat"]
        mis3, esc3 = U.mis_esc(up, refc)
        e3 = float(np.nanmean(esc3))
        f, gap = find_f(core, rg, e3)
        fvals[rg] = f
        pe = U.point_classes(core, rg, scale=f)
        mis_e, esc_e = U.mis_esc(pe, refc)
        mis1, esc1 = U.mis_esc(point, refc)
        add(f"r{rg:g}.f", f, "factor", "every class boundary divided by this factor; chosen on pool rows so that the escalation equals that of P3 (no simulated outcome used)")
        add(f"r{rg:g}.escalation_p3", round(e3, 4), "fraction", "P3 escalation on the pooled held-out rows")
        add(f"r{rg:g}.escalation_equal", round(float(np.nanmean(esc_e)), 4), "fraction", f"P1e and P2e escalation; gap to P3 {gap:.4f}")
        add(f"r{rg:g}.escalation_p1", round(float(np.nanmean(esc1)), 4), "fraction", "P1 and P2 escalation with the current thresholds")
        for nm, a_, b_ in (("mis_triage_p3_minus_p1e", mis_e, mis3), ("escalation_p3_minus_p1e", esc_e, esc3), ("mis_triage_p3_minus_p1", mis1, mis3)):
            p, lo, hi = B.paired_diff_grouped(a_.T, b_.T, grp, lambda z: float(np.nanmean(z)))
            add(f"r{rg:g}.{nm}", round(p, 4), "fraction", "pool-level paired difference, grouped (make and model) bootstrap, 1,000 resamples")
            add(f"r{rg:g}.{nm}_lo", round(lo, 4), "fraction", "95% grouped bootstrap interval")
            add(f"r{rg:g}.{nm}_hi", round(hi, 4), "fraction", "95% grouped bootstrap interval")
        for nm, arr in (("mis_triage_p1e", mis_e), ("mis_triage_p3", mis3), ("mis_triage_p1", mis1)):
            p, lo, hi = U.gmean(arr, grp)
            add(f"r{rg:g}.{nm}", round(p, 4), "fraction", "mean over severe or critical rows; grouped bootstrap interval")
            add(f"r{rg:g}.{nm}_lo", round(lo, 4), "fraction", "95% grouped bootstrap interval")
            add(f"r{rg:g}.{nm}_hi", round(hi, 4), "fraction", "95% grouped bootstrap interval")
        # class arrays aligned with the pair rows of the simulator pools
        g = pairs[pairs.range_g == rg]
        mask = point >= 0
        assert (point[mask] == g.c_hat.to_numpy()).all() and (up[mask] == g.upper.to_numpy()).all(), "pool rows are not aligned with ua_pairs"
        pools_e["classes"][rg] = dict(true=g.true.to_numpy(int), point=pe[mask].astype(int), upper=up[mask].astype(int))
    # ---- simulation cells for P1e and P2e (same seeds and labels as the main study: paired)
    params = tuned_params()
    jobs = []
    for rg in S.RANGES:
        for mode, scen in (("steady", S.STEADY), ("burst", S.BURST)):
            for name, kw in scen:
                for h in range(S.EVAL_HOURS):
                    for pol, base in (("P1e", "P1"), ("P2e", "P2")):
                        jobs.append((S.make_cfg(base, rg, kw, mode == "burst", S.EVAL_SEED, h, pools_e, params, None, f"{mode}_{name}"), dict(range_g=rg, mode=mode, scen=name, pol=pol)))
    X = S.run_jobs(jobs, min(14, os.cpu_count() or 1))
    X.to_csv(C.TABLES / "t1_equal_escalation.csv", index=False)
    R = pd.concat([pd.read_csv(C.TABLES / "s11_sct.csv"), X], ignore_index=True)
    mets = ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "delivered_normal", "node_air_share", "mis_triage", "escalation")
    for rg in S.RANGES:
        for grp_name, modes in (("steady", ("steady",)), ("burst", ("burst",))):
            cells = [(rg, m, s) for m in modes for s in sorted(set(R[(R.range_g == rg) & (R["mode"] == m)].scen))]
            for a, b in (("P2e", "P3"), ("P1e", "P3"), ("P1", "P1e"), ("P2", "P2e")):
                for met in mets:
                    p, lo, hi, n = S.agg_diff(R, met, a, b, cells, ["range_g", "mode", "scen"])
                    if n:
                        u = "s" if "lat" in met else "fraction"
                        t = f"r{rg:g}.{grp_name}.{b}_minus_{a}.{met}"
                        add(t, round(p, 5), u, f"mean over {n} cells of the paired seed-mean difference ({b} minus {a})", "SIMULATED")
                        add(t + "_lo", round(lo, 5), u, "95% bootstrap interval (seeds resampled inside each cell)", "SIMULATED")
                        add(t + "_hi", round(hi, 5), u, "95% bootstrap interval (seeds resampled inside each cell)", "SIMULATED")
    # decision rule
    val = {e["name"]: e["value"] for e in ent}
    for rg in S.RANGES:
        mis_ok = val[f"t1.r{rg:g}.mis_triage_p3_minus_p1e_hi"] < 0
        st_ok = val[f"t1.r{rg:g}.steady.P3_minus_P2e.reach10_critical_lo"] > -0.02
        bu_ok = val[f"t1.r{rg:g}.burst.P3_minus_P2e.reach10_critical_lo"] > -0.02
        add(f"r{rg:g}.decision.mis_triage_below_zero", int(mis_ok), "flag", "rule (i): the pool-level interval of mis-triage (P3 minus P1e, the same class assignment as P2e) is entirely below zero")
        add(f"r{rg:g}.decision.reach_not_worse_steady", int(st_ok), "flag", "rule (ii), steady cells: lower end of reach within 10 s (P3 minus P2e) above -0.02", "SIMULATED")
        add(f"r{rg:g}.decision.reach_not_worse_burst", int(bu_ok), "flag", "rule (ii), burst cells: lower end of reach within 10 s (P3 minus P2e) above -0.02", "SIMULATED")
        add(f"r{rg:g}.decision.p3_wins_at_equal_escalation", int(mis_ok and st_ok and bu_ok), "flag", "preregistered rule: (i) and (ii) in steady and burst cells")
    record_many(ent, purge_prefixes=("t1.",))
    val = {e["name"]: e["value"] for e in ent}
    pd.set_option("display.width", 220)
    for rg in S.RANGES:
        print(rg, "f", fvals[rg], {k: val[f"t1.r{rg:g}.{k}"] for k in ("escalation_p3", "escalation_equal", "escalation_p1", "mis_triage_p1e", "mis_triage_p3", "mis_triage_p1")},
              "P3-P1e mis", [val[f"t1.r{rg:g}.mis_triage_p3_minus_p1e{s}"] for s in ("", "_lo", "_hi")])
        for grp_name in ("steady", "burst"):
            print("   ", grp_name, "P3-P2e reach10", [val.get(f"t1.r{rg:g}.{grp_name}.P3_minus_P2e.reach10_critical{s}") for s in ("", "_lo", "_hi")], "reach30", [val.get(f"t1.r{rg:g}.{grp_name}.P3_minus_P2e.reach30_critical{s}") for s in ("", "_lo", "_hi")])
        print("   wins:", val[f"t1.r{rg:g}.decision.p3_wins_at_equal_escalation"])


if __name__ == "__main__":
    B.N_BOOT
    main()
