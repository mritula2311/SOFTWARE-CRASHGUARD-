"""FRESH-A: freeze, grid draw and the single run of D1 and D2 (docs/02_preregistration/PREREGISTRATION_V12.md sections 1, 3, 5 and 6). Keys ``rd.fa.*``.

    python -m crashguard.rd_fresh_a freeze    # picks the DEV iterations by the preregistered objectives and writes results/tables/rd_frozen_A.json with code hashes; commit it
    python -m crashguard.rd_fresh_a draw      # draws the FRESH-A grid from the SHA-256 of the freeze file and writes results/tables/rd_fresh_A_grid.json with its hash; commit it
    python -m crashguard.rd_fresh_a run       # ONE run on the grid; refuses to run twice

The run refuses to start unless the freeze file matches the current code hashes and the grid file matches its recorded hash.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from crashguard import rd_dev as DEV
from crashguard import rd_eval as E
from crashguard.rd_common import Rec, holm, sha256_file

FROZEN = Path("results/tables/rd_frozen_A.json")
GRID = Path("results/tables/rd_fresh_A_grid.json")
DONE = Path("results/tables/rd_fresh_A_done.json")
CODE = tuple(f"src/crashguard/{m}.py" for m in ("rd_policy", "world_sim", "rd_eval", "rd_d2_model", "rd_common", "rd_fresh_a", "rd_dev", "fin_g", "fin_sim", "pa_sim", "s11_sct", "sct_sim", "lora", "capacity", "packet", "replay"))
HOURS = 600
SRC = "src/crashguard/rd_fresh_a.py"


def code_hashes() -> dict:
    return {f: sha256_file(f) for f in CODE}


def freeze() -> None:
    if FROZEN.exists():
        raise SystemExit("already frozen")
    p1, p2 = DEV.pick("D1"), DEV.pick("D2")
    params = dict(d1=p2["d1"], d2=p2["d2"])
    assert p1["d1"] == p2["d1"], "D2 was developed on a different D1 than the picked one"
    FROZEN.write_text(json.dumps(dict(params=params, code=code_hashes(), dev_log_sha256=sha256_file(DEV.LOG), dev_base_note="baselines run on the DEV grid before any redesign iteration"), indent=1, sort_keys=True), encoding="utf-8")
    print("frozen", sha256_file(FROZEN))


def draw() -> None:
    if GRID.exists():
        raise SystemExit("grid already drawn")
    fh = sha256_file(FROZEN)
    rng = np.random.default_rng(int(fh[:12], 16))
    n_lo, n_hi = int(rng.integers(55, 96)), int(rng.integers(180, 261))
    ps = [round(float(b + rng.uniform(-0.03, 0.03)), 2) for b in (0.15, 0.30, 0.45, 0.60)]
    burst = int(rng.integers(18, 27))
    seed0 = 400000 + int(fh[12:18], 16) % 100000
    grid = dict(n=[n_lo, n_hi], p=ps, sf=[9, 11], duty=[0.005, 0.10], b=[1, burst], seed=seed0, hours=HOURS, freeze_sha256=fh)
    GRID.write_text(json.dumps(grid, indent=1, sort_keys=True), encoding="utf-8")
    print("grid", grid, "sha256", sha256_file(GRID))


def run() -> None:
    if DONE.exists():
        raise SystemExit("FRESH-A has been run once; it is not run again")
    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert fz["code"] == code_hashes(), "code changed after the freeze"
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    assert grid["freeze_sha256"] == sha256_file(FROZEN)
    cells = E.cells_of(grid)
    DONE.write_text(json.dumps(dict(started=True, grid_sha256=sha256_file(GRID), frozen_sha256=sha256_file(FROZEN))), encoding="utf-8")  # written before the run so that a crash cannot lead to a second look
    res = E.run_grid(cells, E.POLICIES, grid["seed"], grid["hours"], fz["params"])
    import pickle

    with open("data/processed/rd_fresh_A_results.pkl", "wb") as fh:
        pickle.dump(res, fh)
    analyse(res, cells, grid)


def analyse(res: dict, cells: list[dict], grid: dict, write: bool = True) -> dict:
    rec = Rec("rd.fa.", SRC)
    names = [c["name"] for c in cells]
    cell_p = {c["name"]: c["p"] for c in cells}
    burst = [c["name"] for c in cells if c["b"] >= 10]
    rows = []
    # H-D1a and H-D1s
    d1a = {c: E.test_cell(res[c], "P1", "D1", "deadline", -0.01) for c in names}
    best = {c: E.best_baseline(res[c], "deadline") for c in names}
    d1s = {c: E.test_cell({"b": res[c][best[c]], "D1": res[c]["D1"]}, "b", "D1", "deadline", -0.02) for c in names}
    # H-D1b
    hi = [c for c in names if cell_p[c] >= 0.40]
    d1b = E.pooled_boot([(res[c], "P1", "D1", "deadline") for c in hi], 0.05)
    # H-D1c
    viol, N = E.duty_ok(res, "D1")
    p_c = float(0.999 ** N) if viol == 0 else 1.0
    # H-D2a, H-D2b
    d2a = {c: E.test_cell(res[c], "D1", "D1D2", "final", -0.02) for c in names}
    d2b = E.pooled_boot([(res[c], "D1", "D1D2", "crit10") for c in burst], 0.05)
    viol2, N2 = E.duty_ok(res, "D1D2")
    for c in names:
        rows.append(dict(cell=c, p=cell_p[c], burst=int(c in burst), events=d1a[c]["n"], d1_minus_p1=d1a[c]["pt"], d1_minus_p1_lb95=d1a[c]["lb95"], best_baseline=best[c], d1_minus_best=d1s[c]["pt"], d1_minus_best_lb95=d1s[c]["lb95"],
                         d2_minus_d1_final=d2a[c]["pt"], d2_minus_d1_final_lb95=d2a[c]["lb95"]))
    import csv

    if write:
        with open("results/tables/rd_fresh_a_cells.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    # model check result for H-D2c
    allr = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith("rd.d2.model.hD2c")}
    crit = dict(
        D1a=all(v["lb95"] > -0.01 for v in d1a.values()), D1b=(d1b["pt"] >= 0.05 and d1b["p"] < 0.05), D1c=(viol == 0), D1s=all(v["lb95"] > -0.02 for v in d1s.values()),
        D2a=all(v["lb95"] > -0.02 for v in d2a.values()), D2b=(d2b["pt"] >= 0.05 and d2b["p"] < 0.05), D2c=bool(allr.get("rd.d2.model.hD2c.criterion_met", 0)))
    raw = dict(D1a=max(v["p"] for v in d1a.values()), D1b=d1b["p"], D1c=p_c, D1s=max(v["p"] for v in d1s.values()), D2a=max(v["p"] for v in d2a.values()), D2b=d2b["p"], D2c=float(allr.get("rd.d2.model.hD2c.p_raw", 1.0)),
               D3=1.0, D4a=1.0, D4b=1.0)  # the three hypotheses of FRESH-B are not run yet: provisional p = 1, the family stays at 10
    adj = holm(raw)
    for k in crit:
        verdict = "SUPPORTED" if (crit[k] and adj[k] < 0.05) else "NOT SUPPORTED"
        rec.add(f"{k}.criterion_met", int(crit[k]), "flag", "criterion of V12 section 6 met on FRESH-A")
        rec.add(f"{k}.p_raw", raw[k], "p", "per-cell largest p (intersection-union) or the pooled bootstrap p")
        rec.add(f"{k}.p_holm_provisional", adj[k], "p", "Holm over the family of 10 with the three FRESH-B hypotheses at p = 1 (provisional; final Holm after FRESH-B)")
        rec.add(f"{k}.verdict_provisional", verdict, "verdict", "SUPPORTED needs the criterion and a Holm-adjusted p below 0.05")
    rec.add("grid.cells", len(cells), "cells", f"FRESH-A grid {GRID}, SHA-256 {sha256_file(GRID) if GRID.exists() else None}")
    rec.add("grid.hours_per_cell", grid["hours"], "hours", "")
    rec.add("grid.sha256", sha256_file(GRID) if GRID.exists() else "n/a", "hash", "")
    rec.add("frozen.sha256", sha256_file(FROZEN) if FROZEN.exists() else "n/a", "hash", "")
    rec.add("d1a.min_cell_lb95", min(v["lb95"] for v in d1a.values()), "fraction", "smallest per-cell lower 95% bound of D1 minus P1")
    rec.add("d1a.min_cell_diff", min(v["pt"] for v in d1a.values()), "fraction", "smallest per-cell point difference D1 minus P1")
    rec.add("d1a.cells_failing", int(sum(v["lb95"] <= -0.01 for v in d1a.values())), "cells", "cells whose lower bound is not above -0.01")
    rec.add("d1b.cells", d1b["cells"], "cells", "cells with loss of 40% or more")
    for k in ("pt", "lo", "hi"):
        rec.add(f"d1b.{k}", d1b[k], "fraction", "pooled mean over cells of D1 minus P1; events resampled within cells; 95% interval")
    rec.add("d1c.runs", N, "runs", "D1 runs on the grid")
    rec.add("d1c.violations", viol, "runs", "runs with a trailing-hour airtime above the cell's duty limit")
    rec.add("d1s.min_cell_diff", min(v["pt"] for v in d1s.values()), "fraction", "smallest per-cell point difference D1 minus the best baseline of the cell")
    rec.add("d1s.cells_failing", int(sum(v["lb95"] <= -0.02 for v in d1s.values())), "cells", "cells whose lower bound is not above -0.02")
    rec.add("d1s.mean_diff", float(np.mean([v["pt"] for v in d1s.values()])), "fraction", "mean over cells of D1 minus the best baseline of each cell")
    for k in ("pt", "lo", "hi"):
        rec.add(f"d2b.{k}", d2b[k], "fraction", "pooled mean over burst cells of D1+D2 minus D1, Critical within 10 s; 95% interval")
    rec.add("d2b.cells", d2b["cells"], "cells", "burst cells")
    rec.add("d2a.min_cell_diff", min(v["pt"] for v in d2a.values()), "fraction", "smallest per-cell point difference D1+D2 minus D1, final delivery")
    rec.add("d2a.cells_failing", int(sum(v["lb95"] <= -0.02 for v in d2a.values())), "cells", "cells whose lower bound is not above -0.02")
    rec.add("d2c.duty_violations", viol2, "runs", f"D1+D2 runs with a duty exceed, of {N2}")
    # means by policy for the decision table
    for pol in E.POLICIES:
        m_dl = float(np.mean([np.nanmean(E.metric(res[c][pol]["ev"], "deadline")) for c in names]))
        m_c10 = float(np.mean([np.nanmean(E.metric(res[c][pol]["ev"], "crit10")) for c in burst]))
        rec.add(f"policy.{pol}.mean_deadline_delivery", m_dl, "fraction", "mean over cells, Critical and Severe delivered before the own deadline")
        rec.add(f"policy.{pol}.burst_mean_crit10", m_c10, "fraction", "mean over burst cells, Critical within 10 s")
    if write:
        rec.write()
    print(json.dumps({k: (int(crit[k]), round(raw[k], 4), round(adj[k], 4)) for k in crit}))
    return dict(rec=rec, crit=crit, raw=raw, adj=adj)


if __name__ == "__main__":
    {"freeze": freeze, "draw": draw, "run": run}[sys.argv[1]]()
