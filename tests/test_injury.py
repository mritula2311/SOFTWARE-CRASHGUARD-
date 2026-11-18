"""X2: rank correlations, partial correlation and the criteria table (synthetic inputs only)."""
import numpy as np
import pytest

from crashguard import injury as I


def test_spearman_monotone_and_reversed():
    x = np.arange(20.0)
    assert I.spearman(x, x ** 3) == pytest.approx(1.0)
    assert I.spearman(x, -x) == pytest.approx(-1.0)
    assert np.isnan(I.spearman(x, np.ones(20)))


def test_partial_correlation_removes_a_common_cause():
    rng = np.random.default_rng(0)
    z = rng.normal(size=400)
    x = z + 0.3 * rng.normal(size=400)
    y = z + 0.3 * rng.normal(size=400)
    assert I.spearman(x, y) > 0.7
    assert abs(I.partial_spearman(x, y, z)) < 0.2  # x and y are related only through z


def test_partial_correlation_keeps_a_direct_effect():
    rng = np.random.default_rng(1)
    z = rng.normal(size=400)
    x = z + rng.normal(size=400)
    y = x + 0.2 * rng.normal(size=400) + z
    assert I.partial_spearman(x, y, z) > 0.5


def test_femur_limit_is_2250_pounds_in_newtons():
    assert I.N_FEMUR_LIMIT == pytest.approx(2250 * 4.4482216, rel=1e-3)
