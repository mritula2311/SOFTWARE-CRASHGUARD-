"""R1 (H-R1a, H-R1b, H-R1c): reboot-resilient freshness (GTF) against a persisted counter.

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md section 4 (committed before this ran). GTF: a 32-bit freshness field equal to GPS UTC seconds; a car without a time source sends a
boot-epoch marker plus a counter. The base accepts a time-stamped alert if the field is inside the window W of its own clock and the triple (sender, field, sequence in second) is not in a ring of R entries
(RAM, cleared at reboot); a no-time alert is accepted if its triple is not in the ring and its counter is above the last counter held for that (sender, epoch).

Parts: (A) a bounded explicit-state check of the acceptance rule itself against two counter schemes (ANALYTICAL within the bounds); (B) a Monte Carlo over base clock drift, car time error, GPS loss and
burst load (SIMULATED); (C) the flash-write count (ANALYTICAL). Cited, not claimed over: ZigBee timestamp replay protection (not opened), LoRaWAN frame counters, a LoRaWAN replay-attack study (author doubtful).
Keys ``ar.r1.*``.

    python -m crashguard.ar_r1
"""
from __future__ import annotations

from collections import deque

import numpy as np
from scipy.stats import binom

from crashguard import config as C
from crashguard.results import record_many

SRC = "src/crashguard/ar_r1.py"
LATENCY_MAX_S = 2.5  # airtime plus up to three retries at 0.6 s spacing (one alert, SF7), an ASSUMPTION fixed in the design
REPLAY_SPAN = 6.0  # a replay is made at a uniform delay in [0, REPLAY_SPAN x W] after the original
Q_BASE_REBOOT = 12 * (REPLAY_SPAN * 10.0) / (365 * 86400.0)  # 12 base reboots per year over the replay interval of a 10 s window: a negligible 2e-5, kept as a parameter
DESIGN = dict(W=(5, 10, 30, 60), R=(64, 128, 256, 512), D=(1, 3), E=(1, 3), g=(0.1, 0.3), burst=(100, 200), runs=2000, seed=22000)
HELD = dict(D=(2, 5), E=(2, 4), g=(0.2, 0.4), burst=(150, 300), runs=2000, seed=24000)


# ---------------------------------------------------------------- (A) bounded model of the acceptance rule
def accept(scheme: str, base: dict, alert: tuple, now: int, W: int, R: int) -> tuple[bool, dict]:
    """The acceptance rule, one implementation for the model and the checks. ``base``: dict(ring tuple, last dict). Returns (accepted, new base)."""
    kind, field, seq, ctr = alert
    ring, last = base["ring"], dict(base["last"])
    if scheme == "gtf":
        if kind == "ts":
            if abs(field - now) > W or (field, seq) in ring:
                return False, base
            ring = (ring + ((field, seq),))[-R:]
            return True, dict(ring=ring, last=last)
        key = ("fb", field)  # field = boot epoch for a no-time alert
        if (field, seq, ctr) in ring or ctr <= last.get(key, -1):
            return False, base
        last[key] = ctr
        ring = (ring + ((field, seq, ctr),))[-R:]
        return True, dict(ring=ring, last=last)
    # counter schemes: field is unused, ctr is the counter
    if ctr <= last.get("ctr", 0):
        return False, base
    last["ctr"] = ctr
    return True, dict(ring=ring, last=last)


def model_check(scheme: str, T: int = 6, W: int = 2, R: int = 2, d: int = 0) -> dict:
    """Explicit-state exploration. Actions: tick, the car sends a fresh alert, the attacker captures any sent alert and replays any captured one at any later time, the base reboots, the car reboots
    (counter scheme: the counter restarts if the car does not persist it; GTF: the car loses its fix and uses the no-time form until a fix returns). Bounds: T ticks, at most 4 sends."""
    persist_base = scheme == "counter_persist_car_volatile"
    car_persist = scheme == "counter_nopersist_base"
    init = (0, dict(ring=(), last={}), dict(ctr=0, epoch=0, has_time=True, seq=-1, seq_t=-1), (), frozenset(), 0)
    seen = set()
    q = deque([(init, ())])
    viol = {"replay_outside_window": None, "replay_accepted": None, "fresh_rejected": None, "replay_accepted_ts": None}
    n = 0

    def key(s):
        t, b, c, sent, cap, nsent = s
        return (t, b["ring"], tuple(sorted(b["last"].items())), tuple(sorted(c.items())), sent, cap)

    while q:
        st, trace = q.popleft()
        k = key(st)
        if k in seen:
            continue
        seen.add(k)
        n += 1
        t, base, car, sent, cap, nsent = st
        now = t + d
        moves = []
        if t < T:
            moves.append(("tick", (t + 1, base, car, sent, cap, nsent)))
        if nsent < 4:
            c2 = dict(car)
            if scheme == "gtf":
                if c2["seq_t"] == t:
                    c2["seq"] += 1
                else:
                    c2["seq"], c2["seq_t"] = 0, t
                if c2["has_time"]:
                    al = ("ts", t, c2["seq"], 0)
                else:
                    c2["ctr"] += 1
                    al = ("fb", c2["epoch"], c2["seq"], c2["ctr"])
            else:
                c2["ctr"] += 1
                al = ("cnt", 0, 0, c2["ctr"])
            ok, nb = accept(scheme, base, al, now, W, R)
            nxt_base = nb if ok else base
            if not ok and viol["fresh_rejected"] is None and (scheme != "gtf" or abs(d) <= W):
                viol["fresh_rejected"] = trace + ("send_fresh",)
            moves.append(("send_fresh", (t, nxt_base, c2, sent + (al,), cap | {al}, nsent + 1)))
        for al in sorted(cap):
            ok, nb = accept(scheme, base, al, now, W, R)
            if ok:
                if viol["replay_accepted"] is None:
                    viol["replay_accepted"] = trace + (f"replay{al}",)
                if al[0] in ("ts", "cnt") and viol["replay_accepted_ts"] is None:
                    viol["replay_accepted_ts"] = trace + (f"replay{al}",)
                if al[0] == "ts" and abs(al[1] - now) > W and viol["replay_outside_window"] is None:
                    viol["replay_outside_window"] = trace + (f"replay{al}",)
            moves.append((f"replay{al}", (t, nb if ok else base, car, sent, cap, nsent)))
        # base reboot: RAM lost; the counter scheme keeps its last counter only if it persists it
        nb = dict(ring=(), last=dict(base["last"]) if persist_base else {})
        moves.append(("base_reboot", (t, nb, car, sent, cap, nsent)))
        # car reboot
        c3 = dict(car)
        if scheme == "gtf":
            c3.update(epoch=car["epoch"] + 1, ctr=0, has_time=False)
        elif not car_persist:
            c3["ctr"] = 0
        moves.append(("car_reboot", (t, base, c3, sent, cap, nsent)))
        if scheme == "gtf" and not car["has_time"]:
            c4 = dict(car, has_time=True)
            moves.append(("gps_fix", (t, base, c4, sent, cap, nsent)))
        for name, nx in moves:
            if key(nx) not in seen and len(trace) < 14:
                q.append((nx, trace + (name,)))
    return dict(states=n, **{k: v for k, v in viol.items()})


# ---------------------------------------------------------------- (B) Monte Carlo
def mc_cell(W: int, R: int, D: float, E: float, g: float, burst: int, runs: int, rng, q_reboot: float = Q_BASE_REBOOT) -> dict:
    """One cell: ``runs`` valid alerts after a car reboot and ``runs`` replay attempts. Availability: a time-stamped alert (probability 1 - g) is accepted if |e - latency - d_b| <= W, with the car
    time error e ~ U(-E, E), latency ~ U(0, 2.5 s), base clock error d_b ~ U(-D, D); a no-time alert (probability g) is accepted (its triple is new). Replay: of a time-stamped alert, at a delay a ~ U(0, 6 W);
    the base holds `burst` accepted triples per window W at a uniform rate, so the original is evicted from a ring of R entries once burst * a / W >= R; a base reboot in the interval clears the ring (probability q_reboot).
    Accepted if inside the window and (evicted or rebooted). Replays of no-time alerts are counted separately (accepted only after a base reboot or eviction, with no time bound)."""
    ts = rng.random(runs) >= g
    e = rng.uniform(-E, E, runs)
    lat = rng.uniform(0, LATENCY_MAX_S, runs)
    db = rng.uniform(-D, D, runs)
    ok = np.where(ts, np.abs(e - lat - db) <= W, True)
    avail = float(ok.mean())
    ts2 = rng.random(runs) >= g
    e2 = rng.uniform(-E, E, runs)
    db2 = rng.uniform(-D, D, runs)
    a = rng.uniform(0, REPLAY_SPAN * W, runs)
    inside = np.abs(e2 - a - db2) <= W
    evicted = burst * a / W >= R
    rebooted = rng.random(runs) < q_reboot
    acc_ts = ts2 & inside & (evicted | rebooted)
    acc_nt = (~ts2) & (evicted | rebooted)
    outside_acc = acc_ts & ~inside  # zero by construction: acceptance needs the window; kept as a check of the model code
    return dict(avail=avail, avail_hits=int(ok.sum()), n_ts_replays=int(ts2.sum()), replay_inside_accepted=int(acc_ts.sum()), replay_rate=float(acc_ts.mean()), replay_outside_accepted=int(outside_acc.sum()),
                notime_replay_accepted=int(acc_nt.sum()), n_notime=int((~ts2).sum()), n=runs)


def grid_cells(g: dict, W: int, R: int):
    for D in g["D"]:
        for E in g["E"]:
            for gl in g["g"]:
                for b in g["burst"]:
                    yield dict(D=D, E=E, g=gl, burst=b, W=W, R=R)


def main() -> None:
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"ar.r1.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    # (A) bounded model
    mres = {}
    for scheme in ("counter_nopersist_base", "counter_persist_car_volatile", "gtf"):
        r = model_check(scheme)
        mres[scheme] = r
        add(f"model.{scheme}.states", r["states"], "states", "reachable states, T = 6 ticks, W = 2, R = 2, base clock offset 0, at most 4 sends, traces up to 14 actions", "ANALYTICAL")
        for k in ("replay_accepted", "replay_accepted_ts", "replay_outside_window", "fresh_rejected"):
            add(f"model.{scheme}.{k}", int(r[k] is not None), "flag", {"replay_accepted": "a replay of an earlier alert is accepted (any kind)", "replay_accepted_ts": "a replay of a counter or time-stamped alert is accepted",
                "replay_outside_window": "a replay of a time-stamped alert is accepted outside the window W", "fresh_rejected": "a valid fresh alert is rejected"}[k] + " (1 = a counterexample exists)", "ANALYTICAL")
            if r[k] is not None:
                add(f"model.{scheme}.{k}.trace", " > ".join(r[k]), "text", "shortest trace found", "ANALYTICAL")
    # (B) design: smallest W and R meeting the criteria on the design grid
    rng = np.random.default_rng(DESIGN["seed"])
    chosenW = chosenR = None
    for W in DESIGN["W"]:
        res = [mc_cell(**{k: v for k, v in c.items() if k != "R"}, R=10**9, runs=DESIGN["runs"], rng=rng) for c in grid_cells(DESIGN, W, 10**9)]
        if min(r["avail"] for r in res) >= 0.99:
            chosenW = W
            break
    for R in DESIGN["R"]:
        res = [mc_cell(**{k: v for k, v in c.items() if k != "R"}, R=R, runs=DESIGN["runs"], rng=rng) for c in grid_cells(DESIGN, chosenW, R)]
        if max(r["replay_rate"] for r in res) <= 0.01 and max(r["replay_outside_accepted"] for r in res) == 0:
            chosenR = R
            break
    add("design.W_s", chosenW, "s", "smallest W of {5, 10, 30, 60} with availability >= 0.99 in every design cell")
    add("design.R_entries", chosenR, "entries", "smallest R of {64, 128, 256, 512} with replay acceptance inside W <= 1% in every design cell")
    # (B) held-out
    rng = np.random.default_rng(HELD["seed"])
    cells = []
    for c in grid_cells(HELD, chosenW, chosenR):
        r = mc_cell(**{k: v for k, v in c.items() if k != "R"}, R=chosenR, runs=HELD["runs"], rng=rng)
        p_a = float(binom.sf(r["avail_hits"] - 1, r["n"], 0.99))
        p_b = float(binom.cdf(r["replay_inside_accepted"], r["n_ts_replays"], 0.01))
        name = f"D{c['D']}_E{c['E']}_g{c['g']}_b{c['burst']}"
        cells.append(dict(name=name, p_a=p_a, p_b=p_b, **r, **c))
        for k in ("avail", "replay_rate", "replay_inside_accepted", "replay_outside_accepted", "notime_replay_accepted", "n_notime", "n_ts_replays"):
            add(f"held.{name}.{k}", round(r[k], 5) if isinstance(r[k], float) else r[k], "value", "held-out cell, 2,000 runs, seed 24000")
        add(f"held.{name}.p_a", round(p_a, 6), "p", "exact one-sided binomial P(X >= hits; n, 0.99)")
        add(f"held.{name}.p_b", round(p_b, 6), "p", "exact one-sided binomial P(X <= accepted replays; n time-stamped replays, 0.01)")
    p_a = max(c["p_a"] for c in cells)
    p_b = max(c["p_b"] for c in cells)
    a_ok = all(c["avail"] >= 0.99 for c in cells)
    b_ok = all(c["replay_rate"] <= 0.01 and c["replay_outside_accepted"] == 0 for c in cells)
    add("hR1a.criterion_met", int(a_ok), "flag", "availability >= 0.99 in every held-out cell")
    add("hR1a.p_raw", round(p_a, 6), "p", "largest over the 16 held-out cells")
    add("hR1a.min_availability", round(min(c["avail"] for c in cells), 5), "fraction", "smallest availability over the held-out cells")
    add("hR1b.criterion_met", int(b_ok), "flag", "replay acceptance inside W <= 1% and zero outside W in every held-out cell")
    add("hR1b.p_raw", round(p_b, 6), "p", "largest over the 16 held-out cells")
    add("hR1b.max_replay_rate", round(max(c["replay_rate"] for c in cells), 5), "fraction", "largest replay acceptance rate inside W over the held-out cells")
    add("hR1b.cells_over_1pct", ",".join(c["name"] for c in cells if c["replay_rate"] > 0.01) or "none", "cells", "held-out cells where the rate exceeds 1% (the ring is smaller than the burst per window)")
    # sensitivity: ring size 512, and drift of 2 s or less (kill criterion)
    rng = np.random.default_rng(HELD["seed"] + 1)
    s512 = [mc_cell(D=c["D"], E=c["E"], g=c["g"], burst=c["burst"], W=chosenW, R=512, runs=HELD["runs"], rng=rng) for c in grid_cells(HELD, chosenW, 512)]
    add("sensitivity.R512.max_replay_rate", round(max(r["replay_rate"] for r in s512), 5), "fraction", "not in the family: ring of 512 entries on the held-out grid")
    low = [mc_cell(D=2, E=e_, g=g_, burst=300, W=chosenW, R=chosenR, runs=HELD["runs"], rng=rng) for e_ in (1, 2) for g_ in (0.0, 0.4)]
    add("kill.availability_loss_drift_le_2s", round(1.0 - min(r["avail"] for r in low), 5), "fraction", "kill check: base clock drift of 2 s or less, car error 1 to 2 s; the kill fires above 0.05")
    # W sweep at the held-out extremes (the trade-off)
    rng = np.random.default_rng(HELD["seed"] + 2)
    for W in DESIGN["W"]:
        r = mc_cell(D=5, E=4, g=0.2, burst=150, W=W, R=10**9, runs=HELD["runs"], rng=rng)
        add(f"tradeoff.W{W}.availability_D5_E4", round(r["avail"], 5), "fraction", "availability at the extreme held-out drift (D = 5 s, E = 4 s)")
    # (C) flash writes
    A_, B_ = 100.0, 12.0
    add("hR1c.alerts_per_car_year", A_, "alerts", "ASSUMPTION fixed in the design: 100 alerts per car and year including false alarms", "ANALYTICAL")
    add("hR1c.boots_per_car_year", B_, "boots", "ASSUMPTION fixed in the design: 12 boots per car and year", "ANALYTICAL")
    ratio = 2 * A_ / B_
    add("hR1c.ratio", round(ratio, 2), "x", "writes of the persist-every-alert scheme (car and base) over writes of GTF (one boot-epoch write per boot)", "ANALYTICAL")
    for A2 in (10.0, 100.0, 876.0):
        for B2 in (12.0, 365.0):
            add(f"hR1c.sensitivity.A{int(A2)}_B{int(B2)}.ratio", round(2 * A2 / B2, 2), "x", "sensitivity table (not the criterion)", "ANALYTICAL")
    add("hR1c.criterion_met", int(ratio >= 10.0), "flag", "ratio at least 10", "ANALYTICAL")
    add("hR1c.p_raw", 0.0 if ratio >= 10.0 else 1.0, "p", "a formula: 0 if met, 1 if not", "ANALYTICAL")
    kill = (1.0 - min(r["avail"] for r in low)) > 0.05 or mres["gtf"]["replay_outside_window"] is not None
    add("kill.fired", int(kill), "flag", "availability loss above 5% at drift <= 2 s, or a time-stamped replay accepted outside W in the model")
    record_many(ent, purge_prefixes=("ar.r1.",))
    print("W", chosenW, "R", chosenR, "a_ok", a_ok, p_a, "b_ok", b_ok, p_b, "kill", kill)
    for k, v in mres.items():
        print(k, v["states"], {x: (None if y is None else len(y)) for x, y in v.items() if x != "states"})
    print([ (c["name"], round(c["avail"], 4), round(c["replay_rate"], 4)) for c in cells])
    print("max rate R512", max(r["replay_rate"] for r in s512), "W sweep done; seed", C.SEED)


if __name__ == "__main__":
    main()
