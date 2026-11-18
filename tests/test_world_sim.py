"""world_sim with every new option off reproduces sct_sim exactly (SIMULATED)."""
from crashguard import s11_sct as S
from crashguard import sct_sim as A
from crashguard import world_sim as W
from crashguard.sct_sim import SctParams


def _cfg(mod, pol, burst, n=60, seed=3000):
    pools = S.load_pools()
    c = S.make_cfg(pol, 16.0, dict(n=n), burst, seed, 1, pools, SctParams(h_s=2.0, rho_f=0.35, sf_raise=True), 0.25, "t")
    return c if mod is A else W.SCfg(**{**c.__dict__, "sct": W.SctParams(**c.sct.__dict__)})


def test_identical_to_sct_sim():
    for pol in ("P0", "P1", "P2", "P3", "P4", "sched"):
        for burst in (False, True):
            a = A.simulate(_cfg(A, pol, burst))
            b = W.simulate(_cfg(W, pol, burst))
            for k, v in a.items():
                assert (v == b[k]) or (v != v and b[k] != b[k]), (pol, burst, k, v, b[k])
