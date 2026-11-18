"""Single place for firmware-style trigger and window settings.

TRIGGER_G and MPU_RANGE_G are PLACEHOLDERS until the author confirms them from firmware v2
(see docs/07_log/DECISIONS.md). Change them here only.
"""
from __future__ import annotations

from pathlib import Path

SEED = 42
SEEDS = (0, 1, 2, 3, 4)

# Trigger and window (firmware style)
TRIGGER_G = 2.0  # |a| above this starts a window. Placeholder, to be confirmed from firmware v2
TRIGGER_SWEEP_G = (1.5, 2.0, 2.5, 3.0)
PRE_S = 1.0  # seconds kept before the trigger sample
POST_S = 1.8  # seconds kept after the trigger sample
MPU_RANGE_G = 16.0  # accelerometer full scale. Placeholder, to be confirmed from firmware v2
MPU_GYRO_RANGE_DPS = 2000.0  # MPU6050 maximum gyro full scale. Assumption, not from the dataset

FS_HZ = 100
DT = 1.0 / FS_HZ
PRE_N = round(PRE_S * FS_HZ)
POST_N = round(POST_S * FS_HZ)
WIN_N = PRE_N + POST_N  # 280 samples = 2.8 s
DEG2RAD = 3.141592653589793 / 180.0

FEATURES = (
    "peak_a", "peak_ax", "peak_ay", "peak_az", "rms_a", "jerk_peak", "energy",
    "dur_above", "peak_ratio_xy", "horiz_share", "kurtosis_a", "crest", "post_quiet", "gyro_peak",
)
SCALE_FREE = ("peak_ratio_xy", "horiz_share", "kurtosis_a", "crest", "post_quiet")
NO_GYRO = tuple(f for f in FEATURES if f != "gyro_peak")
FEATURE_SETS = {"all": FEATURES, "no_gyro": NO_GYRO, "scale_free": SCALE_FREE}

APP_PARTITION_BYTES = 1_310_720  # default Arduino-ESP32 app partition (1.25 MiB) on a 4 MB flash. ASSUMPTION: check the real partition table
COMFORT_FRACTION = 0.05  # "fits comfortably" = estimated forest size at most this share of the app partition
AP_TOLERANCE = 0.002  # recommend the smallest Pareto configuration within this AP of the best one in the sweep
NODE_BYTES = 9  # exported tree node: int8 feature + float32 threshold/leaf value + int16 left + int16 right

RAW_DIR = Path("data/raw")
PROCESSED = Path("data/processed")
TABLES = Path("results/tables")
FIGURES = Path("results/figures")

# ---- Physics-based severity (src/crashguard/severity.py, docs/05_data_code/SEVERITY.md) ----
# Every value is configurable. Sources and UNVERIFIED marks are in docs/05_data_code/SEVERITY.md.
G0 = 9.80665  # standard gravity, m/s^2
SEV_RELEASE_G = 0.5  # pulse ends when horizontal |a| stays below this (our design value, UNVERIFIED as a standard)
SEV_RELEASE_MS = 50.0  # ... for this long (our design value)
SEV_MAX_PULSE_MS = 250.0  # cap on pulse length; NHTSA EDR work: 250 ms records 95% of crash pulses
ASI_FILTER_HZ = 13.0  # UNVERIFIED: EN 1317-2 pre-filter, 4-pole phase-less Butterworth; seen only in search summaries, no source opened (docs/05_data_code/SEVERITY.md)
ASI_AVG_MS = 50.0  # EN 1317-2 moving-average interval
ASI_REF_G = (12.0, 9.0, 10.0)  # EN 1317-2 reference accelerations for x, y, z
ASI_CLASS_LIMITS = (1.0, 1.4, 1.9)  # EN 1317-2 levels A, B, C; 1.9 read in a secondary source (Acta Polytechnica CTU Proc. 39, 2022, table 1); the standard itself not opened
FLAIL_X_M, FLAIL_Y_M = 0.6, 0.3  # UNVERIFIED: THIV flail-space limits. One read source (Baltic J. Road Bridge Eng. 6(1), 2011) gives 0.8 m longitudinal, 0.3 m transversal. THIV is reported only, not used in the class
ROLLOVER_DEG = 90.0  # NASS-CDS / FARS rollover: rotation of 90 degrees or more about the longitudinal (or lateral) axis
SEV_DV_KMH = (24.0, 40.0, 56.0)  # class limits for resultant delta-V: Low < 24 <= Moderate < 40 <= Severe < 56 <= Critical
SEV_NAMES = ("Low", "Moderate", "Severe", "Critical")

# ---- Severity hardening (Phase 2, 2026-11-11). Values below are set by the tuning described in docs/07_log/DECISIONS.md ----
SEV_RELEASE_FRAC = 0.1  # SET 2026-11-11 from the tuning split (src/crashguard/severity_study.py, docs/07_log/DECISIONS.md); pulse ends when horizontal |a| stays below max(floor, frac * pulse peak); 0 means the absolute SEV_RELEASE_G rule. Tuned on the NHTSA tuning split only
SEV_RELEASE_FLOOR_G = 0.5  # lowest release level when a fraction of the peak is used (our design value)
ROLL_QUIET_S = 0.3  # drift-corrected rollover: the last this-many seconds of the window must be quiet to give a gravity vector
ROLL_QUIET_STD_G = 0.2  # ... standard deviation of |a| below this (g)
ROLL_QUIET_GYRO_DPS = 20.0  # ... mean absolute gyro rate below this (deg/s)
SEV_ROLLOVER_CORRECTED = True  # report the drift-corrected (gravity-frame tilt) rollover flag in severity(); set 2026-11-11
SEV_ROLLOVER_IN_CLASS = False  # a rollover flag makes the class Critical. SWITCHED OFF 2026-11-11: both rollover flags fire on more than 0.5% of VZCrash normal driving (docs/07_log/DECISIONS.md)
