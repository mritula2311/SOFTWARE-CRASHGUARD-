"""Report subsection 4.10: the extra software-only experiments X1 to X7 (N17 to N23). Every number goes through the ``Res`` helpers (results.json); hand-typed numbers are only inside backticks."""
from __future__ import annotations

from crashguard.report import Doc, Res, table


def extra_intro(r: Res, d: Doc) -> None:
    d.a("### 4.10 Extra software-only experiments (N17 to N23)\n")
    d.a("Seven experiments were added after the main results. Each was written down with its baseline, split, metrics and decision rule in `docs/02_preregistration/EXPERIMENTS_EXTRA.md` before it was run, and each is judged only by whether its gain clears the 95% bootstrap interval on data it was not tuned on. "
        "NHTSA experiments resample whole vehicle groups (make and model); VZCrash experiments use the de-duplicated splits. A null result is reported with the same detail as a success. "
        "Everything is software only; none of it is a hardware result.\n")


def x1_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N17. Impact direction from one IMU on real crash tests (X1)\n")
    a(f"The firmware rule sums the horizontal acceleration over the initial {r.i('x1.A.window_chosen_ms')} ms after the trigger and takes the impact direction opposite to the impulse. "
      f"The database offers only frontal barrier tests ({r.i('x1.n_tests.frontal.front')}), left-side impactor tests ({r.i('x1.n_tests.side.side')}) and {r.i('x1.n_tests.oblique.front')} oblique frontal tests with instrumentation: "
      "rear impacts have no instrumentation records and every side test strikes the left side, so **rear and right are not scored**, the oblique angle is not scored (fewer than `10` tests), and the left-against-right decision is not independent because the sign of the lateral axis is calibrated on the left-side tests. "
      f"Sign check on the raw records: the mean longitudinal acceleration over the initial 100 ms is negative in {r.f('x1.axis.frontal_share_negative_x', 2)} of the {r.i('x1.axis.n_frontal')} frontal tests (median {r.f('x1.axis.frontal_mean_x_median', 1)} g), so the longitudinal axis points forward; "
      f"in the left-side tests the lateral mean is positive (median {r.f('x1.axis.side_mean_y_median', 1)} g, negative in only {r.f('x1.axis.side_share_negative_y', 2)} of them), so the data's lateral axis points right and is flipped. "
      f"The window was chosen on the tuning groups (make and model): {r.f('x1.A.window_tuning_correct.w30', 1)}, {r.f('x1.A.window_tuning_correct.w60', 1)} and {r.f('x1.A.window_tuning_correct.w100', 1)} correct tuning tests for `30`, `60` and `100` ms, so the `60` ms default stays (the rule needs a gain of more than one test).\n")
    d.tab("x1_main", "X1: front against side (sign-free) on the held-out vehicle groups, by sensor range", "MEASURED_SOFTWARE", "x1.*", "Front against side is recovered; the interval and the majority baseline are shown")
    rows = []
    for sp, nm in (("A", "make and model groups"), ("G", "make, model and year groups")):
        for rg in (16, 32, 64):
            p = f"x1.{sp}.r{rg}"
            ang_f = r.ci(f"{p}.angle_err.frontal.median_deg", 1) if r.has(f"{p}.angle_err.frontal.median_deg") else "n/a"
            ang_s = r.ci(f"{p}.angle_err.side.median_deg", 1) if r.has(f"{p}.angle_err.side.median_deg") else "n/a"
            rows.append([nm, f"±{rg} g", f"{r.i(p + '.n_front')} / {r.i(p + '.n_side')}", r.ci(f"{p}.front.acc", 3), r.f(f"{p}.front.acc_exact_lo", 3), r.ci(f"{p}.side.acc", 3), r.f(f"{p}.side.acc_exact_lo", 3), r.ci(f"{p}.balanced_acc", 3),
                         r.f(f"{p}.baseline_balanced_acc", 2), ang_f, ang_s])
    a(table(["Split", "Range", "Held-out front / side tests", "Front accuracy [grouped 95%]", "Exact lower limit", "Side accuracy [grouped 95%]", "Exact lower limit", "Balanced accuracy [grouped 95%]", "Majority baseline", "Median angle error, frontal (deg)",
             "Median angle error, side (deg)"], rows))
    a("The grouped interval is degenerate when a class has no errors, so the exact binomial lower limit (which ignores grouping) is shown next to it. "
      f"On the make-and-model split the balanced accuracy at ±16 g is {r.ci('x1.A.r16.balanced_acc', 3)} against `0.5` for the majority class: **supported** as a check of a supporting feature, on two classes only. "
      f"The one error at every range is test {r.i('x1.A.r16.failure1.test_no')} ({r.text('x1.A.r16.failure1.make_model')}, a side test whose impulse direction is {r.f('x1.A.r16.failure1.theta_deg', 1)} degrees); in the earlier N14 failure list it is also a short, high-peak pulse. "
      "Principal direction of force from in-vehicle accelerometers is an established topic (Kusano and Gabler; Tadic and Vukajlovic), so N17 is worded as validation of a supporting feature, not a contribution.\n")


def x2_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N18. Severity measures against dummy injury measures (X2)\n")
    a("The criteria are the dummy measurements stored with the NHTSA tests (field meanings from the NHTSA Biomechanics Data Reference Guide, opened). **They are test measurements, not human injury, and the samples are small.** "
      f"Frontal tests with criteria at the driver position: {r.i('x2.avail.frontal.pos01.hic')} with HIC, {r.i('x2.avail.frontal.pos01.clip3m')} with chest acceleration, {r.i('x2.avail.frontal.pos01.femur')} with femur load; side tests at the struck-side front seat: {r.i('x2.avail.side.pos01.hic')} with HIC, "
      f"{r.i('x2.avail.side.pos01.tti')} with TTI(d), {r.i('x2.avail.side.pos01.pelvg')} with the pelvis measure. The list of tests per criterion is in `docs/05_data_code/DATASET.md`. "
      f"Only {r.f('x2.hic.share_window_le_15ms.frontal', 2)} of the frontal dummy records have a HIC interval of at most 15 ms, so most frontal HIC values are not HIC15 and the HIC15 limit is not applied to them.\n")
    d.tab("x2_corr", "X2: Spearman correlation of severity measures with dummy criteria at the driver or struck-side front seat (reference chain), and partial correlation controlling for impact speed (95% intervals over make-and-model groups)", "MEASURED_SOFTWARE", "x2.*",
          "ASI tracks chest acceleration; delta-V adds nothing beyond speed in frontal tests")
    rows = []
    cells = (("frontal", "hic", "HIC"), ("frontal", "clip3m", "chest acceleration (3 ms)"), ("frontal", "femur", "femur load"), ("frontal", "csi", "CSI"), ("side", "hic", "HIC"), ("side", "tti", "TTI(d)"), ("side", "pelvg", "pelvis acceleration"))
    for kind, crit_, cname in cells:
        for sv, sn in (("dv", "delta-V"), ("asi", "ASI"), ("peakp", "peak acceleration"), ("energy", "specific energy"), ("speed", "impact speed")):
            p = f"x2.{kind}.pos01.{crit_}.{'speed' if sv == 'speed' else 'orig'}.{sv}"
            if r.has(p + ".rho"):
                part = r.ci(p + ".partial", 2) if sv != "speed" and r.has(p + ".partial") else "-"
                rows.append([kind, cname, sn, r.i(p + ".n"), r.ci(p + ".rho", 2), part])
    a(table(["Tests", "Criterion", "Severity measure", "n", "Spearman rho [95%]", "Partial rho controlling for speed [95%]"], rows))
    a(f"Delta-V against impact speed alone: frontal {r.ci('x2.frontal.dv_vs_speed.orig.rho', 2)}, side {r.ci('x2.side.dv_vs_speed.orig.rho', 2)} (side tests are all at about the same speed). "
      f"**Primary question (frontal, driver position, delta-V and chest or head criterion, controlling for speed):** the partial correlation of delta-V is {r.ci('x2.frontal.pos01.hic.orig.dv.partial', 2)} for HIC and {r.ci('x2.frontal.pos01.clip3m.orig.dv.partial', 2)} for chest acceleration: "
      "no interval is above zero, so **delta-V adds nothing beyond impact speed for these criteria: no improvement found**. "
      f"ASI, which is built from acceleration, does track chest acceleration ({r.ci('x2.frontal.pos01.clip3m.orig.asi.rho', 2)}; partial {r.ci('x2.frontal.pos01.clip3m.orig.asi.partial', 2)}). "
      f"In side tests delta-V is related to HIC ({r.ci('x2.side.pos01.hic.orig.dv.partial', 2)} partial), TTI(d) ({r.ci('x2.side.pos01.tti.orig.dv.partial', 2)}) and the pelvis measure ({r.ci('x2.side.pos01.pelvg.orig.dv.partial', 2)}).\n")
    d.tab("x2_limits", "X2: share of tests above a regulatory limit, by severity class of the reference chain", "MEASURED_SOFTWARE", "x2.limit.*", "Few tests exceed any limit, so the classes cannot be separated by limit exceedance")
    rows = []
    for kind, crit_, label in (("frontal", "clip3m", "chest acceleration above `60` g (FMVSS 208 S6.3)"), ("frontal", "femur", "femur load above `10,008` N (`2250` pounds, FMVSS 208 S6.5)"), ("side", "hic", "HIC (36 ms) above `1000` (FMVSS 214, ES-2re limit applied to the NHTSA dummy)")):
        for k, cn in enumerate(("Low", "Moderate", "Severe", "Critical")):
            if r.has(f"x2.limit.{kind}.{crit_}.class{k}.n") and int(r.v(f"x2.limit.{kind}.{crit_}.class{k}.n")) > 0:
                share = r.ci(f"x2.limit.{kind}.{crit_}.class{k}.share", 3) if r.has(f"x2.limit.{kind}.{crit_}.class{k}.share") else "too few tests"
                rows.append([label, cn, r.i(f"x2.limit.{kind}.{crit_}.class{k}.n"), share])
    a(table(["Limit", "Severity class", "Tests", "Share above the limit [95%]"], rows))
    a("The limits come from the text of 49 CFR 571.208 and 571.214 (opened). The TTI(d) and pelvis limits of the older side-impact dummy are not in the current text of FMVSS 214 and are **UNVERIFIED**, so no share against them is computed. "
      "The frontal HIC15 limit is not applied because almost none of the frontal HIC records has a 15 ms interval. Almost no test exceeds a limit (these are mostly star-rated tests at 56 to 62 km/h), so the class limits of the severity scale cannot be checked against the criteria with this sample.\n")


def x3_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N19. Early classification: how much of the 1.8 s window is needed (X3)\n")
    a("The deployed forest was trained at post-trigger lengths of `50`, `100`, `200`, `400`, `800` and `1,800` ms (features recomputed). An early-exit rule decides at the earliest checkpoint where the length-specific model is very confident (alarm above `hi`, no alarm below `lo`) and otherwise waits; "
      "`hi`, `lo` and the final threshold were chosen on validation only. System level, de-duplicated test set; the trigger is the same second trigger as elsewhere.\n")
    d.tab("x3_main", "X3: system recall at a fixed false-alarm rate for fixed windows and for the early-exit rule (mean ± std over seeds 0 to 4)", "MEASURED_SOFTWARE", "x3.*", "Most of the recall is there after 50 to 100 ms; the early-exit rule keeps it and decides sooner")
    rows = []
    for al, an in ((1, "1%"), (5, "5%")):
        for m in ("fixed_50", "fixed_100", "fixed_200", "fixed_400", "fixed_800", "fixed_1800", "early_exit"):
            p = f"x3.a{al}.{m}"
            tm = r.f(p + ".time_ms.mean", 0) if m != "early_exit" else f"{r.f(p + '.alarmed_time_ms.mean', 0)} (crashes that alarm); {r.f(p + '.time_ms.mean', 0)} (all triggered crashes)"
            rows.append([an, "early exit" if m == "early_exit" else m.replace("fixed_", "fixed window, post-trigger ms: "), r.ms(f"{p}.recall", 4), r.ms(f"{p}.fa", 4), tm])
    a(table(["False-alarm target", "Method", "System recall", "System false-alarm rate", "Decision time after the trigger (ms)"], rows))
    d.tab("x3_paired", "X3: early-exit rule minus the fixed 1,800 ms window (seed 42, paired bootstrap over test events)", "MEASURED_SOFTWARE", "x3.a*.paired.*", "The recall does not fall and the mean decision time falls by about a second")
    rows = []
    for al, an in ((1, "1%"), (5, "5%")):
        p = f"x3.a{al}.paired"
        ok = float(r.v(p + ".recall_diff_lo")) >= -0.01 and float(r.v(p + ".time_diff_ms_hi")) < 0
        rows.append([an, r.ci(p + ".recall_diff", 4), r.ci(p + ".time_diff_ms", 0), r.f(p + ".rule_a_hi", 4), r.f(p + ".rule_b_lo", 3), "supported" if ok else "not supported"])
    a(table(["False-alarm target", "Recall difference [95%]", "Mean decision time difference of crash events (ms) [95%]", "Chosen early-alarm level (validation false-alarm rate of the length-specific model)", "Chosen early no-alarm quantile", "Decision rule"], rows))
    a("**Reading.** The decision rule of `docs/02_preregistration/EXPERIMENTS_EXTRA.md` (decision time lower by an interval below zero and a recall loss of no more than one point) is met at both targets. "
      "Two cautions. One: the mean decision time of crash events includes crashes that are never alarmed and wait to the end; the time to alarm of the crashes that do alarm is shown in the table above. The other: the recall of the early-exit rule is slightly higher than the fixed window's because it combines six models; this is an ensemble effect, not a physical one. "
      "VZCrash events were pre-selected on the device, so these are decision times after a second trigger on pre-selected events, not for continuous driving.\n")
    a(f"**Cost on the node (ANALYTICAL).** Incremental feature updates need about {r.i('x3.mcu.mul')} multiplies, {r.i('x3.mcu.add')} additions, {r.i('x3.mcu.cmp')} comparisons and {r.i('x3.mcu.sqrt')} square roots per sample and {r.i('x3.mcu.state_bytes')} bytes of state (a `80` sample ring buffer dominates), plus {r.i('x3.mcu.forest_compares_per_checkpoint')} comparisons per checkpoint for the forest: "
      f"about {r.i('x3.mcu.cycles_per_sample_assumed')} cycles per sample at an ASSUMED cost per operation, {r.f('x3.mcu.share_of_sample_period', 5)} of the sample period at `240` MHz; the real cost is NOT_RUN. "
      f"**Effect on the end-to-end timing (SIMULATED, unconfirmed by hardware):** the alert is ready after {r.f('x3.timing.a5.mean_time_before_cancel_window_s.fixed', 2)} s (window plus assumed compute time) with the fixed window, and after {r.f('x3.timing.a1.mean_time_before_cancel_window_s.early', 2)} s (1% target) or {r.f('x3.timing.a5.mean_time_before_cancel_window_s.early', 2)} s (5% target) on average for the crashes that alarm, which would start the cancel window earlier by the difference.\n")


def x4_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N20. Guaranteed false-alarm control by split-conformal thresholds (X4)\n")
    a(f"The calibration set is the {r.i('x4.n_calibration_negatives')} non-crash validation events (system level); the test set has {r.i('x4.n_test_negatives')} non-crash events. The conformal threshold is the k-th smallest calibration score with k = ceil((n + 1)(1 - alpha)); "
      "the baseline is the validation threshold used so far. If calibration and test events are exchangeable the false-alarm rate is at most alpha on average over calibration sets. Calibration sets of `200` to `2,000` events were drawn `200` times per seed and size (seeds 0 to 4 and 42).\n")
    d.tab("x4_main", "X4: test false-alarm rate of the conformal and the validation thresholds, by calibration-set size (mean over seeds and draws, 95% interval for the mean)", "MEASURED_SOFTWARE", "x4.*", "Both thresholds give about the same false-alarm rate; both are above alpha on this test set")
    rows = []
    for al in (1, 5):
        for sz in ("200", "500", "1000", "2000", "all"):
            for meth in ("conformal", "validation"):
                p = f"x4.a{al}.n{sz}.{meth}"
                rows.append([f"{al}%", sz, meth, r.ci(p + ".fa_mean", 4), r.f(p + ".fa_p975", 4), r.f(p + ".share_exceeding_alpha", 2), r.f(p + ".recall_mean", 3)])
    a(table(["alpha", "Calibration events", "Threshold", "Test false-alarm rate: mean [95% for the mean]", "97.5th percentile of single draws", "Share of draws above alpha", "Test recall"], rows))
    a(f"**Result (decision rule: the interval for the mean must not be above alpha for calibration sets of `1,000` or more).** At alpha = `1%` the conformal mean is {r.ci('x4.a1.n1000.conformal.fa_mean', 4)} and at `5%` it is {r.ci('x4.a5.n1000.conformal.fa_mean', 4)}: both intervals are above alpha, so the guarantee is **not supported on this test set**. "
      f"The conformal threshold is not better than the validation threshold (recall difference at the same calibration sets about zero; for example {r.ci('x4.a5.nall.recall_diff_conformal_minus_validation', 4)} at `5%` with the whole validation set). The most likely cause is that validation and test events are not exchangeable here: the validation split may repeat training events (so validation scores are lower than test scores) and the de-duplicated test split has the cross-split duplicates removed. "
      "This is the explanation by elimination; it was not isolated.\n")
    d.tab("x4_shift", "X4: breaking exchangeability on purpose: calibrate on three vehicle-size categories and test on the fourth, and the reverse (false-alarm rate of the conformal threshold, mean over seeds)", "MEASURED_SOFTWARE", "x4.shift.*", "A size shift moves the false-alarm rate by several times alpha for heavy vehicles")
    rows = []
    for al in (1, 5):
        for cat in ("Light", "Medium", "Heavy", "Unknown"):
            loo = f"x4.shift.a{al}.leave_one_category_out.{cat}.conformal"
            single = f"x4.shift.a{al}.single_category_calibration.{cat}.conformal"
            rows.append([f"{al}%", cat, r.f(loo + ".fa_mean", 4) if r.has(loo + ".fa_mean") else "n/a", r.i(loo + ".n_test_neg") if r.has(loo + ".n_test_neg") else "n/a", r.f(single + ".fa_mean", 4) if r.has(single + ".fa_mean") else "n/a"])
    a(table(["alpha", "Category", "Calibrated on the other three, tested on this one", "Test non-crash events", "Calibrated on this one, tested on the other three"], rows))
    a("The false-alarm rate on heavy vehicles is more than twice alpha when the calibration set is made of the other categories, and the guarantee fails by a smaller amount in the other directions. The conformal threshold does not repair this; it needs exchangeability. N20 is reported as a limitation study: no improvement found.\n")
