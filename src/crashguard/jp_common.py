"""Shared helpers of the journal-push studies. Every key written here starts with one of PREFIXES, and a study may purge only prefixes of that kind, so no tagged or v2 key can be overwritten."""
from __future__ import annotations

import numpy as np

from crashguard.results import record_many

PREFIXES = ("t13.heldout.", "t13.neardup.", "sel.", "vz.", "x.")


def record_jp(entries: list[dict], purge_prefixes: tuple[str, ...]) -> None:
    for e in entries:
        if not e["name"].startswith(PREFIXES):
            raise ValueError(f"journal-push entries must start with one of {PREFIXES}: {e['name']}")
    for p in purge_prefixes:
        if not p.startswith(PREFIXES):
            raise ValueError(f"journal-push studies may only purge {PREFIXES}: {p}")
    record_many(entries, purge_prefixes=purge_prefixes)


class Entries:
    """Collects result entries of one study with a fixed prefix, source file and default origin."""

    def __init__(self, prefix: str, source: str, origin: str = "MEASURED_SOFTWARE"):
        self.prefix, self.source, self.origin = prefix, source, origin
        self.items: list[dict] = []

    def add(self, name: str, value, unit: str, notes: str = "", origin: str | None = None) -> None:
        if isinstance(value, (np.floating, np.integer)):
            value = value.item()
        if isinstance(value, (bool, np.bool_)):
            value = int(value)
        if isinstance(value, float) and not np.isfinite(value):
            self.items.append(dict(name=f"{self.prefix}.{name}", value="NOT_RUN", unit=unit, origin="NOT_RUN", source_file=self.source, notes=(notes + "; value not finite").strip("; ")))
            return
        self.items.append(dict(name=f"{self.prefix}.{name}", value=value, unit=unit, origin=origin or self.origin, source_file=self.source, notes=notes))

    def ci(self, name: str, triple, unit: str, notes: str = "", d: int = 4, origin: str | None = None) -> None:
        p, lo, hi = triple
        self.add(name, round(float(p), d), unit, notes, origin)
        self.add(name + "_lo", round(float(lo), d), unit, "95% bootstrap interval", origin)
        self.add(name + "_hi", round(float(hi), d), unit, "95% bootstrap interval", origin)

    def flush(self, purge: tuple[str, ...] | None = None) -> None:
        record_jp(self.items, purge if purge is not None else (f"{self.prefix}.",))
