"""Tests of the round-4 A1 module (docs/02_preregistration/PREREGISTRATION_V15.md section 6): frame, ACK check, repetition rule, engine properties, equivalence with the frozen round-3 trace code."""
from __future__ import annotations

import math
import random

import numpy as np
import pytest

from crashguard import a4_a1 as A
from crashguard import packet as P
from crashguard import r3_t1 as T1
from crashguard.ar_r4 import kdf

MASTER = b"M" * 32


# ---------------------------------------------------------------- frame
def test_frame_is_24_bytes_and_roundtrips():
    key = kdf(MASTER, 7)
    raw = A.encode_prov(key, 7, 12.97, 80.04, 1_000_000, 3)
    assert len(raw) == 24 == A.PROV_LEN
    d = A.decode_prov(raw)
    assert d["node_id"] == 7 and d["epoch"] == 1_000_000 and d["seq"] == 3 and d["msg_type"] == A.MSG_PROV
    assert d["lat"] == round(12.97 * 64) and d["lon"] == round(80.04 * 64)
    assert A.verify_prov(raw, key)


def test_every_covered_byte_is_authenticated():
    key = kdf(MASTER, 7)
    raw = bytearray(A.encode_prov(key, 7, 12.97, 80.04, 55, 1))
    for i in range(24):
        bad = bytearray(raw)
        bad[i] ^= 0x01
        assert not A.verify_prov(bytes(bad), key), i


def test_wrong_vehicle_key_and_length_rejected():
    raw = A.encode_prov(kdf(MASTER, 7), 7, 1.0, 2.0, 5, 0)
    assert not A.verify_prov(raw, kdf(MASTER, 8))
    assert not A.verify_prov(raw[:-1], kdf(MASTER, 7))
    with pytest.raises(ValueError):
        A.decode_prov(raw + b"\x00")


def test_no_type_confusion_with_full_alert():
    key = kdf(MASTER, 7)
    full = P.encode_alert(P.Alert(node_id=7, event_id=1, counter=1, timestamp_ms=1, severity=3, impact_side=0, angle_deg_x10=0, lat_e7=0, lon_e7=0, peak_g_x100=0, ml_prob_x10000=0, rule_sev=0, sw_mask=0, sw_first=0, rollover=0), key)
    assert len(full) == 97 and not A.verify_prov(full, key)
    prov = A.encode_prov(key, 7, 1.0, 2.0, 5, 0)
    # the tag of a provisional frame is not the plain tag of its body (domain separation), so it cannot be replayed as a full alert tag
    assert prov[16:] != P.tag(key, prov[:16])


# ---------------------------------------------------------------- ACK check
def test_ack_stops_only_for_this_vehicle_with_valid_tag_and_known_id():
    s = A.ProvSession(MASTER, 7, 1.0, 2.0, 100, 2)
    good = A.ack_for(MASTER, s.frame)
    other = A.ack_for(MASTER, A.encode_prov(kdf(MASTER, 9), 9, 1.0, 2.0, 100, 2))  # ACK of vehicle 9
    wrong_id = A.ack_for(MASTER, A.encode_prov(kdf(MASTER, 7), 7, 1.0, 2.0, 101, 2))  # names an id the car never sent
    forged_tag = bytearray(good)
    forged_tag[-1] ^= 1
    # vehicle 9's key naming vehicle 7: the tag is wrong for key 7
    cross = P.encode_ack(P.Ack(node_id=7, acked_event_id=100, acked_counter=2, base_counter=1), kdf(MASTER, 9))
    for bad in (other, wrong_id, bytes(forged_tag), cross, good[:-1], b"", b"\x00" * 26):
        assert not s.on_ack(bad) and not s.stopped
    assert s.on_ack(good) and s.stopped


def test_ack_of_wrong_message_type_does_not_stop():
    s = A.ProvSession(MASTER, 7, 1.0, 2.0, 100, 2)
    raw = bytearray(A.ack_for(MASTER, s.frame))
    raw[1] = P.MSG_ALERT
    assert not s.on_ack(bytes(raw))


# ---------------------------------------------------------------- repetition rule
def test_prov_allowed_boundaries():
    a, al = 0.2, 0.5
    assert A.prov_allowed(9.8, a, al, 0.0) == "ok"  # ends exactly at 10.0
    assert A.prov_allowed(9.8001, a, al, 0.0) == "deadline"
    assert A.prov_allowed(1.0, a, al, 36.0 - a - 4 * al) == "ok"
    assert A.prov_allowed(1.0, a, al, 36.0 - a - 4 * al + 1e-6) == "duty"
    assert A.prov_allowed(1.0, a, al, 0.0, reserve_tries=0, limit_s=a) == "ok"


# ---------------------------------------------------------------- engine
def rand_case(rng: np.random.Generator):
    n = 60
    p = float(rng.choice([0.0, 0.2, 0.5, 0.8, 1.0]))
    r = (rng.random(n) >= p).astype(np.uint8)
    ev = (bool(rng.integers(0, 2)), bool(rng.integers(0, 2)), int(rng.integers(0, 2)), float(rng.uniform(0.05, 0.8)))
    return r, ev, float(rng.choice([0.0, 0.3, 0.7]))


def test_engine_invariants_on_random_links():
    rng = np.random.default_rng(1)
    for i in range(400):
        r, ev, pdl = rand_case(rng)
        cfg = A.Cfg(sf=int(rng.choice([7, 9])), gap=float(rng.choice([0.0, 0.1])), reserve=int(rng.choice([0, 4])), after_confirm=bool(rng.integers(0, 2)))
        log: list = []
        o = A.a1_event(r, 0, ev, pdl, random.Random(i), cfg, log=log)
        prov = [x for x in log if x[0] == "prov"]
        assert all(t0 + a <= A.DEADLINE + 1e-9 for _k, t0, a, _g in prov), "provisional frame ends after the deadline"
        assert o["two_air"] <= A.LIMIT_S + 1e-9
        t_prev = -1.0
        for _k, t0, a, _g in log:  # one radio: transmissions do not overlap
            assert t0 >= t_prev - 1e-9
            t_prev = t0 + a
        if o["prov_stop"] == "ack":
            assert any(g for _k, _t, _a, g in prov), "stopped on an ACK although no provisional frame was received"
        assert o["prov_stop"] in (None, "ack", "confirm_acked", "deadline", "duty", "retracted", "cap", "confirm_done")
        if o["prov_arr"] < math.inf:
            assert o["prov_arr"] <= A.DEADLINE + 1e-9


def test_duty_never_exceeded_with_tiny_budget():
    r = np.zeros(80, np.uint8)
    for limit in (0.3, 1.0, 2.5):
        cfg = A.Cfg(limit_s=limit, sf=9)
        log: list = []
        o = A.a1_event(r, 0, (True, True, 1, 0.2), 0.5, random.Random(3), cfg, log=log)
        assert sum(a for _k, _t, a, _g in log) <= limit + 1e-9 and o["two_air"] <= limit + 1e-9


def test_no_stop_without_ack_all_lost():
    r = np.zeros(80, np.uint8)  # nothing is ever received: the repetition must run until the deadline or the duty limit
    o = A.a1_event(r, 0, (True, True, 1, 0.1), 0.0, random.Random(1), A.A1)
    assert o["prov_stop"] in ("deadline", "duty") and o["prov_tx"] > 4 and o["prov_arr"] == math.inf


def test_prov_stops_at_first_ack_all_received():
    r = np.ones(80, np.uint8)
    o = A.a1_event(r, 0, (True, True, 1, 0.1), 0.0, random.Random(1), A.A1)
    assert o["prov_tx"] == 1 and o["prov_stop"] == "ack"


def test_retraction_withdraws_provisional():
    r = np.zeros(80, np.uint8)
    o = A.a1_event(r, 0, (True, False, 1, 0.1), 0.0, random.Random(1), A.A1)
    assert o["prov_stop"] == "retracted" and o["cancel_tx"] == 3


def test_confirm_ack_stops_provisional():
    # frame 0 lost, frame 1 lost ... provisional keeps trying; once the confirm (ready at 1.8 s) is received and acked the repetition ends
    r = np.array([0] * 3 + [1] * 77, np.uint8)
    o = A.a1_event(r, 0, (True, True, 1, 0.1), 0.0, random.Random(1), A.A1)
    assert o["prov_stop"] in ("ack", "confirm_acked")


# ---------------------------------------------------------------- equivalence with the frozen round-3 trace code
@pytest.mark.parametrize("seed", range(5))
def test_round3_compat_mode_equals_r3_event(seed):
    rng = np.random.default_rng(100 + seed)
    for i in range(300):
        n = 60
        p = float(rng.choice([0.0, 0.1, 0.4, 0.8]))
        r = (rng.random(n) >= p).astype(np.uint8)
        ev = (bool(rng.integers(0, 2)), bool(rng.integers(0, 2)), int(rng.integers(0, 2)), float(rng.uniform(0.05, 0.8)))
        pdl = float(rng.choice([0.0, 0.3, 0.6]))
        rng1, rng2 = random.Random(i), random.Random(i)
        o3 = T1.r3_event(r, 0, ev, pdl, rng1)
        if ev[1]:  # r3_event draws the single-stage ACKs first
            T1.arrival_trace(r, 0, T1.FINAL_S + T1.COMPUTE3, T1.A_AL, pdl, rng2)
        o = A.a1_event(r, 0, ev, pdl, rng2, A.R3)
        assert o["two_air"] == pytest.approx(o3["two_air"], abs=1e-12)
        assert o["two_d"] == o3["two_d"]


# ---------------------------------------------------------------- additions after the first mutation run (timing, ACK path, field widths)
class FakeRng:
    """Random source that returns scripted values (an ACK is received when the value is at least p_dl)."""

    def __init__(self, vals):
        self.vals = list(vals)

    def random(self):
        return self.vals.pop(0) if self.vals else 0.0


def test_timing_of_repeats_and_confirm_ready_time():
    r = np.zeros(80, np.uint8)
    log: list = []
    A.a1_event(r, 0, (True, True, 1, 0.2), 0.0, random.Random(1), A.A1, log=log)
    prov = [x for x in log if x[0] == "prov"]
    assert prov[0][1] == pytest.approx(0.2 + A.COMPUTE3)
    a, win = prov[0][2], A.PROC + A._air(P.ACK_LEN, 7) + A.MARGIN
    assert prov[1][1] == pytest.approx(prov[0][1] + a + win)  # zero gap: the next attempt follows the listen window
    conf = [x for x in log if x[0] == "conf"]
    assert conf and conf[0][1] >= A.FINAL_S + A.COMPUTE3 - 1e-9
    assert prov[0][2] == pytest.approx(A._air(24, 7)) and conf[0][2] == pytest.approx(A._air(97, 7))


def test_gap_is_added_between_attempts():
    r = np.zeros(80, np.uint8)
    log: list = []
    A.a1_event(r, 0, (True, False, 0, 0.1), 0.0, random.Random(1), A.Cfg(gap=0.1), log=log)
    prov = [x for x in log if x[0] == "prov"]
    win = A.PROC + A._air(P.ACK_LEN, 7) + A.MARGIN
    assert prov[1][1] == pytest.approx(prov[0][1] + prov[0][2] + win + 0.1)


def test_lost_ack_does_not_stop_the_repetition():
    r = np.ones(80, np.uint8)
    o = A.a1_event(r, 0, (True, True, 1, 0.1), 1.0, random.Random(1), A.A1)  # every frame received, no ACK ever reaches the car
    assert o["prov_tx"] > 4 and o["prov_stop"] in ("deadline", "duty") and o["conf_tx"] == 4


def test_confirm_ack_ends_the_provisional_repetition():
    r = np.ones(80, np.uint8)
    # the ACKs of the provisional frames are lost (0.0 < 0.5), the ACK of the confirm arrives (0.9 >= 0.5)
    o = A.a1_event(r, 0, (True, True, 1, 0.1), 0.5, FakeRng([0.0] * 6 + [0.9] + [0.9] * 20), A.A1)
    assert o["prov_stop"] == "confirm_acked" and o["conf_tx"] >= 1


def test_cap_gives_exactly_four_provisional_frames():
    r = np.zeros(80, np.uint8)
    o = A.a1_event(r, 0, (True, False, 0, 0.1), 0.0, random.Random(1), A.Cfg(cap=4))
    assert o["prov_tx"] == 4 and o["prov_stop"] == "cap"


def test_after_confirm_false_stops_repeats_when_the_confirm_is_done():
    r = np.zeros(120, np.uint8)
    o1 = A.a1_event(r, 0, (True, True, 1, 0.1), 0.0, random.Random(1), A.Cfg(after_confirm=True))
    o0 = A.a1_event(r, 0, (True, True, 1, 0.1), 0.0, random.Random(1), A.Cfg(after_confirm=False))
    assert o0["prov_stop"] == "confirm_done" and o0["prov_tx"] < o1["prov_tx"]


def test_field_widths_and_coarse_position():
    key = kdf(MASTER, 7)
    raw = A.encode_prov(key, 7, -33.5, -70.25, 3_000_000_000, 257)
    d = A.decode_prov(raw)
    assert d["epoch"] == 3_000_000_000 and d["seq"] == 1 and d["lat"] == round(-33.5 * 64) and d["lon"] == round(-70.25 * 64)
    assert A.coarse(1e6) == 32767 and A.coarse(-1e6) == -32768
    assert A.verify_prov(raw, key)


def test_frame_with_full_alert_type_and_valid_tag_is_rejected():
    import struct as _s

    key = kdf(MASTER, 7)
    body = _s.pack(A._PROV_FMT, P.VERSION, P.MSG_ALERT, 7, 1, 0, 0, 5, 0)
    raw = body + A.prov_tag(key, body)  # a 24-byte frame whose tag is valid but whose type is not provisional
    assert len(raw) == 24 and not A.verify_prov(raw, key)


def test_ack_for_names_epoch_and_seq():
    frame = A.encode_prov(kdf(MASTER, 7), 7, 1.0, 2.0, 123456, 9)
    a = P.decode_ack(A.ack_for(MASTER, frame))
    assert (a.node_id, a.acked_event_id, a.acked_counter) == (7, 123456, 9)


def test_ack_with_valid_tag_but_wrong_type_does_not_stop():
    import struct as _s

    s = A.ProvSession(MASTER, 7, 1.0, 2.0, 100, 2)
    body = _s.pack(P._ACK_FMT, P.VERSION, P.MSG_ALERT, 7, 100, 2, 1)  # type is not ACK, tag valid under the vehicle key
    raw = body + P.tag(kdf(MASTER, 7), body)
    assert len(raw) == P.ACK_LEN and not s.on_ack(raw)


def test_ack_naming_an_id_never_sent_does_not_stop():
    s = A.ProvSession(MASTER, 7, 1.0, 2.0, 100, 2)
    never = P.encode_ack(P.Ack(node_id=7, acked_event_id=0, acked_counter=0, base_counter=1), kdf(MASTER, 7))
    assert not s.on_ack(never) and s.sent_ids == {(100, 2)}
