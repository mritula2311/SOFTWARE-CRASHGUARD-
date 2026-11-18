import numpy as np

from crashguard.neardup import scan


def _w(rng, n):
    t = np.linspace(0, 1, 280)[None, :, None]
    return (1.0 + 3 * np.exp(-((t - rng.uniform(.3, .6, (n, 1, 3))) ** 2) / 0.002) * rng.uniform(1, 3, (n, 1, 3)) + 0.01 * rng.standard_normal((n, 280, 3))).astype(np.float32)


def test_exact_copy_and_small_noise_are_flagged_and_others_are_not():
    rng = np.random.default_rng(0)
    ref = _w(rng, 40)
    q = np.concatenate([ref[3:4], ref[7:8] + 0.002 * rng.standard_normal((1, 280, 3)).astype(np.float32), _w(rng, 3)])
    r = scan(q, ref)
    assert r["both"][0] and r["both"][1] and not r["both"][2:].any()
    assert r["max_corr"][0] > 0.9999 and r["min_maxdiff"][0] == 0.0
    assert np.isinf(r["min_maxdiff"][2:]).all()


def test_quiet_windows_with_a_common_offset_are_not_flagged_by_the_offset_alone():
    rng = np.random.default_rng(1)
    base = np.zeros((10, 280, 3), np.float32)
    base[..., 2] = 1.0
    ref = base + 0.02 * rng.standard_normal(base.shape).astype(np.float32)
    q = base[:3] + 0.02 * rng.standard_normal((3, 280, 3)).astype(np.float32)
    r = scan(q, ref)
    assert not r["both"].any() and (r["max_corr"] < 0.99).all()


def test_pair_must_meet_both_thresholds_for_the_same_reference():
    rng = np.random.default_rng(2)
    ref = _w(rng, 5)
    q = ref[:1] + 0.05  # a constant shift: correlation 1, maximum difference 0.05 g
    r = scan(q, ref)
    assert r["corr_only"][0] and not r["diff_only"][0] and not r["both"][0]
