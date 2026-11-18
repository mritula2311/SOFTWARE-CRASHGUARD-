"""Severity code on synthetic pulses with known answers (SIMULATED: proves the code, not real-world accuracy)."""
from dataclasses import replace

import numpy as np
import pytest

from crashguard import config as C
from crashguard import severity as S
from crashguard import severity_synth as Y


def _pulse(shape="half_sine", A=20.0, T=0.1, theta=0.0, fs=100.0, noise=0.0, tilt=0.0, clip=None, seed=0):
    return Y.make_window(shape, A, T, theta, fs, np.random.default_rng(seed), noise_g=noise, tilt_deg=tilt, clip_g=clip)


@pytest.mark.parametrize("shape", Y.SHAPES)
@pytest.mark.parametrize("theta", [0.0, 90.0, 35.0])
def test_delta_v_recovered_at_1khz_without_noise(shape, theta):
    acc, trig = _pulse(shape, 20.0, 0.1, theta, fs=1000.0)
    r = S.severity(acc, 1000.0, trig)
    assert abs(r["dv_res_ms"] - Y.dv_truth_ms(shape, 20.0, 0.1)) / Y.dv_truth_ms(shape, 20.0, 0.1) < 0.01


def test_half_sine_formula_2AT_over_pi():
    acc, trig = _pulse("half_sine", 25.0, 0.12, fs=1000.0)
    assert S.severity(acc, 1000.0, trig)["dv_res_ms"] == pytest.approx(2 * 25.0 * C.G0 * 0.12 / np.pi, rel=0.01)


def test_direction_is_kept_in_the_components():
    r = S.severity(*_pulse("half_sine", 20.0, 0.1, 90.0, fs=1000.0)[:1], 1000.0, _pulse("half_sine", 20.0, 0.1, 90.0, fs=1000.0)[1])
    assert abs(r["dvx_ms"]) < 0.05 * abs(r["dvy_ms"]) and r["dvy_ms"] < 0  # side pulse: lateral, decelerating along -y


def test_gravity_and_tilt_are_removed():
    acc, trig = _pulse("half_sine", 20.0, 0.1, fs=100.0, tilt=3.0, seed=3)
    r = S.severity(acc, 100.0, trig)
    assert abs(r["dv_res_ms"] - Y.dv_truth_ms("half_sine", 20.0, 0.1)) / Y.dv_truth_ms("half_sine", 20.0, 0.1) < 0.10


def test_tolerance_grid_at_100hz_unclipped():
    df = Y.run_grid(seeds=2, fs_list=(100.0,), clips=(None,))
    long = df[df.T_ms >= Y.TOL_MIN_DURATION_S * 1000]
    assert (long.dv_err_pct.abs() <= Y.DV_TOL_PCT).mean() >= 0.95
    assert (long.asi_err_pct.abs() <= Y.ASI_TOL_PCT).mean() >= 0.95


def test_lower_sample_rate_and_clipping_bias_delta_v_downwards():
    df = Y.run_grid(seeds=2)
    d = df[(df.T_ms >= 80)]
    med = d.groupby(["fs", "clip"]).dv_err_pct.median()
    assert med[(50.0, "none")] < med[(100.0, "none")] < 0  # 50 Hz is worse than 100 Hz, both underestimate
    assert med[(100.0, f"+-{C.MPU_RANGE_G:g} g")] < med[(100.0, "none")]  # saturation removes area


def test_asi_class_limits():
    assert [S.asi_class(v) for v in (0.5, 1.0, 1.2, 1.4, 1.5, 1.9, 2.5)] == ["A", "A", "B", "B", "C", "C", ">C"]


def test_class_rules_and_rollover_is_always_critical():
    assert S.classify(10, 0.3, False) == 0 and S.classify(30, 0.3, False) == 1 and S.classify(45, 0.3, False) == 2 and S.classify(60, 0.3, False) == 3
    assert S.classify(10, 1.2, False) == 1 and S.classify(10, 1.6, False) == 2 and S.classify(10, 2.0, False) == 3  # ASI can raise the class
    on = replace(S.DEFAULT, rollover_in_class=True)
    assert S.classify(5, 0.1, True, on) == 3  # with the rollover rule switched on a rollover is always Critical
    assert S.classify(5, 0.1, True) == (3 if C.SEV_ROLLOVER_IN_CLASS else 0)  # the default follows config.py (switched off on 2026-11-11, see docs/07_log/DECISIONS.md)


def test_rollover_from_integrated_gyro():
    n, fs = 280, 100.0
    gyro = np.zeros((n, 3))
    gyro[100:200, 0] = 120.0  # 120 deg/s for 1 s = 120 degrees of roll
    assert S.rollover(gyro, 100, fs)[2] is True
    gyro[100:200, 0] = 30.0  # 30 degrees
    assert S.rollover(gyro, 100, fs)[2] is False


def test_quiet_window_gives_no_pulse():
    acc = np.zeros((280, 3))
    acc[:, 2] = 1.0
    r = S.severity(acc, 100.0, 100)
    assert r["dv_res_kmh"] == 0 and r["asi"] < 1e-9 and r["severity_name"] == "Low"
