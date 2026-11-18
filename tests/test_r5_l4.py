"""Tests of the L4 module (V16 section 6): analytical planner, statistics, file handling; plus a known-answer test of the ns-3 application when WSL and the built binary are available."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from crashguard import lora
from crashguard import r5_l4 as L

ROOT = Path(__file__).resolve().parents[1]


def test_constants_follow_v16():
    assert L.RADII == (1000, 1500, 2000, 2500, 3000) and L.LOSSES == (0.0, 0.1, 0.3) and set(L.SETTINGS) == {"calib", "shipped"}
    assert len(L.cells()) == 30 and (L.EDGE_LO, L.EDGE_HI) == (0.30, 0.95)
    assert list(L.DEV_SEEDS) == list(range(401, 421)) and list(L.HELD_SEEDS) == list(range(501, 541))
    assert (L.DEADLINE_S, L.T_FIRST, L.RX_S, L.MAX_TRIES, L.ALERT_LEN) == (10.0, 0.35, 0.32, 12, 97)
    assert len(L.ITERATIONS) <= 5 and L.ITERATIONS[0] == L.L4Params() and L.L4Params().err == 2.0
    assert {it.k for it in L.ITERATIONS} <= {1, 2, 3} and {it.m0 for it in L.ITERATIONS} <= {0.0, 3.0, 6.0}


def test_airtime_matches_the_repository_formula_and_grows_with_sf():
    assert L.air_s(7) == pytest.approx(lora.airtime_ms(97, 7) / 1000.0)
    a = [L.air_s(s) for s in range(7, 13)]
    assert all(y > x for x, y in zip(a, a[1:])) and 0.1 < a[0] < 0.3


def test_sf_at_round_steps_every_k_rounds_and_caps():
    assert [L.sf_at_round(7, 2, r) for r in range(6)] == [7, 7, 8, 8, 9, 9]
    assert [L.sf_at_round(7, 1, r) for r in range(4)] == [7, 8, 9, 10]
    assert L.sf_at_round(11, 1, 5) == 12 and L.sf_at_round(7, 3, 2) == 7 and L.sf_at_round(7, 3, 3) == 8


def test_schedule_respects_deadline_tries_and_budget():
    for s0 in range(7, 13):
        for k in (1, 2, 3, 99):
            sch = L.attempt_schedule(s0, k)
            assert len(sch) <= 12
            for t, sf in sch:
                assert t + L.air_s(sf) <= 10.0 + 1e-9
            ts = [t for t, _ in sch]
            assert all(b > a for a, b in zip(ts, ts[1:]))
            for (t0, sf0), (t1, _sf1) in zip(sch, sch[1:]):
                assert t1 - t0 == pytest.approx(L.air_s(sf0) + 0.32)
    assert L.attempt_schedule(7, 99)[0][0] == pytest.approx(0.35)
    assert len(L.attempt_schedule(7, 99)) == 12  # twelve attempts of SF7 fit in 10 s
    assert len(L.attempt_schedule(12, 99)) < 12
    # the airtime budget cuts the schedule
    full = L.attempt_schedule(7, 99)
    cut = L.attempt_schedule(7, 99, limit_air_s=3 * L.air_s(7) + 1e-6)
    assert len(cut) == 3 and cut == full[:3]
    # an attempt that would end after the deadline is not planned
    assert L.attempt_schedule(12, 99, deadline=0.35 + L.air_s(12) - 1e-6) == []
    assert len(L.attempt_schedule(12, 99, deadline=0.35 + L.air_s(12) + 1e-6)) == 1


def test_uplink_success_monotone_and_loss_scaling():
    s = [L.uplink_success(m, 0.0, 7) for m in (-10, -4, 0, 4, 10)]
    assert all(b > a for a, b in zip(s, s[1:])) and s[0] < 0.01 and s[-1] > 0.99
    assert L.uplink_success(0.0, 0.0, 7) == pytest.approx(0.5)
    assert L.uplink_success(2.0, 0.0, 7) == pytest.approx(0.8413447, abs=1e-6)  # one sigma of fading
    assert L.uplink_success(20.0, 0.3, 7) == pytest.approx(0.7, abs=1e-6)
    assert L.uplink_success(20.0, 0.3, 9) == pytest.approx(1 - 0.3 * 0.49, abs=1e-6)  # 0.7 per step above the base
    assert L.uplink_success(0.0, 0.0, 8) == pytest.approx(L.phi(3.0 / 2.0))  # one step gains 3 dB of sensitivity
    assert L.uplink_success(-3.0, 0.1, 8) < L.uplink_success(-3.0, 0.0, 8)


def test_expected_delivery_properties():
    assert L.expected_delivery(-30.0, 0.0, 7, 99) < 1e-6 and L.expected_delivery(30.0, 0.0, 7, 99) > 1 - 1e-9
    m = [L.expected_delivery(x, 0.1, 7, 2) for x in (-8, -4, 0, 4)]
    assert all(b >= a for a, b in zip(m, m[1:]))
    assert L.expected_delivery(-6.0, 0.0, 7, 1) > L.expected_delivery(-6.0, 0.0, 7, 99)  # stepping up helps a weak link
    one = L.uplink_success(0.0, 0.0, 7)
    assert L.expected_delivery(0.0, 0.0, 7, 99, max_tries=1) == pytest.approx(one)
    assert L.expected_delivery(0.0, 0.0, 7, 99, max_tries=2) == pytest.approx(1 - (1 - one) ** 2)


def test_plan_is_the_brute_force_optimum_with_stated_tie_breaks():
    for m in (-9.0, -4.0, 0.0, 3.0, 8.0):
        s0, k, e = L.plan(m, 0.1)
        for a in range(7, 13):
            for kk in (1, 2, 3):
                assert L.expected_delivery(m, 0.1, a, kk) <= e + 1e-9
    s0, k, e = L.plan(30.0, 0.0)  # everything is certain: the lower start SF and the smaller k win
    assert (s0, k) == (7, 1) and e > 1 - 1e-9
    s0, _k, _e = L.plan(-12.0, 0.0)
    assert s0 > 7  # a weak link starts higher


def test_start_sf_rule_is_monotone_and_inclusive():
    ms = np.linspace(-20, 12, 33)
    sfs = [L.start_sf_from_margin(m, 3.0) for m in ms]
    assert all(b <= a for a, b in zip(sfs, sfs[1:]))
    assert L.start_sf_from_margin(3.0, 3.0) == 7 and L.start_sf_from_margin(2.999, 3.0) == 8  # 3 dB gained at SF8
    assert L.start_sf_from_margin(-100.0, 3.0) == 12 and L.start_sf_from_margin(50.0, 3.0) == 7
    assert L.start_sf_from_margin(0.0, 6.0) == 9  # needs 6 dB: SF9 gains 6


def test_args_and_file_names():
    a = L.args_for(2000, 1, 0.1, "l4", 405, L.L4Params(k=3, m0=6.0))
    assert "--policy=l4" in a and "--l4k=3" in a and "--l4m0=6" in a and "--l4err=2" in a and "--radius=2000" in a and "--sf=7" in a and "--sensShipped=1" in a and "--seed=405" in a
    z = L.args_for(2000, 0, 0.0, "z0", 1, None)
    assert "--l4k" not in z and "--policy=z0" in z and "--p=0" in z
    assert L.fname(Path("x"), 1500, "calib", 0.3, "z0", 7).name == "r1500_calib_p0.3_z0_7.txt"


def _write(p: Path, delays, inv=(0, 0), dropped=0):
    lines = [f"EV {i} {i * 10.0:.3f} {d:.6f} 0" for i, d in enumerate(delays)] + [f"L4INV {inv[0]} {inv[1]}", "DUTY 1.0 36.0", f"DROPPED {dropped}"]
    p.write_text("\n".join(lines) + "\n")


def test_load_run_parses_delays_and_invariants(tmp_path):
    f = tmp_path / "a.txt"
    _write(f, [1.0, 9.99, 10.0, 10.01, -1.0, -2.0], inv=(0, 2), dropped=1)
    r = L.load_run(f)
    assert r["n"] == 5 and r["deliv"] == pytest.approx(3 / 5) and r["inv"] == (0, 2) and r["dropped"] == 1
    f2 = tmp_path / "duty.txt"
    _write(f2, [1.0])
    f2.write_text(f2.read_text().replace("DUTY 1.0 36.0", "DUTY 36.5 36.0"))
    assert L.load_run(f2)["inv"] == (0, 1)  # the PHY-level duty maximum above the limit counts as a violation
    (tmp_path / "e.txt").write_text("")
    assert L.load_run(tmp_path / "e.txt") is None and L.load_run(tmp_path / "missing.txt") is None
    _write(tmp_path / "all_dropped.txt", [-2.0, -2.0])
    assert L.load_run(tmp_path / "all_dropped.txt") is None


def test_cell_runs_drop_a_crashed_run_for_every_policy(tmp_path):
    for s in (1, 2, 3):
        _write(L.fname(tmp_path, 1000, "calib", 0.0, "z0", s), [1.0, -1.0])
        _write(L.fname(tmp_path, 1000, "calib", 0.0, "l4", s), [1.0, 2.0])
    L.fname(tmp_path, 1000, "calib", 0.0, "l4", 2).write_text("")  # an ns-3 crash
    cr = L.cell_runs(tmp_path, 1000, "calib", 0.0, ("z0", "l4"), range(1, 4))
    assert cr["seeds"] == [1, 3] and cr["n_dropped"] == 1 and list(cr["z0"]) == [0.5, 0.5] and list(cr["l4"]) == [1.0, 1.0]


def test_paired_bootstrap_and_pooled_edge_bootstrap():
    d = np.full(40, 0.05) + np.random.default_rng(0).normal(0, 0.01, 40)
    r = L.paired_boot_mean(d)
    assert r["pt"] == pytest.approx(d.mean()) and 0.04 < r["lo"] < r["pt"] - 0.0005 and r["hi"] > r["pt"] + 0.0005 and r["p"] < 0.01 and r["n"] == 40
    z = L.paired_boot_mean(np.zeros(40))
    assert z["pt"] == 0 and z["p"] > 0.99
    cells = {("a",): d + 0.02, ("b",): d + 0.01, ("c",): d - 0.03}
    p = L.pooled_edge_boot(cells)
    assert p["pt"] == pytest.approx(d.mean())
    dn = d.copy()
    dn[3] = np.nan  # a dropped run in one cell is ignored in that cell only
    pn = L.pooled_edge_boot({("a",): dn + 0.02, ("b",): d + 0.01, ("c",): d - 0.03})
    assert pn["n_runs"] == 40 and pn["pt"] == pytest.approx((np.nanmean(dn + 0.02) + (d + 0.01).mean() + (d - 0.03).mean()) / 3) and p["n_cells"] == 3 and p["n_runs"] == 40 and p["lo"] < p["pt"] < p["hi"]
    neg = L.pooled_edge_boot({("a",): -d})
    assert neg["pt"] < 0 and neg["p"] > 0.99


def test_edge_cell_rule():
    z0 = {(1000, "calib", 0.0): 0.99, (1500, "calib", 0.0): 0.95, (2000, "calib", 0.0): 0.30, (2500, "calib", 0.0): 0.2999, (3000, "calib", 0.0): 0.5}
    assert set(L.edge_cells(z0)) == {(1500, "calib", 0.0), (2000, "calib", 0.0), (3000, "calib", 0.0)}


BIN = Path.home() / "ns3work"  # only a hint; the real check runs inside WSL


def _wsl_ok() -> bool:
    if not shutil.which("wsl"):
        return False
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-lc", "test -x ~/ns3work/ns-3-dev/build/scratch/ns3.48-xsim_alert-optimized && echo yes"], capture_output=True, text=True, timeout=60)
        return "yes" in r.stdout
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _wsl_ok(), reason="WSL or the ns-3 binary is not available")
def test_ns3_l4_without_stepping_equals_z0_and_invariants_hold(tmp_path):
    """Known answer for the C++ change: the ladder with a start margin of -100 dB (always SF7) and k = 1000 (never steps) gives the output of Z0 byte for byte; the invariants print zero."""
    script = tmp_path / "t.sh"
    base = "--n=60 --sf=7 --p=0.1 --radius=2000 --rate=10 --duty=0.01 --seed=3 --sensShipped=1"
    script.write_text(
        "cd ~/ns3work/ns-3-dev\nB=./build/scratch/ns3.48-xsim_alert-optimized\n"
        f"$B {base} --policy=z0 | md5sum\n$B {base} --policy=l4 --l4k=1000 --l4m0=-100 | md5sum\n"
        f"$B {base} --policy=z0 | grep -c EV\n$B {base} --policy=l4 --l4k=1 --l4m0=3 | grep L4INV\n",
        newline="\n",
    )
    p = str(script.resolve()).replace("\\", "/")
    p = "/mnt/" + p[0].lower() + p[2:]
    r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", p], capture_output=True, text=True, timeout=300)
    out = r.stdout.strip().splitlines()
    assert out[0].split()[0] == out[1].split()[0]
    assert int(out[2]) > 100 and out[3].split() == ["L4INV", "0", "0"]
