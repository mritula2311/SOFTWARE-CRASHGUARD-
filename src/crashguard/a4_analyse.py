"""Held-out run and analysis of the A1 trace tests (PREREGISTRATION_V15 section 2.3): H-A1b and the trace cells of H-A1c. Keys ``a4.a1.trace.*`` (fresh sniffer links, confirmatory unless the V15 fallback applies)
and ``a4.a1.loedres.*`` (LoED RESERVE devices, descriptive).

    python -m crashguard.a4_a1 held       # build the sniffer links (first look at their loss distribution), replay R3 and the frozen A1 once
    python -m crashguard.a4_a1 analyse    # paired bootstrap over links
"""
from __future__ import annotations

import json
import pickle
from dataclasses import replace
from pathlib import Path

import numpy as np

from crashguard import a4_a1 as A
from crashguard import a4_common as C
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/a4_analyse.py"
OUT_SNIFF = ROOT / "data" / "processed" / "a4_held_sniffer.pkl"
OUT_LOEDRES = ROOT / "data" / "processed" / "a4_held_loedres.pkl"
NB, SEED = 2000, 42
MIN_LINKS_TOTAL, MIN_LINKS_GROUP = 100, 20


def extra_cfgs(cfg: A.Cfg) -> dict:
    return {"R3_sf9": replace(A.R3, sf=9), "A1_sf9": replace(cfg, sf=9)}


def held_a1(cmd: str) -> None:
    if cmd == "held":
        cfg = A.frozen_cfg()
        links = C.build_sniffer() and pickle.loads(C.OUT_SNIFF.read_bytes())
        sel = sorted(links)
        A.run(links, sel, 300, OUT_SNIFF, cfg, extra_cfgs(cfg))
        l3 = pickle.loads((ROOT / "data" / "processed" / "r3_t1_links.pkl").read_bytes())
        res_sel = sorted(d for d, v in l3.items() if v["half"] == 0)
        A.run(l3, res_sel, 300, OUT_LOEDRES, cfg, extra_cfgs(cfg))
    else:
        out = {}
        for tag, f, conf in (("trace", OUT_SNIFF, True), ("loedres", OUT_LOEDRES, False)):
            if f.exists():
                out[tag] = analyse_traces(f, f"a4.a1.{tag}.", confirmatory=conf)
        record_summary(out)
        for k, v in out.items():
            print(k, {x: v[x] for x in ("hA1b", "hA1c") if x in v})


def groups_of(res: list) -> dict:
    return {g: [i for i, x in enumerate(res) if lo <= x["p"] < hi] for g, lo, hi in A.T1.GROUPS}


def val(res: list, name: str, key: str) -> np.ndarray:
    return np.array([x["acc"][name][key] for x in res], float)


def analyse_traces(f: Path, prefix: str, confirmatory: bool, record: bool = True) -> dict:
    d = pickle.loads(f.read_bytes())
    res = d["res"]
    rng = np.random.default_rng(SEED)
    ent: list[dict] = []
    lab = "confirmatory (fresh data)" if confirmatory else "descriptive (LoED RESERVE devices)"

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"{prefix}{name}", value=round(value, 6) if isinstance(value, float) else value, unit=unit, origin="NOT_RUN" if value == "NOT_RUN" else "TRACE_DRIVEN", source_file=SRC, notes=f"{lab}. {notes}"))

    n = len(res)
    gi = groups_of(res)
    add("n_links", n, "links", "links included (V14 rules)")
    add("invariants.late", d["inv"]["late"], "count", "provisional frames ending after the deadline (must be 0)")
    add("invariants.duty", d["inv"]["duty"], "count", "transmissions above the duty limit (must be 0)")
    add("invariants.overrun", d["inv"]["overrun"], "count", "attempts beyond the sequence (must be 0)")
    for g, idx in gi.items():
        add(f"{g}.n_links", len(idx), "links", f"links with loss in group {g}")
    nE = val(res, "A1", "n_E")
    pa = val(res, "A1", "prov_ok") / np.maximum(nE, 1)
    pr = val(res, "R3", "prov_ok") / np.maximum(nE, 1)
    B = rng.integers(0, n, size=(NB, n))
    diff = pa - pr
    bd = diff[B].mean(1)
    pt = float(diff.mean())
    lo_ = float(np.quantile(bd, 0.025))
    ok_n = n >= MIN_LINKS_TOTAL
    met_b = bool(pt >= 0.03 and lo_ > 0) and (ok_n or not confirmatory)
    p_b = float((np.count_nonzero(bd <= 0) + 1) / (NB + 1))
    add("hA1b.prov_a1", float(pa.mean()), "fraction", "mean over links of the share of early-alarm events whose provisional frame reaches the base before 10 s, A1")
    add("hA1b.prov_r3", float(pr.mean()), "fraction", "same for R3 (14-byte flash, 4 tries)")
    add("hA1b.diff", pt, "fraction", "A1 minus R3, mean over links")
    add("hA1b.diff_lo", lo_, "fraction", "95% paired bootstrap over links, 2,000 resamples, seed 42")
    add("hA1b.diff_hi", float(np.quantile(bd, 0.975)), "fraction", "95% paired bootstrap over links")
    add("hA1b.criterion_met", int(met_b), "flag", "point difference at least 0.03, lower 95% limit above 0, and at least 100 links when confirmatory")
    add("hA1b.p_raw", p_b, "p", "one-sided bootstrap p of H0: difference at most 0")
    for g, idx in gi.items():
        if len(idx):
            Bg = rng.integers(0, len(idx), size=(NB, len(idx)))
            dg = diff[idx]
            bg = dg[Bg].mean(1)
            add(f"hA1b.{g}.diff", float(dg.mean()), "fraction", f"group {g}, descriptive")
            add(f"hA1b.{g}.diff_lo", float(np.quantile(bg, 0.025)), "fraction", "95% bootstrap over links")
            add(f"hA1b.{g}.diff_hi", float(np.quantile(bg, 0.975)), "fraction", "95% bootstrap over links")
            add(f"hA1b.{g}.prov_a1", float(pa[idx].mean()), "fraction", "")
            add(f"hA1b.{g}.prov_r3", float(pr[idx].mean()), "fraction", "")
    # H-A1c trace cells
    cells = {}
    for g, idx in gi.items():
        if len(idx) < MIN_LINKS_GROUP:
            add(f"hA1c.{g}.criterion_met", "NOT_RUN", "status", f"fewer than {MIN_LINKS_GROUP} links in group {g}")
            cells[g] = None
            continue
        da, dr, nc = (val(res, k, c)[idx] for k, c in (("A1", "two_d"), ("R3", "two_d"), ("A1", "n_cr")))
        aa, ar, s1 = (val(res, k, c)[idx] for k, c in (("A1", "two_air"), ("R3", "two_air"), ("A1", "single_air")))
        Bg = rng.integers(0, len(idx), size=(NB, len(idx)))
        dd = (da[Bg].sum(1) - dr[Bg].sum(1)) / nc[Bg].sum(1)
        pt_dd = float((da.sum() - dr.sum()) / nc.sum())
        lo_dd = float(np.quantile(dd, 0.025))
        met = bool(lo_dd >= -0.01)
        p_c = float((np.count_nonzero(dd < -0.01) + 1) / (NB + 1))
        ratio_a = aa.sum() / s1.sum() - 1.0
        ratio_r = ar.sum() / s1.sum() - 1.0
        rb = aa[Bg].sum(1) / s1[Bg].sum(1) - 1.0
        add(f"hA1c.{g}.delivery_diff", pt_dd, "fraction", "A1 minus R3 event delivery of crash events")
        add(f"hA1c.{g}.delivery_diff_lo", lo_dd, "fraction", "95% bootstrap over links")
        add(f"hA1c.{g}.criterion_met", int(met), "flag", "lower 95% limit at least -0.01")
        add(f"hA1c.{g}.p_raw", p_c, "p", "share of resamples with a difference below -0.01, plus one over resamples plus one")
        add(f"{g}.extra_air_a1", float(ratio_a), "ratio", "A1 transmit airtime over single-stage airtime minus 1 (descriptive; SF7 timing)")
        add(f"{g}.extra_air_a1_hi", float(np.quantile(rb, 0.975)), "ratio", "95% bootstrap upper limit")
        add(f"{g}.extra_air_r3", float(ratio_r), "ratio", "the same for R3 (descriptive)")
        for nm in ("A1_sf9", "R3_sf9"):
            if nm in d["res"][0]["acc"]:
                ps = val(res, nm, "prov_ok")[idx] / np.maximum(val(res, nm, "n_E")[idx], 1)
                add(f"{g}.sf9.prov_{nm[:2].lower()}", float(ps.mean()), "fraction", "descriptive: SF9 timing, provisional delivery within 10 s")
        cells[g] = dict(met=met, p=p_c, point=pt_dd, lo=lo_dd)
    out = dict(hA1b=dict(met=met_b, p=p_b, point=pt, lo=lo_, n=n), hA1c=cells, n=n, groups={g: len(i) for g, i in gi.items()})
    ok_c = all(c is not None and c["met"] for c in cells.values())
    out["hA1c_met"] = ok_c
    out["hA1c_p"] = max([c["p"] for c in cells.values() if c] or [1.0])
    add("hA1c.criterion_met", int(ok_c), "flag", "all three groups meet the criterion (a group with fewer than 20 links is NOT_RUN and counts as not met)")
    add("hA1c.p_raw", float(out["hA1c_p"]), "p", "largest group p")
    if record:
        record_many(ent, purge_prefixes=(prefix,))
    return out


def record_summary(out: dict) -> None:
    (ROOT / "results" / "tables" / "a4_a1_trace_summary.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
