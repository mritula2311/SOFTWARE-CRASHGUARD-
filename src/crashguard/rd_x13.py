"""X1.3: D1 and baselines in ns-3 (lorawan module) and in the custom simulator on the same scenario S-X, and the cross-simulator verdicts (docs/02_preregistration/PREREGISTRATION_V12.md addendum B, 10.4). Keys ``rd.x13.*``.

    python -m crashguard.rd_x13 ns3 <hours>       # runs the ns-3 application (xsim/ns3/xsim_alert.cc) for the 32 SF9 cells of FRESH-A, policies p1, quick, d1, lorawan; writes data/processed/rd_x13_ns3.pkl
    python -m crashguard.rd_x13 custom <hours>    # the frozen custom-simulator policies on the same scenario (Critical events only); writes data/processed/rd_x13_custom.pkl
    python -m crashguard.rd_x13 analyse           # verdicts per simulator, agreement table, results.json keys, docs/03_results/XSIM_VERDICTS.md

The ns-3 run uses the frozen D1 table and parameters (rd_frozen_A.json) and re-tunes nothing. It re-uses the cell parameters of FRESH-A (SF9 cells) with new seeds: a cross-check, not a second held-out test.
"""
from __future__ import annotations

import json
import pickle
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from crashguard import rd_eval as E
from crashguard import rd_firmware as F
from crashguard.rd_common import Rec

ROOT = Path(__file__).resolve().parents[2]
GRID = ROOT / "results" / "tables" / "rd_fresh_A_grid.json"
OUT = ROOT / "data" / "processed"
SEED0_CUSTOM = 710000
NS_POLICIES = ("p1", "quick", "d1", "lorawan", "nessa")  # nessa: ADDED-AFTER-SESSION-1 (V12 11.1)
CUSTOM_POLICIES = ("P1", "P0", "P4", "quick", "tamang", "khan", "D1")
NS_BIN = "./build/scratch/ns3.48-xsim_alert-optimized"
SRC = "src/crashguard/rd_x13.py"


def sx_cells() -> list[dict]:
    g = json.loads(GRID.read_text(encoding="utf-8"))
    cells = [c for c in E.cells_of(g) if c["sf"] == 9]
    return cells


# ------------------------------------------------------------------------------------------------ ns-3
JOB_SCRIPT = """#!/bin/bash
# usage: x13_job.sh <jobfile> ; each line: outfile|args
cd ~/ns3work/ns-3-dev
while IFS='|' read -r out args; do
  {NS} $args > "$out" 2>/dev/null
done < "$1"
"""


def nessa_args() -> str:
    pr = json.loads((ROOT / "results" / "tables" / "rd_frozen_C.json").read_text(encoding="utf-8"))["params"]["nessa"]
    return f"--nessaK={pr['k']} --nessaA={pr['A']}"


def ns3_jobs(cells: list[dict], hours: int, policies=NS_POLICIES, adr_cells: int = 0) -> list[tuple[str, str]]:
    outdir = OUT / "xsim_out"
    outdir.mkdir(exist_ok=True)
    tab = F.wsl_path(OUT / "rd_fw_d1_sf9.bin")
    jobs = []
    for c in cells:
        for pol in policies:
            for h in range(hours):
                f = outdir / f"{c['name']}__{pol}__{h}.txt"
                if f.exists() and f.stat().st_size > 0:
                    continue
                args = f"--n={c['n']} --sf=9 --p={c['p']} --duty={c['duty']} --b={c['b']} --seed={h + 1} --policy={pol} --table={tab} {nessa_args() if pol == 'nessa' else ''}"
                jobs.append((F.wsl_path(f), args))
    return jobs


def run_ns3(hours: int, workers: int = 14) -> None:
    F.make_tables((9,))
    cells = sx_cells()
    jobs = ns3_jobs(cells, hours)
    print("ns-3 jobs", len(jobs), flush=True)
    (OUT / "x13_jobs").mkdir(exist_ok=True)
    chunks = [jobs[i::workers] for i in range(workers)]
    script = JOB_SCRIPT.replace("{NS}", NS_BIN)
    (OUT / "x13_jobs" / "x13_job.sh").write_bytes(script.encode("utf-8"))
    procs = []
    for k, ch in enumerate(chunks):
        jf = OUT / "x13_jobs" / f"jobs_{k}.txt"
        jf.write_bytes(("\n".join(f"{o}|{a}" for o, a in ch) + "\n").encode("utf-8"))
        procs.append(subprocess.Popen(["wsl", "-d", "Ubuntu", "--", "bash", F.wsl_path(OUT / "x13_jobs" / "x13_job.sh"), F.wsl_path(jf)]))
    for p in procs:
        p.wait()


def parse_ns3(hours: int) -> dict:
    """Parse the run files. A run whose output file is empty crashed inside ns-3 (a segmentation fault after an ACK callback, about 0.2% of runs, reproducible for the same arguments, cause inside the module not found);
    that cell and hour is dropped for EVERY policy so that the paired comparison keeps the same events. The number of dropped hours is stored in rd_x13_ns3_dropped.json."""
    cells = sx_cells()
    res: dict = {}
    dropped: dict = {}
    for c in cells:
        bad = {h for h in range(hours) for pol in NS_POLICIES if (OUT / "xsim_out" / f"{c['name']}__{pol}__{h}.txt").stat().st_size == 0}
        dropped[c["name"]] = sorted(bad)
        d = {}
        for pol in NS_POLICIES:
            hrs, aid, dly, runs = [], [], [], []
            for h in range(hours):
                if h in bad:
                    continue
                f = OUT / "xsim_out" / f"{c['name']}__{pol}__{h}.txt"
                evs, duty = [], (0.0, 0.0)
                for line in f.read_text().splitlines():
                    t = line.split()
                    if t and t[0] == "EV":
                        evs.append(float(t[3]))
                    elif t and t[0] == "DUTY":
                        duty = (float(t[1]), float(t[2]))
                for k, x in enumerate(evs):
                    hrs.append(h)
                    aid.append(k)
                    dly.append(np.nan if x < 0 else x)
                runs.append((h, int(duty[0] > duty[1] + 1e-9), 0.0, duty[0], 0.0, 0.0))
            d[pol] = dict(ev=dict(hour=np.array(hrs, np.int32), aid=np.array(aid, np.int32), true=np.full(len(hrs), 3, np.int8), delay=np.array(dly, float)), runs=np.array(runs, float))
        res[c["name"]] = d
    (OUT / "rd_x13_ns3_dropped.json").write_text(json.dumps(dropped), encoding="utf-8")
    return res


# ------------------------------------------------------------------------------------------------ custom simulator on S-X
def _init_sx(params: dict) -> None:
    E._init(params)
    pools = E.CTX["pools"]
    cl = pools["classes"][16.0]
    allc = {**cl, "true": np.full_like(cl["true"], 3), "point": np.full_like(cl["point"], 3), "upper": np.full_like(cl["upper"], 3), "lowered": np.full_like(cl["lowered"], 3), "abstain": np.full_like(cl["abstain"], 3)}
    E.CTX["pools"] = {**pools, "classes": {**pools["classes"], 16.0: allc}, "crash_t": np.array([0.3]), "fa_t": np.array([0.3])}


def run_custom(hours: int, workers: int = 14, pols: tuple = CUSTOM_POLICIES) -> dict:
    fz = json.loads((ROOT / "results" / "tables" / "rd_frozen_A.json").read_text(encoding="utf-8"))
    fz["params"]["nessa"] = json.loads((ROOT / "results" / "tables" / "rd_frozen_C.json").read_text(encoding="utf-8"))["params"]["nessa"]
    cells = sx_cells()
    tasks = [(c, pols, SEED0_CUSTOM, h0, min(h0 + 25, hours), True) for c in cells for h0 in range(0, hours, 25)]
    with ProcessPoolExecutor(workers, initializer=_init_sx, initargs=(fz["params"],)) as ex:
        parts = list(ex.map(E.run_task, tasks, chunksize=1))
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


# ------------------------------------------------------------------------------------------------ analysis
def verdicts(res: dict, d1: str, p1: str, baselines: tuple, cells: list[dict], tag: str) -> dict:
    names = [c["name"] for c in cells]
    pm = {c["name"]: c["p"] for c in cells}
    d1a = {c: E.test_cell(res[c], p1, d1, "crit10", -0.01) if False else E.test_cell(res[c], p1, d1, "deadline", -0.01) for c in names}
    hi = [c for c in names if pm[c] >= 0.40]
    d1b = E.pooled_boot([(res[c], p1, d1, "deadline") for c in hi], 0.05)
    viol = int(sum(res[c][d1]["runs"][:, 1].sum() for c in names))
    nruns = int(sum(len(res[c][d1]["runs"]) for c in names))
    best = {c: max(baselines, key=lambda p: float(np.nanmean(E.metric(res[c][p]["ev"], "deadline")))) for c in names}
    d1s = {c: E.test_cell({"b": res[c][best[c]], "D": res[c][d1]}, "b", "D", "deadline", -0.02) for c in names}
    crit = dict(D1a=all(v["lb95"] > -0.01 for v in d1a.values()), D1b=bool(d1b["pt"] >= 0.05 and d1b["p"] < 0.05), D1c=(viol == 0), D1s=all(v["lb95"] > -0.02 for v in d1s.values()))
    return dict(tag=tag, crit=crit, d1a_min_diff=min(v["pt"] for v in d1a.values()), d1a_min_lb=min(v["lb95"] for v in d1a.values()), d1a_failing=int(sum(v["lb95"] <= -0.01 for v in d1a.values())), d1b=d1b,
                viol=viol, nruns=nruns, d1s_min_diff=min(v["pt"] for v in d1s.values()), d1s_mean=float(np.mean([v["pt"] for v in d1s.values()])), d1s_failing=int(sum(v["lb95"] <= -0.02 for v in d1s.values())), best=best,
                means={p: float(np.mean([np.nanmean(E.metric(res[c][p]["ev"], "deadline")) for c in names])) for p in res[names[0]]}, cells=len(names))


def analyse() -> dict:
    cells = sx_cells()
    ns = pickle.load(open(OUT / "rd_x13_ns3.pkl", "rb"))
    cu = pickle.load(open(OUT / "rd_x13_custom.pkl", "rb"))
    vn = verdicts(ns, "d1", "p1", ("p1", "quick", "lorawan", "nessa"), cells, "ns-3")
    cn = OUT / "rd_x13_custom_nessa.pkl"
    if cn.exists():  # ADDED-AFTER-SESSION-1: the Nessa-style policy on S-X in the custom simulator, same seeds, merged for the best-baseline test
        extra = pickle.load(open(cn, "rb"))
        cu = {c: {**cu[c], "nessa": extra[c]["nessa"]} for c in cu}
    vc = verdicts(cu, "D1", "P1", ("P1", "P0", "P4", "quick", "tamang", "khan") + (("nessa",) if cn.exists() else ()), cells, "custom")
    rec = Rec("rd.x13.", SRC)
    for v in (vn, vc):
        t = v["tag"].replace("-", "")
        for k, ok in v["crit"].items():
            rec.add(f"{t}.{k}.criterion_met", int(ok), "flag", f"V12 criterion on scenario S-X in {v['tag']} (SF9 cells of FRESH-A, new seeds)")
        rec.add(f"{t}.d1a.min_cell_diff", v["d1a_min_diff"], "fraction", "smallest per-cell D1 minus severity table")
        rec.add(f"{t}.d1a.cells_failing", v["d1a_failing"], "cells", "cells whose lower bound is not above -0.01")
        for k in ("pt", "lo", "hi"):
            rec.add(f"{t}.d1b.{k}", v["d1b"][k], "fraction", "pooled D1 minus severity table over cells with loss of 40% or more")
        rec.add(f"{t}.d1c.violations", v["viol"], "runs", f"D1 runs with a trailing-hour airtime above the duty limit, of {v['nruns']}")
        rec.add(f"{t}.d1s.min_cell_diff", v["d1s_min_diff"], "fraction", "smallest per-cell D1 minus the best baseline of the cell")
        rec.add(f"{t}.d1s.mean_diff", v["d1s_mean"], "fraction", "")
        for p, m in v["means"].items():
            rec.add(f"{t}.mean_delivery.{p}", m, "fraction", "mean over cells, Critical delivered within 10 s of the crash")
    rows = []
    for k, label in (("D1a", "H-D1a"), ("D1b", "H-D1b"), ("D1c", "H-D1c"), ("D1s", "H-D1s")):
        same = vn["crit"][k] == vc["crit"][k]
        rec.add(f"agree.{k}", int(same), "flag", "same SUPPORTED or NOT SUPPORTED outcome in both simulators on S-X")
        rows.append((label, vc["crit"][k], vn["crit"][k], same))
    rec.write()
    return dict(vn=vn, vc=vc, rows=rows)


def write_doc(out: dict) -> None:
    """docs/03_results/XSIM_VERDICTS.md from the analysis (generated; every number comes from out)."""
    cells = sx_cells()
    dropped = json.loads((OUT / "rd_x13_ns3_dropped.json").read_text())
    nd = sum(len(v) for v in dropped.values())
    vn, vc = out["vn"], out["vc"]
    L = ["# Cross-simulator verdicts (X1.3): D1 and baselines in ns-3 and in the custom simulator", "", "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-14 |", "| Owner | Mritula S |",
         "| Scope | D1 against the severity table and baselines on scenario S-X in ns-3 (lorawan module) and in the custom simulator, with the verdict of each V12 criterion in both (generated). |", "| Evidence labels used | SIMULATED |",
         "| Abbreviations | ACK = acknowledgement frame; ADR = adaptive data rate; LoRa = long-range radio modulation; SF = spreading factor (LoRa) |", "<!-- header:end -->", "",
         "Generated by `python -m crashguard.rd_x13 analyse`. Design, scenario S-X and the agreement rule: `PREREGISTRATION_V12.md` addendum B section 10.4. Constants: `ASSUMPTIONS.md`. Build and local ns-3 changes: `XSIM_BUILD.md`. The calibration criterion of X1.2 was NOT MET (`XSIM_CALIBRATION.md`), so every statement below is made under a calibration that did not reach its own criterion.", "",
         f"Scenario: the {len(cells)} SF9 cells of FRESH-A (SF11 is not expressible in ns-3's ALOHA region), 100 simulated hours per cell and policy, new seeds, Critical events only, frozen D1 table and parameters (nothing re-tuned). These cells were used once before for the custom-simulator verdicts; this run is a cross-check, not a second held-out test. ns-3 runs that crashed inside the module (a segmentation fault after an ACK callback; about 0.2% of runs, same arguments crash again; cause not found) are dropped for all policies of that cell and hour: {nd} of {len(cells) * 100} hours.", "",
         "## Verdicts of the V12 criteria on S-X", "", "| Hypothesis | Custom simulator | ns-3 | Same verdict |", "|---|---|---|---|"]
    for k, lab in (("D1a", "H-D1a no cell below the severity table by more than 1 point"), ("D1b", "H-D1b at least 5 points above the severity table at loss of 40% or more"), ("D1c", "H-D1c duty limit never exceeded"), ("D1s", "H-D1s not below the best baseline of the cell by more than 2 points")):
        a, b = vc["crit"][k], vn["crit"][k]
        L.append(f"| {lab} | {'met' if a else 'not met'} | {'met' if b else 'not met'} | {'yes' if a == b else '**no: simulator-dependent**'} |")
    L += ["", "A hypothesis whose verdict differs between the simulators is simulator-dependent and cannot be in the abstract. D1 enters the main paper only if H-D1a and H-D1b agree (V12 8 and D8).", "",
          "## Numbers", "", "| Quantity | Custom simulator | ns-3 |", "|---|---|---|",
          f"| D1 minus severity table, smallest cell | {vc['d1a_min_diff']:+.3f} | {vn['d1a_min_diff']:+.3f} |", f"| cells whose lower bound is below -0.01 | {vc['d1a_failing']} of {vc['cells']} | {vn['d1a_failing']} of {vn['cells']} |",
          f"| D1 minus severity table, cells with loss of 40% or more (95% interval) | {vc['d1b']['pt']:+.3f} [{vc['d1b']['lo']:+.3f}, {vc['d1b']['hi']:+.3f}] | {vn['d1b']['pt']:+.3f} [{vn['d1b']['lo']:+.3f}, {vn['d1b']['hi']:+.3f}] |",
          f"| D1 runs above the duty limit | {vc['viol']} of {vc['nruns']} | {vn['viol']} of {vn['nruns']} |", f"| D1 minus best baseline of the cell: smallest / mean | {vc['d1s_min_diff']:+.3f} / {vc['d1s_mean']:+.3f} | {vn['d1s_min_diff']:+.3f} / {vn['d1s_mean']:+.3f} |",
          f"| cells below the best baseline by more than 2 points (lower bound) | {vc['d1s_failing']} of {vc['cells']} | {vn['d1s_failing']} of {vn['cells']} |", "", "Mean Critical delivery within 10 s of the crash over the cells:", "", "| Policy | Custom | ns-3 |", "|---|---|---|"]
    names = {"P1": "p1", "P0": None, "P4": None, "quick": "quick", "tamang": None, "khan": None, "nessa": "nessa", "D1": "d1"}
    for c_name, n_name in names.items():
        if c_name not in vc["means"]:
            continue
        L.append(f"| {c_name}{' (ns-3: ' + n_name + ')' if n_name and n_name != c_name else ''} | {vc['means'][c_name]:.3f} | {vn['means'][n_name]:.3f} |" if n_name else f"| {c_name} | {vc['means'][c_name]:.3f} | not implemented in ns-3 |")
    L.append(f"| standard LoRaWAN confirmed uplink (NbTrans 8, RX1 1 s, RX2 2 s, ADR off); custom column: Khan-style | {vc['means']['khan']:.3f} | {vn['means']['lorawan']:.3f} |")
    L += ["", "The Nessa-style row is ADDED-AFTER-SESSION-1 (V12 11.1; parameters frozen on the DEV grid of the custom simulator and reused in ns-3; implemented from a secondary description).",
          "", f"**Decision rule A4 (V12 11.4): D1 goes to the main paper only if H-D1b and H-D1s hold in ns-3 as well.** H-D1b in ns-3: {'met' if vn['crit']['D1b'] else 'not met'}; H-D1s in ns-3 (best of p1, quick, lorawan, nessa): {'met' if vn['crit']['D1s'] else 'not met'}. Result: **{'D1 may go to the main paper' if (vn['crit']['D1b'] and vn['crit']['D1s']) else 'D1 is reported as simulator-dependent and stays in the supplement'}**."]
    L += ["", "## What differs between the two simulators (stated, not isolated)",
          "- The custom policies use a 14-byte flash before every alert round, and a received flash counts as delivery; the ns-3 policies have no flash frame. The D1 table also plans one 97-byte transmission per attempt. Part of D1's gain in the custom simulator may come from the flash; this was not tested.",
          "- ns-3 ACK frames are about 13 bytes (the custom ACK is 26); receive windows are set to 0.1 s and 0.2 s for p1, quick and d1 (a local change) and kept at 1 s and 2 s for standard LoRaWAN.",
          "- The ns-3 baselines p1 and quick are simplified re-implementations from the descriptions. ADR on was not run (NOT_RUN): in a one-hour run with one uplink per ten minutes ADR has no data to act on.",
          "- ns-3 allows one alert per vehicle at a time (a vehicle in its backoff tail gives way to a new crash), the custom simulator keeps several.",
          "- Different collision and reception models (ns-3's own interference matrix); different random draws.", "",
          "## Reading", "",
          "Where the verdicts differ, D1's gain over the severity table is simulator-dependent and is reported so. The comparison with published numbers (X1.4: ICC 2018 ns-3 paper, IEEE TWC 2021 single-gateway model, IEEE Sensors J. 2022 real-versus-simulated study) is NOT_RUN: none of the three was opened. Absence statements: no claim."]
    Path(ROOT / "docs/03_results/XSIM_VERDICTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "ns3":
        if len(sys.argv) < 4 or sys.argv[3] != "parse":
            run_ns3(int(sys.argv[2]))
        pickle.dump(parse_ns3(int(sys.argv[2])), open(OUT / "rd_x13_ns3.pkl", "wb"))
    elif cmd == "custom":
        pickle.dump(run_custom(int(sys.argv[2])), open(OUT / "rd_x13_custom.pkl", "wb"))
    elif cmd == "custom_nessa":
        pickle.dump(run_custom(int(sys.argv[2]), pols=("nessa",)), open(OUT / "rd_x13_custom_nessa.pkl", "wb"))
    elif cmd == "analyse":
        o = analyse()
        write_doc(o)
        print(json.dumps(o["rows"], default=str))


