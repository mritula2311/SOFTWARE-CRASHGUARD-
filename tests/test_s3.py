import numpy as np

from crashguard.conformal import conformal_threshold
from crashguard.s3_conformal import size_weights, weighted_threshold


def test_equal_weights_match_split_conformal():
    rng = np.random.default_rng(0)
    s = rng.random(199)
    t = weighted_threshold(s, np.ones_like(s), 0.05)
    assert t == conformal_threshold(s, 0.05)


def test_no_alarm_threshold_when_weight_never_reaches_target():
    assert weighted_threshold(np.array([0.1, 0.2]), np.ones(2), 0.01) == float("inf")


def test_size_weights_match_the_test_mix():
    cal = np.array(["Light"] * 80 + ["Heavy"] * 20)
    test = np.array(["Light"] * 50 + ["Heavy"] * 50)
    w = size_weights(cal, test)
    # weighted share of Heavy among calibration events = 0.5
    assert abs(w[cal == "Heavy"].sum() / w.sum() - 0.5) < 1e-12


def test_weights_are_zero_for_a_category_missing_from_the_test_mix():
    w = size_weights(np.array(["A", "B"]), np.array(["A", "A"]))
    assert list(w) == [2.0, 0.0] or (w[1] == 0.0 and w[0] > 0)
