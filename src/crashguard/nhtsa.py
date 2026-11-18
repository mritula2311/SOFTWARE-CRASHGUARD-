"""Validation of the severity code on real crash-test data: NHTSA Vehicle Crash Test Database (US government, public domain).

Data come from the public NHTSA NRD API (https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/swagger-ui/index.html). For each test we download the
ISO MME zip (ISO/TS 13499) that the metadata links to, and read the vehicle-CG accelerometer (or, if the test has none, a front sill
accelerometer). The per-channel TSV links were NOT used: for some tests the server returns the same file for every channel. Raw files are
cached in data/raw/nhtsa/ (git-ignored). If the network is not available the step records NOT_RUN and never substitutes other data.

For each test we mimic our sensor (260 Hz front-end bandwidth, saturation at +-MPU_RANGE_G, 40 Hz low-pass, resample to 100 Hz; the
bandwidths are our assumptions) and run the same severity code. Frontal rigid-barrier physics check: v <= delta-V <= 2 v, where v is the
test impact speed (delta-V = v (1 + e), e = coefficient of restitution between 0 and 1).

Exclusion rule (fixed before looking at results): a test is used only if its chosen channel shows a crash pulse (peak above 5 g after the
260 Hz front-end filter). Tests whose channel is flat are counted and listed in the output, not silently dropped.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

from crashguard import config as C
from crashguard import severity as S

API = "https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/api/v1/vehicle-database-test-results"
RAW = C.RAW_DIR / "nhtsa"
UA = {"User-Agent": "Mozilla/5.0"}
FRONT_END_HZ = 260.0  # assumed analog bandwidth of the MEMS accelerometer before its ADC (MPU-6050 DLPF off: 260 Hz, recalled from the datasheet, UNVERIFIED here)
ANTI_ALIAS_HZ = 40.0  # assumed digital low-pass before we sample at 100 Hz (a typical DLPF setting); our assumption
MIN_PULSE_G = 5.0  # exclusion rule: the chosen channel must show a crash pulse
RANGES_G = (8.0, 16.0, 32.0, 64.0)  # sensor ranges compared; 16 g is the MPU-6050 maximum
SPEED_BINS = ((30, 40), (40, 50), (50, 60), (60, 70))
PER_BIN = 60  # tests per speed bin (frontal). Raised from 8 on 2026-11-11 so that every usable test found is used (more power for the held-out evaluation; docs/07_log/DECISIONS.md)
N_SIDE = 60
CACHE = C.PROCESSED / f"nhtsa_selection_{PER_BIN}_{N_SIDE}.joblib"  # parsed signals of the selected tests, so that later steps do not re-read ~850 zip files
GRAVITY_Z_G = 1.0  # added to z so the trigger sees an upright sensor; delta-V does not depend on it (baseline is removed)
NOT_VEHICLE = ("IMPACTOR", "MDB", "BARRIER", "SLED")


def _get(url: str, tries: int = 3, binary: bool = False):
    err: Exception | None = None
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                data = r.read()
            return data if binary else json.loads(data)
        except Exception as e:  # network or server problems: retry, then give up
            err = e
            time.sleep(2)
    raise RuntimeError(f"NHTSA request failed: {url}: {err}")


def search(angle: int, config: str, speed_from: float, speed_to: float, pages: int = 12) -> list[dict]:
    out: list[dict] = []
    for page in range(1, pages + 1):
        d = _get(f"{API}/by-search?pageNumber={page}&count=100&impactAngleFrom={angle}&impactAngleTo={angle}"
                 f"&closingSpeedFrom={speed_from}&closingSpeedTo={speed_to}&testNoFrom=3000")
        res = d.get("results") or []
        out += [t for t in res if t["testConfiguration"] == config and t.get("hasInstrumentationInfo")]
        if len(res) < 100:
            break
    return out


def metadata(test_no: int) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"meta_{test_no}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    m = _get(f"{API}/metadata/{test_no}?isRequestForZipFile=true")["results"][0]
    p.write_text(json.dumps(m), encoding="utf-8")
    return m


def iso_zip(test_no: int, meta: dict) -> zipfile.ZipFile | None:
    url = (meta.get("URL") or {}).get("URL_ISO")
    if not url:
        return None
    p = RAW / f"iso_{test_no}.zip"
    if not p.exists():
        p.write_bytes(_get(url, binary=True))
    try:
        return zipfile.ZipFile(p)
    except zipfile.BadZipFile:
        return None


def _header(text: str) -> dict:
    h = {}
    for line in text.splitlines()[:40]:
        if ":" in line and not re.match(r"^[-\d.eE+ ]+$", line.strip()):
            k, v = line.split(":", 1)
            h[k.strip()] = v.strip()
    return h


def channel_table(z: zipfile.ZipFile) -> list[dict]:
    """Header of every channel file in the ISO MME zip (name of the member, and the fields of ISO/TS 13499)."""
    rows = []
    for name in z.namelist():
        if re.search(r"/Channel/\d+\.\d{3}$", name):
            h = _header(z.read(name)[:2500].decode("latin1"))
            h["member"] = name
            rows.append(h)
    return rows


def pick_channels(rows: list[dict], vehicle_nos: set[int]) -> dict | None:
    """Vehicle-CG accelerometer (X, Y, Z), else a front sill. Direction: Longitudinal, Lateral, Vertical (vehicle axes)."""
    axis = {"Longitudinal": "X", "Lateral": "Y", "Vertical": "Z"}
    want = {str(v) for v in vehicle_nos}
    acc = [r for r in rows if r.get("Dimension") == "Acceleration" and r.get("Data status", "ok") == "ok" and r.get("Direction") in axis
           and r.get("Test object number", "").lstrip("0") in want]
    for attach, test in (("VEHICLE CG", lambda r: "VEHICLE CG" in r.get("Comments", "").upper() or "VEHCCG" in r.get("Channel code", "")),
                         ("SILL - FRONT", lambda r: "SILL" in r.get("Comments", "").upper() and "FRONT" in r.get("Comments", "").upper())):
        by: dict[str, dict] = {}
        for r in (x for x in acc if test(x)):
            by.setdefault(axis[r["Direction"]], r)
        if "X" in by:
            return dict(attach=attach, axes=by)
    return None


def read_channel(z: zipfile.ZipFile, row: dict) -> tuple[np.ndarray, np.ndarray]:
    """(time in s, acceleration in g) of one ISO MME channel file."""
    text = z.read(row["member"]).decode("latin1").splitlines()
    k = next(i for i, ln in enumerate(text) if re.match(r"^\s*[-+]?\d", ln) and ":" not in ln)
    y = np.array([float(x) for x in text[k:] if x.strip()], dtype=np.float64)
    dt = float(row["Sampling interval"])
    t0 = float(row["Time of first sample"])
    unit = row.get("Unit", "").replace(" ", "").lower()
    if unit in ("m/(s*s)", "m/s2", "m/s**2", "m/s^2"):
        y = y / C.G0
    elif unit not in ("g", "gn"):
        raise ValueError(f"unknown acceleration unit {unit!r}")
    return t0 + dt * np.arange(len(y)), y


def _lowpass(x: np.ndarray, fs: float, fc: float) -> np.ndarray:
    return sosfiltfilt(butter(4, fc, fs=fs, output="sos"), x, axis=0)


MIN_PRETRIGGER_S = 0.005  # exclusion rule (added 2026-11-11, docs/07_log/DECISIONS.md): the record must contain at least this long before the trigger, so that a baseline exists


def trigger_index(a_with_g: np.ndarray, fs: float) -> int | None:
    """First sample where |a| (gravity included) exceeds TRIGGER_G. At the original sample rate (10 kHz and up) the detection runs on the signal after the
    260 Hz front-end filter, because a real MEMS sensor cannot report a spike of a few samples; at the 100 Hz sensor rate the signal is already filtered."""
    x = _lowpass(a_with_g, fs, FRONT_END_HZ) if fs > 4 * FRONT_END_HZ else a_with_g
    hit = np.flatnonzero(np.linalg.norm(x, axis=1) > C.TRIGGER_G)
    return int(hit[0]) if len(hit) else None


def load_test(t: dict, side: bool) -> dict | None:
    """Channel choice and signals for one test, or a dict with a ``reason`` if the test cannot be used."""
    meta = metadata(t["testNo"])
    vehs = [v for v in (meta.get("VEHICLE") or [])
            if ((v.get("VEHSPD") or 0) == 0) == side and not any(w in f"{v.get('MAKED', '')} {v.get('MODELD', '')}".upper() for w in NOT_VEHICLE)]
    if not vehs:
        return dict(reason="no vehicle record for the tested car")
    z = iso_zip(t["testNo"], meta)
    if z is None:
        return dict(reason="no ISO MME zip")
    ch = pick_channels(channel_table(z), {v["VEHNO"] for v in vehs})
    if ch is None:
        return dict(reason="no vehicle-CG or front-sill accelerometer")
    try:
        sigs = {ax: read_channel(z, r) for ax, r in ch["axes"].items()}
    except (ValueError, StopIteration) as e:
        return dict(reason=f"channel could not be read ({e})")
    tx = sigs["X"][0]
    acc = np.zeros((len(tx), 3))
    for k, a in enumerate("XYZ"):
        if a in sigs and len(sigs[a][0]) == len(tx):
            acc[:, k] = sigs[a][1]
    fs0 = 1.0 / float(np.median(np.diff(tx)))
    peak = float(np.abs(_lowpass(acc, fs0, FRONT_END_HZ)[:, :2]).max())
    if peak < MIN_PULSE_G:
        return dict(reason=f"chosen channel shows no crash pulse (peak {peak:.2f} g)")
    i_trig = trigger_index(acc + np.array([0, 0, GRAVITY_Z_G]), fs0)
    if i_trig is None or tx[i_trig] - tx[0] < MIN_PRETRIGGER_S:
        return dict(reason="record starts inside the pulse (less than 5 ms before the trigger, no baseline)")
    return dict(t=tx, acc=acc, fs0=fs0, attach=ch["attach"], channels="".join(sorted(ch["axes"])), peak_g=peak, peak_g_raw=float(np.abs(acc[:, :2]).max()))


def _to_window(acc: np.ndarray, fs: float, trig_min_g: float = C.TRIGGER_G) -> tuple[np.ndarray, int]:
    """Cut the 2.8 s firmware-style window (PRE_S before, POST_S after the trigger) with edge-repeat padding, as in features.py."""
    i0 = trigger_index(acc + np.array([0, 0, GRAVITY_Z_G]), fs)
    i0 = 0 if i0 is None else i0
    pre, post = int(round(C.PRE_S * fs)), int(round(C.POST_S * fs))
    idx = np.clip(np.arange(i0 - pre, i0 + post), 0, len(acc) - 1)
    return acc[idx] + np.array([0, 0, GRAVITY_Z_G]), pre


def sensor_like(t: np.ndarray, acc: np.ndarray, range_g: float | None, front_end_hz: float = FRONT_END_HZ) -> tuple[np.ndarray, float]:
    """Model of our sensor: front-end bandwidth (260 Hz), saturation at +-range_g, digital low-pass (40 Hz), 100 Hz sampling."""
    fs0 = 1.0 / float(np.median(np.diff(t)))
    x = _lowpass(acc, fs0, front_end_hz)
    if range_g:
        x = np.clip(x, -range_g, range_g)
    xf = _lowpass(x, fs0, ANTI_ALIAS_HZ)
    t100 = np.arange(t[0], t[-1], 1.0 / C.FS_HZ)
    return np.stack([np.interp(t100, t, xf[:, k]) for k in range(3)], axis=1), float(C.FS_HZ)


def evaluate(sig: dict, test_no: int) -> dict:
    t, acc, fs0 = sig["t"], sig["acc"], sig["fs0"]
    out = dict(test_no=test_no, attach=sig["attach"], channels=sig["channels"], fs_original_hz=round(fs0, 1), n_samples=len(t),
               peak_g=sig["peak_g"], peak_g_raw=sig["peak_g_raw"])
    variants: dict[str, tuple[np.ndarray, float]] = {"orig": (_lowpass(acc, fs0, FRONT_END_HZ), fs0)}  # original rate, after the 260 Hz front end, unclipped: the reference (changed 2026-11-11 from raw: a single raw spike of a few samples set the peak-fraction release level and ended the pulse at once)
    variants["clip260"] = (np.clip(_lowpass(acc, fs0, FRONT_END_HZ), -C.MPU_RANGE_G, C.MPU_RANGE_G), fs0)  # clipping alone, original rate
    variants["hz100"] = sensor_like(t, acc, None)  # sampling alone, unclipped
    for rg in RANGES_G:
        variants[f"hz100_r{rg:g}"] = sensor_like(t, acc, rg)
    variants["hz100_clip"] = variants[f"hz100_r{C.MPU_RANGE_G:g}"]  # the full sensor model at our range
    variants["hz100_r16_fe100"] = sensor_like(t, acc, C.MPU_RANGE_G, 100.0)  # sensitivity: a 100 Hz front end instead of 260 Hz
    for name, (a, fs) in variants.items():
        w, trig = _to_window(a, fs)
        r = S.severity(w, fs, trig)
        for k, v in (("dv", "dv_res_kmh"), ("dvx", "dvx_kmh"), ("dvy", "dvy_kmh"), ("asi", "asi"), ("thiv", "thiv_kmh"), ("pulse", "pulse_ms"),
                     ("peakp", "peak_pulse_g"), ("class", "severity_class")):
            out[f"{k}_{name}"] = r[v]
    return out


_SELECTION: dict[bool, tuple[list, list]] = {}


def select(side: bool) -> list[tuple[dict, dict]]:
    """Frontal barrier tests (4 speed bins, unique vehicles) or side impactor tests, with their signals. Skipped tests: see ``excluded``."""
    if side in _SELECTION:
        return _SELECTION[side][0]
    import joblib

    if CACHE.exists():
        _SELECTION.update(joblib.load(CACHE))
        if side in _SELECTION:
            return _SELECTION[side][0]
    chosen: list[tuple[dict, dict]] = []
    excl: list[dict] = []
    seen: set[tuple] = set()
    if side:
        groups = [sorted(search(270, "IMPACTOR INTO VEHICLE", 40, 70), key=lambda c: c["testNo"])]
        quota = N_SIDE
    else:
        cands = search(0, "VEHICLE INTO BARRIER", 30, 70)
        groups = [sorted((c for c in cands if lo <= c["closingSpeed"] < hi), key=lambda c: c["testNo"]) for lo, hi in SPEED_BINS]
        quota = PER_BIN
    for grp in groups:
        n = 0
        for t in grp:
            key = (t["vehicleMake"], t["vehicleModel"], t["modelYear"])
            if key in seen:
                continue
            sig = load_test(t, side)
            if sig is None or "reason" in sig:
                excl.append(dict(test_no=t["testNo"], kind="side" if side else "frontal", reason=(sig or {}).get("reason", "unknown")))
                continue
            seen.add(key)
            chosen.append((t, sig))
            n += 1
            if n >= quota:
                break
    _SELECTION[side] = (chosen, excl)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump(dict(_SELECTION), CACHE)
    return chosen


def excluded() -> list[dict]:
    return [e for v in _SELECTION.values() for e in v[1]]


def sensor_windows() -> tuple[np.ndarray, np.ndarray]:
    """100 Hz, clipped, firmware-style windows (N, WIN_N, 3) of every selected test, for the C comparison. Gyro is zeros (crash-test CG data has none)."""
    wins = []
    for side in (False, True):
        for _t, sig in select(side):
            a, fs = sensor_like(sig["t"], sig["acc"], C.MPU_RANGE_G)
            w, _trig = _to_window(a, fs)
            wins.append(w.astype(np.float32))
    acc_w = np.stack(wins) if wins else np.zeros((0, C.WIN_N, 3), np.float32)
    return acc_w, np.zeros_like(acc_w)


def run() -> pd.DataFrame:
    rows = []
    for side in (False, True):
        for t, sig in select(side):
            r = evaluate(sig, t["testNo"])
            r.update(kind="side" if side else "frontal", impact_speed_kmh=float(t["closingSpeed"]), make=t["vehicleMake"], model=t["vehicleModel"],
                     year=t["modelYear"], test_type=t["testType"], impact_angle=t["impactAngle"])
            rows.append(r)
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> dict:
    out: dict = {}
    f = df[df.kind == "frontal"].copy()
    out["n_frontal"], out["n_side"] = int(len(f)), int((df.kind == "side").sum())
    ex = excluded()
    out["n_excluded_no_pulse"] = int(sum("no crash pulse" in e["reason"] for e in ex))
    out["n_excluded_other"] = int(sum("no crash pulse" not in e["reason"] for e in ex))
    v = f.impact_speed_kmh
    for name, col in (("hz100_clip", "dv_hz100_clip"), ("hz100", "dv_hz100"), ("orig", "dv_orig")):
        dv = f[col]
        inside = (dv >= v) & (dv <= 2 * v)
        out[f"band_share.{name}"] = float(inside.mean())
        out[f"band_count.{name}"] = int(inside.sum())
        out[f"below_v_count.{name}"] = int((dv < v).sum())
        out[f"above_2v_count.{name}"] = int((dv > 2 * v).sum())
        e = dv / v - 1
        out[f"restitution_median.{name}"] = float(e.median())
        out[f"restitution_p10.{name}"] = float(e.quantile(0.1))
        out[f"restitution_p90.{name}"] = float(e.quantile(0.9))
        out[f"corr_dv_v.{name}"] = float(np.corrcoef(v, dv)[0, 1])
    for name in ["clip260", "hz100"] + [f"hz100_r{r:g}" for r in RANGES_G] + ["hz100_r16_fe100"]:
        err = 100 * (f[f"dv_{name}"] - f.dv_orig) / f.dv_orig
        out[f"dv_err_vs_orig_median_pct.{name}"] = float(err.median())
        out[f"dv_err_vs_orig_abs_p90_pct.{name}"] = float(err.abs().quantile(0.9))
        out[f"dv_err_vs_orig_max_abs_pct.{name}"] = float(err.abs().max())
        out[f"asi_err_vs_orig_median_pct.{name}"] = float(np.median(100 * (f[f"asi_{name}"] - f.asi_orig) / f.asi_orig))
    out["fs_original_median_hz"] = float(df.fs_original_hz.median())
    out["peak_g_median"] = float(f.peak_g.median())
    out["peak_g_raw_median"] = float(f.peak_g_raw.median())
    out["clipped_tests_share"] = float((f.peak_g > C.MPU_RANGE_G).mean())
    return out


def ci_entries(df: pd.DataFrame, src: str) -> list[dict]:
    """95% bootstrap intervals (1,000 resamples of tests) for the validation results: physics-band share, delta-V error median and 90th percentile, ASI error median."""
    from crashguard import boot as B

    f = df[df.kind == "frontal"]
    v = f.impact_speed_kmh.to_numpy()
    out = []

    def put(name, lo, hi, unit):
        for suf, val in (("_lo", lo), ("_hi", hi)):
            out.append(dict(name=f"nhtsa.{name}{suf}", value=round(float(val), 4), unit=unit, origin="MEASURED_SOFTWARE", source_file=src, notes="95% bootstrap interval over tests, 1,000 resamples"))

    for name, col in (("orig", "dv_orig"), ("hz100", "dv_hz100"), ("hz100_clip", "dv_hz100_clip")):
        inside = (f[col].to_numpy() >= v) & (f[col].to_numpy() <= 2 * v)
        _p, lo, hi = B.ci(inside, np.mean)
        put(f"band_share.{name}", lo, hi, "fraction")
    for name in ["clip260", "hz100"] + [f"hz100_r{r:g}" for r in RANGES_G] + ["hz100_r16_fe100"]:
        err = 100 * (f[f"dv_{name}"] - f.dv_orig) / f.dv_orig
        _p, lo, hi = B.ci(err.to_numpy(), np.median)
        put(f"dv_err_vs_orig_median_pct.{name}", lo, hi, "percent")
        _p, lo, hi = B.ci(err.abs().to_numpy(), B.p90)
        put(f"dv_err_vs_orig_abs_p90_pct.{name}", lo, hi, "percent")
        aerr = 100 * (f[f"asi_{name}"] - f.asi_orig) / f.asi_orig
        _p, lo, hi = B.ci(aerr.to_numpy(), np.median)
        put(f"asi_err_vs_orig_median_pct.{name}", lo, hi, "percent")
    return out


def figure(df: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    f = df[df.kind == "frontal"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))
    ax = axes[0]
    ax.scatter(f.impact_speed_kmh, f.dv_hz100_clip, s=16, color=COLORS[0], label="100 Hz, clipped (sensor model)")
    ax.scatter(f.impact_speed_kmh, f.dv_orig, s=16, marker="^", color=COLORS[1], label="original rate, unclipped")
    x = np.array([f.impact_speed_kmh.min() - 2, f.impact_speed_kmh.max() + 2])
    ax.plot(x, x, "k--", lw=0.8, label="delta-V = v")
    ax.plot(x, 2 * x, "k:", lw=0.8, label="delta-V = 2 v")
    ax.set_xlabel("Test impact speed v (km/h)")
    ax.set_ylabel("Computed delta-V (km/h)")
    ax.set_title("Frontal barrier tests", fontsize=9)
    ax.legend(fontsize=7)
    ax = axes[1]
    for i, (name, lab) in enumerate((("hz100", "100 Hz, no clipping"), ("hz100_r64", "100 Hz, range 64 g"), ("hz100_r32", "100 Hz, range 32 g"),
                                     ("hz100_r16", "100 Hz, range 16 g"), ("hz100_r8", "100 Hz, range 8 g"))):
        err = 100 * (f[f"dv_{name}"] - f.dv_orig) / f.dv_orig
        ax.scatter(f.impact_speed_kmh, err, s=14, color=COLORS[i], label=lab)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("Test impact speed v (km/h)")
    ax.set_ylabel("Delta-V change from original (%)")
    ax.legend(fontsize=6)
    ax = axes[2]
    ax.scatter(f.peak_g, f.asi_hz100_clip, s=16, color=COLORS[0], label="100 Hz, clipped")
    ax.scatter(f.peak_g, f.asi_orig, s=16, marker="^", color=COLORS[1], label="original")
    ax.axvline(C.MPU_RANGE_G, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("Peak horizontal acceleration after 260 Hz front-end filter (g)")
    ax.set_ylabel("ASI")
    ax.legend(fontsize=7)
    fig.suptitle("NHTSA crash tests (MEASURED_SOFTWARE)", fontsize=9)
    save(fig, "nhtsa_validation")


def write_dataset_doc(df: pd.DataFrame) -> None:
    """Record test numbers, channels and download date in docs/05_data_code/DATASET.md (generated block)."""
    start, end = "<!-- nhtsa:start -->", "<!-- nhtsa:end -->"
    rows = ["| Test | Kind | Vehicle | Impact speed (km/h) | Channel | Axes | Original rate (Hz) |", "|---|---|---|---|---|---|---|"]
    for r in df.sort_values("test_no").itertuples():
        rows.append(f"| {r.test_no} | {r.kind} | {r.year} {r.make} {r.model} | {r.impact_speed_kmh:g} | {r.attach} | {r.channels} | {r.fs_original_hz:g} |")
    ex = excluded()
    blk = "\n".join([start, "", "## NHTSA Vehicle Crash Test Database (severity validation)",
                     f"Downloaded {date.today().isoformat()} from the public NHTSA NRD API (https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/swagger-ui/index.html), "
                     "US government data (public domain). The ISO MME zip of each test (ISO/TS 13499) is cached in `data/raw/nhtsa/` (git-ignored); accelerations are converted from m/s^2 to g. "
                     "Channels: vehicle-CG accelerometer if the test has one, otherwise the front sill accelerometer, vehicle axes, status ok. "
                     "The per-channel TSV links were not used (the server returned the same file for every channel of some tests). "
                     "Sensor-like processing (assumed): 260 Hz front-end low-pass, clip to +-16 g, 40 Hz low-pass, resample to 100 Hz. "
                     f"Tests are used only if the chosen channel shows a crash pulse (peak above {MIN_PULSE_G:g} g); {len(ex)} candidate tests were skipped for that or another reason "
                     "(listed in `results/tables/nhtsa_excluded.csv`).", "", *rows, "", end])
    p = Path("docs/05_data_code/DATASET.md")
    s = p.read_text(encoding="utf-8")
    if start in s:
        i, j = s.index(start), s.index(end) + len(end)
        s = s[:i] + blk + s[j:]
    else:
        s = s.rstrip("\n") + "\n\n" + blk + "\n"
    p.write_text(s, encoding="utf-8")


def main() -> None:
    from crashguard.results import record_many

    src = "results/tables/nhtsa_tests.csv"
    try:
        df = run()
        if df.empty:
            raise RuntimeError("no usable tests")
    except RuntimeError as err:
        print(f"NOT_RUN: {err}")
        record_many([dict(name="nhtsa.validation", value="NOT_RUN", unit="", origin="NOT_RUN", source_file=src,
                          notes=f"NHTSA download failed or returned nothing ({str(err)[:150]}). Download tests manually from https://www.nhtsa.gov/research-data/research-testing-databases and place the ISO MME zips in data/raw/nhtsa/ as iso_<test>.zip")])
        return
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.TABLES / "nhtsa_tests.csv", index=False)
    pd.DataFrame(excluded()).to_csv(C.TABLES / "nhtsa_excluded.csv", index=False)
    s = summarise(df)
    ent = []
    for k, v in s.items():
        unit = ("tests" if k.startswith("n_") or "count" in k else "fraction" if "share" in k or k.startswith("restitution") or k.startswith("corr")
                else "percent" if "pct" in k else "Hz" if k.startswith("fs_") else "g")
        ent.append(dict(name=f"nhtsa.{k}", value=round(float(v), 4) if not isinstance(v, int) else v, unit=unit, origin="MEASURED_SOFTWARE", source_file=src,
                        notes="NHTSA crash tests; 'orig' = original sample rate, unclipped; 'hz100' = resampled to 100 Hz; 'hz100_clip' = also saturated at the sensor range; 'r<g>' = other ranges; physics band on frontal barrier tests"))
    ent += ci_entries(df, src)
    record_many(ent)
    figure(df)
    write_dataset_doc(df)
    print(pd.Series(s).round(3).to_string())


if __name__ == "__main__":
    main()
