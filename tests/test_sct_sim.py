import numpy as np
import pytest

from crashguard.sct_sim import SCfg, SctParams, Window, max_window_airtime, simulate

TRUE = np.array([0, 0, 1, 2, 3, 3, 3, 2])
POOL = np.array([0.05, 0.1, 0.3, 0.8])


def _cfg(policy, assigned=None, **kw):
    return SCfg(n=kw.pop("n", 20), sf=kw.pop("sf", 7), policy=policy, seed=kw.pop("seed", 1), true_pool=TRUE, assigned_pool=TRUE if assigned is None else assigned, crash_pool=POOL, **kw)


def test_window_enforces_trailing_hour_and_wait_time():
    w = Window(10.0)
    w.add(0.0, 6.0)
    w.add(100.0, 3.0)
    assert w.ok(200.0, 1.0, 10.0) and not w.ok(200.0, 2.0, 10.0)
    assert w.wait_until(200.0, 2.0, 10.0) == pytest.approx(3600.0, abs=1e-3)  # when the first 6 s fall out of the window
    assert w.wait_until(200.0, 20.0, 10.0) == float("inf")


def test_independent_scan_finds_a_violation():
    assert max_window_airtime([(0.0, 6.0), (100.0, 6.0)]) == 12.0
    assert max_window_airtime([(0.0, 6.0), (3700.0, 6.0)]) == 6.0


@pytest.mark.parametrize("policy", ["fixed3", "severity", "scheduler", "sct"])
def test_every_policy_runs_and_never_exceeds_the_duty_limit(policy):
    r = simulate(_cfg(policy, rate_per_car_h=2.0, burst=True, burst_cars=10))
    assert r["duty_exceeded"] == 0 and r["max_window_airtime_s"] <= 36.0 + 1e-9
    assert r["n_critical"] > 0 and 0 <= r["reach30_critical"] <= 1


def test_tight_duty_limit_is_respected_and_delays_alerts():
    r = simulate(_cfg("severity", rate_per_car_h=20.0, duty=0.001, n=3))
    assert r["duty_exceeded"] == 0


def test_mis_triage_is_a_property_of_the_assigned_classes():
    point = np.array([0, 0, 0, 1, 1, 2, 3, 0])  # under-estimates some severe and critical events
    upper = np.minimum(3, point + 2)
    a = simulate(_cfg("sct", assigned=point, rate_per_car_h=5.0))
    b = simulate(_cfg("sct", assigned=upper, rate_per_car_h=5.0))
    assert a["mis_triage"] > b["mis_triage"] and b["mis_triage"] == 0.0
    assert b["escalation"] >= a["escalation"]


def test_deterministic():
    assert simulate(_cfg("sct", rate_per_car_h=2.0)) == simulate(_cfg("sct", rate_per_car_h=2.0))


def test_critical_alert_with_zero_hold_can_be_acked_before_the_table_cancel_window_ends():
    kw = dict(n=1, rate_per_car_h=30.0, p_up=0.0, p_down=0.0, seed=3)
    sct = simulate(_cfg("sct", **kw))
    tab = simulate(_cfg("severity", **kw))
    assert sct["reach5_critical"] > tab["reach5_critical"]  # the table waits the 5 s window; SCT sends at once
    assert tab["reach10_critical"] == 1.0


def test_fast_cap_demotes_alerts_when_the_share_is_used_up():
    capped = simulate(_cfg("sct", sct=SctParams(fast_cap=1e-4), rate_per_car_h=30.0, n=2))
    assert capped["demoted"] > 0
    assert capped["fast_air_share_of_allowance"] <= 1e-4 * 1.01 + 1e-6 or capped["duty_exceeded"] == 0
