"""X1: impact direction rule, sign convention and sectors (synthetic signals only)."""
import numpy as np
import pytest

from crashguard import direction as D


def test_sector_boundaries_and_wraparound():
    assert D.sector(0.0) == "front" and D.sector(44.9) == "front" and D.sector(-44.9) == "front"
    assert D.sector(90.0) == "left" and D.sector(-90.0) == "right"
    assert D.sector(180.0) == "rear" and D.sector(-170.0) == "rear" and D.sector(170.0) == "rear"


def test_the_impact_is_opposite_to_the_impulse():
    # the vehicle is pushed backwards (negative X): the impact came from the front
    assert D.theta_deg(-1.0, 0.0) == pytest.approx(0.0)
    # pushed to the right (negative Y, Y points left): the impact came from the left
    assert D.theta_deg(0.0, -1.0) == pytest.approx(90.0)
    # pushed forward: the impact came from behind
    assert abs(D.theta_deg(1.0, 0.0)) == pytest.approx(180.0)
    # pushed to the left: the impact came from the right
    assert D.theta_deg(0.0, 1.0) == pytest.approx(-90.0)


def _sig(ax, ay, fs0=1000.0, t_end=0.5):
    t = np.arange(0, t_end, 1.0 / fs0)
    acc = np.zeros((len(t), 3))
    pulse = (t > 0.1) & (t < 0.2)
    acc[pulse, 0], acc[pulse, 1] = ax, ay
    return dict(t=t, acc=acc, fs0=fs0)


def test_axis_convention_flags_the_data_signs():
    # frontal: deceleration (negative X) is already forward-positive; left-side: pushed to the right with Y pointing right in the data (positive) -> flip
    tests = [dict(kind="frontal", truth="front", sig=_sig(-10.0, 0.0)) for _ in range(3)] + [dict(kind="side", truth="side", sig=_sig(0.0, 8.0)) for _ in range(3)]
    conv = D.axis_convention(tests)
    assert conv["flip_x"] == 1 and conv["flip_y"] == -1
    tests2 = [dict(kind="frontal", truth="front", sig=_sig(10.0, 0.0)) for _ in range(3)] + [dict(kind="side", truth="side", sig=_sig(0.0, -8.0)) for _ in range(3)]
    conv2 = D.axis_convention(tests2)
    assert conv2["flip_x"] == -1 and conv2["flip_y"] == 1


def test_impulse_recovers_a_frontal_and_a_side_pulse():
    for ax, ay, truth in ((-12.0, 0.5, "front"), (0.5, 12.0, "side")):
        sig = _sig(ax, ay)
        j = D.impulse(sig, 64.0, 100, (1, -1 if truth == "side" else 1))
        pred = "front" if abs(j[0]) >= abs(j[1]) else "side"
        assert pred == truth


def test_split_groups_assigns_every_third_group_to_heldout():
    tests = [dict(test_no=i, g=f"g{i // 2}") for i in range(12)]
    role = D.split_groups(tests, "g")
    assert sorted(role.values()).count("heldout") == 2 and role["g2"] == "heldout" and role["g5"] == "heldout"
