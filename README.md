# CrashGuard: software and data-science part

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Project purpose, honest status table, how to reproduce, licence, citation, data statement. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED_HW_FORMAT, TRACE_DRIVEN, SIMULATED, FORMAL, ANALYTICAL, HARDWARE, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; ESP32 = a Wi-Fi microcontroller family (Espressif); LoRa = long-range radio modulation; NHTSA = National Highway Traffic Safety Administration; SCT = severity-classified transmission; SRIHER = Sri Ramachandra Institute of Higher Education and Research; TLC = the TLA+ model checker; UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

CrashGuard is a low-cost crash-alert system. An ESP32 microcontroller reads one inertial sensor and five vibration sensors, decides whether a crash happened, estimates how severe it was and which side was hit, and sends an authenticated alert over LoRa to a base station.

This repository holds the **software side only**: the detection models, the severity estimate, the alert packet and its security checks, the LoRa delivery simulations, the formal protocol models, and the preregistered studies that test each proposed method. It also holds the paper sources and the scripts that will merge the author's hardware logs later.

Author: Mritula S, B.Tech Cybersecurity and IoT, SRIHER. Academic, non-commercial project.

**Nothing in this repository is a hardware measurement.** The car and radio experiments (H1 to H6) are not started. Every number comes from code in this repo and carries an origin label (see "How to read the results").

## Current status

| Item | State |
|---|---|
| Software pipeline (data, features, models, C export, security, LoRa, severity, studies) | Done and measured in software |
| Studies (rounds 1 to 7c, each preregistered before its runs) | Done in software; most proposed methods are **not supported** and are reported as negatives |
| Hypothesis ledger | 138 preregistered in 15 versions; 125 run: 48 supported, 72 not supported, 4 partly, 13 not run (`docs/04_audits/HYPOTHESIS_LEDGER.md`) |
| Formal models (ProVerif, Tamarin, bounded model check) | Done, with stated limits; TLC not run |
| ns-3 cross-checks | Done in software |
| Firmware | Built and compile-checked (ESP32 footprint is a build artifact); emulator counts, energy and on-device timing are NOT_RUN |
| Journal paper (`paper/main.tex`) and supplement | Written and audited; **not compiled here** (no TeX distribution; upload `paper/` to Overleaf) |
| Submission archive | `release/crashguard-submit-v6.2.zip` (tag `submit-v6.2`; SHA-256 and file list in `docs/04_audits/ROUND7E_REPORT.md`) |
| Car experiments H1 to H6 | Not started (hardware) |

"Built in firmware" means compile-checked only. "Built, not yet measured" means the code exists and no measurement has been made.

### Rounds in short

| Round | Topic | Outcome |
|---|---|---|
| 1 to 2 | Detector, severity (NHTSA), alert packet, attack suite, LoRa delivery simulation | Done; trigger and sensor range are placeholders until firmware v2 is confirmed |
| v2, journal push, positive push, finishing | Uncertainty-aware severity, group-aware training, audits | Mostly not supported (`docs/00_overview/PROJECT_STATUS.md`) |
| Release, combined | Realism gate for synthetic pulses; simulated hardware-format validation; protocol candidates | No generator passed the realism gate; two-stage alert and per-vehicle ACK keys supported |
| Redesign (V12) | Four protocol redesigns D1 to D4 | D1 simulator-dependent (not met in ns-3); D2 to D4 negative |
| Round 3 (V14) | Trace-driven replay, Tamarin and timed models, two-stage alert | 9 of 10 supported; one reboot lemma not proved |
| Paper items (V13) | Refit of H-C3, two-stage alert in ns-3 | H-C3 supported (frontal barrier only); two-stage alert partly (extra airtime 37% at SF7, 54% at SF9 against a 40% limit) |
| Round 4 (V15) | 24-byte provisional alert, receiver diversity, second prover | 0 of 5 supported; ProVerif finds an attack on car-reboot id reuse without a boot-time assumption and proves the boot-counter variant |
| Round 5 (V16) | Ten algorithms L1 to L10, plus L11 | 5 of 13 supported (L1, L3, L4 in ns-3 only, two formal items); L11 not supported |
| Round 6 (V17) | Micro-confirm frame, sequential early exit, prover extensions, ESP32 footprint | 5 of 7 supported; sequential rule not supported (the preregistration misquoted a baseline time; disclosed) |
| Round 7, 7b (V18, V19) | Duty-budget reserve against ACK suppression; pseudonymous vehicle ids | Pseudonym unlinkability proved; one-event reserve fails at a 1% allowance; four-event reserve supported on fresh seeds (a confirmation, since its size came from round-7 data) |
| Round 7c to 7e | Literature corrections, re-ACK deployment requirement (R-REACK), one-time scripts made to refuse to run, final archive | No new hypothesis; see `docs/04_audits/ROUND7C_REPORT.md`, `ROUND7D_REPORT.md`, `ROUND7E_REPORT.md` |

Details for every round: `docs/03_results/` (results) and `docs/04_audits/` (audits and reports).

## Quick start

```bash
make setup        # virtual environment and pinned requirements
make all          # data, features, training, C export, security, LoRa, studies, report, checks
make test         # pytest
```

Windows without `make`: `.\scripts\run_all.ps1`, and `$env:PYTHONPATH="src"; python -m pytest -q` for the tests. Exact commands, the hash-pinned `requirements.lock` and the reproduction check: `docs/05_data_code/REPRODUCE.md`.

VZCrash is gated on Hugging Face: accept the terms on the dataset page and run `huggingface-cli login` (or set `HF_TOKEN`) before `make data`. Never put a token in a file or a chat.

Main make targets: `data`, `features`, `train`, `export`, `cchecks`, `security`, `lora`, `severity`, `studies`, `journal`, `merge` (NOT_RUN without hardware CSVs), `report`, `docs`, `check`. The per-round targets (`positive`, `finish`, `release`, `combined`, `paper`) rebuild one round each.

Requirements: Python 3.12, CPU only. Seed 42 is the headline run; seeds 0 to 4 are the repeated runs. The ns-3, ProVerif, Tamarin and Espressif toolchain reruns need extra tools (WSL); they are described in the round reports and are not part of `make all`.

## How to read the results

Every value in `results/results.json` has one origin label:

| Label | Meaning |
|---|---|
| MEASURED_SOFTWARE | computed from a real dataset |
| SIMULATED / SIMULATED_HW_FORMAT | produced by a simulation with stated assumptions |
| TRACE_DRIVEN | replay of measured LoRaWAN traces |
| FORMAL | proved or checked by a model checker or prover, within stated bounds |
| ANALYTICAL | from a formula |
| HARDWARE | from the author's logs in `data/hardware/` |
| NOT_RUN | not run, with the reason |

Outputs: `results/results.json`, `results/tables/`, `results/figures/` (PNG and PDF), `report/software_results.md`.

Rules the project follows: no invented numbers; splits by recording group or trip, never by random window; thresholds chosen on validation only and the test set touched once per model; hardware files are never edited; synthetic data is watermarked and kept out of `results/`.

## Repository layout

```
README.md, CHANGELOG.md   purpose, status, history
docs/README.md            index of every document, one line each
docs/00_overview/         project status, claims, requirements, architecture, limits
docs/01_protocol/         alert packet, protocols, attack cases, threat model
docs/02_preregistration/  designs and hypotheses written before the runs
docs/05_data_code/        data statement, assumptions, reproduction
docs/07_log/              decisions and NOT_RUN items
src/crashguard/           package code
tests/                    pytest (tests/dummy holds synthetic files only)
c_bundle/, firmware_*/    C export of the models, firmware sources and bench kit
merge/                    hardware ingest for H1 to H6
scripts/                  run_all.ps1 and result-comparison helper
data/hardware/            the author's logs (read-only)
```

<!-- summary:start -->
## What this repo shows (generated from `results/results.json`)

A software-only study for a crash-alert system (ESP32 detector, severity, authenticated LoRa alert). Every number is computed by code in this repository, with its origin labelled; hardware results are the author's and are NOT_RUN here.

- **Detector.** On the de-duplicated VZCrash test set the deployable 15-tree forest has system recall 0.900 [0.892 to 0.909] (mean of 5 seeds; seed 42 alone: 0.909 [0.901 to 0.918]) and system false-alarm rate 0.042 [0.039 to 0.044] (5-seed mean). The 0.901 that the paper quotes is the recall on the test split as supplied, with the duplicates in it, and is neither a naive window-level split nor a vehicle-grouped result (`docs/03_results/DELTA_AUDIT_METHOD.md`). On a stricter test set without window-level near-duplicates the 5-seed system recall is 0.873. With the false-alarm rate fixed at 1% on validation, recall is 0.626 (mean over seeds). The dataset events were pre-selected on the device, so the trigger is a second stage.
- **Sensor requirement.** On 176 NHTSA crash tests, a +-16 g, 100 Hz accelerometer is within 10% of the reference delta-V on 0.07 [0.03 to 0.11] of tests; at least +-64 g and 200 Hz reach 80%. The release rule tuned on the tuning tests lowers the held-out error (paired difference -3.76 points, interval -10.25 to -1.36).
- **N14 saturation-aware estimator.** Held-out median error at +-16 g: 22.9% (plain) to 15.4% (fill) and 11.5% (fill plus ridge); the paired gain clears its interval at +-16 g only. Fill + ridge was named primary after earlier results were seen; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes. The C version equals Python on the real windows (one synthetic clipped window differs: a tie in the pulse-fit grid search).
- **N15 trigger-aware training.** No method raises system recall beyond the interval (seed-averaged difference at the 1% target: -0.0018 [-0.0077 to 0.0039] for joint selection). Reported as no improvement found.
- **N16 scheduler (simulation, supporting only).** Better than the fixed policy for critical alerts in 27 of 31 held-out cells, better than the severity table in 5 (spreading-factor raise on).
- **Security.** The attack suite behaves as designed (48 of 48 cases); our own testing found that strict replay rejection blocks the retry of an alert whose ACK was lost and the idempotent re-ACK repairs it. Documented limits: a shared key, no rotation, a lost counter store, a flood that can still spend airtime.
- **Round 3.** N20 with calibration de-duplicated by recording group: test false-alarm rate 0.0532 [0.0529 to 0.0535] against alpha 5%: the guarantee does not hold. UA-SCT (simulated, preregistered): taking the class from the upper end of a conformal class interval changes mis-triage by -0.048 [-0.079 to -0.021] at +-16 g and sends many more non-severe events to the fast path; in simulated bursts a fast path with a flash changes critical reach within 10 s by 0.247 against the severity table and 0.172 against a table with spaced retries; no gain in steady state. The alert-protocol model check (explicit-state, within bounds, TLC not run) found no violation for the design. At the same escalation, the severity table with lowered thresholds does as well on mis-triage as UA-SCT (-0.003 [-0.011 to 0.003] at +-16 g), so the conformal interval itself shows no benefit; the preregistered hypotheses H-a to H-c still hold against the plain table and survive a Holm correction. In ablations the flash and the hold carry the SCT gain. A second public dataset could not be opened (NOT_RUN). See `report/software_results.md` and `docs/03_results/CLAIM_EVIDENCE.md`.
- **Not shown:** anything measured on the car, ESP32 timing, delivery on real radios, impact direction, transfer to the scale model, injury. See `docs/00_overview/LIMITATIONS.md` and `docs/05_data_code/HARDWARE_READINESS.md`.
- **Where to look:** `report/software_results.md` (the draft), `report/novelty_summary.md` (evidence-only novelty ranking), `docs/05_data_code/FIGURES_TABLES.md`, `docs/02_preregistration/ALGORITHMS.md`, `docs/07_log/DECISIONS.md`, `docs/05_data_code/REPRODUCE.md`.
<!-- summary:end -->

## Data and licence

- Code: Apache-2.0 (`LICENSE`, `NOTICE`).
- VZCrash (https://huggingface.co/datasets/vzc-research-chapter/VZCrash, paper https://arxiv.org/abs/2606.06074) is CC BY-NC 4.0: non-commercial use, and it must be cited. Files derived from it keep that licence. Raw data is not in this repository (`data/raw/` is git-ignored).
- NHTSA Vehicle Crash Test Database (https://www.nhtsa.gov/research-data/research-testing-databases): public-agency data; the terms of use were not verified here.
- SisFall is not redistributed; see `scripts/fetch_sisfall.md`.
- The literature PDFs are not committed.
- Data statement: `docs/05_data_code/DATA_AND_CODE_STATEMENT.md`.

## Limitations

See `docs/00_overview/LIMITATIONS.md`. In short: no hardware result; protocol results come from simulators and a model of the reference code; the trigger and sensor range are placeholders; the dataset was pre-selected on the device and has no vehicle identifier; synthetic data is used for training and stress tests only; the paper has not been compiled here.

## How to cite

Use `CITATION.cff` (also `CITATION.md`), and cite the VZCrash paper and the NHTSA database for derived files.
