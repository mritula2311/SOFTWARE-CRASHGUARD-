"""DEV runs of the Nessa-style baseline (V12 addendum C, 11.1; ADDED-AFTER-SESSION-1): DEV grid of section 3 (seed 31000, 100 hours, 48 cells), at most 5 logged iterations in results/tables/rd_dev_log.csv with algorithm 'Nessa'. Objective: the
largest mean delivery before the own class deadline over the DEV cells. D1 parameters are not involved.

    python -m crashguard.rd_dev_c iter '{"nessa": {"k": 2, "A": 1.0}}' "note"
    python -m crashguard.rd_dev_c pick
"""
from __future__ import annotations

import json
import sys

import numpy as np

from crashguard import rd_dev as DV
from crashguard import rd_eval as E


def params_of(over: dict) -> dict:
    fz = json.loads(DV.Path("results/tables/rd_frozen_A.json").read_text(encoding="utf-8"))["params"]
    return dict(d1=fz["d1"], d2=fz["d2"], nessa=dict(over["nessa"]))


def iterate(over: dict, note: str) -> None:
    params = params_of(over)
    res = E.run_grid(E.cells_of(E.DEV), ("nessa",), E.DEV["seed"], E.DEV["hours"], params)
    cells = list(res)
    dl = float(np.mean([np.nanmean(E.metric(res[c]["nessa"]["ev"], "deadline")) for c in cells]))
    c10 = float(np.mean([np.nanmean(E.metric(res[c]["nessa"]["ev"], "crit10")) for c in cells if c.endswith("_b25")]))
    m = dict(mean_deadline_delivery=dl, burst_mean_crit10=c10, duty_violations=int(sum(res[c]["nessa"]["runs"][:, 1].sum() for c in cells)), cells=len(cells))
    n = DV.append_log("Nessa", params, m, note)
    print("Nessa iteration", n, json.dumps(m, indent=1))


def pick() -> dict:
    rows = [r for r in DV.log_rows() if r["algo"] == "Nessa"]
    best = max(((json.loads(r["metrics"])["mean_deadline_delivery"], -int(r["iteration"]), json.loads(r["params"])) for r in rows), key=lambda x: (x[0], x[1]))
    print("Nessa best iteration", -best[1], best[0])
    return best[2]


if __name__ == "__main__":
    if sys.argv[1] == "iter":
        iterate(json.loads(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "")
    elif sys.argv[1] == "pick":
        print(json.dumps(pick()))
