"""Round 7b: the layered enumeration, the four-event reserve in the engine, and the power arithmetic."""
from crashguard import r7_engine as E
from crashguard import r7b_formal as F


def test_reserve_grows_with_events():
    a = [E.Spec(True, True, 0.1, 7, "reserved", 4, n_res=n).reserve() for n in (1, 2, 3, 4)]
    assert a == sorted(a) and a[3] - a[0] == 3 * 4 * E.air(97, 7) or abs((a[3] - a[0]) - 3 * 4 * E.air(97, 7)) < 1e-9


def test_formal_small_bound_properties():
    F.NMAX = 3
    for m in (1, 4):
        r = F.cell((44, m, "H", "reserved"))
        for n in range(4):
            assert r["by_n"][n]["inv1"] == 0
            assert r["by_n"][n]["inv2_conditional"] == 0
    r4 = F.cell((44, 4, "H", "reserved"))
    assert all(r4["by_n"][n]["inv2_unconditional"] == 0 for n in range(4))


def test_formal_old_policy_is_the_control_under_off_time():
    F.NMAX = 2
    r = F.cell((0, 0, "T", "old"))
    assert r["by_n"][0]["inv2_unconditional"] > 0


def test_layered_counts_match_flat_count_for_one_earlier_event():
    # one earlier confirm event: 16 ACK patterns x 1 gap (first event) x target (2 kinds, gap 0 or 2, 16 or 4 patterns)
    F.NMAX = 1
    r = F.cell((40, 1, "H", "reserved"))
    assert r["by_n"][1]["runs"] == 16 * (2 * 16 + 2 * 4) * 1 * 1 * 1 or r["by_n"][1]["runs"] == 16 * 2 * (16 + 4)


def test_power_arithmetic():
    from crashguard.r7b_g0 import SF_STEP_DB

    assert abs(4.0 / SF_STEP_DB - 1.4286) < 1e-3
