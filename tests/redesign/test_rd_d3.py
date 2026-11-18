"""CV 1 to 3 for D3 (docs/03_results/CODE_VERIFICATION.md, session 2): hand-computed unit cases, property tests, simulator invariants and the no-interference check (D3 switched off equals D1 + D2 bit for bit)."""
from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from crashguard import rd_d3 as D3

P0 = D3.D3Params()


# ---------------------------------------------------------------- CV1 hand-computed cases
def test_n_slots_hand_cases():
    assert D3.n_slots(5, 2.0, 0.6) == 3  # ceil(2.5)
    assert D3.n_slots(1, 2.0, 0.6) == 2  # at least two slots
    assert D3.n_slots(100, 2.0, 0.6) == 8  # cap floor(5 / 0.6) = 8
    assert D3.n_slots(100, 2.0, 0.2) == 12  # cap 12
    assert D3.n_slots(30, 2.0, 2.15) == 2  # SF11-like slot: the 5 s epoch cap leaves 2 slots
    assert D3.n_slots(4, 2.0, 0.6) == 2 and D3.n_slots(6, 2.0, 0.6) == 3 and D3.n_slots(7, 2.0, 0.6) == 4
    assert D3.n_slots(3, 0.5, 0.6) == 6


def test_slot_index_is_sha256_mod_s():
    for epoch, vid, s in ((0, 0, 2), (7, 65535, 5), (123456, 42, 12)):
        h = hashlib.sha256(struct.pack("<IH", epoch, vid)).digest()
        assert D3.slot_index(epoch, vid, s) == int.from_bytes(h, "big") % s
    assert D3.slot_index(2**32 + 5, 3, 7) == D3.slot_index(5, 3, 7)  # the epoch is taken modulo 2^32


def test_alt_sf_hand_cases():
    assert [D3.alt_sf(j, 9) for j in (1, 2, 3, 4)] == [9, 10, 9, 10]
    assert D3.alt_sf(2, 12) == 12 and D3.alt_sf(0, 9) == 9


def test_active_only_for_critical_and_enough_heard():
    assert D3.active(P0, 3, 3) and not D3.active(P0, 2, 3) and not D3.active(P0, 30, 2) and not D3.active(P0, 30, 0)


def test_slot_time_hand_case():
    # t_min 10 s, offset 0, alert 0.5 s, n_hat 4, m 2: S = 2, slot 0.52, epoch 1.04, e0 = floor(9.615) = 9; both slots of epoch 9 start before 10 s, so epoch 10 is used
    t = D3.slot_time(P0, 4, 7, 10.0, 0.0, 0.5, 100.0)
    s = D3.slot_index(10, 7, 2)
    assert t == pytest.approx(10 * 1.04 + s * 0.52)
    assert D3.slot_time(P0, 4, 7, 10.0, 0.0, 0.5, 10.4) is None  # the slot would end after the deadline
    assert D3.slot_time(P0, 4, 7, 10.0, 0.0, 0.5, 10.0) is None


# ---------------------------------------------------------------- CV2 property tests
@settings(max_examples=300, deadline=None)
@given(n=st.integers(1, 200), m=st.sampled_from([0.5, 1.0, 2.0, 3.0]), slot=st.floats(0.05, 3.0))
def test_prop_n_slots_bounds(n, m, slot):
    s = D3.n_slots(n, m, slot)
    assert 2 <= s <= D3.S_MAX
    assert s == 2 or s * slot <= D3.EPOCH_CAP_S + 1e-9  # the epoch is at most 5 s unless the minimum of two slots is longer


@settings(max_examples=400, deadline=None)
@given(n=st.integers(1, 60), vid=st.integers(0, 65535), t_min=st.floats(0.0, 3000.0), off=st.floats(-0.005, 0.005), air=st.floats(0.05, 2.5), slack=st.floats(-1.0, 40.0))
def test_prop_slot_never_after_deadline_never_before_tmin_never_stops(n, vid, t_min, off, air, slack):
    dend = t_min + slack
    t = D3.slot_time(P0, n, vid, t_min, off, air, dend)
    if t is not None:
        assert t >= t_min - 1e-9  # a slot never advances a retry
        assert t + air <= dend + 1e-9  # never after the class deadline
        assert math.isfinite(t) and t - t_min <= 3 * D3.EPOCH_CAP_S + 3 * 2 * (air + D3.GUARD_S) + 1e-6  # a slot delays by at most about two epochs: slotting is a delay, never a stop


@settings(max_examples=200, deadline=None)
@given(j=st.integers(0, 30), sf=st.integers(7, 12))
def test_prop_alt_sf(j, sf):
    assert D3.alt_sf(j, sf) in (sf, min(12, sf + 1))
    assert D3.alt_sf(j, sf) <= 12


@settings(max_examples=200, deadline=None)
@given(n=st.integers(0, 100), cls=st.integers(0, 3))
def test_prop_active_monotone_in_heard(n, cls):
    assert (not D3.active(P0, n, cls)) or D3.active(P0, n + 1, cls)


# ---------------------------------------------------------------- CV3 and no-interference: simulator
pytestmark_sim = pytest.mark.skipif(not Path("data/processed/pa_held.pkl").exists() or not Path("results/tables/rd_frozen_A.json").exists(), reason="data/processed logs not present")


@pytest.fixture(scope="module")
def sim():
    from crashguard import rd_dev_b as B
    from crashguard import rd_eval as E
    from crashguard import world_sim as W

    params = B.params_of({})
    E._init(params)
    return dict(B=B, E=E, W=W, params=params)


def _run(sim, pol, cell, hour, d3=None):
    E, W = sim["E"], sim["W"]
    if d3 is not None:
        E.CTX["params"] = {**sim["params"], "d3": {**sim["params"]["d3"], **d3}}
    else:
        E.CTX["params"] = sim["params"]
    diag: list = []
    r = W.simulate(E.make_cfg(pol, cell, sim["B"].DEV_B["seed"], hour), diag=diag, invariants=True)
    return r, [(a["id"], a["t_rx"]) for a in diag if a["kind"] == "crash"]


@pytestmark_sim
def test_d3_off_equals_d2_bit_for_bit(sim):
    cell = dict(name="n180_p35_sf8_d1_b25", n=180, p=0.35, sf=8, duty=0.01, b=25)
    _, a = _run(sim, "D1D2", cell, 3)
    r3, b = _run(sim, "D3", cell, 3, d3=dict(thr3=10**6))
    assert a == b and r3.get("duty_exceeded", 0) == 0


@pytestmark_sim
def test_d3_invariants_in_burst_cells(sim):
    for cell in (dict(name="n180_p35_sf8_d1_b25", n=180, p=0.35, sf=8, duty=0.01, b=25), dict(name="n80_p55_sf10_d0.2_b25", n=80, p=0.55, sf=10, duty=0.002, b=25)):
        for h in range(2):
            r, ev = _run(sim, "D3", cell, h)  # invariants=True aborts on a negative time, a send in a duty blackout, or a delivery without a send
            assert r["duty_exceeded"] == 0 and len(ev) > 0


@pytestmark_sim
def test_d3_slots_used_in_bursts_and_alert_never_dropped(sim):
    cell = dict(name="n180_p35_sf8_d1_b25", n=180, p=0.35, sf=8, duty=0.01, b=25)
    E, W = sim["E"], sim["W"]
    E.CTX["params"] = sim["params"]
    diag: list = []
    cfg = E.make_cfg("D3", cell, sim["B"].DEV_B["seed"], 1)
    r = W.simulate(cfg, diag=diag, invariants=True)
    assert r["d3_slotted"] > 0 and r["d3_alt_sf"] > 0  # slots and the spreading-factor alternation are used in a burst cell
    tries_crit = [a for a in diag if a["kind"] == "crash" and a["true"] == 3]
    assert tries_crit and all(a["gave_up"] is False or a["tries"] >= 12 for a in tries_crit)  # an alert stops only by an ACK or its try limit (12), never by a slot


@pytestmark_sim
def test_d3_quiet_without_burst(sim):
    """Without a burst the vehicles rarely overhear three others in 10 s: when D3 slots nothing in an hour, the events must be identical to D1 + D2 (the count is what it is)."""
    cell = dict(name="n80_p15_sf8_d1_b1", n=80, p=0.15, sf=8, duty=0.01, b=1)
    for h in range(3):
        r3, b = _run(sim, "D3", cell, h)
        _, a = _run(sim, "D1D2", cell, h)
        if r3["d3_slotted"] == 0:
            assert a == b


@pytestmark_sim
def test_d3_slotting_alone_changes_events(sim):
    """With the spreading-factor alternation off, D3 differs from D1 + D2 only through slotted retry times: the events must differ in a burst hour that slotted at least once."""
    cell = dict(name="n180_p35_sf8_d1_b25", n=180, p=0.35, sf=8, duty=0.01, b=25)
    r3, b = _run(sim, "D3", cell, 1, d3=dict(alt=False))
    _, a = _run(sim, "D1D2", cell, 1)
    assert r3["d3_slotted"] > 0 and a != b


@pytestmark_sim
def test_d3_simulator_decisions_match_reference(sim):
    """Every slot decision recorded inside the simulator equals the pure function evaluated with the vehicle itself counted in N_hat."""
    cell = dict(name="n180_p35_sf8_d1_b25", n=180, p=0.35, sf=8, duty=0.01, b=25)
    E, W = sim["E"], sim["W"]
    E.CTX["params"] = sim["params"]
    trace: list = []
    for h in range(1, 5):
        cfg = E.make_cfg("D3", cell, sim["B"].DEV_B["seed"], h)
        cfg.world["rd"]["trace"] = trace
        W.simulate(cfg, invariants=True)
    p3 = D3.D3Params(**sim["params"]["d3"])
    recs = [t for t in trace if t[0] == "d3"]
    assert len(recs) >= 3
    for _k, _sf, n_oth, node, ready, off, a_air, dend, st_ in recs:
        assert D3.active(p3, n_oth, 3)
        assert D3.slot_time(p3, n_oth + 1, node, ready, off, a_air, dend) == st_


# ---------------------------------------------------------------- more hand-computed slot times (epoch arithmetic, offset, boundary)
def _vid_with_index(epoch: int, s: int, want: int) -> int:
    return next(v for v in range(1000) if D3.slot_index(epoch, v, s) == want)


def test_slot_time_with_offset_and_second_slot():
    # n_hat 4, m 2 -> S = 2, alert 0.5 s, slot 0.52 s, epoch 1.04 s. t_min 9.4 s, offset 0.004 s: e0 = floor(9.396 / 1.04) = 9, slot 1 of epoch 9 starts at 9 * 1.04 + 0.52 + 0.004 = 9.884 >= 9.4
    vid = _vid_with_index(9, 2, 1)
    t = D3.slot_time(P0, 4, vid, 9.4, 0.004, 0.5, 100.0)
    assert t == pytest.approx(9 * 1.04 + 1 * 0.52 + 0.004, abs=1e-9)
    # a vehicle whose slot in epoch 9 is slot 0 (9.364 + 0.004 < 9.4) goes to epoch 10
    vid0 = _vid_with_index(9, 2, 0)
    t0 = D3.slot_time(P0, 4, vid0, 9.4, 0.004, 0.5, 100.0)
    assert t0 == pytest.approx(10 * 1.04 + D3.slot_index(10, vid0, 2) * 0.52 + 0.004, abs=1e-9)


def test_slot_time_boundary_is_accepted():
    vid = _vid_with_index(10, 2, 1)
    t = D3.slot_time(P0, 4, vid, 10.0, 0.0, 0.5, 100.0)
    assert D3.slot_time(P0, 4, vid, t, 0.0, 0.5, 100.0) == t  # a slot that starts exactly at t_min is used
