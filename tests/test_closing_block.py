import numpy as np

from crashguard import attacks_extra as AX
from crashguard import protocol_model_ext as X
from crashguard import ua_core as U


def test_auc_closes_the_curve_with_both_endpoints():
    assert abs(U.auc(np.array([]), np.array([])) - 0.5) < 1e-12  # the line from (0, 1) to (1, 0)
    assert abs(U.auc(np.array([0.5]), np.array([0.0])) - 0.25) < 1e-12  # reaches zero mis-triage at half the escalation
    assert abs(U.auc(np.array([0.9, 0.1]), np.array([0.1, 0.9])) - U.auc(np.array([0.1, 0.9]), np.array([0.9, 0.1]))) < 1e-12  # order of input does not matter


def test_mis_triage_and_escalation_definitions():
    truth = np.array([0, 1, 2, 3, 3, 0])
    assigned = np.array([[0, 2, 1, 3, 1, 0]])
    mis, esc = U.mis_esc(assigned, truth)
    assert np.isnan(mis[0, [0, 1, 5]]).all() and mis[0, 2] == 1 and mis[0, 3] == 0 and mis[0, 4] == 1  # only true Severe or Critical rows count
    assert np.isnan(esc[0, [2, 3, 4]]).all() and esc[0, 1] == 1 and esc[0, 0] == 0  # only true Low or Moderate rows count


def test_classes_use_both_delta_v_and_asi_limits():
    c = U.classes(np.array([10.0, 30.0, 50.0, 60.0]), np.array([0.5, 0.5, 0.5, 0.5]))
    assert list(c) == [0, 1, 2, 3]


def test_designed_attack_cases_all_behave_as_expected_and_are_labelled():
    rows = AX.run_cases()
    assert 8 <= len(rows) <= 10 + 1  # at most ten designed cases plus the split case X04a and X04b
    bad = [r["id"] for r in rows if not r["match"]]
    assert not bad, bad


def test_cancel_overtaking_its_alert_is_lost_in_the_design_and_kept_when_remembered():
    b = X.Bounds(cmax=2, max_events=1, max_tries=2, max_flash=1, max_att=0, max_loss=1, max_inflight=2, max_reboot_base=0, max_reboot_car=0)
    design = X.explore(X.Variant("design", attacker=False), b)
    fixed = X.explore(X.Variant("fixed", attacker=False, keep_pending_cancel=True), b)
    assert not design["props"]["C3_cancel_lost_by_reordering"].get("holds", False)
    assert fixed["props"]["C3_cancel_lost_by_reordering"].get("holds", False)
    assert fixed["props"]["C1_cancel_without_valid_signature"].get("holds", False)
