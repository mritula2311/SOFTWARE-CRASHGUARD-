"""Import the JSON written by ``scripts/c_checks.sh`` (run on Linux, under WSL or on a CI runner) into results/results.json.

    python -m crashguard.merge_c_checks build/c_checks_wsl.json [--label linux_gcc]

Every imported value is MEASURED_SOFTWARE with the platform and compiler in its note. Keys: ``cchecks.<label>.<bundle>.<check>.<what>`` where bundle is ``c_bundle``
(synthetic inputs) or ``c_bundle_real`` (the real test events and windows, built locally by ``python -m crashguard.c_bundle --real``). A check that could not be compiled or run
is recorded as NOT_RUN with its reason. The Windows entries (``export.*``, ``candidate.*``, ``export_severity.*``) are untouched: they stay NOT_RUN with their reason unless this JSON is supplied.
Equivalence of the 10 x 9 candidate forest is reported only from ``cchecks.*.c_bundle_real.forest_10x9`` (or the Windows ``candidate.max_abs_diff`` when that ran).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from crashguard.results import record_many

SRC = "scripts/c_checks.sh"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def default_label(doc: dict) -> str:
    cc = str(doc.get("compiler_version", doc.get("compiler", "cc"))).lower()
    kind = "gcc" if "gcc" in cc else "clang" if "clang" in cc else slug(str(doc.get("compiler", "cc")))
    return f"{slug(str(doc.get('system', 'unknown')))}_{kind}"


def entries(doc: dict, label: str, source: str = SRC) -> list[dict]:
    plat = f"{doc.get('platform', '?')}; {doc.get('compiler_version', doc.get('compiler', '?'))}"
    pre = f"cchecks.{label}"
    ent = [dict(name=f"{pre}.platform", value=str(doc.get("platform", "?")), unit="text", origin="MEASURED_SOFTWARE", source_file=source, notes="platform on which the C checks were compiled and run"),
           dict(name=f"{pre}.compiler", value=str(doc.get("compiler_version", doc.get("compiler", "?"))), unit="text", origin="MEASURED_SOFTWARE", source_file=source, notes=plat),
           dict(name=f"{pre}.n_checks", value=len(doc["checks"]), unit="checks", origin="MEASURED_SOFTWARE", source_file=source, notes=plat),
           dict(name=f"{pre}.all_ran", value=bool(doc.get("all_ran")), unit="bool", origin="MEASURED_SOFTWARE", source_file=source, notes=plat),
           dict(name=f"{pre}.all_passed", value=bool(doc.get("all_passed")), unit="bool", origin="MEASURED_SOFTWARE", source_file=source, notes=plat)]
    for c in doc["checks"]:
        base = f"{pre}.{c['bundle']}.{c['name']}"
        kind = "real test events and windows" if c["bundle"].endswith("real") else "synthetic inputs"
        note = f"C compiled and run on {plat}; {kind}; expected values from the Python reference"
        if not c.get("ran"):
            ent.append(dict(name=f"{base}.max_abs_diff", value="NOT_RUN", unit="", origin="NOT_RUN", source_file=source, notes=f"{c.get('reason', 'not run')[:200]} ({plat})"))
            continue
        ent.append(dict(name=f"{base}.n_rows", value=int(c["n_rows"]), unit="rows", origin="MEASURED_SOFTWARE", source_file=source, notes=note))
        ent.append(dict(name=f"{base}.passes", value=bool(c["passes"]), unit="bool", origin="MEASURED_SOFTWARE", source_file=source, notes=note + "; pass rule = the tolerances in c_bundle/manifest.json (ours) and exact agreement of discrete fields"))
        for f, r in c.get("fields", {}).items():
            ent.append(dict(name=f"{base}.max_abs_diff.{f}", value=float(r["max_abs_diff"]), unit="field units", origin="MEASURED_SOFTWARE", source_file=source, notes=note))
            if "mismatches" in r:
                ent.append(dict(name=f"{base}.mismatches.{f}", value=int(r["mismatches"]), unit="rows", origin="MEASURED_SOFTWARE", source_file=source, notes=note))
        if "decision_mismatches" in c:
            ent.append(dict(name=f"{base}.decision_mismatches", value=int(c["decision_mismatches"]), unit="rows", origin="MEASURED_SOFTWARE", source_file=source, notes=note + "; crash decision at the validation threshold"))
    return ent


def merge(path: Path, label: str | None = None, results: Path | None = None) -> str:
    doc = json.loads(path.read_text(encoding="utf-8"))
    label = label or default_label(doc)
    kw = {"path": results} if results else {}
    record_many(entries(doc, label), purge_prefixes=(f"cchecks.{label}.",), **kw)
    return label


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit("usage: python -m crashguard.merge_c_checks <c_checks.json> [--label NAME]")
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else None
    if label in args:
        args.remove(label)
    used = merge(Path(args[0]), label)
    print(f"merged {args[0]} as cchecks.{used}.*")


if __name__ == "__main__":
    main()
