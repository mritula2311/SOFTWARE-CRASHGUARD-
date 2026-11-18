"""Preemption model (src/crashguard/vf2_preempt.py): the enumeration, its properties and mutations that must break them."""
from crashguard import vf2_preempt as V


def test_stage_sequences_stop_at_the_acknowledgement_and_otherwise_use_all_tries():
    s = V.stages(3)
    assert all("delivered_acked" not in x[:-1] for x in s)
    assert all(len(x) == 3 or x[-1] == "delivered_acked" for x in s)
    assert len(s) == len(set(s))
    assert len(V.stages(1)) == 3 and len(V.stages(2)) == 1 + 6


def test_preemption_adds_no_terminal_state_and_a_delivered_final_frame_leaves_pre():
    for decision in ("confirm", "cancel"):
        for k in range(1, 5):
            fifo, pre = V.run(k, decision, False, False), V.run(k, decision, True, False)
            assert {(b, d) for b, d, _o, _a in pre} <= {(b, d) for b, d, _o, _a in fifo}
            for b, _d, _o, delivered in fifo | pre:
                assert not (b == "PRE" and delivered)
            assert "PRE" in {b for b, *_r in pre}  # stuck in PRE is reachable without a timeout (all final-stage frames lost)
            assert "PRE" not in {b for b, *_r in V.run(k, decision, True, True)}  # and not with a base timeout
            assert "PRE" not in {b for b, *_r in V.run(k, decision, False, True)}


def test_stuck_pre_needs_every_final_stage_frame_lost():
    # restrict the cancel to one delivered frame: no terminal PRE remains
    pre = V.run(2, "cancel", True, False)
    stuck = [x for x in pre if x[0] == "PRE"]
    assert stuck and all(not got for _b, _d, _o, got in stuck)


def test_a_cancel_for_an_event_the_base_does_not_hold_is_rejected():
    res = V.run(1, "cancel", True, False)
    assert ("NONE", False, True, True) in res  # flash lost, cancel delivered: the base stays at NONE


def test_analytic_saving_is_zero_at_sf7_to_sf9_and_positive_from_sf10():
    rows = {(r["sf"], r["who"]): r for r in V.analytic_saving()}
    for sf in (7, 8, 9):
        assert rows[(sf, "median")]["n_late"] == 0 and rows[(sf, "mean")]["n_late"] == 0
    assert rows[(10, "median")]["n_late"] >= 1 and rows[(12, "median")]["saved_s"] > rows[(10, "median")]["saved_s"]
