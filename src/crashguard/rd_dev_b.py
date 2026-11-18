"""DEV runs of D3 (V12 addendum B, section 10.2): new DEV grid (seed base 51000), at most 5 logged iterations, appended to results/tables/rd_dev_log.csv with algo 'D3'. D1 and D2 parameters are the frozen ones of
FRESH-A (results/tables/rd_frozen_A.json); only the D3 parameters (thr3, m, alt) are tuned here.

    python -m crashguard.rd_dev_b iter '{"d3": {"thr3": 3, "m": 2.0, "alt": true}}' "note"
    python -m crashguard.rd_dev_b pick
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from crashguard import rd_dev as DV
from crashguard import rd_eval as E
from crashguard.rd_common import paired_event_test

DEV_B = dict(n=(80, 180), p=(0.15, 0.35, 0.55), sf=(8, 10), duty=(0.01, 0.002), b=(25,), seed=51000, hours=100)
FROZEN_A = Path("results/tables/rd_frozen_A.json")
D3_DEFAULT = dict(thr3=3, m=2.0, alt=True)


def params_of(over: dict) -> dict:
    fz = json.loads(FROZEN_A.read_text(encoding="utf-8"))["params"]
    d3 = dict(D3_DEFAULT)
    d3.update(over.get("d3", {}))
    return dict(d1=fz["d1"], d2=fz["d2"], d3=d3)


def metrics(res: dict) -> dict:
    cells = list(res)
    g10 = {c: paired_event_test(E.paired(res[c], "D1D2", "D3", "crit10"), 0.05) for c in cells}
    gd = {c: paired_event_test(E.paired(res[c], "D1D2", "D3", "deadline"), -0.02) for c in cells}
    return dict(burst_mean_gain_crit10=float(np.mean([g10[c]["pt"] for c in cells])), burst_min_gain_crit10=float(min(g10[c]["pt"] for c in cells)),
                min_cell_deadline_diff=float(min(v["pt"] for v in gd.values())), cells_deadline_below_minus2pt=int(sum(v["pt"] < -0.02 for v in gd.values())),
                duty_violations=int(sum(res[c]["D3"]["runs"][:, 1].sum() for c in cells)), cells=len(cells))


def iterate(over: dict, note: str) -> None:
    params = params_of(over)
    cells = E.cells_of(DEV_B)
    res = E.run_grid(cells, E.POLICIES_B, DEV_B["seed"], DEV_B["hours"], params)
    m = metrics(res)
    n = DV.append_log("D3", params, m, note)
    print("D3 iteration", n, json.dumps(m, indent=1))


def pick() -> dict:
    rows = [r for r in DV.log_rows() if r["algo"] == "D3"]
    ok = []
    for r in rows:
        m = json.loads(r["metrics"])
        if m["min_cell_deadline_diff"] >= -0.02:
            ok.append((m["burst_mean_gain_crit10"], int(r["iteration"]), json.loads(r["params"])))
    if not ok:
        raise SystemExit("D3: no iteration meets the DEV floor (no cell more than 2 points below D1+D2); D3 goes forward with the last iteration and the floor failure is reported")
    best = max(ok, key=lambda x: (x[0], -x[1]))
    print("D3 best iteration", best[1], "burst_mean_gain_crit10", best[0])
    return best[2]


if __name__ == "__main__":
    if sys.argv[1] == "iter":
        iterate(json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}, sys.argv[3] if len(sys.argv) > 3 else "")
    elif sys.argv[1] == "pick":
        print(json.dumps(pick()))
