# Novelty: what can and cannot be claimed

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | What can and cannot be claimed as new. |
| Evidence labels used | SIMULATED_HW_FORMAT, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; ASI = acceleration severity index; CV = cross-validation; CoAP = Constrained Application Protocol; EDR = event data recorder; ESP32 = a Wi-Fi microcontroller family (Espressif); ESV = Enhanced Safety of Vehicles (conference); GPS = Global Positioning System; HMAC = hash-based message authentication code; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; IMU = inertial measurement unit; LoRa = long-range radio modulation; MCU = microcontroller unit; MEMS = micro-electromechanical system; MIC = message integrity code (LoRaWAN); MQTT = Message Queuing Telemetry Transport; NHTSA = National Highway Traffic Safety Administration; PDOF = principal direction of force; SCT = severity-classified transmission; SF = spreading factor (LoRa); SW-420 = a vibration switch module; UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

The contribution is the **combination**, measured end to end. Standalone IoT accident detection is not new.

## Already in the literature (do not claim)
- Accelerometer + GPS crash alert (2020, 2022 project papers).
- Cancel/countdown before sending (2022: 30 s alarm; 2024: cancel button).
- Accelerometer rollover detection (2024 Visual Situation paper).
- LoRa for accident/disaster alerts (2022 search & rescue; 2025 vehicle disaster; 2025 drones).
- Encrypted/integrity-checked LoRa packets (2022 search & rescue paper); ECIES accident reports (2023); blockchain + LoRa (2025 drones).

## Candidate points (each needs its measurement)
| # | Claim | Evidence needed |
|---|---|---|
| N1 | Real-crash-trained detector on a cheap MCU, with a transfer test to the scale model | S2–S6, E6, E7 |
| N2 | Impact side + angle from one IMU in the alert | E1 |
| N3 | HMAC + anti-replay + signed ACK on the MCU, with the spoofed-ACK case | S7, E5 |
| N4 | Severity-aware delivery under a 10% duty-cycle budget | S8, S9, E4 |
| N5 | Measured stage-by-stage latency against HTTP/MQTT/CoAP | E4 + protocols.csv |
| N6 | Open labelled scale-model dataset | release of hw_events + windows |
| N7 | Measured value of a cheap vibration array | E8 |
| N14 | Saturation-aware severity estimator (a pulse-model fill of clipped samples) | `n14.*` held-out result |
| N15 | Trigger-aware training (joint trigger and classifier design) | `n15.*` seed-averaged paired result |
| N16 | Severity- and budget-aware delivery scheduler (simulation, supporting only) | `n16.*` held-out scenarios |

In the 24 project PDFs, no text match was found for HMAC, duty cycle or delta-V, no protocol acknowledgement, and "replay" appears only for voice spoofing and for a federated-learning scheme (`docs/03_results/CLAIM_EVIDENCE.md`). This shows absence only in those 24 papers. Searches beyond them (`docs/06_references/PRIOR_WORK.md`) found an ESP32 HMAC-counter component, the LoRaWAN retransmission-versus-replay discussion, delta-V and direction from consumer MEMS in a full-size crash, a clipped-sensor estimator patent and two-stage crash pipelines, so each point below is worded as "we found / in the sources checked". IEEE Xplore and Scopus could not be searched; the strings are in `docs/06_references/MANUAL_SEARCH_CHECKLIST.md`.

## Wording rules
- The vibration sensors confirm an impact; they do not locate it (the chassis is about 20 cm).
- Scale-model "severity" is impact strength, not injury severity.
- India 433–434.79 MHz: 10 mW e.r.p. and 10% duty cycle are confirmed by G.S.R. 347(E) of 2022 (rule 3 row 1; full text read on 2026-11-16; the observation interval of the duty cycle is not stated). The 10 kHz channel-width mismatch is a testbed limitation; a deployed system would use 865–867 MHz.

<!-- novelty:start -->

## Status after the software milestones (generated, see `report/novelty_summary.md`)

**Headline contribution:** the integrated system (MCU detector, impact direction, authenticated severity-aware LoRa delivery), evaluated end to end. N8 and N9 are evaluation-rigour contributions, not the headline. N11 is a results breakdown, not a contribution. N16 is supporting evidence from simulation, not a contribution. N2 is a supporting feature and N6 is weak (RC-car and open-dataset precedents). N12 is an independent re-discovery of a known LoRaWAN issue in a custom point-to-point link, with a bounded fix.

Statuses: SUPPORTED = software evidence exists for the claim as worded (N14 to N16: the gain clears the 95% interval on data not tuned on); PARTIAL = software done, hardware NOT_RUN or simulation only; NO_IMPROVEMENT_FOUND = tried, no gain beyond the interval; NOT_YET = no evidence yet. The prior-work record is in `docs/06_references/PRIOR_WORK.md`. Hardware IDs H1 to H6 are the minimum plan (see `docs/02_preregistration/EXPERIMENTS.md`).

| Point | Claim | Role | Status | Closest prior work |
|---|---|---|---|---|
| HL | Integrated system: MCU detector + impact direction + authenticated, severity-aware LoRa delivery (software parts built and tested; the end-to-end evaluation on hardware has not been run) | headline | PARTIAL | Each part has prior work; no source found that combines them end to end |
| N1 | Real-crash-trained detector on a cheap MCU, with a transfer test to the scale model | component | PARTIAL | TinyML crash projects; Katsidimas 2023 (forest on Arduino); Balfaqih 2022; emlearn |
| N2 | Impact side and angle from one IMU in the alert | component | NOT_YET | Ebert 2016 (phone IMU, RC car); Balfaqih 2022; Tadic 2016 (PDOF from MEMS) |
| N3 | HMAC, anti-replay counter and signed ACK on the MCU, with the spoofed-ACK case | component | PARTIAL | LoRaWAN MIC and counter; ESP32 HMAC-counter component (msg_auth) |
| N4 | Severity-aware delivery under a 10% duty-cycle budget | component | PARTIAL | Priority-aware LoRa scheduling; LoRaWANSim |
| N5 | Measured stage-by-stage latency against HTTP, MQTT and CoAP | component | NOT_YET | IETF MAPRG protocol slides |
| N6 | Open labelled scale-model dataset | component | NOT_YET | Ebert 2016 (RC car); Katsidimas 2023 (open impact data, plates) |
| N7 | Measured value of a cheap vibration-sensor array | component | NOT_YET | SW-420 hobby projects |
| N13 | Physics-based severity (delta-V + ASI) from one IMU window, carried in the authenticated alert, with a measured requirement on accelerometer range and rate (NHTSA crash tests, mostly high-speed barrier tests, not representative of all real crashes) | component | PARTIAL | EDR delta-V and ASI studies; NHTSA EDR round robin; Tadic 2016 |
| N14 | Clipping restoration for delta-V at low sensor range: a pulse-fit fill with a small ridge correction against spline restoration and plain integration (one range, re-split tests, not a blind test; fill + ridge was named primary after earlier results were seen; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes) | component | SUPPORTED | Spline restoration (Ruder; Chan 2023); US 7,643,921; `SAE 2025-01-5046` pulse fits |
| N15 | Trigger-aware training: joint selection, cost-sensitive training and a learned trigger raise system recall at a fixed false-alarm rate | component | NO_IMPROVEMENT_FOUND | Cascade detectors; two-stage crash pipelines (Kubin 2021, Taccari 2018) |
| N16 | Severity- and budget-aware delivery scheduler (reserve, severity-and-age order, ACK-feedback back-off, optional spreading-factor raise): improves on a fixed retry policy; against a severity table it does not clear zero in the original held-out scenarios and does in the later burst simulator (S5) (SIMULATED; two simulators with different scenario sets; supporting evidence, not a contribution) | component | PARTIAL | Priority-based LoRa allocation (Wei 2023); duty-cycle blackouts (Tomic 2020); back-off with jitter |
| N17 | Impact direction (front against side) from one low-rate IMU, checked on NHTSA crash tests (validation of a supporting feature, not a contribution; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes) | extra experiment | SUPPORTED | Kusano and Gabler 2013; Tadic 2016; Ebert 2016 |
| N18 | Severity measures against dummy injury criteria: delta-V adds no positive association beyond impact speed for frontal chest and head criteria (the partial association with chest acceleration is small and negative); ASI tracks chest acceleration (descriptive, small sample, NHTSA tests) | extra experiment | NO_IMPROVEMENT_FOUND | NHTSA and ESV dummy-criteria literature (snippets) |
| N19 | Early classification: a sequential early-exit rule over six length-specific forests decides about one second earlier (mean over triggered crash events, both false-alarm targets). The part that clears its interval is the time saving; the recall gain over the single full-length forest is an ensemble effect, not an early-exit effect (VZCrash, second trigger on pre-selected events; timing read from the window length, no ESP32 timing) | extra experiment | SUPPORTED | Airbag-algorithm timing; early-exit classification (snippets) |
| N20 | Guaranteed false-alarm control by split-conformal thresholds: the guarantee does not hold on the de-duplicated test set and the threshold is no better than the validation threshold | extra experiment | NO_IMPROVEMENT_FOUND | Split-conformal anomaly detection (snippets) |
| N21 | Sensor-spoofing robustness: a bounded added signal can make non-crash windows alarm from about `0.5` g; simple defences help a little against false crashes at small budgets and cost on hidden crashes (simulation on dataset windows) | extra experiment | PARTIAL | Tu et al. 2018 (acoustic injection); Son 2015 and Trippel 2017 (cited) |
| N22 | Many-car LoRa capacity: at SF7 and the low default alert rate the channel, not the base's ACK duty budget, limits delivery up to `500` cars (at SF12 and high alert rates both limits are large); spaced retries recover most of a burst in the X6 simulator (analytical and simulated) | extra experiment | PARTIAL | Tomic 2020; Wei 2023; Zhong and Nie 2024; LoRa ALOHA and capture analyses |
| N23 | Scale-model transfer by physical scaling of VZCrash events: amplitude dominates, the scale-free features are not invariant (a plausibility check, no claim) | extra experiment | PARTIAL | Scale-model crash similitude (snippets) |
| N24 | Conformal intervals for the clipped delta-V estimate: coverage is about nominal, but the class rule built on them (report the class below when the lower bound is lower, plus a flag) raises under-estimation instead of lowering it (grouped CV+, NHTSA tests, no simulation) | extra experiment | NO_IMPROVEMENT_FOUND | CHOIR (conformal injury severity on police records); jackknife+ and CV+ (abstracts opened) |
| N25 | Prevalence-adaptive alert threshold: the existing threshold gives very low precision at realistic prevalence, but no tested rule (prior-shift adjusted, minimum expected cost, target precision) raises precision within five points of recall at prevalences up to one per cent (VZCrash pools resampled; costs are assumptions) | extra experiment | NO_IMPROVEMENT_FOUND | Saerens 2002 prior shift by EM; Elkan 2001 cost-sensitive decisions (abstracts opened) |
| N26 | Severity-Classified Transmission (SCT): a fast path with a short authenticated flash, a spaced-retry rule and no hold for Critical alerts raises critical reach within ten seconds in bursts, also against a severity table with spaced retries; against the severity table it does not help in steady state (it does against the spaced-retry table, whose spacing costs reach there) and it is worse than the table for a single car at high loss (EXPLORATORY); in ablations (EXPLORATORY) the flash, the hold and the spreading-factor raise carry the gain, while the reserved duty share and the CANCEL message show no effect on reach, and faster retries repair the single-car case but cost reach in bursts (SIMULATED; one-hour duty rule, parameters tuned on separate scenarios) | extra experiment | PARTIAL | Tamang 2022 urgent packets; Shao 2020 interrupt access; Wei 2023; Tomic 2020 |
| N27 | Bounded model check of the alert protocol: within the stated bounds the counter, replay, re-ACK, signed-ACK and CANCEL rules hold against a bounded attacker; strict anti-replay without the re-ACK loses liveness; counters that are not persisted break replay protection and ACK matching (ANALYTICAL, a check of a model, not a proof of the firmware) | extra experiment | PARTIAL | Gao 2019 (Scyther); Dong 2024 (PAT); Wesemeyer 2020 (Tamarin, join procedure) |
| N28 | Uncertainty-aware SCT (UA-SCT): taking the class from the upper end of a conformal class interval lowers mis-triage of Severe and Critical events against the severity table (the preregistered hypotheses H-a and H-c hold; for H-b the escalation part holds and the airtime cap of P4 barely binds), at the cost of many more escalations of non-severe events; at equal escalation the same reduction is reached by lowering the thresholds of the plain table, and critical reach within 30 s in bursts is slightly lower than with plain SCT (SIMULATED on NHTSA class pairs, mostly high-speed barrier tests, not representative of all real crashes) | extra experiment | NO_IMPROVEMENT_FOUND | CHOIR; Tamang 2022; Shao 2020 |
| N29 | Tail-aware clipping estimator: a quantile boosting model on clipping descriptors and pulse-family features lowers the `90th`-percentile delta-V error against fill + ridge at +-16 g on repeated grouped cross-validation (interval above zero) and, as point estimates above 5 points, on two of three fixed splits (only one of them with its interval above zero) (preregistered; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes); plain gradient boosting, tried as an EXPLORATORY variant, has a lower `90th` percentile still | extra experiment | SUPPORTED | Chan 2023 spline restoration (opened); other named papers not opened |
| N30 | Deterministic bounds and adaptive conformal intervals for the clipped delta-V estimate: the plain estimate is a lower bound for almost every test at +-16 g (not at `+-32 g` and `+-64 g`), but the pulse-family upper bound does not contain the reference for enough tests and normalised-score intervals are wider, not narrower, where clipping is mild (preregistered; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes) | extra experiment | NO_IMPROVEMENT_FOUND | CHOIR; jackknife+ and CV+ (abstracts opened) |
| N31 | Clip-onset early severity flag: the time from the trigger to the earliest near-full-scale sample flags only part of the Severe or Critical events at +-16 g, with a median time saved under 100 ms, and it misses more Severe or Critical tests than a running delta-V threshold (preregistered; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes; events that never clip cannot be flagged) | extra experiment | NO_IMPROVEMENT_FOUND | Early-exit classification (snippets); N19 |
| N32 | Load-adaptive escalation: five variants (a per-car controller, a token bucket, a base-station beacon, severity-scaled backoff, graceful demotion) do not raise critical reach within 10 s by 3 points over a matched fixed lowered-threshold rule in the simulated burst cells (small gains in a few cells); the beacon variant lowers it in some cells (SIMULATED; preregistered; every channel and traffic value is an assumption) | extra experiment | NO_IMPROVEMENT_FOUND | Tamang 2022; Shao 2020 (abstract) |
| N33 | Authentication-tag length: an 8-byte tag keeps the forgery work factor (a count of attempts, which the duty limit does not cap) far above 2^32 attempts (ANALYTICAL; truncated HMAC, secret key, no proof), and a 4-byte tag raises critical reach within 10 s in simulated bursts by less than one point (SIMULATED), so there is no capacity reason to shorten the tag | extra experiment | PARTIAL | Truncated tags are a known trade-off; no source opened |
| N34 | Severity-dependent hold: a 2 s hold of Severe alerts cuts the share of false Severe alerts that reach the base without a significant loss in critical reach (SIMULATED; cancel model and costs are assumptions), while the cost model puts the optimal Critical hold at zero only above a cost ratio that depends on the precision (ANALYTICAL) | extra experiment | PARTIAL | None opened |
| N8 | Dataset audit: identical recordings across the official VZCrash splits | evaluation rigour | SUPPORTED | Leakage audits of other datasets; VZCrash paper (III-B) states vehicle-level splits |
| N9 | Trigger-aware evaluation: system-level recall including the trigger stage | evaluation rigour | SUPPORTED | Taccari et al. 2018; two-stage patents; VZCrash real-world population test |
| N10 | Size against accuracy on the MCU, with C-export equivalence | design finding | SUPPORTED | Leaf-refinement paper (2021); emlearn |
| N11 | False-positive rate on near_miss events alone (a results breakdown, not a contribution) | results breakdown | SUPPORTED | VZCrash paper false-positive counts; phone crash-detection studies |
| N12 | Retry versus replay: an independent re-discovery of a known LoRaWAN issue in a custom point-to-point link, with a bounded fix | design finding | SUPPORTED | Known LoRaWAN retransmission-versus-replay issue (ChirpStack discussion) |
| SF | Scale-free features keep most of the AP (a hypothesis for the transfer argument in N1; the physical-scaling check in N23 shows them not invariant) | component | PARTIAL | none found |

<!-- novelty:end -->

<!-- v11:start -->
## Combined run (V11): software-checked on simulated hardware-format data

Statuses for hardware stay as above (NOT_YET). The column below says only what the simulated hardware-format logs (SIMULATED_HW_FORMAT) checked in software; it is never a hardware result.

| Item | Hardware status | Software check on simulated hardware-format logs |
|---|---|---|
| N2 impact side and angle from one IMU | NOT_YET | software-checked: the rule keeps 0.90 or more under tilts up to 30 degrees and fails under an axis-sign flip and at 10 Hz (3 of 16 sets below 0.90; H-S1 NOT SUPPORTED) |
| N5 stage-by-stage latency against HTTP, MQTT and CoAP | NOT_YET | software-checked for the LoRa path only: trigger-to-ACK about 519 ms in the model (H-S4 SUPPORTED); H5 edge timing stays NOT_RUN (placeholder timings) |
| N6 open labelled scale-model dataset | NOT_YET | not checked: the simulated logs are not a dataset |
| N7 measured value of a cheap vibration-sensor array | NOT_YET | software-checked in simulation: false-alarm reduction 0.29, recall loss 0.04, and the sign of the gain depends on the assumed switch sensitivity (H-S6 NOT SUPPORTED) |

<!-- v11:end -->
