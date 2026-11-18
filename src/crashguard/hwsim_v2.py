"""Fault variants of the simulated hardware-format logs (Part S1; evidence label SIMULATED_HW_FORMAT). ``data/simulated_hardware/hwsim.py`` (v1) is left untouched.

Every fault is its own variant set with its own seed (20261114 + 1000 i); one fault at a time; the variants and seeds are fixed in
``docs/02_preregistration/PREREGISTRATION_V11.md`` and listed with hashes in ``docs/03_results/SIMHW_VARIANTS.md``.

Models and constants are those of ``hwsim.py`` (all ASSUMPTIONS, datasheets not opened): MPU6050 +-16 g with 2048 LSB/g, 400 ug/rtHz noise, per-axis bias, 44 Hz second-order
low-pass at a 1 kHz internal rate, logged at 100 Hz (10 Hz in one variant), rounding to the LSB, clipping at +-16 g; six SW-420 switches with a per-unit threshold on the 5 Hz
high-passed acceleration magnitude, a 20 ms latch and 0.03% chatter per sample; SX1278 433 MHz, SF7, 125 kHz, CR 4/5, 10 dBm, log-distance loss. Axes are the native axes of
the repository's NHTSA records (a front impact gives negative x, a left impact positive y); the impact-side rule applies the stored calibration signs.

    python -m crashguard.hwsim_v2 [OUTDIR] [variant names ...]
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.signal import lfilter

BASE_SEED = 20261114
FS_INT = 1000
ACC_LSB, GYR_LSB = 2048.0, 16.4
ACC_ND, GYR_ND = 400e-6, 0.005
DLPF_HZ = 44.0
T_END = 3.0
T_INT = np.arange(0, T_END, 1 / FS_INT)
PER_CELL = 20
SIDES = ("front", "rear", "left", "right", "vertical")
KINDS = ("hand_tap", "hard_braking", "lift_and_place", "ramp_bump", "rough_driving")
AX = {"front": (0, -1), "rear": (0, 1), "left": (1, 1), "right": (1, -1), "vertical": (2, 1)}
COLS = ["t_ms", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"] + [f"sw420_{k}" for k in range(1, 7)]
OUTDIR = Path("data/simulated_hardware/variants")

BASE = dict(rate_hz=100, jitter_ms=0.0, drop=0.0, tilt_axis=None, tilt_deg=0.0, flip=None, noise=1.0, bias_sd=0.03, peak_median=5.0, sw_lo=1.5, sw_hi=4.0,
            loss=None, interferer=False)
VARIANTS: list[tuple[int, str, dict, str]] = [
    (0, "V00_base", {}, "sensor+radio"),
    (1, "T_x15", dict(tilt_axis="x", tilt_deg=15.0), "sensor"),
    (2, "T_x30", dict(tilt_axis="x", tilt_deg=30.0), "sensor"),
    (3, "T_y15", dict(tilt_axis="y", tilt_deg=15.0), "sensor"),
    (4, "T_y30", dict(tilt_axis="y", tilt_deg=30.0), "sensor"),
    (5, "F_x", dict(flip="x"), "sensor"),
    (6, "F_y", dict(flip="y"), "sensor"),
    (7, "S_10Hz", dict(rate_hz=10), "sensor"),
    (8, "S_jit1", dict(jitter_ms=1.0), "sensor"),
    (9, "S_drop05", dict(drop=0.005), "sensor"),
    (10, "N_x2", dict(noise=2.0), "sensor"),
    (11, "N_x4", dict(noise=4.0), "sensor"),
    (12, "B_08", dict(bias_sd=0.08), "sensor"),
    (13, "P_3", dict(peak_median=3.0), "sensor"),
    (14, "P_8", dict(peak_median=8.0), "sensor"),
    (15, "L_0", dict(loss=0.0), "radio"),
    (16, "L_10", dict(loss=0.10), "radio"),
    (17, "L_30", dict(loss=0.30), "radio"),
    (18, "I_block", dict(loss=0.0, interferer=True), "radio"),
]


def variant_params(name: str) -> tuple[int, dict, str]:
    for i, n, p, kind in VARIANTS:
        if n == name:
            return i, {**BASE, **p}, kind
    raise KeyError(name)


def seed_of(i: int) -> int:
    return BASE_SEED + 1000 * i


# ------------------------------------------------------------------ sensor model
def _lp_coeffs(fc: float, fs: float):
    w = math.tan(math.pi * fc / fs)
    k = 1 + math.sqrt(2) * w + w * w
    b0 = w * w / k
    return [b0, 2 * b0, b0], [1.0, 2 * (w * w - 1) / k, (1 - math.sqrt(2) * w + w * w) / k]


def lowpass(x: np.ndarray, fc: float, fs: float = FS_INT) -> np.ndarray:
    """Causal second-order low-pass on rows of x (last axis time), started from the first sample (no start-up step)."""
    b, a = _lp_coeffs(fc, fs)
    x = np.atleast_2d(x)
    pad = 300
    xp = np.concatenate([np.repeat(x[:, :1], pad, axis=1), x], axis=1)
    return lfilter(b, a, xp, axis=1)[:, pad:]


def half_sine(t0: float, dur: float, peak: float) -> np.ndarray:
    x = np.zeros_like(T_INT)
    m = (T_INT >= t0) & (T_INT < t0 + dur)
    x[m] = peak * np.sin(math.pi * (T_INT[m] - t0) / dur)
    return x


def ring(t0: float, f: float, zeta: float, amp: float) -> np.ndarray:
    x = np.zeros_like(T_INT)
    m = T_INT >= t0
    tt = T_INT[m] - t0
    x[m] = amp * np.exp(-zeta * 2 * math.pi * f * tt) * np.sin(2 * math.pi * f * tt)
    return x


def crash_event(rng, side: str, peak_median: float):
    ax_i, sgn = AX[side]
    peak = float(np.clip(rng.lognormal(math.log(peak_median), 0.45), 2.0, 40.0))
    dur = rng.uniform(0.012, 0.045)
    t0 = rng.uniform(0.9, 1.3)
    a = np.zeros((3, len(T_INT)))
    a[ax_i] = sgn * half_sine(t0, dur, peak) + ring(t0 + dur, rng.uniform(60, 140), 0.08, 0.25 * peak) * sgn
    for j in range(3):
        if j != ax_i:
            a[j] += rng.normal(0, 0.12) * half_sine(t0, dur, peak)
    g = np.zeros((3, len(T_INT)))
    for j in range(3):
        g[j] = rng.normal(0, 25 + 4 * peak) * half_sine(t0, dur * 2, 1)
    return a, g


def noncrash_event(rng, kind: str):
    a = np.zeros((3, len(T_INT)))
    g = np.zeros((3, len(T_INT)))
    t0 = rng.uniform(0.8, 1.4)
    if kind == "hand_tap":
        p = rng.uniform(1.0, 3.0)
        ai = int(rng.integers(0, 3))
        a[ai] = half_sine(t0, rng.uniform(0.008, 0.02), p) * rng.choice([-1, 1]) + ring(t0 + 0.01, 90, 0.1, 0.2 * p)
    elif kind == "hard_braking":
        p = rng.uniform(0.35, 0.85)
        ramp = np.clip((T_INT - t0) / 0.25, 0, 1) * np.clip((t0 + rng.uniform(1, 1.6) - T_INT) / 0.25, 0, 1)
        a[0] = -p * ramp
        g[1] = 6 * ramp
    elif kind == "lift_and_place":
        a[2] = 0.6 * np.sin(2 * math.pi * (T_INT - t0) / rng.uniform(0.9, 1.6)) * ((T_INT > t0) & (T_INT < t0 + 1.4)) + half_sine(t0 + 1.5, 0.03, rng.uniform(1, 2.2))
        g[0] = rng.uniform(15, 60) * np.sin(2 * math.pi * (T_INT - t0) / 1.3) * ((T_INT > t0) & (T_INT < t0 + 1.4))
    elif kind == "ramp_bump":
        p = rng.uniform(1.8, 4.5)
        a[2] = half_sine(t0, rng.uniform(0.04, 0.09), p) + ring(t0 + 0.07, 12, 0.15, 0.4 * p)
        g[1] = rng.normal(0, 40) * half_sine(t0, 0.1, 1)
    elif kind == "rough_driving":
        for j in range(3):
            a[j] = lowpass(rng.normal(0, 1, len(T_INT)), 35)[0] * rng.uniform(0.25, 0.7) * 3
        for _ in range(int(rng.integers(1, 4))):
            a[2] += half_sine(rng.uniform(0.3, 2.6), rng.uniform(0.02, 0.06), rng.uniform(1.5, 3.2))
    return a, g


def _rot(axis: str, deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def sample_times(rng, p: dict) -> tuple[np.ndarray, np.ndarray]:
    """Nominal and actual sample times (ms). Jitter moves the instant at which the sample is taken; the log carries the rounded actual time. Dropped samples are removed."""
    step = 1000.0 / p["rate_hz"]
    nominal = np.arange(0, int(T_END * 1000), step)
    actual = nominal + (rng.normal(0, p["jitter_ms"], len(nominal)) if p["jitter_ms"] > 0 else 0.0)
    actual = np.clip(actual, 0, T_END * 1000 - 1)
    keep = np.ones(len(nominal), bool)
    if p["drop"] > 0:
        keep = rng.random(len(nominal)) >= p["drop"]
        keep[0] = True
    return nominal[keep], actual[keep]


def sense(rng, acc_dyn: np.ndarray, gyr_dyn: np.ndarray, p: dict):
    """Vehicle-axis dynamic signals -> logged sensor rows. Returns (t_ms, acc (n,3), gyro (n,3), true specific force (3,N) for the SW-420 model)."""
    g0 = np.array([[0.0], [0.0], [1.0]]) * np.ones((3, len(T_INT)))
    spec = g0 + acc_dyn
    if p["tilt_axis"]:
        R = _rot(p["tilt_axis"], p["tilt_deg"])
        spec = R @ spec
        gyr_dyn = R @ gyr_dyn
    if p["flip"]:
        sgn = np.array([-1.0 if p["flip"] == "x" else 1.0, -1.0 if p["flip"] == "y" else 1.0, 1.0])[:, None]
        spec = spec * sgn
        gyr_dyn = gyr_dyn * sgn
    bias_a = rng.normal(0, p["bias_sd"], (3, 1))
    bias_g = rng.normal(0, 0.6, (3, 1))
    na = rng.normal(0, ACC_ND * p["noise"] * math.sqrt(FS_INT / 2), spec.shape)
    ng = rng.normal(0, GYR_ND * p["noise"] * math.sqrt(FS_INT / 2), gyr_dyn.shape)
    a = lowpass(spec + bias_a + na, DLPF_HZ)
    g = lowpass(gyr_dyn + bias_g + ng, DLPF_HZ)
    a = np.round(np.clip(a, -16, 16) * ACC_LSB) / ACC_LSB
    g = np.round(np.clip(g, -2000, 2000) * GYR_LSB) / GYR_LSB
    nominal, actual = sample_times(rng, p)
    ta = actual / 1000.0
    ai = np.stack([np.interp(ta, T_INT, a[k]) for k in range(3)], axis=1)
    gi = np.stack([np.interp(ta, T_INT, g[k]) for k in range(3)], axis=1)
    ai = np.round(np.clip(ai, -16, 16) * ACC_LSB) / ACC_LSB
    return np.round(actual).astype(int), ai, gi, spec, ta


def sw420(rng, spec: np.ndarray, ta: np.ndarray, p: dict) -> np.ndarray:
    hp = spec - lowpass(spec, 5.0)
    mag = np.sqrt((hp**2).sum(0))
    thr = rng.uniform(p["sw_lo"], p["sw_hi"], 6)
    out = []
    for th in thr:
        s = (mag > th).astype(int)
        s = (np.convolve(s, np.ones(20), "same") > 0).astype(int)
        s |= (rng.random(len(s)) < 0.0003).astype(int)
        idx = np.clip(np.round(ta * FS_INT).astype(int), 0, len(s) - 1)
        out.append(s[idx])
    return np.array(out).T


def write_event(rng, outdir: Path, name: str, scen: str, label: str, side, etype, acc_dyn, gyr_dyn, p: dict, vname: str, seed: int) -> None:
    t, a, g, spec, ta = sense(rng, acc_dyn, gyr_dyn, p)
    s = sw420(rng, spec, ta, p)
    rows = [[int(t[i]), *[round(float(v), 4) for v in a[i]], *[round(float(v), 3) for v in g[i]], *[int(v) for v in s[i]]] for i in range(len(t))]
    d = dict(test_id=name, scenario=scen, true_label=label, impact_side=side, event_type=etype, start=dict(device_millis_start=0, wall_clock_iso=None), columns=COLS,
             rate_hz=p["rate_hz"], variant=vname, data_origin=f"SIMULATED (hwsim_v2.py, variant {vname}, seed {seed}); not measured hardware", rows=rows)
    (outdir / f"{name}.json").write_text(json.dumps(d), encoding="utf-8")


# ------------------------------------------------------------------ radio model (hwsim.py formulas)
def toa_ms(pl: int, sf: int = 7, bw: float = 125e3, cr: int = 1, pre: int = 8, crc: int = 1, h: int = 0) -> float:
    ts = 2**sf / bw
    de = 1 if ts > 0.016 else 0
    n = 8 + max(math.ceil((8 * pl - 4 * sf + 28 + 16 * crc - 20 * h) / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (pre + 4.25 + n) * ts * 1000


NOISE_FLOOR = -174 + 10 * math.log10(125e3) + 6
SNR_LIMIT = -7.5
PL1M = 20 * math.log10(4 * math.pi / (3e8 / 433e6))
H3_RUNS = [("H3-10m-open", 10, False, 0), ("H3-50m-open", 50, False, 0), ("H3-100m-open", 100, False, 0), ("H3-100m-wall", 100, True, 0),
           ("H3-edge-30db", 100, True, 30), ("H3-edge-34db", 100, True, 34), ("H3-edge-38db", 100, True, 38), ("H3-edge-42db", 100, True, 42)]


def link(rng, d, wall=False, extra=0.0, ptx=10, n=3.0, sigma=3.5):
    pl = PL1M + 10 * n * math.log10(max(d, 1)) + rng.normal(0, sigma) + (12 if wall else 0) + extra + 3
    rssi = ptx - pl
    snr = rssi - NOISE_FLOOR
    snr_rep = float(np.clip(min(snr, 10 + rng.normal(0, 1.0)), -20, 10))
    return max(rssi, -148.0), snr, snr_rep


def p_ok(snr: float) -> float:
    return 1 / (1 + math.exp(-(snr - SNR_LIMIT) / 0.9))


class Interferer:
    """Blocks of 5 s in 10% of the minutes; a packet whose airtime overlaps a block is lost."""

    def __init__(self, rng, horizon_s: float):
        self.blocks = []
        for m in range(int(horizon_s // 60) + 1):
            if rng.random() < 0.10:
                s = m * 60 + rng.uniform(0, 55)
                self.blocks.append((s * 1000.0, (s + 5.0) * 1000.0))

    def hit(self, t0_ms: float, dur_ms: float) -> bool:
        return any(t0_ms < b1 and t0_ms + dur_ms > b0 for b0, b1 in self.blocks)


def run_link(rng, run: str, d: float, wall: bool, extra: float, p: dict, npk: int = 100) -> dict:
    ta, tk = toa_ms(97), toa_ms(26)
    itf = Interferer(rng, 3.0 * (npk + 5)) if p["interferer"] else None
    extra_loss = p["loss"] or 0.0
    recs = []
    for k in range(npk):
        tx0 = 3000 + 3000 * k
        ret, t, deliv, last, ack = 0, tx0, False, None, None
        while True:
            ru, su, sru = link(rng, d, wall, extra)
            rd, sd, srd = link(rng, d, wall, extra)
            up = rng.random() < p_ok(su) and rng.random() >= extra_loss
            dn = rng.random() < p_ok(sd) and rng.random() >= extra_loss
            if itf is not None:
                up = up and not itf.hit(t, ta)
                dn = dn and not itf.hit(t + ta, tk + 16)
            last = (ru, sru, rd, srd)
            if up and dn:
                ack = t + ta + rng.uniform(8, 16) + tk
                deliv = True
                break
            if ret >= 3:
                break
            ret += 1
            t += 600 + rng.uniform(0, 40)
        recs.append(dict(packet_no=k + 1, tx_start_ms=tx0, ack_rx_ms=None if ack is None else int(round(ack)), rssi_dbm_at_base=round(last[0], 1), snr_db_at_base=round(last[1], 1),
                         rssi_dbm_at_car=round(last[2], 1), snr_db_at_car=round(last[3], 1), retries=ret, delivered=deliv, crc_error=bool((not deliv) and rng.random() < 0.3)))
    return dict(run_id=run, distance_m=d, wall_between=wall, extra_attenuation_db=extra, added_loss_per_direction=extra_loss, interferer=p["interferer"],
                radio=dict(frequency_mhz=433, sf=7, bw_khz=125, cr="4/5", tx_power_dbm=10), ack_timeout_ms=600, max_retries=3, alert_payload_bytes=97, ack_payload_bytes=26,
                time_on_air_ms=dict(alert=round(ta, 2), ack=round(tk, 2)), noise_floor_dbm=round(NOISE_FLOOR, 1), records=recs,
                data_origin="SIMULATED (hwsim_v2.py); not measured RF")


def run_h7(rng, p: dict, n: int = 100) -> dict:
    ta, tk = toa_ms(97), toa_ms(26)
    loss = p["loss"] if p["loss"] is not None else 0.03
    itf = Interferer(rng, 10.0 * (n + 2)) if p["interferer"] else None
    recs = []
    for i in range(n):
        trig = 10000 * (i + 1)
        dec = trig + 250 + rng.normal(8, 1.5) + 4
        sev = rng.choice(["Moderate", "Severe", "Critical"], p=[0.3, 0.45, 0.25])
        tx0 = dec + rng.uniform(8, 22)
        ret, t = 0, tx0
        while True:
            up = rng.random() >= loss and not (itf and itf.hit(t, ta))
            dn = rng.random() >= loss and not (itf and itf.hit(t + ta, tk + 15))
            if up and dn:
                break
            if ret >= 3:
                break
            ret += 1
            t += 600 + rng.uniform(0, 40)
        ok = up and dn
        brx = t + ta
        back = brx + rng.uniform(9, 15)
        recs.append(dict(event_id=f"H7-{i + 1:02d}", severity_class_sent=str(sev), t_first_sample_over_trigger_ms=trig, t_decision_ms=int(dec), t_tx_start_ms=int(round(tx0)),
                         t_tx_done_ms=int(round(t + ta)), t_ack_rx_ms=int(round(back + tk)) if ok else None, retries=ret, base_rx_ms=int(round(brx)), base_ack_tx_ms=int(round(back)),
                         alert_bytes=97, ack_bytes=26))
    return dict(records=recs, per_direction_loss=loss, interferer=p["interferer"], data_origin="SIMULATED (hwsim_v2.py); time on air from the LoRa formula")


# ------------------------------------------------------------------ driver
def hash_dir(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(d.rglob("*.json")):
        h.update(f.relative_to(d).as_posix().encode())
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


SW_SENS = ((0.8, 2.0), (3.0, 6.0))  # S5 sensitivity: per-unit SW-420 threshold ranges (g); same seed as the variant, so the IMU data are identical to the variant's


def generate(name: str, root: Path = OUTDIR, sw: tuple[float, float] | None = None) -> dict:
    i, p, kind = variant_params(name)
    seed = seed_of(i)
    rng = np.random.default_rng(seed)
    out = root / (name if sw is None else f"{name}__sw{sw[0]:g}-{sw[1]:g}")
    if sw is not None:
        p = {**p, "sw_lo": sw[0], "sw_hi": sw[1]}
    out.mkdir(parents=True, exist_ok=True)
    n_events = 0
    if "sensor" in kind:
        sd = out / "sensor_logs"
        sd.mkdir(exist_ok=True)
        for side in SIDES:
            for k in range(1, PER_CELL + 1):
                a, g = crash_event(rng, side, p["peak_median"])
                write_event(rng, sd, f"H1-{side}-{k:02d}", "impact_side", "crash", side, None, a, g, p, name, seed)
                n_events += 1
        for kd in KINDS:
            for k in range(1, PER_CELL + 1):
                a, g = noncrash_event(rng, kd)
                write_event(rng, sd, f"H2-{kd}-{k:02d}", "crash_vs_noncrash", "non_crash", None, kd, a, g, p, name, seed)
                n_events += 1
    if "radio" in kind:
        pd_ = out / "protocol_logs"
        pd_.mkdir(exist_ok=True)
        for run, d, wall, extra in H3_RUNS:
            (pd_ / f"{run}.json").write_text(json.dumps(run_link(rng, run, d, wall, extra, p)), encoding="utf-8")
        (pd_ / "e2e_latency_H7.json").write_text(json.dumps(run_h7(rng, p)), encoding="utf-8")
    meta = dict(variant=name if sw is None else out.name, index=i, seed=seed, kind=kind, params={k: v for k, v in p.items()}, n_sensor_events=n_events, data_origin="SIMULATED (hwsim_v2.py)")
    (out / "variant.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    meta["sha256"] = hash_dir(out)
    return meta


def main() -> None:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTDIR
    names = sys.argv[2:] or [v[1] for v in VARIANTS]
    res = [generate(n, root) for n in names]
    hp = root / "VARIANT_HASHES.json"
    old = json.loads(hp.read_text(encoding="utf-8")) if hp.exists() else {}
    old.update({r["variant"]: r["sha256"] for r in res})
    hp.write_text(json.dumps(dict(sorted(old.items())), indent=1), encoding="utf-8")
    for r in res:
        print(r["variant"], r["seed"], r["sha256"][:16])
    if len(sys.argv) <= 2:  # all variants: also the S5 sensitivity sets (SW-420 threshold ranges), same seeds as the sensor variants
        sens = {}
        for _i, n, _p, k in VARIANTS:
            if "sensor" in k:
                for sw in SW_SENS:
                    m = generate(n, root, sw)
                    sens[m["variant"]] = m["sha256"]
        (root / "SW_SENS_HASHES.json").write_text(json.dumps(dict(sorted(sens.items())), indent=1), encoding="utf-8")
        print(len(sens), "sensitivity sets")


if __name__ == "__main__":
    main()
