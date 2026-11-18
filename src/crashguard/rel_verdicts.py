"""Holm correction and verdicts over the 20 hypotheses of docs/02_preregistration/PREREGISTRATION_V7.md (rule 5). NOT_RUN hypotheses enter with p = 1 and are never supported. Keys ``q.holm.*`` (Q) and ``pa.holm.*`` (A).

Items whose real-only arm uses code and data identical to an earlier block (no generator passed the realism gate, so the confirmatory arm has no synthetic row) CARRY that block's criterion and p-value; the note says so.
"""
from __future__ import annotations

import json
from pathlib import Path

from crashguard.fin_common import Entries

R = Path("results/results.json")
CARRY = "carried from an earlier block: the real-only arm is identical code and data (no generator passed the realism gate), not re-executed"
# id, plain statement, criterion key, p key, label, note
H = [
    ("hq1a", "H-P1 direct classifier (rerun)", "q.real_only.cv.hF1.criterion_met", "q.real_only.cv.hF1.p_raw", "MEASURED_SOFTWARE", "real-only rerun, nested CV main estimate; synthetic arms are EXPLORATORY (gate failed)"),
    ("hq1b", "H-P2 anchored interval (rerun)", "q.real_only.cv.hF1b.criterion_met", "q.real_only.cv.hF1b.p_raw", "MEASURED_SOFTWARE", "real-only rerun, nested CV main estimate"),
    ("hq1c", "H-P3a abstention (rerun)", "q.real_only.cv.hF1c.criterion_met", "q.real_only.cv.hF1c.p_raw", "MEASURED_SOFTWARE", "real-only rerun, nested CV main estimate"),
    ("hq1d", "H-X5 rank preservation (rerun)", "x.x5.hX5.criterion_met", "x.holm.H-X5.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq1e", "H-X6 anchored estimator (rerun)", "x.x6.hX6.criterion_met", "x.holm.H-X6.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq1f", "H-X7 two-part fusion (rerun)", "x.x7.hX7.criterion_met", "x.holm.H-X7.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq2a", "H-P4a compact forest (rerun)", "p.p4a.hP4a.criterion_met", "p.holm.hp4a.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq2b", "H-P4b augmentation at the 1% target (rerun)", "p.p4b.hP4b.criterion_met", "p.holm.hp4b.p_raw", "MEASURED_SOFTWARE", CARRY + "; the surrogate arm of block F (r chosen 0) is f.f2.*"),
    ("hq2c", "H-P4c calibration variants (rerun)", "p.p4c.hP4c.criterion_met", "p.holm.hp4c.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq2d", "H-X1 16-bit forest (rerun)", "x.x1.hX1.criterion_met", "x.holm.H-X1.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq2e", "H-X2 trigger cascade (rerun)", None, None, "NOT_RUN", "NOT_RUN in advance: the cascade uses whole 16 s records; surrogate windows are trigger-aligned"),
    ("hq2f", "H-X3 group-aware training (rerun)", "x.x3.hX3.criterion_met", "x.holm.H-X3.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq2g", "H-X8 sequential rule (rerun)", "x.x8.hX8.criterion_met", "x.holm.H-X8.p_raw", "MEASURED_SOFTWARE", CARRY),
    ("hq2h", "early-exit rule N19 (rerun)", None, None, "NOT_RUN", "NOT_RUN: no gated surrogate exists to train the forests; the earlier real-only result is unchanged"),
    ("hq3a", "N28 equal-escalation comparison (rerun)", None, None, "NOT_RUN", "NOT_RUN: the rerun on fresh seeds 19000 + h was not completed; block F's verdict (f.holm.hf3a) stays as the earlier result"),
    ("hq3b", "H-B2 P1+ against P0 (rerun)", None, None, "NOT_RUN", "NOT_RUN: as hq3a; block F's verdict (f.holm.hb2) stays"),
    ("hq3c", "P3b abstain routing (rerun)", None, None, "NOT_RUN", "NOT_RUN: as hq3a; block F's verdict (f.holm.hf3b) stays"),
    ("ha1", "H-A1 OS-DR against the best earlier policy", "pa.hA1.criterion_met", "pa.hA1.p_raw", "SIMULATED", "held-out grid, 32 cells, 30 seeds"),
    ("ha2", "H-A2 GS-CA against OS-DR and the slot-probability baseline in burst cells", "pa.hA2.criterion_met", "pa.hA2.p_raw", "SIMULATED", "held-out grid, 16 burst cells, 30 seeds"),
    ("ha3", "H-A3 no new counterexample for OS-DR under forged ACKs and neighbour frames", "pa.model.hA3.criterion_met", None, "ANALYTICAL", "bounded model check; attacker holding the shared key (the documented limit) is the primary model"),
]


def main() -> None:
    r = {e["name"]: e for e in json.loads(R.read_text(encoding="utf-8"))}
    # H-A3 criterion from the model check: no counterexample of any kind for OS-DR, key-holding attacker included
    viol = [int(r[f"pa.model.osdr.{k}.violated.{s}"]["value"]) for k in ("nokey", "key") for s in ("S1", "S2", "S3", "S4")]
    E3 = Entries("pa.model", "src/crashguard/rel_verdicts.py")
    E3.add("hA3.criterion_met", int(sum(viol) == 0), "flag", "ANALYTICAL", "no counterexample for OS-DR within the bounds, attacker without and with the shared key; OS-DR-N is not dropped: its initial send is never delayed (S2) and a retry is enabled by the deadline guard (S3)")
    E3.add("hA3.counterexample", "one forged event-ACK frame (valid tag, key holder) stops every vehicle of the cell before any alert is sent; the per-node baseline needs one forged ACK per vehicle after it was heard, plus lost alerts", "text", "ANALYTICAL", "shortest attack found; OS-DR and OS-DR-N")
    E3.write(purge=False)
    r["pa.model.hA3.criterion_met"] = dict(value=int(sum(viol) == 0), origin="ANALYTICAL")
    rows = []
    for hid, text, kc, kp, lab, note in H:
        if kc is None or kc not in r or r[kc]["value"] in ("NOT_RUN", None):
            crit, p, lab_ = None, 1.0, "NOT_RUN" if kc is None else lab
        else:
            crit = int(r[kc]["value"])
            p = float(r[kp]["value"]) if kp and kp in r else (0.0 if crit else 1.0)
        rows.append([hid, text, crit, p, lab_ if crit is None else lab, note])
    m = len(rows)
    order = sorted(range(m), key=lambda i: rows[i][3])
    adj, running = {}, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * rows[i][3]))
        adj[i] = running
    E = Entries("q.holm", "src/crashguard/rel_verdicts.py")
    EA = Entries("pa.holm", "src/crashguard/rel_verdicts.py")
    for i, (hid, text, crit, p, lab, note) in enumerate(rows):
        ph = adj[i]
        if crit is None:
            verdict = "NOT RUN"
        elif crit and ph < 0.05:
            verdict = "SUPPORTED"
        elif crit:
            verdict = "PARTLY SUPPORTED"
        else:
            verdict = "NOT SUPPORTED"
        Ent = EA if hid.startswith("ha") else E
        pre = hid
        Ent.add(f"{pre}.p_raw", round(p, 4), "p", lab if crit is not None else "NOT_RUN", note)
        Ent.add(f"{pre}.p_holm", round(ph, 4), "p", lab if crit is not None else "NOT_RUN", f"Holm over {m} hypotheses of PREREGISTRATION_V7")
        Ent.add(f"{pre}.criterion_met", crit if crit is not None else "NOT_RUN", "flag", lab if crit is not None else "NOT_RUN", note)
        Ent.add(f"{pre}.verdict", verdict, "text", lab if crit is not None else "NOT_RUN", f"{text}. {note}")
        print(hid, verdict, round(p, 4), round(ph, 4))
    E.add("m_hypotheses", m, "count", "ANALYTICAL", "size of the Holm family")
    E.write()
    EA.write()


if __name__ == "__main__":
    main()
