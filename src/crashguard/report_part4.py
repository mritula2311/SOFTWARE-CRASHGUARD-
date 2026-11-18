"""Report additions from Part 0B and Part 1: N14 against spline restoration (four splits), precision at lower prevalence, and the extra experiments X1 to X7.

Every number goes through the ``Res`` helpers (results.json); numbers typed by hand are only inside backticks.
"""
from __future__ import annotations

from crashguard.report import Doc, Res, table

SPLITS = (("O", "O. original test-number split (held-out tests)"), ("G", "G. grouped by make, model and year (held-out groups)"), ("A", "A. grouped by make and model only (held-out groups)"),
          ("R", "R. repeated grouped cross-validation (5 folds x 10 repeats, all tests out-of-fold)"))
METH = (("B", "plain"), ("SP", "spline restoration"), ("M", "fill"), ("M+", "fill + ridge"))


def n14_extension(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N14 against spline restoration, on four splits\n")
    a("Spline restoration of clipped acceleration (Ruder et al.; tested by Chan et al. (`2023`), opened) is the closest method, so it is the baseline N14 has to beat. It is defined in `docs/02_preregistration/ALGORITHMS.md` (N14 extension, written before the run): "
      "a 5th-order spline through 3 clean samples on each side of every clipped segment of the horizontal axes, no change where fewer than 3 clean samples exist on a side. Its saturation level "
      f"({r.f('n14x.combo.spline_level', 1)} of the range) was chosen on the tuning tests of split G with the same rule as the fill's level. **No result in this subsection is a blind test.** "
      f"The grouped held-out set of split G ({r.i('n14x.G.n_tests_heldout')} tests in {r.i('n14x.G.n_groups_heldout')} groups; tuning {r.i('n14x.G.n_tests_tuning')} tests in {r.i('n14x.G.n_groups_tuning')} groups) had already been seen in the earlier N14 and release-rule results, "
      "so its numbers are called stable under re-splitting. Splits O and A reuse the settings chosen on the tuning tests of G (only the ridge is fitted again), and "
      f"{r.i('n14x.overlap.A_heldout_in_G_tuning_tests')} of the {r.i('n14x.A.n_tests_heldout')} held-out tests of split A and {r.i('n14x.overlap.O_heldout_in_G_tuning_tests')} of the {r.i('n14x.O.n_tests_heldout')} of split O were tuning tests of G. "
      f"Only split R repeats every choice inside the folds ({r.i('n14x.R.n_groups')} make-and-model groups). Split A has {r.i('n14x.A.n_groups_heldout')} held-out groups ({r.i('n14x.A.n_tests_heldout')} tests) and {r.i('n14x.A.n_groups_tuning')} tuning groups ({r.i('n14x.A.n_tests_tuning')} tests). "
      "Intervals resample whole vehicle groups. The primary method for this comparison, set before the run, is fill + ridge; the earlier text named no single primary variant (a fact stated in `docs/02_preregistration/ALGORITHMS.md`).\n")
    d.tab("n14x_methods", "N14 extension: delta-V error of plain integration, spline restoration, fill and fill + ridge on four splits (95% intervals resample vehicle groups)", "MEASURED_SOFTWARE", "n14x.*",
          "The four methods side by side at each range and split")
    rows = []
    for sp, _spn in SPLITS:
        for rg in (16, 32, 64):
            for m, mn in METH:
                p = f"n14x.{sp}.r{rg}.{m}"
                rows.append([sp, f"±{rg} g", mn, f"{r.i(p + '.n')} / {r.i(p + '.n_groups')}", r.ci(f"{p}.median", 1), r.ci(f"{p}.p90", 1), r.f(f"{p}.w10", 2), r.f(f"{p}.w20", 2)])
    a(table(["Split", "Range", "Method", "Tests / groups", "Median absolute error (%) [95%]", "90th percentile (%) [95%]", "Within ±10%", "Within ±20%"], rows))
    a("Split names: " + "; ".join(n for _k, n in SPLITS) + ". Split R pools every test once per repeat and averages over the 10 repeats; its interval is a bootstrap over groups of that repeat-averaged median.\n")
    d.tab("n14x_paired", "N14 extension: paired differences (method minus reference) in median absolute delta-V error, in points, with 95% intervals over vehicle groups", "MEASURED_SOFTWARE", "n14x.*.paired.*",
          "Fill + ridge against spline restoration and against plain integration at each range and split")
    rows = []
    for sp, _n in SPLITS:
        for rg in (16, 32, 64):
            for pair, pn in (("M+_vs_SP", "fill + ridge minus spline"), ("M_vs_SP", "fill minus spline"), ("M+_vs_B", "fill + ridge minus plain"), ("SP_vs_B", "spline minus plain")):
                p = f"n14x.{sp}.r{rg}.paired.{pair}"
                ok = r.v(p + ".clears") == 1 if r.has(p + ".clears") else False
                rows.append([sp, f"±{rg} g", pn, r.ci(f"{p}.d_median", 1), r.ci(f"{p}.d_w10", 2), "whole interval below zero" if ok else "interval reaches zero"])
    a(table(["Split", "Range", "Comparison", "Difference in median error (points) [95%]", "Difference in share within ±10% [95%]", "Median difference"], rows))
    ok16 = all(r.has(f"n14x.{sp}.r16.paired.M+_vs_SP.clears") and r.v(f"n14x.{sp}.r16.paired.M+_vs_SP.clears") == 1 and r.v(f"n14x.{sp}.r16.paired.M+_vs_B.clears") == 1 for sp in ("O", "G", "A", "R"))
    a("**Result by the rule fixed in advance** (fill + ridge counts as an improvement at a range only where its whole interval is below zero against BOTH spline restoration and plain integration). "
      + (f"At ±16 g it holds on all four splits: in repeated grouped cross-validation the median error is {r.f('n14x.R.r16.B.median', 1)}% for plain integration, {r.f('n14x.R.r16.SP.median', 1)}% for spline restoration and {r.f('n14x.R.r16.M+.median', 1)}% for fill + ridge; "
         f"fill + ridge minus spline is {r.ci('n14x.R.r16.paired.M+_vs_SP.d_median', 1)} points. " if ok16 else "At ±16 g it does not hold on every split (see the table). ")
      + f"Spline restoration alone gives a small gain over plain integration at ±16 g that clears zero only in the cross-validation ({r.ci('n14x.R.r16.paired.SP_vs_B.d_median', 1)} points). "
      f"The fill alone also beats spline restoration at ±16 g ({r.ci('n14x.R.r16.paired.M_vs_SP.d_median', 1)} points in cross-validation). "
      f"**At ±32 g: no improvement found** on the three fixed splits (fill + ridge minus plain, upper limits {r.f('n14x.O.r32.paired.M+_vs_B.d_median_hi', 1)}, {r.f('n14x.G.r32.paired.M+_vs_B.d_median_hi', 1)} and {r.f('n14x.A.r32.paired.M+_vs_B.d_median_hi', 1)} points); "
      f"in cross-validation the interval against plain integration only just reaches below zero ({r.ci('n14x.R.r32.paired.M+_vs_B.d_median', 2)}) and against spline restoration it does not ({r.ci('n14x.R.r32.paired.M+_vs_SP.d_median', 2)}). "
      f"**At ±64 g: no improvement found** (almost no pulse saturates; on the fixed splits the methods give identical estimates; in cross-validation the difference from spline restoration is {r.ci('n14x.R.r64.paired.M+_vs_SP.d_median', 2)} points, too small to matter).\n")
    a(f"**What the tables also show.** The 90th-percentile error is not reduced at ±16 g: {r.f('n14x.R.r16.B.p90', 1)}% for plain integration against {r.f('n14x.R.r16.M+.p90', 1)}% for fill + ridge in cross-validation (split G held-out: {r.f('n14x.G.r16.B.p90', 1)}% against {r.f('n14x.G.r16.M+.p90', 1)}%), "
      f"so the gain is in the typical test and the large errors get worse, because the ridge correction multiplies a few estimates too far. Fill + ridge is within ±10% on {r.f('n14x.R.r16.M+.w10', 2)} of tests in cross-validation; this is far below a usable severity sensor, and a wider-range part still works better. "
      f"In cross-validation the choices most often made inside the folds were the {r.text('n14x.R.choice_most_common.M_family')} pulse, saturation level {r.f('n14x.R.choice_most_common.M_level', 1)} and release fraction {r.f('n14x.R.choice_most_common.M_rf', 1)}, the same as the settings fixed earlier.\n")
    a("**Wording for N14.** Fill + ridge is not claimed as a method that beats spline restoration in general. The supported statement is: at ±16 g and 100 Hz, on a software sensor model fed with crash-test records, a pulse-fit fill with a small ridge correction lowers the median delta-V error against plain integration and against spline restoration on four splits of the NHTSA tests, "
      "and gives no improvement at ±32 g or ±64 g; the tail is not improved. It is a comparison of clipping-restoration methods at low sensor range.\n")
    hdr = ["NHTSA test", "Make", "Model", "Test type", "Peak after the 260 Hz front end (g)", "Raw peak (g)", "Absolute error (%)", "Share of pulse samples at or above the saturation level"]
    for key, title, nm, claim in (("n14x_failure", "N14 extension: the ten tests with the largest delta-V error after fill + ridge at ±16 g, in repeated grouped cross-validation (error averaged over the 10 repeats)", "R_cv",
                                   "Large errors come from short pulses and from side tests"),
                                  ("n14x_failure_g", "N14 extension: the ten largest errors after fill + ridge at ±16 g on the held-out tests of split G", "G_heldout", "Same kind of tests as in the cross-validation list")):
        d.tab(key, title, "MEASURED_SOFTWARE", f"n14x.failure16.{nm}.*", claim)
        rows = []
        for k in range(1, 11):
            p = f"n14x.failure16.{nm}.rank{k}"
            rows.append([r.i(p + ".test_no"), r.text(p + ".make"), r.text(p + ".model"), r.text(p + ".kind"), r.f(p + ".peak_g", 1), r.f(p + ".peak_g_raw", 1), r.f(p + ".abs_err_pct", 1), r.f(p + ".clipped_share", 2)])
        a(table(hdr, rows))
    a(f"Most of the large errors are side-impact tests ({r.f('n14x.failure16.R_cv.share_side', 2)} of the cross-validation list). Several have a very short pulse with a large raw peak and no sample near the saturation level after the 40 Hz filter; the fill then has nothing to repair and the ridge cannot help "
      "(the last column is near zero in those rows). Others are frontal pulses that are saturated for a large share of their length, where the fit extrapolates the most.\n")


def prevalence_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### Precision at lower crash prevalence\n")
    a(f"The VZCrash test set has {r.f('prev.test_crash_share', 2)} crashes among its events. The VZCrash paper reports `143` confirmed crashes among `735,000` real-world harsh-driving events (Section III-D), a share of {r.f('prev.paper_real_world_share', 5)} (under `0.02%`), "
      "and its best model's average precision falls from about `97.5%` on the benchmark to about `86%` there. Precision (positive predictive value) at other prevalences is computed from the measured system recall and false-alarm rate (mean of seeds 0 to 4) with the formula "
      "PPV = r p / (r p + f (1 - p)). It assumes that the false-alarm rate measured on VZCrash non-crash events also holds at the stated prevalence; that is an assumption, not a measurement (ANALYTICAL).\n")
    d.tab("prevalence", "Precision (PPV) of the deployed forest, the 10-tree depth-9 candidate and the rule detector at three crash prevalences, at the 1% and 5% false-alarm operating points", "ANALYTICAL", "prev.*",
          "At a prevalence near the real-world one almost every alert would be false")
    rows = []
    for m, mn in (("rf15", "deployed forest (15 trees, depth 6)"), ("rfsel", "10-tree depth-9 candidate"), ("rule", "rule detector")):
        for t in (1, 5):
            rec, fpr = r.f(f"detector.op.t{t}.{m}.test_recall.mean", 3), r.f(f"detector.op.t{t}.{m}.test_fpr.mean", 4)
            rows.append([mn, f"{t}%", rec, fpr] + [r.f(f"prev.{m}.t{t}.pi{tag}.ppv", 4) for tag in ("0p02pct", "1pct", "16pct")])
    a(table(["Detector", "False-alarm target", "System recall", "Achieved false-alarm rate", "PPV at `0.02%` prevalence", "PPV at 1%", "PPV at 16%"], rows))
    a(f"At the real-world prevalence most alerts would be false for every detector here (precision {r.f('prev.rf15.t1.pi0p02pct.ppv', 3)} for the deployed forest at the 1% operating point). **Results on a dataset with roughly `16%` crashes do not describe precision in real driving.** "
      "A usable alert system at that prevalence needs a false-alarm rate several orders lower, or a second confirmation step such as the cancel window, a phone check or a second sensor.\n")
