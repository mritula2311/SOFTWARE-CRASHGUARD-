import numpy as np
import pandas as pd

from crashguard import protocol_model as M
from crashguard.s11_sct import agg_diff
from crashguard.ua_conformal import intervals, merged_groups, split_quantile


def test_split_quantile_order_statistic():
    s = np.array([0, 0, 1, 0, 2, 0, 0, 1, 0, 0], float)  # n = 10
    assert split_quantile(s, 0.1) == 2.0  # ceil(11 * 0.9) = 10th smallest
    assert split_quantile(s[:5], 0.05) == float("inf")  # index 6 > n


def test_upper_end_never_below_the_point_class_and_is_capped_at_critical():
    c_hat_cal = np.array([0] * 20 + [3] * 20)
    c_true_cal = np.array([0] * 10 + [2] * 10 + [3] * 20)  # under-estimates for predicted class 0
    r = intervals(c_hat_cal, c_true_cal, np.array([0, 1, 3]), 0.1, cond=False)
    assert (r["up"] >= np.array([0, 1, 3])).all() and r["up"].max() <= 3
    rc = intervals(c_hat_cal, c_true_cal, np.array([0, 3]), 0.1, cond=True)
    assert rc["up"][0] >= 2 and rc["up"][1] == 3  # class 0 needs an upward step; class 3 cannot go higher


def test_class_conditional_falls_back_to_pooled_for_rare_predicted_classes():
    c_hat_cal = np.array([0] * 30 + [1] * 3)
    c_true_cal = np.array([0] * 30 + [3] * 3)
    r = intervals(c_hat_cal, c_true_cal, np.array([1, 1]), 0.1, cond=True)
    assert r["fallback"] == 2


def test_identical_recordings_are_merged_into_one_group():
    tests = [dict(sig=dict(acc=np.arange(6.0).reshape(2, 3))), dict(sig=dict(acc=np.arange(6.0).reshape(2, 3))), dict(sig=dict(acc=np.ones((2, 3))))]
    meta = pd.DataFrame(dict(group_mm=["A|x", "B|y", "C|z"]))
    g, n_dup = merged_groups(tests, meta)
    assert n_dup == 1 and g[0] == g[1] and g[2] != g[0]


def test_agg_diff_pairs_by_seed_and_cell():
    rows = []
    for cell in ("a", "b"):
        for h in range(10):
            rows += [dict(scen=cell, hour=h, pol="P1", m=0.2), dict(scen=cell, hour=h, pol="P3", m=0.5)]
    R = pd.DataFrame(rows)
    p, lo, hi, n = agg_diff(R, "m", "P1", "P3", [("a",), ("b",)], ["scen"])
    assert n == 2 and abs(p - 0.3) < 1e-12 and lo <= p <= hi


B = M.Bounds(cmax=3, max_events=1, max_tries=2, max_flash=1, max_att=2, max_loss=1, max_inflight=2, max_reboot_base=1, max_reboot_car=0)


def test_base_rule_decisions():
    v, b = M.Variant("x"), M.Bounds()
    base = (0, 0, (), ())
    d, base, ack = M.base_rule(base, ("A", 1, 1, True), v, b)
    assert d == M.ACCEPT and ack == ("K", "A", 1)
    assert M.base_rule(base, ("A", 1, 1, True), v, b)[0] == M.REACK
    assert M.base_rule(base, ("A", 1, 1, False), v, b)[0] == M.REJECT_TAG
    assert M.base_rule(base, ("X", 1, 1, True), v, b)[0] == M.CANCELLED and M.base_rule(base, ("X", 3, 1, True), v, b)[0] == M.REJECT_UNKNOWN
    assert M.base_rule(base, ("A", 1, 1, True), M.Variant("s", idempotent=False), b)[0] == M.REJECT_COUNTER


def test_search_finds_replay_after_base_reboot_without_persistence_and_none_with_it():
    bad = M.explore(M.Variant("np", base_persist=False, cancel=False), B)
    good = M.explore(M.Variant("ok", cancel=False), B)
    assert not bad["props"]["S1_replay_or_forgery_accepted_as_new"]["holds"] and not bad["props"]["S4_accepted_counters_not_increasing"]["holds"]
    assert good["props"]["S1_replay_or_forgery_accepted_as_new"]["holds"] and good["props"]["S4_accepted_counters_not_increasing"]["holds"]
    assert len(bad["props"]["S1_replay_or_forgery_accepted_as_new"]["trace"]) >= 4


def test_strict_anti_replay_fails_liveness_and_the_idempotent_design_holds():
    b = M.Bounds(cmax=3, max_events=1, max_tries=3, max_flash=1, max_att=0, max_loss=1, max_inflight=3, max_reboot_base=0, max_reboot_car=0)
    strict = M.explore(M.Variant("s", idempotent=False, liveness_env=True, cancel=False), b)
    design = M.explore(M.Variant("d", liveness_env=True, cancel=False), b)
    assert not strict["props"]["L1_no_ack_in_terminal_state"]["holds"] and design["props"]["L1_no_ack_in_terminal_state"]["holds"]
