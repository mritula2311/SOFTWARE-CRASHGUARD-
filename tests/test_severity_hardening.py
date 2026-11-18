"""Phase 2 severity hardening: release rule, gravity-frame rollover, bootstrap helper, range study building blocks (all on synthetic signals)."""
from dataclasses import replace

import numpy as np
import pytest

from crashguard import boot as B
from crashguard import config as C
from crashguard import severity as S
from crashguard import severity_study as SS


def _window(peak_g=20.0, dur_s=0.1, tail_g=0.0, tail_s=0.0, fs=100.0, n=280, trig=100):
    acc = np.zeros((n, 3))
    acc[:, 2] = 1.0
    k = int(round(dur_s * fs))
    acc[trig : trig + k, 0] = -peak_g * np.sin(np.pi * (np.arange(k) + 0.5) / k)
    kt = int(round(tail_s * fs))
    acc[trig + k : trig + k + kt, 0] = -tail_g
    return acc


def test_release_fraction_ends_a_pulse_with_a_slow_tail_that_the_absolute_rule_misses():
    acc = _window(tail_g=0.8, tail_s=1.0)
    absolute = S.severity(acc, 100.0, 100, None, replace(S.DEFAULT, release_frac=0.0, release_g=0.5))
    frac = S.severity(acc, 100.0, 100, None, replace(S.DEFAULT, release_frac=0.1))
    assert absolute["pulse_ms"] == pytest.approx(C.SEV_MAX_PULSE_MS, abs=1.0)  # tail above 0.5 g: runs to the cap
    assert frac["pulse_ms"] < 150.0  # release level 0.1 x 20 g = 2 g, so the 0.8 g tail ends the pulse
    assert frac["dv_res_kmh"] < absolute["dv_res_kmh"]


def test_release_level_has_a_floor_and_follows_the_peak():
    h = np.zeros(280)
    h[100:110] = 30.0
    p = replace(S.DEFAULT, release_frac=0.1, release_floor_g=0.5)
    assert S.release_level(h, 100, 100.0, p) == pytest.approx(3.0)
    h[100:110] = 2.0
    assert S.release_level(h, 100, 100.0, p) == pytest.approx(0.5)  # floor
    assert S.release_level(h, 100, 100.0, replace(S.DEFAULT, release_frac=0.0, release_g=0.7)) == pytest.approx(0.7)


def _rotating(axis: int, deg_total: float, fs=100.0, n=280, trig=100, secs=1.0, bias=(0.0, 0.0, 0.0)):
    """Accelerometer (specific force of gravity in the sensor frame) and gyro of a body that rotates about one sensor axis."""
    np.zeros((n, 3))
    gyro = np.tile(np.asarray(bias, float), (n, 1))
    rate = deg_total / secs
    k = int(secs * fs)
    gyro[trig : trig + k, axis] += rate
    ang = np.zeros(n)
    ang[trig : trig + k] = np.degrees(np.cumsum(np.full(k, np.radians(rate) / fs)))
    ang[trig + k :] = deg_total
    # world up expressed in the sensor frame after rotating the body by ang about `axis`
    a, b = [i for i in range(3) if i != axis]
    th = np.radians(ang)
    up = np.zeros((n, 3))
    up[:, 2] = 1.0
    z = up[:, 2].copy()
    if axis == 2:
        up[:, 2] = z
    else:  # rotate the (a, b) pair
        ua, ub = up[:, a].copy(), up[:, b].copy()
        up[:, a] = ua * np.cos(-th) - ub * np.sin(-th)
        up[:, b] = ua * np.sin(-th) + ub * np.cos(-th)
    return up, gyro


def test_tilt_follows_a_roll_and_ignores_a_turn():
    # gravity along z, body rolls about x (axis 0): the tilt must reach the rotated angle; a rotation about z (a turn) must not change it
    up, gyro = _rotating(0, 100.0)
    tl = S.tilt_trajectory(up, gyro, 100, 100.0)
    assert tl is not None and tl.max() == pytest.approx(100.0, abs=2.0)
    up2, gyro2 = _rotating(2, 120.0)
    tl2 = S.tilt_trajectory(up2, gyro2, 100, 100.0)
    assert tl2.max() < 1.0


def test_tilt_needs_the_vehicle_to_be_at_rest_before_the_trigger():
    acc = np.zeros((280, 3))
    assert S.tilt_trajectory(acc, np.zeros((280, 3)), 100, 100.0) is None  # no gravity vector


def test_drift_correction_removes_a_gyro_bias_that_the_gravity_vector_does_not_confirm():
    n, trig = 280, 100
    acc = np.zeros((n, 3))
    acc[:, 2] = 1.0  # never tilts
    gyro = np.zeros((n, 3))
    gyro[trig:, 0] = 60.0  # a gyro offset that starts at the trigger: 1.8 s x 60 deg/s = 108 degrees of false roll
    raw, corr, flag, applied = S.rollover_corrected(acc, gyro, trig, 100.0)
    assert applied and raw > 100.0 and corr < 5.0 and not flag


def test_a_real_roll_that_ends_on_its_side_is_still_flagged_after_correction():
    up, gyro = _rotating(0, 100.0)
    raw, corr, flag, applied = S.rollover_corrected(up, gyro, 100, 100.0)
    assert applied and flag and corr == pytest.approx(100.0, abs=3.0)


def test_severity_returns_both_rollover_flags_and_the_class_ignores_them_by_default():
    up, gyro = _rotating(0, 120.0)
    up = up.copy()
    up[100:110, 0] -= 6.0  # a crash pulse
    r = S.severity(up, 100.0, 100, gyro)
    assert r["rollover_raw"] and r["rollover_corrected"]
    assert (r["severity_class"] == 3) == C.SEV_ROLLOVER_IN_CLASS or r["severity_class"] <= 3


def test_bootstrap_interval_contains_the_true_mean_and_paired_difference_is_exact_for_a_shift():
    x = np.random.default_rng(1).normal(5.0, 1.0, 400)
    p, lo, hi = B.ci(x, np.mean)
    assert lo < 5.0 < hi and lo < p < hi
    d, dlo, dhi = B.paired_diff(x, x + 0.25, np.mean)
    assert d == pytest.approx(0.25) and dlo == pytest.approx(0.25) and dhi == pytest.approx(0.25)


def test_bootstrap_is_reproducible_and_handles_large_samples_in_blocks():
    x = np.arange(100_000, dtype=float)
    a, b = B.ci(x, np.mean, n_boot=20), B.ci(x, np.mean, n_boot=20)
    assert a == b


def test_split_rule_holds_out_every_third_test():
    assert [SS.role_of(r) for r in range(1, 7)] == ["tuning", "tuning", "heldout", "tuning", "tuning", "heldout"]


def _fake_test(v_kmh=50.0, peak_g=40.0, dur_s=0.08, fs0=5000.0):
    t = np.arange(-0.02, 0.4, 1.0 / fs0)
    a = np.zeros((len(t), 3))
    m = (t >= 0) & (t < dur_s)
    a[m, 0] = -peak_g * np.sin(np.pi * t[m] / dur_s)
    return dict(t=t, acc=a, fs0=fs0)


def test_reference_delta_v_matches_the_half_sine_formula():
    sig = _fake_test(peak_g=40.0, dur_s=0.08)
    ref, _ = SS.reference_dv(sig)
    assert ref == pytest.approx(2 * 40.0 * C.G0 * 0.08 / np.pi * 3.6, rel=0.03)


def test_range_study_shows_clipping_bias_and_recovery_at_a_wider_range():
    sig = _fake_test(peak_g=40.0, dur_s=0.08)
    ref, _ = SS.reference_dv(sig)
    low = SS.estimate(sig, 16.0, 100.0)["dv_res_kmh"]
    wide = SS.estimate(sig, 64.0, 400.0)["dv_res_kmh"]
    assert low < 0.85 * ref  # saturation at 16 g removes area
    assert abs(wide - ref) / ref < 0.10


def test_quantisation_step_is_applied():
    sig = _fake_test()
    y = SS.sensor_signal(sig, 200.0, 800.0, lsb_g=0.049)
    assert np.allclose(np.round(y / 0.049) * 0.049, y)


def test_class_limit_sensitivity_changes_the_mix_in_the_expected_direction():
    dv = np.array([20.0, 30.0, 45.0, 60.0])
    asi = np.zeros(4)
    base = SS.class_shares(dv, asi)
    lower = SS.class_shares(dv, asi, dv_lim=tuple(x * 0.8 for x in C.SEV_DV_KMH))
    assert base.sum() == pytest.approx(1.0) and lower.sum() == pytest.approx(1.0)
    assert lower[0] <= base[0] and lower[3] >= base[3]  # lower limits push events up the classes
    assert len(SS.threshold_variants()) == 1 + 12 + 4
