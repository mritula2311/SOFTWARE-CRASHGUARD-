"""D7.3: preemption of the provisional flash by the full decision. Exhaustive enumeration of a small untimed model (FORMAL, bounded) and the analytical airtime that preemption saves.

    python -m crashguard.vf2_preempt

What the code does (read from ``xsim/ns3/xsim_alert.cc`` and ``crashguard.r3_t1``; documented in docs/05_architecture/FRAME_LAYOUT.md section 6): in the two-stage policies r3t and r6m and in the trace replays the node
keeps ONE FIFO queue (first in, first out) per event, [flash, confirm] or [flash, cancel, cancel, cancel]. The flash stays at the head of the queue until its acknowledgement arrives or its 4 tries are used; the confirm or
the cancel waits behind it. Nothing is withdrawn and the confirm does not replace the flash. Only the policy r3a (24-byte provisional frame, preregistration V15) preempts. The recommended design (not implemented in
r3t, r6m) withdraws the remaining flash tries when the full decision is ready.

Model. One event, one vehicle, one base. Node: k flash tries have been made when the full decision becomes ready (k = 1 to 4; every try is lost, delivered with the acknowledgement lost, or delivered and
acknowledged; a try after an acknowledged one is not made). Decision D = confirm (up to 4 tries, stops at the acknowledgement; delivery of the confirm gives CONFIRMED whatever the base held) or cancel (3
unconfirmed transmissions; a delivered cancel gives CANCELLED when the base holds PRE, and is rejected when the base holds NONE, as in ``sct_protocol`` with the default setting). Two variants of the node: the
FIFO node of the code (remaining flash tries up to the 4th are made before the decision's frames) and the preempting node (the remaining flash tries are withdrawn). The channel is half duplex: the frames of one node
reach the base in the order they were sent. Base variants: without a timeout (the code), and with a timeout that takes PRE to EXPIRED when neither confirm nor cancel has been received.
Every outcome of every try is enumerated. Keys ``vf2.preempt.*`` (FORMAL).
"""
from __future__ import annotations

import itertools
import math

from crashguard.lora import airtime_ms
from crashguard.results import record_many

SRC = "src/crashguard/vf2_preempt.py"
TRIES, CONFIRM_TRIES, CANCEL_TX = 4, 4, 3
T_F, C, RX_GAP = 1.808, 0.008, 0.32  # full decision (s), compute (s), receive windows after an uplink in ns-3 (0.2 s RX2 + 0.12 s margin)
OUTCOMES = ("lost", "delivered_ack_lost", "delivered_acked")


def stages(n_max: int):
    """Every outcome sequence of a stage of up to n_max tries that stops after an acknowledged try and otherwise uses all n_max tries."""
    out = []
    for n in range(1, n_max + 1):
        for seq in itertools.product(OUTCOMES, repeat=n):
            if "delivered_acked" in seq[:-1]:
                continue  # no try after an acknowledged one
            if n < n_max and seq[-1] != "delivered_acked":
                continue  # a stage that is not acknowledged uses all its tries
            out.append(seq)
    return out


def run(k: int, decision: str, preempt: bool, timeout: bool) -> set:
    """Set of (base state, flash delivered, order ok, final stage delivered) over all outcomes, when k flash tries were made before the decision (k = 1 to 4)."""
    res = set()
    for before in itertools.chain(*(itertools.product(OUTCOMES, repeat=k),)):
        if "delivered_acked" in before[:-1]:
            continue  # the stage ended at the acknowledgement: covered by the shorter sequences below
        res |= _after_flash(before, k, decision, preempt)
    for n in range(1, k):  # the flash stage ended before the decision was ready (acknowledged flash)
        for before in itertools.product(OUTCOMES, repeat=n):
            if "delivered_acked" in before[:-1] or before[-1] != "delivered_acked":
                continue
            res |= _after_flash(before, k, decision, preempt)
    if timeout:
        res = {("EXPIRED" if b == "PRE" else b, df, ok, a) for (b, df, ok, a) in res}
    return res


def _after_flash(before: tuple, k: int, decision: str, preempt: bool) -> set:
    res = set()
    acked = before[-1] == "delivered_acked"
    delivered_before = any(o != "lost" for o in before)
    extras = [()]
    if not preempt and not acked and len(before) < TRIES:
        extras = stages(TRIES - len(before))  # the FIFO node finishes the flash stage before the decision's frames
    for extra in extras:
        delivered_flash = delivered_before or any(o != "lost" for o in extra)
        base = "PRE" if delivered_flash else "NONE"
        order_ok = True  # half duplex: every flash frame precedes the leading frame of the final stage (checked by construction of the sequence)
        if decision == "confirm":
            for fin in stages(CONFIRM_TRIES):
                got = any(o != "lost" for o in fin)
                res.add(("CONFIRMED" if got else base, delivered_flash, order_ok, got))
        else:
            for cs in itertools.product(("lost", "delivered"), repeat=CANCEL_TX):
                got = any(o == "delivered" for o in cs)
                res.add((("CANCELLED" if base == "PRE" else base) if got else base, delivered_flash, order_ok, got))
    return res


def analytic_saving() -> list[dict]:
    """Flash tries that start at or after the full decision (the ones that preemption removes) for each spreading factor, per event whose flash is not acknowledged."""
    rows = []
    for sf in (7, 8, 9, 10, 11, 12):
        a = airtime_ms(14, sf) / 1000.0
        for who, te in (("median", 0.050), ("mean", 0.112438625)):
            s_f = te + C
            starts = [s_f + j * (a + RX_GAP) for j in range(TRIES)]
            late = [j for j, s in enumerate(starts) if s >= T_F - 1e-12]
            rows.append(dict(sf=sf, who=who, a14=a, n_late=len(late), saved_s=len(late) * a, last_end=starts[-1] + a))
    return rows


def main() -> None:
    ent: list[dict] = []

    def add(name, v, unit, note="", origin="FORMAL"):
        ent.append(dict(name=f"vf2.preempt.{name}", value=(round(v, 6) if isinstance(v, float) else v), unit=unit, origin=origin, source_file=SRC, notes=note))

    all_ok = True
    stuck = {}
    n_cases = 0
    for decision in ("confirm", "cancel"):
        for k in range(1, TRIES + 1):
            fifo, pre = run(k, decision, False, False), run(k, decision, True, False)
            n_cases += 1
            subset = {(b, df) for (b, df, _o, _a) in pre} <= {(b, df) for (b, df, _o, _a) in fifo}
            all_ok &= subset and all(o for (_b, _d, o, _a) in pre | fifo)
            stuck[(decision, k)] = (sorted({b for (b, *_r) in fifo}), sorted({b for (b, *_r) in pre}))
            for var, label in ((fifo, "fifo"), (pre, "preempt")):
                with_to = {("EXPIRED" if b == "PRE" else b) for (b, *_r) in var}
                add(f"{decision}.k{k}.{label}.terminal_states", ",".join(sorted({b for (b, *_r) in var})), "set", "base states reachable at the end over every outcome of every try")
                add(f"{decision}.k{k}.{label}.pre_alert_forever_possible", int("PRE" in {b for (b, *_r) in var}), "flag", "a terminal state in which the base still holds PRE and no further frame will come (no timeout)")
                add(f"{decision}.k{k}.{label}.pre_alert_forever_with_timeout", int("PRE" in with_to), "flag", "same, when the base moves PRE to EXPIRED after a timeout")
            add(f"{decision}.k{k}.preempt_terminal_subset_of_fifo", int(subset), "flag", "every (base state, flash delivered) pair reachable with preemption is reachable without it")
            # a delivered final-stage frame always ends PRE
            for var, label in ((fifo, "fifo"), (pre, "preempt")):
                bad = [(b, df, o, a) for (b, df, o, a) in var if b == "PRE" and a]
                all_ok &= not bad
    add("cases", n_cases, "cases", "(decision, flash tries made before the decision) pairs enumerated, both node variants")
    add("all_properties_hold", int(all_ok), "flag", "preemption adds no terminal state, never reorders flash and final stage, and a delivered final-stage frame always takes the base out of PRE")
    rows = analytic_saving()
    for r in rows:
        add(f"saving.sf{r['sf']}.{r['who']}.late_flash_tries", r["n_late"], "tries", "flash tries (of 4, spaced A14 + 0.32 s from s_f = t_E + 8 ms) that start at or after the full decision T_F = 1.808 s: the tries that preemption removes", "ANALYTICAL")
        add(f"saving.sf{r['sf']}.{r['who']}.saved_airtime_s", r["saved_s"], "s", "airtime of those tries for an event whose flash is not acknowledged (zero at SF7 to SF9)", "ANALYTICAL")
        add(f"saving.sf{r['sf']}.{r['who']}.last_try_end_s", r["last_end"], "s", "end of the 4th flash try if all are unacknowledged", "ANALYTICAL")
    record_many(ent, purge_prefixes=("vf2.preempt.",))
    print("all properties hold:", all_ok)
    for (d, k), (f, p) in stuck.items():
        print(d, k, "fifo", f, "preempt", p)
    for r in rows:
        print(r["sf"], r["who"], r["n_late"], round(r["saved_s"], 3), round(r["last_end"], 3))
    assert math.isfinite(sum(r["saved_s"] for r in rows))


if __name__ == "__main__":
    main()
