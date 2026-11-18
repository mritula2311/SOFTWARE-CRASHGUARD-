"""Tests of the L8 module (V16 section 15.4)."""
from __future__ import annotations


from crashguard import r5_l8 as L


def test_constants_follow_s2():
    assert (L.R_HC, L.HORIZON, L.QUAR_GAP, L.MAX_PER_SLOT, L.STRIKES_TO_QUARANTINE) == (6, 60, 10, 4, 2) and L.KINDS == ("ok", "implausible", "repeat")
    assert len(L.patterns()) == 1 + 3 + 9 + 27 + 81


def test_process_plausible_alerts_are_forwarded_up_to_r_then_rate_limited():
    s = L.initial()
    for slot in range(6):
        s, cls = L.process(s, slot, "ok")
        assert cls == "high"
    assert s[0] == 6
    s, cls = L.process(s, 6, "ok")
    assert cls == "low" and s[2] == 1 and s[0] == 6 and not s[3]  # over the rate: a strike, forwarded as low confidence
    s, cls = L.process(s, 7, "ok")
    assert cls == "low" and s[3]  # the second strike puts the vehicle in quarantine
    s2, cls = L.process(s, 8, "ok")
    assert cls == "drop" or cls == "low"


def test_spacing_one_high_confidence_forward_per_slot():
    s, c1 = L.process(L.initial(), 5, "ok")
    s, c2 = L.process(s, 5, "ok")
    assert (c1, c2) == ("high", "low") and s[2] == 1
    s, c3 = L.process(s, 6, "ok")
    assert c3 == "high"


def test_implausible_and_repeat_alerts_are_strikes_not_high():
    for kind in ("implausible", "repeat"):
        s, cls = L.process(L.initial(), 3, kind)
        assert cls == "low" and s[0] == 0 and s[2] == 1 and not s[3]
        s, cls = L.process(s, 4, kind)
        assert cls == "low" and s[3]


def test_quarantine_forwards_one_low_confidence_alert_per_ten_slots_and_never_high():
    s = (0, -1, 2, True, -1)
    s, c1 = L.process(s, 20, "ok")
    assert c1 == "low" and s[4] == 20
    s, c2 = L.process(s, 25, "ok")
    assert c2 == "drop" and s[4] == 20
    s, c3 = L.process(s, 30, "ok")
    assert c3 == "low" and s[4] == 30
    s, c4 = L.process(s, 29 + 1, "ok")
    assert c4 == "drop"
    assert s[0] == 0  # no high-confidence forward in quarantine
    s9, c9 = L.process((0, -1, 2, True, 20), 29, "ok")
    assert c9 == "drop"


def test_explore_bound_is_tight_and_horizon_dependent():
    r = L.explore(horizon=60, max_per_slot=1)
    assert r["max_high"] == 6
    assert L.explore(horizon=3, max_per_slot=2)["max_high"] == 3  # three slots: at most three forwards
    assert L.explore(horizon=1, max_per_slot=4)["max_high"] == 1  # one slot: spacing gives one
    r2 = L.explore(horizon=12, max_per_slot=3)
    assert r2["max_high"] == 6 and r2["max_low"] >= 2 and r2["horizon"] == 12 and r2["patterns_per_slot"] == 40


def test_explore_full_model_respects_r():
    r = L.explore(horizon=24, max_per_slot=4)
    assert r["max_high"] <= L.R_HC and r["max_high"] == 6


def test_legit_vehicles_without_alerts_are_never_quarantined_and_rate_matters():
    z = L.legit_quarantined(0.0, 200)
    assert z["n_alerts"] == 0 and z["quarantined"] == 0 and z["with_strike"] == 0
    a = L.legit_quarantined(0.5, 3000)
    b = L.legit_quarantined(8.0, 3000)
    assert b["quarantined"] > a["quarantined"] and b["with_strike"] > a["with_strike"] and abs(a["n_alerts"] / 3000 - 0.5) < 0.1
    assert L.legit_quarantined(2.0, 500, seed=1) != L.legit_quarantined(2.0, 500, seed=2) and L.legit_quarantined(2.0, 500) == L.legit_quarantined(2.0, 500)
    assert 0 <= b["not_high"] <= b["n_alerts"]


def test_regression_values():
    r = L.explore(horizon=12, max_per_slot=3)
    assert (r["max_high"], r["max_low"], r["states_visited"]) == (6, 4, 2266)
    assert L.legit_quarantined(8.0, 50) == dict(n_alerts=422, vehicle_hours=50, quarantined=34, with_strike=43, not_high=148)
    assert L.legit_quarantined(3.0, 300) == dict(n_alerts=896, vehicle_hours=300, quarantined=7, with_strike=27, not_high=43)
