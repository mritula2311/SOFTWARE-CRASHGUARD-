import dataclasses
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crashguard import config as C
from crashguard import v2_common as VC
from crashguard import v2_f_study as VF


def test_holm_is_a_step_down_correction():
    adj = VC.holm({"a": 0.001, "b": 0.01, "c": 0.04, "d": 0.5})
    assert adj["a"] == pytest.approx(0.004) and adj["b"] == pytest.approx(0.03) and adj["c"] == pytest.approx(0.08) and adj["d"] == pytest.approx(0.5)
    assert all(adj[k] >= p for k, p in {"a": 0.001, "b": 0.01, "c": 0.04, "d": 0.5}.items())


def test_v2_writer_refuses_keys_outside_the_v2_prefix():
    with pytest.raises(ValueError):
        VC.record_v2([dict(name="s11.x", value=1, unit="x", origin="SIMULATED", source_file="x", notes="")], ("v2.x.",))
    with pytest.raises(ValueError):
        VC.record_v2([dict(name="v2.x.y", value=1, unit="x", origin="SIMULATED", source_file="x", notes="")], ("s11.",))


def test_cost_model_crossing_and_hold_grid():
    p = 0.0043
    cross = 0.9 * (1 - p) / (4 * p)
    assert VF.optimal_hold(cross * 0.9, p) == 4.0 and VF.optimal_hold(cross * 1.1, p) == 0.0
    assert VF.R_of(0.0) == 1.0 and VF.R_of(4.0) == pytest.approx(0.1) and VF.R_of(5.0) == pytest.approx(0.1)


def test_forgery_work_factor_follows_the_tag_length():
    from crashguard.v2_e_study import forgery_table

    t = forgery_table()
    t8 = t[(t.tag_bytes == 8) & (t.sf == 7)].iloc[0]
    assert t8.expected_attempts_log2 == 63 and abs(t8.log2_attempts_for_1e6 - (64 + math.log2(1e-6))) < 1e-6
    t4 = t[(t.tag_bytes == 4) & (t.sf == 7)].iloc[0]
    assert abs(t4.log2_attempts_for_1e6 - math.log2(4294.9)) < 0.05
    a = t[(t.tag_bytes == 8)].sort_values("sf").airtime_s.to_numpy()
    assert (np.diff(a) > 0).all()  # a higher spreading factor takes longer per frame


def test_trapezoid_and_shapes_peak_at_one():
    from crashguard.v2_clip import shape4

    u = np.linspace(0, 1, 101)
    for fam in ("half_sine", "haversine", "triangle", "trapezoid"):
        s = shape4(fam, u)
        assert abs(s.max() - 1.0) < 1e-9 and s[0] == pytest.approx(0.0, abs=1e-9) and s[-1] == pytest.approx(0.0, abs=1e-9)
    assert shape4("trapezoid", np.array([0.5]))[0] == 1.0 and shape4("trapezoid", np.array([1.2]))[0] == 0.0


def _nhtsa():
    from crashguard import severity_study as SS

    try:
        t = SS.load_tests()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"NHTSA data not available: {e}")
    if not t:
        pytest.skip("no NHTSA tests")
    return t


def test_grid_fit_reproduces_the_earlier_fill_for_the_triangle_family():
    from crashguard import saturation as SAT
    from crashguard import saturation_splits as SP
    from crashguard import v2_clip as V

    tests = _nhtsa()
    cells = SP.build_cells(tests)
    for i in (0, 6, 12):
        f = V.features_one(tests[i]["sig"], 16.0)
        assert f["dv_triangle"] == pytest.approx(float(cells[("m", 16.0, "triangle", 0.7, 0.1)][i]), abs=1e-6)
        assert f["dv_plain"] == pytest.approx(float(cells[("b", 16.0, 0.1)][i]), abs=1e-6)
    assert SAT.MIN_UNSAT == 3


def test_lower_bound_holds_for_nearly_all_tests():
    from crashguard import v2_clip as V

    d = V.build()
    for rg in (16.0, 32.0, 64.0):
        x = d[d.range_g == rg]
        assert (x.dv_plain > 1.05 * x.ref).sum() <= 8  # the plain estimate is a lower bound for at least 95% of the tests
        assert (x.dv_upper >= x.dv_plain - 1e-9).all()


def test_pool_escalation_never_rises_with_the_scale_and_matches_ua_pairs():
    from crashguard import v2_pools as VP

    try:
        p = VP.build(False)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"class folds not available: {e}")
    esc = [VP.esc_pool(p, float(s)) for s in VP.SCALES]
    assert all(b <= a + 1e-12 for a, b in zip(esc, esc[1:]))
    pairs = pd.read_csv(C.TABLES / "ua_pairs.csv")
    g = pairs[(pairs.alpha == 0.10) & (pairs.variant == "cc") & (pairs.range_g == 16.0)]
    assert (np.sort(g.c_hat.to_numpy()) == np.sort(p["point"])).all()


def test_simulator_extensions_leave_earlier_runs_and_the_static_path_unchanged():
    from crashguard import s11_sct as S
    from crashguard import v2_pools as VP
    from crashguard.sct_sim import SctParams, simulate

    f = C.TABLES / "s11_sct.csv"
    if not f.exists():
        pytest.skip("s11_sct.csv not available")
    try:
        vp = VP.build(False)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"class folds not available: {e}")
    params = SctParams(h_s=0.0, rho_f=0.35, sf_raise=True)
    pools = S.load_pools()
    R = pd.read_csv(f)
    # (1) the stored P2 run is reproduced bit for bit
    cfg = S.make_cfg("P2", 16.0, dict(S.BURST)["base"], True, S.EVAL_SEED, 0, pools, params, None, "burst_base")
    row = R[(R.range_g == 16.0) & (R["mode"] == "burst") & (R.scen == "base") & (R.pol == "P2") & (R.hour == 0)].iloc[0]
    out = simulate(cfg)
    for m in ("reach10_critical", "mis_triage", "node_air_share", "p95_lat_s_critical"):
        assert out[m] == pytest.approx(row[m], abs=1e-9)
    # (2) the dynamic class decision with a fixed scale of 1 equals the static path on the same pool
    cfg = dataclasses.replace(cfg, true_pool=vp["true"], assigned_pool=vp["point"])
    o1 = simulate(cfg)
    o2 = simulate(dataclasses.replace(cfg, dyn=dict(kind="fixed", s0=1.0), pool_cls=vp["pcls"], pool_scales=vp["scales"]))
    for m in ("reach10_critical", "reach30_critical", "mis_triage", "escalation", "node_air_share", "p95_lat_s_critical"):
        assert o1[m] == pytest.approx(o2[m], abs=1e-9)


def test_tag_length_changes_airtime_but_not_the_default():
    from crashguard import s11_sct as S
    from crashguard.sct_sim import SctParams, simulate

    pools = S.load_pools()
    cfg = S.make_cfg("P2", 16.0, dict(n=20), False, S.EVAL_SEED, 0, pools, SctParams(), None, "e")
    base = simulate(cfg)
    same = simulate(dataclasses.replace(cfg, alert_len=97, flash_len=14, ack_len=26))
    short = simulate(dataclasses.replace(cfg, alert_len=93, flash_len=10))
    assert base["node_air_s"] == pytest.approx(same["node_air_s"], abs=1e-12)
    assert short["node_air_s"] < base["node_air_s"]


def test_v2_documents_avoid_the_banned_words():
    for f in ("docs/03_results/V2_RESULTS.md", "docs/02_preregistration/PREREGISTRATION_V2.md"):
        p = Path(f)
        if p.exists():
            t = p.read_text(encoding="utf-8").lower()
            for w in ("first", "novel", "state-of-the-art", "state of the art"):
                assert not re.search(rf"\b{w}\b", t), (f, w)
