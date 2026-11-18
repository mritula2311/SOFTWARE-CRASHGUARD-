"""N14: saturation-aware severity estimator (docs/02_preregistration/ALGORITHMS.md fixes the rules before any result).

When a crash pulse reaches the accelerometer range, plain delta-V from the clipped signal is biased low. This module fits a pulse model to the UNSATURATED samples of
the pulse with a deterministic grid search, and fills the saturated samples with the model value (keeping the direction), so the ordinary severity code then
integrates a repaired signal. Every step is a fixed loop over a small grid (9 pulse starts x 21 durations), so the same rule is written in C in ``severity.h``.

Pulse families: half-sine, haversine, triangle. The pulse is modelled on the horizontal resultant of the baseline-removed signal.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from crashguard import severity as S

FAMILIES = ("half_sine", "haversine", "triangle")
T0_OFFSETS = tuple(-1.0 + 0.25 * k for k in range(9))  # pulse start relative to the trigger sample, in samples
T_SCALES = tuple(0.6 + 0.05 * k for k in range(21))  # model duration as a multiple of the baseline pulse length
SAT_FRAC = 0.98  # default; the study chooses it on the tuning tests from SAT_FRACS (the 100 Hz sensor chain smooths the clipped plateau, so 0.98 misses most of it)
SAT_FRACS = (0.98, 0.9, 0.8, 0.7, 0.6, 0.5)
A_MAX_FACTOR = 12.0  # the fitted peak may not exceed this multiple of the range (a physical plausibility cap, our choice)
MIN_UNSAT = 3  # at least this many unsaturated pulse samples are needed to fit


def shape(family: str, u: np.ndarray) -> np.ndarray:
    """Pulse shape on u in [0, 1] (zero outside), peak value 1."""
    u = np.asarray(u, dtype=np.float64)
    inside = (u >= 0.0) & (u <= 1.0)
    uc = np.clip(u, 0.0, 1.0)
    if family == "half_sine":
        s = np.sin(np.pi * uc)
    elif family == "haversine":
        s = 0.5 * (1.0 - np.cos(2.0 * np.pi * uc))
    elif family == "triangle":
        s = 1.0 - np.abs(2.0 * uc - 1.0)
    else:
        raise ValueError(family)
    return np.where(inside, s, 0.0)


@dataclass
class Fit:
    saturated: bool
    n_sat: int = 0
    n_pulse: int = 0
    sat_share: float = 0.0
    amplitude_g: float = 0.0
    t0_samples: float = 0.0
    duration_s: float = 0.0
    cost: float = 0.0
    applied: bool = False


def fit_pulse(h: np.ndarray, start: int, end: int, sat: np.ndarray, fs: float, family: str, range_g: float) -> tuple[float, float, float, float] | None:
    """Grid search for (amplitude, t0 offset in samples, duration in s, cost) on the pulse samples start..end.

    ``h`` is the horizontal resultant of the baseline-removed signal, ``sat`` the boolean mask of saturated samples (same length). Returns None if the fit is not possible.
    """
    idx = np.arange(start, end + 1)
    is_sat = sat[idx]
    u_idx, s_idx = idx[~is_sat], idx[is_sat]
    if len(u_idx) < MIN_UNSAT or len(s_idx) == 0:
        return None
    hu, hs = h[u_idx], h[s_idx]
    pulse_len = max((end - start) / fs, 2.0 / fs)
    best = None
    for off in T0_OFFSETS:
        for sc in T_SCALES:
            T = sc * pulse_len
            su = shape(family, ((u_idx - start - off) / fs) / T)
            ss = shape(family, ((s_idx - start - off) / fs) / T)
            den = float((su * su).sum())
            if den <= 0.0:
                continue
            a = float((hu * su).sum() / den)
            pos = ss > 1e-3
            if pos.any():
                a = max(a, float((hs[pos] / ss[pos]).max()))
            a = min(a, A_MAX_FACTOR * range_g)
            cost = float(((hu - a * su) ** 2).sum() + (np.maximum(0.0, hs - a * ss) ** 2).sum())
            if best is None or cost < best[3] - 1e-12:
                best = (a, off, T, cost)
    return best


def fill(acc_g: np.ndarray, trigger_idx: int, fs: float, range_g: float, family: str = "half_sine", p: S.SeverityParams = S.DEFAULT,
         sat_frac: float | None = None) -> tuple[np.ndarray, Fit]:
    """Return (window with the saturated samples refilled, fit information). ``acc_g`` is the sensor reading in g (gravity included, x forward, y left).

    If no pulse sample is saturated, or the fit is not possible, the window is returned unchanged and ``applied`` is False.
    """
    acc_g = np.asarray(acc_g, dtype=np.float64)
    a = S.remove_baseline(acc_g, trigger_idx)
    h = np.hypot(a[:, 0], a[:, 1])
    s0 = int(trigger_idx)
    e = S.pulse_end(h, s0, fs, p)
    sf = SAT_FRAC if sat_frac is None else sat_frac
    sat = (np.abs(acc_g[:, 0]) >= sf * range_g) | (np.abs(acc_g[:, 1]) >= sf * range_g)
    sat_pulse = sat[s0 : e + 1]
    info = Fit(saturated=bool(sat_pulse.any()), n_sat=int(sat_pulse.sum()), n_pulse=int(e - s0 + 1), sat_share=float(sat_pulse.mean()) if e >= s0 else 0.0)
    if not info.saturated or e <= s0:
        return acc_g, info
    sat_full = np.zeros(len(acc_g), bool)
    sat_full[s0 : e + 1] = sat_pulse
    res = fit_pulse(h, s0, e, sat_full, fs, family, range_g)
    if res is None:
        return acc_g, info
    amp, off, T, cost = res
    info.amplitude_g, info.t0_samples, info.duration_s, info.cost, info.applied = amp, off, T, cost, True
    out = acc_g.copy()
    for i in np.flatnonzero(sat_full):
        target = max(h[i], amp * float(shape(family, np.array([((i - s0 - off) / fs) / T]))[0]))
        if h[i] > 0.0 and target > h[i]:
            out[i, :2] += (target / h[i] - 1.0) * a[i, :2]
    return out, info


def severity_filled(acc_g: np.ndarray, fs: float, trigger_idx: int, range_g: float, family: str = "half_sine", p: S.SeverityParams = S.DEFAULT,
                    sat_frac: float | None = None) -> tuple[dict, Fit]:
    """Severity of the refilled window (delta-V, ASI, class ...), and the fit information."""
    filled, info = fill(acc_g, trigger_idx, fs, range_g, family, p, sat_frac)
    return S.severity(filled, fs, trigger_idx, None, p), info


class RidgeCorrection:
    """Small regularised regression (M+): log(reference / M estimate) from [delta-V of the clipped signal (km/h), saturated share, pulse width (ms)].

    Trained on the TUNING tests only. Standardisation and the solution are closed form, so the same arithmetic is written in C with the coefficients in the header.
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.mu = np.zeros(3)
        self.sd = np.ones(3)
        self.w = np.zeros(3)
        self.b = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> RidgeCorrection:
        X = np.asarray(X, dtype=np.float64)
        self.mu = X.mean(axis=0)
        self.sd = X.std(axis=0)
        self.sd = np.where(self.sd > 1e-9, self.sd, 1.0)
        Z = (X - self.mu) / self.sd
        self.b = float(np.mean(y))
        yc = np.asarray(y, dtype=np.float64) - self.b
        self.w = np.linalg.solve(Z.T @ Z + self.alpha * np.eye(3), Z.T @ yc)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.b + ((np.asarray(X, dtype=np.float64) - self.mu) / self.sd) @ self.w

    def factor(self, X: np.ndarray) -> np.ndarray:
        """Multiplicative correction exp(prediction)."""
        return np.exp(self.predict(X))


def ridge_features(dv_clipped_kmh: float, sat_share: float, pulse_ms: float) -> np.ndarray:
    return np.array([dv_clipped_kmh, sat_share, pulse_ms], dtype=np.float64)


__all__ = ["FAMILIES", "Fit", "RidgeCorrection", "fill", "fit_pulse", "ridge_features", "severity_filled", "shape"]


def severity_sat(acc_g: np.ndarray, fs: float, trigger_idx: int, range_g: float, model: dict, p: S.SeverityParams = S.DEFAULT) -> dict:
    """Reference for ``cg_severity_sat`` in severity.h: baseline delta-V, filled delta-V, ridge-corrected delta-V, ASI of the filled window. ``model`` is one entry of
    ``data/processed/n14_model.json`` already reduced to the range: keys family, sat_frac, mu, sd, w, b."""
    base = S.severity(acc_g, fs, trigger_idx, None, p)
    r, info = severity_filled(acc_g, fs, trigger_idx, range_g, model["family"], p, model["sat_frac"])
    corrected = r["dv_res_kmh"]
    if info.applied:
        rc = RidgeCorrection()
        rc.mu, rc.sd, rc.w, rc.b = np.asarray(model["mu"]), np.asarray(model["sd"]), np.asarray(model["w"]), model["b"]
        corrected = r["dv_res_kmh"] * float(rc.factor(ridge_features(base["dv_res_kmh"], info.sat_share, base["pulse_ms"])[None, :])[0])
    return dict(dv_baseline_kmh=base["dv_res_kmh"], dv_fill_kmh=r["dv_res_kmh"], dv_fill_corrected_kmh=float(corrected), asi_fill=r["asi"], sat_share=info.sat_share,
                applied=int(info.applied), saturated=int(info.saturated))
