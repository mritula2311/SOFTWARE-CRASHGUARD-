"""Shared helpers of the finishing branch (keys start with ``f.``; no existing key is changed)."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path

from crashguard.results import record_many

DEC = Path("docs/07_log/DECISIONS.md")


def dec(decision: str, reason: str, effect: str, date: str | None = None) -> None:
    """Append one row to docs/07_log/DECISIONS.md."""
    d = date or _dt.date.today().isoformat()
    row = f"| {d} | {decision.strip()} | {reason.strip()} | {effect.strip()} |\n"
    t = DEC.read_text(encoding="utf-8")
    if not t.endswith("\n"):
        t += "\n"
    DEC.write_text(t + row, encoding="utf-8")


class Entries:
    """Collect results.json entries under one prefix and write them at the end."""

    def __init__(self, prefix: str, source: str):
        self.prefix, self.source, self.ent = prefix, source, []

    def add(self, name: str, value, unit: str, origin: str, notes: str = "") -> None:
        self.ent.append(dict(name=f"{self.prefix}.{name}", value=value, unit=unit, origin=origin, source_file=self.source, notes=notes))

    def write(self, purge: bool = True) -> None:
        record_many(self.ent, purge_prefixes=(self.prefix + ".",) if purge else ())
