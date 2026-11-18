"""Round 7 B1: pseudonym reference, resolver, collision formula."""
import random

import pytest

from crashguard import r7_pseudo as P


def test_pseudonym_is_prf_truncation_and_depends_on_boot_and_counter():
    k = bytes(range(32))
    a = P.pseudonym(k, 7, 9, 4)
    assert len(a) == 4 and a == P.pseudonym(k, 7, 9, 8)[:4]
    assert a != P.pseudonym(k, 7, 10, 4) and a != P.pseudonym(k, 8, 9, 4)
    assert a.hex() == P.pseudonym(k, 7, 9, 4).hex()


def test_resolver_accepts_in_window_rejects_replay_and_wrong_tag():
    rng = random.Random(1)
    keys = [rng.randbytes(32) for _ in range(20)]
    b = P.Base(keys, 16, 4)
    f = P.make_frame(keys[3], 1, 5, 4, b"x" * 8)
    assert b.resolve(f) == (3, 5)
    assert b.resolve(f) is None  # replay: the counter is not above the last accepted one
    f2 = P.make_frame(keys[3], 1, 6, 4, b"y" * 8)
    bad = f2[:-1] + bytes([f2[-1] ^ 1])
    assert b.resolve(bad) is None  # fails the tag: no state change
    assert b.resolve(f2) == (3, 6)
    far = P.make_frame(keys[3], 1, 6 + 17, 4, b"z" * 8)  # beyond the window: does not resolve
    assert b.resolve(far) is None


def test_resync_after_reboot_uses_the_next_boot_value():
    rng = random.Random(2)
    keys = [rng.randbytes(32) for _ in range(10)]
    b = P.Base(keys, 16, 4)
    f = P.make_frame(keys[4], 2, 1, 4, b"r" * 8)  # the vehicle rebooted: boot 2, counter restarts
    assert b.resolve(f) is None
    assert b.resync(f) == (4, 1)
    f2 = P.make_frame(keys[4], 2, 2, 4, b"s" * 8)
    assert b.resolve(f2) == (4, 2)


def test_collision_formula_values():
    assert P.collision_probability(1000, 16, 2) == pytest.approx(0.2164327, rel=1e-5)
    assert P.collision_probability(1000, 16, 4) == pytest.approx(3.72156e-06, rel=1e-4)
    assert P.collision_probability(1000, 16, 5) < 1e-6
