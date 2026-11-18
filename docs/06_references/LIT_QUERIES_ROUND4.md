# Literature queries, round 4 (A4)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Round 4 query log: three topics, OpenAlex queries for journal articles from 2021 and a context search without filters; counts, top titles and the items opened. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; DOI = digital object identifier; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; LPWAN = low-power wide-area network; LoRa = long-range radio modulation; MDPI = Multidisciplinary Digital Publishing Institute; PDF = Portable Document Format; PMC = PubMed Central |
<!-- header:end -->

Run date 2026-11-15. Database: OpenAlex API (no key, no personal detail sent). Journal scope: `from_publication_date:2021-01-01,primary_location.source.type:journal`; context scope: no filter (older and conference work). IEEE Xplore, Scopus, Google Scholar and TRID were not run.

## Topic 14. Gateway or receiver diversity, macro-diversity in LoRaWAN

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `LoRaWAN AND ("macro-diversity" OR macrodiversity OR "gateway diversity" OR "receiver diversity")` | 4 | Interference Mitigation and Decoding Through Gateway Diversity in LoRa (2022, IEEE Transactions on Wireles); Gateway-Diversity-Preserving Multi-Hop Relay With Time-Aware ACK Gatew (2026, IEEE Access); Performance of Unslotted ALOHA With Capture and Multiple Collisions in (2023, IEEE Internet of Things Jour); LoRa Channel Characterization for Flexible and High Reliability Adapti (2021, Computers) |
| context_any | `LoRaWAN AND ("macro-diversity" OR macrodiversity OR "gateway diversity" OR "receiver diversity")` | 10 | Interference Mitigation and Decoding Through Gateway Diversity in LoRa (2022, IEEE Transactions on Wireles); Fragment-Level Macro-Diversity Reception in LoRaWAN Networks with LR-F (2025, Globecom); Gateway-Diversity-Preserving Multi-Hop Relay With Time-Aware ACK Gatew (2026, IEEE Access); Experimental Multi-Gateway LoRaWAN (2026, Mendeley Data) |
| journal_2021plus | `LoRaWAN AND ("multiple gateways" OR "multi-gateway") AND (reliability OR "packet delivery")` | 10 | Improving Energy Efficiency in LoRaWAN Networks with Multiple Gateways (2023, Sensors); ReLoRaWAN: Reliable data delivery in LoRaWAN networks with multiple ga (2023, Ad Hoc Networks); A Multi-Gateway Behaviour Study for Traffic-Oriented LoRaWAN Deploymen (2022, Future Internet); Joint throughput-energy optimization in multi-gateway LoRaWAN networks (2023, Telecommunication Systems) |
| context_any | `LoRaWAN AND ("multiple gateways" OR "multi-gateway") AND (reliability OR "packet delivery")` | 29 | Improving Energy Efficiency in LoRaWAN Networks with Multiple Gateways (2023, Sensors); Adaptive algorithm for spreading factor selection in LoRaWAN networks  (2020, Computer Networks); ReLoRaWAN: Reliable data delivery in LoRaWAN networks with multiple ga (2023, Ad Hoc Networks); Adaptive Data Rate for Multiple Gateways LoRaWAN Networks (2020, IEEE International Conferenc) |
| journal_2021plus | `LoRa AND "spatial diversity" AND gateway` | 1 | Performance of Narrow Band Wide Area Networks with Gateway Diversity (2022, Sensors) |
| context_any | `LoRa AND "spatial diversity" AND gateway` | 6 | Analysis and Performance Optimization of LoRa Networks With Time and A (2018, IEEE Access); Coverage Scalability Analysis of Multi-Cell LoRa Networks (2020, International Conference on ); A Large-Scale LoRa Measurement Campaign in Urban and Suburban Environm (2026, Mendeley Data); Performance of Narrow Band Wide Area Networks with Gateway Diversity (2022, Sensors) |

## Topic 15. Short frames, payload reduction and time on air for latency

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `LoRa AND ("short frame" OR "payload size" OR "payload reduction") AND latency` | 9 | OptFiD-LoRa: Optimized Federated Learning with Differential Privacy fo (2026, IEEE Internet of Things Jour); MCST Scheme for UAV Systems over LoRa Networks (2023, Drones); ALFA: A Software Architecture for Bounded Incremental Firmware Updates (2026, IET Smart Cities); NTN-Aware Federated Learning Framework With Hierarchical Satellite Agg (2026, IEEE Open Journal of the Com) |
| context_any | `LoRa AND ("short frame" OR "payload size" OR "payload reduction") AND latency` | 14 | OptFiD-LoRa: Optimized Federated Learning with Differential Privacy fo (2026, IEEE Internet of Things Jour); MCST Scheme for UAV Systems over LoRa Networks (2023, Drones); Experimental Insights into the Performance of LoRa/LoRaWAN Radio Inter (2024, Preprints.org); ALFA: A Software Architecture for Bounded Incremental Firmware Updates (2026, IET Smart Cities) |
| journal_2021plus | `LoRa AND airtime AND ("short packet" OR "short payload") AND (emergency OR alert)` | 0 | none |
| context_any | `LoRa AND airtime AND ("short packet" OR "short payload") AND (emergency OR alert)` | 0 | none |
| journal_2021plus | `LoRaWAN AND ("preamble" OR "header") AND (overhead OR "short messages")` | 2 | Static Frequency-Based Canonical Coding as a Zero-Overhead Compression (2026, Security of Infocommunicatio); Assessing a Methodology for Evaluating the Latency of IPv6 with SCHC C (2023, Sensors) |
| context_any | `LoRaWAN AND ("preamble" OR "header") AND (overhead OR "short messages")` | 12 | Static Frequency-Based Canonical Coding as a Zero-Overhead Compression (2026, Security of Infocommunicatio); Authenticated Preambles for Denial of Service Mitigation in LPWANs (2018, Lecture notes in computer sc); Authenticated Preambles for Denial of Service Mitigation in LPWANs (2019, arXiv (Cornell University)); Impact of SCHC Compression and Fragmentation in LPWAN: A Case Study wi (2020, Sensors) |

## Topic 16. ProVerif and LoRa or LoRaWAN

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `ProVerif AND (LoRa OR LoRaWAN OR "low-power wide-area")` | 4 | Security analysis and improvement of key exchange protocol in LoRaWAN  (2025, International Journal of Sen); A Secure and LoRaWAN Compatible User Authentication Protocol for Criti (2021, IEEE Transactions on Industr); MAKA: Multi-Factor Authentication and Key Agreement Scheme for LoRa-Ba (2023, IETE Journal of Research); Secure Registration Protocol for the Internet of Drones Using Blockcha (2023, Symmetry) |
| context_any | `ProVerif AND (LoRa OR LoRaWAN OR "low-power wide-area")` | 4 | Security analysis and improvement of key exchange protocol in LoRaWAN  (2025, International Journal of Sen); A Secure and LoRaWAN Compatible User Authentication Protocol for Criti (2021, IEEE Transactions on Industr); MAKA: Multi-Factor Authentication and Key Agreement Scheme for LoRa-Ba (2023, IETE Journal of Research); Secure Registration Protocol for the Internet of Drones Using Blockcha (2023, Symmetry) |
| journal_2021plus | `LoRaWAN AND ("join procedure" OR "key derivation") AND (ProVerif OR Tamarin)` | 0 | none |
| context_any | `LoRaWAN AND ("join procedure" OR "key derivation") AND (ProVerif OR Tamarin)` | 2 | Extensive Security Verification of the LoRaWAN Key-Establishment: Inse (2020, IEEE European Symposium on S); 2020 IEEE European Symposium on Security and Privacy (EuroS&P) (2020, paratext) |

## Items opened

| Item | How it was read | What it does |
|---|---|---|
| Lanka and Kothandaraman, IEEE Access 2026, doi 10.1109/access.2026.3714528 | OpenAlex record (abstract); open access through the DOI, the IEEE Xplore page returns HTTP 418 to scripts, so the full text was not opened | Relay overlay that preserves multi-gateway observations, with a time-aware downlink ACK gateway selection; simulation with an ADR-like link model |
| Petroni and Biagi, IEEE TWC 2022, doi 10.1109/twc.2022.3172629 | OpenAlex record (abstract); not open access | Network-server combining of the same packet received by several gateways; simulation |
| Can et al., Sensors 2022, 22(22), 8831, doi 10.3390/s22228831 | Europe PMC PMC9695022 (full text opened 2026-11-15) | Coverage of LPWAN with several gateways for a packet success rate above 85%; simulation, no deadline, no acknowledgement |
| Abakar et al., Future Internet 2022, 14(11), 312, doi 10.3390/fi14110312 | OpenAlex record (abstract); open-access PDF not opened (MDPI returns HTTP 403 to scripts) | Payload length and packet delivery with several gateways and confirmed traffic; simulation |
| Lopez et al., J. Commun. Technol. Electron. 2021, doi 10.1134/s1064226921140114 | OpenAlex record (abstract); not open access | Time on air against payload size for indoor emergency use, measured; no retry or acknowledgement design |
| Wu et al., ReLoRaWAN, Ad Hoc Networks 2023, doi 10.1016/j.adhoc.2023.103203 | OpenAlex record has an empty abstract; title only, not used for any claim | Reliable delivery with several gateways (per title) |
| Amjadian et al., Int. J. Sensor Networks 2025, doi 10.1504/ijsnet.2025.149892 | OpenAlex record (abstract); not open access | Scyther and ProVerif analysis of the LoRaWAN key-exchange protocol and a proposed scheme |
| Mendeley Data 2026, doi 10.17632/5drwdxt6tr (Experimental Multi-Gateway LoRaWAN) | OpenAlex record (description); not downloaded | Six nodes and two gateways, 26,938 uplinks; too few devices for a test over devices |

Absence wording used in the matrix: "no journal article from 2021 onwards found in the sources checked".
