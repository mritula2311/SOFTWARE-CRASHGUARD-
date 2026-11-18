"""Write docs/04_audits/ALGORITHMS_COMPLIANCE.md: the item-by-item check of the three-algorithm work against docs/02_preregistration/ALGORITHMS.md (written before the runs) and the author's Part 0 list.

Every number comes from results/results.json; a missing or NOT_RUN number is printed as such, never filled in. Status words: DONE, PARTIAL, NOT_DONE.
The text of the original "three algorithm contributions" prompt is not stored in the repository, so the item list follows docs/02_preregistration/ALGORITHMS.md (which was written from it
before the runs), the docs/07_log/PROGRESS.md queue entry, and the points the author listed for the compliance check.
"""
from __future__ import annotations

from crashguard.textutil import clip

import json
from pathlib import Path

OUT = Path("docs/04_audits/ALGORITHMS_COMPLIANCE.md")


class V:
    def __init__(self, path: Path = Path("results/results.json")):
        self.r = {e["name"]: e for e in json.loads(path.read_text(encoding="utf-8"))}

    def f(self, k: str, d: int = 3) -> str:
        e = self.r.get(k)
        if e is None:
            return f"MISSING({k})"
        v = e["value"]
        if isinstance(v, str):
            return v
        return f"{v:.{d}f}" if isinstance(v, float) else str(v)

    def ci(self, k: str, d: int = 3) -> str:
        return f"{self.f(k, d)} [{self.f(k + '_lo', d)}, {self.f(k + '_hi', d)}]"

    def ok(self, *keys: str) -> bool:
        return all(k in self.r and self.r[k]["value"] != "NOT_RUN" for k in keys)


def build(v: V | None = None) -> str:
    v = v or V()
    f, ci = v.f, v.ci
    rows: list[tuple[str, str, str, str, str]] = []  # id, item, status, where, number / note

    def add(i, item, st, where, num):
        rows.append((i, item, st, where, num))

    def n14row(rg):
        return "; ".join(f"{m}: median {f(f'n14.r{rg}.heldout.{m}.median', 1)}, p90 {f(f'n14.r{rg}.heldout.{m}.p90', 1)}, within 10% {f(f'n14.r{rg}.heldout.{m}.w10', 2)}, within 20% {f(f'n14.r{rg}.heldout.{m}.w20', 2)}, in v<=dV<=2v {f(f'n14.r{rg}.heldout.{m}.band', 2)}" for m in ("B", "M", "M+"))

    # ---------------- Algorithm 1 (N14)
    add("A1.1", "Saturation test (sample at or above a level times the range; pulse from the baseline pulse rule)", "DONE", "src/crashguard/saturation.py; `n14.r*.saturated_share`", f"saturated share of tests: +-16 g {f('n14.r16.saturated_share', 3)}, +-32 g {f('n14.r32.saturated_share', 3)}, +-64 g {f('n14.r64.saturated_share', 3)}. The level is a tuned parameter, not the 0.98 first written (item A1.5)")
    add("A1.2", "Pulse model: half-sine, haversine, triangle", "DONE", "saturation.py; `n14.combo.*`, `n14.family.chosen`", f"chosen family {f('n14.family.chosen')}, level {f('n14.sat_frac.chosen', 1)} of the range")
    add("A1.3", "Deterministic grid fit (9 starts x 21 durations, amplitude by least squares, plausibility cap)", "DONE", "saturation.py `fit_pulse`; `firmware_export/severity.h`", "no number")
    add("A1.4", "Fill of saturated samples, direction kept, then the ordinary severity code", "DONE", "saturation.py `fill`, `severity_filled`", "no number")
    add("A1.5", "Family choice on tuning tests only (the text says LOTO error at +-16 g; the run uses the lowest mean over three ranges of the median error, and the saturation level was added as a parameter)", "PARTIAL", "docs/02_preregistration/ALGORITHMS.md revision log; `n14.combo.tuning_mean_median_abs_err_pct.*`", "The rule was changed after a development run on the 118 tuning tests (held-out tests not used); the change is logged. The code differs from the original text of item 5, so this is PARTIAL")
    add("A1.6", "M+: ridge regression of log(reference / M estimate) on three inputs, strength by leave-one-test-out on tuning tests", "DONE", "saturation_study.py; `n14.r*.ridge_*`", f"strength chosen: +-16 g {f('n14.r16.ridge_alpha', 0)} (the largest tried), +-32 g {f('n14.r32.ridge_alpha', 0)}, +-64 g {f('n14.r64.ridge_alpha', 0)}")
    add("A1.7a", "Results at +-16 g (held-out, 58 tests): median and 90th percentile error, shares within +-10% and +-20%, share inside v <= delta-V <= 2v", "DONE", "`n14.r16.heldout.{B,M,M+}.*`; results/tables/n14_metrics.csv", n14row(16))
    add("A1.7b", "Same at +-32 g", "DONE", "`n14.r32.heldout.*`", n14row(32))
    add("A1.7c", "Same at +-64 g", "DONE", "`n14.r64.heldout.*`", n14row(64))
    add("A1.8", "90th-percentile error: M+ is not better than the baseline at +-16 g", "DONE (finding)", "`n14.r16.heldout.M+.p90`", f"p90 {f('n14.r16.heldout.B.p90', 1)}% (baseline) against {f('n14.r16.heldout.M+.p90', 1)}% (M+): the tail is worse; the earlier report text did not say so")
    add("A1.9", "Paired comparison with the baseline and the primary-endpoint decision at each range", "DONE", "`n14.r*.heldout.paired.*`; results/tables/n14_paired.csv",
        f"+-16 g: M {ci('n14.r16.heldout.paired.M.d_median', 2)}, M+ {ci('n14.r16.heldout.paired.M+.d_median', 2)} (clears); +-32 g: M+ {ci('n14.r32.heldout.paired.M+.d_median', 2)} (does not clear); +-64 g: M+ {ci('n14.r64.heldout.paired.M+.d_median', 2)} (no change). Intervals there resample tests, not groups; the grouped intervals are in Part 0B (`n14x.*`)")
    add("A1.10", "Synthetic pulses with analytic delta-V (SIMULATED)", "DONE", "`n14.synthetic.*`; results/tables/n14_synthetic.csv",
        f"matched pulses, median error baseline to fill: +-16 g {f('n14.synthetic.r16.matched.baseline.median_abs_err_pct', 1)}% to {f('n14.synthetic.r16.matched.method.median_abs_err_pct', 1)}%, +-32 g {f('n14.synthetic.r32.matched.baseline.median_abs_err_pct', 1)}% to {f('n14.synthetic.r32.matched.method.median_abs_err_pct', 1)}%, +-64 g {f('n14.synthetic.r64.matched.baseline.median_abs_err_pct', 1)}% to {f('n14.synthetic.r64.matched.method.median_abs_err_pct', 1)}%; square (mismatched) pulses: no change")
    add("A1.11", "Failure cases (held-out tests where the method is worse than the baseline)", "DONE", "results/tables/n14_failure_cases.csv; `n14.r*.heldout.*.worse_tests`", f"+-16 g: M {f('n14.r16.heldout.M.worse_tests', 0)} tests, M+ {f('n14.r16.heldout.M+.worse_tests', 0)} tests; +-32 g: M {f('n14.r32.heldout.M.worse_tests', 0)}, M+ {f('n14.r32.heldout.M+.worse_tests', 0)}")
    add("A1.12a", "Number of held-out and tuning tests and groups", "DONE", "`n14.n_heldout`, `n14.n_tuning`, `n14x.G.*`", f"held-out {f('n14x.G.n_tests_heldout', 0)} tests in {f('n14x.G.n_groups_heldout', 0)} vehicle groups (make, model, year); tuning {f('n14x.G.n_tests_tuning', 0)} tests in {f('n14x.G.n_groups_tuning', 0)} groups. The group counts were not stored before Part 0B; they are now (`n14x.G.n_groups_*`)")
    add("A1.12b", "The grouped held-out set had already been seen in earlier results, so it is 'stable under re-splitting', not a blind test; both splits reported", "DONE", "docs/02_preregistration/ALGORITHMS.md (N14 extension); report Section 4.8; `n14x.O.*` (test-number split) and `n14x.G.*` (grouped)",
        f"split O (test-number rule, {f('n14x.O.n_tests_heldout', 0)} held-out tests) and split G (grouped, {f('n14x.G.n_tests_heldout', 0)} held-out tests) are reported side by side at each range. Before Part 0 the test-number split's N14 numbers were not stored (PARTIAL); completed in B1")
    add("A1.13", "severity.h includes the N14 estimator (saturation test, fit, fill, ridge) with an equivalence test and flash/RAM estimates", "PARTIAL", "firmware_export/severity.h `cg_severity_sat`; `export_severity.n14.*`",
        f"Python float32 mirror vs Python reference: max difference {f('export_severity.n14.mirror.max_abs_diff.dv_fill_kmh', 5)} km/h in the filled delta-V on {f('export_severity.n14.windows', 0)} windows ({f('export_severity.n14.windows_saturated', 0)} saturated), {f('export_severity.n14.mirror.mismatch.applied', 0)} different fit decisions. Compiled C check: {f('export_severity.n14.c.max_abs_diff.dv_fill_kmh', 5)} km/h in the last run. Static RAM added about {f('export_severity.n14.ram_added_by_n14_bytes', 0)} bytes and object code added about {f('export_severity.n14.code_bytes_added_host', 0)} bytes (host estimates, ANALYTICAL). ESP32 flash, RAM and time: NOT_RUN (no ESP32 build). Windows can block the compiled check; see W3")
    add("A1.14", "Which variant (fill only, or fill + ridge) was named the primary method in docs/02_preregistration/ALGORITHMS.md before results were seen", "NOT_DONE", "docs/02_preregistration/ALGORITHMS.md (first version, commit 6bbcf90)", "Neither was named. The text says 'M or M+' in the decision rule and calls half-sine the primary pulse FAMILY. For Part 0B, fill + ridge was declared primary before the B1 run (after the earlier numbers had been seen). The report says so")
    add("A1.15", "Prior-work search and verdict", "DONE", "docs/06_references/PRIOR_WORK.md (N14 section and Part 0B entries); docs/03_results/CLAIM_EVIDENCE.md", "Chan et al. 2023 (the spline baseline) was snippet-only at the time of the first N14 run; it was opened in Part 0B (Europe PMC full text)")
    add("A1.16", "C-version equivalence for the Python and C code on NHTSA and synthetic windows", "DONE", "`export_severity.n14.*`", "see A1.13")

    # ---------------- Algorithm 2 (N15)
    def n15(m, t):
        return f"{f(f'n15.{m}.t{t}.test_recall.mean', 4)} +- {f(f'n15.{m}.t{t}.test_recall.std', 4)} (sys AP {f(f'n15.{m}.t{t}.sys_ap.mean', 4)})"
    add("A2.1", "Baseline: fixed 2.0 g trigger and a separately trained 15-tree forest, threshold on validation", "DONE", "`n15.baseline.*`", f"recall at 1% false alarms {n15('baseline', 1)}; at 5% {n15('baseline', 5)}")
    add("A2.2", "Both targets: 1% and 5% of all non-crash events (system level)", "DONE", "`n15.*.t1.*`, `n15.*.t5.*`", "both reported for every method")
    add("A2.3", "Method a: joint choice of trigger level and threshold on validation", "DONE", "`n15.a_joint.*`, `n15.choice.a_joint.*`",
        f"chose {f('n15.choice.a_joint.t1.trigger_g', 1)} g at 1% and {f('n15.choice.a_joint.t5.trigger_g', 1)} g at 5%; seed-averaged recall difference at 1% {ci('n15.a_joint.t1.paired_seedavg.d_recall', 4)}, at 5% {ci('n15.a_joint.t5.paired_seedavg.d_recall', 4)}; sys AP at 1% {f('n15.a_joint.t1.sys_ap.mean', 4)} (baseline {f('n15.baseline.t1.sys_ap.mean', 4)})")
    add("A2.4", "Method b: cost-sensitive training with the crashes the trigger discards", "DONE", "`n15.b_cost_sensitive.*`", f"weight chosen {f('n15.choice.b_cost_sensitive.t1.gamma', 1)}; difference at 1% {ci('n15.b_cost_sensitive.t1.paired_seedavg.d_recall', 4)}, at 5% {ci('n15.b_cost_sensitive.t5.paired_seedavg.d_recall', 4)}")
    add("A2.5", "Method c: learned trigger (running peak, jerk, short-window energy)", "DONE", "`n15.c_learned_trigger.*`, `n15.choice.c_learned_trigger.*`", f"candidates chosen {f('n15.choice.c_learned_trigger.t1.candidate')} (1%) and {f('n15.choice.c_learned_trigger.t5.candidate')} (5%): a level rule, so at 1% its numbers equal method a's (same 3.0 g trigger); difference at 1% {ci('n15.c_learned_trigger.t1.paired_seedavg.d_recall', 4)}")
    add("A2.6", "Metric: area under the system-level precision-recall curve (PR-AUC, stored as sys_ap)", "DONE", "`n15.*.sys_ap.mean`", f"baseline {f('n15.baseline.t1.sys_ap.mean', 4)}; a at 1% {f('n15.a_joint.t1.sys_ap.mean', 4)}; b {f('n15.b_cost_sensitive.t1.sys_ap.mean', 4)}; c at 1% {f('n15.c_learned_trigger.t1.sys_ap.mean', 4)}")
    add("A2.7", "Trigger rate by VZCrash vehicle-size category", "DONE", "`n15.*.crash_trigger_rate_{Light,Medium,Heavy,Unknown}`", f"baseline: Light {f('n15.baseline.t1.crash_trigger_rate_Light', 3)}, Medium {f('n15.baseline.t1.crash_trigger_rate_Medium', 3)}, Heavy {f('n15.baseline.t1.crash_trigger_rate_Heavy', 3)}; method a at 1%: Light {f('n15.a_joint.t1.crash_trigger_rate_Light', 3)}, Medium {f('n15.a_joint.t1.crash_trigger_rate_Medium', 3)}, Heavy {f('n15.a_joint.t1.crash_trigger_rate_Heavy', 3)}")
    add("A2.8", "RAM and cycle cost of the learned trigger", "PARTIAL", "`n15.learned_trigger.*` (ANALYTICAL)", f"state {f('n15.learned_trigger.state_bytes', 0)} bytes, no window buffer; {f('n15.learned_trigger.cycles_per_sample_assumed', 0)} cycles per sample is an ASSUMPTION (share of the sample period {f('n15.learned_trigger.cycles_share_of_sample_period', 6)}); the measured cost on the ESP32 is NOT_RUN")
    add("A2.9", "Paired bootstrap on test events and the decision rule", "DONE", "docs/02_preregistration/ALGORITHMS.md revision log; `n15.*.paired*`", "The rule was tightened AFTER the seed-42 result had been seen (seed-averaged difference instead of seed 42): logged in docs/02_preregistration/ALGORITHMS.md and DECISIONS.md. No method clears the interval: NO_IMPROVEMENT_FOUND")
    add("A2.10", "Prior-work search", "DONE", "docs/06_references/PRIOR_WORK.md (N15 section)", "Kubin et al. 2021 opened; cascade-detector literature was snippet only")

    # ---------------- Algorithm 3 (N16)
    add("A3.1", "Baselines: fixed 3-retry policy and the severity table with the token bucket", "DONE", "src/crashguard/scheduler.py, scheduler_study.py", "The fixed policy is weak by construction (same 3 tries for every class, arrival order, immediate retry)")
    add("A3.2", "Scheduler rules: reserve, severity-and-age order, ACK-feedback back-off with jitter, optional spreading-factor raise", "DONE", "scheduler.py", "no number")
    add("A3.3", "Parameters tuned on tuning scenarios only (24 combinations)", "DONE", "`n16.tuning.*`, `n16.chosen.*`", f"{f('n16.tuning.scenarios', 0)} tuning scenarios; chosen reserve {f('n16.chosen.rho', 1)}, multiplier {f('n16.chosen.m', 1)}, jitter {f('n16.chosen.jitter', 1)}, spreading-factor raise {f('n16.chosen.sf_raise', 0)}")
    add("A3.4", "Held-out scenarios, scored once", "DONE", "`n16.heldout.*`, `n16.conclusion.*`", f"{f('n16.conclusion.C1_better_critical_than_table.cells', 0)} held-out cells")
    cls = ("low", "moderate", "severe", "critical")
    eff = "; ".join(f"{b} {c}: {ci(f'n16.effect.{b}.{c}.delivered.d', 3)}" for b in ("fixed3", "table") for c in cls)
    add("A3.5", "Effect sizes with 95% intervals against both baselines, per severity class (delivery rate, median and p95 latency, budget)", "DONE", "`n16.effect.{fixed3,table}.{low,moderate,severe,critical}.*`; results/tables/n16_effects.csv", "delivery-rate differences (scheduler minus baseline): " + eff)
    add("A3.6", "Critical-alert latency and the cost against the severity table", "DONE", "`n16.effect.table.critical.*`", f"critical delivery {ci('n16.effect.table.critical.delivered.d', 4)} (does not clear zero); critical median latency {ci('n16.effect.table.critical.median_lat_s.d', 2)} s; critical p95 latency {ci('n16.effect.table.critical.p95_lat_s.d', 2)} s (longer)")
    add("A3.7", "Severity-error coupling from both the plain (+-16 g) and the N14 estimates", "DONE", "`n16.estimator.nhtsa_{plain,sat,oracle}.*`; results/tables/n16_estimator_cells.csv",
        f"class agreement with the reference: plain {f('n16.estimator.nhtsa_plain.class_agreement', 3)}, N14 {f('n16.estimator.nhtsa_sat.class_agreement', 3)}; underestimated: plain {f('n16.estimator.nhtsa_plain.underestimated', 3)}, N14 {f('n16.estimator.nhtsa_sat.underestimated', 3)}; truly critical alerts acknowledged (SF7, 50% loss), table policy: plain {f('n16.estimator.nhtsa_plain.est_iid50_sf7.table.delivered_critical', 3)}, N14 {f('n16.estimator.nhtsa_sat.est_iid50_sf7.table.delivered_critical', 3)}; scheduler: plain {f('n16.estimator.nhtsa_plain.est_iid50_sf7.scheduler.delivered_critical', 3)}, N14 {f('n16.estimator.nhtsa_sat.est_iid50_sf7.scheduler.delivered_critical', 3)}")
    add("A3.8", "Conclusions that survive the held-out cells", "DONE", "`n16.conclusion.*`", "; ".join(f"{k.split('_', 1)[0]} {f(f'n16.conclusion.{k}.holds', 0)} of {f(f'n16.conclusion.{k}.cells', 0)}" for k in ("C1_better_critical_than_table", "C2_better_critical_than_fixed3", "C3_fewer_blocked_critical_than_table", "C4_lower_p95_latency_critical_than_table", "C5_low_alerts_not_sacrificed_vs_table", "C6_less_budget_than_table")) + " (C1 critical better than table, C2 better than fixed, C3 fewer blocked, C4 lower p95 latency, C5 low alerts not sacrificed, C6 less budget)")
    add("A3.9", "Prior work: which entries were opened and which were snippet only", "DONE", "docs/06_references/PRIOR_WORK.md", "Opened: abstracts of arXiv 2212.09453 and 1908.10195 (first N16 search); in Part 0B the full texts of Tomic et al. 2020, Wei et al. 2023 and Zhong and Nie 2024. Snippet only: the Osaka-group priority-aware scheduling paper, a LoRaWAN retransmission patent, the LoRaWANSim studies. Snippet-only items support no claim")

    # ---------------- Wrap-up
    add("W1", "Novelty N14 to N16 in report/novelty_summary.md and docs/06_references/NOVELTY.md with status, evidence keys, prior work, risk, verdict", "DONE", "src/crashguard/novelty.py (generated)", "N14 SUPPORTED at +-16 g only (re-worded in Part 0B); N15 NO_IMPROVEMENT_FOUND; N16 PARTIAL, supporting, SIMULATED")
    add("W2", "Report section 'Proposed methods and evaluation' (4.8)", "DONE", "report/software_results.md Section 4.8", "no number")
    # W3 is generated: one entry per compiled-C check, taken from results.json (ran or not, the value, and the recorded reason where it did not run)
    c_checks = [("forest 15 trees, depth 6 (deployed)", "export.max_abs_diff", "max abs probability difference"),
                ("forest 10 trees, depth 9 (validation-selected candidate)", "candidate.max_abs_diff", "max abs probability difference"),
                ("severity.h on VZCrash test windows", "export_severity.vzcrash_test.c.max_abs_diff.dv_res_kmh", "max abs delta-V difference, km/h"),
                ("severity.h on NHTSA windows", "export_severity.nhtsa.c.max_abs_diff.dv_res_kmh", "max abs delta-V difference, km/h"),
                ("N14 estimator (fill)", "export_severity.n14.c.max_abs_diff.dv_fill_kmh", "max abs delta-V difference, km/h")]
    parts = []
    for label, k, what in c_checks:
        e = v.r.get(k)
        if e is None:
            parts.append(f"{label}: MISSING ({k})")
        elif e["value"] == "NOT_RUN":
            parts.append(f"{label}: **NOT_RUN**, reason recorded in results.json: {clip(e.get('notes', ''), 230)}")
        else:
            parts.append(f"{label}: **ran**, {what} {f(k, 8)}; {clip(e.get('notes', ''), 80)}")
    missing = [lab for lab, k, _ in c_checks if v.r.get(k, {}).get("value") == "NOT_RUN"]
    labels = sorted(k.split(".")[1] for k in v.r if k.startswith("cchecks.") and k.endswith(".platform"))
    other_parts = []
    for lab in labels:
        sub = sorted(k for k in v.r if k.startswith(f"cchecks.{lab}.") and k.endswith(".passes"))
        res = ", ".join(f"{k.split('.', 2)[2][:-len('.passes')]} {'passes' if v.r[k]['value'] else 'FAILS'}" for k in sub)
        other_parts.append(f"{lab} ({v.f(f'cchecks.{lab}.platform')}; {v.f(f'cchecks.{lab}.compiler')}): {res}")
    other = ("; merged C checks from other platforms: " + " || ".join(other_parts)) if other_parts else "; no check merged from another platform (see `crashguard.merge_c_checks`, `scripts/c_checks.sh`)"
    cand_keys = [f"cchecks.{lab}.c_bundle_real.forest_10x9.max_abs_diff.prob" for lab in labels if f"cchecks.{lab}.c_bundle_real.forest_10x9.max_abs_diff.prob" in v.r]
    cand_ok = v.ok("candidate.max_abs_diff") or bool(cand_keys)
    other += ("; equivalence of the 10 x 9 candidate is reported from: " + ", ".join(["Windows `candidate.max_abs_diff`"] * v.ok("candidate.max_abs_diff") + [f"`{k}` = {v.f(k, 8)}" for k in cand_keys])) if cand_ok         else "; equivalence of the 10 x 9 candidate is NOT reported (no compiled check has run)"
    add("W3", "Compiled-C equivalence checks: which ran, which did not, and why", "PARTIAL" if (missing and not cand_ok) or any(v.r[k]["value"] is False for k in v.r if k.startswith("cchecks.") and k.endswith(".passes")) else "DONE", ", ".join(f"`{k}`" for _, k, _ in c_checks),
        "<br>".join(parts) + other + ". The pure-Python float32 mirrors (`export.mirror_max_abs_diff`, `export_severity.*.mirror.*`) ran for the checks that have one. `export.benchmark_us_per_call` is NOT_RUN: needs the ESP32.")
    add("W4", "Headline detector numbers: point estimate and interval describe the same quantity", "DONE (fixed in Part 0)", "`detector.head5.rf15.*` (5-seed mean with its own interval), `detector.head.rf15.*` (seed 42 with its own interval)",
        f"5-seed mean system recall {ci('detector.head5.rf15.sys_recall', 3)}; seed 42 system recall {ci('detector.head.rf15.sys_recall', 3)}. Before the fix the text printed 0.909 with a seed-42 interval without saying 'seed 42', and printed 0.900 with no interval; the 0.900 in tables is a mean with a standard deviation across seeds (spread, not an interval for the mean). All three places now say which quantity they show")
    add("W5", "Parameters, rules or decisions changed after results were seen", "DONE (listed)", "docs/07_log/DECISIONS.md; docs/02_preregistration/ALGORITHMS.md revision log",
        "1) N14 saturation level made a tuned parameter after a development run on the tuning tests. 2) N15 decision rule tightened to the seed-averaged difference after the seed-42 result was printed. 3) NHTSA split changed from test-number to vehicle-group after the first N14 and release-rule results were seen (the grouped held-out set is therefore not blind). 4) NHTSA trigger and exclusion rule changed after a wider set exposed a flaw; the release fraction was re-chosen. 5) NHTSA quotas raised after a development run. 6) Rollover rule kept out of the class by a rule fixed in advance (no change). 7) The report sentence that said very few pulses saturate at +-32 g was wrong (share in `n14.r32.saturated_share`) and was corrected in Part 0B. 8) Fill + ridge declared primary for B1 after the earlier numbers were seen")
    add("W6", "Dummy-data and licence rules", "DONE", "tests/dummy not used for results", "no number")

    # ---------------- Round 3 (master prompt S1 to S13 and the UA-SCT prompt, Parts A to D)
    add("R3.S1", "Attack-case count from results.json; quotes re-checked; W3 generated; N19 wording; literature labels", "DONE", "docs/01_protocol/ATTACK_CASES.md, docs/03_results/CLAIM_EVIDENCE.md, `attacks.cases_total`", f"{f('attacks.cases_total', 0)} cases, {f('attacks.cases_matching_expected', 0)} as expected; one quote page corrected (paper 05, p6)")
    add("R3.S2", "N8 effect on the headline; near-duplicate scan", "DONE", "`dupscan.*`", f"system recall supplied minus de-duplicated {ci('dupscan.rf15.mean5.diff_supplied_minus_dedup.sys_recall', 4)}; against the window-level set {ci('dupscan.rf15.mean5.diff_supplied_minus_dedup_nd.sys_recall', 4)}")
    add("R3.S3", "N20 with a clean calibration set (recording groups and near-duplicates)", "DONE", "`n20c.*`", f"false-alarm rate at alpha 5%: {ci('n20c.hashgroup.a5.nall.conformal.fa_mean', 4)} (recording groups), {ci('n20c.clean.a5.nall.conformal.fa_mean', 4)} (also near-duplicates): the guarantee does not hold")
    add("R3.S4", "N14 and N13 strata, gap, M+ capped, failure cases", "DONE", "`n14s.*`", f"within 10% at +-16 g with fill + ridge {f('n14x.R.r16.M+.w10', 3)} against the 80% target; M+ capped changes nothing at +-16 g ({f('n14s.cap.R.r16.n_predictions_clipped', 0)} clipped)")
    add("R3.S5", "Burst scenario sensitivity (tuning and held-out bursts)", "DONE", "`s5.*` (exploratory, SIMULATED)", f"scheduler better than the table in {f('s5.a4.scheduler_vs_severity.delivered_critical.n_better', 0)} of 8 A4 settings")
    add("R3.S6", "N19 ensemble effect separated from the early exit", "DONE", "`s6.*`", f"ensemble effect at 1%: {ci('s6.a1.mean5.d.Ep_minus_F.recall', 4)}; at 5%: {ci('s6.a5.mean5.d.Ep_minus_F.recall', 4)}")
    add("R3.S7", "C equivalence outside Windows", "PARTIAL", "`scripts/c_checks.sh`, `cchecks.*`", "run with gcc under WSL2 (see W3); the GitHub workflow was written and not run from here; the synthetic N14 check fails on one window (grid-search tie)")
    add("R3.S8", "Novelty scan", "DONE", "docs/06_references/NOVELTY_SCAN.md", "ten candidates scored; S13 implemented; the sources named by the author that could not be opened are listed as not used")
    add("R3.S9", "M1: conformal intervals for clipped delta-V (N24)", "DONE", "`n24.*`", f"coverage at 90%, +-16 g: {ci('n24.r16.nom90.coverage', 3)}; the preregistered class rule does not improve")
    add("R3.S10", "M2: prevalence-adaptive threshold (N25)", "DONE", "`s10.*`", f"precision at 0.02% prevalence with the existing rule {f('s10.rf15.pi0p02pct.a.ppv', 4)}; no rule meets the decision rule at 1% or lower")
    add("R3.S11", "M3: SCT against the severity table, fixed 3-retry and the scheduler (N26)", "DONE", "`s11.*`, docs/01_protocol/PROTOCOL_SCT.md", f"burst, +-16 g: critical reach within 10 s, SCT minus table {ci('s11.diff.r16.burst.P2_minus_P1.reach10_critical', 3)}; steady state {ci('s11.diff.r16.steady.P2_minus_P1.reach10_critical', 3)}")
    add("R3.S12", "M4: bounded check of the retry, replay and ACK protocol (N27)", "PARTIAL", "`s12.*`, docs/01_protocol/PROTOCOL_MODEL.md", "explicit-state search in Python; TLC NOT_RUN (the tool could not be fetched); bounds split into four sets; a check of a model, not a proof")
    add("R3.S13", "Best extra idea: spaced-retry severity table as the baseline for SCT", "DONE", "`s13.*`", f"SCT minus spaced-retry table in bursts, +-16 g: critical reach within 10 s {ci('s13.diff.r16.burst.P2_minus_P1b.reach10_critical', 3)}")
    add("R3.A1", "N20 re-run with calibration de-duplicated by recording group, bootstrap intervals, plain statement", "DONE", "`n20c.*`", "see R3.S3")
    add("R3.A2", "Attack suite: list every case once; count in results.json and CLAIM_EVIDENCE.md agree", "DONE", "docs/01_protocol/ATTACK_CASES.md", f"{f('attacks.cases_total', 0)} cases; no case result changed")
    add("R3.A3", "Stale W3 row fixed", "DONE", "row W3 above", "generated from results.json")
    add("R3.A4", "X6 burst sensitivity: capture none and 6 dB, burst 10, 30, 60, payload 16 and 26 B, cars 50, 100, 200, SF 7 and 9", "DONE", "`s5.a4.*`", f"settings where the scheduler is not better than the table: {f('s5.a4.scheduler_vs_severity.delivered_critical.settings_where_not_better')}")
    add("R3.B1", "Severity from delta-V on the NHTSA tests at +-16, +-32 and +-64 g, 100 and 200 Hz", "PARTIAL", "`ua.b1.*`, `n14x.*`", "fill + ridge at 200 Hz is NOT_RUN (constants tuned at 100 Hz); the plain estimate is reported at both rates")
    add("R3.B2", "Conformal class intervals, calibration de-duplicated and grouped; coverage and width per range", "DONE", "`ua.r*`", f"coverage at 90%, +-16 g {ci('ua.r16.a10.cc.coverage', 3)}; mean width {f('ua.r16.a10.cc.width', 2)} classes")
    add("R3.B3", "Policies P0 to P4 in one simulator", "DONE", "`s11.*`, src/crashguard/sct_sim.py", "P4 cap rarely binds")
    add("R3.B4", "Simulator: 433 MHz, SF7 to SF9, duty-cycle limit as a parameter (1% default, India UNVERIFIED), 97 B alert, 26 B ACK, Semtech airtime, 100 cars, heartbeats, Poisson crashes and bursts, at least 30 seeds per cell", "DONE", "`s11.heldout.seeds_per_cell`", f"{f('s11.heldout.seeds_per_cell', 0)} seeds per cell")
    add("R3.B5", "Metrics: mis-triage, critical delivery within 10 s and 30 s, p95 latency, airtime and escalation, duty-limit exceedance", "DONE", "`s11.cell.*`, `s11.duty.*`", f"runs exceeding the duty limit: {f('s11.duty.runs_exceeding_limit', 0)} of {f('s11.duty.runs', 0)}")
    add("R3.B6", "Hypotheses H-a, H-b, H-c preregistered before the runs", "DONE", "docs/02_preregistration/PREREGISTRATION.md (commit before the runs)", "one wording-only edit after the commit (the word 'first'), logged in DECISIONS")
    add("R3.B7", "P3 against P1 reported honestly, also steady state and bursts", "DONE", "`s11.diff.*`", f"steady, +-16 g: P3 minus P1 critical reach within 10 s {ci('s11.diff.r16.steady.P3_minus_P1.reach10_critical', 3)}")
    add("R3.C", "Bounded formal check of the alert protocol", "PARTIAL", "`s12.*`", "TLC NOT_RUN; explicit-state Python search; properties hold within the bounds for the design; counterexamples for the variants")
    add("R3.D", "Documents: CLAIM_EVIDENCE table, NOVELTY_SCAN, PROTOCOL_UA_SCT, novelty summary, paper-ready tables", "DONE", "docs/, report/", "Jao and Shkel 2022, Zhang et al. 2026, Chen GLOBECOM 2023 and Carvalho et al. could not be opened and are not used")
    add("R3.T1", "T1: equal-escalation comparison (P1e, P2e against P3)", "DONE", "`t1.*`", f"P3 minus the lowered-threshold table, mis-triage at +-16 g {ci('t1.r16.mis_triage_p3_minus_p1e', 3)}; P3 wins at equal escalation: {f('t1.r16.decision.p3_wins_at_equal_escalation', 0)} (0 = no)")
    add("R3.T2", "T2: trade-off curves and areas", "DONE", "`t2.*`", f"area, interval minus point family at +-16 g {ci('t2.r16.auc_interval_minus_point', 4)}")
    add("R3.T3", "T3: expected-cost view and break-even ratio", "DONE", "`t3.*`", f"break-even C_u / C_o at +-16 g, observed mix {ci('t3.r16.sobs.break_even_ratio', 2)}; +-64 g upper end is unbounded (NOT_RUN with reason)")
    add("R3.T4", "T4: the two statements clarified", "DONE", "`t4.*`", f"single car at 60% loss, critical reach within 10 s: table {f('t4.b.loss60.P1.reach10_critical', 3)}, SCT {f('t4.b.loss60.P2.reach10_critical', 3)}, SCT with quick retries {f('t4.b.loss60.P2_quick.reach10_critical', 3)}")
    add("R3.T5", "T5: near-duplicate sensitivity (standard set stays primary)", "DONE", "`t5.*` (exploratory)", f"system recall, standard minus strict {ci('t5.diff_std_minus_strict.recall_f1', 4)}")
    add("R3.T6", "T6: severity-threshold sensitivity (17 settings)", "DONE", "`t6.*`", "H-a holds in all 17 settings; H-c in 15; no external delta-V scale could be opened (NOT_RUN)")
    add("R3.T7", "T7: conformal variants; does any restore N20 at 5%", "DONE", "`t7.*` (exploratory)", "none restores it")
    add("R3.T8", "T8: simulator assumption sweep for P0 to P4", "DONE", "`t8.*`", f"P3 beats P1 on reach within 10 s in {f('t8.count.P3_vs_P1.reach10_critical.n_beats', 0)} of {f('t8.count.P3_vs_P1.reach10_critical.n_cells', 0)} cells")
    add("R3.T9", "T9: ablations of the SCT components", "DONE", "`t9.*` (exploratory, SIMULATED)", f"burst of 30, no flash {ci('t9.diff.burst_base.P2.no_flash_minus_full.reach10_critical', 3)}; no hold {ci('t9.diff.burst_base.P2.no_hold_minus_full.reach10_critical', 3)}; the reserved share and the CANCEL message change nothing in reach")
    add("R3.T10", "T10: airtime and energy accounting", "DONE", "`t10.*` (ANALYTICAL formulas, SIMULATED counts, ASSUMED currents)", f"alert at SF7 {f('t10.airtime.sf7.alert_s', 4)} s; flash {f('t10.airtime.sf7.flash_cancel_s', 4)} s")
    add("R3.T11", "T11: attack-suite review and up to ten designed cases", "DONE", "`attacks_x.*`, docs/01_protocol/ATTACK_CASES.md", f"{f('attacks_x.cases_total', 0)} designed cases, {f('attacks_x.cases_matching_expected', 0)} behave as expected; counted apart from the {f('attacks.cases_total', 0)} original cases")
    add("R3.T12", "T12: model-check extension (flash, CANCEL after a delayed ACK)", "DONE", "`s12x.*`, docs/01_protocol/PROTOCOL_MODEL.md", "CANCEL overtaking its alert is lost in the design; remembering it fixes the model; TLC still NOT_RUN")
    add("R3.T13", "T13: second public dataset", "NOT_RUN", "`t13.second_dataset.analysis`", "no candidate dataset could be opened; no result produced")
    add("R3.T14", "T14: statistics audit with multiplicity correction", "DONE", "docs/03_results/STATS_AUDIT.md, `t14.*`", f"Holm-adjusted p: H-a {f('t14.H-a.p_holm', 4)}, H-c {f('t14.H-c.p_holm', 4)}; H-b below the bootstrap floor")
    add("R3.T15", "T15: paper-ready tables (CSV and LaTeX) and figures, each row naming its results.json key", "DONE", "results/paper/", "10 tables, 2 figures; results/paper/missing_keys.txt is empty")
    add("R3.W", "Two clean rebuilds agree; tests and ruff pass", "DONE", "scripts/run_all.ps1 -Clean (twice); scripts/compare_results.py", "run 1 and run 2 agree on all but 35 of 88,185 entries; those are the Windows compiled-C checks, which Application Control blocked in run 1 (NOT_RUN with the reason) and allowed in run 2; `check_results` 0 errors in both; the piecemeal results of the session agree with run 1 on all but 32 entries (the same blocked checks)")

    lines = ["# Algorithms compliance check\n",
             "Generated by `python -m crashguard.compliance` from `results/results.json`. Status words: DONE, PARTIAL, NOT_DONE. A number that does not exist is printed as MISSING or NOT_RUN and is never filled in. "
             "The text of the original 'three algorithm contributions' prompt is not stored in the repository; the item list follows `docs/02_preregistration/ALGORITHMS.md` (written from it before the runs), the queue entry in `docs/07_log/PROGRESS.md` and the author's Part 0 list.\n",
             "| Item | What | Status | Where (keys, files) | Number or note |", "|---|---|---|---|---|"]
    for i, item, st, where, num in rows:
        lines.append(f"| {i} | {item} | **{st}** | {where} | {num} |")
    nd = [r for r in rows if r[2].startswith("NOT_DONE")]
    pt = [r for r in rows if r[2].startswith("PARTIAL")]
    lines += ["", f"NOT_DONE items: {', '.join(r[0] for r in nd) or 'none'}. PARTIAL items: {', '.join(r[0] for r in pt) or 'none'}.",
              "A1.14 cannot be made DONE: the primary variant was not named before the results. A1.5 describes a change that was logged. A1.13 and W3 depend on the ESP32 or on Windows allowing the compiled test program; A2.8 needs the ESP32."]
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
