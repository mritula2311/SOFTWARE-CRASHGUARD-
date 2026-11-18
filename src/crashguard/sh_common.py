"""Shared helpers for the combined run (Parts S and R): decision log, results writer with the SIMULATED_HW_FORMAT label."""
from __future__ import annotations

from pathlib import Path

DECISIONS = Path("docs/07_log/DECISIONS.md")
DATE = "2026-11-14"


def log(decision: str, reason: str, effect: str) -> None:
    """Append one dated row to docs/07_log/DECISIONS.md (the table has the columns Date, Decision, Reason, Effect on results)."""
    cell = lambda s: " ".join(str(s).split()).replace("|", "/")  # noqa: E731
    with DECISIONS.open("a", encoding="utf-8") as f:
        f.write(f"| {DATE} | {cell(decision)} | {cell(reason)} | {cell(effect)} |\n")
