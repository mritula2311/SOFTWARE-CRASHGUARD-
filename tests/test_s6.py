import numpy as np
import pandas as pd

from crashguard.early import LENGTHS_MS, early_decisions
from crashguard.s6_early import truncated_scores


class _Dummy:
    """predict_proba returns the first feature column, so the score tells which length's rows were used."""

    def predict_proba(self, x):
        p = np.clip(x[:, 0], 0, 1)
        return np.stack([1 - p, p], axis=1)


def test_truncated_scores_use_the_row_of_each_events_own_length():
    n = 6
    feats = {m: pd.DataFrame({"a": np.full(n, k / 10.0)}) for k, m in enumerate(LENGTHS_MS)}
    times = np.array([50, 100, 200, 400, 800, 1800])
    s = truncated_scores(_Dummy(), feats, times)
    assert np.allclose(s, [0.0, 0.1, 0.2, 0.3, 0.4, 0.5])


def test_releasing_decisions_late_does_not_change_the_alarm_set():
    """E' (same rule, decisions released at 1,800 ms) is E with the time replaced: the alarms come from the same function."""
    rng = np.random.default_rng(0)
    S = rng.random((200, 6))
    hi, lo = np.full(5, 0.9), np.full(5, 0.05)
    alarm, t = early_decisions(S, hi, lo, 0.5)
    assert (t <= 1800).all() and t.min() < 1800
    alarm2, _ = early_decisions(S, hi, lo, 0.5)
    assert (alarm == alarm2).all()
