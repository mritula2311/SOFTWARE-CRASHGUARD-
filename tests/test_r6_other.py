"""Small tests of the round-6 quarantine exploration and the airtime helper of the bounds."""
import pytest

from crashguard import r6_bounds as B
from crashguard import r6_quarantine as Q
from crashguard.lora import airtime_ms


def test_rule_a_is_attackable_by_two_unverified_frames_in_the_first_slot():
    a = Q.explore("A")
    assert a["victim_quarantined_reachable"] and a["attack"]["slot"] == 0 and len(a["attack"]["frames"]) == 2
    assert a["max_victim_strikes"] >= 2


def test_rule_b_changes_no_state_because_frames_that_fail_verification_do_not_reach_the_counters():
    b = Q.explore("B")
    assert not b["victim_quarantined_reachable"] and b["max_victim_strikes"] == 0 and b["states_visited"] == Q.SLOTS + 1


def test_frame_patterns_per_slot_cover_all_sequences_up_to_the_bound():
    n = len(Q.KINDS)
    assert len(Q.frames_in_slot()) == sum(n**i for i in range(Q.MAX_PER_SLOT + 1))


@pytest.mark.parametrize("sf", [7, 9, 12])
def test_bounds_airtime_matches_the_time_on_air_function(sf):
    assert B.A(14, sf) == pytest.approx(airtime_ms(14, sf) / 1000.0)
    assert B.A(7, sf) < B.A(14, sf) <= B.A(97, sf)
