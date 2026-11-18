"""Round 7b H-R7b-2 (docs/02_preregistration/PREREGISTRATION_V19.md section 2): benign cost of the reserve for k = 4 follow-up events on the LoED half-0 trace groups at SF7, fresh start points. TRACE_DRIVEN.

    python -m crashguard.r7b_trace          # run once; keys r7b.a2.*, results/tables/r7b_trace_cells.json

As ``r7_trace`` with: trace seed 4242 for the start points (``seeded("t1s", dev, 4242)``) and the event rows (``seeded("t1e", dev, q, 4242)``), bootstrap seed 4242, and the policies old and reserved with k = 1, 2, 3, 4
(k = 4 is the registered comparison, k = 1 to 3 are DESCRIPTIVE). Run-once guard: results/tables/r7b_held_started.json.
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
from crashguard.r7_trace import GROUPS, LIM_DELIV, LIM_TIME, MODELS, NB, SCHEMES, weighted_median
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7b_trace.py"
GUARD = ROOT / "results" / "tables" / "r7b_held_started.json"
OUTJ = ROOT / "results" / "tables" / "r7b_trace_cells.json"
SEED = 4242
POL = (("old", "old", 1), ("res1", "reserved", 1), ("res2", "reserved", 2), ("res3", "reserved", 3), ("res4", "reserved", 4))


def event_result(r, s: int, ev: tuple, p_dl: float, rng: random.Random, scheme: str, model: str, policy: str, n_res: int) -> tuple[int, int, float, float]:
    Ev, F_, y, te = ev
    if F_:  # the single-stage reference of r3_event draws first; the same draws are consumed so that every replay is paired
        T.arrival_trace(r, s, T.FINAL_S + T.COMPUTE3, T.A_AL, p_dl, rng)
    kind, allow = MODELS[model]
    spec = E.Spec(bool(Ev), bool(F_), te, 7, policy, 4, SCHEMES[scheme], T.WIN3, n_res=n_res)
    o = E.run_event(spec, E.Duty(kind, allow), 0.0, lambda i: bool(r[s + i]), lambda i: rng.random() >= p_dl)
    if Ev and not F_:
        d = int(y == 1 and math.isfinite(o["arr_f"]) and bool(o["cancel_lost"]))
    else:
        d = int(y == 1 and (math.isfinite(o["arr_f"]) or math.isfinite(o["arr_c"])))
    return int(y == 1), d, min(o["arr_f"], o["arr_c"]), o["air"]


def device_task(args: tuple) -> dict:
    dev, segs, p_loss, n_start, events = args
    rng0 = T.seeded("t1s", dev, SEED)
    adm = T.admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    out: dict = {}
    for scheme in SCHEMES:
        for model in MODELS:
            for (label, pol, n_res) in POL:
                if model == "none" and label != "old":
                    continue
                n_cr = d = 0
                air = 0.0
                times: list[float] = []
                for q, (si, pos) in enumerate(picks):
                    r = segs[si][0]
                    rng = T.seeded("t1e", dev, q, SEED)
                    ev = events[rng.randrange(len(events))]
                    c, dd, first, a = event_result(r, pos, ev, p_loss, rng, scheme, model, pol, n_res)
                    n_cr += c
                    d += dd
                    air += a
                    if c and dd and math.isfinite(first):
                        times.append(first)
                out[(scheme, model, label)] = dict(n_cr=n_cr, deliv=d, air=air, times=np.array(times, np.float32))
    return dict(dev=dev, p=p_loss, cells=out)


def regression_task(args: tuple) -> tuple:
    """Old path, no duty layer, the V18 start points (seed 42): airtime of R3 and R6-1, for the check against the stored r6.r1.trace ratios."""
    dev, segs, p_loss, n_start, events = args
    rng0 = T.seeded("t1s", dev, T.SEED)
    adm = T.admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    tot = {"R3": 0.0, "R61": 0.0}
    for scheme in SCHEMES:
        for q, (si, pos) in enumerate(picks):
            rng = T.seeded("t1e", dev, q)
            ev = events[rng.randrange(len(events))]
            tot[scheme] += event_result(segs[si][0], pos, ev, p_loss, rng, scheme, "none", "old", 1)[3]
    return p_loss, tot["R3"], tot["R61"]


def main(n_start: int = 300, workers: int = 14) -> None:  # noqa: PLR0915
    if GUARD.exists():
        raise SystemExit("run-once guard: results/tables/r7b_held_started.json exists; H-R7b-2 is not run twice")
    GUARD.write_text(json.dumps(dict(started=True, preregistration="docs/02_preregistration/PREREGISTRATION_V19.md", note="written before the H-R7b-2 run")), encoding="utf-8")
    links = pickle.loads(T.LINKS.read_bytes())
    devs = sorted(d for d, v in links.items() if v["half"] == 0)
    events = T.load_events()
    tasks = [(d, links[d]["segs"], links[d]["p"], n_start, events) for d in devs]
    with ProcessPoolExecutor(workers) as ex:
        reg = list(ex.map(regression_task, tasks, chunksize=8))
    stored0 = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    for g, lo, hi in GROUPS:
        sel = [x for x in reg if lo <= x[0] < hi]
        ratio = sum(x[2] for x in sel) / sum(x[1] for x in sel)
        if abs(ratio - stored0[f"r6.r1.trace.{g}.air_over_r3"]) >= 1e-5:
            raise SystemExit(f"regression mismatch in group {g}: {ratio} against the stored value; the run stops (V19 section 2)")
    reg_ok = True
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(device_task, tasks, chunksize=8))
    ent: list[dict] = []

    def add(name, v, unit, note="", origin="TRACE_DRIVEN"):
        ent.append(dict(name=f"r7b.a2.{name}", value=(round(v, 6) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin=("NOT_RUN" if v == "NOT_RUN" else origin), source_file=SRC, notes=note))

    rng = np.random.default_rng(SEED)
    cellsj: dict = {}
    pd_, pt_, ok_d, ok_t = [], [], [], []
    stored = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    for g, lo, hi in GROUPS:
        sel = [r for r in res if lo <= r["p"] < hi]
        add(f"{g}.n_devices", len(sel), "devices", "LoED half 0 (the development half)")
        if len(sel) < 20:
            add(f"{g}.status", "NOT_RUN", "status", "fewer than 20 devices")
            ok_d.append(False)
            ok_t.append(False)
            pd_.append(1.0)
            pt_.append(1.0)
            continue
        a_m = sum(r["cells"][("R61", "none", "old")]["air"] for r in sel)
        a_t = sum(r["cells"][("R3", "none", "old")]["air"] for r in sel)
        sv = stored[f"r6.r1.trace.{g}.air_over_r3"]
        add(f"regression.{g}.air_over_r3", a_m / a_t, "ratio", f"old path, no duty layer, fresh start points; stored r6.r1.trace.{g}.air_over_r3 = {sv} (start points differ, so the ratio is expected to agree only closely)")
        idx = rng.integers(0, len(sel), (NB, len(sel)))
        for scheme in SCHEMES:
            for model in ("H1", "H10", "T10"):
                for (label, _p, _n) in POL[1:]:
                    S = {pol: {k: np.array([r["cells"][(scheme, model, pol)][k] for r in sel], float) for k in ("n_cr", "deliv", "air")} for pol in ("old", label)}
                    dd = (S[label]["deliv"][idx].sum(1) - S["old"]["deliv"][idx].sum(1)) / S["old"]["n_cr"][idx].sum(1)
                    pt = (S[label]["deliv"].sum() - S["old"]["deliv"].sum()) / S["old"]["n_cr"].sum()
                    lo5 = float(np.quantile(dd, 0.05))
                    p_d = float((int((dd < LIM_DELIV).sum()) + 1) / (NB + 1))
                    med = {}
                    for pol in ("old", label):
                        arrs = [r["cells"][(scheme, model, pol)]["times"] for r in sel]
                        dev_of = np.concatenate([np.full(len(a), i) for i, a in enumerate(arrs)])
                        tv = np.concatenate(arrs)
                        o = np.argsort(tv, kind="stable")
                        med[pol] = (tv[o], dev_of[o])
                    cnt = np.stack([np.bincount(row, minlength=len(sel)) for row in idx])
                    ratio = np.array([weighted_median(med[label][0], cnt[b][med[label][1]].astype(float)) / weighted_median(med["old"][0], cnt[b][med["old"][1]].astype(float)) for b in range(NB)])
                    m_old = weighted_median(med["old"][0], np.ones(len(med["old"][0])))
                    m_res = weighted_median(med[label][0], np.ones(len(med[label][0])))
                    hi95 = float(np.quantile(ratio, 0.95))
                    p_t = float((int((ratio > LIM_TIME).sum()) + 1) / (NB + 1))
                    key = f"{g}.{scheme}.{model}.{label}"
                    add(f"{key}.delivery_diff", float(pt), "fraction", "policy minus old, same duty model")
                    add(f"{key}.delivery_diff_lo95", lo5, "fraction", "one-sided 95% lower limit, cluster bootstrap over devices (2,000 resamples, seed 4242)")
                    add(f"{key}.median_time_old", m_old, "s")
                    add(f"{key}.median_time_policy", m_res, "s")
                    add(f"{key}.time_ratio", m_res / m_old, "ratio")
                    add(f"{key}.time_ratio_hi95", hi95, "ratio", "one-sided 95% upper limit, cluster bootstrap")
                    add(f"{key}.air_ratio", float(S[label]["air"].sum() / S["old"]["air"].sum()), "ratio")
                    cellsj[key] = dict(delivery_diff=float(pt), lo95=lo5, med_old=m_old, med_res=m_res, ratio=m_res / m_old, ratio_hi95=hi95, p_d=p_d, p_t=p_t)
                    if label == "res4":
                        ok_d.append(lo5 >= LIM_DELIV)
                        ok_t.append(hi95 <= LIM_TIME)
                        pd_.append(p_d)
                        pt_.append(p_t)
    add("hR7b_2a.criterion_met", int(all(ok_d)), "flag", "k = 4 policy: lower 95% limit of the delivery difference at least -0.01 in every cell (3 groups x 2 schemes x 3 duty models)")
    add("hR7b_2a.p", float(max(pd_)), "p-value", "largest cell p-value (intersection test)")
    add("hR7b_2b.criterion_met", int(all(ok_t)), "flag", "k = 4 policy: upper 95% limit of the median-time ratio at most 1.10 in every cell")
    add("hR7b_2b.p", float(max(pt_)), "p-value", "largest cell p-value (intersection test)")
    add("hR7b_2.p", float(max(max(pd_), max(pt_))), "p-value", "larger of the two parts")
    add("hR7b_2.criterion_met", int(all(ok_d) and all(ok_t)), "flag")
    add("regression.matches_stored_seed42", int(reg_ok), "flag", "old path, no duty layer, V18 start points: engine reproduces the stored airtime ratio of every group to 1e-5 (checked before the run)")
    add("n_cells", len(ok_d), "cells", "cells with at least 20 devices")
    add("cells_failing_delivery", int(len(ok_d) - sum(ok_d)), "cells")
    add("cells_failing_time", int(len(ok_t) - sum(ok_t)), "cells")
    record_many(ent, purge_prefixes=("r7b.a2.",))
    OUTJ.write_text(json.dumps(cellsj, indent=1), encoding="utf-8")
    print({e["name"]: e["value"] for e in ent if "hR7b" in e["name"] or "regression" in e["name"] or e["name"].endswith("n_cells") or "cells_failing" in e["name"]})


if __name__ == "__main__":
    main()
