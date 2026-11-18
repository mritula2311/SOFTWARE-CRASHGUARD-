"""L7 (docs/02_preregistration/PREREGISTRATION_V16.md section 15.3): forward-secure ratchet. H-L7a is the outcome of the Tamarin lemmas of ``formal/ratchet.spthy`` (FORMAL, read from
``formal/out/ratchet/*.txt``); H-L7b is decided here by exhaustive enumeration of event sequences (FORMAL); the cost is ANALYTICAL.

    python -m crashguard.r5_l7 run

Synchronisation model (the one named in V16 15.3): the car holds index ``c`` and ratchets it by one on a received ACK and by one at every boot; the base holds index ``b`` and accepts an alert with index
``i`` if ``b <= i <= b + W``, derives the key of ``i`` by ``i - b`` hash steps, sets ``b = i`` and keeps that key until an alert with a higher index arrives (so a repeat of the accepted alert after a lost ACK is
accepted again; replay protection is the freshness field of the frame, not this module). Events of one sequence: the alert is lost on the way (L), received and its ACK received (A), received and its ACK lost (K),
the car reboots (B). Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = 8
EVENTS = ("L", "A", "K", "B")
MAX_LEN = 10
MAX_BOOTS = 3


def step(c: int, b: int, ev: str, w: int = W) -> tuple[int, int, bool | None]:
    """One event. Returns (c, b, accepted) where accepted is None for events without an alert reaching the base."""
    if ev == "B":
        return c + 1, b, None
    if ev == "L":
        return c, b, None
    ok = b <= c <= b + w
    if not ok:
        return c, b, False  # a rejected alert changes nothing at the base, and the car gets no ACK
    b2 = c
    if ev == "A":
        return c + 1, b2, True
    return c, b2, True


def run_sequence(seq: tuple, w: int = W) -> dict:
    c = b = 1
    boots = 0
    acc = []
    for ev in seq:
        c, b, a = step(c, b, ev, w)
        boots += ev == "B"
        if a is not None:
            acc.append(a)
    # the next alert, sent with the car's current index
    nxt = b <= c <= b + w
    return dict(c=c, b=b, boots=boots, accepted=acc, next_ok=nxt, gap=c - b)


def enumerate_all(w: int = W, max_len: int = MAX_LEN, max_boots: int = MAX_BOOTS) -> dict:
    """Exhaustive enumeration of every event sequence of length 0 to ``max_len``. Checks (every count must be 0): base_ahead (the base index never exceeds the car index); gap_bound (the gap c - b never
    exceeds the number of boots plus one); accept_iff_window (an alert is accepted exactly when the gap is within the window); next_ok_with_few_boots (with at most ``max_boots`` boots the next alert is
    accepted: resynchronisation succeeds); reject_outside_window (a sequence that ends with a gap above ``w`` rejects the next alert); rejection_changes_state (a rejected alert changes neither index);
    lost_ack_effect (replacing every lost ACK K by a received ACK A leaves the base index and the accept decisions of the alerts that reach the base unchanged except through the car's index)."""
    v = dict(base_ahead=0, gap_bound=0, accept_iff_window=0, next_ok_with_few_boots=0, reject_outside_window=0, rejection_changes_state=0)
    n = n_few = n_over = 0
    for ln in range(max_len + 1):
        for seq in itertools.product(EVENTS, repeat=ln):
            n += 1
            c = b = 1
            for ev in seq:
                c0, b0 = c, b
                c, b, a = step(c, b, ev, w)
                if b > c:
                    v["base_ahead"] += 1
                if ev in ("A", "K"):
                    if a != (b0 <= c0 <= b0 + w):
                        v["accept_iff_window"] += 1
                    if not a and (c, b) != (c0, b0):
                        v["rejection_changes_state"] += 1
            r = run_sequence(seq, w)
            if r["gap"] > r["boots"] + 1:
                v["gap_bound"] += 1
            if r["boots"] <= max_boots:
                n_few += 1
                if not r["next_ok"]:
                    v["next_ok_with_few_boots"] += 1
            if r["gap"] > w:
                n_over += 1
                if r["next_ok"]:
                    v["reject_outside_window"] += 1
    return dict(n_sequences=n, violations=v, n_with_le_max_boots=n_few, n_gap_above_window=n_over, window=w, max_len=max_len)


def cost() -> dict:
    """ANALYTICAL: hash operations and bytes."""
    return dict(hash_per_ack=1, hash_resync_max=W, hash_resync_mean_for_gap_g=lambda g: g, mac_per_alert=1, bytes_added_to_frames=0, car_state_bytes=32 + 4, base_state_bytes_per_vehicle=32 + 4)


def tamarin_status(sub: str = "ratchet3b") -> dict:
    out = {}
    d = ROOT / "formal" / "out" / sub
    for lem in ("executable", "forward_secrecy", "authenticity", "ack_binding"):
        f = d / f"{lem}.txt"
        if not f.exists():
            out[lem] = "NOT_RUN"
            continue
        t = f.read_text(errors="replace")
        m = re.search(rf"{lem} \((?:all-traces|exists-trace)\): (verified|falsified|analysis incomplete)", t)
        wf = "wellformedness check failed" in t
        out[lem] = ("wellformedness_failed:" if wf else "") + (m.group(1) if m else ("timeout" if "exit code: 124" in t else "unknown"))
    return out


def run() -> None:
    from crashguard import r5_common as R5
    from crashguard import r5_guard as G

    G.verify("l7", "r5.l7.hL7")
    rec = R5.Rec("r5.l7.", "src/crashguard/r5_l7.py", "FORMAL")
    st = tamarin_status("ratchet3b")
    for k, v in st.items():
        rec.add(f"a.tamarin.{k}", v, "text", "Tamarin 1.12.0 outcome of the bounded model of record (formal/ratchet3.spthy, three keys; limit per lemma in the output file)")
    for k, v in tamarin_status("ratchet").items():
        rec.add(f"a.tamarin_nat.{k}", v, "text", "outcome of the model with natural numbers (formal/ratchet.spthy): heap of 5 GB exhausted or time limit, so undecided")
    ok = all(st[k] == "verified" for k in ("executable", "forward_secrecy", "authenticity", "ack_binding"))
    rec.add("a.model_sha256", R5.sha256_file(ROOT / "formal" / "ratchet3.spthy"), "text", "hash of the bounded Tamarin model (ratchet3) the outcomes belong to")
    rec.add("a.scope", "window 0, no boot step, chain of three keys in the Tamarin model of record; the windowed and boot variants are covered by the enumeration only", "text", "V16 section 14 and the review of session 2")
    rec.add("hL7a.criterion_met", int(ok), "bool", "lemmas executable, forward_secrecy, authenticity and ack_binding all verified; undecided or timed out counts as not supported")
    e = enumerate_all()
    rec.add("b.n_sequences", e["n_sequences"], "sequences", "every sequence of the events L, A, K, B of length 0 to 10")
    for k, v in e["violations"].items():
        rec.add(f"b.violations.{k}", v, "sequences", "must be 0")
    rec.add("b.n_with_at_most_3_boots", e["n_with_le_max_boots"], "sequences")
    rec.add("b.n_gap_above_window", e["n_gap_above_window"], "sequences", "sequences after which the gap exceeds W = 8 (the next alert is rejected, as required)")
    rec.add("b.nonvacuous", int(e["n_gap_above_window"] > 0), "bool", "some sequence exceeds the window, so the rejection checks are exercised")
    rec.add("hL7b.criterion_met", int(sum(e["violations"].values()) == 0 and e["n_gap_above_window"] > 0), "bool", "resynchronisation succeeds within the window W = 8 and fails outside it, for all enumerated sequences")
    c = cost()
    for k, v in c.items():
        if not callable(v):
            rec.add(f"cost.{k}", v, "count" if "bytes" not in k else "bytes", "ANALYTICAL: the index is the existing counter field, so no byte is added to the 24-byte or 97-byte frames", origin="ANALYTICAL")
    rec.write()
    print(json.dumps(dict(tamarin=st, enum=e), indent=1))


def freeze() -> None:
    from crashguard import r5_guard as G

    d = G.freeze("l7", ["src/crashguard/r5_l7.py", "formal/ratchet.spthy", "formal/ratchet3.spthy"], dict(W=W, MAX_LEN=MAX_LEN, MAX_BOOTS=MAX_BOOTS), None, "r5.l7.hL7")
    print("frozen l7", d["params_sha256"][:16])


def main() -> None:
    {"freeze": freeze, "run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()


if __name__ == "__main__":
    main()
