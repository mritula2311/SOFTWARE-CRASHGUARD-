import pytest

from crashguard import packet as P
from crashguard import sct_protocol as T

KEY = bytes(range(32))
NODE = 0xC0FFEE


def _alert(c, ev=1):
    return P.encode_alert(P.Alert(node_id=NODE, event_id=ev, counter=c, timestamp_ms=1, severity=3), KEY)


def _flash(c, sev=3, typ=T.MSG_FLASH):
    return T.encode_short(T.Short(NODE, c, sev, 0, typ), KEY)


def test_lengths_and_roundtrip():
    f = _flash(70000)
    assert len(f) == 14 == T.FLASH_LEN
    m = T.decode_short(f)
    assert (m.node_id, m.counter, m.severity, m.msg_type) == (NODE & 0xFFFF, 70000 & 0xFFFF, 3, T.MSG_FLASH)
    assert T.short_tag_ok(f, KEY) and not T.short_tag_ok(f, bytes(32))


def test_tag_covers_every_body_byte():
    f = bytearray(_flash(5))
    for i in range(T.FLASH_BODY_LEN):
        g = bytearray(f)
        g[i] ^= 1
        assert not T.short_tag_ok(bytes(g), KEY)


def test_flash_then_alert_same_counter_both_accepted_and_repeats_reacked():
    b = T.SctBase(KEY)
    d, ack_f = b.handle_short(_flash(10))
    assert d == T.ACCEPT_FLASH and len(ack_f) == 26
    assert b.handle_short(_flash(10)) == (T.REACK, ack_f)
    d, ack_a = b.handle_alert(_alert(10))
    assert d == T.ACCEPT_ALERT and ack_a != ack_f
    assert b.handle_alert(_alert(10)) == (T.REACK, ack_a)


def test_alert_without_a_flash_is_accepted():
    assert T.SctBase(KEY).handle_alert(_alert(3))[0] == T.ACCEPT_ALERT


def test_replay_and_forgery_rejected():
    b = T.SctBase(KEY, recent_n=1)
    b.handle_short(_flash(10))
    b.handle_short(_flash(11))  # pushes 10 out of the re-ACK memory
    assert b.handle_short(_flash(10))[0] == T.REJECT_COUNTER
    assert b.handle_short(_flash(12)[:-1] + b"\x00")[0] == T.REJECT_TAG
    assert b.handle_short(b"\x00" * 13)[0] == T.REJECT_LENGTH


def test_counter_wraps_past_16_bits():
    b = T.SctBase(KEY)
    b.last_flash[NODE & 0xFFFF] = 65530
    d, _ = b.handle_short(_flash(65540))  # low 16 bits = 4
    assert d == T.ACCEPT_FLASH and b.last_flash[NODE & 0xFFFF] == 65540


def test_cancel_marks_known_events_only_and_is_idempotent():
    b = T.SctBase(KEY)
    b.handle_short(_flash(20))
    assert b.handle_short(_flash(20, typ=T.MSG_CANCEL))[0] == T.CANCELLED
    assert b.handle_short(_flash(20, typ=T.MSG_CANCEL))[0] == T.CANCELLED
    assert (NODE & 0xFFFF, 20) in b.cancelled
    assert b.handle_short(_flash(99, typ=T.MSG_CANCEL))[0] == T.REJECT_UNKNOWN


def test_flash_does_not_advance_the_alert_counter():
    b = T.SctBase(KEY)
    b.handle_short(_flash(50))
    assert b.last_alert.get(NODE & 0xFFFF, -1) == -1


@pytest.mark.parametrize("sf", [7, 9, 12])
def test_flash_is_shorter_than_the_alert(sf):
    from crashguard.lora import airtime_ms

    assert airtime_ms(14, sf) < airtime_ms(97, sf)
