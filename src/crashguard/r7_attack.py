"""Round 7 A1.5 and H-R7-A1 (docs/02_preregistration/PREREGISTRATION_V18.md section 2.4): ACK suppression against the old and the reserved policy, SIMULATED with ``r7_engine``.

    python -m crashguard.r7_attack          # writes keys r7.a1.sim.* and results/tables/r7_attack_cells.json

Cells: SF 7, 8, 9 x duty models H1, H10, T10 x policy old, reserved. Primary stress: q = 1 (every ACK suppressed) and n_prior = n*_old(SF, d) earlier fully suppressed two-stage events in the preceding hour
(H models); the target event is drawn from the stored event rows with E = 1. 6 seed sets (42, 0 to 4) of 200 runs. Descriptive companions: n_prior in {0, ceil(n*/2), 2 n*}, q = 0.5, k = 2.
"""
from __future__ import annotations

import json
import math
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from crashguard import r7_analytic as AN
from crashguard import r7_engine as E
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7_attack.py"
EVENTS = ROOT / "results" / "tables" / "s6_events_seed42_a1.csv"
SEEDS = (42, 0, 1, 2, 3, 4)
RUNS_PER_SEED = 200
T0 = 3600.0
SFS = (7, 8, 9)
MODELS = ("H1", "H10", "T10")


def load_rows() -> tuple[list, list]:
    ev = pd.read_csv(EVENTS)
    tr = ev[ev.triggered]
    rows = [(bool(e), bool(f), int(y), float(t) / 1000.0) for e, f, y, t in zip(tr.alarm_E, tr.alarm_F, tr.y, tr.time_ms)]
    targets = [r for r in rows if r[0]]
    priors = [r for r in rows if r[0] and r[1]]
    return targets, priors


def duty_for(model: str) -> E.Duty:
    kind, allow = AN.MODELS[model]
    return E.Duty(kind, allow or 0.0)


def prior_times(n: int, gap: float, rng: random.Random) -> list[float] | None:
    span = T0 - (gap + 1.0) - (n - 1) * gap
    if n == 0:
        return []
    if span < 0:
        return None
    u = sorted(rng.random() * span for _ in range(n))
    return [u[i] + i * gap for i in range(n)]


def one_run(sf: int, model: str, policy: str, n_prior: int, q: float, k: int, seed: int, run: int, targets: list, priors: list, n_res: int = 1) -> dict:
    rng = random.Random(f"r7|{seed}|{sf}|{model}|{n_prior}|{q}|{run}")  # the same draws for both policies (paired)
    gap = AN.event_duration_old(sf) + 1.0
    times = prior_times(n_prior, gap, rng) if model != "T10" else []
    if times is None:
        return dict(feasible=False)
    rows = [priors[rng.randrange(len(priors))] for _ in times]
    tgt = targets[rng.randrange(len(targets))]
    ack_rng = random.Random(f"r7ack|{seed}|{sf}|{model}|{n_prior}|{q}|{run}")
    duty = duty_for(model)
    busy = -math.inf
    dropped = 0
    ack_ok = lambda i: ack_rng.random() >= q  # noqa: E731
    for t, (e, f, _y, te) in zip(times, rows):
        if t < busy:
            dropped += 1
            continue
        o = E.run_event(E.Spec(e, f, te, sf, policy, k, n_res=n_res), duty, t, lambda i: True, ack_ok)
        busy = o["end"]
    e, f, _y, te = tgt
    dm = AN.d_max(sf, model, k)["first"]
    if T0 < busy:
        return dict(feasible=True, target_dropped=True, ok=False, delay=math.inf, dmax=dm, deliv10=False, prior_dropped=dropped)
    o = E.run_event(E.Spec(e, f, te, sf, policy, k, n_res=n_res), duty, T0, lambda i: True, ack_ok)
    delay = o["follow_delay"]
    a_first = E.air(97 if f else 14, sf)
    return dict(feasible=True, target_dropped=False, ok=bool(delay <= dm + 1e-9), delay=delay, dmax=dm, deliv10=bool(o["follow_start"] + a_first <= T0 + 10.0), prior_dropped=dropped)


def cell(args: tuple) -> dict:
    sf, model, policy, n_prior, q, k, *rest = args
    n_res = rest[0] if rest else 1
    targets, priors = load_rows()
    res = [one_run(sf, model, policy, n_prior, q, k, s, r, targets, priors, n_res) for s in SEEDS for r in range(RUNS_PER_SEED)]
    if not res[0]["feasible"] or not all(r["feasible"] for r in res):
        return dict(sf=sf, model=model, policy=policy, n_prior=n_prior, q=q, k=k, feasible=False)
    n = len(res)
    x = sum(r["ok"] for r in res)
    d = np.array([r["delay"] for r in res])
    fin = d[np.isfinite(d)]
    lo = float(stats.beta.ppf(0.05, x, n - x + 1)) if x > 0 else 0.0
    return dict(sf=sf, model=model, policy=policy, n_prior=n_prior, q=q, k=k, n_res=n_res, feasible=True, n=n, ok=int(x), rate=x / n, lo95=lo,
                p_ge_099=float(stats.binom.sf(x - 1, n, 0.99)) if x > 0 else 1.0, dmax=res[0]["dmax"],
                delay_median=float(np.median(fin)) if len(fin) else None, delay_p95=float(np.percentile(fin, 95)) if len(fin) else None,
                never_sent_share=float(1 - len(fin) / n), target_dropped_share=float(np.mean([r["target_dropped"] for r in res])),
                deliv10_rate=float(np.mean([r["deliv10"] for r in res])), prior_dropped_mean=float(np.mean([r["prior_dropped"] for r in res])))


def jobs() -> list[tuple]:
    J = []
    for sf in SFS:
        for m in MODELS:
            allow = AN.MODELS[m][1]
            ns = AN.n_star(sf, allow) if allow else 0
            stress = [(ns, 1.0, 4)] if allow else [(0, 1.0, 4)]
            extra = ([(0, 1.0, 4), (math.ceil(ns / 2), 1.0, 4), (2 * ns, 1.0, 4), (ns, 0.5, 4), (ns, 1.0, 2)] if allow else [(0, 0.5, 4), (0, 1.0, 2)])
            for pol in ("old", "reserved"):
                for (n_prior, q, k) in stress + extra:
                    J.append((sf, m, pol, n_prior, q, k))
    return J


def main(record_only: bool = False) -> None:
    if record_only:
        res = json.loads((ROOT / "results" / "tables" / "r7_attack_cells.json").read_text(encoding="utf-8"))
    else:
        J = jobs()
        with ProcessPoolExecutor(14) as ex:
            res = list(ex.map(cell, J, chunksize=1))
        (ROOT / "results" / "tables").mkdir(parents=True, exist_ok=True)
        (ROOT / "results" / "tables" / "r7_attack_cells.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    ent: list[dict] = []

    def add(name, v, unit, note="", origin="SIMULATED"):
        ent.append(dict(name=f"r7.a1.sim.{name}", value=(round(v, 6) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin=("NOT_RUN" if v == "NOT_RUN" else origin), source_file=SRC, notes=note))

    for r in res:
        nstar = AN.n_star(r["sf"], AN.MODELS[r["model"]][1]) if AN.MODELS[r["model"]][1] else 0
        tag = "primary" if (r["q"] == 1.0 and r["k"] == 4 and r["n_prior"] == nstar) else f"n{r['n_prior']}.q{r['q']}.k{r['k']}"
        base = f"{r['model']}.sf{r['sf']}.{r['policy']}.{tag}"
        if not r["feasible"]:
            add(f"{base}.status", "INFEASIBLE", "status", f"{r['n_prior']} earlier events do not fit in one hour at the minimum gap")
            continue
        for key, unit in (("rate", "fraction"), ("lo95", "fraction"), ("p_ge_099", "p"), ("delay_median", "s"), ("delay_p95", "s"), ("never_sent_share", "fraction"), ("target_dropped_share", "fraction"), ("deliv10_rate", "fraction"), ("n", "runs"), ("ok", "runs"), ("dmax", "s")):
            add(f"{base}.{key}", r[key] if r[key] is not None else "NOT_RUN", unit, "rate of runs in which the follow-up starts within D_max of becoming pending" if key == "rate" else ("no run sent the follow-up, so the delay is undefined" if r[key] is None else ""))
    record_many(ent, purge_prefixes=("r7.a1.sim.",))
    print(len(ent), "keys", len(res), "cells")




def posthoc() -> None:
    """EXPLORATORY, after the registered run (not preregistered, outside the Holm family): the reserve sized for n_res events, R = n_res k A97 + A_M, H1 and H10, primary stress. Keys r7.a1.posthoc.*."""
    J = []
    for sf in SFS:
        for m in ("H1", "H10"):
            allow = AN.MODELS[m][1]
            ns = AN.n_star(sf, allow)
            for nr in (1, 2, 4, 8, 16, ns):
                J.append((sf, m, "reserved", ns, 1.0, 4, nr))
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(cell, J, chunksize=1))
    (ROOT / "results" / "tables" / "r7_attack_posthoc.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    ent = []
    for r in res:
        if not r["feasible"]:
            continue
        base = f"r7.a1.posthoc.{r['model']}.sf{r['sf']}.nres{r['n_res']}"
        for key, unit in (("rate", "fraction"), ("lo95", "fraction"), ("delay_median", "s")):
            v = r[key]
            ent.append(dict(name=f"{base}.{key}", value=(round(v, 6) if isinstance(v, float) else (v if v is not None else "NOT_RUN")), unit=unit, origin="SIMULATED", source_file=SRC, notes="EXPLORATORY, post-run, not preregistered; reserve sized for n_res events"))
    record_many(ent, purge_prefixes=("r7.a1.posthoc.",))
    print(len(ent), "posthoc keys")


if __name__ == "__main__":
    import sys

    posthoc() if len(sys.argv) > 1 and sys.argv[1] == "posthoc" else main(record_only=len(sys.argv) > 1 and sys.argv[1] == "record")
