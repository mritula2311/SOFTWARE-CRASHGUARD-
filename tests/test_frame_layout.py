"""The normative frame layout (src/crashguard/frame_layout.py) against the encoders of the repository (CODE rows) and its own reference functions (DESIGN rows)."""
import hashlib
import hmac
import random
import struct

import pytest

from crashguard import frame_layout as FL
from crashguard import packet as P
from crashguard import sct_protocol as S
from crashguard.lora import airtime_ms

KEY = bytes(range(32))


def test_geometry_and_lengths():
    for name, f in FL.FRAMES.items():
        FL.check_row_geometry(name)
        assert f["rows"][-1][2] == "tag"
    assert FL.FRAMES["ALERT"]["length"] == P.ALERT_LEN == 97
    assert FL.FRAMES["ACK"]["length"] == P.ACK_LEN == 26
    assert FL.FRAMES["FLASH-14"]["length"] == S.FLASH_LEN == 14
    assert FL.FRAMES["FLASH-15"]["length"] == 15 and FL.FRAMES["MICRO"]["length"] == 8


def test_alert_code_rows_match_the_encoder():
    a = P.Alert(node_id=0x11223344, event_id=0x55667788, counter=0x01020304, timestamp_ms=0x0A0B0C0D, severity=3, impact_side=2, angle_deg_x10=1234, lat_e7=-123456789, lon_e7=987654321,
                peak_g_x100=4321, ml_prob_x10000=9999, rule_sev=2, sw_mask=5, sw_first=1, rollover=1, delta_v_kmh_x100=3333, asi_x100=444)
    raw = P.encode_alert(a, KEY)
    fmt = {1: "<B", 2: "<H", 4: "<I"}
    got = {}
    for off, size, name, _cov, src, _n in FL.FRAMES["ALERT"]["rows"]:
        if src == "CODE" and name in ("version", "msg_type", "node_id", "event_id", "timestamp_ms", "severity", "impact_side", "angle_deg x10", "peak_g x100", "ml_prob x10000", "rule_sev", "sw_mask", "sw_first", "rollover", "delta_v_kmh x100", "asi x100"):
            got[name] = struct.unpack_from(fmt[size], raw, off)[0]
    assert got["node_id"] == 0x11223344 and got["event_id"] == 0x55667788 and got["timestamp_ms"] == 0x0A0B0C0D
    assert got["severity"] == 3 and got["angle_deg x10"] == 1234 and got["delta_v_kmh x100"] == 3333 and got["asi x100"] == 444
    assert struct.unpack_from("<I", raw, 10)[0] == 0x01020304  # the former counter offset is the freshness field offset
    assert raw[89:] == hmac.new(KEY, raw[:89], hashlib.sha256).digest()[:8]


def test_freshness_fields_in_the_alert_round_trip_and_are_covered_by_the_tag():
    base = P.Alert(node_id=7, event_id=9, counter=0, timestamp_ms=123)
    f = FL.field_time(1_500_000_000)
    raw = FL.pack_alert(base, f, 3, 0xDEADBEEF, KEY)
    assert len(raw) == 97 and FL.unpack_alert_fresh(raw) == (f, 3, 0xDEADBEEF)
    assert P.tag_ok(raw, KEY, 89)
    for off in (10, 42, 43, 46):  # changing any freshness byte after signing is rejected
        bad = bytearray(raw)
        bad[off] ^= 1
        assert not P.tag_ok(bytes(bad), KEY, 89)
    assert raw[47:89] == bytes(42)
    nt = FL.field_no_time(boot=0x12345, counter=0xBEEF)
    assert nt >> 31 == 1 and (nt >> 16) & 0x7FFF == 0x12345 & 0x7FFF and nt & 0xFFFF == 0xBEEF


def test_flash_14_equals_the_code_encoder_when_the_design_bits_are_zero():
    m = S.Short(node_id=0xABCD, counter=0x1234, severity=0, event=1)
    assert S.encode_short(m, KEY) == FL.pack_short(FL.MSG_FLASH, 0xABCD, 0x1234, 1, None, KEY)
    c = S.Short(node_id=0xABCD, counter=0x1234, severity=0, event=0, msg_type=S.MSG_CANCEL)
    assert S.encode_short(c, KEY) == FL.pack_short(FL.MSG_CANCEL, 0xABCD, 0x1234, 0, None, KEY)
    assert S.short_tag_ok(FL.pack_short(FL.MSG_FLASH, 1, 2, 0, None, KEY), KEY)


def test_flash_15_boot_byte_is_covered_and_airtime_equals_the_14_byte_frame_at_sf7_and_sf9():
    raw = FL.pack_short(FL.MSG_FLASH, 5, 0x00FF, 0, 0x1234, KEY)
    assert len(raw) == 15 and raw[6] == 0x34
    bad = bytearray(raw)
    bad[6] ^= 1
    assert raw[7:] != hmac.new(KEY, bytes(bad[:7]), hashlib.sha256).digest()[:8]
    for sf in (7, 9):
        assert airtime_ms(15, sf) == airtime_ms(14, sf) == airtime_ms(13, sf)
    u = FL.unpack_short(raw)
    assert u["boot8"] == 0x34 and not u["no_time"] and u["msg_type"] == FL.MSG_FLASH


def test_no_time_flag_and_class_bits():
    raw = FL.pack_short(FL.MSG_FLASH, 5, FL.field_no_time(3, 77), 2, None, KEY)
    u = FL.unpack_short(raw)
    assert u["no_time"] and u["field16"] == 77 and u["low"] == 2 and raw[5] & 0x70 == 0  # no severity class in the provisional frame


def test_reconstruct_time_stamped_field_within_the_window():
    rnd = random.Random(3)
    for _ in range(2000):
        now = rnd.randrange(1_000_000_000, 1_900_000_000)
        true = now + rnd.randrange(-60, 61)
        assert FL.reconstruct_field(true & 0xFFFF, False, now, 0) == true
    # boundary: unambiguous while the offset is below 2^15 s, ambiguous above
    now = 1_700_000_000
    assert FL.reconstruct_field((now + 32767) & 0xFFFF, False, now, 0) == now + 32767
    assert FL.reconstruct_field((now + 40000) & 0xFFFF, False, now, 0) != now + 40000


def test_reconstruct_boot_counter():
    for known in (0, 5, 250, 255, 256, 1000, 2**32 - 300):
        for step in (0, 1, 7, 255):
            true = known + step
            if true < 2**32:
                assert FL.reconstruct_boot(true & 0xFF, known) == true
    assert FL.reconstruct_boot(0, 255) == 256  # wraps upward


def test_micro_frame_layout_and_tag_formula_of_the_c_code():
    t1 = bytes(range(8))
    b0 = FL.micro_b0(cancel=False, cls=3, event=1, offset_flag=True)
    assert b0 == 0b0_011_01_1_0
    frame = FL.micro_pack(KEY, t1, b0, 0x2A, 0xCAFE, index=9)
    assert len(frame) == 8 == FL.MICRO_LEN and frame[0] == 9 and frame[1] == b0 and frame[2] == 0x2A
    assert frame[3:] == hmac.new(KEY, b"M" + t1 + bytes([b0, 0x2A]) + (0xCAFE).to_bytes(4, "big"), hashlib.sha256).digest()[:5]
    assert frame[1:] == FL.micro_core(KEY, t1, b0, 0x2A, 0xCAFE) and len(frame[1:]) == FL.MICRO_CORE_LEN == 7
    assert FL.micro_b0(True, 0, 0, False) == 0x80  # the cancel differs from the confirm by bit 7, inside the tagged bytes
    assert FL.micro_pack(KEY, t1, FL.micro_b0(True, 3, 1, True), 0x2A, 0xCAFE, index=9)[3:] != frame[3:]


def test_micro_index_lookup_has_one_candidate_and_rejects_wrong_index_stale_boot_and_unknown_index():
    rnd = random.Random(11)
    pending = {i: (bytes(rnd.randrange(256) for _ in range(32)), bytes(rnd.randrange(256) for _ in range(8)), rnd.randrange(50)) for i in range(60)}
    for i in (0, 17, 59):
        k, t1, b = pending[i]
        frame = FL.micro_pack(k, t1, 0x31, 0x00, b, index=i)
        assert FL.micro_lookup(frame, pending)
        assert not FL.micro_lookup(FL.micro_pack(k, t1, 0x31, 0x00, b + 1, index=i), pending)  # the car rebooted: stale boot counter, fallback to the full confirm
        assert not FL.micro_lookup(bytes([(i + 1) % 60]) + frame[1:], pending)  # the index of another entry: that entry's tag does not match
    assert not FL.micro_lookup(bytes([200]) + bytes(7), pending)  # unknown index


def test_index_lookup_tries_one_entry_where_the_trial_lookup_of_the_7_byte_frame_tries_all():
    rnd = random.Random(5)
    pending = [(bytes(rnd.randrange(256) for _ in range(32)), bytes(rnd.randrange(256) for _ in range(8)), 3) for _ in range(60)]
    k, t1, b = pending[17]
    core = FL.micro_core(k, t1, 0x31, 0, b)
    assert FL.micro_lookup_trial(core, pending) == [17]  # same result, 60 tag computations instead of 1


def test_ns3_micro_frame_is_the_smallest_lorawan_frame_and_the_8_byte_design_is_shorter_than_it():
    assert airtime_ms(13, 7) == airtime_ms(14, 7)
    assert airtime_ms(7, 7) <= airtime_ms(8, 7) < airtime_ms(13, 7)
    assert airtime_ms(8, 9) < airtime_ms(13, 9)


@pytest.mark.parametrize("name", list(FL.FRAMES))
def test_every_frame_has_a_source_label_per_row(name):
    for row in FL.FRAMES[name]["rows"]:
        assert row[4] in ("CODE", "DESIGN", "CODE+DESIGN")
