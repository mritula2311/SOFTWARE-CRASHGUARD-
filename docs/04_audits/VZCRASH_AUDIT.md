# VZCrash duplicate audit (independent re-derivation)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Independent re-derivation of the duplicate recordings across VZCrash splits. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | AP = average precision; GPS = Global Positioning System |
<!-- header:end -->

**What this is.** The VZCrash release has recordings that occur in more than one split. The earlier audit of this repository found them; this document records an independent recomputation from the raw supplied files, so that anyone with the dataset can check it. The dataset is not redistributed here: `results/paper/vz_audit_cross_split_groups.csv` holds identifiers and one-way hashes only (no samples). VZCrash is released under CC BY-NC 4.0 (author reply, 2026-11-12, recorded in `docs/07_log/DECISIONS.md`; the downloaded copy is Hugging Face revision 42e1482d005c0e545379d6cfa4939486c9fe4249); the dataset authors allow event identifiers or hashes to be cited in a paper.

## Matching rules and thresholds

1. **Exact array groups.** The SHA-256 hash of the event's accelerometer array (float32 values as stored, row-major, plus the sample count). Events with the same hash form a group. The same was done for the hash of the whole event (accelerometer, gyroscope and GPS speed): the groups are identical, so the copies are whole-event copies.
2. **Window-level near-duplicates (the T5 rule).** Events that pass the 2 g trigger get a 280-sample window (1.0 s before and 1.8 s after the earliest sample whose |a| exceeds 2 g, each axis clipped to +-16 g initial, edge-repeat padding); events whose raw |a| exceeds 16 g are dropped (2 test events). A test window is a near-duplicate if some train or validation window has correlation above 0.999 (per-axis mean removed, axes concatenated) AND maximum absolute difference below 0.01 g.

## Counts (recomputed; every stored value agrees)

- Supplied events: train 137,954, validation 27,175, test 24,174 (24,172 test events after the 16 g drop).
- Exact groups across splits: **217** groups (stored: 217; difference 0), holding 439 events: 426 crash, 2 near_miss, 11 normal_driving; per split: train 206, validation 115, test 118. Events whose array equals an earlier event: 437 (stored 437).
- Test events with an exact copy in train or validation: **118** (114 crash, 1 near_miss, 3 normal_driving), 0.5% of all test events.
- The primary (de-duplicated) test set of the headline removes 150 test events: the exact copies and, in addition, events whose 32-bin downsampled |a| is within 0.005 g of a train or validation event (the nearest-neighbour rule of the earlier audit; it was not re-derived here because its definition is not fully specified in the documents).
- Window level: **5,863** triggered test windows scanned against 37,893 train and validation windows; 18,309 test events never pass the trigger. **1,305** test windows meet both thresholds (stored 1,305, difference 0); 6 meet only the correlation threshold. The flagged event set equals the stored set (only recomputed: 0; only stored: 0). Every flagged window equals its train or validation window sample for sample (maximum difference exactly 0 for 1,305 of 1,305), so these are the same recording seen through the same window, although only 113 of those events are whole-array copies: the rest are the same crash exported with a different 16 s context.
- By class: crash 1,249 of 4,069 triggered crash windows; near_miss 18 of 280; normal_driving 38 of 1,514.

## V2: the two figures about duplicate test windows (a fifth, and about 5%)

Both figures are correct; they use different denominators, and neither is a share of exact copies. (a) **22.3%** (1,305 of 5,863): the share of TRIGGERED test windows that equal a train or validation window (about a fifth). (b) **5.0%** (24,022 to 22,830 test events): the events removed by the strict set, over ALL test events of the primary set, AFTER the 150 events that the primary rule already removed (about 5%). 5.4% of all supplied test events have a flagged window (before any removal). By class the share is very unequal: 29.6% of all crash test events have a flagged window, against 0.5% of near_miss and 0.2% of normal_driving events. The wording to use: 'about a fifth of the triggered test windows (and about 30% of the crash test events) have a window that is identical, sample for sample, to a train or validation window; over all test events the strict set removes about 5% beyond the primary rule.' The words 'identical train or validation window' are accurate for the window; they are not accurate for the whole 16 s event (only the exact-copy test events above are identical as events).
The earlier statement in the novelty summary that the headline was computed 'after removing 217 groups' was wrong: the primary set removes test events (the number above), not groups, and the train and validation copies stay; it is corrected in `crashguard.novelty`. No sentence with the words 'a fifth' was found in the tracked documents of this repository (searched `docs/`, `report/`, `README.md`); if such a sentence exists in an outside summary it should use the wording above.

## Vehicle identifiers

The release has no vehicle identifier, so vehicle-level separation cannot be checked. The only vehicle label is the vehicle size (Light, Medium, Heavy, Unknown). In 216 of 217 cross-split groups all events carry the same size label and in 1 the labels differ (Medium and Unknown); the class label is identical inside all 217 groups. Events of a group have close event ids: the spread between the largest and the smallest id of a group has a median of 4 and is at most 20,563 (the group file lists them). The groups therefore look like one recording exported under neighbouring ids, which the dataset authors can confirm; this audit does not claim it.

## V4: how the headline metrics move (`vz.v4.*`; 5-seed means, paired bootstrap over the supplied test events)

Sets: supplied; without test events with an exact array copy in train or validation; without those and without events whose window equals a train or validation window. Same training, thresholds (validation) and seeds; only the evaluated events differ.

| Model | Metric | Supplied | Exact copies removed | Difference (supplied minus exact) | Near-duplicates also removed | Difference (supplied minus near) |
|---|---|---|---|---|---|---|
| 15-tree forest (headline) | System recall (validation-F1 threshold) | 0.901 [0.892, 0.910] | 0.900 [0.891, 0.909] | +0.0006 [-0.0008, +0.0018] | 0.873 [0.861, 0.884] | +0.0280 [+0.0235, +0.0326] |
| 15-tree forest (headline) | Recall at the 1% false-alarm target | 0.631 [0.618, 0.645] | 0.627 [0.613, 0.641] | +0.0045 [+0.0024, +0.0067] | 0.558 [0.541, 0.576] | +0.0727 [+0.0641, +0.0809] |
| 15-tree forest (headline) | Recall at the 5% target | 0.935 [0.928, 0.942] | 0.934 [0.927, 0.941] | +0.0004 [-0.0006, +0.0014] | 0.914 [0.904, 0.923] | +0.0209 [+0.0171, +0.0248] |
| 15-tree forest (headline) | AP (triggered events) | 0.934 [0.927, 0.940] | 0.931 [0.924, 0.939] | +0.0023 [+0.0018, +0.0029] | 0.892 [0.881, 0.904] | +0.0415 [+0.0358, +0.0471] |
| 15-tree forest (headline) | System AP | 0.906 [0.898, 0.915] | 0.904 [0.895, 0.912] | +0.0026 [+0.0017, +0.0035] | 0.854 [0.842, 0.867] | +0.0525 [+0.0463, +0.0583] |
| 10-tree depth-9 forest | System recall (validation-F1 threshold) | 0.898 [0.888, 0.906] | 0.897 [0.887, 0.905] | +0.0011 [-0.0001, +0.0022] | 0.865 [0.853, 0.876] | +0.0324 [+0.0281, +0.0370] |
| 10-tree depth-9 forest | Recall at the 1% false-alarm target | 0.660 [0.647, 0.673] | 0.655 [0.642, 0.668] | +0.0047 [+0.0029, +0.0066] | 0.585 [0.568, 0.601] | +0.0747 [+0.0664, +0.0824] |
| 10-tree depth-9 forest | Recall at the 5% target | 0.940 [0.933, 0.946] | 0.939 [0.932, 0.946] | +0.0008 [-0.0001, +0.0016] | 0.919 [0.910, 0.928] | +0.0205 [+0.0171, +0.0241] |
| 10-tree depth-9 forest | AP (triggered events) | 0.941 [0.935, 0.948] | 0.939 [0.933, 0.945] | +0.0023 [+0.0018, +0.0028] | 0.903 [0.893, 0.913] | +0.0386 [+0.0333, +0.0437] |
| 10-tree depth-9 forest | System AP | 0.914 [0.906, 0.922] | 0.911 [0.903, 0.919] | +0.0025 [+0.0016, +0.0034] | 0.864 [0.853, 0.876] | +0.0498 [+0.0442, +0.0554] |

Events: supplied 24,172 (4,221 crash), exact-copy removal 24,054, near-duplicate removal 22,862 (2,969 crash). Reading: removing exact copies changes the headline by under a point; removing the window-level duplicates lowers recall by about three points and recall at the 1% target by about seven (the duplicates are mostly crashes, so a model that has seen the crash scores it well). The primary test set of this repository stays the de-duplicated one; the strict set is the sensitivity analysis.

## How to reproduce

```
python -m crashguard.vz_audit      # V1: recompute from data/raw/data/*.parquet (about 2 minutes); writes vz.v1.* and results/tables/vz_audit_*.csv
python -m crashguard.vz_leakage    # V4: three test sets, two forests, five seeds
python -m crashguard.vz_docs       # this document and results/paper/vz_audit_cross_split_groups.csv
```

Files: `results/tables/vz_audit_comparison.csv` (recomputed against stored, every row), `results/tables/vz_audit_cross_split_groups.csv` (group hash, event ids with split, classes, sizes), `results/tables/vz_audit_test_near_dup_flags.csv` and `vz_audit_test_exact_copy_ids.csv` (test event ids only). Every number above is read from `results/results.json` by `vz_docs.py`.
