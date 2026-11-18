# Claim evidence: each novelty point against the 24 project papers

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Each novelty point against the project papers, with the allowed wording. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; AI = artificial intelligence; AP = average precision; ASI = acceleration severity index; BLE = Bluetooth Low Energy; CNN = convolutional neural network; CoAP = Constrained Application Protocol; DOI = digital object identifier; ESP32 = a Wi-Fi microcontroller family (Espressif); GSM = Global System for Mobile communications; HMAC = hash-based message authentication code; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; IMU = inertial measurement unit; KB = kilobyte; LPWAN = low-power wide-area network; LoRa = long-range radio modulation; MCU = microcontroller unit; MEMS = micro-electromechanical system; ML = machine learning; MQTT = Message Queuing Telemetry Transport; NHTSA = National Highway Traffic Safety Administration; OCR = optical character recognition; PDF = Portable Document Format; PDOF = principal direction of force; PMC = PubMed Central; RAM = random-access memory; SAE = Society of Automotive Engineers; SCT = severity-classified transmission; SF = spreading factor (LoRa); SW-420 = a vibration switch module; TLS = Transport Layer Security; UA-SCT = uncertainty-aware SCT; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Written 2026-11-11. Papers are the 24 PDFs in `docs/literature/` (text extracted with pdftotext into `docs/literature/_text/`, git-ignored). Paper 01 had no text layer and was read through OCR (RapidOCR), so its quotes may carry OCR errors. Papers are cited by file number (01 to 24, in alphabetical file order): 01 Kumar, Acharya and Lohani 2020, IoT accident detection and classification with sensor fusion on a smartphone (IEEE IoT J.); 02 dashcam audio ensemble 2021; 03 AI-enabled accident alert, smart cities 2022; 04 ML framework, multimodal sensors in cars 2022; 05 LoRa LPWAN search and rescue 2022; 06 secure accident reporting, ECIES 2023; 07 speaker identification and blockchain 2023; 08 IoT accident detection and visual situation 2024; 09 bi-level crash risk forecasting 2024; 10 AV sensor-related accident severity 2024; 11 calibrated confidence crash severity 2024; 12 federated near-crash detection 2024; 13 spatiotemporal CNN crash prediction 2025; 14 AI traffic crash severity 2025; 15 ensemble imbalance injury severity 2025; 16 real-time IoT public safety alerts 2025; 17 drones, ML and LoRa 2025; 18 crash simulation models for crash-detection calibration 2025; 19 vehicle-based disaster alerting, LoRa 2025; 20 to 24 statistical crash-severity studies 2026 (road, glare, construction, farm, SOM clustering, rural).

**Reading rule.** A zero-hit search shows absence only in these 24 papers. It says nothing about the wider literature. Searches beyond the 24 papers are in `docs/06_references/PRIOR_WORK.md` and `docs/06_references/MANUAL_SEARCH_CHECKLIST.md`.

## Term search over the 24 extracts (2026-11-11, case-insensitive)
| Term | Papers with a hit | What the hits are |
|---|---|---|
| HMAC | none | |
| replay | 07, 12 | 07: voice-replay spoofing. 12: replay attacks on a federated-learning scheme, not on packets |
| authentication | 05, 06, 07, 16, 17 | 06: lightweight cryptography survey and ECIES. 05: encryption plus an integrity check. 16: certificate-based mutual authentication for MQTT. None describe a counter or an ACK |
| duty cycle | none | |
| ACK / acknowledg | 08, 16 (protocol sense: none) | 08: an acknowledgement SMS sent to the person who reports. No protocol ACK in any paper |
| severity | 01, 03, 05, 08, 09, 10 to 24 | 10, 11, 14, 15, 20 to 24 are statistical severity studies on report data. 03, 08, 16, 17, 19 give a severity label in an alert (see rows below) |
| direction | many | Travel direction or camera direction. None estimates the side or angle of impact |
| microcontroller / ESP32 / Arduino | 01, 03, 04 (reference list), 05, 08, 16, 19 | Hardware used as a gateway to a phone or cloud; no on-device trained model reported |
| delta-V / velocity change | none | |
| ASI / severity index | none as Acceleration Severity Index | 07: MFCC feature name. 11, 14: a crash severity index variable |
| near-miss / near-crash | 02, 04, 09, 12, 21 | 02: dashcam audio with near-crash clips. 12: near-crash detection from video. Not IMU-only |
| duplicate / leakage | 04, 06, 08, 14, 16, 21 | 04: removes duplicates in preprocessing. 08: merges duplicate witness reports. None audits identical recordings across train and test splits |

## Table: one row per novelty point
Verdict codes: YES = a paper already does it; PARTLY = a paper does a related part; NOT FOUND = no hit in the 24 papers (not proof of absence).

| Point | Claim sentence | Closest paper(s) and place | Short quote | In the 24 papers | What is left that is ours |
|---|---|---|---|---|---|
| HL | The integrated system (microcontroller detector, impact direction, authenticated severity-aware LoRa delivery) is evaluated end to end | 05 (LoRa packet with encryption and a channel check); 16 (severity-scored alerts); 08 (IMU, vibration, MQTT report) | 05 p6, Algorithm 1 (RoboMaC Transmitter), steps 8 and 9: "if LoRa channel is free, then" / "Send the LoRa Packet" | PARTLY: each part appears in a different paper, none combines all | The combination, with the hardware part still not measured. PARTIAL until H1 to H6 |
| N1 | Real-crash-trained detector on a cheap MCU, with a transfer test to the scale model | 04 (ML on real SHRP2 crashes from in-car sensors); 01 (threshold classifier on a phone); 03, 08, 16 (microcontroller as gateway) | 04 p1: "detecting real-world driving accidents" | PARTLY: real-crash ML (04) is off-device; MCU papers use thresholds | Flash and RAM size against accuracy with C export checked against Python; the transfer test needs hardware |
| N2 | Impact side and angle from one IMU are carried in the alert | None in the 24 | | NOT FOUND | Outside the 24: Tadic and Vukajlovic 2016 estimate the principal direction of force from low-cost MEMS (see PRIOR_WORK). Software evidence for this point is not built. Stays NOT_YET |
| N3 | HMAC, anti-replay counter and signed ACK on the MCU, with the spoofed-ACK case | 05 (encrypts and checks integrity, no counter); 06 (ECIES over MQTT); 16 (TLS certificates) | 05 p6, Algorithm 1 steps 8 and 9: "if LoRa channel is free, then" / "Send the LoRa Packet"; 05 p6 (text, receiver): "the incoming data was hacked or otherwise corrupted" | PARTLY: integrity and encryption appear; counter, replay and signed ACK do not | Outside the 24, an ESP32 HMAC component with a counter exists (embedblocks msg_auth, opened) and LoRaWAN has counters. Ours: the 97-byte alert, 26-byte ACK, attack suite of <!--n:attacks.cases_total-->48<!--/n--> cases (`docs/01_protocol/ATTACK_CASES.md`), the retry fix. PARTIAL |
| N4 | Severity-aware delivery under a 10% duty-cycle budget | 16 (severity score routes alerts to three audiences); 05 (waits for a free channel) | 16 p19 table: "Severity-aware alerting" | PARTLY: severity-based routing exists (16), duty cycle absent | Retry and airtime policy by severity under a duty-cycle budget, simulated. Priority-aware LoRa scheduling exists outside the 24 (Osaka group, snippet only). PARTIAL |
| N5 | Measured stage-by-stage latency against HTTP, MQTT and CoAP | 16 (MQTT over TLS with LoRa fallback); 08 (MQTT) | 16 abstract: "secure MQTT over TLS, with fallback to LoRa" | NOT FOUND for a measured comparison | Needs the hardware logs. NOT_YET |
| N6 | Open labelled scale-model dataset | None | | NOT FOUND | Needs hw_events.csv. NOT_YET |
| N7 | Measured value of a cheap vibration-sensor array | 08 (SW-420 vibration in three levels) | 08 p5: "vibration has been categorized into 3 levels, namely, low, moderate, and high" | PARTLY: a vibration sensor is used with a level label, not measured against an IMU | Needs hardware. NOT_YET |
| N8 | Identical recordings appear across the official VZCrash splits | 04 (duplicates removed in preprocessing only) | 04: "eliminating any duplicates, irregularities in the data" | NOT FOUND as a split audit | The audit and the de-duplicated test set. SUPPORTED, a data-quality finding about one dataset, to be reported to its authors |
| N9 | Trigger-aware evaluation: system recall includes the trigger stage | 18 (calibrates a crash-detection trigger on crash pulses) | 18 p1: "crash-detection algorithm" calibration | PARTLY: trigger design is studied for restraint systems, not reported as system recall on a pre-triggered dataset | Metric definition and sweep on VZCrash. SUPPORTED as evaluation rigour |
| N10 | Size against accuracy on the MCU, with C-export equivalence | None in the 24 | | NOT FOUND | Depth and tree sweep with a validation-only choice. SUPPORTED |
| N11 | False-alarm rate on near_miss events alone (a breakdown) | 02, 12 (near-crash from audio and video) | | PARTLY: near-crash is studied with other sensors | A breakdown, not a contribution |
| N12 | Retry versus replay in a custom point-to-point link, with a bounded fix | None in the 24 | | NOT FOUND | Known LoRaWAN issue outside the 24 (ChirpStack forum, opened). Ours is a re-discovery with a bounded fix |
| N13 | Physics-based severity (delta-V, ASI, rollover) from one low-rate IMU, carried in the alert | 01 (rollover from roll or pitch above 90 degrees with a complementary filter; severity not measured); 08 (hit severity from vibration); 16 (composite severity score) | 01: "if either roll or pitch is greater than 90°, a rollover happened" (OCR) | PARTLY: rollover by angle (01) and severity labels (08, 16) exist; delta-V and ASI do not appear | Outside the 24: Tadic and Vukajlovic 2016 (delta-V and direction from consumer MEMS, low-G sensors saturated, opened). Ours: the range and rate study on NHTSA tests. PARTIAL |
| SF | Scale-free features keep most of the AP | None | | NOT FOUND | Supports the transfer argument only. PARTIAL |

## Notes on the closest papers
- **05 (LoRa search and rescue).** Packet is encrypted, then sent only if the channel is free; the receiver rejects data it finds hacked. No counter, no ACK, no duty-cycle analysis. This is the closest source for the security part, and the existing NOVELTY.md already lists it.
- **16 (public safety alerts).** Its table lists severity-aware alerting as a feature, using a weighted score and three escalation levels. The severity there is a fusion of environment, motion, biometric and video inputs, not delta-V. It means N4 and N13 cannot say "severity in an alert" is new. Only the physics basis and the airtime policy remain.
- **01 (Kumar et al. 2020).** It separates collision, fall-off and rollover with a complementary filter and says it does not focus on severity monitoring. It uses a 5 g and 23 km/h argument. This is the closest source for the rollover step, so a drift-corrected rollover flag is not new either.
- **18 (crash-detection calibration).** Restraint-system trigger calibration from crash pulses. Related to the trigger stage; it works on simulated and tested crash pulses, not on a pre-triggered fleet dataset.

## Quote re-check (round 3, S1.2)
Every quoted phrase attributed to one of the 24 papers was searched in the extracted text (`docs/literature/_text`, whitespace collapsed) and in a page-by-page extraction of the PDFs to confirm the page. Result:
| Quote | Paper and page found | Match |
|---|---|---|
| "if LoRa channel is free, then" / "Send the LoRa Packet" | 05, p6, Algorithm 1 steps 8 and 9 | exact (now the quoted text; the running-text sentence "If the channel is free, the encrypted data packet will be sent." is also exact on p6) |
| "the incoming data was hacked or otherwise corrupted" | 05, **p6** | exact text; the page was given as p5 before and is corrected |
| "detecting real-world driving accidents" | 04, p1 | exact |
| "eliminating any duplicates, irregularities in the data" | 04, p8 | exact |
| "Severity-aware alerting" | 16, p19 | exact |
| "secure MQTT over TLS, with fallback to LoRa" | 16, p1 | exact |
| "vibration has been categorized into 3 levels, namely, low, moderate, and high" | 08, p5 | exact |
| "crash-detection algorithm" | 18, p1 (also pp2, 3, 23, 26) | exact |
| "if either roll or pitch is greater than 90 degrees, a rollover happened" | 01 (OCR) | matches only after OCR spacing is restored (the OCR has no spaces between words); wording otherwise as the OCR reads |

Not checkable here: "strictly separated by vehicle" (VZCrash paper, arXiv 2606.06074) is not among the 24 papers and its PDF is not kept in this repository; the wording was copied when the paper was read on 2026-11-11 and has not been re-checked against a stored copy. The phrases "severity in an alert", "no security" and "built, not yet measured" are our own wording, not quotes.

## Part 0B literature additions (2026-11-11)
Full details, with exactly what was opened for each paper, are in `docs/06_references/PRIOR_WORK.md` ("Part 0B literature entries"). They are numbered L1 to L9 here and are NOT among the 24 project papers, so the zero-hit reading rule above does not apply to them.

| Ref | Source | Opened as | What it shows | Novelty points touched |
|---|---|---|---|---|
| L1 | VZCrash paper, arXiv 2606.06074 | full text | Splits "strictly separated by vehicle" (72/14/14, Section III-B); on-device threshold pre-selection (Section II); AP baselines 97.56 (CNN-RNN), 97.54 (CNN-Transformer), 89.62 (peak-acceleration baseline); no tree models; no embedded test; direction and severity labels listed as future work (Section IV); 143 crashes among 735,000 real-world events (under 0.02%), best-model AP falls to about 86% (Section III-D); no licence in the paper | N1, N8, N9, SF, X8 dropped |
| L2 | Balfaqih et al. 2022, Sustainability 14(1) 210 | abstract only | Microcontroller classifier of severity (GMM, NB tree, DT, CART), crash sides and severity sent by GSM. Arduino, RC-car data and "no security" NOT verified | N1, N2, N13 |
| L3 | Katsidimas et al. 2023, Sensors 23(2) 896 | full text (Europe PMC) | Random forest on an Arduino Nano 33 BLE with flash (88 KB) and RAM (162 KB) reported; public Zenodo dataset; plate impacts with PZT sensors | N1, N10 |
| L4 | Ebert et al. 2016, arXiv 1703.05680 | full PDF | Impact segment and direction from one phone IMU on an RC car; four diagonal classes | N2, N6 |
| L5 | Zhong and Nie 2024, Sci Rep 14 (article number unconfirmed; DOI 10.1038/s41598-024-59058-8) | full text (Europe PMC) | Confirmed LoRa messaging with local ACK and at most 2 retransmissions; no replay, duty-cycle or priority text | N3, N4, N12 |
| L6 | Tomic et al. 2020, arXiv 2002.01472 | full PDF | LoRaWAN duty-cycle blackout periods for event-triggered traffic; priority slots only as future work | N4, N16, X6 |
| L7 | Wei et al. 2023, Sensors 23(5) 2660 | full text (Europe PMC) | Priority-based spreading-factor allocation under 1% duty cycle; no retries, no token budget | N4, N16, X6 |
| L8 | Chan et al. 2023, Sensors 23(10) 4609 (algorithm of Ruder et al.) | full text (Europe PMC) | 5th-order spline through 3 points each side of a clipped segment; still underestimates peaks (-1.40 +- 4.53 g mean, worse for higher peaks) | N14 |
| L9 | Tadic and Vukajlovic 2016, Radioengineering 25(1) | opened earlier | Delta-V and PDOF from consumer MEMS in one real test; saturation of low-G sensors | N2, N13, N14, X1 |

**Downgrades from this reading (also in `report/novelty_summary.md` and `docs/06_references/NOVELTY.md`):**
- **N2** (impact side and angle): a supporting feature, not a contribution. L4 (phone IMU, RC car), L2 (crash side by GSM) and L9 (PDOF from MEMS) exist.
- **N6** (open scale-model dataset): weak. RC-car data (L4) and open impact datasets (L3, on a plate) already exist, so only a labelled CrashGuard-specific set would be new, and it is not built.
- **N1** (real-crash-trained detector on a cheap MCU): partial. A random forest on a microcontroller with flash and RAM reported has precedent (L3, plates) and a CART severity classifier on a microcontroller is reported (L2, abstract only). The VZCrash paper (L1) tested no tree models and ran no embedded test; that is the gap the forest is evaluated in.
- **Integrated system (HL):** each part has a precedent (L2, L3, L5, L6, L7 and the 24 papers); the combination is unmeasured on hardware, so the wording stays "built, not yet measured".
- **N14:** L8 is the spline baseline; the comparison is in `docs/02_preregistration/ALGORITHMS.md` (N14 extension) and the novelty file.

**Still title-only or snippet-only (not used for any claim):** US 9,162,642; SAE 2015-01-1448; ChirpStack threads other than the one opened; the automated-crash-notification PDOF study; the PMC paper on sensor bandwidth and sample rate for head-impact sensors. (US 7,643,921 and the SAE 2025-01-5046 abstract page were read, see PRIOR_WORK.md.)

<!-- claims:start -->
## Claim table (generated by `python -m crashguard.claim_table` from `results/results.json`)

| Claim | Label | Source (keys or file) | Command | Verdict |
|---|---|---|---|---|
| Identical recordings occur across the supplied VZCrash splits (N8) | MEASURED_SOFTWARE | `leakage.*` | `python -m crashguard.split` | **SUPPORTED** |
| Trigger-aligned window-level near-duplicates are far more common than exact duplicates and lower the headline recall (N8 extension) | MEASURED_SOFTWARE | `dupscan.*` | `python -m crashguard.s2_dedup` | **SUPPORTED** |
| The conformal false-alarm guarantee holds on the de-duplicated test set (N20, calibration de-duplicated by recording group) | MEASURED_SOFTWARE | `n20c.*` | `python -m crashguard.s3_conformal` | **NOT SUPPORTED** |
| Fill + ridge lowers the delta-V error at +-16 g against plain and spline restoration (N14; named primary after earlier results were seen) | MEASURED_SOFTWARE | `n14x.*, n14s.*` | `python -m crashguard.saturation_splits; python -m crashguard.s4_n14` | **SUPPORTED** |
| Fill + ridge reaches the N13 target of 80% within 10% at +-16 g | MEASURED_SOFTWARE | `n14x.R.r16.M+.w10` | `python -m crashguard.saturation_splits` | **NOT SUPPORTED** |
| M+ capped improves the tail (exploratory) | MEASURED_SOFTWARE | `n14s.cap.*` | `python -m crashguard.s4_n14` | **NOT SUPPORTED** |
| The early-exit rule saves about a second of decision time (N19) | MEASURED_SOFTWARE (timing from window length) | `s6.*` | `python -m crashguard.s6_early` | **SUPPORTED** |
| The early-exit recall gain over the single full-length forest is an early-exit effect (N19) | MEASURED_SOFTWARE | `s6.*` | `python -m crashguard.s6_early` | **NOT SUPPORTED** |
| The scheduler beats the severity table in bursts across the A4 sweep, X6 simulator (N16, N22) | SIMULATED (exploratory) | `s5.*` | `python -m crashguard.s5_burst` | **PARTIAL** |
| Conformal intervals around the clipped delta-V estimate have about nominal coverage (N24) | MEASURED_SOFTWARE | `n24.*` | `python -m crashguard.s9_conformal_dv` | **PARTIAL** |
| The class rule on those intervals lowers under-estimation (N24) | MEASURED_SOFTWARE | `n24.*` | `python -m crashguard.s9_conformal_dv` | **NOT SUPPORTED** |
| A prevalence-adaptive threshold raises precision within five points of recall at prevalence of one per cent or lower (N25) | MEASURED_SOFTWARE with assumed costs | `s10.*` | `python -m crashguard.s10_adaptive` | **NOT SUPPORTED** |
| UA-SCT B2: the class intervals reach the target coverage at every sensor range (conservative, not exact) | MEASURED_SOFTWARE | `ua.r*.a10.cc.coverage` | `python -m crashguard.ua_conformal` | **PARTIAL** |
| H-a: P3 lowers mis-triage against P1 at +-16 g (reduction of more than two points; the reduction comes from escalating more events, see T1) | MEASURED_SOFTWARE + SIMULATED | `ua.r16.a10.cc.paired.*, s11.diff.*` | `python -m crashguard.ua_conformal; python -m crashguard.s11_sct` | **SUPPORTED** |
| H-b: the cost of P3 is more fast-path escalations, and P4 bounds the fast-path airtime | SIMULATED | `ua.*escalation*, s11.diff.*P4_minus_P3*` | `python -m crashguard.s11_sct` | **PARTIAL** |
| H-c: the gain shrinks at +-64 g because the intervals are narrower | MEASURED_SOFTWARE | `ua.hc.*` | `python -m crashguard.ua_conformal` | **SUPPORTED** |
| B7: P3 raises critical delivery in steady state | SIMULATED | `s11.diff.r16.steady.P3_minus_P1.*` | `python -m crashguard.s11_sct` | **NOT SUPPORTED** |
| B7: P2 (SCT) raises critical reach within 10 s in bursts against the severity table | SIMULATED | `s11.diff.r16.burst.P2_minus_P1.*` | `python -m crashguard.s11_sct` | **PARTIAL** |
| P3 raises critical reach within 30 s over P2 in bursts | SIMULATED | `s11.diff.r16.burst.P3_minus_P2.*` | `python -m crashguard.s11_sct` | **NOT SUPPORTED** |
| SCT improves on a severity table with spaced retries in bursts (N26) | SIMULATED | `s13.*` | `python -m crashguard.s13_spaced_table` | **PARTIAL** |
| The assumed duty-cycle limit (1% default; not verified for India) is never exceeded in any simulated run (independent scan) | SIMULATED | `s11.duty.*` | `python -m crashguard.s11_sct` | **SUPPORTED** |
| The alert protocol model satisfies the replay, forgery, spoofed-ACK, counter and CANCEL properties within its bounds (N27) | ANALYTICAL (bounded model check) | `s12.*` | `python -m crashguard.protocol_check` | **PARTIAL** |
| The abstract base rule agrees with the reference verifier on the mapped attack cases | ANALYTICAL vs SIMULATED | `s12.crosscheck.*` | `python -m crashguard.protocol_check` | **PARTIAL** |
| The attack suite behaves as designed | SIMULATED | `attacks.cases_total, attacks.cases_matching_expected, docs/01_protocol/ATTACK_CASES.md` | `python -m crashguard.attacks; python -m crashguard.attack_doc` | **SUPPORTED** |
| The C code of the forests, severity.h and the N14 estimator equals the Python reference on the real inputs (differences below 5e-5; gcc under WSL; Windows rows NOT_RUN where blocked); one synthetic saturated-pulse check of the N14 estimator fails | MEASURED_SOFTWARE | `cchecks.*, export.*, candidate.*` | `scripts/c_checks.sh; python -m crashguard.merge_c_checks` | **PARTIAL** |
| The preregistered tests of H-a, H-b (the escalation part) and H-c still hold after a Holm correction over the three hypotheses (T14); the airtime-cap part of H-b is PARTIAL (the cap barely binds) | MEASURED_SOFTWARE | `t14.*` | `python -m crashguard.stats_audit` | **SUPPORTED** |
| T1: at the same escalation P3 lowers mis-triage beyond what lowering the thresholds of the plain table does (preregistered rule) | MEASURED_SOFTWARE + SIMULATED | `t1.*` | `python -m crashguard.t1_equal_escalation` | **NOT SUPPORTED** |
| T2: the interval family has a smaller mis-triage against escalation trade-off area than the point-class family | MEASURED_SOFTWARE | `t2.*` | `python -m crashguard.t2_pareto` | **NOT SUPPORTED** |
| T3: P3 costs less than P1 when a missed severe event costs several times a false escalation (break-even ratio above the observed-mix value; not against the equal-escalation table) | MEASURED_SOFTWARE (assumed costs) | `t3.*` | `python -m crashguard.t3_cost` | **PARTIAL** |
| T4: SCT reaches the base as often as the table for a single car at 60% loss; with quick retries it does | SIMULATED + ANALYTICAL | `t4.b.*` | `python -m crashguard.t4_clarify` | **PARTIAL** |
| T5: the headline recall is lower on the test set without window-level near-duplicates (the standard set stays primary) | MEASURED_SOFTWARE (exploratory) | `t5.*` | `python -m crashguard.t5_strict` | **SUPPORTED** |
| T6: H-a survives every shift of the delta-V class limits tested; H-c survives all but two (all limits down by 2 km/h, the middle limit down by 2 km/h) | MEASURED_SOFTWARE | `t6.*` | `python -m crashguard.t6_thresholds` | **PARTIAL** |
| T7: a conformal variant restores the N20 false-alarm guarantee at alpha 5% | MEASURED_SOFTWARE (exploratory) | `t7.b.*` | `python -m crashguard.t7_conformal_variants` | **NOT SUPPORTED** |
| T8: P3 beats P1 in critical reach within 10 s in most cells of the simulator sweep (not in every cell: it loses in steady cells at high loss) | SIMULATED | `t8.count.*` | `python -m crashguard.t8_sweep` | **SUPPORTED** |
| T9: the flash and the severity hold carry the SCT gain in bursts | SIMULATED (exploratory) | `t9.diff.*` | `python -m crashguard.t9_ablations` | **SUPPORTED** |
| T9: the reserved duty share changes critical reach in the cells tested | SIMULATED (exploratory) | `t9.diff.*.no_reserve_minus_full.*` | `python -m crashguard.t9_ablations` | **NOT SUPPORTED** |
| T12: a CANCEL that overtakes its alert is lost in the design and kept when the base remembers it (model) | ANALYTICAL (bounded model check) | `s12x.*` | `python -m crashguard.protocol_check_ext` | **SUPPORTED** |
| T11: the ten designed test cases behave as expected (not independent attackers) | SIMULATED | `attacks_x.*` | `python -m crashguard.attacks_extra` | **SUPPORTED** |
| T13: the finding repeats on a second public dataset | NOT_RUN | `t13.*` | `python -m crashguard.t13_second_dataset` | **NOT SUPPORTED** |
| The integrated system is evaluated end to end on hardware | NOT_RUN | `hw.*` | `merge/ingest_hardware.py` | **NOT SUPPORTED** |
| v2 A: a quantile boosting model on clipping descriptors and pulse-family features lowers the 90th-percentile delta-V error against fill + ridge at +-16 g (preregistered, Holm-corrected) | MEASURED_SOFTWARE | `v2.a.hA1.*` | `python -m crashguard.v2_a_study` | **SUPPORTED** |
| v2 A: adaptive conformal intervals are narrower than plain split-conformal intervals where clipping is mild, with coverage within 2 points of 90% | MEASURED_SOFTWARE | `v2.a.hA2.*, v2.a.a5.*` | `python -m crashguard.v2_a_study` | **NOT SUPPORTED** |
| v2 A: the deterministic bounds (plain estimate; pulse-family upper bound) contain the reference delta-V for at least 90% of tests at +-16 g | MEASURED_SOFTWARE | `v2.a.hA3.*, v2.a.a2.*` | `python -m crashguard.v2_a_study` | **NOT SUPPORTED** |
| v2 B: a load-adaptive escalation variant raises critical reach within 10 s by 3 points over a matched fixed lowered-threshold rule in most burst cells | SIMULATED | `v2.b.hB1.*, v2.b.gain.*` | `python -m crashguard.v2_b_study` | **NOT SUPPORTED** |
| v2 B: no adaptive variant harms steady cells or the single-car 60% loss case by more than 2 points | SIMULATED | `v2.b.hB2.*` | `python -m crashguard.v2_b_study` | **MIXED** |
| v2 B: the per-car token bucket achieves at least 80% of the best variant's gain | SIMULATED | `v2.b.hB3.*` | `python -m crashguard.v2_b_study` | **NOT SUPPORTED** |
| v2 D: the clip-onset flag detects Severe or Critical events at least 100 ms before the full-pulse decision with no more under-triage than the early-exit analogue | MEASURED_SOFTWARE | `v2.d.hD1.*` | `python -m crashguard.v2_d_study` | **NOT SUPPORTED** |
| v2 D: the clip-onset flag flags fewer than 10% of non-severe events | MEASURED_SOFTWARE | `v2.d.hD2.*` | `python -m crashguard.v2_d_study` | **MIXED** |
| v2 E: a 4-byte tag raises critical reach within 10 s by 2 points over an 8-byte tag in the burst cells | SIMULATED | `v2.e.hE1.*` | `python -m crashguard.v2_e_study` | **NOT SUPPORTED** |
| v2 E: an 8-byte tag keeps the duty-capped forgery work factor above 2^32 attempts | ANALYTICAL | `v2.e.hE2.*, v2.e.forgery.*` | `python -m crashguard.v2_e_study` | **SUPPORTED** |
| v2 F: the model-optimal hold of Critical alerts is zero for every cost ratio in the grid | ANALYTICAL | `v2.f.hF1.*, v2.f.opt.*` | `python -m crashguard.v2_f_study` | **NOT SUPPORTED** |
| v2 F: a 2 s hold of Severe alerts cuts false Severe alerts reaching the base by at least 20% with no significant loss in critical reach | SIMULATED | `v2.f.hF2.*` | `python -m crashguard.v2_f_study` | **SUPPORTED** |
| T13a: the N13 requirement (lower interval end of 0.80 within +-10%) is also met on NHTSA tests of other test modes | MEASURED_SOFTWARE | `t13.heldout.grid.*` | `python -m crashguard.t13_heldout` | **NOT SUPPORTED** |
| T13a: fill + ridge beats the spline at +-16 g on other test modes | MEASURED_SOFTWARE | `t13.heldout.all.r16.paired.*` | `python -m crashguard.t13_heldout` | **NOT SUPPORTED** |
| T13c: fill + ridge still beats the spline at +-16 g without near-identical NHTSA pulses (exploratory) | MEASURED_SOFTWARE | `t13.neardup.headline.*` | `python -m crashguard.t13_neardup` | **SUPPORTED** |
| Sensor selection: on the 176 NHTSA tests a range of +-64 g or more is needed to reach the requirement and no +-16 g part reaches it; the held-out modes do not confirm any configuration | MEASURED_SOFTWARE (data sheet table ANALYTICAL) | `sel.s3.*` | `python -m crashguard.sel_study` | **SUPPORTED** |
| V1: an independent recomputation reproduces the stored VZCrash duplicate counts | MEASURED_SOFTWARE | `vz.v1.*` | `python -m crashguard.vz_audit` | **SUPPORTED** |
| V4: window-level duplicates raise the headline recall at the 1% target by several points; exact copies by under one point | MEASURED_SOFTWARE | `vz.v4.*` | `python -m crashguard.vz_leakage` | **SUPPORTED** |
| X: the 16-bit fixed-point forest loses at most 0.005 AP and cuts the flash estimate by 30% (preregistered, Holm-corrected) | MEASURED_SOFTWARE | `x.x1.*; x.holm.H-X1.*` | `python -m crashguard.x1_fixedpoint` | **NOT SUPPORTED** |
| X: a cheap-trigger cascade raises the share of crashes passing the trigger by 2 points over a 2 g threshold at an equal non-crash trigger rate | MEASURED_SOFTWARE | `x.x2.*; x.holm.H-X2.*` | `python -m crashguard.x2_cascade` | **NOT SUPPORTED** |
| X: group-aware training raises recall at the 1% false-alarm target on the strict test set by 1 point | MEASURED_SOFTWARE | `x.x3.*; x.holm.H-X3.*` | `python -m crashguard.x3_groupaware` | **NOT SUPPORTED** |
| X: a +-16 g sensor with fill + ridge preserves the rank of delta-V (Spearman at least 0.90, lower end 0.85) | MEASURED_SOFTWARE | `x.x5.*; x.holm.H-X5.*` | `python -m crashguard.x5_rank` | **NOT SUPPORTED** |
| X: a lower-bound-anchored estimator lowers the 90th-percentile delta-V error by 5 points against fill + ridge at +-16 g | MEASURED_SOFTWARE | `x.x6.*; x.holm.H-X6.*` | `python -m crashguard.x6_anchored` | **SUPPORTED** |
| X: a real two-part pair reaches 0.80 within +-10% where neither part alone does (preregistered fusion rules) | MEASURED_SOFTWARE | `x.x7.*; x.holm.H-X7.*` | `python -m crashguard.x7_fusion` | **NOT SUPPORTED** |
| X: a sequential rule decides 100 ms earlier than the early-exit rule at equal or better recall | MEASURED_SOFTWARE | `x.x8.*; x.holm.H-X8.*` | `python -m crashguard.x8_sequential` | **NOT SUPPORTED** |

SUPPORTED = the claim as worded has software evidence and meets any rule fixed in advance (for a SIMULATED or ANALYTICAL row it holds in that simulation or model, not in the field); PARTIAL = part of the claim fails, or it rests on a simulation with assumed values that the claim goes beyond; NOT SUPPORTED = tried and not cleared, or no evidence. No hardware result is used. Rows about delta-V classes (N14, N24, H-a to H-c, T1 to T3, T6) use NHTSA crash tests, mostly high-speed barrier tests, which are not representative of all real crashes. Rows from the T block marked EXPLORATORY were not preregistered. The v2 rows (preregistered in docs/02_preregistration/PREREGISTRATION_V2.md) also use MIXED = one part of a two-part criterion holds, or the criterion holds but the Holm-adjusted p-value is not below 0.05.

## Allowed wording for the v2 claims (generated)

| Hypothesis | Verdict | Allowed wording | Not allowed |
|---|---|---|---|
| H-A1 | **SUPPORTED** | On 176 NHTSA crash tests, at +-16 g and 100 Hz, a quantile boosting model on clipping descriptors and pulse-family features has a 90th-percentile delta-V error of 42.4% against 58.5% for fill + ridge on repeated grouped cross-validation (difference 16.1 [9.3 to 23.4] points); the gain is 1.5 points on the make/model hold-out split A (interval 0.0 to 28.4); of the three fixed splits only the original-rule split O has its whole interval above zero. | That the estimator works on a real sensor or on crashes unlike the NHTSA tests; that it is the best estimator (plain gradient boosting has a lower 90th percentile on split R, EXPLORATORY; it is not shown better than the triangle fit alone or than ridge on all features); that it fixes the large-error tail. |
| H-A2 | **NOT SUPPORTED** | Normalised-score intervals bring coverage in the lowest clipped-fraction tercile to 0.90 (plain: 0.81) by being wider there (median relative width 0.99 against 0.75); they are narrower in the middle and highest terciles (0.38 and 0.52 against 0.74 and 0.77); the tests that never clip are covered 0.05 of the time. | That adaptive intervals are narrower or tighter where clipping is mild. |
| H-A3 | **NOT SUPPORTED** | At +-16 g the plain estimate is above the reference delta-V for 2 of 176 tests (but for 16 at +-32 g and 20 at +-64 g, so it is not a guarantee); the interval from the plain estimate to the pulse-family upper bound contains the reference for 0.55 of tests. | Guaranteed bounds; an upper bound on delta-V from the unclipped part of the pulse. |
| H-B1 | **NOT SUPPORTED** | In the simulator, none of five load-adaptive escalation variants raised critical reach within 10 s by 3 points over a matched fixed lowered-threshold rule in the burst cells (best mean gain 0.0080); the beacon variant lowered it in cells (for example -0.077 [-0.096 to -0.059] in the loaded SF9 cell). No tested variant reached a 3-point gain in these simulated cells. | That adaptive escalation improves delivery; that where escalations go matters (not shown). |
| H-B2 | **MIXED** | The largest point harm of any variant in a steady or single-car cell is 0.036 (graceful demotion, single car at 60% loss); its interval includes 2 points. For no variant does a whole interval of harm lie above 2 points, but some upper 95% bounds do (beacon variant in the steady cell with loss 0.3, demotion in the single-car cell); two variants are worse than their baseline with the whole interval below zero in some burst cells. | That adaptive variants are safe in steady state. |
| H-B3 | **NOT SUPPORTED** | Not evaluable because H-B1 is not met (the token bucket's mean gain is 0.0003 against 0.0080 for the best variant). | Any claim that a simple rule suffices. |
| H-D1 | **NOT SUPPORTED** | Among the Severe or Critical tests it flags (0.56 of them), the clip-onset flag saves a median of 86 ms (interval 80 to 95); the running delta-V threshold flags 0.69 and saves 55 ms, so the flag is earlier where it fires but misses 0.13 more of the Severe or Critical tests. | That the clip onset gives an early severity flag of 100 ms or more. |
| H-D2 | **MIXED** | The clip-onset flag has an over-triage of 0.054 [0.008 to 0.115]; the raw p-value is 0.055 (Holm-adjusted 0.385) and the interval reaches 0.115. | That the over-triage is below 10% with confidence. |
| H-E1 | **NOT SUPPORTED** | Dropping the tag from 8 to 4 bytes changes critical reach within 10 s by 0.0086 [0.0035 to 0.0136] in the simulated burst cells (about one point). | That a shorter tag gives a capacity gain of 2 points or more. |
| H-E2 | **SUPPORTED** | With a truncated HMAC and a secret key, an 8-byte tag needs about 2^44 forgery attempts for a probability of 1e-6 (a count of attempts, not capped by the duty limit); the smallest tag with both work factors above 2^32 is 7 bytes. The duty limit does not bind an attacker. | A cryptographic proof; that the key cannot be recovered. |
| H-F1 | **NOT SUPPORTED** | In the cost model a positive Critical hold is optimal when D / C_false is below 52 at the precision of the deployed forest at 0.02% prevalence. | That a zero Critical hold is optimal for any cost ratio. |
| H-F2 | **SUPPORTED** | In the simulator, a 2 s hold of Severe alerts reduces the share of false Severe alerts reaching the base by a relative 0.32 [0.25 to 0.39]; critical reach within 10 s changes by -0.008 [-0.029 to 0.010] (a loss of up to 2.9 points is not excluded); the delay to true Severe alerts is not measured. | That the hold is free in the field (the cancel model and every cost are assumptions). |

Studies A and D use 176 NHTSA tests (mostly high-speed barrier tests, not representative of all real crashes); B, H-E1 and F2 are simulations with assumed values, H-E2 and F1 are formulas; the 1% duty limit is not verified for India. Study C is NOT_RUN (see `docs/03_results/V2_RESULTS.md`).

## Allowed wording for the journal-push claims (generated)

| Claim | Allowed wording | Not allowed |
|---|---|---|
| T13a | On 739 NHTSA records of other test modes (506 of them pole tests), methods fitted on the 176 original tests reach a share within 10% of 0.808 [0.775 to 0.840] at +-64 g and 200 Hz and 0.824 [0.794 to 0.852] at +-200 g; no range and rate cell has its lower end at 0.80. At +-16 g fill + ridge has a median error of 18.0% against 16.7% for the spline (paired difference 1.31 [-1.41 to 4.37] points). | That the N13 or N14 findings hold for other crash modes; that fill + ridge beats the spline outside frontal and left-side tests. |
| T13c | Two of the 176 records are the same test channel counted twice (2 pairs); without the flagged tests fill + ridge still has the whole interval below zero against the spline at +-16 g on splits A, G and R (exploratory). | That the NHTSA split is free of duplicates (the duplicates were present in the tagged runs). |
| Sensor selection | On the 176 tests, 30 of 99 configurations of 8 accelerometer parts have a lower interval end of 0.80 within +-10%; the smallest range among them is +-64 g (KX134-1211 at 400 Hz: 0.898, lower end 0.851); no MPU-6050, ADXL345 or LIS3DH configuration does. On the held-out modes no configuration does. | That a part will perform so on a vehicle (software sensor model; datasheet rates, not ESP32 read rates; mostly high-speed barrier tests). |
| V1/V2 | The recomputation from the raw files agrees with every stored count (217 cross-split groups; 1,305 of 5,863 triggered test windows equal a train or validation window, sample for sample). About a fifth of the triggered test windows (22.3%) and 29.6% of the crash test events are affected; the strict set removes about 5% of all test events beyond the primary rule. | That the duplicates are whole 16 s recordings (only the exact-copy events are). |
| V4 | For the 15-tree forest, removing the window-level duplicates lowers system recall by 0.0280 [0.0235 to 0.0326] and recall at the 1% target by 0.0727 [0.0641 to 0.0809]; removing exact copies only changes them by 0.0006 [-0.0008 to 0.0018] and 0.0045 [0.0024 to 0.0067]. | That the duplicates explain all of the gap to a clean evaluation (vehicle-level leakage cannot be checked). |
| H-X1 | Quantising thresholds and leaves of the 10-tree forest to 16 bits changes AP by 0.000000 (upper 95% bound 0.00002); the host flash estimate falls by 22.2% in the existing node layout (44.4% if the left child is implicit). | That the flash target of 30% is met with the existing layout; any ESP32 compile size. |
| H-X2 | At a non-crash trigger rate not above that of 2 g, the cascade passes 0.964 [0.958 to 0.969] of crashes against 0.964 [0.958 to 0.969] for the 2 g threshold; the rule chosen is the 2 g threshold itself in most held-out categories. | That a cheap running-feature trigger beats the fixed threshold on VZCrash. |
| H-X3 | Down-weighting duplicate training windows changes recall at the 1% target on the strict set by 0.0011 [-0.0022 to 0.0045]; 19.0% of training windows are in a duplicate group. | That duplicates in training explain the gap between the supplied and the strict set. |
| H-X5 | At +-16 g and 100 Hz the Spearman correlation of fill + ridge with the reference delta-V is 0.751 [0.678 to 0.805], below the plain estimate's 0.841 [0.791 to 0.875]; at +-32 g it is 0.919 [0.887 to 0.941] and at +-64 g 0.966 [0.949 to 0.979]. Class agreement of fill + ridge at +-16 g: 0.717 [0.649 to 0.779]. | That a +-16 g sensor preserves the order of severity; any claim about injury in real crashes. |
| H-X6 | At +-16 g on split R the 90th-percentile error of the anchored estimator is 27.5% against 58.5% for fill + ridge (gain 31.0 [20.2 to 37.8] points); the gain has its interval above zero on split A and not on G or O; the anchored estimate is never below the plain estimate and over-corrects the 2 tests where plain exceeds the reference. | That it has a lower median error than the tail-aware model (8.9% against 8.5%), that the gain holds on every split, or that it works on a real sensor. |
| H-X7 | None of the 16 preregistered pairs and two fusion rules reaches a lower end of 0.80 (0 of 32 combinations meet it); a wider clipped-sample mask, defined after the initial result (exploratory), reaches it for 3 combinations where neither part alone does. | That fusing a +-16 g and a +-200 g part works as a general method; any time-synchronised or mounted result. |
| H-X8 | At the 1% target the sequential rule decides 120 [40 to 200] ms earlier at the median than the early-exit rule, with recall 0.0081 [0.0029 to 0.0135] higher; at 5% the difference is -20 [-120 to -20] ms (positive = the sequential rule is earlier) and recall -0.0015 [-0.0020 to -0.0009]. The recall gain over the single forest is an ensemble effect. | That the sequential rule is faster at both targets. |
<!-- claims:end -->

<!-- PP:BEGIN -->
## Positive-results push (branch `positive-push`; generated by `pp_docs.py`)

Verdicts of the seven preregistered hypotheses are Holm-corrected (`p.holm.*`). REPORTED = a descriptive result, no hypothesis; EXPLORATORY = defined after seeing results or optional. Allowed wording: state the number with its interval and label; do not write that a method is better, general or deployable unless the verdict says SUPPORTED, and then only on this data (crash tests, mostly high-speed; VZCrash events pre-selected on the device).

| Claim | Evidence label | Section | Keys | Verdict |
|---|---|---|---|---|
| P1: a direct ordinal classifier lowers under-triage and raises macro-F1 by at least 3 points against the best of plain, fill + ridge and anchored estimators in at least two of three ranges (sealed fold) | MEASURED_SOFTWARE | P1 | `p.p1.*; p.holm.hp1.*` | **NOT SUPPORTED** |
| P1 (descriptive): at +-16 g and 100 Hz the best deployable direct model raises macro-F1 by 0.169 [0.046, 0.291] on the sealed fold; under-triage changes by -0.032 [-0.197, 0.125] | MEASURED_SOFTWARE | P1 | `p.p1.r16.f100.paired.*` | **REPORTED** |
| P1 (EXPLORATORY, cross-validation over all 913 records, sealed-fold records included): the augmented 1D CNN raises macro-F1 over the anchored estimator at +-16 g by 0.086 [0.039, 0.130] and at +-32 g by 0.045 [0.003, 0.087]; under-triage is not lower beyond noise (-0.029 [-0.076, 0.018] at +-16 g) | MEASURED_SOFTWARE | P1 | `p.p1cvcnn.*` | **EXPLORATORY** |
| Z1: the crash mode can be inferred from the clipped pulse with balanced accuracy 0.75 (+-16 g), 0.80 (+-32 g), 0.87 (+-64 g) on the sealed fold | MEASURED_SOFTWARE | Z1 | `p.p1.r*.f100.mode.*` | **REPORTED** |
| P2: the interval [plain, plain x q] keeps coverage of at least 0.85 (lower end) overall and for pole and is at least 20% narrower in upper-to-lower ratio than the relative-residual interval around fill + ridge | MEASURED_SOFTWARE | P2 | `p.p2.*; p.holm.hp2.*` | **NOT SUPPORTED** |
| P2 (descriptive): coverage of the one-sided interval at +-16 g is 0.914 [0.871, 0.957]; the lower bound is violated more often at +-32 and +-64 g (share of validation records with reference below plain: see `docs/03_results/POSITIVE_PUSH_RESULTS.md`) | MEASURED_SOFTWARE | P2 | `p.p2.r16.f100.global.coverage*` | **REPORTED** |
| P3a: abstaining on 30% of events halves the under-triage rate of the anchored estimator among retained events and keeps the retained p90 error at or below 20% at +-16 g | MEASURED_SOFTWARE | P3a | `p.p3a.*; p.holm.hp3a.*` | **NOT SUPPORTED** |
| P3b: routing abstained events to the fast path lowers mis-triage by 2 points against a severity table with lowered thresholds at equal escalation | MEASURED_SOFTWARE + SIMULATED | P3b | `p.p3b.*; p.holm.hp3b.*` | **NOT SUPPORTED** |
| P4a: a forest with at most half the flash estimate stays within 0.01 AP of the 10-tree depth-9 forest (trees 8, depth 8, k 14, q16: 20.6 kB against 55.1 kB; AP loss 0.0023 [0.0013, 0.0036]; flash is ANALYTICAL, the measured size is for an x86-64 host) | MEASURED_SOFTWARE + ANALYTICAL | P4a | `p.p4a.*; p.holm.hp4a.*` | **SUPPORTED** |
| P4b: augmentation with group-aware merging raises recall at the 1% target on the strict VZCrash test set by 2 points | MEASURED_SOFTWARE | P4b | `p.p4b.*; p.holm.hp4b.*` | **NOT SUPPORTED** |
| P4c: a group-wise calibration restores the false-alarm guarantee under vehicle-size shift with recall at least 2 points above the trivial rule | MEASURED_SOFTWARE | P4c | `p.p4c.*; p.holm.hp4c.*` | **NOT SUPPORTED** |
| P4d (EXPLORATORY): an int8 tiny 1D CNN (1633 weights) reaches AP 0.961 [0.957, 0.966] against 0.938 for the 10-tree depth-9 forest on the de-duplicated test set; no hypothesis and no multiplicity correction | MEASURED_SOFTWARE + ANALYTICAL (flash) | P4d | `p.p4d.*; p.p4a.dedup.ap_reference` | **EXPLORATORY** |
| B2: a plain delta-V estimate reaches a lower interval end of 0.80 within +-10% for frontal barrier tests at a smaller range than for pole tests; none of the 99 configurations reaches it for side or other tests | MEASURED_SOFTWARE | B2 | `p.b2.*` | **REPORTED** |
<!-- PP:END -->
