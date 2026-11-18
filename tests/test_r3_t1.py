"""Known-answer tests for the trace replay (T1): docs/02_preregistration/PREREGISTRATION_V14.md section 1.3."""
import math
import random

import numpy as np
import pytest

from crashguard import r3_t1 as T


@pytest.fixture(scope="module", autouse=True)
def _ctx():
    T.init_ctx()


def rng():
    return random.Random(1)


def test_all_received_delivers_at_ready_plus_airtime():
    r = np.ones(80, np.uint8)
    a9 = T.air(97, 9)
    for pol, hold in (("quick", 0.0), ("khan", 0.0), ("nessa", 0.0), ("P4", 0.0), ("P1", 5.0), ("P0", 5.0)):
        t, n, used = T.replay_alert(pol, r, 30, rng(), 0.3)
        assert t == pytest.approx(T.READY0 + hold + a9) and n == 1 and used == pytest.approx(a9), pol
    t, n, _ = T.replay_alert("D1", r, 30, rng(), 0.3)
    assert n == 1 and T.READY0 < t < T.DEADLINE


def test_all_lost_never_delivers_and_stays_inside_limits():
    r = np.zeros(80, np.uint8)
    for pol in T.POLICIES:
        t, n, used = T.replay_alert(pol, r, 30, rng(), 0.3)
        assert math.isinf(t) and 1 <= n <= 12 and used <= T.LIMIT_S
    assert T.INV == {"late_delivery": 0, "duty_exceeded": 0, "frame_overrun": 0}


def test_quick_retries_known_timeline():
    r = np.array([0, 0, 1] + [1] * 60, np.uint8)
    t, n, _ = T.replay_alert("quick", r, 0, rng(), 0.0)
    a9, a10 = T.air(97, 9), T.air(97, 10)
    w9 = T.listen_window(9)
    t1 = T.READY0 + a9 + w9 + 0.3
    t2 = t1 + a9 + w9 + 0.3
    assert n == 3 and t == pytest.approx(t2 + a10)  # the third attempt is sent at SF10 (raise after 2 rounds)


def test_fixed3_has_four_tries_and_hold():
    r = np.zeros(80, np.uint8)
    _, n, _ = T.replay_alert("P0", r, 10, rng(), 0.3)
    assert n == 4
    r2 = np.array([0, 0, 0, 1] + [1] * 60, np.uint8)
    t, n2, _ = T.replay_alert("P0", r2, 0, rng(), 0.0)
    assert n2 == 4 and math.isinf(t)  # the fourth attempt would end after 10 s


def test_late_reception_is_not_delivery():
    r = np.array([0, 0, 0, 0, 1] + [1] * 60, np.uint8)
    t, _, _ = T.replay_alert("P1", r, 0, rng(), 0.0)
    assert math.isinf(t)  # P1 holds 5 s: attempts 1 to 4 fill the time to 10 s


def test_deterministic():
    r = (np.random.default_rng(3).random(80) < 0.5).astype(np.uint8)
    a = [T.replay_alert(p, r, 20, random.Random(5), 0.4) for p in T.POLICIES]
    b = [T.replay_alert(p, r, 20, random.Random(5), 0.4) for p in T.POLICIES]
    assert a == b


def test_r3_event_accounting():
    r = np.ones(80, np.uint8)
    o = T.r3_event(r, 10, (True, True, 1, 0.2), 0.0, rng())
    assert o["two_d"] == 1 and o["single_d"] == 1 and o["diff"] == pytest.approx((T.FINAL_S + T.COMPUTE3 + T.A_AL) - (0.2 + T.COMPUTE3 + T.A_FL))
    o2 = T.r3_event(r, 10, (True, False, 0, 0.2), 0.0, rng())  # retracted false alarm: flash plus three CANCEL sends
    assert o2["two_air"] == pytest.approx(T.A_FL * 1 + 3 * T.A_FL) and o2["n_cr"] == 0
