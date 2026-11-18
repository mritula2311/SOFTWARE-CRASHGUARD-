"""B2: precision (positive predictive value) of the detectors at several crash prevalences (ANALYTICAL).

PPV = r * pi / (r * pi + f * (1 - pi)), with the measured system recall r and system false-alarm rate f of each detector at its operating point (mean of seeds 0 to 4,
de-duplicated VZCrash test set, threshold chosen on validation) and an assumed prevalence pi. It assumes that the false-alarm rate measured on VZCrash non-crash
events (near-misses and normal driving that the device already selected as harsh) also holds at the stated prevalence; that is an assumption, not a measurement.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crashguard import config as C

PREVALENCES = (0.0002, 0.01, 0.16)
MODELS = (("rf15", "deployed forest (15 trees, depth 6)"), ("rfsel", "10-tree depth-9 candidate"), ("rule", "rule detector"))
TARGETS = (1, 5)


def ppv(recall: float, fpr: float, prevalence: float) -> float:
    tp = recall * prevalence
    fp = fpr * (1.0 - prevalence)
    return tp / (tp + fp) if tp + fp > 0 else float("nan")


def main(path: Path = Path("results/results.json")) -> None:
    from crashguard.results import record_many

    r = {e["name"]: e["value"] for e in json.loads(path.read_text(encoding="utf-8"))}
    src = "results/tables/prevalence_ppv.csv"
    ent, rows = [], []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"prev.{name}", value=value, unit=unit, origin="ANALYTICAL", source_file=src, notes=notes))

    n_pos, n_all = r["n15.test_crashes"], r["n15.test_events"]
    add("test_crash_share", round(n_pos / n_all, 4), "fraction", "crashes / events of the de-duplicated VZCrash test set (the prevalence under which the measured precision was obtained)")
    add("paper_real_world_share", round(143 / 735000, 6), "fraction", "143 confirmed crashes among 735,000 harsh-driving events (VZCrash paper, Section III-D): under 0.02%")
    for m, label in MODELS:
        for t in TARGETS:
            rec, fpr = float(r[f"detector.op.t{t}.{m}.test_recall.mean"]), float(r[f"detector.op.t{t}.{m}.test_fpr.mean"])
            # check: at the test prevalence the formula must reproduce the measured precision
            chk = ppv(rec, fpr, n_pos / n_all)
            add(f"{m}.t{t}.ppv_check_at_test_prevalence", round(chk, 4), "fraction", f"measured mean precision {r[f'detector.op.t{t}.{m}.test_precision.mean']} (means of ratios differ slightly from the ratio of means)")
            for pi in PREVALENCES:
                v = ppv(rec, fpr, pi)
                tag = f"{pi * 100:g}pct".replace(".", "p")
                add(f"{m}.t{t}.pi{tag}.ppv", round(v, 6), "fraction", f"recall {rec:.4f}, false-alarm rate {fpr:.4f}, prevalence {pi}")
                rows.append(dict(model=label, target_fpr_pct=t, recall=rec, fpr=fpr, prevalence=pi, ppv=v))
    C.TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(C.TABLES / "prevalence_ppv.csv", index=False)
    record_many(ent, purge_prefixes=("prev.",))
    print(pd.DataFrame(rows).round(5).to_string())


if __name__ == "__main__":
    main()
