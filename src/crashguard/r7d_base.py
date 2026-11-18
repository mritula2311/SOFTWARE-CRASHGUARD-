"""Round 7d: the reference configuration of the base that meets requirement R-REACK (docs/05_architecture/FRAME_LAYOUT.md section 12).

``BaseVerifier`` (src/crashguard/verifier.py, not edited) has the re-acknowledgement interval and the downlink budget switched OFF by default: ``reack_interval_s=None`` and ``budget=None``. With both off, a replayed
valid frame is re-acknowledged every time and every re-ACK is airtime. ``reference_base`` builds a verifier with both ON, with the values of the replay-flood study of ``crashguard.attacks`` (stored keys
``attacks.flood.*``): interval = the shortest spacing of two tries of the same alert (its airtime, the processing time, the ACK airtime and the margin of ``delivery_sim.retry_interval_s``), and a token-bucket
downlink budget that refills at the duty cycle of ``crashguard.lora.DUTY`` with a capacity of 360 s.

    python -m crashguard.r7d_base          # regression against the stored flood keys; keys r7d.*
"""
from __future__ import annotations

import json
from pathlib import Path

from crashguard import attacks as A
from crashguard import packet as P
from crashguard import verifier as V
from crashguard.delivery_sim import retry_interval_s
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7d_base.py"
BUDGET_CAPACITY_S = 360.0  # DutyBudget default


def reack_interval_s(sf: int) -> float:
    """R-REACK value 1: no re-ACK of the same (node, event) sooner than the shortest legitimate retry spacing."""
    return retry_interval_s(sf)


def reference_base(key: bytes, sf: int = 7, store: Path | None = None, initial_budget_s: float | None = None) -> V.BaseVerifier:
    """A base that meets R-REACK: the re-ACK interval and the downlink budget are on."""
    return V.BaseVerifier(key, store, reack_interval_s=reack_interval_s(sf), budget=V.DutyBudget(capacity_s=BUDGET_CAPACITY_S, initial_s=initial_budget_s), sf=sf)


def flood(base_factory) -> dict:
    """The replay flood of ``crashguard.attacks.flood`` (20 replays per second for 120 s of one captured valid alert; a genuine alert at 100 s) with the base built by ``base_factory``."""
    v = base_factory()
    raw = P.encode_alert(A._alert(10), A.KEY)
    v.handle(raw, 0.0)
    legit = P.encode_alert(A._alert(50, event_id=7), A.KEY)
    counts: dict = {}
    legit_dec = None
    for i in range(1, A.FLOOD_RATE_PER_S * A.FLOOD_S + 1):
        t = i / A.FLOOD_RATE_PER_S
        if legit_dec is None and t >= A.LEGIT_AT_S:
            legit_dec = v.handle(legit, t)[0]
        d = v.handle(raw, t)[0]
        counts[d] = counts.get(d, 0) + 1
    n = counts.get(V.REACK, 0)
    return dict(reacks=n, airtime_s=n * v.ack_airtime_s, no_budget=counts.get(V.REACK_NO_BUDGET, 0), limited=counts.get(V.REACK_LIMITED, 0), legit=legit_dec, budget_left_s=v.budget.tokens)


def main() -> None:
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    off = flood(lambda: V.BaseVerifier(A.KEY, reack_interval_s=None, budget=V.DutyBudget(initial_s=A.BASE_BUDGET_INITIAL_S), sf=A.FLOOD_SF))
    on = flood(lambda: reference_base(A.KEY, A.FLOOD_SF, initial_budget_s=A.BASE_BUDGET_INITIAL_S))
    ent: list[dict] = []

    def add(name, v, unit, note="", origin="ANALYTICAL"):
        ent.append(dict(name=f"r7d.reack.{name}", value=v, unit=unit, origin=origin, source_file=SRC, notes=note))

    ok_off = off["reacks"] == R["attacks.flood.no_limit.reacks_sent"] and abs(off["airtime_s"] - R["attacks.flood.no_limit.reack_airtime_s"]) < 1e-3 and off["legit"] == R["attacks.flood.no_limit.genuine_alert_during_flood"]
    ok_on = on["reacks"] == R["attacks.flood.with_limit.reacks_sent"] and abs(on["airtime_s"] - R["attacks.flood.with_limit.reack_airtime_s"]) < 1e-3 and on["legit"] == R["attacks.flood.with_limit.genuine_alert_during_flood"]
    add("matches_stored_flood_off", int(ok_off), "flag", "the replay flood with the limits off reproduces the stored attacks.flood.no_limit keys (a regression of the reference configuration, not a new experiment)")
    add("matches_stored_flood_on", int(ok_on), "flag", "the same with reference_base reproduces the stored attacks.flood.with_limit keys")
    for sf in (7, 8, 9):
        add(f"interval_s.sf{sf}", reack_interval_s(sf), "s", "R-REACK interval: alert airtime + 0.1 s processing + ACK airtime + 0.1 s margin")
    add("budget.duty", V.DUTY, "fraction", "refill rate of the downlink budget (crashguard.lora.DUTY)")
    add("budget.capacity_s", BUDGET_CAPACITY_S, "s", "capacity of the token bucket (DutyBudget default)")
    add("budget.initial_s_in_flood_study", A.BASE_BUDGET_INITIAL_S, "s", "budget left when the flood starts in the stored study")
    add("flood.off.reacks", off["reacks"], "re-ACKs", "limits off: replays of one valid frame that were re-acknowledged in 120 s")
    add("flood.off.airtime_s", off["airtime_s"], "s", "downlink airtime of those re-ACKs (26-byte ACK at SF7)")
    add("flood.off.refused_no_budget", off["no_budget"], "replays", "replays that found the budget empty")
    add("flood.off.budget_left_s", off["budget_left_s"], "s")
    add("flood.off.genuine_alert", off["legit"], "decision", "a genuine alert at 100 s is accepted but gets no ACK")
    add("flood.on.reacks", on["reacks"], "re-ACKs")
    add("flood.on.airtime_s", on["airtime_s"], "s")
    add("flood.on.refused_by_interval", on["limited"], "replays")
    add("flood.on.budget_left_s", on["budget_left_s"], "s")
    add("flood.on.genuine_alert", on["legit"], "decision", "a genuine alert at 100 s is accepted and acknowledged")
    add("flood.on.share_of_initial_budget_spent", on["airtime_s"] / A.BASE_BUDGET_INITIAL_S, "fraction", "airtime of the re-ACKs over the budget at the start of the flood (before refill)")
    add("flood.default_verifier_has_limits_off", int(V.BaseVerifier(A.KEY).reack_interval_s is None and V.BaseVerifier(A.KEY).budget is None), "flag", "BaseVerifier defaults: both off")
    record_many(ent, purge_prefixes=("r7d.",))
    for e in ent:
        print(e["name"], e["value"])


if __name__ == "__main__":
    main()
