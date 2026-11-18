"""V4: build docs/04_audits/HYPOTHESIS_LEDGER.md and the vf.ledger.* keys in results.json.

One row per preregistered hypothesis (a test cell such as an SF setting is part of its row).
The rows are written from the decision tables and result files named in the `src` column; the Holm p-values and
verdicts are checked against results.json keys by `check_against_results` (any mismatch stops the script).
"""
from __future__ import annotations

# ruff: noqa: E402  (the guard below runs before the imports on purpose)
raise SystemExit('vf_ledger.py is a one-time script that was already applied in the verification run. Running it again would rewrite the hypothesis ledger with the counts of that run (130 in 13 versions) and rewrite keys in results/results.json. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard


import collections
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

S, NS, M, NR = "SUPPORTED", "NOT SUPPORTED", "PARTLY", "NOT_RUN"

# round, file, name of the family and its size (0 = no Holm family), role of the data
ROUNDS = {
    "V1": ("PREREGISTRATION.md", "UA-SCT severity triage", "H-a to H-c, Holm over 3", "real NHTSA and VZCrash records; grouped bootstrap; no separate held-out split named in the file"),
    "V2": ("PREREGISTRATION_V2.md", "studies A to F", "Holm over 9 with a p-value (A1, A2, A3, B1, B2, D1, D2, E1, F2); B3, E2, F1 by formula or rule", "VZCrash test split (held-out) and simulated grids"),
    "V3": ("PREREGISTRATION_V3.md", "X1 to X8", "Holm over 7 (X1, X2, X3, X5, X6, X7, X8); X4 is a statement about files", "held-out VZCrash test split; T13a held-out harvested records"),
    "V4": ("PREREGISTRATION_V4.md", "P1 to P4", "Holm over 7", "sealed fold (P1 to P3) and test split (P4)"),
    "V5": ("PREREGISTRATION_V5.md", "blocks B, C, F, G", "Holm over 18; NOT_RUN enters with p = 1", "sealed fold, nested cross-validation, simulated grids"),
    "V7": ("PREREGISTRATION_V7.md", "release: reruns Q1 to Q3 and protocol block A", "Holm over 20; NOT_RUN enters with p = 1", "real-only reruns on the original splits; held-out grid of 32 cells"),
    "V11": ("PREREGISTRATION_V11.md", "simulated hardware-format validation (S) and protocol candidates (R)", "two Holm families: S (6) and R (7)", "simulated hardware-format logs; held-out grid of 16 cells"),
    "V12": ("PREREGISTRATION_V12.md", "redesign D1 to D4", "Holm over 10; NOT_RUN enters with p = 1", "design grid, then fresh grids (FRESH-A, FRESH-B), ns-3 cross-check on S-X"),
    "V13": ("PREREGISTRATION_V13.md", "paper items P0 (H-C3 refit) and P1 (two-stage alert in ns-3)", "H-C3 in the 18 of V5 (recomputed); P1 family of 8 (P1a and P1c in 4 cells)", "development fold (P0); ns-3 runs (P1)"),
    "V14": ("PREREGISTRATION_V14.md", "round 3, T1 to T4", "Holm over 7 (T1a x3, T1b, T1c, T3a, T3b); T2, T2sec, T3c decided by rule", "London trace dev/held-out groups (LoED), de-duplicated VZCrash test split, formal models"),
    "V15": ("PREREGISTRATION_V15.md", "round 4, A1 to A3", "Holm over 5", "development on LoED; fresh sniffer links (Zenodo 7919213) for A1b; EXPLORATORY for A2"),
    "V16": ("PREREGISTRATION_V16.md", "round 5, L1 to L11", "Holm over 13 (L1 to L8b, L10a, L10b); L11 own family", "development then freeze then held-out once: VZCrash halves, NHTSA, FARS 2022, UCI HAR, SisFall, simulated hardware-format logs"),
    "V17": ("PREREGISTRATION_V17.md", "round 6, R6-1 to R6-3", "Holm over 7 (H-R6-1a, 1b, 1c, 2a, 2b, 3a, 3b); formal rows p = 1e-300 if proved", "ns-3 seeds 1 to 60 (held-out for this question), LoED half 0 for traces, VZCrash test half 1 (hash r6), bounded models"),
}

# (round, id, short statement, result, verdict, holm p (text), label, placement, note)
ROWS = [
    ("V1", "H-a", "P3 mis-triage lower than P1 at +-16 g", "interval -0.085 to -0.015", S, "0.004", "MEASURED_SOFTWARE", "not in the combined paper", ""),
    ("V1", "H-b", "P3 costs more escalations of non-severe events; P4 bounds fast-path airtime", "interval 0.370 to 0.658", S, "< 0.001", "MEASURED_SOFTWARE", "not in the combined paper", ""),
    ("V1", "H-c", "gain shrinks at +-64 g", "reduction lower limit 0.0005", S, "0.018", "MEASURED_SOFTWARE", "not in the combined paper", ""),
    ("V2", "H-A1", "difficulty-aware severity interval narrows p90 error", "p90 reduction 16.1 points", S, "0.009", "MEASURED_SOFTWARE", "supplement", ""),
    ("V2", "H-A2", "narrowing in the lowest tercile", "no narrowing", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V2", "H-A3", "containment of reference delta-V at least 0.90", "below 0.90", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V2", "H-B1", "burst variant gains 3 points in 6 of 10 cells", "no variant", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V2", "H-B2", "burst variant harms by at most 2 points", "harm bound above 2 points for some cell", M, "1.000", "SIMULATED", "negatives", "labelled MIXED in the source"),
    ("V2", "H-B3", "ratio of gains", "not evaluable because H-B1 failed", NS, "no p (rule)", "SIMULATED", "negatives", ""),
    ("V2", "H-D1", "early flag saves at least 100 ms", "median 86 ms", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V2", "H-D2", "second early-flag criterion", "criterion met, Holm p 0.385", M, "0.385", "MEASURED_SOFTWARE", "negatives", "labelled MIXED in the source"),
    ("V2", "H-E1", "gain of at least 2 points", "gain below 2 points", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V2", "H-E2", "work factors above 2^32", "both above", S, "no p (formula)", "ANALYTICAL", "supplement", ""),
    ("V2", "H-F1", "positive optimal Critical hold", "2 combinations positive", NS, "no p (formula)", "ANALYTICAL", "negatives", ""),
    ("V2", "H-F2", "reduction with the two-stage scheme", "reduction 32%", S, "0.009", "SIMULATED", "supplement", ""),
    ("V3", "H-X1", "16-bit fixed-point forest, AP loss at most 0.005 and 30% flash cut", "flash clause not met", NS, "0.007", "MEASURED_SOFTWARE", "negatives", ""),
    ("V3", "H-X2", "cheap-trigger cascade, +2 points of crashes passing", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V3", "H-X3", "group-aware training +1 point recall at the 1% target", "+0.001", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V3", "H-X5", "+-16 g fill + ridge preserves delta-V rank", "Spearman 0.75", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V3", "H-X6", "lower-bound-anchored estimator lowers p90 delta-V error by 5 points", "p90 gain 31 points", S, "0.007", "MEASURED_SOFTWARE", "main (C3 clipping restoration is a different, later method) and supplement", ""),
    ("V3", "H-X7", "two-part pair reaches 0.80 within +-10%", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V3", "H-X8", "sequential rule 100 ms earlier", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V4", "H-P1", "direct severity classifier beats the anchored estimator", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "raw p 0.836"),
    ("V4", "H-P2", "anchored interval", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V4", "H-P3a", "abstention at 70% retention", "not met", NS, "0.780", "MEASURED_SOFTWARE", "negatives", "raw p 0.130"),
    ("V4", "H-P3b", "abstain routing", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V4", "H-P4a", "compact forest", "criterion met", S, "0.007", "MEASURED_SOFTWARE", "main (detector, 15-tree forest)", ""),
    ("V4", "H-P4b", "augmentation at the 1% false-alarm target", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V4", "H-P4c", "calibration over the trivial rule", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V5", "H-B2", "P1+ against P0 (flash and hold on the severity table)", "not met", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V5", "H-C3", "synthetic requirement matches the real one within one range step", "frontal barrier only; pole and side fail the generator gate", S, "0.018", "SIMULATED", "main (range requirement) with the refit of V13", "re-tested in V13 on the development fold"),
    ("V5", "H-F1", "direct classifier against anchored estimator (EXPLORATORY-REVISED)", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "rerun of H-P1 after its result"),
    ("V5", "H-F1b", "anchored interval (EXPLORATORY-REVISED)", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "rerun of H-P2"),
    ("V5", "H-F1c", "abstention at 70% retention (EXPLORATORY-REVISED)", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "rerun of H-P3a"),
    ("V5", "H-F1d", "H-X6 on splits G and O", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V5", "H-F1e", "H-X5 rank preservation", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V5", "H-F2a", "augmentation at the 1% target (EXPLORATORY-REVISED)", "not met", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "rerun of H-P4b"),
    ("V5", "H-F2b", "group-aware training (EXPLORATORY-REVISED)", "+0.001", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "rerun of H-X3"),
    ("V5", "H-F2c", "trigger cascade (EXPLORATORY-REVISED)", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V5", "H-F2d", "fixed-point forest, AP and flash (EXPLORATORY-REVISED)", "flash clause not met", NS, "0.018", "MEASURED_SOFTWARE", "negatives", "rerun of H-X1"),
    ("V5", "H-F2e", "sequential rule (EXPLORATORY-REVISED)", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V5", "H-F2f", "calibration over the trivial rule (EXPLORATORY-REVISED)", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V5", "H-F3a", "P3 against the lowered table at equal escalation", "not met", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V5", "H-F3b", "abstain routing against the lowered table", "not met", NS, "1.000", "SIMULATED", "negatives", "raw p 0.930"),
    ("V5", "H-G3a", "slotted fast path against pure ALOHA", "not met", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V5", "H-G3b", "listen-before-talk against duty-cycle-only access", "not met", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V5", "H-G3c", "V2V relay against no relay", "not met", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V7", "H-Q1a", "H-P1 rerun on real-only data", "same verdict as the original", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q1b", "H-P2 rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q1c", "H-P3a rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q1d", "H-X5 rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q1e", "H-X6 rerun", "same", S, "0.020", "MEASURED_SOFTWARE", "supplement", ""),
    ("V7", "H-Q1f", "H-X7 rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q2a", "H-P4a rerun", "same", S, "0.020", "MEASURED_SOFTWARE", "main (detector)", ""),
    ("V7", "H-Q2b", "H-P4b rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q2c", "H-P4c rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q2d", "H-X1 rerun", "p 0.02 but criterion not met", NS, "0.020", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q2e", "H-X2 rerun", "not run in advance (surrogate windows)", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V7", "H-Q2f", "H-X3 rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q2g", "H-X8 rerun", "same", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V7", "H-Q2h", "early-exit rule with surrogate-trained forests", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V7", "H-Q3a", "N28 equal-escalation comparison", "not run in the rerun", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V7", "H-Q3b", "H-B2 rerun", "not run in the rerun", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V7", "H-Q3c", "P3b abstain routing rerun", "not run in the rerun", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V7", "H-A1", "OS-DR protocol: 5-point gain in at least 20 of 32 cells", "7 cells; 8 cells lost by more than 2 points", NS, "1.000", "SIMULATED", "negatives", "block A of the release"),
    ("V7", "H-A2", "GS-CA burst protocol: gain in at least 10 of 16 burst cells", "0 cells", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V7", "H-A3", "event ACK secure against a key holder", "a forged ACK from a key holder stops every vehicle", NS, "1.000", "ANALYTICAL", "negatives", ""),
    ("V11", "H-S1", "impact-side rule keeps 0.90 in every sensor variant", "3 of 16 sets below 0.90 (axis flips, 10 Hz)", NS, "1.000", "SIMULATED_HW_FORMAT", "negatives", "family S"),
    ("V11", "H-S2", "2 g trigger recall 0.90 and false alarms at most 0.10", "false-alarm rate 0.640 in the base variant", NS, "1.000", "SIMULATED_HW_FORMAT", "negatives", "family S"),
    ("V11", "H-S3", "UA-SCT delivery at least fixed-3 minus 0.02 on calibrated links", "criterion met, Holm p 1", NS, "1.000", "SIMULATED_HW_FORMAT", "negatives", "family S"),
    ("V11", "H-S4", "median trigger-to-ACK latency at least 500 ms", "median 519 ms", S, "< 0.001", "SIMULATED_HW_FORMAT", "supplement", "family S"),
    ("V11", "H-S5", "no attack accepted; counter persisted", "0 of 289 attempts accepted", S, "< 0.001", "SIMULATED_HW_FORMAT", "supplement", "family S"),
    ("V11", "H-S6", "SW-420 confirmation lowers false alarms by 0.02 and loses at most 0.02 recall", "recall loss 0.043", NS, "< 0.001", "SIMULATED_HW_FORMAT", "negatives", "family S; sign of the criterion explained in the source"),
    ("V11", "H-R1a", "GTF accepts at least 99% of valid alerts after a car reboot", "smallest availability 0.9965", S, "0.003", "SIMULATED", "supplement", "family R"),
    ("V11", "H-R1b", "GTF replay acceptance zero outside, at most 1% inside the window", "largest rate 0.0325", NS, "1.000", "SIMULATED", "negatives", "family R"),
    ("V11", "H-R1c", "GTF cuts flash writes 10 times", "16.7 times", S, "< 0.001", "ANALYTICAL", "main (boot-counter design cost) and supplement", "family R"),
    ("V11", "H-R2a", "40-byte frame with 7 or 8-byte tag raises burst delivery by 5 points", "criterion met, Holm p 0.454", NS, "0.454", "SIMULATED", "negatives", "family R"),
    ("V11", "H-R2b", "97-byte frame dominated by shorter frames with tag at least 8 bytes", "dominated", S, "< 0.001", "SIMULATED", "supplement", "family R"),
    ("V11", "H-R3", "provisional flash at least 0.8 s earlier, under 20% retractions, under 40% airtime", "1.87 s earlier; retractions 0.108", S, "0.014", "SIMULATED", "main (C5)", "family R; later tested in ns-3 (V13)"),
    ("V11", "H-R4", "per-vehicle ACK keys: a forged ACK stops only that node", "suppressed fraction 1.0 to 0.333", S, "< 0.001", "ANALYTICAL", "main (C4)", "family R; later proved in Tamarin (V14)"),
    ("V12", "H-D1a", "D1 loss-adaptive deadline table beats the severity table in every cell", "FRESH-A smallest +0.026; ns-3 smallest -0.013", S, "see REDESIGN_B_RESULTS", "SIMULATED", "supplement (simulator-dependent)", "supported in the custom simulator, not in ns-3"),
    ("V12", "H-D1b", "D1 gains at loss of 40% or more", "+0.162 custom; +0.021 ns-3 (S-X: +0.116 against +0.021)", S, "see REDESIGN_B_RESULTS", "SIMULATED", "main (C6, evaluation finding) and supplement", "not met in ns-3"),
    ("V12", "H-D1c", "D1 within the duty limit", "0 runs above the limit", S, "see REDESIGN_B_RESULTS", "SIMULATED", "supplement", ""),
    ("V12", "H-D1s", "D1 against six baselines", "smallest -0.003, mean +0.031 (FRESH-A); S-X not met", S, "see REDESIGN_B_RESULTS", "SIMULATED", "supplement", "Nessa-style baseline ADDED-AFTER-SESSION-1, outside the family"),
    ("V12", "H-D2a", "D2 gateway-signed cluster ACK loses no delivery", "smallest change -0.001", S, "see REDESIGN_B_RESULTS", "SIMULATED", "supplement", ""),
    ("V12", "H-D2b", "D2 burst gain of 5 points", "+0.011", NS, "see REDESIGN_B_RESULTS", "SIMULATED", "negatives", ""),
    ("V12", "H-D2c", "no vehicle-key holder stops another vehicle", "bounded model, 2 vehicles", S, "see REDESIGN_B_RESULTS", "ANALYTICAL", "supplement", ""),
    ("V12", "H-D3", "D3 slotted retries gain 5 points in bursts", "+0.001", NS, "see REDESIGN_B_RESULTS", "SIMULATED", "negatives", ""),
    ("V12", "H-D4a", "D4 24-byte provisional frame within the airtime bound", "extra airtime 0.410 to 0.496; 0 of 48 cells below 0.25", NS, "see REDESIGN_B_RESULTS", "SIMULATED", "negatives", ""),
    ("V12", "H-D4b", "D4 arrival time and burst delivery", "not run", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V13", "H-C3 (refit)", "H-C3 refit on the development fold (P0)", "frontal barrier only; duration statistic 0.191 against gate 0.20; pole and side fail", S, "0.018 (V5 family recomputed)", "SIMULATED", "main (C2)", "re-test of the V5 hypothesis; counted once, under V5"),
    ("V13", "H-P1a", "provisional alert at least 0.8 s earlier in ns-3", "4 of 4 cells supported (SF7, SF9, two settings)", S, "0.004", "SIMULATED", "main (C5)", "four cells in the family of 8"),
    ("V13", "H-P1b", "retractions under 20% at the 1% target", "0.108", S, "not in the family (data-side)", "MEASURED_SOFTWARE", "main (C5)", ""),
    ("V13", "H-P1c", "extra airtime under 40% and no delivery loss", "2 of 4 cells supported (SF7 yes; SF9 no)", M, "0.004 (SF7), 1.000 (SF9)", "SIMULATED", "main (C5)", "four cells in the family of 8"),
    ("V14", "H-T1a-L", "D1 within 2 points of the best baseline, low-loss group", "best minus D1 = -0.1 points", S, "~0.0035", "TRACE_DRIVEN", "supplement", ""),
    ("V14", "H-T1a-M", "same, medium-loss group", "-1.4 points", S, "~0.0035", "TRACE_DRIVEN", "supplement", ""),
    ("V14", "H-T1a-H", "same, high-loss group", "-6.7 points", S, "~0.0035", "TRACE_DRIVEN", "supplement", ""),
    ("V14", "H-T1b", "D1 above quick retries at loss of 40% or more", "+6.7 points; zero-spacing control 54.0 against D1 49.3", S, "~0.0035", "TRACE_DRIVEN", "main (C6, with the control)", "the control shows the gain is retry timing"),
    ("V14", "H-T1c", "provisional alert earlier, extra airtime under 40%, no delivery loss", "1.87 s; airtime 31% to 37%", S, "~0.0035", "TRACE_DRIVEN", "main (C5)", ""),
    ("V14", "H-T2", "D1 worst-case delivery time not longer than quick retries, k = 0 to 6", "holds; no duty breach", S, "no p (rule)", "FORMAL", "main (C6)", "exhaustive enumeration, not UPPAAL"),
    ("V14", "H-T2sec", "Tamarin: authenticity, ACK binding, freshness, id uniqueness", "all proved except id uniqueness after a car reboot (not decided)", M, "no p (rule)", "FORMAL", "main (C4)", ""),
    ("V14", "H-T3a", "early-exit rule decides at least 0.8 s earlier", "median 1750 ms", S, "~0.0035", "MEASURED_SOFTWARE", "main (C5)", ""),
    ("V14", "H-T3b", "retraction share under 20%", "10.8%", S, "~0.0035", "MEASURED_SOFTWARE", "main (C5)", ""),
    ("V14", "H-T3c", "earlier arrival in at least 2 of 3 link models", "custom and trace; ns-3 NOT_RUN at the time (later run in V13)", S, "no p (rule)", "SIMULATED and TRACE_DRIVEN", "main (C5)", ""),
    ("V15", "H-A1a", "24-byte repeated provisional frame: extra airtime at SF9 at most 40% in all 8 cells", "2 of 8 cells met; 0.31 to 0.61", NS, "1.000", "SIMULATED", "negatives", ""),
    ("V15", "H-A1b", "provisional delivery within 10 s up by 3 points on fresh sniffer links", "+1.4 points", NS, "0.0025", "TRACE_DRIVEN", "negatives", "p below 0.05 but the effect is under the 3 points required"),
    ("V15", "H-A1c", "no cell worse than R3 by more than 1 point", "ns-3 worst cell -2.1 points", NS, "1.000", "SIMULATED and TRACE_DRIVEN", "negatives", ""),
    ("V15", "H-A2a", "two receivers raise 10 s delivery by 10 points on weak links (EXPLORATORY)", "+4.9 points; 52% of devices heard by one gateway", NS, "0.0025", "TRACE_DRIVEN", "negatives", "p below 0.05 but under the 10 points required"),
    ("V15", "H-A2b", "share at 0.99 delivery rises from one to three receivers (EXPLORATORY)", "+0.26 points", NS, "0.051", "TRACE_DRIVEN", "negatives", ""),
    ("V16", "H-L1", "mounting calibration: side accuracy at least 0.90, NHTSA balanced at least 0.90", "0.986 pooled; NHTSA 0.975; mirror flips not recovered", S, "< 1e-9", "SIMULATED_HW_FORMAT and MEASURED_SOFTWARE", "main (C7)", ""),
    ("V16", "H-L2a", "post-event features cut near-miss false alarms by 25%", "-0.545 relative change", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V16", "H-L2b", "retraction share falls by 3 points", "1.4 points", NS, "0.472", "MEASURED_SOFTWARE", "negatives", ""),
    ("V16", "H-L3", "wake-on-motion: recall within 1 point, energy at least 50% lower", "recall 0.631 against 0.609 always-on; energy ratio 0.25", S, "0.005", "MEASURED_SOFTWARE and ANALYTICAL", "main (C7)", "active share 0.20 stated"),
    ("V16", "H-L4", "SF ladder gains 3 points near the SF7 edge", "edge gain 0.098; worst lower limit -0.009", S, "0.005", "SIMULATED (ns-3 only)", "supplement", "custom-simulator part NOT_RUN"),
    ("V16", "H-L5", "end-to-end threshold co-design lowers P90 time by 10%", "no change in any model", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V16", "H-L6", "crash-weighted gateway placement covers 10 points more crashes", "+1.8 to +5.6 points", NS, "0.005", "MEASURED_SOFTWARE and ANALYTICAL", "negatives", "p below 0.05 but under the 10 points required"),
    ("V16", "H-L7a", "Tamarin proves forward secrecy, authenticity, ACK binding of the ratchet", "undecided: heap exhausted", NS, "1.000", "FORMAL", "negatives", "counted as not supported (undecided)"),
    ("V16", "H-L7b", "resynchronisation within a window of 8 for every enumerated sequence", "1,398,101 sequences, no violation", S, "< 1e-9", "FORMAL", "supplement", ""),
    ("V16", "H-L8a", "at most 6 high-confidence forwards per hour", "6 over 232,966 states", S, "< 1e-9", "FORMAL", "supplement", "holds by construction of the counter"),
    ("V16", "H-L8b", "no legitimate alert quarantined", "1 of 2,000 vehicle-hours", NS, "1.000", "SIMULATED and MEASURED_SOFTWARE", "negatives", ""),
    ("V16", "H-L10a", "a further benchmark has more than 1% identical test windows", "0 in UCI HAR and SisFall", NS, "1.000", "MEASURED_SOFTWARE", "main (C1, one sentence) and negatives", ""),
    ("V16", "H-L10b", "removing leaked windows changes a baseline by more than 1 point", "not run (no leak found)", NR, "1.000 (p = 1 rule)", "NOT_RUN", "not reported", ""),
    ("V16", "H-L11a", "mirror-flip detection from turns (ADDED-AFTER-SESSION-1; own family of one)", "both-channel 100% of 100, false detection 0%; accelerometer-only x 57%, y 89% against 95%", NS, "own family", "MEASURED_SOFTWARE", "supplement (descriptive) and negatives", "added after session 1, before any L11 run"),
    ("V16", "H-L11b", "second L11 test", "not run", NR, "own family", "NOT_RUN", "not reported", ""),
    ("V17", "H-R6-1a", "micro-confirm extra airtime at SF9 at most 40% in each of 8 ns-3 cells", "extra airtime -0.23 to +0.03 against single-stage; 0.47 to 0.77 of R3's airtime", S, "0.002", "SIMULATED", "main (C8)", "almost automatic because the micro-confirm replaces the 97-byte confirm; second statistic reported"),
    ("V17", "H-R6-1b", "micro-confirm delivery not lower than R3 by more than 1 point in 16 ns-3 cells and 3 trace groups", "largest loss 0.25 points; trace groups zero by construction", S, "0.002", "SIMULATED and TRACE_DRIVEN", "main (C8)", "13-byte ns-3 frame; trace part degenerate for delivery"),
    ("V17", "H-R6-1c", "micro-confirm binding, anti-replay and cancel lemmas; control attack found", "ProVerif and Tamarin: all lemmas proved; control without T1 attacked", S, "< 1e-9", "FORMAL", "main (C8)", "symbolic model"),
    ("V17", "H-R6-2a", "sequential early exit decides 200 ms earlier on average", "14.2 ms (lower limit 9.0 ms)", NS, "1.000", "MEASURED_SOFTWARE", "negatives", "200 ms is above the largest possible gain (62 ms) given a fixed-rule mean of 112 ms; V17 quoted the mean wrongly"),
    ("V17", "H-R6-2b", "sequential early exit raises retraction by at most 2 points", "+12.6 points (upper limit 14.3)", NS, "1.000", "MEASURED_SOFTWARE", "negatives", ""),
    ("V17", "H-R6-3a", "forward secrecy of the hash ratchet (bounded at 3 steps)", "ProVerif proves authenticity and secrecy of past alerts; Tamarin within the bound", S, "< 1e-9", "FORMAL", "main (C8)", "the bound is part of the result"),
    ("V17", "H-R6-3b", "quarantine cannot be triggered by unverified frames", "variant B proved; variant A attacked with two frames", S, "< 1e-9", "FORMAL", "main (C8)", "the count-before-verification rule of L8 is attackable"),
]

NOT_HYPOTHESES = [
    "V1 to V16: X4 (labels), the T4 energy budget, the zero-spacing duty check (V13), A3 ProVerif (V15), L9 dispatch break-even (V16, descriptive) and the 'B1' and 'B3' checks of V5 are statements, checks or descriptive results with no hypothesis test; they are not counted in the totals.",
    "Versions V6, V8, V9 and V10 do not exist as files: the numbering skipped them. No preregistration was written and then left unrun.",
]


def first_commit(name):
    r = subprocess.run(["git", "log", "--diff-filter=A", "--format=%h %ad", "--date=format:%Y-%m-%d %H:%M", "--", f"docs/02_preregistration/{name}"], cwd=ROOT, capture_output=True, text=True)
    out = r.stdout.strip().splitlines()
    return out[-1] if out else "?"


def check_against_results(rows):
    d = {e["name"]: e["value"] for e in json.load(open(ROOT / "results/results.json", encoding="utf-8"))}
    bad = []

    def verdict(key_met, key_p, id_):
        met, p = d.get(key_met), d.get(key_p)
        return met, p

    checks = {  # (id) -> (verdict key or None, expected verdict text)
        ("V3", "H-X6"): ("x.holm.H-X6.verdict", "SUPPORTED"), ("V3", "H-X1"): ("x.holm.H-X1.verdict", "NOT SUPPORTED"),
        ("V3", "H-X7"): ("x.holm.H-X7.verdict", "NOT SUPPORTED"),
    }
    for (rnd, i), (k, exp) in checks.items():
        if d.get(k) != exp:
            bad.append((rnd, i, k, d.get(k), exp))
    # criterion flags of V7, V11
    for i, k in [("H-Q1e", "q.holm.hq1e.criterion_met"), ("H-Q2a", "q.holm.hq2a.criterion_met"), ("H-S4", "sh.holm.hs4.criterion_met"), ("H-S5", "sh.holm.hs5.criterion_met"), ("H-R1a", "ar.holm.hr1a.criterion_met"), ("H-R3", "ar.holm.hr3.criterion_met"), ("H-R4", "ar.holm.hr4.criterion_met")]:
        if d.get(k) != 1:
            bad.append(("flag", i, k, d.get(k), 1))
    for i, k in [("H-S1", "sh.holm.hs1.criterion_met"), ("H-S2", "sh.holm.hs2.criterion_met"), ("H-Q1a", "q.holm.hq1a.criterion_met"), ("H-A1", "pa.holm.ha1.criterion_met")]:
        if d.get(k) != 0:
            bad.append(("flag", i, k, d.get(k), 0))
    # round 5 family: supported hypotheses
    sup5 = d.get("r5.verdict.n_supported")
    return bad, sup5


def main():
    cnt = collections.Counter()
    by = collections.defaultdict(collections.Counter)
    for r in ROWS:
        if r[1] == "H-C3 (refit)":
            continue
        cnt[r[4]] += 1
        by[r[0]][r[4]] += 1
    bad, sup5 = check_against_results(ROWS)
    assert not bad, bad
    L = ["# Hypothesis ledger", "",
         "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-16 |", "| Owner | Mritula S |",
         "| Scope | One row per preregistered hypothesis of every preregistration version (V1 to V17 and addenda): family, data role, result, Holm p, label, paper location; totals by version (generated by scripts/vf_ledger.py). |",
         "| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, SIMULATED_HW_FORMAT, TRACE_DRIVEN, FORMAL, ANALYTICAL, NOT_RUN |",
         "| Abbreviations | Holm = Holm-Bonferroni step-down correction; AP = average precision; SF = LoRa spreading factor; GTF = boot-epoch freshness design; ns-3 = network simulator 3; LoED = LoRaWAN trace set; FARS = Fatality Analysis Reporting System |",
         "<!-- header:end -->", "",
         "How to read it. A row is one preregistered hypothesis; test cells (for example the SF7 and SF9 cells of H-P1a) belong to their row. A hypothesis is called SUPPORTED only if its stated criterion holds and, where the version has a Holm family, the Holm-adjusted p is below 0.05. A p-value below 0.05 with a missed effect size is NOT SUPPORTED. NOT_RUN rows enter their family with p = 1. PARTLY means some cells hold and others do not. The p-values are the stored ones (`results/results.json`); where a source gives only 'see REDESIGN_B_RESULTS' the value is in `docs/03_results/REDESIGN_B_RESULTS.md`.", "",
         "## Versions", "", "| Version | File | Commit and time of the file | Topic | Holm family | Data roles |", "|---|---|---|---|---|---|"]
    for v, (f, topic, fam, role) in ROUNDS.items():
        L.append(f"| {v} | `{f}` | {first_commit(f)} | {topic} | {fam} | {role} |")
    L += ["", "Not counted: " + " ".join(NOT_HYPOTHESES), "",
          "Addenda written after earlier results (handled as stated): V4 addendum 1 (clarifications after the P1 to P3 freezes, no change of a hypothesis); V5 addenda 1 to 3 (after Blocks B, C and G; the F-family rows marked EXPLORATORY-REVISED re-test earlier hypotheses after their results were seen and are labelled as such; H-C3 is tested for the frontal barrier only because the generator gate failed for the other modes); V12 (the Nessa-style baseline in H-D1s was added after session 1 and sits outside the Holm family); V16 addenda A1 and A2 (before any run) and S2, S2.1, S2.2 (session 2 datasets and designs, before any session-2 run); L11 was added after session 1 and is tested in its own family of one.", "",
          "## Ledger", "", "| Version | ID | Statement | Result | Verdict | Holm p | Label | Paper location | Note |", "|---|---|---|---|---|---|---|---|---|"]
    for r in ROWS:
        L.append("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
    L += ["", "## Totals", "", "| Version | Preregistered | Run | SUPPORTED | NOT SUPPORTED | PARTLY | NOT_RUN |", "|---|---|---|---|---|---|---|"]
    tot = collections.Counter()
    for v in ROUNDS:
        c = by[v]
        n = sum(c.values())
        L.append(f"| {v} | {n} | {n - c[NR]} | {c[S]} | {c[NS]} | {c[M]} | {c[NR]} |")
        tot.update(c)
    N = sum(tot.values())
    L.append(f"| all | {N} | {N - tot[NR]} | {tot[S]} | {tot[NS]} | {tot[M]} | {tot[NR]} |")
    no_p = ("no p (rule)", "no p (formula)", "not in the family (data-side)", "own family")
    conf = [r for r in ROWS if r[1] != "H-C3 (refit)" and r[5] not in no_p]
    cc = collections.Counter(r[4] for r in conf)
    L += ["", f"Confirmatory-family rows (a Holm p-value in a stated family; V12 counted as one family of 10): {len(conf)} rows, {cc[S]} supported, {cc[NS]} not supported, {cc[M]} partly, {cc[NR]} NOT_RUN.",
          f"Round 5 (V16) Holm family of 13: {sup5} supported according to `results.json` (`r5.verdict.n_supported`); the ledger shows the same five (L1, L3, L4, L7b, L8a); L11 in its own family is not supported.", "",
          "The totals count hypotheses, not the hundreds of sub-tests inside them (cells, seeds, bootstrap intervals).", ""]
    (ROOT / "docs/04_audits/HYPOTHESIS_LEDGER.md").write_text("\n".join(L), encoding="utf-8")
    print(N, dict(tot), len(conf), dict(cc), sup5)
    assert sup5 == sum(1 for r in ROWS if r[0] == "V16" and r[4] == S and r[1] not in ("H-L11a", "H-L11b")), "round 5 supported count"
    from crashguard.results import record_many
    src = "scripts/vf_ledger.py"  # round 6 totals go to r6.ledger.*; the vf.ledger.* keys of the verification run (V1 to V16) are not changed
    ent = []
    for v in ROUNDS:
        c = by[v]
        n = sum(c.values())
        for nm, val in [("preregistered", n), ("run", n - c[NR]), ("supported", c[S]), ("not_supported", c[NS]), ("partly", c[M]), ("not_run", c[NR])]:
            ent.append(dict(name=f"r6.ledger.{v}.{nm}", value=val, unit="hypotheses", origin="ANALYTICAL", source_file=src, notes="row count of docs/04_audits/HYPOTHESIS_LEDGER.md; no new measurement"))
    for nm, val in [("preregistered", N), ("run", N - tot[NR]), ("supported", tot[S]), ("not_supported", tot[NS]), ("partly", tot[M]), ("not_run", tot[NR]), ("confirmatory_rows", len(conf)), ("confirmatory_supported", cc[S]), ("confirmatory_not_supported", cc[NS]), ("confirmatory_partly", cc[M]), ("confirmatory_not_run", cc[NR]), ("versions", len(ROUNDS))]:
        ent.append(dict(name=f"r6.ledger.all.{nm}", value=val, unit="hypotheses", origin="ANALYTICAL", source_file=src, notes="row count of docs/04_audits/HYPOTHESIS_LEDGER.md; no new measurement"))
    record_many(ent, purge_prefixes=("r6.ledger.",))
    return N, tot, len(conf), cc, by


if __name__ == "__main__":
    main()
