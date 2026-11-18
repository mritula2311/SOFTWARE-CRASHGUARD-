"""R6-3 H-R6-3b (docs/02_preregistration/PREREGISTRATION_V17.md section 5): can an attacker WITHOUT any vehicle key move a victim into quarantine?

    python -m crashguard.r6_quarantine

Bounded exhaustive exploration (FORMAL, bounded): 3 claimed vehicle ids, horizon 6 slots (one slot = one minute, as in L8), up to 4 attacker frames per slot, every frame claims one of the 3 ids with one of the
alert kinds of L8 (ok, implausible, repeat). Every attacker frame FAILS tag verification (the attacker has no key). Honest vehicles send nothing (the worst case for the victim's own counters cannot be better).
The state machine is ``r5_l8.process`` (strikes, rate, quarantine). Two rules:
  (A) the counter updates on every frame carrying the claimed id, before tag verification (the rule as the L8 model reads);
  (B) the counter updates only on frames that pass tag verification.
The counters are per claimed id and independent, so only frames that claim the victim's id change the victim's state; the exploration is done on the victim's state with up to 4 such frames per slot (the frames for the two other ids cannot matter).
Keys ``r6.f3b.*``.
"""
from __future__ import annotations

import itertools

from crashguard.r5_l8 import HORIZON as L8_HORIZON  # noqa: F401  (the L8 horizon is 60 slots; this bounded model uses 6)
from crashguard.r5_l8 import KINDS, initial, process
from crashguard.results import record_many

SRC = "src/crashguard/r6_quarantine.py"
IDS = (0, 1, 2)
VICTIM = 0
SLOTS = 6
MAX_PER_SLOT = 4


def frames_in_slot():
    """Every sequence of up to MAX_PER_SLOT frames that claim the victim's id (frames that claim another id do not change the victim's state: the counters are per claimed id)."""
    out = [()]
    for n in range(1, MAX_PER_SLOT + 1):
        out += list(itertools.product(KINDS, repeat=n))
    return out


def step(state: tuple, slot: int, frames: tuple, rule: str) -> tuple:
    st = state
    for kind in frames:
        if rule == "A":  # counted before verification
            st, _ = process(st, slot, kind)
        # rule "B": a frame that fails tag verification is dropped before the counters (every attacker frame fails)
    return st


def explore(rule: str) -> dict:
    pats = frames_in_slot()
    frontier = {initial()}
    seen = 1
    first_attack = None
    for slot in range(SLOTS):
        nxt = set()
        for s in frontier:
            for p in pats:
                t = step(s, slot, p, rule)
                if t not in nxt:
                    nxt.add(t)
                    if first_attack is None and t[3]:
                        first_attack = dict(slot=slot, frames=list(p), state=t)
        frontier = nxt
        seen += len(frontier)
    return dict(victim_quarantined_reachable=any(s[3] for s in frontier), max_victim_strikes=max(s[2] for s in frontier), states_visited=seen, patterns_per_slot=len(pats), attack=first_attack)


def main() -> None:
    a, b = explore("A"), explore("B")
    ent = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r6.f3b.{name}", value=v, unit=unit, origin="FORMAL", source_file=SRC, notes=note))

    for tag, r in (("A_count_before_verification", a), ("B_count_after_verification", b)):
        add(f"{tag}.victim_quarantined_reachable", int(r["victim_quarantined_reachable"]), "bool", "an attacker without a key reaches quarantine of the victim within the bound")
        add(f"{tag}.max_victim_strikes", r["max_victim_strikes"], "strikes")
        add(f"{tag}.states_visited", r["states_visited"], "states", f"bound: 3 claimed ids (the other two do not affect the victim), {SLOTS} slots, up to {MAX_PER_SLOT} attacker frames per slot, {r['patterns_per_slot']} patterns per slot")
    if a["attack"]:
        add("A_count_before_verification.shortest_attack_slot", a["attack"]["slot"], "slot", f"frames claiming the victim in that slot: {a['attack']['frames']}")
        add("A_count_before_verification.shortest_attack_frames", len(a["attack"]["frames"]), "frames")
    add("hR6_3b.criterion_met", int(b["victim_quarantined_reachable"] is False), "flag", "H-R6-3b: variant B proved (the quarantine cannot be triggered by frames that fail tag verification); variant A is reported as a finding")
    add("finding.rule_as_read_in_L8_is_attackable", int(a["victim_quarantined_reachable"]), "flag", "if the counter counts frames before tag verification, a key-less attacker quarantines any vehicle")
    record_many(ent, purge_prefixes=("r6.f3b.",))
    print("A", {k: v for k, v in a.items() if k != "attack"}, a["attack"])
    print("B", {k: v for k, v in b.items() if k != "attack"})


if __name__ == "__main__":
    main()
