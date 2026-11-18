"""Unit, property and known-answer tests of the pure core of crashguard.r6_seq (R6-2, V17 section 4)."""
import json
from pathlib import Path

import numpy as np
import pytest

from crashguard import r6_common as C6
from crashguard import r6_seq as S

ROOT = Path(__file__).resolve().parents[1]


def test_bin_edges_equal_count():
    x = np.arange(1000.0)
    e = S.bin_edges(x, 10)
    assert len(e) == 9
    counts = np.bincount(np.searchsorted(e, x, side="right"), minlength=10)
    assert counts.min() >= 95 and counts.max() <= 105


def test_llr_table_identity_and_antisymmetry():
    rng = np.random.default_rng(1)
    sp, sn = rng.beta(5, 2, 500), rng.beta(2, 5, 700)
    e = S.bin_edges(np.r_[sp, sn], 8)
    t = S.llr_table(sp, sn, e, 1.0)
    nb = len(e) + 1
    c0 = np.bincount(np.searchsorted(e, sn, side="right"), minlength=nb) + 1.0
    assert abs(float((c0 / c0.sum() * np.exp(t)).sum()) - 1.0) < 1e-12  # sum_b f0(b) exp(llr(b)) = 1
    assert np.allclose(S.llr_table(sn, sp, e, 1.0), -t)
    assert t[-1] > 0 > t[0]  # high scores favour the crash class


def test_llr_table_empty_bin_is_finite():
    t = S.llr_table(np.array([0.9, 0.95]), np.array([0.1, 0.2]), np.array([0.5]), 1.0)
    assert np.isfinite(t).all()


def test_bin_side_matters_at_the_edge():
    t = S.llr_table(np.array([0.5, 0.9]), np.array([0.1]), np.array([0.5]), 1.0)  # 0.5 belongs to the upper bin
    c1 = np.array([0.0, 2.0]) + 1.0  # the upper bin holds 0.5 and 0.9, the lower bin none
    assert abs(t[1] - (np.log(c1[1] / c1.sum()) - np.log(1.0 / 3.0))) < 1e-12


def test_running_llr_is_the_cumulative_sum():
    edges = [np.array([0.5])] * S.NCHK
    tables = [np.array([-1.0, 2.0 + k]) for k in range(S.NCHK)]
    Sx = np.array([[0.9, 0.1, 0.9, 0.1, 0.9, 0.0], [0.1] * 6])
    L = S.running_llr(Sx, edges, tables)
    assert np.allclose(L[0], np.cumsum([2.0, -1.0, 4.0, -1.0, 6.0]))
    assert np.allclose(L[1], -np.arange(1, S.NCHK + 1))
    assert L.shape == (2, S.NCHK)


def test_seq_decisions_known_answers():
    L = np.array([[0, 0, 3.0, 3, 3],  # crosses A = 2 at checkpoint 2 (200 ms)
                  [-2.0, 0, 0, 0, 0],  # crosses B = -1 at checkpoint 0 (50 ms): no alarm
                  [0.5, 0.5, 0.5, 0.5, 0.5],  # undecided: 1800
                  [2.0, 2, 2, 2, 2],  # exactly A at checkpoint 0: alarm (inclusive)
                  [-1.0, 5, 5, 5, 5],  # exactly B at checkpoint 0: stop (inclusive)
                  [0, 0, 0, 0, 9.0]])  # alarm at checkpoint 4 (800 ms)
    al, t = S.seq_decisions(L, 2.0, -1.0)
    assert al.tolist() == [True, False, False, True, False, True]
    assert t.tolist() == [200, 50, 1800, 50, 50, 800]


def test_seq_decisions_upper_wins_a_tie_and_stop_is_final():
    L = np.array([[5.0, 5, 5, 5, 5]])
    al, t = S.seq_decisions(L, 2.0, 10.0)  # both thresholds crossed: the alarm check comes first
    assert al[0] and t[0] == 50
    L2 = np.array([[-5.0, 9, 9, 9, 9]])
    al2, t2 = S.seq_decisions(L2, 2.0, -1.0)
    assert not al2[0] and t2[0] == 50  # a stop is never reopened by a later checkpoint


def test_provisional_fa_counts_early_alarms_of_non_crash_only():
    alarm = np.array([True, True, True, False, True])
    t = np.array([50, 800, 1800, 50, 200.0])
    neg = np.array([True, True, True, True, False])
    assert S.provisional_fa(alarm, t, neg, 10) == pytest.approx(2 / 10)  # the 1800 ms alarm and the crash event do not count


def test_select_AB_picks_the_fastest_within_tolerance():
    # three events: a crash that alarms at checkpoint 0 for A <= 1 and at checkpoint 1 for A <= 2; a non-crash that reaches 1.5 at checkpoint 1
    L = np.array([[1.0, 2.0, 2, 2, 2], [0.0, 1.5, 1.5, 1.5, 1.5]])
    pos, neg = np.array([True, False]), np.array([False, True])
    best = S.select_AB(L, pos, neg, 2, 0.5, np.array([0.5, 1.0, 1.75]), np.array([-5.0]), 0.001)
    # A = 0.5 alarms the non-crash event at checkpoint 1 (fa 0.5: within the target) and the crash at 50 ms; A = 1.0 also alarms the crash at 50 ms; A = 1.75 alarms the crash at 100 ms only
    assert best["A"] == 1.0 and best["mean_t"] == 50.0
    assert S.select_AB(L, pos, neg, 2, 0.0, np.array([0.5]), np.array([-5.0]), 0.001) is None


def test_select_AB_tie_goes_to_the_larger_A():
    L = np.array([[3.0, 3, 3, 3, 3]])
    pos, neg = np.array([True]), np.array([False])
    best = S.select_AB(L, pos, neg, 1, 0.0, np.array([1.0, 2.0]), np.array([-5.0]), 0.001)
    assert best["A"] == 2.0 and best["B"] == -5.0


def test_select_AB_requires_B_below_A():
    L = np.array([[3.0, 3, 3, 3, 3]])
    pos, neg = np.array([True]), np.array([False])
    assert S.select_AB(L, pos, neg, 1, 0.0, np.array([1.0]), np.array([1.0]), 0.001) is None


def test_retraction_share():
    prov = np.array([True, True, True, False])
    full = np.array([True, False, True, True])
    assert S.retraction_share(prov, full) == pytest.approx(1 / 3)
    assert np.isnan(S.retraction_share(np.zeros(3, bool), full[:3]))


def test_boot_stats_constant_difference():
    n = 200
    t_f, t_s = np.full(n, 400.0), np.full(n, 100.0)
    prov = np.ones(n, bool)
    pos = np.ones(n, bool)
    full = np.ones(n, bool)
    st = S.boot_stats(t_f, t_s, prov, prov, pos, full, n_boot=200)
    assert st["a_pt"] == 300.0 and st["a_lo"] == 300.0 and st["a_hi"] == 300.0
    assert st["a_p"] == pytest.approx(1 / 201)  # no resample has a mean at or below 200 ms
    assert st["b_pt"] == 0.0 and st["b_hi"] == 0.0 and st["b_p"] == pytest.approx(1 / 201)  # no resample reaches +0.02


def test_boot_stats_directions():
    n = 300
    rng = np.random.default_rng(3)
    t_f = np.full(n, 150.0)
    t_s = np.full(n, 140.0)
    prov = np.ones(n, bool)
    pos = np.ones(n, bool)
    full = rng.random(n) > 0.1
    st = S.boot_stats(t_f, t_s, prov, prov, pos, full, n_boot=300)
    assert st["a_p"] == pytest.approx(1.0)  # a 10 ms difference is never above 200 ms
    full_s = full.copy()
    prov_s = prov.copy()
    st2 = S.boot_stats(t_f, t_s, prov, prov_s, pos, full_s, n_boot=300)
    assert st2["b_hi"] == 0.0
    # the sequential rule alarms on extra events that the full window rejects: the retraction share rises
    prov2 = prov.copy()
    full2 = full.copy()
    prov_f = prov & (np.arange(n) < 150)
    st3 = S.boot_stats(t_f, t_s, prov_f, prov2, pos, full2, n_boot=300)
    assert st3["b_pt"] == pytest.approx(S.retraction_share(prov2, full2) - S.retraction_share(prov_f, full2))
    assert st3["n_both"] == 150


def test_boot_stats_uses_only_events_alarming_under_both_rules():
    t_f = np.array([400.0, 400, 400, 400])
    t_s = np.array([100.0, 100, 100, 100])
    prov_f = np.array([True, True, False, True])
    prov_s = np.array([True, False, True, True])
    pos = np.array([True, True, True, False])
    st = S.boot_stats(t_f, t_s, prov_f, prov_s, pos, np.ones(4, bool), n_boot=50)
    assert st["n_both"] == 1


def test_half6_pinned_values():
    assert [C6.half6(i) for i in (1, 2, 3, 100, 12345, 99999)] == [1, 1, 0, 0, 1, 1]


def test_select_AB_paired_objective_needs_events_alarming_under_both_rules():
    # event 0: the fixed rule alarmed at 400 ms; event 1: the fixed rule made no provisional alarm. The sequential rule alarms event 1 earlier (50 ms) than event 0 (100 ms) for A <= 1.
    L = np.array([[0.0, 2.0, 2, 2, 2], [2.0, 2.0, 2, 2, 2]])
    pos, neg = np.array([True, True]), np.array([False, False])
    ref = (np.array([400.0, 1800.0]), np.array([True, False]))
    best = S.select_AB(L, pos, neg, 1, 0.0, np.array([1.0, 3.0]), np.array([-5.0]), 0.001, ref=ref)
    assert best is None or best["A"] == 1.0
    assert best["A"] == 1.0 and best["mean_t"] == pytest.approx(-300.0)  # paired objective: fixed 400 minus sequential 100, over event 0 only (mean_t is minus the difference)
    unpaired = S.select_AB(L, pos, neg, 1, 0.0, np.array([1.0, 3.0]), np.array([-5.0]), 0.001)
    assert unpaired["mean_t"] == pytest.approx(75.0)  # without ref the mean time of both alarmed events is minimised


def test_boot_stats_margin_is_exactly_200_ms():
    n = 100
    ones = np.ones(n, bool)
    below = S.boot_stats(np.full(n, 400.0), np.full(n, 201.0), ones, ones, ones, ones, n_boot=50)  # difference 199
    exact = S.boot_stats(np.full(n, 400.0), np.full(n, 200.0), ones, ones, ones, ones, n_boot=50)  # difference 200: not above 200
    above = S.boot_stats(np.full(n, 401.0), np.full(n, 200.0), ones, ones, ones, ones, n_boot=50)  # difference 201
    assert below["a_p"] == 1.0 and exact["a_p"] == 1.0
    assert above["a_p"] == pytest.approx(1 / 51)


def test_boot_stats_b_margin_is_0_02():
    n = 100
    ones = np.ones(n, bool)
    pos = ones
    full = np.ones(n, bool)
    prov_f = np.zeros(n, bool)
    prov_f[:50] = True  # fixed: 50 provisional, all confirmed (retraction 0)
    prov_s = prov_f.copy()
    prov_s[50:] = True
    full2 = full.copy()
    full2[50:] = False  # sequential: 100 provisional, 50 retracted (retraction 0.5): a large rise
    st = S.boot_stats(np.full(n, 100.0), np.full(n, 100.0), prov_f, prov_s, pos, full2, n_boot=100)
    assert st["b_pt"] == pytest.approx(0.5) and st["b_p"] == pytest.approx(1.0)  # every resample is above +0.02


def test_dev_load_builds_no_test_objects():
    pytest.importorskip("pandas")
    if not (ROOT / "data" / "processed" / "r5_det_seed42.pkl").exists():
        pytest.skip("cache not built")
    D = S.load(with_test=False)
    assert not any(k in D for k in ("St", "yt", "ids_te", "full_alarm_t", "alarm_ft", "tt_f"))


def test_half6_balanced_and_deterministic():
    h = np.array([C6.half6(i) for i in range(2000)])
    assert 900 < h.sum() < 1100
    assert C6.half6(12345) == C6.half6("12345")


def C5_half(i):  # noqa: N802
    import hashlib

    return int(hashlib.sha256(("r5|" + str(i)).encode()).hexdigest(), 16) % 2


def test_half6_differs_from_the_round5_rule():
    a = np.array([C6.half6(i) for i in range(500)])
    b = np.array([C5_half(i) for i in range(500)])
    assert (a != b).sum() > 100


def test_known_answer_fixed_rule_reproduces_the_stored_share_at_50_ms():
    res = ROOT / "results" / "results.json"
    pytest.importorskip("pandas")
    if not (ROOT / "data" / "processed" / "r5_det_seed42.pkl").exists():
        pytest.skip("cache not built")
    stored = {e["name"]: e["value"] for e in json.loads(res.read_text(encoding="utf-8"))}
    D = S.load()
    both = (D["yt"] == 1) & D["alarm_ft"] & D["full_alarm_t"]  # the R3 set (r3_t3): crash events with an alarm of the early-exit rule (E, including its 1,800 ms decisions) and a full-window alarm (F)
    share50 = float((D["tt_f"][both] == 50).mean())
    assert abs(share50 - stored["r3.t3.a1.share_decided_at_50ms"]) < 0.01


def test_running_llr_bin_side_at_an_edge():
    edges = [np.array([0.5])] * S.NCHK
    tables = [np.array([-1.0, 2.0])] * S.NCHK
    L = S.running_llr(np.array([[0.5] * 6]), edges, tables)  # a score equal to the edge belongs to the upper bin
    assert np.allclose(L[0], 2.0 * np.arange(1, S.NCHK + 1))


def test_select_AB_rejects_a_false_alarm_rate_far_below_the_target():
    L = np.array([[3.0, 3, 3, 3, 3], [0.0, 0, 0, 0, 0]])
    pos, neg = np.array([True, False]), np.array([False, True])
    assert S.select_AB(L, pos, neg, 2, 0.5, np.array([1.0]), np.array([-5.0]), 0.001) is None  # the pair gives fa = 0, the target is 0.5


def test_select_AB_prefers_the_smaller_mean_time():
    L = np.array([[0.0, 3.0, 3, 3, 3], [2.5, 3.0, 3, 3, 3]])
    pos, neg = np.array([True, True]), np.array([False, False])
    best = S.select_AB(L, pos, neg, 1, 0.0, np.array([2.0, 3.0]), np.array([-5.0]), 0.001)
    assert best["A"] == 2.0 and best["mean_t"] == 75.0  # A = 2 alarms the second event at 50 ms (mean 75); A = 3 alarms both at 100 ms


def test_boot_stats_margin_is_200_ms_and_lower_limit_is_the_2_5_percentile():
    n = 400
    t_f, t_s = np.full(n, 350.0), np.full(n, 200.0)  # a constant difference of 150 ms: not above 200
    ones = np.ones(n, bool)
    st = S.boot_stats(t_f, t_s, ones, ones, ones, ones, n_boot=100)
    assert st["a_p"] == pytest.approx(1.0)
    rng = np.random.default_rng(5)
    t_s2 = 350.0 - np.where(rng.random(n) < 0.5, 100.0, 500.0)  # differences 100 or 500: mean about 300 with spread
    st2 = S.boot_stats(t_f, t_s2, ones, ones, ones, ones, n_boot=300)
    assert st2["a_lo"] < st2["a_pt"] < st2["a_hi"]
    assert st2["a_lo"] < 0.98 * st2["a_pt"] and st2["a_lo"] == pytest.approx(round(st2["a_lo"], 6))


def test_boot_stats_is_reproducible_with_seed_42():
    n = 120
    rng = np.random.default_rng(11)
    t_f, t_s = rng.uniform(100, 900, n), rng.uniform(50, 700, n)
    ones = np.ones(n, bool)
    a = S.boot_stats(t_f, t_s, ones, ones, ones, rng.random(n) > 0.2, n_boot=200)
    b = S.boot_stats(t_f, t_s, ones, ones, ones, rng.random(n) > 0.2, n_boot=200)
    c = S.boot_stats(t_f, t_s, ones, ones, ones, np.ones(n, bool), n_boot=200)
    assert a["a_lo"] == b["a_lo"] == c["a_lo"]  # the time difference does not depend on the full-window flags and the seed is fixed
    assert a["a_lo"] == pytest.approx(35.18399897, abs=1e-6)  # regression value of the fixed seed 42


def test_stop_time_is_the_checkpoint_of_the_stop():
    L = np.array([[0.0, 0.0, -3.0, 0, 0]])
    al, t = S.seq_decisions(L, 5.0, -1.0)
    assert not al[0] and t[0] == 200
