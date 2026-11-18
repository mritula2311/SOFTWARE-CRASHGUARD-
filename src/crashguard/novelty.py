"""Build report/novelty_summary.md and the status block of docs/06_references/NOVELTY.md from results/results.json.

Framing (author decision, 2026-11-10):
- The headline contribution is the integrated system, evaluated end to end: a detector that fits on an MCU, impact
  direction, and authenticated, severity-aware LoRa delivery. No single part is claimed alone.
- N8 (dataset audit) and N9 (trigger-aware evaluation) are evaluation-rigour contributions, not the headline.
- N11 (near-miss false alarms) is a results breakdown, not a contribution.
- N12 is an independent re-discovery of a known LoRaWAN issue in a custom point-to-point link, with a bounded fix.

Evidence only: each point lists the exact results.json keys and values behind it. Points whose software evidence is
missing are downgraded to NOT_YET automatically. The prior-work record is hand-written in docs/06_references/PRIOR_WORK.md.
Wording rules: no 'first', 'novel' or 'state-of-the-art'; hardware-dependent parts are NOT_RUN.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from crashguard import v2_novelty as V2N
from crashguard.report import L, R_, Res

OUT = Path("report/novelty_summary.md")
DOC = Path("docs/06_references/NOVELTY.md")
PRIOR = Path("docs/06_references/PRIOR_WORK.md")
START, END = "<!-- novelty:start -->", "<!-- novelty:end -->"
P_START, P_END = "<!--prior-start-->", "<!--prior-end-->"
P = "trig_2"
RF = f"s2.{P}.all.rf15"


@dataclass
class Point:
    pid: str
    title: str
    group: str  # headline, rigour, design, component, breakdown
    status: str  # status if the keys in `needs` exist
    needs: list[str]
    evidence: list[tuple[str, int]]  # (results.json key, decimals; -1 = integer, -2 = scientific, 0 = text)
    missing: str
    prior: str
    risk: str


GROUPS = {"headline": "Headline contribution", "rigour": "Evaluation-rigour contributions (not the headline)",
          "design": "Design findings and supporting results", "component": "Components of the integrated system (need hardware)",
          "breakdown": "Results breakdown (not a contribution)", "extra": "Extra software-only experiments (N17 to N23; supporting evidence or negative results)"}


def attack_key(r: Res, prefix: str) -> str | None:
    for k, e in r.r.items():
        if k.startswith("attacks.case") and e["notes"].startswith(prefix):
            return k
    return None


def points(r: Res) -> list[Point]:
    k_strict = attack_key(r, "Strict verifier (before the fix)")
    k_reack = attack_key(r, "ACK lost, car retries same packet")
    k_old = attack_key(r, "Old counter, different content")
    f = "attacks.flood"
    rt, rd = (int(r.v("s4b.recommended.trees")), int(r.v("s4b.recommended.depth"))) if r.has("s4b.recommended.trees") else (0, 0)
    return [
        Point("HL", "Integrated system: MCU detector + impact direction + authenticated, severity-aware LoRa delivery (software parts built and tested; the end-to-end evaluation on hardware has not been run)", "headline", "PARTIAL",
              [f"{RF}.ap.mean", "export.max_abs_diff", "attacks.cases_total", "s9.C_sf12_scarce.severity.reack.loss60.received_critical.mean"],
              [(f"{RF}.sys_f1op_recall.mean", 3), (f"{RF}.sys_f1op_fpr.mean", 3), ("export.max_abs_diff", -2), ("export.decision_agreement", 6),
               ("attacks.cases_matching_expected", -1), ("attacks.cases_total", -1),
               ("s9.C_sf12_scarce.severity.reack.loss60.received_critical.mean", 3), ("s9.C_sf12_scarce.fixed3.reack.loss60.received_critical.mean", 3),
               ("hw.H1", 0), ("hw.H2", 0), ("hw.H3", 0), ("hw.H4", 0), ("hw.H5", 0), ("hw.H6", 0)],
              "The end-to-end hardware evaluation (H1 to H6) has not been run. The software parts (detector, C export, packet and verifier, delivery simulation) exist and are tested. Impact direction has software evidence only as a front-against-side check on NHTSA crash tests (N17, supporting only); VZCrash has no direction labels.",
              "Each part has close prior work (N1 to N5; Balfaqih et al. 2022 (abstract only) combine a microcontroller classifier, severity, crash side and a GSM alert; Zhong and Nie 2024 confirmed LoRa messaging with ACK; Wei et al. 2023 and Tomic et al. 2020 on LoRa priority and duty cycle). We found no source that combines all of them with authentication and a duty-cycle budget and evaluates the combination end to end; a search cannot prove that none exists.",
              "The claim rests on hardware results that do not exist yet. Until H1 to H6 are run it is built, not yet measured: a plan with tested software parts, not a result. The combination is the only novelty candidate and it has no hardware evidence."),
        Point("N8", "Dataset audit: identical recordings across the official VZCrash splits", "rigour", "SUPPORTED",
              ["leakage.exact_hash_groups_across_splits", "leakage.test_events_flagged.total"],
              [("leakage.exact_hash_groups_across_splits", -1), ("leakage.exact_hash_duplicates_total", -1), ("leakage.test_events_flagged.total", -1),
               ("leakage.test_events_flagged.crash", -1), (f"{RF}.ap.mean", 3), (f"{RF}.supplied_ap.mean", 3),
               (f"{RF}.sys_f1op_recall.mean", 3), (f"{RF}.supplied_sys_f1op_recall.mean", 3),
                  ("dupscan.neardup.n_scanned", -1), ("dupscan.neardup.n_both", -1), ("dupscan.neardup.n_both_new", -1), ("dupscan.neardup.n_both_new.crash", -1), ("dupscan.rf15.mean5.diff_supplied_minus_dedup.sys_recall", 4),
                  ("dupscan.rf15.mean5.diff_supplied_minus_dedup.sys_recall_lo", 4), ("dupscan.rf15.mean5.diff_supplied_minus_dedup.sys_recall_hi", 4), ("dupscan.rf15.mean5.dedup.sys_recall", 3), ("dupscan.rf15.mean5.dedup_nd.sys_recall", 3),
                  ("dupscan.rf15.mean5.diff_supplied_minus_dedup_nd.sys_recall", 4), ("dupscan.rf15.mean5.diff_supplied_minus_dedup_nd.sys_recall_lo", 4), ("dupscan.rf15.mean5.diff_supplied_minus_dedup_nd.sys_recall_hi", 4)],
              "Cannot say whether the repeats come from the same vehicle (no vehicle ID in the release) or from one recording stored under several event IDs. The paper states (Section III-B) splits \"strictly separated by vehicle\"; we do not claim leakage by vehicle, only that identical recordings appear across the released splits. The dataset authors should be asked whether they come from the export.",
              "Leakage and de-duplication audits exist for other datasets; none found for VZCrash. The VZCrash paper claims vehicle-level separation and does not mention duplicates.",
              "Medium. The match is on exact identical arrays and a near-neighbour rule, so it may be a dataset export artefact rather than leakage by vehicle. Confirm with the authors before publishing."),
        Point("N9", "Trigger-aware evaluation: system-level recall including the trigger stage", "rigour", "SUPPORTED",
              [f"{RF}.sys_f1op_recall.mean", "trigger.trig_2.crash.rate"],
              [("trigger.trig_1.5.crash.rate", 3), ("trigger.trig_2.crash.rate", 3), ("trigger.trig_3.crash.rate", 3),
               ("trigger.trig_2.near_miss.rate", 3), ("trigger.trig_2.normal_driving.rate", 3),
               (f"{RF}.f1op_recall.mean", 3), (f"{RF}.sys_f1op_recall.mean", 3), (f"{RF}.f1op_fpr.mean", 3), (f"{RF}.sys_f1op_fpr.mean", 3),
               ("trigger_sweep.trig_1.5.all.rf15.sys_f1op_recall.mean", 3), ("trigger_sweep.trig_3.all.rf15.sys_f1op_recall.mean", 3),
               ("vzcrash.crash_events_peak_below_2g", -1), ("errors.crashes_not_triggered_test", -1)],
              "The trigger level and sensor range are placeholders until firmware v2 values arrive. The dataset events were already selected by on-device thresholds, so trigger rates are conditional and not continuous driving. The trigger itself is not run on the car (H2).",
              "Taccari et al. (ITSC 2018) evaluate a random forest on events already selected by trigger algorithms; Kubin et al. (2021, opened) build a threshold baseline against a neural model; the VZCrash paper evaluates on a real-world event population; patents describe two-stage crash analysis. We found no public report of system-level recall including a trigger sweep and intervals on VZCrash.",
              "Medium. This extends existing two-stage practice with measured numbers; it should be worded as an evaluation, not a new method."),
        Point("N12", "Retry versus replay: an independent re-discovery of a known LoRaWAN issue in a custom point-to-point link, with a bounded fix", "design", "SUPPORTED",
              [k for k in (k_strict, k_reack) if k] or ["attacks.missing"],
              [(k, 0) for k in (k_strict, k_reack, k_old) if k] +
              [("attacks.cases_total", -1), ("attacks.cases_matching_expected", -1),
               ("s9.A_sf7_normal.fixed3.strict_same_counter.loss30.acked_all.mean", 3), ("s9.A_sf7_normal.fixed3.reack.loss30.acked_all.mean", 3),
               (f"{f}.no_limit.reack_airtime_s", 1), (f"{f}.with_limit.reack_airtime_s", 1),
               (f"{f}.no_limit.genuine_alert_during_flood", 0), (f"{f}.with_limit.genuine_alert_during_flood", 0)],
              "Real radios (H4): the suite is a software simulation. The limit reduces the cost of a replay flood but does not remove it. The remembered-alert count and the retry interval are design values that firmware must confirm.",
              "The conflict is known in LoRaWAN: a ChirpStack maintainer wrote in June 2021 (opened) that in version 1.0 a replay cannot be told from a retransmission, so retransmitted confirmed uplinks are not acknowledged; version 1.1 adds the uplink channel to the MIC.",
              "High. We re-found a known problem in our own link; the bounded fix (an idempotent re-ACK limited to one per event per retry interval and paid from the base's duty-cycle budget) is tested only in software."),
        Point("N10", "Size against accuracy on the MCU, with C-export equivalence", "design", "SUPPORTED",
              ["gap.rf200_minus_rf15.ap", "export.max_abs_diff", "s4b.recommended.depth"],
              [("gap.rf200_minus_rf15.ap", 4), ("gap.gbt_minus_rf15.ap", 4), ("s4.depth6.trees15.ap.mean", 3), ("s4.depth6.trees200.ap.mean", 3),
               ("s4b.recommended.trees", -1), ("s4b.recommended.depth", -1), ("s4b.chosen.ap_test.mean", 3), ("s4b.chosen.ap_test.std", 3), (f"s4b.t{rt}.d{rd}.ap_val.mean", 3), (f"s4b.t{rt}.d{rd}.flash_est", -1),
               ("export.bytes_est", -1), ("export.max_abs_diff", -2), ("export.decision_agreement", 6)],
              "ESP32 flash, RAM and time per call (H5; `benchmark_rf.ino` is built, not yet measured). The size is a host estimate. The deployed model has not been changed to the recommended configuration.",
              "Accuracy-memory trade-offs for random forests are studied (Buschjäger and Morik, 2021) and tools that export forests to C exist (emlearn).",
              "High. The ingredients are standard; the value is the measured numbers on real crash data, not the method."),
        Point("N4", "Severity-aware delivery under a 10% duty-cycle budget", "component", "PARTIAL",
              ["s9.C_sf12_scarce.severity.reack.loss60.received_critical.mean", "lora.sf12.alerts_per_hour"],
              [("s9.C_sf12_scarce.severity.reack.loss60.received_critical.mean", 3), ("s9.C_sf12_scarce.fixed3.reack.loss60.received_critical.mean", 3),
               ("s9.C_sf12_scarce.severity.reack.loss60.received_all.mean", 3), ("s9.C_sf12_scarce.fixed3.reack.loss60.received_all.mean", 3),
               ("s9.C_sf12_scarce.severity.reack.loss30.median_ack_s_critical.mean", 1), ("s9.C_sf12_scarce.fixed3.reack.loss30.median_ack_s_critical.mean", 1),
               ("lora.sf7.alerts_per_hour", -1), ("lora.sf12.alerts_per_hour", -1), ("hw.H3", 0)],
              "H3 (20 alerts each at 10, 50 and 100 m) and the firmware retry settings. The simulation assumptions (severity mix, retry limits, loss model) are ours. The 10% duty cycle is not verified against WPC/DoT. The critical-alert result is from one scenario (a standard deviation over runs, no interval) and all-alert reception is lower with the severity policy than with the fixed policy in it (both values are in the evidence). Severity measured against impact strength is not in the hardware plan.",
              "Priority-aware LoRa scheduling for emergencies (Osaka University group, snippet only), a severity-scored alert routing table in paper 16 of the project set, duty-cycle budgets kept for high-priority events, and LoRaWANSim studies of ACKs and retransmission counts exist.",
              "High. The policy idea is known; the evidence we can add is a crash-alert replay now (with the real, almost all Low, VZCrash mix as a caveat) and measured delivery after H3."),
        Point("N1", "Real-crash-trained detector on a cheap MCU, with a transfer test to the scale model", "component", "PARTIAL",
              [f"{RF}.ap.mean", "export.max_abs_diff"],
              [(f"{RF}.ap.mean", 3), (f"{RF}.sys_f1op_recall.mean", 3), (f"{RF}.sys_f1op_fpr.mean", 3), ("export.max_abs_diff", -2),
               ("export.decision_agreement", 6), ("export.bytes_est", -1), ("scalefree.rf15.ap_kept_share", 3), ("hw.H2.transfer", 0), ("export.benchmark_us_per_call", 0)],
              "The transfer test inside H2 (VZCrash to the scale model) and H5 (flash, RAM, time per call on the ESP32).",
              "TinyML crash-detection projects exist (Kapalamula, 2024, Arduino Nano 33 BLE); a random forest on an Arduino Nano 33 BLE with flash (`88 KB`) and RAM (`162 KB`) reported exists for plate impacts (Katsidimas et al. 2023, opened); a CART severity classifier on a microcontroller is reported (Balfaqih et al. 2022, abstract only); forest-to-C exporters exist (emlearn). The VZCrash paper (opened) tested no tree models and ran no embedded test: the forest is evaluated where it left a gap. We found none tested for transfer to a scale model.",
              "Medium to high. A forest on a microcontroller with flash and RAM reported has precedent; the transfer test is the distinctive part and it is NOT_RUN."),
        Point("SF", "Scale-free features keep most of the AP (a hypothesis for the transfer argument in N1; the physical-scaling check in N23 shows them not invariant)", "component", "PARTIAL",
              ["scalefree.rf15.ap_kept_share"],
              [("scalefree.rf15.ap_kept_share", 3), ("scalefree.rf200.ap_kept_share", 3), ("scalefree.gbt.ap_kept_share", 3), ("scalefree.lr.ap_kept_share", 3),
               ("scalefree.rf15.ap_drop", 4), ("hw.H2.transfer", 0)],
              "The transfer test inside H2: whether the scale-free subset transfers better than all features on the scale model.",
              "No direct prior work found.",
              "Medium. The argument is a hypothesis until the transfer test is run."),
        Point("N3", "HMAC, anti-replay counter and signed ACK on the MCU, with the spoofed-ACK case", "component", "PARTIAL",
              ["attacks.cases_total", "attacks.cases_matching_expected"],
              [("attacks.cases_total", -1), ("attacks.cases_matching_expected", -1), ("attacks.forgery_probability_per_guess", -2), ("hw.H4", 0)],
              "H4: the attack table measured on the radios (3 tries per case) and the ESP32 verify time (H5).",
              "LoRaWAN already authenticates frames with a MIC and a counter, and an ESP32 component (embedblocks msg_auth, opened) wraps messages with HMAC-SHA256, an epoch and a counter and rejects replays, leaving ACKs and retransmission to the application.",
              "Very high. Each mechanism is standard and an ESP32 HMAC-counter component exists; only the specific alert and ACK layout, the attack suite and the retry fix are ours."),
        Point("N2", "Impact side and angle from one IMU in the alert", "component", "NOT_YET", [],
              [("hw.H1", 0)],
              "H1 (10 hits on each of 4 sides and 10 vertical drops). VZCrash has no direction labels, so there is no software evidence.",
              "Impact segment and direction from one phone IMU on an RC car (Ebert et al. 2016, opened), crash sides reported by a microcontroller system (Balfaqih et al. 2022, abstract only), and the principal direction of force from consumer MEMS in a full-size crash (Tadic and Vukajlovic 2016, opened). US 9,162,642 was seen as a snippet only.",
              "Very high as a method. N2 is a supporting feature, not a contribution; it stays NOT_YET until H1 is run (and see N17 for the software check on NHTSA tests)."),
        Point("N5", "Measured stage-by-stage latency against HTTP, MQTT and CoAP", "component", "NOT_YET", [],
              [("hw.protocol.HTTP.latency_ms_max", 0), ("hw.protocol.MQTT.latency_ms_max", 0), ("hw.protocol.CoAP.latency_ms_max", 0), ("hw.H5", 0), ("hw.H3", 0)],
              "The protocol latencies are measured (HARDWARE) but the stage-by-stage breakdown (H5) and LoRa latency (H3) are NOT_RUN.",
              "Protocol comparisons in vehicular settings exist (IETF MAPRG slides); no stage-by-stage crash-alert breakdown found.",
              "Medium."),
        Point("N6", "Open labelled scale-model dataset", "component", "NOT_YET", [],
              [("hw.H2", 0)],
              "The hw_events and hw_windows files from H1 to H3 and a release licence.",
              "RC-car data exist (Ebert et al. 2016, opened) and open impact datasets exist (Katsidimas et al. 2023, plate impacts on Zenodo, opened); no open labelled CrashGuard-style scale-model crash set was found, and none is built.",
              "Weak as a contribution: RC-car and open-dataset precedents exist. It would be a data release, and it needs the author's data."),
        Point("N7", "Measured value of a cheap vibration-sensor array", "component", "NOT_YET", [],
              [("hw.H6", 0)],
              "H6 (SW-420 ablation, a re-analysis of H1 and H2). The report says 6 sensors and the plan says 5: confirm.",
              "Hobby projects use the SW-420; no measured ablation found.",
              "Medium."),
        Point("N13", "Physics-based severity (delta-V + ASI) from one IMU window, carried in the authenticated alert, with a measured requirement on accelerometer range and rate (NHTSA crash tests, mostly high-speed barrier tests, not representative of all real crashes)", "component", "PARTIAL",
              ["nhtsa.band_count.orig", "severity_synth.runs", "sevstudy.needed.point.min_range_g", "export_severity.vzcrash_test.mirror.windows"],
              [("sevstudy.n_tests", -1), ("sevstudy.grid.r16.f100.dv_within10", 2), ("sevstudy.grid.r16.f100.dv_within10_lo", 2), ("sevstudy.grid.r16.f100.dv_within10_hi", 2),
               ("sevstudy.needed.point.min_range_g", 0), ("sevstudy.needed.point.min_rate_hz", 0), ("sevstudy.grid.r64.f200.dv_within10", 2), ("sevstudy.grid.r64.f200.dv_within10_lo", 2),
               ("sevstudy.grid.r32.f400.dv_within10", 2), ("sevstudy.part6.dv_within10", 2), ("sevstudy.part0.dv_within10", 2),
               ("sevstudy.release.heldout.diff_median_abs_err_pct", 2), ("sevstudy.release.heldout.diff_hi", 2),
               ("nhtsa.band_count.orig", -1), ("nhtsa.band_count.hz100_clip", -1), ("severity_synth.fs100.clip_none.long.dv_within_tol_share", 2),
               ("export_severity.vzcrash_test.mirror.max_abs_diff.dv_res_kmh", -2), ("export_severity.vzcrash_test.mirror.class_mismatches", -1),
               ("severity_vzcrash.rollover.corrected.normal_driving.share", 4), ("severity_vzcrash.score.asi.ap", 3)],
              "Severity measured on the car with a wide-range accelerometer (not in the H1 to H6 plan), and a crash-test or sled comparison of the real sensor. The class limits and names, the ASI pre-filter (13 Hz) and the THIV flail distances are our choices or UNVERIFIED (docs/05_data_code/SEVERITY.md). "
              "The rollover flag is kept out of the class because it still fires on more than `0.5%` of normal driving.",
              "Event data recorders report delta-V and are checked against crash-test accelerometers (NHTSA EDR round robin, about 6% error in frontal pulses); delta-V and ASI from EDRs have been compared (SWOV); sampling-rate and range effects on peak acceleration are known. "
              "Tadic and Vukajlovic (2016, opened) estimated delta-V and the principal direction of force from consumer MEMS in a full-size crash and saw the low-G sensors saturate. "
              "We found no measured sweep of accelerometer range, sample rate and bandwidth against NHTSA crash tests with a held-out part, or a severity field inside an authenticated alert.",
              "High. Delta-V and ASI are established and low-cost MEMS delta-V has been shown. What is ours is the measured requirement (range and rate) on the NHTSA tests with intervals, and the severity fields in the signed alert."),
        Point("N14", "Clipping restoration for delta-V at low sensor range: a pulse-fit fill with a small ridge correction against spline restoration and plain integration (one range, re-split tests, not a blind test; fill + ridge was named primary after earlier results were seen; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes)", "component", "SUPPORTED",
              ["n14x.R.r16.M+.median", "n14x.R.r16.paired.M+_vs_SP.d_median_hi"],
              [("n14x.R.r16.B.median", 1), ("n14x.R.r16.SP.median", 1), ("n14x.R.r16.M.median", 1), ("n14x.R.r16.M+.median", 1),
               ("n14x.R.r16.paired.M+_vs_SP.d_median", 1), ("n14x.R.r16.paired.M+_vs_SP.d_median_lo", 1), ("n14x.R.r16.paired.M+_vs_SP.d_median_hi", 1),
               ("n14x.R.r16.paired.M+_vs_B.d_median", 1), ("n14x.R.r16.paired.M+_vs_B.d_median_lo", 1), ("n14x.R.r16.paired.M+_vs_B.d_median_hi", 1),
               ("n14x.G.r16.paired.M+_vs_SP.d_median_hi", 1), ("n14x.A.r16.paired.M+_vs_SP.d_median_hi", 1), ("n14x.O.r16.paired.M+_vs_SP.d_median_hi", 1),
               ("n14x.R.r16.B.p90", 1), ("n14x.R.r16.M+.p90", 1), ("n14x.R.r32.paired.M+_vs_SP.d_median_hi", 2), ("n14x.R.r32.paired.M+_vs_B.d_median_hi", 2),
               ("n14x.G.r32.paired.M+_vs_B.d_median_hi", 1), ("n14x.A.r32.paired.M+_vs_B.d_median_hi", 1), ("n14x.O.r32.paired.M+_vs_B.d_median_hi", 1),
               ("n14x.R.r64.paired.M+_vs_SP.d_median", 2), ("n14x.R.r64.paired.M+_vs_B.d_median_hi", 2),
               ("n14.r16.heldout.paired.M+.d_median_hi", 2), ("export_severity.n14.mirror.max_abs_diff.dv_fill_kmh", -2)],
              "A real saturated crash pulse from the sensor (hardware). At `+-32 g` and `+-64 g` no practically meaningful improvement was found on the three fixed splits (a few intervals clear zero by under one percentage point) (at +-32 g the repeated cross-validation interval against plain integration only just clears; against spline restoration it does not). The `90th`-percentile error is not lowered (the tail is worse). The estimator does not reach the 10% target at +-16 g.",
              "Spline restoration of clipped acceleration exists (Ruder et al.; tested by Chan et al. 2023, opened: 5th-order spline through 3 points each side, still underestimates peaks); US 7,643,921 estimates values beyond a vehicle sensor's limit from the slope of the measured data; `SAE 2025-01-5046` fits triangular, half-sine and haversine pulses to EDR delta-V; Tadic and Vukajlovic (2016, opened) saw low-G MEMS saturate in a real crash. The comparison with spline restoration was run here (docs/02_preregistration/ALGORITHMS.md, N14 extension).",
              "High. The idea of restoring clipped data is known. At +-16 g the fill with a ridge correction beat both plain integration and our spline baseline on four splits, but the sensor is a software model of crash-test records, the earlier held-out set had been seen before the re-splits (not a blind test), and the large-error tail is not improved. Worded as a comparison of restoration methods at one range."),
        Point("N15", "Trigger-aware training: joint selection, cost-sensitive training and a learned trigger raise system recall at a fixed false-alarm rate", "component", "NO_IMPROVEMENT_FOUND",
              ["n15.baseline.t1.test_recall.mean", "n15.a_joint.t1.paired_seedavg.d_recall"],
              [("n15.baseline.t1.test_recall.mean", 4), ("n15.baseline.t1.test_recall.std", 4), ("n15.a_joint.t1.paired_seedavg.d_recall", 4), ("n15.a_joint.t1.paired_seedavg.d_recall_lo", 4), ("n15.a_joint.t1.paired_seedavg.d_recall_hi", 4),
               ("n15.b_cost_sensitive.t1.paired_seedavg.d_recall", 4), ("n15.b_cost_sensitive.t1.paired_seedavg.d_recall_hi", 4), ("n15.b_cost_sensitive.t5.paired_seedavg.d_recall", 4), ("n15.b_cost_sensitive.t5.paired_seedavg.d_recall_hi", 4),
               ("n15.c_learned_trigger.t1.paired_seedavg.d_recall", 4), ("n15.a_joint.t1.paired.d_recall", 4), ("n15.a_joint.t1.paired.d_sys_ap", 3), ("n15.choice.a_joint.t1.trigger_g", 1)],
              "Nothing to add in software: no method beat the fixed 2.0 g trigger with a separate model beyond the interval. Continuous-driving data (not pre-selected events) would be needed to test a trigger at all.",
              "Cascade detectors and cost-sensitive early rejection are established in computer vision; two-stage threshold-then-model pipelines are established in crash detection (Kubin et al., 2021, opened; Taccari et al., 2018). Joint design with a fixed false-alarm budget on IMU crash data was not found in the sources checked.",
              "Not a contribution. Reported as a negative result: the difference of a single model draw looked positive and was not stable across seeds."),
        Point("N16", "Severity- and budget-aware delivery scheduler (reserve, severity-and-age order, ACK-feedback back-off, optional spreading-factor raise): improves on a fixed retry policy; against a severity table it does not clear zero in the original held-out scenarios and does in the later burst simulator (S5) (SIMULATED; two simulators with different scenario sets; supporting evidence, not a contribution)", "component", "PARTIAL",
              ["n16.chosen.rho", "n16.conclusion.C2_better_critical_than_fixed3.holds"],
              [("s5.heldout.default.diff.scheduler_minus_severity.delivered_critical", 3), ("s5.heldout.default.diff.scheduler_minus_severity.delivered_critical_lo", 3), ("s5.heldout.default.diff.scheduler_minus_severity.delivered_critical_hi", 3), ("s5.heldout.sf12.diff.scheduler_minus_severity.delivered_critical", 3), ("s5.heldout.capture_none.diff.scheduler_minus_severity.delivered_critical", 3),
                  ("s13.diff.r16.burst.P1b_minus_P1.reach30_critical", 3), ("s13.diff.r16.burst.P2_minus_P1b.reach10_critical", 3), ("n16.tuning.scenarios", -1), ("n16.chosen.rho", 1), ("n16.chosen.m", 1), ("n16.chosen.jitter", 1), ("n16.chosen.sf_raise", -1),
               ("n16.conclusion.C2_better_critical_than_fixed3.holds", -1), ("n16.conclusion.C2_better_critical_than_fixed3.cells", -1),
               ("n16.conclusion.C1_better_critical_than_table.holds", -1), ("n16.conclusion.C1_better_critical_than_table.cells", -1),
               ("n16.conclusion.C4_lower_p95_latency_critical_than_table.holds", -1), ("n16.conclusion.C6_less_budget_than_table.holds", -1),
               ("n16.effect.fixed3.critical.delivered.d", 3), ("n16.effect.fixed3.critical.delivered.d_lo", 3), ("n16.effect.fixed3.critical.delivered.d_hi", 3),
               ("n16.effect.table.critical.delivered.d", 3), ("n16.effect.table.critical.delivered.d_lo", 3), ("n16.effect.table.critical.delivered.d_hi", 3),
               ("n16.effect.table.critical.p95_lat_s.d", 1), ("n16.effect.table.critical.p95_lat_s.d_lo", 1), ("n16.effect.table.critical.p95_lat_s.d_hi", 1),
               ("n16.estimator.nhtsa_plain.est_iid50_sf7.scheduler.delivered_critical", 3), ("n16.estimator.nhtsa_sat.est_iid50_sf7.scheduler.delivered_critical", 3)],
              "H3 on hardware (delivery at 10, 50 and 100 m) and the loss-against-spreading-factor relation, which is assumed here. Against the severity table the scheduler's gain in critical delivery does not clear zero and its critical `95th`-percentile latency is longer; the fixed 3-retry baseline is weak (every class gets the same 3 immediate tries, in arrival order), so the gain over it is expected. N16 is supporting evidence (SIMULATED), not a contribution.",
              "Priority-aware LoRa scheduling for emergencies exists (Osaka University group, seen as a snippet only), as do exponential back-off with jitter and duty-cycle budgets; the specific combination was not found in the sources opened.",
              "High. Standard techniques. Held-out: better than the weak fixed policy, not better than the severity table (critical delivery gain not above zero; critical p95 latency worse). Not listed among the contributions."),
        Point("N17", "Impact direction (front against side) from one low-rate IMU, checked on NHTSA crash tests (validation of a supporting feature, not a contribution; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes)", "extra", "SUPPORTED",
              ["x1.A.r16.balanced_acc_lo", "x1.A.r16.baseline_balanced_acc"],
              [("x1.n_tests.frontal.front", -1), ("x1.n_tests.side.side", -1), ("x1.A.window_chosen_ms", -1), ("x1.A.r16.balanced_acc", 3), ("x1.A.r16.balanced_acc_lo", 3), ("x1.A.r16.balanced_acc_hi", 3),
               ("x1.A.r16.baseline_balanced_acc", 2), ("x1.A.r64.balanced_acc_lo", 3), ("x1.G.r16.balanced_acc_lo", 3), ("x1.A.r16.angle_err.frontal.median_deg", 1), ("x1.A.r16.angle_err.side.median_deg", 1),
               ("x1.A.r16.failures", -1), ("x1.n_rear_instrumented", -1), ("x1.n_right_side", -1)],
              "Rear and right impacts (no instrumented tests exist), the oblique angle (fewer than 10 tests) and a lateral sign that is not calibrated on the same tests. The hardware test H1 (10 hits on each of 4 sides) is the real check.",
              "Principal direction of force from in-vehicle accelerometers is established: Kusano and Gabler (2013, abstract opened, crash tests and real collisions), Tadic and Vukajlovic 2016 (opened), Ebert et al. 2016 (phone IMU on an RC car, opened).",
              "Very high as a method. Reported as validation of a supporting feature on two classes: front against side on held-out vehicle groups."),
        Point("N18", "Severity measures against dummy injury criteria: delta-V adds no positive association beyond impact speed for frontal chest and head criteria (the partial association with chest acceleration is small and negative); ASI tracks chest acceleration (descriptive, small sample, NHTSA tests)", "extra", "NO_IMPROVEMENT_FOUND",
              ["x2.frontal.pos01.clip3m.orig.dv.partial", "x2.frontal.pos01.hic.orig.dv.partial"],
              [("x2.avail.frontal.pos01.clip3m", -1), ("x2.frontal.pos01.clip3m.orig.dv.partial", 2), ("x2.frontal.pos01.clip3m.orig.dv.partial_hi", 2), ("x2.frontal.pos01.hic.orig.dv.partial_hi", 2),
               ("x2.frontal.pos01.clip3m.orig.asi.rho", 2), ("x2.frontal.pos01.clip3m.orig.asi.partial_lo", 2), ("x2.side.pos01.hic.orig.dv.partial_lo", 2), ("x2.frontal.dv_vs_speed.orig.rho", 2),
               ("x2.limit.frontal.clip3m.share_exceeding_all", 3), ("x2.limit.side.hic.share_exceeding_all", 3)],
              "More tests with dummy criteria, human-injury outcomes, and the TTI(d) and pelvis limits of the old side-impact dummy (UNVERIFIED, not in the current FMVSS `214` text). Dummy criteria are test measurements, not human injury.",
              "NHTSA and ESV literature reports that HIC and chest g were poor predictors of field injury and that delta-V alone does not capture pulse shape (snippets only). No source opened compares delta-V and ASI with dummy criteria with speed partialled out.",
              "Low. A descriptive result on about `50` frontal tests and `60` side tests; the primary frontal question is a null result."),
        Point("N19", "Early classification: a sequential early-exit rule over six length-specific forests decides about one second earlier (mean over triggered crash events, both false-alarm targets). The part that clears its interval is the time saving; the recall gain over the single full-length forest is an ensemble effect, not an early-exit effect (VZCrash, second trigger on pre-selected events; timing read from the window length, no ESP32 timing)", "extra", "SUPPORTED",
              ["s6.a1.mean5.d.E_minus_Ep.time", "s6.a5.mean5.d.Ep_minus_F.recall_lo"],
              [("s6.a1.mean5.d.E_minus_Ep.time", 0), ("s6.a1.mean5.d.E_minus_Ep.time_lo", 0), ("s6.a1.mean5.d.E_minus_Ep.time_hi", 0), ("s6.a5.mean5.d.E_minus_Ep.time", 0),
               ("s6.a1.mean5.d.Ep_minus_F.recall", 4), ("s6.a1.mean5.d.Ep_minus_F.recall_lo", 4), ("s6.a1.mean5.d.Ep_minus_F.recall_hi", 4),
               ("s6.a5.mean5.d.Ep_minus_F.recall", 4), ("s6.a5.mean5.d.Ep_minus_F.recall_lo", 4), ("s6.a5.mean5.d.Ep_minus_F.recall_hi", 4),
               ("s6.a1.mean5.d.A_minus_F.recall", 4), ("s6.a5.mean5.d.A_minus_F.recall", 4), ("s6.a1.seed42.d.Ep_minus_F.recall", 4), ("x3.mcu.cycles_per_sample_assumed", -1)],
              "Hardware: the incremental feature cost on the ESP32 (NOT_RUN), the real decision time, and continuous-driving data (VZCrash events were already selected on the device).",
              "Early decisions are standard in airbag algorithms (milliseconds, restraint control, calibrated on crash pulses) and early-exit rules are standard in sequential classification; patents on crash detection in sensors were seen as snippets. No source opened reports a fixed-false-alarm early-exit evaluation on VZCrash.",
              "High. The ingredients are standard. At the 1% target the recall gain over the single forest comes from using six forests, not from exiting early (the same forests released at the full window length give the same alarms), and it varies by seed; a single forest cut at the early-exit time loses recall at 1%. At the 5% target the gain is too small to matter (numbers above)."),
        Point("N20", "Guaranteed false-alarm control by split-conformal thresholds: the guarantee does not hold on the de-duplicated test set and the threshold is no better than the validation threshold", "extra", "NO_IMPROVEMENT_FOUND",
              ["x4.a5.n1000.conformal.fa_mean_lo", "x4.a5.nall.recall_diff_conformal_minus_validation"],
              [("n20c.dirty.a5.nall.conformal.fa_mean", 4), ("n20c.hashgroup.a5.nall.conformal.fa_mean", 4), ("n20c.hashgroup.a5.nall.conformal.fa_mean_lo", 4), ("n20c.hashgroup.a5.nall.conformal.fa_mean_hi", 4), ("n20c.clean.a5.nall.conformal.fa_mean", 4), ("n20c.clean.a5.nall.conformal.fa_mean_lo", 4), ("n20c.clean.a5.nall.conformal.fa_mean_hi", 4), ("n20c.clean.a1.nall.conformal.fa_mean", 4), ("n20c.clean.a5.test_se", 4),
                  ("x4.a1.n1000.conformal.fa_mean", 4), ("x4.a1.n1000.conformal.fa_mean_lo", 4), ("x4.a5.n1000.conformal.fa_mean", 4), ("x4.a5.n1000.conformal.fa_mean_lo", 4), ("x4.a5.n1000.validation.fa_mean", 4),
               ("x4.a5.nall.recall_diff_conformal_minus_validation", 4), ("x4.shift.a5.leave_one_category_out.Heavy.conformal.fa_mean", 4), ("x4.shift.a1.leave_one_category_out.Heavy.conformal.fa_mean", 4)],
              "Calibration data that are exchangeable with deployment data (validation and test differ here; the validation split may repeat training events). Weighted and size-stratified calibration were tried (n20c, T7, EXPLORATORY): none restores the guarantee at `5%`; the widened-margin variant is within one standard error of it, so the fair reading is that it is not established.",
              "Split-conformal anomaly detection with a marginal false-alarm guarantee is established (snippets only); weighted conformal prediction exists for shift.",
              "Not a contribution. A limitation study: the guarantee needs exchangeability, which VZCrash splits and vehicle-size shift break."),
        Point("N21", "Sensor-spoofing robustness: a bounded added signal can make non-crash windows alarm from about `0.5` g; simple defences help a little against false crashes at small budgets and cost on hidden crashes (simulation on dataset windows)", "extra", "PARTIAL",
              ["x5.net.a.baseline.eps0.5.structured", "x5.diff.a.D4_physics_ensemble.eps0.5.any_hi"],
              [("x5.net.a.baseline.eps0.5.structured", 3), ("x5.net.a.baseline.eps2.any", 3), ("x5.net.b.baseline.eps2.any", 3), ("x5.diff.a.D4_physics_ensemble.eps0.5.any", 3), ("x5.diff.a.D4_physics_ensemble.eps0.5.any_hi", 3),
               ("x5.diff.b.D4_physics_ensemble.eps0.5.any", 3), ("x5.clean_recall_loss.D4_physics_ensemble", 3), ("x5.clean_recall_loss.D1_median", 3), ("x5.diff.b.D3_adversarial_training.eps1.any", 3)],
              "Whether a real signal could be delivered to a sensor in a car (not studied), attacks adapted to each defence beyond the search used, and hardware. Defences were not combined.",
              "Acoustic and resonant injection into MEMS accelerometers and gyroscopes is published (Tu et al. 2018, opened; Son 2015 and Trippel 2017 cited there, not opened). No source opened evaluates a crash detector's decision against a bounded added signal.",
              "High. The threat premise is published; the evaluation is ours and covers one detector on stored windows. No defence is claimed as general."),
        Point("N22", "Many-car LoRa capacity: at SF7 and the low default alert rate the channel, not the base's ACK duty budget, limits delivery up to `500` cars (at SF12 and high alert rates both limits are large); spaced retries recover most of a burst in the X6 simulator (analytical and simulated)", "extra", "PARTIAL",
              ["x6.analytic.sf12.base_acks_per_hour", "x6.sim.sf7.hb600.n100.r0.1.burst.scheduler.delivered_critical"],
              [("s5.a4.scheduler_vs_severity.delivered_critical.n_better", -1), ("s5.heldout.burst60.diff.scheduler_minus_severity.delivered_critical", 3), ("s5.heldout.hbpayload26.diff.scheduler_minus_severity.delivered_critical", 3), ("s5.heldout.sf9.diff.scheduler_minus_severity.delivered_critical", 3),
                  ("x6.analytic.sf7.base_acks_per_hour", 0), ("x6.analytic.sf12.base_acks_per_hour", 0), ("x6.sim.sf7.hb600.n500.r0.1.steady.severity.delivered_critical", 3), ("x6.sim.sf12.hb600.n200.r0.1.steady.severity.delivered_critical", 3),
               ("x6.sim.sf12.hb600.n200.r0.1.steady.severity.base_ack_airtime_share", 3), ("x6.sim.sf7.hb600.n100.r0.1.burst.severity.delivered_critical", 3), ("x6.sim.sf7.hb600.n100.r0.1.burst.scheduler.delivered_critical", 3),
               ("x6.sim.sf7.hb600.n100.r0.1.burst.critical_delivery_diff_scheduler_minus_severity", 3)],
              "Hardware and a multi-node field test (H3 covers one link only); the capture rule, the heartbeat payload, the stress alert rate and the burst size are assumed.",
              "Duty-cycle blackout periods for event-triggered traffic (Tomic et al. 2020, opened); priority-based spreading-factor allocation under a 1% duty cycle (Wei et al. 2023, opened); confirmed messaging with a local ACK (Zhong and Nie 2024, opened); ALOHA and capture analyses of LoRa (snippets only).",
              "High. Standard ALOHA formulas; the simulation of retry policies with a duty-limited acknowledging base under bursts rests on assumptions and is supporting evidence only."),
        Point("N23", "Scale-model transfer by physical scaling of VZCrash events: amplitude dominates, the scale-free features are not invariant (a plausibility check, no claim)", "extra", "PARTIAL",
              ["x7.filtered.a1.tau1.all.recall.seed42", "x7.filtered.a0.5.tau1.all.recall.mean"],
              [("x7.filtered.a1.tau1.all.recall.seed42", 3), ("x7.filtered.a0.5.tau1.all.recall.mean", 3), ("x7.filtered.a2.tau1.all.fa.mean", 3), ("x7.filtered.a4.tau1.scale_free.sys_ap.mean", 3), ("x7.filtered.a4.tau1.all.sys_ap.mean", 3),
               ("x7.filtered.a1.tau0.25.all.short_pulse_share.mean", 2)],
              "Hardware transfer test H2 on the author's car. This check cannot predict performance on the car.",
              "Scaling laws for acceleration and time in scale-model crash tests and RC-car experiments exist (snippets only).",
              "Not a contribution. A plausibility check that shows the detector's dependence on amplitude and the Nyquist problem for compressed pulses."),
        Point("N11", "False-positive rate on near_miss events alone (a results breakdown, not a contribution)", "breakdown", "SUPPORTED",
              [f"{RF}.sys_f1op_fpr_near_miss.mean", f"{RF}.sys_f1op_fpr_normal.mean"],
              [(f"{RF}.sys_f1op_fpr_near_miss.mean", 3), (f"{RF}.sys_f1op_fpr_normal.mean", 3), (f"{RF}.sys_f1op_fpr.mean", 3),
               (f"s2.{P}.all.gbt.sys_f1op_fpr_near_miss.mean", 3), (f"s2.{P}.all.rf200.sys_f1op_fpr_near_miss.mean", 3),
               ("confusion3.rf15.near_miss.triggered_pred_crash", -1)],
              "In these results near_miss events are not harder than normal_driving events (their false-alarm rate is not higher), so a 'hard negative' framing is not supported by the numbers. Real-world prevalence is far lower than in VZCrash.",
              "The VZCrash paper treats near-miss as negative and reports false-positive counts on a real-world population but not a near-miss-only rate. Phone crash-detection studies report false-positive rates (Hongo et al., 2023).",
              "Not a contribution. Reported as a transparent breakdown next to the overall false-alarm rate."),
        Point("N24", "Conformal intervals for the clipped delta-V estimate: coverage is about nominal, but the class rule built on them (report the class below when the lower bound is lower, plus a flag) raises under-estimation instead of lowering it (grouped CV+, NHTSA tests, no simulation)", "extra", "NO_IMPROVEMENT_FOUND",
              ["n24.r16.nom90.coverage", "n24.r16.nom90.under_drop_hi"],
              [("n24.r16.nom80.coverage", 3), ("n24.r16.nom80.coverage_lo", 3), ("n24.r16.nom80.coverage_hi", 3), ("n24.r16.nom90.coverage", 3), ("n24.r16.nom90.width_kmh_median", 1), ("n24.r16.nom90.in_one_class_share", 3),
               ("n24.r16.nom80.under_point", 3), ("n24.r16.nom80.under_decision", 3), ("n24.r16.nom80.under_drop", 3), ("n24.r16.nom80.under_drop_lo", 3), ("n24.r16.nom80.under_drop_hi", 3), ("n24.r64.nom80.width_kmh_median", 1)],
              "More tests, tests that are not high-speed barrier tests, and an interval around the ASI as well as around delta-V.",
              "Conformal prediction for crash injury severity classes exists on police records (CHOIR, abstract page opened); jackknife+ and CV+ are generic (abstract page opened); conformal intervals around a clipped-sensor estimate were not found (snippets only).",
              "Medium. The coverage result is a calibration check; the class rule was the preregistered use and it failed. The intervals at the low range are wide."),
        Point("N25", "Prevalence-adaptive alert threshold: the existing threshold gives very low precision at realistic prevalence, but no tested rule (prior-shift adjusted, minimum expected cost, target precision) raises precision within five points of recall at prevalences up to one per cent (VZCrash pools resampled; costs are assumptions)", "extra", "NO_IMPROVEMENT_FOUND",
              ["s10.rf15.pi0p02pct.a.ppv", "s10.rf15.pi1pct.d50.recall"],
              [("s10.rf15.pi0p02pct.a.ppv", 4), ("s10.rf15.pi0p02pct.a.recall", 3), ("s10.rf15.pi0p02pct.d10.recall", 3), ("s10.rf15.pi0p02pct.d10.ppv", 3), ("s10.rf15.pi1pct.a.ppv", 3), ("s10.rf15.pi1pct.d50.recall", 3), ("s10.rf15.pi1pct.d50.ppv", 3),
               ("s10.rf15.pi0p02pct.em_prior_over_known", 2), ("s10.rf15.pi16pct.b_known.d_ppv_vs_a", 3)],
              "A prevalence among all driving (VZCrash events were pre-selected on the device), real costs, and calibrated probabilities (the forest probabilities were calibrated by isotonic regression on validation).",
              "Prior-shift correction by EM (Saerens, Latinne and Decaestecker 2002, abstract page opened) and cost-sensitive thresholds (Elkan 2001, summary page opened) are established; applying them to crash-alert precision at low prevalence was not found.",
              "Low as a contribution: established methods; the result is a quantified trade-off between recall and precision and a negative decision-rule result."),
        Point("N26", "Severity-Classified Transmission (SCT): a fast path with a short authenticated flash, a spaced-retry rule and no hold for Critical alerts raises critical reach within ten seconds in bursts, also against a severity table with spaced retries; against the severity table it does not help in steady state (it does against the spaced-retry table, whose spacing costs reach there) and it is worse than the table for a single car at high loss (EXPLORATORY); in ablations (EXPLORATORY) the flash, the hold and the spreading-factor raise carry the gain, while the reserved duty share and the CANCEL message show no effect on reach, and faster retries repair the single-car case but cost reach in bursts (SIMULATED; one-hour duty rule, parameters tuned on separate scenarios)", "extra", "PARTIAL",
              ["s11.diff.r16.burst.P2_minus_P1.reach10_critical", "s13.decision.r16.sct_improves_on_spaced_table"],
              [("s11.diff.r16.burst.P2_minus_P1.reach10_critical", 3), ("s11.diff.r16.burst.P2_minus_P1.reach10_critical_lo", 3), ("s11.diff.r16.burst.P2_minus_P1.reach10_critical_hi", 3), ("s11.diff.r16.steady.P2_minus_P1.reach10_critical", 3),
               ("s11.diff.r16.steady.P2_minus_P1.reach10_critical_lo", 3), ("s13.diff.r16.burst.P2_minus_P1b.reach10_critical", 3), ("s13.diff.r16.burst.P2_minus_P1b.reach10_critical_lo", 3), ("s13.diff.r16.burst.P2_minus_P1b.reach10_critical_hi", 3),
               ("s11.exploratory.single_car.loss60.P1.reach10_critical", 3), ("s11.exploratory.single_car.loss60.P2.reach10_critical", 3), ("s11.duty.runs_exceeding_limit", -1), ("s11.tuned.h_s", 1), ("s11.tuned.rho_f", 2),
               ("t9.diff.burst_base.P2.no_flash_minus_full.reach10_critical", 3), ("t9.diff.burst_base.P2.no_hold_minus_full.reach10_critical", 3), ("t9.diff.burst_base.P2.quick_retries_minus_full.reach10_critical", 3), ("t4.b.loss60.P2_quick.reach10_critical", 3)],
              "Radio delivery on real hardware, real regulatory limits for India (not checked), the firmware implementation of the flash and CANCEL messages, and measured timing.",
              "Priority and urgent-packet handling in LoRaWAN exists (Tamang et al. 2022: urgent packets unconfirmed, separate sub-bands; opened); interrupt-style warning delivery in vehicular networks exists (Shao, Liew and Liang 2020, abstract opened); priority-based spreading-factor allocation and duty-cycle blackout studies (Wei 2023, Tomic 2020, opened earlier). A two-stage flash with signed ACKs and a severity-dependent hold was not found.",
              "Medium to high. The burst gain is partly retry spacing, which a spaced-retry table already gives; the ablations show the flash and the severity-dependent hold matter; all channel and traffic values are assumptions."),
        Point("N27", "Bounded model check of the alert protocol: within the stated bounds the counter, replay, re-ACK, signed-ACK and CANCEL rules hold against a bounded attacker; strict anti-replay without the re-ACK loses liveness; counters that are not persisted break replay protection and ACK matching (ANALYTICAL, a check of a model, not a proof of the firmware)", "extra", "PARTIAL",
              ["s12.ATT.design.S1_replay_or_forgery_accepted_as_new", "s12.LIVE.design.L1_no_ack_in_terminal_state"],
              [("s12.ATT.design.states", -1), ("s12.ATT.design.S1_replay_or_forgery_accepted_as_new", -1), ("s12.ATT.design.S2_spoofed_ack_stops_retries", -1), ("s12.ATT.design.S3_repeat_not_acked_or_budget_exceeded", -1), ("s12.ATT.design.S4_accepted_counters_not_increasing", -1),
               ("s12.ATT.design.C1_cancel_without_valid_signature", -1), ("s12.LIVE.design.L1_no_ack_in_terminal_state", -1), ("s12.LIVE.strict_anti_replay.L1_no_ack_in_terminal_state", -1),
               ("s12.REBB.base_no_persistence.S1_replay_or_forgery_accepted_as_new", -1), ("s12.REBC.car_no_persistence.S2_spoofed_ack_stops_retries", -1), ("s12.crosscheck.agree", -1), ("s12.crosscheck.cases", -1)],
              "TLC (TLA+) was not run; larger bounds; the firmware itself. The model has no event id, so one mapped attack case disagrees.",
              "Formal analyses of LoRaWAN exist with Scyther (Gao, Li and Ma 2019, opened), PAT (Dong et al. 2024, opened, includes replay and ACK spoofing) and Tamarin and ProVerif for the join procedure (Wesemeyer et al. 2020, record opened). A model of a custom point-to-point alert protocol with a re-ACK and a two-stage flash was not found.",
              "Low as a contribution; the value is a checked specification and the counterexamples."),
        Point("N28", "Uncertainty-aware SCT (UA-SCT): taking the class from the upper end of a conformal class interval lowers mis-triage of Severe and Critical events against the severity table (the preregistered hypotheses H-a and H-c hold; for H-b the escalation part holds and the airtime cap of P4 barely binds), at the cost of many more escalations of non-severe events; at equal escalation the same reduction is reached by lowering the thresholds of the plain table, and critical reach within 30 s in bursts is slightly lower than with plain SCT (SIMULATED on NHTSA class pairs, mostly high-speed barrier tests, not representative of all real crashes)", "extra", "NO_IMPROVEMENT_FOUND",
              ["ua.r16.a10.cc.paired.mis_triage_upper_minus_point", "s11.diff.r16.steady.P3_minus_P1.mis_triage", "t1.r16.decision.p3_wins_at_equal_escalation"],
              [("ua.r16.a10.cc.paired.mis_triage_upper_minus_point", 3), ("ua.r16.a10.cc.paired.mis_triage_upper_minus_point_lo", 3), ("ua.r16.a10.cc.paired.mis_triage_upper_minus_point_hi", 3), ("ua.r16.a10.cc.paired.escalation_upper_minus_point", 3),
               ("ua.r16.a10.cc.coverage", 3), ("ua.r16.a10.cc.width", 2), ("ua.r64.a10.cc.width", 2), ("ua.hc.reduction_16_minus_64", 3), ("ua.hc.reduction_16_minus_64_lo", 3), ("ua.hc.width_64_minus_16", 2),
               ("s11.diff.r16.burst.P3_minus_P2.reach10_critical", 3), ("s11.diff.r16.burst.P3_minus_P2.reach10_critical_lo", 3), ("s11.diff.r16.burst.P3_minus_P2.reach10_critical_hi", 3), ("s11.diff.r16.steady.P3_minus_P1.reach10_critical", 3),
               ("s11.tuned.phi", 2), ("s11.exploratory.false_alarm.fa5.P1.fa_tx_fast", 1), ("s11.exploratory.false_alarm.fa5.P3.fa_tx_fast", 1),
               ("t1.r16.mis_triage_p3_minus_p1e", 3), ("t1.r16.mis_triage_p3_minus_p1e_lo", 3), ("t1.r16.mis_triage_p3_minus_p1e_hi", 3), ("t1.r32.mis_triage_p3_minus_p1e", 3), ("t1.r32.mis_triage_p3_minus_p1e_lo", 3), ("t1.r32.mis_triage_p3_minus_p1e_hi", 3),
               ("t3.r16.sobs.break_even_ratio", 2), ("t3.r16.sobs.break_even_ratio_lo", 2), ("t3.r16.sobs.break_even_ratio_hi", 2), ("t14.H-a.p_holm", 4), ("t14.H-c.p_holm", 4)],
              "Hardware, real crash class distributions (NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes), and a measured cost of false escalations.",
              "Conformal prediction for crash injury classes on police records exists (CHOIR, abstract page opened); LoRaWAN priority handling exists (see N26). Using the upper end of a conformal class interval to select a transmission class was not found.",
              "Low as a contribution. The reduction against the table is real but comes from escalating many more events: with thresholds lowered to the same escalation the plain table does as well (T1), the interval family has the larger trade-off area (T2), and P3 is cheaper than the table with the current thresholds only if a missed severe event costs several times a false escalation, and not shown cheaper than the table with lowered thresholds (T3). The cap on the fast path never binds except at the slower spreading factor; the gain over plain SCT in delivery is small."),
    ] + V2N.points(r, Point)


def fmt(r: Res, key: str, d: int) -> str:
    e = r.r.get(key)
    if e is None:
        return f"`{key}` = missing"
    v = e["value"]
    if isinstance(v, str) or v is None:
        return f"`{key}` = {v}" + ("" if e["origin"] == v else f" ({e['origin']})")
    if isinstance(v, bool):
        return f"`{key}` = {v} ({e['origin']})"
    s = f"{v:.2e}" if d == -2 else (f"{int(v)}" if d == -1 else f"{v:.{d}f}")
    return f"`{key}` = {L}{s}{R_} ({e['origin']})"


def _val(r: Res, k: str):
    e = r.r.get(k)
    return e["value"] if e and isinstance(e["value"], (int, float)) and not isinstance(e["value"], bool) else None


def status_of(r: Res, p: Point) -> str:
    if p.status == "NOT_YET":
        return "NOT_YET"
    if p.pid in V2N.PIDS:
        return V2N.status(r, p.pid) if all(k in r.r and r.r[k]["origin"] != "NOT_RUN" for k in p.needs) else "NOT_YET"
    ok = all(k in r.r and r.r[k]["value"] != "NOT_RUN" and r.r[k]["origin"] != "NOT_RUN" for k in p.needs)
    if not ok:
        return "NOT_YET"
    if p.pid == "N14":  # SUPPORTED if at +-16 g fill + ridge beats BOTH plain and spline (whole grouped interval below zero) on all four splits; PARTIAL if on some; else NO_IMPROVEMENT_FOUND
        ok = []
        for sp in ("O", "G", "A", "R"):
            h1 = _val(r, f"n14x.{sp}.r16.paired.M+_vs_SP.d_median_hi")
            h2 = _val(r, f"n14x.{sp}.r16.paired.M+_vs_B.d_median_hi")
            ok.append(h1 is not None and h2 is not None and h1 < 0 and h2 < 0)
        return "SUPPORTED" if all(ok) else ("PARTIAL" if any(ok) else "NO_IMPROVEMENT_FOUND")
    if p.pid == "N17":
        return "SUPPORTED" if all((_val(r, f"x1.A.r{rg}.balanced_acc_lo") or 0) > (_val(r, f"x1.A.r{rg}.baseline_balanced_acc") or 1) for rg in (16, 32, 64)) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N18":  # delta-V adds beyond speed if the partial correlation interval is above zero for the frontal chest or head criterion
        lo = [_val(r, f"x2.frontal.pos01.{c}.orig.dv.partial_lo") for c in ("clip3m", "hic")]
        return "SUPPORTED" if any(x is not None and x > 0 for x in lo) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N19":
        ok = [(_val(r, f"x3.a{a}.paired.time_diff_ms_hi") or 1) < 0 and (_val(r, f"x3.a{a}.paired.recall_diff_lo") or -1) >= -0.01 for a in (1, 5)]
        return "SUPPORTED" if all(ok) else ("PARTIAL" if any(ok) else "NO_IMPROVEMENT_FOUND")
    if p.pid == "N24":
        return "SUPPORTED" if any(_val(r, f"n24.r16.nom{n}.improvement") == 1 for n in (80, 90)) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N25":
        flags = [_val(r, f"s10.rf15.pi{t}.{rule}.improvement") for t in ("0p02pct", "0p1pct", "1pct") for rule in ("b_known", "b_em", "c_known", "c_em", "d10", "d50")]
        return "SUPPORTED" if any(x == 1 for x in flags) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N26":
        return "PARTIAL" if all(_val(r, f"s13.decision.r{rg}.sct_improves_on_spaced_table") == 1 for rg in (16, 32, 64)) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N27":
        return "PARTIAL" if all(_val(r, f"s12.ATT.design.{pr}") == 1 for pr in ("S1_replay_or_forgery_accepted_as_new", "S2_spoofed_ack_stops_retries", "S3_repeat_not_acked_or_budget_exceeded", "S4_accepted_counters_not_increasing")) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N28":
        # the class-level reduction alone is not enough: the conformal interval must also win at equal escalation (T1 decision rule)
        wins = any(_val(r, f"t1.r{rg}.decision.p3_wins_at_equal_escalation") == 1 for rg in (16, 32, 64))
        return "PARTIAL" if wins and (_val(r, "ua.r16.a10.cc.paired.mis_triage_upper_minus_point_hi") or 1) < 0 else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N20":  # the guarantee holds if the interval for the mean false-alarm rate is not above alpha
        ok = [(_val(r, f"x4.a{a}.n1000.conformal.fa_mean_lo") or 1) <= al for a, al in ((1, 0.01), (5, 0.05))]
        return "SUPPORTED" if all(ok) else "NO_IMPROVEMENT_FOUND"
    if p.pid == "N15":  # SUPPORTED only if a seed-averaged paired recall difference has its whole interval above zero
        for m in ("a_joint", "b_cost_sensitive", "c_learned_trigger"):
            for t in ("t1", "t5"):
                lo = _val(r, f"n15.{m}.{t}.paired_seedavg.d_recall_lo")
                if lo is not None and lo > 0:
                    return "SUPPORTED"
        return "NO_IMPROVEMENT_FOUND"
    return p.status


RANK = ["HL", "N8", "N9", "N13", "N12", "N10", "N14", "N19", "N16", "N4", "N1", "SF", "N3", "N2", "N17", "N5", "N6", "N7", "N15", "N18", "N20", "N21", "N22", "N23", "N24", "N25", "N26", "N27", "N28", "N29", "N30", "N31", "N32", "N33", "N34"]
PRIOR_SHORT = {"HL": "Each part has prior work; no source found that combines them end to end",
               "N8": "Leakage audits of other datasets; VZCrash paper (III-B) states vehicle-level splits",
               "N9": "Taccari et al. 2018; two-stage patents; VZCrash real-world population test",
               "N12": "Known LoRaWAN retransmission-versus-replay issue (ChirpStack discussion)",
               "N10": "Leaf-refinement paper (2021); emlearn", "N11": "VZCrash paper false-positive counts; phone crash-detection studies",
               "N4": "Priority-aware LoRa scheduling; LoRaWANSim", "N1": "TinyML crash projects; Katsidimas 2023 (forest on Arduino); Balfaqih 2022; emlearn", "N13": "EDR delta-V and ASI studies; NHTSA EDR round robin; Tadic 2016", "SF": "none found",
               "N3": "LoRaWAN MIC and counter; ESP32 HMAC-counter component (msg_auth)", "N2": "Ebert 2016 (phone IMU, RC car); Balfaqih 2022; Tadic 2016 (PDOF from MEMS)",
               "N14": "Spline restoration (Ruder; Chan 2023); US 7,643,921; `SAE 2025-01-5046` pulse fits", "N15": "Cascade detectors; two-stage crash pipelines (Kubin 2021, Taccari 2018)", "N16": "Priority-based LoRa allocation (Wei 2023); duty-cycle blackouts (Tomic 2020); back-off with jitter",
               "N17": "Kusano and Gabler 2013; Tadic 2016; Ebert 2016", "N18": "NHTSA and ESV dummy-criteria literature (snippets)", "N19": "Airbag-algorithm timing; early-exit classification (snippets)",
               "N20": "Split-conformal anomaly detection (snippets)", "N21": "Tu et al. 2018 (acoustic injection); Son 2015 and Trippel 2017 (cited)", "N22": "Tomic 2020; Wei 2023; Zhong and Nie 2024; LoRa ALOHA and capture analyses",
               "N23": "Scale-model crash similitude (snippets)", "N24": "CHOIR (conformal injury severity on police records); jackknife+ and CV+ (abstracts opened)", "N25": "Saerens 2002 prior shift by EM; Elkan 2001 cost-sensitive decisions (abstracts opened)", "N26": "Tamang 2022 urgent packets; Shao 2020 interrupt access; Wei 2023; Tomic 2020", "N27": "Gao 2019 (Scyther); Dong 2024 (PAT); Wesemeyer 2020 (Tamarin, join procedure)", "N28": "CHOIR; Tamang 2022; Shao 2020", "N5": "IETF MAPRG protocol slides", "N6": "Ebert 2016 (RC car); Katsidimas 2023 (open impact data, plates)", "N7": "SW-420 hobby projects"}
HW = {"HL": "H1 to H6, all of them, with the parts running together on the car",
      "N1": "H2 (including the transfer test) and H5 (flash, RAM and time per call)", "SF": "H2 transfer test, all features against scale-free",
      "N3": "H4 attack table on the radios; H5 verify time", "N4": "H3 delivery at 10, 50 and 100 m (optional wall)", "N2": "H1 impact side",
      "N5": "H3 LoRa latency and H5 stage timings", "N6": "H1 to H3 logs released with their windows", "N7": "H6 SW-420 ablation (re-analysis of H1 and H2)",
      "N13": "A wider-range accelerometer (at least `+-64 g` at 200 Hz) and a crash-test or sled comparison; severity on the car is not in the H1 to H6 plan",
      "N14": "A real saturated pulse from the sensor; a wider-range part makes it unnecessary", "N15": "Continuous-driving data; nothing in the hardware plan", "N16": "H3 delivery on the radios, including the effect of the spreading factor",
      "N17": "H1 impact side on the scale model", "N18": "Nothing in the hardware plan (crash-test dummy data)", "N19": "H5 timing on the ESP32 and H2 on the car", "N20": "Deployment-like calibration data",
      "N21": "No hardware plan (software study; a real sensor test would need a lab)", "N22": "H3 extended to several nodes", "N23": "H2 transfer test", "N24": "A wider-range accelerometer test and crash-test pulses beyond barrier tests", "N25": "Field data on the real prevalence and cost of false alarms (no hardware plan item)", "N26": "H3 delivery on the radios with several nodes and the flash and CANCEL messages in firmware", "N27": "Firmware review against the model; TLC run", "N28": "H3 with several nodes; class distributions from field data",
      "N9": "H2 crash against non-crash on the car, to check the trigger on real impacts", "N10": "H5 compile report and timing on the ESP32",
      "N12": "H4 on the radios (includes the ACK-lost retry), with the re-ACK and its limit implemented in the base-station firmware"}

PRIOR_SHORT.update(V2N.PRIOR_SHORT)
HW.update(V2N.HW)


def paragraph(r: Res) -> str:
    return ("We build and evaluate an integrated crash-alert system: an ESP32 detector, physics-based severity and authenticated LoRa delivery. The software side is done; hardware tests are pending. "
            f"System recall including the trigger is {r.ci('detector.head5.rf15.sys_recall')} (mean of 5 seeds) after removing {r.i('leakage.test_events_flagged.total')} test events that also occur in train or validation ({r.i('leakage.exact_hash_groups_across_splits')} cross-split groups were found), and {r.f('t5.strict.recall_f1', 3)} on a test set that also drops window-level near-duplicates (EXPLORATORY); precision at a realistic crash prevalence would be low. "
            f"At +-16 g a pulse-fit fill with a ridge correction lowers the median delta-V error from {r.f('n14x.R.r16.B.median', 1)}% (plain) and {r.f('n14x.R.r16.SP.median', 1)}% (spline restoration) to {r.f('n14x.R.r16.M+.median', 1)}%, "
            "with no practically meaningful gain at `+-32 g` or `+-64 g` and no blind test. "
            "Impact direction, radio delivery, scale-model transfer and ESP32 timing await hardware results.")


def layered(r: Res) -> str:
    """The layered view: what a low-cost crash node must measure, with the points of each layer."""
    return (
        "**Framing: what a low-cost crash node must measure.** The points fall into four layers.\n\n"
        "- **Sensing and restoration (N13, N14).** A wide-range sensor, or a pulse-fit fill with a ridge correction when the sensor clips. "
        "Fill + ridge was named primary after earlier results were seen, and NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes.\n"
        f"- **Edge decision and prevalence (N9, N25, N19).** System recall includes the trigger. Precision at a realistic prevalence is {r.f('s10.rf15.pi0p02pct.a.ppv', 4)} with the existing threshold, and no tested rule fixes it within five points of recall. "
        "The early-exit rule decides about one second earlier; its recall gain is an ensemble effect.\n"
        f"- **Link and delivery (N26, N16, N22, N28).** In simulated bursts a fast path with a short flash changes critical reach within ten seconds by {r.f('s11.diff.r16.burst.P2_minus_P1.reach10_critical', 3)} against the severity table and by {r.f('s13.diff.r16.burst.P2_minus_P1b.reach10_critical', 3)} against a severity table with spaced retries, with no gain in steady state. "
        f"Taking the class from the upper end of a conformal interval changes mis-triage by {r.f('ua.r16.a10.cc.paired.mis_triage_upper_minus_point', 3)} and sends many more non-severe events to the fast path; with the thresholds of the plain table lowered to the same escalation, the difference is {r.f('t1.r16.mis_triage_p3_minus_p1e', 3)} (no benefit beyond the thresholds).\n"
        "- **Authentication and protocol checks (N3, N12, N27).** Signed alerts and ACKs, a counter and a re-ACK, checked by an attack suite and by a bounded model check of a model (not a proof of the firmware).\n\n"
        "Every result that does not clear its interval is reported as a negative result.\n"
    )


def build(r: Res | None = None) -> str:
    r = r or Res()
    pts = {p.pid: p for p in points(r)}
    st = {k: status_of(r, p) for k, p in pts.items()}
    S: list[str] = []
    a = S.append
    a("# Novelty summary (evidence only)\n")
    a("Generated by `python -m crashguard.novelty` from `results/results.json` and `docs/06_references/PRIOR_WORK.md`.\n")
    a("**Headline contribution.** The integrated system, evaluated end to end: a detector that fits on a microcontroller, impact direction, and authenticated, severity-aware LoRa delivery. "
      "No single part is claimed on its own. **Evaluation-rigour contributions** (dataset audit, trigger-aware evaluation) support the headline but are not the headline. "
      "The near-miss false-alarm rate is a results breakdown, not a contribution. The retry-versus-replay finding is an independent re-discovery of a known LoRaWAN issue in a custom point-to-point link, with a bounded fix.\n")
    a("Wording is 'we found', 'we show', or 'to our knowledge in the sources checked'; a missing source in this list is not proof that none exists. "
      "Status labels: **SUPPORTED** (the claim as worded has software evidence on the data named; for N14 to N16 the paired gain clears the bootstrap interval on data the method was not tuned on; for a point resting on a simulation or a model, SUPPORTED means it holds in that simulation or model, not in the field), **PARTIAL** (software evidence exists, hardware is NOT_RUN, or part of the claim fails), "
      "**NO_IMPROVEMENT_FOUND** (the method was tried and its gain does not clear the interval; reported with the same detail as a success), **NOT_YET** (no evidence yet).\n")
    a("## 1. Points and evidence\n")
    for grp in ("headline", "rigour", "design", "component", "extra", "breakdown"):
        a(f"## {GROUPS[grp]}\n")
        for p in [x for x in points(r) if x.group == grp]:
            a(f"### {p.pid}. {p.title}\n")
            a(f"- **Status:** {st[p.pid]}")
            if p.evidence:
                a("- **Evidence (results.json key = value, origin):**")
                for key, d in p.evidence:
                    a(f"  - {fmt(r, key, d)}")
            else:
                a("- **Evidence:** none in software.")
            a(f"- **Still missing:** {p.missing}")
            a(f"- **Closest prior work:** {p.prior}\n")

    a("## 2. Prior-work check\n")
    a(P_START)
    prior = PRIOR.read_text(encoding="utf-8").split("\n", 1)[1]
    a(re.sub(r"(?m)^(#+) ", r"\1# ", prior))
    a(P_END + "\n")

    a("## 3. Ranked table\n")
    a("Ranked by role (headline, evaluation rigour, design findings, components), then by status and by how far the point is from the closest prior work we found. "
      "N11 is not ranked: it is a results breakdown.\n")
    rows = ["| Rank | Point | Role | Status | Key evidence | Closest prior work | Risk |", "|---|---|---|---|---|---|---|"]
    keyev = {
        "HL": f"software parts done (system recall {r.ci('detector.head5.rf15.sys_recall')}, mean of 5 seeds; {r.f('t5.strict.recall_f1', 3)} on the test set without window-level near-duplicates, EXPLORATORY, C difference {r.sci('export.max_abs_diff')}, {r.i('attacks.cases_matching_expected')} of {r.i('attacks.cases_total')} attack cases); H1 to H6 NOT_RUN",
        "N8": f"{r.i('leakage.exact_hash_groups_across_splits')} cross-split groups; {r.i('leakage.test_events_flagged.total')} test events ({r.i('leakage.test_events_flagged.crash')} crashes)",
        "N9": f"crash trigger rate {r.f('trigger.trig_2.crash.rate')}; model-level recall {r.f(f'{RF}.f1op_recall.mean')} against system recall {r.f(f'{RF}.sys_f1op_recall.mean')} (5-seed means)",
        "N12": f"strict verifier reproduces the failure; re-ACK repairs it; flood re-ACK airtime {r.f('attacks.flood.no_limit.reack_airtime_s', 1)} s without the limit, {r.f('attacks.flood.with_limit.reack_airtime_s', 1)} s with it",
        "N10": f"AP gap to the unconstrained 200-tree forest {r.f('gap.rf200_minus_rf15.ap', 4)} (at depth 6 the 200-tree forest is {r.f('s4.depth6.trees200.ap.mean', 3)} against {r.f('s4.depth6.trees15.ap.mean', 3)}); C difference {r.sci('export.max_abs_diff')}",
        "N4": f"critical alerts reached the base {r.f('s9.C_sf12_scarce.severity.reack.loss60.received_critical.mean')} against {r.f('s9.C_sf12_scarce.fixed3.reack.loss60.received_critical.mean')} (fixed), simulated",
        "N13": f"{r.i('sevstudy.n_tests')} NHTSA tests: within 10% of the reference on {r.f('sevstudy.grid.r16.f100.dv_within10', 2)} at +-16 g, 100 Hz; +-{r.f('sevstudy.needed.point.min_range_g', 0)} g at {r.f('sevstudy.needed.point.min_rate_hz', 0)} Hz needed for `80%`",
        "N1": f"AP {r.f(f'{RF}.ap.mean')}; transfer test and H5 NOT_RUN", "SF": f"AP kept share {r.f('scalefree.rf15.ap_kept_share')} (15-tree forest)",
        "N3": f"{r.i('attacks.cases_matching_expected')} of {r.i('attacks.cases_total')} simulated cases; H4 NOT_RUN",
        "N14": f"+-16 g, repeated grouped CV: median delta-V error plain {r.f('n14x.R.r16.B.median', 1)}%, spline {r.f('n14x.R.r16.SP.median', 1)}%, fill + ridge {r.f('n14x.R.r16.M+.median', 1)}%; fill + ridge minus spline {r.ci('n14x.R.r16.paired.M+_vs_SP.d_median', 1)} points; no gain found at `+-32 g` and `+-64 g`",
        "N15": f"seed-averaged recall difference at 1%: {r.f('n15.a_joint.t1.paired_seedavg.d_recall', 4)} (interval {r.f('n15.a_joint.t1.paired_seedavg.d_recall_lo', 4)} to {r.f('n15.a_joint.t1.paired_seedavg.d_recall_hi', 4)})",
        "N16": f"critical alerts better than the fixed policy in {r.i('n16.conclusion.C2_better_critical_than_fixed3.holds')} of {r.i('n16.conclusion.C2_better_critical_than_fixed3.cells')} held-out cells, better than the severity table in {r.i('n16.conclusion.C1_better_critical_than_table.holds')}; critical delivery gain over the table {r.ci('n16.effect.table.critical.delivered.d', 3)}, critical p95 latency {r.ci('n16.effect.table.critical.p95_lat_s.d', 1)} s; SIMULATED, supporting only",
        "N17": f"front against side, held-out groups, +-16 g: balanced accuracy {r.ci('x1.A.r16.balanced_acc', 3)} against {r.f('x1.A.r16.baseline_balanced_acc', 2)}; rear and right not testable",
        "N18": f"frontal chest acceleration: partial correlation of delta-V with speed removed {r.ci('x2.frontal.pos01.clip3m.orig.dv.partial', 2)}",
        "N19": f"decision time of crash events {r.ci('s6.a5.mean5.d.E_minus_Ep.time', 0)} ms at the 5% target (5-seed mean); recall gain over the single forest {r.ci('s6.a5.mean5.d.Ep_minus_F.recall', 4)} (an ensemble effect); timing read from the window length (MEASURED_SOFTWARE, no ESP32 timing)",
        "N20": f"test false-alarm rate with calibration de-duplicated by recording group {r.ci('n20c.clean.a5.nall.conformal.fa_mean', 4)} against alpha `0.05` (before de-duplication {r.f('x4.a5.n1000.conformal.fa_mean', 4)}; the guarantee fails in both)",
        "N21": f"net success of a structured search at `0.5` g: {r.f('x5.net.a.baseline.eps0.5.structured', 2)} (false crash), {r.f('x5.net.b.baseline.eps0.5.structured', 2)} (hidden crash)",
        "N22": f"base ACK allowance used {r.f('x6.sim.sf12.hb600.n350.r0.1.burst.fixed3.base_ack_airtime_share', 3)} at most at the default alert rate, up to {r.f('x6.sim.sf12.hb600.n50.r10.steady.fixed3.base_ack_airtime_share', 2)} at SF12 with high alert rates; burst of critical alerts at SF7, `100` cars (X6 simulator): severity table {r.f('x6.sim.sf7.hb600.n100.r0.1.burst.severity.delivered_critical', 2)}, scheduler {r.f('x6.sim.sf7.hb600.n100.r0.1.burst.scheduler.delivered_critical', 2)}; SIMULATED",
        "N24": f"`+-16 g`, `90%`: coverage {r.ci('n24.r16.nom90.coverage', 3)}; under-estimation of the class rule {r.f('n24.r16.nom90.under_decision', 3)} against point class {r.f('n24.r16.nom90.under_point', 3)}",
        "N25": f"precision at `0.02%` prevalence {r.f('s10.rf15.pi0p02pct.a.ppv', 4)} (existing rule); a rule aimed at precision `0.5` at `1%` prevalence reaches {r.f('s10.rf15.pi1pct.d50.ppv', 2)} at recall {r.f('s10.rf15.pi1pct.d50.recall', 2)}",
        "N26": f"burst, +-16 g: critical reach within 10 s, SCT minus table {r.ci('s11.diff.r16.burst.P2_minus_P1.reach10_critical', 3)}; SCT minus spaced-retry table {r.ci('s13.diff.r16.burst.P2_minus_P1b.reach10_critical', 3)}; steady state {r.ci('s11.diff.r16.steady.P2_minus_P1.reach10_critical', 3)}",
        "N27": f"{r.i('s12.ATT.design.states')} states; replay, forgery, spoofed ACK, counter and CANCEL properties hold within the bounds; strict anti-replay fails liveness",
        "N28": f"mis-triage, upper end minus point class, +-16 g: {r.ci('ua.r16.a10.cc.paired.mis_triage_upper_minus_point', 3)}; escalation {r.f('ua.r16.a10.cc.paired.escalation_upper_minus_point', 3)}; at equal escalation, P3 minus the lowered-threshold table {r.ci('t1.r16.mis_triage_p3_minus_p1e', 3)}; burst critical reach P3 minus P2 {r.ci('s11.diff.r16.burst.P3_minus_P2.reach10_critical', 3)}",
        "N23": f"recall at amplitude `0.5`: {r.f('x7.filtered.a0.5.tau1.all.recall.mean', 2)}; false-alarm rate at amplitude `2`: {r.f('x7.filtered.a2.tau1.all.fa.mean', 2)}; plausibility check",
        "N2": "H1 NOT_RUN", "N5": "stage breakdown NOT_RUN", "N6": "no data yet", "N7": "H6 NOT_RUN"}
    role = {"HL": "headline", "N8": "evaluation rigour", "N9": "evaluation rigour", "N12": "design finding", "N10": "supporting result", "N16": "supporting evidence", "N17": "supporting feature", "N18": "negative / descriptive",
            "N19": "supporting evidence", "N20": "negative result", "N21": "supporting evidence", "N22": "supporting evidence (SIMULATED)", "N23": "plausibility check", "N24": "negative result (calibration supporting)", "N25": "negative result (trade-off quantified)", "N26": "supporting evidence (SIMULATED)", "N27": "supporting check (ANALYTICAL)", "N28": "negative result at equal escalation (SIMULATED, preregistered)"}
    keyev.update(V2N.keyev(r))
    role.update(V2N.ROLE)
    for i, pid in enumerate(RANK, 1):
        rows.append(f"| {i} | {pid} {pts[pid].title} | {role.get(pid, 'component')} | {st[pid]} | {keyev[pid]} | {PRIOR_SHORT[pid]} | {pts[pid].risk} |")
    a("\n".join(rows) + "\n")

    a("## 4. Draft novelty paragraph\n")
    a(paragraph(r) + "\n")
    a("## 4b. Layered view\n")
    a(layered(r))

    a("## 5. Hardware plan and what it needs to move each point to SUPPORTED\n")
    a("The plan is the author's minimum set. **H1** impact side: 10 hits on each of 4 sides and 10 vertical drops (N2). **H2** crash against not-crash: the H1 hits plus 30 non-crashes "
      "(taps, hard stops, ramp bumps, lift-and-place), and the transfer test from VZCrash (N1, SF). **H3** LoRa: 20 alerts each at 10, 50 and 100 m, with an optional wall (N4, N5). "
      "**H4** security: forged, tampered, replay, spoofed ACK, base reboot and ACK-lost retry, 3 tries each (N3, N12). **H5** edge cost: compile report and logged microseconds (N1, N3). "
      "**H6** SW-420 ablation: re-analysis of H1 and H2 (N7).\n")
    a("**Limitations by design.** Severity measured against impact strength and the 200 m LoRa runs were dropped from the plan, so the work cannot claim a measured severity response or a range beyond 100 m.\n")
    rows = ["| Point | Status now | Needs |", "|---|---|---|"]
    for pid in ("HL", "N1", "N13", "N14", "N15", "N16", "SF", "N3", "N4", "N2", "N5", "N6", "N7", "N9", "N10", "N12", "N17", "N18", "N19", "N20", "N21", "N22", "N23", "N24", "N25", "N26", "N27", "N28"):
        rows.append(f"| {pid} | {st[pid]} | {HW[pid]} |")
    a("\n".join(rows) + "\n")
    return "\n".join(S)


def block(r: Res) -> str:
    pts = {p.pid: p for p in points(r)}
    st = {k: status_of(r, p) for k, p in pts.items()}
    lines = [START, "", "## Status after the software milestones (generated, see `report/novelty_summary.md`)", "",
             "**Headline contribution:** the integrated system (MCU detector, impact direction, authenticated severity-aware LoRa delivery), evaluated end to end. "
             "N8 and N9 are evaluation-rigour contributions, not the headline. N11 is a results breakdown, not a contribution. N16 is supporting evidence from simulation, not a contribution. N2 is a supporting feature and N6 is weak (RC-car and open-dataset precedents). N12 is an independent re-discovery of a known LoRaWAN issue "
             "in a custom point-to-point link, with a bounded fix.", "",
             "Statuses: SUPPORTED = software evidence exists for the claim as worded (N14 to N16: the gain clears the 95% interval on data not tuned on); PARTIAL = software done, hardware NOT_RUN or simulation only; NO_IMPROVEMENT_FOUND = tried, no gain beyond the interval; NOT_YET = no evidence yet. "
             "The prior-work record is in `docs/06_references/PRIOR_WORK.md`. Hardware IDs H1 to H6 are the minimum plan (see `docs/02_preregistration/EXPERIMENTS.md`).", "",
             "| Point | Claim | Role | Status | Closest prior work |", "|---|---|---|---|---|"]
    roles = {"headline": "headline", "rigour": "evaluation rigour", "design": "design finding", "component": "component", "breakdown": "results breakdown", "extra": "extra experiment"}
    for pid in ("HL", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N13", "N14", "N15", "N16", "N17", "N18", "N19", "N20", "N21", "N22", "N23", "N24", "N25", "N26", "N27", "N28", "N29", "N30", "N31", "N32", "N33", "N34", "N8", "N9", "N10", "N11", "N12", "SF"):
        lines.append(f"| {pid} | {pts[pid].title} | {roles[pts[pid].group]} | {st[pid]} | {PRIOR_SHORT[pid]} |")
    lines += ["", END]
    return "\n".join(lines)


def main() -> None:
    r = Res()
    text = build(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text.replace(L, "").replace(R_, ""), encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    blk = block(r).replace(L, "").replace(R_, "")
    if START in doc:
        doc = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: blk, doc, flags=re.S)
    else:
        doc = doc.rstrip("\n") + "\n\n" + blk + "\n"
    DOC.write_text(doc, encoding="utf-8")
    print(f"wrote {OUT} and updated {DOC}")


if __name__ == "__main__":
    main()
