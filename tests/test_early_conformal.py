"""X3 early exit rule and X4 conformal thresholds (synthetic inputs only)."""
import math

import numpy as np
import pandas as pd

from crashguard import conformal as K
from crashguard import early as E


def test_early_exit_decides_at_the_first_confident_checkpoint():
    S = np.array([
        [0.99, 0.5, 0.5, 0.5, 0.5, 0.5],  # confident crash at the first checkpoint
        [0.01, 0.5, 0.5, 0.5, 0.5, 0.5],  # confident non-crash at the first checkpoint
        [0.5, 0.5, 0.95, 0.5, 0.5, 0.5],  # confident crash at the third checkpoint
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.9],  # waits for the end; the final threshold decides
        [0.5, 0.5, 0.5, 0.5, 0.5, 0.2],  # waits for the end; below the final threshold
    ])
    hi, lo = np.full(5, 0.9), np.full(5, 0.05)
    alarm, t = E.early_decisions(S, hi, lo, 0.6)
    assert alarm.tolist() == [True, False, True, True, False]
    assert t.tolist() == [50, 50, 200, 1800, 1800]


def test_no_early_exit_equals_the_fixed_window():
    S = np.random.default_rng(0).random((200, 6))
    alarm, t = E.early_decisions(S, np.full(5, np.inf), np.full(5, -np.inf), 0.7)
    assert np.array_equal(alarm, S[:, -1] >= 0.7) and (t == 1800).all()


def test_scatter_puts_scores_at_the_right_events_and_minus_one_elsewhere():
    full = pd.DataFrame(dict(event_id=[10, 11, 12, 13]))
    out = E.scatter(full, np.array([12, 10]), np.array([0.7, 0.2]))
    assert out.tolist() == [0.2, -1.0, 0.7, -1.0]


def test_mcu_cost_is_positive_and_small_against_the_sample_period():
    c = E.mcu_cost()
    assert c["cycles_per_sample_assumed"] > 0 and c["state_bytes"] > 300 and c["share_of_sample_period"] < 0.01


def test_conformal_threshold_rank_rule():
    s = np.arange(1.0, 100.0)  # n = 99
    # k = ceil(100 * 0.9) = 90 -> the 90th smallest value
    assert K.conformal_threshold(s, 0.1) == 90.0
    assert K.conformal_threshold(np.arange(1.0, 10.0), 0.05) == float("inf")  # k = ceil(10 * 0.95) = 10 > n = 9: no alarms


def test_conformal_false_alarm_rate_is_at_most_alpha_on_average_for_exchangeable_scores():
    rng = np.random.default_rng(1)
    alpha, fa = 0.05, []
    for _ in range(400):
        cal = rng.normal(size=300)
        new = rng.normal(size=20000)
        fa.append(float((new > K.conformal_threshold(cal, alpha)).mean()))
    assert np.mean(fa) <= alpha + 0.002
    assert np.mean(fa) >= alpha - 0.01  # and it is not wildly conservative


def test_conformal_breaks_when_the_test_distribution_shifts():
    rng = np.random.default_rng(2)
    cal = rng.normal(size=2000)
    thr = K.conformal_threshold(cal, 0.05)
    shifted = rng.normal(loc=1.0, size=20000)
    assert (shifted > thr).mean() > 0.2  # far above alpha: the guarantee needs exchangeability


def test_empirical_threshold_keeps_calibration_rate_at_most_alpha():
    rng = np.random.default_rng(3)
    cal = rng.normal(size=1000)
    thr = K.empirical_threshold(cal, 0.05)
    assert (cal >= thr).mean() <= 0.05 + 1e-12
    assert math.isfinite(thr)
