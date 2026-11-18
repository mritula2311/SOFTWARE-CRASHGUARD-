"""Report subsection (round 3): round 3 (software follow-ups, the UA-SCT study, the bounded model check). Numbers only through the ``Res`` helpers; hand-typed numbers only inside backticks."""
from __future__ import annotations

from crashguard.report import Doc, Res, table

RG = (16, 32, 64)


def _flag(r: Res, k: str) -> str:
    e = r.r.get(k)
    if e is None:
        r._miss(k)
        return "missing"
    if e["value"] in ("NOT_RUN", None):
        return "not checked"
    return "holds" if e["value"] == 1 else "**FAILS**"


def round3_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### Round 3: software follow-ups and the UA-SCT study\n")
    a("All results in this subsection are software-only. Origins are stated per table: MEASURED_SOFTWARE (NHTSA tests, VZCrash), SIMULATED (the simulators of `capacity.py` and `sct_sim.py`, every channel, traffic and timing value an assumption), ANALYTICAL (bounded model check). "
      "The UA-SCT hypotheses were written down in `docs/02_preregistration/PREREGISTRATION.md` before any UA-SCT run. The duty-cycle limit is a parameter; the one per cent default is NOT verified for India. NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes.\n")

    # ---------------------------------------------------------------- A1 / S3
    a("#### N20 again: conformal false-alarm control with calibration data de-duplicated by recording group (S3, A1)\n")
    a(f"The calibration pool is the non-crash validation events: all {r.i('n20c.calib.n_negatives_dirty')}; without any event whose raw recording also occurs in a training or test event (recording groups) {r.i('n20c.calib.n_negatives_hashgroup')}; and also without window-level near-duplicates {r.i('n20c.calib.n_negatives_clean')}. "
      f"The de-duplicated test set has {r.i('n20c.test.n_negatives')} non-crash events. Intervals are 95% bootstrap intervals (`1000` resamples) for the mean over seeds and calibration draws; they do not include test-set sampling error, one standard error of which is {r.f('n20c.clean.a1.test_se', 4)} at alpha `1%` and {r.f('n20c.clean.a5.test_se', 4)} at `5%`. "
      "The guarantee is said to hold if the upper end of the interval is at or below alpha plus one standard error (rule fixed in `docs/02_preregistration/EXPERIMENTS_EXTRA.md`).\n")
    d.tab("s3", "N20: test false-alarm rate against alpha with the full calibration pool, by recording group and with near-duplicates removed", "MEASURED_SOFTWARE", "n20c.*", "The guarantee does not hold at alpha `5%`; removing duplicates does not repair it")
    rows = []
    for calib, nm in (("dirty", "all validation non-crash events"), ("hashgroup", "recording groups removed"), ("clean", "recording groups and near-duplicates removed")):
        for al in (1, 5):
            for m in ("conformal", "validation", "weighted"):
                p = f"n20c.{calib}.a{al}.nall.{m}"
                rows.append([nm, f"{al}%", m, r.ci(f"{p}.fa_mean", 4), r.f(f"{p}.share_above_alpha", 2), "yes" if r.has(f"{p}.holds_1se") and r.v(f"{p}.holds_1se") == 1 else "no"])
    a(table(["Calibration pool", "alpha", "Method", "False-alarm rate [95%]", "Share of runs above alpha", "Guarantee holds"], rows))
    a("The duplicates sit almost entirely in the crash class, so the calibration pool barely changes. The excess over alpha comes from the vehicle-level split between validation and test, not from the duplicates. The weighted variant is exploratory.\n")

    # ---------------------------------------------------------------- S2
    a("#### N8 and the headline: identical recordings and near-duplicates (S2)\n")
    a(f"A window-level scan (trigger-aligned windows, correlation above `0.999` and maximum difference below `0.01` g, fixed before the run) finds that {r.i('dupscan.neardup.n_both')} of {r.i('dupscan.neardup.n_scanned')} triggered test windows have a train or validation window that is identical to within `0.01` g; "
      f"{r.i('dupscan.neardup.n_both_new')} of them were not removed by the exact-hash and nearest-neighbour rules ({r.i('dupscan.neardup.n_both_new.crash')} crash events). N8 is a data-quality finding, not a performance finding.\n")
    d.tab("s2", "N8: system recall of the deployed forest on the supplied, the de-duplicated and the stricter window-level de-duplicated test sets (5-seed mean, validation F1 threshold)", "MEASURED_SOFTWARE", "s2.*", "Exact duplicates change the headline by under a point; window-level near-duplicates by about three points")
    rows = []
    for met, nm in (("sys_recall", "System recall"), ("sys_fpr", "System false-alarm rate"), ("ap", "AP (triggered events)"), ("sys_ap", "System AP")):
        rows.append([nm] + [r.ci(f"dupscan.rf15.mean5.{k}.{met}", 4) for k in ("supplied", "dedup", "dedup_nd")] + [r.ci(f"dupscan.rf15.mean5.diff_supplied_minus_dedup.{met}", 4), r.ci(f"dupscan.rf15.mean5.diff_supplied_minus_dedup_nd.{met}", 4)])
    a(table(["Metric", "Supplied test split", "De-duplicated (primary)", "Window-level de-duplicated", "Supplied minus de-duplicated [95%]", "Supplied minus window-level [95%]"], rows))
    a("The primary test set was not changed; the stricter set is reported beside it and the choice is the author's.\n")

    # ---------------------------------------------------------------- S4
    a("#### N14 and N13: severity strata, the gap to the N13 target and the tail (S4)\n")
    a("Fill + ridge was named primary after earlier results were seen. Bins are by reference delta-V (km/h), fixed before the run; split R (repeated grouped cross-validation, `+-16` g, `100` Hz); intervals only for bins with `10` or more tests.\n")
    d.tab("s4_strata", "N14: median absolute delta-V error (%) by reference delta-V bin, split R, +-16 g", "MEASURED_SOFTWARE", "n14s.strata.dv.*", "Fill + ridge helps most in the largest bin; it hurts relative to fill alone in the 30 to 45 km/h bin")
    rows = []
    for b, nm in (("lt30", "below 30"), ("30to45", "`30` to `45`"), ("45to60", "`45` to `60`"), ("ge60", "60 or more")):
        p = f"n14s.strata.dv.{b}"
        row = [nm, r.i(f"{p}.n"), r.f(f"{p}.sat16", 2), r.f(f"{p}.sat32", 2)]
        for m in ("B", "SP", "M", "M+"):
            row.append(r.f(f"{p}.r16.{m}.median", 1))
        row.append(f"{r.f(f'{p}.r16.M+.median_lo', 1)} to {r.f(f'{p}.r16.M+.median_hi', 1)}")
        rows.append(row)
    a(table(["Reference delta-V (km/h)", "Tests", "Saturation test fires at +-16 g", "at +-32 g", "Plain", "Spline", "Fill", "Fill + ridge", "Fill + ridge, 95% interval"], rows))
    a(f"Gap to the N13 target of `80%` within `10%` at `+-16` g and `100` Hz (split R): plain {r.f('n14x.R.r16.B.w10', 3)}, spline {r.f('n14x.R.r16.SP.w10', 3)}, fill {r.f('n14x.R.r16.M.w10', 3)}, fill + ridge {r.f('n14x.R.r16.M+.w10', 3)}; within `20%`: {r.f('n14x.R.r16.B.w20', 3)}, {r.f('n14x.R.r16.SP.w20', 3)}, {r.f('n14x.R.r16.M.w20', 3)}, {r.f('n14x.R.r16.M+.w20', 3)}. "
      "Fill + ridge narrows the gap and does not close it. "
      f"M+ capped (exploratory: the predicted log-correction clipped to the `5`th to `95`th percentile of the tuning groups) clipped {r.i('n14s.cap.R.r16.n_predictions_clipped')} of {r.i('n14s.cap.R.r16.n_predictions_on_saturated_tests')} predictions at `+-16` g, so it is identical to fill + ridge there: it does not improve the tail (`90`th percentile {r.f('n14s.cap.R.r16.M+.p90', 1)}% for both).\n")

    # ---------------------------------------------------------------- S5 / A4
    a("#### N16 and N22: the burst scenario with a sensitivity sweep (S5, A4)\n")
    a("The burst scenario was added after the steady-state comparison against the severity table was a null result, so it is exploratory. The scheduler grid was tuned on separate tuning bursts and scored once on held-out bursts. X6 simulator (token-bucket duty rule, `10%`).\n")
    d.tab("s5", "N16: critical delivery, scheduler minus severity table, over the burst sweep (40 paired seeds per setting)", "SIMULATED", "s5.heldout.*", "The scheduler beats the table in every setting; the gain is small at SF12 and depends on SF, capture and burst size")
    rows = []
    for st, nm in (("default", "default (100 cars, SF7, burst 30, 6 dB capture)"), ("capture_none", "no capture (pure ALOHA)"), ("burst10", "burst 10"), ("burst60", "burst 60"), ("burst100", "burst 100"), ("cars50", "50 cars"), ("cars200", "200 cars"),
                   ("hb60", "heartbeat 60 s"), ("hbpayload26", "heartbeat payload 26 B"), ("hbpayload48", "heartbeat payload `48` B"), ("sf9", "SF9"), ("sf12", "SF12"), ("loss30", "loss 30%"), ("loss60", "loss 60%")):
        p = f"s5.heldout.{st}"
        rows.append([nm, r.f(f"{p}.severity.delivered_critical", 3), r.f(f"{p}.scheduler.delivered_critical", 3), r.ci(f"{p}.diff.scheduler_minus_severity.delivered_critical", 3), r.ci(f"{p}.diff.scheduler_minus_severity.reach30_critical", 3)])
    a(table(["Setting", "Table, critical delivery", "Scheduler, critical delivery", "Scheduler minus table [95%]", "Reach within 30 s, scheduler minus table [95%]"], rows))
    a(f"In the A4 sweep (capture none and `6` dB, burst `10`, `30`, `60`, payload `16` and `26` B, cars `50`, `100`, `200`, SF `7` and `9`) the scheduler is better than the table in {r.i('s5.a4.scheduler_vs_severity.delivered_critical.n_better')} settings; the settings where it is not better: {r.text('s5.a4.scheduler_vs_severity.delivered_critical.settings_where_not_better')}. "
      "The gain is smallest at SF12 (outside A4), where every policy delivers few critical alerts. The burst-tuned scheduler has no reserve, no jitter and no spreading-factor raise, so the gain is retry spacing; the critical `95`th-percentile latency is longer in every setting because more late alerts are delivered.\n")

    # ---------------------------------------------------------------- S6
    a("#### N19: early exit and ensemble effect separated (S6)\n")
    d.tab("s6", "N19: recall at a fixed false-alarm rate and mean decision time of crash events for the single full-length forest (F), the same forest scored at the early-exit time (A) and the six-forest early-exit rule (E); the ensemble without early exit (E') has the alarms of E", "MEASURED_SOFTWARE", "s6.*",
          "The time saving is about one second at both targets; the recall gain is an ensemble effect")
    rows = []
    for al, an in ((1, "1%"), (5, "5%")):
        for lab, k in (("A minus F (early exit, single forest)", "d.A_minus_F.recall"), ("E' minus F (ensemble, no time saving)", "d.Ep_minus_F.recall"), ("E minus E' (early exit with the ensemble)", "d.E_minus_Ep.recall")):
            rows.append([an, lab, r.ci(f"s6.a{al}.mean5.{k}", 4), r.ci(f"s6.a{al}.seed42.{k}", 4)])
        rows.append([an, "Decision time, E minus E' (ms)", r.ci(f"s6.a{al}.mean5.d.E_minus_Ep.time", 0), r.ci(f"s6.a{al}.seed42.d.E_minus_Ep.time", 0)])
    a(table(["False-alarm target", "Difference", "Mean of 5 seeds [95%]", "Seed 42 [95%]"], rows))

    # ---------------------------------------------------------------- S9
    a("#### N24: conformal intervals for the clipped delta-V estimate (S9)\n")
    d.tab("s9", "N24: grouped CV+ intervals around the fill + ridge delta-V at +-16 g: coverage, width and the class decision rule", "MEASURED_SOFTWARE", "s9.*", "Coverage is about nominal; the class rule raises under-estimation")
    rows = []
    for rg in RG:
        for nom in (80, 90):
            p = f"n24.r{rg}.nom{nom}"
            rows.append([f"+-{rg} g", f"{nom}%", r.ci(f"{p}.coverage", 3), r.f(f"{p}.width_kmh_median", 1), r.f(f"{p}.in_one_class_share", 2), r.f(f"{p}.under_point", 3), r.f(f"{p}.under_decision", 3), r.ci(f"{p}.under_drop", 3)])
    a(table(["Range", "Nominal", "Coverage [95%]", "Median width (km/h)", "Interval in one class (share)", "Under-estimation, point class", "Under-estimation, decision rule", "Drop (point minus rule) [95%]"], rows))
    a("The preregistered decision rule (report the class below when the lower bound is lower, plus a flag) does not improve: it lowers the reported class, so under-estimation rises. No improvement found.\n")

    # ---------------------------------------------------------------- S10
    a("#### N25: prevalence-adaptive threshold and cancel-window cost model (S10)\n")
    a(f"Populations of `1,000,000` events resampled from the de-duplicated test pool (`200` repeats), conditional on the device's own pre-selection. Costs are assumptions: a miss costs `1000` times a false alarm and the driver cancels `90%` of false alarms in time. Precision at prevalence `0.02%` with the existing threshold is {r.f('s10.rf15.pi0p02pct.a.ppv', 4)}.\n")
    d.tab("s10", "N25: system recall, precision and false alarms per 100,000 events by prevalence and threshold rule (deployed forest, mean over seeds)", "MEASURED_SOFTWARE", "s10.rf15.*", "No rule raises precision within five points of recall at a prevalence of one per cent or lower")
    rows = []
    for pi, nm in (("0p02pct", "`0.02%`"), ("0p1pct", "0.1%"), ("1pct", "1%"), ("16pct", "16%")):
        for rule, rn in (("a", "existing (F1)"), ("a1", "1% target"), ("b_known", "prior-shift adjusted"), ("c_known", "minimum cost"), ("d10", "target precision 10%"), ("d50", "target precision 50%")):
            p = f"s10.rf15.pi{pi}.{rule}"
            if not r.has(p + ".recall"):
                continue
            rows.append([nm, rn, r.ci(p + ".recall", 3), r.ci(p + ".ppv", 4), r.f(p + ".fp100k", 0)])
    a(table(["Prevalence", "Rule", "Recall [95%]", "Precision [95%]", "False alarms per 100,000 events"], rows))

    # ---------------------------------------------------------------- B1
    a("#### UA-SCT B1: severity class from delta-V at the three sensor ranges and two sampling rates\n")
    a("The plain (unrestored) estimate is reported at `100` and `200` Hz; fill + ridge at `200` Hz is NOT_RUN because its constants (pulse-fit offsets in samples, saturation level, ridge strength) were tuned at `100` Hz and were not re-tuned. The reference class uses the reference delta-V and ASI.\n")
    d.tab("ua_b1", "UA-SCT B1: plain delta-V estimate: median absolute error, share within 10% and class agreement, by range and rate (grouped bootstrap 95% intervals)", "MEASURED_SOFTWARE", "ua.b1.*", "A higher rate helps little at +-16 g; the range matters")
    rows = []
    for fs in (100, 200):
        for rg in RG:
            p = f"ua.b1.plain.f{fs}.r{rg}"
            rows.append([f"{fs} Hz", f"+-{rg} g", r.ci(f"{p}.median_err_pct", 1), r.ci(f"{p}.within10", 3), r.ci(f"{p}.class_agree", 3), r.f(f"{p}.class_under", 3)])
    a(table(["Rate", "Range", "Median error (%) [95%]", "Within 10% [95%]", "Class agrees with the reference [95%]", "Class under-estimated"], rows))
    a(f"Fill + ridge at `100` Hz for comparison (split R, median error): {r.f('n14x.R.r16.M+.median', 1)}% at `+-16` g, {r.f('n14x.R.r32.M+.median', 1)}% at `+-32` g, {r.f('n14x.R.r64.M+.median', 1)}% at `+-64` g.\n")

    # ---------------------------------------------------------------- B2
    a("#### UA-SCT B2: conformal severity classes per sensor range\n")
    a("Point estimate: fill + ridge at `100` Hz. Calibration groups are disjoint from tuning and test groups (identical recordings merged). Class-conditional (per predicted class), one-sided upper end; coverage is of the two-sided interval over the four ordered classes.\n")
    d.tab("ua_cov", "UA-SCT: interval coverage against target and mean width in classes, per sensor range (grouped bootstrap 95% intervals)", "MEASURED_SOFTWARE", "ua.r*", "Coverage is at or above the target (conservative); intervals are wide at +-16 g and narrower at +-64 g")
    rows = []
    for rg in RG:
        for al, nom in ((10, "90%"), (5, "95%")):
            for var, vn in (("pooled", "pooled"), ("cc", "class-conditional")):
                p = f"ua.r{rg}.a{al}.{var}"
                rows.append([f"+-{rg} g", nom, vn, r.ci(f"{p}.coverage", 3), r.f(f"{p}.upper_valid", 3), r.f(f"{p}.width", 2), r.f(f"{p}.upper_above_point", 2)])
    a(table(["Range", "Target", "Version", "Two-sided coverage [95%]", "Upper end valid (one-sided)", "Mean width (classes)", "Upper end above point class"], rows))
    a("The nominal coverage lies below the interval in every row: the intervals are conservative (integer scores and small calibration sets), not exact. Class-conditional intervals fall back to the pooled quantile where a predicted class has fewer than `10` calibration tests.\n")

    # ---------------------------------------------------------------- B3-B7
    a("#### UA-SCT B3 to B7: transmission policies P0 to P4 (S11)\n")
    a(f"P0 fixed 3-retry; P1 severity table (point class); P2 SCT (point class); P3 UA-SCT (upper end of the class interval, alpha `0.10`); P4 P3 with the fast-path airtime capped at a share of the duty budget (tuned on separate scenarios: Severe hold {r.f('s11.tuned.h_s', 0)} s, reserved share {r.f('s11.tuned.rho_f', 2)}, cap share {r.f('s11.tuned.phi', 2)}). "
      f"Duty limit `1%` of every trailing hour (not verified for India), `100` cars, SF `7`, `40` paired seeds per cell. Runs in which an independent scan found more airtime than the limit: {r.i('s11.duty.runs_exceeding_limit')} of {r.i('s11.duty.runs')}.\n")
    for rg in RG:
        for mode, mn in (("steady", "steady state"), ("burst", "burst of 30 critical alerts")):
            d.tab(f"ua_pol_{rg}_{mode}", f"UA-SCT: policy comparison at +-{rg} g, {mn} (default cell; mean over seeds)", "SIMULATED", f"s11.cell.r{rg}.{mode}.base.*",
                  "Mis-triage falls with the upper-end class; delivery in bursts is set by the fast path, not by the upper end")
            rows = []
            for pol, pn in (("P0", "P0 fixed 3-retry"), ("P1", "P1 severity table"), ("sched", "N16 scheduler"), ("P2", "P2 SCT"), ("P3", "P3 UA-SCT"), ("P4", "P4 UA-SCT, capped")):
                p = f"s11.cell.r{rg}.{mode}.base.{pol}"
                rows.append([pn, r.f(f"{p}.mis_triage", 3), r.f(f"{p}.escalation", 3), r.f(f"{p}.reach10_critical", 3), r.f(f"{p}.reach30_critical", 3), r.f(f"{p}.p95_lat_s_critical", 1), r.f(f"{p}.fast_air_share_of_allowance", 3), r.f(f"{p}.node_air_share", 3)])
            a(table(["Policy", "Mis-triage", "Escalation of non-severe events", "Critical reach within 10 s", "within 30 s", "Critical 95th-percentile latency (s, delivered)", "Fast-path airtime, share of allowance", "Airtime, share of allowance"], rows))
    d.tab("ua_diff", "UA-SCT: paired differences over all held-out cells by range (mean over cells; 95% intervals resample the seeds inside every cell)", "SIMULATED", "s11.diff.*", "H-a, H-b, H-c and the burst against steady-state contrast")
    rows = []
    for rg in RG:
        for grp, gn in (("steady", "steady cells"), ("burst", "burst cells")):
            for b, a_, lab in (("P3", "P1", "P3 minus P1"), ("P2", "P1", "P2 minus P1"), ("P3", "P2", "P3 minus P2"), ("P4", "P3", "P4 minus P3")):
                p = f"s11.diff.r{rg}.{grp}.{b}_minus_{a_}"
                rows.append([f"+-{rg} g", gn, lab, r.ci(f"{p}.mis_triage", 3), r.ci(f"{p}.escalation", 3), r.ci(f"{p}.reach10_critical", 3), r.ci(f"{p}.reach30_critical", 3)])
    a(table(["Range", "Cells", "Comparison", "Mis-triage [95%]", "Escalation [95%]", "Critical reach within 10 s [95%]", "within 30 s [95%]"], rows))
    a(f"**H-a** (P3 lowers mis-triage against P1 at `+-16` g): pool-level paired difference {r.ci('ua.r16.a10.cc.paired.mis_triage_upper_minus_point', 3)} (grouped bootstrap), simulated steady cells {r.ci('s11.diff.r16.steady.P3_minus_P1.mis_triage', 3)}: supported, a reduction of more than two points. "
      f"**H-b** (the cost is more fast-path escalations; P4 bounds it): escalation rises by {r.ci('ua.r16.a10.cc.paired.escalation_upper_minus_point', 3)}; P4 stays under its cap share but the cap binds only in few cells (P4 minus P3 in bursts: reach within 10 s {r.ci('s11.diff.r16.burst.P4_minus_P3.reach10_critical', 3)}, node airtime {r.ci('s11.diff.r16.burst.P4_minus_P3.node_air_share', 4)}): the cost is large in escalations and small in airtime. "
      f"**H-c** (the gain shrinks at `+-64` g): the mis-triage reduction at `+-16` g minus that at `+-64` g is {r.ci('ua.hc.reduction_16_minus_64', 3)} and the mean width is narrower by {r.ci('ua.hc.width_64_minus_16', 2)} classes: supported. "
      f"**B7:** in steady state P3 against P1 changes critical reach within 10 s by {r.ci('s11.diff.r16.steady.P3_minus_P1.reach10_critical', 3)} (no gain); the gain is in mis-triage and in bursts, where P2 and P3 gain {r.f('s11.diff.r16.burst.P2_minus_P1.reach10_critical', 3)} and {r.f('s11.diff.r16.burst.P3_minus_P1.reach10_critical', 3)} against P1; P3 against P2 in bursts changes reach within 10 s by {r.ci('s11.diff.r16.burst.P3_minus_P2.reach10_critical', 3)} and within 30 s by {r.ci('s11.diff.r16.burst.P3_minus_P2.reach30_critical', 3)}.\n")
    a("**Where it is worse.** P3 sends many more non-severe events through the fast path (escalation above); with false alarms at the `5%` target the fast path carries "
      f"{r.f('s11.exploratory.false_alarm.fa5.P3.fa_tx_fast', 1)} false alerts per hour at `100` cars against {r.f('s11.exploratory.false_alarm.fa5.P1.fa_tx_fast', 1)} for the table (EXPLORATORY; the false-alarm class mix is a worst-case assumption). "
      f"For a single car with `60%` loss, critical reach within 10 s is {r.f('s11.exploratory.single_car.loss60.P2.reach10_critical', 3)} for SCT against {r.f('s11.exploratory.single_car.loss60.P1.reach10_critical', 3)} for the table (EXPLORATORY): fixed `5` s spacing is worse than immediate retries when there is no collision.\n")
    a("**Which SCT element matters (EXPLORATORY ablations, P2, `+-16` g, burst, critical reach within 10 s):** "
      f"full {r.f('s11.exploratory.ablation.burst.P2.full.reach10_critical', 3)}; no flash {r.f('s11.exploratory.ablation.burst.P2.no_flash.reach10_critical', 3)}; no severity-dependent hold {r.f('s11.exploratory.ablation.burst.P2.no_sev_hold.reach10_critical', 3)}; no preemption {r.f('s11.exploratory.ablation.burst.P2.no_preempt.reach10_critical', 3)}; "
      f"no reserve {r.f('s11.exploratory.ablation.burst.P2.no_reserve.reach10_critical', 3)}; no spreading-factor raise {r.f('s11.exploratory.ablation.burst.P2.no_sf_raise.reach10_critical', 3)}.\n")

    # ---------------------------------------------------------------- S13
    a("#### N26: SCT against a severity table with spaced retries (S13)\n")
    d.tab("s13", "N26: critical reach, SCT (P2) minus the severity table with spaced retries (P1b), and the spaced table minus the plain table", "SIMULATED", "s13.*", "Spacing explains most of the 30 s gain; SCT still adds reach within 10 s in bursts")
    rows = []
    for rg in RG:
        rows.append([f"+-{rg} g", r.ci(f"s13.diff.r{rg}.burst.P1b_minus_P1.reach10_critical", 3), r.ci(f"s13.diff.r{rg}.burst.P1b_minus_P1.reach30_critical", 3), r.ci(f"s13.diff.r{rg}.burst.P2_minus_P1b.reach10_critical", 3), r.ci(f"s13.diff.r{rg}.burst.P2_minus_P1b.reach30_critical", 3),
                     r.ci(f"s13.diff.r{rg}.steady.P2_minus_P1b.reach10_critical", 3), "improves" if r.has(f"s13.decision.r{rg}.sct_improves_on_spaced_table") and r.v(f"s13.decision.r{rg}.sct_improves_on_spaced_table") == 1 else "does not improve"])
    a(table(["Range", "Burst: P1b minus P1, within 10 s", "within 30 s", "Burst: P2 minus P1b, within 10 s", "within 30 s", "Steady: P2 minus P1b, within 10 s", "Decision rule"], rows))

    # ---------------------------------------------------------------- Part C
    a("#### N27: bounded model check of the alert protocol (S12, Part C)\n")
    a("ANALYTICAL. A check of a model within stated bounds, not a proof of the firmware or of the reference code. TLC was NOT_RUN (the tool could not be fetched); the search is an explicit-state level-by-level search in Python. Bounds are in `docs/01_protocol/PROTOCOL_MODEL.md`.\n")
    d.tab("s12", "N27: properties checked (holds = no counterexample within the bounds)", "ANALYTICAL", "s12.*", "The design holds; strict anti-replay and unpersisted counters fail as expected")
    rows = []
    for bn, vn, lab in (("ATT", "design", "design, attacker bound"), ("ATT", "strict_anti_replay", "strict anti-replay, attacker bound"), ("REBB", "design", "design, base reboot"), ("REBB", "base_no_persistence", "base reboot without persistence"),
                        ("REBC", "design", "design, car reboot"), ("REBC", "car_no_persistence", "car reboot without persistence"), ("LIVE", "design", "design, liveness"), ("LIVE", "strict_anti_replay", "strict anti-replay, liveness")):
        p = f"s12.{bn}.{vn}"
        rows.append([lab, r.i(p + ".states")] + [_flag(r, f"{p}.{pr}") for pr in ("S1_replay_or_forgery_accepted_as_new", "S2_spoofed_ack_stops_retries", "S3_repeat_not_acked_or_budget_exceeded", "S4_accepted_counters_not_increasing",
                                                                                 "L1_no_ack_in_terminal_state", "C1_cancel_without_valid_signature", "C2_send_after_valid_ack", "L1b_legit_new_event_rejected_as_replay")])
    a(table(["Variant and bounds", "States", "S1 replay or forgery", "S2 spoofed ACK", "S3 repeat re-ACK, budget", "S4 counters increase", "L1 liveness", "C1 CANCEL signature", "C2 send after ACK", "L1b new event refused"], rows))
    a(f"Cross-check: {r.i('s12.crosscheck.agree')} of {r.i('s12.crosscheck.cases')} mapped attack cases give the same decision in the model as in the reference verifier; the one disagreement is an abstraction gap (the model has no event id).\n")

    # ---------------------------------------------------------------- negative results
    a("#### Negative results of round 3\n")
    d.tab("neg", "Results that did not clear their interval or that went against the idea", "MEASURED_SOFTWARE / SIMULATED", "n20c.*, s9.*, s10.*, s11.*, s4.*", "Reported with the same detail as the positive results")
    rows = [["N20", "the false-alarm guarantee does not hold at alpha `5%`, with or without duplicates", r.ci("n20c.clean.a5.nall.conformal.fa_mean", 4)],
            ["N24", "the class rule on conformal delta-V intervals raises under-estimation", r.ci("n24.r16.nom90.under_drop", 3)],
            ["N25", "no threshold rule raises precision within five points of recall at low prevalence", r.f("s10.rf15.pi0p02pct.b_known.d_recall_vs_a", 3)],
            ["N14", "M+ capped does not change fill + ridge at +-16 g", r.f("n14s.cap.R.r16.paired.Mpc_vs_Mp.d_p90", 3)],
            ["N26", "SCT is not better than the table in steady state and is worse for a single car at high loss", r.ci("s11.diff.r16.steady.P2_minus_P1.reach10_critical", 3)],
            ["N28", "UA-SCT adds little critical delivery over SCT and many escalations", r.ci("s11.diff.r16.burst.P3_minus_P2.reach30_critical", 3)]]
    a(table(["Point", "Result", "Number"], rows))
