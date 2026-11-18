"""V6.6: docs/04_audits/NEGATIVES_BY_LAYER.md, every NOT SUPPORTED or PARTLY hypothesis of the ledger grouped by layer, with its number and the likely mechanism.

The mechanisms are the ones recorded in docs/03_results/NEGATIVES_REGISTER.md and in the decision tables; (inferred) means it was not tested. Where no mechanism was recorded the text says 'not diagnosed'.
usage: python scripts/vf_negatives.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vf_ledger as L  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

ND = "not diagnosed (no mechanism was tested)"
LAYER = {
    "Sensing and severity estimation": ["H-A2", "H-A3", "H-D1", "H-D2", "H-P1", "H-P2", "H-P3a", "H-P3b", "H-X5", "H-X7", "H-F1", "H-F1b", "H-F1c", "H-Q1a", "H-Q1b", "H-Q1c", "H-Q1d", "H-Q1f"],
    "Detection and the node": ["H-X1", "H-X2", "H-X3", "H-X8", "H-P4b", "H-P4c", "H-F2a", "H-F2b", "H-F2d", "H-Q2b", "H-Q2c", "H-Q2d", "H-Q2f", "H-Q2g", "H-L2a", "H-L2b", "H-S1", "H-S2", "H-S6"],
    "Protocol and security": ["H-R1b", "H-R2a", "H-T2sec", "H-L7a", "H-L8b", "H-D4a", "H-A1a"],
    "Link, retry and channel access": ["H-B1", "H-B2", "H-B3", "H-E1", "H-F1", "H-B2", "H-F3a", "H-F3b", "H-G3a", "H-G3b", "H-G3c", "H-S3", "H-D2b", "H-D3", "H-P1c", "H-A1b", "H-A1c", "H-A2a", "H-A2b", "H-L5", "H-L6"],
    "Benchmarks and data": ["H-L10a", "H-L11a"],
}
# (version, id) -> layer for the ids that occur in two versions
OVERRIDE = {("V2", "H-F1"): "Link, retry and channel access", ("V5", "H-F1"): "Sensing and severity estimation", ("V2", "H-B2"): "Link, retry and channel access", ("V5", "H-B2"): "Link, retry and channel access",
            ("V7", "H-A1"): "Link, retry and channel access", ("V7", "H-A2"): "Link, retry and channel access", ("V7", "H-A3"): "Protocol and security", ("V2", "H-A2"): "Sensing and severity estimation",
            ("V2", "H-A3"): "Sensing and severity estimation", ("V15", "H-A1a"): "Protocol and security", ("V13", "H-P1c"): "Protocol and security", ("V2", "H-D1"): "Detection and the node", ("V2", "H-D2"): "Detection and the node",
            ("V12", "H-D2b"): "Link, retry and channel access", ("V12", "H-D3"): "Link, retry and channel access", ("V12", "H-D4a"): "Protocol and security"}
MECH = {
    "H-A2": ND, "H-A3": "containment of the reference delta-V is below 0.90 (not diagnosed)",
    "H-D1": "the flag saves 86 ms where 100 ms were needed; the window length sets the timing (inferred)", "H-D2": "criterion met but the Holm-adjusted p is above 0.05 (statistical power)",
    "H-P1": "small sealed fold (186 records, 7 Low) and 913 real pulses (inferred)", "H-P2": "a one-sided bound from the plain estimate cannot be much narrower when the plain estimate under-reads by a factor of about 2 (inferred)",
    "H-P3a": "the reliability score ranks errors weakly (inferred)", "H-P3b": "the abstain signal is a noisier escalation signal than lowering thresholds (inferred)",
    "H-X5": "the fill + ridge correction adds noise to the ranking (inferred)", "H-X7": "mounting error and synchronisation are not modelled; pole and side modes dominate the shortfall (inferred)",
    "H-F1": "same as the original (H-P1)", "H-F1b": "same as H-P2", "H-F1c": "same as H-P3a",
    "H-Q1a": "same as the original (rerun on real-only data)", "H-Q1b": "same as the original", "H-Q1c": "same as the original", "H-Q1d": "same as the original", "H-Q1f": "same as the original",
    "H-X1": "arithmetic of the node layout: 16-bit thresholds cut the flash estimate by 22%, not 30%", "H-X2": "the 2 g trigger already passes most crashes (stated in the preregistration)",
    "H-X3": "near-duplicates are few among the training windows relative to the whole set (inferred)", "H-X8": "the 5% target favours the early-exit rule (as measured; why was not tested)",
    "H-P4b": "augmented crash copies shift the score distribution against the validation threshold (inferred)", "H-P4c": "structure of the vehicle-size categories (inferred)",
    "H-F2a": "same as H-P4b", "H-F2b": "same as H-X3", "H-F2d": "same as H-X1 (the flash clause is arithmetic)",
    "H-Q2b": "same as the original", "H-Q2c": "same as the original", "H-Q2d": "same as H-X1", "H-Q2f": "same as the original", "H-Q2g": "same as the original",
    "H-L2a": "the confirm stage already holds the false-alarm rate (inferred)", "H-L2b": "same as H-L2a",
    "H-S1": "an axis-sign flip swaps front and rear (or left and right); at 10 Hz a 12 to 45 ms pulse is mostly missed (inferred from the confusion table)",
    "H-S2": "the 2 g trigger passes many bench non-crash events (false-alarm rate 0.640 in the base variant; the cause per event kind was not separated)", "H-S6": "the switch confirmation removes false alarms and also crashes; the balance depends on the assumed switch sensitivity",
    "H-R1b": "the ring was smaller than the alerts per window at the held-out burst load; replays inside the window were accepted",
    "H-R2a": "variance across cells; the fields dropped from the short frame were not designed (inferred)", "H-T2sec": "alert-id uniqueness after a car reboot was not decided in Tamarin (timeouts); ProVerif finds an attack on the frozen design inside the same GPS second",
    "H-L7a": "Tamarin heap of 5 GB exhausted for the ratchet model", "H-L8b": "the per-minute spacing rule quarantines a legitimate vehicle about once in 2,000 vehicle-hours",
    "H-D4a": "a 24-byte frame costs more airtime than the 14-byte flash", "H-A1a": "a 24-byte frame costs more airtime than the 14-byte flash; repeats add channel load (inferred)",
    "H-B1": ND, "H-B2": ND, "H-B3": "not evaluable because H-B1 failed", "H-E1": "gain below 2 points (not diagnosed)",
    "H-F3a": "a lowered table reaches the same escalation", "H-F3b": "same as H-P3b", "H-G3a": "8 slots per 30 s frame for a burst of 30 cars (inferred; slot sweep in G5)",
    "H-G3b": "hidden terminals (sensing probability 0.7, assumed) and the short backoff (inferred)", "H-G3c": "the relayed copy meets the same loss and collisions as the sender's own retries (inferred)",
    "H-S3": "criterion met on the point estimate but no difference from fixed-3 was detectable (raw p 0.39)", "H-D2b": "burst gain +0.011 against 5 points required (not diagnosed further)",
    "H-D3": "0.54 of failures were collisions or a deaf gateway; fixed K put 2.7 times as many frames on the channel", "H-P1c": "at SF9 the flash and the three cancel transmissions add 54% extra airtime against the 40% bound; at SF7 they do not",
    "H-A1b": "a 24-byte frame costs more airtime than the 14-byte flash; repeats add channel load (inferred)", "H-A1c": "repeated frames add channel load at a loss of 0.6 (inferred)",
    "H-A2a": "a second gateway cannot help a device it does not hear (52% of devices are heard by one gateway)", "H-A2b": "same as H-A2a",
    "V7:H-A1": "overheard frames are rare at the assumed load (inferred)", "V7:H-A2": "slots delay the opening attempt (inferred)", "V7:H-A3": "one forged event-level acknowledgement from a holder of the shared key stops every vehicle of the cell",
    "H-L5": "the confirm stage is fixed and the early-exit grid is small (inferred)", "H-L6": "placements overlap in cities (inferred)",
    "H-L10a": "there is nothing to find: no duplicate windows across splits in UCI HAR or SisFall", "H-L11a": "one of two estimates is changed by an accelerometer-only flip and the clips are short (inferred)",
}


def layer_of(v: str, i: str) -> str:
    if (v, i) in OVERRIDE:
        return OVERRIDE[(v, i)]
    for name, ids in LAYER.items():
        if i in ids:
            return name
    return "Other"


def main() -> None:
    rows = [r for r in L.ROWS if r[4] in (L.NS, L.M)]
    by: dict[str, list] = {}
    for r in rows:
        by.setdefault(layer_of(r[0], r[1]), []).append(r)
    out = ["# Negative results by layer", "", "<!-- header:start -->", "<!-- header:end -->", "",
           f"Every hypothesis of `docs/04_audits/HYPOTHESIS_LEDGER.md` whose verdict is NOT SUPPORTED or PARTLY ({len(rows)} rows), grouped by layer, with its number and the likely mechanism. A mechanism marked (inferred) was not tested; 'not diagnosed' means that none was recorded. Original verdicts are not softened. Hypotheses that were not run ({sum(1 for r in L.ROWS if r[4] == L.NR)}) are listed at the end.", ""]
    for name in ["Sensing and severity estimation", "Detection and the node", "Protocol and security", "Link, retry and channel access", "Benchmarks and data", "Other"]:
        if name not in by:
            continue
        out += [f"## {name}", "", "| Version | ID | Statement | Found | Label | Likely mechanism |", "|---|---|---|---|---|---|"]
        for v, i, st, res, ver, p, lab, place, note in by[name]:
            out.append(f"| {v} | {i} | {st} | {res} | {lab} | {MECH.get(v + ":" + i, MECH.get(i, ND))} |")
        out.append("")
    out += ["## Not run", "", "| Version | ID | Statement | Reason |", "|---|---|---|---|"]
    out += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} |" for r in L.ROWS if r[4] == L.NR]
    (ROOT / "docs/04_audits/NEGATIVES_BY_LAYER.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(len(rows), {k: len(v) for k, v in by.items()})


if __name__ == "__main__":
    main()
