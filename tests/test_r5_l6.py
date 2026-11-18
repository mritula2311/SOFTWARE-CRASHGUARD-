"""Tests of the L6 module (V16 section 15.2). Synthetic inputs; one known-answer test reads the FARS 2021 file when present (the development year)."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crashguard import r5_l6 as L

ROOT = Path(__file__).resolve().parents[1]


def test_constants_follow_s2():
    assert L.DEV_YEARS == (2019, 2020, 2021) and L.HELD_YEAR == 2022 and L.KS == (50, 100, 200, 400) and L.R_COV == 4.0 and L.CELL_DEG == 0.02
    assert L.r_cov_km() == pytest.approx(3.981, abs=0.001) and L.r_cov_km(sens_dbm=-123.0) == pytest.approx(2.512, abs=0.001)


def test_xyz_norm_and_chord_distance():
    p = L.xyz(np.array([0.0, 45.0, 90.0]), np.array([0.0, 10.0, 0.0]))
    assert np.allclose(np.linalg.norm(p, axis=1), L.R_EARTH)
    a, b = L.xyz(np.array([40.0]), np.array([-100.0])), L.xyz(np.array([40.0 + 4.0 / 111.19]), np.array([-100.0]))
    assert np.linalg.norm(a - b) == pytest.approx(L.chord(4.0), rel=1e-3) and L.chord(4.0) < 4.0 and L.chord(4.0) == pytest.approx(4.0, rel=1e-6)


def test_greedy_picks_largest_gain_and_updates_overlaps():
    w = np.array([5.0, 1.0, 1.0, 4.0])
    cover = [np.array([0, 1]), np.array([1, 2]), np.array([3]), np.array([0, 1, 2])]
    assert L.greedy(cover, w, 1) == [3]  # covers 7 at once
    assert L.greedy(cover, w, 2) == [3, 2]  # the next gain is target 3 (4.0), not the overlapping sites
    ch = L.greedy(cover, w, 5)
    assert ch == [3, 2]  # nothing uncovered is left, so it stops
    assert L.greedy([np.array([], np.int64)], np.array([1.0]), 3) == []


def test_greedy_ties_go_to_the_lower_index_and_gain_is_non_increasing():
    cover = [np.array([0]), np.array([1]), np.array([2])]
    assert L.greedy(cover, np.ones(3), 3) == [0, 1, 2]
    rng = np.random.default_rng(0)
    cov = [np.unique(rng.integers(0, 60, rng.integers(1, 8))) for _ in range(40)]
    w = rng.uniform(1, 5, 60)
    ch = L.greedy(cov, w, 10)
    seen, gains = np.zeros(60, bool), []
    for i in ch:
        gains.append(w[cov[i][~seen[cov[i]]]].sum())
        seen[cov[i]] = True
    assert all(a >= b - 1e-9 for a, b in zip(gains, gains[1:]))
    assert len(set(ch)) == len(ch)


def test_covers_and_coverage_flags_boundary():
    g = L.xyz(np.array([40.0]), np.array([-100.0]))
    t = L.xyz(np.array([40.0, 40.0 + 3.9 / 111.19, 40.0 + 4.1 / 111.19]), np.array([-100.0, -100.0, -100.0]))
    assert list(L.coverage_flags(g, t, 4.0)) == [True, True, False]
    assert L.coverage_flags(np.zeros((0, 3)), t, 4.0).sum() == 0
    cv = L.covers(g, t, 4.0)
    assert sorted(cv[0].tolist()) == [0, 1]


def test_candidate_sites_use_only_the_given_crashes_and_places():
    cr = pd.DataFrame(dict(lat=[40.001, 40.005, 41.0], lon=[-100.001, -100.002, -90.0], w=[1.0, 1.0, 1.0]))
    pl = pd.DataFrame(dict(lat=[35.0], lon=[-90.5], w=[1e5]))
    s = L.candidate_sites(cr, pl)
    assert len(s) == 2 + 1  # two crashes share a cell
    assert ((s.lat - 40.01).abs() < 1e-9).sum() == 1 and ((s.lat - 35.0).abs() < 1e-9).sum() == 1


def test_grid_sites_returns_about_k_distinct_candidates():
    rng = np.random.default_rng(0)
    sites = pd.DataFrame(dict(lat=rng.uniform(25, 49, 3000), lon=rng.uniform(-124, -67, 3000)))
    for k in (20, 80):
        g = L.grid_sites(sites, k)
        assert len(set(g.tolist())) == len(g) and 0.6 * k <= len(g) <= k


def test_paired_bootstrap_and_criterion():
    rng = np.random.default_rng(1)
    base = rng.random(5000) < 0.3
    better = base | (rng.random(5000) < 0.15)
    r = L.paired_diff_boot(better, base)
    assert 0.08 < r["pt"] < 0.20 and r["lo"] > 0.06 and r["p"] < 0.01 and r["n"] == 5000
    z = L.paired_diff_boot(base, base)
    assert z["pt"] == 0 and z["p"] > 0.5
    good = {50: dict(pt=0.12, lo=0.1, p=0.001), 100: dict(pt=0.2, lo=0.1, p=0.01)}
    assert L.criterion(good) == (True, 0.01)
    assert L.criterion({**good, 200: dict(pt=0.0999, lo=0.05, p=0.0)})[0] is False
    assert L.criterion({**good, 200: dict(pt=0.3, lo=0.0, p=0.0)})[0] is False
    assert L.criterion({**good, 200: dict(pt=0.3, lo=0.1, p=0.2)}) == (True, 0.2)


def test_crash_weighted_beats_population_weighted_when_crashes_are_elsewhere():
    """Synthetic world: places in one cluster, crashes in another; the crash-weighted placement covers more of the crashes."""
    rng = np.random.default_rng(2)
    crash = pd.DataFrame(dict(lat=rng.normal(35, 0.05, 800), lon=rng.normal(-100, 0.05, 800), w=np.ones(800)))
    places = pd.DataFrame(dict(lat=rng.normal(45, 0.05, 50), lon=rng.normal(-80, 0.05, 50), w=rng.uniform(1e4, 1e5, 50)))
    sites = L.candidate_sites(crash, places)
    sx = L.xyz(sites.lat.to_numpy(), sites.lon.to_numpy())
    cc = L.covers(sx, L.xyz(crash.lat.to_numpy(), crash.lon.to_numpy()), 4.0)
    cp = L.covers(sx, L.xyz(places.lat.to_numpy(), places.lon.to_numpy()), 4.0)
    a, b = L.greedy(cc, crash.w.to_numpy(), 5), L.greedy(cp, places.w.to_numpy(), 5)
    cxyz = L.xyz(crash.lat.to_numpy(), crash.lon.to_numpy())
    assert L.coverage_flags(sx[a], cxyz, 4.0).mean() > L.coverage_flags(sx[b], cxyz, 4.0).mean() + 0.3


def test_fars_2021_loads_with_valid_coordinates():
    if not (ROOT / "data" / "raw" / "r5_fars" / "fars2021.zip").exists():
        pytest.skip("FARS file not downloaded")
    d = L.load_crashes(2021)
    assert 38000 < len(d) < 40500 and d.lat.between(24, 50).all() and d.lon.between(-125, -66).all() and (d.w >= 1).all()
    pl = L.load_places() if (ROOT / "data" / "raw" / "r5_fars" / "cities15000.zip").exists() else None
    if pl is not None:
        assert 3000 < len(pl) < 3400 and math.isfinite(pl.w.sum())


def test_fars_weights_are_fatalities():
    if not (ROOT / "data" / "raw" / "r5_fars" / "fars2021.zip").exists():
        pytest.skip("FARS file not downloaded")
    d = L.load_crashes(2021)
    assert d.w.sum() > 1.05 * len(d) and d.w.max() >= 3


def test_grid_sites_stay_inside_the_candidate_set_and_near_k():
    rng = np.random.default_rng(3)
    clustered = pd.DataFrame(dict(lat=rng.uniform(30, 31, 400), lon=rng.uniform(-100, -99, 400)))
    g = L.grid_sites(clustered, 50)
    assert (g >= 0).all() and (g < len(clustered)).all()  # no lattice point without a candidate within 100 km is used
    sites = pd.DataFrame(dict(lat=rng.uniform(25, 49, 4000), lon=rng.uniform(-124, -67, 4000)))
    for k in (30, 100):
        n = len(L.grid_sites(sites, k))
        assert 0.85 * k <= n <= k


def test_bootstrap_interval_brackets_the_estimate():
    rng = np.random.default_rng(4)
    base = rng.random(4000) < 0.3
    better = base | (rng.random(4000) < 0.12)
    r = L.paired_diff_boot(better, base)
    assert r["lo"] < r["pt"] - 0.003 < r["pt"] + 0.003 < r["hi"]


def test_place_all_uses_crashes_for_a_and_places_for_b(monkeypatch):
    rng = np.random.default_rng(5)
    crash = pd.DataFrame(dict(lat=rng.normal(35, 0.05, 600), lon=rng.normal(-100, 0.05, 600), w=np.ones(600)))
    places = pd.DataFrame(dict(lat=rng.normal(45, 0.05, 40), lon=rng.normal(-80, 0.05, 40), w=rng.uniform(1e4, 1e5, 40)))
    monkeypatch.setattr(L, "load_crashes", lambda y: crash)
    monkeypatch.setattr(L, "load_places", lambda: places)
    out = L.place_all(4.0, ks=(5,))
    cx = L.xyz(crash.lat.to_numpy(), crash.lon.to_numpy())
    px = L.xyz(places.lat.to_numpy(), places.lon.to_numpy())
    assert L.coverage_flags(out[5]["crash"], cx, 4.0).mean() > 0.2 and L.coverage_flags(out[5]["pop"], cx, 4.0).mean() == 0.0
    assert L.coverage_flags(out[5]["pop"], px, 4.0).mean() > 0.3 and set(out[5]) == {"crash", "pop", "grid"}
