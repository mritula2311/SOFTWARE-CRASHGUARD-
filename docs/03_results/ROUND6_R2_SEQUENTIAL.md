# Round 6, R6-2: sequential early exit (H-R6-2a and H-R6-2b)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Round 6 sequential early-exit rule against the fixed rule: development log, frozen parameters, held-out result, code checks and limits. |
| Evidence labels used | NOT_RUN |
| Abbreviations | NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Keys `r6.r2.*` in `results/results.json`; code `src/crashguard/r6_seq.py`; design `docs/02_preregistration/PREREGISTRATION_V17.md` section 4.

## 1. Result in one paragraph

Neither hypothesis is supported. On the held-out half of the VZCrash test events the sequential rule decides 14.2 ms earlier on average than the fixed rule (95% interval 9.0 to 19.7 ms; the preregistered criterion is at least 200 ms), and it raises the share of provisional alarms that the full window withdraws by 12.6 points (95% interval 10.9 to 14.3 points; the criterion is at most 2 points). The 200 ms target could not be reached by arithmetic: the fixed rule's mean decision time among provisional crash alarms is 112 ms (median 50 ms, floor 50 ms), so the largest possible mean gain is 62 ms. The preregistration quoted 720 to 780 ms for this mean; that figure was wrong and is corrected in `docs/07_log/DECISIONS.md`. The hypotheses were kept as written.

## 2. Rule and data

- Rule: running LLR of the per-length forest scores at 50, 100, 200, 400 and 800 ms, from class-conditional score histograms fitted on the validation split (40 equal-count bins, add-0.5 smoothing). Upper threshold A sends the provisional frame; lower threshold B stops with no frame; an event not decided by 800 ms goes to the 1,800 ms decision unchanged. A and B were chosen on validation only, with the provisional false-alarm rate within 0.001 of the fixed rule's. The summed LLR treats the six scores as independent although they come from nested windows, so it is a score-combination rule tuned on validation, not a calibrated likelihood-ratio test.
- Reference: the fixed rule of `crashguard.early` (seed 42), unchanged.
- Held-out set: half 1 of the hash `r6|event id` of the de-duplicated test events (2,872 triggered events, 1,960 crash). These events were already scored in earlier rounds by other hypotheses (V17 section 2), so the half is held out for this question only.

## 3. Development log (validation only, four of five iterations)

| Iteration | Bins | Smoothing | Objective | A | B | Validation figure |
|---|---|---|---|---|---|---|
| 1 | 20 | 1.0 | mean time of own alarms | 1.75 | 0.00 | 110.3 ms |
| 2 | 10 | 1.0 | mean time of own alarms | 1.30 | 0.25 | 77.2 ms |
| 3 | 40 | 0.5 | mean time of own alarms | 1.10 | 0.25 | 74.5 ms |
| 4 | 40 | 0.5 | paired difference (H-R6-2a form) | 1.10 | 0.25 | 14.4 ms paired |

The fixed rule's mean over its own alarms is 112.1 ms on validation. The own-alarm means of iterations 1 to 3 fall mainly because the rule alarms fewer, earlier events, which a review of the code pointed out; iteration 4 uses the paired objective and gives the same pair. On validation the retraction share rises from 0.104 to 0.227. Iteration 4 was frozen by hash (`results/tables/r6_frozen.json`) and the held-out run was made once.

## 4. Held-out numbers

| Quantity | Fixed rule | Sequential rule |
|---|---|---|
| Triggered events with a provisional alarm (crash and non-crash) | 1,317 | 1,400 |
| Mean decision time, crash events with a provisional alarm | 112.4 ms | 77.2 ms |
| Median decision time (floor 50 ms; not tested) | 50 ms | 50 ms |
| Retraction share (provisional alarms withdrawn by the full window) | 0.124 | 0.249 |
| Provisional alarms on non-crash events (912 in the half) | 95 (0.104) | 114 (0.125) |
| Recall of crash events, final alarm | 0.663 | 0.656 |

Tested statistics (bootstrap over events, 2,000 resamples, seed 42, 1,079 crash events with a provisional alarm under both rules): mean time difference 14.2 ms, lower 95% limit 9.0 ms, criterion at least 200 ms, not met (p = 1.0). Retraction difference +0.126, upper 95% limit 0.143, criterion at most 0.02, not met (p = 1.0).

The held-out provisional false-alarm rate of the sequential rule (0.125) is higher than the fixed rule's (0.104), while the two were matched on validation. Part of the retraction rise therefore reflects extra alarms on non-crash events; the preregistered statistic is reported as defined. The recall of the two rules is about the same, so the sequential rule does not buy earlier decisions with fewer detected crashes, and it does not buy them with more either.

## 5. Reading

1. Under the stated assumptions the checkpoint design leaves little to gain: two thirds of provisional alarms of the fixed rule are already decided at 50 ms, the earliest checkpoint, so a sequential rule has only the later checkpoints to improve and cannot go below 50 ms.
2. The sequential rule trades a small time gain for roughly twice the retraction share. This is a regime boundary, not a defect of the code: the code passes 31 of 31 mutants and a known-answer test (the fixed rule's share decided at 50 ms reproduces the stored R3 figure within 0.01).
3. The NHTSA frontal-pulse timing check is NOT_RUN (cut order of V17 section 11).

## 6. Code checks (V17 section 1, rule 5)

- 29 tests in `tests/test_r6_seq.py`; 31 mutants in `scripts/r6_mutation.py` (`results/tables/r6_mutation_r2.csv`), all killed.
- Fresh-context review: findings on the selection objective, the development log content, leakage of test objects into development runs, the freeze file list and the weakness of some tests; all were applied before the freeze (DECISIONS.md, 2026-11-16), except two items left as stated limits: the held-out false-alarm match is reported but not forced, and a resample with no event alarming under both rules is counted as a failure in the p-value (with 1,079 such events per held-out half it never occurs).
