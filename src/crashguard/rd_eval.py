"""Evaluation harness of the redesign round (docs/02_preregistration/PREREGISTRATION_V12.md): grids, policy builders, per-event extraction and the paired statistics. SIMULATED.

A task runs one cell for a list of policies and hours inside a worker process that loads the class pools and the D1 tables once. Per run it returns, for every crash alert whose TRUE class is Severe or Critical,
the arrays (hour, alert id, true class, delay from the crash to base reception, NaN if never received) and the run-level counters. Policies share the arrival process of a cell and hour, so events pair by (hour, id).
"""
from __future__ import annotations

import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from crashguard import rd_policy as RP
from crashguard.rd_common import _cluster_sums, paired_cluster_test, paired_event_test

DEADLINE = np.array([0.0, 0.0, 30.0, 10.0])  # by true class
POLICIES = ("P1", "P0", "P4", "quick", "tamang", "khan", "D1", "D1D2")
POLICIES_B = ("D1D2", "D3")  # session 2: D3 against the frozen D1 + D2
BASELINES = ("P1", "P4", "P0", "quick", "tamang", "khan")
DEV = dict(n=(80, 180), p=(0.15, 0.35, 0.55), sf=(8, 10), duty=(0.01, 0.002), b=(1, 25), seed=31000, hours=100)
TAMANG_K = 8  # chosen on the old design grid (pa_design.json); the burst size is given as the oracle estimate


def cells_of(g: dict) -> list[dict]:
    out = []
    for n, p, sf, d, b in itertools.product(g["n"], g["p"], g["sf"], g["duty"], g["b"]):
        out.append(dict(name=f"n{n}_p{int(round(p * 100))}_sf{sf}_d{d * 100:g}_b{b}", n=n, p=p, sf=sf, duty=d, b=b))
    return out


# ------------------------------------------------------------------------------------------------ worker
CTX: dict = {}


def _init(params: dict) -> None:
    from crashguard import fin_g as G
    from crashguard import fin_sim as FS
    from crashguard import pa_sim as PA

    CTX.update(G=G, FS=FS, PA=PA, t=FS.tuned(), pools=PA.pools_real(), params=params, tables={})
    CTX["tamang_k"] = TAMANG_K


def d1_table(sf: int) -> RP.D1Table:
    tabs = CTX["tables"]
    if sf not in tabs:
        tabs[sf] = RP.D1Table(sf, RP.D1Params(**CTX["params"]["d1"]))
    return tabs[sf]


def make_cfg(pol: str, cell: dict, seed: int, hour: int):
    G, PA, t, pools = CTX["G"], CTX["PA"], CTX["t"], CTX["pools"]
    label = f"g_{cell['name']}"
    base_world = G.WORLD
    if pol in ("P1", "P0", "P4"):
        return G.cfg_for(pol, cell, seed, hour, pools, t, label, base_world)
    if pol == "quick":
        return G.cfg_for("P2", cell, seed, hour, pools, t, label, base_world, dict(spacing_crit=0.3, spacing_sev=0.3))
    if pol == "tamang":
        spec = dict(kind="tamang", k_cap=CTX["tamang_k"])
        return G.cfg_for(PA.spec_pol(spec), cell, seed, hour, pools, t, label, PA.spec_world(spec, cell))
    if pol == "khan":
        cl = pools["classes"][16.0]
        pk = {**pools, "classes": {**pools["classes"], 16.0: {**cl, "point": np.full_like(cl["point"], 3)}}}
        over = dict(hold_all=0.0, flash=False, sf_raise=False, preempt=False, reserve=False, max_tries=(9, 9, 9, 9))
        return G.cfg_for("P2", cell, seed, hour, pk, t, label, {**base_world, "rd": dict(khan=(1.0, 3.0))}, over)
    if pol == "nessa":  # ADDED-AFTER-SESSION-1 (V12 11.1): class-agnostic like the Khan-style baseline
        cl = pools["classes"][16.0]
        pk = {**pools, "classes": {**pools["classes"], 16.0: {**cl, "point": np.full_like(cl["point"], 3)}}}
        over = dict(hold_all=0.0, flash=False, sf_raise=False, preempt=False, reserve=False, max_tries=(12, 12, 12, 12))
        nz = CTX["params"]["nessa"]
        return G.cfg_for("P2", cell, seed, hour, pk, t, label, {**base_world, "rd": dict(nessa=dict(k=nz["k"], A=nz["A"]))}, over)
    if pol in ("D1", "D1D2", "D3"):
        rd = dict(d1_table=d1_table(cell["sf"]), d1_params=RP.D1Params(**CTX["params"]["d1"]))
        if pol in ("D1D2", "D3"):
            rd["d2"] = dict(CTX["params"]["d2"])
        if pol == "D3":
            from crashguard import rd_d3 as D3  # session 2 (addendum B): D3 = D1 + D2 + slotted retries

            rd["d3"] = D3.D3Params(**CTX["params"]["d3"])
        if CTX["params"].get("trace"):
            rd["trace"] = CTX["params"]["trace"]
        return G.cfg_for("P4", cell, seed, hour, pools, t, label, {**base_world, "rd": rd}, dict(fast_cap=None))
    raise ValueError(pol)


def _events(diag: list[dict], hour: int) -> dict:
    rows = [(hour, a["id"], a["true"], (a["t_rx"] - a["arrival"]) if a["t_rx"] is not None else np.nan) for a in diag if a["kind"] == "crash" and a["true"] >= 2]
    arr = np.array(rows, float).reshape(-1, 4)
    return dict(hour=arr[:, 0].astype(np.int32), aid=arr[:, 1].astype(np.int32), true=arr[:, 2].astype(np.int8), delay=arr[:, 3].astype(np.float64))


def run_task(task: tuple) -> dict:
    from crashguard import world_sim as W

    cell, pols, seed0, h0, h1, invariants = task
    out: dict = {}
    for pol in pols:
        evs, runs = [], []
        for h in range(h0, h1):
            diag: list = []
            r = W.simulate(make_cfg(pol, cell, seed0, h), diag=diag, invariants=invariants)
            evs.append(_events(diag, h))
            runs.append((h, int(r["duty_exceeded"]), float(r["node_air_share"]), float(r["max_window_airtime_s"]), float(r.get("cluster_ack_air_s", 0.0)), float(r.get("alert_collided_share", 0.0))))
        out[pol] = dict(ev={k: np.concatenate([e[k] for e in evs]) for k in evs[0]}, runs=np.array(runs, float))
    return dict(cell=cell["name"], res=out)


def run_grid(cells: list[dict], pols: tuple, seed0: int, hours: int, params: dict, workers: int | None = None, invariants: bool = True, chunk: int = 50) -> dict:
    tasks = [(c, pols, seed0, h0, min(h0 + chunk, hours), invariants) for c in cells for h0 in range(0, hours, chunk)]
    workers = workers or min(14, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(params,)) as ex:
        parts = list(ex.map(run_task, tasks, chunksize=1))
    res: dict = {}
    for part in parts:
        d = res.setdefault(part["cell"], {})
        for pol, v in part["res"].items():
            if pol not in d:
                d[pol] = dict(ev={k: [x] for k, x in v["ev"].items()}, runs=[v["runs"]])
            else:
                for k, x in v["ev"].items():
                    d[pol]["ev"][k].append(x)
                d[pol]["runs"].append(v["runs"])
    for d in res.values():
        for pol, v in d.items():
            v["ev"] = {k: np.concatenate(x) for k, x in v["ev"].items()}
            v["runs"] = np.concatenate(v["runs"])
            o = np.lexsort((v["ev"]["aid"], v["ev"]["hour"]))
            v["ev"] = {k: x[o] for k, x in v["ev"].items()}
    return res


# ------------------------------------------------------------------------------------------------ metrics
def metric(ev: dict, kind: str) -> np.ndarray:
    """Per-event 0/1 arrays. 'deadline': received before the own class deadline (Critical 10 s, Severe 30 s); 'final': received at any time; 'crit10': Critical only, received within 10 s (NaN for Severe)."""
    d = ev["delay"]
    if kind == "deadline":
        return (d <= DEADLINE[ev["true"]]).astype(float)
    if kind == "final":
        return (~np.isnan(d)).astype(float)
    if kind == "crit10":
        return np.where(ev["true"] == 3, (d <= 10.0).astype(float), np.nan)
    raise ValueError(kind)


def paired(res_cell: dict, a: str, b: str, kind: str) -> np.ndarray:
    """b minus a per event (aligned by hour and alert id)."""
    ea, eb = res_cell[a]["ev"], res_cell[b]["ev"]
    assert np.array_equal(ea["hour"], eb["hour"]) and np.array_equal(ea["aid"], eb["aid"]) and np.array_equal(ea["true"], eb["true"]), "policies do not share the event set"
    return metric(eb, kind) - metric(ea, kind)


def best_baseline(res_cell: dict, kind: str) -> str:
    return max(BASELINES, key=lambda p: float(np.nanmean(metric(res_cell[p]["ev"], kind))))


def test_cell(res_cell: dict, a: str, b: str, kind: str, margin: float) -> dict:
    """Per-cell one-sided test of 'b minus a > margin'. The preregistered event bootstrap and the hour-clustered bootstrap are both computed; the verdict uses the more conservative of the two (the larger p, the
    smaller lower bound). Both are returned."""
    d = paired(res_cell, a, b, kind)
    ev = paired_event_test(d, margin)
    cl = paired_cluster_test(d, res_cell[a]["ev"]["hour"], margin)
    return dict(n=ev["n"], pt=ev["pt"], p=max(ev["p"], cl["p"]), lb95=min(ev["lb95"], cl["lb95"]), lo=min(ev["lo"], cl["lo"]), hi=max(ev["hi"], cl["hi"]), p_event=ev["p"], p_cluster=cl["p"], lb95_event=ev["lb95"], lb95_cluster=cl["lb95"])


def pooled_boot(items: list, margin: float, seed: int = 42, nb: int = 2000) -> dict:
    """Mean over cells of the per-cell mean difference. ``items`` = list of (res_cell, a, b, kind). Two bootstraps: events resampled within each cell (preregistered) and simulated hours resampled within each
    cell (cluster); the verdict uses the more conservative."""
    out = {}
    for mode in ("event", "cluster"):
        rng = np.random.default_rng(seed)
        boots, pts = np.zeros(nb), []
        for rc, a, b, kind in items:
            d = paired(rc, a, b, kind)
            if mode == "event":
                d = d[~np.isnan(d)]
                idx = rng.integers(0, len(d), (nb, len(d)))
                boots += d[idx].mean(1)
                pts.append(d.mean())
            else:
                S, C = _cluster_sums(d, rc[a]["ev"]["hour"])
                idx = rng.integers(0, len(S), (nb, len(S)))
                boots += S[idx].sum(1) / C[idx].sum(1)
                pts.append(S.sum() / C.sum())
        boots /= len(items)
        out[mode] = dict(pt=float(np.mean(pts)), lo=float(np.quantile(boots, 0.025)), hi=float(np.quantile(boots, 0.975)), p=float((boots <= margin).sum() + 1) / (nb + 1))
    return dict(cells=len(items), pt=out["event"]["pt"], lo=min(out["event"]["lo"], out["cluster"]["lo"]), hi=max(out["event"]["hi"], out["cluster"]["hi"]), p=max(out["event"]["p"], out["cluster"]["p"]),
                p_event=out["event"]["p"], p_cluster=out["cluster"]["p"], lo_event=out["event"]["lo"], lo_cluster=out["cluster"]["lo"])


def per_cell(res: dict, a: str, b: str, kind: str, margin: float) -> dict:
    return {c: test_cell(r, a, b, kind, margin) for c, r in res.items()}


def duty_ok(res: dict, pol: str) -> tuple[int, int]:
    n = sum(len(r[pol]["runs"]) for r in res.values())
    viol = int(sum(r[pol]["runs"][:, 1].sum() for r in res.values()))
    return viol, n


def save_params(path: str, params: dict) -> None:
    Path(path).write_text(json.dumps(params, indent=1, sort_keys=True), encoding="utf-8")
