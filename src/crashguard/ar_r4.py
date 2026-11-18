"""R4 (H-R4): per-vehicle ACK key separation, checked on a bounded explicit-state model (ANALYTICAL within the bounds; SIMULATED_HW_FORMAT for the timing).

Problem (found by `pa_model.py`, H-A3): with one shared key and an event-level ACK, ONE forged ACK from a key holder stops every vehicle. Design: per-vehicle keys K_i = HMAC(master, "ack-key" | vehicle id),
derived at the base (one KDF per new id, cached) and in the vehicle (at provisioning); the alert and the ACK of vehicle i are signed with K_i; the ACK names (vehicle id, acked counter), so it
carries 0 extra bytes (the 26-byte layout of `packet.encode_ack` is unchanged: node_id and acked counter are already in it). Per-device keys are standard in LoRaWAN; this is a design
correction found by the check, not a new key scheme.

Model: V vehicles and one gateway; each vehicle is pending (0), stopped (1) or gave up (2) and has sent s times (at most 3). Messages: alert i (to the gateway), ACK for i (to the car). The gateway ACKs
every alert it receives unless its ACK budget is gone. Losses: at most 2. The attacker makes at most 3 actions: inject an invalid-tag ACK, replay a genuine ACK of an older event or counter, forge a valid
ACK (only with the keys it holds), or send valid alerts of its own to exhaust the gateway ACK budget. Rules: `baseline` (shared key, ACK names the vehicle), `osdr` (shared key, event-level ACK stops every
pending vehicle: the H-A3 counterexample) and `pervehicle` (R4). The attacker holds the shared key (baseline, osdr) or the key K_j of the compromised vehicle j in C (pervehicle); the limit case where it holds the
master key (all K_i) is run too and is outside the claim.
Suppressed vehicle i: stopped while the gateway holds no alert of i and none is in flight. Measure: the largest share of vehicles suppressed in any reachable state.

    python -m crashguard.ar_r4
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections import deque
from pathlib import Path

import numpy as np

from crashguard import packet as P
from crashguard import verifier as V
from crashguard.results import record_many

SRC = "src/crashguard/ar_r4.py"
MAX_TRIES, MAX_LOSS, MAX_ATT = 3, 2, 3
MAX_NET = 4


def kdf(master: bytes, vid: int) -> bytes:
    return hmac.new(master, b"ack-key" + vid.to_bytes(4, "big"), hashlib.sha256).digest()


def succ(st, rule: str, comp: frozenset, n: int):
    vs, gw, net, att, loss, gone = st
    out = []
    for i in range(n):
        s, sent = vs[i]
        if s == 0 and sent < MAX_TRIES and len(net) < MAX_NET:
            nv = list(vs)
            nv[i] = (0, sent + 1)
            out.append((f"send{i}", (tuple(nv), gw, tuple(sorted(net + (("alert", i),))), att, loss, gone)))
        if s == 0 and sent >= MAX_TRIES and ("alert", i) not in net and i not in gw:
            nv = list(vs)
            nv[i] = (2, sent)
            out.append((f"giveup{i}", (tuple(nv), gw, net, att, loss, gone)))
    for k, m in enumerate(net):
        rest = net[:k] + net[k + 1:]
        if loss < MAX_LOSS:
            out.append(("lose", (vs, gw, rest, att, loss + 1, gone)))
        if m[0] == "alert":
            i = m[1]
            ng = gw | {i}
            nn = rest
            if not gone and len(nn) < MAX_NET:
                nn = tuple(sorted(nn + (("ack", i, "gen_cur"),)))
            out.append(("gw_rx", (vs, ng, nn, att, loss, gone)))
        else:
            _, i, kind = m
            out.append(("ack_drop", (vs, gw, rest, att, loss, gone)))
            for j in range(n):
                if vs[j][0] != 0:
                    continue
                if rule == "osdr":
                    stops = kind in ("gen_cur", "forged_valid")
                else:
                    stops = j == i and kind in ("gen_cur", "forged_valid")
                if stops:
                    nv = list(vs)
                    nv[j] = (1, vs[j][1])
                    out.append((f"ack_rx{j}", (tuple(nv), gw, rest, att, loss, gone)))
    if att < MAX_ATT:
        out.append(("att_bad_ack", (vs, gw, net, att + 1, loss, gone)))   # invalid tag: rejected by every rule, no state change
        out.append(("att_old_ack", (vs, gw, net, att + 1, loss, gone)))   # genuine ACK of an older event or counter: rejected (the ACK is bound to the current counter)
        if not gone:
            out.append(("att_budget_flood", (vs, gw, net, att + 1, loss, True)))  # valid alerts of its own (own key) exhaust the gateway's ACK budget
        for i in range(n):
            can = rule in ("baseline", "osdr") or i in comp
            if can and vs[i][0] == 0:
                if rule == "osdr":
                    nv = tuple((1, s[1]) if s[0] == 0 else s for s in vs)
                    out.append((f"att_forged_event_ack{i}", (nv, gw, net, att + 1, loss, gone)))
                else:
                    nv = list(vs)
                    nv[i] = (1, vs[i][1])
                    out.append((f"att_forged_ack{i}", (tuple(nv), gw, net, att + 1, loss, gone)))
    return out


def suppressed(st) -> set:
    vs, gw, net, *_ = st
    return {i for i, (s, _) in enumerate(vs) if s == 1 and i not in gw and ("alert", i) not in net}


def check(rule: str, n: int, comp: frozenset) -> dict:
    s0 = (tuple((0, 0) for _ in range(n)), frozenset(), (), 0, 0, False)
    seen = {s0: (None, None)}
    q = deque([s0])
    worst, worst_st = -1, None
    honest_supp, honest_st = 0, None
    giveup_honest = None
    nstates = 0
    while q:
        st = q.popleft()
        nstates += 1
        sp = suppressed(st)
        if len(sp) > worst:
            worst, worst_st = len(sp), st
        hs = {i for i in sp if i not in comp}
        if len(hs) > honest_supp:
            honest_supp, honest_st = len(hs), st
        vs, gw, net, *_ = st
        if giveup_honest is None and any(vs[i][0] == 2 and i not in gw and i not in comp for i in range(n)):
            giveup_honest = st
        for a, nx in succ(st, rule, comp, n):
            if nx not in seen:
                seen[nx] = (st, a)
                q.append(nx)

    def trace(st):
        out = []
        while seen[st][0] is not None:
            out.append(seen[st][1])
            st = seen[st][0]
        return list(reversed(out))

    return dict(states=nstates, max_suppressed=worst, max_fraction=worst / n, honest_suppressed=honest_supp, honest_fraction=honest_supp / n,
                trace_worst=trace(worst_st) if worst > 0 else None, trace_honest=trace(honest_st) if honest_supp else None,
                honest_gave_up_without_delivery=giveup_honest is not None, attacker_actions_worst=(sum(1 for a in trace(worst_st) if a.startswith("att_")) if worst > 0 else None))


def cost_and_bytes() -> dict:
    """Operation count and ACK length with real code; the time is the simulated H5 timing (a placeholder, not a measurement)."""
    master = b"M" * 32
    ka, kb = kdf(master, 7), kdf(master, 9)
    alert = P.encode_alert(P.Alert(node_id=7, event_id=1, counter=5, timestamp_ms=1, severity=3, impact_side=0, peak_g_x100=500, ml_prob_x10000=9000, lat_e7=1, lon_e7=1), ka)
    ack = P.encode_ack(P.Ack(7, 1, 5, 1), ka)
    shared_len = len(P.encode_ack(P.Ack(7, 1, 5, 1), master))
    ok_own = V.node_accepts_ack(ack, ka, 7, 1, 5)
    ok_other = V.node_accepts_ack(P.encode_ack(P.Ack(7, 1, 5, 1), kb), ka, 7, 1, 5)  # vehicle 9's key used for vehicle 7's ACK
    ok_old = V.node_accepts_ack(P.encode_ack(P.Ack(7, 1, 4, 1), ka), ka, 7, 1, 5)  # genuine ACK of an older counter
    # an alert signed with vehicle 9's key but naming node 7: the base derives K_7 and rejects the tag
    forged_alert = P.encode_alert(P.Alert(node_id=7, event_id=1, counter=6, timestamp_ms=1, severity=3, impact_side=0, peak_g_x100=500, ml_prob_x10000=9000, lat_e7=1, lon_e7=1), kb)
    forged_rejected = not P.tag_ok(forged_alert, ka, len(forged_alert) - 8)
    t0 = time.perf_counter()
    for _ in range(2000):
        kdf(master, 7)
    kdf_us_host = (time.perf_counter() - t0) / 2000 * 1e6
    h5 = json.loads(Path("data/simulated_hardware/protocol_logs/edge_timing_H5.json").read_text(encoding="utf-8"))["records"]
    hmac_us = float(np.median([r["hmac_sign_us"] for r in h5]))
    return dict(ack_len_shared=shared_len, ack_len_pervehicle=len(ack), alert_len=len(alert), own_ack_accepted=ok_own, other_vehicle_key_ack_accepted=ok_other, old_counter_ack_accepted=ok_old,
                forged_alert_other_node_rejected=forged_rejected, kdf_us_host=kdf_us_host, hmac_us_h5_median=hmac_us)


def main() -> None:
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="ANALYTICAL"):
        ent.append(dict(name=f"ar.r4.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    res = {}
    for grid, n in (("design", 2), ("held", 3)):
        for rule, comp, tag in (("baseline", frozenset({0}), "shared_key_per_node_ack"), ("osdr", frozenset({0}), "shared_key_event_ack"), ("pervehicle", frozenset({0}), "per_vehicle_one_compromised"),
                                ("pervehicle", frozenset(range(n)), "per_vehicle_master_key_limit")):
            r = check(rule, n, comp)
            res[(grid, tag)] = r
            p = f"{grid}.v{n}.{tag}"
            add(f"{p}.states", r["states"], "states", f"reachable states (attacker actions at most {MAX_ATT}, losses at most {MAX_LOSS}, sends at most {MAX_TRIES})")
            add(f"{p}.max_suppressed_fraction", round(r["max_fraction"], 4), "fraction", "largest share of vehicles stopped while the gateway holds no alert of them, in any reachable state")
            add(f"{p}.honest_suppressed_fraction", round(r["honest_fraction"], 4), "fraction", "the same share counting only vehicles that are not compromised")
            add(f"{p}.attacker_actions_for_max", r["attacker_actions_worst"], "actions", "length of the shortest attack reaching the maximum (None = no suppression)")
            add(f"{p}.honest_gave_up_without_delivery", int(r["honest_gave_up_without_delivery"]), "flag", "an honest vehicle used all its tries and the gateway holds no alert (1 = a path exists; the loss bound is below the number of tries, so it must be 0)")
            print(p, r["states"], r["max_fraction"], r["honest_fraction"], r["attacker_actions_worst"], r["trace_worst"], r["honest_gave_up_without_delivery"])
    c = cost_and_bytes()
    for k, v in c.items():
        add(f"cost.{k}", v if not isinstance(v, float) else round(v, 2), "value" if not k.endswith("us_host") and "us" not in k else "us",
            "operation check with the real packet code" if k.startswith(("ack_len", "alert_len", "own", "other", "old", "forged")) else "host time of one KDF (PC, not the ESP32)" if k.endswith("host") else "median hmac_sign_us of the simulated H5 file (a placeholder, not a measurement)",
            "SIMULATED_HW_FORMAT" if k == "hmac_us_h5_median" else "MEASURED_SOFTWARE" if k.endswith("us_host") or k.startswith(("ack_len", "alert_len", "own", "other", "old", "forged")) else "ANALYTICAL")
    held = res[("held", "per_vehicle_one_compromised")]
    design = res[("design", "per_vehicle_one_compromised")]
    a_ok = all(r["max_fraction"] <= 1 / n + 1e-9 and r["honest_fraction"] == 0 for r, n in ((design, 2), (held, 3))) and not held["honest_gave_up_without_delivery"]
    shared = res[("held", "shared_key_event_ack")]["max_fraction"]
    b_ok = c["ack_len_pervehicle"] == c["ack_len_shared"] == 26 and c["own_ack_accepted"] and not c["other_vehicle_key_ack_accepted"] and not c["old_counter_ack_accepted"]
    add("hR4a.criterion_met", int(a_ok), "flag", "suppressed fraction at most 1/V with one compromised vehicle (V = 2 design, V = 3 held-out), none of the honest vehicles; no other path found")
    add("hR4a.shared_key_event_ack_fraction", shared, "fraction", "the same measure for the shared key with an event-level ACK (the H-A3 counterexample)")
    add("hR4b.criterion_met", int(b_ok), "flag", "0 extra bytes (ACK stays 26 bytes) and one extra KDF per new vehicle id at the base; the other-vehicle key and the old-counter ACK are rejected")
    add("hR4b.extra_kdf_per_alert_without_cache", 1, "KDF", "count: derive K_i once per alert if the base keeps no cache")
    add("hR4b.extra_time_upper_bound_us", round(c["hmac_us_h5_median"], 1), "us", "one KDF costs no more than one HMAC; the simulated H5 file has a median hmac_sign_us (a placeholder, not a measurement)", "SIMULATED_HW_FORMAT")
    add("hR4.p_raw", 0.0 if (a_ok and b_ok) else 1.0, "p", "0 if (a) and (b) both hold, 1 otherwise (a model check and a count)")
    add("hR4.criterion_met", int(a_ok and b_ok), "flag", "H-R4 (a) and (b)")
    record_many(ent, purge_prefixes=("ar.r4.",))
    print(c)
    print("a_ok", a_ok, "b_ok", b_ok, "shared fraction", shared)


if __name__ == "__main__":
    main()
