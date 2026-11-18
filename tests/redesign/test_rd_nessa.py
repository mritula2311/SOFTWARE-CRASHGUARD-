"""CV for the Nessa-style baseline (ADDED-AFTER-SESSION-1): behaviour of the simulator hook on a link that always fails, and the invariants."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not Path("data/processed/pa_held.pkl").exists() or not Path("results/tables/rd_frozen_A.json").exists(), reason="data/processed logs not present")


@pytest.fixture(scope="module")
def sim():
    from crashguard import rd_dev_c as C
    from crashguard import rd_eval as E
    from crashguard import world_sim as W

    params = C.params_of({"nessa": {"k": 2, "A": 1.0}})
    E._init(params)
    return dict(E=E, W=W)


def _run(sim, sf=7, p=1.0, n=5):
    E, W = sim["E"], sim["W"]
    cell = dict(name=f"nessa_t_n{n}_p{int(p * 100)}_sf{sf}", n=n, p=p, sf=sf, duty=0.5, b=1)
    cfg = E.make_cfg("nessa", cell, 9100, 0)
    cfg = type(cfg)(**{**cfg.__dict__, "rate_per_car_h": 3.0, "hb_period_s": 1e9, "duration_s": 600.0})
    diag: list = []
    W.simulate(cfg, diag=diag, invariants=True)
    return [a for a in diag if a["kind"] == "crash"]


def test_sf_ladder_and_try_limit(sim):
    """On a very lossy link every alert climbs the spreading-factor ladder: the spreading factor of the last transmission is sf0 + (tries - 2) // 2 (one step per pair of retransmissions), capped at 12, and no alert exceeds 12 tries."""
    al = [a for a in _run(sim) if a["transmitted"]]
    assert al and any(a["tries"] >= 4 for a in al)
    for a in al:
        assert a["tries"] <= 12
        assert a["sf_used"] == min(12, 7 + max(0, (a["tries"] - 2) // 2))
        if a["t_rx"] is None:
            assert a["tries"] == 12 and a["gave_up"]
