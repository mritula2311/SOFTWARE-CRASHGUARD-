"""Schema loader for the simulated hardware-format logs (Part S, evidence label SIMULATED_HW_FORMAT).

Reads ``data/simulated_hardware/`` (or a variant directory). Every file is checked: it parses; the sensor timestamps are strictly increasing and, in the base set, exactly
10 ms apart; every value is finite and every accelerometer value is inside +-16 g; every JSON carries a ``data_origin`` field that contains SIMULATED. Nothing here reads
``data/hardware/``. The files are simulated by ``hwsim.py`` (seed 20261114); they are never hardware evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

BASE = Path("data/simulated_hardware")
SENSOR_COLS = ["t_ms", "ax_g", "ay_g", "az_g", "gx_dps", "gy_dps", "gz_dps"] + [f"sw420_{k}" for k in range(1, 7)]
RANGE_G = 16.0


class SchemaError(ValueError):
    pass


def load_json(path: Path) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if "SIMULATED" not in str(d.get("data_origin", "")):
        raise SchemaError(f"{path}: data_origin missing or does not contain SIMULATED")
    return d


def check_sensor(d: dict, path: str = "", dt_ms: float | None = 10.0, tol_ms: float = 0.0) -> dict:
    """Validate one sensor log. dt_ms None: only check strictly increasing time. Returns the arrays (t, acc, gyro, sw)."""
    if d.get("columns") != SENSOR_COLS:
        raise SchemaError(f"{path}: columns {d.get('columns')}")
    a = np.asarray(d["rows"], dtype=float)
    if a.ndim != 2 or a.shape[1] != len(SENSOR_COLS):
        raise SchemaError(f"{path}: bad row shape {a.shape}")
    if not np.all(np.isfinite(a)):
        raise SchemaError(f"{path}: non-finite value")
    t = a[:, 0]
    dt = np.diff(t)
    if np.any(dt <= 0):
        raise SchemaError(f"{path}: timestamps not strictly increasing")
    if dt_ms is not None and np.any(np.abs(dt - dt_ms) > tol_ms):
        raise SchemaError(f"{path}: timestamps are not {dt_ms} ms apart (min {dt.min()}, max {dt.max()})")
    if np.abs(a[:, 1:4]).max() > RANGE_G + 1e-9:
        raise SchemaError(f"{path}: accelerometer value outside +-{RANGE_G} g")
    if not np.isin(a[:, 7:13], (0, 1)).all():
        raise SchemaError(f"{path}: SW-420 columns must be 0 or 1")
    return dict(t=t, acc=a[:, 1:4], gyro=a[:, 4:7], sw=a[:, 7:13])


def load_all(root: Path = BASE) -> dict:
    """Load and check every sensor and protocol file under ``root``. Returns counts and the parsed content."""
    sensors, protocols = {}, {}
    for p in sorted((root / "sensor_logs").glob("*.json")):
        d = load_json(p)
        sensors[p.stem] = (d, check_sensor(d, p.name))
    for p in sorted((root / "protocol_logs").glob("*.json")):
        protocols[p.stem] = load_json(p)
    return dict(sensors=sensors, protocols=protocols)


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest(root: Path = BASE) -> list[tuple[str, str]]:
    """SHA-256 of every file under root except the manifest itself, sorted by relative path."""
    out = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256" and "variants" not in p.relative_to(root).parts and "__pycache__" not in p.parts:
            out.append((p.relative_to(root).as_posix(), sha256(p)))
    return out


def write_manifest(root: Path = BASE) -> None:
    (root / "MANIFEST.sha256").write_text("".join(f"{h}  {n}\n" for n, h in manifest(root)), encoding="utf-8", newline="\n")


def verify_manifest(root: Path = BASE) -> list[str]:
    bad = []
    for ln in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        h, n = ln.split("  ", 1)
        if not (root / n).exists() or sha256(root / n) != h:
            bad.append(n)
    return bad
