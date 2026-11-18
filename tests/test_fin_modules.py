"""Tests of the finishing-branch modules (synthetic generator, surrogate windows, simulation helpers, world features)."""
import numpy as np
import pandas as pd
import pytest

from crashguard import fin_sim as FS
from crashguard import fin_surr as SU
from crashguard import fin_synth as G
from crashguard import world_sim as W


@pytest.fixture(scope="module")
def par():
    df = pd.read_parquet("data/processed/f_real_desc.parquet")
    return G.fit(df.to_dict("records"), df["mode"].tolist())


def test_generator_is_deterministic_and_shaped(par):
    a, b = G.make_pulse(par, "frontal_barrier", 7), G.make_pulse(par, "frontal_barrier", 7)
    assert np.array_equal(a["acc"], b["acc"])
    assert a["acc"].shape == (6000, 3) and a["fs0"] == 10000.0
    d = G.descriptors(a)
    assert d is None or (d["peak_g"] > 0 and 0 <= d["asym"] <= 1)
    c = G.make_pulse(par, "frontal_barrier", 8)
    assert not np.array_equal(a["acc"], c["acc"])


def test_generator_shift_raises_peak(par):
    base = np.median([G.make_pulse(par, "other", 100 + k)["peak_g"] for k in range(60)])
    up = np.median([G.make_pulse(par, "other", 100 + k, dict(shift=0.5))["peak_g"] for k in range(60)])
    assert up > base * 1.3


def test_surrogate_windows_trigger_and_class_share():
    rng = np.random.default_rng(0)
    acc = rng.normal(0, 0.05, (200, 280, 3)).astype(np.float32)
    acc[:, :, 2] += 1.0
    acc[:100, 100:140, 0] += 6.0
    gyro = rng.normal(0, 0.05, (200, 280, 3)).astype(np.float32)
    y = np.r_[np.ones(100, int), np.zeros(100, int)]
    par = SU.fit(acc, gyro, y)
    a, g, yl = SU.sample(par, 20, 1)
    assert a.shape == (20, 280, 3) and g.shape == a.shape
    base = a[:, : SU.PRE - 5].mean(1)
    assert (np.linalg.norm(a[:, SU.PRE] - base, axis=1) >= 1.9).all()  # the event component at the trigger sample is at about 2 g or more (gravity and the baseline vector are not part of it)


def test_p_value_rule_and_gain_logic():
    assert FS.q_p([0.001, 0.5, 0.9, 0.9, 1.0], 0.6) == 0.9
    st = dict(pt=0.06, lo=0.01, hi=0.1)
    assert FS.gains(st) and not FS.loses(st)
    assert FS.loses(dict(pt=-0.03, lo=-0.05, hi=0.0))
    d = FS.boot_diff(np.full(30, 0.1))
    assert d["lo"] > 0 and d["p_gain"] <= 0.1


def test_world_features_run_and_respect_duty():
    from crashguard import fin_g as GG

    cell = dict(name="t", n=60, p=0.2, sf=8, duty=0.01, b=15)
    pools = FS.lowered_pools(16.0)
    t = FS.tuned()
    for world in (dict(geom=GG.GEOM), dict(geom=GG.GEOM, slot={}), dict(geom=GG.GEOM, lbt={}), dict(geom=GG.GEOM, relay={}), dict(geom=GG.GEOM, channels=3, rx_delay_s=1.0, cr=4)):
        cfg = GG.cfg_for("P3", cell, 8000, 0, pools, t, "t", world=world)
        o = W.simulate(cfg)
        assert o["duty_exceeded"] == 0
        assert 0.0 <= o["reach10_critical"] <= 1.0
