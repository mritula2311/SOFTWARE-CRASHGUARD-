"""T4: two clarifications (definitions: docs/02_preregistration/PREREGISTRATION.md, Addendum 1, section A1.4, committed before this was run). No new hypothesis.

(a) "Under-estimation" of the S9 class rule against the mis-triage of H-a. S9: share of tests whose reported class is below the reference class, where the reported class comes from the LOWER bound of a
delta-V interval (report the class below plus a flag). H-a: share of true Severe or Critical events whose assigned class is below Severe, where the assigned class is the UPPER end of a conformal class interval.
Both are computed per true class and per range from the stored arrays; the two rules differ, so both statements hold.
(b) Single car, 60% loss both ways: setup, the expected share acknowledged within 10 s from the number of retry rounds that fit (ANALYTICAL), and SCT with quick retries (EXPLORATORY).
MEASURED_SOFTWARE for (a); SIMULATED and ANALYTICAL for (b).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard import s11_sct as S
from crashguard import s9_conformal_dv as S9
from crashguard import saturation_splits as SP
from crashguard import severity_study as SS
from crashguard import ua_core as U
from crashguard.capacity import air
from crashguard.replay import COMPUTE_S, MARGIN_S, PROC_S
from crashguard.sct_sim import FLASH_LEN, SctParams

SRC = "results/tables/t4_clarify.csv"
CLASS_NAMES = ("Low", "Moderate", "Severe", "Critical")


def part_a(ent: list[dict], add) -> None:
    core = U.build()
    refc = U.ref_classes(core)
    grp = core.grp
    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    cells = SP.build_cells(tests)
    asi_tab = core.asi
    res = S9.run(cells, meta, asi_tab)
    # S9 uses its own groups (make and model) and 5 repeats of the same fold scheme
    for rg in SP.RANGES:
        pt = res["pt"][rg]
        for nom, alpha in ((0.8, 0.20), (0.9, 0.10)):
            lo = res["out"][rg][nom]["lo"]
            cls_pt = np.array([U.classes(pt[r], asi_tab[rg]) for r in range(U.REPEATS)])
            cls_s9 = np.zeros_like(cls_pt)
            for r in range(U.REPEATS):
                cls_s9[r], _ = S9.decision_class(pt[r], lo[r], asi_tab[rg])
            iv = U.interval_classes(core, rg, alpha, "cc")
            up = iv["up"]
            t = np.broadcast_to(refc[None, :], cls_pt.shape)
            for c in range(4):
                m = t == c
                n_tests = int((refc == c).sum())
                add(f"a.r{rg:g}.nom{int(nom * 100)}.true{c}.n_tests", n_tests, "tests", f"tests whose reference class is {CLASS_NAMES[c]}")
                for nm, cls in (("under_point", cls_pt), ("under_s9_lower_rule", cls_s9), ("under_upper_end", up)):
                    arr = np.where(m, (cls < t).astype(float), np.nan)
                    p, lo_, hi_ = U.gmean(arr, grp)
                    add(f"a.r{rg:g}.nom{int(nom * 100)}.true{c}.{nm}", round(p, 4) if p == p else "NOT_RUN", "fraction", "share of rows of this true class whose reported class is below the true class; grouped bootstrap interval" if p == p else "no tests of this class")
                    add(f"a.r{rg:g}.nom{int(nom * 100)}.true{c}.{nm}_lo", round(lo_, 4) if lo_ == lo_ else "NOT_RUN", "fraction", "95% grouped bootstrap interval")
                    add(f"a.r{rg:g}.nom{int(nom * 100)}.true{c}.{nm}_hi", round(hi_, 4) if hi_ == hi_ else "NOT_RUN", "fraction", "95% grouped bootstrap interval")
            sev = t >= 2
            for nm, cls in (("point", cls_pt), ("s9_lower_rule", cls_s9), ("upper_end", up)):
                mis = np.where(sev, (cls < 2).astype(float), np.nan)
                und = (cls < t).astype(float)
                for lab, arr in (("mis_triage", mis), ("under_all_classes", und)):
                    p, lo_, hi_ = U.gmean(arr, grp)
                    add(f"a.r{rg:g}.nom{int(nom * 100)}.overall.{lab}.{nm}", round(p, 4), "fraction", "pooled over all rows; mis-triage: true Severe or Critical assigned below Severe; under-estimation: reported class below the true class")
                    add(f"a.r{rg:g}.nom{int(nom * 100)}.overall.{lab}.{nm}_lo", round(lo_, 4), "fraction", "95% grouped bootstrap interval")
                    add(f"a.r{rg:g}.nom{int(nom * 100)}.overall.{lab}.{nm}_hi", round(hi_, 4), "fraction", "95% grouped bootstrap interval")


def analytic_rounds(loss: float) -> dict:
    """Expected share acknowledged within 10 s for a single car (no collisions), from the number of retry rounds that fit. ANALYTICAL; timing values are the simulator's assumptions."""
    sf = 7
    a_fl, a_al, a_ack = air(FLASH_LEN, sf), air(P.ALERT_LEN, sf), air(P.ACK_LEN, sf)
    win = PROC_S + a_ack + MARGIN_S
    q = (1.0 - loss) ** 2  # a message and its ACK must both get through
    t_dec = 0.3  # typical early-exit decision time of the pool (seconds), an assumption
    out = {}
    # SCT: zero hold for Critical, a round = flash, listen, alert, listen; next round after 5 s spacing
    start, rounds, chances = t_dec + COMPUTE_S, 0, 0
    t = start
    for _k in range(12):
        if t >= 10.0:
            break
        rounds += 1
        chances += 1 if t + a_fl + win < 10.0 else 0
        t += a_fl + win
        chances += 1 if t + a_al + win < 10.0 else 0
        t += a_al + win + 5.0
    out["sct_rounds"], out["sct_chances"], out["sct_reach10"] = rounds, chances, 1.0 - (1.0 - q) ** chances
    # table: 5 s cancel window for Critical, then immediate retries (listen window only), at most 12 tries
    t = t_dec + COMPUTE_S + 5.0
    tries = 0
    while tries < 12 and t + a_al + win < 10.0:
        tries += 1
        t += a_al + win
    out["table_tries"], out["table_reach10"] = tries, 1.0 - (1.0 - q) ** tries
    out["q_round"] = q
    return out


def part_b(add) -> None:
    from crashguard import boot as B

    pools = S.load_pools()
    params = SctParams(h_s=2.0, rho_f=0.35, sf_raise=True)
    import json

    r = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    params = SctParams(h_s=float(r["s11.tuned.h_s"]), rho_f=float(r["s11.tuned.rho_f"]), sf_raise=bool(r["s11.tuned.sf_raise"]))
    quick = SctParams(**{**params.__dict__, "spacing_crit": 0.3, "spacing_sev": 0.3})
    jobs = []
    for loss in (0.1, 0.3, 0.6):
        for h in range(S.EVAL_HOURS):
            for pol, sct, meta_pol in (("P1", params, "P1"), ("P2", params, "P2"), ("P2", quick, "P2_quick"), ("P0", params, "P0")):
                cfg = S.make_cfg(pol, 16.0, dict(n=1, p_up=loss, p_down=loss), False, S.EVAL_SEED, h, pools, sct, None, f"single{int(loss * 100)}", dict(rate_per_car_h=20.0))
                jobs.append((cfg, dict(loss=loss, pol=meta_pol)))
    R = S.run_jobs(jobs, min(14, os.cpu_count() or 1))
    R.to_csv(C.TABLES / "t4_single_car.csv", index=False)
    add("b.setup.cars", 1, "cars", "one car, no collisions", "SIMULATED")
    add("b.setup.alerts_per_hour", 20, "alerts per hour", "stress value", "SIMULATED")
    add("b.setup.spreading_factor", 7, "SF", "", "SIMULATED")
    add("b.setup.duty_limit", 0.01, "fraction", "ASSUMPTION; NOT verified for India", "SIMULATED")
    add("b.setup.seeds", S.EVAL_HOURS, "seeds", "paired scenario seeds", "SIMULATED")
    for loss in (0.1, 0.3, 0.6):
        for pol in ("P0", "P1", "P2", "P2_quick"):
            v = R[(R.loss == loss) & (R.pol == pol)].reach10_critical.dropna().to_numpy(float)
            p = B.ci(v, np.mean)
            add(f"b.loss{int(loss * 100)}.{pol}.reach10_critical", round(p[0], 4), "fraction", "mean over seeds, single car, +-16 g class pool", "SIMULATED")
            add(f"b.loss{int(loss * 100)}.{pol}.reach10_critical_lo", round(p[1], 4), "fraction", "95% bootstrap interval", "SIMULATED")
            add(f"b.loss{int(loss * 100)}.{pol}.reach10_critical_hi", round(p[2], 4), "fraction", "95% bootstrap interval", "SIMULATED")
        a = R[(R.loss == loss) & (R.pol == "P1")].sort_values("hour").reach10_critical.to_numpy(float)
        b = R[(R.loss == loss) & (R.pol == "P2_quick")].sort_values("hour").reach10_critical.to_numpy(float)
        m = ~(np.isnan(a) | np.isnan(b))
        d = B.paired_diff(a[m], b[m], np.mean)
        add(f"b.loss{int(loss * 100)}.quick_minus_table.reach10_critical", round(d[0], 4), "fraction", "SCT with quick retries (0.3 s spacing, EXPLORATORY) minus the severity table, paired by seed", "SIMULATED")
        add(f"b.loss{int(loss * 100)}.quick_minus_table.reach10_critical_lo", round(d[1], 4), "fraction", "95% bootstrap interval", "SIMULATED")
        add(f"b.loss{int(loss * 100)}.quick_minus_table.reach10_critical_hi", round(d[2], 4), "fraction", "95% bootstrap interval", "SIMULATED")
        an = analytic_rounds(loss)
        for k, v in an.items():
            add(f"b.analytic.loss{int(loss * 100)}.{k}", round(float(v), 4) if isinstance(v, float) else int(v), "value", "ANALYTICAL: expected reach from the number of rounds (SCT) or tries (table) that fit before 10 s; a message and its ACK must both get through; no collisions; decision time 0.3 s assumed", "ANALYTICAL")


def main() -> None:
    from crashguard.results import record_many

    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"t4.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    part_a(ent, add)
    part_b(add)
    pd.DataFrame([dict(name=e["name"], value=e["value"]) for e in ent]).to_csv(C.TABLES / "t4_clarify.csv", index=False)
    record_many(ent, purge_prefixes=("t4.",))
    g = {e["name"]: e["value"] for e in ent}
    for rg in (16, 32, 64):
        print(rg, {k: g[f"t4.a.r{rg}.nom90.overall.{k}"] for k in ("mis_triage.point", "mis_triage.s9_lower_rule", "mis_triage.upper_end", "under_all_classes.point", "under_all_classes.s9_lower_rule", "under_all_classes.upper_end")})
    for loss in (10, 30, 60):
        print(loss, {p: g[f"t4.b.loss{loss}.{p}.reach10_critical"] for p in ("P0", "P1", "P2", "P2_quick")}, g[f"t4.b.analytic.loss{loss}.sct_reach10"], g[f"t4.b.analytic.loss{loss}.table_reach10"])


if __name__ == "__main__":
    main()
