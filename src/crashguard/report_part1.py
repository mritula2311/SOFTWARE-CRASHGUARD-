"""Report sections 1 to 4.4: introduction, dataset and audit, method, detector, trigger-aware evaluation, robustness, size against accuracy."""
from __future__ import annotations

import pandas as pd

from crashguard import config as C
from crashguard.report import MODEL_NAMES, MODEL_ORDER, P, Doc, Res, table


def introduction(r: Res, d: Doc) -> None:
    a = d.a
    a("## 1. Introduction\n")
    a("A vehicle crash alert has to be sent within seconds, from a device that costs little and runs on a small processor. CrashGuard detects a crash on an ESP32 with one IMU, estimates how hard the "
      "vehicle's velocity changed, and sends an authenticated alert over LoRa to a base station that answers with a signed acknowledgement. The hardware part of the project is measured separately by the author. "
      "This report covers the software and data-science part: what can be learned from public crash data and from simulation before any car is crashed.\n")
    a("Why a microcontroller-sized model. The detector must run inside the sensor node, where flash and RAM are counted in kilobytes, and it must keep working when the network does not. "
      "A 15-tree forest of depth 6 fits in about " + r.i("export.bytes_est") + " bytes (a host estimate). The question is how much accuracy this costs against larger models, and how the result depends on the sensor.\n")
    a("What this draft reports, in plain words:\n")
    a(f"- **Detector.** On a public dataset of real vehicle events (VZCrash), the deployable forest finds crashes with system recall {r.ci('detector.head5.rf15.sys_recall')} and a system false-alarm rate of "
      f"{r.ci('detector.head5.rf15.sys_fpr')} (mean of seeds 0 to 4, with a 95% bootstrap interval for that mean; seed 42 alone gives {r.ci('detector.head.rf15.sys_recall')} and {r.ci('detector.head.rf15.sys_fpr')}, each with its own interval). The trigger in front of the model is a second trigger: the dataset was already selected on the device.")
    a(f"- **Sensor.** On {r.i('sevstudy.n_tests')} NHTSA crash tests, a 16 g accelerometer at 100 Hz estimates the velocity change within 10% on only {r.f('sevstudy.grid.r16.f100.dv_within10', 2)} of the tests. "
      f"At least ±{r.f('sevstudy.needed.point.min_range_g', 0)} g and {r.f('sevstudy.needed.point.min_rate_hz', 0)} Hz are needed to reach 80% of tests inside 10% (Section 4.5).")
    a("- **Security and delivery.** The alert carries an 8-byte HMAC tag and a counter. Our own attack suite found that strict replay rejection blocks the retry of an alert whose ACK was lost; an idempotent re-ACK repairs it. "
      "An end-to-end replay of real events through the whole chain, with a lossy channel, is simulated (Section 4.7).")
    a("- **Three proposed methods**, each judged only by whether its gain clears the 95% bootstrap interval on data it was not tuned on (Section 4.8). The saturation-aware estimator (N14) clears it at ±16 g only, against both plain integration and spline restoration, on re-splits that are not blind tests; "
      "trigger-aware training (N15) does not clear it; the scheduler (N16) is simulated, beats a weak fixed policy but not the severity table, and is supporting evidence only.\n"
      f"- **Precision at real prevalence.** At a crash share near the real-world one, almost every alert would be false (Section 4.1, Table on precision: {r.f('prev.rf15.t1.pi0p02pct.ppv', 3)} for the deployed forest at the 1% operating point; ANALYTICAL). Results on a dataset with roughly `16%` crashes do not describe precision in real driving.\n"
      "- **Where the forest sits against the VZCrash paper.** The paper benchmarks neural and transformer models and a peak-acceleration baseline, tested no tree models and ran no embedded test; the forest is evaluated where the paper left a gap.\n")
    a("The software results are not hardware results. The trigger level and the sensor range are placeholders until they are confirmed from the firmware, and every system-level number is a function of them.\n")


def dataset(r: Res, d: Doc) -> None:
    a = d.a
    a("## 2. Dataset and audit\n")
    a("### What was run\n")
    a(f"- **Data.** VZCrash, {r.i('vzcrash.events_total')} events, each a 16 s window at 100 Hz. Labels: crash ({r.i('vzcrash.events.all.crash')}), "
      f"near_miss ({r.i('vzcrash.events.all.near_miss')}) and normal_driving ({r.i('vzcrash.events.all.normal_driving')}). near_miss counts as a negative class. The licence is CC BY-NC 4.0 (non-commercial; cite the paper).")
    a(f"- **Corrupt events.** {r.i('features.events_dropped_corrupt')} events with a peak above the sensor range were dropped. Signals were clipped to the sensor range.")
    a("- **Window.** The firmware-style trigger is the earliest sample with |a| above the trigger level. The window is 1.0 s before to 1.8 s after it (2.8 s). "
      "The trigger level (2.0 g) and sensor range (16 g) are placeholders until they are confirmed from firmware v2.")
    a("- **Features.** 14 window features (`docs/05_data_code/FEATURES.md`), with two subsets: no gyro (13) and scale-free (5).")
    a("- **Models.** A 15-tree depth-6 random forest (the one that fits on the ESP32), a 200-tree forest, logistic regression, gradient-boosted trees and a peak-and-duration rule. "
      "Seed 42 is the headline run; seeds 0 to 4 give mean ± standard deviation. The logistic regression and the rule have no randomness, so their standard deviation is zero. All training is on the CPU.")
    a("- **Splits and thresholds.** The train, validation and test splits supplied with the dataset. The VZCrash paper (Section III-B) states that the splits are `72/14/14`, \"strictly separated by vehicle\" and stratified by vehicle size; the release has no vehicle or trip ID, so we cannot check this, and we do not claim leakage by vehicle. "
      f"The primary test set leaves out the {r.i('leakage.test_events_flagged.total')} test events that also appear (nearly) in train or validation. Thresholds are chosen on the validation split only. The test set is scored once per model and seed.")
    a("- **Two levels.** *Model level* uses only events that pass the trigger. *System level* counts events that never trigger as predicted negative, as the car would.")
    a("- **Caveat on the trigger.** The VZCrash paper says its events were already selected on the device by threshold heuristics (hard braking and shock events). "
      "Our trigger is therefore a second trigger applied to events that were already triggered once. The trigger rates describe these selected events, not continuous driving.\n")
    d.tab("profile", "Dataset profile (events per split and class)", "MEASURED_SOFTWARE", "vzcrash.events.*, leakage.test_events_kept.*", "The primary test set is the supplied test split without cross-split duplicates")
    rows = [[sp] + [r.i(f"vzcrash.events.{sp}.{c}") for c in ("crash", "near_miss", "normal_driving")] for sp in ("train", "validation", "test")]
    rows.append(["test, de-duplicated (primary)"] + [r.i(f"leakage.test_events_kept.{c}") for c in ("crash", "near_miss", "normal_driving")])
    a(table(["Split", "crash", "near_miss", "normal_driving"], rows))
    a(f"Events dropped as corrupt: {r.i('features.events_dropped_corrupt')} (listed in `results/tables/dropped_events.csv`). Kept events that are not 1600 samples long: {r.i('features.events_not_1600_samples_kept')}. "
      f"Events whose gyro length differs from the accelerometer length: {r.i('features.events_gyro_length_mismatch')}.\n")
    a(f"**Dataset audit.** {r.i('leakage.exact_hash_groups_across_splits')} groups of identical accelerometer recordings appear in more than one split ({r.i('leakage.exact_hash_duplicates_total')} duplicate events in total). "
      f"In the supplied test split, {r.i('leakage.test_events_flagged.total')} events ({r.i('leakage.test_events_flagged.crash')} crash, {r.i('leakage.test_events_flagged.near_miss')} near_miss and "
      f"{r.i('leakage.test_events_flagged.normal_driving')} normal_driving) have an identical or near-identical recording in train or validation. They are removed from the primary test set; the supplied split is a secondary result. "
      "We say only that identical recordings appear across the released splits and ask the authors whether they come from the export. The paper reports no licence; the CC BY-NC 4.0 licence used here is the one on the dataset card (Hugging Face README, `license: cc-by-nc-4.0`). A draft email to the dataset authors with the event IDs is in `docs/04_audits/vzcrash_email_draft.md`; nothing has been sent.\n")
    a(f"**NHTSA crash tests.** For the severity work we use the NHTSA Vehicle Crash Test Database (US government, public domain): {r.i('nhtsa.n_frontal')} frontal barrier tests and {r.i('nhtsa.n_side')} side impactor tests, "
      "read from the ISO MME files (vehicle-centre-of-gravity accelerometer, or a front sill accelerometer when there is none). "
      f"{r.i('nhtsa.n_excluded_other')} candidate tests were skipped because they have no such channel or no pre-trigger baseline, and {r.i('nhtsa.n_excluded_no_pulse')} because the channel showed no pulse. "
      "The list is in `docs/05_data_code/DATASET.md`. The tests are split by vehicle group (make, model and model year) into a tuning part and a held-out part before any result was looked at (every third group, by smallest test number, is held out, with all its tests).\n")


def method(r: Res, d: Doc) -> None:
    a = d.a
    a("## 3. Method\n")
    a("**Trigger, window, features, model.** The node keeps a ring buffer. At the earliest sample where |a| exceeds the trigger level, 1.0 s before and 1.8 s after are cut as one window; 14 features (peak, rms, jerk, energy, duration above 2 g, "
      "peak ratio, horizontal share, kurtosis, crest factor, post-quiet ratio, gyro peak) go to a random forest whose threshold is chosen on validation. "
      "The forest is exported to C as constant arrays, and a compiled check compares it with scikit-learn. Because the trigger is a design choice, it is varied and evaluated at system level.\n")
    a("**Severity.** From the same window the code computes: delta-V (the integral of acceleration over the crash pulse after removing the pre-trigger mean), ASI (the EN 1317-2 formula with a 13 Hz filter and a 50 ms average), "
      "peak and mean pulse acceleration, a gravity-frame tilt for rollover, and a four-class severity (Low, Moderate, Severe, Critical) from delta-V and ASI. "
      "The pulse ends when horizontal acceleration stays below the larger of 0.5 g and a tenth of the pulse peak for 50 ms, or after 250 ms; the fraction was chosen on the NHTSA tuning tests. "
      "THIV (a free-head model) is also computed, but it is UNVERIFIED (its flail distances are in doubt) and is not used in any claim here. These classes describe crash severity, not injury. Constants and their status (read, secondary source, unverified, ours) are in `docs/05_data_code/SEVERITY.md`: the ASI level C limit 1.9 was read in a secondary source; the 13 Hz filter and the THIV flail distances are unverified; the delta-V class limits and names are our choice.\n")
    a("**Packet and security.** The alert is 97 bytes: ids, a 32-bit counter, severity, impact side, position, peak, model probability, delta-V and ASI, then an 8-byte tag (HMAC-SHA256 truncated). "
      "The tag covers bytes `0 to 88`. The base accepts an alert only if the tag and the counter are right, and answers with a signed 26-byte ACK. A retry repeats the same bytes; the base remembers the last accepted alerts and "
      "re-sends the identical ACK for an exact repeat (idempotent re-ACK), at most once per event per retry interval, paying every ACK from its duty-cycle budget. One key is shared by both nodes; there is no key rotation (`docs/01_protocol/PACKET_FORMAT.md`).\n")
    a("**Delivery policy.** Under a 10% duty cycle a token bucket pays for every transmission. Three policies are compared: no retry; a fixed policy with three retries; and a severity table (2, 4, 8 and 12 tries for Low, Moderate, Severe and Critical, the most severe waiting alert served next). "
      "A scheduler proposed in Section 4.8 adds a reserved share, age ordering and back-off.\n")
    a("**Evaluation rules.** Thresholds and every choice are made on validation (VZCrash) or on a tuning set of NHTSA tests; the test or held-out part is scored once. "
      "Confidence intervals are 95% percentile bootstrap intervals from 1,000 resamples of test events, tests or simulated hours (seed 42). A proposed method counts as an improvement only if its paired gain clears the interval on data it was not tuned on.\n")


def detector(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.1 Detector\n")
    d.tab("model_level", "Model level, triggered events of the de-duplicated test set", "MEASURED_SOFTWARE", f"s2.{P}.all.*", "Model-level AP, F1 and Brier of the five models")
    rows = []
    for m in MODEL_ORDER:
        p = f"s2.{P}.all.{m}"
        rows.append([MODEL_NAMES[m], r.ms(f"{p}.ap"), r.ms(f"{p}.roc_auc"), r.ms(f"{p}.f1op_precision"), r.ms(f"{p}.f1op_recall"), r.ms(f"{p}.f1op_f1"), r.ms(f"{p}.f1op_fpr"),
                     r.ms(f"{p}.brier") if m != "rule" else "n/a"])
    a(table(["Model", "AP", "ROC-AUC", "Precision", "Recall", "F1", "FPR (triggered negatives)", "Brier"], rows))
    a(f"Precision, recall and F1 use the threshold that maximises F1 on validation. Crashes are {r.f(f's2.{P}.all.rf15.prevalence_triggered.mean')} of the triggered test events, so AP has a high floor here and should be read with the system-level table.\n")
    d.tab("system_level", "System level, de-duplicated test set", "MEASURED_SOFTWARE", f"s2.{P}.all.*sys_*", "System recall and false-alarm rate, including events the trigger discards")
    rows = []
    for m in MODEL_ORDER:
        p = f"s2.{P}.all.{m}"
        rows.append([MODEL_NAMES[m], r.ms(f"{p}.sys_f1op_recall"), r.ms(f"{p}.sys_f1op_fpr"), r.ms(f"{p}.sys_f1op_fpr_near_miss"), r.ms(f"{p}.sys_f1op_fpr_normal"), r.ms(f"{p}.sys_r95op_recall"), r.ms(f"{p}.sys_r95op_fpr")])
    a(table(["Model", "Recall", "FPR (all negatives)", "FPR near_miss", "FPR normal", "Recall at val. recall 0.95 threshold", "FPR at that threshold"], rows))
    a("In this table, the number after the plus-minus sign is the standard deviation across the five seeds (spread between model fits). It is not an interval for the mean; the interval for the 5-seed mean is in Section 1 (detector.head5). FPR is the share of negative events that raise an alarm. The leading columns use the maximum-F1 validation threshold; the last two use the validation threshold that gives recall 0.95 on validation.\n")
    d.tab("headline_ci", "Headline detector metrics with 95% bootstrap intervals (seed 42, de-duplicated test)", "MEASURED_SOFTWARE", "detector.head.*", "The deployed forest and the validation-selected forest are close; the larger models have a higher AP")
    names = (("rf15", MODEL_NAMES["rf15"]), ("rfsel", f"RF chosen on validation (trees and depth from {d.T('depth_sweep')})"), ("rf200", MODEL_NAMES["rf200"]), ("gbt", MODEL_NAMES["gbt"]), ("lr", MODEL_NAMES["lr"]), ("rule", MODEL_NAMES["rule"]))
    rows = [[nm, r.ci(f"detector.head.{k}.ap"), r.ci(f"detector.head.{k}.sys_ap"), r.ci(f"detector.head.{k}.sys_recall"), r.ci(f"detector.head.{k}.sys_fpr")] for k, nm in names]
    a(table(["Model", "AP (triggered)", "System AP", "System recall", "System false-alarm rate"], rows))
    a(f"{r.i('detector.head.rf15.n_test')} test events, of which {r.i('detector.head.rf15.n_triggered')} pass the trigger. Thresholds come from the validation split (maximum F1).\n")
    a("**Cost of fitting on the ESP32.** ")
    d.tab("gap", "Larger models minus the 15-tree forest", "MEASURED_SOFTWARE", "gap.*", "Fitting on the ESP32 costs AP but not system recall at the maximum-F1 threshold")
    rows = [[nm] + [r.f(f"gap.{k}_minus_rf15.{met}", 4) for met in ("ap", "f1op_f1", "sys_f1op_recall", "sys_f1op_fpr")] for k, nm in (("rf200", "RF 200 trees minus RF 15 trees"), ("gbt", "Gradient-boosted trees minus RF 15 trees"))]
    a(table(["Difference", "AP", "F1 (triggered)", "System recall", "System FPR"], rows))
    a("A positive AP, F1 or recall difference means the larger model is better; a positive FPR difference means more false alarms. The larger models have a higher AP and fewer false alarms, but they do not have a higher system recall at the maximum-F1 threshold.\n")
    d.tab("op_points", "Operating point chosen on validation for a fixed false-alarm rate, test recall scored once (mean ± std over seeds 0 to 4)", "MEASURED_SOFTWARE", "detector.op.*",
          "Fixing the false-alarm rate at 1% costs recall; at 5% the models are close")
    rows = []
    for k, nm in names:
        rows.append([nm, r.ms(f"detector.op.t1.{k}.test_recall"), r.ms(f"detector.op.t1.{k}.test_fpr"), r.ci(f"detector.op.t1.{k}.seed42.recall"),
                     r.ms(f"detector.op.t5.{k}.test_recall"), r.ms(f"detector.op.t5.{k}.test_fpr"), r.ci(f"detector.op.t5.{k}.seed42.recall")])
    a(table(["Model", "Recall at 1% target", "Achieved FPR", "Seed 42 recall with interval", "Recall at 5% target", "Achieved FPR", "Seed 42 recall with interval"], rows))
    a("The threshold is the smallest one whose false-alarm rate on all validation non-crash events (trigger-discarded ones included) does not exceed the target. The achieved test false-alarm rate is shown next to it.\n")
    d.tab("calibration", "Calibration of the probability models (seed 42, triggered de-duplicated test events)", "MEASURED_SOFTWARE", "detector.cal.*", "The forests are reasonably calibrated; Brier and ECE with intervals")
    rows = [[nm, r.ci(f"detector.cal.{k}.brier", 4), r.ci(f"detector.cal.{k}.ece", 4)] for k, nm in names if k != "rule"]
    a(table(["Model", "Brier score", "Expected calibration error (10 bins)"], rows))
    d.tab("ablation", "Feature ablation", "MEASURED_SOFTWARE", "s2.*, s3.*", "The gyro feature adds little; the scale-free subset keeps most of the AP")
    rows = []
    for m in ("rf15", "rf200", "lr", "gbt"):
        row = [MODEL_NAMES[m]]
        for fs, pre in (("all", "s2"), ("no_gyro", "s3"), ("scale_free", "s3")):
            p = f"{pre}.{P}.{fs}.{m}"
            row += [r.ms(f"{p}.ap"), r.ms(f"{p}.sys_f1op_recall")]
        rows.append(row)
    a(table(["Model", "AP, all 14", "System recall, all 14", "AP, no gyro", "System recall, no gyro", "AP, scale-free", "System recall, scale-free"], rows))
    d.fig("s2_pr_curves", "Precision against recall on triggered, de-duplicated test events, seed 42.", "MEASURED_SOFTWARE", f"s2.{P}.*", "Detector quality across thresholds")
    d.fig("detector_reliability", "Reliability curves of the probability models.", "MEASURED_SOFTWARE", "detector.cal.*", "Calibration")
    d.fig("detector_operating_points", "System recall when the false-alarm rate is fixed on validation.", "MEASURED_SOFTWARE", "detector.op.*", "Operating point")


def trigger_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.2 Trigger-aware evaluation\n")
    a("The trigger decides which events the model ever sees. System-level recall therefore includes the crashes the trigger discards. Because VZCrash events were already selected on the device, these rates describe a second trigger.\n")
    d.tab("trigger_rate", "Trigger rate per class", "MEASURED_SOFTWARE", "trigger.*", "Most crashes pass a 2 g trigger; many non-crash events do too")
    rows = [[f"{g:g} g"] + [r.f(f"trigger.trig_{g:g}.{c}.rate") for c in ("crash", "near_miss", "normal_driving")] for g in C.TRIGGER_SWEEP_G]
    a(table(["Trigger level", "crash", "near_miss", "normal_driving"], rows))
    d.tab("trigger_sweep", "Trigger level sweep, 15-tree forest (seed 42, 95% intervals)", "MEASURED_SOFTWARE", "detector.trig.*", "System recall peaks at the 2 g trigger; the share of crashes that pass falls as the level rises")
    rows = [[f"{g:g} g", r.ci(f"detector.trig.{g:g}.sys_recall"), r.ci(f"detector.trig.{g:g}.sys_fpr"), r.ci(f"detector.trig.{g:g}.sys_ap"), r.ci(f"detector.trig.{g:g}.crash_pass_trigger")] for g in C.TRIGGER_SWEEP_G]
    a(table(["Trigger level", "System recall", "System false-alarm rate", "System AP", "Share of crashes that pass the trigger"], rows))
    d.tab("trigger_missed", "Crash events below each trigger, by VZCrash vehicle-size category (seed-independent counts, 95% intervals)", "MEASURED_SOFTWARE", "detector.trigmiss.*", "Which crashes never reach the model")
    rows = []
    for g in C.TRIGGER_SWEEP_G:
        rows.append([f"{g:g} g"] + [f"{r.i(f'detector.trigmiss.{g:g}.{c}.below_trigger')} of {r.i(f'detector.trigmiss.{g:g}.{c}.crashes')} ({r.f(f'detector.trigmiss.{g:g}.{c}.share')})" for c in ("Light", "Medium", "Heavy", "Unknown")])
    a(table(["Trigger level", "Light", "Medium", "Heavy", "Unknown"], rows))
    a("Each cell: crashes that never reach the trigger, of all crashes in that category, and the share. 'Unknown' is a mix of vehicles with no size recorded.\n")
    d.tab("peak_window", "Secondary comparison: window centred on the peak", "MEASURED_SOFTWARE", "peak_window.*", "The trigger-based window costs little against a window that cannot be built on the car")
    a("This window cannot be built on the car (it needs the peak in advance); it is shown only to see what the trigger-based window costs.\n")
    rows = [[MODEL_NAMES[m], r.ms(f"peak_window.peak.all.{m}.ap"), r.ms(f"peak_window.peak.all.{m}.f1op_f1"), r.ms(f"peak_window.peak.all.{m}.sys_f1op_fpr_near_miss")] for m in MODEL_ORDER]
    a(table(["Model", "AP", "F1", "FPR near_miss"], rows))
    d.tab("confusion3", "Three-class outcome, 15-tree forest, seed 42, de-duplicated test split", "MEASURED_SOFTWARE", "confusion3.*", "What happens to each true class")
    rows = [[c] + [r.i(f"confusion3.rf15.{c}.{k}") for k in ("not_triggered", "triggered_pred_negative", "triggered_pred_crash")] for c in ("crash", "near_miss", "normal_driving")]
    a(table(["True class", "Not triggered", "Triggered, predicted negative", "Triggered, predicted crash"], rows))
    d.fig("trigger_sweep", "Trigger rate per class, and system recall and FPR, as the trigger level changes.", "MEASURED_SOFTWARE", "trigger_sweep.*", "Trigger sweep")
    d.fig("s2_confusion_3class", "What happens to each true class: not triggered, triggered but predicted negative, or predicted crash.", "MEASURED_SOFTWARE", "confusion3.*", "Three-class outcome")


def robustness(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.3 Robustness to sensor errors\n")
    a("The perturbations are ours, not measured on a car, and are applied to the raw signals before the sensor clip and the trigger, so the trigger rate changes too. "
      "The models are trained on the unperturbed training split (seed 42), and thresholds come from the unperturbed validation split. Gain error: ±5% and ±10%. Constant offset: 0.5 g on one axis (x, y, z and -z) and `0.25 g` on all axes "
      "(the car's resting reading showed 0.5 g). Axis misalignment: ±5, ±10 and ±20 degrees about each axis. Added noise: three levels. A 50 Hz down-sample.\n")
    df = pd.read_csv(C.TABLES / "robustness_sensor_errors.csv")
    names = list(dict.fromkeys(df.perturbation))
    d.tab("robust", "Sensor-error robustness: AP, system recall and false-alarm rate (seed 42; change in recall against the unperturbed run with a paired 95% interval)", "SIMULATED",
          "robust.*", "Which sensor errors hurt: a 0.5 g offset on the vertical axis and a few misalignments cost the most recall")
    rows = []
    for n in names:
        rows.append([f"`{n}`", r.f(f"robust.{n}.rf15.trigger_rate", 3), r.f(f"robust.{n}.rf15.ap", 3), r.f(f"robust.{n}.rf15.sys_recall", 3),
                     "baseline" if n == "baseline" else f"{r.f(f'robust.{n}.rf15.d_recall_lo', 3)} to {r.f(f'robust.{n}.rf15.d_recall_hi', 3)}", r.f(f"robust.{n}.rf15.sys_fpr", 3),
                     r.f(f"robust.{n}.rfsel.sys_recall", 3), r.f(f"robust.{n}.rule.sys_recall", 3)])
    a(table(["Perturbation", "Trigger rate", "AP (RF15)", "System recall (RF15)", "Change in recall, 95% interval", "System FPR (RF15)", "System recall (RF 10 trees, depth 9)", "System recall (rule)"], rows))
    a(f"The unperturbed re-processing triggers on the same events as the main pipeline (check flag {r.i('robust.check.baseline_trigger_equal')}; largest feature difference {r.sci('robust.check.baseline_max_abs_feature_diff')}). "
      "Origin: the events are VZCrash (MEASURED_SOFTWARE inputs); the perturbations make the results SIMULATED.\n")
    d.fig("robustness_sensor_errors", "Change in system recall and false-alarm rate under each perturbation, for three detectors.", "SIMULATED", "robust.*", "Sensor-error robustness")


def size_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.4 Size against accuracy\n")
    d.tab("size", "Model size against performance, depth 6 (AP: MEASURED_SOFTWARE, bytes: ANALYTICAL)", "MEASURED_SOFTWARE", "s4.depth6.*", "More trees at depth 6 do not raise AP; depth does")
    rows = [[str(n), r.f(f"s4.depth6.trees{n}.nodes", 0), r.f(f"s4.depth6.trees{n}.bytes_est", 0), r.ms(f"s4.depth6.trees{n}.ap")] for n in (1, 3, 5, 10, 15, 30, 60, 100, 200)]
    a(table(["Trees", "Nodes", "Estimated bytes", "AP"], rows))
    a(f"Bytes are the node count times 9 bytes per node, a host estimate, not an ESP32 compile report. At depth 6, 200 trees reach AP {r.f('s4.depth6.trees200.ap.mean')}, no better than 15 trees ({r.f('s4.depth6.trees15.ap.mean')}). "
      f"With depth 8 and 15 trees, AP is {r.f('s4.depth8.trees15.ap.mean')}.\n")
    d.tab("depth_sweep", "Depth against size sweep, chosen on the validation split (AP and nodes: MEASURED_SOFTWARE, flash: ANALYTICAL)", "MEASURED_SOFTWARE", "s4b.*", "A forest of 10 trees and depth 9 is the validation choice under a flash limit")
    rows = []
    for t in (10, 15, 20):
        for dp in (6, 7, 8, 9, 10):
            p = f"s4b.t{t}.d{dp}"
            mark = ("Pareto" if r.v(f"{p}.pareto") else "") + (", recommended" if (t == int(r.v("s4b.recommended.trees")) and dp == int(r.v("s4b.recommended.depth"))) else "")
            rows.append([str(t), str(dp), r.ms(f"{p}.ap_val"), r.f(f"{p}.nodes", 0), r.f(f"{p}.flash_est", 0), r.f(f"{p}.header_bytes", 0), mark.strip(", ")])
    a(table(["Trees", "Depth", "Validation AP", "Nodes", "Estimated flash (bytes)", "C header file (bytes of text)", "Marks"], rows))
    rt, rd = int(r.v("s4b.recommended.trees")), int(r.v("s4b.recommended.depth"))
    a(f"Every AP here is on the validation split; the test set was not used to choose the configuration. The rule was fixed before the sweep. Result: **{r.i('s4b.recommended.trees')} trees at depth {r.i('s4b.recommended.depth')}**, "
      f"estimated {r.f(f's4b.t{rt}.d{rd}.flash_est', 0)} bytes; scored once on the de-duplicated test set it has AP {r.ms('s4b.chosen.ap_test')}. The deployed model is not changed. "
      "Validation events can repeat training events, so validation AP may be optimistic.\n")
    d.tab("lovso", "Leave one vehicle-size category out, 15-tree forest", "MEASURED_SOFTWARE", "lovso.*, ap_by_size.*", "Transfer across vehicle-size categories, not across vehicles")
    rows = [[cat, r.f(f"ap_by_size.{cat}.rf15"), r.ms(f"lovso.{cat}.rf15.ap"), r.ms(f"lovso.{cat}.rf15.sys_f1op_recall"), r.ms(f"lovso.{cat}.rf15.sys_f1op_fpr")] for cat in ("Light", "Medium", "Heavy", "Unknown")]
    a(table(["Category", "AP, standard test", "AP, held out", "System recall, held out", "System FPR, held out"], rows))
    d.tab("c_export", "C export of the 15-tree forest and of the validation-selected candidate", "MEASURED_SOFTWARE", "export.*, candidate.*", "The generated C code equals scikit-learn; the candidate header is ready but not deployed")
    cand_ok = r.origin("candidate.max_abs_diff") != "NOT_RUN"
    exp_ok = r.origin("export.max_abs_diff") != "NOT_RUN"
    rows = [["Nodes in all trees", r.i("export.nodes_total"), r.i("candidate.nodes")], ["Estimated size (bytes, ANALYTICAL)", r.i("export.bytes_est"), r.i("candidate.bytes_est")],
            ["Triggered test events compared", r.i("export.test_rows"), r.i("candidate.test_rows")],
            ["Maximum difference, compiled C against scikit-learn", r.sci("export.max_abs_diff") if exp_ok else "NOT_RUN (the compiled program was blocked; see the mirror row)", r.sci("candidate.max_abs_diff") if cand_ok else "NOT_RUN (the compiled program was blocked)"],
            ["Maximum difference, pure-Python float32 mirror of the C code, against scikit-learn", r.sci("export.mirror_max_abs_diff"), "see `docs/05_data_code/FIRMWARE_SYNC.md`"],
            ["Time per call on the ESP32 (microseconds)", "NOT_RUN (`benchmark_rf.ino` is built, not yet measured)", "NOT_RUN"]]
    a(table(["Item", "Deployed (15 trees, depth 6)", "Candidate (validation choice)"], rows))
    a("The compiled C check is built into `build/` and retried up to five times because Windows Application Control sometimes blocks a freshly built program; if it still cannot run, the row says NOT_RUN with the reason and the pure-Python mirror remains. "
      "`docs/05_data_code/FIRMWARE_SYNC.md` lists what the firmware author must set or check before the candidate header replaces the deployed one.\n")
    d.fig("s4b_depth_sweep_pareto", "Validation AP against estimated flash for the depth sweep.", "MEASURED_SOFTWARE", "s4b.*", "Size against accuracy")
    d.fig("s4_size_vs_ap", "AP against estimated model size for forests of different depth and tree count.", "MEASURED_SOFTWARE", "s4.*", "Size against accuracy")
