"""Documents of the combined run that live inside older files (blocks between markers, rewritten on every run; no text outside a block is touched):

    docs/03_results/NEGATIVES_REGISTER.md       <!-- v11:start --> ... <!-- v11:end -->   rows for the failed hypotheses of families S and R
    docs/00_overview/CLAIMS_FOR_COVER_LETTER.md <!-- v11:start --> ... <!-- v11:end -->   claims with label and verdict
    docs/06_references/NOVELTY.md               <!-- v11:start --> ... <!-- v11:end -->   software-checked status of N2, N5, N6, N7
    paper/generated/numbers_combined.tex                                                  macros read from results.json
    paper/main.tex                              % COMBINED:start ... % COMBINED:end       section text (architecture, protocol candidates, supplement)

Every number is read from results/results.json. Wording follows the evidence label: SIMULATED_HW_FORMAT means code run on simulated hardware-format logs; no sentence says hardware.

    python -m crashguard.ar_docs
"""
from __future__ import annotations

import json
import re
from pathlib import Path

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}


def g(k, nd=3):
    v = R[k]
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def verdict(k: str) -> str:
    pre = "sh" if k.startswith("hs") else "ar"
    return str(R[f"{pre}.holm.{k}.verdict"])


def block(path: Path, start: str, end: str, text: str, anchor_end: str | None = None) -> None:
    t = path.read_text(encoding="utf-8")
    new = f"{start}\n{text}\n{end}"
    if start in t and end in t:
        t = re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _m: new, t, flags=re.S)
    else:
        t = t.rstrip("\n") + "\n\n" + new + "\n"
    path.write_text(t, encoding="utf-8")


def negatives() -> str:
    rows = [
        ("H-S1 impact-side accuracy on simulated logs", "Whether the side rule keeps accuracy of 0.90 or more in every one of 16 simulated sensor sets.", f"NOT SUPPORTED: {R['sh.s2.hS1.n_variants_below_0.90']} of 16 sets below 0.90 (x flip {g('sh.s2.F_x.side_acc')}, y flip {g('sh.s2.F_y.side_acc')}, 10 Hz {g('sh.s2.S_10Hz.side_acc')}).",
         "An axis-sign flip swaps front and rear (or left and right); at 10 Hz a 12 to 45 ms pulse is mostly missed (inferred from the confusion table).", "None tried: the flips need a mounting calibration step in the firmware.", "Whether the real mounting needs a calibration at installation; real logs."),
        ("H-S2 trigger separates crash from non-crash (bench events)", "Whether the 2 g trigger gives recall of 0.90 and a false-alarm rate of 0.10 in every simulated set.", f"NOT SUPPORTED: false-alarm rate {g('sh.s2.V00_base.far')} in the base set; recall below 0.90 only at 10 Hz.",
         "Ramp bumps, rough driving and some hand taps exceed 2 g (the trigger alone is not a detector).", "The forest on bench windows (transfer test) rejects most bench pulses (recall 0.07 to 0.5): bench pulses are shorter than vehicle crashes.", "Real bench logs."),
        ("H-S3 UA-SCT against fixed-3 on simulated link logs", "Whether UA-SCT keeps critical reach within 10 s at or above fixed-3 minus 0.02 on the four edge runs.", f"NOT SUPPORTED after Holm: the point differences pass (largest {g('sh.s3.hS3.H3-edge-34db.diff_P4_minus_P0', 3)} at 34 dB) but the 34 dB interval is wide (p {g('sh.s3.hS3.p_raw', 2)}).",
         "UA-SCT spaces its rounds and is slower within 10 s than the severity table at 34 dB (inferred); gains at 38 and 42 dB rest on the simulator's spreading-factor assumption.", "None.", "Real link logs at the edge of range."),
        ("H-S6 SW-420 confirmation (simulated)", "Whether requiring 2 of 6 switches cuts the false-alarm rate by 0.02 and loses at most 0.02 of the recall.", f"NOT SUPPORTED: reduction {g('sh.s5.base_range_1.5_4.0.pooled.far_reduction')}, recall loss {g('sh.s5.base_range_1.5_4.0.pooled.recall_loss')}.",
         "Weak crashes shake few switches (inferred); the criterion flips with the assumed switch threshold range (0.8 to 2.0 g: met; 3.0 to 6.0 g: recall loss 0.27).", "None.", "A real SW-420 result needs the author's logs."),
        ("H-R1b reboot-resilient freshness: replay bound", "Whether GTF accepts at most 1% of replays inside the window at the held-out burst loads.", f"NOT SUPPORTED: replay rate up to {g('ar.r1.hR1b.max_replay_rate', 3)} in the burst-of-300 cells with the ring of {R['ar.r1.design.R_entries']} chosen on the design grid.",
         "The ring is smaller than the number of alerts per window (inferred; a ring of 512 entries gave rate 0.000).", "A ring of 512 entries on the held-out grid (sensitivity, not a verdict).", "The ring must be sized above the alerts per window of the largest cell; the firmware RAM cost."),
        ("H-R2a short frame with a 7 or 8-byte tag", "Whether a frame of at most 40 bytes raises burst delivery by 5 points in at least 8 of 16 held-out cells (sign test).", f"NOT SUPPORTED: the criterion is met ({R['ar.r2.hR2a.cells_gain5_of_16']} of 16 cells, mean gain {g('ar.r2.hR2a.mean_gain')}) but the sign test p is {g('ar.r2.hR2a.p_raw', 3)}.",
         "The test over 16 cells has little power (10 of 16 gives p 0.23); the cell-level intervals exclude zero in the 10 cells.", "An exploratory pooled paired interval over cells and hours is above zero; it is not a verdict.", "What a 24-byte frame carries; the dropped fields were not designed."),
    ]
    L = ["## Combined run (V11) negatives", "", "| Item | What was tested | Original verdict | Suspected cause | Fix tried and outcome | What remains open |", "|---|---|---|---|---|---|"]
    L += [f"| {' | '.join(r)} |" for r in rows]
    return "\n".join(L)


def claims() -> str:
    L = ["## Combined run (V11) claims", "", "Claims about simulated hardware-format logs carry the label SIMULATED_HW_FORMAT: code run on simulated logs generated from stated sensor and link models; no real hardware measurements are reported.", "",
         "| Claim | Evidence label | Section | Verdict |", "|---|---|---|---|",
         f"| In simulation, a 14-byte provisional alert from the early-exit rule reaches the base about {g('ar.r3.a1.earlier_median_s_p0', 1)} s before the full-window alert, with {100 * R['ar.r3.a1.retraction_share']:.0f}% of provisional alerts retracted and {100 * R['ar.r3.a1.air_ratio_p0']:.0f}% extra airtime. | SIMULATED | Two-stage alert | H-R3 {verdict('hr3')} |",
         f"| In a bounded model, one forged event-level ACK from a key holder stops every vehicle; with per-vehicle keys and an ACK bound to vehicle and counter, a compromised node stops only itself, at one extra key derivation per new vehicle id and no extra bytes. | ANALYTICAL (model, not firmware) | Per-vehicle ACK keys | H-R4 {verdict('hr4')} |",
         f"| A GPS-time freshness field with a 10 s window accepted at least {100 * R['ar.r1.hR1a.min_availability']:.1f}% of valid alerts after a car reboot in the simulation; persisting no counter cuts flash writes about {R['ar.r1.hR1c.ratio']:.0f} times at 100 alerts and 12 boots per car and year. | SIMULATED; ANALYTICAL | Freshness field | H-R1a {verdict('hr1a')}, H-R1c {verdict('hr1c')} |",
         f"| The replay bound inside the window needs a ring larger than the alerts per window: with the ring chosen on the design grid the rate reached {g('ar.r1.hR1b.max_replay_rate', 3)} at the held-out burst. | SIMULATED | Freshness field | H-R1b {verdict('hr1b')} |",
         f"| In simulated bursts a 24-byte frame delivered more critical alerts within 10 s than the 97-byte frame (mean gain {g('ar.r2.hR2a.mean_gain')}), and the 97-byte frame with an 8-byte tag is dominated in forgery effort, time on air and delivery; the preregistered sign test over 16 cells was not significant. | SIMULATED; ANALYTICAL | Frame and tag length | H-R2a {verdict('hr2a')}, H-R2b {verdict('hr2b')} |",
         f"| On simulated hardware-format logs the impact-side rule failed under an axis-sign flip and at 10 Hz sampling and held 0.90 under tilts up to 30 degrees, noise x4, bias sd 0.08 g, jitter and dropped samples; the 2 g trigger alone has a false-alarm rate of about {g('sh.s2.V00_base.far', 1)} on bench non-crash events. | SIMULATED_HW_FORMAT | Simulated hardware-format validation | H-S1 {verdict('hs1')}, H-S2 {verdict('hs2')} |",
         f"| In the model, the trigger-to-ACK latency is about {g('sh.s3.h7.supplied.median_first_try_ms', 0)} ms (250 ms window, 97-byte alert, 26-byte ACK, SF7), so a sub-500 ms statement fails for this configuration. | SIMULATED_HW_FORMAT | Latency decomposition | H-S4 {verdict('hs4')} |",
         f"| The repository's {R['sh.s4.suite.total']} security cases and the nine simulated scenarios behave as designed in software ({R['sh.s4.scenarios.attacks_accepted']} of {R['sh.s4.scenarios.attack_attempts_counted']} attack attempts accepted); the reference verifier persists its counter; the firmware was not tested. | SIMULATED_HW_FORMAT | Security on simulated scenarios | H-S5 {verdict('hs5')} |",
         f"| On simulated link logs, UA-SCT and fixed-3 differ by less than 0.012 in critical reach within 10 s at four edge runs, but the 34 dB interval is too wide to show a difference below 0.02. | SIMULATED_HW_FORMAT | Policies on link logs | H-S3 {verdict('hs3')} |",
         f"| In simulated bench events SW-420 confirmation removed {g('sh.s5.base_range_1.5_4.0.pooled.far_reduction', 2)} of the false alarms and cost {g('sh.s5.base_range_1.5_4.0.pooled.recall_loss', 2)} of the crash recall; the balance depends on the assumed switch sensitivity. | SIMULATED_HW_FORMAT | SW-420 confirmation | H-S6 {verdict('hs6')} |", ""]
    return "\n".join(L)


def novelty() -> str:
    return "\n".join([
        "## Combined run (V11): software-checked on simulated hardware-format data", "",
        "Statuses for hardware stay as above (NOT_YET). The column below says only what the simulated hardware-format logs (SIMULATED_HW_FORMAT) checked in software; it is never a hardware result.", "",
        "| Item | Hardware status | Software check on simulated hardware-format logs |", "|---|---|---|",
        f"| N2 impact side and angle from one IMU | NOT_YET | software-checked: the rule keeps 0.90 or more under tilts up to 30 degrees and fails under an axis-sign flip and at 10 Hz ({R['sh.s2.hS1.n_variants_below_0.90']} of 16 sets below 0.90; H-S1 {verdict('hs1')}) |",
        f"| N5 stage-by-stage latency against HTTP, MQTT and CoAP | NOT_YET | software-checked for the LoRa path only: trigger-to-ACK about {g('sh.s3.h7.supplied.median_first_try_ms', 0)} ms in the model (H-S4 {verdict('hs4')}); H5 edge timing stays NOT_RUN (placeholder timings) |",
        "| N6 open labelled scale-model dataset | NOT_YET | not checked: the simulated logs are not a dataset |",
        f"| N7 measured value of a cheap vibration-sensor array | NOT_YET | software-checked in simulation: false-alarm reduction {g('sh.s5.base_range_1.5_4.0.pooled.far_reduction', 2)}, recall loss {g('sh.s5.base_range_1.5_4.0.pooled.recall_loss', 2)}, and the sign of the gain depends on the assumed switch sensitivity (H-S6 {verdict('hs6')}) |", ""])


def tex_macros() -> str:
    m = {
        "CmbEarlier": g("ar.r3.a1.earlier_median_s_p0", 2), "CmbRetract": f"{100 * R['ar.r3.a1.retraction_share']:.0f}", "CmbAirExtra": f"{100 * R['ar.r3.a1.air_ratio_p0']:.0f}",
        "CmbRFourShared": g("ar.r4.held.v3.shared_key_event_ack.max_suppressed_fraction", 2), "CmbRFourPer": g("ar.r4.held.v3.per_vehicle_one_compromised.max_suppressed_fraction", 2),
        "CmbOneAvail": f"{100 * R['ar.r1.hR1a.min_availability']:.1f}", "CmbOneW": R["ar.r1.design.W_s"], "CmbOneR": R["ar.r1.design.R_entries"], "CmbOneRate": g("ar.r1.hR1b.max_replay_rate", 3),
        "CmbOneRatio": f"{R['ar.r1.hR1c.ratio']:.0f}", "CmbTwoGain": g("ar.r2.hR2a.mean_gain", 3), "CmbTwoCells": R["ar.r2.hR2a.cells_gain5_of_16"], "CmbTwoP": g("ar.r2.hR2a.p_raw", 2),
        "CmbSuite": R["sh.s4.suite.total"], "CmbLatency": g("sh.s3.h7.supplied.median_first_try_ms", 0), "CmbSideBelow": R["sh.s2.hS1.n_variants_below_0.90"],
        "CmbSwRed": g("sh.s5.base_range_1.5_4.0.pooled.far_reduction", 2), "CmbSwLoss": g("sh.s5.base_range_1.5_4.0.pooled.recall_loss", 2),
    }
    return "\n".join(r"\newcommand{\%s}{%s}" % (k, v) for k, v in m.items()) + "\n"


def tex_section() -> str:
    return r"""% COMBINED:start (generated by crashguard.ar_docs; numbers from generated/numbers_combined.tex)
\section{Architecture and protocol candidates}
The alert chain has seven layers (sensing, edge detector, severity, alert frame, freshness and authentication, retry policy, base and acknowledgement); each element is marked implemented, simulated or design-only in the architecture document. Four candidates were tested under a preregistered plan with a Holm correction over seven hypotheses; every result below is a simulation or a bounded model with stated assumptions, and none is measured on hardware.

\subsection{Two-stage alert}
A 14-byte flash from the early-exit rule is sent as a provisional alert, and the full-window decision sends the full alert or an authenticated cancel. On de-duplicated VZCrash test events the provisional alert reached the base about \CmbEarlier{} s before the single-stage alert, \CmbRetract{}\% of the provisional alerts were retracted, and the extra transmit airtime was \CmbAirExtra{}\%. Timing is the window length of the early-exit rule, not an ESP32 timing. The single-stage baseline waits for the full window; an early-exit alert without a cancel path would be as fast. No crash-alert version of this design was found in the sources checked (IEEE Xplore, OpenAlex; Scopus, Google Scholar and TRID not run).

\subsection{Per-vehicle acknowledgement keys}
In a bounded model of the alert protocol, one forged event-level acknowledgement from a holder of the shared key stops every vehicle (suppressed fraction \CmbRFourShared{}). With keys derived per vehicle and an acknowledgement bound to the vehicle and counter, a compromised node stops only itself (suppressed fraction \CmbRFourPer{} for three vehicles), at one key derivation per new vehicle id and no extra bytes. Per-device keys are standard in LoRaWAN; this is a design correction found by the check, and a holder of the master key is outside the claim.

\section{Supplement: further candidates and validation on simulated logs}
\textbf{Freshness field.} A GPS-time freshness field with a 10 s window accepted at least \CmbOneAvail{}\% of valid alerts after a car reboot in the simulation, and persisting no counter cuts flash writes about \CmbOneRatio{} times under stated rates. The replay bound inside the window needed a ring larger than the alerts per window: the ring of \CmbOneR{} entries chosen on the design grid let \CmbOneRate{} of replays through at the held-out burst. Timestamp replay protection exists for other networks and LoRaWAN uses frame counters; the contribution is the quantified trade-off in this setting.

\textbf{Frame and tag length.} A 24-byte frame delivered more critical alerts within 10 s than the 97-byte frame in simulated bursts (mean gain \CmbTwoGain{}; \CmbTwoCells{} of 16 cells gained at least five points), but the preregistered sign test over 16 cells gave $p=\CmbTwoP{}$, so the hypothesis is not supported. The shorter frame drops fields that were not designed.

\textbf{Simulated hardware-format logs.} The code was evaluated on simulated hardware-format logs generated from stated sensor and link models; no real hardware measurements are reported. The impact-side rule fell below 0.90 in \CmbSideBelow{} of 16 sets (axis-sign flips and 10 Hz sampling). In the model the trigger-to-acknowledgement latency is about \CmbLatency{} ms. The repository's \CmbSuite{} security cases behave as designed in software. SW-420 confirmation removed \CmbSwRed{} of the simulated false alarms and cost \CmbSwLoss{} of the crash recall, depending on the assumed switch sensitivity.
% COMBINED:end"""


def main() -> None:
    block(Path("docs/03_results/NEGATIVES_REGISTER.md"), "<!-- v11:start -->", "<!-- v11:end -->", negatives())
    block(Path("docs/06_references/NOVELTY.md"), "<!-- v11:start -->", "<!-- v11:end -->", novelty())
    block(Path("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md"), "<!-- v11:start -->", "<!-- v11:end -->", claims())
    Path("paper/generated/numbers_combined.tex").write_text(tex_macros(), encoding="utf-8")
    p = Path("paper/main.tex")
    t = p.read_text(encoding="utf-8")
    if r"\input{generated/numbers_combined.tex}" not in t:
        t = t.replace(r"\input{generated/numbers.tex}", "\\input{generated/numbers.tex}\n\\input{generated/numbers_combined.tex}", 1)
    sec = tex_section()
    if "% COMBINED:start" in t:
        t = re.sub(r"% COMBINED:start.*?% COMBINED:end", lambda _m: sec, t, flags=re.S)
    else:
        t = t.replace("\\section{Negative results}", sec + "\n\n\\section{Negative results}", 1)
    p.write_text(t, encoding="utf-8")
    print("written")


if __name__ == "__main__":
    main()
