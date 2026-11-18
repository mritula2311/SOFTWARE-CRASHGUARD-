"""Shared simulation helpers of the finishing branch (SIMULATED): configs on ``world_sim``, parallel runs, paired per-cell statistics, p-value rule of docs/02_preregistration/PREREGISTRATION_V5.md section 0."""
from __future__ import annotations

import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import s11_sct as S
from crashguard import world_sim as W
from crashguard.sct_sim import SctParams as OldParams

NB = 1000
_N16 = S.n16_params()  # read once: s11_sct.make_cfg parses the 30 MB results file on every call otherwise
S.n16_params = lambda: _N16


def results_map() -> dict:
    return {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}


def tuned() -> dict:
    r = results_map()
    return dict(h_s=float(r["s11.tuned.h_s"]), rho_f=float(r["s11.tuned.rho_f"]), sf_raise=bool(r["s11.tuned.sf_raise"]), phi=float(r["s11.tuned.phi"]))


def p1plus_params(h_s: float, **over) -> W.SctParams:
    """P1+: severity table with flash and hold only (docs/02_preregistration/PREREGISTRATION_V5.md B2)."""
    d = dict(h_s=h_s, rho_f=0.0, sf_raise=False, preempt=False, flash=True, sev_hold=True, reserve=False, spacing_crit=0.0, spacing_sev=0.0, max_tries=(2, 4, 8, 12), p1_retry=True)
    d.update(over)
    return W.SctParams(**d)


def sct_params(t: dict, **over) -> W.SctParams:
    d = dict(h_s=t["h_s"], rho_f=t["rho_f"], sf_raise=t["sf_raise"])
    d.update(over)
    return W.SctParams(**d)


def lowered_pools(rg: float = 16.0) -> dict:
    """Pools like ``s11_sct.load_pools`` with the point class of the lowered-threshold table (factor f of t1, the escalation of P3) in place of the point class (P1e, P1+e)."""
    from crashguard import ua_core as U

    pools = S.load_pools()
    core = U.build()
    f = float(results_map()[f"t1.r{rg:g}.f"])
    pe = U.point_classes(core, rg, scale=f)
    point = U.interval_classes(core, rg, 0.10, "cc")["c_hat"]
    mask = point >= 0
    cl = pools["classes"][rg]
    assert (point[mask] == cl["point"]).all()
    pools = {**pools, "classes": {**pools["classes"], rg: {**cl, "lowered": pe[mask].astype(int)}}}
    return pools


def to_w(cfg) -> W.SCfg:
    return W.SCfg(**{**cfg.__dict__, "sct": W.SctParams(**cfg.sct.__dict__)})


def make_cfg(pol: str, rg: float, kw: dict, burst: bool, seed: int, hour: int, pools: dict, t: dict, label: str, extra: dict | None = None, world: dict | None = None, sct_over: dict | None = None) -> W.SCfg:
    """Policies: P0, P1, P1e, P1+, P1+e, sched, P2, P3, P4 (+ abstain 'P3b' only via pools with an 'abstain' class set)."""
    base = {"P1e": "P1", "P1+": "P2", "P1+e": "P2"}.get(pol, pol)
    pool = pools["classes"][rg]
    if pol in ("P1e", "P1+e"):
        pools = {**pools, "classes": {**pools["classes"], rg: {**pool, "point": pool["lowered"]}}}
    s11pol = base
    c = S.make_cfg(s11pol, rg, kw, burst, seed, hour, pools, OldParams(h_s=t["h_s"], rho_f=t["rho_f"], sf_raise=t["sf_raise"]), t["phi"] if pol == "P4" else None, label, extra)
    w = to_w(c)
    if pol in ("P1+", "P1+e"):
        w = W.SCfg(**{**w.__dict__, "sct": p1plus_params(t["h_s"], **(sct_over or {}))})
    elif sct_over:
        w = W.SCfg(**{**w.__dict__, "sct": W.SctParams(**{**w.sct.__dict__, **sct_over})})
    if world is not None:
        w = W.SCfg(**{**w.__dict__, "world": world})
    return w


def _run(args) -> dict:
    cfg, meta = args
    out = W.simulate(cfg)
    out.update(meta)
    return out


def run_jobs(jobs: list, workers: int | None = None) -> pd.DataFrame:
    workers = workers or min(14, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers) as ex:
        rows = list(ex.map(_run, jobs, chunksize=16))
    return pd.DataFrame(rows)


def boot_diff(d: np.ndarray, margin: float = 0.0, seed: int = C.SEED) -> dict:
    """Paired per-seed differences -> point, 95% interval, one-sided p-values P(mean <= margin) and P(mean <= -0.02) over 1,000 resamples of the seeds."""
    d = np.asarray(d, float)
    d = d[~np.isnan(d)]
    if len(d) < 3:
        return dict(n=len(d), pt=np.nan, lo=np.nan, hi=np.nan, p_gain=1.0, p_lose=1.0)
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (NB, len(d)))].mean(1)
    return dict(n=len(d), pt=float(d.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), p_gain=max(float((m <= margin).mean()), 0.001), p_lose=max(float((m <= -0.02).mean()), 0.001))


def cell_pair(R: pd.DataFrame, cell: dict, a: str, b: str, metric: str, margin: float = 0.05) -> dict:
    """b minus a on one cell (paired by hour)."""
    sub = R
    for k, v in cell.items():
        sub = sub[sub[k] == v]
    pa = sub[sub.pol == a].sort_values("hour")[metric].to_numpy(float)
    pb = sub[sub.pol == b].sort_values("hour")[metric].to_numpy(float)
    m = ~(np.isnan(pa) | np.isnan(pb))
    return boot_diff(pb[m] - pa[m], margin)


def gains(st: dict, margin: float = 0.05) -> bool:
    return bool(st["pt"] >= margin and st["lo"] > 0)


def loses(st: dict) -> bool:
    return bool(st["pt"] < -0.02)


def q_p(ps: list[float], share: float) -> float:
    """p-value of 'in at least ``share`` of the cells' (rule 5): the p-value of the cell at that quantile of the ascending per-cell p-values."""
    s = sorted(ps)
    return float(s[max(int(np.ceil(share * len(s))) - 1, 0)])


def verdict_cells(R: pd.DataFrame, cells: list[dict], a: str, b: str, metric: str, margin: float = 0.05, share: float = 0.60) -> dict:
    """Criterion of rules 4 and 5: ``b`` gains >= margin (interval excluding zero) in >= share of cells and loses by more than 2 points in none."""
    st = [cell_pair(R, c, a, b, metric, margin) for c in cells]
    n_gain = sum(gains(s, margin) for s in st)
    n_lose = sum(loses(s) for s in st)
    met = n_gain >= int(np.ceil(share * len(cells))) and n_lose == 0
    p = max(q_p([s["p_gain"] for s in st], share), max(s["p_lose"] for s in st))
    return dict(n_cells=len(cells), n_gain=n_gain, n_lose=n_lose, met=bool(met), p=p, stats=st)
