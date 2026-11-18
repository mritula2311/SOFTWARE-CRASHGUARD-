"""Tests of the L5 module (V16 section 7). Synthetic inputs; the known answer ties the custom link model to ``ar_r3.arrival``."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from crashguard import r5_l5 as L


def test_constants_follow_v16():
    assert (L.CAP_S, L.DEADLINE_S, L.COMPUTE_S, L.FINAL_S, L.TRIES, L.SF, L.P_LOSS, L.NDRAW) == (60.0, 10.0, 0.008, 1.808, 4, 9, 0.1, 20)
    assert list(L.DEV_NS3_SEEDS) == list(range(421, 441)) and list(L.HELD_NS3_SEEDS) == list(range(601, 641))
    assert L.LINK_MODELS == ("custom", "ns3", "loed") and len(L.ITERATIONS) <= 5 and L.ITERATIONS[0] == L.L5Params()
    assert L.A_FLASH < L.A_ALERT and L.A_ACK > 0 and L.WIN == pytest.approx(0.1 + L.A_ACK + 0.1)


def test_custom_link_known_answer_against_ar_r3(monkeypatch):
    """With the SF7 constants of ar_r3 the delays of the custom model equal ``ar_r3.arrival`` for the same random stream."""
    from crashguard import ar_r3 as A

    monkeypatch.setattr(L, "WIN", A.WIN)
    for a in (A.A_FL, A.A_AL):
        r1, r2 = np.random.default_rng(3), np.random.default_rng(3)
        mine = L.arrival_delays(a, 0.3, r1, 500)
        ref = A.arrival(0.0, a, 0.3, r2, 500)
        assert np.array_equal(mine, ref)


def test_arrival_delays_distribution_and_support():
    rng = np.random.default_rng(0)
    d = L.arrival_delays(L.A_ALERT, 0.0, rng, 100)
    assert (d == L.A_ALERT).all()
    assert np.isinf(L.arrival_delays(L.A_ALERT, 1.0, rng, 100)).all()
    d = L.arrival_delays(L.A_FLASH, 0.1, np.random.default_rng(1), 40000)
    allowed = {L.A_FLASH + k * (L.A_FLASH + L.WIN) for k in range(4)}
    fin = d[np.isfinite(d)]
    assert all(min(abs(x - a) for a in allowed) < 1e-9 for x in np.unique(fin))
    assert np.mean(d == L.A_FLASH) == pytest.approx(0.9, abs=0.01)  # the first uplink gets through
    assert np.mean(np.isinf(d)) == pytest.approx(0.1**4, abs=0.001)  # all four uplinks fail
    assert np.mean(d > L.A_FLASH + L.WIN + L.A_FLASH + 1e-6) < 0.015  # a late arrival needs two failures


def test_trace_delay_rules():
    a, w = 0.2, L.WIN
    assert L.trace_delay(np.array([1, 1, 1, 1], np.uint8), 0, a) == pytest.approx(a)
    assert L.trace_delay(np.array([0, 1, 1, 1], np.uint8), 0, a) == pytest.approx(a + w + a)
    assert L.trace_delay(np.array([0, 0, 0, 1, 1], np.uint8), 0, a) == pytest.approx(3 * (a + w) + a)
    assert np.isinf(L.trace_delay(np.array([0, 0, 0, 0, 1], np.uint8), 0, a))  # the fifth frame is not tried
    assert np.isinf(L.trace_delay(np.array([0, 0], np.uint8), 0, a))
    assert L.trace_delay(np.array([0, 0, 1, 1, 1], np.uint8), 1, a) == pytest.approx(a + w + a)  # the start frame shifts the attempts
    assert np.isinf(L.trace_delay(np.array([1], np.uint8), 5, a))
    assert L.trace_delay(np.array([1, 0, 0, 0], np.uint8), 0, 0.5) == pytest.approx(0.5)


def test_time_to_awareness_stage_logic():
    n = 5
    prov = np.array([1, 1, 0, 0, 1], bool)
    conf = np.array([1, 0, 1, 0, 1], bool)
    tp = np.full(n, 50.0)
    df = np.full((n, 2), 0.3)
    da = np.full((n, 2), 0.7)
    T = L.time_to_awareness(prov, conf, tp, df, da)
    assert T.shape == (n, 2)
    assert T[0, 0] == pytest.approx(0.05 + 0.008 + 0.3)  # both stages: the flash is earlier
    assert (T[1] == 60.0).all()  # a provisional alarm that is not confirmed is cancelled
    assert T[2, 0] == pytest.approx(1.808 + 0.7)  # a single-stage alert
    assert (T[3] == 60.0).all()
    df2 = np.full((n, 2), np.inf)
    assert L.time_to_awareness(prov, conf, tp, df2, da)[0, 0] == pytest.approx(1.808 + 0.7)  # the flash is lost: the alert counts
    assert (L.time_to_awareness(prov, conf, tp, df2, np.full((n, 2), np.inf)) == 60.0).all()
    late = np.full((n, 2), 9.0)  # the alert would arrive after the 10 s deadline
    assert L.time_to_awareness(prov, conf, tp, df2, late)[0, 0] == 60.0
    assert L.time_to_awareness(prov, conf, np.full(n, 9000.0), np.full((n, 2), 1.0), da)[0, 0] == pytest.approx(1.808 + 0.7)  # a flash arriving after 10 s does not count
    assert L.time_to_awareness(prov, conf, tp, df, da)[4, 0] < L.time_to_awareness(prov, conf, np.full(n, 800.0), df, da)[4, 0]


def test_deadline_is_applied_to_each_frame_separately():
    prov, conf = np.array([True]), np.array([True])
    inf = np.full((1, 2), np.inf)
    # the flash arrives at 9000 ms + 8 ms + 1.0 s = 10.008 s: after the deadline, and the alert never arrives: not aware
    assert L.time_to_awareness(prov, conf, np.array([9000.0]), np.full((1, 2), 1.0), inf)[0, 0] == 60.0
    assert L.time_to_awareness(prov, conf, np.array([9000.0]), np.full((1, 2), 0.9), inf)[0, 0] == pytest.approx(9.908)
    # the alert arrival exactly at the deadline counts (inclusive); search the delay that makes the sum exact in floating point
    d = L.DEADLINE_S - L.FINAL_S
    for cand in (d, np.nextafter(d, 0.0), np.nextafter(d, 20.0)):
        if L.FINAL_S + cand == L.DEADLINE_S:
            t = L.time_to_awareness(np.array([False]), conf, np.array([0.0]), inf, np.full((1, 2), cand))[0, 0]
            assert t == L.DEADLINE_S
            break
    t_after = L.time_to_awareness(np.array([False]), conf, np.array([0.0]), inf, np.full((1, 2), np.nextafter(d, 20.0) + 1e-9))[0, 0]
    assert t_after == 60.0


def test_criterion_and_tie_helpers():
    assert L.criterion_met(0.10, 0.001) and not L.criterion_met(0.0999, 0.5) and not L.criterion_met(0.3, 0.0) and not L.criterion_met(0.3, -0.01) and not L.criterion_met(0.05, 0.02)
    cap = np.full((3, 2), 60.0)
    ok = np.full((3, 2), 2.0)
    assert L.is_tied(cap, cap) and not L.is_tied(cap, ok) and not L.is_tied(ok, cap) and not L.is_tied(ok, ok)


def test_p90_and_conditional():
    x = np.r_[np.arange(1.0, 11.0), np.full(10, 60.0)]
    assert L.p90(x) == 60.0 and L.p90(x, conditional=True) == pytest.approx(np.quantile(np.arange(1.0, 11.0), 0.9))
    assert np.isnan(L.p90(np.full(5, 60.0), conditional=True))
    assert L.p90(np.arange(100.0)) == pytest.approx(89.1)


def test_sample_draws_common_random_numbers():
    d = dict(flash=np.arange(100.0), alert=np.arange(100.0) + 1000)
    f1, a1 = L.sample_draws(d, 30, 5)
    f2, a2 = L.sample_draws(d, 30, 5)
    assert np.array_equal(f1, f2) and np.array_equal(a1, a2) and f1.shape == (30, L.NDRAW)
    assert (a1 >= 1000).all() and (f1 < 100).all()
    f3, _a3 = L.sample_draws(d, 30, 6)
    assert not np.array_equal(f1, f3)
    assert not np.array_equal(f1 + 1000, a1)  # the flash and alert draws are independent


def test_reduction_bootstrap():
    rng = np.random.default_rng(0)
    base = rng.uniform(1, 10, (400, 20))
    same = L.reduction_boot(base, base, False, nb=300)
    assert same["pt"] == 0.0 and same["p"] > 0.4
    fast = L.reduction_boot(base, base * 0.7, False, nb=300)
    assert fast["pt"] == pytest.approx(0.3) and 0.25 < fast["lo"] < fast["pt"] < fast["hi"] and fast["p"] < 0.01
    slow = L.reduction_boot(base, base * 1.2, False, nb=300)
    assert slow["pt"] < 0 and slow["p"] > 0.99
    capped = np.where(rng.random((400, 20)) < 0.5, 60.0, base)
    r = L.reduction_boot(capped, np.where(capped < 60.0, capped * 0.5, 60.0), True, nb=300)
    assert r["pt"] == pytest.approx(0.5, abs=0.01) and r["p90_base"] > r["p90_new"]


def test_rule_decisions_only_provisional_before_1800():
    S = np.array([[0.9, 0, 0, 0, 0, 0.9], [0.1, 0.1, 0.1, 0.1, 0.1, 0.95], [0.1, 0.1, 0.9, 0.1, 0.1, 0.1], [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]])
    hi = np.full(5, 0.8)
    lo = np.full(5, 0.05)
    alarm, t = L.rule_decisions(S, hi, lo)
    assert list(alarm) == [True, False, True, False] and t[0] == 50 and t[2] == 200 and t[1] == 1800 and t[3] == 1800
    a2, _t2 = L.rule_decisions(S, np.full(5, np.inf), np.full(5, -np.inf))
    assert not a2.any()


def _toy(n_ev=3000, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n_ev) < 0.3).astype(int)
    S = np.clip(rng.normal(0.25 + 0.5 * y[:, None], 0.2, (n_ev, 6)), 0, 1)
    frame = pd.DataFrame(dict(event_id=np.arange(n_ev), y=y))
    return frame, S, y


def test_candidate_rules_grid_sizes_and_shapes():
    from crashguard.early import A_HI, B_LO

    frame, S, y = _toy()
    full_v = [S[:, k] for k in range(6)]
    base = dict(a_hi=A_HI[1], b_lo=B_LO[1])
    assert len(L.candidate_rules(S, y, full_v, y, base, "full")) == len(A_HI) * len(B_LO)
    a = L.candidate_rules(S, y, full_v, y, base, "a_hi")
    b = L.candidate_rules(S, y, full_v, y, base, "b_lo")
    assert len(a) == len(A_HI) and {c["b_lo"] for c in a} == {B_LO[1]} and len(b) == len(B_LO) and {c["a_hi"] for c in b} == {A_HI[1]}
    assert all(c["hi"].shape == (5,) and c["lo"].shape == (5,) for c in a)


@pytest.mark.parametrize("alpha", [0.01, 0.02, 0.05])
def test_choose_point_respects_the_budget_and_minimises(alpha):
    from crashguard.early import A_HI, B_LO, scatter

    frame, S, y = _toy(6000, 1)
    ids = frame.event_id.to_numpy()
    full_v = [scatter(frame, ids, S[:, k]) for k in range(6)]
    F = S[:, -1] > 0.45  # most crash events are confirmed, so the 90th percentile is not the cap
    base = dict(a_hi=A_HI[0], b_lo=B_LO[0])
    delays = dict(flash=np.full(50, 0.3), alert=np.full(50, 0.7))
    prm = L.L5Params(alpha=alpha)
    best = L.choose_point(prm, S, y, full_v, y, frame, ids, base, F, delays, 42)
    n_neg = int((y == 0).sum())
    allowed = int(np.floor(alpha * n_neg))
    prov, _t = L.rule_decisions(S, best["rule"]["hi"], best["rule"]["lo"])
    assert int((prov & (y == 0)).sum()) <= allowed
    crash = y == 1
    d_f, d_a = L.sample_draws(delays, int(crash.sum()), 42)
    objs, feasible, infeasible_better = [], 0, 0
    for c in L.candidate_rules(S, y, full_v, y, base, "full"):
        pv, tt = L.rule_decisions(S, c["hi"], c["lo"])
        obj = L.p90(L.time_to_awareness(pv[crash], F[crash], tt[crash], d_f, d_a))
        if int((pv & (y == 0)).sum()) > allowed:
            infeasible_better += int(obj < best["obj"] - 1e-9)
            continue
        feasible += 1
        objs.append(obj)
        assert best["obj"] <= obj + 1e-9  # nothing feasible is better
    assert feasible >= 1 and best["obj"] == pytest.approx(min(objs))
    if alpha == 0.01:
        assert infeasible_better >= 1  # the budget is binding: an infeasible rule would be better
    tight = L.choose_point(L.L5Params(alpha=0.0), S, y, full_v, y, frame, ids, base, F, delays, 42)
    assert tight is None or int((L.rule_decisions(S, tight["rule"]["hi"], tight["rule"]["lo"])[0] & (y == 0)).sum()) == 0


def test_second_smallest():
    assert L.second_smallest([0.5, 0.01, 0.2]) == 0.2 and L.second_smallest([0.3, 0.3, 0.9]) == 0.3


def test_ns3_delay_extraction(tmp_path, monkeypatch):
    from crashguard import pp_r3_ns3 as P1

    ev = tmp_path / "events.txt"
    ev.write_text("1 1 1 0.050\n1 0 1 0.100\n0 1 1 1.800\n1 1 1 0.200\n")
    monkeypatch.setattr(P1, "EVENTS", ev)
    run = tmp_path / f"sf{L.SF}_shipped_p{L.P_LOSS:g}_r3t_7.txt"
    # R3 k v t row dropped flash alert cancel air
    run.write_text("R3 0 1 5.0 0 0 0.60 2.50 0 0.4\nR3 1 2 6.0 1 0 -1 -1 0 0.1\nR3 2 3 7.0 2 0 -1 2.30 0 0.2\nR3 3 4 8.0 3 1 0.5 2.0 0 0.2\nDUTY 1.0 36.0\nDROPPED 1\n")
    d = L.delays_ns3([7, 8], tmp_path)
    # row 0: E and F, tE 0.05: flash delay 0.60 - (0.05 + 0.008); alert delay 2.50 - 1.808
    # row 1: E only with tE 0.10: its flash was not delivered; no alert (F = 0)
    # row 2: F only (E = 0): alert delay 2.30 - 1.808; row 3 is dropped
    assert sorted(d["flash"][np.isfinite(d["flash"])]) == [pytest.approx(0.60 - 0.058)] and int(np.isinf(d["flash"]).sum()) == 1
    assert sorted(d["alert"]) == [pytest.approx(2.30 - 1.808), pytest.approx(2.50 - 1.808)]
    assert d["n_runs"] == 1 and d["label"] == "SIMULATED"
