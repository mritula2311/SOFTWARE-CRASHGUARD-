"""CV 7 (session 2): the simulator code changed after the FRESH-A freeze (D3 hooks, decision trace records). D1 and D1+D2 must give the stored FRESH-A per-event delays bit for bit under the current code."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

PKL = Path("data/processed/rd_fresh_A_results.pkl")
pytestmark = pytest.mark.skipif(not PKL.exists() or not Path("data/processed/pa_held.pkl").exists(), reason="stored FRESH-A results or class pools not present")


def test_d1_and_d1d2_reproduce_fresh_a_bit_for_bit():
    import pickle

    from crashguard import rd_eval as E

    res = pickle.loads(PKL.read_bytes())
    fz = json.loads(Path("results/tables/rd_frozen_A.json").read_text(encoding="utf-8"))
    grid = json.loads(Path("results/tables/rd_fresh_A_grid.json").read_text(encoding="utf-8"))
    cells = E.cells_of(grid)
    sel = [c for c in cells if c["sf"] == 9 and c["b"] > 1][:2] + [c for c in cells if c["sf"] == 11 and c["b"] == 1][:1] + [c for c in cells if c["sf"] == 11 and c["b"] > 1][:1]
    new = E.run_grid(sel, ("D1", "D1D2"), grid["seed"], 8, fz["params"], workers=4)
    for c in sel:
        for pol in ("D1", "D1D2"):
            o, n = res[c["name"]][pol]["ev"], new[c["name"]][pol]["ev"]
            m = o["hour"] < 8
            assert m.sum() > 0
            for k in ("hour", "aid", "true", "delay"):
                assert np.array_equal(o[k][m], n[k], equal_nan=True), (c["name"], pol, k)
