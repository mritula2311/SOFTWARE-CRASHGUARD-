"""Part 0B: spline restoration, grouped bootstrap, split rules, precision at other prevalences, seed-mean statistics (synthetic inputs only)."""
import numpy as np
import pandas as pd
import pytest

from crashguard import boot as B
from crashguard import config as C
from crashguard import detector_extra as DX
from crashguard import prevalence as PV
from crashguard import saturation_splits as SS
from crashguard import severity_synth as Y
from crashguard import spline_restore as SPL

FS = float(C.FS_HZ)


def test_runs_finds_maximal_segments_inside_the_pulse():
    m = np.array([0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0], bool)
    assert SPL.runs(m, 0, 11) == [(2, 3), (5, 5), (8, 10)]
    assert SPL.runs(m, 4, 7) == [(5, 5)]  # a run must start inside the interval


def test_restore_leaves_unclipped_window_unchanged():
    acc, trig = Y.make_window("half_sine", 8.0, 0.1, 0.0, FS, np.random.default_rng(0), noise_g=0.0, tilt_deg=0.0)
    out, info = SPL.restore(acc, trig, FS, 16.0, 0.9)
    assert info["segments"] == 0 and np.array_equal(out, acc)


def test_restore_raises_a_clipped_peak_and_never_lowers_a_reading():
    acc, trig = Y.make_window("half_sine", 40.0, 0.12, 0.0, FS, np.random.default_rng(1), noise_g=0.0, tilt_deg=0.0, clip_g=16.0)
    out, info = SPL.restore(acc, trig, FS, 16.0, 0.9)
    assert info["segments"] >= 1
    assert (np.abs(out[:, :2]) >= np.abs(acc[:, :2]) - 1e-12).all()
    assert np.abs(out[:, :2]).max() > np.abs(acc[:, :2]).max()
    assert np.abs(out[:, :2]).max() <= SPL.A_MAX_FACTOR * 16.0 + 1e-9


def test_segment_with_too_few_clean_samples_is_skipped():
    acc = np.zeros((40, 3))
    acc[:, 2] = 1.0
    acc[2:8, 0] = [16.0, 16.0, 16.0, 16.0, 8.0, 4.0]  # the saturated run starts at sample 2: only 2 samples exist before it
    out, info = SPL.restore(acc, 2, FS, 16.0, 0.9)
    assert info["segments"] == 1 and info["skipped"] == 1 and info["restored"] == 0
    assert np.array_equal(out, acc)


def test_grouped_bootstrap_draws_whole_groups():
    groups = np.array(["a", "a", "b", "c", "c", "c"])
    mem = B.group_members(groups)
    assert [m.tolist() for m in mem] == [[0, 1], [2], [3, 4, 5]]
    for idx in B._gidx(mem, 20, 1):
        counts = np.bincount(idx, minlength=6)
        assert counts[0] == counts[1] and counts[3] == counts[4] == counts[5]  # members of a group always come together


def test_grouped_ci_is_wider_than_row_ci_when_rows_in_a_group_are_identical():
    rng = np.random.default_rng(0)
    vals = np.repeat(rng.normal(size=30), 4)
    groups = np.repeat(np.arange(30), 4)
    _p, lo_g, hi_g = B.ci_grouped(vals, groups, np.mean)
    _p, lo_r, hi_r = B.ci(vals, np.mean)
    assert hi_g - lo_g > hi_r - lo_r


def test_paired_diff_grouped_matches_the_point_difference():
    a, b = np.array([5.0, 6, 7, 8]), np.array([4.0, 5, 6, 7])
    d, lo, hi = B.paired_diff_grouped(a, b, np.array([0, 0, 1, 1]), np.median)
    assert d == pytest.approx(-1.0) and lo == pytest.approx(-1.0) and hi == pytest.approx(-1.0)


def test_every_third_group_is_held_out_and_groups_never_split():
    meta = pd.DataFrame(dict(test_no=[1, 2, 3, 4, 5, 6, 7, 8, 9], kind=["frontal"] * 9, group=list("aabbccddd"), group_mm=list("aabbccddd")))
    held = SS.split_by(meta, "group")
    assert set(meta.group[held]) == {"c"}  # groups sorted by smallest test number: a, b, c, d -> rank 3 = c
    for g in set(meta.group):
        assert len(set(held[meta.group == g])) == 1


def test_split_o_holds_out_ranks_3_6_9_within_each_kind():
    meta = pd.DataFrame(dict(test_no=list(range(1, 10)) + list(range(101, 107)), kind=["frontal"] * 9 + ["side"] * 6))
    held = SS.split_O(meta)
    assert meta.test_no[held].tolist() == [3, 6, 9, 103, 106]


def test_ppv_formula_and_limits():
    assert PV.ppv(1.0, 0.0, 0.01) == pytest.approx(1.0)
    assert PV.ppv(0.5, 0.01, 0.5) == pytest.approx(0.25 / 0.255)
    assert PV.ppv(0.9, 0.05, 0.0002) < 0.01  # at a rare prevalence almost every alert is false
    assert PV.ppv(0.6, 0.01, 0.16) > PV.ppv(0.6, 0.01, 0.01) > PV.ppv(0.6, 0.01, 0.0002)


def test_seed_mean_statistics_average_over_seed_columns():
    # columns: y, pred seed a, pred seed b. recall of seed a = 1.0, seed b = 0.5 -> mean 0.75 ; fpr a = 0, b = 0.5 -> 0.25
    a = np.array([[1, 1, 1], [1, 1, 0], [0, 0, 1], [0, 0, 0]])
    assert DX._mean_recall_stat(a) == pytest.approx(0.75)
    assert DX._mean_fpr_stat(a) == pytest.approx(0.25)
