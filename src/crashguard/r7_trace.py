"""Round 7 H-R7-A2 (docs/02_preregistration/PREREGISTRATION_V18.md section 2.4): benign cost of the reserved policy on the LoED half-0 trace groups at SF7 (TRACE_DRIVEN).

    python -m crashguard.r7_trace          # run once; writes keys r7.a2.* and results/tables/r7_trace_cells.json

Same start points and event rows as ``r6_micro.trace_device`` (300 per device, seeds of ``r3_t1.seeded``). Schemes: R3 (full confirm) and R6-1 (13-byte micro frame, the ns-3 size of the stored R6-1 runs).
Duty models: none (regression against the stored ``r6.r1.trace.*`` airtime ratios), H1, H10, T10. Policies: old, reserved. Each start point is an isolated event (fresh duty state).
"""
from __future__ import annotations

import json
import math
import pickle
import random
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from crashguard import r3_t1 as T
from crashguard import r7_engine as E
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7_trace.py"
GUARD = ROOT / "results" / "tables" / "r7_held_started.json"
OUTJ = ROOT / "results" / "tables" / "r7_trace_cells.json"
SCHEMES = {"R3": None, "R61": E.MICRO13}
MODELS = {"none": ("none", 0.0), "H1": ("H", 36.0), "H10": ("H", 360.0), "T10": ("T", 0.0)}
POLICIES = ("old", "reserved")
GROUPS = (("L", 0.0, 0.10), ("M", 0.10, 0.40), ("H", 0.40, 1.01))
NB, SEED = 2000, 42
LIM_DELIV, LIM_TIME = -0.01, 1.10


def event_result(r, s: int, ev: tuple, p_dl: float, rng: random.Random, scheme: str, model: str, policy: str) -> tuple[int, int, float, float]:
    """(is crash event, delivered, time to first alert or inf, airtime)."""
    Ev, F_, y, te = ev
    if F_:  # the single-stage reference of r3_event draws first; the same draws are consumed so that every replay is paired
        T.arrival_trace(r, s, T.FINAL_S + T.COMPUTE3, T.A_AL, p_dl, rng)
    kind, allow = MODELS[model]
    spec = E.Spec(bool(Ev), bool(F_), te, 7, policy, 4, SCHEMES[scheme], T.WIN3)
    o = E.run_event(spec, E.Duty(kind, allow), 0.0, lambda i: bool(r[s + i]), lambda i: rng.random() >= p_dl)
    if Ev and not F_:
        d = int(y == 1 and math.isfinite(o["arr_f"]) and bool(o["cancel_lost"]))
    else:
        d = int(y == 1 and (math.isfinite(o["arr_f"]) or math.isfinite(o["arr_c"])))
    first = min(o["arr_f"], o["arr_c"])
    return int(y == 1), d, first, o["air"]


def device_task(args: tuple) -> dict:
    dev, segs, p_loss, n_start, events = args
    rng0 = T.seeded("t1s", dev, T.SEED)
    adm = T.admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    out: dict = {}
    for scheme in SCHEMES:
        for model in MODELS:
            for pol in POLICIES:
                if model == "none" and pol == "reserved":
                    continue
                n_cr = d = 0
                air = 0.0
                times: list[float] = []
                for q, (si, pos) in enumerate(picks):
                    r = segs[si][0]
                    rng = T.seeded("t1e", dev, q)
                    ev = events[rng.randrange(len(events))]
                    c, dd, first, a = event_result(r, pos, ev, p_loss, rng, scheme, model, pol)
                    n_cr += c
                    d += dd
                    air += a
                    if c and dd and math.isfinite(first):
                        times.append(first)
                out[(scheme, model, pol)] = dict(n_cr=n_cr, deliv=d, air=air, times=np.array(times, np.float32))
    return dict(dev=dev, p=p_loss, cells=out)


def weighted_median(vals_sorted: np.ndarray, w: np.ndarray) -> float:
    c = np.cumsum(w)
    return float(vals_sorted[int(np.searchsorted(c, 0.5 * c[-1]))])


def main(n_start: int = 300, workers: int = 14) -> None:  # noqa: PLR0915
    if GUARD.exists():
        raise SystemExit("run-once guard: results/tables/r7_held_started.json exists; H-R7-A2 is not run twice")
    GUARD.write_text(json.dumps(dict(started=True, preregistration="docs/02_preregistration/PREREGISTRATION_V18.md", note="written before the H-R7-A2 run")), encoding="utf-8")
    links = pickle.loads(T.LINKS.read_bytes())
    devs = sorted(d for d, v in links.items() if v["half"] == 0)
    events = T.load_events()
    tasks = [(d, links[d]["segs"], links[d]["p"], n_start, events) for d in devs]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(device_task, tasks, chunksize=8))
    ent: list[dict] = []

    def add(name, v, unit, note="", origin="TRACE_DRIVEN"):
        ent.append(dict(name=f"r7.a2.{name}", value=(round(v, 6) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin=("NOT_RUN" if v == "NOT_RUN" else origin), source_file=SRC, notes=note))

    rng = np.random.default_rng(SEED)
    regress = {}
    cellsj = {}
    pvals_d, pvals_t = [], []
    ok_d, ok_t = [], []
    for g, lo, hi in GROUPS:
        sel = [r for r in res if lo <= r["p"] < hi]
        add(f"{g}.n_devices", len(sel), "devices", "LoED half 0 (the development half)")
        if len(sel) < 20:
            add(f"{g}.status", "NOT_RUN", "status", "fewer than 20 devices")
            ok_d.append(False)
            ok_t.append(False)
            pvals_d.append(1.0)
            pvals_t.append(1.0)
            continue
        idx = rng.integers(0, len(sel), (NB, len(sel)))
        # regression of the old path with no duty layer against the stored R6-1 trace airtime ratio
        a_m = sum(r["cells"][("R61", "none", "old")]["air"] for r in sel)
        a_t = sum(r["cells"][("R3", "none", "old")]["air"] for r in sel)
        regress[g] = a_m / a_t
        for scheme in SCHEMES:
            for model in ("H1", "H10", "T10"):
                S = {pol: {k: np.array([r["cells"][(scheme, model, pol)][k] for r in sel], float) for k in ("n_cr", "deliv", "air")} for pol in POLICIES}
                dd = (S["reserved"]["deliv"][idx].sum(1) - S["old"]["deliv"][idx].sum(1)) / S["old"]["n_cr"][idx].sum(1)
                pt = (S["reserved"]["deliv"].sum() - S["old"]["deliv"].sum()) / S["old"]["n_cr"].sum()
                lo5 = float(np.quantile(dd, 0.05))
                p_d = float((int((dd < LIM_DELIV).sum()) + 1) / (NB + 1))
                # median time to first alert, pooled over the devices of the resample (weights = bootstrap counts)
                med = {}
                for pol in POLICIES:
                    arrs = [r["cells"][(scheme, model, pol)]["times"] for r in sel]
                    dev_of = np.concatenate([np.full(len(a), i) for i, a in enumerate(arrs)])
                    tv = np.concatenate(arrs)
                    o = np.argsort(tv, kind="stable")
                    med[pol] = (tv[o], dev_of[o])
                cnt = np.stack([np.bincount(row, minlength=len(sel)) for row in idx])
                ratio = np.empty(NB)
                for b in range(NB):
                    m_o = weighted_median(med["old"][0], cnt[b][med["old"][1]].astype(float))
                    m_r = weighted_median(med["reserved"][0], cnt[b][med["reserved"][1]].astype(float))
                    ratio[b] = m_r / m_o
                m_old = weighted_median(med["old"][0], np.ones(len(med["old"][0])))
                m_res = weighted_median(med["reserved"][0], np.ones(len(med["reserved"][0])))
                hi95 = float(np.quantile(ratio, 0.95))
                p_t = float((int((ratio > LIM_TIME).sum()) + 1) / (NB + 1))
                key = f"{g}.{scheme}.{model}"
                add(f"{key}.delivery_diff", float(pt), "fraction", "reserved minus old, same duty model")
                add(f"{key}.delivery_diff_lo95", lo5, "fraction", "one-sided 95% lower limit, cluster bootstrap over devices (2,000 resamples, seed 42)")
                add(f"{key}.median_time_old", m_old, "s", "median time to first alert of delivered crash events, old policy")
                add(f"{key}.median_time_reserved", m_res, "s", "same, reserved policy")
                add(f"{key}.time_ratio", m_res / m_old, "ratio", "reserved over old")
                add(f"{key}.time_ratio_hi95", hi95, "ratio", "one-sided 95% upper limit, cluster bootstrap")
                add(f"{key}.air_ratio", float(S["reserved"]["air"].sum() / S["old"]["air"].sum()), "ratio", "reserved airtime over old")
                ok_d.append(lo5 >= LIM_DELIV)
                ok_t.append(hi95 <= LIM_TIME)
                pvals_d.append(p_d)
                pvals_t.append(p_t)
                cellsj[key] = dict(delivery_diff=float(pt), lo95=lo5, med_old=m_old, med_res=m_res, ratio_hi95=hi95, p_d=p_d, p_t=p_t)
    stored = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    for g in regress:
        sv = stored[f"r6.r1.trace.{g}.air_over_r3"]
        add(f"regression.{g}.air_over_r3", regress[g], "ratio", f"old path, no duty layer; stored r6.r1.trace.{g}.air_over_r3 = {sv}")
        add(f"regression.{g}.matches_stored", int(abs(regress[g] - sv) < 1e-5), "flag", "engine reproduces the stored airtime ratio to 1e-5")
    add("hR7_A2a.criterion_met", int(all(ok_d)), "flag", "one-sided 95% lower limit of the delivery difference at least -0.01 in every cell (3 groups x 2 schemes x 3 duty models)")
    add("hR7_A2a.p", float(max(pvals_d)), "p-value", "largest cell p-value (intersection test)")
    add("hR7_A2b.criterion_met", int(all(ok_t)), "flag", "one-sided 95% upper limit of the median-time ratio at most 1.10 in every cell")
    add("hR7_A2b.p", float(max(pvals_t)), "p-value", "largest cell p-value (intersection test)")
    add("hR7_A2.p", float(max(max(pvals_d), max(pvals_t))), "p-value", "larger of the two parts")
    add("n_cells", len(ok_d), "cells", "cells with at least 20 devices")
    record_many(ent, purge_prefixes=("r7.a2.",))
    OUTJ.write_text(json.dumps(cellsj, indent=1), encoding="utf-8")
    print({e["name"]: e["value"] for e in ent if "regression" in e["name"] or "hR7" in e["name"]})


if __name__ == "__main__":
    main()
