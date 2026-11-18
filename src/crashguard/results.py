"""Single writer for results/results.json. Every entry carries an origin label."""
from __future__ import annotations

import json
from pathlib import Path

RESULTS_PATH = Path("results/results.json")
ORIGINS = {"MEASURED_SOFTWARE", "SIMULATED", "SIMULATED_HW_FORMAT", "TRACE_DRIVEN", "FORMAL", "ANALYTICAL", "EMULATED", "HARDWARE", "NOT_RUN"}  # SIMULATED_HW_FORMAT: code run on simulated hardware-format logs; never hardware evidence. TRACE_DRIVEN: measured link traces replayed in software. FORMAL: proof or exhaustive model check. EMULATED: run in an emulator, not on a device


def record(
    name: str,
    value: object,
    unit: str,
    origin: str,
    source_file: str,
    notes: str = "",
    path: Path = RESULTS_PATH,
) -> None:
    """Add or replace one entry (keyed by ``name``)."""
    if origin not in ORIGINS:
        raise ValueError(f"origin must be one of {sorted(ORIGINS)}, got {origin!r}")
    entries = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    entries = [e for e in entries if e["name"] != name]
    entries.append(
        {"name": name, "value": value, "unit": unit, "origin": origin, "source_file": source_file, "notes": notes}
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def record_many(entries: list[dict], path: Path = RESULTS_PATH, purge_prefixes: tuple[str, ...] = ()) -> None:
    """Add or replace many entries at once. Each dict has the keyword arguments of ``record``.

    ``purge_prefixes``: entries whose name starts with one of these are removed first, so a study that is re-run leaves no stale keys from an older run behind.
    """
    for e in entries:
        if e["origin"] not in ORIGINS:
            raise ValueError(f"origin must be one of {sorted(ORIGINS)}, got {e['origin']!r}")
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    new = {e["name"]: {"name": e["name"], "value": e["value"], "unit": e["unit"], "origin": e["origin"],
                       "source_file": e["source_file"], "notes": e.get("notes", "")} for e in entries}
    merged = [e for e in old if e["name"] not in new and not e["name"].startswith(purge_prefixes)] + list(new.values())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
