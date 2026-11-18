# Reproduce every result

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Exact commands, environment and reproduction check for the main pipeline. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; ASI = acceleration severity index; CI = confidence interval; CPU = central processing unit; CSV = comma-separated values; CV = cross-validation; FPR = false-positive rate; LoRa = long-range radio modulation; NHTSA = National Highway Traffic Safety Administration; PPV = positive predictive value; SCT = severity-classified transmission; SW-420 = a vibration switch module; THIV = theoretical head impact velocity; UA-SCT = uncertainty-aware SCT; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Tested on Windows 11 (AMD64) with Python 3.12 (the exact version, platform and package versions of a run are written to `results/results.json` under `env.*`). Everything runs on the CPU; seed 42 is the headline run and seeds 0 to 4 the repeated runs.

## 1. One-time setup
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock     # exact versions with file hashes
# or, without hashes:  .\.venv\Scripts\python -m pip install -r requirements.txt
```
`requirements.txt` lists the top-level pins; `requirements.lock` lists every installed package with its sha256 hashes (built from the working environment on 2026-11-11).
`make` is not installed on this Windows machine; `scripts\run_all.ps1` is the same sequence as `make all`. On Linux or macOS use `make setup` and `make all`.

## 2. Data (read-only inputs; nothing is committed)
- VZCrash (CC BY-NC 4.0, cite the paper): `data/raw/data/*.parquet`, downloaded by `python -m crashguard.data` (the dataset is gated: log in to Hugging Face after accepting the terms; never paste a token into a chat or a file).
- NHTSA Vehicle Crash Test Database (public domain): `data/raw/nhtsa/`, downloaded by `python -m crashguard.nhtsa` from the public NHTSA API; if the network is unavailable the step records NOT_RUN and never substitutes other data.
- Hardware logs: `data/hardware/` (the author's files, read-only).

## 3. Rebuild everything from deleted outputs
```powershell
.\scripts\run_all.ps1 -Clean        # removes results, tables, figures, data/processed, build, generated reports; then runs every step in order
```
The last step, `python -m crashguard.check_results`, fails with a non-zero exit code if a result that the report cites is missing or NOT_RUN without a stated reason. To run without deleting: `.\scripts\run_all.ps1`.
Steps, in order: `env_record`, `data`, `features`, `split`, `models`, `export_c`, `attacks`, `forgery`, `lora`, `delivery_sim`, `severity_synth`, `nhtsa`, `severity_vzcrash`, `severity_study`, `saturation_study`, `export_severity`,
`detector_extra`, `robustness`, `replay_study`, `trigger_aware`, `scheduler_study`, `merge/ingest_hardware.py`, `report`, `novelty`, `vzcrash_email`, `check_results`. Then `python -m crashguard.docs_gen` writes `docs/05_data_code/FIRMWARE_SYNC.md`,
`docs/05_data_code/HARDWARE_READINESS.md` and the generated blocks of `README.md`, `docs/01_protocol/PACKET_FORMAT.md` and `docs/05_data_code/SEVERITY.md`.

## 4. Tests and style
```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python -m pytest -q          # all tests; test_report.py checks that every number in the report is in results.json
.\.venv\Scripts\ruff check src tests merge
```

## 5. Check that a rebuild reproduces the numbers
Run `run_all.ps1 -Clean` twice (two folders, or one after the other) and compare the two `results/results.json` files: `python scripts/compare_results.py A/results/results.json B/results/results.json` prints every entry that differs by more than 1e-6 (relative).
`env.*` entries are expected to be the same on one machine. Tolerance: two clean runs on this machine agreed on all but a handful of entries; the differences seen were the compiled C check being blocked by Windows in one run (NOT_RUN against a value) and last-digit differences (about 1e-5) in N15 learned-trigger false-alarm rates, traced to thread-dependent summation in the forest's `predict_proba`; scoring forests now use one thread. Treat differences below 1e-5 in a rate as the same result.

## 6. Known environment issue
Windows Application Control sometimes blocks a freshly built program ("An Application Control policy has blocked this file"). The C equivalence checks are built into `build/` and into a fixed folder in the system temp directory, each run is tried up to five times
with growing waits, and if the program still cannot run, the result is recorded as NOT_RUN with the reason and a pure-Python float32 mirror of the C code is the remaining check. Nothing from an older run is carried forward.

## 6b. C equivalence checks outside Windows (gcc, WSL, CI)
`python -m crashguard.c_bundle` writes `c_bundle/` (committed; synthetic inputs only: random feature vectors, vectors on and one float step either side of every split threshold, synthetic crash pulses and clipped pulses; expected values from the Python reference). `python -m crashguard.c_bundle --real` writes `build/c_bundle_real/` (git-ignored) with the real triggered test events and the VZCrash and NHTSA windows. `scripts/c_checks.sh [OUT.json]` compiles every check with gcc (`CC=clang` for another compiler) and runs it. It needs only bash, python3 and a C compiler.
- **Under WSL (Windows):** `wsl bash scripts/c_checks.sh build/c_checks_wsl.json` from the repository folder (WSL mounts the drive, for example `/mnt/d/...`; install a compiler with `wsl sudo apt install gcc` if missing). `run_all.ps1` does this automatically when WSL is installed.
- **On GitHub:** `.github/workflows/c_checks.yml` runs the script on `ubuntu-latest` for the committed synthetic bundle and uploads `c_checks.json` as the artifact `c_checks_json`.
- **Import:** `python -m crashguard.merge_c_checks build/c_checks_wsl.json --label wsl2_ubuntu_gcc` records the values as MEASURED_SOFTWARE under `cchecks.<label>.*` with the platform and compiler in the note. The Windows rows (`export.*`, `candidate.*`, `export_severity.*`) stay as they are, NOT_RUN with their reason when Windows blocked the program, unless the JSON is supplied. The 10 x 9 candidate forest is described as equivalent only where a compiled check has run (Windows `candidate.max_abs_diff` or a merged `c_bundle_real.forest_10x9`).

## 7. Where things are
`docs/02_preregistration/ALGORITHMS.md` (rules fixed before the N14 to N16 runs), `docs/07_log/DECISIONS.md` (every decision with date and reason), `docs/03_results/CLAIM_EVIDENCE.md` and `docs/06_references/PRIOR_WORK.md` (literature), `docs/06_references/MANUAL_SEARCH_CHECKLIST.md` (searches only the author can run),
`report/software_results.md` (the draft), `report/novelty_summary.md` (evidence-only novelty ranking), `docs/05_data_code/FIGURES_TABLES.md` (index of every figure and table).

<!-- repro_tables:start -->
## 8. One command per table and figure (generated by `python -m crashguard.repro_table`)

Run `.\scripts\run_all.ps1` once (it builds every input in order). After that, the command in the last column recomputes that table's numbers and `python -m crashguard.report` renders them again. Tables and figures from the closing block (T1 to T14) also have CSV and LaTeX versions in `results/paper/`, written by `python -m crashguard.paper_tables`; every row there names its `results.json` key.

| Item | Title | results.json keys | Command |
|---|---|---|---|
| Table 1 | Dataset profile (events per split and class) | `vzcrash.events.*, leakage.test_events_kept.*` | `python -m crashguard.data` |
| Table 2 | Model level, triggered events of the de-duplicated test set | `s2.trig_2.all.*` | `python -m crashguard.models` |
| Table 3 | System level, de-duplicated test set | `s2.trig_2.all.*sys_*` | `python -m crashguard.models` |
| Table 4 | Headline detector metrics with 95% bootstrap intervals (seed 42, de-duplicated test) | `detector.head.*` | `python -m crashguard.detector_extra` |
| Table 5 | Larger models minus the 15-tree forest | `gap.*` | `python -m crashguard.models` |
| Table 6 | Operating point chosen on validation for a fixed false-alarm rate, test recall scored ... | `detector.op.*` | `python -m crashguard.detector_extra` |
| Table 7 | Calibration of the probability models (seed 42, triggered de-duplicated test events) | `detector.cal.*` | `python -m crashguard.detector_extra` |
| Table 8 | Feature ablation | `s2.*, s3.*` | `python -m crashguard.models` |
| Figure 1 | Precision against recall on triggered, de-duplicated test events, seed 42. | `s2.trig_2.*` | `python -m crashguard.models` |
| Figure 2 | Reliability curves of the probability models. | `detector.cal.*` | `python -m crashguard.detector_extra` |
| Figure 3 | System recall when the false-alarm rate is fixed on validation. | `detector.op.*` | `python -m crashguard.detector_extra` |
| Table 9 | Precision (PPV) of the deployed forest, the 10-tree depth-9 candidate and the rule ... | `prev.*` | `python -m crashguard.prevalence` |
| Table 10 | Trigger rate per class | `trigger.*` | `python -m crashguard.features` |
| Table 11 | Trigger level sweep, 15-tree forest (seed 42, 95% intervals) | `detector.trig.*` | `python -m crashguard.detector_extra` |
| Table 12 | Crash events below each trigger, by VZCrash vehicle-size category (seed-independent ... | `detector.trigmiss.*` | `python -m crashguard.detector_extra` |
| Table 13 | Secondary comparison: window centred on the peak | `peak_window.*` | `python -m crashguard.models` |
| Table 14 | Three-class outcome, 15-tree forest, seed 42, de-duplicated test split | `confusion3.*` | `python -m crashguard.models` |
| Figure 4 | Trigger rate per class, and system recall and FPR, as the trigger level changes. | `trigger_sweep.*` | not mapped |
| Figure 5 | What happens to each true class: not triggered, triggered but predicted negative, or ... | `confusion3.*` | `python -m crashguard.models` |
| Table 15 | Sensor-error robustness: AP, system recall and false-alarm rate (seed 42; change in ... | `robust.*` | `python -m crashguard.robustness` |
| Figure 6 | Change in system recall and false-alarm rate under each perturbation, for three detectors. | `robust.*` | `python -m crashguard.robustness` |
| Table 16 | Model size against performance, depth 6 (AP: MEASURED_SOFTWARE, bytes: ANALYTICAL) | `s4.depth6.*` | `python -m crashguard.models` |
| Table 17 | Depth against size sweep, chosen on the validation split (AP and nodes ... | `s4b.*` | `python -m crashguard.detector_extra` |
| Table 18 | Leave one vehicle-size category out, 15-tree forest | `lovso.*, ap_by_size.*` | `python -m crashguard.models` |
| Table 19 | C export of the 15-tree forest and of the validation-selected candidate | `export.*, candidate.*` | `python -m crashguard.export_c` |
| Figure 7 | Validation AP against estimated flash for the depth sweep. | `s4b.*` | `python -m crashguard.detector_extra` |
| Figure 8 | AP against estimated model size for forests of different depth and tree count. | `s4.*` | `python -m crashguard.models` |
| Table 20 | Severity code on synthetic pulses with known answers (95% intervals on the shares) | `severity_synth.*` | `python -m crashguard.severity_synth` |
| Table 21 | NHTSA frontal rigid-barrier tests: the physical band v <= delta-V <= 2 v | `nhtsa.band_*, nhtsa.restitution_*` | `python -m crashguard.nhtsa` |
| Table 22 | Change in delta-V against the original recording, by sensor range at 100 Hz (95% ... | `nhtsa.dv_err_vs_orig_*` | `python -m crashguard.nhtsa` |
| Table 23 | Share of tests with delta-V within ±10% of the reference, by range and rate (95% ... | `sevstudy.grid.*` | `python -m crashguard.severity_study` |
| Table 24 | Median and 90th-percentile absolute delta-V error (%), by range and rate | `sevstudy.grid.*` | `python -m crashguard.severity_study` |
| Table 25 | Share of frontal tests inside v <= delta-V <= 2 v, by range and rate | `sevstudy.grid.*band_share` | `python -m crashguard.severity_study` |
| Table 26 | The same study for frontal and side tests separately: share within ±10% at `400 Hz` | `sevstudy.grid_frontal.*, sevstudy.grid_side.*` | `python -m crashguard.severity_study` |
| Table 27 | Front-end bandwidth sweep at 1600 Hz sampling: median absolute delta-V error (%) and ... | `sevstudy.bw.*` | `python -m crashguard.severity_study` |
| Table 28 | Named accelerometers through the same model (range, rate and resolution from the ... | `sevstudy.part*` | `python -m crashguard.severity_study` |
| Table 29 | Datasheet values of the four parts (read from the PDFs opened on `2026-11-11`) | `sevstudy.sheet.*` | `python -m crashguard.severity_study` |
| Table 30 | Release rule: tuning scores and the held-out result | `sevstudy.release.*` | `python -m crashguard.severity_study` |
| Table 31 | Rollover flag rate by VZCrash class, before and after the drift correction (95% intervals) | `severity_vzcrash.rollover.*` | `python -m crashguard.severity_vzcrash` |
| Table 32 | VZCrash triggered events: severity measures by class (95% intervals on the medians and ... | `severity_vzcrash.dist.*, severity_vzcrash.ci.*` | `python -m crashguard.severity_vzcrash` |
| Table 33 | Delta-V and ASI used alone as a crash score, de-duplicated test set | `severity_vzcrash.score.*` | `python -m crashguard.severity_vzcrash` |
| Table 34 | Class mix when each class limit is moved by ±20% (NHTSA tests with the reference delta-V ... | `sevstudy.thr.*, severity_vzcrash.thr.*` | `python -m crashguard.severity_study` |
| Table 35 | C version of the severity code against Python; pure-Python float32 mirror of the C code ... | `export_severity.*` | `python -m crashguard.export_severity` |
| Figure 9 | Median delta-V error, share within ±10%, and physical-band share for each range and ... | `sevstudy.grid.*` | `python -m crashguard.severity_study` |
| Figure 10 | Median absolute delta-V error against front-end bandwidth for four ranges. | `sevstudy.bw.*` | `python -m crashguard.severity_study` |
| Figure 11 | NHTSA frontal tests: delta-V against impact speed with the v and 2 v lines, the change ... | `nhtsa.*` | `python -m crashguard.nhtsa` |
| Figure 12 | Severity code on synthetic pulses: delta-V error against pulse duration. | `severity_synth.*` | `python -m crashguard.severity_synth` |
| Figure 13 | VZCrash triggered events: distributions of delta-V, ASI and THIV (UNVERIFIED, not used in ... | `severity_vzcrash.*` | `python -m crashguard.severity_vzcrash` |
| Table 36 | Attack suite (software simulation of the reference verifier) | `attacks.*` | `python -m crashguard.attacks` |
| Table 37 | Replay flood against the re-ACK, with and without the limit | `attacks.flood.*` | `python -m crashguard.attacks` |
| Table 38 | Forgery and counter analysis | `forgery.*, counter.*` | `python -m crashguard.forgery` |
| Table 39 | Severity mix of the alerts the replay sends | `replay.pool.*` | `python -m crashguard.replay_study` |
| Table 40 | Replay with the stress mix at 30% loss: delivery, latency and budget, by spreading ... | `replay.grid.stress.*` | `python -m crashguard.replay_study` |
| Table 41 | Replay with the real VZCrash mix at 30% loss (all alerts are Low): delivery by policy | `replay.grid.vzcrash.*` | `python -m crashguard.replay_study` |
| Table 42 | Base station already near its duty-cycle budget (2 s left), 60 alerts per hour, 30% loss ... | `replay.sens.stress.basenear_*` | `python -m crashguard.replay_study` |
| Table 43 | Replay flood inside the replay pipeline: alerts that arrive during the flood | `replay.flood.*` | `python -m crashguard.replay_study` |
| Table 44 | Which conclusions survive when the assumptions change (cells where the interval condition ... | `replay.conclusion.*` | `python -m crashguard.replay_study` |
| Table 45 | Stages from the trigger to the ACK for a lossless exchange at SF7 | `replay.timeline.*, replay.assume.*` | `python -m crashguard.replay_study` |
| Figure 14 | Delivery against loss, independent and burst, three policies and three spreading factors. | `replay.grid.stress.*` | `python -m crashguard.replay_study` |
| Figure 15 | Trigger-to-ACK time per severity class. | `results/tables/replay_grid.csv` | `python -m crashguard.replay_study` |
| Figure 16 | Cumulative node airtime during one simulated hour for the three policies. | `results/tables/replay_grid.csv` | `python -m crashguard.replay_study` |
| Figure 17 | Pipeline stage timeline by severity class. | `replay.timeline.*` | `python -m crashguard.replay_study` |
| Table 46 | N14 on the held-out NHTSA tests: baseline (B), fill (M) and fill plus ridge correction ... | `n14.r*.heldout.*` | `python -m crashguard.saturation_study` |
| Table 47 | N14 paired comparison with the baseline on the same held-out tests (method minus ... | `n14.r*.heldout.paired.*` | `python -m crashguard.saturation_study` |
| Table 48 | N14 on synthetic saturated pulses with analytic delta-V: median absolute error (%) | `n14.synthetic.*` | `python -m crashguard.saturation_study` |
| Figure 18 | N14: estimated against reference delta-V on the held-out tests for the three methods and ... | `n14.*` | `python -m crashguard.saturation_study` |
| Table 49 | N14 extension: delta-V error of plain integration, spline restoration, fill and fill + ... | `n14x.*` | `python -m crashguard.saturation_splits` |
| Table 50 | N14 extension: paired differences (method minus reference) in median absolute delta-V ... | `n14x.*.paired.*` | `python -m crashguard.saturation_splits` |
| Table 51 | N14 extension: the ten tests with the largest delta-V error after fill + ridge at ±16 g ... | `n14x.failure16.R_cv.*` | `python -m crashguard.saturation_splits` |
| Table 52 | N14 extension: the ten largest errors after fill + ridge at ±16 g on the held-out tests ... | `n14x.failure16.G_heldout.*` | `python -m crashguard.saturation_splits` |
| Table 53 | N15: system recall at a fixed false-alarm rate on the de-duplicated test set (mean ± std ... | `n15.*` | `python -m crashguard.trigger_aware` |
| Table 54 | N15: share of test crashes that pass each method's trigger, by vehicle-size category ... | `n15.*.crash_trigger_rate_*` | `python -m crashguard.trigger_aware` |
| Table 55 | N16: held-out scenarios where the scheduler's paired difference meets each condition ... | `n16.conclusion.*` | `python -m crashguard.scheduler_study` |
| Table 56 | N16 held-out scenario SF12, 30% independent loss, 20 alerts per hour: by true severity ... | `n16.heldout.loss_iid30_sf12.*` | `python -m crashguard.scheduler_study` |
| Table 57 | N16 paired differences (scheduler minus baseline) in three held-out scenarios: critical ... | `n16.paired.*` | `python -m crashguard.scheduler_study` |
| Table 58 | N16 effect sizes by true severity class, pooled over all held-out cells (scheduler minus ... | `n16.effect.*` | `python -m crashguard.scheduler_study` |
| Table 59 | N16 with severity estimated by the car: truly critical alerts acknowledged when priority ... | `n16.estimator.*` | `python -m crashguard.scheduler_study` |
| Figure 19 | N16: critical-alert delivery against loss for the three policies in the held-out ... | `n16.heldout.*` | `python -m crashguard.scheduler_study` |
| Figure 20 | N16: truly critical alerts acknowledged for three sources of the severity class. | `n16.estimator.*` | `python -m crashguard.scheduler_study` |
| Table 60 | LoRa airtime and duty-cycle budget | `lora.*` | `python -m crashguard.lora` |
| Table 61 | Earlier delivery simulation: strict verifier before the fix against the idempotent re-ACK ... | `s9.*` | `python -m crashguard.delivery_sim` |
| Table 62 | Hardware logs ingested and what is still NOT_RUN | `hw.*` | `python merge/ingest_hardware.py (NOT_RUN: the author's hardware logs are not read in this software-only run)` |
| Figure 21 | Measured Wi-Fi protocol latency next to the analytical LoRa time on air. | `hw.protocol.*, lora.*` | `python merge/ingest_hardware.py (NOT_RUN: the author's hardware logs are not read in this software-only run)` |
| Figure 22 | Share of alerts whose ACK reached the car with the strict verifier and with the ... | `s9.*` | `python -m crashguard.delivery_sim` |
| Figure 23 | Time on air against payload size for SF7 to SF12. | `lora.*` | `python -m crashguard.lora` |
| Table 63 | X1: front against side (sign-free) on the held-out vehicle groups, by sensor range | `x1.*` | `python -m crashguard.direction` |
| Table 64 | X2: Spearman correlation of severity measures with dummy criteria at the driver or ... | `x2.*` | `python -m crashguard.injury` |
| Table 65 | X2: share of tests above a regulatory limit, by severity class of the reference chain | `x2.limit.*` | `python -m crashguard.injury` |
| Table 66 | X3: system recall at a fixed false-alarm rate for fixed windows and for the early-exit ... | `x3.*` | `python -m crashguard.early` |
| Table 67 | X3: early-exit rule minus the fixed 1,800 ms window (seed 42, paired bootstrap over test ... | `x3.a*.paired.*` | `python -m crashguard.early` |
| Table 68 | X4: test false-alarm rate of the conformal and the validation thresholds, by ... | `x4.*` | `python -m crashguard.conformal` |
| Table 69 | X4: breaking exchangeability on purpose: calibrate on three vehicle-size categories and ... | `x4.shift.*` | `python -m crashguard.conformal` |
| Table 70 | X5: attack success against the deployed forest, by budget and attack, net of what the ... | `x5.net.*` | `python -m crashguard.spoofing` |
| Table 71 | X5: defences: attack success with any attack (95% intervals over windows), the paired ... | `x5.asr.*, x5.diff.*, x5.clean.*` | `python -m crashguard.spoofing` |
| Table 72 | X6: airtime and the base station's ACK budget by spreading factor (ANALYTICAL) | `x6.analytic.*` | `python -m crashguard.capacity` |
| Table 73 | X6: probability that an alert is not destroyed by another packet (pure ALOHA, and with ... | `x6.analytic.*` | `python -m crashguard.capacity` |
| Table 74 | X6: simulated critical-alert delivery and heartbeat delivery against the number of cars ... | `x6.sim.*` | `python -m crashguard.capacity` |
| Table 75 | X6: a burst of 30 critical alerts within 10 s (SF7, heartbeat every 600 s): critical ... | `x6.sim.*burst*` | `python -m crashguard.capacity` |
| Table 76 | X7: system recall, false-alarm rate and system AP over the amplitude (a) and time-scale ... | `x7.filtered.*` | `python -m crashguard.physical_scaling` |
| Table 77 | X7: median relative change of each feature when only the amplitude (x2) or only the time ... | `x7.invariance.*` | `python -m crashguard.physical_scaling` |
| Table 78 | X7: the Nyquist problem: share of triggered crash windows whose time above 2 g is shorter ... | `x7.filtered.a1.*` | `python -m crashguard.physical_scaling` |
| Table 79 | N20: test false-alarm rate against alpha with the full calibration pool, by recording ... | `n20c.*` | `python -m crashguard.s3_conformal` |
| Table 80 | N8: system recall of the deployed forest on the supplied, the de-duplicated and the ... | `s2.*` | `python -m crashguard.models` |
| Table 81 | N14: median absolute delta-V error (%) by reference delta-V bin, split R, +-16 g | `n14s.strata.dv.*` | `python -m crashguard.s4_n14` |
| Table 82 | N16: critical delivery, scheduler minus severity table, over the burst sweep (40 paired ... | `s5.heldout.*` | `python -m crashguard.s5_burst` |
| Table 83 | N19: recall at a fixed false-alarm rate and mean decision time of crash events for the ... | `s6.*` | `python -m crashguard.s6_early` |
| Table 84 | N24: grouped CV+ intervals around the fill + ridge delta-V at +-16 g: coverage, width and ... | `s9.*` | `python -m crashguard.delivery_sim` |
| Table 85 | N25: system recall, precision and false alarms per 100,000 events by prevalence and ... | `s10.rf15.*` | `python -m crashguard.s10_adaptive` |
| Table 86 | UA-SCT B1: plain delta-V estimate: median absolute error, share within 10% and class ... | `ua.b1.*` | `python -m crashguard.ua_conformal` |
| Table 87 | UA-SCT: interval coverage against target and mean width in classes, per sensor range ... | `ua.r*` | `python -m crashguard.ua_conformal` |
| Table 88 | UA-SCT: policy comparison at +-16 g, steady state (default cell; mean over seeds) | `s11.cell.r16.steady.base.*` | `python -m crashguard.s11_sct` |
| Table 89 | UA-SCT: policy comparison at +-16 g, burst of 30 critical alerts (default cell; mean over ... | `s11.cell.r16.burst.base.*` | `python -m crashguard.s11_sct` |
| Table 90 | UA-SCT: policy comparison at +-32 g, steady state (default cell; mean over seeds) | `s11.cell.r32.steady.base.*` | `python -m crashguard.s11_sct` |
| Table 91 | UA-SCT: policy comparison at +-32 g, burst of 30 critical alerts (default cell; mean over ... | `s11.cell.r32.burst.base.*` | `python -m crashguard.s11_sct` |
| Table 92 | UA-SCT: policy comparison at +-64 g, steady state (default cell; mean over seeds) | `s11.cell.r64.steady.base.*` | `python -m crashguard.s11_sct` |
| Table 93 | UA-SCT: policy comparison at +-64 g, burst of 30 critical alerts (default cell; mean over ... | `s11.cell.r64.burst.base.*` | `python -m crashguard.s11_sct` |
| Table 94 | UA-SCT: paired differences over all held-out cells by range (mean over cells; 95% ... | `s11.diff.*` | `python -m crashguard.s11_sct` |
| Table 95 | N26: critical reach, SCT (P2) minus the severity table with spaced retries (P1b), and the ... | `s13.*` | `python -m crashguard.s13_spaced_table` |
| Table 96 | N27: properties checked (holds = no counterexample within the bounds) | `s12.*` | `python -m crashguard.protocol_check` |
| Table 97 | Results that did not clear their interval or that went against the idea | `n20c.*, s9.*, s10.*, s11.*, s4.*` | `python -m crashguard.s3_conformal` |
| Table 98 | T1: P3 against the severity table with thresholds lowered to the same escalation ... | `t1.*` | `python -m crashguard.t1_equal_escalation` |
| Table 99 | T2: area under the mis-triage against escalation curve (lower is better), by family and ... | `t2.*` | `python -m crashguard.t2_pareto` |
| Table 100 | T3: break-even ratio C_u / C_o above which P3 costs less than P1 (grouped bootstrap), by ... | `t3.*` | `python -m crashguard.t3_cost` |
| Table 101 | T4: under-estimation and mis-triage under three rules, 90% level, by range (grouped ... | `t4.a.*` | `python -m crashguard.t4_clarify` |
| Table 102 | T4: single car, critical reach within 10 s, by loss (SIMULATED) and the analytical ... | `t4.b.*` | `python -m crashguard.t4_clarify` |
| Table 103 | T5: standard test set against the set without window-level near-duplicates (5-seed means ... | `t5.*` | `python -m crashguard.t5_strict` |
| Table 104 | T6: H-a and H-c under shifted delta-V class limits (all limits together, and each limit ... | `t6.*` | `python -m crashguard.t6_thresholds` |
| Table 105 | T7: class intervals at the `90%` level: the current pooled split-conformal intervals ... | `t7.a.*` | `python -m crashguard.t7_conformal_variants` |
| Table 106 | T7: the N20 false-alarm guarantee with conformal variants (clean calibration pool; test ... | `t7.b.*` | `python -m crashguard.t7_conformal_variants` |
| Table 107 | T8: cells in which P3 beats, ties or loses against P1 and P2 | `t8.count.*` | `python -m crashguard.t8_sweep` |
| Table 108 | T9: change in critical reach within 10 s when one SCT part is changed (P2, variant minus ... | `t9.diff.*` | `python -m crashguard.t9_ablations` |
| Table 109 | T9: transmissions of the CANCEL message and critical reach within 10 s with and without ... | `t9.steady_fa5.*` | `python -m crashguard.t9_ablations` |
| Table 110 | T10: time on air (s) by message and spreading factor (Semtech formula, `125` kHz, coding ... | `t10.airtime.*` | `python -m crashguard.t10_airtime` |
| Table 111 | T10: transmit airtime and estimated energy per crash event, simulated counts at SF7 ... | `t10.sim.*` | `python -m crashguard.t10_airtime` |
| Table 112 | T12: flash and CANCEL properties of the bounded model (holds = no counterexample within ... | `s12x.*` | `python -m crashguard.protocol_check_ext` |
| Table 113 | T14: the preregistered hypotheses with Holm correction (grouped-bootstrap p-values, 1,000 ... | `t14.*` | `python -m crashguard.stats_audit` |
| Figure 24 | Events per class in each supplied split. | `vzcrash.events.*` | `python -m crashguard.data` |
| Figure 25 | AP and F1 with all features, without the gyro feature, and with scale-free features only. | `s3.*` | `python -m crashguard.models` |
| Figure 26 | AP when a vehicle-size category is held out of training. | `lovso.*` | `python -m crashguard.models` |
| Figure 27 | Attack suite outcomes. | `attacks.*` | `python -m crashguard.attacks` |
| Figure 28 | Reliability curves from the original model comparison (seed 42). | `s5.*` | `python -m crashguard.s5_burst` |

Key prefixes without a mapped module: trigger_sweep.

## 9. One command per v2 table (branch `v2-algorithms`; plan: `docs/02_preregistration/PREREGISTRATION_V2.md`, results: `docs/03_results/V2_RESULTS.md`)

Run `scripts/run_all.ps1` once (the v2 steps follow the T block), or run the commands below in this order after the earlier steps: A, D, B, B5, E, F, verdicts, documents, tables. Each table has a CSV and a LaTeX version in `results/paper/`; every row names its `results.json` key.

| Table | Study | Command that computes it | Command that writes the table |
|---|---|---|---|
| `results/paper/v2_tab_estimators.csv`, `.tex` | A: clipping estimators | `python -m crashguard.v2_a_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_bounds.csv`, `.tex` | A2: bounds | `python -m crashguard.v2_a_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_intervals.csv`, `.tex` | A5: conformal intervals by clipped-fraction bin | `python -m crashguard.v2_a_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_abstention.csv`, `.tex` | A6: abstention flag | `python -m crashguard.v2_a_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_onset_flag.csv`, `.tex` | D: clip-onset flag | `python -m crashguard.v2_d_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_adaptive.csv`, `.tex` | B: adaptive variants against matched baselines | `python -m crashguard.v2_b_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_sensitivity.csv`, `.tex` | B5: sensitivity | `python -m crashguard.v2_b_sens` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_tag_length.csv`, `.tex` | E: tag length | `python -m crashguard.v2_e_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_hold_cost_grid.csv`, `.tex` | F1: hold cost grid | `python -m crashguard.v2_f_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_hold_sim.csv`, `.tex` | F2: hold simulation | `python -m crashguard.v2_f_study` | `python -m crashguard.v2_paper_tables` |
| `results/paper/v2_tab_verdicts.csv`, `.tex` | all: verdicts and Holm correction | `python -m crashguard.v2_verdicts` | `python -m crashguard.v2_paper_tables` |

Study C was not run (see `docs/03_results/V2_RESULTS.md`). The verdicts and the Holm correction: `python -m crashguard.v2_verdicts`; the results document: `python -m crashguard.v2_docs`; the claim rows: `python -m crashguard.claim_table`.
<!-- repro_tables:end -->

<!-- command-check:start -->
## 9. Command check after the 2026-11-13 reorganisation

`python scripts/check_reproduce.py` checks that every module, script and make target named in the guides, the Makefile and `scripts/run_all.ps1` exists. Result on 2026-11-13: 145 distinct commands, 0 unresolved. It does not run the commands; a full rebuild takes hours.
<!-- command-check:end -->

## 10. Release blocks (P, Q, A)

`make release` runs, in order, the generator fits and gates, the surrogate gate, the design and held-out protocol grids, the bounded model check, the Q1 real-only evaluation, the Holm verdicts, and the generated documents. The exploratory physics arm (`python -m crashguard.q_f1 PH-A all ungated`, then `python -m crashguard.q_eval pha_ungated`) takes more than an hour per run and is not part of `make release`. The run time of the whole target was not measured as one run.

## Combined run (2026-11-14)

`make combined` (or `make PY=.venv/Scripts/python combined` on Windows) rebuilds the combined run: re-verification (`crashguard.sh_v`), the 19 simulated variants and the SW-420 sensitivity sets (`crashguard.hwsim_v2`, files under `data/simulated_hardware/variants/`, not committed; hashes in `docs/03_results/SIMHW_VARIANTS.md`), Part S (`sh_s2` to `sh_s5`), Part R (`ar_r4`, `ar_r1`, `ar_r2`, `ar_r3`), the Holm verdicts (`ar_verdicts`), the documents (`sh_docs`, `ar_arch`, `r_docs`, `ar_docs`), headers and the claim audit (`scripts/combined_audit.py`). About 10 minutes on a 14-core machine. Run `python -m crashguard.ar_docs` after `make report`, which regenerates NOVELTY.md and drops its combined-run block. Checks: `python -m crashguard.check_results`, `python -m pytest -q`, `python -m ruff check src tests merge crashclip scripts`. Release archive: `python scripts/build_combined.py`.
