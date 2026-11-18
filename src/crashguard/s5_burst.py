"""S5: burst scenario with sensitivity (plan, defaults, tuning set and reading rule: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S5, written before this was run). SIMULATED, exploratory.

The burst scenario was added to X6 after the N16 steady-state comparison against the severity table was a null result, so every result here is exploratory.
Tuning bursts (8 combinations of cars, burst size, spreading factor and loss; seed 1000) choose a scheduler from the 24-combination grid; the held-out bursts (the sweep; seed 2000) are scored once.
All MCU, channel and traffic values are ASSUMPTIONS of ``capacity.py``; nothing here is measured on radios.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard.capacity import Cfg, simulate
from crashguard.scheduler import grid

TUNE_SEED, EVAL_SEED = 1000, 2000
TUNE_HOURS, EVAL_HOURS = 3, 40
TUNE_COMBOS = ((75, 20, 7, 0.20), (75, 60, 9, 0.45), (150, 20, 9, 0.45), (150, 60, 7, 0.20), (75, 40, 12, 0.20), (150, 40, 12, 0.45), (120, 20, 7, 0.45), (120, 60, 9, 0.20))
DEFAULT = dict(n=100, sf=7, hb_period_s=600.0, hb_bytes=16, burst_cars=30, p_up=0.1, p_down=0.1, capture="db6")
SWEEP = [("default", {}), ("capture_none", dict(capture="none")), ("burst10", dict(burst_cars=10)), ("burst60", dict(burst_cars=60)), ("burst100", dict(burst_cars=100)), ("cars50", dict(n=50)), ("cars200", dict(n=200)),
         ("hb60", dict(hb_period_s=60.0)), ("hbpayload26", dict(hb_bytes=26)), ("hbpayload48", dict(hb_bytes=48)), ("sf9", dict(sf=9)), ("sf12", dict(sf=12)), ("loss30", dict(p_up=0.3, p_down=0.3)), ("loss60", dict(p_up=0.6, p_down=0.6))]
POLICIES = ("fixed3", "severity", "scheduler", "scheduler_b")
METRICS = ("delivered_critical", "p95_lat_s_critical", "reach30_critical")
SRC = "results/tables/s5_burst.csv"


def n16_params() -> dict:
    import json

    r = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    return dict(rho=r["n16.chosen.rho"], m=r["n16.chosen.m"], jitter=r["n16.chosen.jitter"], sf_raise=r["n16.chosen.sf_raise"])


def _run(args) -> dict:
    cfg, sp, tag = args
    out = simulate(cfg, sp)
    out["tag"] = tag
    return out


def _cfg(kw: dict, policy: str, seed: int, hour: int) -> Cfg:
    d = {**DEFAULT, **kw}
    return Cfg(n=d["n"], sf=d["sf"], hb_period_s=d["hb_period_s"], policy="scheduler" if policy == "scheduler_b" else policy, burst=True, seed=seed, hour=hour,
               p_up=d["p_up"], p_down=d["p_down"], burst_cars=d["burst_cars"], capture=d["capture"], hb_bytes=d["hb_bytes"])


def tune(workers: int) -> tuple[pd.DataFrame, dict]:
    combos = grid()
    jobs = []
    for ci, p in enumerate(combos):
        sp = dict(rho=p.rho, m=p.m, jitter=p.jitter, sf_raise=int(p.sf_raise))
        for (n, bc, sf, loss) in TUNE_COMBOS:
            for h in range(TUNE_HOURS):
                cfg = Cfg(n=n, sf=sf, hb_period_s=600.0, policy="scheduler", burst=True, seed=TUNE_SEED, hour=h, p_up=loss, p_down=loss, burst_cars=bc)
                jobs.append((cfg, sp, ci))
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_run, jobs, chunksize=8))
    R = pd.DataFrame(rows)
    t = R.groupby("tag").agg(J=("delivered_critical", "mean"), node_airtime=("node_airtime_share", "mean")).reset_index()
    t["name"] = [combos[i].name for i in t.tag]
    t["n_features"] = [int(combos[i].rho > 0) + int(combos[i].jitter > 0) + int(combos[i].sf_raise) for i in t.tag]
    best = t.sort_values(["J", "n_features", "node_airtime"], ascending=[False, True, True]).iloc[0]
    p = combos[int(best.tag)]
    return t, dict(rho=p.rho, m=p.m, jitter=p.jitter, sf_raise=int(p.sf_raise), name=p.name, J=float(best.J))


def heldout(sp_n16: dict, sp_b: dict, workers: int) -> pd.DataFrame:
    jobs = []
    for name, kw in SWEEP:
        for pol in POLICIES:
            sp = sp_b if pol == "scheduler_b" else sp_n16
            for h in range(EVAL_HOURS):
                jobs.append((_cfg(kw, pol, EVAL_SEED, h), sp, (name, pol)))
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_run, jobs, chunksize=8))
    R = pd.DataFrame(rows)
    R["setting"] = [t[0] for t in R.tag]
    R["pol"] = [t[1] for t in R.tag]
    return R


def paired_row(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float, int]:
    """Mean of (b - a) over seeds where both are defined, with a 95% bootstrap interval."""
    m = ~(np.isnan(a) | np.isnan(b))
    if m.sum() < 3:
        return float("nan"), float("nan"), float("nan"), int(m.sum())
    d = B.paired_diff(a[m], b[m], np.mean)
    return d[0], d[1], d[2], int(m.sum())


def classify(lo: float, hi: float, latency: bool = False) -> str:
    """Sign of a paired interval. For delivery and reach, positive = better; for latency, positive = longer (worse)."""
    if latency:
        return "longer" if lo > 0 else ("shorter" if hi < 0 else "no_difference")
    return "better" if lo > 0 else ("worse" if hi < 0 else "no_difference")


def main() -> None:
    from crashguard.results import record_many

    workers = min(12, os.cpu_count() or 1)
    sp16 = n16_params()
    tdf, chosen = tune(workers)
    tdf.to_csv(C.TABLES / "s5_tuning.csv", index=False)
    R = heldout(sp16, chosen, workers)
    R.to_csv(C.TABLES / "s5_burst.csv", index=False)
    ent: list[dict] = []

    def add(name, value, unit, origin="SIMULATED", notes=""):
        ent.append(dict(name=f"s5.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("n_tuning_sims", int(len(tdf)), "grid points", notes="scheduler grid points tuned on the tuning bursts")
    add("chosen.rho", chosen["rho"], "fraction", notes="burst-tuned scheduler: reserve")
    add("chosen.m", chosen["m"], "multiplier", notes="burst-tuned scheduler: spacing multiplier")
    add("chosen.jitter", chosen["jitter"], "fraction", notes="burst-tuned scheduler: jitter")
    add("chosen.sf_raise", chosen["sf_raise"], "flag", notes="burst-tuned scheduler: spreading-factor raise")
    add("chosen.J_tuning", round(chosen["J"], 4), "fraction", notes="mean critical delivery over the tuning bursts")
    add("n16_setting.rho", sp16["rho"], "fraction", notes="N16 steady-state setting, scored here without re-tuning")
    add("n16_setting.m", sp16["m"], "multiplier", notes="N16 steady-state setting")
    add("n16_setting.jitter", sp16["jitter"], "fraction", notes="N16 steady-state setting")
    add("n16_setting.sf_raise", int(sp16["sf_raise"]), "flag", notes="N16 steady-state setting")
    add("heldout.hours_per_setting", EVAL_HOURS, "seeds", notes="paired scenario seeds per setting")
    verdict: dict = {}
    for setting, _kw in SWEEP:
        g = R[R.setting == setting]
        piv = {pol: g[g.pol == pol].sort_values("hour") for pol in POLICIES}
        for pol in POLICIES:
            for met in METRICS:
                v = piv[pol][met].to_numpy(float)
                v = v[~np.isnan(v)]
                if len(v):
                    p = B.ci(v, np.mean)
                    u = "s" if met.startswith("p95") else "fraction"
                    add(f"heldout.{setting}.{pol}.{met}", round(p[0], 4), u, notes="mean over scenario seeds")
                    add(f"heldout.{setting}.{pol}.{met}_lo", round(p[1], 4), u, notes="95% bootstrap interval")
                    add(f"heldout.{setting}.{pol}.{met}_hi", round(p[2], 4), u, notes="95% bootstrap interval")
            add(f"heldout.{setting}.{pol}.n_critical_mean", round(float(piv[pol].n_critical.mean()), 2), "alerts", notes="critical alerts per simulated hour")
        for sched in ("scheduler", "scheduler_b"):
            for base in ("severity", "fixed3"):
                for met in METRICS:
                    d, lo, hi, n = paired_row(piv[base][met].to_numpy(float), piv[sched][met].to_numpy(float))
                    tag = f"heldout.{setting}.diff.{sched}_minus_{base}.{met}"
                    u = "s" if met.startswith("p95") else "fraction"
                    add(tag, round(d, 4), u, notes=f"scheduler minus {base}, paired by scenario seed; seeds with both defined: {n}")
                    add(tag + "_lo", round(lo, 4), u, notes="95% bootstrap interval")
                    add(tag + "_hi", round(hi, 4), u, notes="95% bootstrap interval")
                    verdict.setdefault((sched, base, met), {})[setting] = classify(lo, hi, met.startswith("p95")) if not np.isnan(lo) else "undefined"
    for (sched, base, met), d in verdict.items():
        classes = ("longer", "no_difference", "shorter", "undefined") if met.startswith("p95") else ("better", "no_difference", "worse", "undefined")
        for cls in classes:
            add(f"conclusion.{sched}_vs_{base}.{met}.n_{cls}", sum(v == cls for v in d.values()), "settings", notes="of the sweep settings; sign of the paired interval of (scheduler minus baseline): better/longer = the whole interval is above zero")
        add(f"conclusion.{sched}_vs_{base}.{met}.settings_not_{classes[0]}", ",".join(k for k, v in d.items() if v != classes[0]) or "none", "text", notes="settings where the whole interval is not above zero")
    a4 = ("default", "capture_none", "burst10", "burst60", "cars50", "cars200", "hbpayload26", "sf9")  # the A4 sweep of the UA-SCT prompt: capture none and 6 dB, burst 10, 30 and 60, payload 16 and 26 B, cars 50, 100 and 200, SF 7 and 9
    for sched in ("scheduler", "scheduler_b"):
        for met in ("delivered_critical", "reach30_critical"):
            d = verdict[(sched, "severity", met)]
            lost = [k for k in a4 if d.get(k) != "better"]
            add(f"a4.{sched}_vs_severity.{met}.settings_where_not_better", ",".join(lost) or "none", "text", notes=f"A4 sweep settings where the whole paired interval of (scheduler minus severity table) is not above zero; the sweep: {', '.join(a4)}")
            add(f"a4.{sched}_vs_severity.{met}.n_better", sum(d.get(k) == "better" for k in a4), "settings", notes=f"of {len(a4)} A4 settings")
    record_many(ent, purge_prefixes=("s5.",))
    pd.set_option("display.width", 250)
    print("chosen:", chosen)
    for sched in ("scheduler", "scheduler_b"):
        for base in ("severity", "fixed3"):
            print(sched, "vs", base, {met: {k: v for k, v in verdict[(sched, base, met)].items()} for met in ("delivered_critical",)})


if __name__ == "__main__":
    main()
