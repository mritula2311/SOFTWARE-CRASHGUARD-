# Positive-results push: results (generated)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Results of the positive-results push (generated). |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL |
| Abbreviations | AP = average precision; CNN = convolutional neural network; CV = cross-validation; ESP32 = a Wi-Fi microcontroller family (Espressif); GBM = gradient boosting machine; NHTSA = National Highway Traffic Safety Administration; RAM = random-access memory; UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

Branch `positive-push` (from tag `journal-push-v3`), 2026-11-12. Software only; `data/hardware` was not read. Every number below is read from `results/results.json` (keys `p.*`) by `src/crashguard/pp_docs.py`. Labels: MEASURED_SOFTWARE unless stated; the UA-SCT cells of P3b are SIMULATED; flash and RAM estimates are ANALYTICAL. The design (preregistration, sealed fold, freeze commits) is in `docs/02_preregistration/PREREGISTRATION_V4.md` and `docs/05_data_code/SEALED_SPLIT.md`. NHTSA records are crash tests, mostly high-speed; the sensor is a software model; VZCrash events were selected on the device before release. Nothing here is a field or hardware result.

## Verdicts (Holm over seven preregistered hypotheses)

| Hypothesis | Raw p | Holm p | Criterion met | Verdict |
|---|---|---|---|---|
| H-P1 | 0.836 | 1.000 | 0 | NOT SUPPORTED |
| H-P2 | 1.000 | 1.000 | 0 | NOT SUPPORTED |
| H-P3a | 0.130 | 0.780 | 0 | NOT SUPPORTED |
| H-P3b | 0.906 | 1.000 | 0 | NOT SUPPORTED |
| H-P4a | 0.001 | 0.007 | 1 | SUPPORTED |
| H-P4b | 1.000 | 1.000 | 0 | NOT SUPPORTED |
| H-P4c | 1.000 | 1.000 | 0 | NOT SUPPORTED |

Of the seven hypotheses, 1 is SUPPORTED and 6 are NOT SUPPORTED. Anything outside the seven (P4d, the cross-validation of P1, the matched-escalation comparison of P3b, the exploratory interval variants) is EXPLORATORY and says so in its key and caption.

## One line per task

- **Z0** pooled set of 913 records (174 + 739) in 325 make-and-model groups; modes: frontal barrier 116, pole 529, side 58, other 210; development 543, validation 184, sealed 186 records (`docs/05_data_code/SEALED_SPLIT.md`).
- **Z1** mode inferred from the pulse: sealed-fold balanced accuracy 0.754 at +-16 g, 0.800 at +-32 g, 0.867 at +-64 g (100 Hz); every mode-using model is reported with the true mode (oracle, labelled) and the inferred mode.
- **P1 / H-P1: NOT SUPPORTED.** Criterion (macro-F1 +0.03 and under-triage -0.03, both intervals excluding zero, in at least two of three ranges) met in 0 ranges. At +-16 g the best deployable direct model (fe_none) against the best baseline (c): macro-F1 0.169 [0.046, 0.291], under-triage -0.032 [-0.197, 0.125].
- **P1 exploratory cross-validation (all 913 records, not a test):** the augmented CNN against the anchored estimator at +-16 g: macro-F1 0.086 [0.039, 0.130], under-triage -0.029 [-0.076, 0.018]; at +-32 g macro-F1 0.045 [0.003, 0.087]; at +-64 g macro-F1 -0.016 [-0.054, 0.021]. The direct GBM is not better than the anchored estimator (+-16 g macro-F1 -0.017 [-0.060, 0.018], under-triage 0.075 [0.041, 0.112]).
- **P2 / H-P2: NOT SUPPORTED.** Sealed coverage of the interval [plain, plain x q] at +-16 g: 0.914 [0.871, 0.957]; lower end overall 0.871 and for pole 0.868 (coverage condition met); mean upper-to-lower ratio 1.93 against 1.96 for the existing interval, a reduction of 0.018 (needed 0.20).
- **P3a / H-P3a: NOT SUPPORTED.** At +-16 g the anchored estimator's under-triage among retained events is 0.74 of the unselected rate (upper end 0.91; needed at most 0.5); retained p90 error 18.8% (needed at most 20%, met).
- **P3b / H-P3b: NOT SUPPORTED.** Abstaining to the fast path minus the lowered severity table: mis-triage 0.032 [-0.030, 0.114] at +-16 g (needed at most -0.02, interval below zero); N28 stays NO_IMPROVEMENT_FOUND.
- **P4a / H-P4a: SUPPORTED.** Selected on validation: trees 8, depth 8, k 14, q16; flash estimate 20.6 kB against 55.1 kB (ratio 0.374); AP loss 0.0023 [0.0013, 0.0036]; measured host size 21725 against 56004 bytes (x86-64, not an ESP32).
- **P4b / H-P4b: NOT SUPPORTED.** Augmentation with merging changes recall at the 1% target on the strict set by -0.0175 [-0.0219, -0.0132] (needed +0.02): it is lower.
- **P4c / H-P4c: NOT SUPPORTED.** In leave-one-vehicle-size-category-out evaluation every variant, including the trivial rule, has a false-alarm rate with upper end below target + 0.01 (pooled conformal: 0.0535 at the 5% target, upper 0.0567); no variant gains recall over the trivial rule, and the variants that bring the rate to the target or below lose recall (V4 -0.019, V5 -0.115 at the 5% target).
- **P4d (EXPLORATORY).** An int8 tiny 1D CNN (1633 weights, 1756 bytes of weights and biases) reached AP 0.9614 [0.9571, 0.9658] on the de-duplicated test set and 0.9403 [0.9332, 0.9470] on the strict set, against 0.9383 and 0.9010 for the 10-tree depth-9 forest (about 55 kB). No hypothesis and no multiplicity correction.
- **B1** CrashClip package: `crashclip/` (records, parts, split, evaluation, de-duplication audit, baselines). **B2** requirement calculator: `scripts/requirement_calculator.py`. **B3** `docs/05_data_code/REPRODUCE_FINISH.md`.

## Negative results

- **H-P1 (NOT SUPPORTED):** the direct route does not lower under-triage in a way the intervals can tell from zero in any range (at +-64 g the upper end of the difference is exactly 0.0, at +-32 g the point difference is positive); macro-F1 gains have intervals above zero at +-16 g and at +-32 g, but the preregistered conjunction fails in all three ranges.
- **H-P2 (NOT SUPPORTED):** the one-sided interval is not narrower than the relative-residual interval around fill + ridge (reduction near 2%, needed 20%); at +-32 and +-64 g the lower bound fails in more records, so coverage falls under 0.90.
- **H-P3a (NOT SUPPORTED):** abstaining on 30% of events lowers under-triage among the retained events only to about three quarters of the unselected rate.
- **H-P3b (NOT SUPPORTED):** an abstain signal sends fewer non-severe events to the fast path than the lowered table and does not mis-triage less, with or without matching escalation on the sealed fold.
- **H-P4b (NOT SUPPORTED):** augmentation with merging lowers recall at the 1% target on the strict set.
- **H-P4c (NOT SUPPORTED):** no group-wise calibration restores more recall than the trivial rule; the guarantee at target + 0.01 held for all variants including the trivial one, and exact control at the target costs recall.

## Tables

### P1 (sealed fold, 100 Hz and 200 Hz)

| Rate (Hz) | Range (g) | Role | Model | Macro-F1 | Under-triage | Over-triage | Balanced accuracy |
|---|---|---|---|---|---|---|---|
| 100 | +-16 | best of (a) to (c) on validation | anchored | 0.578 [0.426, 0.690] | 0.355 [0.209, 0.507] | 0.363 [0.276, 0.452] | 0.570 [0.432, 0.693] |
| 100 | +-16 | best deployable direct model on validation | 1D CNN, augmented (none mode) | 0.746 [0.636, 0.832] | 0.323 [0.203, 0.481] | 0.097 [0.038, 0.158] | 0.761 [0.645, 0.849] |
| 100 | +-16 | difference, direct minus base (sealed fold, paired) |  | 0.169 [0.046, 0.291] | -0.032 [-0.197, 0.125] |  |  |
| 100 | +-32 | best of (a) to (c) on validation | fill + ridge | 0.735 [0.638, 0.818] | 0.274 [0.135, 0.433] | 0.073 [0.019, 0.138] | 0.820 [0.752, 0.880] |
| 100 | +-32 | best deployable direct model on validation | 1D CNN, augmented (inferred mode) | 0.803 [0.705, 0.874] | 0.306 [0.175, 0.455] | 0.113 [0.065, 0.157] | 0.811 [0.741, 0.875] |
| 100 | +-32 | difference, direct minus base (sealed fold, paired) |  | 0.068 [0.005, 0.138] | 0.032 [-0.050, 0.117] |  |  |
| 100 | +-64 | best of (a) to (c) on validation | fill + ridge | 0.801 [0.711, 0.884] | 0.242 [0.111, 0.375] | 0.016 [0.000, 0.038] | 0.863 [0.799, 0.925] |
| 100 | +-64 | best deployable direct model on validation | 1D CNN, augmented (inferred mode) | 0.841 [0.758, 0.905] | 0.161 [0.069, 0.264] | 0.105 [0.056, 0.157] | 0.858 [0.767, 0.928] |
| 100 | +-64 | difference, direct minus base (sealed fold, paired) |  | 0.040 [-0.033, 0.108] | -0.081 [-0.167, 0.000] |  |  |
| 200 | +-16 | best of (a) to (c) on validation | anchored | 0.635 [0.467, 0.746] | 0.290 [0.143, 0.455] | 0.242 [0.160, 0.327] | 0.606 [0.475, 0.733] |
| 200 | +-16 | best deployable direct model on validation | 1D CNN, augmented (none mode) | 0.669 [0.505, 0.777] | 0.290 [0.164, 0.449] | 0.177 [0.097, 0.247] | 0.645 [0.506, 0.774] |
| 200 | +-16 | difference, direct minus base (sealed fold, paired) |  | 0.035 [-0.053, 0.164] | 0.000 [-0.138, 0.152] |  |  |
| 200 | +-32 | best of (a) to (c) on validation | fill + ridge | 0.711 [0.603, 0.809] | 0.194 [0.083, 0.328] | 0.161 [0.092, 0.233] | 0.795 [0.667, 0.882] |
| 200 | +-32 | best deployable direct model on validation | 1D CNN, augmented (inferred mode) | 0.760 [0.575, 0.859] | 0.290 [0.163, 0.433] | 0.129 [0.073, 0.180] | 0.718 [0.563, 0.847] |
| 200 | +-32 | difference, direct minus base (sealed fold, paired) |  | 0.049 [-0.087, 0.134] | 0.097 [0.020, 0.180] |  |  |
| 200 | +-64 | best of (a) to (c) on validation | anchored | 0.848 [0.768, 0.907] | 0.097 [0.019, 0.189] | 0.177 [0.112, 0.241] | 0.872 [0.776, 0.938] |
| 200 | +-64 | best deployable direct model on validation | direct GBM, augmented (inferred mode) | 0.822 [0.698, 0.921] | 0.129 [0.043, 0.235] | 0.129 [0.077, 0.182] | 0.833 [0.707, 0.932] |
| 200 | +-64 | difference, direct minus base (sealed fold, paired) |  | -0.025 [-0.089, 0.026] | 0.032 [0.000, 0.085] |  |  |

### P2

| Range (g) | Interval | Coverage [95%] | Mean upper/lower ratio [95%] | Frontal barrier inside v..2v |
|---|---|---|---|---|
| +-16 | [plain, plain x q], global q | 0.914 [0.871, 0.957] | 1.93 [1.93, 1.93] | 0.00 |
| +-16 | q by clipped-duration bin | 0.919 [0.865, 0.969] | 2.10 [2.04, 2.18] | 0.05 |
| +-16 | q by inferred mode | 0.930 [0.885, 0.975] | 2.19 [2.00, 2.43] | 0.05 |
| +-16 | global q, group-weighted (exploratory) | 0.919 [0.874, 0.962] | 1.97 [1.97, 1.97] | 0.00 |
| +-16 | relative residual around fill + ridge (split form) | 0.914 [0.877, 0.952] | 1.96 [1.96, 1.96] | 0.00 |
| +-16 | grouped CV+ around fill + ridge (exploratory) | 0.957 [0.929, 0.983] | 2.39 [2.39, 2.39] | 0.00 |
| +-32 | [plain, plain x q], global q | 0.871 [0.826, 0.920] | 1.94 [1.94, 1.94] | 0.00 |
| +-32 | q by clipped-duration bin | 0.866 [0.819, 0.913] | 2.73 [2.58, 2.87] | 0.75 |
| +-32 | q by inferred mode | 0.866 [0.823, 0.913] | 1.38 [1.37, 1.39] | 0.80 |
| +-32 | global q, group-weighted (exploratory) | 0.871 [0.826, 0.920] | 3.18 [3.18, 3.18] | 0.00 |
| +-32 | relative residual around fill + ridge (split form) | 0.946 [0.916, 0.975] | 1.80 [1.80, 1.80] | 0.00 |
| +-32 | grouped CV+ around fill + ridge (exploratory) | 0.946 [0.916, 0.975] | 1.79 [1.79, 1.79] | 0.00 |
| +-64 | [plain, plain x q], global q | 0.833 [0.775, 0.887] | 1.69 [1.69, 1.69] | 1.00 |
| +-64 | q by clipped-duration bin | 0.833 [0.775, 0.887] | 1.69 [1.69, 1.69] | 1.00 |
| +-64 | q by inferred mode | 0.828 [0.773, 0.876] | 1.40 [1.39, 1.42] | 0.00 |
| +-64 | global q, group-weighted (exploratory) | 0.833 [0.775, 0.887] | 4.32 [4.32, 4.32] | 0.00 |
| +-64 | relative residual around fill + ridge (split form) | 0.930 [0.889, 0.967] | 1.45 [1.45, 1.45] | 0.00 |
| +-64 | grouped CV+ around fill + ridge (exploratory) | 0.930 [0.889, 0.967] | 1.46 [1.46, 1.46] | 0.00 |

### P3a

| Range (g) | Estimator | Retained by | p90 error retained (%) | p90 error all (%) | Under-triage retained | Under-triage all | Ratio retained / all |
|---|---|---|---|---|---|---|---|
| +-16 | plain | validation threshold | 32.4 [25.6, 35.9] | 37.4 [34.6, 40.5] | 0.83 [0.73, 0.92] | 0.85 [0.77, 0.93] | 0.97 [0.93, 0.99] |
| +-16 | plain | rank (exactly 70%) | 32.3 [23.8, 35.3] | 37.4 [34.6, 40.5] | 0.82 [0.70, 0.91] | 0.85 [0.77, 0.93] | 0.95 [0.90, 0.99] |
| +-16 | fill + ridge | validation threshold | 24.0 [20.8, 29.0] | 33.6 [26.0, 37.6] | 0.36 [0.16, 0.56] | 0.42 [0.24, 0.61] | 0.85 [0.61, 0.97] |
| +-16 | fill + ridge | rank (exactly 70%) | 23.7 [19.5, 29.2] | 33.6 [26.0, 37.6] | 0.37 [0.17, 0.58] | 0.42 [0.24, 0.61] | 0.88 [0.65, 1.03] |
| +-16 | anchored | validation threshold | 18.8 [15.2, 20.7] | 25.7 [20.1, 29.7] | 0.26 [0.12, 0.42] | 0.35 [0.21, 0.51] | 0.74 [0.49, 0.91] |
| +-16 | anchored | rank (exactly 70%) | 18.4 [13.9, 20.9] | 25.7 [20.1, 29.7] | 0.22 [0.09, 0.37] | 0.35 [0.21, 0.51] | 0.63 [0.35, 0.83] |
| +-16 | best direct model | validation threshold | n/a (class output) | n/a | 0.32 [0.17, 0.50] | 0.32 [0.20, 0.48] | 0.99 [0.77, 1.18] |
| +-16 | best direct model | rank (exactly 70%) | n/a (class output) | n/a | 0.31 [0.15, 0.48] | 0.32 [0.20, 0.48] | 0.95 [0.68, 1.14] |
| +-32 | plain | validation threshold | 10.2 [7.9, 12.4] | 17.4 [12.6, 20.3] | 0.37 [0.23, 0.52] | 0.40 [0.26, 0.55] | 0.91 [0.80, 1.01] |
| +-32 | plain | rank (exactly 70%) | 10.1 [8.0, 12.0] | 17.4 [12.6, 20.3] | 0.37 [0.24, 0.52] | 0.40 [0.26, 0.55] | 0.92 [0.83, 1.00] |
| +-32 | fill + ridge | validation threshold | 8.8 [7.5, 10.4] | 14.5 [10.5, 20.2] | 0.26 [0.13, 0.42] | 0.27 [0.14, 0.43] | 0.96 [0.82, 1.09] |
| +-32 | fill + ridge | rank (exactly 70%) | 8.9 [7.5, 10.5] | 14.5 [10.5, 20.2] | 0.25 [0.13, 0.40] | 0.27 [0.14, 0.43] | 0.93 [0.80, 1.03] |
| +-32 | anchored | validation threshold | 9.2 [8.2, 9.5] | 13.8 [11.0, 19.7] | 0.14 [0.03, 0.27] | 0.18 [0.05, 0.31] | 0.79 [0.37, 1.04] |
| +-32 | anchored | rank (exactly 70%) | 9.2 [8.1, 9.5] | 13.8 [11.0, 19.7] | 0.14 [0.03, 0.26] | 0.18 [0.05, 0.31] | 0.76 [0.36, 1.00] |
| +-32 | best direct model | validation threshold | n/a (class output) | n/a | 0.30 [0.17, 0.45] | 0.31 [0.18, 0.45] | 0.97 [0.85, 1.09] |
| +-32 | best direct model | rank (exactly 70%) | n/a (class output) | n/a | 0.29 [0.16, 0.43] | 0.31 [0.18, 0.45] | 0.94 [0.82, 1.03] |

### P3b (pool level)

| Range (g) | System | Mis-triage [95%] | Escalation of non-severe [95%] |
|---|---|---|---|
| +-16 | abstain to the fast path | 0.081 [0.014, 0.170] | 0.653 [0.566, 0.757] |
| +-16 | severity table, lowered thresholds | 0.048 [0.000, 0.122] | 0.734 [0.661, 0.812] |
| +-16 | severity table, current thresholds | 0.145 [0.057, 0.245] | 0.331 [0.246, 0.427] |
| +-16 | difference A minus lowered table | 0.032 [-0.030, 0.114] | -0.081 [-0.216, 0.066] |
| +-32 | abstain to the fast path | 0.065 [0.000, 0.143] | 0.629 [0.520, 0.722] |
| +-32 | severity table, lowered thresholds | 0.000 [0.000, 0.000] | 0.694 [0.613, 0.776] |
| +-32 | severity table, current thresholds | 0.113 [0.018, 0.224] | 0.218 [0.140, 0.301] |
| +-32 | difference A minus lowered table | 0.065 [0.000, 0.143] | -0.065 [-0.214, 0.081] |

### P4a

| Model | Configuration | Flash estimate (bytes, analytical) | Measured host size (bytes, x86-64 -Os) | RAM estimate (bytes) | Validation AP | Test AP (de-duplicated) | Test AP (strict) | Recall at 1% target | Recall at 5% target |
|---|---|---|---|---|---|---|---|---|---|
| reference | trees 10, depth 9, k 14, float | 55120 | 56004 | 76 | 0.9343 | 0.9383 | 0.9010 | 0.658 | 0.938 |
| selected | trees 8, depth 8, k 14, q16 | 20644 | 21725 | 76 | 0.9299 | 0.9359 | 0.8982 | 0.647 | 0.936 |
| AP loss, reference minus selected |  |  |  |  |  | 0.0023 [0.0013, 0.0036] | 0.0029 [0.0011, 0.0048] |  |  |

### P4b

| Set | Variant | Recall at 1% [95%] | AP [95%] | Difference to standard, recall at 1% [95%] |
|---|---|---|---|---|
| strict | standard | 0.5584 [0.5408, 0.5740] | 0.8922 [0.8799, 0.9033] |  |
| strict | merge | 0.5622 [0.5441, 0.5782] | 0.8920 [0.8800, 0.9035] | 0.0038 [-0.0002, 0.0076] |
| strict | aug | 0.5419 [0.5236, 0.5576] | 0.8871 [0.8751, 0.8990] | -0.0165 [-0.0215, -0.0118] |
| strict | aug_merge | 0.5409 [0.5221, 0.5566] | 0.8870 [0.8750, 0.8987] | -0.0175 [-0.0219, -0.0132] |
| dedup | standard | 0.6265 [0.6118, 0.6392] | 0.9315 [0.9242, 0.9382] |  |
| dedup | merge | 0.6296 [0.6152, 0.6421] | 0.9309 [0.9235, 0.9379] | 0.0030 [-0.0003, 0.0063] |
| dedup | aug | 0.6136 [0.5986, 0.6263] | 0.9283 [0.9208, 0.9355] | -0.0129 [-0.0171, -0.0088] |
| dedup | aug_merge | 0.6118 [0.5968, 0.6246] | 0.9281 [0.9205, 0.9354] | -0.0147 [-0.0186, -0.0112] |

### P4c

| Evaluation | Target | Variant | False-alarm rate | Upper end (95%) | Recall | Recall minus V0 | gain_lo | gain_hi |
|---|---|---|---|---|---|---|---|---|
| loco | 0.01 | V0 | 0.0113 | 0.0127 | 0.6231 | 0.0 | 0.0 | 0.0 |
| loco | 0.01 | V1 | 0.0112 | 0.0126 | 0.6224 | -0.0008 | -0.0011 | -0.0004 |
| loco | 0.01 | V2 | 0.0112 | 0.0126 | 0.6224 | -0.0008 | -0.0011 | -0.0004 |
| loco | 0.01 | V3 | 0.0101 | 0.0115 | 0.5694 | -0.0537 | -0.0591 | -0.048 |
| loco | 0.01 | V4 | 0.0101 | 0.0115 | 0.598 | -0.0252 | -0.0282 | -0.0224 |
| loco | 0.01 | V5 | 0.0078 | 0.009 | 0.5066 | -0.1165 | -0.1245 | -0.1085 |
| loco | 0.05 | V0 | 0.0536 | 0.0568 | 0.9313 | 0.0 | 0.0 | 0.0 |
| loco | 0.05 | V1 | 0.0535 | 0.0567 | 0.9312 | -0.0001 | -0.0002 | 0.0 |
| loco | 0.05 | V2 | 0.0535 | 0.0567 | 0.9312 | -0.0001 | -0.0002 | 0.0 |
| loco | 0.05 | V3 | 0.0529 | 0.0561 | 0.9271 | -0.0042 | -0.0061 | -0.0024 |
| loco | 0.05 | V4 | 0.0478 | 0.0508 | 0.9122 | -0.019 | -0.0223 | -0.0159 |
| loco | 0.05 | V5 | 0.033 | 0.0355 | 0.8166 | -0.1147 | -0.1239 | -0.1059 |
| supplied | 0.01 | V0 | 0.0105 | 0.0119 | 0.6265 | 0.0 | 0.0 | 0.0 |
| supplied | 0.01 | V1 | 0.0104 | 0.0118 | 0.6247 | -0.0018 | -0.0024 | -0.0012 |
| supplied | 0.01 | V2 | 0.0106 | 0.0119 | 0.6388 | 0.0123 | 0.0053 | 0.0194 |
| supplied | 0.01 | V4 | 0.009 | 0.0103 | 0.594 | -0.0326 | -0.0358 | -0.0296 |
| supplied | 0.01 | V5 | 0.0045 | 0.0054 | 0.4626 | -0.1639 | -0.1736 | -0.1543 |
| supplied | 0.05 | V0 | 0.0533 | 0.0564 | 0.9345 | 0.0 | 0.0 | 0.0 |
| supplied | 0.05 | V1 | 0.0532 | 0.0564 | 0.9344 | -0.0 | -0.0001 | 0.0 |
| supplied | 0.05 | V2 | 0.0517 | 0.0547 | 0.91 | -0.0245 | -0.0304 | -0.0186 |
| supplied | 0.05 | V4 | 0.0462 | 0.0491 | 0.9162 | -0.0183 | -0.0214 | -0.0154 |
| supplied | 0.05 | V5 | 0.022 | 0.024 | 0.7795 | -0.1549 | -0.165 | -0.1446 |

### P4d (EXPLORATORY)

| Set | Model | AP [95%] | Recall at 1% [95%] | Recall at 5% [95%] |
|---|---|---|---|---|
| dedup | 1D CNN, float weights | 0.9614 [0.9571, 0.9658] | 0.769 [0.757, 0.780] | 0.950 [0.943, 0.956] |
| dedup | 1D CNN, int8 weights | 0.9614 [0.9571, 0.9658] | 0.769 [0.757, 0.779] | 0.950 [0.943, 0.956] |
| strict | 1D CNN, float weights | 0.9404 [0.9332, 0.9471] | 0.719 [0.705, 0.734] | 0.935 [0.926, 0.944] |
| strict | 1D CNN, int8 weights | 0.9403 [0.9332, 0.9470] | 0.719 [0.705, 0.733] | 0.935 [0.926, 0.943] |
| both | parameters / flash estimate (int8) | 1633 / 1756 bytes |  |  |

### P1 cross-validation (EXPLORATORY)

| Range (g) | Model | Macro-F1 [95%] | Under-triage [95%] | CNN minus model, macro-F1 [95%] | CNN minus model, under-triage [95%] |
|---|---|---|---|---|---|
| +-16 | fill + ridge | 0.581 [0.534, 0.624] | 0.332 [0.272, 0.391] | 0.147 [0.109, 0.184] | -0.059 [-0.111, -0.006] |
| +-16 | anchored | 0.643 [0.592, 0.688] | 0.302 [0.254, 0.353] | 0.086 [0.039, 0.130] | -0.029 [-0.076, 0.018] |
| +-16 | direct GBM | 0.653 [0.600, 0.697] | 0.364 [0.314, 0.416] | 0.076 [0.033, 0.119] | -0.091 [-0.125, -0.053] |
| +-16 | 1D CNN, augmented | 0.729 [0.680, 0.768] | 0.273 [0.230, 0.324] |  |  |
| +-32 | fill + ridge | 0.729 [0.691, 0.769] | 0.286 [0.236, 0.337] | 0.054 [0.013, 0.091] | -0.070 [-0.107, -0.032] |
| +-32 | anchored | 0.738 [0.689, 0.782] | 0.195 [0.151, 0.242] | 0.045 [0.003, 0.087] | 0.021 [-0.016, 0.058] |
| +-32 | direct GBM | 0.744 [0.696, 0.791] | 0.265 [0.214, 0.313] | 0.039 [0.004, 0.077] | -0.048 [-0.081, -0.015] |
| +-32 | 1D CNN, augmented | 0.783 [0.741, 0.821] | 0.217 [0.172, 0.260] |  |  |
| +-64 | fill + ridge | 0.782 [0.744, 0.821] | 0.270 [0.220, 0.321] | 0.030 [-0.016, 0.076] | -0.099 [-0.141, -0.059] |
| +-64 | anchored | 0.828 [0.792, 0.863] | 0.144 [0.106, 0.184] | -0.016 [-0.054, 0.021] | 0.027 [-0.007, 0.063] |
| +-64 | direct GBM | 0.828 [0.787, 0.864] | 0.190 [0.147, 0.232] | -0.016 [-0.054, 0.018] | -0.019 [-0.051, 0.019] |
| +-64 | 1D CNN, augmented | 0.812 [0.768, 0.854] | 0.171 [0.125, 0.217] |  |  |

### B2 requirement table

| Mode | Records | Configurations meeting the rule | Smallest configuration | Share within +-10% [95% lower, upper] |
|---|---|---|---|---|
| frontal barrier | 116 | 43 | kx134, +-32 g, 100 Hz | 0.888 [0.829, 0.944] |
| pole | 529 | 5 | kx134, +-64 g, 100 Hz | 0.841 [0.812, 0.869] |
| side | 58 | 0 | none of the 99 configurations |  |
| other | 210 | 0 | none of the 99 configurations |  |

## Sealed-fold and test-split scorings

| hypothesis | scored_at | freeze_commit | deviation |
|---|---|---|---|
| P4a | 2026-11-12 08:34 | 1a3aff90747d2cb9df4b468fa5faabdaab0737fd |  |
| P4b | 2026-11-12 08:39 | 7a42da37747f66b178b5494c927de1b53172a11f |  |
| P4b | 2026-11-12 08:39 | 7a42da37747f66b178b5494c927de1b53172a11f | initial run crashed before any test event was scored (AttributeError in mask construction); repeated after the fix |
| P4c | 2026-11-12 08:41 | ab6239f47e17f165fa634a0a8677d823cb6f9b76 |  |
| P1 | 2026-11-12 08:41 | 1d2251103c6f727c82783f84ccd4d1583ccd68fe |  |
| P2 | 2026-11-12 08:42 | 505ac57f68d97878f3d22f95d8dbc687ebb34c41 |  |
| P3a | 2026-11-12 08:43 | 23015883aa0b56728d828d758271bd46f3f6517b |  |
| P3b | 2026-11-12 08:43 | 015e2b5a1af942640434ce08207c82f1b8136bb1 |  |
| P4c | 2026-11-12 08:53 | ab6239f47e17f165fa634a0a8677d823cb6f9b76 | repeat after fixing a closure bug in the recall-gain statistic; models, settings and alarms unchanged |
| P3b | 2026-11-12 08:55 | 015e2b5a1af942640434ce08207c82f1b8136bb1 | repeat after a failed write of results.json (concurrent writers); simulated cells read back from p3b_cells.csv |
| P4d | 2026-11-12 09:13 | 35f77661ac8cec352fa83cf8b4ef463ede8b10e3 |  |

## Deviations, mistakes and fixes

All are in `docs/07_log/DECISIONS.md` with the date: the wording-only edits, the grouping choice, a crash of the P4b evaluation before scoring, the closure bug in the P4c recall-gain statistic (the initial P4c verdict was produced by the bug and is replaced), a failed write of results.json during P3b (the pool-level and simulated entries were rewritten from the stored cells), and the measurement fixes of P4a.

## Not run

ESP32 flash and RAM (no cross compiler or emlearn here: `p.p4a.measured_bytes_esp32`); +-64 g in P3b; any hardware result; a second public crash dataset. the code is under Apache-2.0 (`LICENSE`, `NOTICE`; added on branch `finish`, 2026-11-13).
