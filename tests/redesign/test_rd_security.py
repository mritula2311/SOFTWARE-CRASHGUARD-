"""CV 1 and 2 for the existing ACK check that D1 and D2 rely on (node side): a signed ACK counts only for the alert that waits for it."""
from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from crashguard import packet as P
from crashguard import verifier as V

KEY = b"redesign-test-key-32-bytes------"


def test_node_accepts_only_matching_ack():
    ack = P.encode_ack(P.Ack(7, 100, 5, 1), KEY)
    assert V.node_accepts_ack(ack, KEY, 7, 100, 5)
    assert not V.node_accepts_ack(ack, KEY, 7, 100, 6)  # other counter
    assert not V.node_accepts_ack(ack, KEY, 7, 101, 5)  # other event
    assert not V.node_accepts_ack(ack, KEY, 8, 100, 5)  # other vehicle
    assert not V.node_accepts_ack(ack, b"x" * 32, 7, 100, 5)  # wrong key


@settings(max_examples=100, deadline=None)
@given(pos=st.integers(0, P.ACK_LEN - 1), bit=st.integers(0, 7))
def test_tampered_ack_never_accepted(pos, bit):
    ack = bytearray(P.encode_ack(P.Ack(7, 100, 5, 1), KEY))
    ack[pos] ^= 1 << bit
    assert not V.node_accepts_ack(bytes(ack), KEY, 7, 100, 5)
