"""Event loading and the repository's trigger and impact-side rules, applied to simulated hardware-format logs (Part S, SIMULATED_HW_FORMAT)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from crashguard import config as C
from crashguard import direction as D
from crashguard import sh_load as L

VARIANT_ROOT = Path("data/simulated_hardware/variants")
SUPPLIED = Path("data/simulated_hardware")
HORIZONTAL = ("front", "rear", "left", "right")
SIDE_WINDOW_MS = float(D.W_DEFAULT)  # 60 ms after the trigger


def calibration_signs() -> tuple[int, int]:
    """Signs stored by the NHTSA axis study (x1.axis.flip_x, x1.axis.flip_y); read from results.json."""
    r = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"].startswith("x1.axis.flip")}
    return int(r["x1.axis.flip_x"]), int(r["x1.axis.flip_y"])


def load_dir(root: Path, relaxed: bool = False) -> list[dict]:
    """All sensor logs under ``root/sensor_logs``. ``relaxed`` allows gaps and jitter in the time axis (strictly increasing is still required)."""
    out = []
    for p in sorted((root / "sensor_logs").glob("*.json")):
        d = L.load_json(p)
        arr = L.check_sensor(d, p.name, dt_ms=None if relaxed else 10.0)
        out.append(dict(name=d["test_id"], label=d["true_label"], side=d.get("impact_side"), kind=d.get("event_type"), rate_hz=d.get("rate_hz", 100), **arr))
    return out


def trigger_index(ev: dict, thr: float = C.TRIGGER_G) -> int | None:
    mag = np.linalg.norm(ev["acc"], axis=1)
    hit = np.flatnonzero(mag > thr)
    return int(hit[0]) if len(hit) else None


def side_rule(ev: dict, i0: int, signs: tuple[int, int], w_ms: float = SIDE_WINDOW_MS) -> tuple[str, float]:
    """The repository's firmware rule on one event: pre-trigger mean removed, horizontal impulse over the initial ``w_ms`` after the trigger, theta = atan2(-Jy, -Jx)."""
    t, a = ev["t"].astype(float), ev["acc"]
    pre = a[:i0] if i0 > 0 else a[:1]
    base = pre[max(0, len(pre) - 100):].mean(axis=0)  # up to 1 s at 100 Hz (fewer samples at 10 Hz)
    seg = np.flatnonzero((t >= t[i0]) & (t < t[i0] + w_ms))
    nxt = np.append(t[1:], t[-1] + 1000.0 / ev["rate_hz"])
    dt = (nxt[seg] - t[seg]) / 1000.0
    jx = float(((a[seg, 0] - base[0]) * dt).sum()) * signs[0]
    jy = float(((a[seg, 1] - base[1]) * dt).sum()) * signs[1]
    th = D.theta_deg(jx, jy)
    return D.sector(th), th


def resample_window(ev: dict, fs: float = float(C.FS_HZ)) -> tuple[np.ndarray, np.ndarray]:
    """Acceleration (n,3) in g and gyro (n,3) in deg/s on a regular 100 Hz grid by linear interpolation of the logged samples."""
    tt = np.arange(0.0, ev["t"][-1] + 1e-9, 1000.0 / fs)
    a = np.stack([np.interp(tt, ev["t"], ev["acc"][:, k]) for k in range(3)], axis=1)
    g = np.stack([np.interp(tt, ev["t"], ev["gyro"][:, k]) for k in range(3)], axis=1)
    return a, g
