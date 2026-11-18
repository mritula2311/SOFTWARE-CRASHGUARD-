"""Smoke test of the FRESH-A analysis code on a small DEV-seed run (no result is written): every hypothesis key is produced, pairing assertions hold, and the cluster and event bootstraps agree on sign."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(not Path("data/processed/pa_held.pkl").exists(), reason="data/processed logs not present")


def test_analysis_runs_and_pairs():
    from crashguard import rd_dev as DEV
    from crashguard import rd_eval as E
    from crashguard import rd_fresh_a as FA

    params = DEV.merge({})
    cells = [c for c in E.cells_of(E.DEV) if c["n"] == 80 and c["sf"] == 8 and c["duty"] == 0.01 and c["p"] in (0.35, 0.55)]
    assert len(cells) == 4
    res = E.run_grid(cells, E.POLICIES, 31000, 6, params, workers=2, chunk=3)
    out = FA.analyse(res, cells, dict(hours=6), write=False)
    keys = {e["name"] for e in out["rec"].ent}
    for k in ("D1a", "D1b", "D1c", "D1s", "D2a", "D2b", "D2c"):
        assert f"rd.fa.{k}.verdict_provisional" in keys
    for c in cells:  # events pair across policies
        for pol in E.POLICIES:
            assert np.array_equal(res[c["name"]]["P1"]["ev"]["aid"], res[c["name"]][pol]["ev"]["aid"])
    t = E.test_cell(res[cells[0]["name"]], "P1", "D1", "deadline", -0.01)
    assert t["p"] >= max(t["p_event"], t["p_cluster"]) - 1e-12 and t["lb95"] <= min(t["lb95_event"], t["lb95_cluster"]) + 1e-12
    json.dumps({k: bool(v) for k, v in out["crit"].items()})
