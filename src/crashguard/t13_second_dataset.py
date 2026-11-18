"""T13: a second public crash or impact dataset. NOT_RUN: none could be obtained and opened in this environment (reason recorded in results.json)."""
from __future__ import annotations

REASON = ("searched 2026-11-11 for a second public vehicle crash-test or crash-pulse set; the candidates found were: the Bridge of Knowledge dataset of vehicle centre-of-gravity accelerations from EN 1317 TB32 impacts "
          "(page blocked by an access check, not opened), the Fraunhofer crash-box dataset (component tests, not vehicle pulses, not opened), and NHTSA event-data-recorder report PDFs (reports, not signals). "
          "No dataset was opened, so the sensor-requirement and mis-triage analyses were not repeated on a second source")


def main() -> None:
    from crashguard.results import record_many

    ent = [dict(name="t13.second_dataset.analysis", value="NOT_RUN", unit="", origin="NOT_RUN", source_file="src/crashguard/t13_second_dataset.py", notes=REASON)]
    record_many(ent, purge_prefixes=("t13.",))
    print("NOT_RUN:", REASON)


if __name__ == "__main__":
    main()
