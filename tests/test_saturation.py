"""N14 saturation-aware estimator: shapes, fill rules, ridge correction and the float32 mirror of the C code (synthetic signals only)."""
import numpy as np
import pytest

from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import severity as S
from crashguard import severity_synth as Y
from crashguard.c_mirror import sat_mirror

FS = float(C.FS_HZ)


@pytest.mark.parametrize("fam", SAT.FAMILIES)
def test_shapes_peak_at_one_and_vanish_outside(fam):
    u = np.linspace(0.0, 1.0, 1001)
    s = SAT.shape(fam, u)
    assert s.max() == pytest.approx(1.0, abs=1e-6) and s[0] == pytest.approx(0.0, abs=1e-9) and s[-1] == pytest.approx(0.0, abs=1e-9)
    assert SAT.shape(fam, np.array([-0.1, 1.1])).tolist() == [0.0, 0.0]


def _clipped(shape="half_sine", A=60.0, T=0.1, rng_g=16.0, seed=1):
    return Y.make_window(shape, A, T, 0.0, FS, np.random.default_rng(seed), noise_g=0.0, tilt_deg=0.0, clip_g=rng_g)


def test_unsaturated_pulse_is_returned_unchanged():
    acc, trig = Y.make_window("half_sine", 8.0, 0.1, 0.0, FS, np.random.default_rng(0), noise_g=0.0, tilt_deg=0.0)
    out, info = SAT.fill(acc, trig, FS, 16.0)
    assert not info.saturated and not info.applied and np.array_equal(out, acc)


@pytest.mark.parametrize("shape", ["half_sine", "triangular"])
def test_fill_recovers_most_of_the_delta_v_lost_to_clipping(shape):
    acc, trig = _clipped(shape, A=40.0, T=0.12)
    truth = Y.dv_truth_ms(shape, 40.0, 0.12) * 3.6
    base = S.severity(acc, FS, trig)["dv_res_kmh"]
    filled, info = SAT.severity_filled(acc, FS, trig, 16.0, "half_sine" if shape == "half_sine" else "triangle", sat_frac=0.9)
    assert info.saturated and info.applied
    assert base < 0.8 * truth  # clipping at 16 g removes area
    assert abs(filled["dv_res_kmh"] - truth) < abs(base - truth)  # the fill brings it closer
    assert abs(filled["dv_res_kmh"] - truth) / truth < 0.15


def test_fill_never_lowers_a_sample_and_keeps_direction():
    acc, trig = Y.make_window("half_sine", 30.0, 0.16, 35.0, FS, np.random.default_rng(3), noise_g=0.0, tilt_deg=0.0, clip_g=16.0)
    out, info = SAT.fill(acc, trig, FS, 16.0, "half_sine", sat_frac=0.9)
    assert info.applied
    a0, a1 = S.remove_baseline(acc, trig)[:, :2], S.remove_baseline(out, trig)[:, :2]
    h0, h1 = np.hypot(*a0.T), np.hypot(*a1.T)
    assert (h1 >= h0 - 1e-9).all()
    m = h0 > 1.0
    assert np.allclose(a0[m] / h0[m, None], a1[m] / h1[m, None], atol=1e-6)  # same direction


def test_fit_needs_three_unsaturated_samples():
    h = np.full(40, 20.0)
    sat = np.ones(40, bool)
    sat[10:12] = False
    assert SAT.fit_pulse(h, 5, 30, sat, FS, "half_sine", 16.0) is None


def test_ridge_correction_recovers_a_linear_relation_and_shrinks_with_alpha():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 3)) * [10, 0.1, 30] + [40, 0.3, 150]
    y = 0.2 + 0.05 * (X[:, 0] - 40) / 10 - 0.03 * (X[:, 2] - 150) / 30 + rng.normal(0, 0.005, 200)
    weak = SAT.RidgeCorrection(0.01).fit(X, y)
    strong = SAT.RidgeCorrection(1000.0).fit(X, y)
    assert np.abs(weak.predict(X) - y).mean() < 0.01
    assert np.abs(strong.w).sum() < np.abs(weak.w).sum() and strong.b == pytest.approx(y.mean())
    assert weak.factor(X[:2]).shape == (2,)


def test_float32_mirror_of_the_c_code_matches_the_python_reference():
    model = dict(family="triangle", sat_frac=0.7, mu=[40.0, 0.3, 150.0], sd=[15.0, 0.15, 45.0], w=[-0.06, -0.08, 0.06], b=0.15)
    for shape, A, T in (("half_sine", 60.0, 0.1), ("triangular", 40.0, 0.12), ("half_sine", 8.0, 0.08), ("square", 30.0, 0.06)):
        acc, trig = _clipped(shape, A, T, seed=4)
        ref = SAT.severity_sat(acc, FS, trig, 16.0, model)
        mir = sat_mirror(acc.astype(np.float32), trig, FS, model, 16.0, SAT.FAMILIES.index("triangle"))
        for k in ("dv_baseline_kmh", "dv_fill_kmh", "dv_fill_corrected_kmh", "asi_fill"):
            assert mir[k] == pytest.approx(ref[k], rel=2e-3, abs=2e-3), (shape, k)
        assert mir["applied"] == ref["applied"] and mir["saturated"] == ref["saturated"]
