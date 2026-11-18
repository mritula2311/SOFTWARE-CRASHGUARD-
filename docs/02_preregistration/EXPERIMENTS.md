# Experiments, metrics and figures

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Experiment list with metrics, figures and origin labels (original plan). |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; FPR = false-positive rate; LoRa = long-range radio modulation; NHTSA = National Highway Traffic Safety Administration; PR = precision-recall; RAM = random-access memory; RSSI = received signal strength indicator; SNR = signal-to-noise ratio; SW-420 = a vibration switch module |
<!-- header:end -->

## Software (this repo)
| ID | Experiment | Metrics | Figures | Origin |
|---|---|---|---|---|
| S1 | Dataset profile | counts, balance, quality | class balance | MEASURED_SOFTWARE |
| S2 | Model comparison (5 models × 5 seeds) | AP, P, R, F1, FPR@R0.95, ROC-AUC | PR curves, confusion matrix | MEASURED_SOFTWARE |
| S3 | Feature ablation (all vs scale-free) | AP, F1 | bar chart | MEASURED_SOFTWARE |
| S4 | Size vs performance | AP against nodes/bytes | scatter | MEASURED_SOFTWARE / ANALYTICAL |
| S5 | Calibration | reliability, Brier | reliability curve | MEASURED_SOFTWARE |
| S6 | C export equivalence | max abs diff | none | MEASURED_SOFTWARE |
| S7 | Attack suite | accept/reject | table image | SIMULATED |
| S8 | Airtime + duty budget | ms, alerts/h | airtime curve, alerts/h | ANALYTICAL |
| S9 | Delivery simulation | delivery %, time to ACK | delivery vs loss, ACK time by severity | SIMULATED |

## Minimum hardware plan (H1 to H6), decided 2026-11-10
The `experiment` column of `hw_events.csv` uses these IDs. They replace E1 to E8 in the report and in `make merge` (old E-IDs in older logs are mapped).

| ID | What | Counts | Supports |
|---|---|---|---|
| H1 | Impact side | 10 hits on each of 4 sides + 10 vertical drops | N2 |
| H2 | Crash against not-crash, and transfer from VZCrash | the H1 hits + 30 non-crashes (taps, hard stops, ramp bumps, lift-and-place) | N1, scale-free transfer |
| H3 | LoRa delivery | 20 alerts each at 10, 50 and 100 m (+ optional wall) | N4, N5 |
| H4 | Security | forged, tampered, replay, spoofed ACK, base reboot, ACK-lost retry; 3 tries each | N3, N12 |
| H5 | Edge cost | compile report + logged microseconds | N1, N3 |
| H6 | SW-420 ablation | re-analysis of H1 and H2 | N7 |

**Dropped from the plan, so they are limitations:** severity against impact strength (old E3) and the 200 m LoRa runs. The work cannot claim a measured severity response or a range beyond 100 m.

## Hardware (original list E1 to E8, kept for reference; see the minimum plan above)
| ID | Test | Procedure | Report |
|---|---|---|---|
| E1 | Impact direction | 20 hits per side + 20 vertical drops | 5-class confusion, angle error |
| E2 | Crash vs not-crash | ≥60 crashes at 3 speeds; ≥60 non-crashes | P, R, F1, FPR, rules vs model |
| E3 | Severity | speed / ramp height | peak g vs speed |
| E4 | LoRa delivery | 30 alerts at 10/50/100/200 m + walls | initial-try/final PDR, RTT, RSSI/SNR |
| E5 | Security | forged, tampered, replay, spoofed ACK, reboot | attack table |
| E6 | Edge cost | compile report + timings | flash/RAM, µs |
| E7 | Transfer | VZCrash → own data | AP/F1 all vs scale-free |
| E8 | SW-420 ablation | reuse E1/E2 | FPR/recall with/without, sw_first accuracy |

## Combined paper figures (after merge)
1. Protocol comparison (hardware) with LoRa airtime (analytical).
2. Latency breakdown per stage (hardware).
3. Delivery rate: simulation against measured.
4. Transfer result.
5. Direction confusion matrix.
6. SW-420 ablation.

## Software experiments added on 2026-11-11 (see `docs/02_preregistration/ALGORITHMS.md` for the rules fixed before the runs)
| ID | Experiment | Module | results.json prefix | Origin |
|---|---|---|---|---|
| S10 | Accelerometer range, sample rate and bandwidth study on NHTSA tests, named parts, release-rule tuning, class-limit sensitivity | `severity_study.py` | `sevstudy.*` | MEASURED_SOFTWARE (datasheet values ANALYTICAL) |
| S11 | Rollover false-alarm check and bootstrap intervals on VZCrash severity | `severity_vzcrash.py` | `severity_vzcrash.rollover.*`, `severity_vzcrash.ci.*` | MEASURED_SOFTWARE |
| S12 | Operating points at 1% and 5% false-alarm rate, calibration, headline and trigger intervals, deployment candidate | `detector_extra.py` | `detector.*`, `candidate.*` | MEASURED_SOFTWARE |
| S13 | Sensor-error robustness of three detectors | `robustness.py` | `robust.*` | SIMULATED |
| S14 | End-to-end replay of real events through trigger, model, severity, signed alert, lossy channel and verifier | `replay.py`, `replay_study.py` | `replay.*` | MEASURED_SOFTWARE pool, SIMULATED channel |
| S15 | Forgery and counter analysis; property-based tests and fuzzing | `forgery.py`, `tests/test_security_properties.py` | `forgery.*`, `counter.*` | ANALYTICAL |
| N14 | Saturation-aware severity estimator | `saturation.py`, `saturation_study.py` | `n14.*` | MEASURED_SOFTWARE, SIMULATED (synthetic) |
| N15 | Trigger-aware training | `trigger_aware.py` | `n15.*` | MEASURED_SOFTWARE |
| N16 | Severity- and budget-aware delivery scheduler | `scheduler.py`, `scheduler_study.py` | `n16.*` | SIMULATED |
