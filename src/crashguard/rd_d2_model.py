"""H-D2c (ANALYTICAL, bounded explicit-state check of a MODEL; not a proof about firmware): can a node that holds only a vehicle key make another vehicle stop retrying under D2, and can anything make a vehicle
wait without bound?

Model. V vehicles (0 .. V-1), one gateway, one attacker. A vehicle is pending (0), stopped (1) or gave up (2); it has sent s alerts (at most 2), has deferred d times (at most 2) and may not send before tick
``until``. The gateway signs a cluster ACK with its private key (Ed25519; vehicles hold only the public key) listing the vehicles it has received. Time is a tick counter (T ticks). A vehicle stops only on a cluster ACK
that verifies, belongs to its event, is fresh and not yet processed by it, and lists it; on such a frame that does not list it, it defers (until = max(until, tick + DEFER)), at most 2 times.
Attacker (at most 3 actions, at most 2 message losses): (a) inject a frame with an invalid signature; (b) replay a genuine earlier cluster ACK of the same event (a frame of the gateway, fresh) or of an older event
(rejected); (c) flood: send valid alerts under its own vehicle key (the gateway lists it; nothing else changes); (d) only in the limit variant, forge a cluster ACK with the gateway key (a stolen gateway key is outside the claim).
Rules: ``d2`` (the design), ``osdr`` (shared key, an event-level ACK stops every pending vehicle; the H-A3 counterexample is reproduced as a control).
Bounds actually run: 2 vehicles with the preregistered bounds (attacker <= 3 actions, <= 2 losses); 3 vehicles with attacker <= 2 actions, <= 1 loss and one send per vehicle (the state space of the preregistered bounds is too large for this representation); sends <= 2 (2 vehicles), defers <= 3 (as in the simulator), ticks <= 3.
Limits of the model: the signature check is an abstraction (a frame is accepted if its signature field is the gateway's), so the cryptography is not checked here (it is unit-tested in tests/redesign); S2 holds largely by construction of the defer rule; the freshness window (T = 3 ticks) cannot reject a frame inside the horizon; the attacker's alerts are valid only under its own vehicle key (R4 per-vehicle keys).
Properties on every reachable state: S1 a stopped vehicle is in the gateway's received set (no suppression), unless the attacker used a forged valid-signature frame; S2 a defer never pushes ``until``
beyond tick + DEFER and a vehicle defers at most 2 times (a deferral is bounded)..

    python -m crashguard.rd_d2_model
"""
from __future__ import annotations

from collections import deque

from crashguard.rd_common import Rec

SRC = "src/crashguard/rd_d2_model.py"
MAX_TRIES, MAX_DEFERS, MAX_ATT, MAX_LOSS, DEFER, T = 2, 3, 2, 1, 2, 3


def succ(st, rule: str, key_gw: bool, n: int):
    vs, gw, net, proc, tick, att, loss, forged_used, sent_frames = st
    out = []
    for i in range(n):
        s, sends, defers, until = vs[i]
        if s == 0 and sends < MAX_TRIES and tick >= until and len(net) < 3:
            nv = list(vs)
            nv[i] = (0, sends + 1, defers, until)
            out.append((f"send{i}", (tuple(nv), gw, tuple(sorted(net + (("alert", i),))), proc, tick, att, loss, forged_used, sent_frames)))
        if s == 0 and sends >= MAX_TRIES and ("alert", i) not in net and i not in gw:
            nv = list(vs)
            nv[i] = (2, sends, defers, until)
            out.append((f"giveup{i}", (tuple(nv), gw, net, proc, tick, att, loss, forged_used, sent_frames)))
    if tick < T:
        out.append(("tick", (vs, gw, net, proc, tick + 1, att, loss, forged_used, sent_frames)))
    for k, m in enumerate(net):
        rest = net[:k] + net[k + 1:]
        if loss < MAX_LOSS:
            out.append(("lose", (vs, gw, rest, proc, tick, att, loss + 1, forged_used, sent_frames)))
        if m[0] == "alert":
            ng = gw | {m[1]}
            frame = ("cluster", ng, "gw_sig", tick)  # the gateway answers with a cluster ACK listing everything it holds
            nn = tuple(sorted(rest + (frame,))) if len(rest) < 3 else rest
            out.append(("gw_rx", (vs, ng, nn, proc, tick, att, loss, forged_used, sent_frames | {frame})))
        elif m[0] == "cluster":
            _, listed, sig, fresh = m
            ok_sig = sig == "gw_sig" or (sig == "forged_gw" and key_gw)
            out.append(("frame_drop", (vs, gw, rest, proc, tick, att, loss, forged_used, sent_frames)))
            if rule == "osdr":
                # event-level stop under the shared key: any valid-looking frame stops every pending vehicle
                if sig in ("gw_sig", "forged_shared"):
                    nv = tuple((1, a, b, c) if s == 0 else (s, a, b, c) for s, a, b, c in vs)
                    out.append(("deliver_all", (nv, gw, rest, proc, tick, att, loss, forged_used, sent_frames)))
                continue
            for j in range(n):
                if vs[j][0] != 0:
                    continue
                if not ok_sig or abs(tick - fresh) > T or (j, m) in proc:
                    continue
                s_, sends, defers, until = vs[j]
                np_ = proc | {(j, m)}
                if j in listed:
                    nv = list(vs)
                    nv[j] = (1, sends, defers, until)
                    out.append((f"stop{j}", (tuple(nv), gw, rest, np_, tick, att, loss, forged_used, sent_frames)))
                elif defers < MAX_DEFERS:
                    nv = list(vs)
                    nv[j] = (0, sends, defers + 1, max(until, tick + DEFER))
                    out.append((f"defer{j}", (tuple(nv), gw, rest, np_, tick, att, loss, forged_used, sent_frames)))
    if att < MAX_ATT:
        out.append(("att_bad_sig", (vs, gw, net, proc, tick, att + 1, loss, forged_used, sent_frames)))  # rejected by the signature check: no state change
        for fr in sorted(sent_frames, key=str):
            if len(net) < 3:
                out.append(("att_replay", (vs, gw, tuple(sorted(net + (fr,))), proc, tick, att + 1, loss, forged_used, sent_frames)))
        if len(net) < 3:
            out.append(("att_old_event", (vs, gw, net, proc, tick, att + 1, loss, forged_used, sent_frames)))  # a frame of an older event: rejected, no state change
        out.append(("att_flood", (vs, gw | {n}, net, proc, tick, att + 1, loss, forged_used, sent_frames)))  # the attacker's own alerts: the gateway lists a vehicle id n (outside 0..n-1)
        if rule == "osdr" and len(net) < 3:
            out.append(("att_forged_event_ack", (vs, gw, tuple(sorted(net + (("cluster", frozenset(), "forged_shared", tick),))), proc, tick, att + 1, loss, True, sent_frames)))
        if rule == "d2" and key_gw and len(net) < 3:
            for listed in (frozenset(range(n)),):
                out.append(("att_forged_gw_frame", (vs, gw, tuple(sorted(net + (("cluster", listed, "forged_gw", tick),))), proc, tick, att + 1, loss, True, sent_frames)))
    return out


def check(rule: str, n: int, key_gw: bool, att: int | None = None, loss: int | None = None, with_trace: bool = True, tries: int | None = None) -> dict:
    global MAX_ATT, MAX_LOSS, MAX_TRIES
    old = (MAX_ATT, MAX_LOSS, MAX_TRIES)
    MAX_ATT, MAX_LOSS, MAX_TRIES = (old[0] if att is None else att), (old[1] if loss is None else loss), (old[2] if tries is None else tries)
    try:
        return _check(rule, n, key_gw, with_trace)
    finally:
        MAX_ATT, MAX_LOSS, MAX_TRIES = old


def _check(rule: str, n: int, key_gw: bool, with_trace: bool = True) -> dict:
    s0 = (tuple((0, 0, 0, 0) for _ in range(n)), frozenset(), (), frozenset(), 0, 0, 0, False, frozenset())
    h0 = hash(s0)
    parent: dict = {h0: (None, None)} if with_trace else {}
    seen = set() if with_trace else {h0}  # without traces only 64-bit hashes of states are kept (a hash collision could hide a state; the probability is negligible at this size)
    q = deque([s0])
    viol = dict(S1=None, S2=None)
    nst = 0
    worst_supp = 0
    while q:
        st = q.popleft() if with_trace else q.pop()  # breadth first when traces are kept (shortest trace); depth first otherwise (a small frontier)
        nst += 1
        vs, gw, net, proc, tick, att, loss, forged_used, sent = st
        supp = [i for i, v in enumerate(vs) if v[0] == 1 and i not in gw]
        worst_supp = max(worst_supp, len(supp))
        if supp and viol["S1"] is None:
            viol["S1"] = st  # a vehicle stopped although the gateway holds no alert of it
        for v in vs:
            if v[0] == 0 and (v[2] > MAX_DEFERS or v[3] > tick + DEFER) and viol["S2"] is None:
                viol["S2"] = st
        for a, nx in succ(st, rule, key_gw, n):
            hn = hash(nx)
            if with_trace:
                if hn not in parent:
                    parent[hn] = (hash(st), a)
                    q.append(nx)
            elif hn not in seen:
                seen.add(hn)
                q.append(nx)

    def trace(st):
        out, h = [], hash(st)
        while parent[h][0] is not None:
            out.append(parent[h][1])
            h = parent[h][0]
        return list(reversed(out))

    return dict(states=nst, worst_suppressed=worst_supp, **{k: (None if v is None else (trace(v) if with_trace else ["(no trace kept)"])) for k, v in viol.items()})


def main() -> None:
    rec = Rec("rd.d2.model.", SRC, "ANALYTICAL")
    res = {}
    for name, rule, key_gw, n, att, loss, tr, *dfr in (("d2_vehiclekey_v2", "d2", False, 2, 3, 2, False), ("d2_vehiclekey_v3", "d2", False, 3, 2, 1, False, 1), ("osdr_shared_v2", "osdr", False, 2, 1, 0, True), ("d2_stolen_gateway_key_v2", "d2", True, 2, 1, 0, True)):
        r = check(rule, n, key_gw, att, loss, tr, dfr[0] if dfr else None)  # dfr = sends per vehicle
        res[name] = r
        rec.add(f"{name}.states", r["states"], "states", f"reachable states, rule {rule}, {n} vehicles, attacker actions <= {att}, losses <= {loss}, ticks <= {T}")
        rec.add(f"{name}.worst_suppressed", r["worst_suppressed"], "vehicles", "largest number of vehicles stopped while the gateway holds no alert of them, over reachable states")
        for k in ("S1", "S2"):
            rec.add(f"{name}.{k}_violation", int(r[k] is not None), "flag", {"S1": "a vehicle stopped without the gateway holding its alert", "S2": "a deferral was unbounded"}[k] + " (1 = counterexample)")
            if r[k] is not None:
                rec.add(f"{name}.{k}_trace", " > ".join(r[k]), "text", "shortest trace found")
    ok = all(res[k][s] is None for k in ("d2_vehiclekey_v2", "d2_vehiclekey_v3") for s in ("S1", "S2"))
    control = res["osdr_shared_v2"]["S1"] is not None  # the control must reproduce the H-A3 counterexample
    rec.add("hD2c.criterion_met", int(ok and control), "flag", "no vehicle-key holder can stop another vehicle or make a deferral unbounded; 2 vehicles with the preregistered bounds (attacker actions <= 3, losses <= 2), 3 vehicles with attacker actions <= 2, losses <= 1 and one send per vehicle (smaller than preregistered, state space); the shared-key event-level control reproduces the H-A3 counterexample")
    rec.add("hD2c.p_raw", 0.0 if (ok and control) else 1.0, "p", "a model check: 0 if met, 1 if not")
    rec.add("hD2c.stolen_gateway_key_outside_claim", int(res["d2_stolen_gateway_key_v2"]["S1"] is not None), "flag", "limit case: with the gateway private key an attacker can stop every vehicle (1 = yes); outside the claim")
    rec.write()
    print({k: (v["states"], v["worst_suppressed"], [x is not None for x in (v["S1"], v["S2"])]) for k, v in res.items()}, "criterion", ok and control)


if __name__ == "__main__":
    main()
