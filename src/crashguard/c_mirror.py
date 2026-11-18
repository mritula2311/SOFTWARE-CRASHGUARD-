"""Pure-Python mirrors of the C code, written step by step in single precision (float32) in the same order of arithmetic as the C source.

They exist because the compiled C check can be blocked by Windows Application Control (``cbuild.py``). They are independent of the Python reference code
(``severity.py``, scikit-learn): the forest mirror reads the generated header text, the severity mirror follows the generated ``severity.h`` line by line.
Differences against the double-precision references come only from single against double arithmetic and from the platform's cosf/sinf/acosf.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from scipy.signal import butter

from crashguard import config as C

f32 = np.float32


# ---------------------------------------------------------------- forest
def parse_header(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    def arr(name: str, conv):
        m = re.search(rf"{name}\[[^\]]*\]\s*=\s*\{{([^}}]*)\}}", text)
        return [conv(x.strip().rstrip("f")) for x in m.group(1).split(",")]

    return dict(feat=arr("cg_feat", int), thr=np.array(arr("cg_thr", float), dtype=np.float32), left=arr("cg_left", int), right=arr("cg_right", int), root=arr("cg_root", int))


def rf_mirror(path: Path, X: np.ndarray) -> np.ndarray:
    """predict_prob of the generated header: threshold compare in float32, leaf values summed tree by tree in float32, divided by the number of trees."""
    h = parse_header(path)
    feat, thr, left, right, root = h["feat"], h["thr"], h["left"], h["right"], h["root"]
    n_trees = f32(len(root))
    out = np.zeros(len(X), np.float32)
    for r in range(len(X)):
        x = X[r].astype(np.float32)
        acc = f32(0.0)
        for t in root:
            n = t
            while feat[n] >= 0:
                n = left[n] if x[feat[n]] <= thr[n] else right[n]
            acc = f32(acc + thr[n])
        out[r] = f32(acc / n_trees)
    return out


# ---------------------------------------------------------------- severity
def severity_mirror(acc: np.ndarray, gyro: np.ndarray, trig: int, fs: float = C.FS_HZ) -> dict:
    """cg_severity of firmware_export/severity.h for one window, in float32. acc, gyro: (n, 3)."""
    n = len(acc)
    fs32 = f32(fs)
    dt = f32(1.0) / fs32
    G0 = f32(C.G0)
    acc = acc.astype(np.float32)
    gyro = gyro.astype(np.float32)
    npre = trig if trig > 0 else 1
    base = []
    for k in range(3):
        s = f32(0.0)
        for i in range(npre):
            s = f32(s + acc[i, k])
        base.append(f32(s / f32(npre)))
    a = np.zeros((n, 3), np.float32)
    h = np.zeros(n, np.float32)
    for i in range(n):
        for k in range(3):
            a[i, k] = f32(acc[i, k] - base[k])
        h[i] = np.sqrt(f32(f32(a[i, 0] * a[i, 0]) + f32(a[i, 1] * a[i, 1])))
    run = int(np.ceil(f32(f32(f32(C.SEV_RELEASE_MS) * fs32) / f32(1000.0)) - f32(1e-9)))
    run = max(run, 1)
    end = n - 1
    level = f32(C.SEV_RELEASE_G)
    if f32(C.SEV_RELEASE_FRAC) > 0:
        hi = min(trig + int(f32(f32(f32(C.SEV_MAX_PULSE_MS) * fs32) / f32(1000.0))), n - 1)
        pk = f32(0.0)
        for i in range(trig, hi + 1):
            if h[i] > pk:
                pk = h[i]
        level = f32(f32(C.SEV_RELEASE_FRAC) * pk)
        if level < f32(C.SEV_RELEASE_FLOOR_G):
            level = f32(C.SEV_RELEASE_FLOOR_G)
    if n - trig >= run:
        for i in range(trig, n - run + 1):
            if all(h[i + j] < level for j in range(run)):
                end = i
                break
    cap = trig + int(f32(f32(f32(C.SEV_MAX_PULSE_MS) * fs32) / f32(1000.0)))
    end = min(end, cap, n - 1)
    dvx = dvy = peak = f32(0.0)
    if end > trig:
        sx = sy = f32(0.0)
        for i in range(trig, end + 1):
            sx = f32(sx + a[i, 0])
            sy = f32(sy + a[i, 1])
            if h[i] > peak:
                peak = h[i]
        sx = f32(sx - f32(f32(0.5) * f32(a[trig, 0] + a[end, 0])))
        sy = f32(sy - f32(f32(0.5) * f32(a[trig, 1] + a[end, 1])))
        dvx, dvy = f32(G0 * dt * sx), f32(G0 * dt * sy)
    dv_res = np.sqrt(f32(f32(dvx * dvx) + f32(dvy * dvy)))
    pulse_s = f32(f32(end - trig) * dt)
    out = dict(dvx_kmh=f32(dvx * f32(3.6)), dvy_kmh=f32(dvy * f32(3.6)), dv_res_kmh=f32(dv_res * f32(3.6)), pulse_ms=f32(pulse_s * f32(1000.0)), peak_pulse_g=peak,
               mean_pulse_g=f32(f32(dv_res / pulse_s) / G0) if pulse_s > 0 else f32(0.0))
    # ASI: zero-phase 2nd-order Butterworth, causal moving average, scaled by the reference accelerations
    b, aa = butter(2, C.ASI_FILTER_HZ / (fs / 2.0))
    B = [f32(x) for x in b]
    A = [f32(1.0), f32(aa[1]), f32(aa[2])]
    ft = np.zeros((3, n), np.float32)
    for k in range(3):
        z1 = z2 = f32(0.0)
        for i in range(n):
            x = a[i, k]
            y = f32(f32(B[0] * x) + z1)
            z1 = f32(f32(f32(B[1] * x) - f32(A[1] * y)) + z2)
            z2 = f32(f32(B[2] * x) - f32(A[2] * y))
            ft[k, i] = y
        z1 = z2 = f32(0.0)
        for i in range(n - 1, -1, -1):
            x = ft[k, i]
            y = f32(f32(B[0] * x) + z1)
            z1 = f32(f32(f32(B[1] * x) - f32(A[1] * y)) + z2)
            z2 = f32(f32(B[2] * x) - f32(A[2] * y))
            ft[k, i] = y
    navg = max(int(f32(f32(f32(C.ASI_AVG_MS) * fs32) / f32(1000.0)) + f32(0.5)), 1)
    asi = f32(0.0)
    s3 = [f32(0.0)] * 3
    refs = [f32(r) for r in C.ASI_REF_G]
    for i in range(n):
        for k in range(3):
            s3[k] = f32(s3[k] + ft[k, i])
            if i >= navg:
                s3[k] = f32(s3[k] - ft[k, i - navg])
        m = [f32(f32(f32(s3[k] / f32(navg)) / refs[k])) for k in range(3)]
        v = np.sqrt(f32(f32(f32(m[0] * m[0]) + f32(m[1] * m[1])) + f32(m[2] * m[2])))
        if v > asi:
            asi = v
    out["asi"] = asi
    # THIV
    vx = vy = sxp = syp = f32(0.0)
    out["thiv_kmh"], out["thiv_hit"] = f32(0.0), 0
    fx, fy = f32(C.FLAIL_X_M), f32(C.FLAIL_Y_M)
    for i in range(trig + 1, n):
        nvx = f32(vx - f32(f32(f32(f32(0.5) * dt) * G0) * f32(a[i, 0] + a[i - 1, 0])))
        nvy = f32(vy - f32(f32(f32(f32(0.5) * dt) * G0) * f32(a[i, 1] + a[i - 1, 1])))
        sxp = f32(sxp + f32(f32(f32(0.5) * dt) * f32(nvx + vx)))
        syp = f32(syp + f32(f32(f32(0.5) * dt) * f32(nvy + vy)))
        vx, vy = nvx, nvy
        if abs(sxp) >= fx or abs(syp) >= fy:
            out["thiv_kmh"] = f32(np.sqrt(f32(f32(vx * vx) + f32(vy * vy))) * f32(3.6))
            out["thiv_hit"] = 1
            break
    # rollover: raw integrated roll and pitch, then the gravity-frame tilt with the drift correction
    out["roll_deg"] = out["pitch_deg"] = f32(0.0)
    rollover = 0
    out["tilt_deg"] = out["tilt_corrected_deg"] = f32(0.0)
    out["roll_corrected_applied"] = 0
    if n - trig >= 2:
        gb = [f32(0.0)] * 3
        for i in range(npre):
            for k in range(3):
                gb[k] = f32(gb[k] + gyro[i, k])
        gb = [f32(x / f32(npre)) for x in gb]
        ang = [f32(0.0)] * 2
        mx = [f32(0.0)] * 2
        for i in range(trig + 1, n):
            for k in range(2):
                ang[k] = f32(ang[k] + f32(f32(f32(0.5) * dt) * f32(f32(gyro[i, k] - gb[k]) + f32(gyro[i - 1, k] - gb[k]))))
                if abs(ang[k]) > mx[k]:
                    mx[k] = f32(abs(ang[k]))
        out["roll_deg"], out["pitch_deg"] = mx[0], mx[1]
        rollover = int(mx[0] >= f32(C.ROLLOVER_DEG) or mx[1] >= f32(C.ROLLOVER_DEG))
        nb = np.sqrt(f32(f32(f32(base[0] * base[0]) + f32(base[1] * base[1])) + f32(base[2] * base[2])))
        if nb > f32(0.5):
            u0 = [f32(base[k] / nb) for k in range(3)]
            u = list(u0)
            m = n - trig
            tl = np.zeros(m, np.float32)
            raw_max = f32(0.0)
            rad = f32(0.017453292519943295)
            for i in range(1, m):
                om = [f32(f32(f32(f32(0.5) * dt) * f32(f32(gyro[trig + i, k] - gb[k]) + f32(gyro[trig + i - 1, k] - gb[k]))) * rad) for k in range(3)]
                th = np.sqrt(f32(f32(f32(om[0] * om[0]) + f32(om[1] * om[1])) + f32(om[2] * om[2])))
                if th > 0:
                    nx, ny, nz = f32(om[0] / th), f32(om[1] / th), f32(om[2] / th)
                    c, sn = np.cos(th), np.sin(th)
                    cx, cy, cz = f32(f32(ny * u[2]) - f32(nz * u[1])), f32(f32(nz * u[0]) - f32(nx * u[2])), f32(f32(nx * u[1]) - f32(ny * u[0]))
                    d = f32(f32(f32(nx * u[0]) + f32(ny * u[1])) + f32(nz * u[2]))
                    omc = f32(f32(1.0) - c)
                    u = [f32(f32(f32(u[0] * c) - f32(cx * sn)) + f32(f32(nx * d) * omc)), f32(f32(f32(u[1] * c) - f32(cy * sn)) + f32(f32(ny * d) * omc)),
                         f32(f32(f32(u[2] * c) - f32(cz * sn)) + f32(f32(nz * d) * omc))]
                dd = f32(f32(f32(u[0] * u0[0]) + f32(u[1] * u0[1])) + f32(u[2] * u0[2]))
                dd = f32(min(max(dd, f32(-1.0)), f32(1.0)))
                tl[i] = f32(np.arccos(dd) * f32(57.29577951308232))
                if tl[i] > raw_max:
                    raw_max = tl[i]
            out["tilt_deg"] = raw_max
            corr_max = raw_max
            nq = max(int(f32(f32(C.ROLL_QUIET_S) * fs32) + f32(0.5)), 2)
            if m > nq:
                mean_a = [f32(0.0)] * 3
                mg = [f32(0.0)] * 2
                mn = f32(0.0)
                for i in range(n - nq, n):
                    for k in range(3):
                        mean_a[k] = f32(mean_a[k] + acc[i, k])
                    mg[0], mg[1] = f32(mg[0] + gyro[i, 0]), f32(mg[1] + gyro[i, 1])
                    mn = f32(mn + np.sqrt(f32(f32(f32(acc[i, 0] * acc[i, 0]) + f32(acc[i, 1] * acc[i, 1])) + f32(acc[i, 2] * acc[i, 2]))))
                mean_a = [f32(x / f32(nq)) for x in mean_a]
                mg = [f32(x / f32(nq)) for x in mg]
                mn = f32(mn / f32(nq))
                var = gdev = f32(0.0)
                for i in range(n - nq, n):
                    mg_i = np.sqrt(f32(f32(f32(acc[i, 0] * acc[i, 0]) + f32(acc[i, 1] * acc[i, 1])) + f32(acc[i, 2] * acc[i, 2])))
                    var = f32(var + f32(f32(mg_i - mn) * f32(mg_i - mn)))
                    gdev = f32(gdev + f32(abs(f32(gyro[i, 0] - mg[0])) + abs(f32(gyro[i, 1] - mg[1]))))
                sd = np.sqrt(f32(var / f32(nq)))
                gdev = f32(gdev / f32(2 * nq))
                if sd < f32(C.ROLL_QUIET_STD_G) and gdev < f32(C.ROLL_QUIET_GYRO_DPS):
                    ne = np.sqrt(f32(f32(f32(mean_a[0] * mean_a[0]) + f32(mean_a[1] * mean_a[1])) + f32(mean_a[2] * mean_a[2])))
                    dd = f32(f32(f32(f32(mean_a[0] * u0[0]) + f32(mean_a[1] * u0[1])) + f32(mean_a[2] * u0[2])) / (ne if ne > 0 else f32(1.0)))
                    dd = f32(min(max(dd, f32(-1.0)), f32(1.0)))
                    meas = f32(np.arccos(dd) * f32(57.29577951308232))
                    drift = f32(tl[m - 1] - meas)
                    corr_max = f32(0.0)
                    for i in range(m):
                        v = abs(f32(tl[i] - f32(f32(f32(i) / f32(m - 1)) * drift)))
                        if v > corr_max:
                            corr_max = f32(v)
                    out["roll_corrected_applied"] = 1
            out["tilt_corrected_deg"] = corr_max
            if C.SEV_ROLLOVER_CORRECTED:
                rollover = int(corr_max >= f32(C.ROLLOVER_DEG))
        elif C.SEV_ROLLOVER_CORRECTED:
            rollover = 0
    out["rollover"] = rollover
    dvk = out["dv_res_kmh"]
    if rollover and C.SEV_ROLLOVER_IN_CLASS:
        cls = 3
    else:
        c_dv = sum(dvk >= f32(x) for x in C.SEV_DV_KMH)
        c_asi = sum(asi > f32(x) for x in C.ASI_CLASS_LIMITS)
        cls = max(c_dv, c_asi)
    out["severity_class"] = int(cls)
    return {k: float(v) for k, v in out.items()}


# ---------------------------------------------------------------- N14 saturation-aware delta-V
def _shape_f32(family: int, u: np.float32) -> np.float32:
    if u < 0 or u > 1:
        return f32(0.0)
    if family == 0:
        return f32(np.sin(f32(f32(3.14159265358979) * u)))
    if family == 1:
        return f32(f32(0.5) * f32(f32(1.0) - np.cos(f32(f32(6.28318530717959) * u))))
    return f32(f32(1.0) - abs(f32(f32(2.0) * u - f32(1.0))))


def sat_mirror(acc: np.ndarray, trig: int, fs: float, model: dict, range_g: float, family: int) -> dict:
    """cg_severity_sat of severity.h for one window in float32 (fit loops in the same order as the C code). ``model`` is one entry of n14_model.json for the range."""
    from crashguard import saturation as SAT

    acc = acc.astype(np.float32)
    n = len(acc)
    fs32 = f32(fs)
    gyro = np.zeros((n, 3), np.float32)
    base_r = severity_mirror(acc, gyro, trig, fs)
    npre = trig if trig > 0 else 1
    bm = []
    for k in range(3):
        s = f32(0.0)
        for i in range(npre):
            s = f32(s + acc[i, k])
        bm.append(f32(s / f32(npre)))
    a = np.zeros((n, 2), np.float32)
    h = np.zeros(n, np.float32)
    for i in range(n):
        a[i, 0], a[i, 1] = f32(acc[i, 0] - bm[0]), f32(acc[i, 1] - bm[1])
        h[i] = np.sqrt(f32(f32(a[i, 0] * a[i, 0]) + f32(a[i, 1] * a[i, 1])))
    # pulse end, as in cg_severity
    run = max(int(np.ceil(f32(f32(f32(C.SEV_RELEASE_MS) * fs32) / f32(1000.0)) - f32(1e-9))), 1)
    level = f32(C.SEV_RELEASE_G)
    if f32(C.SEV_RELEASE_FRAC) > 0:
        hi = min(trig + int(f32(f32(f32(C.SEV_MAX_PULSE_MS) * fs32) / f32(1000.0))), n - 1)
        pk = f32(max(h[trig:hi + 1])) if hi >= trig else f32(0.0)
        level = max(f32(f32(C.SEV_RELEASE_FRAC) * pk), f32(C.SEV_RELEASE_FLOOR_G))
    end = n - 1
    if n - trig >= run:
        for i in range(trig, n - run + 1):
            if all(h[i + j] < level for j in range(run)):
                end = i
                break
    end = min(end, trig + int(f32(f32(f32(C.SEV_MAX_PULSE_MS) * fs32) / f32(1000.0))), n - 1)
    sf = f32(model["sat_frac"])
    rg = f32(range_g)
    sat = np.zeros(n, bool)
    nsat = 0
    for i in range(trig, end + 1):
        sat[i] = bool(abs(acc[i, 0]) >= f32(sf * rg) or abs(acc[i, 1]) >= f32(sf * rg))
        nsat += int(sat[i])
    n_pulse = end - trig + 1
    sat_share = f32(f32(nsat) / f32(n_pulse)) if end >= trig else f32(0.0)
    out = acc.copy()
    applied = 0
    if nsat > 0 and end > trig and n_pulse - nsat >= 3:
        pulse_len = max(f32(f32(end - trig) / fs32), f32(f32(2.0) / fs32))
        best = None
        for oi in range(9):
            off = f32(f32(-1.0) + f32(f32(0.25) * f32(oi)))
            for si in range(21):
                T = f32(f32(f32(0.6) + f32(f32(0.05) * f32(si))) * pulse_len)
                den = num = f32(0.0)
                amax_sat = f32(-1.0)
                for i in range(trig, end + 1):
                    if not sat[i]:
                        su = _shape_f32(family, f32(f32(f32(f32(i - trig) - off) / fs32) / T))
                        den = f32(den + f32(su * su))
                        num = f32(num + f32(h[i] * su))
                if not den > 0:
                    continue
                amp = f32(num / den)
                for i in range(trig, end + 1):
                    if sat[i]:
                        ss = _shape_f32(family, f32(f32(f32(f32(i - trig) - off) / fs32) / T))
                        if ss > f32(1e-3):
                            r = f32(h[i] / ss)
                            if r > amax_sat:
                                amax_sat = r
                if amax_sat > amp:
                    amp = amax_sat
                amp = min(amp, f32(f32(SAT.A_MAX_FACTOR) * rg))
                cost = f32(0.0)
                for i in range(trig, end + 1):
                    m = f32(amp * _shape_f32(family, f32(f32(f32(f32(i - trig) - off) / fs32) / T)))
                    if (not sat[i]) or h[i] > m:
                        d = f32(h[i] - m)
                        cost = f32(cost + f32(d * d))
                if best is None or cost < f32(best[0] - f32(1e-12)):
                    best = (cost, amp, off, T)
        if best is not None:
            applied = 1
            _c, amp, off, T = best
            for i in range(trig, end + 1):
                if sat[i]:
                    target = f32(amp * _shape_f32(family, f32(f32(f32(f32(i - trig) - off) / fs32) / T)))
                    if target < h[i]:
                        target = h[i]
                    if h[i] > 0 and target > h[i]:
                        kf = f32(f32(target / h[i]) - f32(1.0))
                        out[i, 0] = f32(out[i, 0] + f32(kf * a[i, 0]))
                        out[i, 1] = f32(out[i, 1] + f32(kf * a[i, 1]))
    fill_r = severity_mirror(out, gyro, trig, fs)
    corrected = f32(fill_r["dv_res_kmh"])
    if applied:
        x = [f32(base_r["dv_res_kmh"]), sat_share, f32(base_r["pulse_ms"])]
        z = f32(model["b"])
        for k in range(3):
            z = f32(z + f32(f32(f32(x[k] - f32(model["mu"][k])) / f32(model["sd"][k])) * f32(model["w"][k])))
        corrected = f32(f32(fill_r["dv_res_kmh"]) * np.exp(z))
    return dict(dv_baseline_kmh=base_r["dv_res_kmh"], dv_fill_kmh=fill_r["dv_res_kmh"], dv_fill_corrected_kmh=float(corrected), asi_fill=fill_r["asi"], sat_share=float(sat_share), applied=applied,
                saturated=int(nsat > 0))
