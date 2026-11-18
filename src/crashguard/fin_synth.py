"""Synthetic crash-pulse generator (block C; SIMULATED stress test, assumptions in docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md; never a substitute for real data).

Families: half-sine, triangle (peak at fraction a of the duration), multi-peak (2 or 3 half-sine bumps). Per crash mode the log peak, log duration (width at 10% of the peak) and logit asymmetry are drawn from a multivariate
normal fitted (mean and covariance only) to the real pulses of that mode; the direction is the unit vector of the real velocity change, drawn from the mode with 5 degrees of jitter; high-frequency noise has the fitted
relative level. Pulse k of a call with seed0 uses seed seed0 + k. Signals are in the format of the pooled NHTSA records (``t``, ``acc`` in g without gravity, ``fs0``) so that the same sensor chain and reference delta-V code apply.
"""
from __future__ import annotations

import numpy as np

from scipy.signal import butter, sosfiltfilt
from scipy.stats import norm, rankdata

from crashguard import nhtsa as N
from crashguard import severity_study as SS

FS0 = 10000.0
T_TOT, T_PRE = 0.6, 0.1
_trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy 2 renamed trapz to trapezoid; values are identical

MODES = ("frontal_barrier", "pole", "side", "other")
FAMILIES = ("halfsine", "triangle", "multipeak")
DESC = ("peak_g", "duration_ms", "dv_kmh", "asym", "shape")
_SOS = {}


def _lp(x: np.ndarray, fs: float, fc: float) -> np.ndarray:
    key = (fs, fc)
    if key not in _SOS:
        _SOS[key] = butter(4, fc, fs=fs, output="sos")
    return sosfiltfilt(_SOS[key], x, axis=0)


def descriptors(sig: dict, ref: float | None = None) -> dict | None:
    """Peak, duration (width at 10% of the peak), delta-V (the N13 reference), asymmetry, shape ratio, direction and relative noise of the 300 Hz-filtered horizontal resultant from the trigger."""
    acc, fs = np.asarray(sig["acc"], float), float(sig["fs0"])
    i0 = N.trigger_index(acc + np.array([0, 0, 1.0]), fs)
    if i0 is None:
        return None
    base = acc[: max(i0, 1), :2].mean(0)
    n = int(0.5 * fs)
    raw = acc[i0 : i0 + n, :2] - base
    f = _lp(acc[:, :2] - base, fs, 300.0)[i0 : i0 + n]
    a = np.linalg.norm(f, axis=1)
    pk = float(a.max())
    idx = np.flatnonzero(a >= 0.1 * pk)
    if pk <= 0 or len(idx) < 3:
        return None
    t0, t1 = idx[0], idx[-1]
    dur = (t1 - t0) / fs
    area = float(_trapz(a[t0 : t1 + 1], dx=1 / fs))
    v = f.sum(0)
    u = v / (np.linalg.norm(v) + 1e-12)
    resid = np.linalg.norm(raw[t0 : t1 + 1] - f[t0 : t1 + 1], axis=1)
    dv = float(ref) if ref is not None else SS.reference_dv(sig)[0]
    return dict(peak_g=pk, duration_ms=dur * 1e3, dv_kmh=dv, asym=float((int(np.argmax(a)) - t0) / max(t1 - t0, 1)), shape=area / (pk * dur + 1e-12), ux=float(u[0]), uy=float(u[1]), noise_rel=float(resid.std() / pk))


def fit(descs: list[dict], modes: list[str]) -> dict:
    """Per mode: a Gaussian copula (correlation of the normal scores) with the empirical 101-point quantile marginals of (log peak, log duration, logit asymmetry, log delta-V), the empirical unit vectors, the noise level (median and log-sd of the relative noise)."""
    out = {}
    for m in MODES:
        D = [d for d, mm in zip(descs, modes) if mm == m and d is not None]
        if len(D) < 5:
            continue
        a = np.clip([d["asym"] for d in D], 0.02, 0.98)
        X = np.column_stack([np.log([d["peak_g"] for d in D]), np.log([d["duration_ms"] for d in D]), np.log(a / (1 - a)), np.log([d["dv_kmh"] for d in D])])
        Z = norm.ppf((rankdata(X, axis=0) - 0.5) / len(X))  # normal scores: Gaussian copula with the empirical marginals
        nz = np.log(np.clip([d["noise_rel"] for d in D], 1e-4, None))
        out[m] = dict(n=len(D), q=np.quantile(X, np.linspace(0, 1, 101), axis=0).T.tolist(), corr=np.corrcoef(Z.T).tolist(), units=[[d["ux"], d["uy"]] for d in D], noise_mu=float(nz.mean()), noise_sd=float(nz.std()), calib=[0.0, 0.0, 0.0])
    return out


def _shape(fam: str, u: np.ndarray, a: float, rng: np.random.Generator) -> np.ndarray:
    """Pulse shape on u in [0, 1] with maximum 1."""
    if fam == "halfsine":
        return np.sin(np.pi * u)
    if fam == "triangle":
        return np.where(u < a, u / a, (1 - u) / (1 - a))
    k = int(rng.integers(2, 4))
    amp = rng.uniform(0.5, 1.0, k)
    c = (np.arange(k) + 0.5) / k
    w = 1.2 / k
    s = np.zeros_like(u)
    for j in range(k):
        x = (u - (c[j] - w / 2)) / w
        s += amp[j] * np.where((x > 0) & (x < 1), np.sin(np.pi * x), 0.0)
    return s / s.max()


_U = np.linspace(0.0, 1.0, 801)
_BETA = np.linspace(1.0, 0.0, 41)
_ETA = 0.105  # plateau level (share of the peak) of the low-fill component (assumption A-C6)
_OMEGA = 0.03


def _fill_power(base: np.ndarray, target: float, a: float = 0.3) -> tuple[np.ndarray, float]:
    """Blend of the family shape (weight beta) with a plateau of 0.105 of the peak plus a narrow spike at the asymmetry position (weight 1 - beta), beta chosen so that the area over (peak x width at 10%) matches the target (real pulses have ratios of 0.25 to 0.33,
    below the 0.5 to 0.64 of single smooth shapes). Returns the shape on the grid (maximum 1) and its width at 10% of the peak in units of the grid length."""
    spike = np.exp(-(((_U - a) / _OMEGA) ** 2))
    best = None
    for b in _BETA:
        s = b * base + (1 - b) * (_ETA + (1 - _ETA) * spike)
        s = s / s.max()
        idx = np.flatnonzero(s >= 0.1)
        if len(idx) < 3:
            continue
        w = (idx[-1] - idx[0]) / (len(_U) - 1)
        r = float(_trapz(s, _U)) / w
        if best is None or abs(r - target) < best[0]:
            best = (abs(r - target), s, w)
    return best[1], best[2]


def make_pulse(par: dict, mode: str, seed: int, ovr: dict | None = None) -> dict:
    """One synthetic record. ``ovr`` (assumption variants): shift (log-peak shift), dur_scale, rho_shift (correlation of log peak and log duration, added to the fitted), noise_scale, fam_p (family probabilities), pre_s."""
    ovr = ovr or {}
    rng = np.random.default_rng(seed)
    p = par[mode]
    R = np.array(p["corr"])
    if ovr.get("rho_shift"):
        R = R.copy()
        R[0, 1] = R[1, 0] = float(np.clip(R[0, 1] + ovr["rho_shift"], -0.95, 0.95))
    u = norm.cdf(rng.multivariate_normal(np.zeros(4), R))
    q = np.array(p["q"])
    z = np.array([np.interp(u[k] * 100.0, np.arange(101), q[k]) for k in range(4)])
    z[0] += p["calib"][0]
    z[1] += p["calib"][1]
    z[3] += p["calib"][2]
    peak, dur = float(np.exp(z[0] + ovr.get("shift", 0.0))), float(np.exp(z[1]) / 1e3 * ovr.get("dur_scale", 1.0))
    a = float(np.clip(1 / (1 + np.exp(-z[2])), 0.1, 0.9))
    rho = float(np.clip(np.exp(z[3] + ovr.get("shift", 0.0) * ovr.get("dv_follow", 1.0)) / (peak * dur * 35.304), 0.12, 0.62))  # shape ratio implied by the drawn delta-V (km/h per g s = 35.304)
    fam = FAMILIES[int(rng.choice(3, p=ovr.get("fam_p", (1 / 3, 1 / 3, 1 / 3))))]
    pre = ovr.get("pre_s", T_PRE)
    n = int(round((pre + 0.5) * FS0))
    t = np.arange(n) / FS0
    base = np.clip(_shape(fam, _U, a, rng), 0.0, None)
    gs, w10 = _fill_power(base, rho, a)
    T = dur / w10  # length of the unit interval so that the width at 10% of the peak equals the drawn duration
    u = (t - pre) / T
    sh = np.where((u >= 0) & (u <= 1), np.interp(np.clip(u, 0, 1), _U, gs), 0.0)
    un = np.array(p["units"][int(rng.integers(len(p["units"])))])
    th = np.arctan2(un[1], un[0]) + np.deg2rad(5.0) * rng.standard_normal()
    d = np.array([np.cos(th), np.sin(th)])
    noise_rel = float(np.exp(p["noise_mu"] + p["noise_sd"] * rng.standard_normal())) * ovr.get("noise_scale", 1.0)
    nz = _lp(rng.standard_normal((n, 2)), FS0, 1500.0)
    msk = sh > 0.1
    nz = nz / ((nz[msk].std() if msk.sum() > 5 else nz.std()) + 1e-12) * noise_rel * peak * msk[:, None]
    acc = np.zeros((n, 3))
    acc[:, :2] = sh[:, None] * peak * d[None, :] + nz + rng.normal(0, 0.002, (n, 2))
    acc[:, 2] = rng.normal(0, 0.002, n)
    return dict(t=t, acc=acc, fs0=FS0, attach="SYNTHETIC", channels="XYZ", peak_g=peak, peak_g_raw=float(np.abs(acc[:, :2]).max()), family=fam, mode=mode, seed=seed)


def calibrate(par: dict, n: int = 300, iters: int = 3, seed0: int = 900_000) -> dict:
    """Shift the log peak, log duration and log delta-V so that the MEASURED geometric medians of the generated pulses equal the real ones (the measured peak includes noise; the delta-V includes the tail below 10% of
    the peak). Pilot pulses use seeds seed0 + k, never the seeds of the published pulses. The total shifts are stored in ``calib``."""
    out = {m: dict(p, calib=[0.0, 0.0, 0.0]) for m, p in par.items()}
    for m, p in out.items():
        q = np.array(p["q"])
        tgt = np.exp(q[:, 50])[[0, 1, 3]]
        for _ in range(iters):
            S = [descriptors(make_pulse(out, m, seed0 + k)) for k in range(n)]
            S = [s for s in S if s]
            meas = np.array([np.exp(np.mean(np.log([s[k] for s in S]))) for k in ("peak_g", "duration_ms", "dv_kmh")])
            sh = np.log(tgt / meas)
            sh[2] = 0.0  # delta-V is not shifted: its fitted marginal is already near the measured one and a shift distorts its narrow upper tail (decided after a fidelity look, DECISIONS 2026-11-13)
            p["calib"] = [c0 + s for c0, s in zip(p["calib"], sh)]
    return out
