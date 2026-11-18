"""Per-record, per-sensor-cell features of the positive-results push (docs/02_preregistration/PREREGISTRATION_V4.md, sections 0 and 1).

A cell is (range in g, output rate in Hz). For each pooled record the generic sensor chain of ``severity_study.sensor_signal`` gives the window; from it come
* the plain delta-V and pulse length, the N14 fill (triangle, level 0.7, release 0.1) and its saturated share,
* the clipping descriptors and pulse-family features of Study A (``v2_clip.features_one``, used by the anchored estimator),
* the descriptors of the direct classifier and the features of the mode classifier,
* the clipped waveform (x, y, resultant over the range; 0.1 s before to 0.4 s after the trigger).
``augment`` builds augmented copies of a record for training (time scaling, amplitude scaling before the sensor model, noise, resampling phase) and recomputes their reference delta-V.
Everything is a function of one record's signal; nothing is fitted here.
"""
from __future__ import annotations

import pickle
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import nhtsa as N
from crashguard import saturation as SAT
from crashguard import saturation_splits as SP
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard import v2_clip as V
from crashguard.pp_common import RANGES, RATES

CACHE = C.PROCESSED / "pp_feat.pkl"
PARAMS = SP.sp_params(0.1)
CLIP_LEVEL = 0.7
PRE_S, POST_S = 0.1, 0.4

DESC_D = ["dv_plain", "pulse_ms", "clip_ms", "n_runs", "clip_frac", "time_to_clip_ms", "rise_rate", "area_before_clip", "area_unclipped", "peak_unclipped", "slope_in", "slope_out",
          "clip_over_pulse", "area_before_over_time", "peak_unclipped_over_range", "dv_per_ms"]
MONO = ["dv_plain", "clip_ms", "clip_frac", "area_unclipped", "peak_unclipped_over_range"]
MODE_FEATS = ["dv_plain", "pulse_ms", "dvx", "dvy", "angle", "peak_x", "peak_y", "t_peak_ms", "width50_ms", "peak_h_over_range", "clip_ms", "clip_frac", "rise_rate", "area_unclipped", "dv_per_ms", "sign_y"]
V2_DESC = ("clip_ms", "n_runs", "clip_frac", "slope_in", "slope_out", "rise_ms", "area_unclipped", "area_clip")
V2_FAM = ("dv_mean", "dv_median", "dv_best", "dv_wmean", "disagree")


def wave_len(fs: float) -> int:
    return int(round(PRE_S * fs)) + int(round(POST_S * fs))


def cell_from_signal(y: np.ndarray, rg: float, fs: float) -> dict:
    """Features of one sensor reading ``y`` (g, gravity on z) at range ``rg`` and rate ``fs``. Keys: scalars plus ``wave`` (3, L)."""
    w, trig = SS._window(y, fs)
    r = S.severity(w, fs, trig, None, PARAMS)
    a = S.remove_baseline(w, trig)
    h = np.hypot(a[:, 0], a[:, 1])
    s0 = int(trig)
    e = max(S.pulse_end(h, s0, fs, PARAMS), s0)
    sat = ((np.abs(w[:, 0]) >= CLIP_LEVEL * rg) | (np.abs(w[:, 1]) >= CLIP_LEVEL * rg))
    sat_p = np.zeros(len(w), bool)
    sat_p[s0 : e + 1] = sat[s0 : e + 1]
    idx = np.flatnonzero(sat_p)
    n_pulse = e - s0 + 1
    pulse_ms = (e - s0) / fs * 1000.0
    hp = h[s0 : e + 1]
    f: dict = dict(dv_plain=float(r["dv_res_kmh"]), pulse_ms=float(r["pulse_ms"]), dvx=float(r["dvx_kmh"]), dvy=float(r["dvy_kmh"]))
    f["angle"] = float(np.degrees(np.arctan2(abs(f["dvy"]), abs(f["dvx"]) + 1e-9)))
    f["sign_y"] = float(np.sign(f["dvy"]))
    f["peak_x"] = float(np.abs(a[s0 : e + 1, 0]).max() / rg)
    f["peak_y"] = float(np.abs(a[s0 : e + 1, 1]).max() / rg)
    ip = int(np.argmax(hp))
    f["t_peak_ms"] = ip / fs * 1000.0
    f["peak_h_over_range"] = float(hp.max() / rg)
    f["width50_ms"] = float((hp >= 0.5 * hp.max()).sum() / fs * 1000.0)
    f["n_sat"] = int(len(idx))
    f["clip_ms"] = len(idx) / fs * 1000.0
    f["clip_frac"] = len(idx) / n_pulse
    f["n_runs"] = (1 + int((np.diff(idx) > 1).sum())) if len(idx) else 0
    if len(idx):
        j0, j1 = int(idx[0]), int(idx[-1])
        k0, k1 = max(j0 - 3, s0), min(j1 + 3, e)
        f["time_to_clip_ms"] = (j0 - s0) / fs * 1000.0
        f["rise_rate"] = float((h[j0] - h[s0]) / max((j0 - s0) / fs, 1.0 / fs))
        f["area_before_clip"] = float(h[s0:j0].sum() / fs)
        f["slope_in"] = float((h[j0] - h[k0]) / max((j0 - k0) / fs, 1.0 / fs))
        f["slope_out"] = float((h[k1] - h[j1]) / max((k1 - j1) / fs, 1.0 / fs))
        f["area_unclipped"] = float(h[s0 : e + 1][~sat_p[s0 : e + 1]].sum() / fs)
        unc = h[s0 : e + 1][~sat_p[s0 : e + 1]]
        f["peak_unclipped"] = float(unc.max()) if len(unc) else 0.0
    else:
        f.update(time_to_clip_ms=pulse_ms, rise_rate=float(hp.max() / max(ip / fs, 1.0 / fs)), area_before_clip=float(hp.sum() / fs), slope_in=0.0, slope_out=0.0, area_unclipped=float(hp.sum() / fs), peak_unclipped=float(hp.max()))
    f["clip_over_pulse"] = f["clip_ms"] / max(pulse_ms, 1e-6)
    f["area_before_over_time"] = f["area_before_clip"] / max(f["time_to_clip_ms"], 1.0)
    f["peak_unclipped_over_range"] = f["peak_unclipped"] / rg
    f["dv_per_ms"] = f["dv_plain"] / max(pulse_ms, 1.0)
    pre, post = int(round(PRE_S * fs)), int(round(POST_S * fs))
    ii = np.clip(np.arange(s0 - pre, s0 + post), 0, len(w) - 1)
    f["wave"] = (np.stack([a[ii, 0], a[ii, 1], h[ii]], axis=0) / rg).astype(np.float32)
    return f


def fill_of(y: np.ndarray, rg: float, fs: float) -> tuple[float, float, int]:
    w, trig = SS._window(y, fs)
    r, info = SAT.severity_filled(w, fs, trig, rg, SP.FINAL_FAMILY, PARAMS, SP.FINAL_SAT)
    return float(r["dv_res_kmh"]), float(info.sat_share), int(info.applied)


def record_cells(sig: dict) -> dict:
    """All (range, rate) cells of one record, with the Study A features for the anchored estimator."""
    out = {}
    for rg in RANGES:
        for fs in RATES:
            y = SS.sensor_signal(sig, rg, float(fs))
            f = cell_from_signal(y, rg, float(fs))
            f["dv_fill"], f["sat_share"], f["fill_applied"] = fill_of(y, rg, float(fs))
            V.FS = float(fs)
            v = V.features_one(sig, rg)
            for k in V2_DESC + V2_FAM:
                f["v2_" + k] = float(v[k])
            out[(rg, fs)] = f
    return out


def _work(sig: dict) -> dict:
    return record_cells(sig)


def build(force: bool = False, workers: int = 12) -> dict:
    """{(range, rate): (DataFrame aligned with the pool, waves array (n, 3, L))}; cached."""
    if CACHE.exists() and not force:
        return pickle.loads(CACHE.read_bytes())
    from crashguard import pp_pool

    pool = pp_pool.load()["pool"]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_work, [p["sig"] for p in pool], chunksize=4))
    out = {}
    for rg in RANGES:
        for fs in RATES:
            rows = [r[(rg, fs)] for r in res]
            waves = np.stack([r.pop("wave") for r in rows])
            out[(rg, fs)] = (pd.DataFrame(rows), waves)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(out))
    return out


# ---- augmentation (training data only) ----
def stretch(sig: dict, s: float, a: float) -> dict:
    """Pulse stretched in time by ``s`` (duration x s) and scaled in amplitude by ``a``; same original sampling rate; gravity is not in ``acc``."""
    t, acc, fs0 = np.asarray(sig["t"]), np.asarray(sig["acc"]), float(sig["fs0"])
    t2 = t[0] + np.arange(0, (t[-1] - t[0]) * s, 1.0 / fs0)
    src = t[0] + (t2 - t[0]) / s
    acc2 = np.stack([np.interp(src, t, acc[:, k]) for k in range(3)], axis=1) * a
    return dict(sig, t=t2, acc=acc2, peak_g=float(np.abs(acc2).max()))


def sensor_aug(sig: dict, rg: float, fs: float, phase: float, noise_g: float, rng: np.random.Generator) -> np.ndarray:
    """``severity_study.sensor_signal`` with a shifted sampling grid (phase in samples) and white noise on the output."""
    t, acc, fs0 = np.asarray(sig["t"]), np.asarray(sig["acc"]), float(sig["fs0"])
    x = N._lowpass(acc, fs0, SS.FE_HZ) if SS.FE_HZ < 0.45 * fs0 else acc
    x = np.clip(x, -rg, rg)
    dig = min(0.4 * fs, SS.FE_HZ)
    if dig < 0.45 * fs0:
        x = N._lowpass(x, fs0, dig)
    tt = np.arange(t[0] + phase / fs, t[-1], 1.0 / fs)
    y = np.stack([np.interp(tt, t, x[:, k]) for k in range(3)], axis=1) + np.array([0, 0, N.GRAVITY_Z_G])
    if noise_g > 0:
        y[:, :2] += rng.normal(0.0, noise_g, size=(len(y), 2))
    return y


def augment_one(sig: dict, rg: float, fs: float, rng: np.random.Generator) -> tuple[dict, float]:
    s = float(np.exp(rng.uniform(np.log(0.8), np.log(1.25))))
    a = float(np.exp(rng.uniform(np.log(0.7), np.log(1.4))))
    sig2 = stretch(sig, s, a)
    ref, _ = SS.reference_dv(sig2)
    y = sensor_aug(sig2, rg, fs, float(rng.uniform(0.0, 1.0)), float(rng.uniform(0.005, 0.03)), rng)
    return cell_from_signal(y, rg, fs), float(ref)


def _aug_work(args) -> list:
    sig, rg, fs, k, seed = args
    rng = np.random.default_rng(seed)
    return [augment_one(sig, rg, fs, rng) for _ in range(k)]


def augment_cell(idx: np.ndarray, rg: float, fs: float, copies: int = 6, seed: int = 42, workers: int = 12) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray]:
    """Augmented copies of the pool records ``idx`` at one cell. Returns (features, waves, reference delta-V, source index of each copy)."""
    from crashguard import pp_pool

    pool = pp_pool.load()["pool"]
    jobs = [(pool[i]["sig"], rg, fs, copies, seed * 100003 + int(i)) for i in idx]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_aug_work, jobs, chunksize=8))
    rows, refs, src = [], [], []
    for i, r in zip(idx, res):
        for f, ref in r:
            rows.append(f)
            refs.append(ref)
            src.append(int(i))
    waves = np.stack([r.pop("wave") for r in rows])
    return pd.DataFrame(rows), waves, np.array(refs), np.array(src)


if __name__ == "__main__":
    import time

    t = time.time()
    d = build(force=True)
    for k, (df, wv) in d.items():
        print(k, df.shape, wv.shape)
    print(round(time.time() - t), "s")
