"""Tests of the round-6 micro-confirm analysis (src/crashguard/r6_micro.py): pure statistics, the trace-driven micro event against the R3 event, and a known answer against the stored P1 results."""
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crashguard import r3_t1 as T
from crashguard import r6_micro as M

ROOT = Path(__file__).resolve().parents[1]


def frame(rows):
    """Run output with columns k, flash, alert, cancel, air, dropped and the event columns E, F, y."""
    d = pd.DataFrame(rows, columns=["k", "dropped", "flash", "alert", "cancel", "air", "E", "F", "y"])
    d["v"], d["t"], d["row"], d["tE"] = 0, 0.0, 0, 0.1
    return d


def test_two_stage_delivered_cases():
    cr = frame([
        (0, 0, -1, 1.0, 0, 1, 1, 1, 1),  # confirm arrived
        (1, 0, 0.5, -1, 1, 1, 1, 0, 1),  # flash arrived, but a cancel followed: not delivered
        (2, 0, 0.5, -1, 0, 1, 1, 0, 1),  # flash arrived, no cancel: delivered
        (3, 0, 0.5, -1, 1, 1, 1, 1, 1),  # flash arrived and the event was confirmed in the final stage: delivered
        (4, 0, -1, -1, 0, 1, 1, 1, 1),  # nothing arrived
        (5, 0, -1, -1, 0, 1, 0, 0, 1),  # nothing at all
    ])
    assert [M.two_stage_delivered(cr.iloc[[i]]) for i in range(len(cr))] == [1, 0, 1, 1, 0, 0]
    assert M.two_stage_delivered(frame([(0, 0, -1, 0.0, 0, 1, 1, 1, 1)])) == 1  # a confirm arrival at time 0 counts


def test_run_pair_stats_drops_events_dropped_in_any_run_and_counts_crash_events():
    s = frame([(0, 0, -1, 1.0, 0, 2.0, 1, 1, 1), (1, 0, -1, 1.0, 0, 2.0, 0, 1, 0), (2, 1, -1, 1.0, 0, 2.0, 1, 1, 1)])
    t = frame([(0, 0, 0.5, 1.0, 0, 3.0, 1, 1, 1), (1, 0, -1, 1.0, 0, 3.0, 0, 1, 0), (2, 0, 0.5, 1.0, 0, 3.0, 1, 1, 1)])
    m = frame([(0, 0, 0.5, 1.0, 0, 1.5, 1, 1, 1), (1, 0, -1, 1.0, 0, 1.5, 0, 1, 0), (2, 0, 0.5, 1.0, 0, 1.5, 1, 1, 1)])
    st = M.run_pair_stats(s, t, m)
    assert st["air_s"] == 4.0 and st["air_t"] == 6.0 and st["air_m"] == 3.0  # event 2 is dropped in s and removed from all three
    assert st["n_cr"] == 1 and st["del_t"] == 1 and st["del_m"] == 1
    assert st["n_drop"] == 1 and st["n_ev"] == 3


def test_run_pair_stats_delivery_differs_by_policy():
    s = frame([(0, 0, -1, 1.0, 0, 1.0, 1, 1, 1)])
    t = frame([(0, 0, 0.5, 1.0, 0, 1.0, 1, 1, 1)])
    m = frame([(0, 0, -1, -1, 0, 1.0, 1, 1, 1)])  # the micro scheme lost the event
    st = M.run_pair_stats(s, t, m)
    assert st["del_t"] == 1 and st["del_m"] == 0


def test_two_stage_delivery_has_a_10_second_limit():
    cr = frame([(0, 0, -1, 9.9, 0, 1, 1, 1, 1), (1, 0, -1, 10.1, 0, 1, 1, 1, 1), (2, 0, 10.5, -1, 0, 1, 1, 0, 1), (3, 0, 9.0, -1, 0, 1, 1, 0, 1)])
    assert [M.two_stage_delivered(cr.iloc[[i]]) for i in range(4)] == [1, 0, 0, 1]
    assert M.two_stage_delivered(cr, deadline=1e9) == 4


def test_airtime_per_delivered_alert_against_r3():
    c = M.boot_cell(runs(10, air_m=60.0, air_t=100.0, del_m=45, del_t=90), np.random.default_rng(1), 50)
    assert c["ratio_pd_pt"] == pytest.approx((60 / 45) / (100 / 90)) and np.allclose(c["ratio_pd"], (60 / 45) / (100 / 90))


def test_run_pair_stats_each_run_can_cause_a_drop():
    base = [(0, 0, 0.5, 1.0, 0, 1.0, 1, 1, 1), (1, 0, 0.5, 1.0, 0, 1.0, 1, 1, 1)]
    dropped = [(0, 0, 0.5, 1.0, 0, 1.0, 1, 1, 1), (1, 1, 0.5, 1.0, 0, 1.0, 1, 1, 1)]
    for which in range(3):
        fr = [frame(base), frame(base), frame(base)]
        fr[which] = frame(dropped)
        st = M.run_pair_stats(*fr)
        assert st["n_drop"] == 1 and st["n_cr"] == 1 and st["air_s"] == 1.0


def runs(n, **kw):
    base = dict(air_s=100.0, air_t=130.0, air_m=80.0, n_cr=100, del_t=90, del_m=90, n_ev=500, n_drop=0)
    base.update(kw)
    return [dict(base) for _ in range(n)]


def test_boot_cell_constant_runs_have_a_degenerate_interval():
    c = M.boot_cell(runs(10), np.random.default_rng(1), 100)
    assert c["ratio_s_pt"] == pytest.approx(80 / 100 - 1) and np.allclose(c["ratio_s"], -0.2)
    assert c["ratio_t_pt"] == pytest.approx(80 / 130) and np.allclose(c["ratio_t"], 80 / 130)
    assert c["dd_pt"] == 0.0 and np.allclose(c["dd"], 0.0)
    assert c["deliv_t"] == pytest.approx(0.9) and c["n_cr"] == 1000


def test_boot_cell_delivery_difference_has_the_sign_micro_minus_r3():
    c = M.boot_cell(runs(10, del_m=95, del_t=90), np.random.default_rng(1), 50)
    assert c["dd_pt"] == pytest.approx(0.05) and np.allclose(c["dd"], 0.05)
    c = M.boot_cell(runs(10, del_m=85, del_t=90), np.random.default_rng(1), 50)
    assert c["dd_pt"] == pytest.approx(-0.05)


def test_boot_cell_is_a_cluster_bootstrap_over_runs():
    rs = runs(4) + runs(4, air_m=200.0)  # two kinds of runs: the resampled ratio varies and stays between the two kinds
    c = M.boot_cell(rs, np.random.default_rng(7), 400)
    lo, hi = 80 / 100 - 1, 200 / 100 - 1
    assert c["ratio_s"].min() >= lo - 1e-12 and c["ratio_s"].max() <= hi + 1e-12 and c["ratio_s"].std() > 0.05
    assert c["ratio_s_pt"] == pytest.approx(0.4)  # the ratio of sums of the original runs: (4 * 80 + 4 * 200) / 800 - 1


def test_boot_cell_resamples_every_run_including_the_last():
    rs = runs(7) + runs(1, air_m=1000.0)
    c = M.boot_cell(rs, np.random.default_rng(3), 400)
    assert c["ratio_s"].max() > 0.5 and c["ratio_s"].min() == pytest.approx(-0.2)


def cell(ratio_s=None, dd=None):
    return dict(ratio_s=np.asarray(ratio_s if ratio_s is not None else [0.0]), dd=np.asarray(dd if dd is not None else [0.0]))


def test_criterion_a_boundary_is_inclusive_at_0_40():
    ok, hi, p = M.criterion_a(cell(ratio_s=np.full(100, 0.40)))
    assert ok and hi == pytest.approx(0.40)
    assert p == pytest.approx(101 / 101)  # every resample is at or above 0.40
    ok, hi, p = M.criterion_a(cell(ratio_s=np.full(100, 0.4001)))
    assert not ok
    ok, hi, p = M.criterion_a(cell(ratio_s=np.full(100, -0.2)))
    assert ok and p == pytest.approx(1 / 101)


def test_criterion_a_uses_the_97_5_percentile():
    x = np.concatenate([np.full(95, -0.2), np.full(5, 0.9)])  # 5% of resamples above 0.40: the 97.5th percentile is above 0.40
    assert not M.criterion_a(cell(ratio_s=x))[0]
    x = np.concatenate([np.full(98, -0.2), np.full(2, 0.9)])  # 2% above: the 97.5th percentile is below
    assert M.criterion_a(cell(ratio_s=x))[0]


def test_criterion_b_boundary_and_direction():
    ok, lo, p = M.criterion_b(cell(dd=np.full(100, -0.01)))
    assert ok and lo == pytest.approx(-0.01) and p == pytest.approx(1 / 101)  # -0.01 is not below the margin
    ok, lo, p = M.criterion_b(cell(dd=np.full(100, -0.0101)))
    assert not ok and p == pytest.approx(1.0)
    x = np.concatenate([np.full(3, -0.5), np.full(97, 0.0)])  # 3% of resamples far below: the 2.5th percentile is below -0.01
    assert not M.criterion_b(cell(dd=x))[0]
    x = np.concatenate([np.full(2, -0.5), np.full(98, 0.0)])
    assert M.criterion_b(cell(dd=x))[0]


def test_file_names_and_arguments():
    assert M.fname_new(Path("d"), 9, "shipped", 0.3, "r6m", 5, 30.0).name == "sf9_shipped_p0.3_r6m_5_pend30.txt"
    assert M.fname_new(Path("d"), 7, "calib", 0.0, "r3t", 5).name == "sf7_calib_p0_r3t_5.txt"
    a = M.args_for(9, 1, 0.3, 5, "r6m", 30.0)
    assert "--policy=r6m" in a and "--pend=30" in a and "--sensShipped=1" in a and "--seed=5" in a and "--sf=9" in a and "--n=60" in a
    assert "--pend" not in M.args_for(9, 1, 0.3, 5, "r3t", None)


def test_development_and_held_out_seeds_are_disjoint():
    assert not set(M.DEV_SEEDS) & set(M.HELD_SEEDS) and len(M.HELD_SEEDS) == 60 and min(M.DEV_SEEDS) == 101 and len(M.DEV_SEEDS) == 20


# ---------------------------------------------------------------------------------- trace-driven micro event
def test_arrival_ack_has_the_draws_and_results_of_the_r3_function():
    for seed in range(40):
        g = random.Random(seed)
        r = np.array([g.random() < 0.5 for _ in range(30)])
        a = T.arrival_trace(r, 3, 2.0, 0.17, 0.3, random.Random(seed + 1000))
        b = M.arrival_ack(r, 3, 2.0, 0.17, 0.3, random.Random(seed + 1000), T.WIN3, T.TRIES3)
        assert a == b[:2]
    r = np.array([True, False, False, False, False, False, False, False])  # the first try is received, the acknowledgement is lost (p_dl = 1): no acknowledgement
    assert M.arrival_ack(r, 0, 0.0, 0.1, 1.0, random.Random(0), T.WIN3, T.TRIES3)[2] is False
    assert M.arrival_ack(r, 0, 0.0, 0.1, 0.0, random.Random(0), T.WIN3, T.TRIES3) == (0.1, 1, True)
    assert M.arrival_ack(np.zeros(8, bool), 0, 0.0, 0.1, 0.0, random.Random(0), T.WIN3, T.TRIES3)[1:] == (4, False)


def _event_pairs(n=300, p_loss=0.3):
    out = []
    a_micro = T.air(13, T.SF_R3)
    for i in range(n):
        g = random.Random(i)
        r = np.array([g.random() >= p_loss for _ in range(40)])
        ev = [(True, True, 1, 0.1), (True, False, 1, 0.1), (True, False, 0, 0.3), (False, True, 1, 0.0), (True, True, 0, 0.2)][i % 5]
        r3 = T.r3_event(r, 4, ev, p_loss, random.Random(i + 5))
        mi = M.micro_event(r, 4, ev, p_loss, random.Random(i + 5), a_micro)
        out.append((r3, mi, ev))
    return out


def test_micro_event_delivery_equals_r3_and_airtime_is_not_larger():
    n_less = 0
    for r3, mi, ev in _event_pairs():
        assert mi["two_d"] == r3["two_d"] and mi["n_cr"] == r3["n_cr"]
        assert mi["two_air"] <= r3["two_air"] + 1e-12
        n_less += mi["two_air"] < r3["two_air"] - 1e-12
    assert n_less > 50  # the micro frames save airtime on a good share of events


def test_micro_event_uses_the_micro_frame_only_after_an_acknowledged_flash():
    a_micro = 0.01  # shorter than any real frame, so that every use of it is visible
    r = np.ones(40, bool)
    ev = (True, True, 1, 0.1)
    o = M.micro_event(r, 0, ev, 0.0, random.Random(0), a_micro)  # flash acknowledged on the first try: flash + one micro-confirm
    assert o["two_air"] == pytest.approx(T.A_FL + a_micro)
    o = M.micro_event(r, 0, ev, 1.0, random.Random(0), a_micro)  # every acknowledgement lost: no acknowledged flash, so four flashes and four full confirms
    assert o["two_air"] == pytest.approx(4 * T.A_FL + 4 * T.A_AL)
    o = M.micro_event(r, 0, (True, False, 0, 0.1), 0.0, random.Random(0), a_micro)  # a cancel after an acknowledged flash: three micro-cancels
    assert o["two_air"] == pytest.approx(T.A_FL + 3 * a_micro)
    o = M.micro_event(r, 0, (True, False, 0, 0.1), 1.0, random.Random(0), a_micro)  # no acknowledged flash: the 14-byte cancels of R3
    assert o["two_air"] == pytest.approx(4 * T.A_FL + 3 * T.A_FL)
    o = M.micro_event(r, 0, (False, True, 1, 0.0), 0.0, random.Random(0), a_micro)  # no flash: the full alert, as in R3
    assert o["two_air"] == pytest.approx(T.A_AL)


def test_micro_frame_is_shorter_than_the_flash_and_the_alert():
    assert T.air(13, T.SF_R3) <= T.A_FL < T.A_AL  # at SF7 the 13-byte frame has the airtime of the 14-byte flash (same symbol count)


# ---------------------------------------------------------------------------------- known answer
def test_known_answer_the_stored_p1_cell_is_reproduced_when_the_micro_run_is_the_r3_run():
    d = M.R3OUT
    if not (d / "sf9_shipped_p0.3_r3t_60.txt").exists() or not M.EVENTS.exists():
        pytest.skip("ns-3 outputs not built")
    stored = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    ev = M.event_table()
    fs = [M.fname_new(d, 9, "shipped", 0.3, "r3s", s) for s in M.HELD_SEEDS]
    ft = [M.fname_new(d, 9, "shipped", 0.3, "r3t", s) for s in M.HELD_SEEDS]
    rs = []
    for a_, b_ in zip(fs, ft):
        rs.append(M.run_pair_stats(M.parse(a_, ev), M.parse(b_, ev), M.parse(b_, ev), deadline=1e9))  # the stored P1 delivery has no 10 s limit
    c = M.boot_cell(rs, np.random.default_rng(M.SEED), 50)
    assert c["ratio_s_pt"] == pytest.approx(stored["pp.p1.sf9.shipped.p0.3.extra_air_ratio"], abs=2e-4)
    assert c["deliv_t"] == pytest.approx(stored["pp.p1.sf9.shipped.p0.3.delivery_two"], abs=2e-4)
    assert c["dd_pt"] == 0.0 and c["ratio_t_pt"] == pytest.approx(1.0)
    assert not math.isnan(c["ratio_s_pt"])


# ---------------------------------------------------------------------------------- ns-3 policy r6m (needs the WSL build)
def _ns3(policy, extra=""):
    import subprocess

    from crashguard import rd_firmware as F

    cmd = f"cd ~/ns3work/ns-3-dev && {M.NS_BIN} --n=30 --sf=9 --p=0.3 --radius=1500 --rate=10 --duty=0.01 --seed=3 --policy={policy} --events={F.wsl_path(M.EVENTS)} --sensShipped=1 {extra} 2>/dev/null"
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd], capture_output=True, text=True, timeout=300)
    except Exception:  # noqa: BLE001
        pytest.skip("WSL not available")
    if r.returncode != 0 or "DUTY" not in r.stdout:
        pytest.skip("ns-3 binary not available")
    return r.stdout.splitlines()


def test_ns3_r6m_counts_micro_frames_and_falls_back_to_the_full_frames_when_the_lifetime_is_too_short():
    out = _ns3("r6m", "--pend=30")
    n_micro, n_full = map(int, next(ln for ln in out if ln.startswith("R6M ")).split()[1:])
    assert n_micro > 20 and n_full >= 0  # micro frames are sent after acknowledged flashes
    # a lifetime shorter than any acknowledgement delay: no micro frame is ever sent, and the run equals R3's two-stage run line for line (same random streams)
    short = _ns3("r6m", "--pend=0.0001")
    n_micro0 = int(next(ln for ln in short if ln.startswith("R6M ")).split()[1])
    assert n_micro0 == 0
    r3 = _ns3("r3t")
    assert [ln for ln in short if ln.startswith("R3 ")] == [ln for ln in r3 if ln.startswith("R3 ")]
