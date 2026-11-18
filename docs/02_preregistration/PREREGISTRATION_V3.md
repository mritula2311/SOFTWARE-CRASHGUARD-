# Preregistration v3: algorithm studies X1 to X3 and X5 to X8 (written and committed before any Block 4 or Block 4b result exists)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | Studies X1 to X3 and X5 to X8 and the sensor-selection study, with addenda. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | AP = average precision; ASI = acceleration severity index; ESP32 = a Wi-Fi microcontroller family (Espressif); ESV = Enhanced Safety of Vehicles (conference); NCAP = New Car Assessment Programme; NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Date: 2026-11-12. Branch `journal-push` (from `v2-algorithms`). Software only; `data/hardware` is not read. Result keys of these studies start with `x.` (for example `x.x1.*`). No existing key or tagged result is changed.

Anything not written here is EXPLORATORY and is labelled so. Primary metrics, splits, thresholds and decision rules below are not changed after the earliest Block 4 number is produced. A mistake in this text is corrected in a dated addendum at the end, never by editing the sentences above it. Blocks 1 to 3 (T13a, T13c, sensor selection, VZCrash audit) are descriptive or confirmatory; their decision rules were written in `docs/07_log/DECISIONS.md` before each run.

Labels: MEASURED_SOFTWARE (computed from NHTSA crash tests or VZCrash windows), ANALYTICAL (formula or host estimate), SIMULATED, NOT_RUN (with reason). NHTSA tests are mostly high-speed barrier tests and the sensor is a software model; VZCrash events were selected on the device before release (the trigger here is a second stage) and no vehicle identifier is released.

## 0. Common rules

- **Seeds.** 42 for single-seeded work; 0 to 4 for repeated runs (forests, models with randomness); folds of grouped cross-validation use seed 42 plus the repeat index, as in `saturation_splits` (10 repeats of grouped 5-fold on make/model groups).
- **Intervals.** 95% percentile bootstrap, 1,000 resamples. Where the unit is a crash test, whole make/model groups are resampled together (`boot.ci_grouped`). Where the unit is a VZCrash test event, events are resampled; the same drawn events feed every compared method, so differences are paired.
- **p-values.** One-sided bootstrap p-value of each hypothesis' null (share of resamples on the wrong side; floor 0.001 with 1,000 resamples). The null of each hypothesis is given with it.
- **Multiplicity.** One Holm correction over the seven hypotheses H-X1, H-X2, H-X3, H-X5, H-X6, H-X7 and H-X8 together. H-X4 (labels) is a statement about the files and has no p-value. A hypothesis is SUPPORTED only if its stated criterion is met and its Holm-adjusted p-value is below 0.05; MIXED if the criterion is met and the adjusted p-value is not below 0.05; NOT SUPPORTED otherwise. If a hypothesis has two conditions (H-X1), the p-value belongs to the statistical condition and the other condition is decided by its rule.
- **Test set use.** Thresholds, rules and hyper-parameters are chosen on validation (VZCrash) or on training folds (NHTSA). The VZCrash test split is scored once per model and seed.
- **VZCrash sets.** Primary test set: the de-duplicated set of the headline pipeline (24,022 events). Sensitivity: the strict set (22,830 events; also without window-level near-duplicates), as in T5 and V4. Supplied splits only; no re-splitting.
- **Reporting.** Every result is reported with its interval, favourable or not. A negative result is an acceptable outcome of every study.
- **Origins.** All hypotheses are MEASURED_SOFTWARE except the flash estimates (ANALYTICAL, host arithmetic, not an ESP32 compile report).

## X1. Fixed-point forest for the microcontroller (VZCrash)

**Model.** The 10-tree depth-9 random forest chosen on validation (`rfsel`; `s4b.recommended.trees` = 10, `s4b.recommended.depth` = 9), trained per seed 0 to 4 on the training windows of the headline pipeline.

**Quantisation.** Per feature, an affine grid of 2^b levels over the range of that feature in the training windows; each split threshold is rounded to the nearest level; each leaf value (crash probability) is rounded to the nearest of 2^b levels on [0, 1]; the sum over trees stays in floating point; inputs are not quantised (the quantised-threshold comparison is the one the microcontroller would make). b = 16 (primary) and b = 8.

**Flash estimate (ANALYTICAL).** Nodes times bytes per node. Primary layout (the existing export): 1 byte feature index, a threshold field, two 2-byte child indices. Float32 thresholds: 9 bytes (the stored `export.bytes_est` rule). 16-bit thresholds: 7 bytes per node (reduction 22.2%); 8-bit thresholds: 6 bytes (33.3%). Variant (EXPLORATORY, a different change from quantisation): pre-order node layout with an implicit left child, one stored child index: float 7 bytes, 16-bit 5 bytes (28.6%), 8-bit 4 bytes (42.9%). **Stated before the run: under the primary layout the 16-bit version cannot cut the estimate by 30% (it cuts 22.2% by arithmetic).**

**Metrics.** AP of triggered test events; system recall at the validation-F1 threshold; system recall at the 1% and 5% false-alarm targets (thresholds re-chosen on validation with the quantised model's scores); the largest absolute difference between the quantised and the float probability over all real test events (and the number of events whose decision at the validation-F1 threshold changes). Intervals: paired bootstrap over test events (5-seed mean), 1,000 resamples. Sets: de-duplicated (primary), strict (sensitivity).

**H-X1.** The 16-bit version loses no more than 0.005 AP (the upper 95% bound of float AP minus 16-bit AP is at most 0.005) AND cuts the flash estimate by at least 30% (primary layout). Null for the p-value: AP loss at least 0.005 (p = share of resamples with loss below 0.005). **Counts against:** either condition fails. Expected: the flash condition fails by arithmetic; the AP condition is expected to hold.

## X2. Cheap-trigger cascade (VZCrash, lowest priority)

**Relation to N15.** N15 (c) already tried a learned trigger on running features inside the full system (a forest re-trained per candidate, chosen on system recall at a fixed false-alarm rate) and found no gain. X2 differs in what is compared: only the trigger stage, at an EQUAL non-crash trigger rate, against the 2 g and 1.5 g thresholds, with the rule selected by that constraint (not by system recall) and evaluated on held-out vehicle-size categories. It uses a wider family of cheap features. It is closer to N15 (c) than to a new idea, and is reported as a check of that null.

**Rule family.** Per event (the whole 16 s record, clipped to +-16 g per axis), running causal features: p = |a|; j = |a_t - a_(t-1)| x 100 (g/s); e = mean of (|a| - 1)^2 over the last 10 samples. Stage 1 fires at the earliest sample where p >= P OR (j >= J AND e >= Ee), with P in {1.2, 1.5, 2.0, 2.5, 3.0} g, J in {off, 25, 50, 100, 200} g/s and Ee in {0.05, 0.1, 0.25, 0.5, 1.0, 2.0} g^2. Stage 2 is the forest (not re-run: only the trigger-stage pass share is evaluated).

**Selection.** On the validation split: among the rules whose non-crash trigger rate does not exceed that of the 2 g threshold on the same events, the one with the largest crash pass share (ties: fewer terms, then larger P). Grouped evaluation: leave-one-vehicle-size-category-out (Light, Medium, Heavy, Unknown): the rule is selected on the validation events of the other categories and scored on the test events of the held-out category; categories are pooled for the point estimate and resampled as events for the interval.

**Metrics.** Crash pass share, non-crash trigger rate, for the cascade, the 2 g and the 1.5 g threshold, on the de-duplicated test set (strict as sensitivity).

**H-X2.** At a non-crash trigger rate not above that of the 2 g threshold, the cascade raises the crash pass share by at least 2 points over the 2 g threshold on the grouped evaluation (point estimate at least 0.02 and the paired interval above zero). Null: gain at most zero. **Counts against:** the interval includes zero, or the gain is below 2 points, or the non-crash trigger rate of the cascade on the test events exceeds that of the 2 g threshold by more than 1 point.

## X3. Group-aware training against near-duplicates (VZCrash)

**Data.** Near-duplicate groups among TRAINING windows: triggered training events whose 2.8 s trigger-aligned window is identical sample for sample (the V1 audit found that every flagged test window equals its training window with a maximum difference of exactly 0, so exact window equality is the T5 outcome). Groups come from the V1 window cache; no label is used.

**Variants.** Standard (baseline: every window weight 1); down-weight (primary): weight 1 / group size; merge (EXPLORATORY): one window per group. Model: the headline 15-tree forest (`rf15`); thresholds from the validation split as in the headline pipeline (validation is not changed).

**Metrics.** System recall at the 1% false-alarm target (threshold from validation) on the strict test set (primary), also at the 5% target, AP, and the same on the de-duplicated and supplied sets (secondary). 5-seed mean, paired bootstrap over strict test events.

**H-X3.** Down-weighting raises recall at the 1% target on the strict set by at least 1 point over standard training (5-seed mean of the paired difference at least 0.01, interval above zero). Null: gain at most zero. **Counts against:** the interval includes zero or the gain is below 1 point.

## X4 (optional): do the labels support more than crash against non-crash?

Read the dataset card (`data/raw/card/README.md`), the supplied columns and the paper's description; report what direction or severity information exists. No labels are invented. No hypothesis, no p-value.

## X5. Does a clipped sensor still rank severity correctly? (NHTSA, 176 tests)

**Data.** The 176 tests, the sensor model of `severity_study.sensor_signal`, ranges +-16, +-32, +-64 g, output rates 100 and 200 Hz. The estimators that were trained at 100 Hz (fill + ridge; the tail-aware median model) are scored at 100 Hz only; plain, spline, ASI and the direction-adjusted variants at both rates. Fitted estimators use out-of-fold predictions of repeated grouped 5-fold cross-validation on make/model groups (split R, 10 repeats); correlations are computed per repeat and averaged.

**Severity measures.** (1) plain delta-V; (2) spline delta-V; (3) fill + ridge delta-V; (4) tail-aware delta-V (the preregistered median model of Study A, `QR`); (5) ASI of the sensor window; (6) direction-adjusted: the longitudinal component of the plain delta-V for frontal tests and the lateral component for side tests. Reference: the N13 reference delta-V, and the ASI of the unclipped original-rate pulse.

**Primary quantities.** Spearman rank correlation between each measure and the reference delta-V; class agreement (accuracy and linear-weighted kappa) between the class of the estimate and the class of the reference delta-V (the limits of `config.SEV_DV_KMH`: 24, 40, 56 km/h), both with 95% grouped bootstrap intervals (make/model groups).

**H-X5 (primary).** At +-16 g and 100 Hz, the Spearman correlation between the fill + ridge delta-V and the reference delta-V is at least 0.90 and the lower end of its 95% grouped interval is at least 0.85. Null: correlation at most 0.85 (p = share of resamples with correlation at or below 0.85). Class agreement is reported with intervals and is not part of the criterion. **Counts against:** point estimate below 0.90 or lower end below 0.85. The plain estimate's correlation is the baseline and is reported next to it, because the plain estimate is the lower bound and a high correlation of both would mean that the ranking was never the problem.

**Exploratory: injury criteria.** Recorded dummy criteria in the NHTSA metadata (`OCCUPANT` records): for frontal tests the driver-seat dummy (location 01): head injury criterion (`HIC`) and chest 3 ms clip (`CLIP3M`); for side tests the driver-side dummy (location 01): thoracic trauma index (`TTI`) and pelvis acceleration (`PELVG`). A value counts only if it is above 0 and below 9,000 (the file stores missing values as 0 or 9999). The number of tests with each criterion is reported. **The reference's own Spearman correlation with each criterion is reported before any comparison; a criterion whose reference correlation is below 0.2 is dropped from the comparison** (prior work, Wusk and Gabler at the 25th ESV: delta-V, ASI and OLC only weakly related to dummy injury criteria in frontal NCAP tests at one speed; the numbers were given in the task and could not be verified here). For retained criteria: Spearman of each estimate with the criterion and the difference from the reference's correlation with grouped intervals; a loss whose interval reaches below -0.05 counts against "the clipped estimate preserves what the reference says about the dummy". No claim about injury in real crashes is made.

## X6. Lower-bound-anchored estimator (NHTSA, 176 tests)

**Related work to distinguish.** US 7,643,921 (Continental, granted 2010; opened 2026-11-11, local text `data/raw/refs/us7643921.txt`) extrapolates clipped samples with a slope set below 100% of the measured slope; our estimator is a learned correction factor applied to a delta-V estimate and constrained to be at least 1. Jao and Shkel 2022 and Zhang et al. 2026 could not be found by search and are not used.

**Estimator.** dv_anchored = dv_plain x exp(max(0, g(x))): g is a regression of y+ = max(0, log(reference / dv_plain)) on the clipping descriptors (clip_ms, n_runs, clip_frac, slope_in, slope_out, rise_ms, area_unclipped, area_clip), the pulse-family features (dv_mean, dv_median, dv_best, dv_wmean, disagree), dv_plain and pulse_ms (the feature set of Study A; `v2_clip`); the model is gradient boosting with squared-error loss (100 trees, depth 2, learning rate 0.05, subsample 0.8, as in Study A), fitted on the training tests of each fold; the output is clipped at zero from below, so the estimate can never fall below the plain (lower-bound) estimate. A ridge variant of g is EXPLORATORY. Tests with reference below the plain estimate (y < 0; 2 of 176 at +-16 g) enter training with y+ = 0 and are listed.

**Comparators.** fill + ridge (M+), the tail-aware median model (QR), the triangle fit (TRI) and plain (B) on the same splits.

**Splits.** R (primary), G, A, O (`saturation_splits`), +-16 g and 100 Hz primary; +-32 and +-64 g EXPLORATORY.

**H-X6.** At +-16 g on split R, the 90th-percentile absolute delta-V error of the anchored estimator is at least 5 points below that of fill + ridge (point estimate of p90(M+) minus p90(anchored) at least 5, with the 95% grouped interval of the difference excluding zero), the gain also has its whole interval above zero on at least one of the splits G, A, O, and the under-estimation share (estimate below the reference by more than 10%) of the anchored estimator is lower than that of the tail-aware estimator (point estimate of the paired difference below zero; its interval is reported). Null for the p-value: p90 difference at most zero on split R. **Counts against:** the interval includes zero, or the gain appears on one split only, or the under-estimation share is not lower.

## X7. Two-part sensor fusion from real parts (NHTSA, 176 tests; extends Block 2)

**Prior art.** Single-chip dual-range parts exist; a datasheet of one (LSM6DSK320X, low-g to +-16 g, high-g to +-320 g) was opened on 2026-11-12 (`docs/05_data_code/SENSOR_DATASHEETS.md`). The page of the LSM6DSV32X named in the task could not be opened. A fusion method is not the contribution; the quantified requirement table on real pulses is.

**Pairs (fixed before the run).** Low-range part: ADXL345 +-16 g at 3200 Hz, MPU-6050 +-16 g at 1000 Hz, LIS3DH +-16 g at 1250 Hz, KX134-1211 +-16 g at 1600 Hz. High-range part: ADXL375 +-200 g at 3200 Hz, H3LIS331DL +-200 g at 1000 Hz, ADXL372 +-200 g at 3200 Hz, KX134-1211 +-64 g at 1600 Hz. All 16 combinations are evaluated (mounting error and time synchronisation are not modelled: both parts see the same original signal; the high-range signal is resampled onto the low-range grid by linear interpolation). Configurations come from `sel_parts.py` (datasheet values, noise at the datasheet density).

**Fusion.** (i) Substitution with gain match: where the low-range sample is within 2% of its range or inside a clipped run, use the gain-matched high-range sample, elsewhere the low-range sample; the gain is the least-squares ratio of low to high on the unclipped samples of the pulse. (ii) Ridge-calibrated blend: the delta-V of the substituted signal times exp of a ridge prediction from [plain low-range delta-V, high-range delta-V, clipped share of the low-range part] (regularisation by leave-one-make/model-out on the training tests of each fold), out-of-fold on split R.

**Metrics.** Share of tests within +-10% of the reference delta-V (grouped interval), median and 90th-percentile error; the cost of the second part as an extra row (a count of parts and of bus transactions, not a price).

**H-X7.** Some pair, at some configuration in the list, has the lower end of the 95% interval of the share within +-10% at least 0.80 while neither of its two parts alone reaches that lower end at any configuration of the list. Null for the p-value: share within +-10% below 0.80 for that pair (the smallest one-sided bootstrap p over the 16 pairs and two fusion rules, multiplied by 32, capped at 1). **Counts against:** no pair does.

## X8. Sequential decision with error control (VZCrash)

**Rule.** The six length-specific forests of N19 give a crash probability p_k at post-trigger lengths 50, 100, 200, 400, 800 and 1,800 ms. Sequential statistic (a CUSUM-style recursion with lower reflection removed, equal to a SPRT with two boundaries): S_k = S_(k-1) + log(p_k / (1 - p_k)) - log(pi / (1 - pi)), S_0 = 0, with pi the validation crash share among triggered events (probabilities clipped to [0.001, 0.999]). Alarm and stop at the earliest checkpoint with S_k >= h_k; no alarm and stop with S_k <= l_k; at 1,800 ms the threshold t_f decides. The upper boundaries h_k are chosen on validation as the smallest values for which the per-event false-alarm rate at stopping is at most the target (1% or 5% of ALL non-crash events, system level, the trigger-discarded events counting as non-alarms); a common level h with k-dependence h_k = h x w_k (w_k from a fixed grid of three shapes) and l_k = -c in a grid of four values; the choice among grid points is the one with the smallest mean decision time on validation crashes subject to the false-alarm constraint (and recall not below the existing rule's recall on validation).

**Comparators.** The existing early-exit rule (N19, `early.py`) and the full-window forest at 1,800 ms, at the same 1% and 5% targets, seeds 0 to 4, on the de-duplicated and strict sets.

**Metrics.** Median decision time (ms) of triggered crash events, recall at the target, false-alarm rate at the target; paired bootstrap over test events; the ensemble-effect arms of S6 (the same six forests released at 1,800 ms) are repeated for this rule.

**H-X8.** The sequential rule gives an earlier median decision than the existing early-exit rule by at least 100 ms (paired interval excluding zero) at equal or better recall at the same false-alarm target. Null: median difference at most zero. **Counts against:** the interval includes zero, or the recall is lower with its interval excluding zero. The earlier recall gain of N19 was an ensemble effect (S6); the same is checked for this rule and reported.

## Seeds, baselines and what is reported (summary)

| Study | Seeds | Baselines | Primary metric | Origin |
|---|---|---|---|---|
| X1 | 0 to 4 | float forest | AP loss (upper bound) and flash estimate | MEASURED_SOFTWARE; flash ANALYTICAL |
| X2 | none (deterministic) | 2 g and 1.5 g trigger | crash pass share at equal non-crash rate | MEASURED_SOFTWARE |
| X3 | 0 to 4 | standard training | recall at the 1% target, strict set | MEASURED_SOFTWARE |
| X5 | 42 (fold seeds 42 + repeat) | plain estimate | Spearman against the reference delta-V | MEASURED_SOFTWARE |
| X6 | 42 (fold seeds 42 + repeat) | fill + ridge, tail-aware, triangle fit, plain | p90 of the absolute error | MEASURED_SOFTWARE |
| X7 | 42 | each part alone | share within +-10% | MEASURED_SOFTWARE |
| X8 | 0 to 4 | early-exit rule (N19), full window | median decision time at equal recall | MEASURED_SOFTWARE |

## Addenda

(none yet)
