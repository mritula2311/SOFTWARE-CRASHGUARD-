"""Q1 evaluation (EXPLORATORY-REVISED): H-Q1a (H-P1), H-Q1b (H-P2), H-Q1c (H-P3a) from the runs of ``fin_f1`` (real-only control and the old family arm) or ``q_f1`` (physics arms), with the original criteria.

Arms (keys ``q.<arm>.*``):
- ``real_only``: the runs of ``fin_f1`` restricted to the mixing ratio 0 (identical code, no synthetic row): the confirmatory real-only rerun. Selection of the model uses the REAL validation rows only.
- ``fam_f1``: the runs of ``fin_f1`` with the family generator that passed the earlier fidelity check (kept as the earlier block-F arm; it fails the V7 realism gate and is therefore EXPLORATORY here).
- ``pha_ungated`` and ``phb_ungated``: the physics generators used although they failed the V7 realism gate: EXPLORATORY, gate failed.
Scoring reuses ``fin_f1_eval`` unchanged (original thresholds; none relaxed); only the ratio grid and the key prefix differ.

    python -m crashguard.q_eval real_only|fam_f1|pha_ungated|phb_ungated
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

from crashguard import config as C
from crashguard import fin_f1 as F1
from crashguard import fin_f1_eval as FE
from crashguard.fin_common import Entries
from crashguard.pp_ctx import Ctx

SRC = "results/tables/q_q1.csv"
ARMS = {
    "real_only": (F1.OUT, (0.0,), "real-only rerun (mixing ratio 0, identical code); confirmatory"),
    "fam_f1": (F1.OUT, F1.RATIOS, "family generator of block F (passed the old fidelity check, fails the V7 realism gate); EXPLORATORY"),
    "pha_ungated": (C.PROCESSED / "q_f1_pha_ungated_runs.pkl", F1.RATIOS, "PH-A physics generator used although it failed the V7 realism gate; EXPLORATORY, gate failed"),
    "phb_ungated": (C.PROCESSED / "q_f1_phb_ungated_runs.pkl", F1.RATIOS, "PH-B physics generator used although it failed the V7 realism gate; EXPLORATORY, gate failed"),
}


def evaluate(arm: str) -> None:
    path, ratios, label = ARMS[arm]
    runs = pickle.loads(Path(path).read_bytes())
    cx = Ctx()
    FE.RATIOS = ratios  # the scoring functions read the module-level grid
    E = Entries(f"q.{arm}", SRC)
    for scheme, sl in (("sealed", "sealed fold, scored once more, revised after the negative"), ("cv", "grouped nested cross-validation over all 913 real records (main estimate)")):
        if not all(n in runs for n in FE.SCHEMES[scheme]):
            E.add(f"{scheme}.status", "NOT_RUN: runs missing", "text", "NOT_RUN", "the runs of this arm had not finished")
            continue
        lab = f"{sl}; {label}"
        st = FE.run_scheme(E, runs, cx, scheme, lab)
        FE.interval_checks(E, runs, cx, scheme, lab, st)
        stats = [s for r in FE.SCHEMES[scheme] for s in runs[r].get("synth_stats", [])]
        if stats and ratios != (0.0,):
            tot = sum(s["n_generated"] for s in stats)
            E.add(f"{scheme}.synthetic_dropped_share", round(1.0 - sum(s.get("n_kept", s["n_generated"]) for s in stats) / max(tot, 1), 4), "fraction", "SIMULATED", "share of generated pulses dropped by the physical checks and the real-range check")
    # rename the F1 verdict keys to the V7 ids and mark the label
    for e in E.ent:
        e["notes"] = (e["notes"] + " | " if e["notes"] else "") + f"arm {arm}: {label}"
    E.write()
    print("wrote q.%s.*" % arm, len(E.ent), "entries")


if __name__ == "__main__":
    evaluate(sys.argv[1])
