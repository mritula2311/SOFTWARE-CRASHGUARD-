# CrashGuard: software pipeline

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

CrashGuard is a low-cost system that detects a vehicle crash on an ESP32 microcontroller with one inertial sensor and five vibration sensors, works out how severe the crash is and which side was hit, and sends an authenticated alert to a base station over LoRa. This repository holds the **software and data-science side**: the detection models, the severity estimate, the alert packet and its security checks, the LoRa delivery simulation, the studies that test each proposed method against a preregistered criterion, and the scripts that merge the author's hardware measurements.

Author: Mritula S, B.Tech Cybersecurity and IoT, SRIHER. Academic, non-commercial project. Software only: the car and radio experiments are the author's and are not part of these results.

##status

| Area | Status |
|---|---|
| Detector (VZCrash) | Done and measured in software; trigger and sensor range are placeholders until confirmed from firmware v2 |
| Severity (delta-V, class) and sensor-range study | Done and measured in software on NHTSA crash tests; not run on the car |
| Alert packet and attack suite | Done in software (simulated cases, property tests, bounded model check); built in firmware, not yet aligned byte for byte |
| LoRa delivery and protocol layers | Simulated under stated assumptions; airtime and duty budget are analytical; not measured on radios |
| Proposed methods (rounds 3, v2, journal push, positive push, finishing round) | Each judged by a preregistered criterion; most are not supported. Verdict table: `docs/00_overview/PROJECT_STATUS.md` |
| Release blocks (physics-based synthetic pulses, reruns, protocol-layer algorithms) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V7.md` before the runs. No generator passed the realism gate; the confirmatory reruns are real-only and unchanged; the two protocol candidates are not supported on the held-out grid. Details: `docs/03_results/RELEASE_RESULTS.md` |
| Combined run (re-verification, literature, simulated hardware-format validation, four architecture and protocol candidates) | Done in software on simulated hardware-format logs (SIMULATED_HW_FORMAT; no real hardware measurement), preregistered in `docs/02_preregistration/PREREGISTRATION_V11.md` before the runs. Family S: 2 of 6 supported (latency decomposition, security suite on the simulated scenarios); family R: 5 of 7 supported (two-stage alert and per-vehicle ACK keys in the main paper; freshness field and frame length in the supplement). Details: `docs/03_results/COMBINED_VERDICTS.md`, `docs/03_results/SIMHW_RESULTS.md`, `docs/05_architecture/ARCHITECTURE.md`. |
| Redesign round (diagnosis of the failed protocol algorithms, D1 loss-adaptive deadline policy, D2 gateway-signed cluster ACK, D3 slotted retries, D4 short provisional frame, code verification, ns-3 cross-check, C firmware path in a host build, bench kit, reviewer pack) | Done in software and preregistered in `docs/02_preregistration/PREREGISTRATION_V12.md` (addenda A and B) before any development run; each redesign tested once on a fresh held-out grid drawn after its freeze. D1: supported in the custom simulator (+0.16 over the severity table, which is a weak baseline; +0.036 over quick retries; not reliably better than the best of seven baselines per cell once a Nessa-style baseline is added), **simulator-dependent**: not met in ns-3 (+0.02), so not in the main paper. D2: no-harm and security model met, the 5-point burst gain not met (negative). D3: not met (+0.0006 against +0.05; negative). D4: not met (a 24-byte provisional frame costs more airtime than R3's 14-byte flash; negative). Firmware decision path: 0 mismatches against the Python reference in 10,000 random histories; ESP32 size, emulator and hardware NOT_RUN. Results: `docs/03_results/REDESIGN_A_RESULTS.md`, `REDESIGN_B_RESULTS.md`, `REDESIGN_DECISION_TABLE.md`, `XSIM_VERDICTS.md`; reviewer questions: `docs/09_review/REVIEWER_RESPONSES.md` |
| Round 3 (journal literature check from 2021; replay of the retry policies on measured LoRaWAN traces; Tamarin models and an exhaustive timed check of the alert protocol; two-stage alert on real crash data; energy budget) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V14.md` before the runs. Labels TRACE_DRIVEN and FORMAL; no hardware data. Seven preregistered tests supported; one reboot lemma not proved; D1 gain on traces explained by retry timing (zero-spacing control). Decision table: `docs/03_results/ROUND3_DECISION_TABLE.md`; novelty matrix: `docs/06_references/NOVELTY_MATRIX_2021PLUS.md` |
<!-- pp:start -->
| Part C: combined journal paper (`paper/main.tex`, supplement, figures, cover letter) | Written and audited in software, not compiled here (no TeX distribution; upload `paper/` to Overleaf). Preregistered in `docs/02_preregistration/PREREGISTRATION_V13.md` before the runs. H-C3 refit on the development fold: SUPPORTED (frontal barrier only). Two-stage alert in ns-3: PARTLY (6 of 8 tests supported; extra airtime 37% at SF7 and 54% at SF9 against a 40% limit). Audit reports: `docs/04_audits/PP_PAPER_CLAIM_AUDIT.md`, `docs/04_audits/PP_REFERENCE_CHECK.md`. No hardware data. |
<!-- pp:end -->
| Round 4 (algorithm round: 24-byte repeated provisional alert A1, receiver diversity A2, second prover A3; branch `algo4`) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V15.md` before the runs. A1 and A2 are killed by their preregistered rules (0 of 5 tests supported; A2 is EXPLORATORY, same dataset as development); the formal rerun proves the provisional frame authentic and its ACK vehicle-bound; ProVerif finds an attack on the frozen design for car-reboot id reuse without a boot-time assumption and proves the boot-counter variant. See `docs/03_results/A4_DECISION_TABLE.md`, `A4_RESULTS.md`, `A4_A3_PROVERIF.md` |
| Round 5 (ten algorithms L1 to L10 and L11 added after the initial session; branch `round5`) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V16.md` (addenda A1, A2, S2, S2.1, S2.2) before each run; 5 of the 13 hypotheses of the Holm family are supported (L1, L3, L4 in ns-3 only, and two FORMAL items with stated limits); L11 (own family) is not supported; L2, L5, L6, L8b, L10a are negative results. Results: `docs/03_results/ROUND5_RESULTS.md`, `ROUND5_DECISION_TABLE.md`; code verification: `docs/03_results/R5_CODE_VERIFICATION.md`; audit: `docs/04_audits/R5_CLAIM_AUDIT.md`. |
| Final verification run (branch `verify`, from tag `round5-v1`; no new experiment) | Recomputation from a fresh clone, formal and ns-3 reruns, hypothesis ledger (at that run 123 preregistered hypotheses in 12 preregistration versions: 40 supported, 66 not supported, 4 partly, 13 not run; round 6 added 7, so the total is now 130 in 13 versions: 45 supported, 68 not supported, 4 partly, 13 not run), literature integration, rewritten manuscript (8 figures, 5 tables, 12 pages estimated), reference check against Crossref, submission package. Logs: `docs/04_audits/FINAL_VERIFICATION.md`, `docs/04_audits/FINAL_REPORT.md`, `docs/04_audits/HYPOTHESIS_LEDGER.md`, `docs/04_audits/RECOMPUTE.md`. Paper not compiled with the Access class here (see `docs/04_audits/LATEX_LINT.md`). |
| Round 6 (micro-confirm, sequential early exit, prover extensions, ESP32 build footprint, bounds, reframing; branch `round6`) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V17.md` before any development run; 5 of 7 hypotheses supported (micro-confirm airtime and delivery in the 16 ns-3 cells only: the trace groups are zero by construction and are not evidence for delivery; H-R6-1a was nearly automatic because the micro-confirm replaces the 97-byte confirm, so the airtime over the two-stage alert, 0.46 to 0.77, is the number to quote; micro-confirm lemmas in ProVerif and Tamarin; the ratchet within 3 steps in ProVerif; the quarantine finding is the spoofed-id attack on count-before-verification and the two-counter fix, variant B holds by construction); the sequential early-exit rule is not supported (the preregistration quoted the fixed rule's mean decision time as 720 to 780 ms, it is 112 ms, so 200 ms was out of reach; the error is disclosed). The micro-confirm frame has 13 bytes in ns-3 (design: 8 with a pending index, finalize run); at SF7 it costs the airtime of the 14-byte flash. ESP32 footprint is a build artifact (Espressif GCC); emulator counts and energy are NOT_RUN. No hardware data. Results: `docs/03_results/ROUND6_RESULTS.md`; ledger now 130 hypotheses in 13 versions. Manuscript reframed (constrained-node profile). |
| Delta verification run (branch `verify2`, from tag `round6-v1`; no new experiment) | Round-6 numbers recomputed from a fresh clone (260 rows, 180 ns-3 runs, the footprint build and the formal models rerun: all equal), normative frame layout (`docs/05_architecture/FRAME_LAYOUT.md`) that closes blocker B5, table of 16 abstractions between layout, formal models and ns-3, duty lockout condition and gating rule (ANALYTICAL; the stored results use an hourly allowance only), preemption analysis and enumeration, audit procedure with four test-set versions (descriptive), supplement trimmed to about 35 pages with the rest in `supplementary_full/` of the release archive. Log: `docs/04_audits/DELTA_VERIFICATION.md`; report: `docs/04_audits/DELTA_FINAL_REPORT.md`. |
| Round 7 (duty-budget reserve against ACK suppression, pseudonymous vehicle ids with an unlinkability proof; branch `round7`) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V18.md` before any run (literature gate `docs/01_literature/R7_PRIOR_ART.md`; no stop rule triggered). 2 of the 5 hypotheses of the Holm family are supported (H-R7-B1 resolution cost, H-R7-B3 diff-equivalence in ProVerif with the fixed-id control failing); not supported: H-R7-A1 (the one-event reserve keeps the follow-up on time in 70%, 27% and 35% of runs at SF7, SF8, SF9 under a 1% allowance; a reserve for four events restores 100% in a post-run exploration), H-R7-A2 (delivery falls 2.4 points in the high-loss trace group under a 10% per-transmission off-time) and H-R7-B2 (pseudonym collision probability 0.216 at 2 bytes and 3.7e-6 at 4 bytes against 1e-6). H-R7-A3 is descriptive (the enabling spreading factor stays SF7). Results in `docs/03_results/ROUND7_RESULTS.md`, `ROUND7_A.md`, `ROUND7_B.md`; log in `docs/04_audits/ROUND7.md`. Nothing measured on hardware. |
| Round 7b (re-test of the four-event reserve, prior art, quarantine lemma status; branch `round7b`) | Done in software, preregistered in `docs/02_preregistration/PREREGISTRATION_V19.md` before any run: H-R7b-1 supported (four-event reserve, fresh seeds), H-R7b-2 not supported (benign delivery cost under a 10% off-time); the reserve size was chosen from round-7 data, so a confirmation and not a blind test; report `docs/04_audits/ROUND7B_REPORT.md`; nothing measured on hardware; paper not compiled |
| Round 7c (literature corrections and last code checks; branch `round7c`, from tag `submit-v5.1`) | Done: no new experiment or hypothesis. Corrections to the introduction (Carneiro et al. report delivery ratio and latency), the formal-verification wording (LoRaWAN key establishment and authentication were analysed before), the availability related work (Chen et al., Liu et al., Kumar), one absence rule, SisFall not redistributed (`scripts/fetch_sisfall.md`), the ACK-after-verification and atomic seen-set requirements; report `docs/04_audits/ROUND7C_REPORT.md`; the literature-check file named in the brief was not in the session |
| Car experiments H1 to H6 | Not started (hardware) |

"Built in firmware" means compile-checked only. "Built, not yet measured" means the code exists and no measurement has been made.

## Quick start

```bash
make setup
make all          # downloads data, trains, exports, simulates, writes the report, checks results
make test
```

VZCrash is gated on Hugging Face: accept the terms on the dataset page and run `huggingface-cli login` (or set `HF_TOKEN`) before `make data`. Never paste a token into a chat or a file. Without `make` (Windows): `.\scripts
un_all.ps1`, and `PYTHONPATH=src python -m pytest -q` for the tests. Exact commands, the lock file and the reproduction check: `docs/05_data_code/REPRODUCE.md`.

Outputs: `results/results.json` (every number with its origin label: MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, HARDWARE, NOT_RUN), `results/tables/`, `results/figures/`, `report/software_results.md`, `report/novelty_summary.md`.

## Repository layout

```
README.md, CHANGELOG.md   purpose, status, history
docs/README.md            index of every document, one line each
docs/00_overview/         project status, claims, requirements, architecture, limits
docs/01_protocol/         alert packet, protocols, attack cases, threat model
docs/02_preregistration/  designs and hypotheses written before the runs
docs/03_results/          result summaries, negatives register, claim evidence
docs/04_audits/           data, claim and preregistration audits
docs/05_data_code/        data statement, assumptions, provenance, reproduction
docs/06_references/       references, literature status, novelty scope
docs/07_log/              decisions, NOT_RUN items, cleanup log, path map
docs/archive/             superseded documents (each with a SUPERSEDED header)
src/crashguard/           package code
tests/                    pytest; tests/dummy holds synthetic files only
merge/                    hardware ingest and merged analysis (H1 to H6)
crashclip/                clipped-accelerometer severity protocol package
firmware_export/          generated C model and severity code
results/                  generated tables, figures, results.json (tagged results are not edited)
data/raw, data/processed  downloads and caches (git-ignored); data/hardware: the author's logs
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
- VZCrash (https://huggingface.co/datasets/vzc-research-chapter/VZCrash, paper https://arxiv.org/abs/2606.06074) is released under CC BY-NC 4.0: non-commercial use, and it must be cited. Files derived from it keep that licence. Raw data is never committed.
- NHTSA Vehicle Crash Test Database (https://www.nhtsa.gov/research-data/research-testing-databases): public-agency data; the terms of use were not verified here.
- The 24 literature PDFs in `RESEARCH PAPERS/` are git-ignored; text extracts are not committed.
- Data statement: `docs/05_data_code/DATA_AND_CODE_STATEMENT.md`.

## Limitations

See `docs/00_overview/LIMITATIONS.md` and the limits section of `docs/00_overview/PROJECT_STATUS.md`. In short: no hardware result; protocol results come from a simulator; the trigger and sensor range are placeholders; the dataset was pre-selected on the device and has no vehicle identifier; synthetic data is used for training and stress tests only.

## How to cite

Use `CITATION.cff` (also `CITATION.md`), and cite the VZCrash paper and the NHTSA database for derived files.
