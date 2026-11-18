"""B1: build the CrashClip package files from the pooled records and the study tables (no raw NHTSA signals and no VZCrash data are written).

Writes crashclip/records.csv (record id, NHTSA test number and vehicle role, mode, group hash, fold, reference delta-V and class: values derived from public NHTSA records), crashclip/parts.json
(the 8 parts of the sensor model with the datasheet values, source addresses and dates), crashclip/split.json (fold digests and the severity class limits) and crashclip/baselines/*.csv (copies of the result tables).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from crashguard import config as C
from crashguard import pp_pool as PP
from crashguard.sel_parts import PARTS

OUT = Path("crashclip")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d = PP.load()
    T = PP.table(d)
    T["group_hash"] = [hashlib.sha256(g.encode()).hexdigest()[:12] for g in T.group]
    T["ref_class"] = np.searchsorted(np.array(C.SEV_DV_KMH), T.ref, side="right")
    T["ref_dv_kmh"] = T.ref.round(3)
    T[["rid", "test_no", "src", "mode", "group_hash", "fold", "v", "ref_dv_kmh", "ref_class"]].rename(columns={"v": "closing_speed_kmh", "src": "source_set"}).to_csv(OUT / "records.csv", index=False)
    parts = []
    for p in PARTS:
        dd = dataclasses.asdict(p)
        dd["mg_per_lsb"] = {str(k): v for k, v in dd["mg_per_lsb"].items()}
        parts.append(dd)
    (OUT / "parts.json").write_text(json.dumps(parts, indent=1), encoding="utf-8")
    h = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()  # noqa: E731
    split = dict(seed=PP.SEED, fractions=PP.FRACS, class_limits_kmh=list(C.SEV_DV_KMH), class_names=list(C.SEV_NAMES), n_records=int(len(T)),
                 folds={f: dict(n_records=int((T.fold == f).sum()), n_groups=int(T[T.fold == f].group.nunique()), digest_sha256=h("\n".join(sorted(T[T.fold == f].group.unique())))) for f in PP.FOLDS},
                 note="digest = SHA-256 of the sorted group keys (make + first word of the model, upper case) joined by newlines; group_hash in records.csv = first 12 hex characters of the SHA-256 of the key")
    (OUT / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8")
    (OUT / "baselines").mkdir(exist_ok=True)
    for f in ("p1_sealed.csv", "p1_sealed_by_mode.csv", "p1_validation.csv", "p1_cv.csv", "p2_sealed.csv", "p3a_risk_coverage.csv", "p3b_cells.csv", "p4a_sweep.csv", "p4b_augmentation.csv", "p4c_guarantee.csv", "p4d_cnn.csv", "p_b2_table.csv"):
        if (C.TABLES / f).exists():
            shutil.copy(C.TABLES / f, OUT / "baselines" / f)
    print(len(T), "records;", len(list((OUT / 'baselines').glob('*.csv'))), "baseline tables")


if __name__ == "__main__":
    main()
