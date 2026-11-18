"""ADDED-AFTER-SESSION-1 (V12 addendum C, 11.1): the Nessa-style baseline on the FRESH-A grid, run once, and the comparison with D1. Keys ``rd.fc.*``. This adds a baseline; it tunes nothing in D1 and enters no Holm family.

    python -m crashguard.rd_fresh_c freeze    # picks the DEV iteration of the Nessa-style baseline, writes results/tables/rd_frozen_C.json with code hashes; commit it
    python -m crashguard.rd_fresh_c run       # ONE run on the FRESH-A grid; refuses to run twice
    python -m crashguard.rd_fresh_c analyse   # analysis from the stored results
"""
from __future__ import annotations

import csv
import json
import pickle
import sys
from pathlib import Path

import numpy as np

from crashguard import rd_dev_c as DC
from crashguard import rd_eval as E
from crashguard.rd_common import Rec, sha256_file

FROZEN = Path("results/tables/rd_frozen_C.json")
DONE = Path("results/tables/rd_fresh_C_done.json")
GRID = Path("results/tables/rd_fresh_A_grid.json")
PKL_A = Path("data/processed/rd_fresh_A_results.pkl")
PKL_C = Path("data/processed/rd_fresh_C_results.pkl")
CODE = tuple(f"src/crashguard/{m}.py" for m in ("world_sim", "rd_eval", "rd_dev_c", "rd_fresh_c", "rd_common", "rd_policy", "fin_g", "fin_sim", "pa_sim", "s11_sct", "sct_sim", "lora", "capacity", "packet", "replay")) + ("results/tables/rd_fresh_A_grid.json",)
SRC = "src/crashguard/rd_fresh_c.py"
BASE7 = ("P1", "P4", "P0", "quick", "tamang", "khan", "nessa")
LAB = "ADDED-AFTER-SESSION-1; not in the Holm family"


def code_hashes() -> dict:
    return {f: sha256_file(f) for f in CODE}


def freeze() -> None:
    if FROZEN.exists():
        raise SystemExit("already frozen")
    p = DC.pick()
    FROZEN.write_text(json.dumps(dict(params=p, code=code_hashes(), dev_log_sha256=sha256_file("results/tables/rd_dev_log.csv"), label="ADDED-AFTER-SESSION-1"), indent=1, sort_keys=True), encoding="utf-8")
    print("frozen", sha256_file(FROZEN))


def run() -> None:
    if DONE.exists():
        raise SystemExit("the Nessa-style run on FRESH-A has been done once; it is not run again")
    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert fz["code"] == code_hashes(), "code changed after the freeze"
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    assert PKL_A.exists()
    DONE.write_text(json.dumps(dict(started=True, frozen_sha256=sha256_file(FROZEN), grid_sha256=sha256_file(GRID))), encoding="utf-8")
    res = E.run_grid(E.cells_of(grid), ("nessa",), grid["seed"], grid["hours"], fz["params"])
    with open(PKL_C, "wb") as fh:
        pickle.dump(res, fh)
    analyse()


def analyse(write: bool = True) -> dict:
    ra = pickle.loads(PKL_A.read_bytes())
    rc = pickle.loads(PKL_C.read_bytes())
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    cells = E.cells_of(grid)
    names = [c["name"] for c in cells]
    res = {c: {**ra[c], "nessa": rc[c]["nessa"]} for c in names}
    pm = {c["name"]: c["p"] for c in cells}
    prm = json.loads(FROZEN.read_text(encoding="utf-8"))["params"]["nessa"]
    rec = Rec("rd.fc.", SRC)
    dn = {c: E.test_cell(res[c], "nessa", "D1", "deadline", 0.02) for c in names}
    pooled = E.pooled_boot([(res[c], "nessa", "D1", "deadline") for c in names], 0.02)
    share_pt = float(np.mean([dn[c]["pt"] >= 0.02 for c in names]))
    share_lb = float(np.mean([dn[c]["lb95"] > 0.02 for c in names]))
    better = bool(pooled["pt"] >= 0.02 and pooled["lo"] > 0.0 and share_pt >= 0.5)
    best = {c: max(BASE7, key=lambda p: float(np.nanmean(E.metric(res[c][p]["ev"], "deadline")))) for c in names}
    d1s = {c: E.test_cell({"b": res[c][best[c]], "D": res[c]["D1"]}, "b", "D", "deadline", -0.02) for c in names}
    crit_s = all(v["lb95"] > -0.02 for v in d1s.values())
    p_s = max(v["p"] for v in d1s.values())
    by_level = {}
    for lv in sorted({round(pm[c], 1) for c in names}):
        cs = [c for c in names if round(pm[c], 1) == lv]
        by_level[lv] = E.pooled_boot([(res[c], "nessa", "D1", "deadline") for c in cs], 0.02)
    mean_dl = {p: float(np.mean([np.nanmean(E.metric(res[c][p]["ev"], "deadline")) for c in names])) for p in BASE7 + ("D1",)}
    vq = E.pooled_boot([(res[c], "quick", "D1", "deadline") for c in names], 0.0)
    rec.add("nessa.params_k", prm["k"], "factor", f"timeout factor chosen on DEV; {LAB}")
    rec.add("nessa.params_A", prm["A"], "s", f"redundant-copy spacing chosen on DEV; {LAB}")
    for k in ("pt", "lo", "hi"):
        rec.add(f"d1_minus_nessa.{k}", pooled[k], "fraction", f"D1 minus Nessa-style, mean over {len(names)} FRESH-A cells, Critical and Severe before the own deadline, 95% interval; {LAB}")
    rec.add("d1_minus_nessa.min_cell", min(v["pt"] for v in dn.values()), "fraction", f"smallest per-cell D1 minus Nessa-style; {LAB}")
    rec.add("d1_minus_nessa.max_cell", max(v["pt"] for v in dn.values()), "fraction", f"largest per-cell D1 minus Nessa-style; {LAB}")
    rec.add("d1_minus_nessa.share_cells_ge_2pt", share_pt, "fraction", f"share of cells in which D1 is better than Nessa-style by at least 2 points (point estimate); {LAB}")
    rec.add("d1_minus_nessa.share_cells_lb_gt_2pt", share_lb, "fraction", f"same with the lower 95% bound above 2 points; {LAB}")
    rec.add("d1_better_than_nessa", int(better), "flag", "reading rule of V12 11.1: pooled difference >= 0.02 with lower bound above 0 and at least half of the cells >= 2 points; 0 means Nessa-style matches or beats D1 and D1 is not claimed over it")
    for lv, v in by_level.items():
        rec.add(f"d1_minus_nessa.loss{lv:g}.pt", v["pt"], "fraction", f"by loss level; {LAB}")
    for k in ("pt", "lo", "hi"):
        rec.add(f"d1_minus_quick.{k}", vq[k], "fraction", "D1 minus quick retries, pooled over all FRESH-A cells, 95% interval (A2)")
    rec.add("d1s7.criterion_met", int(crit_s), "flag", f"H-D1s rerun with seven baselines (the six of V12 section 4 plus Nessa-style), lower bound above -0.02 in every cell; {LAB}")
    rec.add("d1s7.p_raw", p_s, "p", f"largest per-cell p; unadjusted; {LAB}")
    rec.add("d1s7.min_cell_diff", min(v["pt"] for v in d1s.values()), "fraction", "smallest per-cell D1 minus the best of seven")
    rec.add("d1s7.mean_diff", float(np.mean([v["pt"] for v in d1s.values()])), "fraction", "mean per-cell D1 minus the best of seven")
    rec.add("d1s7.cells_failing", int(sum(v["lb95"] <= -0.02 for v in d1s.values())), "cells", "cells whose lower bound is not above -0.02")
    rec.add("d1s7.best_nessa_cells", int(sum(b == "nessa" for b in best.values())), "cells", "cells in which Nessa-style is the best of the seven")
    for p, m in mean_dl.items():
        rec.add(f"mean_deadline_delivery.{p}", m, "fraction", f"mean over cells; {LAB}" if p == "nessa" else "mean over cells")
    if write:
        rec.write()
        with open("results/tables/rd_fresh_c_cells.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["cell", "loss", "d1_minus_nessa", "lb95", "best_of_seven", "d1_minus_best", "d1_minus_best_lb95"])
            for c in names:
                w.writerow([c, pm[c], round(dn[c]["pt"], 5), round(dn[c]["lb95"], 5), best[c], round(d1s[c]["pt"], 5), round(d1s[c]["lb95"], 5)])
    print(json.dumps(dict(pooled=[round(pooled[k], 4) for k in ("pt", "lo", "hi")], share_ge_2pt=round(share_pt, 3), better=better, d1s7=crit_s, mean=mean_dl)))
    return dict(pooled=pooled, share_pt=share_pt, better=better, crit_s=crit_s)


if __name__ == "__main__":
    {"freeze": freeze, "run": run, "analyse": analyse}[sys.argv[1]]()
