"""D7.1: duty lockout after the provisional flash. ANALYTICAL condition under a per-transmission off-time model, the duty models the code enforces, and a check against the stored ns-3 runs.

    PYTHONPATH=src python scripts/vf2_duty.py

Writes docs/03_results/DELTA_DUTY_LOCKOUT.md and keys vf2.duty.* (ANALYTICAL for the formulas, SIMULATED for the diagnostic on stored ns-3 runs). Nothing is rerun.
Model of a per-transmission off-time (the stock formula of the ns-3 LoRaWAN module, ``LogicalLoraChannelHelper::AddEvent``: next allowed start = start + airtime / duty; the European rule T_off = T_on (1/duty - 1)):
after a frame that starts at s on a sub-band with duty fraction d and airtime A, the next frame on the same sub-band starts at s + A / d at the earliest.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard.lora import airtime_ms  # noqa: E402
from crashguard.results import record_many  # noqa: E402

SRC = "scripts/vf2_duty.py"
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
T_F = 1.808  # full-window decision: 1.8 s window plus 8 ms compute (xsim_alert.cc R3_FINAL_S; r3_t1.FINAL_S + COMPUTE3)
C = 0.008  # compute time before the flash is sent (R3_COMPUTE_S)
T_E = {"median": R["r6.r2.held.median_time_fixed_ms"] / 1000.0, "mean": R["r6.r2.held.mean_time_fixed_ms"] / 1000.0}  # decision time of the early-exit rule on held-out crash events with a provisional alarm
DUTIES = (0.01, 0.10)
SFS = (7, 8, 9, 10, 11, 12)
FRAMES = {"flash": 14, "micro_design": 7, "micro_ns3": 13, "alert": 97, "ack": 26}
ent: list[dict] = []


def A(n: int, sf: int) -> float:
    return airtime_ms(n, sf) / 1000.0


def add(name, v, unit, note="", origin="ANALYTICAL"):
    ent.append(dict(name=f"vf2.duty.{name}", value=(round(v, 6) if isinstance(v, float) else v), unit=unit, origin=origin, source_file=SRC, notes=note))


def lockout_start(s_f: float, a_f: float, d: float) -> float:
    return s_f + a_f / d


def attempts(deadline: float, a: float, a_ack: float, d: float) -> int:
    gap = max(a / d, a + 0.2 + a_ack)
    return int(math.floor((deadline - a) / gap)) + 1 if deadline >= a else 0


def diagnostic() -> dict:
    """Stored ns-3 runs of R3 (policy r3t) and R6-1 (r6m): how many two-stage events sent the confirm before the lockout of the flash would have ended."""
    from crashguard import pp_r3_ns3 as P
    from crashguard import r6_micro as M

    pend = json.loads((ROOT / "results" / "tables" / "r6_frozen.json").read_text(encoding="utf-8"))["r1"]["params"]["pend_s"]
    ev = M.event_table()
    out = {}
    for sf in (7, 9):
        a14, a97 = A(14, sf), A(97, sf)
        for pol, src, pe in (("r3t", P.OUT, None), ("r6m", M.OUT, pend)):
            n = inside = 0
            gaps = []
            for st in ("calib", "shipped"):
                for p in (0.0, 0.1, 0.3, 0.6):
                    for s in range(1, 61):
                        f = M.fname_new(src, sf, st, p, pol, s, pe)
                        if not M.usable(f):
                            continue
                        d = M.parse(f, ev)
                        d = d[(d.dropped == 0) & (d.E == 1) & (d.F == 1) & (d.flash >= 0) & (d.alert >= 0)]
                        # initial start of the confirm = arrival - airtime of the frame that arrived; for r6m the frame can be the 13-byte micro frame: its airtime gives the latest possible start (fewest events counted inside the lockout)
                        a_c = A(13, sf) if pol == "r6m" else a97
                        gap = (d.alert - a_c) - (d.flash - a14)  # confirm start minus flash start
                        n += len(d)
                        inside += int((gap < 100 * a14 - 1e-9).sum())
                        gaps.append(gap)
            g = pd.concat(gaps)
            out[(sf, pol)] = dict(n=n, inside=inside, share=inside / max(1, n), gap_min=float(g.min()), gap_median=float(g.median()), required=100 * a14)
    return out


def main() -> None:
    rows = []
    for sf in SFS:
        a = {k: A(n, sf) for k, n in FRAMES.items()}
        for k, v in a.items():
            add(f"air.sf{sf}.{k}_s", v, "s", f"time on air of {FRAMES[k]} bytes at SF{sf}")
        for k in ("flash", "micro_design", "alert"):
            add(f"lockout.sf{sf}.{k}_s", 99.0 * a[k], "s", f"99 x time on air: off-time after the end of a {FRAMES[k]}-byte frame at duty 1%")
        for who, te in T_E.items():
            s_f = te + C
            for d in DUTIES:
                L = lockout_start(s_f, a["flash"], d)
                add(f"earliest_confirm.sf{sf}.d{int(d * 100)}.{who}_s", L, "s", f"earliest start of the next frame on the same sub-band after a flash that starts at {s_f:.3f} s (decision time {who} {te:.3f} s + 8 ms): s_f + A14/d; the confirm is due at {T_F} s")
                add(f"delay.sf{sf}.d{int(d * 100)}.{who}_s", max(0.0, L - T_F), "s", "(L - T_F)+ : delay of the confirm caused by the flash lockout")
                add(f"cond_a.sf{sf}.d{int(d * 100)}.{who}", int(L <= T_F + 1e-12), "flag", "condition A: the lockout ends before the confirm is due (L <= T_F), the same as A14 <= d (T_F - s_f)")
                add(f"cond_c.sf{sf}.d{int(d * 100)}.{who}", int(L - T_F < a["alert"] - a["micro_design"] - 1e-12), "flag", "condition C (micro-confirm, 7 bytes): L - T_F < A97 - A7: the micro scheme reaches the base before the single-stage alert would")
        for d in DUTIES:
            add(f"attempts_alert_10s.sf{sf}.d{int(d * 100)}", attempts(10.0, a["alert"], a["ack"], d), "attempts", "attempts of the 97-byte alert before a 10 s deadline on one sub-band with per-transmission off-time: floor((D - A) / max(A/d, A + 0.2 s + A26)) + 1")
        rows.append((sf, a))
    for who, te in T_E.items():
        for d in DUTIES:
            add(f"critical_airtime.d{int(d * 100)}.{who}_s", d * (T_F - te - C), "s", "largest flash airtime for which condition A holds: d (T_F - s_f)")
            ok = [sf for sf in SFS if A(14, sf) <= d * (T_F - te - C)]
            add(f"max_sf_condition_a.d{int(d * 100)}.{who}", max(ok) if ok else 0, "SF", "largest spreading factor at which condition A holds for the 14-byte flash (0 = none up to SF12)")
    dg = diagnostic()
    for (sf, pol), v in dg.items():
        add(f"stored.sf{sf}.{pol}.events", v["n"], "events", "two-stage crash events with the flash and the confirm both delivered, in the 16 stored cells (60 seeds each)", "SIMULATED")
        add(f"stored.sf{sf}.{pol}.inside_lockout_share", v["share"], "fraction", "share whose confirm started less than 100 x A14 after the start of the flash (that is: inside the lockout of the per-transmission off-time model)", "SIMULATED")
        add(f"stored.sf{sf}.{pol}.gap_median_s", v["gap_median"], "s", "median of confirm start minus flash start", "SIMULATED")
        add(f"stored.sf{sf}.{pol}.gap_required_s", v["required"], "s", "100 x A14: the gap that the per-transmission off-time model requires", "SIMULATED")
    record_many(ent, purge_prefixes=("vf2.duty.",))
    G = {e["name"][len("vf2.duty.") :]: e["value"] for e in ent}

    def g(k):
        return G[k]

    L = ["# Duty lockout after the provisional flash (delta verification D7.1)", "", "<!-- header:start -->", "<!-- header:end -->", "",
         "Generated by `python scripts/vf2_duty.py` (keys `vf2.duty.*`). Labels: ANALYTICAL for the formulas, SIMULATED for the check against the stored ns-3 runs. Nothing was rerun. Time on air is `crashguard.lora.airtime_ms` (Semtech formula, 125 kHz, coding rate 4/5, explicit header, CRC, 8 preamble symbols).", "",
         "## 1. Which duty model each part of the code enforces", "",
         "| Part | Duty model enforced | Where | Channels or sub-bands |", "|---|---|---|---|",
         "| ns-3 application (`xsim_alert.cc`), policies p1, quick, d1, r3s, r3t, r3a, r6m and others | **hourly allowance**: the airtime of every uplink in any trailing 3,600 s must stay within `duty x 3600` s (36 s at 1%); the application waits (`WaitUntil`) before a send; the end-of-run line `DUTY` reports the largest trailing-hour use | `WaitUntil`, `Used`, `g_limit = duty x 3600` | the LoRaWAN module is configured with the ALOHA region: one sub-band (868.0 to 868.6 MHz) whose duty cycle is **1** and one logical channel (868.1 MHz). The stock formula next start = start + airtime / duty therefore adds no off-time (duty 1). RX2 downlinks outside the known sub-band are not duty-limited after the local patch (`XSIM_BUILD.md`) |",
         "| custom simulator (`world_sim.Window`) | hourly allowance (trailing window) | `Window.ok`, `wait_until` | one channel (same capture rule); no sub-band model |",
         "| trace replay (`r3_t1`, `r5_l4`) | hourly allowance of the device (`LIMIT_S = 0.01 x 3600`; counter `duty_exceeded`), no per-transmission off-time | `r3_t1.py` lines 38 and 115 | one link per device; no crowd |",
         "| 433 MHz | **no channel plan or sub-band list exists in the repository**; the 1% limit is an assumption and the Indian 433 MHz rule (G.S.R. 347(E), rule 3 row 1) allows a duty cycle of at most 10% with no channel plan (`FINALIZE_INDIA_RULES.md`) | none | not modelled: the rules give no channel plan, so the number of channels a node may use is not limited by them |", "",
         "**Consequence.** Every stored result of this study (R3, R6-1 and the others) was produced under an hourly allowance with no per-transmission off-time. The lockout trap does **not arise under the evaluated model**. It arises in regions that enforce an off-time after each frame on a shared sub-band (for example the European 1% sub-bands, where T_off = T_on x (1/duty - 1) = 99 x T_on at 1%).", "",
         "## 2. Exact numbers for a region with per-transmission off-time (not evaluated)", "",
         "Inputs: duty d = 1% (and 10% for comparison); the confirm is due at T_F = 1.808 s after the trigger (1.8 s window plus 8 ms); the flash starts at s_f = t_E + 8 ms, with t_E the decision time of the early-exit rule on the held-out crash events (median " + f"{T_E['median'] * 1000:.0f} ms, mean {T_E['mean'] * 1000:.1f} ms; keys `r6.r2.held.median_time_fixed_ms`, `mean_time_fixed_ms`). One sub-band shared by all frames of the node.", "",
         "| SF | A14 (ms) | 99 x A14 (s) | A7 (ms) | 99 x A7 (s) | A97 (ms) | 99 x A97 (s) | earliest confirm after the flash, median t_E (s) | delay beyond T_F (s) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for sf, a in rows[:3]:
        L.append(f"| {sf} | {a['flash'] * 1000:.2f} | {g(f'lockout.sf{sf}.flash_s'):.2f} | {a['micro_design'] * 1000:.2f} | {g(f'lockout.sf{sf}.micro_design_s'):.2f} | {a['alert'] * 1000:.2f} | {g(f'lockout.sf{sf}.alert_s'):.2f} | {g(f'earliest_confirm.sf{sf}.d1.median_s'):.2f} | {g(f'delay.sf{sf}.d1.median_s'):.2f} |")
    L += ["", "Rows are duty 1%. The 13-byte ns-3 micro frame has the airtime of the 14-byte flash at SF7 and SF9 (`FRAME_LAYOUT.md`), so its lockout equals the flash's. The same table at 10% (earliest confirm, median t_E): "
          + ", ".join(f"SF{sf} {g(f'earliest_confirm.sf{sf}.d10.median_s'):.2f} s" for sf in (7, 8, 9, 10)) + ".", "",
          "## 3. The condition (ANALYTICAL)", "",
          "**Terms.** d: duty fraction of the sub-band; A_f: time on air of the provisional frame; s_f: start time of the flash; T_F: time at which the confirm is due; A_c: time on air of the confirm frame (97 bytes, or the micro frame); L = s_f + A_f / d: the earliest start of any further frame on the sub-band after the flash (per-transmission off-time model above).", "",
          "**Proposition (a condition, not a theorem).** Under that model, with one sub-band for all frames, the confirm starts at max(T_F, L), so it reaches the base at max(T_F, L) + A_c when the initial attempt succeeds. Hence:",
          "1. *Severity content (A_c = 97 bytes).* The confirm is delayed by (L - T_F)+ against the single-stage alert, and the delay is zero **if and only if** L <= T_F, that is A_f <= d (T_F - s_f). With a 97-byte confirm the severity never arrives earlier than in the single-stage alert: the flash buys only the earlier notice that a crash happened (earlier by T_F + A_97 - s_f - A_f).",
          "2. *Micro-confirm (A_c = A_micro < A_97).* The micro scheme delivers the severity content earlier than the single-stage alert **if and only if** L - T_F < A_97 - A_micro.",
          "3. *Net reading of the flash.* The flash gains G = T_F + A_97 - s_f - A_f on the crash notice and costs D = (L - T_F)+ on the severity content. The lockout it causes (L - T_F) is shorter than the time it gains when L - T_F < G.", "",
          "*Derivation (every step).* (a) The model fixes the earliest next start on the sub-band as L (the stock ns-3 rule and the European off-time rule agree). (b) The confirm is ready at T_F and no frame may start before L, so its start is max(T_F, L): both bounds are necessary and together sufficient. (c) The arrival of the initial attempt is the start plus A_c. (d) The difference to the single-stage arrival T_F + A_97 is (L - T_F)+ + A_c - A_97, which gives 1 and 2 as equivalences (the inequalities are between the same quantities in both directions, with no other assumption). (e) Item 3 is the difference of two sums stated in the text. A retry of the flash restarts the lockout and only adds to L, so L is a lower bound when retries occur.", "",
          "**Numbers (computed, not copied).**", "", "| SF | d | A14 (s) | critical airtime d (T_F - s_f) (s) | condition A (median t_E) | condition A (mean t_E) | condition C (median t_E) | attempts of the 97-byte alert before 10 s |", "|---|---|---:|---:|---|---|---|---:|"]
    for sf, a in rows[:4]:
        for d in DUTIES:
            k = int(d * 100)
            L.append(f"| {sf} | {k}% | {a['flash']:.4f} | {g(f'critical_airtime.d{k}.median_s'):.4f} | {'holds' if g(f'cond_a.sf{sf}.d{k}.median') else 'fails'} | {'holds' if g(f'cond_a.sf{sf}.d{k}.mean') else 'fails'} | {'holds' if g(f'cond_c.sf{sf}.d{k}.median') else 'fails'} | {g(f'attempts_alert_10s.sf{sf}.d{k}')} |")
    L += ["", f"At 1% the critical airtime is {g('critical_airtime.d1.median_s') * 1000:.1f} ms for the median decision time: no frame of 7 bytes or more fits at any spreading factor (A7 at SF7 is {A(7, 7) * 1000:.1f} ms), so with one sub-band and 1% a flash always delays the confirm. At 10% the condition holds for the 14-byte flash up to SF{g('max_sf_condition_a.d10.median')} (median decision time) and up to SF{g('max_sf_condition_a.d10.mean')} (mean decision time).", "",
          "**With more than one sub-band.** If the confirm is sent on a different sub-band from the flash, L does not apply to it and the delay is zero. The number of sub-bands a node may use at 433 MHz is not known from the repository (section 1), so no claim is made for that case; a node that is allowed two sub-bands should send the flash on one and the confirm on the other.", "",
          "## 4. Check against the stored ns-3 results", "",
          "| SF | Policy | Two-stage events with flash and confirm delivered | Share whose confirm started inside the lockout | Median gap (confirm start - flash start) (s) | Gap required by the off-time model (100 x A14) (s) |", "|---|---|---:|---:|---:|---:|"]
    for (sf, pol), v in dg.items():
        L.append(f"| {sf} | {pol} | {v['n']:,} | {v['share']:.4f} | {v['gap_median']:.3f} | {v['required']:.3f} |")
    L += ["", "**Reading.** The stored results are consistent with the proposition in its no-lockout branch, and only there: they were produced with a sub-band duty of 1 (ALOHA region of the module) and an hourly allowance, so the confirm starts at its due time T_F whatever the flash did, and every one of the events above would have been delayed under a per-transmission off-time at 1%. This is the reason, and nothing was rerun to make the two agree. The stored two-stage delivery and extra-airtime numbers therefore **do not transfer** to a region that enforces an off-time on one shared sub-band.", "",
          "## 5. One link-aware gating rule (merged with the spreading-factor rule of R6-7)", "",
          "Enable the two-stage alert (flash, then confirm) at a spreading factor only if **both** hold:",
          "1. *Load gate (R6-7, ROUND6_BOUNDS.md section 2):* the lower bound of the extra airtime times the retry and collision inflation measured in ns-3 stays within the 40% limit. Evaluated: SF7 passes, SF9 fails; SF8 and SF10 to SF12 were not run.",
          "2. *Lockout gate (this section), only in a region that enforces a per-transmission off-time on the sub-band that carries both frames:* condition A holds (A_f <= d (T_F - s_f)), or the confirm is sent on another sub-band. Under an hourly allowance only, this gate is open at every spreading factor.", "",
          "Rule: send two-stage alerts up to the highest spreading factor at which both gates are open, and the single-stage full decision above it. Under the evaluated model (hourly allowance) the rule gives SF7; under a 1% per-transmission off-time on one sub-band it gives no spreading factor (single-stage everywhere); under 10% it gives SF" + f"{min(7, g('max_sf_condition_a.d10.median'))}" + " by the load gate alone. This is a design rule derived from the analysis and checked against two simulated cells and the stored runs above; it is not a tested hypothesis.", ""]
    (ROOT / "docs" / "03_results" / "DELTA_DUTY_LOCKOUT.md").write_text("\n".join(L), encoding="utf-8")
    print({k: v for k, v in G.items() if k.startswith(("max_sf", "critical", "stored"))})


if __name__ == "__main__":
    main()
