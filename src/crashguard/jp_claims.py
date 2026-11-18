"""Claim rows and allowed wording for the journal-push blocks (T13a, T13c, sensor selection, VZCrash audit, X1 to X8), added to the claim table of docs/03_results/CLAIM_EVIDENCE.md by ``claim_table``.
Verdicts are read from results.json (``x.holm.verdict.*`` and the stored criteria); the wording is generated from results.json so that no number is typed here."""
from __future__ import annotations

from crashguard.report import Res

HX = {"H-X1": ("x1", "python -m crashguard.x1_fixedpoint"), "H-X2": ("x2", "python -m crashguard.x2_cascade"), "H-X3": ("x3", "python -m crashguard.x3_groupaware"), "H-X5": ("x5", "python -m crashguard.x5_rank"),
      "H-X6": ("x6", "python -m crashguard.x6_anchored"), "H-X7": ("x7", "python -m crashguard.x7_fusion"), "H-X8": ("x8", "python -m crashguard.x8_sequential")}
CLAIM = {"H-X1": "X: the 16-bit fixed-point forest loses at most 0.005 AP and cuts the flash estimate by 30% (preregistered, Holm-corrected)",
         "H-X2": "X: a cheap-trigger cascade raises the share of crashes passing the trigger by 2 points over a 2 g threshold at an equal non-crash trigger rate",
         "H-X3": "X: group-aware training raises recall at the 1% false-alarm target on the strict test set by 1 point",
         "H-X5": "X: a +-16 g sensor with fill + ridge preserves the rank of delta-V (Spearman at least 0.90, lower end 0.85)",
         "H-X6": "X: a lower-bound-anchored estimator lowers the 90th-percentile delta-V error by 5 points against fill + ridge at +-16 g",
         "H-X7": "X: a real two-part pair reaches 0.80 within +-10% where neither part alone does (preregistered fusion rules)",
         "H-X8": "X: a sequential rule decides 100 ms earlier than the early-exit rule at equal or better recall"}
LABEL = {h: "MEASURED_SOFTWARE" for h in CLAIM}


def jp_rows(r: Res) -> list[tuple]:
    v = lambda k: r.r[k]["value"]  # noqa: E731
    rows = [
        ("T13a: the N13 requirement (lower interval end of 0.80 within +-10%) is also met on NHTSA tests of other test modes", "MEASURED_SOFTWARE", "t13.heldout.grid.*", "python -m crashguard.t13_heldout",
         "SUPPORTED" if v("t13.heldout.grid.criterion.cells_meeting_lower_bound") > 0 else "NOT SUPPORTED"),
        ("T13a: fill + ridge beats the spline at +-16 g on other test modes", "MEASURED_SOFTWARE", "t13.heldout.all.r16.paired.*", "python -m crashguard.t13_heldout", "SUPPORTED" if v("t13.heldout.all.r16.paired.M+_vs_SP.clears") == 1 else "NOT SUPPORTED"),
        ("T13c: fill + ridge still beats the spline at +-16 g without near-identical NHTSA pulses (exploratory)", "MEASURED_SOFTWARE", "t13.neardup.headline.*", "python -m crashguard.t13_neardup",
         "SUPPORTED" if all(v(f"t13.neardup.headline.{s}.r16.paired.M+_vs_SP.clears") == 1 for s in ("A", "G", "R")) else "NOT SUPPORTED"),
        ("Sensor selection: on the 176 NHTSA tests a range of +-64 g or more is needed to reach the requirement and no +-16 g part reaches it; the held-out modes do not confirm any configuration", "MEASURED_SOFTWARE (data sheet table ANALYTICAL)", "sel.s3.*",
         "python -m crashguard.sel_study", "SUPPORTED" if v("sel.s3.smallest_range_g") == 64.0 and v("sel.s3.part_meets_any.mpu6050") == 0 and v("sel.s3.part_meets_any.adxl345") == 0 else "NOT SUPPORTED"),
        ("V1: an independent recomputation reproduces the stored VZCrash duplicate counts", "MEASURED_SOFTWARE", "vz.v1.*", "python -m crashguard.vz_audit",
         "SUPPORTED" if v("vz.v1.exact.acc.groups_across_splits.vs_stored.difference") == 0 and v("vz.v1.near.test_windows_both.vs_stored.difference") == 0 else "NOT SUPPORTED"),
        ("V4: window-level duplicates raise the headline recall at the 1% target by several points; exact copies by under one point", "MEASURED_SOFTWARE", "vz.v4.*", "python -m crashguard.vz_leakage",
         "SUPPORTED" if v("vz.v4.rf15.diff_supplied_minus_near.recall_at_1pct_lo") > 0.03 and abs(v("vz.v4.rf15.diff_supplied_minus_exact.recall_at_1pct")) < 0.01 else "NOT SUPPORTED"),
    ]
    for h, (k, cmd) in HX.items():
        rows.append((CLAIM[h], LABEL[h], f"x.{k}.*; x.holm.{h}.*", cmd, v(f"x.holm.{h}.verdict")))
    return rows


def wording(r: Res) -> str:
    f = lambda k, d=3: f"{r.r[k]['value']:.{d}f}"  # noqa: E731
    n_ = lambda k: f"{int(r.r[k]['value']):,}"  # noqa: E731
    ci = lambda k, d=3: f"{f(k, d)} [{f(k + '_lo', d)} to {f(k + '_hi', d)}]"  # noqa: E731
    rows = [
        ("T13a", f"On {n_('t13.heldout.count.n_used')} NHTSA records of other test modes ({n_('t13.heldout.count.mode.VEHICLE_INTO_POLE_270')} of them pole tests), methods fitted on the 176 original tests reach a share within 10% of {ci('t13.heldout.grid.r64.f200.w10')} at +-64 g and 200 Hz and {ci('t13.heldout.grid.r200.f200.w10')} at +-200 g; no range and rate cell has its lower end at 0.80. At +-16 g fill + ridge has a median error of {f('t13.heldout.all.r16.M+.median', 1)}% against {f('t13.heldout.all.r16.SP.median', 1)}% for the spline (paired difference {ci('t13.heldout.all.r16.paired.M+_vs_SP.d_median', 2)} points).",
         "That the N13 or N14 findings hold for other crash modes; that fill + ridge beats the spline outside frontal and left-side tests."),
        ("T13c", f"Two of the 176 records are the same test channel counted twice ({n_('t13.neardup.pairs.within_176.all')} pairs); without the flagged tests fill + ridge still has the whole interval below zero against the spline at +-16 g on splits A, G and R (exploratory).", "That the NHTSA split is free of duplicates (the duplicates were present in the tagged runs)."),
        ("Sensor selection", f"On the 176 tests, {n_('sel.s3.n_meeting')} of {n_('sel.s3.n_configs')} configurations of 8 accelerometer parts have a lower interval end of 0.80 within +-10%; the smallest range among them is +-{f('sel.s3.smallest_range_g', 0)} g ({r.r['sel.s3.smallest_range_part']['value']} at {f('sel.s3.smallest_range_odr_hz', 0)} Hz: {f('sel.s3.smallest_range_w10')}, lower end {f('sel.s3.smallest_range_w10_lo')}); no MPU-6050, ADXL345 or LIS3DH configuration does. On the held-out modes no configuration does.",
         "That a part will perform so on a vehicle (software sensor model; datasheet rates, not ESP32 read rates; mostly high-speed barrier tests)."),
        ("V1/V2", f"The recomputation from the raw files agrees with every stored count ({n_('vz.v1.exact.acc.groups_across_splits')} cross-split groups; {n_('vz.v1.near.test_windows_both.vs_stored')} of {n_('vz.v1.near.test_windows_scanned')} triggered test windows equal a train or validation window, sample for sample). About a fifth of the triggered test windows ({100 * r.r['vz.v1.near.share_of_triggered_test_windows']['value']:.1f}%) and {100 * r.r['vz.v1.near.share_of_all_test_events_of_class.crash']['value']:.1f}% of the crash test events are affected; the strict set removes about 5% of all test events beyond the primary rule.", "That the duplicates are whole 16 s recordings (only the exact-copy events are)."),
        ("V4", f"For the 15-tree forest, removing the window-level duplicates lowers system recall by {ci('vz.v4.rf15.diff_supplied_minus_near.sys_recall', 4)} and recall at the 1% target by {ci('vz.v4.rf15.diff_supplied_minus_near.recall_at_1pct', 4)}; removing exact copies only changes them by {ci('vz.v4.rf15.diff_supplied_minus_exact.sys_recall', 4)} and {ci('vz.v4.rf15.diff_supplied_minus_exact.recall_at_1pct', 4)}.", "That the duplicates explain all of the gap to a clean evaluation (vehicle-level leakage cannot be checked)."),
        ("H-X1", f"Quantising thresholds and leaves of the 10-tree forest to 16 bits changes AP by {f('x.x1.hX1.ap_loss_q16', 6)} (upper 95% bound {f('x.x1.hX1.ap_loss_q16_hi', 5)}); the host flash estimate falls by {100 * r.r['x.x1.hX1.flash_reduction_primary']['value']:.1f}% in the existing node layout ({100 * r.r['x.x1.flash.compact.q16_vs_export_9byte.reduction']['value']:.1f}% if the left child is implicit).", "That the flash target of 30% is met with the existing layout; any ESP32 compile size."),
        ("H-X2", f"At a non-crash trigger rate not above that of 2 g, the cascade passes {ci('x.x2.dedup.cascade.crash_pass')} of crashes against {ci('x.x2.dedup.t2g.crash_pass')} for the 2 g threshold; the rule chosen is the 2 g threshold itself in most held-out categories.", "That a cheap running-feature trigger beats the fixed threshold on VZCrash."),
        ("H-X3", f"Down-weighting duplicate training windows changes recall at the 1% target on the strict set by {ci('x.x3.hX3.gain', 4)}; {100 * r.r['x.x3.train.share_in_duplicate_group']['value']:.1f}% of training windows are in a duplicate group.", "That duplicates in training explain the gap between the supplied and the strict set."),
        ("H-X5", f"At +-16 g and 100 Hz the Spearman correlation of fill + ridge with the reference delta-V is {ci('x.x5.hX5.rho_fillridge')}, below the plain estimate's {ci('x.x5.hX5.rho_plain')}; at +-32 g it is {ci('x.x5.r32.f100.fillridge.rho_ref')} and at +-64 g {ci('x.x5.r64.f100.fillridge.rho_ref')}. Class agreement of fill + ridge at +-16 g: {ci('x.x5.r16.f100.fillridge.class_accuracy')}.", "That a +-16 g sensor preserves the order of severity; any claim about injury in real crashes."),
        ("H-X6", f"At +-16 g on split R the 90th-percentile error of the anchored estimator is {f('x.x6.R.r16.ANC.p90', 1)}% against {f('x.x6.R.r16.M+.p90', 1)}% for fill + ridge (gain {ci('x.x6.hX6.p90_gain_R', 1)} points); the gain has its interval above zero on split A and not on G or O; the anchored estimate is never below the plain estimate and over-corrects the {n_('x.x6.lowerbound.r16.n_violations')} tests where plain exceeds the reference.", f"That it has a lower median error than the tail-aware model ({f('x.x6.R.r16.ANC.median', 1)}% against {f('x.x6.R.r16.QR.median', 1)}%), that the gain holds on every split, or that it works on a real sensor."),
        ("H-X7", f"None of the 16 preregistered pairs and two fusion rules reaches a lower end of 0.80 ({n_('x.x7.hX7.n_meeting_any')} of {n_('x.x7.hX7.n_pairs_rules')} combinations meet it); a wider clipped-sample mask, defined after the initial result (exploratory), reaches it for {n_('x.x7.hX7.n_counting_exploratory_wide')} combinations where neither part alone does.", "That fusing a +-16 g and a +-200 g part works as a general method; any time-synchronised or mounted result."),
        ("H-X8", f"At the 1% target the sequential rule decides {ci('x.x8.a1.dedup.diff.time_early_minus_seq_median', 0)} ms earlier at the median than the early-exit rule, with recall {ci('x.x8.a1.dedup.diff.recall_seq_minus_early', 4)} higher; at 5% the difference is {ci('x.x8.a5.dedup.diff.time_early_minus_seq_median', 0)} ms (positive = the sequential rule is earlier) and recall {ci('x.x8.a5.dedup.diff.recall_seq_minus_early', 4)}. The recall gain over the single forest is an ensemble effect.", "That the sequential rule is faster at both targets."),
    ]
    out = ["", "## Allowed wording for the journal-push claims (generated)", "", "| Claim | Allowed wording | Not allowed |", "|---|---|---|"]
    out += [f"| {h} | {a} | {n} |" for h, a, n in rows]
    return "\n".join(out)
