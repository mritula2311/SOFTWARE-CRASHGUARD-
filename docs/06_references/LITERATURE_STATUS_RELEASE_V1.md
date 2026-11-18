# Literature status

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | The release session's literature status, kept as written (superseded by LITERATURE_STATUS.md). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | DOI = digital object identifier; IEEE = Institute of Electrical and Electronics Engineers; LoRa = long-range radio modulation; OS-DR = overhear-and-suppress retries with deadlines; URL = uniform resource locator |
<!-- header:end -->

The release prompt named a file `LITERATURE_STATUS.md` as supplied with it. That file was not in the repository or the working folder, so this file was written from scratch in the release session. It lists only what this session opened. Nothing named in the release prompt but not opened here is treated as verified, and none of it is cited in the paper text.

## Opened in the release session (2026-11-14)

| Work | What was opened | URL | Used for |
|---|---|---|---|
| Tamang et al., "Fast Transmission of Massive Concurrent Alarm Messages in LoRaWAN", MSWiM 2023, DOI 10.1145/3616388.3617542 | OpenAlex record (title, authors, year, venue, DOI). The abstract and the paper were not read. | https://api.openalex.org/works?search=slotted%20concurrent%20alarms%20LoRa%20at%20least%20one%20packet | Existence and bibliographic data only. The slot-probability baseline in Block A is a re-implementation from the description in the release prompt, not from the paper. |
| Khan, Jurdak, Portmann, "A Model for Reliable Uplink Transmissions in LoRaWAN", DCOSS-IoT 2019, DOI 10.1109/dcoss.2019.00042 | OpenAlex record. The paper was not read. | https://api.openalex.org/works?search=confirmed%20uplink%20LoRaWAN%20Markov%20model%20delay%20energy | Existence only. The retry schedule of OS-DR is derived here, in the style of such models; no formula or number is taken from the paper. |
| Rafe and Das, "CHOIR: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata", arXiv 2609.11592 (submitted 10 Sep 2026, revised 1 Oct 2026) | The arXiv abstract page (title, authors, dates, the opening two abstract sentences). | https://arxiv.org/abs/2609.11592 | Prior art for conformal prediction of crash severity with coverage guarantees: no claim of novelty is made for a conformal severity interval. |

## Searched and not found (2026-11-14)

OpenAlex searches for Beltramelli et al. (slotted ALOHA and CSMA for LoRa), Jao and Shkel (accelerometer saturation restoration) and a Semtech time-on-air application note returned no matching record. They stay unverified.

## Named in the release prompt, not opened here (unverified, not cited)

Sisinni et al. (WFCS 2021; Transactions on Industrial Informatics 2022); Carneiro et al. (NOMS 2023); Wei et al. 2025 (Traffic Injury Prevention); Wesemeyer et al. 2020; Dima and Covaciu 2017; the 1975 crash-data acquisition report; the i-KAN work on over-range inertial signals; Zhang et al. 2026. The prompt also asserts corrections to earlier entries (a mis-attributed "Carvalho 2021"; a "Chen et al. GLOBECOM 2023" that was not found). Those corrections are recorded in `REFERENCES_UNVERIFIED.md` as claims of the prompt, not as facts checked here.

## Databases

IEEE Xplore was not reachable in this session; Scopus was not run by Claude (strings for the author: `SCOPUS_STRINGS.md`).
