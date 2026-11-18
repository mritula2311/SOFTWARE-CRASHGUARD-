"""Round 7 B2: read the ProVerif and Tamarin outputs in formal/out/r7 and record the outcomes (keys r7.formal.b.*, FORMAL) after checking each against the expectation written in V18.

    python -m crashguard.r7_formal_record
"""
from __future__ import annotations

import re
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "formal" / "out" / "r7"
SRC = "src/crashguard/r7_formal_record.py"


def pv(name: str) -> tuple[list[str], int]:
    t = (OUT / f"pv_{name}.txt").read_text(encoding="utf-8", errors="replace")
    res = []
    for ln in t.splitlines():
        if ln.startswith("RESULT"):
            res.append("true" if (" is true" in ln or "equivalence is true" in ln) else "false" if (" is false" in ln or "cannot be proved" in ln) else "other")
    m = re.search(r"wall time (\d+) s", t)
    return res, int(m.group(1)) if m else -1


def tam(lemma: str) -> tuple[str, int]:
    t = (OUT / "tam" / f"{lemma}.txt").read_text(encoding="utf-8", errors="replace")
    m = re.search(rf"^\s*{re.escape(lemma)} \((?:all-traces|exists-trace)\): (verified|falsified)", t, re.M)
    w = re.search(r"wall time (\d+) s", t)
    return (m.group(1) if m else "incomplete"), int(w.group(1)) if w else -1


# model: (expected list of outcomes per RESULT line, meaning)
PV_EXPECT = {
    "r7_unlink": (["true"], "diff-equivalence, two alerts of one vehicle against two vehicles"),
    "r7_unlink_many": (["true"], "diff-equivalence, unboundedly many alerts"),
    "r7_unlink_control": (["false", "false"], "control: fixed id in clear (the equivalence is not provable and ProVerif found a trace)"),
    "r7_unlink_bootclear": (["false", "false"], "sensitivity control: boot counter sent in clear"),
    "r7_lemmas_alert": (["true", "true", "false", "true", "false"], "uniqueness of ids; authenticity; injective form (not provable in ProVerif: table semantics) and its non-injective part (true); executability line"),
    "r7_lemmas_alert_nowrite": (["false", "true", "false", "true", "false"], "control: boot counter not written, uniqueness must fail"),
    "r7_lemmas_micro": (["true", "true", "true", "false"], "micro-confirm authenticity, binding to the flash, micro-cancel; executability line"),
    "r7_lemmas_micro_control": (["false", "true", "true", "false"], "control: T1 not in the micro tag; acceptance no longer tied to the micro the vehicle sent for that T1"),
    "r7_lemmas_quarantine": (["false", "true", "false"], "no framing: injective form not provable in ProVerif, its non-injective part true; executability line"),
    "r7_lemmas_quarantine_control": (["false", "false", "false"], "control: strike counted before the tag check; the non-injective no-framing form is also false"),
}
TAM_EXPECT = {
    "executable_ts": "verified", "executable_after_car_reboot": "verified", "L4_replay_outside_window": "verified", "L4b_at_most_once": "verified",
    "L5_no_double_accept_with_car_reboot": "verified", "L6_base_reboot_replay": "falsified", "L7_no_time_alert_can_be_stale": "verified",
}


def main() -> None:
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r7.formal.b.{name}", value=v, unit=unit, origin="FORMAL", source_file=SRC, notes=note))

    bad = []
    for m, (exp, note) in PV_EXPECT.items():
        res, wt = pv(m)
        add(f"pv.{m}.outcomes", ";".join(res), "list", note)
        add(f"pv.{m}.wall_time_s", wt, "s", "ProVerif 2.05 in WSL")
        add(f"pv.{m}.as_expected", int(res == exp), "flag", f"expected {';'.join(exp)}")
        if res != exp:
            bad.append((m, res, exp))
    for lem, exp in TAM_EXPECT.items():
        res, wt = tam(lem)
        add(f"tam.{lem}.outcome", res, "text", "Tamarin 1.12.0, model formal/r7_alert_pseudo_fresh_bootctr.spthy")
        add(f"tam.{lem}.wall_time_s", wt, "s")
        add(f"tam.{lem}.as_expected", int(res == exp), "flag", f"expected {exp}")
        if res != exp:
            bad.append((lem, res, exp))
    # the non-injective no-framing form is in the output text
    t = (OUT / "pv_r7_lemmas_quarantine.txt").read_text(encoding="utf-8", errors="replace")
    add("pv.r7_lemmas_quarantine.noninjective_no_framing_true", int("(but event(Strike(v_2,a_2)) ==> event(CarSentBad(v_2,a_2)) || event(Revealed(v_2)) is true.)" in t), "flag", "no framing holds in the non-injective form")
    t2 = (OUT / "pv_r7_lemmas_quarantine_control.txt").read_text(encoding="utf-8", errors="replace")
    add("pv.r7_lemmas_quarantine_control.noninjective_no_framing_false", int("(even event(Strike(v_2,a_2)) ==> event(CarSentBad(v_2,a_2)) || event(Revealed(v_2)) is false.)" in t2), "flag", "rule A: the attacker frames a vehicle")
    ok_unlink = pv("r7_unlink")[0] == ["true"] and pv("r7_unlink_many")[0] == ["true"] and pv("r7_unlink_control")[0] == ["false", "false"]
    add("hR7_B3.criterion_met", int(ok_unlink), "flag", "diff-equivalence proved for two alerts and for unboundedly many, and the fixed-id control fails")
    add("hR7_B3.p", 1e-300 if ok_unlink else 1.0, "p-value", "V18: 1e-300 if proved and the control fails")
    all_ok = not bad
    add("lemmas_all_hold", int(all_ok), "flag", "every lemma of the list of V18 section 3.2 has its expected outcome (the injective forms are proved in Tamarin: L4b)")
    record_many(ent, purge_prefixes=("r7.formal.b.",))
    print("mismatches:", bad, "unlink ok:", ok_unlink)


if __name__ == "__main__":
    main()
