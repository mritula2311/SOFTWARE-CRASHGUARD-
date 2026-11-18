"""F3 (SIMULATED, EXPLORATORY-REVISED): feed the improved severity estimates of F1 (grouped nested cross-validation, +-16 g, 100 Hz, 913 real records: out-of-fold estimates) into the UA-SCT simulator on the HELD-OUT grid of B2
(12 cells, seeds 9000 + h, 30 seeds). H-F3a: original N28 rule (P3 beats the lowered-threshold table at equal escalation); H-F3b: original H-P3b (abstain routing against the lowered table). Docs: docs/02_preregistration/PREREGISTRATION_V5.md F3."""
from __future__ import annotations

import pickle

import numpy as np

from crashguard import fin_b2 as B2
from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard import pp_common as PC
from crashguard import s11_sct as S
from crashguard.fin_common import Entries
from crashguard.fin_f1 import OUT, RANGES  # noqa: F401
from crashguard.pp_ctx import Ctx

SRC = "results/tables/f_f3.csv"
RATIO_GRID = (0.0, 0.5, 1.0, 2.0, 5.0)  # V7: block A sets (0.0,) to take real-only estimates
G.KEY["P2e"], G.BASE["P2e"] = "lowered", "P2"


def pairs_from_cv(runs: dict, cx: Ctx, rg: float = 16.0) -> dict:
    """Pooled out-of-fold pairs: true class, improved point class, upper class (anchored x q), abstain class and validation-side classes for choosing the lowering factor."""
    rows = dict(te=[], pt=[], up=[], ab=[], va_pt=[], va_up=[], va_ab=[], va_plain=[])
    for k in range(5):
        run, Rg = runs[f"cv{k}"]["run"], runs[f"cv{k}"]["ranges"][rg]
        va, te = run["va"], run["te"]
        refv = cx.ref[va]
        rb = min(RATIO_GRID, key=lambda r: (round(float(np.quantile(np.abs(Rg[f"c_va_{r:g}"] - refv) / refv, 0.9)), 9), r))
        cv, ct = Rg[f"c_va_{rb:g}"], Rg[f"c_te_{rb:g}"]
        ratio = np.sort(refv / np.maximum(cv, 1e-6))
        alpha = max(0.02, 0.10 - float((refv < cv).mean()))
        q = float(ratio[min(int(np.ceil((len(ratio) + 1) * (1 - alpha))) - 1, len(ratio) - 1)])
        rr = min(RATIO_GRID, key=lambda r: (round(float(np.quantile(np.abs(Rg[f"c_va_{r:g}"][Rg[f"rel_va_{r:g}"] <= np.quantile(Rg[f"rel_va_{r:g}"], 0.7)] - refv[Rg[f"rel_va_{r:g}"] <= np.quantile(Rg[f"rel_va_{r:g}"], 0.7)]) / refv[Rg[f"rel_va_{r:g}"] <= np.quantile(Rg[f"rel_va_{r:g}"], 0.7)], 0.9)), 9), r))
        thr = np.quantile(Rg[f"rel_va_{rr:g}"], 0.7)
        pt, up = PC.cls_of(ct), PC.cls_of(ct * q)
        ab = np.where(Rg[f"rel_te_{rr:g}"] > thr, 3, pt)
        vp, vu = PC.cls_of(cv), PC.cls_of(cv * q)
        vab = np.where(Rg[f"rel_va_{rr:g}"] > thr, 3, vp)
        rows["te"].append(te)
        rows["pt"].append(pt)
        rows["up"].append(up)
        rows["ab"].append(ab)
        rows["va_pt"].append(vp)
        rows["va_up"].append(vu)
        rows["va_ab"].append(vab)
        rows["va_plain"].append((cv, cx.y[va]))
    te = np.concatenate(rows["te"])
    out = dict(te=te, true=cx.y[te], group=cx.group[te], point=np.concatenate(rows["pt"]), upper=np.concatenate(rows["up"]), abstain=np.concatenate(rows["ab"]))
    # lowering factors chosen on the validation rows (no simulated outcome): equal escalation to P3 and to the abstain rule
    cvv = np.concatenate([r[0] for r in rows["va_plain"]])
    yv = np.concatenate([r[1] for r in rows["va_plain"]])
    non = yv < 2

    def esc(c):
        return float((c[non] >= 2).mean())

    for nm, key in (("f_p3", "va_up"), ("f_ab", "va_ab")):
        tgt = esc(np.concatenate(rows[key]))
        out[nm] = float(min(np.round(np.arange(0.30, 1.0001, 0.0025), 4), key=lambda f: abs(esc(PC.cls_of(cvv / f)) - tgt)))
    # lowered classes of the test pairs: the improved estimate divided by f (two versions)
    ct_all = np.concatenate([runs[f"cv{k}"]["ranges"][rg][f"c_te_{rb_of(runs, cx, k, rg):g}"] for k in range(5)])
    out["lowered_p3"], out["lowered_ab"] = PC.cls_of(ct_all / out["f_p3"]), PC.cls_of(ct_all / out["f_ab"])
    return out


def rb_of(runs, cx, k, rg):
    run, Rg = runs[f"cv{k}"]["run"], runs[f"cv{k}"]["ranges"][rg]
    refv = cx.ref[run["va"]]
    return min(RATIO_GRID, key=lambda r: (round(float(np.quantile(np.abs(Rg[f"c_va_{r:g}"] - refv) / refv, 0.9)), 9), r))


def main() -> None:
    runs = pickle.loads(OUT.read_bytes())
    cx = Ctx()
    E = Entries("f.f3", SRC)
    if not all(f"cv{k}" in runs for k in range(5)):
        E.add("status", "NOT_RUN: F1 cross-validation runs missing", "text", "NOT_RUN")
        E.write()
        return
    pr = pairs_from_cv(runs, cx)
    true = pr["true"]
    G_ = PC.GBoot(pr["group"])
    sev = true >= 2
    mis = lambda c: ((c < 2) & sev).astype(float)  # noqa: E731
    non = true < 2

    def pool(name, fn):
        pt, lo, hi = G_.ci(fn)
        for suf, v in (("", pt), ("_lo", lo), ("_hi", hi)):
            E.add(f"{name}{suf}", round(float(v), 4), "fraction", "MEASURED_SOFTWARE", "pooled out-of-fold pairs (F1 improved estimates), grouped bootstrap; EXPLORATORY-REVISED")

    for nm, c in (("p3", pr["upper"]), ("p1e_p3", pr["lowered_p3"]), ("abstain", pr["abstain"]), ("p1e_ab", pr["lowered_ab"]), ("point", pr["point"])):
        pool(f"pool.mis_triage.{nm}", lambda i, c=c: mis(c)[i][sev[i]].mean())
        pool(f"pool.escalation.{nm}", lambda i, c=c: (c[i][non[i]] >= 2).mean())
    E.add("pool.f_equal_escalation_p3", pr["f_p3"], "factor", "MEASURED_SOFTWARE", "chosen on validation rows")
    E.add("pool.f_equal_escalation_abstain", pr["f_ab"], "factor", "MEASURED_SOFTWARE", "chosen on validation rows")
    for tag, a, b in (("hF3a", "p1e_p3", "p3"), ("hF3b", "p1e_ab", "abstain")):
        ca, cb = {"p1e_p3": pr["lowered_p3"], "p1e_ab": pr["lowered_ab"]}[a], {"p3": pr["upper"], "abstain": pr["abstain"]}[b]
        pt, d = G_.stat(lambda i: mis(cb)[i][sev[i]].mean() - mis(ca)[i][sev[i]].mean())
        s = PC.summ(pt, d)
        for suf, v in zip(("", "_lo", "_hi"), s):
            E.add(f"{tag}.pool_mis_triage_diff{suf}", round(float(v), 4), "fraction", "MEASURED_SOFTWARE", f"{b} minus the lowered table at equal escalation, pooled out-of-fold pairs")
        E.add(f"{tag}.pool_clause_met", int(s[0] <= (0.0 if tag == "hF3a" else -0.02) and s[2] < 0), "flag", "MEASURED_SOFTWARE", "interval entirely below zero" + (" and at most -0.02" if tag == "hF3b" else ""))
        E.add(f"{tag}.p_pool", round(float(PC.p_above(d, 0.0 if tag == "hF3a" else -0.02)), 4), "p", "MEASURED_SOFTWARE")
    # simulator cells: pools of the improved pairs, legacy world (no G features), HELD-OUT grid of B2
    base = S.load_pools()
    pools = {**base, "classes": {16.0: dict(true=true.astype(int), point=pr["point"].astype(int), upper=pr["upper"].astype(int), lowered=pr["lowered_p3"].astype(int), abstain=pr["abstain"].astype(int))}}
    pools_ab = {**base, "classes": {16.0: dict(true=true.astype(int), point=pr["point"].astype(int), upper=pr["upper"].astype(int), lowered=pr["lowered_ab"].astype(int), abstain=pr["abstain"].astype(int))}}
    t = FS.tuned()
    jobs = []
    for n, p, b in B2.HO_CELLS:
        cell = dict(name=f"n{n}_p{int(p * 100)}_b{b}", n=n, p=p, sf=8, duty=0.01, b=b)
        for pol, pl in (("P1e", pools), ("P2e", pools), ("P3", pools), ("P3b", pools_ab), ("P1e_ab", pools_ab)):
            real = "P1e" if pol == "P1e_ab" else pol
            for h in range(30):
                c = G.cfg_for(real, cell, 9000, h, pl, t, f"f3_{cell['name']}", world={})
                jobs.append((c, dict(cell=cell["name"], pol=pol, hour=h)))
    R = FS.run_jobs(jobs)
    R.to_csv("results/tables/f_f3.csv", index=False)
    E.add("runs", int(len(R)), "runs", "SIMULATED")
    E.add("runs_exceeding_duty", int(R.duty_exceeded.sum()), "runs", "SIMULATED", "must be 0")
    cells = [dict(cell=c) for c in sorted(R.cell.unique())]
    # H-F3a (simulated clause): P3 against P2e (equal-escalation SCT) and P1e on critical reach within 10 s
    for comp in ("P2e", "P1e"):
        v = FS.verdict_cells(R, cells, comp, "P3", "reach10_critical")
        E.add(f"hF3a.p3_vs_{comp}.n_cells_gain5", v["n_gain"], "cells", "SIMULATED", "P3 minus the comparator >= 0.05 with the interval above zero")
        E.add(f"hF3a.p3_vs_{comp}.n_cells_lose2", v["n_lose"], "cells", "SIMULATED")
        E.add(f"hF3a.p3_vs_{comp}.criterion_met", int(v["met"]), "flag", "SIMULATED")
        E.add(f"hF3a.p3_vs_{comp}.p_raw", round(v["p"], 4), "p", "SIMULATED")
        if comp == "P2e":
            sim = v
    pool_ok = bool(E.ent and [e for e in E.ent if e["name"] == "f.f3.hF3a.pool_clause_met"][0]["value"])
    E.add("hF3a.criterion_met", int(pool_ok and sim["met"]), "flag", "SIMULATED", "pool-level mis-triage clause AND the simulated reach clause against P2e (EXPLORATORY-REVISED)")
    E.add("hF3a.p_raw", round(max(sim["p"], [e for e in E.ent if e["name"] == "f.f3.hF3a.p_pool"][0]["value"]), 4), "p", "SIMULATED")
    # H-F3b: simulated cells are descriptive (mis-triage, escalation, reach) as in the original; the criterion is pool level
    for m in ("mis_triage", "escalation", "reach10_critical", "reach30_critical", "node_air_share"):
        for pol in ("P3b", "P1e_ab", "P3", "P1e", "P2e"):
            a = G.arr(R, pol, m, sorted(R.cell.unique()))
            tri = G.pooled(a)
            for suf, v in zip(("", "_lo", "_hi"), tri):
                E.add(f"cells.{pol}.{m}{suf}", None if v != v else round(float(v), 5), "fraction", "SIMULATED", "mean over 12 held-out cells of the seed mean")
    E.add("hF3b.criterion_met", int([e for e in E.ent if e["name"] == "f.f3.hF3b.pool_clause_met"][0]["value"]), "flag", "MEASURED_SOFTWARE", "original H-P3b criterion at pool level")
    E.add("hF3b.p_raw", [e for e in E.ent if e["name"] == "f.f3.hF3b.p_pool"][0]["value"], "p", "MEASURED_SOFTWARE")
    E.write()


if __name__ == "__main__":
    main()
