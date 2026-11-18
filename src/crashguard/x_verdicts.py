"""Holm correction over the seven tested hypotheses of docs/02_preregistration/PREREGISTRATION_V3.md (H-X1, H-X2, H-X3, H-X5, H-X6, H-X7, H-X8) and the verdict of each. Reads only results/results.json.
Rule (from the preregistration): SUPPORTED if the criterion is met and the Holm-adjusted p-value is below 0.05; MIXED if the criterion is met and it is not; NOT SUPPORTED otherwise. No threshold is chosen here."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crashguard import config as C
from crashguard.jp_common import Entries
from crashguard.v2_common import holm

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
KEYS = {"H-X1": "x1.hX1", "H-X2": "x2.hX2", "H-X3": "x3.hX3", "H-X5": "x5.hX5", "H-X6": "x6.hX6", "H-X7": "x7.hX7", "H-X8": "x8.hX8"}
WHY = {"H-X1": "the AP condition holds but the flash estimate falls by 22.2% against the required 30%", "H-X2": "no gain over the 2 g threshold at an equal non-crash trigger rate",
       "H-X3": "the gain is below 1 point and its interval includes zero", "H-X5": "the rank correlation of fill + ridge with the reference delta-V is below 0.90 and its lower end below 0.85",
       "H-X6": "", "H-X7": "no preregistered pair and fusion rule reaches a lower end of 0.80", "H-X8": "the criterion holds at the 1% target only (at 5% the sequential rule is slower and its recall lower)"}


def main() -> None:
    p_raw = {h: float(R[f"x.{k}.p_raw"]) for h, k in KEYS.items()}
    adj = holm(p_raw)
    E = Entries("x.holm", "results/tables/x_verdicts.csv")
    rows = []
    for h, k in KEYS.items():
        crit = int(R[f"x.{k}.criterion_met"]) == 1
        sig = adj[h] < 0.05
        v = "SUPPORTED" if crit and sig else ("MIXED" if crit else "NOT SUPPORTED")
        E.add(f"{h}.p_raw", round(p_raw[h], 4), "probability", "one-sided bootstrap p-value of the statistical condition")
        E.add(f"{h}.p_holm", round(adj[h], 4), "probability", "Holm-adjusted over the seven hypotheses")
        E.add(f"{h}.verdict", v, "verdict", WHY[h] if v != "SUPPORTED" and WHY[h] else "criterion met and the Holm-adjusted p-value is below 0.05")
        rows.append(dict(hypothesis=h, verdict=v, p_raw=p_raw[h], p_holm=adj[h], criterion_met=crit))
    E.add("family_size", len(KEYS), "hypotheses", "H-X1, H-X2, H-X3, H-X5, H-X6, H-X7, H-X8; H-X4 is a statement about the files")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "x_verdicts.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string())


if __name__ == "__main__":
    main()
