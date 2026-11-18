"""R6-1 (docs/02_preregistration/PREREGISTRATION_V17.md section 3): chained micro-confirm in ns-3 (policy ``r6m``) and on the LoED traces.

    python -m crashguard.r6_micro dev <iteration 1..5> <pend_s>   # development: validation-style runs on seeds 101 to 120 (never held-out seeds); appends to results/tables/r6_micro_dev_log.json
    python -m crashguard.r6_micro freeze <iteration>              # freeze the pending lifetime by hash (results/tables/r6_frozen.json)
    python -m crashguard.r6_micro held                            # held-out: 16 cells x seeds 1 to 60 against the stored r3s and r3t runs, plus the trace groups of LoED half 0; keys r6.r1.ns3.*, r6.r1.trace.*

The ns-3 frame of the micro-confirm and micro-cancel is 13 bytes (the smallest frame of the LoRaWAN module; the design frame has 7 bytes), so the simulated airtime is conservative.
Evidence labels: ns-3 SIMULATED; LoED traces TRACE_DRIVEN.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import r6_common as C6
from crashguard import rd_firmware as F

ROOT = C6.ROOT
SRC = "src/crashguard/r6_micro.py"
OUT = ROOT / "data" / "processed" / "r6m_out"
R3OUT = ROOT / "data" / "processed" / "r3ns3_out"
JOBS = ROOT / "data" / "processed" / "r6m_jobs"
EVENTS = ROOT / "data" / "processed" / "r3_ns3_events.txt"
NS_BIN = "./build/scratch/ns3.48-xsim_alert-optimized"
SFS = (7, 9)
SETTINGS = {"calib": 0, "shipped": 1}
LOSSES = (0.0, 0.1, 0.3, 0.6)
DEV_LOSSES = (0.0, 0.3)
DEV_SEEDS = range(101, 121)
HELD_SEEDS = range(1, 61)
PENDS = (10.0, 30.0, 60.0)
N_VEH, RADIUS, RATE = 60, 1500, 10
NB, SEED = 2000, 42
DEADLINE = 10.0  # H-R6-1b: critical content delivered within 10 s of the crash
LIMIT_A, LIMIT_B = 0.40, -0.01
WORKERS = 14
COLS = ["k", "v", "t", "row", "dropped", "flash", "alert", "cancel", "air"]
JOB_SCRIPT = """#!/bin/bash
# usage: job.sh <jobfile> ; each line: outfile|args
cd ~/ns3work/ns-3-dev
while IFS='|' read -r out args; do
  {NS} $args > "$out" 2>/dev/null
done < "$1"
"""


# ----------------------------------------------------------------------------- pure core (tested and mutated)
def two_stage_delivered(cr: pd.DataFrame, deadline: float = DEADLINE) -> int:
    """Crash events of a two-stage run whose critical content reached the base within ``deadline`` seconds: the confirm arrived, or the flash arrived and no cancel followed or the event was confirmed anyway
    (R3 definition of ``pp_r3_ns3``, with the 10 s limit added)."""
    a = (cr.alert >= 0) & (cr.alert <= deadline)
    f = (cr.flash >= 0) & (cr.flash <= deadline)
    ok = a | ((cr.E == 1) & (cr.F == 0) & f & (cr.cancel == 0)) | ((cr.E == 1) & (cr.F == 1) & f)
    return int(ok.sum())


def run_pair_stats(s: pd.DataFrame, t: pd.DataFrame, m: pd.DataFrame, deadline: float = DEADLINE) -> dict:
    """Per-run sums of the paired runs of one seed (single-stage ``s``, R3 two-stage ``t``, micro-confirm ``m``) over events that none of the three dropped."""
    x = s.merge(t, on="k", suffixes=("_s", "_t")).merge(m.add_suffix("_m").rename(columns={"k_m": "k"}), on="k")
    x = x[(x.dropped_s == 0) & (x.dropped_t == 0) & (x.dropped_m == 0)]
    cr = x[x.y_s == 1]
    crt = cr[["alert_t", "flash_t", "cancel_t", "E_t", "F_t"]].rename(columns=lambda c: c[:-2])
    crm = cr[["alert_m", "flash_m", "cancel_m", "E_m", "F_m"]].rename(columns=lambda c: c[:-2])
    return dict(air_s=float(x.air_s.sum()), air_t=float(x.air_t.sum()), air_m=float(x.air_m.sum()), n_cr=int(len(cr)), del_t=two_stage_delivered(crt, deadline), del_m=two_stage_delivered(crm, deadline),
                n_ev=int(len(s)), n_drop=int(((s.dropped == 1) | (t.dropped == 1) | (m.dropped == 1)).sum()))


def boot_cell(runs: list[dict], rng: np.random.Generator, nb: int = NB) -> dict:  # noqa: PLR0915
    """Cluster bootstrap over runs: extra airtime of the micro scheme against single-stage (R3 definition), airtime against R3's two-stage total, delivery difference micro minus R3."""
    n = len(runs)
    idx = rng.integers(0, n, (nb, n))
    A = {k: np.array([r[k] for r in runs], float) for k in ("air_s", "air_t", "air_m", "n_cr", "del_t", "del_m")}
    ratio_s = A["air_m"][idx].sum(1) / A["air_s"][idx].sum(1) - 1.0
    ratio_t = A["air_m"][idx].sum(1) / A["air_t"][idx].sum(1)
    ratio_pd = (A["air_m"][idx].sum(1) / A["del_m"][idx].sum(1)) / (A["air_t"][idx].sum(1) / A["del_t"][idx].sum(1))
    dd = (A["del_m"][idx].sum(1) - A["del_t"][idx].sum(1)) / A["n_cr"][idx].sum(1)
    return dict(ratio_s_pt=float(A["air_m"].sum() / A["air_s"].sum() - 1.0), ratio_s=ratio_s, ratio_t_pt=float(A["air_m"].sum() / A["air_t"].sum()), ratio_t=ratio_t, ratio_pd_pt=float((A["air_m"].sum() / A["del_m"].sum()) / (A["air_t"].sum() / A["del_t"].sum())), ratio_pd=ratio_pd,
                dd_pt=float((A["del_m"].sum() - A["del_t"].sum()) / A["n_cr"].sum()), dd=dd, deliv_t=float(A["del_t"].sum() / A["n_cr"].sum()), deliv_m=float(A["del_m"].sum() / A["n_cr"].sum()), n_cr=int(A["n_cr"].sum()))


def criterion_a(c: dict) -> tuple[bool, float, float]:
    """H-R6-1a in one cell: the upper 95% limit of the extra airtime is at most 0.40; the p-value counts resamples at or above 0.40."""
    hi = float(np.quantile(c["ratio_s"], 0.975))
    return hi <= LIMIT_A, hi, float((int((c["ratio_s"] >= LIMIT_A).sum()) + 1) / (len(c["ratio_s"]) + 1))


def criterion_b(c: dict) -> tuple[bool, float, float]:
    """H-R6-1b in one cell: the lower 95% limit of the delivery difference (micro minus R3) is at least -0.01; the p-value counts resamples below -0.01."""
    lo = float(np.quantile(c["dd"], 0.025))
    return lo >= LIMIT_B, lo, float((int((c["dd"] < LIMIT_B).sum()) + 1) / (len(c["dd"]) + 1))


# ----------------------------------------------------------------------------- ns-3 runs
def fname_new(d: Path, sf: int, st: str, p: float, pol: str, seed: int, pend: float | None = None) -> Path:
    tag = f"_pend{pend:g}" if pend is not None else ""
    return d / f"sf{sf}_{st}_p{p:g}_{pol}_{seed}{tag}.txt"


def run_jobs(jobs: list[tuple[Path, str]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / "job.sh").write_bytes(JOB_SCRIPT.replace("{NS}", NS_BIN).encode("utf-8"))
    chunks = [jobs[i::WORKERS] for i in range(WORKERS)]
    procs = []
    for k, ch in enumerate(chunks):
        if not ch:
            continue
        jf = JOBS / f"jobs_{k}.txt"
        jf.write_bytes(("\n".join(f"{F.wsl_path(o)}|{a}" for o, a in ch) + "\n").encode("utf-8"))
        procs.append(subprocess.Popen(["wsl", "-d", "Ubuntu", "--", "bash", F.wsl_path(JOBS / "job.sh"), F.wsl_path(jf)], env={**__import__("os").environ, "MSYS_NO_PATHCONV": "1"}))
    for pr in procs:
        pr.wait()


def args_for(sf: int, sh: int, p: float, seed: int, pol: str, pend: float | None) -> str:
    a = f"--n={N_VEH} --sf={sf} --p={p:g} --radius={RADIUS} --rate={RATE} --duty=0.01 --seed={seed} --policy={pol} --events={F.wsl_path(EVENTS)} --sensShipped={sh}"
    return a + (f" --pend={pend:g}" if pend is not None else "")


def parse(f: Path, ev: pd.DataFrame) -> pd.DataFrame:
    rows = [ln.split()[1:] for ln in f.read_text().splitlines() if ln.startswith("R3 ")]
    d = pd.DataFrame(rows, columns=COLS).astype(dict(k=int, v=int, t=float, row=int, dropped=int, flash=float, alert=float, cancel=int, air=float))
    return d.join(ev, on="row")


def usable(*fs: Path) -> bool:
    return all(f.exists() and f.stat().st_size > 0 for f in fs)


def cell_runs(files_s, files_t, files_m, ev) -> list[dict]:
    runs = []
    for fs, ft, fm in zip(files_s, files_t, files_m):
        if not usable(fs, ft, fm):
            continue  # an ns-3 crash (empty output): the seed is dropped for all three policies
        runs.append(run_pair_stats(parse(fs, ev), parse(ft, ev), parse(fm, ev)))
    return runs


def event_table() -> pd.DataFrame:
    return pd.read_csv(EVENTS, sep=" ", header=None, names=["E", "F", "y", "tE"])


def dev(it: int, pend: float) -> None:
    log = ROOT / "results" / "tables" / "r6_micro_dev_log.json"
    cur = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
    assert 1 <= it <= 5 and len(cur) < 5, "at most five development iterations"
    assert pend in PENDS
    ev = event_table()
    jobs = []
    for sf in SFS:
        for st, sh in SETTINGS.items():
            for p in DEV_LOSSES:
                for s in DEV_SEEDS:
                    for pol, pe in (("r3s", None), ("r3t", None), ("r6m", pend)):
                        f = fname_new(OUT, sf, st, p, pol, s, pe)
                        if not usable(f):
                            jobs.append((f, args_for(sf, sh, p, s, pol, pe)))
    print("ns-3 jobs", len(jobs), flush=True)
    run_jobs(jobs)
    rng = np.random.default_rng(SEED)
    cells = {}
    for sf in SFS:
        for st in SETTINGS:
            for p in DEV_LOSSES:
                fs = [fname_new(OUT, sf, st, p, "r3s", s) for s in DEV_SEEDS]
                ft = [fname_new(OUT, sf, st, p, "r3t", s) for s in DEV_SEEDS]
                fm = [fname_new(OUT, sf, st, p, "r6m", s, pend) for s in DEV_SEEDS]
                runs = cell_runs(fs, ft, fm, ev)
                c = boot_cell(runs, rng, 500)
                cells[f"sf{sf}.{st}.p{p:g}"] = dict(n_runs=len(runs), dd=c["dd_pt"], ratio_s=c["ratio_s_pt"], ratio_t=c["ratio_t_pt"])
    worst = min(v["dd"] for v in cells.values())
    r = dict(iteration=it, pend_s=pend, worst_cell_delivery_diff=worst, max_ratio_s=max(v["ratio_s"] for v in cells.values()), cells=cells)
    cur.append(r)
    log.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in r.items() if k != "cells"}, indent=1))


def freeze(it: int) -> None:
    log = json.loads((ROOT / "results" / "tables" / "r6_micro_dev_log.json").read_text(encoding="utf-8"))
    ch = [e for e in log if e["iteration"] == it]
    assert len(ch) == 1
    prm = dict(pend_s=ch[0]["pend_s"], iteration=it, ns3_frame_bytes=13)
    C6.freeze_entry("r1", [SRC, "xsim/ns3/xsim_alert.cc", "src/crashguard/pp_r3_ns3.py", "src/crashguard/r3_t1.py", "data/processed/r3_ns3_events.txt", "results/tables/r6_micro_dev_log.json"], prm, "r6.r1.ns3.")
    print("frozen", prm)


# ----------------------------------------------------------------------------- trace-driven micro-confirm (LoED half 0), paired with r3_t1.r3_event
def arrival_ack(r, s: int, t0: float, a_msg: float, p_dl: float, rng: random.Random, win: float, tries: int) -> tuple[float, int, bool]:
    """Same random draws as ``r3_t1.arrival_trace`` plus whether the stage ended with an acknowledgement."""
    arr = math.inf
    for k in range(tries):
        t_k = t0 + k * (a_msg + win)
        if r[s + k]:
            if arr == math.inf:
                arr = t_k + a_msg
            if rng.random() >= p_dl:
                return arr, k + 1, True
    return arr, tries, False


def micro_event(r, s: int, ev: tuple, p_dl: float, rng: random.Random, a_micro: float) -> dict:
    """Two-stage event with the micro-confirm and micro-cancel after an acknowledged flash; otherwise the full confirm and the 14-byte cancel of R3."""
    from crashguard.r3_t1 import A_AL, A_FL, CANCEL_TX, COMPUTE3, FINAL_S, TRIES3, WIN3

    E, F_, y, te = ev
    out = dict(n_cr=int(y == 1), two_air=0.0, two_d=0)
    if F_:  # the single-stage reference of ``r3_event`` draws first; the same draws are consumed here so that the two replays are paired
        arrival_ack(r, s, FINAL_S + COMPUTE3, A_AL, p_dl, rng, WIN3, TRIES3)
    if E:
        arr_f, n_f, acked = arrival_ack(r, s, te + COMPUTE3, A_FL, p_dl, rng, WIN3, TRIES3)
        k0 = s + n_f
        if F_:
            a_c = a_micro if acked else A_AL
            arr_c, n_c, _ = arrival_ack(r, k0, FINAL_S + COMPUTE3, a_c, p_dl, rng, WIN3, TRIES3)
            out["two_air"] = A_FL * n_f + a_c * n_c
            out["two_d"] = int(y == 1 and (math.isfinite(arr_f) or math.isfinite(arr_c)))
        else:
            a_x = a_micro if acked else A_FL
            cancel_lost = all(not r[k0 + j] for j in range(CANCEL_TX))
            out["two_air"] = A_FL * n_f + CANCEL_TX * a_x
            out["two_d"] = int(y == 1 and math.isfinite(arr_f) and cancel_lost)
    elif F_:
        arr_c, n_c, _ = arrival_ack(r, s, FINAL_S + COMPUTE3, A_AL, p_dl, rng, WIN3, TRIES3)
        out["two_air"] = A_AL * n_c
        out["two_d"] = int(y == 1 and math.isfinite(arr_c))
    return out


def trace_device(args: tuple) -> dict:
    from crashguard import r3_t1 as T

    dev_, segs, p_loss, n_start, events, a_micro, a_micro7 = args
    rng0 = T.seeded("t1s", dev_, T.SEED)
    adm = T.admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    tot = dict(n_cr=0, air_s=0.0, air_t=0.0, air_m=0.0, air_m7=0.0, del_t=0, del_m=0)
    for q, (si, pos) in enumerate(picks):
        r = segs[si][0]
        rng = T.seeded("t1e", dev_, q)
        ev = events[rng.randrange(len(events))]
        # r3_event draws from the generator after the event pick, exactly as device_task does: rebuild that state for each of the two replays
        rng2 = T.seeded("t1e", dev_, q)
        rng2.randrange(len(events))
        o3 = T.r3_event(r, pos, ev, p_loss, rng2)
        rng3 = T.seeded("t1e", dev_, q)
        rng3.randrange(len(events))
        om = micro_event(r, pos, ev, p_loss, rng3, a_micro)
        rng4 = T.seeded("t1e", dev_, q)
        rng4.randrange(len(events))
        om7 = micro_event(r, pos, ev, p_loss, rng4, a_micro7)
        tot["air_m7"] += om7["two_air"]
        tot["n_cr"] += o3["n_cr"]
        tot["air_s"] += o3["single_air"]
        tot["air_t"] += o3["two_air"]
        tot["air_m"] += om["two_air"]
        tot["del_t"] += o3["two_d"]
        tot["del_m"] += om["two_d"]
    return dict(dev=dev_, p=p_loss, **tot)


def trace_groups(n_start: int = 300) -> dict:
    import pickle
    from concurrent.futures import ProcessPoolExecutor

    from crashguard import r3_t1 as T
    from crashguard.lora import airtime_ms

    links = pickle.loads(T.LINKS.read_bytes())
    devs = sorted(d for d, v in links.items() if v["half"] == 0)
    events = T.load_events()
    a_micro = airtime_ms(13, T.SF_R3) / 1000.0
    a_micro7 = airtime_ms(7, T.SF_R3) / 1000.0
    tasks = [(d, links[d]["segs"], links[d]["p"], n_start, events, a_micro, a_micro7) for d in devs]
    with ProcessPoolExecutor(WORKERS) as ex:
        res = list(ex.map(trace_device, tasks, chunksize=8))
    return dict(res=res)


# ----------------------------------------------------------------------------- held-out run and analysis
def held() -> None:
    from crashguard.results import record_many

    prm = C6.check_frozen("r1", "r6.r1.ns3.")
    pend = prm["pend_s"]
    marker = ROOT / "results" / "tables" / "r6_held_started_r1.json"
    if marker.exists():
        raise RuntimeError("the held-out run of R6-1 was started before: it is made once (delete the marker only with a DECISIONS.md entry)")
    marker.write_text(json.dumps(dict(frozen_params_sha256=C6.sha256_json(prm), pend_s=pend)), encoding="utf-8")
    ev = event_table()
    jobs = []
    for sf in SFS:
        for st, sh in SETTINGS.items():
            for p in LOSSES:
                for s in HELD_SEEDS:
                    f = fname_new(OUT, sf, st, p, "r6m", s, pend)
                    if not usable(f):
                        jobs.append((f, args_for(sf, sh, p, s, "r6m", pend)))
    print("ns-3 jobs", len(jobs), flush=True)
    run_jobs(jobs)
    rng = np.random.default_rng(SEED)
    ent: list[dict] = []

    def add(name, v, unit, note="", origin="SIMULATED"):
        ent.append(dict(name=f"r6.r1.{name}", value=(round(v, 6) if isinstance(v, float) else v), unit=unit, origin=origin, source_file=SRC, notes=note))

    add("ns3.params.pend_s", float(pend), "s", "pending-table lifetime used (frozen)")
    add("ns3.params.frame_bytes", 13, "bytes", "ns-3 micro frame size (smallest LoRaWAN frame; the design frame has 7 bytes, so the airtime is conservative)")
    a_met, b_met, pa, pb = [], [], [], []
    cells = {}
    for sf in SFS:
        for st in SETTINGS:
            for p in LOSSES:
                fs = [fname_new(R3OUT, sf, st, p, "r3s", s) for s in HELD_SEEDS]
                ft = [fname_new(R3OUT, sf, st, p, "r3t", s) for s in HELD_SEEDS]
                fm = [fname_new(OUT, sf, st, p, "r6m", s, pend) for s in HELD_SEEDS]
                runs = cell_runs(fs, ft, fm, ev)
                n_ev = sum(r["n_ev"] for r in runs)
                n_dr = sum(r["n_drop"] for r in runs)
                c = boot_cell(runs, rng)
                cn = f"sf{sf}.{st}.p{p:g}"
                cells[cn] = c
                ma, ha, qa = criterion_a(c)
                mb, lb, qb = criterion_b(c)
                add(f"ns3.{cn}.n_runs", len(runs), "runs", "paired runs used (seeds with an empty output are dropped for all three policies)")
                add(f"ns3.{cn}.dropped_share", n_dr / max(1, n_ev), "fraction", "events dropped in at least one of the three runs (these events are removed from all three, as in P1)")
                add(f"ns3.{cn}.runs_failed", len(HELD_SEEDS) - len(runs), "runs", "seeds dropped because an output was missing or empty")
                add(f"ns3.{cn}.reliable", int(n_dr / max(1, n_ev) <= 0.05 and len(runs) == len(HELD_SEEDS)), "flag", "at most 5% of events dropped and no run lost (reported; not part of the criteria)")
                add(f"ns3.{cn}.extra_air_ratio", c["ratio_s_pt"], "ratio", "micro scheme airtime over single-stage airtime minus 1 (ratio of sums over runs)")
                add(f"ns3.{cn}.extra_air_ratio_hi", ha, "ratio", "upper 95% limit, cluster bootstrap over runs (2,000 resamples, seed 42)")
                add(f"ns3.{cn}.air_over_r3", c["ratio_t_pt"], "ratio", "micro scheme airtime over R3 two-stage airtime")
                add(f"ns3.{cn}.air_per_delivered_over_r3", c["ratio_pd_pt"], "ratio", "airtime per delivered crash alert of the micro scheme over that of R3 (second statistic of H-R6-1a)")
                add(f"ns3.{cn}.air_per_delivered_over_r3_hi", float(np.quantile(c["ratio_pd"], 0.975)), "ratio", "upper 95% limit")
                add(f"ns3.{cn}.delivery_r3", c["deliv_t"], "fraction", f"R3 two-stage delivery over {c['n_cr']} crash events")
                add(f"ns3.{cn}.delivery_micro", c["deliv_m"], "fraction", "micro scheme delivery over the same crash events")
                add(f"ns3.{cn}.delivery_diff", c["dd_pt"], "fraction", "micro minus R3")
                add(f"ns3.{cn}.delivery_diff_lo", lb, "fraction", "lower 95% limit, cluster bootstrap")
                b_met.append(mb)
                pb.append(qb)
                if sf == 9:
                    a_met.append(ma)
                    pa.append(qa)
    trace = trace_groups()
    groups = {}
    for g, lo, hi in (("L", 0.0, 0.10), ("M", 0.10, 0.40), ("H", 0.40, 1.01)):
        sel = [r for r in trace["res"] if lo <= r["p"] < hi]
        if len(sel) < 20:
            add(f"trace.{g}.status", "NOT_RUN", "status", f"fewer than 20 devices of LoED half 0 in group {g}", "NOT_RUN")
            b_met.append(False)
            pb.append(1.0)
            continue
        S = {k: np.array([r[k] for r in sel], float) for k in ("n_cr", "air_t", "air_m", "del_t", "del_m")}
        idx = rng.integers(0, len(sel), (NB, len(sel)))
        dd = (S["del_m"][idx].sum(1) - S["del_t"][idx].sum(1)) / S["n_cr"][idx].sum(1)
        ratio_t = S["air_m"][idx].sum(1) / S["air_t"][idx].sum(1)
        lb = float(np.quantile(dd, 0.025))
        add(f"trace.{g}.n_devices", len(sel), "devices", "LoED half 0 (the development half; never a held-out set)", "TRACE_DRIVEN")
        add(f"trace.{g}.delivery_diff", float((S["del_m"].sum() - S["del_t"].sum()) / S["n_cr"].sum()), "fraction", "micro minus R3 (loss depends on the frame index, not the frame length, so the difference is zero by construction unless a pending lifetime expires)", "TRACE_DRIVEN")
        add(f"trace.{g}.delivery_diff_lo", lb, "fraction", "lower 95% limit, bootstrap over devices", "TRACE_DRIVEN")
        add(f"trace.{g}.air_over_r3", float(S["air_m"].sum() / S["air_t"].sum()), "ratio", "micro airtime over R3 two-stage airtime", "TRACE_DRIVEN")
        add(f"trace.{g}.air_over_r3_7byte", float(sum(r["air_m7"] for r in sel) / S["air_t"].sum()), "ratio", "same with the 7-byte design frame (traces have no 13-byte minimum)", "TRACE_DRIVEN")
        add(f"trace.{g}.air_over_r3_hi", float(np.quantile(ratio_t, 0.975)), "ratio", "upper 95% limit", "TRACE_DRIVEN")
        b_met.append(lb >= LIMIT_B)
        pb.append(float((int((dd < LIMIT_B).sum()) + 1) / (NB + 1)))
        groups[g] = lb
    add("hR6_1a.criterion_met", int(all(a_met) and len(a_met) == 8), "flag", "upper 95% limit of the extra airtime at most 0.40 in each of the 8 SF9 cells")
    add("hR6_1a.p", float(max(pa)), "p-value", "largest cell p-value (intersection test)")
    add("hR6_1b.criterion_met", int(all(b_met) and len(b_met) == 19), "flag", "lower 95% limit of the delivery difference at least -0.01 in each of the 16 ns-3 cells and 3 trace groups")
    add("hR6_1b.p", float(max(pb)), "p-value", "largest cell p-value (intersection test)")
    record_many(ent, purge_prefixes=("r6.r1.ns3.", "r6.r1.trace.", "r6.r1.hR6_1a.", "r6.r1.hR6_1b."))
    print({e["name"]: e["value"] for e in ent if "hR6" in e["name"] or "params" in e["name"]})


def main() -> None:
    cmd = sys.argv[1]
    if cmd == "dev":
        dev(int(sys.argv[2]), float(sys.argv[3]))
    elif cmd == "freeze":
        freeze(int(sys.argv[2]))
    elif cmd == "held":
        held()


if __name__ == "__main__":
    main()
