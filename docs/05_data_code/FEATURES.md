# Window features (14)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | The 14 window features: definitions and firmware details. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | SF = spreading factor (LoRa) |
<!-- header:end -->

Window: about 2.8 s at 100 Hz around the trigger. |a| = √(ax²+ay²+az²) in g. "SF" marks a candidate **scale-free** feature, meaning it does not depend on absolute g level.

| # | Name | Definition | SF |
|---|---|---|---|
| 1 | peak_a | max \|a\| | |
| 2 | peak_ax | max \|ax\| | |
| 3 | peak_ay | max \|ay\| | |
| 4 | peak_az | max \|az\| | |
| 5 | rms_a | RMS of \|a\| − 1 g | |
| 6 | jerk_peak | max \|d\|a\|/dt\| | |
| 7 | energy | Σ(\|a\|−1)² · dt | |
| 8 | dur_above | time with \|a\| > 2 g (ms) | |
| 9 | peak_ratio_xy | peak_ax / (peak_ay + ε) | SF |
| 10 | horiz_share | peak horizontal / peak_a | SF |
| 11 | kurtosis_a | kurtosis of \|a\| | SF |
| 12 | crest | peak_a / rms_a | SF |
| 13 | post_quiet | std of \|a\| in the last 0.8 s ÷ std of the whole window | SF |
| 14 | gyro_peak | max \|ω\| (rad/s, or as the dataset provides) | |

Claude Code may refine these definitions, but it must record every change here and in DECISIONS.md. The C export expects features in this exact order.

## Impact direction (firmware rule, not a trained model)
- Uses the opening 60 ms after the trigger.
- Computes the angle as atan2 of the horizontal impulse.
- Classes are FRONT, REAR, LEFT, RIGHT and VERTICAL.
- Evaluated only on hardware data (E1).

## Implementation details (src/crashguard/features.py, fixed 2026-11-10)
- |a| is computed after clipping each axis to +-MPU_RANGE_G. Windows have 280 samples (1.0 s before, 1.8 s after the trigger sample) with edge-repeat padding.
- `rms_a` = sqrt(mean((|a| - 1)^2)); `jerk_peak` = max |difference of |a|| / 0.01 s, in g/s; `energy` = sum((|a| - 1)^2) * 0.01 s; `dur_above` uses a fixed 2 g, in ms.
- `peak_ratio_xy` = peak_ax / (peak_ay + 0.001); `horiz_share` = peak of sqrt(ax^2 + ay^2) / peak_a; `crest` = peak_a / (rms_a + 0.001).
- `kurtosis_a` is excess kurtosis (normal = 0), with a 1e-12 guard; `post_quiet` = std of the last 0.8 s of |a| / (std of the window + 1e-6).
- `gyro_peak` = max of the gyro vector norm, converted from deg/s to rad/s (gyro clipped to +-2000 deg/s initial).
- Feature subsets: `scale_free` = features 9 to 13; `no_gyro` = features 1 to 13.
