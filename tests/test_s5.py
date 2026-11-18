import numpy as np

from crashguard.capacity import P_DOWN, P_UP, Cfg, simulate
from crashguard.s5_burst import classify, paired_row

SP = dict(rho=0.0, m=0.5, jitter=0.0, sf_raise=1)


def test_classify_signs():
    assert classify(0.1, 0.3) == "better" and classify(-0.3, -0.1) == "worse" and classify(-0.1, 0.2) == "no_difference"
    assert classify(1.0, 3.0, latency=True) == "longer" and classify(-3.0, -1.0, latency=True) == "shorter"


def test_paired_row_drops_undefined_seeds():
    a = np.array([0.2, 0.3, np.nan, 0.25, 0.3])
    b = a + 0.1
    d, lo, hi, n = paired_row(a, b)
    assert n == 4 and abs(d - 0.1) < 1e-12 and lo <= d <= hi


def test_explicit_defaults_equal_implicit_defaults():
    a = simulate(Cfg(n=50, sf=7, hb_period_s=600.0, policy="severity", burst=True, seed=3, hour=0), SP)
    b = simulate(Cfg(n=50, sf=7, hb_period_s=600.0, policy="severity", burst=True, seed=3, hour=0, p_up=P_UP, p_down=P_DOWN, burst_cars=30, capture="db6", hb_bytes=16), SP)
    assert a == b


def test_pure_aloha_collides_at_least_as_often_as_capture():
    kw = dict(n=100, sf=7, hb_period_s=600.0, policy="fixed3", burst=True, seed=5, hour=0)
    with_capture = simulate(Cfg(**kw, capture="db6"), SP)
    without = simulate(Cfg(**kw, capture="none"), SP)
    assert without["alert_tx_collided_share"] >= with_capture["alert_tx_collided_share"]
    assert without["delivered_critical"] <= with_capture["delivered_critical"] + 0.05


def test_burst_size_option_sets_the_number_of_critical_alerts():
    r = simulate(Cfg(n=100, sf=7, hb_period_s=600.0, policy="severity", burst=True, seed=1, hour=0, burst_cars=10, rate_per_car_h=0.0), SP)
    assert r["n_critical"] == 10
