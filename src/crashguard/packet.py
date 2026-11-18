"""97-byte alert and 26-byte ACK (docs/01_protocol/PACKET_FORMAT.md). Little-endian, HMAC-SHA256 truncated to 8 bytes.

The layout is a proposal for software tests; align it with firmware v2 and update PACKET_FORMAT.md if it differs.
"""
from __future__ import annotations

import hashlib
import hmac
import struct
from dataclasses import dataclass

VERSION = 1
MSG_ALERT, MSG_ACK, MSG_HEARTBEAT = 1, 2, 3
ALERT_LEN, ALERT_BODY_LEN, TAG_LEN = 97, 89, 8
ACK_LEN, ACK_BODY_LEN = 26, 18
_ALERT_FMT = "<BBIIIIBBHiiHHBBBBHH"  # 42 bytes (offsets 38-41: delta_v_kmh x100, asi x100), then 47 reserved bytes
_ACK_FMT = "<BBIIII"
RESERVED_LEN = ALERT_BODY_LEN - struct.calcsize(_ALERT_FMT)
assert struct.calcsize(_ALERT_FMT) == 42 and RESERVED_LEN == 47


@dataclass
class Alert:
    node_id: int
    event_id: int
    counter: int
    timestamp_ms: int
    severity: int = 0  # 0 low, 1 moderate, 2 severe, 3 critical
    impact_side: int = 0  # 0 F, 1 R, 2 L, 3 Rt, 4 V
    angle_deg_x10: int = 0
    lat_e7: int = 0
    lon_e7: int = 0
    peak_g_x100: int = 0
    ml_prob_x10000: int = 0
    rule_sev: int = 0
    sw_mask: int = 0
    sw_first: int = 0
    rollover: int = 0
    delta_v_kmh_x100: int = 0  # offset 38, u16: resultant delta-V in km/h x 100 (0 to 655.35)
    asi_x100: int = 0  # offset 40, u16: ASI x 100
    version: int = VERSION
    msg_type: int = MSG_ALERT
    reserved: bytes = bytes(RESERVED_LEN)


@dataclass
class Ack:
    node_id: int
    acked_event_id: int
    acked_counter: int
    base_counter: int
    version: int = VERSION
    msg_type: int = MSG_ACK


def tag(key: bytes, body: bytes) -> bytes:
    return hmac.new(key, body, hashlib.sha256).digest()[:TAG_LEN]


def encode_alert(a: Alert, key: bytes) -> bytes:
    body = struct.pack(_ALERT_FMT, a.version, a.msg_type, a.node_id, a.event_id, a.counter, a.timestamp_ms, a.severity,
                       a.impact_side, a.angle_deg_x10, a.lat_e7, a.lon_e7, a.peak_g_x100, a.ml_prob_x10000, a.rule_sev,
                       a.sw_mask, a.sw_first, a.rollover, a.delta_v_kmh_x100, a.asi_x100) + a.reserved
    assert len(body) == ALERT_BODY_LEN
    return body + tag(key, body)


def decode_alert(raw: bytes) -> Alert:
    """Parse fields without checking the tag. Raises ValueError on wrong length."""
    if len(raw) != ALERT_LEN:
        raise ValueError(f"alert must be {ALERT_LEN} bytes, got {len(raw)}")
    v = struct.unpack_from(_ALERT_FMT, raw)
    d = dict(zip(["version", "msg_type", "node_id", "event_id", "counter", "timestamp_ms", "severity", "impact_side",
                  "angle_deg_x10", "lat_e7", "lon_e7", "peak_g_x100", "ml_prob_x10000", "rule_sev", "sw_mask", "sw_first", "rollover", "delta_v_kmh_x100", "asi_x100"], v))
    return Alert(reserved=raw[42:ALERT_BODY_LEN], **d)


def tag_ok(raw: bytes, key: bytes, body_len: int) -> bool:
    return hmac.compare_digest(raw[body_len:], tag(key, raw[:body_len]))


def encode_ack(a: Ack, key: bytes) -> bytes:
    body = struct.pack(_ACK_FMT, a.version, a.msg_type, a.node_id, a.acked_event_id, a.acked_counter, a.base_counter)
    return body + tag(key, body)


def decode_ack(raw: bytes) -> Ack:
    if len(raw) != ACK_LEN:
        raise ValueError(f"ACK must be {ACK_LEN} bytes, got {len(raw)}")
    v, t, node, ev, ctr, base = struct.unpack_from(_ACK_FMT, raw)
    return Ack(version=v, msg_type=t, node_id=node, acked_event_id=ev, acked_counter=ctr, base_counter=base)
