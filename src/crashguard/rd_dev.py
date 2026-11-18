"""DEV runs of D1 and D2 on the DEV grid (new seeds), at most 5 logged iterations per algorithm (PREREGISTRATION_V12 section 5). Every iteration is appended to results/tables/rd_dev_log.csv.

    python -m crashguard.rd_dev base                       # baselines on the DEV grid (cached)
    python -m crashguard.rd_dev iter D1 '{"d1": {...}}' "note"
    python -m crashguard.rd_dev iter D2 '{"d2": {...}}' "note"      # D2 is run on top of the frozen or current D1 parameters
    python -m crashguard.rd_dev pick D1|D2                 # best iteration by the preregistered DEV objective
"""
from __future__ import annotations

import copy
import csv
import json
import pickle
import sys
from datetime import date
from pathlib import Path

import numpy as np

from crashguard import rd_eval as E
from crashguard.rd_common import paired_event_test

LOG = Path("results/tables/rd_dev_log.csv")
BASE_CACHE = Path("data/processed/rd_dev_base.pkl")
MAX_ITER = 5
DEFAULT = dict(
    d1=dict(n0=6.0, l0=0.3, forget=0.97, rho=(0.0, 0.10, 0.30, 0.50), g0=1.0, share=(0.0, 0.0, 0.3, 0.5)),
    d2=dict(thr=4, tc=1.5, sig_len=64, max_ids=24, max_defers=3, defer_scale=1.0),
)


def merge(over: dict) -> dict:
    p = copy.deepcopy(DEFAULT)
    for k, v in over.items():
        p[k].update({kk: (tuple(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()})
    return p


def log_rows() -> list[dict]:
    if not LOG.exists():
        return []
    with LOG.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def append_log(algo: str, params: dict, metrics: dict, note: str) -> int:
    rows = log_rows()
    n = sum(r["algo"] == algo for r in rows) + 1
    if n > MAX_ITER:
        raise SystemExit(f"{algo}: at most {MAX_ITER} DEV iterations are allowed")
    new = dict(date=str(date.today()), algo=algo, iteration=n, params=json.dumps(params, sort_keys=True), metrics=json.dumps(metrics, sort_keys=True), note=note)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(new))
        if not rows:
            w.writeheader()
        w.writerow(new)
    return n


def base() -> None:
    cells = E.cells_of(E.DEV)
    res = E.run_grid(cells, E.BASELINES, E.DEV["seed"], E.DEV["hours"], merge({}))
    with BASE_CACHE.open("wb") as fh:
        pickle.dump(res, fh)
    print("baselines cached", len(res), "cells")


def d1_metrics(res: dict) -> dict:
    cells = list(res)
    d1 = {c: paired_event_test(E.paired(res[c], "P1", "D1", "deadline"), -0.01) for c in cells}
    pt = np.array([d1[c]["pt"] for c in cells])
    lo = np.array([d1[c]["lb95"] for c in cells])
    hi_loss = [c for c in cells if "_p55_" in c]
    best = {c: E.best_baseline(res[c], "deadline") for c in cells}
    vs_best = np.array([paired_event_test(E.paired({"b": res[c][best[c]], "D1": res[c]["D1"]}, "b", "D1", "deadline"), -0.02)["pt"] for c in cells])
    return dict(mean_gain_vs_P1=float(pt.mean()), min_cell_gain=float(pt.min()), cells_below_minus1pt=int((pt < -0.01).sum()), cells_lb_below_minus1pt=int((lo < -0.01).sum()),
                mean_gain_vs_P1_p55=float(np.mean([d1[c]["pt"] for c in hi_loss])), mean_gain_vs_best_baseline=float(vs_best.mean()), min_gain_vs_best_baseline=float(vs_best.min()),
                duty_violations=int(sum(res[c]["D1"]["runs"][:, 1].sum() for c in cells)), cells=len(cells))


def d2_metrics(res: dict) -> dict:
    cells = list(res)
    burst = [c for c in cells if c.endswith("_b25")]
    g = {c: paired_event_test(E.paired(res[c], "D1", "D1D2", "final"), -0.02) for c in cells}
    b10 = {c: paired_event_test(E.paired(res[c], "D1", "D1D2", "crit10"), 0.05) for c in burst}
    return dict(burst_mean_gain_crit10=float(np.mean([b10[c]["pt"] for c in burst])), burst_min_gain_crit10=float(min(b10[c]["pt"] for c in burst)),
                min_cell_final_diff=float(min(v["pt"] for v in g.values())), cells_final_below_minus2pt=int(sum(v["pt"] < -0.02 for v in g.values())),
                duty_violations=int(sum(res[c]["D1D2"]["runs"][:, 1].sum() for c in cells)), burst_cells=len(burst))


def iterate(algo: str, over: dict, note: str) -> None:
    params = merge(over)
    cells = E.cells_of(E.DEV)
    pols = ("D1",) if algo == "D1" else ("D1", "D1D2")
    res = E.run_grid(cells, pols, E.DEV["seed"], E.DEV["hours"], params)
    with BASE_CACHE.open("rb") as fh:
        b = pickle.load(fh)
    for c in res:
        res[c].update(b[c])
    m = d1_metrics(res) if algo == "D1" else d2_metrics(res)
    n = append_log(algo, params, m, note)
    print(algo, "iteration", n, json.dumps(m, indent=1))


def check_after_fix(note: str) -> None:
    """Re-run the CHOSEN parameters of D1 (iteration 2) and D2 (iteration 4) after the pre-freeze code review fixes. Not an iteration: nothing is chosen or changed from it; logged in rd_dev_checks.csv."""
    pick("D1")
    p2 = pick("D2")
    cells = E.cells_of(E.DEV)
    params = dict(d1=p2["d1"], d2=p2["d2"])
    res = E.run_grid(cells, ("D1", "D1D2"), E.DEV["seed"], E.DEV["hours"], params)
    with BASE_CACHE.open("rb") as fh:
        b = pickle.load(fh)
    for c in res:
        res[c].update(b[c])
    out = dict(d1=d1_metrics(res), d2=d2_metrics(res))
    chk = Path("results/tables/rd_dev_checks.csv")
    with chk.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if chk.stat().st_size == 0:
            w.writerow(["date", "note", "params", "metrics"])
        w.writerow([str(date.today()), note, json.dumps(params, sort_keys=True), json.dumps(out, sort_keys=True)])
    print(json.dumps(out, indent=1))


def pick(algo: str) -> dict:
    rows = [r for r in log_rows() if r["algo"] == algo]
    ok, key = [], ("mean_gain_vs_P1" if algo == "D1" else "burst_mean_gain_crit10")
    for r in rows:
        m = json.loads(r["metrics"])
        floor = m["min_cell_gain"] >= -0.01 if algo == "D1" else m["min_cell_final_diff"] >= -0.02
        if floor:
            ok.append((m[key], int(r["iteration"]), json.loads(r["params"])))
    if not ok:
        raise SystemExit(f"{algo}: no iteration meets the DEV floor; the algorithm goes forward with the last iteration and the floor failure is reported")
    best = max(ok, key=lambda x: (x[0], -x[1]))
    print(algo, "best iteration", best[1], key, best[0])
    return best[2]


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "base":
        base()
    elif cmd == "iter":
        iterate(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}, sys.argv[4] if len(sys.argv) > 4 else "")
    elif cmd == "check":
        check_after_fix(sys.argv[2])
    elif cmd == "pick":
        print(json.dumps(pick(sys.argv[2])))
