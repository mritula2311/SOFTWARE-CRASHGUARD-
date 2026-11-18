"""Block L documents (one-off, kept for the audit trail): literature status, search strings, reference additions. Only sources opened on 2026-11-14 are listed as verified."""
from pathlib import Path

D = "2026-11-14"
Path("docs/06_references/LITERATURE_STATUS.md").write_text(f"""# Literature status

<!-- header:start -->
<!-- header:end -->

The release prompt named a file `LITERATURE_STATUS.md` as supplied with it. That file was not in the repository or the working folder, so this file was written from scratch in the release session. It lists only what this session opened. Nothing named in the release prompt but not opened here is treated as verified, and none of it is cited in the paper text.

## Opened in the release session ({D})

| Work | What was opened | URL | Used for |
|---|---|---|---|
| Tamang et al., "Fast Transmission of Massive Concurrent Alarm Messages in LoRaWAN", MSWiM 2023, DOI 10.1145/3616388.3617542 | OpenAlex record (title, authors, year, venue, DOI). The abstract and the paper were not read. | https://api.openalex.org/works?search=slotted%20concurrent%20alarms%20LoRa%20at%20least%20one%20packet | Existence and bibliographic data only. The slot-probability baseline in Block A is a re-implementation from the description in the release prompt, not from the paper. |
| Khan, Jurdak, Portmann, "A Model for Reliable Uplink Transmissions in LoRaWAN", DCOSS-IoT 2019, DOI 10.1109/dcoss.2019.00042 | OpenAlex record. The paper was not read. | https://api.openalex.org/works?search=confirmed%20uplink%20LoRaWAN%20Markov%20model%20delay%20energy | Existence only. The retry schedule of OS-DR is derived here, in the style of such models; no formula or number is taken from the paper. |
| Rafe and Das, "CHOIR: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata", arXiv 2609.11592 (submitted 10 Sep 2026, revised 1 Oct 2026) | The arXiv abstract page (title, authors, dates, the opening two abstract sentences). | https://arxiv.org/abs/2609.11592 | Prior art for conformal prediction of crash severity with coverage guarantees: no claim of novelty is made for a conformal severity interval. |

## Searched and not found ({D})

OpenAlex searches for Beltramelli et al. (slotted ALOHA and CSMA for LoRa), Jao and Shkel (accelerometer saturation restoration) and a Semtech time-on-air application note returned no matching record. They stay unverified.

## Named in the release prompt, not opened here (unverified, not cited)

Sisinni et al. (WFCS 2021; Transactions on Industrial Informatics 2022); Carneiro et al. (NOMS 2023); Wei et al. 2025 (Traffic Injury Prevention); Wesemeyer et al. 2020; Dima and Covaciu 2017; the 1975 crash-data acquisition report; the i-KAN work on over-range inertial signals; Zhang et al. 2026. The prompt also asserts corrections to earlier entries (a mis-attributed "Carvalho 2021"; a "Chen et al. GLOBECOM 2023" that was not found). Those corrections are recorded in `REFERENCES_UNVERIFIED.md` as claims of the prompt, not as facts checked here.

## Databases

IEEE Xplore was not reachable in this session; Scopus was not run by Claude (strings for the author: `SCOPUS_STRINGS.md`).
""", encoding="utf-8")

Path("docs/06_references/SCOPUS_STRINGS.md").write_text("""# Search strings for Scopus and IEEE Xplore

<!-- header:start -->
<!-- header:end -->

Scopus was not run by Claude. The strings below are for the author to run; fill the table and keep the date. Older strings with result columns are in `MANUAL_SEARCH_CHECKLIST.md`.

| Topic | Scopus string (TITLE-ABS-KEY) |
|---|---|
| Concurrent alarms over LoRa, at least one packet arrives | `(LoRa OR LoRaWAN) AND (alarm OR emergency) AND (concurrent OR burst OR simultaneous) AND (slot* OR ALOHA OR CSMA)` |
| Confirmed uplink delay and energy model | `LoRaWAN AND (confirmed OR acknowledg*) AND (Markov OR renewal OR analytical) AND (delay OR energy OR retransmission)` |
| Overhearing and suppression, deadline-aware retries | `(overhear* OR suppress*) AND (retransmission OR retry) AND (deadline OR latency) AND (LoRa OR "low power wide area")` |
| GPS-slotted or time-synchronised access for LoRa | `(GPS OR "time pulse" OR PPS) AND (slotted OR TDMA OR "time synchron*") AND LoRa` |
| Vehicle crash alert over LoRa | `(crash OR accident) AND (LoRa OR LoRaWAN) AND (alert OR notification OR emergency)` |
| Lumped-parameter crash pulse model | `("lumped parameter" OR "spring-damper" OR Kelvin) AND (crash OR collision) AND (pulse OR deceleration) AND vehicle` |
| Clipped or saturated accelerometer restoration | `(accelerometer OR "inertial sensor") AND (saturat* OR clipp* OR "over-range") AND (restor* OR reconstruct*) AND (impact OR crash)` |
| Conformal prediction for crash severity | `conformal AND (crash OR collision) AND severity` |

| Date run | Database | Topic | Count | Ten most relevant titles |
|---|---|---|---|---|
|  |  |  |  |  |
""", encoding="utf-8")


def append(path: str, text: str) -> None:
    p = Path(path)
    p.write_text(p.read_text(encoding="utf-8").rstrip("\n") + "\n" + text, encoding="utf-8")


append("docs/06_references/REFERENCES.md", f"""
## Release additions (opened {D}; metadata only unless stated)

| Work | Fields verified | Source opened | Not verified |
|---|---|---|---|
| Tamang et al., Fast Transmission of Massive Concurrent Alarm Messages in LoRaWAN, MSWiM 2023, DOI 10.1145/3616388.3617542 | title, lead author, year, venue, DOI (OpenAlex record) | https://api.openalex.org (opened {D}) | abstract and full text |
| Khan, Jurdak and Portmann, A Model for Reliable Uplink Transmissions in LoRaWAN, DCOSS-IoT 2019, DOI 10.1109/dcoss.2019.00042 | title, authors, year, venue, DOI (OpenAlex record) | https://api.openalex.org (opened {D}) | abstract and full text |
| Rafe and Das, CHOIR: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata, arXiv 2609.11592 | title, authors, dates, opening two abstract sentences | https://arxiv.org/abs/2609.11592 (opened {D}) | the paper body, its results |
""")
append("docs/06_references/REFERENCES_UNVERIFIED.md", f"""
## Release additions: named in the release prompt, not opened ({D})

| Named work | Status |
|---|---|
| Sisinni et al. (WFCS 2021; Transactions on Industrial Informatics 2022), Carneiro et al. (NOMS 2023), Wei et al. 2025, Wesemeyer et al. 2020, Dima and Covaciu 2017, a 1975 crash-data acquisition report, i-KAN over-range inertial signals, Zhang et al. 2026, Beltramelli et al., Jao and Shkel 2022, a Semtech time-on-air note | not opened in this session; not cited in the paper text; the corrections to earlier entries that the prompt asserts are claims of the prompt, not checked here |
""")
append("docs/06_references/NOVELTY_SCAN.md", f"""
## Release scope ({D}); wording: "no study found in the sources checked"

| Point | Sources actually opened | Closest prior work | Scope of any claim |
|---|---|---|---|
| Conformal severity interval | arXiv 2609.11592 abstract | CHOIR (Rafe and Das) | No novelty claim: conformal severity prediction with coverage guarantees is prior art |
| Physics-based pulse generator checked against real data by a discriminator | no new source opened | not searched beyond the repository's references | No claim; the generators fail the realism gate (`docs/03_results/PH_INTEGRITY_REPORT.md`) |
| Overhear-and-suppress retries, GPS-slotted critical alerts | OpenAlex records of Tamang et al. and Khan et al. (metadata only) | Tamang et al. (slotted concurrent alarms), Khan et al. (confirmed-uplink model) | No claim: both candidates are negative results under the stated assumptions |
| Retry-schedule formula | none | | Reported as an approximation that overestimates collisions (`pa.analytic.*`) |
""")

s = Path("scripts/doc_meta.py").read_text(encoding="utf-8")
s = s.replace('    "docs/06_references/NOVELTY_SCAN.md"', '    "docs/06_references/LITERATURE_STATUS.md": "What the release session opened (URL and date), what was searched and not found, and what stays unverified.",\n    "docs/06_references/SCOPUS_STRINGS.md": "Search strings for the author to run in Scopus, with an empty results table (Scopus was not run by Claude).",\n    "docs/06_references/NOVELTY_SCAN.md"', 1)
Path("scripts/doc_meta.py").write_text(s, encoding="utf-8")
print("ok")
