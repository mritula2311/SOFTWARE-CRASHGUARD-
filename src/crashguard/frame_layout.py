"""Normative byte layout of every CrashGuard frame (docs/05_architecture/FRAME_LAYOUT.md is generated from ``FRAMES`` here by ``frame_layout_doc``).

Each field row says where the layout comes from: CODE (an encoder in the repository fixes it: packet.py, sct_protocol.py, firmware_rd/cg_rd.c, firmware_r6/cg_r6.c), or DESIGN (chosen in the delta
verification run to close the gap B5; no encoder in the repository, no stored result depends on it). ``tests/test_frame_layout.py`` checks the CODE rows against the encoders and the DESIGN rows
against the reference functions below. Nothing in this file changes a stored result: sizes of the evaluated frames (97, 26, 14 bytes; the micro frame is 8 bytes in the design and was 13 bytes in ns-3) are kept or lower.

Byte order: little-endian for every multi-byte field of every frame. The micro-confirm tag input uses a big-endian boot counter (cg_r6.c); it is a MAC input, not a frame field.
"""
from __future__ import annotations

import hashlib
import hmac
import struct

from crashguard import packet as P
from crashguard import sct_protocol as S

TAG8, TAG5 = 8, 5
FLASH14, FLASH15, MICRO_LEN, MICRO_CORE_LEN = 14, 15, 8, 7  # the micro frame is the 7-byte frame of cg_micro_pack behind a one-byte pending index
MSG_FLASH, MSG_CANCEL = S.MSG_FLASH, S.MSG_CANCEL
FLASH_ACK_EVENT = S.FLASH_EVENT_ID
MICRO_LETTER = b"M"
NO_TIME_BIT = 0x80  # byte 5 of the flash and the cancel (DESIGN): 1 = the freshness field is the no-time form
FIELD_NO_TIME = 1 << 31  # bit 31 of the 32-bit freshness field (DESIGN): 1 = no-time form (15-bit epoch, 16-bit counter)

# (offset, size, field, covered by tag, source, note)
FRAMES: dict[str, dict] = {
    "ALERT": dict(length=97, tag=8, rows=[
        (0, 1, "version", True, "CODE", "packet.VERSION = 1"),
        (1, 1, "msg_type", True, "CODE", "1 = alert (domain separation: the type is inside the tagged bytes)"),
        (2, 4, "node_id", True, "CODE", "u32"),
        (6, 4, "event_id", True, "CODE", "u32, unique per event of the vehicle"),
        (10, 4, "freshness field", True, "DESIGN", "was `counter` (u32). Time-stamped form: GPS seconds since 1980-01-06 00:00:00 UTC, bit 31 = 0. No-time form: bit 31 = 1, bits 30 to 16 = epoch (boot counter mod 2^15), bits 15 to 0 = counter"),
        (14, 4, "timestamp_ms", True, "CODE", "u32, unchanged"),
        (18, 1, "severity", True, "CODE", "0 low to 3 critical"),
        (19, 1, "impact_side", True, "CODE", "0 F, 1 R, 2 L, 3 Rt, 4 V"),
        (20, 2, "angle_deg x10", True, "CODE", "u16"),
        (22, 4, "lat x1e7", True, "CODE", "i32"),
        (26, 4, "lon x1e7", True, "CODE", "i32"),
        (30, 2, "peak_g x100", True, "CODE", "u16"),
        (32, 2, "ml_prob x10000", True, "CODE", "u16"),
        (34, 1, "rule_sev", True, "CODE", "u8"),
        (35, 1, "sw_mask", True, "CODE", "u8"),
        (36, 1, "sw_first", True, "CODE", "u8"),
        (37, 1, "rollover", True, "CODE", "u8"),
        (38, 2, "delta_v_kmh x100", True, "CODE", "u16"),
        (40, 2, "asi x100", True, "CODE", "u16"),
        (42, 1, "sequence in second", True, "DESIGN", "u8, the lead byte of the 47 reserved bytes: number of alerts the vehicle already sent with the same freshness field (0 for the initial alert; saturates at 255)"),
        (43, 4, "boot counter", True, "DESIGN", "u32, non-volatile, increased and written once per boot (four of the reserved bytes)"),
        (47, 42, "reserved", True, "CODE", "zeros; the 47 reserved bytes of packet.RESERVED_LEN minus the 5 bytes used above"),
        (89, 8, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, bytes 0 to 88)[:8]"),
    ]),
    "ACK": dict(length=26, tag=8, rows=[
        (0, 1, "version", True, "CODE", "1"),
        (1, 1, "msg_type", True, "CODE", "2 = ACK"),
        (2, 4, "node_id", True, "CODE", "u32, the vehicle that is acknowledged (the ACK is tagged with that vehicle's key)"),
        (6, 4, "acked event_id", True, "CODE", "u32; 0xFFFFFFFF = the ACK of a provisional frame (sct_protocol.FLASH_EVENT_ID)"),
        (10, 4, "acked freshness field", True, "DESIGN", "was `acked counter`: the 32-bit freshness field of the acknowledged frame (for a flash: reconstructed by the base)"),
        (14, 4, "base counter", True, "CODE+DESIGN", "u32, the base's own counter; no model uses it. In the ACK of a provisional frame its low byte is the pending index that the micro frame returns (DESIGN, finalize run)"),
        (18, 8, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, bytes 0 to 17)[:8]"),
    ]),
    "FLASH-14": dict(length=14, tag=8, rows=[
        (0, 1, "version and type", True, "CODE", "high nibble version (1), low nibble type: 4 = flash (domain separation inside the tagged bytes)"),
        (1, 2, "short node id", True, "CODE", "u16, low 16 bits of node_id; ASSUMPTION: unique in the fleet"),
        (3, 2, "freshness field, low 16 bits", True, "CODE+DESIGN", "CODE: low 16 bits of the 32-bit counter of the event. DESIGN: of the 32-bit freshness field of the event (the flash and the full alert of one event carry the same field)"),
        (5, 1, "flags and event type", True, "CODE+DESIGN", "bit 7 (DESIGN) = no-time form; bits 6 to 4 = 0: the provisional frame carries no severity class (the encoder allows a class there; the design leaves it zero); bits 3 to 0 = event type (0 crash, 1 rollover, 2 other)"),
        (6, 8, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, bytes 0 to 5)[:8]"),
    ]),
    "CANCEL-14": dict(length=14, tag=8, rows=[
        (0, 1, "version and type", True, "CODE", "type 5 = cancel"),
        (1, 2, "short node id", True, "CODE", "as the flash"),
        (3, 2, "freshness field, low 16 bits", True, "CODE+DESIGN", "of the event that is cancelled"),
        (5, 1, "flags and reason", True, "CODE+DESIGN", "bit 7 = no-time form (DESIGN); bits 3 to 0 = reason (0 = driver cancel)"),
        (6, 8, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, bytes 0 to 5)[:8]"),
    ]),
    "FLASH-15": dict(length=15, tag=8, rows=[
        (0, 1, "version and type", True, "CODE", "as FLASH-14"),
        (1, 2, "short node id", True, "CODE", "as FLASH-14"),
        (3, 2, "freshness field, low 16 bits", True, "CODE+DESIGN", "as FLASH-14"),
        (5, 1, "flags and event type", True, "CODE+DESIGN", "as FLASH-14"),
        (6, 1, "boot counter, low 8 bits", True, "DESIGN", "u8: B mod 256; the base rebuilds the 32-bit value nearest above its last known one"),
        (7, 8, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, bytes 0 to 6)[:8]"),
    ]),
    "CANCEL-15": dict(length=15, tag=8, rows=[
        (0, 1, "version and type", True, "CODE", "type 5"),
        (1, 2, "short node id", True, "CODE", "as FLASH-14"),
        (3, 2, "freshness field, low 16 bits", True, "CODE+DESIGN", "of the cancelled event"),
        (5, 1, "flags and reason", True, "CODE+DESIGN", "as CANCEL-14"),
        (6, 1, "boot counter, low 8 bits", True, "DESIGN", "as FLASH-15"),
        (7, 8, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, bytes 0 to 6)[:8]"),
    ]),
    "MICRO": dict(length=8, tag=5, rows=[
        (0, 1, "pending index", False, "DESIGN", "u8, assigned by the base when it acknowledges the provisional frame (low byte of the `base counter` of that ACK) and sent back here; it names the pending entry (vehicle key, T1, boot counter), so the base verifies the tag under one candidate. It is not in the MAC input: a changed index selects another entry, whose tag then fails (probability 2^-40 per frame to pass). F3 of the finalize run"),
        (1, 1, "type, class, event, flag", True, "CODE+DESIGN", "bit 7 = type (0 confirm, 1 cancel); bits 6 to 4 = severity class (for a cancel the reason); bits 3 to 2 = event type; bit 1 = position-offset flag; bit 0 = 0 (spare). V17 section 3 fixes the fields, the bit positions are DESIGN. The tag function treats the byte as opaque (cg_micro_tag)"),
        (2, 1, "position offset", True, "CODE+DESIGN", "high nibble east, low nibble north, each signed 4 bits in units of 128 m relative to the last position the base holds for the vehicle; 0x00 when the flag is 0"),
        (3, 5, "tag", False, "CODE", "HMAC-SHA256(K_vehicle, 'M' followed by T1 (8 bytes), the two content bytes (the type byte and the position offset) and the boot counter (u32, big endian))[:5]; T1 = the 8-byte tag of the provisional frame; the frame carries neither T1 nor the vehicle, the index names them. Bytes 1 to 7 are the 7-byte frame of `cg_micro_pack`"),
    ]),
}

SEPARATION = [
    ("alert", "msg_type byte = 1 at offset 1, inside the tagged bytes; length 97", "'A'"),
    ("ACK", "msg_type byte = 2 at offset 1, inside the tagged bytes; length 26", "'ACK'"),
    ("provisional frame", "type nibble 4 in byte 0, inside the tagged bytes; length 14 or 15", "'F' (ProVerif and Tamarin R6), 'P' (round-4 model)"),
    ("cancel (14 or 15 bytes)", "type nibble 5 in byte 0, inside the tagged bytes", "no letter in the frozen models; micro-cancel 'X'"),
    ("micro-confirm and micro-cancel", "ASCII 'M' (0x4D) in front of the MAC input; confirm and cancel differ by bit 7 of byte 0, inside the tagged bytes; length 8", "'M' (confirm), 'X' (cancel)"),
]


def check_row_geometry(name: str) -> None:
    """Rows are contiguous, cover the whole frame, and the tag is the last row."""
    f = FRAMES[name]
    pos = 0
    for off, size, _fld, _cov, _src, _note in f["rows"]:
        assert off == pos, (name, off, pos)
        pos += size
    assert pos == f["length"], (name, pos, f["length"])
    assert f["rows"][-1][1] == f["tag"]


for _n in FRAMES:
    check_row_geometry(_n)


# ----------------------------------------------------------------------------- reference functions (DESIGN rows)
def mac(key: bytes, body: bytes, n: int) -> bytes:
    return hmac.new(key, body, hashlib.sha256).digest()[:n]


def field_time(gps_seconds: int) -> int:
    assert 0 <= gps_seconds < FIELD_NO_TIME
    return gps_seconds


def field_no_time(boot: int, counter: int) -> int:
    return FIELD_NO_TIME | ((boot & 0x7FFF) << 16) | (counter & 0xFFFF)


def pack_alert(a: P.Alert, field: int, seq: int, boot: int, key: bytes) -> bytes:
    """97-byte alert with the freshness field at offset 10 (the former counter), sequence at 42 and boot counter at 43 to 46."""
    a = P.Alert(**{**a.__dict__, "counter": field, "reserved": bytes([seq & 0xFF]) + struct.pack("<I", boot & 0xFFFFFFFF) + bytes(P.RESERVED_LEN - 5)})
    return P.encode_alert(a, key)


def unpack_alert_fresh(raw: bytes) -> tuple[int, int, int]:
    """(freshness field, sequence in second, boot counter) of a 97-byte alert."""
    field = struct.unpack_from("<I", raw, 10)[0]
    seq = raw[42]
    boot = struct.unpack_from("<I", raw, 43)[0]
    return field, seq, boot


def pack_short(msg_type: int, node_id: int, field: int, event_or_reason: int, boot: int | None, key: bytes) -> bytes:
    """14-byte frame (boot is None) or 15-byte frame (boot counter low byte at offset 6). ``field`` is the 32-bit freshness field; the frame carries its low 16 bits and the no-time flag."""
    flags = (NO_TIME_BIT if field & FIELD_NO_TIME else 0) | (event_or_reason & 0x0F)
    body = struct.pack("<BHHB", (P.VERSION << 4) | msg_type, node_id & 0xFFFF, field & 0xFFFF, flags)
    if boot is not None:
        body += bytes([boot & 0xFF])
    return body + mac(key, body, TAG8)


def unpack_short(raw: bytes) -> dict:
    assert len(raw) in (FLASH14, FLASH15)
    b0, nid, f16, fl = struct.unpack_from("<BHHB", raw)
    return dict(version=b0 >> 4, msg_type=b0 & 0xF, node_id=nid, field16=f16, no_time=bool(fl & NO_TIME_BIT), low=fl & 0x0F, boot8=raw[6] if len(raw) == FLASH15 else None, tag=raw[-TAG8:])


def reconstruct_field(f16: int, no_time: bool, now_gps: int, last_epoch: int) -> int:
    """32-bit freshness field from the 16 transmitted bits: time-stamped form, the value congruent to f16 modulo 2^16 nearest the base's own GPS second (valid while |field - now| < 2^15 s);
    no-time form, the epoch the base holds for the vehicle (15 bits) above the 16-bit counter."""
    if no_time:
        return field_no_time(last_epoch, f16)
    base = now_gps - ((now_gps - f16) & 0xFFFF)  # largest value <= now that is congruent to f16
    cands = (base, base + 0x10000)
    return min(cands, key=lambda x: abs(x - now_gps))


def reconstruct_boot(b8: int, last_known: int) -> int:
    """32-bit boot counter from its low byte: the smallest value >= last_known with that low byte."""
    return last_known + ((b8 - last_known) & 0xFF)


def micro_b0(cancel: bool, cls: int, event: int, offset_flag: bool) -> int:
    assert 0 <= cls < 8 and 0 <= event < 4
    return (int(cancel) << 7) | (cls << 4) | (event << 2) | (int(offset_flag) << 1)


def micro_tag(key: bytes, t1: bytes, b0: int, b1: int, boot: int) -> bytes:
    assert len(t1) == 8
    return mac(key, MICRO_LETTER + t1 + bytes([b0, b1]) + struct.pack(">I", boot & 0xFFFFFFFF), TAG5)


def micro_core(key: bytes, t1: bytes, b0: int, b1: int, boot: int) -> bytes:
    """The 7-byte frame of ``cg_micro_pack`` (two content bytes and the 5-byte tag)."""
    return bytes([b0, b1]) + micro_tag(key, t1, b0, b1, boot)


def micro_pack(key: bytes, t1: bytes, b0: int, b1: int, boot: int, index: int) -> bytes:
    """8-byte micro frame: pending index, then the 7-byte core. The index is outside the MAC input."""
    assert 0 <= index < 256
    return bytes([index]) + micro_core(key, t1, b0, b1, boot)


def micro_lookup(frame: bytes, pending: dict[int, tuple[bytes, bytes, int]]) -> bool:
    """Direct lookup: the base takes the entry that the index names and verifies the tag under it (one candidate, so 2^-40 per frame). False if the index is unknown or the tag fails."""
    assert len(frame) == MICRO_LEN
    ent = pending.get(frame[0])
    if ent is None:
        return False
    k, t1, b = ent
    return hmac.compare_digest(micro_tag(k, t1, frame[1], frame[2], b), frame[3:])


def micro_lookup_trial(frame7: bytes, pending: list[tuple[bytes, bytes, int]]) -> list[int]:
    """The lookup of the 7-byte frame (rejected by the finalize run): indices of every pending entry under which the tag verifies; the cost and the forgery probability grow with the number of entries."""
    assert len(frame7) == MICRO_CORE_LEN
    return [i for i, (k, t1, b) in enumerate(pending) if hmac.compare_digest(micro_tag(k, t1, frame7[0], frame7[1], b), frame7[2:])]
