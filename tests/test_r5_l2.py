"""Tests of the L2 module (V16 section 4 and the code verification of section 10). Synthetic inputs only, except the two known-answer tests that read the cached detector scores of seed 42."""
from __future__ import annotations

import json
import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crashguard import r5_l2 as L

ROOT = Path(__file__).resolve().parents[1]


def test_cut_repeats_the_edges():
    x = np.arange(10.0)
    assert list(L._cut(x, -3, 2)) == [0, 0, 0, 0, 1]
    assert list(L._cut(x, 8, 13)) == [8, 9, 9, 9, 9]


def test_gps_times_spread_over_the_event():
    t = L.gps_times(1600, 16)
    assert math.isclose(t[1], 1.0) and math.isclose(t[-1], 15.0)
    t2 = L.gps_times(800, 16)
    assert math.isclose(t2[1], 0.5)


def test_speed_features_known_values():
    gps = np.array([50.0, 50, 50, 50, 50, 50, 48, 40, 10, 2, 0, 0, 0, 0, 0, 0])
    f = L.speed_features(gps, 1600, 800, 1180)  # trigger at 8 s, window end at 11.8 s
    assert f["speed_pre"] == pytest.approx(np.median([50, 48, 40, 10]))  # samples at 5, 6, 7, 8 s
    assert f["drop"] == pytest.approx(f["speed_pre"] - 0.0)  # sample nearest 11.8 s is j = 12
    assert f["gps_missing"] == 0.0
    f2 = L.speed_features(gps, 1600, 800, 1180)
    assert f2["rel_drop"] == pytest.approx(f2["drop"] / f2["speed_pre"])


def test_speed_features_sign_and_clipping():
    gps = np.array([1.0] * 8 + [30.0] * 8)  # speed rises: negative drop
    f = L.speed_features(gps, 1600, 600, 1000)
    assert f["drop"] < 0
    gps2 = np.array([0.5] * 8 + [40.0] * 8)  # small pre-speed: the relative drop uses at least 1
    f2 = L.speed_features(gps2, 1600, 600, 1000)
    assert f2["rel_drop"] == pytest.approx(-2.0) and f2["speed_pre"] == 0.5
    gps3 = np.array([0.5] * 8 + [0.9] * 8)
    f3 = L.speed_features(gps3, 1600, 600, 1000)
    assert f3["rel_drop"] == pytest.approx((0.5 - 0.9) / 1.0)


def test_speed_features_missing_gps():
    assert L.speed_features(np.array([5.0]), 1600, 800, 1100)["gps_missing"] == 1.0
    assert L.speed_features(np.array([5.0, np.nan, 3.0]), 1600, 800, 1100)["gps_missing"] == 1.0
    assert L.speed_features(np.zeros(0), 1600, 800, 1100)["gps_missing"] == 1.0


def test_speed_pre_falls_back_to_the_nearest_earlier_sample():
    gps = np.array([10.0, 20.0, 30.0, 40.0])  # k = 4 over 16 s: samples at 0, 4, 8, 12 s
    f = L.speed_features(gps, 1600, 1000, 1400)  # trigger at 10 s: samples in [7, 10] -> the one at 8 s
    assert f["speed_pre"] == 30.0
    f = L.speed_features(gps, 1600, 1500, 1900)  # trigger at 15 s: sample at 12 s lies in [12, 15]
    assert f["speed_pre"] == 40.0
    f = L.speed_features(gps, 1600, 1100 + 0, 1500)  # trigger at 11 s: window [8, 11] holds the 8 s sample
    assert f["speed_pre"] == 30.0
    g2 = np.array([10.0, 20.0, 30.0, 40.0])
    f = L.speed_features(g2, 4000, 2500, 2900)  # k = 4 over 40 s: samples at 0, 10, 20, 30 s; trigger at 25 s: window [22, 25] is empty
    assert f["speed_pre"] == 30.0  # the nearest earlier sample is the one at 20 s (the third sample)


def _quiet_event(n=1600):
    acc = np.tile([0.0, 0.0, 1.0], (n, 1))
    gyro = np.zeros((n, 3))
    return acc, gyro


def test_post_features_quiet_event():
    acc, gyro = _quiet_event()
    f = L.post_features(acc, gyro, np.full(16, 30.0), 800, 2)
    assert f["quiet"] == 1.0 and f["orient"] == pytest.approx(0.0, abs=1e-3) and f["gyro_mean"] == 0.0 and f["log_rot_energy"] == 0.0
    assert f["drop"] == 0.0 and f["pad_after"] == 0.0


def test_post_features_orientation_change_and_energy():
    acc, gyro = _quiet_event()
    i0, w = 800, 2
    end, we = i0 + 180, i0 + 180 + 200
    th = math.radians(40)
    acc[we - 50 : we] = [math.sin(th), 0.0, math.cos(th)]  # the vehicle has tipped by 40 degrees in the last 0.5 s
    gyro[i0:we, 1] = 10.0  # 10 deg/s over the whole span from the trigger to the end of the window
    f = L.post_features(acc, gyro, np.full(16, 30.0), i0, w)
    assert f["orient"] == pytest.approx(40.0, abs=1e-6)
    assert f["log_rot_energy"] == pytest.approx(math.log1p(100.0 * (we - i0) / 100.0))
    assert f["gyro_mean"] == pytest.approx(10.0)
    assert f["quiet"] == pytest.approx(1.0)  # |a| is 1 g throughout
    acc2 = acc.copy()
    acc2[end : we - 50] = [0.0, 0.0, 1.3]  # not quiet in the first part; the last second is [we - 100, we)
    f2 = L.post_features(acc2, gyro, np.full(16, 30.0), i0, w)
    assert f2["quiet"] == pytest.approx(0.5, abs=0.02)


def test_post_features_use_only_their_window():
    """Property: samples before the pre-trigger second or after the end of the window change nothing; samples inside the stated ranges do."""
    rng = np.random.default_rng(0)
    acc = np.tile([0.0, 0.0, 1.0], (1600, 1)) + rng.normal(0, 0.01, (1600, 3))
    gyro = rng.normal(0, 1.0, (1600, 3))
    gps = np.linspace(40, 0, 16)
    i0, w = 600, 2
    base = L.post_features(acc, gyro, gps, i0, w)
    a2, g2 = acc.copy(), gyro.copy()
    a2[: i0 - 100] += 5.0
    g2[: i0] += 50.0  # gyro before the trigger is not used at all
    a2[i0 + 180 + 200 :] += 5.0
    g2[i0 + 180 + 200 :] += 50.0
    assert L.post_features(a2, g2, gps, i0, w) == base
    a3 = acc.copy()
    a3[i0 - 100 : i0] += [0.5, 0.0, 0.0]  # the pre-trigger second is used (reference direction)
    assert L.post_features(a3, gyro, gps, i0, w)["orient"] != base["orient"]
    g3 = gyro.copy()
    g3[i0 + 10] += 400.0  # inside [trigger, end of window): rotation energy
    assert L.post_features(acc, g3, gps, i0, w)["log_rot_energy"] > base["log_rot_energy"]


def test_post_features_window_length_and_padding():
    acc, gyro = _quiet_event(1000)
    f = L.post_features(acc, gyro, np.full(10, 20.0), 700, 3)  # 700 + 180 + 300 = 1180 > 1000
    assert f["pad_after"] == 1.0
    assert L.post_features(acc, gyro, np.full(10, 20.0), 300, 3)["pad_after"] == 0.0
    a2, g2 = _quiet_event(1600)
    a2[780 + 100 :, 2] = 1.2  # a 3 s window reaches the change, a 1 s window does not at i0 = 600: [780, 880) vs [780, 1080)
    f1 = L.post_features(a2, g2, np.full(16, 1.0), 600, 1)
    f3 = L.post_features(a2, g2, np.full(16, 1.0), 600, 3)
    assert f1["quiet"] == 1.0 and f3["quiet"] == 0.0


def test_design_fills_missing_and_keeps_column_order():
    post = pd.DataFrame({"event_id": [1, 2, 3]}).set_index("event_id")
    for w in L.WS:
        post[f"drop_w{w}"] = [1.0, np.nan, 3.0]
        post[f"rel_drop_w{w}"] = [0.1, np.nan, 0.3]
        post[f"speed_pre_w{w}"] = [10.0, np.nan, 30.0]
        post[f"gyro_mean_w{w}"] = [1.0, 2.0, 3.0]
        post[f"quiet_w{w}"] = [1.0, 0.5, 0.0]
        post[f"orient_w{w}"] = [0.0, 5.0, 10.0]
        post[f"log_rot_energy_w{w}"] = [1.0, 2.0, 9.0]
        post[f"gps_missing_w{w}"] = [0.0, 1.0, 0.0]
    X, fill = L.design(post, np.array([1, 2, 3]), np.array([0.1, 0.5, 0.9]), 2)
    assert list(fill) == L.FEATS and X.shape == (3, len(L.FEATS))
    assert X[1, L.FEATS.index("drop")] == pytest.approx(2.0) and fill["drop"] == pytest.approx(2.0)  # the median of 1 and 3
    assert X[1, L.FEATS.index("gps_missing")] == 1.0 and X[0, 0] == 0.1
    X2, _ = L.design(post, np.array([2]), np.array([0.5]), 2, {**fill, "drop": 7.0})
    assert X2[0, L.FEATS.index("drop")] == 7.0  # a given fill (the train medians) is used as it is
    skew = post.copy()
    skew["speed_pre_w2"] = [1.0, np.nan, 100.0]
    _X3, fill3 = L.design(skew, np.array([1, 2, 3]), np.array([0.1, 0.5, 0.9]), 2)
    assert fill3["speed_pre"] == pytest.approx(50.5)  # nanmedian of two values equals their mean here; see the next test for a skewed case
    sk2 = skew.copy()
    sk2.loc[2, "speed_pre_w2"] = 2.0
    sk3 = pd.concat([sk2, pd.DataFrame({c: [sk2[c].iloc[0]] for c in sk2.columns}, index=[4])])
    sk3.loc[4, "speed_pre_w2"] = 3.0
    _X4, fill4 = L.design(sk3, np.array([1, 2, 3, 4]), np.array([0.1, 0.2, 0.3, 0.4]), 2)
    assert fill4["speed_pre"] == pytest.approx(2.5)  # median of 1, 2, 3, 100 (a mean would be 26.5)


def test_fit_model_kinds_and_class_weight():
    rng = np.random.default_rng(1)
    X = rng.normal(0, 1, (600, len(L.FEATS)))
    y = (X[:, 0] + 0.3 * rng.normal(size=600) > 1.0).astype(int)  # imbalanced
    p_none = L.fit_model(X, y, L.L2Params()).predict_proba(X)[:, 1]
    p_bal = L.fit_model(X, y, L.L2Params(class_weight="balanced")).predict_proba(X)[:, 1]
    assert p_bal.mean() > p_none.mean() + 0.05  # balanced weights raise the scores of the rare class
    t = L.fit_model(X, y, L.L2Params(model="tree"))
    assert t.get_depth() <= 3 and t.min_samples_leaf == 50
    assert L.fit_model(X, y, L.L2Params()).predict_proba(X).shape == (600, 2)
    assert np.corrcoef(p_none, X[:, 0])[0, 1] > 0.6  # the model uses the detector score


def test_thr_for_recall_is_the_largest_threshold_that_meets_the_target():
    y = np.array([1] * 10 + [0] * 5)
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, -1.0] + [0.35, 0.3, 0.2, -1.0, -1.0])
    for target in (0.0, 0.2, 0.55, 0.6, 0.9, 1.0):
        t = L.thr_for_recall(y, s, target)
        assert L.recall_at(y, s, t) >= target - 1e-12 or target > 0.9  # one crash event is untriggered, so a recall of 1.0 cannot be met
        higher = np.nextafter(t, np.inf)
        if target <= 0.9 and target > 0:
            assert L.recall_at(y, s, higher) < target
    assert L.thr_for_recall(y, s, 0.55) == 0.4  # ceil(5.5) = 6 events: the sixth highest score
    assert L.thr_for_recall(y, s, 0.5) == 0.5


def test_recall_at_counts_untriggered_events_as_missed():
    y = np.array([1, 1, 1, 0])
    s = np.array([0.9, 0.8, -1.0, 0.7])
    assert L.recall_at(y, s, 0.5) == pytest.approx(2 / 3)


def test_rel_reduction_bootstrap():
    rng = np.random.default_rng(0)
    base = (rng.random(4000) < 0.30).astype(float)
    same = L.rel_reduction_boot(base, base)
    assert same["pt"] == 0.0 and same["lo"] <= 0.0 <= same["hi"] and same["p"] > 0.4
    half = base.copy()
    half[(base == 1) & (rng.random(4000) < 0.5)] = 0.0  # cancels half of the alarms
    r = L.rel_reduction_boot(base, half)
    assert 0.4 < r["pt"] < 0.6 and r["lo"] > 0.3 and r["p"] < 0.01
    assert L.rel_reduction_boot(base, np.zeros_like(base))["pt"] == pytest.approx(1.0)
    worse = np.maximum(base, (rng.random(4000) < 0.1).astype(float))
    assert L.rel_reduction_boot(base, worse)["pt"] < 0.0


def test_diff_bootstrap():
    d = np.r_[np.full(500, 1.0), np.zeros(500)]
    r = L.diff_boot(d)
    assert r["pt"] == 0.5 and r["lo"] < 0.5 < r["hi"] and r["p"] < 0.01
    z = L.diff_boot(np.zeros(100))
    assert z["pt"] == 0.0 and z["p"] > 0.99


def _toy(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.3).astype(int)
    label = np.where(y == 1, 0, np.where(rng.random(n) < 0.4, 1, 2))
    h1 = rng.random(n) < 0.5
    E = rng.random(n) < 0.4
    F_base = (E & (rng.random(n) < 0.8)) | (y == 1) & (rng.random(n) < 0.6)
    return y, label, h1, E, F_base


def test_heldout_stats_selects_the_half_and_the_classes():
    y, label, h1, E, F_base = _toy()
    r = L.heldout_stats(F_base, F_base, F_base, E, y, label, h1)
    assert r["n_half1"] == int(h1.sum()) and r["n_crash"] == int(((y == 1) & h1).sum()) and r["n_nearmiss"] == int(((label == 1) & h1).sum())
    assert r["b"]["n_prov"] == int((E & h1).sum()) and r["a"]["pt"] == 0.0
    r0 = L.heldout_stats(F_base, F_base, F_base, E, y, label, ~h1)
    assert r0["n_half1"] == int((~h1).sum()) and r0["n_crash"] == int(((y == 1) & ~h1).sum())


def test_heldout_stats_criteria_and_directions():
    y, label, h1, E, F_base = _toy(8000, 1)
    nm = label == 1
    F_a = F_base.copy()
    F_a[nm & F_base & (np.arange(len(y)) % 2 == 0)] = False  # cancels about half of the near-miss alarms, no crash is lost
    r = L.heldout_stats(F_base, F_a, F_base, E, y, label, h1)
    assert r["a"]["pt"] > 0.25 and r["a"]["criterion_met"] and r["a"]["recall_l2"] == r["a"]["recall_base"]
    F_lose = F_a.copy()
    F_lose[(y == 1) & F_lose & (np.arange(len(y)) % 5 == 0)] = False  # loses recall: the criterion fails although the reduction holds
    r2 = L.heldout_stats(F_base, F_lose, F_base, E, y, label, h1)
    assert r2["a"]["pt"] > 0.25 and not r2["a"]["criterion_met"]
    F_small = F_base.copy()
    F_small[nm & F_base & (np.arange(len(y)) % 20 == 0)] = False  # a reduction of a few per cent: below 25%
    assert not L.heldout_stats(F_base, F_small, F_base, E, y, label, h1)["a"]["criterion_met"]
    # H-L2b: confirming provisional alerts that the baseline retracts lowers the retraction share
    F_b = F_base.copy()
    F_b[E & ~F_base & (np.arange(len(y)) % 2 == 0)] = True
    rb = L.heldout_stats(F_base, F_base, F_b, E, y, label, h1)["b"]
    assert rb["pt"] > 0.03 and rb["criterion_met"] and rb["rescued"] > 0 and rb["cancelled_more"] == 0
    F_c = F_base.copy()
    F_c[E & F_base & (np.arange(len(y)) % 2 == 0)] = False  # cancelling more raises the share: negative fall
    rc = L.heldout_stats(F_base, F_base, F_c, E, y, label, h1)["b"]
    assert rc["pt"] < 0 and not rc["criterion_met"] and rc["cancelled_more"] > 0 and rc["rescued"] == 0


def test_iteration_table_matches_v16():
    d = L.L2Params()
    assert (d.w, d.model, d.class_weight, d.alpha) == (2, "logistic", "none", 0.01)
    assert len(L.ITERATIONS) <= 5 and L.ITERATIONS[0] == d
    assert {it.w for it in L.ITERATIONS} <= {1, 2, 3} and {it.model for it in L.ITERATIONS} <= {"logistic", "tree"}
    assert L.FEATS[0] == "s_F" and len(L.FEATS) == 9


DET = ROOT / "data" / "processed" / "r5_det_seed42.pkl"
POSTF = ROOT / "data" / "processed" / "r5_l2_post.parquet"


@pytest.mark.skipif(not (DET.exists() and POSTF.exists()), reason="detector cache or post-event cache not built")
def test_baseline_reproduces_round3_retraction_numbers():
    """Known answer: the baseline arms reproduce r3.t3.a1 and r3.t3.a5 (provisional alarms and retraction share) on the full test split. This reads no L2 result."""
    from crashguard import r5_det as D

    res = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8")) if e["name"].startswith("r3.t3.a")}
    fr = D.load_frames()
    det = D.fit_seed(42, fr)
    for alpha, tag in ((0.01, "a1"), (0.05, "a5")):
        b = L.baseline_arms(42, alpha, fr, det)
        E, F = b["E_te"], b["F_te"] >= b["thr_f"]
        assert int(E.sum()) == res[f"r3.t3.{tag}.n_provisional_alarms"]
        assert round(float((E & ~F).sum() / E.sum()), 6) == res[f"r3.t3.{tag}.retraction_share"]


@pytest.mark.skipif(not (DET.exists() and POSTF.exists()), reason="detector cache or post-event cache not built")
def test_cache_covers_every_triggered_event_and_the_trigger_matches_the_window():
    """The post-event cache has a row for every triggered event of the three splits, and its trigger index is the one of the cached window (window sample PRE_N is the trigger sample)."""
    from crashguard import config as C
    from crashguard import windows_cache as W

    det = pickle.loads(DET.read_bytes())
    post = L.load_post()
    for k in ("ids_tr", "ids_va", "ids_te"):
        assert pd.Index(det[k]).isin(post.index).all()
    d = W.load("validation")
    i = 7
    eid = int(d["event_id"][i])
    mag = np.linalg.norm(d["acc"][i], axis=1)
    assert mag[C.PRE_N] > C.TRIGGER_G and (mag[: C.PRE_N] <= C.TRIGGER_G).all()
    assert 0 <= int(post.loc[eid, "i0"]) < int(post.loc[eid, "n"])


def test_pre_trigger_reference_uses_the_whole_second():
    acc, gyro = _quiet_event()
    base = L.post_features(acc, gyro, np.full(16, 30.0), 800, 2)["orient"]
    a2 = acc.copy()
    a2[700:750] += [0.6, 0.0, 0.0]  # only the older half of the pre-trigger second
    assert L.post_features(a2, gyro, np.full(16, 30.0), 800, 2)["orient"] > base + 1.0


def test_criteria_need_a_lower_limit_and_the_margin():
    n = 12
    y = np.array([1] * 4 + [0] * 8)
    label = np.array([0] * 4 + [1] * 8)
    h1 = np.ones(n, bool)
    E = np.zeros(n, bool)
    F_base = np.array([True] * 4 + [True, True, True, False, False, False, False, False])
    F_a = np.array([True] * 4 + [True, False, False, False, False, False, False, False])  # near-miss alarms 3 -> 1 of 8 in a tiny sample
    r = L.heldout_stats(F_base, F_a, F_base, E, y, label, h1)
    assert r["a"]["pt"] > 0.25 and r["a"]["lo"] <= 0 and not r["a"]["criterion_met"]  # the point estimate is not enough
    # a fall of 1 point is significant in a big sample but below the margin of 3 points
    rng = np.random.default_rng(5)
    m = 40000
    E2 = np.ones(m, bool)
    Fb = rng.random(m) < 0.8
    Fc = Fb | (rng.random(m) < 0.05)  # confirms 1 point of the 20% retractions' complement: fall of about 0.01
    y2 = (rng.random(m) < 0.1).astype(int)
    rb = L.heldout_stats(Fb, Fb, Fc, E2, y2, np.full(m, 2), np.ones(m, bool))["b"]
    assert 0.005 < rb["pt"] < 0.03 and rb["lo"] > 0 and not rb["criterion_met"]
