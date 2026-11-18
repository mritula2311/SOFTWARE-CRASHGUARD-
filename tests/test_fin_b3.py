from crashguard.fin_b3 import toa_formula
from crashguard.lora import airtime_ms


def test_hand_values():
    # SF7, 125 kHz, CR 4/5, preamble 8, explicit header, CRC on, 97 bytes: ceil(792/28) = 29 groups x 5 + 8 = 153 symbols; (12.25 + 153) x 1.024 ms
    assert abs(airtime_ms(97, 7) - 165.25 * 1.024) < 1e-9
    assert abs(toa_formula(97, 7) - 165.25 * 1.024) < 1e-9
    assert abs(airtime_ms(14, 9) - toa_formula(14, 9)) < 1e-9


def test_pending_cancel_option():
    from crashguard import attacks_extra as AX
    from crashguard import sct_protocol as T
    from crashguard.attacks import KEY, NODE

    b = T.SctBase(KEY)
    assert b.handle_short(AX._short(40, T.MSG_CANCEL))[0] == T.REJECT_UNKNOWN
    b = T.SctBase(KEY, pending_cancel=True)
    assert b.handle_short(AX._short(40, T.MSG_CANCEL))[0] == T.CANCELLED
    b.handle_alert(AX._alert(40))
    assert (NODE & 0xFFFF, 40) in b.cancelled
    # an old CANCEL (counter not above the accepted ones) is still refused
    b.handle_short(AX._short(60))
    assert b.handle_short(AX._short(50, T.MSG_CANCEL))[0] == T.REJECT_UNKNOWN
