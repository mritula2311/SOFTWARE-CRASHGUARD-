"""Tests of the L9 module (V16 section 15.5)."""
from __future__ import annotations

import numpy as np
import pytest

from crashguard import r5_l9 as L


def test_constants():
    assert (L.F_PRE, L.PHI) == (0.1, 0.5)


def test_thresholds_formula_and_known_value():
    t = L.thresholds(0.108155, 1750.0 / 60000.0)
    assert t["act_vs_wait"] == pytest.approx((1 - 0.108155) * (1750 / 60000) / 0.108155)
    assert t["act_vs_wait"] == pytest.approx(0.2405, abs=0.001)
    assert t["pre_vs_act"] == pytest.approx(t["act_vs_wait"] * 0.5 / 0.9) and t["pre_vs_wait"] == pytest.approx(t["act_vs_wait"] * 5.0)
    assert L.thresholds(0.5, 0.1)["act_vs_wait"] == pytest.approx(0.1)
    assert L.thresholds(0.2, 0.1, f_pre=0.2, phi=0.4)["pre_vs_wait"] == pytest.approx(L.thresholds(0.2, 0.1)["act_vs_wait"] * 2.0)


def test_best_option_matches_the_thresholds():
    r, g = 0.108155, 1750 / 60000
    t = L.thresholds(r, g)
    assert L.best_option(0.5 * t["pre_vs_act"], r, g) == "act"
    assert L.best_option(0.5 * (t["pre_vs_act"] + t["pre_vs_wait"]), r, g) == "pre"
    assert L.best_option(2.0 * t["pre_vs_wait"], r, g) == "wait"
    # at the break-even values the two options have equal cost
    rho = t["act_vs_wait"]
    assert r * rho == pytest.approx((1 - r) * g)
    rho2 = t["pre_vs_act"]
    assert r * rho2 == pytest.approx(L.F_PRE * r * rho2 + (1 - r) * (1 - L.PHI) * g)
    rho3 = t["pre_vs_wait"]
    assert (1 - r) * g == pytest.approx(L.F_PRE * r * rho3 + (1 - r) * (1 - L.PHI) * g)


def test_interval_bootstrap_brackets_the_point_and_is_deterministic():
    b = L.boot(0.108, 0.097, 0.120, 1750.0, 1750.0, 1750.0)
    t = L.thresholds(0.108, 1750 / 60000)
    for k in t:
        assert b[k][0] < t[k] < b[k][1]
    assert L.boot(0.108, 0.097, 0.120, 1750.0, 1750.0, 1750.0) == b
    assert L.boot(0.108, 0.097, 0.120, 1750.0, 1700.0, 1800.0) != b
    assert L.sd_from_interval(0.0, 3.92) == pytest.approx(1.0)
    assert all(np.isfinite(v) for lohi in b.values() for v in lohi)


def test_regression_values():
    b = L.boot(0.108, 0.097, 0.120, 1750.0, 1700.0, 1800.0)
    assert b["act_vs_wait"] == pytest.approx((0.2150384183766234, 0.27513913705269816)) and b["pre_vs_act"] == pytest.approx((0.119465787987013, 0.15285507614038785))
    t = L.thresholds(0.2, 0.1)
    assert t["act_vs_wait"] == pytest.approx(0.4) and t["pre_vs_act"] == pytest.approx(0.2222222) and t["pre_vs_wait"] == pytest.approx(2.0)
    assert (L.best_option(0.9, 0.2, 0.1), L.best_option(0.3, 0.2, 0.1), L.best_option(0.01, 0.2, 0.1)) == ("pre", "pre", "act")
    assert L.best_option(5.0, 0.2, 0.1) == "wait"
    # a larger share captured by the pre-alert moves the pre-alert-versus-wait boundary
    assert L.thresholds(0.2, 0.1, phi=0.8)["pre_vs_wait"] > t["pre_vs_wait"] and L.thresholds(0.2, 0.1, phi=0.8)["pre_vs_act"] < t["pre_vs_act"]
