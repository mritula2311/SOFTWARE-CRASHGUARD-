"""Record the Python version, operating system and package versions in results.json (origin ANALYTICAL: they describe the environment, not a result)."""
from __future__ import annotations

import platform
import sys
from importlib import metadata

from crashguard.results import record_many

PACKAGES = ("numpy", "pandas", "scipy", "scikit-learn", "lightgbm", "matplotlib", "pyarrow", "pytest", "hypothesis", "ruff", "ziglang")


def main() -> None:
    src = "src/crashguard/env_record.py"
    ent = [dict(name="env.python_version", value=platform.python_version(), unit="text", origin="ANALYTICAL", source_file=src, notes="interpreter that ran the pipeline"),
           dict(name="env.platform", value=platform.platform(), unit="text", origin="ANALYTICAL", source_file=src, notes="operating system"),
           dict(name="env.machine", value=platform.machine(), unit="text", origin="ANALYTICAL", source_file=src),
           dict(name="env.executable_in_venv", value=bool(sys.prefix != getattr(sys, "base_prefix", sys.prefix)), unit="bool", origin="ANALYTICAL", source_file=src)]
    for p in PACKAGES:
        try:
            ent.append(dict(name=f"env.package.{p}", value=metadata.version(p), unit="version", origin="ANALYTICAL", source_file=src, notes="pinned in requirements.txt and requirements.lock"))
        except metadata.PackageNotFoundError:
            ent.append(dict(name=f"env.package.{p}", value="NOT_RUN", unit="version", origin="NOT_RUN", source_file=src, notes="package not installed"))
    record_many(ent, purge_prefixes=("env.",))
    print({e["name"]: e["value"] for e in ent})


if __name__ == "__main__":
    main()
