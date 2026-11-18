# Audit of the V4 preregistration addendum (A2)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Timing audit of the V4 preregistration addendum. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Written 2026-11-13 on branch `finish`. Sources: `git log` of `docs/02_preregistration/PREREGISTRATION_V4.md`, `results/tables/p_sealed_access.csv`, file modification times of the evaluation logs and tables, and the V4 tables. Nothing was re-scored for this audit; no tagged result is changed.

## Timeline (all +05:30, 2026-11-12)

| Event | Commit | Time |
|---|---|---|
| Preregistration v4 committed | `b566b9e` | 08:11:34 |
| Wording-only fix (forbidden word) | `2c742a43` | 08:11:49 |
| Freeze P4a (before any test scoring) | `1a3aff9` | 08:33:51 |
| **Earliest held-out scoring: P4a test split** (`scored_at` 08:34; sweep table written 08:37:21) | earliest committed in `35d97ef` | 08:38:56 |
| Freeze P4b and P4c | `7a42da3`, `ab6239f` | 08:39:03, 08:39:05 |
| Freeze P1 | `1d22511` | 08:39:42 |
| P4b scored (table and log last written 08:41:22) | earliest committed in `aa2f6bc` (the P4b fix `bf53a1e` is 08:39:31) | 08:41:22 (file time) |
| **Addendum 1 committed** | `fd1b95a` | **08:41:41** |
| **Initial scoring of the sealed NHTSA fold: P1** (table written 08:42:13) | `aa2f6bc` | 08:42:27 |
| P2, P3a and P3b scored | `0582cba` and later | 08:43 |
| P4c (initial run logged at `scored_at` 08:41; log last written 08:42:44) | `aa2f6bc` | see below |
| P4c repeated after a closure bug fix (logged deviation) | `840e293` | 08:53:58 |

What the timeline shows:
- The addendum is dated before the sealed NHTSA fold was scored (P1 to P3: all after 08:41:41), as it says.
- It is **not** dated before every held-out scoring. P4a (test split) was scored about seven minutes before it and P4b about 19 seconds before it. The addendum's own header says so ("P4a had been scored and P4b was being scored"; P4b had in fact just finished).
- P4c: `p_sealed_access.csv` records its initial scoring at minute resolution (08:41); its log was last written at 08:42:44, after the addendum commit. The records do not show whether the run started before or after 08:41:41. It is reported here as unresolved.

## Exact text of each resolved reading

Reading 1 (p-value margins):
> 1. **p-values.** The bootstrap p-value of a condition of the form "interval above zero" uses the margin 0 (share of resamples at or below 0 for a gain, at or above 0 for a reduction of under-triage). Where the criterion also names a point margin (0.03, 0.02, 0.20, 0.01 +alpha), that margin is checked on the point estimate; where the text of a hypothesis gives the margin for the p-value (H-P2 width clause 0.20, H-P3a retained p90 0.20, H-P4a 0.01, H-P4b 0.02, H-P4c alpha + 0.01 and 0.02) that margin is used.

Reading 5 (P4b set definitions):
> 5. **P4b.** `frames_full` returns the de-duplicated test events, so the de-duplicated set is the whole frame and the supplied (24,174-event) set is not scored. The initial run of the evaluation stopped before scoring because of a code error (`te.leaky` does not exist); see `results/tables/p_sealed_access.csv` and `docs/07_log/DECISIONS.md`.

Reading 6 (P4c set definitions):
> 6. **P4c.** In the leave-one-category-out evaluation V2 has no calibration data of the held-out group and falls back to the pooled V1 threshold, so V2 equals V1 there; the pooled supplied-test evaluation (secondary) is where V2 differs. V3 is scored in the leave-one-category-out evaluation only.

## Did any hypothesis threshold change?

No. The addendum says "None changes a hypothesis, metric, threshold or rule". A line-by-line comparison of the hypothesis paragraphs (H-P4b: +0.02, interval above zero; H-P4c: alpha + 0.01 and +0.02 over the trivial rule) between `b566b9e` and the addendum shows no edit to them. The only edits to text above the addendum are two single words changed by the wording-only fix (two words of the repository wording rule, changed to `leading` and `earliest`, commit `2c742a43`, logged); the addendum is an appended section.

## Verdicts under the stated reading and the stricter alternative reading (computed from the stored V4 tables)

| Hypothesis | Stated reading | Stricter alternative reading | Flips? |
|---|---|---|---|
| H-P4b | NOT SUPPORTED. Strict set, augmentation with merging: recall at the 1% target -0.0175 [-0.0219, -0.0132] (needed +0.02). | Every variant must reach +0.02 on both the strict and the de-duplicated set: no variant does (strict: merge +0.0038 [-0.0002, 0.0076], aug -0.0165; de-duplicated: merge +0.0030, aug -0.0129). NOT SUPPORTED. | No |
| H-P4c | NOT SUPPORTED. Leave-one-category-out: no variant gains 0.02 recall over the trivial rule at either target (gains from -0.1165 to -0.0001; V2 equals V1 here by the addendum's reading 6). | (a) False-alarm upper end must be at most alpha (no +0.01 slack): fails for V0 to V4 at 1% (upper ends 0.0115 to 0.0127); V5 meets it at both targets (0.0090, 0.0355) but loses 0.1165 and 0.1147 recall. (b) V2 scored on its own pooled supplied-test evaluation (where it differs from V1): at 1% gain +0.0123 [0.0053, 0.0194] (below 0.02), at 5% gain -0.0245. NOT SUPPORTED under both. | No |

**Plain statement: no verdict would flip under the alternative readings checked here.** The p-value readings (reading 1) affect only the Holm-adjusted p-values, and the one SUPPORTED hypothesis (H-P4a, raw p 0.001, Holm 0.007, AP-loss upper end 0.0036 against the 0.01 margin) does not depend on them.

Limits of this audit: the stricter readings are the ones named above; other readings could be defined, and a reading chosen after seeing results is EXPLORATORY. The P4c time ordering remains unresolved (see timeline).
