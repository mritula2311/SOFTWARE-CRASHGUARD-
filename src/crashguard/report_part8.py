"""Report subsection: the closing block (T1 to T14). Numbers only through the ``Res`` helpers; hand-typed numbers only inside backticks."""
from __future__ import annotations

from crashguard.report import Doc, Res, table

RG = (16, 32, 64)


def _yn(r: Res, k: str) -> str:
    e = r.r.get(k)
    if e is None:
        r._miss(k)
        return "missing"
    return "yes" if e["value"] == 1 else "no"


def _p(r: Res, k: str) -> str:
    """p-value; the bootstrap floor is 0.002, so a printed zero is reported as below the floor."""
    if r.has(k) and r.v(k) == 0:
        return "below `0.002` (no resample crossed zero)"
    return r.f(k, 4)


def closing_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### Closing block: equal-escalation comparison, trade-off curves, costs, robustness and component evidence\n")
    a("The analyses T1 to T4, T6 and T8 were written down in `docs/02_preregistration/PREREGISTRATION.md` (Addendum 1) before they ran, after the main UA-SCT results had been seen (the addendum lists what had been seen). T5, T7 and T9 to T13 are EXPLORATORY. "
      "NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes. Every simulated value is an ASSUMPTION of the simulator; the duty limit is NOT verified for India.\n")

    # ---------------------------------------------------------------- T1
    a("#### T1: equal-escalation comparison\n")
    a("P1e and P2e use the point estimates of P1 and P2 with every class boundary divided by a factor f, chosen on the pooled held-out rows so that they send the same share of non-severe events to the fast path as P3. No simulated outcome was used to choose f.\n")
    d.tab("t1", "T1: P3 against the severity table with thresholds lowered to the same escalation (pool-level grouped bootstrap; simulated cells for delivery)", "MEASURED_SOFTWARE / SIMULATED", "t1.*", "P3 does not win at equal escalation")
    rows = []
    for rg in RG:
        rows.append([f"+-{rg} g", r.f(f"t1.r{rg}.f", 3), r.f(f"t1.r{rg}.escalation_p3", 3), r.f(f"t1.r{rg}.escalation_equal", 3), r.ci(f"t1.r{rg}.mis_triage_p1e", 3), r.ci(f"t1.r{rg}.mis_triage_p3", 3), r.ci(f"t1.r{rg}.mis_triage_p3_minus_p1e", 3),
                     r.ci(f"t1.r{rg}.steady.P3_minus_P2e.reach10_critical", 3), r.ci(f"t1.r{rg}.burst.P3_minus_P2e.reach10_critical", 3), r.ci(f"t1.r{rg}.burst.P3_minus_P2e.reach30_critical", 3), _yn(r, f"t1.r{rg}.decision.p3_wins_at_equal_escalation")])
    a(table(["Range", "Factor f", "Escalation P3", "Escalation P1e and P2e", "Mis-triage P1e [95%]", "Mis-triage P3 [95%]", "P3 minus P1e [95%]", "Steady: reach within 10 s, P3 minus P2e [95%]", "Burst: reach within 10 s [95%]", "Burst: within 30 s [95%]", "P3 wins at equal escalation"], rows))
    a("Plainly: at equal escalation P3 does not lower mis-triage beyond what lowering the thresholds of the plain table does (at `+-32` g and `+-64` g the lowered table is at or below P3), and delivery is the same within the intervals. The preregistered rule is not met at any range. "
      f"The earlier statement that P3 lowers mis-triage against P1 is true only because P3 escalates many more events: at `+-16` g the table with the current thresholds escalates {r.f('t1.r16.escalation_p1', 3)} of the non-severe events and P3 escalates {r.f('t1.r16.escalation_p3', 3)}; "
      f"at `+-32` g the table escalates {r.f('t1.r32.escalation_p1', 3)} and P3 {r.f('t1.r32.escalation_p3', 3)}.\n")

    # ---------------------------------------------------------------- T2
    a("#### T2: trade-off curves\n")
    d.tab("t2", "T2: area under the mis-triage against escalation curve (lower is better), by family and range, with the matched-escalation comparison at `+-16` g (EXPLORATORY)", "MEASURED_SOFTWARE", "t2.*", "The interval family does not dominate the point-class family")
    rows = []
    for rg in RG:
        rows.append([f"+-{rg} g", r.ci(f"t2.r{rg}.point.auc", 4), r.ci(f"t2.r{rg}.interval.auc", 4), r.ci(f"t2.r{rg}.auc_interval_minus_point", 4)])
    a(table(["Range", "Point-class family (P0, P1, P2) [95%]", "Interval family (P3, P4) [95%]", "Interval minus point [95%]"], rows))
    rows = []
    for x in (20, 30, 40, 50, 60, 70):
        rows.append([f"`{x}%`", r.f(f"t2.r16.matched.x{x}.point.mis_triage", 3), r.f(f"t2.r16.matched.x{x}.interval.mis_triage", 3), r.ci(f"t2.r16.matched.x{x}.interval_minus_point", 3)])
    a(table(["Escalation", "Mis-triage, point-class family", "Mis-triage, interval family", "Interval minus point [95%] (EXPLORATORY)"], rows))
    a("The areas close each curve with the endpoints `(0, 1)` and `(1, 0)` as preregistered; the interval family cannot reach low escalation, which penalises it, so the matched-escalation table is given too. Figure: `results/figures/t2_pareto.png` (all grid points plotted, none selected).\n")

    # ---------------------------------------------------------------- T3
    a("#### T3: expected-cost view\n")
    d.tab("t3", "T3: break-even ratio C_u / C_o above which P3 costs less than P1 (grouped bootstrap), by range and share of Severe or Critical events", "MEASURED_SOFTWARE", "t3.*", "P3 pays only if a missed severe event costs several times a false escalation; no break-even against the equal-escalation table")
    rows = []
    for rg in RG:
        for tag, nm in (("0p1", "`0.1`"), ("0p3", "`0.3`"), ("obs", "observed"), ("0p9", "`0.9`")):
            rows.append([f"+-{rg} g", nm, r.ci(f"t3.r{rg}.s{tag}.break_even_ratio", 2)])
    a(table(["Range", "Share of true Severe or Critical events", "Break-even C_u / C_o [95%]"], rows))
    rows = []
    for t in ("0p1", "0p3", "1", "3", "10", "30", "100", "300", "1000"):
        k = f"t3.r16.sobs.ratio{t}"
        rows.append([f"`{t.replace('p', '.')}`", r.f(f"{k}.cost.P1", 3), r.f(f"{k}.cost.P3", 3), r.ci(f"{k}.cost_diff_p3_minus_p1", 3), r.ci(f"{k}.cost_diff_p3_minus_p1e", 3)])
    a(table(["C_u / C_o", "Cost P1 (also P0, P2)", "Cost P3 (also P4)", "P3 minus P1 [95%]", "P3 minus the equal-escalation table [95%]"], rows))
    a("Costs are per crash event in units of the over-triage cost at `+-16` g with the observed class mix (not representative of real traffic). Against the table with lowered thresholds, P3 is not shown to be cheaper at any ratio listed (every interval includes zero). At `+-64` g the upper end of the break-even interval is unbounded (shown as NOT_RUN): some resamples contain no mis-triage gain for P3 at all.\n")

    # ---------------------------------------------------------------- T4
    a("#### T4: two clarifications\n")
    a("**(a)** The S9 rule reports the class from the LOWER bound of a delta-V interval (the class below plus a flag); H-a uses the UPPER end of a class interval. Under-estimation is the share of rows whose reported class is below the true class; mis-triage is the share of true Severe or Critical rows assigned below Severe. They are different rules, so both statements hold.\n")
    d.tab("t4a", "T4: under-estimation and mis-triage under three rules, 90% level, by range (grouped bootstrap; per-class values are in `results.json`, keys `t4.a.*`)", "MEASURED_SOFTWARE", "t4.a.*", "The lower-bound rule under-estimates more; the upper end less; the point class in between")
    rows = []
    for rg in RG:
        for lab, k in (("point class", "point"), ("S9 rule, lower bound", "s9_lower_rule"), ("upper end of the class interval", "upper_end")):
            rows.append([f"+-{rg} g", lab, r.ci(f"t4.a.r{rg}.nom90.overall.under_all_classes.{k}", 3), r.ci(f"t4.a.r{rg}.nom90.overall.mis_triage.{k}", 3)])
    a(table(["Range", "Rule", "Under-estimation, any class [95%]", "Mis-triage [95%]"], rows))
    a("**(b)** Setup: one car, no collisions, `20` alerts per hour, SF`7`, duty limit `1%` (not verified for India), both directions lost with the stated probability, `40` seeds, class pool at `+-16` g.\n")
    d.tab("t4b", "T4: single car, critical reach within 10 s, by loss (SIMULATED) and the analytical expectation from the number of rounds that fit", "SIMULATED / ANALYTICAL", "t4.b.*", "The 5 s retry spacing is the cause of the weak result at high loss")
    rows = []
    for loss in (10, 30, 60):
        rows.append([f"`{loss}%`", r.ci(f"t4.b.loss{loss}.P1.reach10_critical", 3), r.ci(f"t4.b.loss{loss}.P2.reach10_critical", 3), r.ci(f"t4.b.loss{loss}.P2_quick.reach10_critical", 3), r.f(f"t4.b.analytic.loss{loss}.table_reach10", 3), r.f(f"t4.b.analytic.loss{loss}.sct_reach10", 3)])
    a(table(["Loss", "Table (P1) [95%]", "SCT (P2) [95%]", "SCT with quick retries, `0.3` s spacing (EXPLORATORY) [95%]", "Analytical, table", "Analytical, SCT"], rows))
    a("Cause: a round of SCT is a flash and an alert followed by a `5` s wait, so only about two rounds fit before `10` s; the table waits its `5` s cancel window and then retries every few tenths of a second. At `60%` loss a message and its ACK both get through in about one case in six, so more tries within the deadline win. Quick retries remove the weakness for a single car; whether they cost anything in bursts is tested in T9.\n")

    # ---------------------------------------------------------------- T5
    a("#### T5: near-duplicate sensitivity (EXPLORATORY)\n")
    a(f"Matching rule: a triggered test event is a near-duplicate if a train or validation window has correlation above `0.999` and maximum difference below `0.01` g with it (trigger-aligned, `2.8` s, `2` g trigger; the same ids are removed for every trigger level). Standard set: {r.i('t5.n_events.std')} events; strict set: {r.i('t5.n_events.strict')} events. The standard set stays primary.\n")
    d.tab("t5", "T5: standard test set against the set without window-level near-duplicates (5-seed means, validation-chosen operating points)", "MEASURED_SOFTWARE", "t5.*", "Near-duplicates inflate recall and AP; the N19 gain and the trigger results hold on both sets")
    rows = []
    for met, lab in (("recall_f1", "System recall, validation F1 threshold"), ("recall_t1", "Recall at the `1%` false-alarm target"), ("recall_t5", "Recall at the `5%` false-alarm target"), ("ap_model", "AP, triggered events"), ("ap_system", "System AP")):
        rows.append([lab, r.ci(f"t5.std.{met}", 4), r.ci(f"t5.strict.{met}", 4), r.ci(f"t5.diff_std_minus_strict.{met}", 4)])
    a(table(["Metric", "Standard set [95%]", "Strict set [95%]", "Difference [95%]"], rows))
    rows = []
    for an, nm in (("a1", "`1%`"), ("a5", "`5%`")):
        rows.append([nm, r.ci(f"t5.n19.std.{an}.recall_gain_ensemble", 4), r.ci(f"t5.n19.strict.{an}.recall_gain_ensemble", 4), r.ci(f"t5.n19.std.{an}.time_diff_ms", 0), r.ci(f"t5.n19.strict.{an}.time_diff_ms", 0)])
    a(table(["N19, target", "Recall gain, standard", "Recall gain, strict", "Decision time difference (ms), standard", "Decision time difference (ms), strict"], rows))
    rows = []
    for var, nm in (("trig_1.5", "`1.5` g"), ("trig_2", "`2` g"), ("trig_2.5", "`2.5` g"), ("trig_3", "`3` g")):
        rows.append([nm, r.f(f"t5.n9.{var}.std.crash_trigger_rate", 3), r.f(f"t5.n9.{var}.strict.crash_trigger_rate", 3), r.f(f"t5.n9.{var}.std.model_level_recall", 3), r.f(f"t5.n9.{var}.strict.model_level_recall", 3), r.f(f"t5.n9.{var}.std.system_recall", 3), r.f(f"t5.n9.{var}.strict.system_recall", 3)])
    a(table(["N9, trigger level", "Crash trigger rate, standard", "strict", "Model-level recall, standard", "strict", "System recall, standard", "strict"], rows))

    # ---------------------------------------------------------------- T6
    a("#### T6: severity-threshold sensitivity\n")
    d.tab("t6", "T6: H-a and H-c under shifted delta-V class limits (all limits together, and each limit alone, by `-2`, `-1`, `+1`, `+2` km/h)", "MEASURED_SOFTWARE", "t6.*", "H-a survives every setting; H-c fails for the largest downward shifts")
    rows = []
    for tag, nm in (("base", "none"), ("allm2", "all `-2`"), ("allm1", "all `-1`"), ("allp1", "all `+1`"), ("allp2", "all `+2`"), ("lowm2", "low `-2`"), ("lowm1", "low `-1`"), ("lowp1", "low `+1`"), ("lowp2", "low `+2`"),
                    ("midm2", "mid `-2`"), ("midm1", "mid `-1`"), ("midp1", "mid `+1`"), ("midp2", "mid `+2`"), ("highm2", "high `-2`"), ("highm1", "high `-1`"), ("highp1", "high `+1`"), ("highp2", "high `+2`")):
        rows.append([nm, f"`{r.text(f't6.{tag}.limits')}`", r.ci(f"t6.{tag}.r16.mis_triage_upper_minus_point", 3), _yn(r, f"t6.{tag}.H_a_survives"), r.ci(f"t6.{tag}.hc.reduction_16_minus_64", 3), _yn(r, f"t6.{tag}.H_c_survives")])
    a(table(["Shift", "Limits (km/h)", "Mis-triage, upper end minus point class, `+-16` g [95%]", "H-a survives", "Reduction at `+-16` g minus at `+-64` g [95%]", "H-c survives"], rows))
    a(f"A delta-V severity scale from an opened source was not available (candidate pages returned an access error), so that setting is {r.text('t6.external_scale')[:12]}. "
      "The mis-triage gain of the upper end over the point class (H-a) keeps its sign and interval in all `17` settings. The larger gain at `+-16` g than at `+-64` g (H-c) loses its interval when all limits move down by `2` km/h and when only the middle limit moves down by `2` km/h; it keeps it in the other `15` settings.\n")

    # ---------------------------------------------------------------- T7
    a("#### T7: conformal variants (EXPLORATORY)\n")
    d.tab("t7a", "T7: class intervals at the `90%` level: the current pooled split-conformal intervals against group-wise calibration by test kind, a one-class margin and class-conditional intervals", "MEASURED_SOFTWARE", "t7.a.*", "Every variant covers above the nominal level; the margin and group-wise variants buy coverage with escalation")
    rows = []
    for rg in RG:
        for nm, lab in (("current_pooled", "current (pooled)"), ("kind_groupwise", "group-wise by test kind"), ("widened_plus1", "margin of one class"), ("class_conditional", "class-conditional")):
            rows.append([f"+-{rg} g", lab, r.ci(f"t7.a.r{rg}.{nm}.coverage", 3), r.f(f"t7.a.r{rg}.{nm}.width", 2), r.f(f"t7.a.r{rg}.{nm}.mis_triage", 3), r.f(f"t7.a.r{rg}.{nm}.escalation", 3)])
    a(table(["Range", "Variant", "Coverage on held-out vehicles [95%]", "Mean width (classes)", "Mis-triage", "Escalation"], rows))
    d.tab("t7b", "T7: the N20 false-alarm guarantee with conformal variants (clean calibration pool; test false-alarm rate, 95% bootstrap interval over test events)", "MEASURED_SOFTWARE", "t7.b.*", "No variant restores the guarantee at alpha `5%`")
    rows = []
    for al, an in ((1, "`1%`"), (5, "`5%`")):
        for nm, lab in (("current_pooled", "current (pooled)"), ("size_groupwise", "group-wise by vehicle size"), ("widened_margin", "widening margin"), ("class_conditional_oracle", "class-conditional (not deployable: needs the true class)")):
            rows.append([an, lab, r.ci(f"t7.b.a{al}.{nm}.fa_mean", 4), r.f(f"t7.b.a{al}.{nm}.recall", 3), _yn(r, f"t7.b.a{al}.{nm}.holds")])
    a(table(["alpha", "Variant", "False-alarm rate [95%]", "Recall", "Guarantee holds"], rows))
    a("The guarantee is said to hold if the upper end of the interval is at or below alpha plus one binomial standard error of the test negatives. No variant is shown to restore it at `5%`; the widening margin comes within one standard error of it, so for that variant the guarantee is not established rather than clearly broken.\n")

    # ---------------------------------------------------------------- T8
    a("#### T8: simulator assumption sweep for the UA-SCT policies\n")
    a(f"P0 to P4 at `+-16` g, one factor at a time from the default; {r.i('t8.runs')} runs, {r.i('t8.seeds_per_cell')} paired seeds per cell, runs above the duty limit: {r.i('t8.duty.runs_exceeding_limit')}. A policy beats another in a cell for a metric only if the whole paired interval is on the favourable side.\n")
    d.tab("t8", "T8: cells in which P3 beats, ties or loses against P1 and P2", "SIMULATED", "t8.count.*", "P3 beats P1 on delivery within 10 s in bursts and loses in steady cells at high loss; against P2 it adds a little within 10 s and loses a little within 30 s in bursts")
    rows = []
    for base in ("P1", "P2"):
        for met, lab in (("reach10_critical", "reach within 10 s"), ("reach30_critical", "reach within 30 s"), ("mis_triage", "mis-triage")):
            p = f"t8.count.P3_vs_{base}.{met}"
            rows.append([base, lab, r.i(p + ".n_beats"), r.i(p + ".n_tie"), r.i(p + ".n_loses"), r.i(p + ".n_cells"), r.text(p + ".cells_not_beating")])
    a(table(["Baseline", "Metric", "P3 beats", "Tie", "P3 loses", "Cells", "Cells where P3 does not beat the baseline"], rows))
    a("Reading the cells in `results.json` (keys `t8.diff.*`): against P1, P3 gains `0.10` to `0.36` in critical reach within 10 s in the burst cells and loses in the steady cells with `40%` and `60%` loss (`-0.09` and `-0.26`; the spaced retries of the SCT cost a single car at high loss, as T4 explained). "
      "Against P2, the gain within 10 s is small (at most `0.064`) and the loss within 30 s in six burst cells is small (at most `0.040`). The mis-triage difference in this table is the class-level difference of P3 and P1 and is the one T1 shows to come from escalation.\n")

    # ---------------------------------------------------------------- T9
    a("#### T9: ablations of the SCT components (EXPLORATORY)\n")
    d.tab("t9", "T9: change in critical reach within 10 s when one SCT part is changed (P2, variant minus full SCT, paired by seed, 95% interval). For the five removals a negative value means the part helps; for quick retries (a change that adds a faster retry spacing, not a removal) a negative value means the change lowers reach", "SIMULATED", "t9.diff.*", "Flash and hold matter most; the reserve and the CANCEL message show no effect on reach; quick retries cost reach in bursts")
    rows = []
    for cell, cn in (("steady_base", "steady"), ("burst_base", "burst of 30"), ("burst_b60", "burst of 60"), ("burst_sf9", "burst, SF9"), ("burst_loss30", "burst, loss `30%`"), ("steady_fa5", "steady with false alarms at the `5%` target")):
        row = [cn]
        for vn in ("no_flash", "no_hold", "no_reserve", "no_sf_raise", "no_cancel_msg", "quick_retries"):
            row.append(r.ci(f"t9.diff.{cell}.P2.{vn}_minus_full.reach10_critical", 3))
        rows.append(row)
    a(table(["Cell", "No flash [95%]", "No hold [95%]", "No reserve [95%]", "No SF raise [95%]", "No CANCEL message [95%]", "Quick retries, `0.3` s spacing [95%]"], rows))
    a("The same table for P3 is in `results.json` (keys `t9.diff.*.P3.*`); the signs agree. In these cells the reserved duty share never binds (removing it changes nothing, to the last digit) and the CANCEL message only matters where false alarms happen. "
      "Quick retries help a single car at high loss (T4) but, with many cars sharing the channel, they lower critical reach within `30` s; the weakness found in T4 is a trade-off, not a defect.\n")
    d.tab("t9b", "T9: transmissions of the CANCEL message and critical reach within 10 s with and without it, steady cell with false alarms (P2)", "SIMULATED", "t9.steady_fa5.*", "The CANCEL message costs a few transmissions per hour and its small gain in reach does not clear its interval")
    rows = []
    for vn, nm in (("full", "with CANCEL message"), ("no_cancel_msg", "without CANCEL message")):
        rows.append([nm, r.ci(f"t9.steady_fa5.P2.{vn}.cancel_tx", 2), r.ci(f"t9.steady_fa5.P2.{vn}.fa_tx_fast", 2), r.ci(f"t9.steady_fa5.P2.{vn}.reach10_critical", 4), r.ci(f"t9.steady_fa5.P2.{vn}.max_window_airtime_s", 2)])
    a(table(["Variant", "CANCEL transmissions per hour [95%]", "Fast-path transmissions for false alarms per hour [95%]", "Critical reach within 10 s [95%]", "Largest trailing-hour airtime (s) [95%]"], rows))

    # ---------------------------------------------------------------- T10
    a("#### T10: airtime and energy accounting (ANALYTICAL formulas; simulated counts; ASSUMED currents)\n")
    a(f"Assumptions (ours, not datasheet-verified): supply {r.f('t10.assumption.supply_v', 1)} V, transmit current {r.f('t10.assumption.i_tx_ma', 0)} mA, receive current {r.f('t10.assumption.i_rx_ma', 0)} mA while listening for an ACK, idle and sleep ignored. These are estimates, not measurements.\n")
    d.tab("t10a", "T10: time on air (s) by message and spreading factor (Semtech formula, `125` kHz, coding rate `4/5`)", "ANALYTICAL", "t10.airtime.*", "A flash takes about a quarter to a third of an alert's airtime")
    rows = []
    for sf in (7, 8, 9, 10, 11, 12):
        rows.append([f"SF{sf}", r.f(f"t10.airtime.sf{sf}.flash_cancel_s", 4), r.f(f"t10.airtime.sf{sf}.alert_s", 4), r.f(f"t10.airtime.sf{sf}.ack_s", 4), r.f(f"t10.airtime.sf{sf}.heartbeat16_s", 4), r.f(f"t10.listen_window.sf{sf}_s", 4)])
    a(table(["SF", "Flash or CANCEL (14 B)", "Alert (97 B)", "ACK (26 B)", "Heartbeat (16 B)", "Listen window per try"], rows))
    d.tab("t10b", "T10: transmit airtime and estimated energy per crash event, simulated counts at SF7 (default cells, +-16 g; ASSUMED currents)", "SIMULATED", "t10.sim.*", "In bursts SCT sends fewer transmissions and less airtime than the table; in the steady cell it sends one more message per event")
    rows = []
    for mode in ("steady", "burst"):
        for pol, nm in (("P0", "P0"), ("P1", "P1"), ("P2", "P2"), ("P3", "P3"), ("P4", "P4")):
            rows.append([mode, nm, r.f(f"t10.sim.{mode}.{pol}.tries_per_event", 2), r.f(f"t10.sim.{mode}.{pol}.airtime_per_event_s", 3), r.f(f"t10.sim.{mode}.{pol}.energy_per_event_mj", 1)])
    a(table(["Cell", "Policy", "Transmissions per event", "Airtime per event (s)", "Energy per event (mJ, estimate)"], rows))
    a(f"In the steady cell the SCT policies send about one more message per event than the table (the flash), at {r.f('t10.sim.steady.P2.airtime_per_event_s', 3)} s of airtime against {r.f('t10.sim.steady.P1.airtime_per_event_s', 3)} s. In the burst cell the SCT policies send fewer transmissions and less airtime than the table (P2: {r.f('t10.sim.burst.P2.airtime_per_event_s', 3)} s, P1: {r.f('t10.sim.burst.P1.airtime_per_event_s', 3)} s). "
      "Energy values multiply the airtime by the assumed transmit current and supply and add the listening window of the assumed receive current; they are estimates, not measurements.\n")

    # ---------------------------------------------------------------- T11
    a("#### T11: attack-suite review\n")
    a(f"The {r.i('attacks.cases_total')} original cases are listed by category in `docs/01_protocol/ATTACK_CASES.md` ({r.i('attacks.cases_matching_expected')} behave as expected). {r.i('attacks_x.cases_total')} additional DESIGNED TEST CASES (not independent attackers; expected outcomes fixed before the run) were added: counter wrap of the 16-bit flash counter, "
      f"a bounded brute force of the 8-byte tag ({r.i('attacks_x.brute_force.tries')} random tags, expected successes {r.sci('attacks_x.brute_force.expected_successes')}), late and old ACKs, duplicate and early CANCEL, a short-id collision, type confusion and a flash ACK shown to a node waiting for the alert; {r.i('attacks_x.cases_matching_expected')} behave as expected. "
      "Two of them document known weaknesses (CANCEL before its alert is refused; two nodes with the same short id refuse each other).\n")

    # ---------------------------------------------------------------- T12
    a("#### T12: model-check extension (ANALYTICAL)\n")
    d.tab("t12", "T12: flash and CANCEL properties of the bounded model (holds = no counterexample within the bounds; a check of the model, not of the implementation)", "ANALYTICAL", "s12x.*", "A CANCEL that overtakes its alert is lost in the design; remembering it fixes the model")
    rows = []
    for vn, nm in (("design", "design"), ("keep_pending_cancel", "CANCEL remembered")):
        rows.append([nm, r.i(f"s12x.EXT.{vn}.states")] + [("holds" if r.has(f"s12x.EXT.{vn}.{p}") and r.v(f"s12x.EXT.{vn}.{p}") == 1 else "**FAILS**") for p in ("S1_replay_or_forgery_accepted_as_new", "S2_spoofed_ack_stops_retries", "S3_repeat_not_acked_or_budget_exceeded",
                                                                                                                                         "S4_accepted_counters_not_increasing", "C1_cancel_without_valid_signature", "C2_send_after_valid_ack",
                                                                                                                                         "C3_cancel_lost_by_reordering", "C4_late_ack_restarts_sending", "F1_flash_ack_stops_alert_retries")])
    a(table(["Variant", "States", "S1", "S2", "S3", "S4", "C1", "C2", "C3 CANCEL lost by reordering", "C4 late ACK restarts sending", "F1 flash ACK ends retries"], rows))

    # ---------------------------------------------------------------- T13 / T14
    a("#### T13: a second public dataset\n")
    a(f"{r.text('t13.second_dataset.analysis')}. Reason: no candidate dataset could be opened in this environment, so the finding was not repeated on a second source (see `results.json`, key `t13.second_dataset.analysis`).\n")
    a("#### T14: statistics audit\n")
    d.tab("t14", "T14: the preregistered hypotheses with Holm correction (grouped-bootstrap p-values, 1,000 resamples, so the smallest p-value that can be shown is `0.002`)", "MEASURED_SOFTWARE", "t14.*", "H-a, H-b and H-c survive the correction; all other intervals are uncorrected and exploratory where marked")
    rows = []
    for h in ("H-a", "H-b", "H-c"):
        rows.append([h, _p(r, f"t14.{h}.p_raw"), _p(r, f"t14.{h}.p_holm"), _yn(r, f"t14.{h}.survives_correction")])
    a(table(["Hypothesis", "Raw p", "Holm-adjusted p", "Survives"], rows))
    a("The families of comparisons, their tests and intervals, and the table of post-hoc choices are in `docs/03_results/STATS_AUDIT.md`.\n")
