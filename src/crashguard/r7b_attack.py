"""Round 7b H-R7b-1 (docs/02_preregistration/PREREGISTRATION_V19.md section 2): ACK suppression against the old policy and the reserved policy with a reserve for k = 1 to 4 follow-up events, fresh seeds. SIMULATED.

    python -m crashguard.r7b_attack          # keys r7b.a1.sim.*, results/tables/r7b_attack_cells.json

Same engine and cells as ``r7_attack`` (SF 7 to 9, H1, H10, T10, q = 1, primary stress n_prior = n*_old); seeds 100 to 105 (V18 used 42 and 0 to 4), 200 runs each. The k = 4 policy is the registered one; k = 1 to 3 and old are descriptive.
"""
from __future__ import annotations

import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from crashguard import r7_analytic as AN
from crashguard import r7_attack as A
from crashguard.results import record_many

A.SEEDS = (100, 101, 102, 103, 104, 105)  # applied again in every worker process when this module is imported there
ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7b_attack.py"
POLICIES = (("old", "old", 1), ("res1", "reserved", 1), ("res2", "reserved", 2), ("res3", "reserved", 3), ("res4", "reserved", 4))


def cell(args: tuple) -> dict:
    sf, model, label, n_prior = args
    pol, n_res = next((p, n) for (lb, p, n) in POLICIES if lb == label)
    r = A.cell((sf, model, pol, n_prior, 1.0, 4, n_res))
    r["label"] = label
    return r


def main() -> None:
    jobs = []
    for sf in A.SFS:
        for m in A.MODELS:
            allow = AN.MODELS[m][1]
            ns = AN.n_star(sf, allow) if allow else 0
            for (label, _p, _n) in POLICIES:
                jobs.append((sf, m, label, ns))
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(cell, jobs, chunksize=1))
    (ROOT / "results" / "tables" / "r7b_attack_cells.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r7b.a1.sim.{name}", value=(round(v, 6) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin=("NOT_RUN" if v == "NOT_RUN" else "SIMULATED"), source_file=SRC, notes=note))

    worst_p, worst_lo, feas = 0.0, 1.0, 0
    for r in res:
        base = f"{r['model']}.sf{r['sf']}.{r['label']}"
        if not r["feasible"]:
            add(f"{base}.status", "INFEASIBLE", "status", f"{r['n_prior']} earlier events do not fit in one hour")
            continue
        for key, unit in (("rate", "fraction"), ("lo95", "fraction"), ("p_ge_099", "p"), ("delay_median", "s"), ("never_sent_share", "fraction"), ("target_dropped_share", "fraction"), ("n", "runs"), ("ok", "runs"), ("dmax", "s")):
            add(f"{base}.{key}", r[key] if r[key] is not None else "NOT_RUN", unit)
        if r["label"] == "res4":
            feas += 1
            worst_p = max(worst_p, r["p_ge_099"])
            worst_lo = min(worst_lo, r["lo95"])
    add("hR7b_1.n_feasible_cells", feas, "cells")
    add("hR7b_1.worst_lower_limit", worst_lo, "fraction", "smallest lower 95% Clopper-Pearson limit over the feasible cells, k = 4 policy")
    add("hR7b_1.criterion_met", int(worst_lo >= 0.99), "flag", "lower limit at least 0.99 in every feasible cell")
    add("hR7b_1.p", worst_p, "p-value", "worst feasible cell, one-sided exact binomial p-value of rate <= 0.99")
    record_many(ent, purge_prefixes=("r7b.a1.sim.",))
    print({e["name"]: e["value"] for e in ent if "hR7b_1" in e["name"] or ("res4" in e["name"] and e["name"].endswith(".rate")) or (".old." in e["name"] and e["name"].endswith(".rate")) or ("res1" in e["name"] and e["name"].endswith(".rate"))})


if __name__ == "__main__":
    main()
