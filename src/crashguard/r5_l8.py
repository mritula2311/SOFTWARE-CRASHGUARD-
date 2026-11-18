"""L8 (docs/02_preregistration/PREREGISTRATION_V16.md section 15.4): spoofed-alert flood containment at the base.

    python -m crashguard.r5_l8 run          # H-L8a (exhaustive bounded model, FORMAL) and H-L8b (SIMULATED plus real rates); keys r5.l8.*

Base rule per vehicle: at most ``R`` high-confidence forwards in any window of 60 slots (slot = 1 minute) and at most one per slot (spacing of 60 s); an alert is implausible if its position change is
inconsistent with the reported speed or if the position repeats within 10 minutes; an implausible or over-rate alert is a strike (it is forwarded as low confidence); two strikes put the vehicle in
quarantine for the rest of the horizon, in which at most one alert per 10 slots is forwarded, as low confidence. H-L8a is decided by exhaustive exploration of the reachable states for every alert pattern of
one compromised vehicle over the 60-slot horizon. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import json
import sys

import numpy as np

R_HC = 6
HORIZON = 60
QUAR_GAP = 10
MAX_PER_SLOT = 4
KINDS = ("ok", "implausible", "repeat")  # attributes the adversary may give an alert: a plausible new position, an implausible jump, a repeated position
STRIKES_TO_QUARANTINE = 2


def initial() -> tuple:
    """State: (hc_count, last_hc_slot or -1, strikes, quarantined, last_quarantine_forward_slot or -1)."""
    return (0, -1, 0, False, -1)


def process(state: tuple, slot: int, kind: str) -> tuple[tuple, str]:
    """One alert in ``slot`` of the given kind. Returns the new state and the forward class: "high", "low" or "drop"."""
    hc, last_hc, strikes, quar, last_q = state
    if quar:
        if last_q < 0 or slot - last_q >= QUAR_GAP:
            return (hc, last_hc, strikes, quar, slot), "low"
        return state, "drop"
    over = (hc >= R_HC) or (last_hc == slot)  # the window is the whole horizon (60 slots), so the window count is hc
    if kind != "ok" or over:
        strikes += 1
        quar = strikes >= STRIKES_TO_QUARANTINE
        return (hc, last_hc, strikes, quar, last_q), "low"
    return (hc + 1, slot, strikes, quar, last_q), "high"


def patterns(max_per_slot: int = MAX_PER_SLOT):
    """All multisets of alert kinds in one slot (order inside a slot is explored as sequences, so every order is covered)."""
    import itertools

    out = [()]
    for n in range(1, max_per_slot + 1):
        out += list(itertools.product(KINDS, repeat=n))
    return out


def explore(horizon: int = HORIZON, max_per_slot: int = MAX_PER_SLOT) -> dict:
    """Reachable states slot by slot for every adversary pattern; returns the largest number of high-confidence forwards, the largest number of low-confidence forwards and the state counts."""
    pats = patterns(max_per_slot)
    frontier = {initial()}
    seen_total, max_hc, max_low = 1, 0, 0
    low_by_state = {initial(): 0}
    for slot in range(horizon):
        nxt: dict[tuple, int] = {}
        for st in frontier:
            low0 = low_by_state[st]
            for pat in pats:
                s, low = st, low0
                for kind in pat:
                    s, cls = process(s, slot, kind)
                    low += cls == "low"
                if s not in nxt or low > nxt[s]:
                    nxt[s] = low
                max_hc = max(max_hc, s[0])
                max_low = max(max_low, low)
        frontier = set(nxt)
        low_by_state = nxt
        seen_total += len(frontier)
    return dict(max_high=max_hc, max_low=max_low, states_visited=seen_total, patterns_per_slot=len(pats), horizon=horizon)


# ------------------------------------------------------------------------------------------------ H-L8b
def legit_quarantined(rate_per_hour: float, vehicle_hours: int, seed: int = 42) -> dict:
    """Legitimate vehicles: alerts at Poisson times with plausible new positions (speed 0 to 30 m/s, so the position change is consistent); a duplicate in the same slot counts as an over-rate alert.
    Returns the number of vehicle-hours, of alerts and of vehicle-hours with a quarantine or a strike."""
    rng = np.random.default_rng(seed)
    n_alerts = quarantined = strikes_any = high_denied = 0
    for _ in range(vehicle_hours):
        n = int(rng.poisson(rate_per_hour))
        slots = np.sort(rng.integers(0, HORIZON, n))
        st = initial()
        n_alerts += n
        for s in slots:
            st, cls = process(st, int(s), "ok")
            high_denied += cls != "high"
        quarantined += int(st[3])
        strikes_any += int(st[2] > 0)
    return dict(n_alerts=n_alerts, vehicle_hours=vehicle_hours, quarantined=quarantined, with_strike=strikes_any, not_high=high_denied)


def real_rate_per_vehicle_hour(events_per_hour: float = 10.0) -> float:
    """Alerts per vehicle-hour: events per vehicle-hour times the share of VALIDATION events (all events, MEASURED_SOFTWARE) that alarm at the confirm threshold of the 1% target."""
    from crashguard import r5_det as D
    from crashguard import r5_l2 as L2

    fr = D.load_frames()
    det = D.fit_seed(42, fr)
    base = L2.baseline_arms(42, 0.01, fr, det)
    return float(events_per_hour * (base["F_va"] >= base["thr_f"]).mean())


def run() -> None:
    from crashguard import r5_common as R5
    from crashguard import r5_guard as G

    G.verify("l8", "r5.l8.hL8")
    rec = R5.Rec("r5.l8.", "src/crashguard/r5_l8.py", "FORMAL")
    res = explore()
    rec.add("a.max_high_confidence_forwards", res["max_high"], "alerts", "exhaustive exploration of every alert pattern of one compromised vehicle over 60 slots, up to 4 alerts per slot, 3 kinds each")
    rec.add("a.max_low_confidence_forwards", res["max_low"], "alerts", "descriptive: low-confidence forwards of the worst pattern")
    rec.add("a.states_visited", res["states_visited"], "states")
    rec.add("a.patterns_per_slot", res["patterns_per_slot"], "patterns")
    rec.add("a.bound_R", R_HC, "alerts")
    met_a = res["max_high"] <= R_HC
    rec.add("hL8a.criterion_met", int(met_a), "bool", "no pattern gets more than R high-confidence forwards in the hour (exhaustive bounded model; FORMAL)")
    rec.add("hL8a.scope", "an invariant of the per-hour counter and the quarantine state machine: the bound holds by construction of the counter, and the exploration confirms that the implemented state machine keeps it for every alert pattern; the plausibility test is abstracted to its outcome label, the counter has no refill within the 60-slot horizon", "text", "review of session 2: not a proof about the position, speed and time arithmetic")
    rate = real_rate_per_vehicle_hour()
    out = legit_quarantined(rate, 2000)
    rec.add("b.rate_per_vehicle_hour", rate, "alerts per vehicle-hour", "10 events per vehicle-hour times the share of validation events that alarm at the 1% target (MEASURED_SOFTWARE input)", origin="MEASURED_SOFTWARE")
    for k, v in out.items():
        rec.add(f"b.{k}", v, "count", "SIMULATED legitimate vehicles, 2,000 vehicle-hours, seed 42", origin="SIMULATED")
    met_b = out["quarantined"] == 0
    rec.add("hL8b.criterion_met", int(met_b), "bool", "no legitimate vehicle is quarantined in the replay", origin="SIMULATED")
    rec.add("hL8b.strike_free_share", 1 - out["with_strike"] / out["vehicle_hours"], "fraction", "share of legitimate vehicle-hours without any strike", origin="SIMULATED")
    rec.write()
    print(json.dumps(dict(res=res, rate=rate, legit=out, met_a=met_a, met_b=met_b), indent=1))


def freeze() -> None:
    from crashguard import r5_guard as G

    d = G.freeze("l8", ["src/crashguard/r5_l8.py", "src/crashguard/r5_l2.py", "src/crashguard/r5_det.py"], dict(R=R_HC, H=HORIZON, Q=QUAR_GAP, M=MAX_PER_SLOT), ["data/processed/r5_det_seed42.pkl"], "r5.l8.hL8")
    print("frozen l8", d["params_sha256"][:16])


def main() -> None:
    {"freeze": freeze, "run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()


if __name__ == "__main__":
    main()
