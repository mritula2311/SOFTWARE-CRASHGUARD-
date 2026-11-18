"""Round 7: analytic bounds and the bounded enumeration (small bounds) behave as preregistered."""
import itertools

from crashguard import r7_analytic as AN
from crashguard import r7_formal as F


def test_n_star_and_reserve_limits_at_sf7():
    assert AN.n_star(7, 36.0) == 42 and AN.n_star(7, 360.0) == 418
    assert AN.n_h_limit(7, 36.0) == 52
    assert AN.n_first_fail(7, 36.0) == AN.n_star(7, 36.0)


def test_dmax_bounds():
    d = AN.d_max(7, "H1")
    assert abs(d["first"] - (AN.A(14, 7) + 0.32)) < 1e-12
    assert AN.d_max(9, "T10")["first"] == 0.0
    assert AN.d_max(8, "H1")["kth"] > AN.d_max(8, "H1")["first"]


def test_formal_control_violates_and_reserve_holds_on_a_sample():
    k, B = 1, 20
    viol_old = viol_res = 0
    for acks in itertools.product(*[(False, True)] * 3):
        ev = [(0, (acks[0], False), (acks[1],), "confirm"), (0, (False, False), (acks[2],), "confirm"), (0, (False, False), (False,), "confirm")]
        o = F.simulate("old", "H", B, k, ev)
        r = F.simulate("reserved", "H", B, k, ev)
        viol_old += int(o["delay"] > 2)
        assert r["inv1"]
        if r["intact"]:
            assert r["delay"] <= 2
        viol_res += int(r["intact"] and r["delay"] > 2)
    assert viol_res == 0


def test_off_time_model_reserved_never_late():
    for acks in itertools.product((False, True), repeat=2):
        ev = [(0, acks, (False,), "confirm")]
        assert F.simulate("reserved", "T", 16, 1, ev)["delay"] == 0
