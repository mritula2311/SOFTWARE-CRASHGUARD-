"""Tests of the paper-session modules (P0 refit, P1 ns-3 two-stage alert analysis, zero-spacing check)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import pp_r3_ns3 as N

ROOT = Path(__file__).resolve().parents[1]


def _res():
    return {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}


def _frame(rows):
    d = pd.DataFrame(rows, columns=["k", "dropped", "flash", "alert", "cancel", "air", "E", "F", "y"])
    return d


def test_run_stats_pairs_and_delivery():
    # event 0: crash, E and F, flash 0.1 s and alert 2.0 s arrive; event 1: crash, E only, flash arrives and no cancel; event 2: dropped in the two-stage run
    s = _frame([[0, 0, -1, 2.0, 0, 0.2, 1, 1, 1], [1, 0, -1, -1, 0, 0.0, 1, 0, 1], [2, 0, -1, 2.0, 0, 0.2, 1, 1, 1]])
    t = _frame([[0, 0, 0.1, 2.0, 0, 0.3, 1, 1, 1], [1, 0, 0.1, -1, 0, 0.3, 1, 0, 1], [2, 1, -1, -1, 0, 0.0, 1, 1, 1]])
    r = N.run_stats(s, t)
    assert r["n_cr"] == 2 and r["n_drop"] == 1
    assert np.allclose(r["diffs"], [1.9])
    assert r["del_s"] == 1 and r["del_t"] == 2  # the E-only crash counts as delivered when the flash arrived and no cancel did
    assert abs(r["air_t"] - 0.6) < 1e-9 and abs(r["air_s"] - 0.2) < 1e-9


def test_cancel_removes_delivery():
    s = _frame([[0, 0, -1, -1, 0, 0.0, 1, 0, 1]])
    t = _frame([[0, 0, 0.1, -1, 1, 0.3, 1, 0, 1]])
    assert N.run_stats(s, t)["del_t"] == 0


def test_cpp_has_r3_policies_and_null_guard_documented():
    src = (ROOT / "xsim" / "ns3" / "xsim_alert.cc").read_text(encoding="utf-8")
    assert "R3S" in src and "R3T" in src and "ScheduleNow(&R3Next" in src
    assert "logical-lora-channel-helper.cc" in (ROOT / "docs" / "03_results" / "XSIM_BUILD.md").read_text(encoding="utf-8")


def test_stored_p1_p0_z0_keys():
    R = _res()
    assert R["pp.p1.verdict"] in ("HOLDS IN NS-3", "PARTLY", "DOES NOT HOLD IN NS-3")
    assert R["pp.p1.sf9.calib.hP1c.verdict"] in ("SUPPORTED", "NOT SUPPORTED")
    assert R["pp.p0.holm.hc3.verdict_refit"] in ("SUPPORTED", "MIXED", "NOT SUPPORTED", "NOT_RUN")
    assert R["pp.c6.z0.valid"] in (0, 1)
    assert R["pp.c6.z0.invariant_late_delivery"] == 0
    assert all(R[k] == v for k, v in (("r3.t1.invariants.duty_exceeded", 0),))
