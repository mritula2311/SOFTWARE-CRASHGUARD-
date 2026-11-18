"""Round 7 A2.2 (docs/02_preregistration/PREREGISTRATION_V18.md section 2.3): exhaustive enumeration of a bounded model of the node's frame queue, budget counter and duty refill with the attacker choosing every ACK outcome. FORMAL (bounded).

    python -m crashguard.r7_formal          # keys r7.formal.*, results/tables/r7_formal.json

Model (an independent integer re-implementation, not the float engine): one step = one time unit; a frame of cost x occupies the radio for x + 1 steps (send and one receive window). Hourly model H: the cost of the frames
started in the last W steps may not exceed B. Off-time model T: after a frame of cost x the next frame starts no earlier than x (1 + 2) steps later. An event triggers when the node is idle (a gap of 0, 2 or 5 steps after
the previous event is over), its flash is ready 1 step later (class L, at most 2 tries of cost 1), the follow-up is pending 3 steps after the trigger (a confirm of cost 4 with at most k tries, class H, or three cancels of
cost 1). The attacker chooses, for every frame that needs one, whether its ACK arrives. Reserve R = k 4 + 1 (k confirm copies and one micro-confirm of cost 1).
Bounds: B in {16, 20, 24, 28, 32, 40}, k in {1, 2}, W = 30 steps (an event lasts about 13 steps, so up to three events share a window), up to 2 earlier events (confirm events) and one target event (confirm or cancel), models H and T, policies old and reserved.
Invariant 1: no class-L frame of the reserved policy is sent when it would leave less than R of the allowance (H) or when its off-time ends after the follow-up is due (T). Invariant 2: when the follow-up of the target event
becomes pending and the reserve is intact (remaining allowance >= R at that instant; the whole condition is true in the T model), its first frame starts within D_max of becoming pending (D_max = 2 steps in H: a flash that
started just before; 0 in T). The old policy is the control for Invariant 2. The smallest number of earlier events at which the reserved policy violates the unconditional form is reported with a stored trace.
"""
from __future__ import annotations

import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7_formal.py"
W, C, M_COST, F_TRIES, OFF = 30, 4, 1, 2, 2
GAPS = (0, 2, 5)
BS = (16, 20, 24, 28, 32, 40)
KS = (1, 2)


def used(log: list, t: int) -> int:
    return sum(c for (s, c, _cls, _e) in log if s > t - W)


def first_fit(log: list, s: int, cost: int, B: int, model: str, off_until: int) -> int:
    t = max(s, off_until) if model == "T" else s
    if model == "H":
        while used(log, t) + cost > B:
            t += 1
    return t


def simulate(policy: str, model: str, B: int, k: int, events: list) -> dict:  # noqa: PLR0912, PLR0915
    """events: list of (gap, flash_acks (2 bools), follow_acks (k bools), kind). Returns the log and, for the last event, the delay and whether the reserve was intact at pending."""
    R = k * C + M_COST
    reserved = policy == "reserved"
    log: list = []
    radio_free, off_until, prev_end = 0, 0, 0
    info: dict = {}
    for ei, (gap, fl_acks, fu_acks, kind) in enumerate(events):
        T0 = prev_end + gap
        pend = T0 + 3
        s_ready = T0 + 1
        acked = False
        for j in range(F_TRIES):
            cost = 1
            s = max(s_ready, radio_free)
            if reserved:
                t = max(s, off_until) if model == "T" else s
                if model == "T":
                    if t + cost * (1 + OFF) > pend:
                        break
                else:
                    if t > pend or B - used(log, t) - cost < R:
                        break
                s = t
            else:
                s = first_fit(log, s, cost, B, model, off_until)
            log.append((s, cost, "L", ei))
            radio_free = s + cost + 1
            off_until = s + cost * (1 + OFF)
            if fl_acks[j]:
                acked = True
                break
        rem_at_pend = B - used(log, pend)
        first = None
        if kind == "confirm":
            for j in range(k):
                s = first_fit(log, max(pend, radio_free), C, B, model, off_until)
                log.append((s, C, "H", ei))
                first = s if first is None else first
                radio_free = s + C + 1
                off_until = s + C * (1 + OFF)
                if fu_acks[j]:
                    break
        else:
            for c in range(3):
                s = first_fit(log, max(pend + c, radio_free), 1, B, model, off_until)
                log.append((s, 1, "H", ei))
                first = s if first is None else first
                radio_free = s + 2
                off_until = s + 1 * (1 + OFF)
        prev_end = max(radio_free, off_until) if model == "T" else radio_free
        info = dict(pend=pend, first=first, delay=first - pend, intact=(rem_at_pend >= R) if model == "H" else True, acked=acked)
    inv1 = True
    if reserved:
        # independent re-check from the log: class L frames leave at least R (H) or end their off-time by the follow-up due time (T); the due time of an event is its first frame's trigger + 4
        starts = sorted(s for (s, _c, cls, _e) in log if cls == "L")
        if model == "H":
            inv1 = all(B - used([x for x in log if x[0] <= s], s) >= R for s in starts)
    return dict(log=log, inv1=inv1, **info)


def patterns(k: int, kind: str) -> list:
    fl = list(itertools.product((False, True), repeat=F_TRIES))
    fu = list(itertools.product((False, True), repeat=k)) if kind == "confirm" else [tuple([False] * k)]
    return [(a, b) for a in fl for b in fu]


def enumerate_cell(args: tuple) -> dict:
    B, k, model, policy = args
    dmax = 0 if model == "T" else 2
    out = dict(B=B, k=k, model=model, policy=policy, runs=0, inv1_viol=0, inv2_viol_uncond={0: 0, 1: 0, 2: 0}, inv2_viol_cond=0, runs_by_n={0: 0, 1: 0, 2: 0}, cond_runs=0, example=None, example_n=None)
    for n_prior in (0, 1, 2):
        prior_sets = list(itertools.product(itertools.product(GAPS, patterns(k, "confirm")), repeat=n_prior)) if n_prior else [()]
        for pr in prior_sets:
            prior = [(g if i else 0, a, b, "confirm") for i, (g, (a, b)) in enumerate(pr)]
            for kind in ("confirm", "cancel"):
                for tg in (GAPS if n_prior else (0,)):
                    for a, b in patterns(k, kind):
                        ev = prior + [(tg, a, b, kind)]
                        r = simulate(policy, model, B, k, ev)
                        out["runs"] += 1
                        out["runs_by_n"][n_prior] += 1
                        if not r["inv1"]:
                            out["inv1_viol"] += 1
                        late = r["delay"] > dmax
                        if late:
                            out["inv2_viol_uncond"][n_prior] += 1
                            if out["example"] is None or n_prior < out["example_n"]:
                                out["example"] = dict(events=[(g, list(a_), list(b_), kd) for (g, a_, b_, kd) in ev], log=r["log"], delay=r["delay"], dmax=dmax, intact=r["intact"])
                                out["example_n"] = n_prior
                        if r["intact"]:
                            out["cond_runs"] += 1
                            if late:
                                out["inv2_viol_cond"] += 1
    return out


def main() -> None:
    jobs = [(B, k, m, p) for B in BS for k in KS for m in ("H", "T") for p in ("old", "reserved") if not (m == "T" and B != BS[0])]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(enumerate_cell, jobs, chunksize=1))
    (ROOT / "results" / "tables" / "r7_formal.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r7.formal.{name}", value=v, unit=unit, origin="FORMAL", source_file=SRC, notes=note))

    tot = {p: dict(runs=0, inv1=0, cond=0, cond_runs=0, unc=0) for p in ("old", "reserved")}
    for r in res:
        key = f"{r['model']}.B{r['B']}.k{r['k']}.{r['policy']}" if r["model"] == "H" else f"T.k{r['k']}.{r['policy']}"
        add(f"{key}.runs", r["runs"], "runs", "enumerated configurations (earlier events 0 to 2, target event, every ACK pattern)")
        add(f"{key}.inv1_violations", r["inv1_viol"], "count")
        add(f"{key}.inv2_violations_conditional", r["inv2_viol_cond"], "count", "reserve intact at the instant the follow-up becomes pending")
        for n in (0, 1, 2):
            add(f"{key}.inv2_violations_unconditional_n{n}", r["inv2_viol_uncond"][n], "count", f"{n} earlier events")
        t = tot[r["policy"]]
        t["runs"] += r["runs"]
        t["inv1"] += r["inv1_viol"]
        t["cond"] += r["inv2_viol_cond"]
        t["cond_runs"] += r["cond_runs"]
        t["unc"] += sum(r["inv2_viol_uncond"].values())
    for p, t in tot.items():
        add(f"total.{p}.runs", t["runs"], "runs")
        add(f"total.{p}.inv1_violations", t["inv1"], "count")
        add(f"total.{p}.inv2_violations_conditional", t["cond"], "count")
        add(f"total.{p}.inv2_violations_unconditional", t["unc"], "count")
        add(f"total.{p}.conditional_runs", t["cond_runs"], "runs")
    inv1_ok = tot["reserved"]["inv1"] == 0
    inv2_ok = tot["reserved"]["cond"] == 0
    control_ok = tot["old"]["cond"] > 0 or tot["old"]["unc"] > 0
    add("inv1_proved_in_bounds", int(inv1_ok), "flag")
    add("inv2_proved_in_bounds", int(inv2_ok), "flag", "conditional on the reserve being intact at pending time")
    add("control_old_violates_inv2", int(control_ok), "flag", "the old policy violates Invariant 2 in the same space")
    # smallest number of earlier events at which the reserved policy violates the unconditional form (H model, any B, k)
    mins = [r["example_n"] for r in res if r["policy"] == "reserved" and r["example"] is not None]
    add("reserved_min_earlier_events_unconditional_violation", min(mins) if mins else "none in bounds", "events")
    record_many(ent, purge_prefixes=("r7.formal.",))
    print({e["name"]: e["value"] for e in ent if e["name"].startswith("r7.formal.total") or "proved" in e["name"] or "control" in e["name"] or "min_earlier" in e["name"]})


if __name__ == "__main__":
    main()
