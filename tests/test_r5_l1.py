"""Tests of the L1 module (V16 section 3 and the code verification of section 10). Seeds here are test seeds, never the development or held-out seeds."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from crashguard import hwsim_v2 as H
from crashguard import r5_l1 as L

ROOT = Path(__file__).resolve().parents[1]
QUIET = {**H.BASE, "noise": 0.0, "bias_sd": 0.0}
SIGNS = (1, -1)


def _cal(R, accel=False, seed=7, p=None):
    rng = np.random.default_rng(seed)
    return L.calibration_drive(rng, R, accel, p)


def test_sense_rot_identity_reproduces_hwsim_sense():
    """Known answer: the identity mounting gives the rows of hwsim_v2.sense for the same random stream."""
    for side in ("front", "left"):
        r1, r2 = np.random.default_rng(5), np.random.default_rng(5)
        a, g = H.crash_event(r1, side, 5.0)
        a2, g2 = H.crash_event(r2, side, 5.0)
        t1, acc1, gy1, _s, _ta = H.sense(r1, a, g, {**H.BASE})
        t2, acc2, gy2 = L.sense_rot(r2, a2, g2, np.eye(3), 3.0)
        assert np.array_equal(t1, t2) and np.array_equal(acc1, acc2) and np.array_equal(gy1, gy2)


def test_sense_rot_matches_hwsim_flip_and_tilt():
    """The mirror variants and the tilt of hwsim_v2 are special cases of the general mounting."""
    for key, val, R in (("flip", "y", np.diag([1.0, -1, 1])), ("tilt", ("x", 15.0), L.rot_x(15))):
        p = {**H.BASE}
        if key == "flip":
            p["flip"] = val
        else:
            p["tilt_axis"], p["tilt_deg"] = val
        r1, r2 = np.random.default_rng(9), np.random.default_rng(9)
        a, g = H.crash_event(r1, "rear", 5.0)
        a2, g2 = H.crash_event(r2, "rear", 5.0)
        _t, acc1, gy1, _s, _ta = H.sense(r1, a, g, p)
        _t2, acc2, gy2 = L.sense_rot(r2, a2, g2, R, 3.0)
        assert np.allclose(acc1, acc2) and np.allclose(gy1, gy2)


@pytest.mark.parametrize("seed", range(5))
def test_random_rotations_are_proper(seed):
    R = L.random_physical_rotation(np.random.default_rng(seed))
    assert np.allclose(R @ R.T, np.eye(3), atol=1e-9) and math.isclose(np.linalg.det(R), 1.0, abs_tol=1e-9)
    tilt = math.degrees(math.acos(np.clip(R[2, 2], -1, 1)))  # angle of the vehicle up axis from the sensor up axis (or from its opposite)
    assert tilt <= 30.0 + 1e-6 or tilt >= 150.0 - 1e-6


@pytest.mark.parametrize("accel", [False, True])
@pytest.mark.parametrize("R", [np.eye(3), L.rot_z(180), L.rot_x(180), L.rot_y(180), L.rot_z(90), L.rot_x(30), L.rot_x(180) @ L.rot_y(20)])
def test_estimate_recovers_rotation_without_noise(R, accel):
    """Noise-free calibration drive: the estimated rotation is the inverse of the mounting (vehicle = R_hat sensor)."""
    c = _cal(R, accel, p=QUIET)
    est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], c["gps_v"])
    assert est["ok"], est["reason"]
    assert np.allclose(est["R_hat"], R.T, atol=0.03)


@pytest.mark.parametrize("R", [L.rot_z(37), L.rot_x(180) @ L.rot_z(90) @ L.rot_y(10)])
def test_estimated_rotation_is_proper_with_noise(R):
    c = _cal(R, True, seed=11)
    est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], c["gps_v"])
    Rh = est["R_hat"]
    assert np.allclose(Rh @ Rh.T, np.eye(3), atol=1e-6) and math.isclose(np.linalg.det(Rh), 1.0, abs_tol=1e-6)


def test_corrected_decision_is_invariant_to_the_mounting():
    """Property: with no noise, the same crash and the same drive under two mountings give the same corrected decision."""
    rng = np.random.default_rng(3)
    res = {}
    for k, R in enumerate((np.eye(3), L.rot_z(180), L.rot_y(180) @ L.rot_x(20))):
        r = np.random.default_rng(100)  # identical vehicle-frame signals under every mounting
        a, g = H.crash_event(r, "left", 5.0)
        t, acc, gy = L.sense_rot(np.random.default_rng(1), a, g, R, 3.0, QUIET)
        c = _cal(R, False, seed=5, p=QUIET)
        est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], c["gps_v"])
        res[k] = L.classify(dict(side="left", t=t, acc=acc, gyro=gy, rate_hz=100), est["R_hat"], SIGNS)
    assert len(set(res.values())) == 1 and res[0] == "left", res
    del rng


def test_raw_rule_fails_on_a_rotated_mounting_and_l1_recovers():
    """The control: the unchanged rule on a yaw of 180 degrees swaps front and rear and left and right; L1 repairs it."""
    ev = L.crash_events(np.random.default_rng(1), L.rot_z(180), 10, QUIET)
    truth = [e["side"] for e in ev]
    raw = [L.classify(e, None, SIGNS) for e in ev]
    c = _cal(L.rot_z(180), False, p=QUIET)
    est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], c["gps_v"])
    fixed = [L.classify(e, est["R_hat"], SIGNS) for e in ev]
    assert np.mean([a == b for a, b in zip(raw, truth)]) <= 0.1
    assert np.mean([a == b for a, b in zip(fixed, truth)]) >= 0.95


def test_still_window_rules():
    p = L.L1Params()
    n = 400
    acc = np.tile([0.0, 0.0, 1.0], (n, 1))
    gyro = np.zeros((n, 3))
    assert len(L.still_windows(acc, gyro, 100.0, p)) == n - 200 + 1
    g2 = gyro.copy()
    g2[200:, 0] = 3.0  # at the limit: not still
    st = L.still_windows(acc, g2, 100.0, p)
    assert st.max() + 200 <= 200
    a2 = acc.copy()
    a2[:, 2] = 1.16  # bias beyond the gate of addendum A1
    assert len(L.still_windows(a2, gyro, 100.0, p)) == 0
    a3 = acc.copy()
    a3[:, 2] = 1.14  # a bias inside the gate (about 0.14 g) still counts as still
    assert len(L.still_windows(a3, gyro, 100.0, p)) > 0
    a4 = acc.copy()
    a4[::2, 2] += 0.05  # noise above the standard deviation limit
    assert len(L.still_windows(a4, gyro, 100.0, p)) == 0
    assert len(L.still_windows(acc[:150], gyro[:150], 100.0, p)) == 0  # shorter than the window


def test_speed_segments():
    p = L.L1Params()
    t = np.arange(0, 8.0, 1.0)
    brake = np.array([18, 18, 18, 15, 12, 9, 9, 9], float)
    assert L.speed_segments(t, brake, p) == [(2.0, 5.0, -1)]
    short = np.array([18, 18, 18, 15, 12, 12, 12, 12], float)  # two intervals: exactly 2 s: allowed
    assert L.speed_segments(t, short, p) == [(2.0, 4.0, -1)]
    one = np.array([18, 18, 18, 15, 15, 15, 15, 15], float)  # a single interval: 1 s: too short
    assert L.speed_segments(t, one, p) == []
    weak = np.array([18, 17.5, 17, 16.5, 16, 15.5, 15, 14.5], float)  # 0.5 m/s per second: below a_min = 1.0
    assert L.speed_segments(t, weak, p) == []
    assert L.speed_segments(t, weak, L.L1Params(a_min=0.5)) == [(0.0, 7.0, -1)]
    mixed = np.array([10, 12, 14, 12, 10, 10, 10, 10], float)  # up then down: two runs of the same length
    runs = L.speed_segments(t, mixed, p)
    assert [r[2] for r in runs] == [1, -1]


def test_forward_axis_sign_follows_the_speed_change():
    """The same mounting gives the same forward axis whether the calibration is a braking or an acceleration."""
    R = L.rot_z(90) @ L.rot_x(10)
    outs = []
    for accel in (False, True):
        c = _cal(R, accel, p=QUIET)
        est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], c["gps_v"])
        outs.append(est["x_hat"])
    assert np.allclose(outs[0], outs[1], atol=0.05)
    assert np.allclose(outs[0], R[:, 0], atol=0.05)  # the vehicle x axis expressed in the sensor frame


def test_curve_and_weak_segments_are_rejected():
    R = np.eye(3)
    c = _cal(R, False, p=QUIET)
    g = c["gyro"].copy()
    g[300:600, 2] += 20.0  # a turn during the braking only (the still part before it stays still): yaw rate along z_hat
    assert not L.estimate_mounting(c["t_ms"], c["acc"], g, c["gps_t"], c["gps_v"])["ok"]
    acc = c["acc"].copy()
    acc[:, 0] *= 0.0  # no horizontal acceleration at all although the speed changes
    est = L.estimate_mounting(c["t_ms"], acc, c["gyro"], c["gps_t"], c["gps_v"])
    assert not est["ok"]
    est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], np.full_like(c["gps_v"], 10.0))
    assert not est["ok"] and est["reason"] == "no speed-change segment"
    noisy = c["acc"] + np.random.default_rng(0).normal(0, 0.3, c["acc"].shape)
    assert not L.estimate_mounting(c["t_ms"], noisy, c["gyro"], c["gps_t"], c["gps_v"])["ok"]  # never still: "no still window"


def test_stale_detection():
    p = L.L1Params()
    z = np.array([0.0, 0.0, 1.0])
    w9 = np.tile([math.sin(math.radians(9)), 0.0, math.cos(math.radians(9))], (50, 1))
    w11 = np.tile([math.sin(math.radians(11)), 0.0, math.cos(math.radians(11))], (50, 1))
    assert not L.is_stale(z, w9, p) and L.is_stale(z, w11, p)
    assert math.isclose(L.gravity_angle_deg(z, w9), 9.0, abs_tol=1e-6)
    assert L.is_stale(z, -w9, p)  # upside down is a large change


def test_installations_are_physical_and_fixed():
    for seed in (L.DEV_SEED, L.HELD_SEED):
        ins = L.installations(seed)
        assert len(ins) == 13
        for _n, R in ins:
            assert math.isclose(np.linalg.det(R), 1.0, abs_tol=1e-9)
    assert not np.allclose(L.installations(L.DEV_SEED)[10][1], L.installations(L.HELD_SEED)[10][1])
    assert {n for n, _ in L.installations(1)} == {n for n, _ in L.installations(2)}


def test_evaluation_on_two_installations_runs_and_l1_beats_control():
    ins = L.installations(123)
    out = []
    for i in (5, 7):  # a 180-degree yaw and a 180-degree turn about y
        n, R = ins[i]
        inst = L.build_installation(n, R, 123, i)
        inst["events"] = inst["events"][::4]
        out.append(L.evaluate_installation(inst, L.L1Params(), SIGNS))
    for r in out:
        assert r["est_ok"] and r["acc_l1"] >= 0.8 and r["acc_raw"] <= 0.6
        assert r["up_err_deg"] < 5.0


def test_pooled_and_bootstrap_helpers():
    rows = [dict(ok_l1=np.array([True] * 18 + [False] * 2)), dict(ok_l1=np.array([True] * 20))]
    acc, k, n = L.pooled(rows, "ok_l1")
    assert (k, n) == (38, 40) and math.isclose(acc, 0.95)
    lo, hi = L.boot_pooled_lower(rows, "ok_l1")
    assert lo < acc < hi and 0.85 < lo < 0.95


def test_iteration_table_matches_v16_items():
    d = L.L1Params()
    assert (d.a_min, d.still_s, d.g_still, d.ang_stale, d.a_still) == (1.0, 2.0, 3.0, 10.0, 0.15)
    assert len(L.ITERATIONS) <= 5 and L.ITERATIONS[0] == d
    for it in L.ITERATIONS[1:]:  # only the four development items differ from the defaults
        for f in ("a_still", "sd_still", "seg_min_s", "seg_trim_s", "straight_dps", "h_min_g"):
            assert getattr(it, f) == getattr(d, f)


@pytest.mark.skipif(not (ROOT / "data" / "processed" / "nhtsa_selection_60_60.joblib").exists(), reason="NHTSA cache not built")
def test_nhtsa_identity_reproduces_x1_balanced_accuracy():
    """Known answer: the identity rotation without L1 is the X1 pipeline (key x1.A.r16.balanced_acc, window 60 ms)."""
    res = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8")) if e["name"].startswith("x1.A.")}
    if res.get("x1.A.window_chosen_ms") != 60:
        pytest.skip("X1 used another window")
    _tune, held = L.nhtsa_heldout_tests()
    d = L.nhtsa_rows(held, L.L1Params(), 42, n_rot=1, identity=True)
    assert abs(L.balanced(d, "pred_raw") - res["x1.A.r16.balanced_acc"]) < 1e-3


def test_speed_segment_threshold_is_inclusive():
    t = np.arange(0, 5.0, 1.0)
    v = np.array([18.0, 17.0, 16.0, 15.0, 15.0])  # exactly 1.0 m/s per second on three intervals
    assert L.speed_segments(t, v, L.L1Params()) == [(0.0, 3.0, -1)]


def test_random_rotation_family_covers_upright_and_upside_down():
    ups = [float(L.random_physical_rotation(np.random.default_rng(s))[2, 2]) for s in range(80)]
    assert any(u > 0.8 for u in ups) and any(u < -0.8 for u in ups)
    assert max(abs(u) for u in ups) <= 1.0 and min(abs(u) for u in ups) >= math.cos(math.radians(30)) - 1e-9


@pytest.mark.skipif(not (ROOT / "data" / "processed" / "nhtsa_selection_60_60.joblib").exists(), reason="NHTSA cache not built")
def test_nhtsa_rotated_rows_l1_recovers_the_rotation():
    tune, _held = L.nhtsa_heldout_tests()
    sub = tune[:12]
    d = L.nhtsa_rows(sub, L.L1Params(), 5, n_rot=3)
    assert len(d) == 36 and d.est_ok.all()
    assert L.balanced(d, "pred_l1") >= max(0.85, L.balanced(d, "pred_raw") - 1e-9)
    d0 = L.nhtsa_rows(sub, L.L1Params(), 5, n_rot=1, identity=True)
    assert (d0.pred_l1 == d0.pred_raw).mean() >= 0.9  # without a rotation L1 changes (almost) nothing


def test_vehicle_frame_signal_matches_the_unrotated_signal():
    """Without noise the rotated-back samples equal the samples of an upright, forward-facing mounting (also for a mounting that is not its own inverse)."""
    R = L.rot_z(90) @ L.rot_x(25)
    r1, r2 = np.random.default_rng(4), np.random.default_rng(4)
    a, g = H.crash_event(r1, "front", 6.0)
    a2, g2 = H.crash_event(r2, "front", 6.0)
    _t, ref, _g = L.sense_rot(r1, a, g, np.eye(3), 3.0, QUIET)
    _t2, rot, _g2 = L.sense_rot(r2, a2, g2, R, 3.0, QUIET)
    c = _cal(R, False, p=QUIET)
    est = L.estimate_mounting(c["t_ms"], c["acc"], c["gyro"], c["gps_t"], c["gps_v"])
    assert np.allclose(L.to_vehicle(rot, est["R_hat"]), ref, atol=0.08)
    assert not np.allclose(rot @ est["R_hat"], ref, atol=0.3)


def test_segment_gravity_reference_removes_a_horizontal_bias():
    """A constant horizontal offset (a zero-g error) must not turn the forward axis: the still-window mean is subtracted."""
    R = L.rot_z(30)
    c = _cal(R, False, p=QUIET)
    acc = c["acc"] + np.array([0.0, 0.2, 0.0])
    est = L.estimate_mounting(c["t_ms"], acc, c["gyro"], c["gps_t"], c["gps_v"])
    assert est["ok"] and np.allclose(est["x_hat"], R[:, 0], atol=0.1)
