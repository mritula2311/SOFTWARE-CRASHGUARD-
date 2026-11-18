"""CV 3 and 7 (docs/03_results/CODE_VERIFICATION.md): run-time invariants of the simulator with the redesign hooks, and known-answer reproduction of three earlier numbers with the hooked code."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crashguard import rd_policy as RP

pytestmark = pytest.mark.skipif(not Path("data/processed/pa_held.pkl").exists(), reason="data/processed logs not present")


@pytest.fixture(scope="module")
def ctx():
    from crashguard import fin_g as G
    from crashguard import fin_sim as FS
    from crashguard import pa_sim as PA

    return dict(PA=PA, G=G, t=FS.tuned(), pools=PA.pools_real(), des=json.loads(Path("data/processed/pa_design.json").read_text(encoding="utf-8")))


def _cfg(ctx, cell, pol_spec, hour, rd=None, sct_over=None):
    PA, G = ctx["PA"], ctx["G"]
    w = PA.spec_world(pol_spec, cell)
    if rd:
        w = {**w, "rd": rd}
    return G.cfg_for(PA.spec_pol(pol_spec), cell, PA.HELD_A["seed"], hour, ctx["pools"], ctx["t"], f"g_{cell['name']}", w, sct_over)


def _cell(ctx, name):
    return next(c for c in ctx["PA"].cells(ctx["PA"].HELD_A) if c["name"] == name)


# ---------------------------------------------------------------- CV7: known answers
def test_known_answer_uasct_cell(ctx):
    from crashguard import world_sim as W

    R = pd.read_pickle("data/processed/pa_held.pkl")
    cell = _cell(ctx, "n100_p20_sf8_d1_b30")
    for h in range(4):
        out = W.simulate(_cfg(ctx, cell, dict(kind="P4"), h), invariants=True)
        ref = R[(R.cell == cell["name"]) & (R.pol == "P4") & (R.hour == h)].iloc[0]
        for k in ("reach10_critical", "reach10_rx_critical", "al_collided", "al_tx", "node_air_s", "ack_sent"):
            assert out[k] == pytest.approx(float(ref[k]), abs=1e-12), k


def test_known_answer_osdr_cell(ctx):
    from crashguard import world_sim as W

    R = pd.read_pickle("data/processed/pa_held.pkl")
    cell = _cell(ctx, "n100_p20_sf8_d1_b30")
    spec = dict(kind="osdr", N=ctx["des"]["osdr_N"])
    for h in range(4):
        out = W.simulate(_cfg(ctx, cell, spec, h), invariants=True)
        ref = R[(R.cell == cell["name"]) & (R.pol == "osdr") & (R.hour == h)].iloc[0]
        for k in ("reach10_critical", "suppressed", "suppressed_unrx", "al_collided", "node_air_s"):
            assert out[k] == pytest.approx(float(ref[k]), abs=1e-12), k


def test_known_answer_r3_result():
    from crashguard import ar_r3 as R3

    stored = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith("ar.r3.a1.")}
    S = R3.stage_table(pd.read_csv("results/tables/s6_events_seed42_a1.csv"))
    v = R3.clause_values(S["E"], S["F"], S["y"], S["t"], np.arange(len(S["E"])), np.random.default_rng(42))
    assert round(v["air_ratio_p0"], 5) == stored["ar.r3.a1.air_ratio_p0"]
    assert round(v["retraction_share"], 5) == stored["ar.r3.a1.retraction_share"]


# ---------------------------------------------------------------- CV3: invariants with D1 and D2 on
@pytest.fixture(scope="module")
def rd_cfgs(ctx):
    d1 = dict(d1_table=RP.D1Table(8), d1_params=RP.D1Params())
    d12 = dict(d1, d2=dict(thr=4, tc=1.5, sig_len=64, max_ids=24, max_defers=3, defer_scale=1.0))
    return d1, d12


@pytest.mark.parametrize("name", ["n100_p20_sf8_d1_b30", "n200_p40_sf8_d0.1_b30", "n100_p40_sf8_d1_b1"])
def test_invariants_d1_and_d2(ctx, rd_cfgs, name):
    from crashguard import world_sim as W

    cell = _cell(ctx, name)
    for rd in rd_cfgs:
        for h in range(3):
            diag: list = []
            out = W.simulate(_cfg(ctx, cell, dict(kind="P4"), h, rd=rd, sct_over=dict(fast_cap=None)), diag=diag, invariants=True)  # an assertion aborts the run
            assert out["duty_exceeded"] == 0
            for a in diag:
                if a["acked"]:
                    assert a["t_rx"] is not None  # an ACK, own or in a verified cluster ACK, only exists for an alert the base received
                    assert a["t_ack"] is not None and a["t_ack"] >= a["t_rx"] - 1e-9
                assert not (a["gave_up"] and a["acked"])


def test_d2_acts_in_a_burst_and_not_in_steady_state(ctx, rd_cfgs):
    from crashguard import world_sim as W

    burst = W.simulate(_cfg(ctx, _cell(ctx, "n100_p20_sf8_d1_b30"), dict(kind="P4"), 0, rd=rd_cfgs[1], sct_over=dict(fast_cap=None)), invariants=True)
    assert burst["cluster_ack_tx"] > 0 and burst["defers"] >= 0
    steady_c = _cell(ctx, "n100_p40_sf8_d1_b1")
    a = W.simulate(_cfg(ctx, steady_c, dict(kind="P4"), 1, rd=rd_cfgs[0], sct_over=dict(fast_cap=None)), invariants=True)
    b = W.simulate(_cfg(ctx, steady_c, dict(kind="P4"), 1, rd=rd_cfgs[1], sct_over=dict(fast_cap=None)), invariants=True)
    assert b["cluster_ack_tx"] == 0
    for k in ("reach10_rx_critical", "al_tx", "node_air_s", "ack_sent", "al_collided"):
        assert a[k] == b[k], k  # without a burst, D2 behaves as D1 exactly


def test_invariant_checker_detects_violations():
    from crashguard import world_sim as W

    base = dict(arrival=1.0, ready=2.0, tries=1, n_flash=0, n_ok=1, n_lost=0, n_collided=0, n_deaf=0, t_rx=3.0, first_tx=2.5, t_ack_first=None)
    W.check_invariants([dict(base)], [])  # consistent
    with pytest.raises(AssertionError):
        W.check_invariants([dict(base, n_ok=0)], [])  # a delivered packet with no decoded transmission (and events not conserved)
    with pytest.raises(AssertionError):
        W.check_invariants([dict(base, tries=2)], [])  # sent != accounted
    with pytest.raises(AssertionError):
        W.check_invariants([dict(base, t_rx=2.0)], [])  # received before the first send
    with pytest.raises(AssertionError):
        W.check_invariants([dict(base, arrival=-1.0)], [])  # negative time
    with pytest.raises(AssertionError):
        W.check_invariants([dict(base, t_ack_first=2.9)], [])  # ACK before reception
