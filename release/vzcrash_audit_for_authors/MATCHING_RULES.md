# VZCrash duplicate audit: matching rules, counts and commands

Prepared for the VZCrash authors by Mritula S (2026-11-13). This folder agrees with the audit package the author already sent by email on 2026-11-12; nothing is resent from here. It holds identifiers, split and class labels, vehicle-size labels and one-way SHA-256 hashes only. **It holds no raw signal values.**

Data: VZCrash, Hugging Face `vzc-research-chapter/VZCrash`, revision `42e1482d005c0e545379d6cfa4939486c9fe4249`. Released by its authors under CC BY-NC 4.0 (author reply, 2026-11-12). This folder is a VZCrash-derived artefact and is released under CC BY-NC 4.0 with attribution to Bianconcini et al., arXiv 2606.06074.

**Identifiers.** Every record in the release has an `event_id` (int64). All identifiers in `affected_events.csv` are the `event_id` values as they appear in the dataset. No affected record lacks one, so hashes are not needed to name events; `groups_with_array_hashes.csv` additionally gives the group hash. The release has no vehicle identifier.

## Rules

**R1, identical-array group.** For each event, the SHA-256 hash of the accelerometer array as stored (float32 values, row-major, plus the sample count). Events with the same hash form a group. The same was done with the hash of the whole event (accelerometer, gyroscope and GPS speed): the groups are the same, so the repeats are whole-event copies. A group is "cross-split" if it holds events from more than one of train, validation and test. **R1b:** a test event whose array hash equals that of a train or validation event.

**R2, primary de-duplication rule of the earlier audit (test events only).** A test event is removed if R1b holds, or if the L-infinity distance between its 32-bin downsampled |a| vector and that of some train or validation event is below 0.005 g. (Quiet driving can match this rule by chance near 1 g, so R2 events are all normal-driving events in this release.)

**R3, window-level near-duplicate (test windows only).** Events that cross the 2 g trigger get a 280-sample window: 1.0 s before and 1.8 s after the earliest sample whose |a| exceeds 2 g, each axis clipped to +-16 g beforehand, edge-repeat padding. Events whose raw |a| exceeds 16 g are dropped before this (2 test events). A test window is flagged if some train or validation window has Pearson correlation above 0.999 (per-axis mean removed, the three axes concatenated) AND maximum absolute difference below 0.01 g. In this release every flagged window equals its train or validation window sample for sample (maximum difference exactly 0 in 1,305 of 1,305).

**Events and windows.** An event is one record (one `event_id`). A window is the 280-sample trigger-aligned segment above. 18,309 test events never cross the trigger and have no window.

## Counts

| Item | Count |
|---|---|
| Supplied events: train / validation / test | 137,954 / 27,175 / 24,174 (24,172 test events after the 16 g drop) |
| Cross-split identical-array groups (R1) | **217** groups, **439** events (426 crash, 2 near_miss, 11 normal_driving); per split: train 206, validation 115, test 118 |
| Test events with an identical array in train or validation (R1b) | **118** (114 crash, 1 near_miss, 3 normal_driving) |
| Primary de-duplicated test set (R2 removes 150 of 24,172) | **24,022** events |
| Strict test set (R3 flags also removed) | **22,830** events: 24,022 to 22,830 is 1,192 further events (1,138 crash) |
| R3 flagged windows | **1,305 of 5,863** triggered test windows (crash 1,249 of 4,069; near_miss 18 of 280; normal_driving 38 of 1,514) |

Per rule, split and class: `counts_per_rule_split_class.csv`. Per event: `affected_events.csv` (columns: event_id, group_id, split, class, vehiclesize, rule; an event can appear under more than one rule). `group_id` is the group number of `vzcrash_duplicate_groups.csv` of the repository; `groups_with_array_hashes.csv` lists the group hashes and event ids.

## Reproduce

Needs the dataset at the revision above in `data/raw/data/*.parquet` (not included). From the repository root, with `PYTHONPATH=src`:

```
python -m crashguard.vz_audit     # R1 and R3 from the raw files (about 2 minutes); results/tables/vz_audit_*.csv
python -m crashguard.features     # events_meta (hashes, 32-bin vectors, labels)
python -m crashguard.split        # R2 (leaky_test_events)
python -m crashguard.s2_dedup     # window-level flags used in the headline comparisons
python -m crashguard.fin_a4       # writes this folder from the tables above
```
