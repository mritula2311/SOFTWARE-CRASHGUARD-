"""Gate for ``run_all.ps1`` and ``make all``: fail loudly if a result is missing without a stated reason.

Errors (exit code 1):
- a result the report cites is absent from results.json, or is NOT_RUN without a note giving the reason;
- any results.json entry marked NOT_RUN with an empty note;
- an entry with an unknown origin label;
- a configured value that the tuning step says must be changed (``*.config_matches_tuning`` = 0).
Warnings are printed for every NOT_RUN that does have a reason, so a blocked check is never silent.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from crashguard import report as R
from crashguard.results import ORIGINS

PATH = Path("results/results.json")
# NOT_RUN entries that are expected on a machine without the car (hardware) or without a C program that can run; they still need a reason.
EXPECTED_PREFIXES = ("hw.", "merge.", "export.benchmark_us_per_call", "hardware.")


def check(path: Path = PATH) -> tuple[list[str], list[str]]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    by = {e["name"]: e for e in entries}
    errors: list[str] = []
    warns: list[str] = []
    for e in entries:
        if e["origin"] not in ORIGINS:
            errors.append(f"{e['name']}: unknown origin {e['origin']!r}")
        if (e["value"] == "NOT_RUN" or e["origin"] == "NOT_RUN"):
            if not str(e.get("notes", "")).strip():
                errors.append(f"{e['name']}: NOT_RUN without a stated reason")
            else:
                warns.append(f"NOT_RUN {e['name']}: {str(e['notes'])[:110]}")
        if e["name"].endswith("config_matches_tuning") and e["value"] != 1:
            errors.append(f"{e['name']} = {e['value']}: update config.py to the tuned value and re-run")
    R.MISSING.clear()
    R.build()
    for name, kind in sorted(set(R.MISSING)):
        if kind == "absent":
            errors.append(f"report cites {name}, which is not in results.json")
        elif not str(by[name].get("notes", "")).strip():
            errors.append(f"report cites {name}, which is NOT_RUN without a stated reason")
    return errors, warns


def main() -> None:
    errors, warns = check()
    for w in warns:
        print("WARNING", w)
    for e in errors:
        print("ERROR  ", e)
    print(f"{len(warns)} NOT_RUN entries with a reason, {len(errors)} errors")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
