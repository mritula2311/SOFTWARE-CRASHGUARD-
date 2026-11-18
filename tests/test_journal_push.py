"""Unit tests of the journal-push modules (small synthetic inputs; no NHTSA or VZCrash files needed)."""
from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestClassifier

from crashguard import jp_common
from crashguard import sel_parts as SP
from crashguard import vz_audit as V
from crashguard import x1_fixedpoint as X1
from crashguard import x5_rank as X5
from crashguard import x7_fusion as X7
from crashguard import x8_sequential as X8


def test_prefix_guard_rejects_foreign_keys():
    with pytest.raises(ValueError):
        jp_common.record_jp([dict(name="v2.foo", value=1, unit="", origin="MEASURED_SOFTWARE", source_file="x")], ("x.",))
    with pytest.raises(ValueError):
        jp_common.record_jp([], ("n14x.",))


def test_float_traversal_reproduces_sklearn_and_quantising_is_close():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(600, 5))
    y = (X[:, 0] + 0.5 * X[:, 1] > 0).astype(int)
    m = RandomForestClassifier(n_estimators=6, max_depth=5, random_state=0).fit(X, y)
    lo, hi = X.min(0), X.max(0)
    p_float = X1.predict(X1.quantise(m, lo, hi, None), X)
    assert np.abs(p_float - m.predict_proba(X)[:, 1]).max() < 1e-12
    p16 = X1.predict(X1.quantise(m, lo, hi, 16), X)
    p8 = X1.predict(X1.quantise(m, lo, hi, 8), X)
    assert np.abs(p16 - p_float).max() <= np.abs(p8 - p_float).max() + 1e-12
    assert np.abs(p16 - p_float).mean() < 0.01


def test_rank_correlation_matches_scipy_and_kappa_is_one_for_perfect_agreement():
    rng = np.random.default_rng(1)
    a, b = rng.normal(size=50), rng.normal(size=50)
    a[:5] = a[5:10]  # ties
    assert abs(float(X5.rho(a, b)) - spearmanr(a, b)[0]) < 1e-12
    c = np.array([0, 1, 2, 3, 2, 1, 0, 3])
    assert X5.kappa_lin(c, c) == pytest.approx(1.0)


def test_sequential_rule_stops_early_on_strong_evidence_and_waits_otherwise():
    S = np.array([[0.99, 0.99, 0.99, 0.99, 0.99, 0.99], [0.01, 0.01, 0.01, 0.01, 0.01, 0.01], [0.3, 0.3, 0.3, 0.3, 0.3, 0.9]])
    alarm, t = X8.seq_decisions(S, 0.2, np.full(5, 3.0), 4.0, 0.5)
    assert alarm.tolist() == [True, False, True]
    assert t[0] == 50 and t[1] <= 200 and t[2] == 1800


def test_near_duplicate_scan_finds_exact_copy_and_ignores_noisy_copy():
    rng = np.random.default_rng(2)
    ref = rng.normal(size=(20, 40, 3)).astype(np.float32)
    q = np.stack([ref[3].copy(), ref[5] + rng.normal(0, 0.05, ref[5].shape).astype(np.float32), rng.normal(size=(40, 3)).astype(np.float32)])
    best, both, corr_only, md = V.near_dups(q, ref)
    assert both.tolist() == [True, False, False]
    assert md[0] == 0.0 and best[0] > 0.999


def test_datasheet_table_values():
    assert SP.BY_KEY["kx134"].mg_per_lsb[16] == pytest.approx(1000 / 2048)
    assert SP.BY_KEY["adxl345"].bw_hz(3200) == 1600
    assert SP.BY_KEY["mpu6050"].bw_hz(100) == 260
    assert SP.BY_KEY["adxl375"].noise_ug_rthz is None


def _pulse_sig(peak_g: float = 60.0, dur_s: float = 0.04, fs0: float = 10000.0) -> dict:
    t = np.arange(0.0, 0.5, 1.0 / fs0)
    a = np.zeros((len(t), 3))
    on = (t > 0.05) & (t < 0.05 + dur_s)
    a[on, 0] = -peak_g * np.sin(np.pi * (t[on] - 0.05) / dur_s)
    return dict(t=t, acc=a, fs0=fs0)


def test_fusion_recovers_clipped_pulse_better_than_low_range_alone():
    sig = _pulse_sig()
    lo, hi = ("lis3dh", 16, 1250), ("h3lis331dl", 200, 1000)
    y, fs, info = X7.fuse_signal(sig, lo, hi, 1, 0.5, 3)
    dv_fused, _ = X7.dv_of(y, fs)
    dv_low, _ = X7.dv_of(info["yl"], fs)
    ref = 2 * 60.0 * 0.04 / np.pi * 9.80665 * 3.6
    assert dv_low < 0.8 * ref
    assert abs(dv_fused - ref) / ref < 0.25
