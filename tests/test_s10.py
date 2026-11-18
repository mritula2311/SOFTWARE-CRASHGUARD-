import numpy as np

from crashguard.s10_adaptive import Prep, adjust, cost_theta, counts_at, em_prior, k_raw, q_threshold


def test_q_threshold_is_equivalent_to_the_adjusted_posterior_rule():
    q = np.linspace(0.001, 0.999, 400)
    for pi_dep, pi_tr, th in ((0.001, 0.17, 0.5), (0.2, 0.17, 0.3), (0.0002, 0.1, 1e-4)):
        qt = q_threshold(th, pi_dep, pi_tr)
        assert np.all((adjust(q, pi_dep, pi_tr) >= th) == (q >= qt))


def test_adjustment_is_identity_when_the_prior_does_not_change():
    q = np.array([0.1, 0.5, 0.9])
    assert np.allclose(adjust(q, 0.17, 0.17), q)


def test_em_recovers_the_deployment_prior_on_calibrated_scores():
    rng = np.random.default_rng(0)
    y = rng.random(100_000) < 0.02
    s = np.where(y, rng.normal(1, 1, y.size), rng.normal(-1, 1, y.size))
    q = 1 / (1 + np.exp(-2 * s))  # posterior under prior 0.5 for unit-variance gaussians 2 apart
    assert abs(em_prior(q, np.ones_like(q), 0.5) - 0.02) < 0.004


def test_cost_theta_falls_when_a_miss_costs_more_or_drivers_cancel_more():
    assert cost_theta(1000, 1, 0.9) < cost_theta(10, 1, 0.9)
    assert cost_theta(100, 1, 0.95) < cost_theta(100, 1, 0.5)
    assert np.isclose(cost_theta(1.0, 1.0, 0.0) , 0.5)


def test_cumulative_counts_and_raw_threshold_index():
    P = Prep.__new__(Prep)
    P.s_sorted = np.array([0.9, 0.8, 0.8, 0.1, -1.0])
    assert k_raw(P, 0.8) == 3 and k_raw(P, 0.95) == 0 and k_raw(P, 0.0) == 4
    cum = np.cumsum([1, 0, 2, 5, 1])
    assert counts_at(cum, 0) == 0 and counts_at(cum, 3) == 3


def test_target_threshold_takes_the_highest_recall_that_meets_the_target():
    P = Prep.__new__(Prep)
    P.val_t = np.array([0.9, 0.7, 0.5, 0.3])
    P.val_r = np.array([0.2, 0.5, 0.8, 0.95])
    P.val_f = np.array([0.0001, 0.001, 0.01, 0.1])
    t = P.target_threshold(0.01, 0.5)  # PPV at 1%: 0.67, 0.34... compute: 0.01*r/(0.01*r+0.99*f)
    ppv = 0.01 * P.val_r / (0.01 * P.val_r + 0.99 * P.val_f)
    assert ppv[0] >= 0.5 and (ppv[1] < 0.5 or t == 0.7)
    assert P.target_threshold(0.0001, 0.99) is None
