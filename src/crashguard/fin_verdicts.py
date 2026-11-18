"""Holm correction and verdicts over the 18 hypotheses of docs/02_preregistration/PREREGISTRATION_V5.md (rule 5). NOT_RUN hypotheses enter with p = 1 and are never supported. Keys f.holm.*."""
from __future__ import annotations

from crashguard import fin_sim as FS
from crashguard.fin_common import Entries

HYP = [  # name, original hypothesis, label, key stem
    ("H-B2", "P1+ against P0 (flash and hold on the severity table)", "SIMULATED", "f.b2.hB2"),
    ("H-C3", "synthetic requirement matches the real one within one range step", "SIMULATED", "f.c.hC3"),
    ("H-F1", "H-P1: direct classifier against the anchored estimator", "EXPLORATORY-REVISED", "f.f1.{S}.hF1"),
    ("H-F1b", "H-P2: anchored interval", "EXPLORATORY-REVISED", "f.f1.{S}.hF1b"),
    ("H-F1c", "H-P3a: abstention at 70% retention", "EXPLORATORY-REVISED", "f.f1.{S}.hF1c"),
    ("H-F1d", "H-X6 on splits G and O", "EXPLORATORY-REVISED", "f.f1.hF1d"),
    ("H-F1e", "H-X5 rank preservation", "EXPLORATORY-REVISED", "f.f1.hF1e"),
    ("H-F2a", "H-P4b: augmentation, recall at the 1% target", "EXPLORATORY-REVISED", "f.f2.hF2a"),
    ("H-F2b", "H-X3: group-aware training", "EXPLORATORY-REVISED", "f.f2.hF2b"),
    ("H-F2c", "H-X2: trigger cascade", "EXPLORATORY-REVISED", "f.f2.hF2c"),
    ("H-F2d", "H-X1: fixed-point forest (AP and flash)", "EXPLORATORY-REVISED", "f.f2.hF2d"),
    ("H-F2e", "H-X8: sequential rule", "EXPLORATORY-REVISED", "f.f2.hF2e"),
    ("H-F2f", "H-P4c: calibration over the trivial rule", "EXPLORATORY-REVISED", "f.f2.hF2f"),
    ("H-F3a", "N28: P3 against the lowered table at equal escalation", "SIMULATED, EXPLORATORY-REVISED", "f.f3.hF3a"),
    ("H-F3b", "H-P3b: abstain routing against the lowered table", "SIMULATED, EXPLORATORY-REVISED", "f.f3.hF3b"),
    ("H-G3a", "slotted fast path against pure ALOHA", "SIMULATED", "f.g.g3.hG3a"),
    ("H-G3b", "listen-before-talk against duty-cycle-only access", "SIMULATED", "f.g.g3.hG3b"),
    ("H-G3c", "V2V relay against no relay", "SIMULATED", "f.g.g3.hG3c"),
]


def main() -> dict:
    R = FS.results_map()
    rows = []
    for name, desc, label, stem in HYP:
        scheme = "cv" if "f.f1.cv.hF1.criterion_met" in R else "sealed"
        s = stem.replace("{S}", scheme)
        met, p = R.get(f"{s}.criterion_met"), R.get(f"{s}.p_raw")
        notrun = met in (None, "NOT_RUN") or p is None
        rows.append(dict(name=name, desc=desc, label=label, met=0 if notrun else int(met), p=1.0 if notrun else float(p), notrun=notrun, stem=s))
    order = sorted(range(len(rows)), key=lambda i: rows[i]["p"])
    m = len(rows)
    run_max = 0.0
    for rank, i in enumerate(order):
        run_max = max(run_max, (m - rank) * rows[i]["p"])
        rows[i]["p_holm"] = min(1.0, run_max)
    E = Entries("f.holm", "src/crashguard/fin_verdicts.py")
    E.add("family_size", m, "hypotheses", "SIMULATED", "preregistered family (NOT_RUN hypotheses enter with p = 1)")
    for r in rows:
        v = "NOT_RUN" if r["notrun"] else ("SUPPORTED" if r["met"] and r["p_holm"] < 0.05 else "MIXED" if r["met"] else "NOT SUPPORTED")
        r["verdict"] = v
        k = r["name"].replace("-", "").lower()
        E.add(f"{k}.p_raw", r["p"], "p", "SIMULATED", f"from {r['stem']}")
        E.add(f"{k}.p_holm", round(r["p_holm"], 4), "p", "SIMULATED")
        E.add(f"{k}.criterion_met", "NOT_RUN" if r["notrun"] else r["met"], "flag", "NOT_RUN" if r["notrun"] else "SIMULATED", "not run: the reason is in the NOT_RUN entry of the study (docs/02_preregistration/PREREGISTRATION_V5.md addendum 2)" if r["notrun"] else "")
        E.add(f"{k}.verdict", v, "text", "NOT_RUN" if r["notrun"] else "SIMULATED", f"{r['desc']}; label {r['label']}; scheme for F1: {scheme}")
    E.write()
    for r in rows:
        print(f"{r['name']:7s} met={r['met']} p={r['p']:.3f} holm={r['p_holm']:.3f} {r['verdict']}")
    return {r["name"]: r for r in rows}


if __name__ == "__main__":
    main()
