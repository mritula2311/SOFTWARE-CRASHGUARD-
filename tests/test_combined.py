"""Combined run: unit checks of the new modules (Holm, GTF rule, model checkers, two-stage arithmetic, side rule, frames) and consistency of the stored verdict keys."""
import json
from pathlib import Path

import numpy as np

from crashguard import ar_r1 as R1
from crashguard import ar_r2 as R2
from crashguard import ar_r3 as R3
from crashguard import ar_r4 as R4
from crashguard import ar_verdicts as V
from crashguard import sh_events as E
from crashguard import sh_s5


def test_holm_matches_hand_calculation():
    adj = V.holm([0.001, 0.04, 0.03])
    assert np.allclose(adj, [0.003, 0.06, 0.06])
    assert V.holm([1.0, 1.0]) == [1.0, 1.0]


def test_gtf_accept_rules():
    base = dict(ring=(), last={})
    ok, b = R1.accept("gtf", base, ("ts", 10, 0, 0), 10, 2, 2)
    assert ok
    assert not R1.accept("gtf", b, ("ts", 10, 0, 0), 10, 2, 2)[0]  # same triple: seen
    assert not R1.accept("gtf", base, ("ts", 10, 0, 0), 14, 2, 2)[0]  # outside the window
    ok, b = R1.accept("gtf", b, ("ts", 11, 0, 0), 11, 2, 1)
    ok2, _ = R1.accept("gtf", b, ("ts", 10, 0, 0), 11, 2, 1)  # ring of 1 evicted the first: a replay inside the window is accepted
    assert ok and ok2
    ok, b = R1.accept("gtf", base, ("fb", 3, 0, 1), 0, 2, 2)
    assert ok and not R1.accept("gtf", b, ("fb", 3, 1, 1), 0, 2, 2)[0]  # counter not above the last of that epoch


def test_r1_model_counterexamples():
    a = R1.model_check("counter_nopersist_base", T=3)
    b = R1.model_check("counter_persist_car_volatile", T=3)
    assert a["replay_accepted_ts"] is not None and a["fresh_rejected"] is None
    assert b["replay_accepted"] is None and b["fresh_rejected"] is not None


def test_r1_monte_carlo_bounds():
    rng = np.random.default_rng(1)
    r = R1.mc_cell(W=10, R=512, D=2, E=2, g=0.2, burst=150, runs=4000, rng=rng)
    assert r["avail"] >= 0.99 and r["replay_inside_accepted"] <= 5 and r["replay_outside_accepted"] == 0
    r2 = R1.mc_cell(W=10, R=64, D=2, E=2, g=0.0, burst=300, runs=4000, rng=rng)
    assert r2["replay_rate"] > 0.05  # a ring smaller than the alerts per window lets replays through


def test_r4_model_small():
    shared = R4.check("osdr", 2, frozenset({0}))
    per = R4.check("pervehicle", 2, frozenset({0}))
    assert shared["max_fraction"] == 1.0 and shared["attacker_actions_worst"] == 1
    assert per["max_fraction"] == 0.5 and per["honest_fraction"] == 0.0
    c = R4.cost_and_bytes()
    assert c["ack_len_pervehicle"] == c["ack_len_shared"] == 26 and not c["other_vehicle_key_ack_accepted"] and not c["old_counter_ack_accepted"]


def test_r3_arithmetic_and_frames():
    rng = np.random.default_rng(0)
    a = R3.arrival(1.0, R3.A_FL, 0.0, rng, 5)
    assert np.allclose(a, 1.0 + R3.A_FL)
    assert R3.exp_tries(0.0) == 1.0 and R3.exp_tries(1.0) == 4.0
    assert (24, 12) not in R2.feasible() and (24, 8) in R2.feasible() and (97, 4) in R2.feasible()
    lo, ex = R2.forgery(8)
    assert abs(lo - 44.07) < 0.01 and ex == 63


def test_side_rule_on_a_synthetic_pulse():
    t = np.arange(0, 3000, 10)
    acc = np.zeros((len(t), 3))
    acc[:, 2] = 1.0
    acc[100:104, 0] = -4.0  # a front impact in the native axes (negative x)
    ev = dict(t=t, acc=acc, gyro=np.zeros_like(acc), sw=np.zeros((len(t), 6)), rate_hz=100)
    i0 = E.trigger_index(ev)
    assert i0 == 100
    assert E.side_rule(ev, i0, E.calibration_signs())[0] == "front"


def test_sw_confirmation_needs_two_switches():
    t = np.arange(0, 3000, 10)
    acc = np.zeros((len(t), 3))
    acc[:, 2] = 1.0
    acc[100:104, 0] = -4.0
    sw = np.zeros((len(t), 6))
    sw[100:110, 0] = 1
    ev = dict(name="x", label="crash", side="front", kind=None, rate_hz=100, t=t, acc=acc, gyro=acc * 0, sw=sw)
    assert not sh_s5.decisions([ev]).both.iloc[0]
    ev["sw"][100:110, 1] = 1
    assert sh_s5.decisions([ev]).both.iloc[0]


def test_stored_verdicts_are_consistent():
    r = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith(("sh.holm.", "ar.holm."))}
    assert r["sh.holm.family_size"] == 6 and r["ar.holm.family_size"] == 7
    for k in ("hs1", "hs2", "hs3", "hs4", "hs5", "hs6"):
        assert r[f"sh.holm.{k}.verdict"] in ("SUPPORTED", "NOT SUPPORTED")
        assert (r[f"sh.holm.{k}.verdict"] == "SUPPORTED") == (r[f"sh.holm.{k}.criterion_met"] == 1 and r[f"sh.holm.{k}.p_holm"] < 0.05)
    for k in ("hr1a", "hr1b", "hr1c", "hr2a", "hr2b", "hr3", "hr4"):
        assert (r[f"ar.holm.{k}.verdict"] == "SUPPORTED") == (r[f"ar.holm.{k}.criterion_met"] == 1 and r[f"ar.holm.{k}.p_holm"] < 0.05)
    allk = json.loads(Path("results/results.json").read_text(encoding="utf-8"))
    assert not any(e["origin"] == "HARDWARE" for e in allk if e["name"].startswith(("sh.", "ar.")))
