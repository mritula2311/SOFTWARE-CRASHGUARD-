"""Holm correction over the nine tested v2 hypotheses and the verdict of every v2 hypothesis (docs/02_preregistration/PREREGISTRATION_V2.md sections 0 and 8). Reads only ``results/results.json`` and the run tables of Study B;
writes ``v2.verdict.*`` and ``v2.holm.*`` and ``results/tables/v2_verdicts.csv``. No threshold is chosen here: every rule is the one written before the runs.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import v2_b_study as VB
from crashguard.v2_common import Entries, holm

R = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
ORIGIN = {"H-A1": "MEASURED_SOFTWARE", "H-A2": "MEASURED_SOFTWARE", "H-A3": "MEASURED_SOFTWARE", "H-B1": "SIMULATED", "H-B2": "SIMULATED", "H-B3": "SIMULATED", "H-D1": "MEASURED_SOFTWARE",
          "H-D2": "MEASURED_SOFTWARE", "H-E1": "SIMULATED", "H-E2": "ANALYTICAL", "H-F1": "ANALYTICAL", "H-F2": "SIMULATED"}
PKEY = {"H-A1": "v2.a.hA1.p_raw", "H-A2": "v2.a.hA2.p_raw", "H-A3": "v2.a.hA3.p_raw", "H-B1": "v2.b.hB1.p_raw", "H-B2": "v2.b.hB2.p_raw", "H-D1": "v2.d.hD1.p_raw", "H-D2": "v2.d.hD2.p_raw",
        "H-E1": "v2.e.hE1.p_raw", "H-F2": "v2.f.hF2.p_raw"}
SRC = "results/tables/v2_verdicts.csv"


def b2_lower_bound_excludes() -> tuple[bool, float]:
    """True if some variant has a harm above 2 points in a steady or single-car cell whose 95% interval lies entirely above 2 points (a stated 'counts against' condition)."""
    runs = pd.read_csv(C.TABLES / "v2_b_runs.csv")
    worst_lo = -1.0
    for cell in sorted(set(runs[runs.group.isin(["steady", "single"])].cell)):
        for v in VB.VARIANTS:
            for m, sign in (("reach10_critical", -1.0), ("mis_triage", 1.0)):
                g, dr, n = VB.gain_stats(runs, cell, f"M[{v}]", v, m)
                if np.isnan(g):
                    continue
                worst_lo = max(worst_lo, float(np.nanquantile(sign * dr, 0.025)))
    return worst_lo > 0.02, worst_lo


def main() -> None:
    p_raw = {h: float(R[k]) for h, k in PKEY.items()}
    adj = holm(p_raw)
    ent = Entries("v2.holm", SRC, "MEASURED_SOFTWARE")
    for h in p_raw:
        ent.add(f"{h}.p_raw", round(p_raw[h], 4), "probability", f"one-sided bootstrap p-value of {PKEY[h]}; floor 0.001 with 1,000 resamples", origin=ORIGIN[h])
        ent.add(f"{h}.p_holm", round(adj[h], 4), "probability", "Holm-adjusted over the nine tested hypotheses of the v2 preregistration", origin=ORIGIN[h])
    ent.add("family_size", len(p_raw), "hypotheses", "H-A1, H-A2, H-A3, H-B1, H-B2, H-D1, H-D2, H-E1, H-F2; H-B3, H-E2 and H-F1 have no p-value and are decided by their stated rule")
    sig = {h: adj[h] < 0.05 for h in adj}
    verdict: dict[str, tuple[str, str]] = {}

    def two(crit: bool, h: str, why_not: str) -> tuple[str, str]:
        if crit and sig[h]:
            return "SUPPORTED", "criterion met and the Holm-adjusted p-value is below 0.05"
        if crit:
            return "MIXED", "criterion met, but the Holm-adjusted p-value is not below 0.05"
        return "NOT SUPPORTED", why_not

    verdict["H-A1"] = two(R["v2.a.hA1.criterion_met"] == 1, "H-A1", "the interval includes zero, or the 5-point gain appears on fewer than two splits")
    narrow = R["v2.a.hA2.low_tercile.relwidth_iii_minus_i_hi"] < 0
    band = 0.88 <= R["v2.a.hA2.coverage_iii"] <= 0.92
    verdict["H-A2"] = two(R["v2.a.hA2.criterion_met"] == 1, "H-A2", "counts against: " + ("no narrowing in the lowest tercile" if not narrow else "") + ("; " if (not narrow and not band) else "") + ("coverage outside 0.88 to 0.92" if not band else ""))
    verdict["H-A3"] = two(R["v2.a.hA3.criterion_met"] == 1, "H-A3", "containment of the reference delta-V is below 0.90")
    verdict["H-B1"] = two(R["v2.b.hB1.criterion_met"] == 1, "H-B1", "no variant gains 3 points with an interval above zero in 6 of the 10 burst cells")
    excl, worst_lo = b2_lower_bound_excludes()
    ent.add("hB2.worst_harm_lower_bound", round(worst_lo, 5), "fraction", "largest lower 95% end of any harm in a steady or single-car cell")
    if R["v2.b.hB2.criterion_met"] == 1:
        verdict["H-B2"] = two(True, "H-B2", "")
    elif excl:
        verdict["H-B2"] = ("NOT SUPPORTED", "a variant harms by more than 2 points with the whole interval above 2 points")
    else:
        verdict["H-B2"] = ("MIXED", "the upper 95% bound of the harm exceeds 2 points for some variant and cell, but no interval lies entirely above 2 points")
    verdict["H-B3"] = ("SUPPORTED", "criterion met") if R["v2.b.hB3.criterion_met"] == 1 else ("NOT SUPPORTED", "not evaluable because H-B1 is not met" if R["v2.b.hB3.evaluable"] == 0 else "the token bucket gains less than 80% of the best variant")
    time_ok = R["v2.d.hD1.median_time_saved_ms"] >= 100 and R["v2.d.hD1.median_time_saved_ms_lo"] >= 100
    worse = R["v2.d.hD1.under_triage_D2_minus_analogue_lo"] > 0
    if time_ok and not worse:
        verdict["H-D1"] = two(True, "H-D1", "")
    else:
        verdict["H-D1"] = ("NOT SUPPORTED", ("the median time saved is below 100 ms" if not time_ok else "") + ("; " if (not time_ok and worse) else "") + ("the under-triage interval lies entirely above zero" if worse else ""))
    verdict["H-D2"] = two(R["v2.d.hD2.criterion_met"] == 1, "H-D2", "the over-triage is not below 10%")
    verdict["H-E1"] = two(R["v2.e.hE1.criterion_met"] == 1, "H-E1", "the gain is below 2 points or its interval includes zero")
    verdict["H-E2"] = ("SUPPORTED", "formula: both work factors above 2^32") if R["v2.e.hE2.criterion_met"] == 1 else ("NOT SUPPORTED", "a work factor is at or below 2^32")
    verdict["H-F1"] = ("SUPPORTED", "formula: optimal Critical hold is zero in every case") if R["v2.f.hF1.criterion_met"] == 1 else ("NOT SUPPORTED", f"{R['v2.f.hF1.n_positive']} ratio and p combinations have a positive optimal Critical hold")
    f2_loss = R["v2.f.hF2.change_critical_reach10_hi"] < 0
    verdict["H-F2"] = two(R["v2.f.hF2.criterion_met"] == 1, "H-F2", "the reduction is below 20% or the critical reach falls significantly" if (f2_loss or R["v2.f.hF2.relative_reduction_false_severe_reaching_base"] < 0.2) else "criterion not met")
    rows = []
    for h in ORIGIN:
        ent.add(f"verdict.{h}", verdict[h][0], "verdict", verdict[h][1], origin=ORIGIN[h])
        rows.append(dict(hypothesis=h, verdict=verdict[h][0], reason=verdict[h][1], p_raw=p_raw.get(h, np.nan), p_holm=adj.get(h, np.nan), origin=ORIGIN[h]))
    pd.DataFrame(rows).to_csv(C.TABLES / "v2_verdicts.csv", index=False)
    ent.flush()
    print(pd.DataFrame(rows).round(4).to_string())


if __name__ == "__main__":
    main()
