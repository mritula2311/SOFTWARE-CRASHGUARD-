"""Round 7b G3: record the Tamarin outputs of formal/r7b_quarantine_pseudo.spthy as keys r7b.g3.* (FORMAL).

    python -m crashguard.r7b_formal_record
"""
from __future__ import annotations

import re
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "formal" / "out" / "r7b"
SRC = "src/crashguard/r7b_formal_record.py"
LEM = ("executable_strike", "no_framing_noninjective", "no_framing_injective")
EXPECT = {"ATOMIC": ("verified", "verified", "verified"), "NOSEEN": ("verified", "verified", "falsified"), "NOTAG": ("verified", "falsified", "falsified")}


def main() -> None:
    ent = []
    ok_all = True
    for var, exp in EXPECT.items():
        for lem, e in zip(LEM, exp):
            t = (OUT / f"tam_{var}" / f"{lem}.txt").read_text(encoding="utf-8", errors="replace")
            m = re.search(rf"{lem} \((?:exists-trace|all-traces)\): (verified|falsified)", t)
            res = m.group(1) if m else "no result"
            w = re.search(r"processing time: ([0-9.]+)s", t)
            ok_all &= res == e
            ent.append(dict(name=f"r7b.g3.tamarin.{var}.{lem}", value=res, unit="result", origin="FORMAL", source_file=SRC, notes=f"formal/r7b_quarantine_pseudo.spthy -D={var}; expected {e}; Tamarin 1.12.0 single thread, limit 300 s; processing time {w.group(1) if w else 'n/a'} s"))
    ent.append(dict(name="r7b.g3.all_as_expected", value=int(ok_all), unit="flag", origin="FORMAL", source_file=SRC, notes="design verified in all three lemmas; the two controls fail where expected"))
    t = (ROOT / "formal" / "out" / "r7" / "pv_r7_lemmas_quarantine.txt").read_text(encoding="utf-8", errors="replace")
    ent.append(dict(name="r7b.g3.proverif.injective_trace_is_two_base_copies", value=int("event Strike(a_3,a_5) at {19} in copy a_6" in t and "event Strike(a_3,a_5) at {19} in copy a_7" in t), unit="flag", origin="FORMAL", source_file=SRC, notes="the stored ProVerif trace has two copies of the base thread (a_6, a_7) striking on one car event"))
    record_many(ent, purge_prefixes=("r7b.g3.",))
    print({e["name"]: e["value"] for e in ent})


if __name__ == "__main__":
    main()
