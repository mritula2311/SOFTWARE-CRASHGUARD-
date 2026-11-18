"""Release blocks P and A: the physics generator integrates sensible pulses, the bounded model check finds what it should, the simulator features are inert when off."""
import numpy as np
import pandas as pd

from crashguard import pa_model as PM
from crashguard import ph_gates as PGT
from crashguard import ph_gen as PG
from crashguard import world_sim as W
from crashguard.fin_sim import p1plus_params


def _par():
    rows = pd.DataFrame(dict(mode=["frontal_barrier"] * 20, v=np.linspace(55, 65, 20), ref=np.linspace(60, 72, 20), ux=np.ones(20), uy=np.zeros(20)))
    base = PG._measured(rows, "frontal_barrier")
    x0 = PG._x0(pd.DataFrame(dict(peak_g=[45.0])), "a")
    return {"m": dict(base, h=dict(zip(PG.HYPER, [float(x) for x in x0])))}


def test_physics_pulse_conserves_momentum_and_energy():
    par = _par()
    sigs, diag = PG.make_batch(par, "m", 16, 3, "a", with_diag=True)
    assert len(sigs) == 16 and np.isfinite(sigs[0]["acc"]).all()
    chk = PGT.physical_checks(diag, "frontal_barrier")
    for k in ("integral", "restitution", "energy", "complete"):
        assert np.mean(chk[k]) > 0.8, k  # most pulses pass the integration checks
    s = diag["s"]
    dv = diag["clean"].sum(1) * PG.DT * PG.G0
    assert np.allclose(dv, s["kappa"] * (s["v0"] - s["u_end"]), rtol=0.1)


def test_model_check_finds_forged_event_ack_only_with_key():
    assert not PM.check("osdr", False)["violated"]["S4"]
    r = PM.check("osdr", True)
    assert r["violated"]["S4"] and r["attacker_actions_S4"] == 1
    assert PM.check("baseline", True)["attacker_actions_S4"] == 2
    n = PM.check("osdr_n", True)["violated"]
    assert not n["S2"] and not n["S3"]  # the initial send is never delayed; a retry is enabled at the deadline guard


def test_pa_features_inert_when_absent():
    def run(world):
        cfg = W.SCfg(n=20, sf=8, policy="sct", seed=5, hour=0, duty=0.01, hb_period_s=1e9, burst=True, burst_cars=5, sct=p1plus_params(2.0), true_pool=np.array([3]), assigned_pool=np.array([3]),
                     crash_pool=np.array([0.3]), duration_s=800.0, label="t", world=world)
        r = W.simulate(cfg)
        return r["reach10_critical"], r["al_tx"], r["ack_sent"]

    assert run(None) == run({})
    assert run({"pa": dict(mode="osdr", N=2)})[0] >= 0.0  # runs without error
