# Product Requirements Document: CrashGuard software

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | Original requirements for the software side and what counts as done. |
| Evidence labels used | SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; CPU = central processing unit; CoAP = Constrained Application Protocol; DoT = Department of Telecommunications (India); ESP32 = a Wi-Fi microcontroller family (Espressif); FPR = false-positive rate; GPU = graphics processing unit; HTTP = Hypertext Transfer Protocol; IMU = inertial measurement unit; LoRa = long-range radio modulation; MPU6050 = an accelerometer and gyroscope chip; MQTT = Message Queuing Telemetry Transport; PR = precision-recall; RF = random forest; SW-420 = a vibration switch module; SX1278 = a 433 MHz LoRa radio chip; WPC = Wireless Planning and Coordination wing (India) |
<!-- header:end -->

| | |
|---|---|
| Owner | Mritula S |
| Version | 1.0 (10 Nov 2026) |
| Scope | Software, data science and simulation. Hardware is out of scope except for ingesting its logs. |

## 1. Background
CrashGuard detects a collision on an ESP32 with an MPU6050 IMU at 100 Hz and five SW-420 vibration sensors. It estimates severity and impact side, and sends an HMAC-signed alert over 433 MHz LoRa (SX1278 / Ra-02) to an ESP32 base station, which returns a signed ACK.

Hardware results so far are in `data/hardware/`:
- an HTTP / MQTT / CoAP comparison;
- LoRa test and telemetry packets;
- gateway counters.

No crash has been classified yet. The software side must supply:
1. a detector trained on real crashes that fits on the ESP32;
2. checks of the alert design;
3. simulations of delivery under the legal duty-cycle limit;
4. a merge path for the hardware experiments.

## 2. Goals
| ID | Goal | Linked novelty point |
|---|---|---|
| G1 | Train and compare crash detectors on VZCrash with vehicle- or trip-held-out splits | N1 |
| G2 | Export a 15-tree, depth-6 random forest to plain C that matches Python exactly | N1 |
| G3 | Test transfer from full-size crashes to scale-model data, with all features and with scale-free features only | N1 |
| G4 | Specify and test the 97-byte signed alert and signed ACK against an attack suite | N3 |
| G5 | Calculate LoRa airtime and duty-cycle budgets, and simulate severity-aware delivery against a naive retry policy | N4 |
| G6 | Ingest hardware logs and produce all paper tables and figures, including the measured latency breakdown | N2, N4, N5, N7 |
| G7 | Produce a reproducible repo and a plain-language results section | N6 (dataset release support) |

## 3. Non-goals
- Firmware development. The firmware already exists; this repo only generates `crashguard_rf.h` and a benchmark sketch.
- Encryption of alerts (future work).
- Blockchain (future work).
- Claims about human injury severity.

## 4. Users
- **The author**: runs the pipeline and merges hardware data.
- **The reviewer or examiner**: reruns `make all` and checks claims against `results.json`.

## 5. Functional requirements
### FR1 Data (`make data`)
- Download VZCrash with `huggingface_hub` or `datasets`. On failure, stop with a clear message and never fall back to fake data.
- Write `docs/05_data_code/DATASET_FACTS.md`, marking each fact CONFIRMED_FROM_DATA or CONFIRMED_FROM_CARD/PAPER. Highlight any difference from `docs/05_data_code/DATASET.md`.
- Run quality checks: missing values, sampling-rate consistency, duplicates, constant signals, and class balance.

### FR2 Features (`make features`)
- Window of about 2.8 s around the trigger at 100 Hz; adapt to the dataset and document the choice.
- Compute the 14 features defined in `docs/05_data_code/FEATURES.md`, and flag the `scale_free` subset.

### FR3 Models (`make train`)
- Models to compare:
  - RF with 15 trees, depth 6 (the deployable model);
  - RF with 200 trees (reference);
  - logistic regression;
  - gradient-boosted trees;
  - a rule detector (peak and duration).
- Splits: train/validation/test held out by vehicle or trip. Thresholds are set on validation.
- Metrics: AP, precision, recall, F1, FPR at recall 0.95, ROC-AUC, confusion matrix, PR curve, and calibration curve. Report mean ± std over 5 seeds.
- Ablation: all features against `scale_free` only.
- Error analysis: the top 20 false positives and top 20 false negatives.

### FR4 Export (`make export`)
- `firmware_export/crashguard_rf.h`: `const` arrays, no heap, and `float predict_prob(const float f[14])`.
- An equivalence test: compile with gcc and compare against Python on the full test set. The maximum absolute difference must be ≤ 1e-6.
- Host size estimate (labelled ANALYTICAL) and `benchmark_rf.ino`, which times 1,000 calls on the ESP32.

### FR5 Security (`make security`)
- Encode and decode the packet as in `docs/01_protocol/PACKET_FORMAT.md`.
- Reference verifier with counter persistence.
- Attack suite with expected outcomes:

| Case | Expected |
|---|---|
| Valid | accept |
| Forged tag | reject |
| Tampered field | reject |
| Replay | reject |
| Old counter | reject |
| Spoofed ACK | reject |
| Base reboot, counter persisted | reject replay |
| Base reboot, counter lost | **document** the vulnerability |

### FR6 LoRa (`make lora`)
- Semtech airtime formula, parameterised. Check: 97 B at SF7/125 kHz/CR4-5 should come to about 169 ms.
- Alerts per hour at a 10% duty cycle for SF7 to SF12.
- Event-driven delivery simulation with a token bucket. Packet loss is swept from 0 to 60%. Compare the severity policy against a fixed 3-retry policy.

### FR7 Merge (`make merge`)
- Read `data/hardware/*.csv` using the schemas in `docs/05_data_code/HARDWARE_SCHEMA.md`. Any file that is missing gives `NOT_RUN`.
- When `hw_events.csv` is present, run the following:
  - E1 impact-side confusion matrix and angle error;
  - E2 crash detection metrics, rules against the model;
  - E3 severity against peak g;
  - E4 delivery rate and latency by distance and severity;
  - E5 the measured attack table, if logged;
  - E6 timings;
  - E7 transfer;
  - E8 SW-420 ablation.
- Plot the hardware protocol results next to the LoRa results.

### FR8 Report (`make report`)
- Write `report/software_results.md` with these sections: what was run, tables, figures with captions, "What these results do and do not show", and "Still needed from hardware".
- Every number in it must exist in `results.json`. A test enforces this.

## 6. Non-functional requirements
- Python 3.11 or later with pinned dependencies. Runs on a laptop CPU; there are no GPU requirements.
- `make all` should finish within about 2 hours on a laptop. Subsample for development with `FAST=1`.
- Code is typed, has docstrings and passes `ruff`. Tests cover the packet, airtime, export equivalence and merge schemas.

## 7. Acceptance criteria (definition of done)
1. `make all && make test` pass from a clean clone.
2. `results.json` contains every reported number, each with an origin label. Nothing is labelled MEASURED unless it was computed.
3. The C model is equivalent to the Python model (≤ 1e-6).
4. The airtime check passes (97 B at SF7 comes to about 169 ms).
5. The attack-suite outcomes match the table in FR5.
6. The merge runs on the dummy file (with watermarks) and reports NOT_RUN without real files.
7. `report/software_results.md` exists, contains no invented numbers, and includes a limitations section.

## 8. Risks and limitations
| Risk | Mitigation |
|---|---|
| The VZCrash schema differs from the notes | FR1 facts file; log in DECISIONS.md |
| No vehicle ID, so leakage between splits | Group by the most independent key and state it |
| Transfer to the scale model fails | Report it as a finding (it motivates own data) |
| Class imbalance | Use AP and PR curves, not accuracy |
| The simulation loss model is unrealistic | Label it SIMULATED and compare with E4 hardware |
| Regulatory figures are unverified | Check against the official WPC/DoT notification |

## 9. Milestones
| M | Deliverable |
|---|---|
| M1 | `make data` + DATASET_FACTS.md |
| M2 | features + models + figures |
| M3 | C export + equivalence |
| M4 | security suite |
| M5 | LoRa analytics + simulation |
| M6 | merge + report |
