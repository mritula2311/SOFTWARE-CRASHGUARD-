"""X4: do the VZCrash labels support impact direction or severity beyond crash against non-crash? Read from the supplied parquet schema and the dataset card (data/raw/card/README.md). No label is invented.
MEASURED_SOFTWARE (a statement about the supplied files)."""
from __future__ import annotations

import glob
from pathlib import Path

import pyarrow.parquet as pq

from crashguard.jp_common import Entries

SRC = "data/raw/data/*.parquet (schema); data/raw/card/README.md"


def main() -> None:
    cols = pq.ParquetFile(sorted(glob.glob("data/raw/data/*.parquet"))[0]).schema_arrow.names
    card = Path("data/raw/card/README.md").read_text(encoding="utf-8").lower()
    E = Entries("x.x4", SRC)
    E.add("columns", ", ".join(cols), "text", "columns of the supplied files")
    E.add("label_classes", "crash, near_miss, normal_driving", "text", "the only event label; reviewed by three experts with dashcam footage, which is not supplied")
    for k in ("direction", "severity", "delta-v", "injury", "impact side"):
        E.add(f"card_mentions.{k.replace(' ', '_').replace('-', '')}", int(k in card), "flag", "1 if the dataset card text contains the word")
    E.add("supports_direction_labels", 0, "flag", "no column or card text gives an impact direction")
    E.add("supports_severity_labels", 0, "flag", "no column or card text gives a severity, delta-V or injury level; the card notes that axis alignment can be suboptimal in some events, so a direction derived from the IMU would not be a label")
    E.add("vehicle_size_only_vehicle_attribute", 1, "flag", "vehiclesize (Light, Medium, Heavy, Unknown) is the only vehicle attribute; there is no vehicle identifier")
    E.flush()
    print(cols)


if __name__ == "__main__":
    main()
