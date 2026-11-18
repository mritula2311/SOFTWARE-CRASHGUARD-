import numpy as np

from crashguard import config as C
from crashguard.features import compute_features, process_event


def _sig(n=1600):
    a = np.zeros((n, 3), np.float32)
    a[:, 2] = 1.0
    return a, np.zeros((n, 3), np.float32)


def test_rest_signal_features():
    a, g = _sig(C.WIN_N)
    f = compute_features(a[None], g[None])[0]
    d = dict(zip(C.FEATURES, f))
    assert abs(d["peak_a"] - 1) < 1e-6 and d["rms_a"] < 1e-6 and d["dur_above"] == 0 and d["gyro_peak"] == 0


def test_trigger_window_and_padding():
    a, g = _sig()
    a[500, 0] = 3.0  # |a| = sqrt(10) > 2
    r = process_event(a, g)
    wa, _, pb, pa = r["windows"]["trig_2"]
    assert wa.shape == (C.WIN_N, 3) and not pb and not pa
    assert np.argmax(np.linalg.norm(wa, axis=1)) == C.PRE_N  # trigger sample sits PRE_N into the window
    a[5, 0] = 3.0  # trigger near the start -> pad before
    assert process_event(a, g)["windows"]["trig_2"][2]


def test_not_triggered_and_corrupt():
    a, g = _sig()
    assert process_event(a, g)["windows"]["trig_2"] is None
    a[10, 0] = 50.0
    assert process_event(a, g)["dropped"]


def test_gyro_converted_to_rad_per_s():
    a, g = _sig(C.WIN_N)
    g[10, 0] = 180.0
    f = dict(zip(C.FEATURES, compute_features(a[None], g[None])[0]))
    assert abs(f["gyro_peak"] - np.pi) < 1e-5
