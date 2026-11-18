# CrashClip: a protocol for clipped-accelerometer crash severity

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | CrashClip package: sensor-model simulator, sealed split and baselines for clipped-accelerometer severity. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ASI = acceleration severity index; CNN = convolutional neural network; HTTP = Hypertext Transfer Protocol; NHTSA = National Highway Traffic Safety Administration; UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

CrashClip packages what the CrashGuard study needs to compare severity methods for accelerometers that clip: a sensor-model simulator, a sealed split of 913 pooled NHTSA crash-test records, the severity classes, a mode-stratified evaluation, baseline results, and an audit procedure for window datasets. It is a resource and a protocol, not a claim that any method is good. Software only; the sensor is a model; NHTSA tests are mostly high-speed.

## What is in this folder

| File | What it is |
|---|---|
| `records.csv` | One row per record: record id, NHTSA test number, source set, crash mode (frontal barrier, pole, side, other), make-and-model group hash, fold (dev, val, test), closing speed, reference delta-V (km/h) and reference class. Values are derived from public NHTSA records; no signals are included |
| `split.json` | Seed, fractions, class limits, fold sizes and SHA-256 digests of the sorted group keys of each fold |
| `parts.json` | The 8 parts of the sensor model (MPU-6050, ADXL345, ADXL375, H3LIS331DL, LIS3DH, KX134-1211, ADXL372, LSM6DSK320X high-g channel): ranges, resolution, output rates, bandwidth rule, noise density, the document that was opened, its address and date |
| `evaluate.py` | Mode-stratified scoring of a predictions file with grouped bootstrap intervals (numpy and pandas only) |
| `audit_windows.py` | De-duplication audit of a window dataset using hashes only |
| `baselines/*.csv` | Result tables of every method in the push (P1 to P4, B2) |
| `../scripts/requirement_calculator.py` | Smallest part and configuration that meets a stated rule for a crash-mode mix |

## Data and terms

- **NHTSA records.** The signals come from the NHTSA vehicle crash test database through its public NRD interface. The data.gov catalogue entry for the database (https://catalog.data.gov/dataset/vehicle-crash-test-database, opened 2026-11-12) gives "public" in its licence/rights field and states a use constraint: the database is not intended to support general consumer safety issues. That entry describes tests from 1981 to 2015; whether the same terms are stated for the later tests fetched here was not verified, and the nhtsa.gov policy pages returned HTTP 403 and were not opened. **No signals are redistributed**; rebuild them with `src/crashguard/nhtsa.py` and `t13_harvest.py` (the NRD interface must be reachable). `records.csv` lists test numbers so the same records can be fetched.
- **VZCrash** (CC BY-NC 4.0, non-commercial, cite the dataset) is not included; the audit procedure below produces hashes only.
- **The sealed fold is public once this folder is released.** It was scored once per hypothesis in the CrashGuard study (`docs/05_data_code/SEALED_SPLIT.md`); anyone using it afterwards should treat it as a development fold.

## Severity classes

Low, Moderate, Severe, Critical from the resultant delta-V with the limits 24, 40 and 56 km/h (`split.json`). The UA-SCT study also took the maximum with an ASI class; ASI is not available for all 913 records, so CrashClip classes use delta-V only. The reference delta-V is the maximum over the 300 ms after the trigger of the running integral of the unclipped, original-rate, baseline-removed longitudinal and lateral acceleration.

## Metrics (definitions fixed)

Macro-F1 over the classes present; balanced accuracy; **under-triage** = share of true Severe or Critical records predicted a lower class than their own; **over-triage** = share of true Low or Moderate records predicted a higher class; **mis-triage** = share of true Severe or Critical assigned below Severe; **escalation** = share of true Low or Moderate assigned Severe or above. Intervals: 1,000 resamples of whole make-and-model groups, seed 42. Always report per mode (frontal barrier, pole, side, other); the pooled mix is not a deployment mix.

## Protocol

1. Choose a sensor cell (part, range, output rate) from `parts.json`, or the generic chain (4th-order zero-phase low-pass at 260 Hz, saturation at the range, digital low-pass at min(0.4 x rate, 260 Hz), linear resampling).
2. Run each record through the chain (`src/crashguard/severity_study.sensor_signal`, `sel_study.chain` for a named part). Train and tune on `dev` and `val` only. A node does not know the crash mode: a model that uses the mode must also be reported with a mode inferred from the pulse (the oracle result is labelled).
3. Freeze the model and its settings in a commit, then score `test` once and report every metric above per mode with intervals. Report negative results.
4. Compare with the baselines in `baselines/` (plain delta-V, fill + ridge, anchored estimator, direct classifiers, interval and abstention methods).
5. For a window dataset with a public train, validation and test split, run `audit_windows.py` before reporting a test number (exact copies and near-identical windows across splits) and report both the supplied-test result and the result without the copies.

## Quick use

```
python crashclip/evaluate.py predictions.csv --fold test        # predictions.csv: rid,pred_class
python scripts/requirement_calculator.py --mix frontal_barrier=0.3,pole=0.4,side=0.1,other=0.2 --required 0.80
python crashclip/audit_windows.py windows.npy splits.txt --out audit
```

## Limits

Crash tests are mostly high-speed barrier, pole and side tests; the reference delta-V is a computed quantity, not an injury outcome (prior work cited in `docs/06_references/NOVELTY_SCAN.md` reports a weak link between delta-V and dummy injury criteria; its numbers could not be opened here); the sensor is a software model, not a measured part; the baselines are from one study with one sealed fold of 186 records.

<!-- PP:BEGIN -->
## Baseline results (generated; sealed fold, 100 Hz; full tables in `baselines/`)

| Range (g) | Role | Model | Macro-F1 | Under-triage | Over-triage | Balanced accuracy |
|---|---|---|---|---|---|---|
| +-16 | best of (a) to (c) on validation | anchored | 0.578 [0.426, 0.690] | 0.355 [0.209, 0.507] | 0.363 [0.276, 0.452] | 0.570 [0.432, 0.693] |
| +-16 | best deployable direct model on validation | 1D CNN, augmented (none mode) | 0.746 [0.636, 0.832] | 0.323 [0.203, 0.481] | 0.097 [0.038, 0.158] | 0.761 [0.645, 0.849] |
| +-16 | difference, direct minus base (sealed fold, paired) |  | 0.169 [0.046, 0.291] | -0.032 [-0.197, 0.125] |  |  |
| +-32 | best of (a) to (c) on validation | fill + ridge | 0.735 [0.638, 0.818] | 0.274 [0.135, 0.433] | 0.073 [0.019, 0.138] | 0.820 [0.752, 0.880] |
| +-32 | best deployable direct model on validation | 1D CNN, augmented (inferred mode) | 0.803 [0.705, 0.874] | 0.306 [0.175, 0.455] | 0.113 [0.065, 0.157] | 0.811 [0.741, 0.875] |
| +-32 | difference, direct minus base (sealed fold, paired) |  | 0.068 [0.005, 0.138] | 0.032 [-0.050, 0.117] |  |  |
| +-64 | best of (a) to (c) on validation | fill + ridge | 0.801 [0.711, 0.884] | 0.242 [0.111, 0.375] | 0.016 [0.000, 0.038] | 0.863 [0.799, 0.925] |
| +-64 | best deployable direct model on validation | 1D CNN, augmented (inferred mode) | 0.841 [0.758, 0.905] | 0.161 [0.069, 0.264] | 0.105 [0.056, 0.157] | 0.858 [0.767, 0.928] |
| +-64 | difference, direct minus base (sealed fold, paired) |  | 0.040 [-0.033, 0.108] | -0.081 [-0.167, 0.000] |  |  |

Requirement table (B2, plain estimate, all 913 records):

| Mode | Records | Configurations meeting the rule | Smallest configuration | Share within +-10% [95% lower, upper] |
|---|---|---|---|---|
| frontal barrier | 116 | 43 | kx134, +-32 g, 100 Hz | 0.888 [0.829, 0.944] |
| pole | 529 | 5 | kx134, +-64 g, 100 Hz | 0.841 [0.812, 0.869] |
| side | 58 | 0 | none of the 99 configurations |  |
| other | 210 | 0 | none of the 99 configurations |  |
<!-- PP:END -->
