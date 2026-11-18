"""Round 7b G1 formal check (docs/02_preregistration/PREREGISTRATION_V19.md section 3): exhaustive enumeration of a bounded model of the node queue with a reserve for m follow-up events.

    python -m crashguard.r7b_formal          # keys r7b.formal.*, results/tables/r7b_formal.json

An independent re-implementation of the model of ``r7_formal`` (same event semantics) with two changes: the reserve covers m follow-up events, R = m x TC x C + M (TC = 2 confirm tries, C = 4, M = 1), and the
enumeration is a layered search over canonical states (the log is kept relative to the end of the previous event and pruned to the window), so that up to FIVE earlier events fit. Each state carries its multiplicity
and the first event list that reached it (for the stored trace). Frames and costs: flash 1 (class L, 2 tries), confirm 4 (class H, TC tries) or three cancels of cost 1 (class H); a frame occupies the radio for cost + 1 steps;
off-time model T: cost x (1 + 2) steps. Hourly model H: window W = 70 steps and allowance B. The attacker chooses every ACK outcome.
"""
from __future__ import annotations

import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7b_formal.py"
W, C, M_COST, TC, F_TRIES, OFF = 70, 4, 1, 2, 2, 2
GAPS = (0, 2)
BS = (40, 44, 48)
MS = (1, 4)
NMAX = 5
DMAX_H, DMAX_T = 2, 0


def used(log, t):
    return sum(c for (s, c, _cls) in log if s > t - W)


def first_fit(log, s, cost, B, model, off_until):
    t = max(s, off_until) if model == "T" else s
    if model == "H":
        while used(log, t) + cost > B:
            t += 1
    return t


def step(state, ev, policy, model, B, m):
    """Simulate one event from a canonical state (times relative to the end of the previous event = 0). Returns (new_state, info)."""
    log0, radio_free, off_until = state
    gap, fl_acks, fu_acks, kind = ev
    R = m * TC * C + M_COST
    reserved = policy == "reserved"
    log = list(log0)
    T0 = gap
    pend, s_ready = T0 + 3, T0 + 1
    inv1 = True
    for j in range(F_TRIES):
        cost = 1
        s = max(s_ready, radio_free)
        if reserved:
            t = max(s, off_until) if model == "T" else s
            if model == "T":
                if t + cost * (1 + OFF) > pend:
                    break
            elif t > pend or B - used(log, t) - cost < R:
                break
            s = t
        else:
            s = first_fit(log, s, cost, B, model, off_until)
        if reserved and model == "H" and B - (used(log, s) + cost) < R:
            inv1 = False
        log.append((s, cost, "L"))
        radio_free = s + cost + 1
        off_until = s + cost * (1 + OFF)
        if fl_acks[j]:
            break
    rem_at_pend = B - used(log, pend)
    first = None
    if kind == "confirm":
        for j in range(TC):
            s = first_fit(log, max(pend, radio_free), C, B, model, off_until)
            log.append((s, C, "H"))
            first = s if first is None else first
            radio_free = s + C + 1
            off_until = s + C * (1 + OFF)
            if fu_acks[j]:
                break
    else:
        for c in range(3):
            s = first_fit(log, max(pend + c, radio_free), 1, B, model, off_until)
            log.append((s, 1, "H"))
            first = s if first is None else first
            radio_free = s + 2
            off_until = s + 1 * (1 + OFF)
    end = max(radio_free, off_until) if model == "T" else radio_free
    new_log = tuple(sorted((s - end, c, cl) for (s, c, cl) in log if s > end - W - 1))
    info = dict(delay=first - pend, intact=(rem_at_pend >= R) if model == "H" else True, inv1=inv1)
    return (new_log, radio_free - end, off_until - end), info


def patterns(kind):
    fl = list(itertools.product((False, True), repeat=F_TRIES))
    fu = list(itertools.product((False, True), repeat=TC)) if kind == "confirm" else [tuple([False] * TC)]
    return [(a, b) for a in fl for b in fu]


def cell(args):
    B, m, model, policy = args
    dmax = DMAX_T if model == "T" else DMAX_H
    state0 = ((), 0, 0)
    layer = {state0: (1, [])}
    prior_evs_g = lambda n: [(g, a, b, "confirm") for g in (GAPS if n else (0,)) for (a, b) in patterns("confirm")]  # noqa: E731
    out = dict(B=B, m=m, model=model, policy=policy, by_n={}, example={}, states={})
    for n in range(NMAX + 1):
        runs = viol_unc = viol_cond = cond_runs = inv1_viol = 0
        for st, (mult, path) in layer.items():
            for kind in ("confirm", "cancel"):
                for g in (GAPS if n else (0,)):
                    for a, b in patterns(kind):
                        ev = (g, a, b, kind)
                        _ns, info = step(st, ev, policy, model, B, m)
                        runs += mult
                        if not info["inv1"]:
                            inv1_viol += mult
                        late = info["delay"] > dmax
                        if late:
                            viol_unc += mult
                            if n not in out["example"]:
                                out["example"][n] = [list(map(lambda x: x if not isinstance(x, tuple) else list(x), e)) for e in path + [ev]]
                        if info["intact"]:
                            cond_runs += mult
                            if late:
                                viol_cond += mult
        out["by_n"][n] = dict(runs=runs, inv2_unconditional=viol_unc, inv2_conditional=viol_cond, conditional_runs=cond_runs, inv1=inv1_viol)
        out["states"][n] = len(layer)
        if n == NMAX:
            break
        nxt: dict = {}
        for st, (mult, path) in layer.items():
            for (g, a, b, kd) in prior_evs_g(n):
                ev = (g if n else 0, a, b, kd)
                ns, info = step(st, ev, policy, model, B, m)
                if not info["inv1"]:
                    out["by_n"].setdefault("prefix_inv1", 0)
                    out["by_n"]["prefix_inv1"] += mult
                if ns in nxt:
                    nxt[ns] = (nxt[ns][0] + mult, nxt[ns][1])
                else:
                    nxt[ns] = (mult, path + [ev])
        layer = nxt
    return out


def main() -> None:
    jobs = []
    for B in BS:
        jobs.append((B, 0, "H", "old"))
        for m in MS:
            jobs.append((B, m, "H", "reserved"))
    for m in MS:
        jobs.append((0, m, "T", "reserved"))
    jobs.append((0, 0, "T", "old"))
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(cell, jobs, chunksize=1))
    (ROOT / "results" / "tables" / "r7b_formal.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r7b.formal.{name}", value=v, unit=unit, origin="FORMAL", source_file=SRC, notes=note))

    first_viol: dict = {}
    for r in res:
        key = f"{r['model']}.B{r['B']}.m{r['m']}.{r['policy']}" if r["model"] == "H" else f"T.m{r['m']}.{r['policy']}"
        pre = r["by_n"].get("prefix_inv1", 0)
        add(f"{key}.prefix_inv1_violations", pre, "count")
        for n in range(NMAX + 1):
            b = r["by_n"][n]
            add(f"{key}.n{n}.runs", b["runs"], "runs", "enumerated target events with n earlier confirm events, every gap and ACK pattern")
            add(f"{key}.n{n}.inv1_violations", b["inv1"], "count")
            add(f"{key}.n{n}.inv2_unconditional_violations", b["inv2_unconditional"], "count")
            add(f"{key}.n{n}.inv2_conditional_violations", b["inv2_conditional"], "count", "reserve intact at the instant the follow-up becomes pending")
            add(f"{key}.n{n}.distinct_states", r["states"][n], "states")
        viol_ns = [n for n in range(NMAX + 1) if r["by_n"][n]["inv2_unconditional"] > 0]
        first_viol[key] = viol_ns[0] if viol_ns else "none in bounds"
        add(f"{key}.first_unconditional_violation_n", first_viol[key], "earlier events")
    # summary flags
    res_m = lambda mm: [r for r in res if r["policy"] == "reserved" and r["m"] == mm and r["model"] == "H"]  # noqa: E731
    for mm in MS:
        rs = res_m(mm)
        add(f"summary.m{mm}.inv1_violations_total", sum(r["by_n"][n]["inv1"] for r in rs for n in range(NMAX + 1)) + sum(r["by_n"].get("prefix_inv1", 0) for r in rs), "count")
        add(f"summary.m{mm}.inv2_conditional_violations_total", sum(r["by_n"][n]["inv2_conditional"] for r in rs for n in range(NMAX + 1)), "count")
        add(f"summary.m{mm}.min_n_unconditional_violation", min([n for r in rs for n in range(NMAX + 1) if r["by_n"][n]["inv2_unconditional"] > 0] or [99]), "earlier events", "99 = none in bounds")
        add(f"summary.m{mm}.unconditional_violations_n_le_{mm - 1}", sum(r["by_n"][n]["inv2_unconditional"] for r in rs for n in range(mm)), "count", f"the m-event guarantee: no violation with at most {mm - 1} earlier events")
    old = [r for r in res if r["policy"] == "old" and r["model"] == "H"]
    add("summary.old.inv2_conditional_violations_total", sum(r["by_n"][n]["inv2_conditional"] for r in old for n in range(NMAX + 1)), "count", "control: the old policy violates Invariant 2")
    add("bounds.text", f"B in {BS}, W = {W}, m in {MS}, TC = {TC}, flash tries = {F_TRIES}, gaps {GAPS}, earlier events 0 to {NMAX}, model T once per m", "text")
    record_many(ent, purge_prefixes=("r7b.formal.",))
    print({e["name"]: e["value"] for e in ent if e["name"].startswith("r7b.formal.summary")})


if __name__ == "__main__":
    main()
