"""Round 5 documents: the literature query log (L1 to L5) and the rows L1 to L5 of the novelty matrix (idempotent: the rows sit between marker comments).

    python -m crashguard.r5_lit_docs

Reads ``results/tables/r5_lit_queries.json`` (from ``r5_lit``). The rows state what was read (abstract level for every item below) and the overlap level; no result of the round is used.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "results" / "tables" / "r5_lit_queries.json"
OUT = ROOT / "docs" / "06_references" / "LIT_QUERIES_ROUND5.md"
MATRIX = ROOT / "docs" / "06_references" / "NOVELTY_MATRIX_2021PLUS.md"
BEGIN, END = "<!-- r5:begin -->", "<!-- r5:end -->"
TOPIC_NAME = {21: "L1: mounting orientation, gravity and driving direction", 22: "L2: post-crash corroboration, confirmation stage", 23: "L3: wake-on-motion, pre-trigger buffer, sensor energy",
              24: "L4: spreading factor escalation under retransmission and deadlines", 25: "L5: cross-layer co-design of detection threshold and network delay"}
OPENED = [
    ("Gaitan et al., Metrologia 2021, doi 10.1088/1681-7575/abeccf", "OpenAlex record (abstract)", "Laboratory calibration of tri-axis accelerometers; mounting misalignment on the calibration instrument; not a vehicle mounting method"),
    ("Zhang et al., IEEE Trans. Instrum. Meas. 2026, doi 10.1109/tim.2026.3731729", "OpenAlex record (abstract)", "Gravity-aided transfer alignment for inertial navigation systems with a cubature Kalman filter; heading misalignment under low dynamics"),
    ("ResQ app, Utilitas Mathematica 2025 and ResQ framework, IJARSCT 2026 (doi 10.48175/ijarsct-31811)", "OpenAlex records (abstract)", "Smartphone accident detection with accelerometer, gyro and GPS; thresholds; a 30 s user confirmation timer; the abstracts state no mounting calibration and no post-event kinematic check"),
    ("Bhadane, IJRASET 2026, doi 10.22214/ijraset.2026.78311", "OpenAlex record (abstract)", "MPU6050 and ESP32 at 100 Hz; time-gated thresholds to reject potholes, turns and hard braking; post-impact voice logging; no post-event speed or stillness check in the abstract"),
    ("Alhosani et al., Accident Guardian, AHFE 2026, doi 10.54941/ahfe1007856", "OpenAlex record (abstract)", "Aftermarket collision detector with a driver verification step to cancel false alarms; manual, no kinematic corroboration"),
    ("Hallur and Gajendra, Discover Vehicles 2026, doi 10.1007/s44465-026-00047-8", "OpenAlex record (abstract)", "Functional safety framework for two-wheelers with sensor fusion, LSTM collision prediction and rider intervention"),
    ("Elsabathi and Tjisyah, J. Sist. Teknol. Inf. 2026", "OpenAlex record (abstract); targets stated, not measured results", "Fall detection with a threshold wake-up detector followed by a lightweight network; power target below 5 mA; no pre-trigger buffer in the abstract"),
    ("Casals Ibanez et al., The SF12 Well in LoRaWAN, Sensors 2021, doi 10.3390/s21196478", "OpenAlex record (abstract); MDPI full text not fetched by script", "After failed frame delivery devices raise the spreading factor; with link-layer reliability the network can collapse to SF12; end-device-based remedies by simulation"),
    ("Gorrela et al., IEEE Internet Things J. 2026, doi 10.1109/jiot.2026.3659938", "OpenAlex record (abstract)", "Adaptive data rate for mobile and dense LoRaWAN with a learning-based mechanism; packet loss and retransmission rates"),
    ("Khalifeh et al., Simul. Model. Pract. Theory 2026, doi 10.1016/j.simpat.2026.103277", "OpenAlex record has an empty abstract; title only, not used for any claim", "Joint channel and spreading factor selection"),
]
ROWS = """| L1 | Gravity-referenced automatic calibration of the sensor mounting (rotation into the vehicle frame from stillness and a straight braking or acceleration) before the impact-side rule | Gaitan et al., Metrologia 2021 (lab calibration); Zhang et al., IEEE TIM 2026 (gravity-aided alignment for inertial navigation); ResQ (2025, 2026) and Bhadane (2026), smartphone and MPU6050 crash detectors; all at abstract level | Calibrate sensors in the laboratory or align an inertial navigation system with a filter; the crash detectors use thresholds and state no mounting calibration in the abstract | A measured effect on the impact-side rule (round 5, V16 H-L1) with real crash pulses under synthetic rotations | Partial for the principle (gravity plus driving direction to find the vehicle frame is established in navigation and smartphone sensing); none found for a crash impact-side rule | "No journal article from 2021 onwards found in the sources checked (OpenAlex; IEEE Xplore, Scopus, Google Scholar and TRID not run) that applies a gravity and braking-direction calibration to an impact-side rule." The method itself is not claimed as new; only its measured effect on the side rule is reported | Baseline is the unchanged rule on raw axes; no uniqueness wording |
| L2 | Post-event state corroboration (speed drop, stillness, orientation change, rotation energy over a bounded window) that confirms or cancels an alert already sent | ResQ (2025, 2026; 30 s user timer); Accident Guardian (AHFE 2026; driver cancels); Bhadane (2026; time gates, voice log); Hallur and Gajendra (2026); abstract level | Confirmation by the user or by time gates on the sensor signal; none states a post-event kinematic check or a trained combination with the detector score in the abstract | A trained confirm rule on real events with a paired comparison at equal recall (V16 H-L2a, H-L2b) | Partial: confirmation after detection is common; the post-event kinematic state used as a trained feature was not found | "No journal article from 2021 onwards found in the sources checked (OpenAlex only) that trains a confirm or cancel rule on post-event speed, stillness and orientation features of a crash detector." Wording limited to the measured result | The R3 confirm stage is the baseline |
| L3 | Wake-on-motion with a pre-trigger sensor FIFO (accelerometer only in idle, gyro off, MCU asleep) | Elsabathi and Tjisyah (2026; threshold wake-up detector, power target, targets not measured results); Bhadane (2026; 100 Hz always on); abstract level | A threshold wake-up stage in front of a classifier is the usual design for fall detection; no pre-trigger buffer sized to the sensor FIFO in the abstracts | A replay of real crash events and an analytical energy estimate from opened datasheets (V16 H-L3) | Substantial for wake-up by threshold before classification (already the 2 g trigger of this design); none found for the FIFO-sized pre-trigger window on crash data | The always-on 100 Hz design is the baseline arm; no claim for the trigger idea. "No journal article from 2021 onwards found in the sources checked (OpenAlex only) that replays crash events with a FIFO-sized pre-trigger window." | Baseline arm A; claim limited to the measured recall and the analytical energy ratio |
| L4 | Deadline-optimal spreading-factor ladder: start from the link margin, send at once, step up after k failures, plan from the duty budget | Casals Ibanez et al., Sensors 2021 (SF12 Well); Gorrela et al., IEEE IoT-J 2026 (ADR for mobile and dense networks); Khalifeh et al., 2026 (empty abstract); abstract level | Raising the spreading factor after failures is the standard reaction of LoRaWAN end devices and is shown to be harmful under load; ADR variants adapt the rate for throughput and energy | A planned ladder with a deadline and a duty budget, run in two simulators against a zero-spacing control and the repository's `quick` policy | Substantial for escalation after failures (the repository already has `quick`); none found for a deadline-and-duty plan of the ladder | `quick` and the zero-spacing control are baselines. "No journal article from 2021 onwards found in the sources checked (OpenAlex only) that plans the spreading-factor ladder from a deadline and a duty budget for single alerts." SIMULATED only: supplement unless two link models hold | Baselines: Z0, `quick` |
| L5 | End-to-end choice of the detector thresholds from the detector score distribution and the network delay distribution, at a false-alarm budget | None close among the 2021+ results (query 25.1 returned security and unrelated items; queries 25.2 and 25.3 returned 0 hits) | - | A threshold choice by the 90th percentile of the time to awareness with three link models | None found | "No journal article from 2021 onwards found in the sources checked (OpenAlex only) that chooses a crash-detector threshold with the network delay distribution in the objective." Wording limited to the measured result | Baseline: the R3 rule at the same budget |
"""


def main() -> None:
    q = json.loads(Q.read_text(encoding="utf-8"))
    L = ["# Literature queries, round 5 (L1 to L5)", "", "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-15 |", "| Owner | Mritula S |",
         "| Scope | Round 5 query log for L1 to L5: OpenAlex queries for journal articles from 2021 and a context search without filters; counts, top titles and the items opened. |",
         "| Evidence labels used | NOT_RUN |",
         "| Abbreviations | ADR = adaptive data rate; DOI = digital object identifier; FIFO = sensor chip buffer (queue); GPS = Global Positioning System; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; LoRa = long-range radio modulation; MCU = microcontroller; MDPI = Multidisciplinary Digital Publishing Institute; SF = spreading factor (LoRa) |",
         "<!-- header:end -->", "",
         f"Run date {q[0]['date_run']}. Database: OpenAlex API (no key, no personal detail sent). Journal scope: `{q[0]['filters']}`; context scope: no filter (older and conference work). IEEE Xplore, Scopus, Google Scholar and TRID were not run. L6 to L10 are added in session 2.", ""]
    for t in sorted({r["topic"] for r in q}):
        L += [f"## Topic {t}. {TOPIC_NAME[t]}", "", "| Scope | Query | Count | Top titles (year, venue) |", "|---|---|---:|---|"]
        for r in [x for x in q if x["topic"] == t]:
            tops = "; ".join(f"{w['title'][:70]} ({w['year']}, {(w['journal'] or w['type'] or '')[:28]})" for w in r["top15"][:4]) or "none"
            L.append(f"| {r['scope']} | `{r['query']}` | {r['count']} | {tops} |")
        L.append("")
    L += ["## Items opened", "", "| Item | How it was read | What it does |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in OPENED]
    L += ["", "Absence wording used in the matrix: \"no journal article from 2021 onwards found in the sources checked\". The record of an item is read at abstract level only; no full text was read in this session.", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    s = MATRIX.read_text(encoding="utf-8")
    block = f"{BEGIN}\n{ROWS}{END}\n"
    if BEGIN in s:
        i, j = s.index(BEGIN), s.index(END) + len(END) + 1
        s = s[:i] + block + s[j:]
    else:
        key = "\n## Rows kept from the provisional C rows"
        head = ("\n## Round 5 rows (L1 to L5; L6 to L10 follow in session 2)\n\nPreregistration `PREREGISTRATION_V16.md`; queries in `LIT_QUERIES_ROUND5.md`; items opened as listed there. Written before the held-out run of each algorithm.\n\n"
                "| Key | Claim | Closest 2021+ journal articles opened | What they do | What this work adds | Overlap | Allowed wording | Action |\n|---|---|---|---|---|---|---|---|\n")
        s = s.replace(key, head + block + key, 1)
    MATRIX.write_text(s, encoding="utf-8")
    print("written", OUT.name, "and matrix rows")


if __name__ == "__main__":
    main()
