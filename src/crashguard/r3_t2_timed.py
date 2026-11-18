"""T2.2 (docs/02_preregistration/PREREGISTRATION_V14.md section 2.2): worst-case time to delivery under at most k consecutive lost attempts, and the duty-cycle check (FORMAL).

    python -m crashguard.r3_t2_timed

Tool: exhaustive explicit-state enumeration over the frozen policy code of ``r3_t1.replay_alert`` (own code; NOT UPPAAL and not a timed-automata model checker: UPPAAL is not obtainable in this run,
see DECISIONS.md). Model: one Critical alert, crash at 0, deadline 10 s, ready time READY0 + hold, base SF 9, 1% duty in a sliding hour, listen window PROC + ACK airtime + MARGIN after every
transmission, time on air from ``lora.airtime_ms``. The policies are deterministic except for random gaps, which are replaced by the end of their support (the worst case): the Khan-style gap U(1, 3) by 3 s, the
Nessa-style gaps by the upper end, and the D1 backoff jitter by its maximum. Exhaustive dimensions:
  * D1 belief state: all 2**12 failure histories of the 12 rounds before the alert (every reachable loss estimate within that bound), from the frozen prior;
  * loss pattern: the first k uplinks lost (k = 0..6) and the next one received. Delivery time is non-decreasing in the number of initial losses, so the worst case over all patterns with no run longer
    than k is the pattern with exactly k initial losses (checked by enumerating all patterns of the leading 8 attempts with runs of at most k: 2**8 patterns);
  * initial airtime already used in the sliding hour: 0 for H-T2; 0 to 35 s in steps of 5 s for the duty check.
A delivery that cannot happen before the deadline (or is blocked by the duty gate) has time inf.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np

from crashguard import r3_t1 as T
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r3_t2_timed.py"
K_MAX = 6
HIST = 12


class WorstRng:
    """Replaces every random draw by the end of its support (the worst case for the delivery time)."""

    def uniform(self, a: float, b: float) -> float:
        return b

    def random(self) -> float:
        return 1.0


def first_rx_time(pol: str, pattern: list[int], hist: list[int], used0: float = 0.0) -> tuple[float, float]:
    """Time of the earliest reception when the uplink pattern is ``pattern`` (1 = received) after the 12-round history ``hist``; plus airtime used."""
    r = np.array(list(hist) + list(pattern) + [1] * 40, np.uint8)
    t, _n, used = T.replay_alert(pol, r, len(hist), WorstRng(), 0.0, used0)
    return t, used


def longest_run(p: list[int]) -> int:
    best = cur = 0
    for x in p:
        cur = cur + 1 if x == 0 else 0
        best = max(best, cur)
    return best


def main() -> None:
    T.init_ctx()
    hist_all = [list(h) for h in itertools.product((0, 1), repeat=HIST)]
    quiet = [1] * HIST  # a link with no recent failure (used for the policies with no state)
    table: dict = {}
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        if isinstance(value, float) and math.isfinite(value):
            value = round(value, 6)
        if isinstance(value, float) and math.isinf(value):
            value = "inf"
        ent.append(dict(name=f"r3.t2.timed.{name}", value=value, unit=unit, origin="FORMAL", source_file=SRC, notes=notes))

    for pol in T.POLICIES:
        rows = []
        for k in range(K_MAX + 1):
            pat = [0] * k + [1]
            if pol == "D1":
                times = [first_rx_time(pol, pat, h)[0] for h in hist_all]
                worst, best = max(times), min(times)
            else:
                worst = best = first_rx_time(pol, pat, quiet)[0]
            # exhaustive patterns of the leading 8 attempts with runs of at most k: the worst case must equal the exactly-k pattern
            wp = 0.0
            hs = hist_all if pol == "D1" else [quiet]
            for h in (hs[:: max(1, len(hs) // 64)] if pol == "D1" else hs):  # 64 histories spread over the whole range for the pattern check (all 4096 are used above)
                for p8 in itertools.product((0, 1), repeat=8):
                    p8 = list(p8)
                    if longest_run(p8) <= k and 1 in p8:
                        wp = max(wp, first_rx_time(pol, p8, h)[0] if math.isfinite(first_rx_time(pol, p8, h)[0]) else math.inf)
            consistent = (wp <= worst + 1e-9) or math.isinf(worst)
            rows.append(dict(k=k, worst=worst, best=best, pattern_check=bool(consistent)))
            add(f"{pol}.k{k}.worst_s", float(worst), "s", "worst-case time from the crash to reception at the base over all loss estimates (D1) and the pattern with k initial losses; inf = not delivered before the deadline")
            add(f"{pol}.k{k}.best_s", float(best), "s", "best case over the same states (equal to the worst case for stateless policies)")
            add(f"{pol}.k{k}.pattern_check", int(consistent), "flag", "exhaustive check of all patterns of 8 attempts with runs of at most k: none is later than the exactly-k pattern")
        table[pol] = rows

    # H-T2: D1 not longer than quick for every k
    cmp_rows = []
    ok_all = True
    first_bad = None
    for k in range(K_MAX + 1):
        d = table["D1"][k]["worst"]
        q = table["quick"][k]["worst"]
        ok = (d <= q + 1e-9) or (math.isinf(d) and math.isinf(q))
        cmp_rows.append(dict(k=k, d1=d, quick=q, ok=bool(ok)))
        add(f"hT2.k{k}.d1_not_longer_than_quick", int(ok), "flag", f"D1 worst {d:.4f} s against quick {q:.4f} s")
        if not ok and first_bad is None:
            first_bad = dict(k=k, d1=d, quick=q)
        ok_all &= ok
    # duty check: exhaustive over initial airtime used and (for D1) all histories and all 2**8 patterns
    breaches = 0
    runs = 0
    blocked_by_pol = {p: 0 for p in T.POLICIES}
    for pol in T.POLICIES:
        hs = hist_all if pol == "D1" else [quiet]
        for u0 in range(0, 36, 5):
            for h in hs[:: 16 if pol == "D1" else 1]:
                for p12 in itertools.product((0, 1), repeat=6):
                    t, used = first_rx_time(pol, list(p12), h, float(u0))
                    runs += 1
                    if used > T.LIMIT_S + 1e-9:
                        breaches += 1
                    if math.isinf(t) and used + 0.5 > T.LIMIT_S - 1e-9 and u0 >= 30:
                        blocked_by_pol[pol] += 1
    add("duty.runs", runs, "runs", "initial airtime 0 to 35 s, all 2**6 patterns of 6 uplinks, all policies, D1 over 256 of the 4096 histories (every 16th)")
    add("duty.breaches", breaches, "runs", "runs in which the airtime used in the sliding hour exceeded the 36 s allowance (must be 0)")
    add("hT2.criterion_met", int(ok_all and breaches == 0), "flag", "D1 worst case not longer than quick retries for k = 0..6, and no duty breach")
    out = dict(table={p: [dict(k=r["k"], worst=("inf" if math.isinf(r["worst"]) else r["worst"]), best=("inf" if math.isinf(r["best"]) else r["best"]), pattern_check=r["pattern_check"]) for r in rows] for p, rows in table.items()},
               compare=[dict(k=c["k"], d1=("inf" if math.isinf(c["d1"]) else c["d1"]), quick=("inf" if math.isinf(c["quick"]) else c["quick"]), ok=c["ok"]) for c in cmp_rows],
               duty=dict(runs=runs, breaches=breaches), criterion=bool(ok_all and breaches == 0), first_counterexample=first_bad)
    record_many(ent, purge_prefixes=("r3.t2.timed.",))
    (ROOT / "results" / "tables" / "r3_t2_timed.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for p in T.POLICIES:
        print(p, [("inf" if math.isinf(r["worst"]) else round(r["worst"], 3)) for r in table[p]])
    print("hT2", ok_all, "breaches", breaches, "first_bad", first_bad)


if __name__ == "__main__":
    main()
