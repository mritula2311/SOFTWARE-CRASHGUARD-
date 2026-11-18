"""A4 documents: the round-4 literature query log and the rows A1 to A3 of the novelty matrix (idempotent: the rows sit between marker comments).

    python -m crashguard.a4_lit_docs
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q = ROOT / "results" / "tables" / "a4_lit_queries.json"
OUT = ROOT / "docs" / "06_references" / "LIT_QUERIES_ROUND4.md"
MATRIX = ROOT / "docs" / "06_references" / "NOVELTY_MATRIX_2021PLUS.md"
BEGIN, END = "<!-- a4:begin -->", "<!-- a4:end -->"

TOPIC_NAME = {14: "Gateway or receiver diversity, macro-diversity in LoRaWAN", 15: "Short frames, payload reduction and time on air for latency", 16: "ProVerif and LoRa or LoRaWAN"}

OPENED = [
    ("Lanka and Kothandaraman, IEEE Access 2026, doi 10.1109/access.2026.3714528", "OpenAlex record (abstract); open access through the DOI, the IEEE Xplore page returns HTTP 418 to scripts, so the full text was not opened", "Relay overlay that preserves multi-gateway observations, with a time-aware downlink ACK gateway selection; simulation with an ADR-like link model"),
    ("Petroni and Biagi, IEEE TWC 2022, doi 10.1109/twc.2022.3172629", "OpenAlex record (abstract); not open access", "Network-server combining of the same packet received by several gateways; simulation"),
    ("Can et al., Sensors 2022, 22(22), 8831, doi 10.3390/s22228831", "Europe PMC PMC9695022 (full text opened 2026-11-15)", "Coverage of LPWAN with several gateways for a packet success rate above 85%; simulation, no deadline, no acknowledgement"),
    ("Abakar et al., Future Internet 2022, 14(11), 312, doi 10.3390/fi14110312", "OpenAlex record (abstract); open-access PDF not opened (MDPI returns HTTP 403 to scripts)", "Payload length and packet delivery with several gateways and confirmed traffic; simulation"),
    ("Lopez et al., J. Commun. Technol. Electron. 2021, doi 10.1134/s1064226921140114", "OpenAlex record (abstract); not open access", "Time on air against payload size for indoor emergency use, measured; no retry or acknowledgement design"),
    ("Wu et al., ReLoRaWAN, Ad Hoc Networks 2023, doi 10.1016/j.adhoc.2023.103203", "OpenAlex record has an empty abstract; title only, not used for any claim", "Reliable delivery with several gateways (per title)"),
    ("Amjadian et al., Int. J. Sensor Networks 2025, doi 10.1504/ijsnet.2025.149892", "OpenAlex record (abstract); not open access", "Scyther and ProVerif analysis of the LoRaWAN key-exchange protocol and a proposed scheme"),
    ("Mendeley Data 2026, doi 10.17632/5drwdxt6tr (Experimental Multi-Gateway LoRaWAN)", "OpenAlex record (description); not downloaded", "Six nodes and two gateways, 26,938 uplinks; too few devices for a test over devices"),
]

ROWS = """| A1 | Short provisional alert frame (24 bytes) repeated until a verified per-vehicle ACK, with a full confirm frame (round 4; tested and killed: H-A1a and H-A1b not met) | Lopez et al., J. Commun. Technol. Electron. 2021 (time on air against payload size, abstract level); Abakar et al., Future Internet 2022 (payload length with several gateways, abstract level) | Measured time on air for short payloads in emergency use; simulated delivery against payload length and gateway count. Neither designs a repeated short alert with an authenticated per-vehicle ACK | A tested design that did not meet its criteria; nothing to claim | None found for the design (context only) | "No journal article from 2021 onwards found in the sources checked (OpenAlex; IEEE Xplore, Scopus, Google Scholar and TRID not run in this round) that combines a short repeated provisional alert with an authenticated per-vehicle ACK." No claim of benefit is made; the design is a negative result | Negatives register (A1) |
| A2 | Receiver diversity for deadline-bound crash alerts, measured on real per-gateway traces (round 4, EXPLORATORY; H-A2a not met) | Petroni and Biagi, IEEE TWC 2022 (network-server combining, simulation); Can et al., Sensors 2022 (full text opened: coverage with gateway diversity, simulation); Lanka and Kothandaraman, IEEE Access 2026 (abstract: relays that keep gateway diversity, time-aware ACK gateway selection, simulation); Wu et al., Ad Hoc Networks 2023 (title only) | Gateway diversity is established as a way to raise packet success; the cited work simulates it and does not measure delivery before a deadline by receiver count on real traces | Delivery within 10 s by number of receivers on {n_dev} LoED devices: a second receiver adds {a2a} points on weak links (not the 10 points preregistered), {one}% of devices are heard by one gateway only | Partial (the idea is known; the deadline-bound measurement on real traces was not found) | "Gateway diversity is known to help; on the LoED traces the gain in 10 s delivery from a second receiver was small (EXPLORATORY, same dataset as development)." No novelty wording | Negatives register (A2) |
| A3 | Second prover (ProVerif 2.05) for the car-reboot alert-id lemma, frozen design and boot-counter variant (round 4) | Amjadian et al., Int. J. Sensor Networks 2025 (ProVerif and Scyther on LoRaWAN key exchange, abstract level); Wesemeyer et al., EuroS&P 2020 (Tamarin, LoRaWAN 1.1 key establishment, context) | ProVerif and Tamarin have been used on LoRaWAN key-exchange and join protocols; none of the items opened treats alert-id reuse after a vehicle reboot | Alert-id uniqueness across reboots, with and without a boot counter, in two tools | None found for alert-id reuse | "No journal article from 2021 onwards found in the sources checked that formally analyses alert-id reuse after a reboot in a LoRa alert protocol." Using ProVerif on LoRaWAN is not new | Main text only as a design note if the result supports it |
"""


def main() -> None:
    q = json.loads(Q.read_text(encoding="utf-8"))
    L = ["# Literature queries, round 4 (A4)", "",
         "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-15 |", "| Owner | Mritula S |",
         "| Scope | Round 4 query log: three topics, OpenAlex queries for journal articles from 2021 and a context search without filters; counts, top titles and the items opened. |",
         "| Evidence labels used | NOT_RUN |", "<!-- header:end -->", "",
         f"Run date {q[0]['date_run']}. Database: OpenAlex API (no key, no personal detail sent). Journal scope: `{q[0]['filters']}`; context scope: no filter (older and conference work). IEEE Xplore, Scopus, Google Scholar and TRID were not run.", ""]
    for t in sorted({r["topic"] for r in q}):
        L += [f"## Topic {t}. {TOPIC_NAME[t]}", "", "| Scope | Query | Count | Top titles (year, venue) |", "|---|---|---:|---|"]
        for r in [x for x in q if x["topic"] == t]:
            tops = "; ".join(f"{w['title'][:70]} ({w['year']}, {(w['journal'] or w['type'] or '')[:28]})" for w in r["top15"][:4]) or "none"
            L.append(f"| {r['scope']} | `{r['query']}` | {r['count']} | {tops} |")
        L.append("")
    L += ["## Items opened", "", "| Item | How it was read | What it does |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in OPENED]
    L += ["", "Absence wording used in the matrix: \"no journal article from 2021 onwards found in the sources checked\".", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    s = MATRIX.read_text(encoding="utf-8")
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    rows = ROWS.replace("{n_dev}", f"{R['a4.a2.reserve.n_devices']:,}").replace("{a2a}", f"{R['a4.a2.reserve.hA2a.diff'] * 100:.1f}").replace("{one}", f"{R['a4.a2.reserve.share_one_gateway'] * 100:.0f}")
    block = f"{BEGIN}\n{rows}{END}\n"
    if BEGIN in s:
        i, j = s.index(BEGIN), s.index(END) + len(END) + 1
        s = s[:i] + block + s[j:]
    else:
        # the matrix table ends with the row T3; the round-4 rows follow it as a separate small table
        key = "\n## Rows kept from the provisional C rows"
        head = "\n## Round 4 rows (A1 to A3)\n\nPreregistration `PREREGISTRATION_V15.md`; queries in `LIT_QUERIES_ROUND4.md`; items opened as listed there.\n\n| Key | Claim | Closest 2021+ journal articles opened | What they do | What this work adds | Overlap | Allowed wording | Action |\n|---|---|---|---|---|---|---|---|\n"
        s = s.replace(key, head + block + key, 1)
    MATRIX.write_text(s, encoding="utf-8")
    print("written", OUT.name, "and matrix rows")


if __name__ == "__main__":
    main()
