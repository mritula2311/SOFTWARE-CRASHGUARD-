"""Round 7d: R-REACK reference configuration."""
from crashguard import packet as P
from crashguard import r7d_base as B
from crashguard import verifier as V

KEY = bytes(range(32))


def _frame():
    return P.encode_alert(P.Alert(node_id=7, event_id=1, counter=5, timestamp_ms=1000), KEY)


def test_default_verifier_has_both_limits_off_and_reacks_every_replay():
    v = V.BaseVerifier(KEY)
    assert v.reack_interval_s is None and v.budget is None
    raw = _frame()
    v.handle(raw, 0.0)
    assert all(v.handle(raw, 0.01 * i)[0] == V.REACK for i in range(1, 50))


def test_reference_base_limits_replays_and_keeps_new_acks():
    v = B.reference_base(KEY, sf=7)
    assert v.reack_interval_s == B.reack_interval_s(7) and v.budget is not None
    raw = _frame()
    assert v.handle(raw, 0.0)[0] == V.ACCEPT
    inside = [v.handle(raw, 0.01 * i)[0] for i in range(1, 30)]  # 0.29 s < 0.43 s
    assert set(inside) == {V.REACK_LIMITED}
    assert v.handle(raw, B.reack_interval_s(7) * 1.01)[0] == V.REACK  # a genuine retry one interval later


def test_interval_grows_with_spreading_factor_and_flood_matches_stored_keys():
    assert B.reack_interval_s(7) < B.reack_interval_s(8) < B.reack_interval_s(9)
    from crashguard import attacks as A

    off = B.flood(lambda: V.BaseVerifier(A.KEY, reack_interval_s=None, budget=V.DutyBudget(initial_s=A.BASE_BUDGET_INITIAL_S), sf=A.FLOOD_SF))
    on = B.flood(lambda: B.reference_base(A.KEY, A.FLOOD_SF, initial_budget_s=A.BASE_BUDGET_INITIAL_S))
    assert off["reacks"] == 679 and on["reacks"] == 266 and off["legit"] == V.ACCEPT_NO_ACK and on["legit"] == V.ACCEPT
