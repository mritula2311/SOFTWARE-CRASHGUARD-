import numpy as np

from crashguard.s9_conformal_dv import cvplus, decision_class


def test_cvplus_constant_model_and_residuals_gives_relative_band():
    f_test = np.full((5, 3), 40.0)
    fold = np.repeat(np.arange(5), 20)
    r = np.full(100, 0.25)
    lo, hi = cvplus(f_test, fold, r, 0.1)
    assert np.allclose(lo, 30.0) and np.allclose(hi, 50.0)


def test_cvplus_uses_the_floor_and_ceil_order_statistics():
    n = 19  # alpha 0.1: floor(2.0) = 2nd smallest lower, ceil(18.0) = 18th smallest upper
    f_test = np.ones((1, 1))
    r = np.linspace(0.01, 0.19, n)
    lo, hi = cvplus(f_test, np.zeros(n, int), r, 0.1)
    assert np.isclose(lo[0], 1 - np.sort(r)[::-1][1]) and np.isclose(hi[0], 1 + np.sort(r)[17])


def test_cvplus_small_calibration_set_gives_infinite_upper_bound():
    lo, hi = cvplus(np.ones((1, 1)), np.zeros(5, int), np.full(5, 0.1), 0.01)
    assert np.isinf(hi[0]) and lo[0] == 0.0


def test_decision_class_reports_the_class_below_when_the_lower_bound_is_lower():
    dv = np.array([45.0, 45.0, 10.0])
    lo = np.array([42.0, 30.0, 5.0])
    cls, flag = decision_class(dv, lo, np.zeros(3))
    assert list(flag) == [False, True, False] and list(cls) == [2, 1, 0]


def test_asi_class_can_dominate():
    cls, flag = decision_class(np.array([10.0]), np.array([5.0]), np.array([1.6]))
    assert cls[0] == 2 and not flag[0]
