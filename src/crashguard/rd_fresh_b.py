"""FRESH-B: freeze, grid draw and the single run of D3 and H-D4a (docs/02_preregistration/PREREGISTRATION_V12.md addendum B, section 10.5). Keys ``rd.fb.*``.

    python -m crashguard.rd_fresh_b freeze    # picks the D3 DEV iteration by the preregistered objective, writes results/tables/rd_frozen_B.json with code hashes; commit it
    python -m crashguard.rd_fresh_b draw      # draws the FRESH-B grid from the SHA-256 of the freeze file, writes results/tables/rd_fresh_B_grid.json with its hash; commit it
    python -m crashguard.rd_fresh_b run       # ONE run; refuses to run twice

The run refuses to start unless the freeze file matches the current code hashes and the grid file matches the freeze. D1 and D2 parameters are those of FRESH-A (rd_frozen_A.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from crashguard import rd_d4 as D4
from crashguard import rd_dev_b as DB
from crashguard import rd_eval as E
from crashguard.rd_common import Rec, holm, sha256_file

FROZEN = Path("results/tables/rd_frozen_B.json")
GRID = Path("results/tables/rd_fresh_B_grid.json")
DONE = Path("results/tables/rd_fresh_B_done.json")
FROZEN_A = Path("results/tables/rd_frozen_A.json")
CODE = tuple(f"src/crashguard/{m}.py" for m in ("rd_policy", "world_sim", "rd_eval", "rd_d2_model", "rd_common", "rd_fresh_a", "rd_dev", "rd_dev_b", "rd_d3", "rd_d4", "rd_fresh_b", "rd_firmware", "fin_g", "fin_sim", "pa_sim", "s11_sct", "sct_sim", "lora", "capacity", "packet", "replay", "ar_r3")) + (
    "firmware_rd/cg_rd.c", "firmware_rd/cg_rd.h", "firmware_rd/cg_rd_cli.c", "firmware_rd/cg_stubs.c", "firmware_rd/tweetnacl.c", "firmware_rd/tweetnacl.h", "firmware_rd/build.sh", "firmware_rd/size.sh", "src/crashguard/results.py", "src/crashguard/ar_r1.py",
    "results/tables/s6_events_seed42_a1.csv", "data/processed/pa_held.pkl", "data/processed/pa_design.json")
HOURS = 300
SRC = "src/crashguard/rd_fresh_b.py"


def code_hashes() -> dict:
    return {f: sha256_file(f) for f in CODE}


def freeze() -> None:
    if FROZEN.exists():
        raise SystemExit("already frozen")
    try:
        p, floor_ok = DB.pick(), True
    except SystemExit:  # no iteration met the DEV floor: the last iteration goes forward and the floor failure is recorded in the freeze file
        rows = [r for r in DB.DV.log_rows() if r["algo"] == "D3"]
        p, floor_ok = json.loads(rows[-1]["params"]), False
    FROZEN.write_text(json.dumps(dict(dev_floor_met=floor_ok, params=p, code=code_hashes(), frozen_A_sha256=sha256_file(FROZEN_A), dev_log_sha256=sha256_file("results/tables/rd_dev_log.csv")), indent=1, sort_keys=True), encoding="utf-8")
    print("frozen", sha256_file(FROZEN))


def draw() -> None:
    if GRID.exists():
        raise SystemExit("grid already drawn")
    fh = sha256_file(FROZEN)
    rng = np.random.default_rng(int(fh[:12], 16))
    n_lo, n_hi = int(rng.integers(55, 96)), int(rng.integers(180, 261))
    ps = [round(float(b + rng.uniform(-0.03, 0.03)), 2) for b in (0.15, 0.30, 0.45, 0.60)]
    burst = int(rng.integers(18, 27))
    seed0 = 600000 + int(fh[12:18], 16) % 100000
    losses = sorted({round(float(x), 2) for x in rng.uniform(0.0, 0.7, 8)})
    while len(losses) < 8:
        losses = sorted(set(losses) | {round(float(rng.uniform(0.0, 0.7)), 2)})
    grid = dict(n=[n_lo, n_hi], p=ps, sf=[9, 11], duty=[0.005, 0.10], b=[burst], seed=seed0, hours=HOURS, d4_losses=losses, d4_sfs=[7, 8, 9, 10, 11, 12], freeze_sha256=fh)
    GRID.write_text(json.dumps(grid, indent=1, sort_keys=True), encoding="utf-8")
    print("grid", grid, "sha256", sha256_file(GRID))


def run() -> None:
    if DONE.exists():
        raise SystemExit("FRESH-B has been run once; it is not run again")
    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert fz["code"] == code_hashes(), "code changed after the freeze"
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    assert grid["freeze_sha256"] == sha256_file(FROZEN)
    cells = E.cells_of(grid)
    final_holm(0.5, 0.5)  # pre-flight: the stored raw p-values of FRESH-A must be readable before the single run is committed to
    D4.load_events()
    assert Path("data/processed/pa_held.pkl").exists()
    DONE.write_text(json.dumps(dict(started=True, grid_sha256=sha256_file(GRID), frozen_sha256=sha256_file(FROZEN))), encoding="utf-8")  # written before the run: a crash cannot lead to a second look
    ev4 = D4.load_events()
    d4 = D4.run_grid(ev4, grid["d4_sfs"], grid["d4_losses"])
    res = E.run_grid(cells, E.POLICIES_B, grid["seed"], grid["hours"], fz["params"])
    import pickle

    with open("data/processed/rd_fresh_B_results.pkl", "wb") as fh:
        pickle.dump(dict(res=res, d4=d4), fh)
    analyse(res, d4, cells, grid)


def final_holm(raw_d3: float, raw_d4a: float) -> tuple[dict, dict]:
    """One Holm family of ten: the seven hypotheses of FRESH-A (raw p-values stored by rd_fresh_a), H-D3, H-D4a and H-D4b (not run: p = 1)."""
    stored = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith("rd.fa.") and e["name"].endswith(".p_raw")}
    raw = {k: float(stored[f"rd.fa.{k}.p_raw"]) for k in ("D1a", "D1b", "D1c", "D1s", "D2a", "D2b", "D2c")}
    raw.update(D3=raw_d3, D4a=raw_d4a, D4b=1.0)
    return raw, holm(raw)


def analyse(res: dict, d4: dict, cells: list[dict], grid: dict, write: bool = True) -> dict:
    rec = Rec("rd.fb.", SRC)
    names = [c["name"] for c in cells]
    # H-D3
    g10 = E.pooled_boot([(res[c], "D1D2", "D3", "crit10") for c in names], 0.05)
    noharm = {c: E.test_cell(res[c], "D1D2", "D3", "deadline", -0.02) for c in names}
    viol, N = E.duty_ok(res, "D3")
    crit_d3 = bool(g10["pt"] >= 0.05 and g10["p"] < 0.05 and all(v["lb95"] > -0.02 for v in noharm.values()))
    p_d3 = max(g10["p"], max(v["p"] for v in noharm.values()))
    # H-D4a: the criterion is the 'ub95 below 0.25' of the D4 variant in every cell; p = the largest per-cell p
    cells4 = d4["d4_prov24"]
    crit_d4a = bool(all(v["ub95"] < D4.LIMIT for v in cells4.values()))
    p_d4a = max(v["p_value"] for v in cells4.values())
    raw, adj = final_holm(p_d3, p_d4a)
    crit = dict(D3=crit_d3, D4a=crit_d4a)
    for k in crit:
        verdict = "SUPPORTED" if (crit[k] and adj[k] < 0.05) else "NOT SUPPORTED"
        rec.add(f"{k}.criterion_met", int(crit[k]), "flag", "criterion of V12 addendum B met on FRESH-B")
        rec.add(f"{k}.p_raw", raw[k], "p", "largest per-cell p (intersection-union) or the pooled bootstrap p")
        rec.add(f"{k}.p_holm_final", adj[k], "p", "Holm over the family of ten (H-D4b not run, p = 1)")
        rec.add(f"{k}.verdict", verdict, "verdict", "SUPPORTED needs the criterion and a Holm-adjusted p below 0.05", origin="SIMULATED" if k == "D3" else "ANALYTICAL")
    why = ("H-D4a is met, so H-D4b was required, but the two-stage alert with per-alert frame lengths does not exist in world_sim: NOT_RUN" if crit_d4a else "H-D4a is not met, so under the kill rule of V12 10.3 H-D4b is not run")
    rec.add("D4b.verdict", "NOT_RUN", "verdict", why, origin="NOT_RUN")
    rec.add("D4b.p_raw", 1.0, "p", "not run: enters the family at p = 1", origin="NOT_RUN")
    for k in ("D1a", "D1b", "D1c", "D1s", "D2a", "D2b", "D2c"):
        rec.add(f"holm_final.{k}", adj[k], "p", "final Holm-adjusted p of the family of ten (replaces the provisional values of rd.fa.*)")
    rec.add("holm_final.D4b", adj["D4b"], "p", "")
    rec.add("holm_final.D3", adj["D3"], "p", "")
    rec.add("holm_final.D4a", adj["D4a"], "p", "")
    for k in ("pt", "lo", "hi"):
        rec.add(f"d3.crit10_gain_{k}", g10[k], "fraction", "pooled mean over burst cells of D3 minus D1+D2, Critical within 10 s; 95% interval (more conservative of event and hour bootstrap)")
    rec.add("d3.cells", len(names), "cells", f"FRESH-B burst cells, {grid['hours']} hours each, grid {GRID}")
    rec.add("d3.noharm_min_cell_diff", min(v["pt"] for v in noharm.values()), "fraction", "smallest per-cell point difference D3 minus D1+D2, delivery before the own deadline")
    rec.add("d3.noharm_min_lb95", min(v["lb95"] for v in noharm.values()), "fraction", "smallest per-cell lower 95% bound of that difference")
    rec.add("d3.noharm_cells_failing", int(sum(v["lb95"] <= -0.02 for v in noharm.values())), "cells", "cells whose lower bound is not above -0.02")
    rec.add("d3.duty_violations", viol, "runs", f"D3 runs with a duty exceed, of {N}")
    gains = [float(np.nanmean(E.paired(res[c], "D1D2", "D3", "crit10"))) for c in names]
    rec.add("d3.cells_with_gain_ge_5pt", int(sum(g >= 0.05 for g in gains)), "cells", "burst cells in which the point gain is at least 5 points")
    for pol in E.POLICIES_B:
        rec.add(f"policy.{pol}.burst_mean_crit10", float(np.mean([np.nanmean(E.metric(res[c][pol]["ev"], "crit10")) for c in names])), "fraction", "mean over burst cells, Critical within 10 s")
        rec.add(f"policy.{pol}.burst_mean_deadline", float(np.mean([np.nanmean(E.metric(res[c][pol]["ev"], "deadline")) for c in names])), "fraction", "mean over burst cells, delivered before the own deadline")
    for name, v in d4.items():
        pts = [c["pt"] for c in v.values()]
        rec.add(f"d4.{name}.extra_airtime_min", float(min(pts)), "fraction", "smallest extra airtime over the 48 cells (ANALYTICAL on the stored test events)", origin="ANALYTICAL")
        rec.add(f"d4.{name}.extra_airtime_max", float(max(pts)), "fraction", "largest extra airtime over the 48 cells", origin="ANALYTICAL")
        rec.add(f"d4.{name}.cells_ub95_below_025", int(sum(c["ub95"] < D4.LIMIT for c in v.values())), "cells", "cells whose upper 95% bound is below 0.25", origin="ANALYTICAL")
    rec.add("d4.cells", len(cells4), "cells", "6 spreading factors x 8 loss levels drawn after the freeze", origin="ANALYTICAL")
    rec.add("grid.sha256", sha256_file(GRID), "hash", "")
    rec.add("frozen.sha256", sha256_file(FROZEN), "hash", "")
    if write:
        rec.write()
    print(json.dumps({k: (int(crit[k]), round(raw[k], 4), round(adj[k], 4)) for k in crit}), "D3 gain", round(g10["pt"], 4))
    return dict(rec=rec, crit=crit, raw=raw, adj=adj, g10=g10, noharm=noharm, d4=d4)


def analyse_only() -> None:
    """Re-do the analysis from the stored results of the single run (no simulation)."""
    import pickle

    grid = json.loads(GRID.read_text(encoding="utf-8"))
    with open("data/processed/rd_fresh_B_results.pkl", "rb") as fh:
        d = pickle.load(fh)
    analyse(d["res"], d["d4"], E.cells_of(grid), grid)


if __name__ == "__main__":
    {"freeze": freeze, "draw": draw, "run": run, "analyse": analyse_only}[sys.argv[1]]()
