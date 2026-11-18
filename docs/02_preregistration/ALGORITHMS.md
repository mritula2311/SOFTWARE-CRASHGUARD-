# Proposed algorithms: baselines, splits, metrics and rules (fixed before any result was looked at)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Algorithm proposals N14 to N16: baselines, splits, metrics and rules, with a revision log. |
| Evidence labels used | SIMULATED, ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; ASI = acceleration severity index; LOTO = leave-one-test-out; NHTSA = National Highway Traffic Safety Administration; PMC = PubMed Central; RAM = random-access memory; SF = spreading factor (LoRa) |
<!-- header:end -->

Written 2026-11-11, before the algorithm runs. Rules that apply to all three (from CLAUDE.md and the author's instruction):

- A claim counts only if the improvement over its baseline clears the 95% bootstrap confidence interval (1,000 resamples, seed 42) on data the method was not tuned on. Otherwise the result is reported as **no improvement found**, in the same detail as a success. A non-result is never presented as a contribution.
- Nothing is tuned on a test split. Every parameter below is chosen on a tuning part; the held-out part is scored once.
- `TRIGGER_G`, `MPU_RANGE_G`, `PRE_S` and `POST_S` stay placeholders in `config.py`; every system-level result is a function of them.
- Every number goes to `results/results.json` with an origin label. The banned words listed in CLAUDE.md are not used.
- Status words in the novelty files: SUPPORTED (clears the interval on data not tuned on), PARTIAL, NO_IMPROVEMENT_FOUND.

---

## N14. Saturation-aware severity estimator

**Problem.** A 16 g accelerometer clips real crash pulses (the NHTSA tests peak at about 42 g after the front-end filter), so plain delta-V from the clipped signal is biased low. The range study shows the fix by hardware (a wider range). This algorithm asks whether software can repair the clipped signal.

**Data.** The NHTSA tests of `results/tables/sevstudy_tests.csv`: frontal barrier tests and side impactor tests, vehicle-CG or front-sill accelerometer. Split by vehicle group (make, model, model year), fixed on 2026-11-11 (docs/07_log/DECISIONS.md, follow-up 1): groups sorted by their smallest test number, ranks 3, 6, 9, ... are HELD-OUT with all their tests, the others are TUNING; no group spans both sides (an earlier version split by test number). Leave-one-test-out cross-validation (LOTO) on the tuning set chooses every parameter; the held-out tests are scored once. Synthetic pulses with known delta-V are a second, SIMULATED data set.

**Reference.** The reference delta-V of `severity_study.reference_dv`: the largest resultant of the running integral of the original-rate, unclipped, baseline-removed horizontal acceleration within 300 ms of the trigger. Error is the sensor-model estimate against this reference.

**Sensor model.** The generic model of `severity_study.sensor_signal`: 260 Hz front end (4th-order zero-phase low-pass), saturation at the range, a digital low-pass at 0.4 x the sample rate, sampling at 100 Hz. Ranges +-16 g, +-32 g and +-64 g.

**Baseline B.** Plain delta-V integration of the clipped 100 Hz signal with the current `severity.py` (release rule 0.1 x peak, floor 0.5 g, 50 ms hold, 250 ms cap), as already implemented.

**Method M (saturation-aware).** Applied only when the pulse is saturated; otherwise M equals B.
1. *Saturation test.* A sample is saturated when |a_x| or |a_y| (the sensor reading, gravity included) is at least 0.98 x range. The pulse is the interval the baseline pulse rule gives (trigger to release). If no sample of the pulse is saturated, M = B.
2. *Pulse model.* The horizontal resultant h(t) = sqrt(a_x^2 + a_y^2) of the baseline-removed signal is modelled as A x s((t - t0) / T) for t0 <= t <= t0 + T and 0 elsewhere, with s one of: half-sine `sin(pi u)`, haversine `(1 - cos(2 pi u)) / 2`, triangle `1 - |2u - 1|` (u in [0, 1]).
3. *Fit.* A deterministic grid search, so that the same rule can be written in C without heap: t0 in {start - 1, start - 0.75, ..., start + 1} samples (9 values; start = the trigger sample), T in 21 values from 0.6 to 1.6 x the baseline pulse length (equal steps). For each (t0, T) the amplitude A is the least-squares amplitude over the UNSATURATED samples of the pulse, raised to at least the saturation level L = 0.98 x range (the clipped samples must be at or above the limit). The cost is the sum of squared errors on the unsaturated samples plus the sum of squared shortfalls max(0, L - A s) over the saturated samples. The (t0, T, A) with the lowest cost is kept. This uses the pulse timing (the unsaturated rise and fall) and the level of the unsaturated part.
4. *Fill.* At each saturated sample the horizontal vector is rescaled so that its magnitude is max(h_measured, A s(t)); the direction is kept. The baseline severity code is then run on the filled window, so delta-V and ASI both change.
5. *Family choice.* Half-sine is the primary method. Haversine and triangle are tried; the family with the lowest LOTO median absolute error on the tuning tests at +-16 g is the reported family (ties go to half-sine). The choice is made on the tuning tests only.

**Method M+ (learned correction).** On top of M, a ridge regression predicts the log of (reference / M estimate) from three inputs: the delta-V of the unsaturated part (km/h), the saturated share of the pulse samples, and the pulse width (ms). Inputs are standardised on the tuning set; the regularisation strength is chosen from {0.01, 0.1, 1, 10, 100} by LOTO on the tuning set. The correction is applied only when the pulse is saturated. One model per range.

**Metrics** (each at +-16, +-32 and +-64 g, for B, M and M+): median and 90th percentile of the absolute delta-V error (%), the share of tests within +-10% and within +-20% of the reference, and the share of frontal tests inside v <= delta-V <= 2 v (v = test impact speed). Each with a 95% bootstrap interval over tests. The comparison with the baseline is paired on the same tests: the difference in median absolute error and in the share within +-10%, with a 95% interval. Failure cases are all tests where the method's absolute error is larger than the baseline's.

**Decision rule (primary endpoint).** The difference (M or M+ minus B) in the median absolute delta-V error on the HELD-OUT tests at +-16 g. The method is SUPPORTED at a range only if the whole 95% interval of that difference is below zero. The same test is applied at +-32 g and +-64 g. The share within +-10% is secondary.

**Synthetic check (SIMULATED).** Half-sine, haversine, triangular and (as a mismatched case) square pulses with analytic delta-V, peak 20 to 150 g, duration 40 to 150 ms, passed through the same sensor model. Errors of B and M against the analytic value.

**C version.** The saturation test, the grid fit for the chosen family, the fill and (if M+ is kept) the correction are added to `firmware_export/severity.h` and checked against Python on the NHTSA and synthetic windows. Flash and RAM are host estimates (ANALYTICAL).

**Prior work to search:** clipped or saturated accelerometer reconstruction and pulse-function fits in crash and impact analysis. Queries, dates and closest work go to `docs/06_references/PRIOR_WORK.md`.

---

## N15. Trigger-aware training

**Problem.** The detector is a second stage behind a fixed trigger. This asks whether choosing or learning the trigger together with the classifier raises the system recall at a fixed false-alarm rate. **VZCrash events were already selected on the device by threshold heuristics, so the trigger here is a second stage; the results do not apply to continuous driving.**

**Data.** The de-duplicated VZCrash splits (primary test set), the same events and windows as the existing results. Thresholds and every choice below use the validation split only; the test split is scored once per method and seed.

**Baseline B.** The fixed trigger (config value, 2.0 g) followed by a separately trained 15-tree, depth-6 forest (the deployed model), with the decision threshold chosen on validation to meet the target false-alarm rate. Seeds 42 (headline) and 0 to 4 (mean and standard deviation).

**Target false-alarm rates.** 1% and 5% of ALL non-crash events (system level: events the trigger discards count as correct negatives). The threshold is the smallest one for which the validation false-alarm rate does not exceed the target.

**Method a. Joint selection.** For each trigger level in {1.5, 2.0, 2.5, 3.0} g (the variants already extracted), train the forest on the triggered training events, choose the threshold on validation for the target rate, and score validation system recall. The trigger level with the highest validation system recall at the target rate is selected (ties go to the config trigger). The test set is scored once for that selection.

**Method b. Cost-sensitive training.** Crashes that the config trigger discards are treated as errors: their peak-centred window features (the existing `peak` variant) are added to the training set as positives with weight g, for g in {0, 0.5, 1, 2}; g = 0 is the baseline. The weight is chosen on validation (highest system recall at the target rate). The test events are triggered with the config trigger as in the baseline.

**Method c. Learned trigger.** A rule on three cheap running features that can be computed without buffering the window: the running peak |a| (p), the jerk (largest absolute difference of |a| between consecutive samples, per second, j) and the energy of the last 10 samples (sum of (|a| - 1)^2 times the sample period, e). The trigger fires at the earliest sample where `|a| >= p`, or where `jerk >= j AND energy >= e`. Candidates: p in {2.0, 2.5, 3.0, 4.0} g, j in {50, 100, 200} g/s (j off = infinity), e in {0.5, 1.0, 2.0} g^2 s. A candidate is a combination of the three; the total is at most 4 x 4 x 3 = 48 candidates (j off needs no e). For every candidate the windows, features and a forest are rebuilt and the validation system recall at the target rate is computed; the best candidate is selected on validation. RAM and operation counts are ANALYTICAL.

**Metrics.** System recall at 1% and 5% false-alarm rate (test), the area under the system-level precision-recall curve (system AP), the trigger rate by VZCrash vehicle-size category (crash events), all with 5 seeds mean +- std. The comparison with B is the paired bootstrap difference on the same test events (1,000 resamples): the difference in system recall at each target, and in system AP.

**Decision rule.** A method is SUPPORTED only if the whole 95% interval of its paired difference in system recall (at either target rate, stated which) is above zero on the test set. Otherwise NO_IMPROVEMENT_FOUND.

**Prior work to search:** joint trigger and classifier design, cascade detectors, cost-sensitive early-stage rejection in crash or impact detection.

---

## N16. Severity- and budget-aware delivery scheduler (supporting evidence only)

**Problem.** Under a 10% duty cycle, which alerts get airtime earlier, and how should retries be spaced? Everything here is SIMULATED and is supporting evidence that hardware test H3 would replace.

**Baselines.** (i) the fixed 3-retry policy (arrival order, immediate retry); (ii) the current severity-table policy with the token bucket (maximum tries 2, 4, 8 and 12 for low, moderate, severe and critical, the most severe waiting alert next, immediate retry).

**Scheduler S (all rules and parameters).**
1. *Reserve.* A fraction `rho` of the node's token capacity (360 s) is kept for critical alerts: a non-critical alert may be sent only if tokens after the send are at least `rho` x capacity.
2. *Order.* Waiting alerts are served by effective severity = class + min(age / tau, 0.99), highest served next, with `tau` = 300 s (an old low alert can overtake a newer one of the same class but never one of a higher class).
3. *Retry spacing.* After the k-th failed try the next try is ready after the listening window plus `m x base_sev x 2^min(k-1, 5) x (1 + jitter x u) x (1 + 2 x (1 - p_hat))`, capped at `cap_sev`, where u is uniform in [0, 1), `p_hat` is an exponentially weighted share of successful tries (weight 0.3, start 1.0, updated after each try by ACK feedback), `base_sev` = 0.5, 1, 2 and 4 s and `cap_sev` = 8, 16, 32 and 64 s for critical, severe, moderate and low. Maximum tries are those of baseline (ii).
4. *Spreading factor.* If enabled, after 3 consecutive failures of an alert of class moderate or above the alert's next try uses SF + 1 (at most SF12), but only if the tokens after the send are at least twice the new airtime. ASSUMPTIONS stated in the report: the base receives all spreading factors, and the per-transmission loss at SF s is the SF7 loss times 0.7 per step above SF7 (no measurement; H3 would measure it).
5. *Parameters to tune:* `rho` in {0, 0.2}, `m` in {0.5, 1, 2}, `jitter` in {0, 0.5}, SF raise on or off (24 combinations).

**Scenarios.** Tuning scenarios: seeds 100 to 104, iid loss 15%, 35% and 55%, a Gilbert-Elliott burst at mean 25% and 45% (P_BG = 0.3, bad-state loss 0.9), SF7 and SF12, event rates 20 and 120 per hour, the base at its full budget or with 2 s left. Held-out scenarios (different seeds 200 to 204 and different loss settings, never used for tuning): iid loss 10%, 30%, 50% and 60%, burst at mean 30% and 50%, separate ACK loss (uplink 30%, downlink 10% and 50%), event rates 10, 60 and 240 per hour, a base already near its budget (2 s left), SF7, SF9 and SF12.

**Tuning objective (fixed now).** J = mean over tuning scenarios of [ (1 x delivered_low + 2 x delivered_moderate + 4 x delivered_severe + 8 x delivered_critical) / 15 - 0.2 x airtime_share_total ], where delivered_c is the share of class-c alerts whose ACK reached the car; a class with no alerts in a scenario is left out of that scenario's weighted sum and the weights are renormalised. The best combination is the one with the highest J; ties go to fewer enabled features.

**Severity classes of the alerts.** From the replay pipeline (docs/02_preregistration/ALGORITHMS.md sections above and `replay.py`): the real VZCrash mix (almost all low), the NHTSA mix through the 16 g sensor with the plain estimator, the NHTSA mix with the saturation-aware estimator (N14), the reference classes, and an assumed 40/30/20/10 stress mix. For the estimator comparison each alert has a TRUE class (reference delta-V) and an ESTIMATED class (what the car would send); the policy uses the estimated class and the results are reported by the true class.

**Metrics** for each class: delivery rate (ACK reached the car), median and 95th percentile of the trigger-to-ACK time, mean retries, share of the duty-cycle budget used, and the number of critical alerts blocked by budget exhaustion (initial transmission delayed by more than 1 s, and never sent within the hour). Bootstrap 95% intervals over simulated hours (scenario seeds x hours); policy comparisons are paired on the same arrivals.

**Decision rule.** N16 is supporting evidence, never the headline. It is reported SUPPORTED for a conclusion only where the paired 95% interval of the held-out difference excludes zero; the report lists which conclusions survive when the loss model, spreading factor, event rate, cancel window or base budget changes, and which do not.

---

## Order of work and files
N14: `src/crashguard/saturation.py` (+ tests, + C in `severity.h`); N15: `src/crashguard/trigger_aware.py` (+ tests); N16: `src/crashguard/scheduler.py` (+ tests). Results go to `results/results.json` under `n14.*`, `n15.*` and `n16.*`; figures and tables under `results/`.

---

## Revision log (kept in the open; no held-out result had been looked at at the time of any entry)

**2026-11-11, N14, development on the TUNING tests only.** An initial run of the method as written (saturation level 0.98 x range, three pulse families) on the 118 tuning tests at 100 Hz showed that the fill barely changes delta-V (median absolute error at +-16 g: baseline 25.3%, fill 23 to 25%). Reason: in the sensor chain the clipping happens before the 40 Hz low-pass, so the clipped plateau is smoothed and few samples reach 0.98 x range. The saturation level is therefore a parameter of the method, chosen with the pulse family on the tuning tests: levels {0.98, 0.9, 0.8, 0.7, 0.6, 0.5} x range, families {half-sine, haversine, triangle}; the pair with the lowest mean over the three ranges of the median absolute error on the tuning tests is used (ties: half-sine, then the higher level). Samples at or above the level are treated as lower bounds (they may be filled but are not used in the fit); the fit uses the samples below the level (the rise and fall). Nothing else changed. The held-out tests were not used in this development; they are scored once by `saturation_study.py`.

**2026-11-11, N15 decision rule made explicit after the initial run (this one tightens, not loosens, the rule).** The initial run printed the seed-42 paired differences: for method a (trigger 3.0 g chosen on validation at the 1% target) recall was +1.4 points with an interval above zero, while the mean over seeds 0 to 4 was -0.2 points (baseline 0.6265 +- 0.0039, method 0.6247 +- 0.0050). A single model draw is not enough, so the decision rule uses the SEED-AVERAGED paired difference: for each bootstrap resample of test events, the mean over seeds 0 to 4 of (method recall - baseline recall). A method is SUPPORTED only if the whole 95% interval of that difference is above zero (system recall at the stated target); the seed-42 difference and the change in system AP are reported next to it. Nothing else changed.

---

## N14 extension (Part 0B, B1). Definitions written 2026-11-11 BEFORE the B1 code was run

**Why.** The closest threat to N14 is spline restoration of clipped acceleration (Ruder et al., applied and tested by Chan et al. 2023, Sensors 23(10) 4609; opened through Europe PMC, PMC10222349). N14 is compared with it, on stricter splits, before any claim is kept. **Status of the earlier result:** the grouped held-out set (58 tests, 56 groups; tuning 118 tests, 112 groups) was seen in the earlier N14 and release-rule results, so a rerun on it is "stable under re-splitting", not a blind test. No result here is described as a blind test.

**Primary method.** The earlier text above names "M or M+" in the decision rule and says half-sine is the primary pulse family; it never names one of fill-only (M) or fill + ridge (M+) as primary. That is stated openly. From this point (set now, before the B1 run, so after the earlier numbers were seen) the primary method for B1 is **M+ (fill + ridge)**, because the author's decision rule is written for it. M (fill only) is reported next to it. Nothing about M+ is changed.

**Methods compared (four), each at +-16, +-32 and +-64 g, on the same sensor model as above:**
1. **Plain** (B): integration of the clipped signal.
2. **Spline restoration** (SP), fixed as follows. Per horizontal axis (x and y) of the sensor reading, a *clipped segment* is a maximal run of consecutive samples, from the trigger sample to the end of the baseline pulse (the same pulse end as B), with |reading| >= L x range. L is the saturation level, chosen on the original TUNING tests from {0.98, 0.9, 0.8, 0.7, 0.6, 0.5} by the lowest mean over the three ranges of the median absolute error (the same selection rule as M; ties go to the higher level). For each segment the 3 samples immediately before it and the 3 immediately after it (clean samples: below L x range, not in another segment) are taken; a 5th-order spline (order 5, as in the MATLAB `spapi(5, ...)` call that Chan et al. report; implemented as degree 4 with `scipy.interpolate.make_interp_spline`, so knots may differ from MATLAB) is interpolated through these 6 points and evaluated at the segment samples. The restored value replaces the measured one only where its magnitude is larger (restoration may not shrink the reading) and is capped at 12 x range (same cap as M). **If fewer than 3 clean samples exist on either side (window edge, or another segment closer than 3 samples), that segment is left as measured.** Delta-V is then computed from the restored window with the same severity code.
3. **Fill** (M) and 4. **fill + ridge** (M+) exactly as defined above (triangle pulse, saturation level 0.7, release fraction 0.1, ridge strength chosen by leave-one-test-out on the tuning tests of the split being used).

**Metrics per method, range and split:** median and 90th percentile of the absolute delta-V error (%), share within +-10% and within +-20%. **Paired comparisons** (M+ minus SP, M minus SP, M+ minus plain, SP minus plain): difference in median absolute error and in share within +-10%, 95% bootstrap interval **resampled by vehicle group** (1,000 resamples, seed 42; all tests of a drawn group are drawn together).

**Decision rule (fixed now).** N14 counts as an improvement at a range, on a split, only if the whole interval of (M+ minus SP) in median absolute error is below zero AND the whole interval of (M+ minus plain) is below zero. Where SP matches M+ (interval contains zero) or is better, the result is reported that way and N14 is re-worded in `novelty_summary.md` as "a comparison of clipping-restoration methods for delta-V at low sensor range", with the pulse-fit method labelled as not better than spline restoration. Where M+ is not better than plain at +-32 g and +-64 g the words are "no improvement found".

**Splits.**
- **O. Original test-number split.** Within each kind (frontal, side), tests sorted by test number; ranks 3, 6, 9, ... held out.
- **G. Grouped by make, model and model year** (the current split; groups sorted by smallest test number, every third held out).
- **A. Stricter split A: grouped by make and model only** (model year ignored); groups sorted by their smallest test number, every third group held out. The numbers of groups and tests on each side are reported.
- **R. Repeated grouped cross-validation** over all groups (make and model), 5 folds x 10 repeats, group order shuffled with seed 42 + repeat index and dealt round-robin to folds. Inside every fold, using the training groups only: the pulse family, saturation level and release fraction are chosen from {3 families} x {6 levels} x {release fractions 0.05, 0.1, 0.2} by the lowest mean over the three ranges of the median absolute error (these choices have no fitted parameters; the held-out fold never enters), the ridge strength is chosen from {0.01, 0.1, 1, 10, 100} by leave-one-GROUP-out on the training groups (the inner grouped cross-validation), the ridge is fitted on the training groups, and the held-out fold is scored once. The plain method and the spline choose their own release fraction (and level) the same way. Pooled result: the median absolute error over all out-of-fold predictions of one repeat, averaged over the 10 repeats; interval by bootstrap resampling of groups on the pooled predictions of repeat 0 plus the spread (min to max) across the 10 repeats is reported separately.

**Settings for O, G and A (no re-tuning).** Triangle pulse, saturation level 0.7 (fill), release fraction 0.1, spline level chosen on G's tuning tests; ridge strength chosen and ridge fitted on that split's own tuning tests. Note: the settings were chosen on G's tuning groups; some A and O held-out tests were in G's tuning set, so only the ridge is new on those splits. R is the only split where every choice is repeated inside the folds.

**Failure-case table (+-16 g).** The ten tests with the largest absolute error after fill + ridge: make, model, test type, peak g (the front-end-filtered peak and the raw peak) and the share of pulse samples at or above the saturation level. Listed for the held-out set of G and, separately, from the out-of-fold predictions of R.
