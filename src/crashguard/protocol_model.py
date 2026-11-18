"""Bounded explicit-state check of the alert protocol model (S12 and Part C of the UA-SCT prompt; model and properties: docs/01_protocol/PROTOCOL_MODEL.md, written before the runs). ANALYTICAL (bounded model check).

This checks a MODEL of the protocol within stated bounds. It is not a proof of the firmware or of the reference code. Cryptography is assumed perfect: only the car can produce a message with a valid tag; an attacker can
replay captured messages and inject messages with invalid tags. TLC (TLA+) was not run: the tool jar could not be fetched in this environment (NOT_RUN); this search is the explicit-state alternative.

Participants: car, base, attacker. Messages (the last field is the validity of the tag; the third field of an uplink message is a GHOST serial number of the car's event, not a protocol field, used only to state the properties):
  uplink   (kind, counter, serial, ok), kind F (flash), A (alert), X (CANCEL);  downlink  ('K', stage, counter, serial, ok), an ACK of stage F or A.
Car: counter, one event at a time (active until acknowledged, cancelled or out of tries), at most MAX_TRIES alert sends and MAX_FLASH flash sends per event, may send in any order at any time (timers are non-deterministic),
stops on a valid ACK of its alert, driver cancel sends a CANCEL, reboot with or without counter persistence (a persisted counter is written before the initial send).
Base: last accepted flash counter, last accepted alert counter, the last RECENT accepted messages with a re-ACK count (budget REACK_MAX per message), the cancelled set, reboot with or without persistence.
Channel: lose, duplicate (replay by the attacker), reorder (delivery in any order). Attacker: at most MAX_ATT actions (replay a captured message to the base or the car; inject an invalid-tag message; spoof an ACK).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

REJECT_TAG, REJECT_COUNTER, ACCEPT, REACK, REACK_NOBUDGET, CANCELLED, REJECT_UNKNOWN = "reject_tag", "reject_counter", "accept", "reack", "reack_no_budget", "cancelled", "reject_unknown"


@dataclass(frozen=True)
class Bounds:
    cmax: int = 4  # counters 1..cmax
    max_events: int = 3  # car events (serials) in one run
    max_tries: int = 3  # alert sends per event
    max_flash: int = 2  # flash sends per event
    max_att: int = 6  # attacker actions
    max_loss: int = 2  # lost messages
    max_reboot_base: int = 1
    max_reboot_car: int = 1
    recent: int = 2  # re-ACK memory (messages)
    reack_max: int = 2  # re-ACKs per remembered message
    max_inflight: int = 3


@dataclass(frozen=True)
class Variant:
    name: str
    idempotent: bool = True  # exact repeats of accepted messages are re-ACKed
    base_persist: bool = True  # counters and the re-ACK memory survive a base reboot
    car_persist: bool = True  # the car writes its counter before the initial send
    flash: bool = True
    cancel: bool = True
    attacker: bool = True
    liveness_env: bool = False  # restrict the environment for the liveness check: no attacker, no cancel, no reboot


PROPS = ("S1_replay_or_forgery_accepted_as_new", "S2_spoofed_ack_stops_retries", "S3_repeat_not_acked_or_budget_exceeded", "S4_accepted_counters_not_increasing", "L1_no_ack_in_terminal_state",
         "C1_cancel_without_valid_signature", "C2_send_after_valid_ack", "L1b_legit_new_event_rejected_as_replay")


def base_rule(base: tuple, msg: tuple, v: Variant, b: Bounds):
    """(decision, new base, ack or None). base = (last_flash, last_alert, recent, cancelled); recent = tuple of (kind, counter, re-ACKs used), oldest first."""
    kind, c, _s, ok = msg
    lf, la, recent, canc = base
    if not ok:
        return REJECT_TAG, base, None
    if kind == "X":
        if any(k in ("F", "A") and cc == c for k, cc, _u in recent):
            return CANCELLED, (lf, la, recent, tuple(sorted(set(canc) | {c}))), None
        return REJECT_UNKNOWN, base, None
    last = lf if kind == "F" else la
    if v.idempotent:
        for idx, (k, cc, used) in enumerate(recent):
            if k == kind and cc == c:
                if used >= b.reack_max:
                    return REACK_NOBUDGET, base, None
                r2 = recent[:idx] + ((k, cc, used + 1),) + recent[idx + 1:]
                return REACK, (lf, la, r2, canc), ("K", kind, c)
    if c <= last:
        return REJECT_COUNTER, base, None
    rec = recent + ((kind, c, 0),)
    rec = rec[-b.recent:]
    nb = (c, la, rec, canc) if kind == "F" else (lf, c, rec, canc)
    return ACCEPT, nb, ("K", kind, c)


# state = (car, base, up, down, seen_up, seen_down, att, loss, reb_base, reb_car, acc, persisted_base, ack_serials)
# car = (ctr, phase, tries, fsends, serial, persisted_ctr, f_ack, a_ack); phase 0 idle, 1 active, 2 done (valid ACK), 3 cancelled
def initial() -> tuple:
    return ((0, 0, 0, 0, 0, 0, False, False), (0, 0, (), ()), (), (), frozenset(), frozenset(), 0, 0, 0, 0, (), (0, 0, (), ()), frozenset())


def _add(t: tuple, m, cap: int) -> tuple | None:
    """Put one more copy of a message in flight (copies are counted: each copy can be lost or delivered on its own). A full channel blocks the sender; it is never a silent loss, losses are counted separately."""
    if len(t) >= cap:
        return None
    return tuple(sorted(t + (m,)))


def successors(s: tuple, v: Variant, b: Bounds):
    car, base, up, down, seen_up, seen_down, att, loss, rbb, rbc, acc, pbase, acks = s
    ctr, phase, tries, fsends, serial, pctr, f_ack, a_ack = car
    # ---- car
    if phase == 0 and serial < b.max_events and ctr < b.cmax:
        nctr = ctr + 1
        ncar = (nctr, 1, 0, 0, serial + 1, nctr if v.car_persist else pctr, False, False)
        yield "car starts event", (ncar, base, up, down, seen_up, seen_down, att, loss, rbb, rbc, acc, pbase, acks), ()
    if phase == 1:
        if v.flash and fsends < b.max_flash and not f_ack:
            m = ("F", ctr, serial, True)
            nu = _add(up, m, b.max_inflight) if m not in up else None  # a retry only after the previous copy has left the channel (timeout)
            if nu is not None:
                yield "car sends flash", ((ctr, 1, tries, fsends + 1, serial, pctr, f_ack, a_ack), base, nu, down, seen_up | {m}, seen_down, att, loss, rbb, rbc, acc, pbase, acks), ()
        if tries < b.max_tries:
            m = ("A", ctr, serial, True)
            nu = _add(up, m, b.max_inflight) if m not in up else None  # a retry only after the previous copy has left the channel (timeout)
            if nu is not None:
                yield "car sends alert", ((ctr, 1, tries + 1, fsends, serial, pctr, f_ack, a_ack), base, nu, down, seen_up | {m}, seen_down, att, loss, rbb, rbc, acc, pbase, acks), ()
        if v.cancel and (fsends > 0 or tries > 0):
            m = ("X", ctr, serial, True)
            nu = _add(up, m, b.max_inflight)
            if nu is not None:
                yield "driver cancels, car sends CANCEL", ((ctr, 3, tries, fsends, serial, pctr, f_ack, a_ack), base, nu, down, seen_up | {m}, seen_down, att, loss, rbb, rbc, acc, pbase, acks), ()
    if rbc < b.max_reboot_car and not v.liveness_env:
        nctr = pctr if v.car_persist else 0
        yield "car reboots", ((nctr, 0, 0, 0, serial, pctr if v.car_persist else 0, False, False), base, up, down, seen_up, seen_down, att, loss, rbb, rbc + 1, acc, pbase, acks), ()
    # ---- car receives a downlink message
    for i, m in enumerate(down):
        rest = down[:i] + down[i + 1:]
        _k, stage, c, ms, ok = m
        viol = []
        ncar = car
        if phase == 1 and ok and c == ctr:
            if stage == "F":
                ncar = (ctr, 1, tries, fsends, serial, pctr, True, a_ack)
            else:
                ncar = (ctr, 2, tries, fsends, serial, pctr, f_ack, True)
                if not any(e[2] == serial for e in acc if e[0] == "A"):
                    viol.append("S2_spoofed_ack_stops_retries")
        yield f"car receives {m}", (ncar, base, up, rest, seen_up, seen_down, att, loss, rbb, rbc, acc, pbase, acks), tuple(viol)
        if loss < b.max_loss:
            yield "ACK lost", (car, base, up, rest, seen_up, seen_down, att, loss + 1, rbb, rbc, acc, pbase, acks), ()
    # ---- base receives an uplink message
    for i, m in enumerate(up):
        rest = up[:i] + up[i + 1:]
        kind, c, ms, ok = m
        dec, nb, ack = base_rule(base, m, v, b)
        viol = []
        nacc = acc
        if dec == ACCEPT:
            serial_seen = any(e[0] == kind and e[2] == ms for e in acc)
            if (not ok) or serial_seen or ms == 0:
                viol.append("S1_replay_or_forgery_accepted_as_new")
            for e in acc:
                if e[0] == kind and c <= e[1]:
                    viol.append("S4_accepted_counters_not_increasing")
                    break
            nacc = acc + ((kind, c, ms),)
        if dec == REJECT_COUNTER and ok and kind in ("F", "A") and not any(e[0] == kind and e[2] == ms for e in acc):
            viol.append("L1b_legit_new_event_rejected_as_replay")  # a valid opening message of a new car event is refused because its counter is not above the last one
        if dec == CANCELLED and not ok:
            viol.append("C1_cancel_without_valid_signature")
        if v.idempotent and dec == REJECT_COUNTER and ok and any(e[0] == kind and e[1] == c for e in acc):
            # an exact repeat of a message the base accepted is rejected although (by the model's own memory rule) it might still be within the window: only a violation if it is still remembered
            if any(k == kind and cc == c for k, cc, _u in base[2]):
                viol.append("S3_repeat_not_acked_or_budget_exceeded")
        for k, cc, used in nb[2]:
            if used > b.reack_max:
                viol.append("S3_repeat_not_acked_or_budget_exceeded")
        ndown = down
        nseen_down = seen_down
        if ack is not None:
            mm = ("K", ack[1], ack[2], ms, True)
            nd = _add(down, mm, b.max_inflight)
            if nd is None:
                continue  # the downlink is full: the base waits (no silent loss)
            ndown, nseen_down = nd, seen_down | {mm}
        npbase = nb if v.base_persist else pbase
        yield f"base receives {m} -> {dec}", (car, nb, rest, ndown, seen_up, nseen_down, att, loss, rbb, rbc, nacc, npbase, acks), tuple(viol)
        if loss < b.max_loss:
            yield "uplink message lost", (car, base, rest, down, seen_up, seen_down, att, loss + 1, rbb, rbc, acc, pbase, acks), ()
    if rbb < b.max_reboot_base and not v.liveness_env:
        nb = base if v.base_persist else (0, 0, (), ())
        yield "base reboots", (car, nb, up, down, seen_up, seen_down, att, loss, rbb + 1, rbc, acc, pbase, acks), ()
    # ---- attacker
    if v.attacker and not v.liveness_env and att < b.max_att:
        for m in sorted(seen_up):
            nu = _add(up, m, b.max_inflight)
            if nu is not None:
                yield f"attacker replays {m} to the base", (car, base, nu, down, seen_up, seen_down, att + 1, loss, rbb, rbc, acc, pbase, acks), ()
        for m in sorted(seen_down):
            nd = _add(down, m, b.max_inflight)
            if nd is not None:
                yield f"attacker replays {m} to the car", (car, base, up, nd, seen_up, seen_down, att + 1, loss, rbb, rbc, acc, pbase, acks), ()
        for kind in ("F", "A", "X"):
            m = (kind, 1, 0, False)
            nu = _add(up, m, b.max_inflight)
            if nu is not None:
                yield f"attacker injects {m}", (car, base, nu, down, seen_up, seen_down, att + 1, loss, rbb, rbc, acc, pbase, acks), ()
        for stage in ("F", "A"):
            m = ("K", stage, ctr if ctr else 1, 0, False)
            nd = _add(down, m, b.max_inflight)
            if nd is not None:
                yield f"attacker spoofs ACK {m}", (car, base, up, nd, seen_up, seen_down, att + 1, loss, rbb, rbc, acc, pbase, acks), ()


def explore(v: Variant, b: Bounds, max_states: int = 4_000_000) -> dict:
    """Level-by-level search of every reachable state. Returns state count, depth, per-property result (holds or the shortest counterexample trace) and L1."""
    init = initial()
    parent: dict = {init: None}
    q = deque([(init, 0)])
    first: dict = {}
    depth = 0
    terminal_bad = None
    n_trans = 0
    while q:
        s, d = q.popleft()
        depth = max(depth, d)
        succ = list(successors(s, v, b))
        n_trans += len(succ)
        for label, ns, viol in succ:
            for p in viol:
                if p not in first:
                    first[p] = (s, label, ns)
            if ns not in parent:
                parent[ns] = (s, label)
                if len(parent) > max_states:
                    return dict(variant=v.name, states=len(parent), depth=depth, truncated=True, props={}, transitions=n_trans)
                q.append((ns, d + 1))
        car = s[0]
        if not succ and terminal_bad is None and car[1] not in (2, 3) and v.liveness_env:
            terminal_bad = s
        # C2: no send after a valid ACK
        if car[1] == 2:
            for label, _ns, _vv in succ:
                if label.startswith("car sends"):
                    first.setdefault("C2_send_after_valid_ack", (s, label, _ns))
    props = {}

    def trace(s, label, ns) -> list[str]:
        steps = [label]
        cur = s
        while parent.get(cur):
            p, lab = parent[cur]
            steps.append(lab)
            cur = p
        return list(reversed(steps))

    for p in PROPS:
        if p == "L1_no_ack_in_terminal_state":
            if not v.liveness_env:
                props[p] = dict(checked=False)
            elif terminal_bad is None:
                props[p] = dict(checked=True, holds=True)
            else:
                steps, cur = [], terminal_bad
                while parent.get(cur):
                    pp, lab = parent[cur]
                    steps.append(lab)
                    cur = pp
                props[p] = dict(checked=True, holds=False, trace=list(reversed(steps)))
            continue
        if p in first:
            s, label, ns = first[p]
            props[p] = dict(checked=True, holds=False, trace=trace(s, label, ns))
        else:
            props[p] = dict(checked=True, holds=True)
    return dict(variant=v.name, states=len(parent), depth=depth, truncated=False, props=props, transitions=n_trans)
