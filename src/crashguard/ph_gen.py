"""Physics-based synthetic crash pulses (block P, SIMULATED; docs/02_preregistration/PREREGISTRATION_V7.md section 1; assumptions P-1 onward in docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md).

Two generators with the same interface (``fit``, ``make_batch``, ``make_pulse``, ``MODES``):
- ``PH-A`` (``gen='a'``): lumped-parameter vehicle front. A crush element (Kelvin spring and damper, nonlinear stiffness: linear rise to a plateau, plateau with slight hardening, bottoming out beyond a crush
  limit) between two bodies of reduced-mass ratio kappa = mu / m_v; closing speed v0; unloading with restitution e (energy based); the struck-vehicle deceleration is the output. A damped modal response of the
  structure to the force jerk and a causal second-order mount low-pass are added.
- ``PH-B`` (``gen='b'``): structurally different alternative: exponentially saturating force law, a Maxwell relaxation of the viscous force (decaying spike), no crush limit, priors placed on the saturation
  level and the crush distance, three structural modes and a different mount filter.
Parameters are drawn per pulse from priors whose hyper-parameters are fitted to the TRAIN rows given to ``fit`` (the DEVELOPMENT fold for the frozen generator) by moment matching: closing speed, restitution and mass
ratio are measured from the rows (test speed and reference delta-V); the other hyper-parameters are found by Nelder-Mead on the mismatch of the moments of (log peak, log duration, log delta-V, asymmetry, shape ratio,
log noise level) and three correlations. Nothing from a validation or sealed record is read here.
Signals are in the format of the pooled NHTSA records (``t``, ``acc`` in g without gravity, ``fs0`` = 10 kHz) so the sensor chain and the reference delta-V of the earlier blocks apply unchanged.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

from scipy.optimize import minimize
from scipy.signal import butter, lfilter, sosfilt

from crashguard import config as C

FS0 = 10000.0
_trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy 2 renamed trapz to trapezoid; values are identical

DT = 1.0 / FS0
N0 = 1000  # contact starts at 0.1 s (same pre-trigger length as fin_synth)
N_MAX = 7000  # 0.7 s
MODES = ("frontal_barrier", "pole", "side", "other")
RIGID = {"frontal_barrier": True, "pole": True, "side": False, "other": False}
G0 = C.G0
# stated crush limits (assumption P-12): crush beyond this is physically excluded in the consistency check (m)
CRUSH_HARD_M = {"frontal_barrier": 0.9, "pole": 0.9, "side": 0.35, "other": 0.9}
VIB_A = dict(f=(45.0, 110.0, 260.0, 540.0, 1100.0), zeta=(0.04, 0.05, 0.06, 0.05, 0.04), w=(0.3, 0.5, 0.8, 1.0, 1.0), mount=(1200.0, 2200.0))
VIB_B = dict(f=(80.0, 400.0, 900.0), zeta=(0.05, 0.06, 0.05), w=(0.5, 1.0, 1.0), mount=(900.0, 1600.0))
HYPER = ("mu_ap", "sd_ap", "mu_x1", "sd_x1", "mu_xl", "sd_xl", "zeta", "mu_vib", "sd_vib", "rho_av", "mu_fc")
H_LO = np.array([np.log(0.5), 0.05, np.log(0.005), 0.05, np.log(0.08), 0.05, 0.03, np.log(0.02), 0.05, -0.9, np.log(25.0)])
H_HI = np.array([np.log(80.0), 1.2, np.log(0.4), 1.2, np.log(1.2), 1.2, 1.2, np.log(1.5), 1.2, 0.95, np.log(400.0)])
_MOUNT: dict = {}


def _mount_sos(fc: float):
    k = max(round(fc / 5.0) * 5.0, 5.0)
    if k not in _MOUNT:
        _MOUNT[k] = butter(2, k, fs=FS0, output="sos")
    return _MOUNT[k]


# ------------------------------------------------------------------ priors
def _draw(par: dict, n: int, rng: np.random.Generator, gen: str) -> dict:
    """Per-pulse physical parameters. ``par`` holds the hyper-parameters of one mode."""
    h = par["h"]
    Z = rng.standard_normal((n, 10))
    za = Z[:, 0]
    zv = h["rho_av"] * Z[:, 0] + np.sqrt(max(1 - h["rho_av"] ** 2, 1e-6)) * Z[:, 7]
    v0 = np.exp(par["mu_v"] + par["sd_v"] * zv) / 3.6  # m/s
    e = np.clip(par["e_mean"] + par["e_sd"] * Z[:, 5], 0.0, 0.6)
    kappa = np.ones(n) if par["rigid"] else np.clip(par["kappa_mean"] * np.exp(par["kappa_sd"] * Z[:, 6]), 0.2, 0.97)
    out = dict(v0=v0, e=e, kappa=kappa, ap=np.exp(h["mu_ap"] + h["sd_ap"] * za), x1=np.exp(h["mu_x1"] + h["sd_x1"] * Z[:, 1]), xl=np.exp(h["mu_xl"] + h["sd_xl"] * Z[:, 2]),
               zeta=np.clip(h["zeta"] * np.exp(0.3 * Z[:, 3]), 0.03, 1.5), vib=np.exp(h["mu_vib"] + h["sd_vib"] * Z[:, 4]), wj=np.exp(0.3 * rng.standard_normal((n, 5))),
               mount=rng.uniform(*(VIB_A if gen == "a" else VIB_B)["mount"], n), kb=rng.uniform(6.0, 14.0, n), hs=rng.uniform(0.2, 2.0, n), tau_m=rng.uniform(0.005, 0.03, n), fc=np.exp(h["mu_fc"] + 0.3 * rng.standard_normal(n)))
    ang = rng.choice(len(par["units"]), n)
    th = np.arctan2([par["units"][i][1] for i in ang], [par["units"][i][0] for i in ang]) + np.deg2rad(5.0) * rng.standard_normal(n)
    out["dir"] = np.stack([np.cos(th), np.sin(th)], 1)
    return out


# ------------------------------------------------------------------ dynamics
def _load_curve(z, ap, x1, xl, kb, gen, z0=None, hs=0.5):
    if gen == "a":
        base = np.where(z < x1, ap * z / x1, ap * (1.0 + hs * (z - x1) / xl))
        return base + ap * kb * np.clip(z - xl, 0.0, None) / x1
    return ap * (1.0 - np.exp(-z / z0))  # PH-B: exponentially saturating force law (acceleration units, g)


def simulate(p: dict, gen: str = "a") -> dict:
    """Integrate the contact for a batch (all arrays of length B). Returns the deceleration of the struck vehicle in g (B, N) and the diagnostics used by the consistency checks."""
    B = len(p["v0"])
    ap, x1, xl, kb, kap, e, zeta, v0, hs = (p[k] for k in ("ap", "x1", "xl", "kb", "kappa", "e", "zeta", "v0", "hs"))
    z0 = np.maximum(0.5 * kap * v0 ** 2 / np.maximum(ap * G0, 1e-9) * 0.25, 1e-3) if gen == "b" else None
    k1 = ap * G0 / (x1 if gen == "a" else z0)  # initial stiffness per vehicle mass (1/s^2)
    cdamp = 2.0 * zeta * np.sqrt(k1 * kap)
    a = np.zeros((B, N_MAX))
    z = np.zeros(B)
    u = v0.copy()
    phase = np.zeros(B, int)  # 0 loading, 1 unloading, 2 free
    zmax = np.zeros(B)
    Fmax = np.zeros(B)
    xperm = np.zeros(B)
    WL = np.zeros(B)  # loading energy per vehicle mass (J/kg)
    work = np.zeros(B)  # energy absorbed (force times relative displacement) per vehicle mass
    u_prev = u.copy()
    mono = np.ones(B, bool)
    umax_seen = v0.copy()
    for n in range(N0, N_MAX):
        t_rel = (n - N0) * DT
        ld, un = phase == 0, phase == 1
        f = _load_curve(z, ap, x1, xl, kb, gen, z0, hs)
        if gen == "a":
            av = f + cdamp * np.where(ld, u, 0.0) / G0
        else:
            av = f + cdamp * np.where(ld, u, 0.0) / G0 * np.exp(-t_rel / p["tau_m"])
        denom = np.maximum(zmax - xperm, 1e-9)
        a_un = Fmax * np.clip(z - xperm, 0.0, None) / denom
        av = np.where(un, a_un, av)
        av = np.where(phase == 2, 0.0, np.maximum(av, 0.0))
        a[:, n] = av
        zdd = -av * G0 / kap
        u_prev = u
        u = np.where(phase == 2, u, u + zdd * DT)
        z = np.where(phase == 2, z, z + u * DT)
        work += av * G0 * u * DT * (phase < 2)  # signed: the energy returned on unloading counts negative
        mono &= ~((phase < 2) & (u > u_prev + 1e-9))
        umax_seen = np.maximum(umax_seen, u)
        # transitions
        turn = ld & (u <= 0.0)
        if turn.any():
            zmax = np.where(turn, np.maximum(z, 1e-6), zmax)
            Fmax = np.where(turn, np.maximum(_load_curve(zmax, ap, x1, xl, kb, gen, z0, hs), 1e-6), Fmax)
            # loading energy by the closed form of the piecewise curve (per vehicle mass, J/kg), numerically on a 200-point grid
            zz = np.linspace(0.0, 1.0, 200)[None, :] * zmax[:, None]
            fl = _load_curve(zz, ap[:, None], x1[:, None], xl[:, None], kb[:, None], gen, None if z0 is None else z0[:, None], hs[:, None]) * G0
            WLn = _trapz(fl, zz, axis=1)
            WL = np.where(turn, WLn, WL)
            xperm = np.where(turn, np.clip(zmax - 2.0 * (e ** 2) * WL / np.maximum(Fmax * G0, 1e-9), 0.0, zmax * 0.995), xperm)
            phase = np.where(turn, 1, phase)
        sep = (phase == 1) & (z <= xperm + 1e-9)
        phase = np.where(sep, 2, phase)
        if n > N0 + 200 and (phase == 2).all():
            break
    return dict(a=a, zmax=zmax, u_end=u, work=work, mono=mono, umax=umax_seen, v0=v0, e=e, kappa=kap, ap=ap)


def _modes(p: dict, gen: str, a: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Damped modal response of the structure to the force jerk, scaled to the drawn relative level; plus the causal mount low-pass and a small sensor noise."""
    V = VIB_A if gen == "a" else VIB_B
    B, N = a.shape
    pk = np.maximum(a.max(1), 1e-6)
    x = np.diff(a, axis=1, prepend=0.0) / pk[:, None]
    af = np.empty_like(a)  # compartment response: causal second-order low-pass of the crush force (assumption P-10)
    for i in range(B):
        af[i] = sosfilt(_mount_sos(float(np.clip(p["fc"][i], 10.0, 500.0))), a[i])
    tot = np.zeros((B, N))
    for j, fj in enumerate(V["f"]):
        w = 2 * np.pi * fj
        r = np.exp(-V["zeta"][j] * w * DT)
        th = w * np.sqrt(1 - V["zeta"][j] ** 2) * DT
        y = lfilter([0.0, r * np.sin(th)], [1.0, -2 * r * np.cos(th), r * r], x, axis=1)
        tot += (V["w"][j] * p["wj"][:, j % 5])[:, None] * y
    # structural micro-events (assumption P-11): six resonators of 350 to 1800 Hz (damped sinusoids), each hit by 8 impulses at random instants of the pulse
    rat = np.zeros((B, N))
    for fr in np.exp(np.linspace(np.log(350.0), np.log(1800.0), 6)):
        w = 2 * np.pi * fr
        r = np.exp(-0.05 * w * DT)
        th = w * np.sqrt(1 - 0.05 ** 2) * DT
        X = np.zeros((B, N))
        for i in range(B):
            w_act = a[i] / max(a[i].sum(), 1e-9)
            idx = rng.choice(N, 8, p=w_act)
            np.add.at(X[i], idx, rng.lognormal(0.0, 0.5, 8))
        rat += lfilter([0.0, r * np.sin(th)], [1.0, -2 * r * np.cos(th), r * r], X, axis=1)
    live0 = a > 0.02 * pk[:, None]
    rm_m = np.sqrt((tot ** 2 * live0).sum(1) / np.maximum(live0.sum(1), 1))
    rm_r = np.sqrt((rat ** 2 * live0).sum(1) / np.maximum(live0.sum(1), 1))
    tot = 0.4 * tot / np.maximum(rm_m, 1e-9)[:, None] + 0.9 * rat / np.maximum(rm_r, 1e-9)[:, None]
    live = a > 0.02 * pk[:, None]
    rms = np.sqrt((tot ** 2 * live).sum(1) / np.maximum(live.sum(1), 1))
    vib = tot / np.maximum(rms, 1e-9)[:, None] * (p["vib"] * pk)[:, None]
    sig = af + vib
    out = np.empty_like(sig)
    for i in range(B):
        out[i] = sosfilt(_mount_sos(p["mount"][i]), sig[i])
    return out + rng.normal(0.0, 0.002, out.shape)


def make_batch(par: dict, mode: str, n: int, seed: int, gen: str | None = None, with_diag: bool = False):
    """``n`` synthetic records of ``mode``; pulse k uses the batch seed ``seed``. Returns a list of signal dicts (and the diagnostics of the batch when ``with_diag``)."""
    gen = gen or par.get("_gen_kind", "a")
    rng = np.random.default_rng(seed)
    pm = par[mode]
    p = _draw(pm, n, rng, gen)
    s = simulate(p, gen)
    a = _modes(p, gen, s["a"], rng)
    t = np.arange(N_MAX) / FS0
    sigs = []
    for i in range(n):
        acc = np.zeros((N_MAX, 3))
        acc[:, :2] = a[i][:, None] * p["dir"][i][None, :] + rng.normal(0.0, 0.002, (N_MAX, 2))
        acc[:, 2] = rng.normal(0.0, 0.002, N_MAX)
        sigs.append(dict(t=t, acc=acc, fs0=FS0, attach="SYNTHETIC", channels="XYZ", peak_g=float(a[i].max()), peak_g_raw=float(np.abs(acc[:, :2]).max()), family="physics_" + gen, mode=mode, seed=seed))
    if with_diag:
        return sigs, dict(p=p, s=s, clean=s["a"])
    return sigs


def make_pulse(par: dict, mode: str, seed: int, ovr: dict | None = None) -> dict:
    return make_batch(par, mode, 1, seed)[0]


# ------------------------------------------------------------------ fitting (moment matching on the TRAIN rows given)
def _measured(df, mode: str) -> dict:
    d = df[df["mode"] == mode]
    v = d["v"].to_numpy(float)
    ok = v > 5.0
    vv = np.where(ok, v, np.nan)
    vv = np.where(np.isnan(vv), np.nanmedian(vv), vv)
    ratio = d["ref"].to_numpy(float) / vv
    lv = np.log(vv)
    rigid = RIGID[mode]
    if rigid:
        e_mean, e_sd = float(np.clip(np.median(ratio) - 1.0, 0.0, 0.5)), float(np.clip(np.std(ratio), 0.02, 0.2))
        kappa_mean, kappa_sd = 1.0, 0.0
    else:
        e_mean, e_sd = 0.10, 0.05  # assumed (P-8)
        kappa_mean = float(np.clip(np.median(ratio) / (1 + e_mean), 0.25, 0.95))
        kappa_sd = float(np.clip(np.std(np.log(np.maximum(ratio, 1e-3))), 0.05, 0.6))
    units = d[["ux", "uy"]].to_numpy(float).tolist()
    return dict(rigid=rigid, mu_v=float(lv.mean()), sd_v=float(max(lv.std(), 0.02)), e_mean=e_mean, e_sd=e_sd, kappa_mean=kappa_mean, kappa_sd=kappa_sd, units=units, n=int(len(d)))


def _targets(d) -> np.ndarray:
    lp, ld, lv = np.log(d["peak_g"].to_numpy(float)), np.log(d["duration_ms"].to_numpy(float)), np.log(np.maximum(d["dv_kmh"].to_numpy(float), 1e-3))
    c = np.corrcoef(np.stack([lp, ld, lv]))
    return np.array([lp.mean(), lp.std(), ld.mean(), ld.std(), lv.mean(), lv.std(), d["asym"].mean(), d["shape"].mean(), np.log(np.maximum(d["noise_rel"].to_numpy(float), 1e-4)).mean(), c[0, 1], c[0, 2], c[1, 2]])


_SCALE = np.array([0.12, 0.10, 0.12, 0.10, 0.12, 0.10, 0.05, 0.03, 0.25, 0.15, 0.15, 0.15])


def _simulated_targets(par_mode: dict, gen: str, n: int, seed: int) -> np.ndarray | None:
    from crashguard import fin_synth as FSY

    sigs = make_batch({"m": par_mode}, "m", n, seed, gen)
    rows = [FSY.descriptors(s) for s in sigs]
    rows = [r for r in rows if r]
    if len(rows) < max(10, n // 3):
        return None
    import pandas as pd

    return _targets(pd.DataFrame(rows))


def _cost(x: np.ndarray, base: dict, tgt: np.ndarray, gen: str, n: int, seed: int) -> float:
    x = np.clip(x, H_LO, H_HI)
    pm = dict(base, h=dict(zip(HYPER, [float(v) for v in x])))
    s = _simulated_targets(pm, gen, n, seed)
    if s is None:
        return 1e3
    z = (s - tgt) / _SCALE
    return float(np.sum(z * z))


def _x0(d, gen: str) -> np.ndarray:
    pk = float(np.median(d["peak_g"]))
    return np.array([np.log(pk * (0.35 if gen == "a" else 0.5)), 0.4, np.log(0.04), 0.4, np.log(0.5), 0.4, 0.3, np.log(0.25), 0.4, 0.3, np.log(80.0)])


def fit_mode(df, mode: str, gen: str, n_sim: int = 100, maxiter: int = 150, seed: int = 11) -> dict:
    d = df[df["mode"] == mode]
    base = _measured(df, mode)
    tgt = _targets(d)
    r = minimize(_cost, _x0(d, gen), args=(base, tgt, gen, n_sim, seed), method="Nelder-Mead", options=dict(maxiter=maxiter, xatol=1e-2, fatol=1e-2, adaptive=True))
    x = np.clip(r.x, H_LO, H_HI)
    lx = np.log(np.maximum(d[["peak_g", "duration_ms", "dv_kmh"]].to_numpy(float), 1e-6))
    out = dict(base, h=dict(zip(HYPER, [float(v) for v in x])), fit_cost=float(r.fun), fit_evals=int(r.nfev), targets=tgt.tolist(),
               range_mu=lx.mean(0).tolist(), range_cov=(np.cov(lx.T) + 1e-9 * np.eye(3)).tolist())
    return out


def range_ok(par_mode: dict, d1: dict) -> bool:
    """Check (vi): peak, duration and delta-V inside the 99.5% chi-square ellipsoid of the TRAIN rows' log-descriptors."""
    from scipy.stats import chi2

    x = np.log(np.maximum([d1["peak_g"], d1["duration_ms"], d1["dv_kmh"]], 1e-6)) - np.array(par_mode["range_mu"])
    return bool(x @ np.linalg.inv(np.array(par_mode["range_cov"])) @ x <= chi2.ppf(0.995, 3))


def _fit_job(a):
    df, mode, gen, n_sim, maxiter = a
    return mode, fit_mode(df, mode, gen, n_sim, maxiter)


def fit(df, gen: str = "a", n_sim: int = 100, maxiter: int = 150, workers: int = 4) -> dict:
    """``df``: descriptor rows (columns of ``f_real_desc`` plus ``v`` and ``ref``) of the TRAIN rows only, one row per record, with a ``mode`` column. Returns the parameter dict (keys: modes, ``_gen_kind``)."""
    from concurrent.futures import ProcessPoolExecutor

    modes = [m for m in MODES if (df["mode"] == m).sum() >= 8]
    with ProcessPoolExecutor(min(workers, len(modes))) as ex:
        res = dict(ex.map(_fit_job, [(df, m, gen, n_sim, maxiter) for m in modes]))
    res["_gen_kind"] = gen
    return res


def params_hash(par: dict) -> str:
    return hashlib.sha256(json.dumps(par, sort_keys=True, default=float).encode()).hexdigest()
