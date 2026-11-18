"""Physics-based crash severity from one triggered IMU window: delta-V, ASI, THIV, pulse shape, rollover, class.

Input: ``acc_g`` (n, 3) in g with x forward, y left, z up (VZCrash / CrashGuard axes), ``gyro_dps`` (n, 3) in deg/s,
the sample rate and the trigger sample index. Every step is deterministic and has a plain-C twin in
``firmware_export/severity.h`` (see ``export_severity.py``). Sources, constants and UNVERIFIED marks: docs/05_data_code/SEVERITY.md.

This is crash severity (how hard the vehicle's velocity changed), not diagnosed injury.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import math

import numpy as np
from scipy.signal import butter, lfilter

from crashguard import config as C

G0 = C.G0


@dataclass(frozen=True)
class SeverityParams:
    """All thresholds in one place (defaults come from config.py)."""

    release_g: float = C.SEV_RELEASE_G
    release_ms: float = C.SEV_RELEASE_MS
    max_pulse_ms: float = C.SEV_MAX_PULSE_MS
    asi_filter_hz: float = C.ASI_FILTER_HZ
    asi_avg_ms: float = C.ASI_AVG_MS
    asi_ref_g: tuple = C.ASI_REF_G
    asi_limits: tuple = C.ASI_CLASS_LIMITS
    flail_x_m: float = C.FLAIL_X_M
    flail_y_m: float = C.FLAIL_Y_M
    rollover_deg: float = C.ROLLOVER_DEG
    release_frac: float = C.SEV_RELEASE_FRAC
    release_floor_g: float = C.SEV_RELEASE_FLOOR_G
    rollover_corrected: bool = C.SEV_ROLLOVER_CORRECTED
    rollover_in_class: bool = C.SEV_ROLLOVER_IN_CLASS
    dv_limits_kmh: tuple = C.SEV_DV_KMH
    names: tuple = field(default=C.SEV_NAMES)


DEFAULT = SeverityParams()


def remove_baseline(x: np.ndarray, trigger_idx: int) -> np.ndarray:
    """Gravity / orientation removal: subtract the mean of the samples before the trigger, per axis.

    Formula: a_lin[i] = a[i] - mean(a[0:trigger_idx]). With the sensor at rest before the crash, the mean equals gravity
    projected on the sensor axes, so this removes both gravity and a constant mounting tilt. It does NOT remove gravity
    leakage caused by rotation during the crash. Our design step (no standard); it is the usual EDR/IMU practice of
    zeroing the pre-crash offset.
    """
    pre = x[: max(int(trigger_idx), 1)]
    return x - pre.mean(axis=0)


def release_level(h_g: np.ndarray, start: int, fs: float, p: SeverityParams = DEFAULT) -> float:
    """Release level in g: ``release_g`` (absolute rule), or max(``release_floor_g``, ``release_frac`` * pulse peak) if ``release_frac`` > 0.

    The pulse peak is the largest horizontal acceleration between the trigger and the maximum pulse length. The window is already
    buffered, so the peak is known when the pulse end is searched. The fraction is tuned on the NHTSA tuning split (docs/07_log/DECISIONS.md).
    """
    if p.release_frac <= 0:
        return p.release_g
    cap = min(len(h_g) - 1, start + int(p.max_pulse_ms * fs / 1000.0))
    peak = float(h_g[start : cap + 1].max()) if cap >= start else 0.0
    return max(p.release_floor_g, p.release_frac * peak)


def pulse_end(h_g: np.ndarray, start: int, fs: float, p: SeverityParams = DEFAULT) -> int:
    """Index of the last sample of the crash pulse.

    The pulse starts at the trigger sample and ends at the first sample from which the horizontal acceleration
    h = sqrt(ax^2 + ay^2) stays below the release level (``release_level``) for ``release_ms``, or after ``max_pulse_ms``, or at the window end.
    Our design rule (docs/05_data_code/SEVERITY.md); the 250 ms cap follows NHTSA EDR studies (250 ms records 95% of pulses).
    """
    n = len(h_g)
    run = max(1, int(np.ceil(p.release_ms * fs / 1000.0 - 1e-9)))
    quiet = (h_g < release_level(h_g, start, fs, p)).astype(np.int64)
    if n - start >= run:
        hits = np.flatnonzero(np.convolve(quiet, np.ones(run, np.int64), "valid")[start:] == run)
        end = start + int(hits[0]) if len(hits) else n - 1
    else:
        end = n - 1
    return int(min(end, start + int(p.max_pulse_ms * fs / 1000.0), n - 1))


def trapz_total(y: np.ndarray, dt: float) -> np.ndarray:
    """Trapezoidal integral over all samples: dt * (sum(y) - (y[0] + y[-1]) / 2). Works on (m,) or (m, k) arrays."""
    if len(y) < 2:
        return np.zeros(y.shape[1:])
    return dt * (y.sum(axis=0) - 0.5 * (y[0] + y[-1]))


def trapz_cumulative(y: np.ndarray, dt: float) -> np.ndarray:
    """Running trapezoidal integral, same length as y, starting at 0."""
    out = np.zeros_like(y, dtype=np.float64)
    out[1:] = np.cumsum(0.5 * dt * (y[1:] + y[:-1]), axis=0)
    return out


def _filter_zero_phase(x: np.ndarray, fs: float, cutoff_hz: float) -> np.ndarray:
    """Forward-backward 2nd-order Butterworth = 4 poles, zero phase (EN 1317-2 ASI pre-filter, 13 Hz). Zero initial state, no padding."""
    b, a = butter(2, cutoff_hz / (fs / 2.0))
    y = lfilter(b, a, x, axis=0)
    return lfilter(b, a, y[::-1], axis=0)[::-1]


def asi(a_lin_g: np.ndarray, fs: float, p: SeverityParams = DEFAULT) -> float:
    """Acceleration Severity Index (EN 1317-2).

    ASI(t) = sqrt((ax_bar/12 g)^2 + (ay_bar/9 g)^2 + (az_bar/10 g)^2), ASI = max over t, where *_bar are 50 ms moving averages of the
    (13 Hz phase-less low-pass filtered) vehicle accelerations. Constants: Nasution et al. 2009 as quoted by Baltic J. Road Bridge
    Eng. 6(1) 2011 (12 g, 9 g, 10 g, 50 ms); the 13 Hz Butterworth is from a secondary snippet (UNVERIFIED). Here the moving
    average is causal (the last 50 ms) and runs over the whole window.
    """
    f = _filter_zero_phase(a_lin_g, fs, p.asi_filter_hz) if p.asi_filter_hz else a_lin_g
    n = max(1, int(p.asi_avg_ms * fs / 1000.0 + 0.5))
    c = np.vstack([np.zeros((1, 3)), np.cumsum(f, axis=0)])
    idx = np.arange(len(f))
    mavg = (c[idx + 1] - c[np.maximum(0, idx + 1 - n)]) / n
    ref = np.asarray(p.asi_ref_g, dtype=np.float64)
    return float(np.sqrt(((mavg / ref) ** 2).sum(axis=1)).max())


def asi_class(value: float, p: SeverityParams = DEFAULT) -> str:
    """EN 1317-2 impact severity level: A (<= 1.0), B (<= 1.4), C (<= 1.9), otherwise '>C' (not an EN level)."""
    for lim, name in zip(p.asi_limits, "ABC"):
        if value <= lim:
            return name
    return ">C"


def thiv(a_xy_ms2: np.ndarray, dt: float, p: SeverityParams = DEFAULT) -> tuple[float, bool]:
    """Theoretical Head Impact Velocity (EN 1317-2), flail-space model, in km/h.

    The head is a free particle. Relative to the vehicle its acceleration is -a_vehicle, so relative velocity v_r = -int a dt and
    relative position s = int v_r dt (trapezoidal, from the trigger). The head hits the interior when |s_x| >= flail_x or
    |s_y| >= flail_y; THIV = |v_r| at that moment. Concept: Baltic J. Road Bridge Eng. 6(1) 2011; flail distances 0.6 m and 0.3 m are
    UNVERIFIED; the standard's yaw-rotation term is NOT implemented. Returns (THIV, hit); (0.0, False) if the head never hits in the window.
    """
    v = -trapz_cumulative(a_xy_ms2, dt)
    s = trapz_cumulative(v, dt)
    hit = np.flatnonzero((np.abs(s[:, 0]) >= p.flail_x_m) | (np.abs(s[:, 1]) >= p.flail_y_m))
    if not len(hit):
        return 0.0, False
    i = int(hit[0])
    return float(np.hypot(v[i, 0], v[i, 1]) * 3.6), True


def rollover(gyro_dps: np.ndarray, trigger_idx: int, fs: float, p: SeverityParams = DEFAULT) -> tuple[float, float, bool]:
    """Integrated roll (about x) and pitch (about y) in degrees, and the rollover flag.

    angle(t) = int (g - g_pre) dt from the trigger, with the pre-trigger mean g_pre removed as a rate bias. Flag when the largest
    |roll| or |pitch| reaches ``rollover_deg`` (90 degrees: NASS-CDS / FARS definition of a rollover). The MPU range clips fast
    rotation (2000 deg/s), which makes the angle an underestimate.
    """
    g = remove_baseline(gyro_dps, trigger_idx)[int(trigger_idx):, :2]
    if len(g) < 2:
        return 0.0, 0.0, False
    ang = trapz_cumulative(g, 1.0 / fs)
    roll, pitch = float(np.abs(ang[:, 0]).max()), float(np.abs(ang[:, 1]).max())
    return roll, pitch, bool(max(roll, pitch) >= p.rollover_deg)


def tilt_trajectory(acc_g: np.ndarray, gyro_dps: np.ndarray, trigger_idx: int, fs: float) -> np.ndarray | None:
    """Tilt of the vehicle away from its pre-crash upright orientation, in degrees, from the trigger to the end of the window.

    The gravity direction is known in the sensor frame before the trigger (mean of the pre-trigger accelerometer samples, unit vector u0). It is carried through
    the crash by the gyro (rate bias removed with the pre-trigger mean): per sample the body turns by omega * dt, so a world-fixed vector turns by the opposite
    rotation in the sensor frame (Rodrigues). Tilt = angle between that vector and u0. A rotation about the vertical axis (a turn) does not change the tilt, so
    this does not depend on how the sensor is mounted. Returns None if the vehicle was not at rest before the trigger (mean |a| below 0.5 g). Our design.
    """
    acc_g = np.asarray(acc_g, dtype=np.float64)
    gyro_dps = np.asarray(gyro_dps, dtype=np.float64)
    t0 = int(trigger_idx)
    pre = acc_g[: max(t0, 1)].mean(axis=0)
    nb = math.sqrt(float(pre @ pre))
    if nb <= 0.5 or len(acc_g) - t0 < 2:
        return None
    u0 = (pre / nb).tolist()
    bias = gyro_dps[: max(t0, 1)].mean(axis=0).tolist()
    g = (gyro_dps[t0:] - np.asarray(bias)).tolist()
    dt = 1.0 / fs
    k = math.pi / 180.0
    u = list(u0)
    out = [0.0]
    for i in range(1, len(g)):
        ox, oy, oz = (0.5 * dt * (g[i][j] + g[i - 1][j]) * k for j in range(3))
        th = math.sqrt(ox * ox + oy * oy + oz * oz)
        if th > 0.0:
            nx, ny, nz = ox / th, oy / th, oz / th
            c, sn = math.cos(th), math.sin(th)
            cx, cy, cz = ny * u[2] - nz * u[1], nz * u[0] - nx * u[2], nx * u[1] - ny * u[0]  # n x u
            d = nx * u[0] + ny * u[1] + nz * u[2]
            u = [u[0] * c - cx * sn + nx * d * (1 - c), u[1] * c - cy * sn + ny * d * (1 - c), u[2] * c - cz * sn + nz * d * (1 - c)]
        out.append(math.degrees(math.acos(max(-1.0, min(1.0, u[0] * u0[0] + u[1] * u0[1] + u[2] * u0[2])))))
    return np.asarray(out)


def rollover_corrected(acc_g: np.ndarray, gyro_dps: np.ndarray, trigger_idx: int, fs: float,
                       p: SeverityParams = DEFAULT) -> tuple[float, float, bool, bool]:
    """Gravity-frame tilt and a drift-corrected rollover flag: (tilt_max_deg, tilt_corrected_max_deg, flag, correction_applied).

    ``tilt_max_deg`` is the largest tilt from ``tilt_trajectory``. The last ``ROLL_QUIET_S`` of the window is checked to be quiet (standard deviation of |a| and mean gyro
    deviation small). If so, the gravity vector there gives the measured net tilt; the part of the integrated final tilt that disagrees with it is gyro drift and is
    removed linearly in time from the trigger to the end of the window (a complementary use of gyro for the fast motion and gravity for the slow reference).
    The flag is raised when the corrected (or, without a quiet end, the uncorrected) maximum tilt reaches ``rollover_deg``. Without a usable gravity vector all
    values are 0 and the flag is False.
    """
    acc_g = np.asarray(acc_g, dtype=np.float64)
    gyro_dps = np.asarray(gyro_dps, dtype=np.float64)
    tl = tilt_trajectory(acc_g, gyro_dps, trigger_idx, fs)
    if tl is None:
        return 0.0, 0.0, False, False
    raw_max = float(tl.max())
    nq = max(2, int(round(C.ROLL_QUIET_S * fs)))
    seg_a, seg_g = acc_g[-nq:], gyro_dps[-nq:, :2]
    quiet = bool(len(tl) > nq and float(np.linalg.norm(seg_a, axis=1).std()) < C.ROLL_QUIET_STD_G
                 and float(np.abs(seg_g - seg_g.mean(axis=0)).mean()) < C.ROLL_QUIET_GYRO_DPS)
    corr_max = raw_max
    if quiet:
        pre = acc_g[: max(int(trigger_idx), 1)].mean(axis=0)
        u0 = pre / np.linalg.norm(pre)
        ue = seg_a.mean(axis=0)
        ue = ue / np.linalg.norm(ue)
        meas = math.degrees(math.acos(max(-1.0, min(1.0, float(u0 @ ue)))))
        drift = tl[-1] - meas
        corr_max = float(np.abs(tl - np.linspace(0.0, 1.0, len(tl)) * drift).max())
    return raw_max, corr_max, bool(corr_max >= p.rollover_deg), quiet


def classify(dv_kmh: float, asi_value: float, is_rollover: bool, p: SeverityParams = DEFAULT) -> int:
    """Severity class 0 Low, 1 Moderate, 2 Severe, 3 Critical.

    class = max(class from resultant delta-V, class from ASI); a rollover is always Critical.
    delta-V: Low < 24 km/h <= Moderate < 40 <= Severe < 56 <= Critical (limits in config; see docs/05_data_code/SEVERITY.md).
    ASI: <= 1.0 Low, <= 1.4 Moderate, <= 1.9 Severe, above Critical (EN 1317-2 levels A, B, C mapped by us).
    """
    if is_rollover and p.rollover_in_class:
        return 3
    c_dv = sum(dv_kmh >= lim for lim in p.dv_limits_kmh)
    c_asi = sum(asi_value > lim for lim in p.asi_limits)
    return int(max(c_dv, c_asi))


def severity(acc_g: np.ndarray, fs: float = C.FS_HZ, trigger_idx: int | None = None, gyro_dps: np.ndarray | None = None,
             p: SeverityParams = DEFAULT) -> dict:
    """All severity measures for one triggered window. Units are in the key names."""
    acc_g = np.asarray(acc_g, dtype=np.float64)
    if trigger_idx is None:
        trigger_idx = int(np.argmax(np.linalg.norm(acc_g, axis=1) > C.TRIGGER_G))
    dt = 1.0 / fs
    a_g = remove_baseline(acc_g, trigger_idx)
    a_ms2 = a_g * G0
    h = np.hypot(a_g[:, 0], a_g[:, 1])
    s0 = int(trigger_idx)
    e = pulse_end(h, s0, fs, p)
    if e > s0:
        dvx, dvy = trapz_total(a_ms2[s0 : e + 1, :2], dt)
    else:
        dvx = dvy = 0.0
    dv_res = float(np.hypot(dvx, dvy))
    pulse_s = (e - s0) * dt
    out = {
        "dvx_ms": float(dvx), "dvy_ms": float(dvy), "dv_res_ms": dv_res,
        "dvx_kmh": float(dvx * 3.6), "dvy_kmh": float(dvy * 3.6), "dv_res_kmh": dv_res * 3.6,
        "pulse_ms": pulse_s * 1000.0,
        "peak_pulse_g": float(h[s0 : e + 1].max()) if e > s0 else 0.0,
        "mean_pulse_g": dv_res / pulse_s / G0 if pulse_s > 0 else 0.0,
        "specific_energy_j_per_kg": 0.5 * dv_res**2,
    }
    out["asi"] = asi(a_g, fs, p)
    out["asi_class"] = asi_class(out["asi"], p)
    out["thiv_kmh"], out["thiv_hit"] = thiv(a_ms2[s0:, :2], dt, p)
    if gyro_dps is not None:
        gy = np.asarray(gyro_dps, dtype=np.float64)
        out["roll_deg"], out["pitch_deg"], out["rollover_raw"] = rollover(gy, s0, fs, p)
        out["tilt_deg"], out["tilt_corrected_deg"], out["rollover_corrected"], out["roll_corrected_applied"] = rollover_corrected(acc_g, gy, s0, fs, p)
        out["rollover"] = out["rollover_corrected"] if p.rollover_corrected else out["rollover_raw"]
    else:
        out["roll_deg"] = out["pitch_deg"] = out["tilt_deg"] = out["tilt_corrected_deg"] = float("nan")
        out["rollover"] = out["rollover_raw"] = out["rollover_corrected"] = out["roll_corrected_applied"] = False
    out["severity_class"] = classify(out["dv_res_kmh"], out["asi"], out["rollover"], p)
    out["severity_name"] = p.names[out["severity_class"]]
    return out
