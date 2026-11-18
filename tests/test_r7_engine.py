"""Round 7: the engine's old path with no duty layer equals the stored replay logic draw for draw; duty layers and the reserved policy behave as preregistered (V18 section 2)."""
import math
import random

import numpy as np
import pytest

from crashguard import r3_t1 as T
from crashguard import r6_micro as M6
from crashguard import r7_engine as E7
from crashguard.lora import airtime_ms

A = lambda n, sf=7: airtime_ms(n, sf) / 1000.0  # noqa: E731


def engine_trace(r, s, ev, p_dl, rng, micro_bytes=None, policy="old", duty=None, win=None):
    E, F, y, te = ev
    if F:  # the single-stage reference consumes its draws first, as in r3_event and micro_event
        T.arrival_trace(r, s, T.FINAL_S + T.COMPUTE3, T.A_AL, p_dl, rng)
    spec = E7.Spec(bool(E), bool(F), te, 7, policy, 4, micro_bytes, T.WIN3 if win is None else win)
    return E7.run_event(spec, duty or E7.Duty("none"), 0.0, lambda i: bool(r[s + i]), lambda i: rng.random() >= p_dl)


def cases(n=400, seed=1):
    g = np.random.default_rng(seed)
    for q in range(n):
        p = float(g.choice([0.0, 0.1, 0.3, 0.6, 0.9]))
        r = g.random(60) >= p
        ev = (bool(g.integers(0, 2)), bool(g.integers(0, 2)), int(g.integers(0, 2)), float(g.choice([0.05, 0.11, 0.4, 1.0])))
        yield q, r, ev, float(g.choice([0.0, 0.2, 0.5]))


def test_old_path_equals_r3_event():
    for q, r, ev, p_dl in cases():
        a = T.r3_event(r, 3, ev, p_dl, random.Random(q))
        rng = random.Random(q)
        o = engine_trace(r, 3, ev, p_dl, rng)
        E, F, y, _ = ev
        if not (E or F):
            continue
        assert math.isclose(o["air"], a["two_air"], abs_tol=1e-12), (q, ev)
        if E and not F:
            assert (y == 1 and math.isfinite(o["arr_f"]) and bool(o["cancel_lost"])) == bool(a["two_d"])
        else:
            assert (y == 1 and (math.isfinite(o["arr_f"]) or math.isfinite(o["arr_c"]))) == bool(a["two_d"])


def test_old_path_equals_micro_event():
    a_micro = A(13)
    for q, r, ev, p_dl in cases(seed=2):
        E, F, y, _ = ev
        if not (E or F):
            continue
        a = M6.micro_event(r, 3, ev, p_dl, random.Random(q), a_micro)
        o = engine_trace(r, 3, ev, p_dl, random.Random(q), micro_bytes=13)
        assert math.isclose(o["air"], a["two_air"], abs_tol=1e-12), (q, ev)
        if E and not F:
            assert (y == 1 and math.isfinite(o["arr_f"]) and bool(o["cancel_lost"])) == bool(a["two_d"])
        else:
            assert (y == 1 and (math.isfinite(o["arr_f"]) or math.isfinite(o["arr_c"]))) == bool(a["two_d"])


def full_suppression(spec, duty, t0=0.0):
    return E7.run_event(spec, duty, t0, lambda i: True, lambda i: False)


def test_hourly_old_policy_sends_all_eight_frames_when_ack_suppressed():
    o = full_suppression(E7.Spec(True, True, 0.05, 7), E7.Duty("H", 36.0))
    assert o["n_f"] == 4 and o["n_c"] == 4
    assert math.isclose(o["air"], 4 * A(14) + 4 * A(97), rel_tol=1e-12)
    assert o["follow_delay"] < 1e-9


def test_reserved_hourly_class_l_never_leaves_less_than_reserve():
    # allowance just above the reserve: no flash is sent, the confirm is still sent
    sf = 7
    spec = E7.Spec(True, True, 0.05, sf, "reserved")
    allow = 4 * A(14, sf) + 0.5 * A(97, sf)
    d = E7.Duty("H", allow)
    o = full_suppression(spec, d)
    assert o["n_f"] == 0 and o["flash_blocked"]
    assert o["n_c"] >= 1 and o["follow_delay"] < 1e-9
    # old policy with the same allowance spends it on flash tries and delays the confirm into the next hour
    d2 = E7.Duty("H", allow)
    o2 = full_suppression(E7.Spec(True, True, 0.05, sf, "old"), d2)
    assert o2["n_f"] == 4 and o2["follow_delay"] > 1.0


def test_off_time_old_policy_delays_confirm_and_reserved_does_not():
    for sf, exp_tries in ((7, 3), (8, 3), (9, 3)):
        old = full_suppression(E7.Spec(True, True, 0.05, sf, "old"), E7.Duty("T"))
        res = full_suppression(E7.Spec(True, True, 0.05, sf, "reserved"), E7.Duty("T"))
        assert res["follow_delay"] < 1e-9, sf
        assert old["follow_delay"] >= 0.0
        assert res["n_f"] <= 4
    # SF9: the old policy's confirm starts after the fourth flash try and its off-time (about 6.65 s)
    old9 = full_suppression(E7.Spec(True, True, 0.05, 9, "old"), E7.Duty("T"))
    assert 4.0 < old9["follow_delay"] < 6.0


def test_reserved_equals_old_without_duty_pressure():
    for q, r, ev, p_dl in cases(200, seed=3):
        if ev[3] > 0.4:  # a flash that starts late would still be retrying when the follow-up is due: the reserved policy withdraws those tries by design
            continue
        a = engine_trace(r, 3, ev, p_dl, random.Random(q), policy="old")
        b = engine_trace(r, 3, ev, p_dl, random.Random(q), policy="reserved", duty=E7.Duty("H", 36.0))
        assert a["air"] == pytest.approx(b["air"]) and a["n_f"] == b["n_f"] and a["n_c"] == b["n_c"]
