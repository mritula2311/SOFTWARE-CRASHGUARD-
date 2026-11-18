"""R6-1 (H-R6-1c) and R6-3 (H-R6-3a, H-R6-3b): read the prover outputs in formal/out/r6 and the bounded quarantine model, decide the three formal hypotheses. Keys ``r6.f.*``.

    python -m crashguard.r6_formal      (after scripts/r6_formal.sh and python -m crashguard.r6_quarantine)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "formal" / "out" / "r6"
SRC = "src/crashguard/r6_formal.py"


def pv(name: str) -> list[tuple[str, bool]]:
    t = (OUT / f"{name}.txt").read_text(encoding="utf-8")
    return [(q.strip(), v == "true") for q, v in re.findall(r"^Query (.*) is (true|false)\.$", t, re.M)]


def tam(name: str) -> dict[str, str]:
    t = (OUT / f"{name}.txt").read_text(encoding="utf-8")
    return {m.group(1): m.group(2) for m in re.finditer(r"^\s+(\w+) \((?:all|exists)-traces?\): (verified|falsified)", t, re.M)}


def meta(name: str) -> str:
    t = (OUT / f"{name}.txt").read_text(encoding="utf-8")
    m = re.search(r"exit code: (\d+) ; wall time (\d+) s ; peak memory (\d+) MB", t)
    return f"exit {m.group(1)}, {m.group(2)} s, {m.group(3)} MB" if m else "?"


def main() -> None:
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}
    ent: list[dict] = []

    def add(name, v, unit="flag", note=""):
        ent.append(dict(name=f"r6.f.{name}", value=v, unit=unit, origin="FORMAL", source_file=SRC, notes=note))

    p = pv("pv_micro_confirm")  # 4 queries: (i) auth, (ii) binding, (iii) cancel, executability (a 'not event' query is false when the event is reachable)
    c = pv("pv_micro_confirm_control")
    t = tam("tam_micro_confirm")
    tc = tam("tam_micro_confirm_control")
    pv_i, pv_ii, pv_iii, pv_exec = p[0][1], p[1][1], p[2][1], (not p[3][1])
    ctrl_attack = (not c[0][1]) or (not c[2][1])
    tam_ok = t.get("micro_auth") == "verified" and t.get("micro_binding") == "verified" and t.get("cancel_auth") == "verified" and t.get("executable_micro") == "verified"
    tam_ctrl = tc.get("micro_auth") == "falsified" and tc.get("cancel_auth") == "falsified"
    for k, v in (("proverif.i_micro_auth", pv_i), ("proverif.ii_binding_to_flash", pv_ii), ("proverif.iii_cancel_not_forgeable", pv_iii), ("proverif.executable", pv_exec),
                 ("proverif.control_attack_found", ctrl_attack), ("tamarin.all_lemmas_verified", tam_ok), ("tamarin.control_attack_found", tam_ctrl)):
        add(f"h1c.{k}", int(v), note=("ProVerif " + meta("pv_micro_confirm")) if k.startswith("proverif") else ("Tamarin " + meta("tam_micro_confirm")))
    ok1c = pv_i and pv_ii and pv_iii and pv_exec and ctrl_attack and tam_ok and tam_ctrl
    add("h1c.criterion_met", int(ok1c), note="H-R6-1c: parts (i) to (iii) proved in both provers and the control (tag without T1) finds an attack")
    a = pv("pv_ratchet_auth")
    s = pv("pv_ratchet_secrecy")  # attacker(p1) false, attacker(p2) false, attacker(p3) true expected
    auth_ok = a[0][1] and a[1][1] and a[2][1]
    sec_ok = s[0][1] and s[1][1] and (not s[2][1])
    add("h3a.authenticity_of_past_alerts_proved", int(auth_ok), note="three ratchet steps; ProVerif " + meta("pv_ratchet_auth"))
    add("h3a.secrecy_of_past_alerts_proved", int(sec_ok), note="compromise of the current key K_3 does not reveal p1 and p2; p3 (current) is readable as expected; ProVerif " + meta("pv_ratchet_secrecy"))
    add("h3a.ratchet_steps_bound", 3, "steps", "the bound of the proof")
    add("h3a.criterion_met", int(auth_ok and sec_ok), note="H-R6-3a within the stated bound of three ratchet steps (symbolic model)")
    add("h3b.criterion_met", int(R["r6.f3b.hR6_3b.criterion_met"]), note="H-R6-3b: rule B (count after tag verification) cannot be triggered; by construction of the rule")
    add("h3b.attack_on_rule_A", int(R["r6.f3b.finding.rule_as_read_in_L8_is_attackable"]), note="finding: rule A (count before verification) is attackable by a key-less attacker")
    record_many(ent, purge_prefixes=("r6.f.",))
    print({e["name"]: e["value"] for e in ent})


if __name__ == "__main__":
    main()
