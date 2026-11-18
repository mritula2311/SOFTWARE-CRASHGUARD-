"""Report sections 4.8 to 8: proposed methods (N14, N15, N16), LoRa and hardware logs, figures, limitations, threats, hardware still needed, reproduce."""
from __future__ import annotations

from crashguard import config as C
from crashguard.report import Doc, Res, table

CLASS_NAMES = ("low", "moderate", "severe", "critical")


def _clears_below(r: Res, base: str) -> bool:
    """True if the whole interval name_lo..name_hi lies below zero (an improvement when the quantity is an error)."""
    hi = r.r.get(base + "_hi", {}).get("value")
    return isinstance(hi, (int, float)) and hi < 0


def _clears_above(r: Res, base: str) -> bool:
    lo = r.r.get(base + "_lo", {}).get("value")
    return isinstance(lo, (int, float)) and lo > 0


def algorithms_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.8 Proposed methods and evaluation\n")
    a("Three methods are proposed. Their baselines, splits, metrics and decision rules were written in `docs/02_preregistration/ALGORITHMS.md` before the runs (with a dated revision log). "
      "A method counts as an improvement only if its paired gain clears the 95% bootstrap interval on data it was not tuned on. If it does not, it is reported as no improvement found, with the same detail as a success.\n")
    # ---------------- N14
    a("#### N14. Saturation-aware severity estimator\n")
    a(f"A 16 g accelerometer clips real crash pulses, so plain delta-V is biased low. When a pulse reaches the range, the estimator fits a pulse model to the unsaturated rise and fall and fills the saturated samples (keeping the direction); "
      f"the ordinary severity code then integrates the repaired signal. A deterministic grid fit is used so that the same rule runs in C. The pulse family ({r.text('n14.family.chosen')}) and the saturation level "
      f"({r.f('n14.sat_frac.chosen', 1)} of the range) were chosen on the {r.i('n14.n_tuning')} tuning tests; the {r.i('n14.n_heldout')} held-out tests were scored once. A learned correction (M+) is a ridge regression of the log of "
      "reference over estimate on three inputs (delta-V of the clipped signal, saturated share, pulse width); its strength was chosen by leave-one-test-out on the tuning tests.\n")
    d.tab("n14_main", "N14 on the held-out NHTSA tests: baseline (B), fill (M) and fill plus ridge correction (M+), by sensor range at 100 Hz (95% intervals)", "MEASURED_SOFTWARE", "n14.r*.heldout.*",
          "The fill lowers the delta-V error of a 16 g sensor, but not enough to reach the 10% target; at 32 g and 64 g there is nothing to repair")
    rows = []
    for rg in (16, 32, 64):
        for m, nm in (("B", "baseline (plain integration)"), ("M", "fill"), ("M+", "fill + ridge")):
            p = f"n14.r{rg}.heldout.{m}"
            rows.append([f"±{rg} g", nm, r.i(f"{p}.n"), r.ci(f"{p}.median", 1), r.f(f"{p}.p90", 1), r.ci(f"{p}.w10", 2), r.f(f"{p}.w20", 2), r.ci(f"{p}.band", 2)])
    a(table(["Range", "Method", "Tests", "Median absolute error (%)", "90th percentile (%)", "Share within ±10%", "Share within ±20%", "Frontal share in v <= delta-V <= 2 v"], rows))
    d.tab("n14_paired", "N14 paired comparison with the baseline on the same held-out tests (method minus baseline; negative median difference is better)", "MEASURED_SOFTWARE", "n14.r*.heldout.paired.*",
          "The gain at ±16 g clears the interval; at ±32 g and ±64 g it does not")
    rows = []
    for rg in (16, 32, 64):
        for m in ("M", "M+"):
            p = f"n14.r{rg}.heldout.paired.{m}"
            ok = _clears_below(r, f"{p}.d_median")
            rows.append([f"±{rg} g", m, f"{r.f(f'{p}.d_median', 2)} [{r.f(f'{p}.d_median_lo', 2)} to {r.f(f'{p}.d_median_hi', 2)}]", f"{r.f(f'{p}.d_w10', 2)} [{r.f(f'{p}.d_w10_lo', 2)} to {r.f(f'{p}.d_w10_hi', 2)}]",
                         r.i(f"{p}.n_better"), r.i(f"{p}.n_worse"), "clears the interval" if ok else "does not clear the interval"])
    a(table(["Range", "Method", "Difference in median absolute error (points), 95% interval", "Difference in share within ±10%, 95% interval", "Tests better", "Tests worse", "Primary endpoint"], rows))
    f16 = _clears_below(r, "n14.r16.heldout.paired.M.d_median")
    f16p = _clears_below(r, "n14.r16.heldout.paired.M+.d_median")
    a(f"**Result.** At ±16 g the fill {'clears' if f16 else 'does not clear'} the interval on the held-out tests (median absolute error {r.f('n14.r16.heldout.B.median', 1)}% to {r.f('n14.r16.heldout.M.median', 1)}%) and the ridge correction "
      f"{'clears' if f16p else 'does not clear'} it ({r.f('n14.r16.heldout.M+.median', 1)}%); the share within ±10% rises from {r.f('n14.r16.heldout.B.w10', 2)} to {r.f('n14.r16.heldout.M+.w10', 2)}. This is still far from the 80% target and from what a wider-range sensor gives "
      f"(±32 g: {r.f('n14.r32.heldout.B.w10', 2)}), so the estimator repairs a 16 g sensor partly; it does not replace a wider range. The ridge weights are small and its strength was chosen as {r.f('n14.r16.ridge_alpha', 0)} (the strongest tried), so M+ is mostly a constant correction "
      f"of about {r.f('n14.r16.ridge_bias', 2)} in the logarithm. At ±32 g, {r.f('n14.r32.saturated_share', 2)} of tests reach the saturation level and at ±64 g only {r.f('n14.r64.saturated_share', 2)}; the gain does not clear the interval at either range. "
      f"**Failure cases** (held-out tests where the method is worse than the baseline): at ±16 g, {r.i('n14.r16.heldout.M.worse_tests')} tests for M and {r.i('n14.r16.heldout.M+.worse_tests')} for M+ (listed with their errors in `results/tables/n14_failure_cases.csv`); "
      f"at ±32 g, {r.i('n14.r32.heldout.M.worse_tests')} and {r.i('n14.r32.heldout.M+.worse_tests')}. They are tests where the model overshoots a pulse that is short or not shaped like the family.\n")
    d.tab("n14_synth", "N14 on synthetic saturated pulses with analytic delta-V: median absolute error (%)", "SIMULATED", "n14.synthetic.*", "The fill works on pulses that match the family and fails on a square pulse")
    rows = []
    for rg in (16, 32, 64):
        for kind, kn in (("matched", "half-sine and triangular (matched)"), ("mismatched", "square (mismatched)")):
            if r.has(f"n14.synthetic.r{rg}.{kind}.n"):
                rows.append([f"±{rg} g", kn, r.i(f"n14.synthetic.r{rg}.{kind}.n"), r.ci(f"n14.synthetic.r{rg}.{kind}.baseline.median_abs_err_pct", 1), r.ci(f"n14.synthetic.r{rg}.{kind}.method.median_abs_err_pct", 1)])
    a(table(["Range", "Pulse shape", "Saturated windows", "Baseline", "Fill"], rows))
    ok_c = r.origin("export_severity.n14.c.max_abs_diff.dv_fill_kmh") != "NOT_RUN"
    a(f"**C version.** The saturation test, the grid fit, the fill and the ridge correction are in `firmware_export/severity.h`. On {r.i('export_severity.n14.windows')} windows ({r.i('export_severity.n14.windows_saturated')} saturated; NHTSA sensor windows and synthetic pulses) "
      f"the pure-Python float32 mirror differs from the Python reference by at most {r.sci('export_severity.n14.mirror.max_abs_diff.dv_fill_kmh')} km/h in the filled delta-V, with {r.i('export_severity.n14.mirror.mismatch.applied')} different fit decisions. "
      + (f"The compiled C code differs by at most {r.sci('export_severity.n14.c.max_abs_diff.dv_fill_kmh')} km/h with {r.i('export_severity.n14.c.mismatch.applied')} different decisions. " if ok_c else "The compiled C check was blocked by Windows on the last run (NOT_RUN with the reason in results.json). ")
      + f"Host estimates (ANALYTICAL): about {r.i('export_severity.n14.ram_added_by_n14_bytes')} bytes of static RAM added and {r.i('export_severity.n14.code_bytes_added_host')} bytes of object code added on the host; an ESP32 build will differ.\n")
    d.fig("n14_estimates", "N14: estimated against reference delta-V on the held-out tests for the three methods and three ranges.", "MEASURED_SOFTWARE", "n14.*", "Saturation-aware estimator")
    from crashguard import report_part4 as P4

    P4.n14_extension(r, d)
    # ---------------- N15
    a("#### N15. Trigger-aware training\n")
    a("VZCrash events were already selected on the device by threshold heuristics, so the trigger here is a second stage and these results do not apply to continuous driving. "
      "Baseline: the fixed 2.0 g trigger and a separately trained 15-tree forest. Method a chooses the trigger level and the threshold jointly on validation; method b adds the crashes the trigger discards to the training set as positives (weight chosen on validation); "
      "method c is a learned trigger on running features (|a|, jerk, short-window energy) that needs no window buffer. Targets: false-alarm rate 1% and 5% of all non-crash events, chosen on validation.\n")
    d.tab("n15_main", "N15: system recall at a fixed false-alarm rate on the de-duplicated test set (mean ± std over seeds 0 to 4) and the paired difference with the baseline", "MEASURED_SOFTWARE", "n15.*",
          "None of the three methods raises system recall beyond the interval; the 2.0 g trigger with a separate model is about as good")
    rows = []
    for m, nm in (("baseline", "baseline (2.0 g trigger, separate forest)"), ("a_joint", "a. joint trigger level and threshold"), ("b_cost_sensitive", "b. cost-sensitive training"), ("c_learned_trigger", "c. learned trigger")):
        row = [nm]
        for t in ("t1", "t5"):
            row += [r.ms(f"n15.{m}.{t}.test_recall"), r.f(f"n15.{m}.{t}.sys_ap.mean")]
            if m == "baseline":
                row += ["-", "-"]
            else:
                pa = f"n15.{m}.{t}.paired_seedavg.d_recall"
                p4 = f"n15.{m}.{t}.paired.d_recall"
                row += [f"{r.f(pa, 4)} [{r.f(pa + '_lo', 4)} to {r.f(pa + '_hi', 4)}]", f"{r.f(p4, 4)} [{r.f(p4 + '_lo', 4)} to {r.f(p4 + '_hi', 4)}]"]
        rows.append(row)
    a(table(["Method", "Recall at 1% (mean ± std)", "System AP at 1%", "Difference in recall at 1%, seed-averaged, 95% interval (decision)", "Difference at 1%, seed 42 only", "Recall at 5% (mean ± std)",
             "System AP at 5%", "Difference in recall at 5%, seed-averaged (decision)", "Difference at 5%, seed 42 only"], rows))
    supported = [m for m in ("a_joint", "b_cost_sensitive", "c_learned_trigger") for t in ("t1", "t5") if _clears_above(r, f"n15.{m}.{t}.paired_seedavg.d_recall")]
    a("**Result.** " + ("The seed-averaged paired difference clears the interval for: " + ", ".join(sorted(set(supported))) + ". " if supported else
                         "No method clears the interval: **no improvement found** for any of the three. ")
      + f"Method a chose a trigger of {r.f('n15.choice.a_joint.t1.trigger_g', 1)} g at the 1% target; on seed 42 alone this looked like a gain of {r.f('n15.a_joint.t1.paired.d_recall', 4)} in recall, which is why the decision rule uses the seed-averaged difference "
      f"({r.f('n15.a_joint.t1.paired_seedavg.d_recall', 4)}). The higher trigger also lowers the system AP ({r.f('n15.a_joint.t1.paired.d_sys_ap', 3)} against the baseline) because it discards more crashes. "
      f"Method b chose a weight of {r.f('n15.choice.b_cost_sensitive.t1.gamma', 1)} ({r.i('n15.test_crashes')} test crashes). The learned trigger collapsed to a plain level rule (candidate {r.text('n15.choice.c_learned_trigger.t1.candidate')} at 1% and "
      f"{r.text('n15.choice.c_learned_trigger.t5.candidate')} at 5%): no combination of jerk and energy beat a level. Its cost, had it been chosen: about {r.i('n15.learned_trigger.state_bytes')} bytes of state and no sample buffer; "
      f"at the assumed {r.i('n15.learned_trigger.cycles_per_sample_assumed')} cycles per sample (an unverified assumption, ANALYTICAL; the real cost is NOT_RUN) it would use {r.f('n15.learned_trigger.cycles_share_of_sample_period', 6)} of the cycles available per sample at `240 MHz`.\n")
    d.tab("n15_size", "N15: share of test crashes that pass each method's trigger, by vehicle-size category (seed 42, 1% target)", "MEASURED_SOFTWARE", "n15.*.crash_trigger_rate_*", "The trigger choice moves the share of crashes that reach the model")
    rows = [[nm] + [r.f(f"n15.{m}.t1.crash_trigger_rate_{c}", 3) for c in ("Light", "Medium", "Heavy", "Unknown")] for m, nm in (("baseline", "baseline"), ("a_joint", "a. joint"), ("b_cost_sensitive", "b. cost-sensitive"), ("c_learned_trigger", "c. learned trigger"))]
    a(table(["Method", "Light", "Medium", "Heavy", "Unknown"], rows))
    # ---------------- N16
    a("#### N16. Severity- and budget-aware delivery scheduler (SIMULATED; supporting evidence only, not a contribution)\n")
    a(f"**Statement.** Against the fixed 3-retry policy the scheduler improves critical-alert delivery ({r.ci('n16.effect.fixed3.critical.delivered.d', 3)} in the pooled held-out cells). Against the severity table, the baseline that is already in the design, its gain in critical delivery does not clear zero "
      f"({r.ci('n16.effect.table.critical.delivered.d', 3)}) and its critical 95th-percentile latency is longer ({r.ci('n16.effect.table.critical.p95_lat_s.d', 1)} s). So N16 improves on a fixed retry policy but not on a severity table, and it is not listed among the paper's contributions. "
      "**The fixed-policy baseline is weak.** It is defined as: every alert, whatever its class, gets at most `3` tries, served in arrival order, with an immediate retry after each lost ACK and no spacing, no reserve and no priority. "
      "The severity table gives critical alerts up to `12` tries and serves the most severe waiting alert next, so beating the fixed policy is the expected result and says little about the scheduler. All of this is SIMULATED under the stated loss and stage-time assumptions.\n")
    a(f"The scheduler keeps a reserved share of the duty-cycle budget for critical alerts, orders waiting alerts by severity and age, spaces retries with exponential back-off and jitter driven by ACK feedback, and may raise the spreading factor after repeated failures. "
      f"Its parameters were tuned on {r.i('n16.tuning.scenarios')} tuning scenarios (separate seeds and loss settings) and scored once on held-out scenarios. Chosen: reserve {r.f('n16.chosen.rho', 1)}, back-off multiplier {r.f('n16.chosen.m', 1)}, "
      f"jitter {r.f('n16.chosen.jitter', 1)}, spreading-factor raise {'on' if r.v('n16.chosen.sf_raise') else 'off'}. **Everything here is SIMULATED**; the spreading-factor effect rests on an assumption (loss falls by a factor of `0.7` per step), and hardware test H3 would replace it.\n")
    d.tab("n16_conclusions", "N16: held-out scenarios where the scheduler's paired difference meets each condition (cells where it holds, of all held-out cells)", "SIMULATED", "n16.conclusion.*",
          "The scheduler beats the fixed policy for critical alerts almost everywhere but gains little over the severity table")
    concl = (("C1_better_critical_than_table", "Critical delivery better than the severity table (interval above zero)"), ("C2_better_critical_than_fixed3", "Critical delivery better than the fixed policy"),
             ("C3_fewer_blocked_critical_than_table", "Fewer critical alerts blocked by the budget than the severity table"), ("C4_lower_p95_latency_critical_than_table", "Lower 95th-percentile critical latency than the severity table"),
             ("C5_low_alerts_not_sacrificed_vs_table", "Low-alert delivery not more than `0.05` lower than the severity table"), ("C6_less_budget_than_table", "Less of the duty-cycle budget used than the severity table"))
    rows = [[nm, f"{r.i(f'n16.conclusion.{k}.holds')} of {r.i(f'n16.conclusion.{k}.cells')}", r.f(f"n16.conclusion.{k}.mean_difference", 4)] for k, nm in concl]
    a(table(["Condition", "Cells where it holds", "Mean difference over cells"], rows))
    d.tab("n16_cell", "N16 held-out scenario SF12, 30% independent loss, 20 alerts per hour: by true severity class (100 simulated hours, 95% intervals)", "SIMULATED", "n16.heldout.loss_iid30_sf12.*",
          "Per-class delivery, latency, retries and budget for the three policies")
    rows = []
    pols = ["fixed3", "table", "scheduler"] + (["scheduler_nosf"] if r.has("n16.heldout.loss_iid30_sf12.scheduler_nosf.delivered_all") else [])
    for pol in pols:
        for cls in CLASS_NAMES:
            p = f"n16.heldout.loss_iid30_sf12.{pol}"
            if r.has(f"{p}.delivered_{cls}"):
                rows.append([pol, cls, r.ci(f"{p}.delivered_{cls}", 2), r.f(f"{p}.median_lat_s_{cls}", 1), r.f(f"{p}.p95_lat_s_{cls}", 1), r.f(f"{p}.retries_{cls}", 2), r.f(f"{p}.airtime_share_{cls}", 3), r.f(f"{p}.blocked_{cls}", 3)])
    a(table(["Policy", "Class", "Alerts acknowledged", "Median trigger-to-ACK (s)", "95th percentile (s)", "Mean retries", "Share of budget used", "Blocked by the budget"], rows))
    d.tab("n16_paired", "N16 paired differences (scheduler minus baseline) in three held-out scenarios: critical alerts", "SIMULATED", "n16.paired.*", "Where the scheduler gains and where it does not")
    rows = []
    for tag, nm in (("loss_iid30_sf7", "SF7, 30% independent loss"), ("loss_iid50_sf7", "SF7, 50% independent loss"), ("loss_iid30_sf12", "SF12, 30% independent loss"), ("loss_ge30_sf12", "SF12, 30% burst loss")):
        for base in ("table", "fixed3"):
            p = f"n16.paired.{tag}.scheduler_minus_{base}"
            if r.has(f"{p}.delivered_critical.d"):
                rows.append([nm, base, f"{r.f(f'{p}.delivered_critical.d', 3)} [{r.f(f'{p}.delivered_critical.d_lo', 3)} to {r.f(f'{p}.delivered_critical.d_hi', 3)}]",
                             f"{r.f(f'{p}.p95_lat_s_critical.d', 1)} [{r.f(f'{p}.p95_lat_s_critical.d_lo', 1)} to {r.f(f'{p}.p95_lat_s_critical.d_hi', 1)}]",
                             f"{r.f(f'{p}.airtime_share_total.d', 3)} [{r.f(f'{p}.airtime_share_total.d_lo', 3)} to {r.f(f'{p}.airtime_share_total.d_hi', 3)}]"])
    a(table(["Scenario", "Baseline", "Critical alerts acknowledged: difference", "95th percentile critical latency (s): difference", "Share of budget used: difference"], rows))
    d.tab("n16_effects", "N16 effect sizes by true severity class, pooled over all held-out cells (scheduler minus baseline, paired on cell, seed and hour, 95% intervals)", "SIMULATED", "n16.effect.*",
          "Per-class gains and costs against both baselines: delivery, latency and budget")
    rows = []
    for base, bn in (("fixed3", "fixed policy"), ("table", "severity table")):
        for cls in CLASS_NAMES:
            def cell(metric, dd):
                p = f"n16.effect.{base}.{cls}.{metric}"
                return f"{r.f(p + '.d', dd)} [{r.f(p + '.d_lo', dd)} to {r.f(p + '.d_hi', dd)}]" if r.has(p + ".d") else "n/a"
            rows.append([bn, cls, cell("delivered", 3), cell("median_lat_s", 1), cell("p95_lat_s", 1), cell("airtime_share", 3), r.i(f"n16.effect.{base}.{cls}.delivered.n") if r.has(f"n16.effect.{base}.{cls}.delivered.n") else "n/a"])
    a(table(["Baseline", "True class", "Delivery rate: difference", "Median trigger-to-ACK (s): difference", "95th percentile (s): difference", "Budget used (share): difference", "Paired hours"], rows))
    a("A negative latency or budget difference is an improvement; a positive delivery difference is an improvement. Latency includes the window fill and the cancel window, which the policies do not change.\n")
    d.tab("n16_estimator", "N16 with severity estimated by the car: truly critical alerts acknowledged when priority follows the plain estimate, the saturation-aware estimate or the reference class", "SIMULATED", "n16.estimator.*",
          "An underestimated class lowers the priority of the alerts that matter; the saturation-aware estimate reduces the loss")
    rows = []
    for pool, nm in (("nhtsa_plain", "plain estimate at ±16 g"), ("nhtsa_sat", "saturation-aware estimate (N14)"), ("nhtsa_oracle", "reference class")):
        rows.append([nm, r.f(f"n16.estimator.{pool}.class_agreement", 2), r.f(f"n16.estimator.{pool}.underestimated", 2), r.f(f"n16.estimator.{pool}.est_share.critical", 2), r.f(f"n16.estimator.{pool}.true_share.critical", 2)]
                    + [r.ci(f"n16.estimator.{pool}.est_iid50_sf7.{pol}.delivered_critical", 2) for pol in ("table", "scheduler")])
    a(table(["Severity source", "Class agreement with the reference", "Underestimated", "Share estimated Critical", "Share truly Critical", "Truly critical alerts acknowledged, table (SF7, 50% loss)", "Same, scheduler"], rows))
    a("The NHTSA tests are full-speed crashes, so about half are truly Critical; the plain 16 g estimate puts most of them in lower classes, which lowers their priority, cancel-window handling and retry budget. "
      "The saturation-aware estimate moves the mix toward the reference. This ties the three methods together; it is a simulation with assumed stage times and losses.\n")
    d.fig("n16_critical_delivery", "N16: critical-alert delivery against loss for the three policies in the held-out scenarios.", "SIMULATED", "n16.heldout.*", "Scheduler evaluation")
    d.fig("n16_estimator_effect", "N16: truly critical alerts acknowledged for three sources of the severity class.", "SIMULATED", "n16.estimator.*", "Estimator effect")


def lora_and_hardware(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.9 LoRa airtime, the earlier delivery simulation and the hardware logs\n")
    d.tab("airtime", "LoRa airtime and duty-cycle budget", "ANALYTICAL", "lora.*", "A 97 B alert takes about 169 ms at SF7; the budget allows a limited number of alerts per hour")
    rows = [[f"SF{s}", r.f(f"lora.sf{s}.alert_airtime_ms", 1), r.f(f"lora.sf{s}.ack_airtime_ms", 1), r.i(f"lora.sf{s}.alerts_per_hour")] for s in range(7, 13)]
    a(table(["Spreading factor", "97 B alert (ms)", "26 B ACK (ms)", "Alerts per hour at 10% duty"], rows))
    a(f"Check: a 97 B alert at SF7 takes {r.f('lora.check_sf7_97B_ms', 2)} ms (documented value: about 169 ms). The 10% duty cycle is not verified against the WPC/DoT notification.\n")
    d.tab("delivery_old", "Earlier delivery simulation: strict verifier before the fix against the idempotent re-ACK (30% loss)", "SIMULATED", "s9.*", "A lost ACK is never repaired by a strict verifier")
    rows = []
    for sc in ("A_sf7_normal", "B_sf12_normal", "C_sf12_scarce"):
        for pol, nm in (("fixed3", "fixed, 3 retries"), ("severity", "severity-aware")):
            for mode, mn in (("strict_same_counter", "strict"), ("reack", "re-ACK")):
                p = f"s9.{sc}.{pol}.{mode}.loss30"
                rows.append([sc[0], nm, mn, r.f(f"{p}.received_all.mean"), r.f(f"{p}.acked_all.mean"), r.f(f"{p}.acked_critical.mean"), r.f(f"{p}.median_ack_s_critical.mean", 1)])
    a(table(["Scenario", "Policy", "Verifier", "Reached base, all", "ACK received, all", "ACK received, critical", "Median time to ACK, critical (s)"], rows))
    a("Assumptions are in `src/crashguard/delivery_sim.py` (A: SF7 with a full hourly budget; B: SF12; C: SF12 with a burst and most of the budget used). The end-to-end replay of Section 4.7 supersedes this simulation; it is kept for the strict-against-re-ACK comparison.\n")
    d.tab("hw", "Hardware logs ingested and what is still NOT_RUN", "HARDWARE", "hw.*", "The Wi-Fi protocol comparison and two LoRa gateway snapshots are measured; H1 to H6 are not")
    rows = []
    for p in ("HTTP", "MQTT", "CoAP"):
        rows.append([p, f"{r.f(f'hw.protocol.{p}.latency_ms_min', 0)} to {r.f(f'hw.protocol.{p}.latency_ms_max', 0)}", f"{r.f(f'hw.protocol.{p}.throughput_bps_min', 0)} to {r.f(f'hw.protocol.{p}.throughput_bps_max', 0)}",
                     f"{r.f(f'hw.protocol.{p}.packet_bytes_min', 0)} to {r.f(f'hw.protocol.{p}.packet_bytes_max', 0)}", r.f(f"hw.protocol.{p}.loss_pct", 0)])
    a(table(["Protocol", "Latency (ms)", "Throughput (bps)", "Packet size (bytes)", "Loss (%)"], rows))
    a(f"LoRa gateway snapshots: {r.i('hw.lora_gateway.snapshot1.valid')} valid frames in {r.i('hw.lora_gateway.snapshot1.uptime_s')} s, then {r.i('hw.lora_gateway.snapshot2.valid')} valid frames in {r.i('hw.lora_gateway.snapshot2.uptime_s')} s; "
      f"invalid frames {r.i('hw.lora_gateway.snapshot2.invalid')}; failed ACKs {r.i('hw.lora_gateway.snapshot2.ack_fail')}. A delivery ratio needs the transmitter total, which is missing: NOT_RUN.\n")
    nr = [k for k in ("H1", "H2", "H3", "H4", "H5", "H6") if r.origin(f"hw.{k}") == "NOT_RUN"]
    if r.origin("hw.H2.transfer") == "NOT_RUN":
        nr.append("H2 transfer")
    a("Hardware experiments with no data yet (NOT_RUN): " + (", ".join(nr) if nr else "none") + ". The plan (H1 to H6) is in Section 7.\n")
    d.fig("fig1_protocols_vs_lora", "Measured Wi-Fi protocol latency next to the analytical LoRa time on air.", "HARDWARE", "hw.protocol.*, lora.*", "Protocol latency against LoRa airtime")
    d.fig("s9_ack_strict_vs_reack", "Share of alerts whose ACK reached the car with the strict verifier and with the idempotent re-ACK.", "SIMULATED", "s9.*", "The retry fix")
    d.fig("s8_airtime_curve", "Time on air against payload size for SF7 to SF12.", "ANALYTICAL", "lora.*", "Airtime")


def figures_note(r: Res, d: Doc) -> None:
    d.a("### Other figures\n")
    d.fig("s1_class_balance", "Events per class in each supplied split.", "MEASURED_SOFTWARE", "vzcrash.events.*", "Class balance")
    d.fig("s3_feature_ablation", "AP and F1 with all features, without the gyro feature, and with scale-free features only.", "MEASURED_SOFTWARE", "s3.*", "Feature ablation")
    d.fig("lovso_vehicle_size", "AP when a vehicle-size category is held out of training.", "MEASURED_SOFTWARE", "lovso.*", "Vehicle-size transfer")
    d.fig("s7_attack_table", "Attack suite outcomes.", "SIMULATED", "attacks.*", "Security")
    d.fig("s5_reliability", "Reliability curves from the original model comparison (seed 42).", "MEASURED_SOFTWARE", "s5.*", "Calibration")


def limitations(r: Res, d: Doc) -> None:
    a = d.a
    a("## 5. Limitations\n")
    a("### What these results do and do not show\n")
    a("**They show:**")
    a(f"- On the de-duplicated VZCrash test set, the deployable 15-tree forest finds crashes with system recall {r.ci('detector.head5.rf15.sys_recall')} at a system false-alarm rate of {r.ci('detector.head5.rf15.sys_fpr')} (mean of 5 seeds, interval for the mean; seed 42 alone: {r.ci('detector.head.rf15.sys_recall')} and {r.ci('detector.head.rf15.sys_fpr')}); "
      f"with the false-alarm rate fixed at 1% on validation, recall is {r.ms('detector.op.t1.rf15.test_recall')}.")
    a(f"- Fitting on the ESP32 costs AP: the 200-tree forest is higher by {r.f('gap.rf200_minus_rf15.ap', 4)} and gradient-boosted trees by {r.f('gap.gbt_minus_rf15.ap', 4)}. A 10-tree depth-9 forest chosen on validation is close to the deployed model.")
    a("- Sensor errors move recall by a few points at most, except a 0.5 g offset on the vertical axis and some misalignments (Section 4.3).")
    a(f"- For severity, the range of the accelerometer is the limit: a ±16 g sensor at 100 Hz is within 10% of the reference delta-V on {r.f('sevstudy.grid.r16.f100.dv_within10', 2)} of crash tests; ±{r.f('sevstudy.needed.point.min_range_g', 0)} g at {r.f('sevstudy.needed.point.min_rate_hz', 0)} Hz reaches 80%.")
    a("- The security design behaves as intended in software tests. Our own testing found the retry-against-replay problem; the idempotent re-ACK with a rate limit fixes it, at the cost of a flood that can still spend airtime.")
    a("- N14 holds at ±16 g only and not as a blind test; N15 gives no improvement beyond the interval; the scheduler (N16) improves on a weak fixed policy but not on the severity table and is supporting evidence only (Section 4.8).")
    a("- The forest is evaluated where the VZCrash paper left a gap: that paper benchmarks neural and transformer models and a peak-acceleration baseline, tested no tree models and ran no embedded test. We do not run a transformer comparison.\n")
    a("**They do not show:**")
    for t in ("Injury. The severity classes indicate crash severity, not diagnosed injury, and VZCrash has no severity labels.",
              "That the severity scale is a published standard. The 13 Hz filter and the THIV flail-space distances are unverified; the delta-V class limits, the class names and the release rule are our choices (`docs/05_data_code/SEVERITY.md`).",
              "A reliable rollover flag. Both the integrated-angle flag and the gravity-corrected flag fire on more than 0.5% of normal driving, so the flag is reported but kept out of the severity class.",
              "Anything about the car. No hardware crash has been classified here; every MEASURED_SOFTWARE number comes from full-size vehicle data or crash tests, not the scale model. The transfer test is part of H2 and is NOT_RUN.",
              "Timing or memory on the ESP32. Sizes are host estimates; the benchmark sketch is built but not run.",
              "Real radio behaviour. Airtime is a formula, delivery results are simulations with stated assumptions (one node, no collisions, assumed stage times), and the 10% duty cycle is not verified against the official notification.",
              "Security beyond integrity, authenticity and replay rejection. Alerts are not encrypted; one key is shared; there is no key rotation; a lost counter store allows a replay.",
              "Results for the final trigger and sensor settings. The trigger level and sensor range are placeholders until confirmed from firmware v2, and every system-level number moves with them."):
        a(f"- {t}")
    a("\n### Limitations in a list\n")
    for t in ("The trigger level (2.0 g) and sensor range (16 g), the window lengths (1.0 s before and 1.8 s after the trigger) are placeholders in `src/crashguard/config.py`.",
              "Prevalence. Results on a dataset with roughly `16%` crashes do not describe precision in real driving: the VZCrash paper reports `143` confirmed crashes among `735,000` real-world harsh-driving events (under `0.02%`), where its best model's average precision fell to about `86%`. Precision at lower prevalence in Table 'prevalence' is ANALYTICAL and assumes the measured false-alarm rate carries over.",
              "VZCrash events were already triggered on the device: the dataset is pre-selected and the trigger here is a second stage. Results do not apply to continuous driving.",
              "VZCrash has no vehicle or trip ID, so the stated vehicle-level separation of its splits cannot be checked; repeated recordings were found across splits and removed from the primary test set.",
              "Duplicates: the validation split may also repeat training events (not corrected), which may make validation scores optimistic.",
              "The severity class limits (24, 40 and 56 km/h) and the class names are our choice, supported by cited literature but not a published four-class scale; the class mix moves when the limits move by 20%.",
              "The MPU-6050 range is ±16 g: it clips crash pulses and underestimates delta-V in full-speed crashes. A wider-range part is needed to measure severity.",
              "The NHTSA tests are frontal barrier and side impactor tests of cars; the reference delta-V is a defined integral, not a measured vehicle velocity change. The sensor model is generic and ours.",
              "Unverified constants: the 13 Hz ASI pre-filter; the THIV flail-space distances (`0.6 m` used, `0.8 m` in one read source); the class names and cut points. The ASI level C limit was read in a secondary source, not the standard.",
              "Simulation assumptions: Poisson arrivals, independent or Gilbert-Elliott loss, assumed stage times and cancel windows, one node, no collisions, the base receives every spreading factor, loss falls by an assumed factor with the spreading factor.",
              "Replay flood and shared key: a sustained flood can still exhaust the base station's budget; one key is shared on both nodes with no rotation; the lost-counter-store replay is documented, not fixed.",
              "Hardware: the 433 MHz band is for the testbed only; scale-model impact forces are not real-vehicle forces; severity against impact strength and runs at 200 m are not in the minimum plan.",
              "Compiled C checks can be blocked by Windows Application Control; then they are recorded as NOT_RUN and the pure-Python mirror is the remaining check."):
        a(f"- {t}")
    a("")


def threats(r: Res, d: Doc) -> None:
    a = d.a
    a("## 6. Threats to validity\n")
    for t in ("**Selection of events.** VZCrash events passed a device-side trigger before release. A detector that works here may not work on continuous driving, where the false-alarm exposure is far larger.",
              "**Leakage.** Identical recordings occur across the official splits. We removed the ones we found (exact and near-identical); other correlations (the same vehicle in train and test) cannot be checked without a vehicle ID, so scores may be optimistic.",
              "**Small crash-test set.** The NHTSA set is a few dozen frontal tests per speed class and many side tests; held-out parts have a few dozen tests, so intervals are wide. The reference delta-V is our own definition.",
              "**Tuning on small sets.** The release fraction and the N14 settings were chosen on tuning tests; held-out tests were scored once, but a development run with all tests together had been looked at before the wider NHTSA set was fixed (logged in `docs/07_log/DECISIONS.md`).",
              "**Simulation validity.** The replay and the scheduler depend on assumed loss processes, stage times and a spreading-factor model. Conclusions are stated per assumption, and hardware test H3 is the check.",
              "**Single seed in paired intervals.** Paired intervals resample test events for one model draw; the trigger study therefore uses the seed-averaged difference after a seed-42 difference proved unstable.",
              "**Multiple comparisons.** Many cells and metrics are reported; an interval that excludes zero in a single cell is not a claim. Claims are stated for pre-set endpoints.",
              "**Environment.** Python, package versions and the operating system are recorded in `results/results.json` (`env.*`); results reproduce exactly on this machine; other platforms may differ in the last digit."):
        a(f"- {t}")
    a("")


def hardware_needed(r: Res, d: Doc) -> None:
    a = d.a
    a("## 7. What hardware must still show (Still needed from hardware)\n")
    for t in ("Confirm from firmware v2: trigger level, sensor range, window lengths, the packet byte layout (little-endian is assumed), the sampling rate and the sensor count (`docs/05_data_code/FIRMWARE_SYNC.md`).",
              "Implement the idempotent re-ACK with its limit on the base station and decide how many alerts it remembers. Without it, a lost ACK is never repaired when the car repeats a counter.",
              "The minimum hardware plan, logged in `hw_events.csv`, `hw_windows.csv`, `hw_attacks.csv` and `hw_memory.csv` (schemas in `docs/05_data_code/HARDWARE_SCHEMA.md`), then `make merge`: "
              "**H1** impact side (10 hits on each of 4 sides and 10 vertical drops); **H2** crash against not-crash and the transfer test from VZCrash; **H3** LoRa delivery (20 alerts each at 10, 50 and 100 m), which would replace the replay; "
              "**H4** security (forged, tampered, replay, spoofed ACK, base reboot, ACK-lost retry); **H5** edge cost (compile report and microseconds), which would replace the host size estimates; **H6** SW-420 ablation. `docs/05_data_code/HARDWARE_READINESS.md` has the schemas and a dry run of the merge on dummy files.",
              "Transmitter totals for the LoRa tests, so a delivery ratio can be computed.",
              "Run `benchmark_rf.ino` on the ESP32 and compile the generated headers with the Arduino toolchain (gcc), including `crashguard_rf_candidate.h` and `severity.h`.",
              "Choose an accelerometer of at least ±64 g sampled at 200 Hz or faster if severity is to be measured, or accept the partial repair of N14 at ±16 g.",
              "Verify the 433 MHz limits and duty cycle against the WPC/DoT notification, and the EN 1317-2 constants against the standard (`docs/06_references/MANUAL_SEARCH_CHECKLIST.md`)."):
        a(f"- {t}")
    a("")


def reproduce(r: Res, d: Doc) -> None:
    a = d.a
    a("## 8. Reproduce\n")
    a(f"Environment recorded in the run: Python `{r.text('env.python_version')}` on `{r.text('env.platform')}`. The exact commands are in `docs/05_data_code/REPRODUCE.md`; in short, `.\\scripts\\run_all.ps1 -Clean` rebuilds every output from a clean checkout "
      "(it fails loudly if a result the report cites is NOT_RUN without a stated reason), and `PYTHONPATH=src python -m pytest -q` runs the tests. On Linux, `make all`.\n")
    if C.TRIGGER_G:
        a("The trigger level and sensor range in `config.py` are placeholders; change them there only and re-run.\n")
