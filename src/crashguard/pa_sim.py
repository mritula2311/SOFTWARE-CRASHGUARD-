"""Block A (SIMULATED): OS-DR, OS-DR-N, GS-CA and their baselines on the protocol simulator (docs/02_preregistration/PREREGISTRATION_V7.md section 3).

Grids, seeds, policies and the choice rules are fixed in the preregistration. Class pairs are the REAL out-of-fold pairs of the nested cross-validation (``fin_f3.pairs_from_cv``), so no synthetic pulse enters the
protocol study. The new features are switched on through ``world['pa']`` of ``world_sim`` (all off by default).

    python -m crashguard.pa_sim design      # DESIGN grid: best earlier policy and the design parameters (N, K); writes data/processed/pa_design.pkl and pa_design.json
    python -m crashguard.pa_sim held        # HELD-OUT grid with the design choices fixed
"""
from __future__ import annotations

import itertools
import json
import math
import pickle
import sys

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import fin_f1 as F1
from crashguard import fin_f3 as F3
from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard import s11_sct as S
from crashguard.lora import airtime_ms
from crashguard import packet as P
from crashguard.pp_ctx import Ctx

OUT = C.PROCESSED
DESIGN_A = dict(n=(75, 150), p=(0.1, 0.3), sf=(7, 9), duty=(0.01, 0.001), b=(1, 20), seed=16000)
HELD_A = dict(n=(100, 200), p=(0.2, 0.4), sf=(8, 10), duty=(0.01, 0.001), b=(1, 30), seed=18000)
HOURS = 30
N_CHOICES = (1, 2, 4, 8, 16, 32)
K_CAP_CHOICES = (1, 2, 4, 8, 16)
EARLIER = G.EARLIER
MECH = G.MECH
GUARD_S = 0.02
EPS_S = 0.005
DEADLINE_SLOTS_S = 8.0


def cells(g: dict) -> list[dict]:
    return [dict(name=f"{G.cell_name(n, p, sf, d)}_b{b}", n=n, p=p, sf=sf, duty=d, b=b)
            for n, p, sf, d, b in itertools.product(g["n"], g["p"], g["sf"], g["duty"], g["b"])]


def slot_len(sf: int) -> float:
    return airtime_ms(P.ALERT_LEN, sf) / 1000.0 + GUARD_S


def k_for(sf: int, k_cap: int) -> int:
    return int(max(1, min(k_cap, math.floor(DEADLINE_SLOTS_S / slot_len(sf)))))


def tamang_m(n_hat: int, K: int, trials: int = 20000, seed: int = 42) -> int:
    """Number of slots (uniform over the first m of K) that maximises the probability that at least one slot holds exactly one transmitter for n_hat transmitters (collision model without capture)."""
    rng = np.random.default_rng(seed)
    best, bm = -1.0, 1
    for m in range(1, K + 1):
        x = rng.integers(0, m, size=(trials, max(n_hat, 1)))
        ok = np.zeros(trials, bool)
        for s in range(m):
            ok |= (x == s).sum(1) == 1
        if ok.mean() > best + 1e-12:
            best, bm = float(ok.mean()), m
    return bm


def pools_real() -> dict:
    F3.RATIO_GRID = (0.0,)  # class pairs from REAL-ONLY estimates (mixing ratio 0): no synthetic training row influences the protocol study
    cx = Ctx()
    runs = pickle.loads(F1.OUT.read_bytes())
    pr = F3.pairs_from_cv(runs, cx)
    base = S.load_pools()
    return {**base, "classes": {16.0: dict(true=pr["true"].astype(int), point=pr["point"].astype(int), upper=pr["upper"].astype(int), lowered=pr["lowered_p3"].astype(int), abstain=pr["abstain"].astype(int))}}


def spec_world(spec: dict, cell: dict) -> dict:
    """World dictionary of a policy specification: ``kind`` is an earlier policy name or one of the new modes."""
    k = spec["kind"]
    base_world = {**G.WORLD, **spec.get("world_over", {})}
    if k in EARLIER:
        return base_world
    if k.startswith("P4+"):
        return {**base_world, **G.MECH[k.split("+")[1]]}
    pa = dict(mode=spec["kind"], eps=EPS_S, guard=GUARD_S, D_crit=10.0, D_sev=30.0)
    pa.update(spec.get("pa_over", {}))
    if spec["kind"] in ("osdr", "osdr_n"):
        pa.update(N=spec["N"], gamma=0.5)
    else:
        K = k_for(cell["sf"], spec["k_cap"])
        pa["K"] = K
        if spec["kind"] == "tamang":
            n_hat = spec.get("n_hat") or cell["b"]
            m = tamang_m(int(n_hat), K)
            pa["pvec"] = [1.0 / m] * m + [0.0] * (K - m)
    return {**base_world, "pa": pa}


def spec_pol(spec: dict) -> str:
    k = spec["kind"]
    if k in EARLIER:
        return k
    if k.startswith("P4+"):
        return "P4"
    return "P1+"


def make_jobs(g: dict, specs: dict, pools: dict, t: dict, hours: int = HOURS) -> list:
    jobs = []
    for cell in cells(g):
        for name, spec in specs.items():
            w = spec_world(spec, cell)
            for h in range(hours):
                c = G.cfg_for(spec_pol(spec), cell, g["seed"], h, pools, t, f"g_{cell['name']}", w)
                jobs.append((c, dict(cell=cell["name"], n=cell["n"], p=cell["p"], sf=cell["sf"], duty=cell["duty"], b=cell["b"], pol=name, hour=h)))
    return jobs


def earlier_specs() -> dict:
    d = {k: dict(kind=k) for k in EARLIER}
    d.update({"P4+lbt": dict(kind="P4+lbt"), "P4+slot": dict(kind="P4+slot"), "P4+relay": dict(kind="P4+relay")})
    return d


def mean_cells(R: pd.DataFrame, pol: str, metric: str) -> float:
    g = R[R.pol == pol].groupby("cell")[metric].mean()
    return float(g.mean())


def design() -> None:
    t = FS.tuned()
    pools = pools_real()
    des = {}
    # 1. earlier policies (including the block G mechanisms on top of P4)
    R0 = FS.run_jobs(make_jobs(DESIGN_A, earlier_specs(), pools, t))
    ok = [p for p in sorted(R0.pol.unique()) if int(R0[R0.pol == p].duty_exceeded.sum()) == 0]
    best = max(ok, key=lambda p: (round(mean_cells(R0, p, "reach10_critical"), 9), -mean_cells(R0, p, "node_air_share")))
    des["best_earlier"] = best
    des["earlier_mean_reach10_critical"] = {p: mean_cells(R0, p, "reach10_critical") for p in sorted(R0.pol.unique())}
    # 2. OS-DR: N
    specs = {f"osdr_N{n}": dict(kind="osdr", N=n) for n in N_CHOICES}
    R1 = FS.run_jobs(make_jobs(DESIGN_A, specs, pools, t))
    des["osdr_mean_reach10_critical"] = {p: mean_cells(R1, p, "reach10_critical") for p in specs}
    des["osdr_N"] = int(max(N_CHOICES, key=lambda n: (round(mean_cells(R1, f"osdr_N{n}", "reach10_critical"), 9), -n)))
    # 3. slotted variants: K cap
    specs2 = {}
    for kc in K_CAP_CHOICES:
        specs2[f"gsca_K{kc}"] = dict(kind="gsca", k_cap=kc)
        specs2[f"slot_aloha_K{kc}"] = dict(kind="slot_aloha", k_cap=kc)
        specs2[f"tamang_K{kc}"] = dict(kind="tamang", k_cap=kc)
    R2 = FS.run_jobs(make_jobs(DESIGN_A, specs2, pools, t))
    for fam in ("gsca", "slot_aloha", "tamang"):
        des[f"{fam}_mean_reach10_critical"] = {f"K{kc}": mean_cells(R2, f"{fam}_K{kc}", "reach10_critical") for kc in K_CAP_CHOICES}
        des[f"{fam}_k_cap"] = int(max(K_CAP_CHOICES, key=lambda kc: (round(mean_cells(R2, f"{fam}_K{kc}", "reach10_critical"), 9), -kc)))
    pd.concat([R0, R1, R2]).to_pickle(OUT / "pa_design.pkl")
    (OUT / "pa_design.json").write_text(json.dumps(des, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in des.items() if not k.endswith("mean_reach10_critical")}))


def held_specs(des: dict) -> dict:
    d = {"best_earlier": dict(kind=des["best_earlier"])}
    d["osdr"] = dict(kind="osdr", N=des["osdr_N"])
    d["osdr_n"] = dict(kind="osdr_n", N=des["osdr_N"])
    d["gsca"] = dict(kind="gsca", k_cap=des["gsca_k_cap"])
    d["slot_aloha"] = dict(kind="slot_aloha", k_cap=des["slot_aloha_k_cap"])
    d["tamang"] = dict(kind="tamang", k_cap=des["tamang_k_cap"])  # n_hat = the cell's burst size (oracle: the strongest form of the baseline)
    return d


def held() -> None:
    des = json.loads((OUT / "pa_design.json").read_text(encoding="utf-8"))
    t = FS.tuned()
    pools = pools_real()
    specs = held_specs(des)
    # every earlier policy as well, for the regime map
    specs_all = {**{k: v for k, v in earlier_specs().items()}, **{k: v for k, v in specs.items() if k != "best_earlier"}}
    R = FS.run_jobs(make_jobs(HELD_A, specs_all, pools, t))
    R.to_pickle(OUT / "pa_held.pkl")
    print("held-out runs", len(R), "duty exceeded", int(R.duty_exceeded.sum()))


if __name__ == "__main__":
    {"design": design, "held": held}[sys.argv[1]]()
