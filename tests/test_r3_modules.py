"""Tests of the round 3 modules: frame-counter extraction rules, the timed check helpers and the stored results (docs/02_preregistration/PREREGISTRATION_V14.md)."""
import json
import math
from pathlib import Path

import numpy as np

from crashguard import r3_t1_extract as X
from crashguard import r3_t2_timed as TT

ROOT = Path(__file__).resolve().parents[1]


def seqs(fc, step=60.0):
    t = np.arange(len(fc), dtype=float) * step
    return X.frames_of_device(t, np.array(fc))


def test_gap_counts_lost_frames():
    s = seqs([10, 11, 14, 15])
    assert len(s) == 1 and list(s[0][0]) == [1, 1, 0, 0, 1, 1]


def test_duplicate_copies_are_merged_and_wrap_is_continuous():
    t = np.array([0.0, 0.5, 60.0, 120.0])
    s = X.frames_of_device(t, np.array([65534, 65534, 65535, 0]))
    assert len(s) == 1 and list(s[0][0]) == [1, 1, 1]


def test_reset_and_long_gap_start_new_segments():
    s = seqs([5000, 5001, 10, 11])  # counter decreases from below 60,000: reset
    assert len(s) == 2 and [len(r) for r, _ in s] == [2, 2]
    s2 = seqs([1, 2, 300, 301])  # gap of 298 frames: outage, not loss
    assert len(s2) == 2


def test_split_is_stable_and_balanced():
    h = [X.half_of(f"dev{i}") for i in range(2000)]
    assert h == [X.half_of(f"dev{i}") for i in range(2000)] and 0.45 < np.mean(h) < 0.55


def test_timed_check_known_values():
    TT.T.init_ctx()
    t0, _ = TT.first_rx_time("quick", [1], [1] * 12)
    assert t0 == TT.T.READY0 + TT.T.air(97, 9) + 0.0
    t2, _ = TT.first_rx_time("quick", [0, 0, 1], [1] * 12)
    t3, _ = TT.first_rx_time("quick", [0, 0, 0, 1], [1] * 12)
    assert t0 < t2 < t3
    assert math.isinf(TT.first_rx_time("P1", [0, 0, 0, 1], [1] * 12)[0])  # the severity table holds 5 s: no fourth attempt ends in time
    assert TT.longest_run([1, 0, 0, 1, 0]) == 2


def test_stored_round3_results_are_consistent():
    r = {e["name"]: e for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    assert r["r3.t1.invariants.late_delivery"]["value"] == 0 and r["r3.t1.invariants.duty_exceeded"]["value"] == 0
    assert r["r3.t1.n_heldout_devices"]["value"] >= 100
    assert r["r3.t2.timed.duty.breaches"]["value"] == 0
    for k in ("r3.holm.ht1b.verdict", "r3.holm.ht3a.verdict", "r3.decide.hT2.verdict"):
        assert k in r
    assert all(e["origin"] in {"TRACE_DRIVEN", "FORMAL", "MEASURED_SOFTWARE", "ANALYTICAL", "SIMULATED", "NOT_RUN"} for n, e in r.items() if n.startswith("r3."))
