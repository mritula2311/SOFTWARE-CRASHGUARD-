"""Tests of the L3 module (V16 section 5 with addendum A1). Synthetic inputs, plus known-answer tests that read the stored caches when they exist."""
from __future__ import annotations

import math
import pickle
from pathlib import Path

import numpy as np
import pytest

from crashguard import config as C
from crashguard import r5_l3 as L

ROOT = Path(__file__).resolve().parents[1]


def _still(n=600):
    return np.tile([0.0, 0.0, 1.0], (n, 1))


def test_constants_follow_the_datasheets_and_v16():
    assert L.FIFO_SAMPLES == 170 and L.FIFO_BYTES == 1024
    cur = L.CURRENTS
    assert (cur["sensor_full"], cur["sensor_acc_only"], cur["mcu_light_sleep"]) == (3.8, 0.5, 0.8)
    assert (cur["mcu_active_lo"], cur["mcu_active_hi"]) == (20.0, 31.0)
    assert L.HIST == 50 and L.HOLD == 200 and L.T_MOTS == (0.3, 0.5, 1.0)
    d = L.L3Params()
    assert (d.t_mot, d.l_gyro_ms, d.retrain, d.alpha) == (0.5, 30, True, 0.01) and len(L.ITERATIONS) <= 5


def test_deviation_known_values():
    a = _still(120)
    a[80] = [0.0, 0.0, 2.5]
    d = L.deviation(a)
    assert d[0] == pytest.approx(0.0) and d[10] == pytest.approx(0.0) and d[80] == pytest.approx(1.5)
    b0 = _still(5)
    b0[0] = [0.0, 0.0, 2.2]
    assert L.deviation(b0)[0] == pytest.approx(1.2)  # no history: the reference is 1 g
    assert L.interrupt_index(b0, 0.5, 0) == 0
    assert d[81] == pytest.approx(abs(1.0 - (49 * 1.0 + 2.5) / 50))  # the previous 0.5 s includes the spike


def test_interrupt_index_is_the_start_of_the_awake_period_containing_the_trigger():
    a = _still(600)
    a[100, 2] = 1.5  # deviation 0.5: not above 0.5
    assert L.interrupt_index(a, 0.5, 100) == -1
    a[100, 2] = 1.51
    assert L.interrupt_index(a, 0.5, 100) == 100
    a[60, 2] = 1.4  # an earlier, weaker bump: awake from 60 for 200 samples
    assert L.interrupt_index(a, 0.3, 100) == 60 and L.interrupt_index(a, 0.5, 100) == 100
    assert L.interrupt_index(_still(50), 0.3, 10) == -1
    # a bump more than the hold (200 samples) before the event does not leave the node awake
    b = _still(900)
    b[50, 2] = 2.0
    b[500, 2] = 2.0
    assert L.interrupt_index(b, 0.5, 500) == 500
    b[300, 2] = 2.0  # within the hold of the bump at 500: the period starts at 300
    assert L.interrupt_index(b, 0.5, 500) == 300
    assert L.interrupt_index(b, 0.5, 700) == 300 or L.interrupt_index(b, 0.5, 700) == -1  # 700 is 200 after 500: idle again
    assert L.interrupt_index(b, 0.5, 699) == 300
    assert L.interrupt_index(b, 0.5, 700) == -1


def test_awake_mask_hold_length():
    a = _still(1000)
    a[100, 2] = 3.0
    m = L.awake_mask(a, 0.5)
    assert m.sum() == 200 and m[100] and m[299] and not m[300] and not m[99]
    assert not L.awake_mask(_still(300), 0.5).any()


def test_active_share_hold_and_edges():
    a = _still(1000)
    assert L.active_share(a, 0.5) == 0.0
    a[100, 2] = 3.0
    s = L.active_share(a, 0.5)
    assert s == pytest.approx(0.2, abs=1e-12)  # asserted at sample 100 only (the mean rises afterwards), held for exactly 200 samples
    a2 = a.copy()
    a2[900, 2] = 3.0  # a second event near the end: its hold runs past the end of the recording
    assert L.active_share(a2, 0.5) > s + 0.05
    a3 = a.copy()
    a3[250, 2] = 3.0  # a second event inside the hold: the hold is extended, not doubled
    s3 = L.active_share(a3, 0.5)
    assert s < s3 < 2 * s


def test_stitch_window_accelerometer_and_gyro_rules():
    n = 1600
    rng = np.random.default_rng(0)
    acc = rng.normal(0, 1, (n, 3))
    gyro = rng.normal(5, 1, (n, 3))
    i0, i_m = 800, 760
    wa, wg, used = L.stitch_window(acc, gyro, i0, i_m, 1, 3)
    j = np.arange(i0 - C.PRE_N, i0 - C.PRE_N + C.WIN_N)
    assert np.array_equal(wa, acc[j])  # B100: the accelerometer path is identical to the always-on path
    assert (wg[j < i_m + 3] == 0).all() and np.array_equal(wg[j >= i_m + 3], gyro[j[j >= i_m + 3]])
    assert used == i_m - (i0 - C.PRE_N)
    wa4, _wg4, _u = L.stitch_window(acc, gyro, i0, i_m, 4, 3)
    pre = j < i_m
    assert np.array_equal(wa4[pre], acc[(j[pre] // 4) * 4]) and np.array_equal(wa4[~pre], acc[j[~pre]])
    assert (wa4[pre][:4] == wa4[pre][0]).all() or j[pre][0] % 4 != 0  # zero-order hold


def test_fifo_capacity_is_never_exceeded():
    """Property: with the interrupt at or before the trigger sample the pre-interrupt samples needed never exceed the FIFO."""
    acc = np.zeros((1600, 3))
    for i0 in (100, 450, 800, 1300):
        for lead in (0, 1, 50, 99, 100, 300):
            i_m = max(i0 - lead, 0)
            _a, _g, used = L.stitch_window(acc, np.zeros((1600, 3)), i0, i_m, 1, 3)
            assert 0 <= used <= C.PRE_N <= L.FIFO_SAMPLES
    _a, _g, used = L.stitch_window(acc, np.zeros((1600, 3)), 800, 800, 1, 3)
    assert used == C.PRE_N  # the interrupt at the trigger sample: the whole pre-trigger second comes from the FIFO


def test_stitch_window_no_future_samples_in_the_pre_part():
    """Property: the pre-interrupt samples of the window come from times before the interrupt (zero-order hold looks backwards only)."""
    n = 1600
    acc = np.arange(n * 3, dtype=float).reshape(n, 3)
    for step in (1, 4, 10):
        for i_m in (700, 790, 800):
            wa, _wg, _u = L.stitch_window(acc, np.zeros((n, 3)), 800, i_m, step, 3)
            j = np.arange(800 - C.PRE_N, 800 - C.PRE_N + C.WIN_N)
            src = (wa[:, 0] / 3).astype(int)  # the sample index the window sample was taken from
            pre = j < i_m
            assert (src[pre] <= j[pre]).all() and (src[pre] > j[pre] - step).all()
            assert (src[~pre] == j[~pre]).all()


def test_gyro_start_up_delay_follows_the_datasheet_value():
    acc, gyro = _still(1600), np.ones((1600, 3))
    _a, wg30, _u = L.stitch_window(acc, gyro, 800, 780, 1, 3)
    _a, wg70, _u = L.stitch_window(acc, gyro, 800, 780, 1, 7)
    assert (wg30 == 0).all(axis=1).sum() == (780 + 3) - (800 - C.PRE_N)
    assert (wg70 == 0).all(axis=1).sum() == (780 + 7) - (800 - C.PRE_N)


def test_energy_ratio_formula_and_monotonicity():
    cur = L.CURRENTS
    p_a = 3.8 + 20.0
    assert L.energy_ratio(1.0) == pytest.approx(1.0) and L.energy_ratio(0.0) == pytest.approx((0.5 + 0.8) / p_a)
    assert L.energy_ratio(0.25) == pytest.approx((1.3 * 0.75 + p_a * 0.25) / p_a)
    ds = np.linspace(0, 1, 11)
    r = [L.energy_ratio(d) for d in ds]
    assert all(b > a for a, b in zip(r, r[1:]))
    assert L.energy_ratio(0.5, cur["mcu_active_hi"]) < L.energy_ratio(0.5, cur["mcu_active_lo"]) + 1e-12  # a bigger MCU current makes the idle share worth more
    # break-even: the ratio at the break-even share is the target
    for tgt in (0.3, 0.5, 0.8):
        d = L.break_even_share(tgt)
        assert L.energy_ratio(d) == pytest.approx(tgt)
    assert 0.46 < L.break_even_share(0.5) < 0.49


def test_share_bootstrap():
    sh = np.r_[np.zeros(500), np.ones(500)]
    m, lo, hi = L.share_bootstrap(sh)
    assert m == 0.5 and lo < 0.5 < hi and hi - lo < 0.1


def test_heldout_stats_directions_and_margin():
    rng = np.random.default_rng(0)
    n = 6000
    y = (rng.random(n) < 0.4).astype(int)
    mask = rng.random(n) < 0.5
    a = (y == 1) & (rng.random(n) < 0.6)
    same = L.heldout_stats(a, a, y, mask)
    assert same["loss"] == 0.0 and same["recall_met"] and same["p"] < 0.05 and same["n_crash"] == int(((y == 1) & mask).sum())
    b = a.copy()
    b[(y == 1) & a & (np.arange(n) % 20 == 0)] = False  # a loss of about 3 points
    r = L.heldout_stats(a, b, y, mask)
    assert 0.01 < r["loss"] and not r["recall_met"] and r["p"] > 0.5
    c = a.copy()
    c[(y == 1) & ~a & (np.arange(n) % 3 == 0)] = True  # B better than A
    assert L.heldout_stats(a, c, y, mask)["loss"] < 0 and L.heldout_stats(a, c, y, mask)["recall_met"]
    allm = L.heldout_stats(a, b, y, np.ones(n, bool))
    assert allm["n_crash"] == int((y == 1).sum())


def test_combo_names_cover_the_iterations():
    names = {c[0] for c in L.COMBOS}
    for it in L.ITERATIONS:
        assert L.combo_name(it) in names
    assert L.combo_name(L.L3Params(), 4) == "b25_t05_l30" and L.combo_name(L.L3Params(), 10) == "b10_t05_l30"


CACHE = ROOT / "data" / "processed" / "r5_l3_cache.pkl"


@pytest.mark.skipif(not CACHE.exists(), reason="L3 cache not built")
def test_cache_known_answers():
    """The cache has the triggered events of the post-event cache of L2 (same trigger rule), the interrupt is never later than the trigger sample for any event the arm detects, and B100 windows equal the A windows
    in the accelerometer channels."""
    z = L.load_cache()
    det = pickle.loads((ROOT / "data" / "processed" / "r5_det_seed42.pkl").read_bytes()) if (ROOT / "data" / "processed" / "r5_det_seed42.pkl").exists() else None
    if det is not None:
        for k in ("ids_tr", "ids_va", "ids_te"):
            assert all(int(e) in z["row"] for e in det[k])
    det05 = z["detected"]["b100_t05_l30"].astype(bool)
    assert (z["i_m"][det05, 1] <= z["i0"][det05]).all() and (z["i_m"][det05, 1] >= 0).all()
    assert ((z["i_m"][~det05, 1] < 0) | (z["i_m"][~det05, 1] > z["i0"][~det05])).all()
    assert len(z["shares"]) > 1000 and all(len(v) == 3 for v in list(z["shares"].values())[:50])
    # a lower interrupt threshold detects at least as many events
    d3, d10 = z["detected"]["b100_t03_l30"].sum(), z["detected"]["b100_t10_l30"].sum()
    assert d3 >= det05.sum() >= d10
    # active share is non-increasing in the threshold
    sh = np.array(list(z["shares"].values()))
    assert (sh[:, 0] >= sh[:, 1] - 1e-12).all() and (sh[:, 1] >= sh[:, 2] - 1e-12).all()


@pytest.mark.skipif(not (CACHE.exists() and (ROOT / "data" / "processed" / "r5_det_seed42.pkl").exists()), reason="caches not built")
def test_b100_windows_keep_the_always_on_accelerometer_features():
    """Known answer on one validation event: the stitched B100 window has the accelerometer rows of the always-on window; only the gyro rows differ."""
    from crashguard import windows_cache as W

    z = L.load_cache()
    d = W.load("validation")
    for i in range(3):
        eid = int(d["event_id"][i])
        if not z["detected"]["b100_t05_l30"][z["row"][eid]]:
            continue
        # accelerometer-only features do not depend on the gyro: peak_a is feature 0
        fa = W.features_of(d["acc"][i : i + 1], np.zeros_like(d["gyro"][i : i + 1]))
        fb = z["feats"]["b100_t05_l30"][z["row"][eid]]
        for name in ("peak_a", "rms_a", "energy", "dur_above"):
            assert fb[list(C.FEATURES).index(name)] == pytest.approx(float(fa[name].iloc[0]), rel=1e-4, abs=1e-5)
        break
    else:
        pytest.skip("no detected event among the first three")
    assert math.isfinite(float(fb.sum()))


def test_interrupt_detected_rule():
    assert L.interrupt_detected(0, 0) and L.interrupt_detected(5, 9) and L.interrupt_detected(9, 9)
    assert not L.interrupt_detected(-1, 9) and not L.interrupt_detected(10, 9)


class _Stub:
    def predict_proba(self, X):
        p = np.clip(X[:, 0], 0.0, 1.0)
        return np.stack([1.0 - p, p], axis=1)


def test_arm_scores_use_the_positive_class_and_mark_missed_events():
    cache = dict(row={11: 0, 12: 1, 13: 2}, feats={"b100_t05_l30": np.array([[0.9, 0], [0.2, 0], [0.7, 0]], np.float32)}, detected={"b100_t05_l30": np.array([True, True, False])})
    s = L.arm_scores(cache, "b100_t05_l30", np.array([13, 11, 12]), _Stub())
    assert s[0] == -1.0 and s[1] == pytest.approx(0.9) and s[2] == pytest.approx(0.2)
    none = dict(cache, detected={"b100_t05_l30": np.array([False, False, False])})
    assert (L.arm_scores(none, "b100_t05_l30", np.array([11, 12]), _Stub()) == -1.0).all()
