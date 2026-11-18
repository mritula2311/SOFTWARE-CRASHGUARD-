"""T14: statistics audit. For every family of comparisons in the paper: the test, the interval, the number of comparisons, and the correction (or an explicit exploratory flag); one table of every post-hoc choice.

The three preregistered hypotheses (H-a, H-b, H-c) are corrected for multiplicity: Holm correction of grouped-bootstrap p-values (two-sided, share of resamples on the other side of zero, times two) and, for
comparison, Bonferroni-widened intervals (95% / 3 = 98.3% two-sided). All other families are descriptive or EXPLORATORY: their 95% intervals are not corrected and a result that clears one of them is not
a confirmed finding. MEASURED_SOFTWARE for the correction; the audit tables are documentation.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import ua_core as U

DOC = Path("docs/03_results/STATS_AUDIT.md")
SRC = "results/tables/stats_audit.csv"

FAMILIES = [
    # (id, what, prefix regex for the interval keys, test, interval, status)
    ("F1", "Detector headline metrics (system recall, AP, false-alarm rate)", r"^detector\.head", "bootstrap of test events (1,000 resamples); mean over 5 seeds for the 5-seed rows", "95% percentile", "descriptive"),
    ("F2", "N8 supplied against de-duplicated and window-level sets", r"^dupscan\.", "paired bootstrap over the supplied test events (same drawn rows for both sets)", "95% percentile", "descriptive (sensitivity)"),
    ("F3", "N14 clipping methods: paired differences between methods", r"^n14x\..*\.paired\.", "paired grouped (make and model) bootstrap, 1,000 resamples", "95% percentile", "decision rule fixed in advance for 'M+ against spline and plain' per range and split; no multiplicity correction; fill + ridge was named primary after earlier results were seen"),
    ("F4", "N16 and N22 scheduler against the table (X6 and the burst sweep)", r"^(s5|x6)\.", "paired bootstrap over scenario seeds", "95% percentile", "EXPLORATORY: the burst scenario was added after the steady-state null result"),
    ("F5", "N19 arms (F, A, E, E')", r"^s6\.", "paired bootstrap over test events", "95% percentile", "descriptive; the early-exit rule was chosen on validation"),
    ("F6", "N20 conformal false-alarm rate against alpha", r"^(x4|n20c)\.", "bootstrap of the mean over (seed, draw) pairs plus one binomial standard error of the test set", "95% percentile", "decision rule fixed in advance; the 3 variants of T7 are EXPLORATORY"),
    ("F7", "N24 conformal delta-V intervals", r"^n24\.", "grouped bootstrap", "95% percentile", "decision rule fixed in advance (two conditions); the 6 range and level combinations are not corrected"),
    ("F8", "N25 prevalence-adaptive rules against the existing rule", r"^s10\.", "percentile interval over 200 resampled populations", "95% percentile", "decision rule fixed in advance; 8 rules x 4 prevalences are not corrected"),
    ("F9", "UA-SCT class intervals (coverage, width, mis-triage)", r"^ua\.r", "grouped bootstrap (make and model groups, 1,000 resamples)", "95% percentile", "preregistered: H-a, H-b, H-c (corrected below); other rows descriptive"),
    ("F10", "UA-SCT policy differences over the held-out cells", r"^s11\.diff", "mean over cells of paired seed-mean differences; seeds resampled inside every cell", "95% percentile", "preregistered cells; 6 comparisons x 3 ranges x 2 cell types x 10 metrics reported, not corrected; read the preregistered metrics only"),
    ("F11", "T1 equal-escalation comparison", r"^t1\.", "pool-level grouped bootstrap; cell-level seed bootstrap", "95% percentile", "preregistered in Addendum 1 (decision rule)"),
    ("F12", "T2 Pareto areas", r"^t2\.", "grouped bootstrap of the area", "95% percentile", "preregistered in Addendum 1; matched-escalation rows EXPLORATORY"),
    ("F13", "T3 expected cost and break-even ratio", r"^t3\.", "grouped bootstrap", "95% percentile", "preregistered in Addendum 1; the delivery term is EXPLORATORY"),
    ("F14", "T4 clarifications", r"^t4\.", "grouped bootstrap; analytical expected values", "95% percentile", "descriptive"),
    ("F15", "T5 near-duplicate sensitivity", r"^t5\.", "bootstrap over test events, paired between sets", "95% percentile", "EXPLORATORY (sensitivity analysis)"),
    ("F16", "T6 threshold sensitivity (17 settings)", r"^t6\.", "grouped bootstrap", "95% percentile", "preregistered in Addendum 1; 17 settings reported, H-a and H-c counted per setting, not corrected"),
    ("F17", "T7 conformal variants", r"^t7\.", "grouped bootstrap (severity) and bootstrap over test events (false alarms)", "95% percentile", "EXPLORATORY"),
    ("F18", "T8 simulator sweep", r"^t8\.", "paired bootstrap over seeds per cell; cells counted", "95% percentile", "preregistered cells; counts of cells reported"),
    ("F19", "T9 ablations", r"^t9\.", "paired bootstrap over seeds per cell", "95% percentile", "EXPLORATORY"),
    ("F20", "S11 exploratory blocks (ablations, false alarms, single car)", r"^s11\.exploratory", "bootstrap over seeds", "95% percentile", "EXPLORATORY"),
    ("F21", "T13a held-out NHTSA modes: N13 grid and N14 methods", r"^t13\.heldout\.", "grouped (make and model) bootstrap, 1,000 resamples", "95% percentile", "decision rules written before the run (docs/07_log/DECISIONS.md); 25 grid cells and 12 paired comparisons are reported, not corrected"),
    ("F22", "T13c near-duplicate NHTSA pulses", r"^t13\.neardup\.", "counts; grouped bootstrap for the headline comparison without the flagged tests", "95% percentile", "EXPLORATORY"),
    ("F23", "Sensor selection (S1 to S3)", r"^sel\.cfg\.", "grouped (make and model) bootstrap", "95% percentile", "decision rule S3 written before the run; 99 configurations are reported, not corrected"),
    ("F24", "VZCrash leakage sensitivity (V4)", r"^vz\.v4\.", "paired bootstrap over the supplied test events", "95% percentile", "descriptive; the independent audit V1 has no interval (counts)"),
    ("F25", "Blocks 4 and 4b (X1 to X8)", r"^x\.x[1-8]\.", "grouped bootstrap (NHTSA) or paired bootstrap over test events (VZCrash)", "95% percentile", "preregistered in docs/02_preregistration/PREREGISTRATION_V3.md; Holm correction over the seven hypotheses (x.holm.*); every other row EXPLORATORY"),
]

POST_HOC = [
    ("X7 wide clipped-sample mask", "after the preregistered X7 rule gave a poor initial result", "docs/07_log/DECISIONS.md", "EXPLORATORY; never counts toward H-X7"),
    ("H-X8 read as holding at both false-alarm targets", "the preregistration does not say which target", "docs/07_log/DECISIONS.md", "the 1% and 5% results are both reported"),
    ("Two repeated records found among the 176 NHTSA tests", "found by T13c after the tagged runs", "docs/07_log/DECISIONS.md", "tagged results not changed; T13c reports the comparison without them"),
    ("X2 crash mask corrected (label 0 is crash)", "after the initial run printed an impossible crash pass share", "docs/07_log/DECISIONS.md", "keys rewritten by the re-run; no result of the faulty run was used"),
    ("Fill + ridge named the primary N14 variant", "after the earlier N14 results were seen", "docs/02_preregistration/ALGORITHMS.md, docs/07_log/DECISIONS.md", "stated next to every N14 headline number"),
    ("Burst scenario added to X6", "after the N16 steady-state null result", "docs/07_log/DECISIONS.md (S5)", "all burst results labelled exploratory; tuning and held-out bursts separated"),
    ("N14 saturation level made a tuned parameter; NHTSA split changed from test-number to vehicle group", "after development and first results", "docs/07_log/DECISIONS.md, compliance W5", "the grouped held-out set is not blind"),
    ("N15 decision rule tightened to the seed-averaged difference", "after the seed-42 result was printed", "docs/07_log/DECISIONS.md, compliance W5", "reported as no improvement found"),
    ("Window-level near-duplicate scan added", "after the exact-hash audit; thresholds fixed in advance", "docs/07_log/DECISIONS.md (S2, T5)", "primary test set not changed; sensitivity analysis"),
    ("M+ capped variant", "after the N14 tail result", "docs/02_preregistration/EXPERIMENTS_EXTRA.md S4", "EXPLORATORY; one variant only"),
    ("S9 class rule (report the class below plus a flag)", "defined before the S9 run; the UA-SCT idea was then chosen after S9 and S5 were seen", "docs/02_preregistration/PREREGISTRATION.md section 0", "disclosed before the UA-SCT runs"),
    ("UA-SCT preregistration written after S5, S9 and the SCT idea; addendum 1 written after the main UA-SCT results", "after results of the main study were seen (T1 to T4, T6, T8 definitions)", "docs/02_preregistration/PREREGISTRATION.md section 0 and Addendum 1", "the addendum lists what was seen"),
    ("Spaced-retry baseline P1b (S13)", "after the S5 tuning showed that spacing is the active ingredient", "docs/02_preregistration/EXPERIMENTS_EXTRA.md S13", "decision rule fixed before the run"),
    ("Bound sets of the protocol check split (REBB, REBC) and the in-flight copy semantics changed", "after the first reboot bound set was truncated and after two modelling errors were found", "docs/07_log/DECISIONS.md (Part C)", "reported as limits of the model"),
    ("Key-prefix collision repaired", "after check_results reported errors", "docs/07_log/DECISIONS.md", "no number changed"),
    ("T5, T7, T9, T10, T11, T12, T13 are exploratory by design", "written in the closing-block prompt", "this table", "labelled EXPLORATORY in results.json"),
]


def families_table(res: dict) -> pd.DataFrame:
    rows = []
    for fid, what, pat, test, interval, status in FAMILIES:
        keys = [k for k in res if re.search(pat, k)]
        n_int = sum(1 for k in keys if k.endswith("_lo"))
        rows.append(dict(id=fid, comparisons=what, test=test, interval=interval, n_intervals_reported=n_int, n_keys=len(keys), correction_or_flag=status))
    return pd.DataFrame(rows)


def holm(p: dict) -> dict:
    order = sorted(p, key=p.get)
    m = len(p)
    out, prev = {}, 0.0
    for i, k in enumerate(order):
        adj = min(1.0, (m - i) * p[k])
        prev = max(prev, adj)
        out[k] = prev
    return out


def main() -> None:
    from crashguard.results import record_many

    res = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
    core = U.build()
    refc = U.ref_classes(core)
    grp = core.grp
    nm = lambda z: float(np.nanmean(z))  # noqa: E731
    iv16 = U.interval_classes(core, 16.0, 0.10, "cc")
    iv64 = U.interval_classes(core, 64.0, 0.10, "cc")
    mp, ep = U.mis_esc(iv16["c_hat"], refc)
    mu, eu = U.mis_esc(iv16["up"], refc)
    mp64, _ = U.mis_esc(iv64["c_hat"], refc)
    mu64, _ = U.mis_esc(iv64["up"], refc)
    w16 = np.where(iv16["c_hat"] >= 0, (iv16["hi"] - iv16["lo"] + 1).astype(float), np.nan)
    w64 = np.where(iv64["c_hat"] >= 0, (iv64["hi"] - iv64["lo"] + 1).astype(float), np.nan)

    def paired(a, b, level=0.95):
        return B.paired_diff_grouped(a.T, b.T, grp, nm, level=level)

    def pval(a, b):
        mem = B.group_members(grp)
        d = np.array([nm(b.T[i]) - nm(a.T[i]) for i in B._gidx(mem, B.N_BOOT, B.SEED)])
        return float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean()))), d

    pa, da = pval(mp, mu)  # H-a: upper minus point mis-triage (expected negative)
    pb, db = pval(ep, eu)  # H-b: upper minus point escalation (expected positive)
    r16, r64 = mp - mu, mp64 - mu64
    pc1, dc1 = pval(r64, r16)  # reduction at 16 minus at 64 (expected positive)
    pc2, dc2 = pval(w16, w64)  # width at 64 minus at 16 (expected negative)
    pc = max(pc1, pc2)  # H-c needs both parts
    p = {"H-a": pa, "H-b": pb, "H-c": pc}
    adj = holm(p)
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"t14.{name}", value=value, unit=unit, origin="MEASURED_SOFTWARE", source_file=SRC, notes=notes))

    wide = 1 - 0.05 / 3
    for h, (a, b) in (("H-a", (mp, mu)), ("H-b", (ep, eu))):
        d = paired(a, b, wide)
        add(f"{h}.p_raw", round(p[h], 4), "probability", "two-sided grouped-bootstrap p-value (twice the share of resamples on the other side of zero; floor 0.002 with 1,000 resamples)")
        add(f"{h}.p_holm", round(adj[h], 4), "probability", "Holm-adjusted over H-a, H-b, H-c")
        add(f"{h}.bonferroni_interval_lo", round(d[1], 4), "fraction", "98.3% interval (Bonferroni for three hypotheses), grouped bootstrap")
        add(f"{h}.bonferroni_interval_hi", round(d[2], 4), "fraction", "98.3% interval")
        add(f"{h}.survives_correction", int(adj[h] < 0.05), "flag", "Holm-adjusted p below 0.05")
    d1 = paired(r64, r16, wide)
    d2 = paired(w16, w64, wide)
    add("H-c.p_raw", round(p["H-c"], 4), "probability", "the larger p-value of its two parts (reduction larger at +-16 g, intervals narrower at +-64 g)")
    add("H-c.p_holm", round(adj["H-c"], 4), "probability", "Holm-adjusted")
    add("H-c.bonferroni_reduction_lo", round(d1[1], 4), "fraction", "98.3% interval of (reduction at +-16 g minus at +-64 g)")
    add("H-c.bonferroni_width_hi", round(d2[2], 4), "classes", "upper end of the 98.3% interval of (width at +-64 g minus at +-16 g)")
    add("H-c.survives_correction", int(adj["H-c"] < 0.05), "flag", "Holm-adjusted p below 0.05")
    fam = families_table(res)
    fam.to_csv(C.TABLES / "stats_audit.csv", index=False)
    ph = pd.DataFrame(POST_HOC, columns=["post-hoc choice", "when", "where logged", "how it is handled"])
    ph.to_csv(C.TABLES / "stats_audit_posthoc.csv", index=False)
    n_total = int(fam.n_intervals_reported.sum())
    add("n_intervals_reported_total", n_total, "intervals", "number of key_lo entries in the families of this audit")
    md = ["# Statistics audit (T14, 2026-11-11)", "",
          "Generated by `python -m crashguard.stats_audit` from `results/results.json`. For every family of comparisons: the test, the interval, the number of intervals reported and the correction or the flag. "
          "Only the three preregistered hypotheses are corrected; every other interval is a 95% interval without multiplicity correction and an exploratory or descriptive result must not be read as confirmed.", "",
          "## 1. Preregistered hypotheses with multiplicity correction", "",
          "| Hypothesis | Raw p (grouped bootstrap) | Holm-adjusted p | Survives (adjusted p < 0.05) |", "|---|---|---|---|"]
    for h in ("H-a", "H-b", "H-c"):
        md.append(f"| {h} | {p[h]:.4f} | {adj[h]:.4f} | {'yes' if adj[h] < 0.05 else 'no'} |")
    md += ["", "The p-values are bootstrap p-values (1,000 resamples), so the smallest value is about 0.002; they are a convenience for the correction, not exact tests.", "",
           "## 2. Families of comparisons", "", "| Id | Comparisons | Test | Interval | Intervals reported | Correction or flag |", "|---|---|---|---|---|---|"]
    md += [f"| {r.id} | {r.comparisons} | {r.test} | {r.interval} | {r.n_intervals_reported} | {r.correction_or_flag} |" for r in fam.itertuples()]
    md += ["", f"Total intervals in these families: {n_total}. At a 95% level about one in twenty intervals that include a true zero would exclude it by chance; this is why uncorrected families are flagged.", "",
           "## 3. Post-hoc choices", "", "| Choice | When | Where logged | Handling |", "|---|---|---|---|"]
    md += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in POST_HOC]
    DOC.write_text("\n".join(md) + "\n", encoding="utf-8")
    record_many(ent, purge_prefixes=("t14.",))
    print({h: (round(p[h], 4), round(adj[h], 4)) for h in p})


if __name__ == "__main__":
    main()
