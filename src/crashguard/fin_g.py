"""Block G (SIMULATED): the earlier policies and three new mechanisms through the protocol layers on assumption-driven simulated data (docs/02_preregistration/PREREGISTRATION_V5.md section G; assumptions: docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md).
DESIGN grid (seeds 6000 + h) is used to choose anything (here: only the baseline policy of G3); HELD-OUT grid (seeds 8000 + h) confirms. Nothing is tuned to produce a win. Class pairs come from synthetic pulses of the modes that passed C2."""
from __future__ import annotations

import itertools
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import fin_sim as FS
from crashguard import packet as P
from crashguard import pp_common as PC
from crashguard import s11_sct as S
from crashguard import world_sim as W

SRC = "results/tables/f_g_cells.csv"
CACHE = C.PROCESSED / "f_g_pairs.pkl"
N_PAIR, SEED0_PAIR = 1500, 700_000
GEOM = dict(R_m=3000.0, n_exp=3.0, pl0_db=25.0, ptx_dbm=14.0, extra_loss_db=10.0, sigma_sh_db=6.0, ngw=1)
WORLD = dict(geom=GEOM)
DESIGN = dict(n=(75, 150), p=(0.1, 0.3), sf=(7, 9), duty=(0.01, 0.001), b=20, seed=6000)
HELD = dict(n=(100, 200), p=(0.2, 0.4), sf=(8, 10), duty=(0.01, 0.001), b=30, seed=8000)
EARLIER = ("P0", "P1", "P1e", "P1+", "P1+e", "P2", "P3", "P4", "P3b")
KEY = {"P0": "point", "P1": "point", "P1e": "lowered", "P1+": "point", "P1+e": "lowered", "P2": "point", "P3": "upper", "P4": "upper", "P3b": "abstain", "P1+f": "improved", "P3f": "improved_upper", "P1+u": "upper", "P1+a": "abstain"}
BASE = {"P0": "P0", "P1": "P1", "P1e": "P1", "P1+": "P2", "P1+e": "P2", "P2": "P2", "P3": "P3", "P4": "P4", "P3b": "P2", "P1+f": "P2", "P3f": "P3", "P1+u": "P2", "P1+a": "P2"}
P1PLUS = ("P1+", "P1+e", "P1+f", "P1+u", "P1+a")
METS = ("mis_triage", "escalation", "escalation_used", "reach10_critical", "reach30_critical", "reach30_rx_critical", "p95_lat_s_critical", "node_air_share", "fast_air_share_of_allowance", "duty_exceeded",
        "dup_rx_critical", "relay_air_share_of_allowance", "slot_beacon_duty_share", "relay_tx", "delivered_normal", "max_window_airtime_s")


def cell_name(n, p, sf, d):
    return f"n{n}_p{int(round(p * 100))}_sf{sf}_d{d * 100:g}"


def cells_of(g: dict) -> list[dict]:
    return [dict(name=cell_name(n, p, sf, d), n=n, p=p, sf=sf, duty=d, b=g["b"]) for n, p, sf, d in itertools.product(g["n"], g["p"], g["sf"], g["duty"])]


# ------------------------------------------------------------------ pools
def build_pairs(force: bool = False) -> dict:
    """Class pairs of synthetic pulses (frontal barrier and other, mode proportions of the real pool) at +-16 and +-32 g, 100 Hz: true class from the reference delta-V, assigned class from the plain estimate; the upper class
    from plain x q (q = conformal quantile of reference / plain on the real development and validation records, 90% target, the V4 alpha rule); abstain = clipped share above the 70th percentile of the real development and validation rows."""
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    from crashguard import fin_f1 as F1
    from concurrent.futures import ProcessPoolExecutor
    from crashguard.pp_ctx import Ctx

    cx = Ctx()
    par = json.load(open("results/synthetic/generator_params_all913.json"))
    passed = json.load(open("results/synthetic/modes_passed.json"))
    cnt = np.array([(cx.mode == m).sum() for m in passed], float)
    rng = np.random.default_rng(SEED0_PAIR)
    ms = rng.choice(len(passed), size=N_PAIR, p=cnt / cnt.sum())
    jobs = [(par, passed[m], SEED0_PAIR + 1 + k) for k, m in enumerate(ms)]
    with ProcessPoolExecutor(12) as ex:
        res = list(ex.map(F1._syn_job, jobs, chunksize=8))
    out = {}
    trv = cx.dev | cx.val
    for rg in (16.0, 32.0):
        df, _W = cx.cell(rg, 100)
        plain_r, ref_r, sat_r = df.dv_plain.to_numpy(float)[trv], cx.ref[trv], df.sat_share.to_numpy(float)[trv]
        ratio = np.sort(ref_r / np.maximum(plain_r, 1e-6))
        alpha = max(0.02, 0.10 - float((ref_r < plain_r).mean()))
        q = float(ratio[min(int(np.ceil((len(ratio) + 1) * (1 - alpha))) - 1, len(ratio) - 1)])
        thr = float(np.quantile(sat_r, 0.70))
        syn = pd.DataFrame([r[2][rg] for r in res])
        ref = np.array([r[1] for r in res])
        plain, sat = syn.dv_plain.to_numpy(float), syn.sat_share.to_numpy(float)
        true = PC.cls_of(ref)
        point = PC.cls_of(plain)
        upper = PC.cls_of(plain * q)
        out[rg] = dict(true=true.astype(int), point=point.astype(int), upper=upper.astype(int), abstain=np.where(sat > thr, 3, point).astype(int), plain=plain, sat=sat, q=q, thr=thr, modes=[r[0] for r in res])
        # lowered-threshold table: factor f so that the escalation of the lowered point class equals that of the upper class (no simulated outcome used)
        nons = true < 2
        e_up = float((upper[nons] >= 2).mean())
        best = min(np.round(np.arange(0.30, 1.0001, 0.0025), 4), key=lambda f: abs(float((PC.cls_of(plain / f)[nons] >= 2).mean()) - e_up))
        out[rg]["f"] = float(best)
        out[rg]["lowered"] = PC.cls_of(plain / best).astype(int)
    CACHE.write_bytes(pickle.dumps(out))
    return out


def to_pools(pairs: dict, improved: dict | None = None) -> dict:
    base = S.load_pools()
    classes = {}
    for rg, d in pairs.items():
        classes[rg] = dict(true=d["true"], point=d["point"], upper=d["upper"], lowered=d["lowered"], abstain=d["abstain"])
        if improved and rg in improved:
            classes[rg].update(improved[rg])
    return {**base, "classes": classes}


# ------------------------------------------------------------------ configs
def lens(tag: int) -> dict:
    return dict(alert_len=P.ALERT_LEN - 8 + tag, flash_len=max(14 - 8 + tag, 6), ack_len=P.ACK_LEN - 8 + tag)


def cfg_for(pol: str, cell: dict, seed: int, hour: int, pools: dict, t: dict, label: str, world: dict | None = None, sct_over: dict | None = None, cfg_over: dict | None = None, rg: float = 16.0) -> W.SCfg:
    cl = pools["classes"][rg]
    key = KEY[pol]
    pl2 = {**pools, "classes": {**pools["classes"], rg: {**cl, "point": cl[key], "upper": cl[key]}}}
    kw = dict(n=cell["n"], sf=cell["sf"], p_up=cell["p"], p_down=cell["p"], duty=cell["duty"], burst_cars=cell["b"])
    c = S.make_cfg(BASE[pol], rg, kw, True, seed, hour, pl2, FS.OldParams(h_s=t["h_s"], rho_f=t["rho_f"], sf_raise=t["sf_raise"]), t["phi"] if pol == "P4" else None, label, None)
    w = FS.to_w(c)
    over = sct_over or {}
    sc = FS.p1plus_params(t["h_s"], **over) if pol in P1PLUS else W.SctParams(**{**w.sct.__dict__, **over})
    d = {**w.__dict__, "sct": sc, "world": world if world is not None else WORLD}
    d.update(cfg_over or {})
    return W.SCfg(**d)


def run(jobs: list) -> pd.DataFrame:
    return FS.run_jobs(jobs)


def grid_jobs(g: dict, pools, t, pols, hours=30, world=None, sct_over=None, cfg_over=None, tag="", rg=16.0, polname=None) -> list:
    jobs = []
    for cell in cells_of(g):
        for pol in pols:
            for h in range(hours):
                jobs.append((cfg_for(pol, cell, g["seed"], h, pools, t, f"g_{cell['name']}", world, sct_over, cfg_over, rg), dict(cell=cell["name"], n=cell["n"], p=cell["p"], sf=cell["sf"], duty=cell["duty"], pol=polname or pol, hour=h, variant=tag)))
    return jobs


# ------------------------------------------------------------------ statistics (cells fixed, seeds resampled inside each cell)
def arr(R: pd.DataFrame, pol: str, metric: str, cells: list[str]) -> np.ndarray:
    out = []
    for c in cells:
        g = R[(R.cell == c) & (R.pol == pol)].sort_values("hour")
        out.append(g[metric].to_numpy(float))
    return np.array(out)  # (cells, seeds)


def pooled(a: np.ndarray, b: np.ndarray | None = None, seed: int = C.SEED) -> tuple[float, float, float]:
    """Mean over cells of the seed-mean of a (or of b minus a), with a 95% interval from 1,000 resamples of the seeds inside every cell (the same draws for every call: paired)."""
    d = a if b is None else b - a
    ok = ~np.isnan(d).any(axis=0)
    d = d[:, ok]
    if d.shape[1] < 3:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, d.shape[1], (FS.NB, d.shape[1]))
    m = np.stack([d[:, i].mean(1) for i in idx]).mean(1)
    return float(d.mean()), float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


# ------------------------------------------------------------------ G1
def g1(pools, t, pols) -> pd.DataFrame:
    jobs = [(c, {**m, "grid": "design"}) for c, m in grid_jobs(DESIGN, pools, t, pols)] + [(c, {**m, "grid": "held"}) for c, m in grid_jobs(HELD, pools, t, pols)]
    return run(jobs)


def mean_by(R, grid, pol, metric):
    sub = R[R.grid == grid]
    cells = sorted(sub.cell.unique())
    return pooled(arr(sub, pol, metric, cells))


# ------------------------------------------------------------------ G2
def g2_variants(t: dict) -> dict:
    """name -> (layer, policy, sct_over, world_over, cfg_over)."""
    v = {"base": ("-", "P1+", None, None, None)}
    v["sf_raise"] = ("PHY", "P1+", dict(sf_raise=True), None, None)
    v["cr_4_8"] = ("PHY", "P1+", None, dict(cr=4), None)
    v["spaced_retries"] = ("MAC", "P1+", dict(spacing_crit=5.0, spacing_sev=10.0), None, None)
    v["no_hold"] = ("MAC", "P1+", dict(sev_hold=False), None, None)
    v["backoff_normal"] = ("MAC", "P1+", dict(p1_retry=False), None, None)
    v["reserved_share"] = ("MAC", "P1+", dict(reserve=True, rho_f=0.35), None, None)
    v["preempt"] = ("MAC", "P1+", dict(preempt=True), None, None)
    v["capture_off"] = ("MAC", "P1+", None, None, dict(capture="none"))
    v["tag_4"] = ("NET", "P1+", None, None, lens(4))
    v["tag_16"] = ("NET", "P1+", None, None, lens(16))
    v["unsigned_ack"] = ("NET", "P1+", None, None, dict(ack_len=P.ACK_LEN - 8))
    v["upper_end_class"] = ("APP", "P1+u", None, None, None)
    v["abstain_route"] = ("APP", "P1+a", None, None, None)
    for a, b in (("sf_raise", "spaced_retries"), ("no_hold", "spaced_retries"), ("sf_raise", "tag_16")):
        sa, sb = v[a], v[b]
        merged_s = {**(sa[2] or {}), **(sb[2] or {})} or None
        merged_w = {**(sa[3] or {}), **(sb[3] or {})} or None
        merged_c = {**(sa[4] or {}), **(sb[4] or {})} or None
        v[f"{a}+{b}"] = ("INTERACTION", "P1+", merged_s, merged_w, merged_c)
    return v


def g2(pools, t) -> pd.DataFrame:
    jobs = []
    for gname, g in (("design", DESIGN), ("held", HELD)):
        for name, (layer, pol, so, wo, co) in g2_variants(t).items():
            world = {**WORLD, **(wo or {})}
            for c, m in grid_jobs(g, pools, t, [pol], world=world, sct_over=so, cfg_over=co, tag=name, polname=name):
                m.update(grid=gname, layer=layer)
                jobs.append((c, m))
    # CANCEL: needs false alarms; paired baseline with the same false alarms
    for gname, g in (("design", DESIGN), ("held", HELD)):
        for name, so in (("fa_cancel_on", None), ("fa_cancel_off", dict(cancel_msg=False))):
            for c, m in grid_jobs(g, pools, t, ["P1+"], world=WORLD, sct_over=so, cfg_over=dict(fa_per_car_h=0.25), tag=name, polname=name):
                m.update(grid=gname, layer="NET")
                jobs.append((c, m))
    return run(jobs)


# ------------------------------------------------------------------ G3
MECH = {"slot": dict(slot={}), "lbt": dict(lbt={}), "relay": dict(relay={})}


def g3(pools, t, best: str) -> pd.DataFrame:
    jobs = []
    for mech in ("base",) + tuple(MECH):
        world = {**WORLD, **MECH.get(mech, {})}
        for c, m in grid_jobs(HELD, pools, t, [best], world=world, tag=mech, polname=mech):
            m.update(grid="held")
            jobs.append((c, m))
    return run(jobs)


# ------------------------------------------------------------------ G5
def g5_variants() -> dict:
    ge = lambda **k: dict(geom={**GEOM, **k})  # noqa: E731
    return {"base": {}, "sigma3": ge(sigma_sh_db=3.0), "sigma9": ge(sigma_sh_db=9.0), "nexp2.5": ge(n_exp=2.5), "nexp3.5": ge(n_exp=3.5), "capture3": dict(capture_db=3.0), "capture10": dict(capture_db=10.0),
            "ackdelay0.5": dict(rx_delay_s=0.5), "ackdelay1.0": dict(rx_delay_s=1.0), "channels3": dict(channels=3), "gateways2": ge(ngw=2),
            "relay_delay_short": dict(relay=dict(delay_s=(0.5, 2.0))), "relay_delay_long": dict(relay=dict(delay_s=(3.0, 8.0))), "hear0.25": dict(relay=dict(p_hear=0.25)), "hear0.75": dict(relay=dict(p_hear=0.75)),
            "slots4": dict(slot=dict(n_slots=4)), "slots16": dict(slot=dict(n_slots=16)), "sense0.4": dict(lbt=dict(p_sense=0.4)), "sense0.9": dict(lbt=dict(p_sense=0.9))}


def g5(pools, t, best: str) -> pd.DataFrame:
    """For every variant: baseline policy without mechanism, with slot, with LBT, with relay (each mechanism only with its own settings), and P1+; held-out cells."""
    jobs = []
    for name, wo in g5_variants().items():
        wbase = {**WORLD, **{k: v for k, v in wo.items() if k in ("geom", "capture_db", "rx_delay_s", "channels", "cr")}}
        specs = [("P1+", "P1+", wbase), ("base", best, wbase), ("slot", best, {**wbase, "slot": wo.get("slot", {})}), ("lbt", best, {**wbase, "lbt": wo.get("lbt", {})}), ("relay", best, {**wbase, "relay": wo.get("relay", {})})]
        for lab, pol, w in specs:
            for c, m in grid_jobs(HELD, pools, t, [pol], world=w, tag=name, polname=lab):
                m.update(grid="held")
                jobs.append((c, m))
    return run(jobs)


def g5_range(pools, t, best: str) -> pd.DataFrame:
    jobs = []
    for lab, pol in (("P1+", "P1+"), ("base", best)):
        for c, m in grid_jobs(HELD, pools, t, [pol], tag="range32", polname=lab, rg=32.0):
            m.update(grid="held")
            jobs.append((c, m))
    return run(jobs)


# ------------------------------------------------------------------ main
def main(stage: str = "all") -> None:
    pairs = build_pairs()
    if stage == "pairs":
        print({rg: (round(d["q"], 2), round(d["thr"], 3), d["f"], np.bincount(d["true"], minlength=4).tolist(), np.bincount(d["point"], minlength=4).tolist(), np.bincount(d["upper"], minlength=4).tolist(), np.bincount(d["lowered"], minlength=4).tolist(), float((d["abstain"] == 3).mean())) for rg, d in pairs.items()})
        return
    t = FS.tuned()
    imp = None
    ip = C.PROCESSED / "f_g_improved.pkl"
    if ip.exists():
        imp = pickle.loads(ip.read_bytes())
    pools = to_pools(pairs, imp)
    out = Path("data/processed")
    pols = list(EARLIER) + (["P1+f", "P3f"] if imp else [])
    if stage in ("all", "g1"):
        R1 = g1(pools, t, pols)
        R1.to_pickle(out / "f_g1.pkl")
    if stage in ("all", "g2"):
        g2(pools, t).to_pickle(out / "f_g2.pkl")
    R1 = pd.read_pickle(out / "f_g1.pkl")
    best = max([p for p in EARLIER], key=lambda p: mean_by(R1, "design", p, "reach10_critical")[0])
    (out / "f_g_best.json").write_text(json.dumps(dict(best=best)))
    if stage in ("all", "g3"):
        g3(pools, t, best).to_pickle(out / "f_g3.pkl")
    if stage in ("all", "g5"):
        g5(pools, t, best).to_pickle(out / "f_g5.pkl")
        g5_range(pools, t, best).to_pickle(out / "f_g5r.pkl")
    print("best on DESIGN:", best)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
