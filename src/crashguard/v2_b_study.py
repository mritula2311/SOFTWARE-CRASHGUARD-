"""Study B (docs/02_preregistration/PREREGISTRATION_V2.md section 3): load-adaptive escalation. SIMULATED; every channel and traffic value is an ASSUMPTION of ``sct_sim`` and the 1% duty limit is NOT verified for India.
Five adaptive variants against matched fixed lowered-threshold baselines (same realised escalation), 40 paired seeds per cell. Prefix ``v2.b.``.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import s11_sct as S11
from crashguard import v2_pools as VP
from crashguard.s13_spaced_table import P1B
from crashguard.sct_sim import SCfg, SctParams
from crashguard.v2_common import Entries

SRC = "results/tables/v2_b_runs.csv"
RES = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
F0 = float(RES["t1.r16.f"])
EVAL_SEED, TUNE_SEED, EVAL_HOURS, TUNE_HOURS = S11.EVAL_SEED, S11.TUNE_SEED, S11.EVAL_HOURS, S11.TUNE_HOURS
W_BACKOFF = (2.0, 1.0, 0.5, 0.25)
N16 = dict(rho=RES["n16.chosen.rho"], m=RES["n16.chosen.m"], jitter=RES["n16.chosen.jitter"], sf_raise=int(RES["n16.chosen.sf_raise"]))  # read once (``s11_sct.n16_params`` parses results.json on every call)
METRICS = ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "mis_triage", "escalation", "escalation_used", "delivered_normal", "node_air_share", "fast_air_share_of_allowance", "duty_exceeded",
           "beacon_air_s", "beacon_tx", "demoted", "n_critical", "n_nonsevere", "max_window_airtime_s")
VARIANTS = ("V1", "V2", "V3", "V4", "V5")
VNAME = {"V1": "controller", "V2": "token bucket", "V3": "beacon-assisted", "V4": "severity-scaled backoff", "V5": "graceful demotion"}
GRID = {"V1": [dict(g=g) for g in (0.02, 0.05, 0.10)], "V2": [dict(b=b, r=r) for b in (1.0, 2.0) for r in (0.5, 1.0, 2.0, 4.0)], "V3": [dict(period_s=120.0)], "V4": [dict()], "V5": [dict(k=k) for k in (1, 2, 3)]}
DEFAULT = S11.DEFAULT


def dyn_of(v: str, par: dict) -> dict:
    kind = {"V1": "controller", "V2": "bucket", "V3": "beacon", "V4": "backoff", "V5": "demote"}[v]
    d = dict(kind=kind, s0=F0, **par)
    if v == "V4":
        d["W"] = W_BACKOFF
    return d


def cells() -> list[dict]:
    out = []
    for name, kw in (("base", {}), ("burst10", dict(burst_cars=10)), ("burst60", dict(burst_cars=60)), ("cars50", dict(n=50)), ("cars200", dict(n=200)), ("sf9", dict(sf=9)), ("capnone", dict(capture="none"))):
        out.append(dict(name=f"burst_{name}", group="burst", kw=kw, burst=True, loaded=False))
    for name, kw in (("base", {}), ("cars200", dict(n=200)), ("sf9", dict(sf=9))):
        out.append(dict(name=f"loadedburst_{name}", group="burst", kw=kw, burst=True, loaded=True, rate=1.0))
    for name, kw in (("base", {}), ("cars50", dict(n=50)), ("cars200", dict(n=200)), ("sf9", dict(sf=9)), ("capnone", dict(capture="none")), ("loss30", dict(p_up=0.3, p_down=0.3))):
        out.append(dict(name=f"steady_{name}", group="steady", kw=kw, burst=False, loaded=False))
    out.append(dict(name="single_loss60", group="single", kw=dict(n=1, p_up=0.6, p_down=0.6), burst=False, loaded=False, rate=20.0))
    out.append(dict(name="mixed_cars200", group="mixed", kw=dict(n=200), burst=False, loaded=True, rate=1.0))
    return out


def tune_cells() -> list[dict]:
    return [dict(name=f"tune{ci}", group="tune", kw=dict(n=n, burst_cars=bc, sf=sf, p_up=loss, p_down=loss), burst=True, loaded=False) for ci, (n, bc, sf, loss, _rg) in enumerate(S11.TUNE_COMBOS)]


def make(cell: dict, cfg_name: str, dyn: dict | None, hour: int, seed: int, pools: dict, params: SctParams) -> SCfg:
    d = {**DEFAULT, **cell["kw"]}
    pool = pools["loaded" if cell["loaded"] else "unloaded"]
    policy = {"P1": "severity", "P1b": "scheduler"}.get(cfg_name, "sct")
    cfg = SCfg(n=d["n"], sf=d["sf"], policy=policy, seed=seed, hour=hour, duty=d["duty"], hb_period_s=d["hb_period_s"], hb_bytes=d["hb_bytes"], burst=cell["burst"], burst_cars=d["burst_cars"], p_up=d["p_up"],
               p_down=d["p_down"], sct=params, sched=dict(P1B) if cfg_name == "P1b" else dict(N16), true_pool=pool["true"], assigned_pool=pool["point"], crash_pool=pool["crash_t"], fa_pool=pool["fa_t"],
               fa_per_car_h=0.0, rate_per_car_h=cell.get("rate", 0.1), label=f"b_{cell['name']}", capture=d.get("capture", "db6"))
    if dyn is not None:
        cfg.dyn, cfg.pool_cls, cfg.pool_scales = dyn, pool["pcls"], pool["scales"]
    return cfg


def jobs_for(cells_: list[dict], named: dict[str, dict | None], seed: int, hours: int, pools: dict, params: SctParams, tag: str) -> list:
    jobs = []
    for cell in cells_:
        for name, dyn in named.items():
            for h in range(hours):
                jobs.append((make(cell, name.split(":")[0] if name in ("P1", "P1b") else name, dyn, h, seed, pools, params), dict(cell=cell["name"], group=cell["group"], cfg=name, hour=h, phase=tag)))
    return jobs


def pool_of(cell: dict, pools: dict) -> dict:
    return pools["loaded" if cell["loaded"] else "unloaded"]


def match_scale(pool: dict, target: float, kappa: float) -> float:
    """Bisection on the grid of scales in [F0, 1] for the fixed rule whose (calibrated) pool escalation is closest to the target."""
    lo, hi = VP.scale_index(F0), VP.scale_index(1.0)
    f = lambda j: kappa * VP.esc_pool(pool, float(VP.SCALES[j]))  # noqa: E731  (non-increasing in the scale)
    if target >= f(lo):
        return float(VP.SCALES[lo])
    if target <= f(hi):
        return float(VP.SCALES[hi])
    for _ in range(40):
        if hi - lo <= 1:
            break
        mid = (lo + hi) // 2
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    j = lo if abs(f(lo) - target) <= abs(f(hi) - target) else hi
    return float(VP.SCALES[j])


def run_phase(cells_: list[dict], variants: dict[str, dict], seed: int, hours: int, pools: dict, params: SctParams, tag: str, workers: int, with_refs: bool = True) -> pd.DataFrame:
    named: dict[str, dict | None] = {}
    if with_refs:
        named.update({"P1": None, "P1b": None, "P2": dict(kind="fixed", s0=1.0)})
    named["FIX0"] = dict(kind="fixed", s0=F0)
    named.update(variants)
    R1 = S11.run_jobs(jobs_for(cells_, named, seed, hours, pools, params, tag), workers)
    jobs = []
    sb: dict = {}
    for cell in cells_:
        pool = pool_of(cell, pools)
        fx = R1[(R1.cell == cell["name"]) & (R1.cfg == "FIX0")]
        kappa = float(fx.escalation_used.mean()) / max(VP.esc_pool(pool, F0), 1e-9)
        for v in variants:
            tgt = float(R1[(R1.cell == cell["name"]) & (R1.cfg == v)].escalation_used.mean())
            s = match_scale(pool, tgt, kappa)
            sb[(cell["name"], v)] = s
            for h in range(hours):
                jobs.append((make(cell, "M", dict(kind="fixed", s0=s), h, seed, pools, params), dict(cell=cell["name"], group=cell["group"], cfg=f"M[{v}]", hour=h, phase=tag, s_b=s)))
    R2 = S11.run_jobs(jobs, workers) if jobs else pd.DataFrame()
    R = pd.concat([R1, R2], ignore_index=True)
    R["s_b"] = R.get("s_b", np.nan)
    return R


def gain_stats(R: pd.DataFrame, cell: str, a: str, b: str, metric: str, seed: int = C.SEED) -> tuple[float, np.ndarray, int]:
    """b minus a, paired by seed hour inside one cell: point, bootstrap draws of the mean, number of pairs."""
    sub = R[R.cell == cell]
    pa = sub[sub.cfg == a].sort_values("hour")[metric].to_numpy(float)
    pb = sub[sub.cfg == b].sort_values("hour")[metric].to_numpy(float)
    m = ~(np.isnan(pa) | np.isnan(pb))
    d = (pb - pa)[m]
    if len(d) < 3:
        return float("nan"), np.array([np.nan]), len(d)
    rng = np.random.default_rng(seed)
    draws = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)])
    return float(d.mean()), draws, len(d)


def tune(pools: dict, params: SctParams, workers: int) -> dict:
    tc = tune_cells()
    variants = {}
    for v, grid in GRID.items():
        for par in grid:
            variants[f"{v}:" + ",".join(f"{k}={x}" for k, x in par.items())] = dyn_of(v, par)
    R = run_phase(tc, variants, TUNE_SEED, TUNE_HOURS, pools, params, "tune", workers, with_refs=False)
    chosen, rows = {}, []
    for v, grid in GRID.items():
        best = None
        for par in grid:
            nm = f"{v}:" + ",".join(f"{k}={x}" for k, x in par.items())
            gains = []
            for cell in tc:
                g, _d, n = gain_stats(R, cell["name"], f"M[{nm}]", nm, "reach10_critical")
                gains.append(g)
            mg = float(np.nanmean(gains))
            rows.append(dict(variant=v, params=nm, mean_gain=mg))
            if best is None or mg > best[0] + 1e-12:  # ties keep the earliest (simplest) setting of the grid
                best = (mg, par)
        chosen[v] = best[1]
    pd.DataFrame(rows).to_csv(C.TABLES / "v2_b_tuning.csv", index=False)
    return chosen


def main() -> None:
    workers = min(14, os.cpu_count() or 1)
    params = SctParams(h_s=float(RES["s11.tuned.h_s"]), rho_f=float(RES["s11.tuned.rho_f"]), sf_raise=bool(RES["s11.tuned.sf_raise"]))
    pools = VP.default_pools()
    chosen = tune(pools, params, workers)
    ent = Entries("v2.b", SRC, "SIMULATED")
    for v, par in chosen.items():
        ent.add(f"tuned.{v}", json.dumps(par), "parameters", f"{VNAME[v]}: chosen on the tuning scenarios (seed {TUNE_SEED}, {TUNE_HOURS} hours) by the largest mean gain over the matched baseline")
    cl = cells()
    variants = {v: dyn_of(v, chosen[v]) for v in VARIANTS}
    R = run_phase(cl, variants, EVAL_SEED, EVAL_HOURS, pools, params, "eval", workers)
    R.to_csv(C.TABLES / "v2_b_runs.csv", index=False)
    ent.add("duty.runs_exceeding_limit", int(R.duty_exceeded.sum()), "runs", "independent scan; must be 0")
    ent.add("runs", len(R), "runs")
    ent.add("seeds_per_cell", EVAL_HOURS, "seeds")
    ent.add("F0", F0, "scale", "starting threshold scale = the factor of T1 at +-16 g")
    ent.add("pool.loaded_nonsevere_share", round(pools["loaded"]["share_nonsevere"], 4), "fraction")
    ent.add("pool.unloaded_nonsevere_share", round(pools["unloaded"]["share_nonsevere"], 4), "fraction")
    # ---- cell summaries
    for cell in cl:
        for cfg in sorted(set(R[R.cell == cell["name"]].cfg)):
            sub = R[(R.cell == cell["name"]) & (R.cfg == cfg)]
            nm = cfg.replace("[", "_").replace("]", "")
            for m in ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "mis_triage", "escalation_used", "delivered_normal", "node_air_share", "beacon_air_s"):
                v = sub[m].dropna().to_numpy(float)
                if len(v):
                    rng = np.random.default_rng(C.SEED)
                    dr = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(1000)]
                    ent.ci(f"cell.{cell['name']}.{nm}.{m}", (float(v.mean()), float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "s" if "lat" in m else "fraction", d=5)
            if cfg.startswith("M["):
                ent.add(f"cell.{cell['name']}.{nm}.s_b", round(float(sub.s_b.iloc[0]), 4), "scale", "matched fixed threshold scale")
    # ---- B1 match error
    for cell in cl:
        for v in VARIANTS:
            g, dr, n = gain_stats(R, cell["name"], v, f"M[{v}]", "escalation_used")
            ent.ci(f"match.{cell['name']}.{v}.escalation_baseline_minus_variant", (g, float(np.nanquantile(dr, 0.025)), float(np.nanquantile(dr, 0.975))), "fraction", "realised escalation of the matched baseline minus that of the variant", d=5)
    # ---- gains
    raw: dict[tuple, float] = {}
    gains: dict[tuple, tuple] = {}
    for cell in cl:
        for v in VARIANTS:
            for m in ("reach10_critical", "reach30_critical", "p95_lat_s_critical", "mis_triage", "delivered_normal", "node_air_share"):
                g, dr, n = gain_stats(R, cell["name"], f"M[{v}]", v, m)
                if np.isnan(g):
                    continue
                lo, hi = float(np.nanquantile(dr, 0.025)), float(np.nanquantile(dr, 0.975))
                ent.ci(f"gain.{cell['name']}.{v}.{m}", (g, lo, hi), "s" if "lat" in m else "fraction", "variant minus matched fixed baseline, paired by seed", d=5)
                if m == "reach10_critical":
                    raw[(cell["name"], v)] = float(max(np.mean(dr <= 0.0), 1.0 / 1001))
                    gains[(cell["name"], v)] = (g, lo, hi)
                    ent.add(f"gain.{cell['name']}.{v}.reach10_critical_p", round(raw[(cell["name"], v)], 4), "probability", "one-sided: gain at or below 0")
    burst_cells = [c["name"] for c in cl if c["group"] == "burst"]
    weakest = min(burst_cells, key=lambda c: float(R[(R.cell == c) & (R.cfg == "M[V2]")].reach10_critical.mean()))
    ent.add("hB1.weakest_baseline_cell", weakest, "cell", "burst cell where the matched baseline (token bucket) has the lowest critical reach within 10 s")
    best_v, best_n, best_p = None, -1, 1.0
    for v in VARIANTS:
        ok = [c for c in burst_cells if gains[(c, v)][0] >= 0.03 and gains[(c, v)][1] > 0.0]
        ps = sorted(raw[(c, v)] for c in burst_cells)
        p6 = min(1.0, 5.0 * ps[5])
        ent.add(f"hB1.{v}.n_cells_gain_3pts", len(ok), "cells", "gain of at least 3 points with the interval above zero")
        ent.add(f"hB1.{v}.p_conjunction", round(p6, 4), "probability", "five times the sixth smallest of the ten one-sided p-values")
        mg = float(np.mean([gains[(c, v)][0] for c in burst_cells]))
        ent.add(f"hB1.{v}.mean_gain_burst_cells", round(mg, 5), "fraction")
        if len(ok) > best_n or (len(ok) == best_n and p6 < best_p):
            best_v, best_n, best_p = v, len(ok), p6
    ok_best = [c for c in burst_cells if gains[(c, best_v)][0] >= 0.03 and gains[(c, best_v)][1] > 0.0]
    only_weakest = len(ok_best) > 0 and set(ok_best) <= {weakest}
    b1 = best_n >= 6 and not only_weakest
    ent.add("hB1.best_variant", best_v, "variant")
    ent.add("hB1.criterion_met", int(b1), "flag", "at least one variant with a gain of 3 points and an interval above zero in at least 6 of the 10 burst cells, not only in the weakest-baseline cell")
    ent.add("hB1.p_raw", round(best_p, 4), "probability", "of the variant with the most such cells")
    # ---- H-B2
    ps2, ok2, worst = [], True, 0.0
    ncheck = 0
    for cell in [c for c in cl if c["group"] in ("steady", "single")]:
        for v in VARIANTS:
            for m, sign in (("reach10_critical", -1.0), ("mis_triage", 1.0)):
                g, dr, n = gain_stats(R, cell["name"], f"M[{v}]", v, m)
                if np.isnan(g):
                    continue
                harm = sign * dr
                up = float(np.nanquantile(harm, 0.95))
                ps2.append(float(max(np.mean(harm >= 0.02), 1.0 / 1001)))
                ok2 = ok2 and up < 0.02
                worst = max(worst, sign * g)
                ncheck += 1
                ent.add(f"hB2.{cell['name']}.{v}.{m}.harm_upper95", round(up, 5), "fraction", "upper end of the one-sided 95% bound of the harm (baseline minus variant for reach; variant minus baseline for mis-triage)")
    ent.add("hB2.n_tests", ncheck, "tests")
    ent.add("hB2.worst_point_harm", round(worst, 5), "fraction")
    ent.add("hB2.criterion_met", int(ok2), "flag", "every upper 95% bound of the harm is below 2 points")
    ent.add("hB2.p_raw", round(max(ps2), 4), "probability", "largest of the one-sided non-inferiority p-values (intersection test)")
    # ---- H-B3
    mg = {v: float(np.mean([gains[(c, v)][0] for c in burst_cells])) for v in VARIANTS}
    top = max(mg.values())
    ent.add("hB3.best_mean_gain", round(top, 5), "fraction")
    ent.add("hB3.bucket_mean_gain", round(mg["V2"], 5), "fraction")
    ent.add("hB3.evaluable", int(b1), "flag", "decided only if H-B1 holds")
    ent.add("hB3.criterion_met", int(b1 and top > 0 and mg["V2"] >= 0.8 * top), "flag", "token-bucket mean gain at least 80% of the best variant's")
    n_beats = {v: sum(1 for c in cl if gains.get((c["name"], v), (0, -1, 0))[1] > 0) for v in VARIANTS}
    for v in VARIANTS:
        ent.add(f"cells_beating_matched.{v}", n_beats[v], "cells", "of 18 cells: whole interval above zero in critical reach within 10 s")
    ent.flush()
    pd.DataFrame([dict(h="H-B1", p=best_p), dict(h="H-B2", p=max(ps2))]).to_csv(C.TABLES / "v2_b_pvalues.csv", index=False)
    print("tuned", chosen)
    print("best variant", best_v, best_n, "of 10; B1", b1, "p", best_p, "| B2", ok2, "worst harm", round(worst, 4), "p", round(max(ps2), 4), "| B3", mg)
    summ = R.groupby(["cell", "cfg"]).reach10_critical.mean().unstack().round(3)
    pd.set_option("display.width", 250)
    print(summ.to_string())


if __name__ == "__main__":
    main()
