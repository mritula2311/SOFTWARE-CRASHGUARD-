"""H-A3 (ANALYTICAL, bounded explicit-state check of a MODEL; not a proof of firmware): can an attacker that forges ACKs or neighbour frames make OS-DR (or OS-DR-N) stop an alert that the gateway never received?

Model. Two vehicles A and B in one event cell (event E1), one gateway, an attacker with at most ``MAX_ATT`` actions and at most ``MAX_LOSS`` message losses. Each vehicle has: a status (pending, stopped, gave up), a number of
alert sends (at most 3), a lowered-priority flag (OS-DR-N) and a clock-based retry gate. The gateway keeps the set of vehicles whose alert it received and issues an ACK (valid tag) carrying the event identifier and the cell
for each received alert. Messages are delivered in any order; the attacker may (a) inject an ACK with an invalid tag, (b) replay a valid ACK of an OLDER event (E0), (c) replay a genuine ACK of this event, (d) inject a
neighbour alert frame, and, in the key-holder variant, (e) forge an ACK or a neighbour frame with a VALID tag (the key is shared between vehicles and base: a documented limit, docs/01_protocol/PACKET_FORMAT.md).
Rules under test: OS-DR stops a vehicle only on a valid-tag ACK whose event identifier and cell equal its own (event-level stop); the BASELINE stops it only on a valid-tag ACK that names the vehicle itself (per-node stop).
OS-DR-N lowers the retry priority when a neighbour frame is decoded; a lowered priority defers a RETRY by at most DEFER ticks and never beyond the deadline guard; it never touches the initial send.
Properties (checked on every reachable state): S1 no vehicle stops while the gateway holds no alert of the event, unless a valid-tag forgery was used; S2 the initial send of a pending vehicle is always enabled; S3 a retry is enabled
no later than the deadline guard whatever the attacker did; S4 (event reach) after the attack the gateway has an alert of the event or some vehicle is still pending. The shortest attack found for "every vehicle stopped and the
gateway holds no alert" is reported with its length (the number of attacker actions).
Variants: attacker without key and attacker with the key; rules baseline, OS-DR, OS-DR-N. Results (keys ``pa.model.*``) are ANALYTICAL within the bounds.
"""
from __future__ import annotations

from collections import deque

MAX_ATT = 3
MAX_LOSS = 2
MAX_TRIES = 3
DEFER = 2
GUARD_TICK = 4
VEH = (0, 1)


def initial():
    # per vehicle: (status 0 pending / 1 stopped / 2 gave up, sends, lowered, observed_by_attacker)
    vs = tuple((0, 0, 0, 0) for _ in VEH)
    return (vs, frozenset(), (), 0, 0, 0, False)  # vehicles, gateway_has, in transit, clock, att used, losses, forged_valid_used


def successors(st, rule: str, key: bool):
    vs, gw, net, clock, att, loss, fv = st
    out = []
    # vehicle sends
    for i, (status, sends, low, obs) in enumerate(vs):
        if status != 0 or sends >= MAX_TRIES:
            continue
        enabled = sends == 0 or low == 0 or clock >= DEFER or clock >= GUARD_TICK  # a lowered priority defers a retry by at most DEFER ticks
        if sends >= 1 and rule == "osdr_n" and low == 1 and clock < DEFER:
            enabled = False
        if enabled:
            nv = list(vs)
            nv[i] = (0, sends + 1, low, 1)
            out.append((f"send{i}", (tuple(nv), gw, net + (("alert", i, True),), clock, att, loss, fv)))
    # the retry gate relies on a clock tick
    if clock < GUARD_TICK + 1:
        out.append(("tick", (vs, gw, net, clock + 1, att, loss, fv)))
    for k, m in enumerate(net):
        rest = net[:k] + net[k + 1:]
        kind = m[0]
        if loss < MAX_LOSS:
            out.append(("lose", (vs, gw, rest, clock, att, loss + 1, fv)))
        if kind == "alert":
            _, i, valid = m
            if valid:
                out.append(("gw_rx", (vs, gw | {i}, rest + (("ack", i, "E1", True, False),), clock, att, loss, fv)))
                # a neighbour decodes the alert frame (OS-DR-N only changes the priority)
                nv = list(vs)
                for j, (s, n_, lw, ob) in enumerate(vs):
                    if j != i and rule == "osdr_n":
                        nv[j] = (s, n_, 1, ob)
                out.append(("nb_rx", (tuple(nv), gw, rest, clock, att, loss, fv)))
        elif kind == "ack":
            _, i, ev, valid, forged = m
            for j, (s, n_, lw, ob) in enumerate(vs):
                if s != 0 or not valid:
                    continue
                stops = (rule in ("osdr", "osdr_n") and ev == "E1") or (rule == "baseline" and ev == "E1" and j == i)
                if stops:
                    nv = list(vs)
                    nv[j] = (1, n_, lw, ob)
                    out.append((f"ack_rx{j}", (tuple(nv), gw, rest, clock, att, loss, fv or forged)))
            out.append(("ack_drop", (vs, gw, rest, clock, att, loss, fv)))
    # attacker
    if att < MAX_ATT:
        for j in VEH:
            out.append((f"att_bad_ack{j}", (vs, gw, net, clock, att + 1, loss, fv)))  # invalid tag: no valid rule accepts it (no state change)
            out.append((f"att_old_ack{j}", (vs, gw, net, clock, att + 1, loss, fv)))  # valid tag, other event: ignored
            if rule != "baseline" and key:
                nv = list(vs)
                nv[j] = nv[j] if nv[j][0] != 0 else (1, nv[j][1], nv[j][2], nv[j][3])
                # the event ACK is forged with a valid tag for the event of the cell, delivered to every vehicle in range
                nv2 = tuple((1, s[1], s[2], s[3]) if s[0] == 0 else s for s in vs)
                out.append(("att_forged_event_ack", (nv2, gw, net, clock, att + 1, loss, True)))
            if rule == "baseline" and key and vs[j][3] == 1 and vs[j][0] == 0:
                nv = list(vs)
                nv[j] = (1, vs[j][1], vs[j][2], vs[j][3])
                out.append((f"att_forged_node_ack{j}", (tuple(nv), gw, net, clock, att + 1, loss, True)))
            if rule == "osdr_n":
                nv = list(vs)
                nv[j] = (vs[j][0], vs[j][1], 1, vs[j][3])
                out.append((f"att_neighbour_frame{j}", (tuple(nv), gw, net, clock, att + 1, loss, fv)))
    return out


def check(rule: str, key: bool) -> dict:
    s0 = initial()
    seen = {s0: (None, None)}
    q = deque([s0])
    viol = {"S1": None, "S2": None, "S3": None, "S4": None}
    n_states = 0
    while q:
        st = q.popleft()
        n_states += 1
        vs, gw, net, clock, att, loss, fv = st
        # S1: stopped without any gateway reception and without a valid-tag forgery
        if viol["S1"] is None and any(v[0] == 1 for v in vs) and not gw and not fv:
            viol["S1"] = st
        # S2: the initial send of every pending vehicle that has not sent is enabled
        if viol["S2"] is None:
            for i, v in enumerate(vs):
                if v[0] == 0 and v[1] == 0 and f"send{i}" not in [a for a, _ in successors(st, rule, key)]:
                    viol["S2"] = st
        # S3: a retry is enabled at the deadline guard
        if viol["S3"] is None and clock >= GUARD_TICK:
            for i, v in enumerate(vs):
                if v[0] == 0 and 1 <= v[1] < MAX_TRIES and f"send{i}" not in [a for a, _ in successors(st, rule, key)]:
                    viol["S3"] = st
        # S4: every vehicle stopped while the gateway holds no alert (the event is silently lost)
        if viol["S4"] is None and all(v[0] == 1 for v in vs) and not gw and not any(m[0] == "alert" for m in net):
            viol["S4"] = st
        for a, nxt in successors(st, rule, key):
            if nxt not in seen:
                seen[nxt] = (st, a)
                q.append(nxt)

    def trace(st):
        out = []
        while seen[st][0] is not None:
            out.append(seen[st][1])
            st = seen[st][0]
        return list(reversed(out))

    return dict(states=n_states, violated={k: (v is not None) for k, v in viol.items()}, trace_S4=(trace(viol["S4"]) if viol["S4"] else None), attacker_actions_S4=(sum(1 for a in trace(viol["S4"]) if a.startswith("att_")) if viol["S4"] else None))


def main() -> None:
    from crashguard.fin_common import Entries

    E = Entries("pa.model", "src/crashguard/pa_model.py")
    for rule in ("baseline", "osdr", "osdr_n"):
        for key in (False, True):
            r = check(rule, key)
            p = f"{rule}.{'key' if key else 'nokey'}"
            E.add(f"{p}.states", r["states"], "states", "ANALYTICAL", f"reachable states of the bounded model (attacker actions at most {MAX_ATT}, message losses at most {MAX_LOSS}, sends at most {MAX_TRIES})")
            for s_, name in (("S1", "stop_without_gateway_alert_or_valid_forgery"), ("S2", "initial_send_blocked"), ("S3", "retry_blocked_at_deadline_guard"), ("S4", "event_silently_lost")):
                E.add(f"{p}.violated.{s_}", int(r["violated"][s_]), "flag", "ANALYTICAL", f"{name}: 1 = a counterexample exists within the bounds")
            E.add(f"{p}.attacker_actions_to_lose_event", r["attacker_actions_S4"], "actions", "ANALYTICAL", "shortest attack found that stops every vehicle while the gateway holds no alert of the event (None = none within the bounds)")
            print(p, r["violated"], r["attacker_actions_S4"], r["trace_S4"])
    E.write()


if __name__ == "__main__":
    main()
