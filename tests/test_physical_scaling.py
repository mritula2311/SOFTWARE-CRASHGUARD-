"""X7: time and amplitude scaling of events (synthetic signals only)."""
import numpy as np
import pytest

from crashguard import config as C
from crashguard import physical_scaling as PS


def _event(n=1600, pulse_at=700, amp=6.0, width=10):
    acc = np.zeros((n, 3))
    acc[:, 2] = 1.0
    acc[pulse_at : pulse_at + width, 0] = np.hanning(width) * amp
    return acc, np.zeros((n, 3))


def test_identity_transform_changes_nothing():
    acc, gyro = _event()
    out, g = PS.transform_event(acc, gyro, 1.0, 1.0)
    assert np.array_equal(out, acc) and np.array_equal(g, gyro)


def test_amplitude_scaling_keeps_the_gravity_part():
    acc, gyro = _event()
    out, _g = PS.transform_event(acc, gyro, 2.0, 1.0)
    assert out[:, 2].mean() == pytest.approx(1.0, abs=1e-9)
    assert out[:, 0].max() == pytest.approx(2.0 * acc[:, 0].max())


def test_time_stretch_changes_the_length_and_lowpass_removes_aliasing_when_compressing():
    acc, gyro = _event(width=8)
    long_, _ = PS.transform_event(acc, gyro, 1.0, 2.0)
    short_, _ = PS.transform_event(acc, gyro, 1.0, 0.25)
    assert len(long_) == 3200 and len(short_) == 400
    short_raw, _ = PS.transform_event(acc, gyro, 1.0, 0.25, antialias=False)
    assert np.abs(short_[:, 0]).max() < np.abs(short_raw[:, 0]).max()  # the filter lowers a pulse that is shorter than the sampling allows


def test_window_of_needs_the_trigger_and_clips_at_the_range():
    quiet = np.zeros((1600, 3))
    quiet[:, 2] = 1.0
    assert PS.window_of(quiet, np.zeros((1600, 3))) is None
    acc, gyro = _event(amp=60.0)
    w = PS.window_of(acc, gyro)
    assert w is not None and w[0].shape == (C.WIN_N, 3) and w[0].max() <= C.MPU_RANGE_G + 1e-9
    assert np.abs(w[0][C.PRE_N]).max() > C.TRIGGER_G * 0.9  # the trigger sample sits at the window position PRE_N or just before


def test_a_larger_amplitude_triggers_a_window_that_a_smaller_one_does_not():
    acc, gyro = _event(amp=2.5)
    assert PS.window_of(PS.transform_event(acc, gyro, 0.25, 1.0)[0], gyro) is None
    assert PS.window_of(PS.transform_event(acc, gyro, 2.0, 1.0)[0], gyro) is not None
