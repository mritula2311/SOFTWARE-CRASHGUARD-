"""Verification of severity.py on synthetic pulses with known answers. This proves the code, not real-world accuracy (SIMULATED).

Pulses: half-sine, triangular (peak at the middle) and square, with known peak A (g) and duration T (s), in front (0 deg),
side (90 deg) and oblique (35 deg) directions, with gravity, sensor noise and a small orientation offset (tilt) added.
Exact delta-V: half-sine 2*A*T/pi, triangular A*T/2, square A*T (times g). The ASI reference is the same EN 1317-2 algorithm run on the
noiseless pulse at 1 kHz (so the 13 Hz filter is part of the truth); the analytic unfiltered ASI of a frontal pulse is also given.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import severity as S

SHAPES = ("half_sine", "triangular", "square")
DIRECTIONS = {"front": 0.0, "side": 90.0, "oblique": 35.0}
AMPLITUDES_G = (8.0, 16.0, 24.0, 40.0)
DURATIONS_S = (0.04, 0.08, 0.12, 0.16)
NOISE_G = 0.02  # per-axis Gaussian noise (a typical MEMS IMU level at 100 Hz; our assumption)
TILT_DEG = 3.0  # random roll and pitch offset of the sensor frame (our assumption)
DV_TOL_PCT = 10.0  # stated tolerance for delta-V; 49 CFR 563.7 allows +-10% for event data recorders (verified)
ASI_TOL_PCT = 10.0  # stated tolerance for ASI (our choice)
TOL_MIN_DURATION_S = 0.08  # the tolerance is claimed for pulses at least this long at 100 Hz (shorter ones are shown, not claimed)
PRE_S, POST_S = C.PRE_S, C.POST_S


def shape_fn(shape: str, t: np.ndarray, t0: float, T: float) -> np.ndarray:
    u = (t - t0) / T
    inside = (u >= 0) & (u < 1)
    if shape == "half_sine":
        return np.where(inside, np.sin(np.pi * u), 0.0)
    if shape == "triangular":
        return np.where(inside, 1.0 - np.abs(2.0 * u - 1.0), 0.0)
    if shape == "square":
        return np.where(inside, 1.0, 0.0)
    raise ValueError(shape)


def dv_truth_ms(shape: str, A_g: float, T: float) -> float:
    k = {"half_sine": 2.0 / np.pi, "triangular": 0.5, "square": 1.0}[shape]
    return k * A_g * C.G0 * T


def asi_truth_unfiltered(shape: str, A_g: float, T: float, theta_deg: float, w: float = 0.05) -> float:
    """Analytic ASI without the 13 Hz filter: max over t of the 50 ms mean, same shape on both axes, window w <= T."""
    f = {"half_sine": 2 * T / (np.pi * w) * np.sin(np.pi * w / (2 * T)), "triangular": 1 - w / (2 * T), "square": 1.0}[shape]
    th = np.radians(theta_deg)
    return float(A_g * f * np.hypot(np.cos(th) / 12.0, np.sin(th) / 9.0))


def make_window(shape: str, A_g: float, T: float, theta_deg: float, fs: float, rng: np.random.Generator, noise_g: float = NOISE_G,
                tilt_deg: float = TILT_DEG, clip_g: float | None = None) -> tuple[np.ndarray, int]:
    """One triggered window (n, 3) in g, and the trigger index. The pulse decelerates the vehicle along -(cos, sin)(theta)."""
    n = int(round((PRE_S + POST_S) * fs))
    t0 = PRE_S + 0.01  # pulse start; the trigger is found from the signal, as in the firmware
    phase = rng.random()  # random sampling phase, so results do not depend on grid alignment
    t = (np.arange(n) + phase) / fs
    f = shape_fn(shape, t, t0, T)
    th = np.radians(theta_deg)
    a_true = np.stack([-A_g * f * np.cos(th), -A_g * f * np.sin(th), np.zeros(n)], axis=1)
    roll, pitch = np.radians(rng.uniform(-tilt_deg, tilt_deg, 2))
    g_vec = np.array([-np.sin(pitch), np.sin(roll) * np.cos(pitch), np.cos(roll) * np.cos(pitch)])  # gravity seen by a tilted sensor, in g
    acc = a_true + g_vec + rng.normal(0.0, noise_g, (n, 3))
    if clip_g:
        acc = np.clip(acc, -clip_g, clip_g)
    mag = np.linalg.norm(acc, axis=1)
    hit = np.flatnonzero(mag > C.TRIGGER_G)
    return acc, int(hit[0]) if len(hit) else -1


def run_grid(seeds: int = 5, fs_list=(100.0, 50.0), clips=(None, C.MPU_RANGE_G)) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(C.SEED)
    for shape in SHAPES:
        for dname, theta in DIRECTIONS.items():
            for A in AMPLITUDES_G:
                for T in DURATIONS_S:
                    # reference ASI: same algorithm, noiseless, 1 kHz
                    ref_acc, ref_trig = make_window(shape, A, T, theta, 1000.0, np.random.default_rng(0), noise_g=0.0, tilt_deg=0.0)
                    asi_ref = S.severity(ref_acc, 1000.0, ref_trig)["asi"]
                    dv_true = dv_truth_ms(shape, A, T)
                    for fs in fs_list:
                        for clip in clips:
                            for _ in range(seeds):
                                acc, trig = make_window(shape, A, T, theta, fs, rng, clip_g=clip)
                                if trig < 0:
                                    continue
                                r = S.severity(acc, fs, trig)
                                rows.append(dict(shape=shape, direction=dname, A_g=A, T_ms=T * 1000, fs=fs, clip=("none" if clip is None else f"+-{clip:g} g"),
                                                 dv_true_ms=dv_true, dv_ms=r["dv_res_ms"], dv_err_pct=100 * (r["dv_res_ms"] - dv_true) / dv_true,
                                                 asi_ref=asi_ref, asi=r["asi"], asi_err_pct=100 * (r["asi"] - asi_ref) / asi_ref,
                                                 asi_analytic_unfiltered=asi_truth_unfiltered(shape, A, T, theta), thiv_kmh=r["thiv_kmh"], cls=r["severity_class"]))
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    d = df.assign(abs_dv=df.dv_err_pct.abs(), abs_asi=df.asi_err_pct.abs(), long_pulse=df.T_ms >= TOL_MIN_DURATION_S * 1000)
    g = d.groupby(["fs", "clip", "long_pulse"]).agg(dv_err_median_pct=("dv_err_pct", "median"), dv_abs_err_median_pct=("abs_dv", "median"),
                                                     dv_abs_err_p90_pct=("abs_dv", lambda x: x.quantile(0.9)), asi_abs_err_median_pct=("abs_asi", "median"),
                                                     asi_abs_err_p90_pct=("abs_asi", lambda x: x.quantile(0.9)), n=("abs_dv", "size")).reset_index()
    key = d.groupby(["fs", "clip", "long_pulse"])
    g["dv_within_tol_share"] = key.abs_dv.apply(lambda x: float((x <= DV_TOL_PCT).mean())).to_numpy()
    g["asi_within_tol_share"] = key.abs_asi.apply(lambda x: float((x <= ASI_TOL_PCT).mean())).to_numpy()
    return g


def figure(df: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    d = df[(df.A_g == 40.0) & (df["shape"] == "half_sine")]
    for i, (fs, clip) in enumerate([(100.0, "none"), (100.0, f"+-{C.MPU_RANGE_G:g} g"), (50.0, "none"), (50.0, f"+-{C.MPU_RANGE_G:g} g")]):
        g = d[(d.fs == fs) & (d["clip"] == clip)].groupby("T_ms").dv_err_pct.median()
        axes[0].plot(g.index, g.values, marker="o", color=COLORS[i], label=f"{fs:g} Hz, clip {clip}")
    axes[0].axhline(0, color="gray", lw=0.8)
    axes[0].axhline(DV_TOL_PCT, color="gray", ls=":", lw=0.8)
    axes[0].axhline(-DV_TOL_PCT, color="gray", ls=":", lw=0.8)
    axes[0].set_xlabel("Pulse duration (ms)")
    axes[0].set_ylabel("Delta-V error (%), half-sine, peak 40 g")
    axes[0].legend(fontsize=7)
    for i, fs in enumerate((100.0, 50.0)):
        g = df[(df.fs == fs) & (df["clip"] == "none")]
        axes[1].scatter(g.dv_true_ms * 3.6, g.dv_ms * 3.6, s=6, alpha=0.5, color=COLORS[i], label=f"{fs:g} Hz")
        axes[2].scatter(g.asi_ref, g.asi, s=6, alpha=0.5, color=COLORS[i], label=f"{fs:g} Hz")
    lim = df.dv_true_ms.max() * 3.6
    axes[1].plot([0, lim], [0, lim], color="black", lw=0.8)
    axes[1].set_xlabel("True delta-V (km/h, analytic)")
    axes[1].set_ylabel("Recovered delta-V (km/h)")
    axes[1].legend(fontsize=7)
    lim = df.asi_ref.max()
    axes[2].plot([0, lim], [0, lim], color="black", lw=0.8)
    axes[2].set_xlabel("Reference ASI (1 kHz, same algorithm)")
    axes[2].set_ylabel("ASI from the sampled window")
    axes[2].legend(fontsize=7)
    fig.suptitle("Synthetic pulses (SIMULATED): checks the code, not real-world accuracy", fontsize=9)
    save(fig, "severity_synthetic_verification")


def main() -> None:
    from crashguard.results import record_many

    df = run_grid()
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.TABLES / "severity_synthetic_runs.csv", index=False)
    s = summarise(df)
    s.to_csv(C.TABLES / "severity_synthetic_summary.csv", index=False)
    src = "results/tables/severity_synthetic_summary.csv"
    ent = [dict(name="severity_synth.dv_tolerance_pct", value=DV_TOL_PCT, unit="percent", origin="ANALYTICAL", source_file=src, notes="stated tolerance; 49 CFR 563.7 gives +-10% for EDR delta-V"),
           dict(name="severity_synth.asi_tolerance_pct", value=ASI_TOL_PCT, unit="percent", origin="ANALYTICAL", source_file=src, notes="our stated tolerance"),
           dict(name="severity_synth.tolerance_min_duration_ms", value=TOL_MIN_DURATION_S * 1000, unit="ms", origin="ANALYTICAL", source_file=src, notes="tolerance claimed at 100 Hz for pulses at least this long"),
           dict(name="severity_synth.runs", value=int(len(df)), unit="windows", origin="SIMULATED", source_file=src, notes="synthetic windows; random noise, tilt and sampling phase, seed 42")]
    for r in s.itertuples():
        tag = f"fs{int(r.fs)}.clip_{'none' if r.clip == 'none' else 'on'}.{'long' if r.long_pulse else 'short'}"
        for k in ("dv_err_median_pct", "dv_abs_err_median_pct", "dv_abs_err_p90_pct", "asi_abs_err_median_pct", "asi_abs_err_p90_pct", "dv_within_tol_share", "asi_within_tol_share", "n"):
            ent.append(dict(name=f"severity_synth.{tag}.{k}", value=round(float(getattr(r, k)), 4), unit={"n": "windows"}.get(k, "fraction" if "share" in k else "percent"),
                            origin="SIMULATED", source_file=src, notes="synthetic pulses with known answers; 'long' = pulse duration at least the tolerance minimum"))
    from crashguard import boot as B

    d = df.assign(abs_dv=df.dv_err_pct.abs(), abs_asi=df.asi_err_pct.abs(), long_pulse=df.T_ms >= TOL_MIN_DURATION_S * 1000)
    for (fs, clip, lp), g in d.groupby(["fs", "clip", "long_pulse"]):
        tag = f"fs{int(fs)}.clip_{'none' if clip == 'none' else 'on'}.{'long' if lp else 'short'}"
        for k, col, f, unit in (("dv_abs_err_median_pct", "abs_dv", np.median, "percent"), ("dv_abs_err_p90_pct", "abs_dv", B.p90, "percent"),
                                ("dv_within_tol_share", "abs_dv", lambda x: float(np.mean(x <= DV_TOL_PCT)), "fraction"),
                                ("asi_within_tol_share", "abs_asi", lambda x: float(np.mean(x <= ASI_TOL_PCT)), "fraction")):
            _p, lo, hi = B.ci(g[col].to_numpy(), f)
            ent.append(dict(name=f"severity_synth.{tag}.{k}_lo", value=round(lo, 4), unit=unit, origin="SIMULATED", source_file=src, notes="95% bootstrap interval, 1,000 resamples of the synthetic windows"))
            ent.append(dict(name=f"severity_synth.{tag}.{k}_hi", value=round(hi, 4), unit=unit, origin="SIMULATED", source_file=src))
    record_many(ent)
    figure(df)
    print(s.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
