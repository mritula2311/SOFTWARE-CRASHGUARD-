"""Round 7 A1 (analytic part), the bound D_max and H-R7-A3 (docs/02_preregistration/PREREGISTRATION_V18.md sections 2.2 and 2.4). Keys ``r7.a.*``, all ANALYTICAL.

    python -m crashguard.r7_analytic

Every formula is written in docs/03_results/ROUND7_A.md next to its inputs. Nothing here is a hypothesis test; H-R7-A3 is descriptive.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from crashguard import r7_engine as E
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7_analytic.py"
SFS = (7, 8, 9)
SFS_ALL = (7, 8, 9, 10, 11, 12)
MODELS = {"H1": ("H", 0.01 * 3600.0), "H10": ("H", 0.10 * 3600.0), "T10": ("T", None)}
K = 4


def A(n: int, sf: int) -> float:
    return E.air(n, sf)


def w_event(sf: int) -> float:
    """Node airtime of a fully ACK-suppressed two-stage event on the confirm path: 4 flash tries and 4 confirm tries (the shipped caps)."""
    return 4 * A(14, sf) + 4 * A(97, sf)


def w_cancel(sf: int) -> float:
    return 4 * A(14, sf) + 3 * A(14, sf)


def n_star(sf: int, allowance_s: float) -> int:
    """V18: n* = ceil(B / W_e), the number of fully suppressed events at which the old policy has spent the trailing-hour allowance."""
    return math.ceil(allowance_s / w_event(sf))


def n_first_fail(sf: int, allowance_s: float) -> int:
    """Smallest number of earlier fully suppressed events after which the old policy cannot send the next event's confirm inside the allowance (the next event's own flash tries are counted)."""
    return int((allowance_s - 4 * A(14, sf) - A(97, sf)) // w_event(sf)) + 1


def n_h_limit(sf: int, allowance_s: float) -> int:
    """Largest number of earlier fully suppressed events (4 confirm copies each, no flash) after which the reserved policy can still send the next confirm: n 4 A97 + A97 <= B."""
    return int((allowance_s - A(97, sf)) // (4 * A(97, sf)))


def event_duration_old(sf: int, t_e: float = 0.05) -> float:
    """End of the radio use of a fully suppressed event under the old policy with no duty layer."""
    o = E.run_event(E.Spec(True, True, t_e, sf, "old"), E.Duty("none"), 0.0, lambda i: True, lambda i: False)
    return o["end"]


def t10_chain(sf: int, t_e: float, policy: str) -> dict:
    o = E.run_event(E.Spec(True, True, t_e, sf, policy), E.Duty("T"), 0.0, lambda i: True, lambda i: False)
    return dict(n_f=o["n_f"], follow_start=o["follow_start"], delay=o["follow_delay"], confirm_end_try1=o["follow_start"] + A(97, sf))


def d_max(sf: int, model: str, k: int = K) -> dict:
    """Bound of the reserved policy: first copy and k-th copy of the confirm, as functions of SF and the duty model."""
    a14, a97 = A(14, sf), A(97, sf)
    if model == "T10":
        first = 0.0
        kth = first + (k - 1) * max(a97 + E.W_NS3, 10.0 * a97)
    else:
        first = a14 + E.W_NS3
        kth = first + (k - 1) * (a97 + E.W_NS3)
    return dict(first=first, kth=kth)


def sat_delay(sf: int, d: float) -> float:
    """Delay of a frame that meets an allowance that is full at a sustained use: the window refills at d seconds of airtime per second, so a frame of airtime A waits about A / d (ANALYTICAL, steady state)."""
    return A(97, sf) / d


def gating(sf: int, model: str) -> dict:  # noqa: PLR0912
    """H-R7-A3: the link-aware gating rule of DELTA_DUTY_LOCKOUT.md section 5 with and without the reserve. The load gate is the stored one (SF7 passes, SF9 fails, others not run)."""
    load_open = {7: True, 9: False}.get(sf)  # None = not run
    out: dict = dict(sf=sf, model=model, load_gate=load_open)
    t_s = 0.050 + E.COMPUTE
    if model == "T10":
        d = 0.10
        a_f = A(14, sf)
        cond_a = a_f <= d * (E.T_F - t_s)  # condition A of the lockout analysis (median decision time)
        out["lockout_gate_old"] = cond_a
        out["lockout_gate_reserved"] = cond_a  # the time reserve admits the first flash iff s_f + A_f / d <= T_F, the same inequality
        # flash tries admitted by the time reserve with the median decision time
        n = 0
        s = t_s
        rf = -math.inf
        while n < 4:
            s = max(s, rf)
            if s + 10.0 * a_f > E.T_F + 1e-9:
                break
            n += 1
            rf = s + 10.0 * a_f
            s = rf
        out["flash_tries_reserved"] = n
        out["flash_tries_old"] = 4
    else:
        out["lockout_gate_old"] = True
        out["lockout_gate_reserved"] = True
        _, allow = MODELS[model]
        R = K * A(97, sf) + A(E.MICRO13, sf)
        out["reserve_s"] = R
        out["reserve_share_of_allowance"] = R / allow
        out["flash_fits_beside_reserve"] = allow - R >= 4 * A(14, sf)
    old_open = (load_open if load_open is not None else None)
    out["cutoff_open_old"] = None if old_open is None else bool(old_open and out["lockout_gate_old"])
    out["cutoff_open_reserved"] = None if old_open is None else bool(old_open and out["lockout_gate_reserved"] and out.get("flash_fits_beside_reserve", True))
    return out


def main() -> None:  # noqa: PLR0915
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r7.a.{name}", value=(round(v, 6) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin="ANALYTICAL", source_file=SRC, notes=note))

    for sf in SFS_ALL:
        for n in (8, 13, 14, 26, 97):
            add(f"air.sf{sf}.b{n}", A(n, sf), "s", "time on air, crashguard.lora.airtime_ms")
    for sf in SFS:
        we, wc = w_event(sf), w_cancel(sf)
        add(f"sf{sf}.node_air_event_confirm_path", we, "s", "4 A14 + 4 A97, every ACK suppressed")
        add(f"sf{sf}.node_air_event_cancel_path", wc, "s", "4 A14 + 3 A14")
        add(f"sf{sf}.attacker_cost_per_event", 8 * A(26, sf), "s", "upper bound: jam the whole 26-byte ACK of each of the 8 frames (4 flash, 4 confirm); a reactive jammer needs fewer symbols, not used as a number")
        add(f"sf{sf}.attacker_cost_ratio", 8 * A(26, sf) / we, "ratio", "attacker airtime per event over the node's airtime per event")
        add(f"sf{sf}.event_duration_old", event_duration_old(sf), "s", "end of radio use of a fully suppressed event, old policy, no duty layer, t_E = 50 ms")
        for m, (kind, allow) in MODELS.items():
            if kind == "H":
                add(f"{m}.sf{sf}.n_star", n_star(sf, allow), "events", "ceil(B / W_e), V18 definition")
                add(f"{m}.sf{sf}.n_first_fail", n_first_fail(sf, allow), "events", "smallest number of earlier suppressed events after which the old policy cannot send the next confirm inside the allowance")
                add(f"{m}.sf{sf}.n_h_limit", n_h_limit(sf, allow), "events", "largest number of earlier suppressed events (4 confirm copies each) after which the reserved policy still sends the next confirm")
                add(f"{m}.sf{sf}.sat_delay", sat_delay(sf, allow / 3600.0), "s", "A97 / d: wait of a confirm that meets a full allowance at sustained use")
            dm = d_max(sf, m)
            add(f"{m}.sf{sf}.dmax_first", dm["first"], "s", "reserved policy: first copy of the follow-up")
            add(f"{m}.sf{sf}.dmax_kth", dm["kth"], "s", f"reserved policy: k = {K}th copy")
        for tag, te in (("median", 0.050), ("mean", 0.1124386)):
            o, r = t10_chain(sf, te, "old"), t10_chain(sf, te, "reserved")
            add(f"T10.sf{sf}.{tag}.old_confirm_delay", o["delay"], "s", f"old policy, 10% per-transmission off-time, all ACKs suppressed, t_E = {te} s: confirm start minus T_F")
            add(f"T10.sf{sf}.{tag}.old_confirm_start", o["follow_start"], "s", "")
            add(f"T10.sf{sf}.{tag}.reserved_confirm_delay", r["delay"], "s", "reserved policy, same inputs")
            add(f"T10.sf{sf}.{tag}.reserved_flash_tries", r["n_f"], "tries", "flash tries the time reserve admits")
    for sf in SFS_ALL:
        for m in MODELS:
            g = gating(sf, m)
            for key, v in g.items():
                if key in ("sf", "model"):
                    continue
                add(f"a3.{m}.sf{sf}.{key}", v if v is not None else "NOT_RUN", "bool or s or tries" if key != "reserve_s" else "s", "H-R7-A3 descriptive; load gate from the stored R6-7 runs (SF7 pass, SF9 fail, others not run)")
    record_many(ent, purge_prefixes=("r7.a.",))
    (ROOT / "results" / "tables").mkdir(parents=True, exist_ok=True)
    (ROOT / "results" / "tables" / "r7_analytic.json").write_text(json.dumps({e["name"]: e["value"] for e in ent}, indent=1), encoding="utf-8")
    print(len(ent), "keys")


if __name__ == "__main__":
    main()
