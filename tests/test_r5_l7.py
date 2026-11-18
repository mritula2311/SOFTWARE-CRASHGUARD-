"""Tests of the L7 module (V16 section 15.3): the synchronisation model, the exhaustive enumeration and the Tamarin output reader."""
from __future__ import annotations


from crashguard import r5_l7 as L


def test_constants_follow_s2():
    assert (L.W, L.MAX_LEN, L.MAX_BOOTS) == (8, 10, 3) and L.EVENTS == ("L", "A", "K", "B")


def test_step_semantics():
    assert L.step(1, 1, "L") == (1, 1, None) and L.step(1, 1, "B") == (2, 1, None)
    assert L.step(1, 1, "A") == (2, 1, True) and L.step(1, 1, "K") == (1, 1, True)
    assert L.step(9, 1, "A") == (10, 9, True)  # gap 8: the edge of the window
    assert L.step(10, 1, "A") == (10, 1, False) and L.step(10, 1, "K") == (10, 1, False)  # gap 9: rejected, nothing changes
    assert L.step(5, 2, "A", w=3) == (6, 5, True) and L.step(6, 2, "A", w=3) == (6, 2, False)


def test_a_lost_ack_does_not_desynchronise():
    r = L.run_sequence(("K",) * 10)
    assert r["gap"] == 0 and r["next_ok"] and all(r["accepted"])
    r = L.run_sequence(("A", "K", "A", "L", "K"))
    assert r["next_ok"] and r["gap"] <= 1


def test_boots_open_a_gap_up_to_the_window():
    assert L.run_sequence(("B",) * 3)["next_ok"] and L.run_sequence(("B",) * 7)["next_ok"]  # gap 7
    assert L.run_sequence(("B",) * 7)["gap"] == 7 and L.run_sequence(("B",) * 8)["gap"] == 8 and L.run_sequence(("B",) * 8)["next_ok"]
    assert not L.run_sequence(("B",) * 9)["next_ok"]
    r = L.run_sequence(("B",) * 9 + ("A",))
    assert r["accepted"] == [False] and r["gap"] == 9  # stays out of sync: the window is the bound
    r = L.run_sequence(("B", "B", "A", "B", "A"))
    assert r["accepted"] == [True, True] and r["gap"] == 1


def test_enumeration_has_no_violation_and_is_not_vacuous():
    e = L.enumerate_all(max_len=8)
    assert e["n_sequences"] == sum(4**k for k in range(9)) and all(v == 0 for v in e["violations"].values())
    assert e["n_gap_above_window"] == 0 and e["n_with_le_max_boots"] > 0  # a gap of 9 needs 9 boots, so no sequence of length 8 exceeds the window
    assert L.enumerate_all(max_len=10)["n_gap_above_window"] > 0


def test_enumeration_detects_a_broken_window():
    # with a window of 2 and up to 3 boots the claim 'the next alert is accepted' must show violations
    e = L.enumerate_all(w=2, max_len=6, max_boots=3)
    assert e["violations"]["next_ok_with_few_boots"] > 0 and e["n_gap_above_window"] > 0


def test_cost_values():
    c = L.cost()
    assert c["hash_per_ack"] == 1 and c["hash_resync_max"] == 8 and c["bytes_added_to_frames"] == 0 and c["car_state_bytes"] == 36


def test_tamarin_status_reader(tmp_path, monkeypatch):
    d = tmp_path / "formal" / "out" / "ratchet"
    d.mkdir(parents=True)
    (d / "executable.txt").write_text("  executable (exists-trace): verified (9 steps)\nexit code: 0")
    (d / "forward_secrecy.txt").write_text("exit code: 124 ; wall time 500 s")
    (d / "authenticity.txt").write_text("WARNING: 1 wellformedness check failed\n  authenticity (all-traces): verified (4 steps)")
    (d / "ack_binding.txt").write_text("  ack_binding (all-traces): falsified - found trace (8 steps)")
    monkeypatch.setattr(L, "ROOT", tmp_path)
    st = L.tamarin_status("ratchet")
    assert st == {"executable": "verified", "forward_secrecy": "timeout", "authenticity": "wellformedness_failed:verified", "ack_binding": "falsified"}
    (d / "executable.txt").unlink()
    assert L.tamarin_status("ratchet")["executable"] == "NOT_RUN"


def test_enumeration_regression_values_for_a_small_window():
    e = L.enumerate_all(w=2, max_len=3, max_boots=3)
    assert e["n_sequences"] == 85 and e["n_gap_above_window"] == 2 and e["violations"]["next_ok_with_few_boots"] == 2
    e2 = L.enumerate_all(w=2, max_len=3, max_boots=2)
    assert e2["violations"]["next_ok_with_few_boots"] == 1 and e2["n_with_le_max_boots"] < 85  # with two boots after an acknowledged alert the gap is already 3


def test_the_checks_catch_a_broken_step(monkeypatch):
    real = L.step

    def boot_twice(c, b, ev, w=L.W):
        return (c + 2, b, None) if ev == "B" else real(c, b, ev, w)

    def base_ahead(c, b, ev, w=L.W):
        c2, b2, a = real(c, b, ev, w)
        return (c2, b2 + 1, a) if a else (c2, b2, a)

    def wide_window(c, b, ev, w=L.W):
        return real(c, b, ev, w + 1)

    monkeypatch.setattr(L, "step", boot_twice)
    assert L.enumerate_all(max_len=4)["violations"]["gap_bound"] > 0
    monkeypatch.setattr(L, "step", base_ahead)
    assert L.enumerate_all(max_len=3)["violations"]["base_ahead"] > 0
    monkeypatch.setattr(L, "step", wide_window)
    assert L.enumerate_all(w=2, max_len=4)["violations"]["accept_iff_window"] > 0
