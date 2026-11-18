"""S11 and the UA-SCT study: policies P0 to P4 in one simulator (plan, scenarios, metrics, hypotheses and reading rules: docs/02_preregistration/PREREGISTRATION.md, committed before this was run; protocol: docs/01_protocol/PROTOCOL_SCT.md).

P0 fixed 3-retry; P1 severity table (point class); P2 SCT (point class); P3 UA-SCT (class from the upper end of the one-sided class-conditional conformal interval, alpha 0.10); P4 P3 with the fast-path airtime capped
at phi of the duty budget. Also scored as a secondary baseline: the N16 scheduler (point class). Class pairs (assigned, true) come from the NHTSA cross-validated pairs of ``ua_conformal``; decision times
from the N19 early-exit distribution (seed 42, 5% target). SIMULATED; every value is an ASSUMPTION of ``sct_sim``. The duty limit is a parameter (default 1%, NOT verified for India).
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard.sct_sim import SCfg, SctParams, simulate

TUNE_SEED, EVAL_SEED = 1000, 3000
TUNE_HOURS, EVAL_HOURS = 3, 40
RANGES = (16.0, 32.0, 64.0)
POLICIES = ("P0", "P1", "sched", "P2", "P3", "P4")
DEFAULT = dict(n=100, sf=7, hb_period_s=600.0, p_up=0.1, p_down=0.1, duty=0.01, burst_cars=30, hb_bytes=16)
STEADY = [("base", {}), ("cars50", dict(n=50)), ("cars200", dict(n=200)), ("sf9", dict(sf=9)), ("hb60", dict(hb_period_s=60.0)), ("loss30", dict(p_up=0.3, p_down=0.3)), ("duty10", dict(duty=0.10))]
BURST = [("base", {}), ("burst10", dict(burst_cars=10)), ("burst60", dict(burst_cars=60)), ("cars50", dict(n=50)), ("cars200", dict(n=200)), ("sf9", dict(sf=9)), ("hb60", dict(hb_period_s=60.0)),
         ("loss30", dict(p_up=0.3, p_down=0.3)), ("duty10", dict(duty=0.10))]
TUNE_COMBOS = [(75, 20, 7, 0.20, 16.0), (75, 40, 9, 0.30, 32.0), (150, 20, 9, 0.30, 64.0), (150, 40, 7, 0.20, 16.0), (120, 20, 7, 0.30, 32.0), (120, 40, 9, 0.20, 64.0), (75, 40, 7, 0.20, 64.0), (150, 20, 9, 0.20, 32.0)]
PHIS = (0.1, 0.25, 0.5)
METRICS = ("mis_triage", "escalation", "reach10_critical", "reach30_critical", "reach10_fast", "p95_lat_s_critical", "median_lat_s_critical", "delivered_critical", "delivered_normal", "fast_air_share_of_allowance",
           "node_air_share", "node_air_per_event_s", "hb_dropped_share", "alert_collided_share", "duty_exceeded", "ack_budget_drop", "demoted", "n_critical", "n_nonsevere", "max_window_airtime_s")
SRC = "results/tables/s11_sct.csv"


def load_pools() -> dict:
    pairs = pd.read_csv(C.TABLES / "ua_pairs.csv")
    pairs = pairs[(pairs.alpha == 0.10) & (pairs.variant == "cc")]
    pools = {}
    for rg in RANGES:
        g = pairs[pairs.range_g == rg]
        pools[rg] = dict(true=g.true.to_numpy(int), point=g.c_hat.to_numpy(int), upper=g.upper.to_numpy(int))
    ev = pd.read_csv(C.TABLES / "s6_events_seed42_a5.csv")
    crash_t = ev[(ev.y == 1) & ev.alarm_E & ev.triggered].time_ms.to_numpy() / 1000.0
    fa_t = ev[(ev.y == 0) & ev.alarm_E & ev.triggered].time_ms.to_numpy() / 1000.0
    return dict(classes=pools, crash_t=crash_t, fa_t=fa_t)


def n16_params() -> dict:
    import json

    r = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    return dict(rho=r["n16.chosen.rho"], m=r["n16.chosen.m"], jitter=r["n16.chosen.jitter"], sf_raise=int(r["n16.chosen.sf_raise"]))


def make_cfg(pol: str, rg: float, kw: dict, burst: bool, seed: int, hour: int, pools: dict, sct: SctParams, phi: float | None, label: str, extra: dict | None = None) -> SCfg:
    d = {**DEFAULT, **kw, **(extra or {})}
    cl = pools["classes"][rg]
    assigned = cl["upper"] if pol in ("P3", "P4") else cl["point"]
    policy = {"P0": "fixed3", "P1": "severity", "sched": "scheduler"}.get(pol, "sct")
    params = SctParams(**{**sct.__dict__, "fast_cap": phi if pol == "P4" else None})
    return SCfg(n=d["n"], sf=d["sf"], policy=policy, seed=seed, hour=hour, duty=d["duty"], hb_period_s=d["hb_period_s"], hb_bytes=d["hb_bytes"], burst=burst, burst_cars=d["burst_cars"],
                p_up=d["p_up"], p_down=d["p_down"], sct=params, sched=n16_params(), true_pool=cl["true"], assigned_pool=assigned, crash_pool=pools["crash_t"], fa_pool=pools["fa_t"],
                fa_per_car_h=d.get("fa_per_car_h", 0.0), rate_per_car_h=d.get("rate_per_car_h", 0.1), label=label)


def _run(args) -> dict:
    cfg, meta = args
    out = simulate(cfg)
    out.update(meta)
    return out


def run_jobs(jobs: list, workers: int) -> pd.DataFrame:
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_run, jobs, chunksize=8))
    return pd.DataFrame(rows)


def tune(pools: dict, workers: int) -> tuple[SctParams, float, pd.DataFrame, pd.DataFrame]:
    grid = [(h, r, sf) for h in (0.0, 1.0, 2.0, 3.0) for r in (0.2, 0.35, 0.5) for sf in (False, True)]
    jobs = []
    for ci, (n, bc, sf, loss, rg) in enumerate(TUNE_COMBOS):
        kw = dict(n=n, burst_cars=bc, sf=sf, p_up=loss, p_down=loss)
        for h in range(TUNE_HOURS):
            jobs.append((make_cfg("P1", rg, kw, True, TUNE_SEED, h, pools, SctParams(), None, f"tune{ci}"), dict(combo=ci, pol="P1", gi=-1)))
            for gi, (hs, rho, sfr) in enumerate(grid):
                jobs.append((make_cfg("P2", rg, kw, True, TUNE_SEED, h, pools, SctParams(h_s=hs, rho_f=rho, sf_raise=sfr), None, f"tune{ci}"), dict(combo=ci, pol="P2", gi=gi)))
    R = run_jobs(jobs, workers)
    ref = R[R.pol == "P1"].groupby("combo").agg(normal=("delivered_normal", "mean")).normal
    rows = []
    for gi, (hs, rho, sfr) in enumerate(grid):
        g = R[(R.pol == "P2") & (R.gi == gi)].groupby("combo").agg(reach=("reach10_fast", "mean"), normal=("delivered_normal", "mean"))
        pen = np.maximum(0.0, ref.reindex(g.index).to_numpy() - g.normal.to_numpy() - 0.05)
        J = float((g.reach.to_numpy() - 2.0 * pen).mean())
        rows.append(dict(gi=gi, h_s=hs, rho_f=rho, sf_raise=sfr, J=J, n_features=int(hs > 0) + int(rho > 0) + int(sfr)))
    T = pd.DataFrame(rows)
    best = T.sort_values(["J", "n_features"], ascending=[False, True]).iloc[0]
    params = SctParams(h_s=float(best.h_s), rho_f=float(best.rho_f), sf_raise=bool(best.sf_raise))
    # phi for P4: the smallest share that keeps critical reach within 10 s within 2 points of P3 on the tuning scenarios
    jobs = []
    for ci, (n, bc, sf, loss, rg) in enumerate(TUNE_COMBOS):
        kw = dict(n=n, burst_cars=bc, sf=sf, p_up=loss, p_down=loss)
        for h in range(TUNE_HOURS):
            jobs.append((make_cfg("P3", rg, kw, True, TUNE_SEED, h, pools, params, None, f"tune{ci}"), dict(combo=ci, pol="P3", phi=-1)))
            for phi in PHIS:
                jobs.append((make_cfg("P4", rg, kw, True, TUNE_SEED, h, pools, params, phi, f"tune{ci}"), dict(combo=ci, pol="P4", phi=phi)))
    Rp = run_jobs(jobs, workers)
    p3 = float(Rp[Rp.pol == "P3"].reach10_critical.mean())
    phi_rows = [dict(phi=phi, reach10_critical=float(Rp[(Rp.pol == "P4") & (Rp.phi == phi)].reach10_critical.mean())) for phi in PHIS]
    ok = [r["phi"] for r in phi_rows if r["reach10_critical"] >= p3 - 0.02]
    phi = min(ok) if ok else max(PHIS)
    return params, phi, T, pd.DataFrame(phi_rows).assign(p3=p3)


def heldout(pools: dict, params: SctParams, phi: float, workers: int) -> pd.DataFrame:
    jobs = []
    for rg in RANGES:
        for mode, scen in (("steady", STEADY), ("burst", BURST)):
            for name, kw in scen:
                for pol in POLICIES:
                    for h in range(EVAL_HOURS):
                        jobs.append((make_cfg(pol, rg, kw, mode == "burst", EVAL_SEED, h, pools, params, phi, f"{mode}_{name}"), dict(range_g=rg, mode=mode, scen=name, pol=pol)))
    return run_jobs(jobs, workers)


def exploratory(pools: dict, params: SctParams, phi: float, workers: int) -> pd.DataFrame:
    """EXPLORATORY (not part of the hypotheses): ablations of SCT at +-16 g, false alarms at 1% and 5% targets, a single car with loss 10%, 30%, 60%."""
    jobs = []
    abl = {"full": {}, "no_preempt": dict(preempt=False), "no_flash": dict(flash=False), "no_sev_hold": dict(sev_hold=False), "no_reserve": dict(reserve=False), "no_sf_raise": dict(sf_raise=False)}
    for mode in ("steady", "burst"):
        for pol in ("P2", "P3"):
            for an, ov in abl.items():
                sct = SctParams(**{**params.__dict__, **ov})
                for h in range(EVAL_HOURS):
                    jobs.append((make_cfg(pol, 16.0, {}, mode == "burst", EVAL_SEED, h, pools, sct, None, f"abl_{mode}"), dict(block="ablation", mode=mode, pol=pol, variant=an)))
    for fa, tag in ((0.05, "fa1"), (0.25, "fa5")):
        for pol in ("P1", "P2", "P3", "P4"):
            for h in range(EVAL_HOURS):
                jobs.append((make_cfg(pol, 16.0, {}, False, EVAL_SEED, h, pools, params, phi, f"fa_{tag}", dict(fa_per_car_h=fa)), dict(block="false_alarm", mode=tag, pol=pol, variant="")))
    for loss in (0.1, 0.3, 0.6):
        for pol in ("P0", "P1", "P2", "P3"):
            for h in range(EVAL_HOURS):
                jobs.append((make_cfg(pol, 16.0, dict(n=1, p_up=loss, p_down=loss), False, EVAL_SEED, h, pools, params, phi, f"single{int(loss * 100)}", dict(rate_per_car_h=20.0)), dict(block="single_car", mode=f"loss{int(loss * 100)}", pol=pol, variant="")))
    return run_jobs(jobs, workers)


def agg_diff(R: pd.DataFrame, metric: str, a: str, b: str, cells: list[tuple], by: list[str]) -> tuple[float, float, float, int]:
    """Mean over cells of the paired mean difference (b minus a) over seeds, with a 95% bootstrap interval that resamples the seeds inside every cell (1,000 resamples)."""
    per = []
    for c in cells:
        sub = R
        for col, v in zip(by, c):
            sub = sub[sub[col] == v]
        pa = sub[sub.pol == a].sort_values("hour")[metric].to_numpy(float)
        pb = sub[sub.pol == b].sort_values("hour")[metric].to_numpy(float)
        m = ~(np.isnan(pa) | np.isnan(pb))
        if m.sum() >= 3:
            per.append(pb[m] - pa[m])
    if not per:
        return float("nan"), float("nan"), float("nan"), 0
    rng = np.random.default_rng(C.SEED)
    point = float(np.mean([p.mean() for p in per]))
    draws = [np.mean([p[rng.integers(0, len(p), len(p))].mean() for p in per]) for _ in range(B.N_BOOT)]
    return point, float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975)), len(per)


def main() -> None:
    from crashguard.results import record_many

    workers = min(14, os.cpu_count() or 1)
    pools = load_pools()
    params, phi, T, Tphi = tune(pools, workers)
    T.to_csv(C.TABLES / "s11_tuning.csv", index=False)
    Tphi.to_csv(C.TABLES / "s11_tuning_phi.csv", index=False)
    R = heldout(pools, params, phi, workers)
    R.to_csv(C.TABLES / "s11_sct.csv", index=False)
    X = exploratory(pools, params, phi, workers)
    X.to_csv(C.TABLES / "s11_exploratory.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"s11.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("tuned.h_s", params.h_s, "s", "SCT Severe hold, chosen on the tuning scenarios (P2, point classes)")
    add("tuned.rho_f", params.rho_f, "fraction", "reserved share of the hourly allowance, chosen on the tuning scenarios")
    add("tuned.sf_raise", int(params.sf_raise), "flag", "spreading-factor raise, chosen on the tuning scenarios")
    add("tuned.phi", phi, "fraction", "P4 fast-path share of the duty budget: the smallest of 0.1, 0.25, 0.5 whose tuning-scenario critical reach within 10 s is within 2 points of P3")
    for r in Tphi.itertuples():
        add(f"tuning.phi{r.phi:g}.reach10_critical", round(float(r.reach10_critical), 4), "fraction", f"P4 on the tuning scenarios; P3 = {r.p3:.4f}")
    add("heldout.seeds_per_cell", EVAL_HOURS, "seeds", "paired scenario seeds per cell (at least 30 required)")
    add("heldout.cells", int(R.groupby(["range_g", "mode", "scen"]).ngroups), "cells", "sensor range x steady or burst x one-factor scenario")
    add("assumed.duty_default", DEFAULT["duty"], "fraction", "ASSUMPTION; NOT verified for India (WPC/DoT not checked)")
    # per cell means and intervals
    for (rg, mode, scen, pol), g in R.groupby(["range_g", "mode", "scen", "pol"]):
        base = f"cell.r{rg:g}.{mode}.{scen}.{pol}"
        for met in METRICS:
            v = g[met].dropna().to_numpy(float)
            if len(v):
                p = B.ci(v, np.mean)
                u = "s" if "lat" in met else "fraction"
                add(f"{base}.{met}", round(p[0], 5), u, "mean over scenario seeds")
                add(f"{base}.{met}_lo", round(p[1], 5), u, "95% bootstrap interval over seeds")
                add(f"{base}.{met}_hi", round(p[2], 5), u, "95% bootstrap interval over seeds")
    # duty compliance over every run
    add("duty.runs", int(len(R) + len(X)), "runs", "all simulated runs of this study")
    add("duty.runs_exceeding_limit", int(R.duty_exceeded.sum() + X.duty_exceeded.sum()), "runs", "runs in which an independent scan of the logged transmissions finds more airtime than duty x 3,600 s in a trailing hour (node or base); must be 0")
    add("duty.share_of_runs_exceeding", round(float((R.duty_exceeded.sum() + X.duty_exceeded.sum()) / (len(R) + len(X))), 6), "fraction", "same, as a share of runs")
    # paired differences, by sensor range, over steady cells, burst cells and all cells
    comps = (("P1", "P0"), ("P1", "P2"), ("P1", "P3"), ("P1", "P4"), ("P2", "P3"), ("P3", "P4"), ("P1", "sched"))
    mets = ("mis_triage", "escalation", "reach10_critical", "reach30_critical", "reach10_fast", "p95_lat_s_critical", "delivered_normal", "fast_air_share_of_allowance", "node_air_share", "hb_dropped_share")
    for rg in RANGES:
        for grp, modes in (("steady", ("steady",)), ("burst", ("burst",)), ("all", ("steady", "burst"))):
            cells = [(rg, m, s) for m in modes for s in sorted(set(R[(R.range_g == rg) & (R["mode"] == m)].scen))]
            for a, b in comps:
                for met in mets:
                    p, lo, hi, n = agg_diff(R, met, a, b, cells, ["range_g", "mode", "scen"])
                    if n:
                        u = "s" if "lat" in met else "fraction"
                        t = f"diff.r{rg:g}.{grp}.{b}_minus_{a}.{met}"
                        add(t, round(p, 5), u, f"mean over {n} cells of the paired seed-mean difference ({b} minus {a})")
                        add(t + "_lo", round(lo, 5), u, "95% bootstrap interval (seeds resampled inside each cell)")
                        add(t + "_hi", round(hi, 5), u, "95% bootstrap interval (seeds resampled inside each cell)")
        # per-cell sign counts for the primary comparison
        for a, b in (("P1", "P3"), ("P1", "P2")):
            for met in ("reach10_critical", "mis_triage"):
                cnt = {"better": 0, "no_diff": 0, "worse": 0}
                for (m_, s_), _g in R[R.range_g == rg].groupby(["mode", "scen"]):
                    p, lo, hi, n = agg_diff(R, met, a, b, [(rg, m_, s_)], ["range_g", "mode", "scen"])
                    if not n:
                        continue
                    good = lo > 0 if met != "mis_triage" else hi < 0
                    bad = hi < 0 if met != "mis_triage" else lo > 0
                    cnt["better" if good else "worse" if bad else "no_diff"] += 1
                for k, v in cnt.items():
                    add(f"cells.r{rg:g}.{b}_vs_{a}.{met}.n_{k}", v, "cells", "cells whose paired interval is entirely on the favourable side (better), the unfavourable side (worse) or contains zero")
    # exploratory block
    for (blk, mode, pol, var), g in X.groupby(["block", "mode", "pol", "variant"]):
        for met in ("reach10_critical", "reach10_fast", "p95_lat_s_critical", "delivered_normal", "fast_air_share_of_allowance", "node_air_per_event_s", "fa_tx_fast", "cancel_tx", "n_fa_alerts", "alert_collided_share", "mis_triage", "escalation"):
            if met in g:
                v = g[met].dropna().to_numpy(float)
                if len(v):
                    p = B.ci(v, np.mean)
                    base = f"exploratory.{blk}.{mode}.{pol}{('.' + var) if var else ''}.{met}"
                    add(base, round(p[0], 5), "s" if "lat" in met else "fraction", "EXPLORATORY: not part of the preregistered hypotheses; mean over seeds")
                    add(base + "_lo", round(p[1], 5), "fraction", "95% bootstrap interval over seeds")
                    add(base + "_hi", round(p[2], 5), "fraction", "95% bootstrap interval over seeds")
    record_many(ent, purge_prefixes=("s11.",))
    pd.set_option("display.width", 250)
    print("tuned:", params, "phi", phi)
    for rg in RANGES:
        sel = R[(R.range_g == rg) & (R["mode"] == "burst") & (R.scen == "base")].groupby("pol")[["mis_triage", "escalation", "reach10_critical", "reach30_critical", "p95_lat_s_critical", "fast_air_share_of_allowance", "node_air_share"]].mean().round(3)
        print(rg, "burst base\n", sel.to_string())
        sel = R[(R.range_g == rg) & (R["mode"] == "steady") & (R.scen == "base")].groupby("pol")[["mis_triage", "escalation", "reach10_critical", "reach30_critical", "p95_lat_s_critical", "fast_air_share_of_allowance", "node_air_share"]].mean().round(3)
        print(rg, "steady base\n", sel.to_string())
    print("duty exceeded:", int(R.duty_exceeded.sum() + X.duty_exceeded.sum()), "of", len(R) + len(X))


if __name__ == "__main__":
    main()
