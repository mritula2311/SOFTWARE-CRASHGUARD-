"""L1 (docs/02_preregistration/PREREGISTRATION_V16.md section 3): gravity-referenced automatic mounting calibration for the impact-side rule.

    python -m crashguard.r5_l1 dev          # development iterations (at most 5), simulated installations D01 to D12 (seed 50261115) and NHTSA tuning groups
    python -m crashguard.r5_l1 freeze       # hash the sources and the chosen parameters
    python -m crashguard.r5_l1 held         # held-out run, once: installations H01 to H12 (seed 60261116) and the NHTSA held-out groups; keys r5.l1.*

Evidence: SIMULATED_HW_FORMAT (generators of ``hwsim_v2`` with a general mounting rotation and a synthetic calibration drive) and MEASURED_SOFTWARE for the real NHTSA pulses
(synthetic rotations and synthetic calibration drive, stated). The side rule itself (``sh_events.side_rule``) is unchanged; L1 only rotates the samples into the vehicle frame before it.
Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, dataclass

import numpy as np

from crashguard import hwsim_v2 as H
from crashguard import sh_events as SE

DEV_SEED, HELD_SEED = 50261115, 60261116
FS = 100.0
SIDES = ("front", "rear", "left", "right")
N_PER_SIDE = 20
RANDOM_NOISE_G = 0.008  # road vibration of the synthetic calibration drive (g, low-passed); an assumption
G_MS2 = 9.81


@dataclass(frozen=True)
class L1Params:
    """Frozen design values of V16 section 3.1 (with addendum A1); development may change the four marked items only."""

    a_min: float = 1.0  # development item: GPS speed change (m/s per second) that makes a segment usable
    still_s: float = 2.0  # development item: still window length (s)
    g_still: float = 3.0  # development item: gyro magnitude limit in a still window (deg/s)
    ang_stale: float = 10.0  # development item: gravity direction change (degrees) that makes the calibration stale
    a_still: float = 0.15  # not a development item (addendum A1)
    sd_still: float = 0.02  # standard deviation of |a| in a still window (g)
    seg_min_s: float = 2.0  # minimum length of the speed-change segment (s)
    seg_trim_s: float = 0.25  # samples within this time of the segment ends are not used (GPS timing)
    straight_dps: float = 5.0  # gyro component along z_hat that still counts as a straight line
    h_min_g: float = 0.05  # minimum horizontal mean acceleration (g)


ITERATIONS = [L1Params(), L1Params(a_min=0.5), L1Params(a_min=1.5), L1Params(still_s=1.5, g_still=5.0), L1Params(g_still=2.0, ang_stale=5.0)]


# ------------------------------------------------------------------------------------------------ rotations
def rot_x(deg: float) -> np.ndarray:
    return H._rot("x", deg)


def rot_y(deg: float) -> np.ndarray:
    return H._rot("y", deg)


def rot_z(deg: float) -> np.ndarray:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def axis_angle(k: np.ndarray, deg: float) -> np.ndarray:
    k = np.asarray(k, float) / np.linalg.norm(k)
    th = math.radians(deg)
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) * math.cos(th) + math.sin(th) * K + (1 - math.cos(th)) * np.outer(k, k)


def random_physical_rotation(rng: np.random.Generator) -> np.ndarray:
    """V16 section 3.3: yaw from 0, 90, 180, 270; tilt of 0 to 30 degrees about a random horizontal axis; an extra 180 degrees about x with probability 0.25. Sensor = R vehicle."""
    yaw = float(rng.choice([0, 90, 180, 270]))
    tilt = float(rng.uniform(0.0, 30.0))
    az = float(rng.uniform(0.0, 2 * math.pi))
    R = axis_angle(np.array([math.cos(az), math.sin(az), 0.0]), tilt) @ rot_z(yaw)
    if rng.random() < 0.25:
        R = rot_x(180.0) @ R
    return R


def installations(seed: int) -> list[tuple[str, np.ndarray]]:
    """The 12 physical installations of V16 section 3.2 (the random ones are drawn from the role's own seed)."""
    rng = np.random.default_rng(seed + 31)

    def rnd() -> np.ndarray:
        az = float(rng.uniform(0, 2 * math.pi))
        return axis_angle(np.array([math.cos(az), math.sin(az), 0.0]), float(rng.uniform(5.0, 30.0))) @ rot_z(float(rng.choice([90, 180, 270])))

    return [("I00_identity", np.eye(3)), ("I01_tilt_x15", rot_x(15)), ("I02_tilt_x30", rot_x(30)), ("I03_tilt_y15", rot_y(15)), ("I04_tilt_y30", rot_y(30)), ("I05_rot_z180", rot_z(180)),
            ("I06_rot_x180", rot_x(180)), ("I07_rot_y180", rot_y(180)), ("I08_yaw_p90", rot_z(90)), ("I09_yaw_m90", rot_z(-90)), ("I10_random_a", rnd()), ("I11_random_b", rnd()),
            ("I12_x180_tilt20", rot_x(180) @ rot_y(20))]


# ------------------------------------------------------------------------------------------------ sensor model with a general mounting
def sense_rot(rng: np.random.Generator, acc_dyn: np.ndarray, gyr_dyn: np.ndarray, R: np.ndarray, t_end: float, p: dict | None = None):
    """``hwsim_v2.sense`` for a mounting ``R`` (sensor = R vehicle; a det -1 matrix reproduces the mirror variants) and a recording of ``t_end`` seconds. With R = identity and t_end = 3 it draws the
    same random numbers in the same order and returns the same rows as ``hwsim_v2.sense`` (checked by a test). Returns (t_ms, acc (n,3) in g, gyro (n,3) in deg/s)."""
    p = p or {**H.BASE}
    t_int = np.arange(0, t_end, 1 / H.FS_INT)
    g0 = np.array([[0.0], [0.0], [1.0]]) * np.ones((3, len(t_int)))
    spec = R @ (g0 + acc_dyn)
    gyr = R @ gyr_dyn
    bias_a = rng.normal(0, p["bias_sd"], (3, 1))
    bias_g = rng.normal(0, 0.6, (3, 1))
    na = rng.normal(0, H.ACC_ND * p["noise"] * math.sqrt(H.FS_INT / 2), spec.shape)
    ng = rng.normal(0, H.GYR_ND * p["noise"] * math.sqrt(H.FS_INT / 2), gyr.shape)
    a = H.lowpass(spec + bias_a + na, H.DLPF_HZ)
    g = H.lowpass(gyr + bias_g + ng, H.DLPF_HZ)
    a = np.round(np.clip(a, -16, 16) * H.ACC_LSB) / H.ACC_LSB
    g = np.round(np.clip(g, -2000, 2000) * H.GYR_LSB) / H.GYR_LSB
    nominal = np.arange(0, int(t_end * 1000), 1000.0 / p["rate_hz"])
    actual = np.clip(nominal, 0, t_end * 1000 - 1)
    ta = actual / 1000.0
    ai = np.stack([np.interp(ta, t_int, a[k]) for k in range(3)], axis=1)
    gi = np.stack([np.interp(ta, t_int, g[k]) for k in range(3)], axis=1)
    ai = np.round(np.clip(ai, -16, 16) * H.ACC_LSB) / H.ACC_LSB
    return np.round(actual).astype(int), ai, gi


def calibration_drive(rng: np.random.Generator, R: np.ndarray, accelerate: bool, p: dict | None = None) -> dict:
    """Synthetic calibration drive of one installation (V16 section 3.2): 3 s steady, 3 s of straight braking (or acceleration) of 0.25 to 0.45 g with 0.3 s ramps, 3 s steady; road
    vibration of 0.008 g; GPS speed at 1 Hz with 0.1 m/s noise. Vehicle axes: x forward (braking gives negative x acceleration)."""
    t_end = 9.0
    t = np.arange(0, t_end, 1 / H.FS_INT)
    b = float(rng.uniform(0.25, 0.45))
    ramp = np.clip((t - 3.0) / 0.3, 0, 1) * np.clip((6.0 - t) / 0.3, 0, 1)
    sgn = 1.0 if accelerate else -1.0
    a = np.zeros((3, len(t)))
    a[0] = sgn * b * ramp
    for k in range(3):
        a[k] += H.lowpass(rng.normal(0, 1, len(t)), 8.0)[0] * RANDOM_NOISE_G * 3.0
    g = np.zeros((3, len(t)))
    t_ms, acc, gyr = sense_rot(rng, a, g, R, t_end, p)
    v0 = 4.0 if accelerate else 18.0
    speed = v0 + sgn * b * G_MS2 * np.cumsum(ramp) / H.FS_INT
    gps_t = np.arange(0.0, t_end - 0.5, 1.0)
    gps_v = np.interp(gps_t, t, speed) + rng.normal(0, 0.1, len(gps_t))
    return dict(t_ms=t_ms, acc=acc, gyro=gyr, gps_t=gps_t, gps_v=gps_v)


def crash_events(rng: np.random.Generator, R: np.ndarray, n_per_side: int = N_PER_SIDE, p: dict | None = None) -> list[dict]:
    p = p or {**H.BASE}
    out = []
    for side in SIDES:
        for _ in range(n_per_side):
            a, g = H.crash_event(rng, side, p["peak_median"])
            t_ms, acc, gyr = sense_rot(rng, a, g, R, H.T_END, p)
            out.append(dict(side=side, t=t_ms, acc=acc, gyro=gyr, rate_hz=100))
    return out


def build_installation(name: str, R: np.ndarray, seed: int, idx: int, mirror: bool = False) -> dict:
    rng = np.random.default_rng(seed + 1000 * (idx + 1))
    cal = calibration_drive(rng, R, accelerate=bool(idx % 2), p=None)
    ev = crash_events(rng, R, N_PER_SIDE)
    return dict(name=name, R=R, cal=cal, events=ev, mirror=mirror)


# ------------------------------------------------------------------------------------------------ the algorithm
def still_windows(acc: np.ndarray, gyro: np.ndarray, fs: float, p: L1Params) -> np.ndarray:
    """Start indices of the still windows (V16 3.1 item 1 with addendum A1)."""
    n, L = len(acc), int(round(p.still_s * fs))
    if n < L:
        return np.zeros(0, int)
    mag = np.linalg.norm(acc, axis=1)
    gn = np.linalg.norm(gyro, axis=1)
    bad = ((gn >= p.g_still) | (np.abs(mag - 1.0) >= p.a_still)).astype(int)
    cb = np.concatenate([[0], np.cumsum(bad)])
    c1, c2 = np.concatenate([[0], np.cumsum(mag)]), np.concatenate([[0], np.cumsum(mag**2)])
    st = np.arange(0, n - L + 1)
    m1, m2 = (c1[st + L] - c1[st]) / L, (c2[st + L] - c2[st]) / L
    sd = np.sqrt(np.maximum(m2 - m1**2, 0.0))
    return st[((cb[st + L] - cb[st]) == 0) & (sd < p.sd_still)]


def speed_segments(gps_t: np.ndarray, gps_v: np.ndarray, p: L1Params) -> list[tuple[float, float, int]]:
    """Runs of consecutive 1 Hz intervals with |dv/dt| >= a_min of one sign and a length of at least seg_min_s: (t_start, t_end, sign)."""
    dv = np.diff(gps_v) / np.diff(gps_t)
    runs, i = [], 0
    while i < len(dv):
        if abs(dv[i]) >= p.a_min:
            s = int(np.sign(dv[i]))
            j = i
            while j + 1 < len(dv) and abs(dv[j + 1]) >= p.a_min and int(np.sign(dv[j + 1])) == s:
                j += 1
            if gps_t[j + 1] - gps_t[i] >= p.seg_min_s - 1e-9:
                runs.append((float(gps_t[i]), float(gps_t[j + 1]), s))
            i = j + 1
        else:
            i += 1
    return runs


def estimate_mounting(t_ms: np.ndarray, acc: np.ndarray, gyro: np.ndarray, gps_t: np.ndarray, gps_v: np.ndarray, p: L1Params = L1Params(), fs: float = FS) -> dict:
    """Rotation into the vehicle frame from one calibration drive. Returns dict(ok, reason, R_hat (rows x, y, z), z_hat, x_hat, still_start)."""
    t = np.asarray(t_ms, float) / 1000.0
    starts = still_windows(acc, gyro, fs, p)
    if not len(starts):
        return dict(ok=False, reason="no still window")
    segs = speed_segments(np.asarray(gps_t, float), np.asarray(gps_v, float), p)
    if not segs:
        return dict(ok=False, reason="no speed-change segment")
    L = int(round(p.still_s * fs))
    for (t0, t1, sgn) in sorted(segs, key=lambda s: (-(s[1] - s[0]), s[0])):
        before = starts[(starts + L) / fs <= t0 + 1e-9]
        use = before if len(before) else starts
        s0 = int(use[-1])
        m_still = acc[s0 : s0 + L].mean(axis=0)
        z_hat = m_still / np.linalg.norm(m_still)
        sel = (t >= t0 + p.seg_trim_s) & (t <= t1 - p.seg_trim_s)
        if sel.sum() < 10:
            continue
        dyn = acc[sel] - m_still
        horiz = dyn - np.outer(dyn @ z_hat, z_hat)
        h = horiz.mean(axis=0)
        if np.linalg.norm(h) < p.h_min_g:
            continue
        if abs(float((gyro[sel] @ z_hat).mean())) >= p.straight_dps:
            continue
        x_hat = sgn * h / np.linalg.norm(h)
        y_hat = np.cross(z_hat, x_hat)
        R_hat = np.stack([x_hat, y_hat / np.linalg.norm(y_hat), z_hat])
        return dict(ok=True, reason="", R_hat=R_hat, z_hat=z_hat, x_hat=x_hat, still_start=s0)
    return dict(ok=False, reason="no usable segment")


def gravity_angle_deg(z_hat: np.ndarray, acc_window: np.ndarray) -> float:
    """Angle between the stored gravity direction and the mean acceleration of a still window (V16 3.1 item 5)."""
    m = acc_window.mean(axis=0)
    c = float(np.clip(m @ z_hat / np.linalg.norm(m), -1.0, 1.0))
    return math.degrees(math.acos(c))


def is_stale(z_hat: np.ndarray, acc_window: np.ndarray, p: L1Params) -> bool:
    return gravity_angle_deg(z_hat, acc_window) > p.ang_stale


# ------------------------------------------------------------------------------------------------ evaluation on simulated installations
def to_vehicle(acc: np.ndarray, R_hat: np.ndarray) -> np.ndarray:
    """Samples (n, 3) of the sensor frame in the vehicle frame: v = R_hat s for every row."""
    return acc @ R_hat.T


def classify(ev: dict, R_hat: np.ndarray | None, signs: tuple[int, int]) -> str:
    """Impact side of one crash log: the unchanged rule on raw axes (R_hat None) or after the rotation into the vehicle frame."""
    e = ev if R_hat is None else dict(ev, acc=to_vehicle(ev["acc"], R_hat))
    i0 = SE.trigger_index(e)
    if i0 is None:
        return "none"
    return SE.side_rule(e, i0, signs)[0]


def evaluate_installation(inst: dict, p: L1Params, signs: tuple[int, int]) -> dict:
    cal = inst["cal"]
    est = estimate_mounting(cal["t_ms"], cal["acc"], cal["gyro"], cal["gps_t"], cal["gps_v"], p)
    truth = [e["side"] for e in inst["events"]]
    raw = [classify(e, None, signs) for e in inst["events"]]
    if est["ok"]:
        l1 = [classify(e, est["R_hat"], signs) for e in inst["events"]]
    else:
        l1 = ["no decision"] * len(truth)
    ok_raw = np.array([a == b for a, b in zip(raw, truth)])
    ok_l1 = np.array([a == b for a, b in zip(l1, truth)])
    ang = float("nan")
    if est["ok"]:
        # angle between the estimated and the true up and forward directions (true: the columns of R for the vehicle axes)
        R = inst["R"]
        ang = float(math.degrees(math.acos(np.clip(est["z_hat"] @ (R @ np.array([0, 0, 1.0])), -1, 1))))
    return dict(name=inst["name"], n=len(truth), acc_raw=float(ok_raw.mean()), acc_l1=float(ok_l1.mean()), ok_raw=ok_raw, ok_l1=ok_l1, est_ok=bool(est["ok"]), reason=est["reason"], up_err_deg=ang)


def run_role(seed: int, p: L1Params, signs: tuple[int, int], with_mirror: bool = True) -> dict:
    rows = []
    for i, (name, R) in enumerate(installations(seed)):
        rows.append(evaluate_installation(build_installation(name, R, seed, i), p, signs))
    mir = []
    if with_mirror:
        for j, (name, R) in enumerate((("M_flip_x", np.diag([-1.0, 1, 1])), ("M_flip_y", np.diag([1.0, -1, 1])))):
            mir.append(evaluate_installation(build_installation(name, R, seed, 50 + j, mirror=True), p, signs))
    return dict(rows=rows, mirror=mir)


def pooled(rows: list[dict], key: str) -> tuple[float, int, int]:
    k = int(sum(r[key].sum() for r in rows))
    n = int(sum(len(r[key]) for r in rows))
    return k / n, k, n


def boot_pooled_lower(rows: list[dict], key: str, seed: int = 42, nb: int = 2000) -> tuple[float, float]:
    x = np.concatenate([r[key] for r in rows]).astype(float)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, len(x), (nb, len(x)))].mean(1)
    return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))


# ------------------------------------------------------------------------------------------------ NHTSA part (real pulses, synthetic rotation and calibration drive)
def nhtsa_rows(tests: list[dict], p: L1Params, seed: int, n_rot: int = 4, range_g: float = 16.0, w_ms: int = 60, identity: bool = False) -> "pd.DataFrame":  # noqa: F821
    """Front-against-side decision of every (test, rotation) with the raw rotated axes (control) and with L1; ``identity`` uses no rotation (the column ``pred_raw`` is then the X1 pipeline)."""
    import pandas as pd

    from crashguard import nhtsa as N
    from crashguard import severity as S
    from crashguard import severity_study as SS

    rows = []
    rng = np.random.default_rng(seed)
    for t in tests:
        for k in range(n_rot):
            R = np.eye(3) if identity else random_physical_rotation(rng)
            cal = calibration_drive(rng, R, accelerate=bool(rng.integers(0, 2)))
            est = estimate_mounting(cal["t_ms"], cal["acc"], cal["gyro"], cal["gps_t"], cal["gps_v"], p)
            sig = dict(t["sig"], acc=np.asarray(t["sig"]["acc"]) @ R.T)
            y = SS.sensor_signal(sig, range_g, FS) + (R @ np.array([0, 0, N.GRAVITY_Z_G]) - np.array([0, 0, N.GRAVITY_Z_G]))
            w, trig = SS._window(y, FS)
            n = max(int(round(w_ms * FS / 1000.0)), 1)

            def pred(win: np.ndarray) -> str:
                a = S.remove_baseline(win, trig)
                j = a[trig : trig + n, :2].sum(axis=0)
                return "front" if abs(j[0]) >= abs(j[1]) else "side"

            raw = pred(w)
            l1 = pred(to_vehicle(w, est["R_hat"])) if est["ok"] else "no decision"
            rows.append(dict(test_no=t["test_no"], group_mm=t["group_mm"], truth=t["truth"], kind=t["kind"], rot=k, pred_raw=raw, pred_l1=l1, est_ok=bool(est["ok"])))
    return pd.DataFrame(rows)


def balanced(d: "pd.DataFrame", col: str) -> float:  # noqa: F821
    rec = [float((g[col] == c).mean()) for c, g in d.groupby("truth") if len(g)]
    return float(np.mean(rec)) if rec else float("nan")


def nhtsa_heldout_tests() -> tuple[list[dict], list[dict]]:
    from crashguard import direction as D

    tests = D.all_tests()
    role = D.split_groups(tests, "group_mm")
    for t in tests:
        t["role"] = role[t["group_mm"]]
    sc = [t for t in tests if t["truth"] in ("front", "side")]
    return [t for t in sc if t["role"] == "tuning"], [t for t in sc if t["role"] == "heldout"]


def nhtsa_part(tests: list[dict], p: L1Params, seed: int) -> dict:
    from crashguard import boot as B

    d = nhtsa_rows(tests, p, seed)
    out = dict(n_tests=len(tests), n_rows=len(d), est_fail=int((~d.est_ok).sum()))
    for col, nm in (("pred_raw", "raw"), ("pred_l1", "l1")):
        out[f"bacc_{nm}"] = balanced(d, col)
    # grouped bootstrap of the balanced accuracy of L1 over make-and-model groups
    mem = B.group_members(d.group_mm.to_numpy())
    draws = []
    for idx in B._gidx(mem, 2000, 42):
        g = d.iloc[idx]
        draws.append(balanced(g, "pred_l1"))
    out["bacc_l1_lo"], out["bacc_l1_hi"] = float(np.nanquantile(draws, 0.025)), float(np.nanquantile(draws, 0.975))
    return out


# ------------------------------------------------------------------------------------------------ drivers
def _dev() -> None:
    from crashguard import r5_common as R5

    signs = SE.calibration_signs()
    log = []
    for it, p in enumerate(ITERATIONS):
        res = run_role(DEV_SEED, p, signs, with_mirror=False)
        acc, k, n = pooled(res["rows"], "ok_l1")
        raw, _k, _n = pooled(res["rows"], "ok_raw")
        entry = dict(iteration=it, params=asdict(p), dev_pooled_acc_l1=acc, dev_pooled_acc_raw=raw, n=n, per_installation={r["name"]: round(r["acc_l1"], 4) for r in res["rows"]}, est_fail=[r["name"] for r in res["rows"] if not r["est_ok"]])
        tune, _held = nhtsa_heldout_tests()
        entry["dev_nhtsa"] = nhtsa_part(tune, p, 42 + it)
        log.append(entry)
        print(it, round(acc, 4), round(raw, 4), entry["est_fail"], {k2: (round(v, 3) if isinstance(v, float) else v) for k2, v in entry["dev_nhtsa"].items()}, flush=True)
    (R5.TABLES / "r5_l1_dev_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    base = log[0]["dev_pooled_acc_l1"]
    best = max(range(len(log)), key=lambda i: (round(log[i]["dev_pooled_acc_l1"], 9), -i))
    chosen = best if log[best]["dev_pooled_acc_l1"] - base > 0.01 else 0
    (R5.TABLES / "r5_l1_dev_choice.json").write_text(json.dumps(dict(chosen=chosen, params=log[chosen]["params"], rule="V16 3.5: highest pooled development side accuracy; defaults kept unless another iteration is better by more than 1 point"), indent=1), encoding="utf-8")
    print("chosen iteration", chosen)


def _freeze() -> None:
    from crashguard import r5_common as R5

    ch = json.loads((R5.TABLES / "r5_l1_dev_choice.json").read_text(encoding="utf-8"))
    d = R5.freeze_entry("l1", ["src/crashguard/r5_l1.py", "src/crashguard/hwsim_v2.py", "src/crashguard/sh_events.py", "src/crashguard/direction.py", "src/crashguard/nhtsa.py", "src/crashguard/severity.py", "src/crashguard/severity_study.py", "src/crashguard/boot.py"], ch["params"])
    print("frozen l1", d["params_sha256"][:16])


def _held() -> None:
    from scipy.stats import binomtest

    from crashguard import r5_common as R5

    prm = R5.check_frozen("l1")
    p = L1Params(**prm)
    signs = SE.calibration_signs()
    res = run_role(HELD_SEED, p, signs, with_mirror=True)
    rec = R5.Rec("r5.l1.", "src/crashguard/r5_l1.py", "SIMULATED_HW_FORMAT")
    for r in res["rows"] + res["mirror"]:
        rec.add(f"held.{r['name']}.acc_l1", r["acc_l1"], "fraction", f"n = {r['n']}; calibration estimate ok = {r['est_ok']} {r['reason']}")
        rec.add(f"held.{r['name']}.acc_raw", r["acc_raw"], "fraction", "unchanged rule on raw sensor axes (control)")
    acc, k, n = pooled(res["rows"], "ok_l1")
    lo, hi = boot_pooled_lower(res["rows"], "ok_l1")
    raw, _k, _n = pooled(res["rows"], "ok_raw")
    pval = float(binomtest(k, n, 0.90, alternative="greater").pvalue)
    all_ok = all(r["acc_l1"] >= 0.90 for r in res["rows"])
    sim_met = bool(all_ok and lo >= 0.90)
    rec.add("held.sim.pooled_acc_l1", acc, "fraction", f"{k} of {n} horizontal crash events, 13 physical installations; bootstrap interval in _lo and _hi (cluster over events, 2,000, seed 42)")
    rec.add("held.sim.pooled_acc_l1_lo", lo, "fraction")
    rec.add("held.sim.pooled_acc_l1_hi", hi, "fraction")
    rec.add("held.sim.pooled_acc_raw", raw, "fraction", "control: unchanged rule on raw axes")
    rec.add("held.sim.p", pval, "p", "one-sided exact binomial test of H0: pooled accuracy at most 0.90")
    rec.add("held.sim.criterion_met", int(sim_met), "bool", "every installation at least 0.90 and the lower 95% limit of the pooled accuracy at least 0.90")
    rec.add("held.sim.n_installations_below_090", int(sum(r["acc_l1"] < 0.90 for r in res["rows"])), "count")
    rec.add("held.sim.n_estimation_failures", int(sum(not r["est_ok"] for r in res["rows"])), "count", "installations in which no rotation could be estimated (counted wrong)")
    _tune, held = nhtsa_heldout_tests()
    nh = nhtsa_part(held, p, 42)
    nrec = dict(origin="MEASURED_SOFTWARE")
    for k2, v in nh.items():
        rec.add(f"held.nhtsa.{k2}", v, "fraction" if "bacc" in k2 else "count", "real NHTSA pulses at 16 g and 100 Hz; synthetic rotations (seed 42) and synthetic calibration drive", origin=nrec["origin"])
    nh_met = bool(nh["bacc_l1"] >= 0.90 and nh["bacc_l1_lo"] >= 0.85)
    rec.add("held.nhtsa.criterion_met", int(nh_met), "bool", "balanced accuracy at least 0.90 and lower 95% limit (bootstrap over make-and-model groups) at least 0.85", origin="MEASURED_SOFTWARE")
    rec.add("hL1.criterion_met", int(sim_met and nh_met), "bool", "H-L1: simulated part and NHTSA part both met")
    rec.add("hL1.p", pval, "p", "p-value for the Holm family: pooled binomial test of the simulated part")
    rec.add("hL1.contribution", int(sim_met and nh_met), "bool", "G0 rule 4: a contribution only if the NHTSA part also passes; otherwise supplement")
    rec.write()
    print(json.dumps({e["name"]: e["value"] for e in rec.ent if "pooled" in e["name"] or "criterion" in e["name"] or e["name"].endswith(".p")}, indent=1))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"dev": _dev, "freeze": _freeze, "held": _held}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
