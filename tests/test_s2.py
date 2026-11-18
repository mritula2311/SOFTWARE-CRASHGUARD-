import numpy as np
from sklearn.metrics import average_precision_score

from crashguard.s2_dedup import fast_ap, metrics


def test_fast_ap_matches_sklearn_with_ties():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 500)
    s = np.round(rng.random(500), 1)
    s[:100] = -1.0
    assert abs(fast_ap(y, s) - average_precision_score(y, s)) < 1e-12


def test_metrics_basic():
    y = np.array([1, 1, 0, 0])
    s = np.array([0.9, -1.0, 0.8, 0.1])
    m = metrics(y, s, s >= 0, 0.5)
    assert m["sys_recall"] == 0.5 and m["sys_fpr"] == 0.5
