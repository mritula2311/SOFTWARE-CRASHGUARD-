"""Tests of the L11 module (V16 sections 15.7 and 15.9). Synthetic right-handed drives; no VZCrash data is read."""
from __future__ import annotations

import numpy as np
import pytest

from crashguard import r5_l11 as L

P = L.L11Params()


def drive(seed=0, noise=0.0, turn=0.3, accel=0.8, n=1600, left=True):
    """Right-handed vehicle frame (x forward, y left, z up): a_h = dv/dt f + v w (z x f) = (dv/dt, v w, 0)."""
    rng = np.random.default_rng(seed)
    k = 16
    t_g = np.arange(k) * (n / 100) / k
    prof = lambda tt: 10.0 + accel * np.minimum(tt, 3.0) - accel * np.maximum(tt - 13.0, 0.0)  # noqa: E731  accelerate 0-3 s, cruise, brake after 13 s
    gps = prof(t_g) * 3.6
    v = L.speed_series(gps, n)
    t = np.arange(n) / 100
    w = np.where((t > 4) & (t < 10), turn if left else -turn, 0.0)
    a_long = np.gradient(v, 0.01)
    acc = np.stack([a_long / L.G, v * w / L.G, np.ones(n)], axis=1) + rng.normal(0, noise, (n, 3))
    gyro = np.stack([np.zeros(n), np.zeros(n), np.degrees(w)], axis=1) + rng.normal(0, noise * 20, (n, 3))
    return acc, gyro, gps


def test_constants_follow_s2():
    assert (L.N_SEG, L.N_VALID) == (100, 20) and L.LOOSE.w_min == 5.0 and L.LOOSE.v_min == 5.0 and L.LOOSE.a_long == 0.3
    d = L.L11Params()
    assert (d.w_min, d.v_min, d.a_long, d.theta, d.s0) == (10.0, 5.0, 0.3, 0.0, 1.0) and len(L.ITERATIONS) <= 5 and L.ITERATIONS[0] == d


def test_hashed_halves_and_order():
    h = [L.half_l11(i) for i in range(4000)]
    assert 0.46 < np.mean(h) < 0.54 and h == [L.half_l11(i) for i in range(4000)]
    assert L.order_key(5) != L.order_key(6) and L.order_key(5) == L.order_key(5)
    assert L.half_l11(7) == int(__import__("hashlib").sha256(b"l11|7").hexdigest(), 16) % 2


def test_speed_series_interpolation_and_missing():
    v = L.speed_series(np.array([36.0, 72.0, 108.0, 144.0]), 400)  # 4 samples over 4 s: 10, 20, 30, 40 m/s at 0, 1, 2, 3 s
    assert v[0] == pytest.approx(10.0) and v[100] == pytest.approx(20.0) and v[150] == pytest.approx(25.0) and len(v) == 400
    assert L.speed_series(np.array([5.0]), 400) is None and L.speed_series(np.array([5.0, np.nan]), 400) is None


def test_known_answer_right_handed_turn_agreement_is_one():
    for left in (True, False):
        a = L.event_agreement(*drive(left=left), P)
        assert a == pytest.approx(1.0, abs=0.02)


def test_agreement_is_rotation_invariant():
    acc, gyro, gps = drive()
    base = L.event_agreement(acc, gyro, gps, P)
    for name in ("yaw90", "yaw180", "tilt25x", "rot180x"):
        a, g = L.transform(acc, gyro, name)
        assert L.event_agreement(a, g, gps, P) == pytest.approx(base, abs=0.02), name
    rng = np.random.default_rng(0)
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    q = q * np.sign(np.linalg.det(q))
    assert L.event_agreement(acc @ q.T, gyro @ q.T, gps, P) == pytest.approx(base, abs=0.02)


def test_mirror_flips_change_the_sign_and_flipping_twice_returns():
    acc, gyro, gps = drive()
    for name in ("mirror_x", "mirror_y", "mirror_z", "acc_only_x", "acc_only_y"):
        a, g = L.transform(acc, gyro, name)
        assert L.event_agreement(a, g, gps, P) == pytest.approx(-1.0, abs=0.02), name
    a, g = L.transform(*L.transform(acc, gyro, "mirror_y"), "mirror_y")
    assert np.allclose(a, acc) and np.allclose(g, gyro)
    a, g = L.transform(*L.transform(acc, gyro, "acc_only_x"), "acc_only_x")
    assert np.allclose(a, acc)


def test_expected_blind_spots_are_not_detected():
    acc, gyro, gps = drive()
    for name in ("acc_only_z", "gyro_only_x", "gyro_only_y"):
        a, g = L.transform(acc, gyro, name)
        assert L.event_agreement(a, g, gps, P) == pytest.approx(1.0, abs=0.05), name
    a, g = L.transform(acc, gyro, "gyro_only_z")
    assert L.event_agreement(a, g, gps, P) == pytest.approx(-1.0, abs=0.02)


def test_an_unflipped_frame_is_never_declared_flipped_by_a_single_turn():
    for seed in range(20):
        acc, gyro, gps = drive(seed, noise=0.01, turn=np.random.default_rng(seed).uniform(0.15, 0.5), left=bool(seed % 2))
        a = L.event_agreement(acc, gyro, gps, P)
        assert a is not None and L.installation_decision([a], P, n=1) is False
        a2, g2 = L.transform(acc, gyro, "mirror_x")
        assert L.installation_decision([L.event_agreement(a2, g2, gps, P)], P, n=1) is True


def test_validity_requirements():
    acc, gyro, gps = drive()
    assert L.event_agreement(acc, gyro, gps, P) is not None
    assert L.event_agreement(acc, gyro, np.array([30.0]), P) is None  # no GPS
    flat = drive(turn=0.0)
    assert L.event_agreement(*flat, P) is None  # no turn
    cruise = drive(accel=0.0)
    assert L.event_agreement(*cruise, P) is None  # no longitudinal change
    assert L.event_agreement(acc, gyro, gps, L.L11Params(w_min=40.0)) is None  # the turn is below the threshold (17 deg/s)
    assert L.event_agreement(acc, gyro, gps, L.L11Params(v_min=30.0)) is None
    assert L.event_agreement(acc, gyro, gps, L.L11Params(a_long=1.0)) is None
    short = drive(n=150)
    assert L.event_agreement(*short, P) is None
    assert L.event_agreement(acc * 0.1, gyro, gps, P) is None  # no gravity
    # a 99-sample turn is too short, a 101-sample turn is valid
    a2, g2, p2 = drive()
    t = np.arange(1600) / 100
    g2[:, 2] = np.where((t > 4) & (t <= 4.99), np.degrees(0.3), 0.0)
    assert L.event_agreement(a2, g2, p2, P) is None
    g2[:, 2] = np.where((t > 4) & (t <= 5.02), np.degrees(0.3), 0.0)
    assert L.event_agreement(a2, g2, p2, P) is not None


def test_installation_decision_rules():
    assert L.installation_decision([0.9] * 20, P) is False and L.installation_decision([-0.9] * 20, P) is True
    assert L.installation_decision([0.9] * 19, P) is None and L.installation_decision([None, 0.9] * 20, P) is False  # skips None, uses the first 20 valid
    mixed = [1.0] * 10 + [-1.0] * 10
    assert L.installation_decision(mixed, P) is False  # mean 0 is not below theta 0
    assert L.installation_decision([-0.05] * 20, L.L11Params(theta=-0.1)) is False and L.installation_decision([-0.05] * 20, L.L11Params(theta=0.1)) is True
    assert L.installation_decision([0.9] * 20, L.L11Params(s0=-1.0)) is True  # reference sign flips the meaning
    long = [0.9] * 20 + [-1.0] * 100
    assert L.installation_decision(long, P) is False  # only the first 20 count


def test_groups_are_disjoint_ordered_and_capped():
    g = L.groups_of(list(range(1000)))
    assert len(g) == 50 and all(len(x) == 20 for x in g) and len({i for x in g for i in x}) == 1000
    assert [i for x in g for i in x] == sorted(range(1000), key=L.order_key)
    assert len(L.groups_of(list(range(5000)))) == 100 and len(L.groups_of(list(range(19)))) == 0 and len(L.groups_of(list(range(39)))) == 1


def test_exact_binomial_helpers():
    assert L.exact_binom_p_greater(100, 100, 0.95) == pytest.approx(0.95**100)
    assert L.exact_binom_p_greater(95, 100, 0.95) > 0.5
    assert L.exact_upper(0, 100) == pytest.approx(1 - 0.05 ** (1 / 100), abs=1e-6) and L.exact_upper(5, 5) == 1.0


def _events(n=60, seed=0):
    ev = {}
    for i in range(n):
        acc, gyro, gps = drive(seed + i, noise=0.01, turn=0.2 + 0.01 * (i % 10), left=bool(i % 2))
        ev[i] = dict(id=i, acc=acc.astype(np.float32), gyro=gyro.astype(np.float32), gps=gps.astype(np.float32))
    return ev


def test_evaluate_and_rates_on_synthetic_events():
    ev = _events(60)
    res = L.evaluate(ev, P)
    assert res["n_valid"] == 60 and res["n_groups"] == 3
    r = L.rates(res)
    assert r["false_detection"] == 0.0 and r["n_unflipped"] == 15
    for nm, s in r["sens"].items():
        if L.TRANSFORMS[nm][2] == "criterion":
            assert s == 1.0, nm
    assert r["sens"]["acc_only_z"] == 0.0 and r["sens"]["gyro_only_x"] == 0.0
    assert L.score(r) == pytest.approx(1.0)
    s0, med = L.reference_sign(ev, P)
    assert s0 == 1.0 and med == pytest.approx(1.0, abs=0.05)
    flipped = {i: dict(e, acc=L.transform(e["acc"].astype(float), e["gyro"].astype(float), "mirror_x")[0].astype(np.float32)) for i, e in ev.items()}
    s0f, medf = L.reference_sign(flipped, P)
    assert s0f == -1.0 and medf == pytest.approx(1.0, abs=0.05)


def test_score_penalises_false_detection():
    base = dict(sens={"mirror_x": 0.9, "mirror_y": 1.0, "acc_only_z": 0.0}, false_detection=0.0)
    assert L.score(base) == pytest.approx(0.9)
    assert L.score(dict(base, false_detection=0.05)) == pytest.approx(0.4)
    assert L.score(dict(sens={"mirror_x": 1.0, "acc_only_z": 0.0}, false_detection=0.0)) == 1.0  # descriptive transformations are not in the score


def test_transform_table_matches_s2():
    crit = {n for n, v in L.TRANSFORMS.items() if v[2] == "criterion"}
    assert crit == {"mirror_x", "mirror_y", "mirror_z", "acc_only_x", "acc_only_y"}
    assert {n for n, v in L.TRANSFORMS.items() if v[2] == "unflipped"} == {"identity", "yaw90", "yaw180", "tilt25x", "rot180x"}
    for n, (Ma, Mg, _g) in L.TRANSFORMS.items():
        assert np.allclose(Ma @ Ma.T, np.eye(3)) and np.allclose(Mg @ Mg.T, np.eye(3))
        if L.TRANSFORMS[n][2] == "unflipped":
            assert np.linalg.det(Ma) == pytest.approx(1.0) and np.linalg.det(Mg) == pytest.approx(1.0)


def test_dominant_axis_and_up_along_x_blind_spot():
    acc, gyro, gps = drive()
    ev = {1: dict(acc=acc.astype(np.float32))}
    assert L.dominant_axis(ev, [1]) == "z"
    R = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]])  # a proper rotation that puts gravity on the x axis
    a2, g2 = acc @ R.T, gyro @ R.T
    assert L.dominant_axis({1: dict(acc=a2.astype(np.float32))}, [1]) == "x"
    assert L.event_agreement(a2, g2, gps, P) == pytest.approx(1.0, abs=0.03)
    # with up along x the accelerometer-only flip of x is the vertical flip: not detected; the flip of z becomes a lateral or longitudinal flip
    for name, want in (("acc_only_x", 1.0), ("acc_only_z", -1.0)):
        Ma = L.TRANSFORMS[name][0]
        assert L.event_agreement(a2 @ Ma.T, g2, gps, P) == pytest.approx(want, abs=0.05), name


def test_exact_upper_limit_uses_the_number_of_installations():
    assert L.exact_upper(0, 100) == pytest.approx(0.0295, abs=0.0005) and L.exact_upper(0, 500) < 0.0061
