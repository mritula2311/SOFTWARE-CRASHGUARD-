"""N15 (trigger-aware training) and N16 (severity- and budget-aware scheduler): rules, bounds and engine behaviour on small synthetic inputs."""
import random

import numpy as np
import pytest

from crashguard import detector_extra as D
from crashguard import replay as RP
from crashguard import scheduler as SCH
from crashguard import trigger_aware as TA

# ----------------------------------------------------------------------------- N15


def test_candidate_grid_has_the_documented_size_and_names():
    c = TA.candidates()
    assert len(c) == 4 + 4 * 3 * 3 and len(set(map(TA.cand_name, c))) == len(c)
    assert TA.cand_name((3.0, None, None)) == "p3" and TA.cand_name((2.0, 100.0, 1.0)) == "p2_j100_e1"


def _pulse(peak=3.0, rise=4):
    mag = np.ones(300)
    mag[100:100 + rise] = np.linspace(1.0, peak, rise)
    mag[100 + rise:110 + rise] = peak
    return mag


def test_magnitude_rule_fires_at_the_first_sample_above_p():
    mag = _pulse(peak=3.5)
    assert TA.trigger_index(mag, (3.0, None, None)) == int(np.flatnonzero(mag > 3.0)[0])
    assert TA.trigger_index(mag, (4.0, None, None)) is None


def test_jerk_and_energy_rule_fires_where_the_level_rule_does_not():
    mag = np.ones(300)
    mag[100:110] = 3.5  # sustained but below p = 4 g: needs the jerk and energy rule (ten samples of 2.5 g deviation give 0.625 g^2 s)
    assert TA.trigger_index(mag, (4.0, None, None)) is None
    first = TA.trigger_index(mag, (4.0, 50.0, 0.5))
    assert first == 110  # jerk and energy must hold at the same sample: the step down at 110 still has 0.56 g^2 s in its window
    # energy needs ten samples of history: a one-sample spike has jerk but no energy
    spike = np.ones(300)
    spike[100] = 3.0
    assert TA.trigger_index(spike, (4.0, 50.0, 0.5)) is None


def test_running_features_use_only_the_previous_sample_and_a_ten_sample_ring():
    mag = np.ones(50)
    mag[20] = 2.0
    jerk, en = TA.running_features(mag)
    assert jerk[20] == pytest.approx(100.0) and jerk[21] == pytest.approx(100.0) and jerk[5] == 0.0
    assert en[19] == 0.0 and en[20] == pytest.approx(1.0 * 0.01) and en[29] == pytest.approx(0.01) and en[30] == 0.0


def test_learned_trigger_cost_is_small_and_counted_from_the_rule():
    c = TA.learned_trigger_cost()
    assert c["state_bytes"] < 100 and c["cycles_assumed"] > 0 and c["cycles_assumed"] < 0.001 * c["period_cycles_at_240mhz_100hz"]


def test_threshold_for_fpr_never_exceeds_the_target_on_the_validation_scores():
    rng = np.random.default_rng(0)
    y = np.r_[np.zeros(2000), np.ones(500)].astype(int)
    s = np.r_[rng.beta(2, 5, 2000), rng.beta(5, 2, 500)]
    s[rng.random(len(s)) < 0.4] = -1.0  # events the trigger discarded are never alarms
    for target in (0.01, 0.05):
        thr = D.threshold_for_fpr(y, s, target)
        assert D.sys_rates(y, s, thr)["fpr"] <= target + 1e-12


# ----------------------------------------------------------------------------- N16


def _alert(sev, arrival, tries=0):
    return dict(sev=sev, arrival=arrival, tries=tries)


def test_scheduler_orders_by_class_and_age_without_letting_age_beat_a_higher_class():
    p = SCH.Scheduler()
    old_low, new_low = _alert(0, 0.0), _alert(0, 100.0)
    assert p.key(old_low, 400.0) < p.key(new_low, 400.0)  # same class: older first
    assert p.key(_alert(1, 399.0), 400.0) < p.key(old_low, 400.0)  # a higher class beats an old lower one (age bonus is below 1)
    assert p.key(_alert(3, 399.0), 400.0) < p.key(_alert(2, 0.0), 400.0)


def test_retry_spacing_grows_is_capped_has_bounded_jitter_and_follows_feedback():
    rng = random.Random(1)
    p = SCH.Scheduler(m=1.0, jitter=0.0)
    delays = [p.retry_ready(_alert(3, 0.0, k), 10.0, 0.5, rng) - 10.5 for k in range(1, 8)]
    assert delays[0] == pytest.approx(0.5) and delays[1] == pytest.approx(1.0) and max(delays) <= SCH.CAP_S[3] + 1e-9 and delays == sorted(delays)
    j = SCH.Scheduler(m=1.0, jitter=0.5)
    d = [j.retry_ready(_alert(2, 0.0, 2), 0.0, 0.0, rng) for _ in range(200)]
    assert min(d) >= 2.0 - 1e-9 and max(d) <= 3.0 + 1e-9  # base 1 s x 2 x (1 + 0.5 u)
    bad = SCH.Scheduler(m=1.0, jitter=0.0)
    for _ in range(10):
        bad.observe(False)
    assert bad.retry_ready(_alert(2, 0.0, 1), 0.0, 0.0, rng) > SCH.Scheduler().retry_ready(_alert(2, 0.0, 1), 0.0, 0.0, rng)  # failing link: longer spacing
    assert 0.0 <= bad.p_hat < 0.1


def test_spreading_factor_raise_needs_three_failures_a_high_enough_class_and_budget():
    p = SCH.Scheduler(sf_raise=True)
    assert p.sf_for(_alert(2, 0, 2), 7, 100.0) == 7  # only two failures
    assert p.sf_for(_alert(0, 0, 3), 7, 100.0) == 7  # low class
    assert p.sf_for(_alert(2, 0, 3), 7, 0.1) == 7  # not enough tokens
    assert p.sf_for(_alert(2, 0, 3), 7, 100.0) == 8
    assert p.sf_for(_alert(2, 0, 3), 12, 100.0) == 12
    assert SCH.Scheduler(sf_raise=False).sf_for(_alert(2, 0, 3), 7, 100.0) == 7


def test_reserve_keeps_tokens_for_critical_alerts():
    p = SCH.Scheduler(rho=0.2)
    assert p.reserve_frac == 0.2 and not p.may_spend(_alert(0, 0), 60.0, 0.2, 360.0) and p.may_spend(_alert(3, 0), 60.0, 0.2, 360.0)
    assert p.may_spend(_alert(0, 0), 100.0, 0.2, 360.0)


def test_grid_has_24_combinations():
    g = SCH.grid()
    assert len(g) == 24 and len({x.name for x in g}) == 24


def test_burst_channel_has_the_requested_mean_loss_and_is_bursty():
    for kind in ("iid", "ge"):
        ch = RP.Channel(kind, 0.3, 0.1, random.Random(5))
        up = np.array([ch.lost("up") for _ in range(40000)])
        down = np.array([ch.lost("down") for _ in range(40000)])
        assert up.mean() == pytest.approx(0.3, abs=0.02) and down.mean() == pytest.approx(0.1, abs=0.02)
        if kind == "ge":
            np.diff(np.flatnonzero(np.diff(np.r_[0, up.astype(int), 0]))) [::2]
            assert up[1:][up[:-1]].mean() > up.mean() + 0.2  # a loss makes the next loss more likely


def test_loss_scale_lowers_the_loss():
    ch = RP.Channel("iid", 0.4, 0.4, random.Random(2))
    assert np.mean([ch.lost("up", 0.5) for _ in range(30000)]) == pytest.approx(0.2, abs=0.02)


def test_engine_reports_by_true_class_and_policy_state_does_not_leak_between_hours():
    pairs = np.array([[0, 3]] * 20 + [[3, 3]] * 20)  # estimated low, truly critical, for half the alerts
    sc = RP.Scenario("t", 7, 60, loss_up=0.3, loss_down=0.3)
    sched = SCH.Scheduler(rho=0.2, jitter=0.5)
    a = RP.simulate(pairs, sc, sched, random.Random("a"), random.Random("c"))
    assert sched.p_hat == 1.0  # the caller's policy object is untouched
    b = RP.simulate(pairs, sc, sched, random.Random("a"), random.Random("c"))
    assert [x["t_ack"] for x in a] == [x["t_ack"] for x in b]  # same seeds, same hour
    s = RP.summarise(a)
    assert s["n_critical"] == s["n_all"] and "n_low" not in s  # reported by the true class
    assert all(x["true"] == 3 for x in a)


def test_engine_scheduler_not_worse_than_none_for_critical_alerts():
    pool = np.repeat([0, 1, 2, 3], 10)
    sc = RP.Scenario("t", 7, 120, loss_up=0.4, loss_down=0.4)
    none = RP.run_config(pool, sc, RP.POLICIES["none"], seeds=(1,), hours=4)
    sched = RP.run_config(pool, sc, SCH.Scheduler(), seeds=(1,), hours=4)
    assert sched.delivered_critical.mean() > none.delivered_critical.mean()
