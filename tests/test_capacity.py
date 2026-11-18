"""X6: ALOHA formulas, the base ACK limit and the multi-car simulation (small cases)."""
import numpy as np
import pytest

from crashguard import capacity as K
from crashguard import packet as P

SP = dict(rho=0.0, m=0.5, jitter=0.0, sf_raise=1)


def test_aloha_success_decreases_with_load_and_capture_helps():
    a = [K.aloha_success(n, 7, 600.0, 0.1, "alert", False) for n in (1, 10, 100, 500)]
    assert a[0] == 1.0 and a == sorted(a, reverse=True)
    assert K.aloha_success(500, 7, 60.0, 0.1, "alert", True) > K.aloha_success(500, 7, 60.0, 0.1, "alert", False)
    assert K.aloha_success(100, 12, 600.0, 0.1, "alert", False) < K.aloha_success(100, 7, 600.0, 0.1, "alert", False)  # slower spreading factor, longer packets


def test_base_ack_limit_matches_the_duty_cycle():
    for sf in (7, 9, 12):
        assert K.base_ack_limit_per_hour(sf) == pytest.approx(0.1 * 3600.0 / K.air(P.ACK_LEN, sf))
    assert K.base_ack_limit_per_hour(7) > 10 * K.base_ack_limit_per_hour(12)


def test_single_car_delivery_follows_the_retry_budget():
    # one car, no collisions possible: per-try success 0.9 x 0.9 = 0.81, fixed policy has 4 tries -> about 0.9987
    rs = [K.simulate(K.Cfg(n=1, sf=7, hb_period_s=600.0, policy="fixed3", rate_per_car_h=60.0, seed=s, hour=0), SP) for s in range(8)]
    d = np.nanmean([r["delivered_all"] for r in rs])
    n = sum(r["alerts"] for r in rs)
    assert n > 200 and d > 0.97
    assert all(r["alert_tx_collided_share"] == 0.0 for r in rs)


def test_many_cars_at_a_slow_spreading_factor_collide_more_than_few():
    few = K.simulate(K.Cfg(n=10, sf=12, hb_period_s=60.0, policy="severity", seed=0, hour=0), SP)
    many = K.simulate(K.Cfg(n=200, sf=12, hb_period_s=60.0, policy="severity", seed=0, hour=0), SP)
    assert many["hb_delivery"] < few["hb_delivery"]


def test_policies_see_the_same_arrivals():
    a = K.simulate(K.Cfg(n=50, sf=7, hb_period_s=600.0, policy="fixed3", rate_per_car_h=5.0, seed=1, hour=0), SP)["alerts"]
    b = K.simulate(K.Cfg(n=50, sf=7, hb_period_s=600.0, policy="scheduler", rate_per_car_h=5.0, seed=1, hour=0), SP)["alerts"]
    assert a == b
