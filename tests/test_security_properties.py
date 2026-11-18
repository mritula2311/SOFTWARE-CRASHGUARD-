"""Property-based tests (hypothesis) and fuzzing of the verifier and the packet parser (software only, no radio)."""
import hypothesis.strategies as st
import pytest
from hypothesis import HealthCheck, given, settings

from crashguard import forgery
from crashguard import packet as P
from crashguard import verifier as V
from crashguard.attacks import KEY

SETTINGS = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
DECISIONS = {V.ACCEPT, V.ACCEPT_NO_ACK, V.REACK, V.REACK_LIMITED, V.REACK_NO_BUDGET, V.REJECT_LENGTH, V.REJECT_VERSION, V.REJECT_TYPE, V.REJECT_TAG, V.REJECT_COUNTER}
u32 = st.integers(min_value=0, max_value=2**32 - 1)
alerts = st.builds(P.Alert, node_id=st.integers(1, 4), event_id=u32, counter=u32, timestamp_ms=u32, severity=st.integers(0, 3), impact_side=st.integers(0, 4),
                   angle_deg_x10=st.integers(0, 3600), lat_e7=st.integers(-2**31, 2**31 - 1), lon_e7=st.integers(-2**31, 2**31 - 1), peak_g_x100=st.integers(0, 65535),
                   ml_prob_x10000=st.integers(0, 10000), rule_sev=st.integers(0, 3), sw_mask=st.integers(0, 31), sw_first=st.integers(0, 5), rollover=st.integers(0, 1),
                   delta_v_kmh_x100=st.integers(0, 65535), asi_x100=st.integers(0, 65535))


@SETTINGS
@given(st.lists(st.one_of(alerts.map(lambda a: P.encode_alert(a, KEY)), st.binary(max_size=120), alerts.map(lambda a: P.encode_alert(a, bytes(32)))), max_size=40))
def test_counter_never_goes_backwards_whatever_arrives(packets):
    v = V.BaseVerifier(KEY)
    seen: dict[int, int] = {}
    base = 0
    for raw in packets:
        dec, _ack = v.handle(raw)
        assert dec in DECISIONS
        for node, c in v.last.items():
            assert c >= seen.get(node, -1)
            seen[node] = c
        assert v.base_counter >= base
        base = v.base_counter


@SETTINGS
@given(alerts, st.integers(1, 5))
def test_re_ack_is_idempotent(a, repeats):
    v = V.BaseVerifier(KEY)
    raw = P.encode_alert(a, KEY)
    dec, ack = v.handle(raw)
    assert dec == V.ACCEPT and V.node_accepts_ack(ack, KEY, a.node_id, a.event_id, a.counter)
    state = (dict(v.last), v.base_counter)
    for _ in range(repeats):
        d2, ack2 = v.handle(raw)
        assert d2 == V.REACK and ack2 == ack
        assert (dict(v.last), v.base_counter) == state  # the alert is not processed again


@SETTINGS
@given(alerts, st.integers(0, P.ALERT_LEN - 1), st.integers(0, 7))
def test_any_single_bit_flip_in_the_alert_is_rejected(a, pos, bit):
    raw = P.encode_alert(a, KEY)
    t = bytearray(raw)
    t[pos] ^= 1 << bit
    dec, ack = V.BaseVerifier(KEY).handle(bytes(t))
    assert dec.startswith("reject") and ack is None  # bytes 0..88 are covered by the tag; 89..96 are the tag


@SETTINGS
@given(alerts, st.integers(0, 300))
def test_truncation_and_padding_are_rejected(a, n):
    raw = P.encode_alert(a, KEY)
    mutated = (raw + bytes(300))[:n]
    if n != P.ALERT_LEN:
        assert V.BaseVerifier(KEY).handle(mutated)[0] == V.REJECT_LENGTH
    else:
        assert V.BaseVerifier(KEY).handle(mutated)[0] == V.ACCEPT


@SETTINGS
@given(st.integers(1, 2**32 - 1), u32, u32, u32)
def test_any_single_bit_flip_in_an_ack_is_rejected_by_the_node(node, event, counter, base_counter):
    ack = P.encode_ack(P.Ack(node, event, counter, base_counter), KEY)
    assert V.node_accepts_ack(ack, KEY, node, event, counter)
    for pos in range(len(ack)):
        for bit in range(8):
            t = bytearray(ack)
            t[pos] ^= 1 << bit
            assert not V.node_accepts_ack(bytes(t), KEY, node, event, counter)


@SETTINGS
@given(st.binary(max_size=200))
def test_fuzz_parser_never_crashes_and_every_outcome_is_accept_or_reject(raw):
    v = V.BaseVerifier(KEY)
    dec, ack = v.handle(raw)
    assert dec in DECISIONS
    assert (ack is None) == (not dec.startswith("accept") or dec == V.ACCEPT_NO_ACK) or dec == V.REACK  # an ACK exists only with an accept or a re-ACK
    assert isinstance(V.node_accepts_ack(raw, KEY, 1, 1, 1), bool)
    try:
        P.decode_alert(raw)
    except ValueError:
        assert len(raw) != P.ALERT_LEN
    try:
        P.decode_ack(raw)
    except ValueError:
        assert len(raw) != P.ACK_LEN


@SETTINGS
@given(alerts, st.lists(st.tuples(st.integers(0, P.ALERT_LEN - 1), st.integers(0, 255)), min_size=1, max_size=6))
def test_fuzz_mutations_of_a_valid_alert_are_never_accepted_unless_unchanged(a, edits):
    raw = P.encode_alert(a, KEY)
    t = bytearray(raw)
    for pos, val in edits:
        t[pos] = val
    dec, _ = V.BaseVerifier(KEY).handle(bytes(t))
    assert (bytes(t) == raw) == (dec == V.ACCEPT)


def test_forgery_numbers_follow_from_the_formula():
    assert forgery.TAG_BITS == 64
    rows = {(r["sf"], r["attacker"]): r for r in forgery.rows()}
    r7, r12 = rows[(7, "airtime_limit")], rows[(12, "airtime_limit")]
    assert r7["packets_per_s"] == pytest.approx(1000.0 / r7["airtime_ms"])
    assert r12["expected_years"] > r7["expected_years"] > 1e9  # billions of years even at the airtime limit
    assert rows[(7, "duty_limited")]["expected_years"] == pytest.approx(rows[(7, "airtime_limit")]["expected_years"] * 10.0)
    wrap = {(r["sf"], r["basis"]): r for r in forgery.counter_rows()}
    assert wrap[(7, "duty_limit_alerts_per_hour")]["wrap_years"] > 100.0  # 2^32 alerts at the fastest legal rate
