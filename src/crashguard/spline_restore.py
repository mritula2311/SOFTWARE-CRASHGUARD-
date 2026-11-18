"""Spline restoration of clipped acceleration: the N14 comparison baseline (docs/02_preregistration/ALGORITHMS.md, "N14 extension", fixed before the run).

Restores each clipped segment of the horizontal axes with a 5th-order spline (degree 4, as in the MATLAB ``spapi(5, ...)`` call reported by Chan et al. 2023,
Sensors 23(10) 4609, for the algorithm of Ruder et al.) through the 3 clean samples before and the 3 after the segment. The restored window goes through the same
severity code as every other method.
"""
from __future__ import annotations

import numpy as np
from scipy.interpolate import make_interp_spline

from crashguard import severity as S

N_SIDE = 3  # clean samples used on each side of a segment
ORDER = 5  # spline order (degree 4)
A_MAX_FACTOR = 12.0  # restored magnitude may not exceed this multiple of the range (same cap as the pulse-fit fill)


def aptknt(xs: np.ndarray, k: int = ORDER) -> np.ndarray:
    """Knots of an order-k spline through the sites ``xs`` as chosen by MATLAB's ``aptknt`` (used by ``spapi``): end sites repeated k times, interior knots are averages of k - 1 consecutive
    interior sites. For 6 sites and order 5 there is one interior knot, the mean of sites 2 to 5. Written out here so that the result does not depend on the SciPy version."""
    n = len(xs)
    interior = [float(np.mean(xs[j + 1 : j + k])) for j in range(n - k)]
    return np.array([xs[0]] * k + interior + [xs[-1]] * k, dtype=np.float64)


def runs(mask: np.ndarray, lo: int, hi: int) -> list[tuple[int, int]]:
    """Maximal runs of True in mask that start inside [lo, hi] (inclusive); a run may continue past hi."""
    out, i, n = [], lo, len(mask)
    while i <= min(hi, n - 1):
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def restore(acc_g: np.ndarray, trigger_idx: int, fs: float, range_g: float, level: float, p: S.SeverityParams = S.DEFAULT) -> tuple[np.ndarray, dict]:
    """Return (restored window, info). info: segments found, segments restored, segments skipped for fewer than 3 clean samples on a side."""
    acc_g = np.asarray(acc_g, dtype=np.float64)
    a = S.remove_baseline(acc_g, trigger_idx)
    h = np.hypot(a[:, 0], a[:, 1])
    e = S.pulse_end(h, int(trigger_idx), fs, p)
    out = acc_g.copy()
    found = done = skipped = 0
    for ax in (0, 1):
        sat = np.abs(acc_g[:, ax]) >= level * range_g
        for i0, i1 in runs(sat, int(trigger_idx), int(e)):
            found += 1
            left, right = list(range(i0 - N_SIDE, i0)), list(range(i1 + 1, i1 + 1 + N_SIDE))
            if left[0] < 0 or right[-1] >= len(acc_g) or sat[left].any() or sat[right].any():
                skipped += 1
                continue
            xs = np.array(left + right, dtype=np.float64)
            spl = make_interp_spline(xs, acc_g[left + right, ax], k=ORDER - 1, t=aptknt(xs))
            idx = np.arange(i0, i1 + 1)
            cand = spl(idx.astype(np.float64))
            meas = acc_g[idx, ax]
            ok = (np.sign(cand) == np.sign(meas)) & (np.abs(cand) > np.abs(meas))
            cand = np.clip(cand, -A_MAX_FACTOR * range_g, A_MAX_FACTOR * range_g)
            out[idx[ok], ax] = cand[ok]
            done += 1
    return out, dict(segments=found, restored=done, skipped=skipped)


def severity_restored(acc_g: np.ndarray, fs: float, trigger_idx: int, range_g: float, level: float, p: S.SeverityParams = S.DEFAULT) -> tuple[dict, dict]:
    w, info = restore(acc_g, trigger_idx, fs, range_g, level, p)
    return S.severity(w, fs, trigger_idx, None, p), info
