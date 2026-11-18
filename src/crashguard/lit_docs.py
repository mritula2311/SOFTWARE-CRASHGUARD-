"""Part A: write docs/06_references/LIT_QUERIES_2021PLUS.md from results/tables/lit_queries.json.

Every number in the document comes from the stored query log. The `OPENED` table lists what was read:
an OpenAlex record with its abstract (read through the API on 2026-11-14) is an abstract-level read; no
full text of any item below was read in this run unless the Note says so.
"""
from __future__ import annotations

import json

from crashguard.lit_search import ROOT
from crashguard.results import record_many

TOPIC_NAMES = {
    1: "LoRa or LPWAN crash or accident alerting",
    2: "Severity-aware or deadline-aware retransmission and scheduling for critical LoRa traffic",
    3: "Two-stage, provisional or early crash notification; eCall and next-generation eCall",
    4: "Authenticated alert and ACK protocols for LoRa or LoRaWAN; replay protection; per-device keys",
    5: "Formal verification of LoRa or LoRaWAN protocols, including timing",
    6: "Overhearing, cooperative suppression or aggregated ACKs in LPWAN",
    7: "Trace-driven or measurement-based evaluation of LoRaWAN MAC policies; LoED and other datasets",
    8: "Simulator validation for LoRa (ns-3, FLoRa, LoRaSim) against measurements",
    9: "Accelerometer range, sampling rate and saturation in crash or impact sensing; delta-V",
    10: "Dataset leakage, duplicates and validation-split problems in sensor-based detection benchmarks",
    11: "Compact or embedded crash detectors (tree models, TinyML)",
    12: "Synthetic crash pulse generation and physics-based crash models",
    13: "Energy budget or survivability of IoT nodes after power loss",
}

# (OpenAlex id, topics, note)  -- abstract read through the OpenAlex API on 2026-11-14
OPENED = [
    ("W4389870150", "1", "Vinodhini et al., IJCS 2023. LoRa accident detection with ultrasonic edge nodes, GPS LoRa shield, cloud, hospital notification."),
    ("W4412036200", "1", "IJACSA 2025. Accident detection with ML, IoT drones and LoRa."),
    ("W4409590986", "1", "J. Electron. Autom. Eng. 2025. Arduino LoRa vehicle coordination with ultrasonic sensors."),
    ("W4413056091", "1", "Zhang et al., Sci. Rep. 2025. IoT public-safety alert system (ESP32, cloud); LoRa not the focus."),
    ("W3199272654", "2", "IEEE Commun. Lett. 2021. Bidirectional LoRa: ACK collisions, maximum retransmissions as the critical parameter."),
    ("W4394689617", "2", "Sci. Rep. 2024. Single-channel LoRa gateway for rapid confirmed messaging (emergency alerting named as the target)."),
    ("W4313591022", "2", "IEEE Access 2023. Delay optimisation by adaptive scheduling with unsupervised learning."),
    ("W4403835654", "2", "Mathematics 2024. ADR for power-constrained LoRa devices."),
    ("W3210114490", "2, 6", "Sisinni et al., IEEE TII 2022 (online 2021-11-02). Redundancy for LoRaWAN emergency communication on the factory floor."),
    ("W4390277924", "2", "Zorbas, Comput. Commun. 2023. Downlink SF selection. The record has no abstract: title and metadata only."),
    ("W4327779085", "2", "Farhad et al., CCNC 2023 (conference; context)."),
    ("W4414155287", "2", "Alshaer et al., IEEE IoT J. 2025. Enhanced ADR and power control."),
    ("W4243199167", "3", "IJVSS 2021. Prediction of occupant injuries for eCall (simulation model, injury pattern and severity in an automated call)."),
    ("W4220716409", "3", "IEEE ITS Mag. 2022. eCall system with injury severity, installed in service vehicles."),
    ("W7165046622", "3", "Transp. Res. Interdiscip. Perspect. 2026. GIDAS logistic regression for injury patterns for next-generation eCall."),
    ("W4221066772", "3", "Acad. Pediatr. 2022. Advanced ACN for children. The record has no abstract: title and metadata only."),
    ("W4301595718", "3", "SAE 2022-28-0399 (SAE technical paper). Motorcycle crash severity estimation for emergency response."),
    ("W4412747859", "4, 5", "IEEE IoT J. 2025. Privacy-preserving lightweight LoRaWAN authentication."),
    ("W4292348028", "4", "IEEE Access 2022. LoRaWAN session key update scheme (unique key per session)."),
    ("W3197586672", "4", "Sensors 2021. Hash-chain key management for LoRaWAN."),
    ("W3157897910", "4, 5", "IEEE TII 2021. LoRaWAN-compatible user authentication for critical applications."),
    ("W4416313224", "5", "Int. J. Sens. Netw. 2025. Security analysis and improvement of the LoRaWAN key exchange."),
    ("W4382699871", "5", "IETE J. Res. 2023. MAKA, multi-factor authentication and key agreement for LoRa smart grid."),
    ("W4396842943", "5", "Performance Evaluation 2024. Probabilistic evaluation of class-A LoRaWAN. The record has no abstract: title and metadata only."),
    ("W3131690400", "6", "Sensors 2021. DG-LoRa: deterministic group acknowledgment in LoRa networks."),
    ("W4401611171", "6", "FUOYE J. Eng. Technol. 2024. Fairness of current use in time-slotted LoRa."),
    ("W7224295386", "7", "J. Telecommun. Inf. Technol. 2026. Gateway-level early warning of link degradation, built on LoED records."),
    ("W7223685629", "7", "IEEE Access 2026. Data quality and missing data in LoRaWAN environmental IoT (frame-counter anomalies named)."),
    ("W4281756149", "7", "Int. J. Eng. Trends Technol. 2022, a different 'LoED' (forest monitoring system). Not the Imperial dataset. No abstract in the record."),
    ("W4288786426", "8", "Citoni et al., IEEE Sensors J. 2022. Urban LoRaWAN deployment, real world against simulation."),
    ("W3043344477", "8", "Magrin et al., IEEE TWC 2021. Configurable mathematical model for single-gateway LoRaWAN."),
    ("W4410091983", "8", "Technol. Eng. 2025. FLoRa simulator compared with measurements."),
    ("W4408215394", "8", "Sensors 2025. Mesh-topology LoRa network."),
    ("W7204150407", "9", "PEAR-VAE, IEEE Sensors J. 2026. Saturation compensation of low-range accelerometers in impact windows."),
    ("W4381465825", "9", "Chan et al., Sensors 2023. Spline restoration of clipped tibial acceleration."),
    ("W3207999649", "9", "Traffic Inj. Prev. 2021. Delta-v slope as an injury indicator (CIREN, EDR)."),
    ("W3125792140", "9", "SAE technical paper 2021. Reconstructing vehicle motion from EDR delta-v in high-yaw crashes."),
    ("W7167712123", "9", "IJLTEMAS 2026. Direction-aware telematics crash detection."),
    ("W7214642774", "10", "Mach. Learn. Knowl. Extr. 2026. Leakage, attribution and calibration audit in fall-detection benchmarks."),
    ("W7221480893", "10", "Measurement 2026. User-independent pre-impact fall detection on KFall, with leakage prevention."),
    ("W4405078322", "10", "Algorithms 2024. HAR validation methods (subject-dependent k-fold against leave-one-subject-out)."),
    ("W7219830528", "10", "Sci. Rep. 2026. Calibrated, leakage-aware crash severity stacking (tabular crash records)."),
    ("W4200514941", "11", "CMC 2021. TinyML fall detection for personal mobility vehicles."),
    ("W7160417041", "11", "IJCOR 2026. ESP32 and MPU6050 TinyML accident detection."),
    ("W3159454463", "12", "Accid. Anal. Prev. 2021. Kinematic-feature injury-severity algorithm. The record has no abstract: title and metadata only."),
    ("W4385230230", "12", "J. Biomech. Eng. 2023. Lightweight pre-crash injury prediction by knowledge distillation."),
    ("W7161695129", "13", "Pantao 2026. Disaster detector with a 12 V backup supply; not an energy-survivability study."),
]


def main() -> None:
    rows = json.loads((ROOT / "results" / "tables" / "lit_queries.json").read_text(encoding="utf-8"))
    L = ["# Literature queries, journal articles from 2021 (Part A)", "",
         "Run date 2026-11-14. Database: OpenAlex API (no key, no personal detail sent; the key request in the service notice was ignored). "
         "Filters: `from_publication_date:2021-01-01,primary_location.source.type:journal`; field `title_and_abstract.search`; "
         "at most 5 boolean operators per query; 1 s between queries; results sorted by relevance (the service default for a search). "
         "The same queries can be rerun with `python -m crashguard.lit_search run` (counts change as the index changes). "
         "Raw log: `results/tables/lit_queries.json`.", "",
         "**Not run.** Scopus, Google Scholar and TRID are not available to this run. IEEE Xplore (Journals, 2021 to 2026): the search page "
         "returned HTTP 418 to a scripted request, so the Xplore query set is NOT_RUN here; it was not bypassed. Crossref was used for metadata only "
         "(`results/tables/lit_crossref.json`, 51 of 51 DOIs found). OpenAlex source type `journal` includes some SAE technical papers and "
         "low-tier outlets; those are marked in the notes.", ""]
    for t, name in TOPIC_NAMES.items():
        L += [f"## Topic {t}. {name}", "", "| # | Query | Count |", "|---|---|---|"]
        qs = [r for r in rows if r["topic"] == t]
        for i, r in enumerate(qs, 1):
            L.append(f"| {i} | `{r['query']}` | {r['count'] if r['status'] == 'OK' else 'NOT_RUN'} |")
        L.append("")
        for i, r in enumerate(qs, 1):
            L += [f"Query {i}, top {len(r['top15'])} by relevance (year, journal, DOI):", ""]
            for w in r["top15"]:
                doi = (w["doi"] or "no DOI").replace("https://doi.org/", "")
                L.append(f"- {w['year']}, {w['journal'] or 'unknown'}, {doi}: `{w['title']}`")
            L.append("")
    L += ["## Items opened (abstract level, OpenAlex record, 2026-11-14)", "",
          "URL form: `https://api.openalex.org/works/<id>` (read 2026-11-14); the DOI of each item is in `docs/06_references/REFERENCES_2021PLUS.bib` "
          "(metadata from Crossref). No full text was read in this run; \"abstract level\" means the abstract in the record. A record with no abstract "
          "is title-and-metadata only and stays UNVERIFIED for content.", "",
          "| OpenAlex id | Topics | What the record says |", "|---|---|---|"]
    for i, tp, note in OPENED:
        L.append(f"| {i} | {tp} | {note} |")
    L.append("")
    (ROOT / "docs" / "06_references" / "LIT_QUERIES_2021PLUS.md").write_text("\n".join(L), encoding="utf-8")
    cr = json.loads((ROOT / "results" / "tables" / "lit_crossref.json").read_text(encoding="utf-8"))
    src = "src/crashguard/lit_docs.py"
    ok = [r for r in rows if r["status"] == "OK"]
    ent = [
        dict(name="lit.queries.n", value=len(rows), unit="queries", origin="MEASURED_SOFTWARE", source_file=src, notes="OpenAlex queries run on 2026-11-14, journal articles from 2021-01-01"),
        dict(name="lit.queries.ok", value=len(ok), unit="queries", origin="MEASURED_SOFTWARE", source_file=src, notes="queries that returned a result list"),
        dict(name="lit.opened.n", value=len(OPENED), unit="records", origin="MEASURED_SOFTWARE", source_file=src, notes="OpenAlex records read at abstract level (some have no abstract)"),
        dict(name="lit.crossref.found", value=sum(1 for m in cr.values() if m["status"] == "OK"), unit="DOIs", origin="MEASURED_SOFTWARE", source_file=src, notes=f"of {len(cr)} DOIs checked in Crossref"),
        dict(name="lit.xplore.status", value="NOT_RUN", unit="status", origin="NOT_RUN", source_file=src, notes="IEEE Xplore returned HTTP 418 to a scripted request and was not bypassed"),
        dict(name="lit.scopus_scholar_trid.status", value="NOT_RUN", unit="status", origin="NOT_RUN", source_file=src, notes="not available to this run"),
    ]
    record_many(ent, purge_prefixes=("lit.",))


if __name__ == "__main__":
    main()
