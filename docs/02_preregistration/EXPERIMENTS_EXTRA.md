# Extra software-only experiments X1 to X7 (N17 to N23): baselines, splits, metrics, primary variants and decision rules

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Extra experiments X1 to X7 (N17 to N23): baselines, splits, metrics, decision rules. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; ASI = acceleration severity index; CV = cross-validation; FMVSS = Federal Motor Vehicle Safety Standards; HIC = head injury criterion; ISO = International Organization for Standardization; LoRa = long-range radio modulation; MCU = microcontroller unit; MEMS = micro-electromechanical system; NCAP = New Car Assessment Programme; NHTSA = National Highway Traffic Safety Administration; PPV = positive predictive value; SCT = severity-classified transmission; SF = spreading factor (LoRa); UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

Written 2026-11-11, BEFORE any of these experiments was run. Rules for all seven (from CLAUDE.md and the author's instruction):

- **Software only.** Nothing here is a hardware result. Every number goes to `results/results.json` with an origin label (MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN). The banned words listed in `CLAUDE.md` (rule 7) are not used. `TRIGGER_G`, `MPU_RANGE_G`, `PRE_S` and `POST_S` stay placeholders in `config.py`; results that depend on them say so.
- **A claim counts only if the improvement clears the 95% bootstrap interval on data the method was not tuned on.** A result that does not is reported as NO_IMPROVEMENT_FOUND in the same detail as a success. Every choice (window, threshold, defence parameter) is made on a tuning part or on the validation split; the held-out or test part is scored once.
- **Splits.** NHTSA experiments use the grouped NHTSA split (by make and model; the make, model and year split is also reported) and **resample whole groups** for every interval. VZCrash experiments use the de-duplicated splits (supplied train and validation, de-duplicated test set; 24,022 test events); thresholds come from validation only; seed 42 for headline numbers and seeds 0 to 4 for repeated runs.
- **Prior-work search.** Each experiment gets a dated search (queries, closest work, opened or snippet-only) in `docs/06_references/PRIOR_WORK.md`, and a verdict N17 to N23 in `report/novelty_summary.md`. A search cannot prove that nothing exists. Snippet-only items support no claim.
- **Status words:** SUPPORTED (clears the interval on data not tuned on), PARTIAL, NO_IMPROVEMENT_FOUND.
- **Wording for the novelty file:** the framing stays "what a low-cost crash node must measure" and the integrated system. New items are supporting evidence or negative results where that is what they show.

---

## X1 (N17). Impact direction on real crashes

**Question.** Does the firmware direction rule (angle of the horizontal impulse over the opening 60 ms after the trigger) recover the impact side on real crash-test records seen through our sensor model?

**Data.** The 176 NHTSA tests already used, plus any further tests the API returns with the same selection rules for other impact configurations. What the database offers was checked on 2026-11-11 by scanning every impact angle 0 to 359 (test number 3000 and above): angles present are 0 (frontal barrier), 270 (impactor or vehicle into vehicle, side), 285 (vehicle into pole), 345 (oblique impactor) and 10 (sled); angle 180 (rear) has no instrumentation records. So **rear impacts cannot be tested** and the struck side of the 270 tests must be read from the metadata (dummy seat, test title). **A class with fewer than 10 usable tests in total is not scored; no accuracy is printed for it.**

**Axes and sign convention (documented, then verified on the frontal tests beforehand).** CrashGuard: X forward, Y left, Z up. The ISO MME channels are read as longitudinal (X) and lateral (Y) vehicle axes; the sign of each is *checked against the data*, not assumed: in frontal tests the vehicle decelerates, so the mean X acceleration over the pulse must be negative if X points forward. If it is not, the axis is flipped and the flip is recorded. The side tests then check the Y sign using the struck side from the metadata. The vehicle accelerates away from the impact point, so **the impact side is opposite to the impulse direction**: impact direction = atan2(-Jy, -Jx), measured from +X (front) towards +Y (left).

**Rule (firmware).** After the 100 Hz sensor model (260 Hz front end, clipping at the range, 40 Hz low-pass), baseline (gravity) removed by the pre-trigger mean: impulse J = sum of horizontal acceleration over the initial W ms after the trigger sample. Class by sector of the impact direction: front (within 45 degrees of +X), left (45 to 135), rear (beyond 135), right (-135 to -45). Reported angle = impact direction in degrees.
**Parameter tuned on the tuning groups only:** the window W from {30, 60, 100} ms (the firmware text says 60 ms; 60 is the default and is changed only if another value is better on the tuning groups by more than one test). No other parameter.

**Baselines.** (1) Always the majority class of the tuning groups. (2) The sign of the longitudinal impulse only (front or rear) for the front-rear question.

**Metrics.** Confusion matrix, per-class accuracy, overall accuracy; for tests with a recorded oblique angle, the absolute angle error (median, 90th percentile) where the reference angle can be read from the metadata without guessing (otherwise it is not reported). Ranges +-16, +-32 and +-64 g. Intervals: bootstrap over make-and-model groups. Failure cases are listed.

**Decision rule.** The rule is SUPPORTED for a class and range if the lower end of the 95% grouped interval of per-class accuracy on the held-out groups is above the best baseline's accuracy for that class. A class below the count limit is reported as NOT_SCORED.

**Prior work.** Start from Balfaqih 2022, Ebert 2016, Tadic and Vukajlovic 2016 (opened). Principal direction of force estimation from in-vehicle accelerometers is established, so N17 is worded as **validation of a supporting feature**, not a contribution, unless the evidence says otherwise.

---

## X2 (N18). Severity measures against dummy injury measures

**Question.** Which of delta-V, ASI, peak acceleration and specific energy track the dummy injury criteria recorded in the same crash tests, and does delta-V add anything beyond the impact speed?

**Data.** The occupant records in the NHTSA metadata already cached for each test (`OCCUPANT` entries: dummy type, seat position, HIC, chest, femur, neck and pelvis fields where present). Which tests have which criteria is recorded in `docs/05_data_code/DATASET.md`. **If the criteria are not usable (missing or all zero), the experiment stops, writes exactly what is missing and moves on.** The meaning and unit of each field (for example HIC15 against HIC36) is checked in the data dictionary the database provides before it is used; if it cannot be established the field is not used.

**Severity measures** from the same chain as the other NHTSA results: delta-V, ASI, peak pulse acceleration and specific energy (half the squared delta-V) computed from the vehicle-CG channel, at the unclipped reference chain and at +-16 g and +-64 g sensor models.

**Analysis.** Spearman correlation of each severity measure with each injury criterion, **separately for frontal and side tests**, per dummy position; the correlation of delta-V with the impact speed alone; and the **partial Spearman correlation** of delta-V (and of ASI) with each criterion controlling for impact speed (rank-based partial correlation). Grouped bootstrap (make and model) for every interval. A correlation counts as present only if its 95% interval excludes zero; "delta-V adds beyond speed" counts only if the partial correlation's interval excludes zero.
**Severity classes against limits.** For each of the four classes (Low, Moderate, Severe, Critical), the share of tests whose criterion exceeds a regulatory limit. Limits are cited from documents that were opened (FMVSS 208 or Euro NCAP text); any limit that could not be verified is marked UNVERIFIED and not used for a claim.
**Stated plainly:** dummy criteria are test measurements, not human injury, and the sample is small.

**Primary question for the decision.** Does the partial correlation of delta-V with the chest or head criterion, controlling for speed, have an interval above zero for frontal tests? Everything else is descriptive.

---

## X3 (N19). Early classification

**Question.** How much of the 1.8 s post-trigger window does the deployed forest need, and does a sequential early-exit rule cut the decision time without losing recall at a fixed false-alarm rate?

**Data and model.** De-duplicated VZCrash splits, the same windows as the deployed model with the post-trigger length truncated to {50, 100, 200, 400, 800, 1800} ms (pre-trigger length fixed at 1.0 s). Features recomputed for each length; the deployed forest (15 trees, depth 6) trained at each length, seeds 0 to 4 (seed 42 for headline), threshold chosen on validation for 1% and 5% false alarms of all non-crash events (system level, as in the detector study).

**Baseline.** The full 1,800 ms window (the deployed model).

**Early-exit rule.** Checkpoints at the six lengths. At checkpoint k the model of length k gives a probability p. If p >= hi_k the event is declared a crash at that time; if p <= lo_k it is declared not a crash at that time (no alarm); otherwise the decision waits for the next checkpoint; at 1,800 ms the validation threshold decides. **hi_k and lo_k are chosen on validation only** from a fixed grid of quantiles: for the false-alarm target, the pair (one global hi quantile and one global lo quantile, each applied to every checkpoint through the model's validation score distribution) with the highest validation system recall subject to validation system false-alarm rate at most the target; ties go to the lower mean validation decision time.

**Metrics.** System recall at the fixed false-alarm rate against decision time (fixed windows: the post-trigger length plus the trigger itself; early-exit rule: its own mean decision time); mean and 95th percentile of the decision time of crash events for the early-exit rule against the fixed 1,800 ms window. Paired bootstrap over test events for the difference in recall and in mean decision time. The MCU cost of incremental feature updates is **ANALYTICAL** (operation count per sample from the feature definitions). The effect on the end-to-end time before the cancel window is **SIMULATED** (stage times assumed from `docs/` and the replay study) and marked as unconfirmed by hardware.

**Decision rule.** SUPPORTED if the early-exit rule's mean decision time for crash events is lower than 1,800 ms by a paired interval below zero AND its recall difference interval does not fall below -0.01 (a one-point loss) at the same false-alarm target. Otherwise NO_IMPROVEMENT_FOUND.

---

## X4 (N20). Guaranteed false-alarm control

**Question.** Does split-conformal threshold selection give a false-alarm rate at most alpha when exchangeability holds, and where does it fail when it does not?

**Method.** Scores of the deployed forest. Calibration set = non-crash events of the validation split (system level: events the trigger discards have score -1 and count as non-alarms). Conformal threshold for alpha in {1%, 5%}: the k-th smallest calibration score with k = ceil((n + 1)(1 - alpha)); the alarm is score above the threshold, so that for a new exchangeable non-crash event P(false alarm) <= alpha. **Baseline:** the existing validation-chosen threshold (the smallest threshold whose validation false-alarm rate is at most alpha).

**Experiments.** (a) Test-set false-alarm rate and recall over seeds 0 to 4 and calibration-set sizes {200, 500, 1,000, 2,000, all}, with 200 random draws of the calibration set per size and seed; report the share of draws where the test false-alarm rate exceeds alpha (the guarantee is marginal over calibration draws: about alpha of draws at most are expected to exceed it only in a coverage sense, so the report states the expected and observed values). (b) Break exchangeability on purpose: calibrate on three VZCrash vehicle-size categories and test on the fourth, and the reverse (calibrate on one and test on the other three); report the false-alarm rate against alpha and by how much it fails.

**Decision rule.** The guarantee is SUPPORTED if in (a) the mean test false-alarm rate is at most alpha with the interval over draws and seeds not above alpha for calibration sets of 1,000 or more; (b) is a limitation study and has no decision rule. A recall difference against the baseline counts only if its paired interval excludes zero.

---

## X5 (N21). Sensor-spoofing robustness

**Threat model** (`docs/01_protocol/THREAT_MODEL_SPOOFING.md`). An attacker can add a bounded signal to the accelerometer reading. Budgets: amplitude epsilon in {0.1, 0.25, 0.5, 1, 2} g (maximum absolute value added on any axis), and bandwidth limited to a sinusoid or a narrow band (one to three frequencies chosen from 2 to 45 Hz; the sensor is sampled at 100 Hz, so nothing above 50 Hz exists). Goals: (a) make a non-crash window cross the trigger and be classified as a crash; (b) hide a real crash (make it not trigger or not classify). **Simulated only on the dataset windows. No attack code is written to act on a physical sensor** (no signal generator, no resonance search, no hardware interface); the perturbation exists only as an array added to a stored window.
Parts of this threat model are taken from published work on acoustic and resonant attacks on MEMS accelerometers and gyroscopes; which parts is stated in the report after the search.

**Attacks on the deployed forest.** (1) Random search: 500 random draws of a bounded signal per window. (2) Structured search: a grid over frequency (2 to 45 Hz), amplitude (the budget) and phase for sinusoids and narrow bands, 200 candidates. (3) Gradient-based attack on a surrogate (a logistic regression and a small neural network on the downsampled window), with the perturbation projected onto the budget and the narrow-band constraint, then transferred to the forest.
**Attacked windows.** A fixed random sample of 1,000 non-crash and 1,000 crash windows of the de-duplicated test set that pass the trigger (seed 42), scored once; nothing is tuned on them.

**Defences** (parameters chosen on validation windows only): (D1) median filter (3 and 5 samples) on the window before features; (D2) a plausibility check: delta-V against peak acceleration consistency and cross-axis share (a pure sinusoid has large peak and near-zero delta-V), limits taken from the training crashes; (D3) adversarial training: the forest is retrained with attacked training windows at the same budgets (labels unchanged); (D4) an ensemble with the physics-based severity check (alarm only if the forest and the severity check agree).

**Metrics.** Attack success rate against budget for the baseline and each defence, with bootstrap intervals over windows; the cost of each defence in recall and false-alarm rate on clean test events (seed 42 headline, intervals by bootstrap).

**Decision rule.** A defence is SUPPORTED at a budget if its attack success rate is below the baseline's by an interval that excludes zero AND its clean recall loss at the 5% false-alarm target is below 0.02 (two points). The attack results themselves are descriptive.

---

## X6 (N22). Many-car LoRa capacity

**ANALYTICAL part.** Pure-ALOHA collision probability for N cars with alert and heartbeat rates stated in the report, and with the capture effect (a packet survives a collision if its power exceeds the others' by 6 dB, a stated assumption), for SF7, SF9 and SF12 using the airtime formula already in `lora.py`; and the base station's own limit: ACKs per hour that fit in its 10% duty cycle (26-byte ACK).

**SIMULATED part.** Event-driven simulation, N from 1 to 500 cars on one channel (the 433 MHz testbed assumption), Poisson crashes per car, a burst scenario (several alerts within seconds), heartbeats at a stated rate, a half-duplex base that cannot receive while it sends an ACK, base ACKs paid from its token bucket, per-car duty-cycle bucket as in the single-node simulation. Policies compared: fixed 3-retry, severity table, severity-aware scheduler (the same rules and parameters as N16, not re-tuned).

**Metrics.** Critical-alert delivery (ACK received by the car) and trigger-to-ACK latency against N, with bootstrap intervals over simulated hours; the N at which the base's ACK budget becomes the bottleneck; which conclusions change with the heartbeat rate and the spreading factor.
**Decision rule.** Descriptive: no method is claimed. A policy comparison is reported as different only where the paired interval excludes zero.
**Prior work.** Start from Tomic 2020, Wei 2023, Zhong and Nie 2024 (opened), then search further.

---

## X7 (N23). Scale-model transfer by physical scaling

**Question.** If a scale model's crash windows are an amplitude- and time-scaled version of a real crash, how do the deployed model's all-feature and scale-free-feature versions behave?

**Method.** VZCrash de-duplicated test windows are transformed: amplitude a in {0.25, 0.5, 1, 2, 4} (applied to the baseline-removed acceleration, gravity restored) and time-scale tau in {0.25, 0.5, 1, 2} (x'(t) = a x(t / tau), resampled at 100 Hz; for tau < 1 a zero-phase low-pass at 45 Hz is applied initial so that the result is not aliased, and an unfiltered variant is also reported). The window is re-cut (trigger and features recomputed). The deployed models, trained on the unscaled data (all 14 features, and the 5 scale-free features), are applied unchanged (seed 42; seeds 0 to 4 for means).
**Metrics.** AP and system recall at the validation threshold over the (a, tau) grid; which features are invariant (checked analytically and numerically); the Nyquist problem when tau shortens a pulse below about 40 ms (share of crash pulses whose duration above 2 g is below 40 ms after scaling).
**Decision rule.** None: this is a plausibility check, stated plainly. **It cannot predict performance on the author's car; hardware transfer test H2 is the real test.**

---

## Order of work and files

X1 `src/crashguard/direction.py`; X2 `src/crashguard/injury.py`; X3 `src/crashguard/early.py`; X4 `src/crashguard/conformal.py`; X5 `src/crashguard/spoofing.py`; X6 `src/crashguard/capacity.py`; X7 `src/crashguard/physical_scaling.py`. Results under `x1.*` to `x7.*` keys (N17 to N23). Each module has its tests. Each experiment is committed with an entry in `docs/07_log/PROGRESS.md`.

---

# Round 3 plans (written 2026-11-11 before the runs; keys `s2.*` to `s12.*`)

## S2. Effect of the cross-split duplicates (N8) on the headline

**Claim type.** N8 is a data-quality finding about one dataset, not a performance finding. This item only measures how much the duplicates move the headline.

**Part 1: side by side.** Deployed forest (15 trees, depth 6) with seeds 0 to 4 (mean) and seed 42; also the validation-selected 10 x 9 candidate. Threshold = validation maximum-F1 threshold (the headline rule), chosen once. Metrics: system recall, system false-alarm rate, model-level AP (triggered events) and system AP, each on (a) the supplied test split and (b) the de-duplicated test split (the primary one). The paired difference (a minus b) comes from one bootstrap over the supplied events in which both sets are recomputed from the same drawn rows (the de-duplicated set is the drawn rows that are not flagged); 1,000 resamples, seed 42. The point estimate for the 5-seed mean is the mean over seeds of each metric; each resample averages over seeds.

**Part 2: near-duplicates.** Windows are the firmware-style windows (trigger-aligned, 1.0 s before and 1.8 s after, 280 samples, clipped to the sensor range) of the triggered events. For each test event: the maximum Pearson correlation to any train or validation window (per-axis mean removed, the three axes concatenated, so the 1 g offset on one axis cannot make quiet windows look alike) and the minimum over train and validation windows of the maximum absolute difference (raw g, all axes, all samples). **Thresholds, fixed now: correlation above 0.999 and maximum absolute difference below 0.01 g.** A test event is a near-duplicate if one train or validation window meets both for the same pair. The maximum-difference search is exact for the 0.01 g question: every pair with a maximum difference below 0.01 g has an L2 distance below 0.01 sqrt(840) = 0.29, so all pairs within that L2 distance are checked. The exact-hash result (`leakage.*`) is not changed. Events not triggered have no window and are not scanned (their count is reported).

## S3. N20 re-run with a clean calibration set

**Step 1.** Count exact (raw-array hash) and near-duplicate (same rule as S2) events between the validation split and the training split and between the validation split and the test split.
**Step 2.** Clean calibration set: validation non-crash events with every exact-hash or near-duplicate match to a training event or to a test event removed. Split-conformal thresholds for alpha 1% and 5% from the clean set; the baseline is the validation-chosen threshold from the same clean set. Empirical false-alarm rate on the de-duplicated test set with intervals over seeds 42 and 0 to 4, calibration sizes 200, 500, 1000, 2000 and all (200 random draws per seed and size), and the share of runs above alpha.
**Step 3 (exploratory, defined now).** Size-stratified variant: the calibration negatives are re-weighted so that their vehicle-size mix matches the test negatives' mix (weighted conformal with weights w_c = share_test_c / share_cal_c; the threshold is the weighted (1 - alpha) quantile with the test point carrying the largest weight). Leave-one-category-out shift test repeated with the clean calibration set (calibration negatives from the other categories, and a variant that re-weights to the held-out category's size mix is not possible, so the weights use the pooled test mix; the Unknown category is reported separately).
**Decision rule, fixed now.** The guarantee "holds" if the upper end of the 95% interval for the mean test false-alarm rate is at or below alpha plus the sampling error of the test set, where the sampling error is the binomial standard error sqrt(alpha (1 - alpha) / n_test_negatives) (one standard error; the 95% bound is also printed). Either outcome is reported in full.

## S4. N14 and N13: representativeness and the remaining gap (defined 2026-11-11 before the run)

**Facts known before fixing the bins (descriptive counts only, no error was looked at):** the 176 tests have closing speeds from 32 to 66 km/h (143 of 176 at 55 km/h or more) and reference delta-V from 15 km/h upwards (93 at 60 km/h or more). The example bins in the task (below 30, 30 to 45, 45 to 60 km/h of impact speed) would have 0, 13 and 52 tests, so the bins are set on the reference delta-V instead.
**Bin edges, fixed now.** Primary: reference delta-V (km/h) < 30, 30 to 45, 45 to 60, >= 60. Secondary: closing speed (km/h) < 45, 45 to 60, >= 60. Binning on the reference delta-V conditions on the outcome (low bins tend to be over-estimated, high bins under-estimated), so the closing-speed bins are the less biased view; both are shown.
**Scores.** Split R (repeated grouped 5-fold cross-validation over make and model, 10 repeats, all 176 tests, each test scored only by models that did not see its make and model). Per bin: number of tests; the share of tests where the saturation test fires (final pulse family and level) at +-16, +-32 and +-64 g; the median absolute delta-V error for plain, spline, fill, fill + ridge and the M+ capped variant; a grouped (make and model) bootstrap 95% interval only for bins with 10 or more tests.
**Gap to the N13 target.** Shares within +-10% and +-20% at +-16 g, 100 Hz, for plain, spline, fill, fill + ridge (splits R and G), next to the 80% target.
**M+ capped (exploratory, one variant, defined now).** Same as fill + ridge, but the predicted log-correction is clipped to the 5th to 95th percentile of the realised log-correction log(reference / fill estimate) of the saturated tests of the tuning groups; fitted on the tuning groups only. Reported on all four splits (O, G, A, R) beside fill + ridge, with the paired difference and its interval, for the median, the 90th percentile and the shares within 10% and 20%. It is not the primary variant.
**Failure cases.** The ten worst tests after fill + ridge at +-16 g, 100 Hz (split R, mean error over repeats): make, model, test type, peak g, clipped share.
**Wording.** fill + ridge was named primary after earlier results were seen; NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes.

## S5. N16 and X6: burst scenario with sensitivity (defined 2026-11-11 before the run)

**Status of the burst scenario.** It was added to X6 after the N16 steady-state comparison against the severity table was a null result (critical delivery +0.006 [-0.000, +0.012]). It is therefore exploratory (`docs/07_log/DECISIONS.md`).
**Simulator.** `crashguard.capacity.simulate` (the X6 many-car simulator); the new options only add parameters, and with the defaults it reproduces the earlier runs exactly (checked).
**Defaults.** 100 cars, SF7, heartbeat every 600 s with a 16-byte payload, burst of 30 critical alerts within 10 s at t = 600 s on top of the Poisson background (0.1 alerts per car per hour, mix 40/30/20/10), 10% uplink and 10% downlink loss, capture rule "6 dB" (a packet survives an overlap if it is 6 dB above every overlapping packet), one simulated hour.
**Tuning bursts (8 combinations, seeds 1000, hours 0 to 2) and held-out bursts (the sweep below, seed 2000, hours 0 to 39) are disjoint in seeds and in parameter values.** Tuning combinations (cars, burst size, SF, loss): (75, 20, 7, 0.20), (75, 60, 9, 0.45), (150, 20, 9, 0.45), (150, 60, 7, 0.20), (75, 40, 12, 0.20), (150, 40, 12, 0.45), (120, 20, 7, 0.45), (120, 60, 9, 0.20).
**Tuned object.** The 24-combination grid of the N16 scheduler (reserve, spacing multiplier, jitter, spreading-factor raise). Objective fixed now: mean critical delivery over the tuning bursts; ties go to fewer features, then to lower node airtime. The chosen setting is called "scheduler (burst-tuned)"; the setting of the N16 steady-state study ("scheduler (N16)") is also scored. Both are scored once on the held-out bursts.
**Sweep (one factor at a time, the others at their defaults; 14 settings):** capture rule {6 dB, none (pure ALOHA)}; burst size {10, 30, 100}; cars {50, 100, 200}; heartbeat period {60, 600 s}; heartbeat payload {16, 48 bytes}; SF {7, 9, 12}; channel loss {10%, 30%, 60%} (both directions).
**Metrics.** Critical delivery (share of critical alerts ACKed), critical 95th-percentile latency (delivered alerts only; read with the delivery share), critical share ACKed within 30 s of the alert's creation. Differences scheduler minus severity table and scheduler minus fixed 3-try policy, paired by scenario seed, 95% bootstrap interval over the 40 seeds.
**Reading rule, fixed now.** A conclusion "holds across the sweep" if the interval has the same sign and excludes zero in at least 10 of the 14 settings; it "depends on an assumption" if it flips or loses significance when one factor changes, and the factor is named.

## S6. N19: separate the ensemble effect from the early exit (defined 2026-11-11 before the run)

**Why.** The earlier N19 result (early exit about 1.1 s earlier, recall +0.030 [0.021, 0.039] at the 1% target and +0.0037 [0.0005, 0.0068] at 5%, against the single 1,800 ms model) mixes two things: the sequential rule uses six length-specific forests (an ensemble), and it decides earlier.
**Arms, all at the same false-alarm target (1% and 5%, threshold or rule chosen on validation only), seeds 42 and 0 to 4, test set = the de-duplicated test split.**
- **F, single model at 1,800 ms:** the 1,800 ms forest and its validation threshold (the existing fixed-1800 arm).
- **A, the same single model scored at the early-exit time (isolates the early exit):** the 1,800 ms forest applied to the window truncated at each event's early-exit time (the time the sequential rule of E gives for that event, taken from the length grid 50, 100, 200, 400, 800, 1,800 ms); the threshold is chosen on validation with the same truncation rule (validation events truncated at their own early-exit times) for the same false-alarm target. This shows what cutting the window costs without length-specific models.
- **E, ensemble with early exit:** the existing rule (six length-specific forests, sequential exit).
- **E', ensemble without early exit (isolates the ensemble):** the same six forests and the same rule, but every decision is released at 1,800 ms. By construction its alarms equal those of E, so E' minus E in recall is exactly zero and the time difference is the whole early-exit saving; E' minus F is the ensemble (plus rule) effect at no time saving.
**Reported per target:** recall at the fixed false-alarm rate and the mean decision time of the triggered crash events for F, A, E and E'; paired differences A minus F, E' minus F (ensemble), E minus E' (early exit with the ensemble) with 95% bootstrap intervals (paired bootstrap of test events, 1,000 resamples; seed 42 and the mean of seeds 0 to 4).
**Wording rule.** N19 is re-worded around the part that clears its interval at both targets; a part that does not is stated as not shown.

## S9. M1: conformal intervals for clipped delta-V (N24) (defined 2026-11-11 before the run)

**Claim to test.** At +-16 g the point estimate of delta-V is often wrong, so the alert should carry a calibrated interval or an "at least this severe" statement.
**Method (grouped CV+).** Point estimate: fill + ridge (the N14 primary, named after earlier results were seen). Group = make and model. Outer split: the repeated grouped 5-fold cross-validation of split R (5 repeats here, seeds 42 + repeat), so every test is scored by models and calibration residuals that never saw its make and model. Inside each outer training set, an inner grouped 5-fold CV+ (Barber, Candes, Ramdas and Tibshirani, jackknife+ and CV+): for each inner fold k a model f_-k is fitted on the outer training groups without fold k (the pulse family, level, release fraction and ridge strength are re-chosen inside each fit); the out-of-fold relative residual of a calibration test i is r_i = |y_i - f_-k(i)(x_i)| / f_-k(i)(x_i) (the residual scale is the relative error); for a new test x the interval is [q_lo, q_hi] with q_lo the floor(alpha (n + 1))-th smallest of f_-k(i)(x) (1 - r_i) and q_hi the ceil((1 - alpha)(n + 1))-th smallest of f_-k(i)(x) (1 + r_i), n = number of calibration tests. Nominal coverage 80% and 90% (alpha 0.2 and 0.1). Why CV+ and not one split: with 176 tests (about 100 make and model groups) a separate calibration split would leave too few tuning tests for the ridge step; CV+ uses every test for both roles and its coverage guarantee is 1 - 2 alpha in the worst case (stated, not measured here). Ranges +-16, +-32 and +-64 g at 100 Hz.
**Evaluation (held-out groups only).** Empirical coverage of the reference delta-V with a grouped (make and model) bootstrap interval; median interval width (relative, and in km/h); the share of tests whose interval lies in one severity class (the class is the maximum of the delta-V class and the ASI class; the ASI of the filled window is the point value, not an interval).
**Severity decision rule.** k = class of the point estimate, k_lo = class of the lower bound. Report k if k_lo = k; otherwise report the class below k (at least 0) and set a flag "at least this severe, probably more". The final class is the maximum of the delta-V class and the ASI class. Compared with the point-estimate class: agreement with the reference class, under-estimation share, over-estimation share, share flagged.
**Decision rule, fixed now.** An improvement only if (i) the nominal coverage lies inside the 95% grouped bootstrap interval of the empirical coverage, and (ii) the under-estimation share of the decision-rule class is below that of the point-estimate class by an amount whose paired grouped bootstrap interval excludes zero. Either outcome is reported in full.

## S10. M2: prevalence-adaptive alert threshold and cancel-window cost model (N25) (defined 2026-11-11 before the run)

**Claim to test.** A threshold chosen on a data set with a crash share of about one in six gives very low precision at the prevalence of real driving, so the threshold should be set for the deployment prevalence and a cost model.
**Populations.** For prevalences 0.02%, 0.1%, 1% and 16% (of events that the device passes to the detector; VZCrash events were pre-selected on the device, so these are conditional numbers and the prevalence among all driving is lower still) a population of 1,000,000 events is drawn by resampling the de-duplicated test events: initial the test pool is bootstrapped (events drawn with replacement, which carries the finite-test-set error), then crashes (round(prevalence x 1,000,000)) and non-crashes (the rest) are drawn with replacement from the bootstrapped pool. 200 repeats. Events the trigger discards are in the pool with score -1 and are never alarms (system level). Models: the deployed 15-tree forest and the 10 x 9 candidate, seeds 0 to 4 (results are the mean over seeds within a repeat, intervals are 95% percentile intervals over repeats).
**Thresholds, all chosen on validation only, one per (model, seed) and rule.**
(a) the existing validation rule: the maximum-F1 threshold (also shown: the 1% and 5% false-alarm targets).
(b) prior-shift adjusted: the forest probabilities are calibrated on the triggered validation events by isotonic regression (prior pi_tr = crash share of those events), then adjusted for the deployment prior among triggered events, p' = a q / (a q + b (1 - q)), a = pi_dep / pi_tr, b = (1 - pi_dep) / (1 - pi_tr); an event alarms if p' >= 0.5 (equal costs). Two versions: pi_dep known (the expected crash share among triggered events of the population) and pi_dep estimated by the EM procedure of Saerens, Latinne and Decaestecker (2002) from the unlabeled triggered events of the drawn population.
(c) minimum expected cost: an event alarms if p' / (1 - p') >= C_false (1 - p_cancel) / C_miss, with a false alarm costing C_false only when the driver does not cancel in time (probability 1 - p_cancel). Base case: C_miss / C_false = 1,000 and p_cancel = 0.9 (our assumptions; there is no measured cost). Both pi_dep versions as in (b).
(d) target precision: the highest-recall validation threshold whose validation precision at the deployment prevalence (computed from validation recall and false-alarm rate) is at least 10% or 50%; "unreachable" if none exists.
**Reported per prevalence and rule:** system recall, precision (PPV), false alarms per 100,000 events, expected cost per 100,000 events in units of C_false (all with intervals over repeats), the PPV-recall curves (expected, from the test pool), and for (d) the recall given up against (a), or "cannot be reached".
**Sensitivity.** C_miss / C_false in {10, 100, 1,000, 10,000} and p_cancel in {0.5, 0.7, 0.9, 0.95} for rule (c) with known prevalence.
**Decision rule, fixed now.** Rule (b), (c) or (d) is an improvement over (a) at a prevalence only if the paired difference in PPV (rule minus (a), over repeats) has a 95% interval above zero AND recall is no more than 5 points lower. Reported in full either way.

## S13. Spaced-retry severity table as the baseline for SCT (defined 2026-11-11 before the run; chosen in `docs/06_references/NOVELTY_SCAN.md`)
**Why.** In the burst cells the N16 scheduler and the fixed 3-try policy both beat the severity table, and the burst tuning (S5) chose the scheduler with no reserve, no jitter, no spreading-factor raise and the longest spacing multiplier: the gain looks like retry spacing, not severity awareness. SCT (P2) therefore needs a baseline that has the severity table's tries and ordering but spaced retries.
**P1b.** The severity table (maximum tries 2, 4, 8 and 12, service by severity, cancel windows by class, point classes) with exponentially spaced retries: spacing multiplier 2, no jitter, no reserve, no spreading-factor raise (the S5 burst-tuned setting; it was tuned on S5 tuning bursts, not on the UA-SCT cells). It is the `scheduler` policy of `crashguard.scheduler` with those parameters.
**Held-out cells and seeds:** exactly those of `docs/02_preregistration/PREREGISTRATION.md` section 5 (3 ranges x 7 steady and 9 burst cells x 40 seeds), P1b paired by scenario seed with the stored P1 and P2 runs.
**Decision rule, fixed now.** SCT (P2) improves on the spaced-retry table if (i) in the burst cells the mean over cells of the paired difference in critical reach within 10 s (P2 minus P1b) has a 95% interval above zero at each range, and (ii) in the steady cells P2's reach within 10 s is not lower than P1b's by more than 2 points (lower end of the interval above -0.02). Otherwise the severity table with spaced retries is sufficient for that outcome. Reported either way, also for reach within 30 s and the critical 95th-percentile latency.
