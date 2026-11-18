"""CV 1 and 2 (docs/03_results/CODE_VERIFICATION.md): unit tests with hand-computed cases and property tests of the redesign policy logic (src/crashguard/rd_policy.py)."""
from __future__ import annotations

import math
import struct

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from crashguard import rd_policy as RP
from crashguard.lora import airtime_ms

# ---------------------------------------------------------------- CV1: unit tests with hand-computed values
# Time on air by the Semtech formula, worked by hand: Tsym = 2^SF / 125000; payload symbols = 8 + ceil((8 PL - 4 SF + 44) / (4 (SF - 2 DE))) * 5;
# time = (12.25 + payload symbols) * Tsym; DE = 1 when Tsym > 16 ms.
HAND = {
    (24, 7): 61.696,  # Tsym 1.024 ms; ceil(208/28) = 8 -> 8 + 40 = 48 symbols; 60.25 * 1.024
    (40, 9): 287.744,  # Tsym 4.096 ms; ceil(328/36) = 10 -> 58 symbols; 70.25 * 4.096
    (97, 10): 985.088,  # Tsym 8.192 ms; ceil(780/40) = 20 -> 108 symbols; 120.25 * 8.192
    (24, 11): 823.296,  # Tsym 16.384 ms, DE = 1; ceil(192/36) = 6 -> 38 symbols; 50.25 * 16.384
    (97, 12): 3940.352,  # Tsym 32.768 ms, DE = 1; ceil(772/40) = 20 -> 108 symbols; 120.25 * 32.768
}


@pytest.mark.parametrize("key,ms", list(HAND.items()))
def test_airtime_hand(key, ms):
    assert airtime_ms(key[0], key[1]) == pytest.approx(ms, abs=1e-6)


@pytest.mark.parametrize("pl", [24, 40, 97])
def test_airtime_monotone_in_sf_and_length(pl):
    t = [airtime_ms(pl, sf) for sf in range(7, 13)]
    assert t == sorted(t) and airtime_ms(pl + 8, 9) > airtime_ms(pl, 9)


def test_beta_update_hand():
    b = RP.BetaLoss(n0=6.0, l0=0.3, forget=0.97)
    assert b.mean == pytest.approx(0.3)
    b.update(True)  # failure: a = 1.8 + 1, b = 4.2
    assert (b.a, b.b) == (pytest.approx(2.8), pytest.approx(4.2)) and b.mean == pytest.approx(0.4)
    b.update(False)  # forget towards the prior by 0.97, then a success: a = 1.8 + 0.97 = 2.77, b = 4.2 + 1
    assert (b.a, b.b) == (pytest.approx(2.77), pytest.approx(5.2)) and b.mean == pytest.approx(2.77 / 7.97)


def test_beta_no_forget_counts():
    b = RP.BetaLoss(n0=2.0, l0=0.5, forget=1.0)
    for f in (True, True, False):
        b.update(f)
    assert (b.a, b.b) == (3.0, 2.0)


def test_deadline_arithmetic():
    assert RP.time_left(10.0, 100.0, 103.0) == 7.0
    assert RP.retry_allowed(10.0, 100.0, 109.0, 0.5)
    assert not RP.retry_allowed(10.0, 100.0, 109.6, 0.5)
    assert RP.retry_allowed(10.0, 100.0, 109.5, 0.5)  # ends exactly at the deadline


def test_bins():
    assert [RP.loss_bin(x) for x in (0.0, 0.05, 0.10, 0.39, 0.40, 0.84, 0.85, 1.0)] == [0, 0, 1, 3, 4, 6, 7, 7]
    assert [RP.load_bin(n) for n in (0, 1, 3, 4, 9, 10, 50)] == [0, 1, 1, 2, 2, 3, 3]
    assert [RP.budget_units(b, 0.3) for b in (0.0, 0.29, 0.3, 0.95, 100.0)] == [0, 0, 1, 3, RP.NB_MAX]


def test_cluster_ack_length_formula():
    assert struct.calcsize(RP._HDR) == 11
    assert RP.cluster_ack_len(0) == 11 + 64 and RP.cluster_ack_len(10) == 11 + 20 + 64


# ---------------------------------------------------------------- D1 table
_TABS: dict = {}


def tab_for(sf: int):
    if sf not in _TABS:
        _TABS[sf] = RP.D1Table(sf)
    return _TABS[sf]


def test_table_none_without_time_or_budget():
    tab8 = tab_for(8)
    assert tab8.lookup(3, 0, 0.0, 0.3, 0, 5.0) is None
    assert tab8.lookup(3, 0, 5.0, 0.3, 0, 0.0) is None  # no budget unit
    assert tab8.lookup(3, 0, 0.1, 0.3, 0, 5.0) is None  # an SF8 frame (0.297 s) does not fit in 0.1 s


def test_table_action_fits():
    r = tab_for(8).lookup(3, 0, 6.0, 0.5, 0, 3.0)
    assert r is not None
    gap, sf = r
    assert gap in RP.GAPS and 8 <= sf <= 10 and gap + airtime_ms(97, sf) / 1000 <= 6.0


def test_table_size_reported():
    assert tab_for(8).size_bytes() == sum(a.size for a in tab_for(8).A.values()) > 100_000


# ---------------------------------------------------------------- CV2: property tests
def chain(tab, c, tau, l_hat, n_heard, budget):
    """Follow the table assuming every attempt fails; return (start offset, airtime, sf) of each attempt."""
    t, spent, j, out = 0.0, 0.0, 0, []
    while j < 60:
        r = tab.lookup(c, j, tau - t, l_hat, n_heard, budget - spent)
        if r is None:
            break
        gap, sf = r
        a = airtime_ms(97, sf) / 1000
        out.append((t + gap, a, sf))
        t += gap + RP.round_s(sf)
        spent += a
        j += 1
    return out


@settings(max_examples=150, deadline=None)
@given(c=st.sampled_from([2, 3]), tau=st.floats(0.0, 30.0), l_hat=st.floats(0.0, 1.0), n_heard=st.integers(0, 40), budget=st.floats(0.0, 8.0), sf0=st.sampled_from([7, 8, 9, 10]))
def test_property_budget_and_deadline(c, tau, l_hat, n_heard, budget, sf0):
    tab = tab_for(sf0)
    tau = min(tau, RP.DEADLINE_S[c])
    seq = chain(tab, c, tau, l_hat, n_heard, budget)
    for start, a, _sf in seq:  # a retry is never scheduled after the class deadline
        assert start + a <= tau + 1e-9
    assert sum(a for _s, a, _f in seq) <= budget + 1e-9  # airtime planned never exceeds the budget


def test_property_table_monotone():
    """Less time left or a higher loss never lowers urgency (urgency = a shorter retry gap), where both entries have an action."""
    tab = tab_for(8)
    viol = 0
    for c in (2, 3):
        A = tab.A[c]
        gap = np.where(A >= 0, np.array([g for g, _k in tab.acts])[np.clip(A, 0, None)], np.nan)
        d_t = gap[:, 1:, :, :, :] - gap[:, :-1, :, :, :]  # entry with more time minus entry with less time: must not be negative
        viol += int(np.nansum(d_t < -1e-9))
        d_l = gap[:, :, 1:, :, :] - gap[:, :, :-1, :, :]  # entry with higher loss minus lower loss: must not be positive
        viol += int(np.nansum(d_l > 1e-9))
    assert viol == 0, f"{viol} monotonicity violations"


# ---------------------------------------------------------------- D2: cluster ACK security and decisions
_sk = RP.new_gateway_key()
_GW = (_sk, _sk.public_key())


def test_cluster_listed_stops_unlisted_defers():
    sk, pk = _GW
    f = RP.encode_cluster_ack(sk, event_id=77, fresh_s=1000, ids=[3, 5, 9])
    assert len(f) == RP.cluster_ack_len(3)
    assert RP.ClusterAckVerifier(pk).check(f, 5, 77, 1002).action == "stop"
    assert RP.ClusterAckVerifier(pk).check(f, 4, 77, 1002).action == "defer"


def test_cluster_rejections():
    sk, pk = _GW
    f = RP.encode_cluster_ack(sk, 77, 1000, [5])
    v = RP.ClusterAckVerifier(pk)
    assert v.check(f, 5, 78, 1000).reason == "other_event"
    assert v.check(f, 5, 77, 1011).reason == "stale"
    assert v.check(f, 5, 77, 989).reason == "stale"
    assert v.check(f, 5, 77, 1000).action == "stop"
    assert v.check(f, 5, 77, 1001).reason == "replay"  # a processed frame is not accepted again
    assert v.check(f[:10], 5, 77, 1000).reason == "short"


def test_vehicle_key_holder_cannot_forge():
    """A node holding only a vehicle key (any key other than the gateway private key) cannot produce a frame that a vehicle accepts."""
    other = RP.new_gateway_key()
    forged = RP.encode_cluster_ack(other, 77, 1000, [5])
    assert RP.ClusterAckVerifier(_GW[1]).check(forged, 5, 77, 1000).reason == "bad_signature"


@settings(max_examples=150, deadline=None)
@given(pos=st.integers(0, 10_000), bit=st.integers(0, 7))
def test_property_tampered_frame_never_accepted(pos, bit):
    f = bytearray(RP.encode_cluster_ack(_GW[0], 77, 1000, [1, 2, 5, 9]))
    f[pos % len(f)] ^= 1 << bit
    assert RP.ClusterAckVerifier(_GW[1]).check(bytes(f), 5, 77, 1000).action == "ignore"


@settings(max_examples=100, deadline=None)
@given(ids=st.lists(st.integers(0, 65535), max_size=40), my=st.integers(0, 65535), dt=st.integers(-30, 30), ev=st.integers(0, 2**32 - 1), ev2=st.integers(0, 2**32 - 1))
def test_property_accept_only_fresh_same_event_unprocessed(ids, my, dt, ev, ev2):
    f = RP.encode_cluster_ack(_GW[0], ev, 5000, ids)
    v = RP.ClusterAckVerifier(_GW[1])
    r = v.check(f, my, ev2, 5000 + dt)
    if ev != ev2 or abs(dt) > RP.CLUSTER_FRESH_S:
        assert r.action == "ignore"
    else:
        assert r.action == ("stop" if my in set(ids) else "defer")
        assert v.check(f, my, ev2, 5000 + dt).action == "ignore"  # replay of the same frame


@settings(max_examples=200, deadline=None)
@given(verdicts=st.lists(st.sampled_from(["stop", "defer", "ignore"]), max_size=30))
def test_property_vehicle_stops_only_on_verified_listing(verdicts):
    ns = RP.NodeState(5, 77, 3, 0.0)
    for a in verdicts:
        ns.on_verdict(RP.ClusterVerdict(a, "x"))
    assert ns.pending == ("stop" not in verdicts)
    assert ns.verified_ack == ("stop" in verdicts)


@settings(max_examples=200, deadline=None)
@given(cls=st.sampled_from([2, 3]), now=st.floats(0, 1e5), ready=st.floats(0, 1e5), u=st.floats(0, 1), scale=st.floats(0.1, 4.0))
def test_property_defer_is_bounded_never_a_stop(cls, now, ready, u, scale):
    r = RP.defer_until(cls, now, 0.0, ready, u, scale)
    assert math.isfinite(r) and r >= ready and r <= max(ready, now + RP.DEFER_S[cls] * scale) + 1e-9


# ---------------------------------------------------------------- tests added after the first mutation run (survivors M11, M14, M24)
def test_table_depends_on_failed_attempts_and_lookup_uses_it():
    tab = tab_for(8)
    A = tab.A[3]
    diff = np.argwhere(A[0] != A[5])
    assert len(diff) > 0  # the table is not the same for 0 and 5 failures
    _c, t, li, q, nb = (0, *diff[0][:4]) if len(diff[0]) == 4 else tuple(diff[0])
    tau = t * RP.TAU_STEP[3] + 1e-6
    l_hat, n_heard, budget = RP.L_CENTRES[li], [0, 1, 4, 10][q], nb * tab.unit_s + 1e-6
    r0 = tab.lookup(3, 0, tau, l_hat, n_heard, budget)
    r5 = tab.lookup(3, 5, tau, l_hat, n_heard, budget)
    assert r0 != r5


def test_table_depends_on_load():
    tab = tab_for(8)
    assert any((tab.A[c][:, :, :, 3, :] != tab.A[c][:, :, :, 0, :]).any() for c in (2, 3))  # a crowd changes the retry choice somewhere


def test_cluster_ack_with_inconsistent_count_is_rejected():
    body = struct.pack(RP._HDR, RP.MSG_CLUSTER_ACK, 1, 77, 1000, 5) + struct.pack("<HH", 1, 5)  # says 5 ids, carries 2, validly signed
    frame = body + _GW[0].sign(body)
    assert RP.ClusterAckVerifier(_GW[1]).check(frame, 5, 77, 1000).reason == "malformed"
