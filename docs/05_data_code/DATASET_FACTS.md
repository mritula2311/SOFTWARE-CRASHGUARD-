# VZCrash facts

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | Counts and quality facts of VZCrash computed from the downloaded files. |
| Evidence labels used | MEASURED_SOFTWARE |
| Abbreviations | AP = average precision; GPS = Global Positioning System; PDF = Portable Document Format |
<!-- header:end -->

Status: **downloaded and profiled** (2026-11-10). All 16 parquet shards are in `data/raw/data/` (git-ignored). Counts and quality checks are CONFIRMED_FROM_DATA, computed by `make data` and listed in full in [DATASET_FACTS_QUALITY.md](DATASET_FACTS_QUALITY.md) and `results/results.json` (`vzcrash.*`, origin MEASURED_SOFTWARE). Other items are CONFIRMED_FROM_CARD (dataset card, read 2026-11-10).

| Item | docs/05_data_code/DATASET.md belief | Fact | Source | Matches? |
|---|---|---|---|---|
| Size | about 190,000 events, 31,090 crashes | 189,303 events; **31,079 crashes** (train 137,954 / validation 27,175 / test 24,174) | CONFIRMED_FROM_DATA | Yes (31,079, not 31,090) |
| Accelerometer | 100 Hz, g | 100 Hz, tri-axial, g. 188,887 events have exactly 1600 samples; 416 differ (1000 to 4100 samples) | CARD + DATA | Yes; 100 Hz is from the card, sample counts are measured |
| Axes | X forward, Y left, Z up | Same, 1 g at rest; card warns alignment is sometimes suboptimal. Median \|a\| of the events is about 1.02 g | CARD + DATA | Yes, with a caveat |
| Gyro | rad/s "or as dataset provides" | deg/s; 1 deg/s resolution (103,548 events) or 0.001 deg/s (85,755 events) | CARD + DATA | **Differs** |
| Labels | binary crash / non-crash | **three classes**: crash 31,079 (16.4%), near_miss 28,681 (15.1%), normal_driving 129,543 (68.4%). Paper uses near_miss as negative | CONFIRMED_FROM_DATA | **Differs** |
| Window | about 2.8 s around trigger | each event is about **16 s**. In crash events the peak \|a\| sits at sample 1003 (median; 5th to 95th percentile: 484 to 1314), so the crash is roughly 10 s into the window | CONFIRMED_FROM_DATA | **Differs** |
| GPS | not mentioned | 1 Hz speed, km/h, 14 to 17 samples per event | CARD + DATA | New |
| Vehicle / trip ID | needed | **none**; only `vehiclesize` (Light 27,615, Medium 67,937, Heavy 30,967, Unknown 62,784) | CONFIRMED_FROM_DATA | **Differs** |
| Splits | to be made by us | supplied train/validation/test; no event_id appears in two splits; the paper states vehicle-level separation but the release has no vehicle ID | CONFIRMED_FROM_DATA + PAPER | Cannot be verified; duplicates found across splits |
| Severity / direction labels | none | none | CONFIRMED_FROM_DATA | Yes |
| Licence | CC BY-NC 4.0 | CC BY-NC 4.0; cite Bianconcini et al., ITSC 2026 | CARD | Yes |
| Paper baseline (AP 97.56%) | stated | Table I of the paper lists it for its best deep model on full 16 s events | CONFIRMED_FROM_PAPER | Yes; not comparable with our 2.8 s post-trigger windows |

## Checked against the paper (arXiv 2606.06074, PDF read in full on 2026-11-10; CONFIRMED_FROM_PAPER)
- **Splits:** train 72%, validation 14%, test 14%, "strictly separated by vehicle" with stratified sampling at the vehicle level. This **contradicts our earlier note that grouping was unverified**: the paper claims vehicle-level separation. The release has no vehicle ID, so we still cannot check it, and the cross-split duplicates found by our audit (see DATASET_FACTS_QUALITY.md and results.json `leakage.*`) suggest the separation is not complete or that one recording is stored under several event IDs.
- **On-device triggers:** recordings "were triggered on-device based on multiple threshold heuristics" (high X-axis values for hard braking and acceleration, high XY-norm for shock events), then processed in the cloud. Every event, including normal_driving, was therefore already selected once by a trigger. Our trigger is a second one on top.
- **Counts:** the paper gives 31,090 verified crashes; the data we downloaded has 31,079 crash events (the difference is not explained).
- **Paper baselines** (full 16 s events, accelerometer only, server-side): Table I lists AP for a physical baseline and several deep models. Our windows are 2.8 s after a trigger, so the numbers measure different tasks and we do not compare them.
- **Not in the paper:** duplicate recordings, a near-miss-only false-positive rate, any microcontroller deployment. Direction and severity labels are listed as future work.

## Quality findings
- No missing values (NaN) and no constant accelerometer signals.
- No duplicated event_id.
- 416 events are not 1600 samples long; 6 events have gyro length different from accelerometer length.
- **Corrupt values:** 15 events have a peak |a| above 16 g (the largest is about 2.7 million g) and 15 have peak gyro above 2000 deg/s. Three events hit 32766 deg/s or more (looks like integer overflow). 120 events have a median |a| outside 0.5 to 2 g (bad calibration or axis alignment).
- Crash strength: median peak |a| in crash events is 4.2 g, and 1,209 crash events peak below 2 g. A rule detector on peak g alone will miss these.
- Class balance is similar in all three splits (crash 15.7% to 17.5%).

## Open decisions for M2
See DECISIONS.md: near_miss handling, trigger and window position, glitch filtering, and the split grouping.
