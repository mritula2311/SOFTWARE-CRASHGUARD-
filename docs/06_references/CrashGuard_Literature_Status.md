# CrashGuard: literature status (checked 2026-11-13)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Literature status of 2026-11-13 to 2026-11-14 as supplied: opened items, searches, prior-art checks. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; ASI = acceleration severity index; DOI = digital object identifier; ESV = Enhanced Safety of Vehicles (conference); GPS = Global Positioning System; HIC = head injury criterion; HMAC = hash-based message authentication code; IEEE = Institute of Electrical and Electronics Engineers; IMU = inertial measurement unit; IOP = Institute of Physics; LPWAN = low-power wide-area network; LoRa = long-range radio modulation; MAC = message authentication code; ML = machine learning; NCAP = New Car Assessment Programme; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; SAE = Society of Automotive Engineers; V2V = vehicle-to-vehicle |
<!-- header:end -->

How this was made: web searches and page fetches from a cloud session. A page counts as OPENED only if its content was read in this session. IEEE Xplore was searched on 2026-11-13 in the user's Chrome (section 5). Scopus needs a login and was not run. Crossref and OpenAlex API calls, ResearchGate, HAL and X-MOL pages were blocked, so some fields below are unverified. Nothing here is a claim that prior work is absent.

## 1. Opened and verified (cite these; fields as read)

| Short name | Fields read | Used for | Notes |
|---|---|---|---|
| Wusk and Gabler, NHTSA ESV 25-0407 (nrd.nhtsa.gov PDF) | Virginia Tech; 140 frontal NCAP tests at about 56 km/h; delta-V, OLC, ASI against HIC, chest and pelvis criteria; R squared 0.006 to 0.056 | X5, injury-criteria caveat | Year and DOI not read; authors' given names not read |
| US 7,643,921 (Continental Automotive Systems) | Inventors Andres and McConnell; granted 2010-01-05; filed 2005-08-26; claim 1: estimated slope below 100% of actual slope beyond the sensor limit | Clipping restoration prior art | Not a lower-bound constraint |
| Sechaud, Jacques, Abry, Tachella, arXiv 2602.22279 (Feb 2026) | Self-supervised reconstruction from saturated data, audio declipping and HDR images | General saturation-reconstruction prior art | Not accelerometers or crashes |
| HEROS-GAN, arXiv 2502.18064 | Extends 8 g to 16 g range of smartphone accelerometers; LASED shaking dataset; no crash or delta-V | Range-extension prior art | Authors and date not read |
| Evaluation of a restoration algorithm applied to clipped tibial acceleration signals (Sensors, May 2023; DOAJ record) | Spline restoration of clipped signals from a plus-minus 16 g sensor against a plus-minus 200 g reference; peak differences about -1.4 g | Spline baseline prior art | Authors not read |
| Stitzel et al., ESV paper 17-0319 (nrd.nhtsa.gov PDF 25ESV-000319) | Wake Forest; OTDA advanced automatic crash notification; inputs delta-V (longitudinal and lateral), rollover quarter turns, belt, airbags; 38,970 NASS-CDS occupants 2000 to 2011; undertriage 20% to 11%, overtriage 54% to 34% nationwide estimate | Application context for severity-based notification | Cite as the ESV paper; year from paper number, confirm |
| Sisinni, Bellagente, Depari, Carvalho, Flammini, Pasetti, Rinaldi, Ferrari, "Investigating redundancy of LoRaWAN for emergency notifications in industrial plants", IEEE WFCS 2021, pp. 15 to 18, DOI 10.1109/WFCS46889.2021.9483609 (IRIS Brescia record) | Title, authors, venue, pages, DOI | LoRaWAN emergency redundancy | Abstract not read. This is what was cited as "Carvalho 2021": Carvalho is a co-author, not lead author |
| Dong, Zhu, Chen, Ge, "A Security Verification Framework for the LoRaWAN Protocol with Application in the Manufacturing Industry", ISSRE 2024, pp. 535 to 546, DOI 10.1109/ISSRE62328.2024.00057 (ECNU record) | CSP models in PAT; replay, DoS, ACK spoofing, bit flipping and man-in-the-middle attacks | LoRaWAN formal verification | This is the closest match to "Chen et al. GLOBECOM 2023", which was NOT found |
| "Extensive Security Verification of the LoRaWAN Key-Establishment: Insecurities & Patches", IEEE EuroS&P 2020, DOI 10.1109/EuroSP48549.2020.00034 (REF 2021 record) | Title, venue, year, DOI, theorem-proving of the JOIN procedure | LoRaWAN formal verification | Author list not shown on the page; the "Wesemeyer 2020" attribution is unconfirmed |
| Tamang, Heusse, Abrardo, Duda, "Fast Transmission of Massive Concurrent Alarm Messages in LoRaWAN", ACM MSWiM 2023 | Slotted one-packet-per-node alarm delivery, optimised slot probabilities, goal at least one packet received within 500 ms, SF7 to SF10, simulation only | Closest prior art for burst alarm access | Re-implement only as a clearly labelled baseline |
| Beltramelli, Mahmood, Osterberg, Gidlund, "LoRa beyond ALOHA", arXiv 2002.10732 | Slotted ALOHA and non-persistent CSMA against ALOHA; capture effect helps at high density; no emergency traffic | MAC baselines | Date not read |
| Beltramelli, Mahmood, Osterberg, Gidlund, Ferrari, Sisinni, "Energy efficiency of slotted LoRaWAN communication with out-of-band synchronization", arXiv 2012.07579 | FM-RDS synchronised slotted LoRaWAN; no alarm traffic | Slotted MAC prior art | Date not read |
| Khan, Jurdak, Portmann, "A Model for Reliable Uplink Transmissions in LoRaWAN", DCOSS 2019 (arXiv 2009.09397) | Markov model of confirmed uplink delay and energy, RX1 and RX2 ACK behaviour, duty limits | Analytical baseline for retry design | Year from proceedings text |
| Liu, Fan, Xiang, Yang, "Low-cost Parallel Transmission for Dense Indoor Data Collection with LoRaWAN", arXiv 2605.23588 (2026) | TDMA overlay with out-of-band beacons, static priorities; 20-node testbed, delivery 74.17% to 94.98%; ACKs and retransmissions disabled | Slotted MAC prior art | Publication date not read |
| Loh, Raffeck, Metzger, Hossfeld, "Improving LoRaWAN's Successful Information Transmission Rate with Redundancy", WiMob 2021, pp. 313 to 318 (Crossref record) | Title, authors, venue, pages, DOI 10.1109/wimob52687.2021.9606388 | LoRaWAN redundancy | Not emergency-specific |
| Kmec, Pavelka, Soltes, "Modeling and Analysis of a Vehicle Dynamics at Frontal Impact into the Rigid Barrier Using a System Identification Toolbox", MM Science Journal, June 2021, DOI 10.17973/MMSJ.2021_6_2021013 | Kelvin (spring-mass-damper) model fitted to a 56.17 km/h NCAP test | Physics basis for synthetic pulses | The reported stiffness and damping units look inconsistent for a crash; do not reuse the numbers |
| Jao and Shkel, IEEE Sensors J. 22(1), pp. 695 to 706, 2022, DOI 10.1109/JSEN.2021.3130120 (Xplore document 9624969) | Triangle approximation with Gaussian-process regression, foot-mounted IMU | Saturation reconstruction prior art (N14, X6) | Opened on Xplore 2026-11-13; keep clipping claims narrow |
| Zhang et al., IEEE Sensors J. 26(19), pp. 29298 to 29306, 2026, DOI 10.1109/JSEN.2026.3724900 (Xplore document 11664249) | PEAR-VAE for saturation compensation in rail-impact windows | Saturation reconstruction prior art (N14, X6) | Opened on Xplore 2026-11-13; given names not recorded |
| Sisinni, Carvalho, Ferrari, Flammini, Gidlund, "Adding Redundancy to LoRaWAN for Emergency Communications at the Factory Floor", IEEE Trans. Industrial Informatics 18(10), 2022 | Authors, title, venue, volume and issue from the Xplore results list | LoRaWAN emergency redundancy | Abstract, pages and DOI not read |
| Carneiro, Batista, Hirata Junior, Ullah, "A Crash Response System using LoRa-based V2X Communications", IEEE/IFIP NOMS 2023 | Authors, title, venue from the Xplore results list | Closest LoRa crash-response prior art | Abstract not read; open before citing |
| Wesemeyer, Boureanu, Smith, Treharne, EuroS&P 2020 | Author list now read on Xplore | Replaces "Wesemeyer 2020" uncertainty | Confirmed 2026-11-13 |

## 2. Not found, not opened, or mis-attributed

| Item | Status |
|---|---|
| Jao and Shkel 2022 | NOW VERIFIED, see section 1. Do not cite the Multibody System Dynamics paper (Neurauter) for saturation |
| Zhang et al. 2026 | NOW VERIFIED, see section 1. i-KAN and MoE-Gyro (arXiv 2506.06318) remain unopened and UNVERIFIED |
| CHOIR, arXiv 2609.11592 | NOW VERIFIED through the OpenAlex record and abstract (section 6). The TRID record is Wei et al. 2025, also verified there |
| "Chen et al. GLOBECOM 2023" LoRaWAN verification | NOT FOUND. Use Dong et al. ISSRE 2024 (above) only if it is the intended work; otherwise remove |
| "Wesemeyer 2020" | Authors confirmed on Xplore (Wesemeyer, Boureanu, Smith, Treharne) |
| "Carvalho 2021" | Replace by Sisinni et al. WFCS 2021 and Sisinni et al. TII 2022 (section 1). The IoT Journal "Transparent LoRaWAN Enhancement" article remains UNVERIFIED |
| Semtech time-on-air application note | Could not be opened in the finishing run; no Semtech number may be cited |
| nhtsa.gov terms of use | Returned 403; data.gov entry states "public" |

## 3. What the scan says about each novelty point (provisional)

- Sensor range requirement on real crash pulses (N13): no study found that measures range and rate requirements on real crash-test pulses. Related: HEROS-GAN, the tibial restoration study, Sechaud et al., US 7,643,921. Absence is not established; the Scopus and IEEE Xplore runs are still needed.
- Clipping restoration (N14): spline, slope extrapolation and learned reconstruction exist. Keep it a narrow evaluation, not a method claim.
- Delta-V and severity against injury criteria: Wusk and Gabler found weak links in frontal NCAP tests, so avoid injury-prediction claims.
- Severity-based notification as a use case: Stitzel et al. (OTDA) uses delta-V inputs and triage metrics. The alert-transport side is separate.
- LoRa alarm delivery: Tamang et al. (concurrent alarms, optimised slotted access), Sisinni et al. (redundancy for emergencies), Beltramelli et al. (slotted ALOHA, CSMA), Khan et al. (reliable uplink model). A severity-classed fast path with duty-reserved airtime is not what these study, but each is a baseline family to compare with.
- LoRaWAN formal verification: Dong et al. (CSP and PAT), the EuroS&P 2020 verification work. Our bounded check covers a different, small alert protocol.
- Dataset duplicate leakage: general leakage literature exists (one 2026 arXiv paper on sensor-AI evaluation under distribution shift, arXiv 2609.09257, appeared in search and was not opened). The VZCrash audit itself is verified by the authors' reply.

## 4. Scopus and IEEE Xplore strings for the user to run (title, abstract, keywords)

1. `("crash" OR "collision" OR "accident") AND ("accelerometer" OR "IMU") AND ("saturat*" OR "clipp*" OR "measurement range" OR "full-scale range") AND ("delta-V" OR "severity")`
2. `("LoRa" OR "LoRaWAN") AND ("accident" OR "crash" OR "emergency" OR "alarm") AND ("priority" OR "severity" OR "deadline" OR "latency")`
3. `("conformal prediction") AND ("crash" OR "accident" OR "injury") AND ("severity")`
4. `("near-duplicate" OR "data leakage" OR "duplicate") AND ("accelerometer" OR "crash detection" OR "time series") AND ("benchmark" OR "dataset")`
5. `("LoRaWAN") AND ("formal verification" OR "model checking" OR "bounded") AND ("acknowledg*" OR "replay" OR "counter")`
6. `("vehicle crash" OR "frontal impact") AND ("lumped parameter" OR "spring-mass" OR "Kelvin") AND ("pulse" OR "deceleration")`

Record for each: date run, database, result count, and the titles of the ten most relevant results. Paste them back for review. Do not cite a result you have not opened.

## 5. IEEE Xplore results (run 2026-11-13, simple search, no login; Scopus NOT run)

Xplore simple search is strict AND, so long strings return nothing. Short forms were used. Counts are as displayed; titles are from the results list only (abstracts not read unless stated).

| Query | Count | Relevant titles |
|---|---|---|
| accelerometer saturation crash | 1 | None relevant (LoRa WAN mining unsafe-event ML, ICCES 2024) |
| crash pulse clipping accelerometer | 0 | none |
| crash pulse delta-V | 3 | None on sensor range; IEEE Std 1616-2004 MVEDR (event data recorder standard) is a relevant reference for crash-data recording |
| crash LoRa V2X | 3 | Carneiro et al. NOMS 2023; Velvizhi et al. ICCCT 2021 (two vehicles over LoRa); Minhas et al. IEEE Access 2026, "Toward the Design and Development of Intelligent Transportation Devices" (unopened) |
| LoRa accident severity priority | 0 | none |
| conformal crash severity | 1 | None relevant (antenna paper) |
| LoRaWAN formal verification | 11 | Dong et al. ISSRE 2024; Wesemeyer et al. EuroS&P 2020; Mostefa et al., "Formal Validation of ADR Protocol in LoraWan Network Using Event-b", ICCSM 2023 (new, unopened); Avoine, Claverie, Delaune, CSF 2025 (nonce misuse, not LoRaWAN-specific); several key-management and authentication papers |
| crash detection data leakage | 47 | None on dataset leakage in crash or accelerometer benchmarks (results are security and software topics) |
| near-duplicate accelerometer benchmark | 0 | none |
| lumped parameter crash pulse | 0 | none |
| redundancy LoRaWAN emergency factory | 2 | Sisinni et al. WFCS 2021; Sisinni et al. TII 2022 |

Reading of the Xplore run: no Xplore record addresses sensor range or clipping requirements from real crash pulses, duplicate leakage in crash-detection benchmarks, conformal severity-to-LoRa-class mapping, or lumped-parameter synthetic crash pulses. Because the strict-AND search returned zero for several topical phrases, this is weak evidence of absence, not proof. Still to do: Scopus (login required), Google Scholar, and TRID for the non-IEEE crash literature (SAE, ESV, Accident Analysis and Prevention).

New items to open before citing: Carneiro NOMS 2023, Sisinni TII 2022 (abstract), Mostefa ICCSM 2023, Minhas IEEE Access 2026, IEEE Std 1616-2004. Marciano et al. 2024 ("Improving Safety Roads with LoRa Communication Devices: Features and Limitations") was seen earlier and not opened.

## 6. Open-index search (OpenAlex API read in Chrome, run 2026-11-13; no login; replaces Scopus for now)

OpenAlex indexes titles, abstracts and full text from many publishers and repositories, including open-access material. It is not Scopus: coverage and ranking differ. Records below were read as OpenAlex JSON (authors, venue, date, abstract); the papers themselves were not opened.

| Topic query | Count | Closest results |
|---|---|---|
| crash accelerometer saturation clipping delta-V | 7 | None relevant |
| crash pulse accelerometer measurement range requirement | 1,714 | Dima and Covaciu, "Solutions for acceleration measurement in vehicle crash tests", IOP Conf. Series: Materials Science and Engineering 252, 2017 (DOI 10.1088/1757-899x/252/1/012007; open access; abstract: two accelerometers with different input ranges, 32-bit microcontroller logger, filter recommendations from standards); "Analysis of automobile crash test data and recommendations for acquiring and filtering accelerometer data" (1975, no DOI listed); Can Machine Learning beat Physics at Modeling Car Crashes? (2018, DOI 10.21427/d74f8z). Neither opened |
| data leakage duplicate crash detection benchmark | 1,283 | No crash-sensor benchmark audit found. Analogue in another domain: "Train-Test Leakage in Pothole Detection Benchmarks: Evidence from a Video-Disjoint Re-Split of BharatPotHole" (2026, preprint, DOI 10.21203/rs.3.rs-11338135/v1) |
| conformal prediction crash severity | 3,878 | CHOIR, Rafe and Das (Texas State), arXiv 2609.11592, 2026-09-10: groupwise and weighted conformal prediction with risk control for KABCO severity, 4.04 million Texas crashes; Wei, Miyazaki, Sato, "Pre-crash injury risk prediction with guaranteed confidence level: a conformal and interpretable framework", Traffic Injury Prevention, 2025-08-19, DOI 10.1080/15389588.2025.2538725 (conformal sets at 90% coverage, NASS-CDS and CISS pre-crash factors) |
| LoRa crash alert severity latency deadline | 2 | None relevant |
| lumped-parameter vehicle crash pulse synthetic Kelvin | 7 | None relevant |

Consequences for claims:
- Conformal prediction for crash severity exists (CHOIR; Wei et al. 2025), on tabular crash records. Do not claim conformal severity prediction as new. What stays distinct, in the sources checked, is conformal intervals computed from crash-pulse features and mapped to a LoRa alert class under an airtime budget. Cite both and state the difference.
- Crash-test accelerometer range and acquisition guidance exists (Dima and Covaciu 2017; the 1975 report; the SAE J211 lineage, which was not opened). The range-requirement result must be framed as a quantification on a public pulse set, not as an initial look at range. Cite these.
- In the sources checked (IEEE Xplore, OpenAlex), no crash-sensor benchmark duplicate audit was found; the nearest are leakage audits in other detection benchmarks. Word it as "no study found in the sources checked".
- Scopus, Google Scholar and TRID were not run. Do not write that absence is established.

## 7. Google Scholar attempt and second open-index pass (2026-11-13)

Google Scholar returned its automated-query block ("Sorry..." page) on all four queries from the user's Chrome. It was not bypassed, so Google Scholar was NOT searched. Instead OpenAlex was re-queried with fielded title-and-abstract filters, and Crossref was tried once (its relevance ranking returned book chapters only). Titles are from result lists; none opened.

| Query (title and abstract) | Count | Relevant titles |
|---|---|---|
| crash AND (clipping OR saturation OR "measurement range") | 619 | None relevant (newspaper clippings, epidemiology) |
| LoRa AND (crash OR accident) AND (severity OR priority OR airtime) | 15 | None on crash alerting with severity classes. Nearest: "LoRaLife: Seamless Traffic Clearance System for Emergency Response" (2026, DOI 10.22214/ijraset.2026.82446), "Smart Traffic Management for Emergency and VIP Vehicles" (2025) |
| (duplicate OR near-duplicate OR leakage) AND (accelerometer OR crash detection OR fall detection) AND (benchmark OR split) | 32 | "Auditing Multimodal Fusion Benchmarks: Leakage, Attribution, and Calibration in Elderly Fall Detection", Machine Learning and Knowledge Extraction 2026, DOI 10.3390/make8100298 (closest analogue: a leakage audit of a sensor benchmark in a neighbouring task); "Evaluating pre-impact fall detection: A user-independent assessment ... KFall", Measurement 2026, DOI 10.1016/j.measurement.2026.123369; GroupKFold study on bearing faults, 2026 |
| ("crash pulse" OR "crash pulses") AND (synthetic OR generator OR lumped OR delta-V) | 70 | "Modeling of a Rear-End Crash Pulse Generator" (Advanced Materials Research 630, 2012, DOI 10.4028/www.scientific.net/amr.630.360); "Crash pulse recorder - validation in full scale crash tests" (Accident Analysis and Prevention, 1995, DOI 10.1016/0001-4575(95)00025-u); "Crash Pulse Recorder (CPR): development and evaluation of a low cost device for measuring crash pulse and delta-V in real life accidents" (1991); "Comparison of Crash Pulse Data from Motor Vehicle Event Data Recorders and Laboratory Instrumentation" (2004); "Influence of Crash Pulse Characteristics on Injury Risk in Frontal Impacts Based on Real-Life Crashes" (Traffic Injury Prevention 2010, DOI 10.1080/15389588.2010.492053); "Optimal Crash Pulse for Minimization of Peak Occupant Deceleration in Frontal Impact" (SAE 2006-01-0670) |

Consequences:
- Crash pulse generators and low-cost delta-V recorders exist in the older literature (a 2012 rear-end pulse generator; 1990s pulse recorders). The physics-generator claim must be limited to "stated-assumption lumped-parameter pulses validated against NHTSA test pulses" and must cite these.
- Benchmark leakage audits exist for neighbouring sensor tasks (fall detection, pothole detection). The VZCrash audit stays a data-quality finding on one named dataset, not a new method.
- No source found so far addresses a LoRa crash alert with severity classes and an airtime budget beyond the Carneiro 2023 and Marciano 2024 crash-response papers.
- Open before citing: the 2012 generator paper, the 1995 pulse recorder validation, and the fall-detection leakage audit.

## 8. Prior-art check for architecture and protocol-layer candidates (OpenAlex and IEEE Xplore, run 2026-11-14; titles from result lists, none opened)

| Candidate | Query focus | Count | Closest results | Reading |
|---|---|---|---|---|
| Reboot-resilient freshness (GPS-time or timestamp instead of a persisted counter) | replay protection with timestamp, counter or nonce in LoRa or low-power networks | 5 (OpenAlex) | "Timestamp Scheme to Mitigate Replay Attacks in Secure ZigBee Networks", IEEE TMC 2020 (DOI 10.1109/tmc.2020.3006905) and its 2019 conference version; "An Investigation of a Replay Attack on LoRaWAN Wearable Devices", Perkovic et al., MeditCom 2023 (Xplore) | Timestamp replay protection exists for ZigBee; a LoRaWAN replay attack paper exists. No crash-alert or reboot-availability study found. Concept is not new; the quantified trade-off in this setting may be |
| Tag length, payload and airtime for emergency alerts | truncated MAC with LoRa airtime or payload | 4 | "FC-HMAC: Fragment-Chained HMAC ... for Duty-Cycled LoRa Fragmented Payloads", Zenodo 2026 (DOI 10.5281/zenodo.20515930) | Related MAC-on-LoRa work on fragmented payloads; no study found on tag length against burst collisions for single-packet alerts |
| Two-stage (provisional then refined) crash alert | provisional, progressive or two-stage with crash and cancel or update | 25 | None on crash alerts. Hits were accident prediction and smartphone alert systems | No crash-alert design of this kind found in the sources checked |
| LoRa burst of concurrent alarms | LoRa, alarm, burst or concurrent | 5 | LoRaSense (2019); Tamang et al. MSWiM 2023 (already listed) | Tamang et al. remains the closest |
| eCall or minimum set of data over LoRa | automatic crash notification, eCall, MSD with LoRa or LPWAN | 1 (irrelevant) | None | No LoRa eCall-style minimum-data work found; do not claim absence |
| LoRa crash alerting with authentication | LoRa with HMAC, authentication or secure, and crash or accident | 15 | "IoV-Based Blockchain Over LoRa for Accident Detection" (2023 book chapter); "Developing real-time IoT-based public safety alert and emergency response systems" (Scientific Reports 2025, already in the project files) | No HMAC-and-counter crash-alert protocol with a bounded model check found |

Notes: OpenAlex rate-limited one broad query, which was rerun with fewer operators. Scopus, Google Scholar and TRID not run. Use "no study found in the sources checked".

## 9. Verification added 2026-11-14 (OpenAlex records read in the user's Chrome; abstracts read only where stated)

| Item | Fields read | Notes |
|---|---|---|
| Marciano, Seixas, Pereira, Cordeiro, Guerreiro, Lopes, Fernao Pires, Foito, Pinto, "Improving Safety Roads with LoRa Communication Devices: Features and Limitations", 2024, DOI 10.1109/me61309.2024.10789689 | Title, year, DOI, nine authors (ISEL Lisbon, IPS Setubal, IST Lisbon) | Venue name not read; abstract not read. The combined run could not find it; it exists |
| Perkovic, Sabic, Zovko, Solic, "An Investigation of a Replay Attack on LoRaWAN Wearable Devices", IEEE MeditCom 2023, DOI 10.1109/meditcom58224.2023.10266648 | Title, authors (University of Split, FESB), year, DOI; also seen in the Xplore results list | Lead author is Toni Perkovic. Abstract not read |
| Minhas, Elahi, Ahmed, Arshad, Hafiz, Siddique, Sabir, Zaman, "Toward the Design and Development of Intelligent Transportation Devices", IEEE Access 14, 2026, DOI 10.1109/access.2026.3694624 | Title, authors, year, DOI; also seen in Xplore | Abstract not read; content relevance unknown |
| Farha, Ning, Yang, Xu, Zhang, Choo, "Timestamp Scheme to Mitigate Replay Attacks in Secure ZigBee Networks", IEEE Trans. Mobile Computing, 2020, DOI 10.1109/tmc.2020.3006905 | Authors, venue, year, DOI, full abstract | Abstract states that ZigBee frame counters are insufficient after the coordinator restarts and presents a timestamp-based countermeasure in which fully powered devices supply the current timestamp to power-constrained ones |

Consequence for R1 (reboot-resilient freshness): the problem (replay after a restart when the protocol relies on frame counters) and a timestamp countermeasure are already published for ZigBee. R1 may be presented only as an application and quantification for a LoRa crash-alert link (GPS time, seen-set sizing, flash-write saving), in the supplement, with this paper cited as the closest prior work.

## 10. Prior art for the redesign round and the simulator cross-check (OpenAlex, run 2026-11-14; titles from result lists, none opened)

| Topic | Count | Closest results | Reading |
|---|---|---|---|
| LoRa retransmission, adaptive or deadline | 40 | "Adaptive Latency Reduction in LoRa for Mission Critical Communications in Mines", IEEE CNS 2020 (DOI 10.1109/cns48642.2020.9162318); "Mobility Adaptive Data Rate Based on Kalman Filter for LoRa-Empowered IoT Applications", CCNC 2023 (DOI 10.1109/ccnc51644.2023.10060330); "Improvement of LoRa Communication Scalability using Machine Learning Based Adaptiveness", TechRxiv 2021; "Enhanced Adaptive Data Rate and Power Control for Resilient and Energy-Efficient LoRaWAN", IEEE IoT Journal 2025 (DOI 10.1109/jiot.2025.3609239) | D1 must cite these. The mines paper is the closest (mission-critical latency, adaptive). D1's distinct part, if any, is per-severity deadlines under a duty-cycle budget with an online loss estimate; confirm by opening the mines paper |
| LoRa with MDP or Markov decision for retries | 1 | PPO for multi-hop LoRa in forests (IJACSA 2026) | No MDP retry policy for emergency alerts found in the sources checked |
| LoRaWAN priority with duty cycle and deadline | 0 | none | No study found in the sources checked |
| LoRa overhearing with ACK | 1 | LoRa multi-hop water metering preprint (2026) | No overhear-and-defer with gateway-signed cluster ACK found in the sources checked |
| Simulator validation (ns-3, FLoRa, LoRaSim) | 26 | "Simulation of LoRa in NS-3: Improving LoRa Performance with CSMA", ICC 2018 (DOI 10.1109/icc.2018.8422800); "A Configurable Mathematical Model for Single-Gateway LoRaWAN Performance Analysis", IEEE TWC 2021 (DOI 10.1109/twc.2021.3136029); "Comparative Analysis of an Urban LoRaWAN Deployment: Real World Versus Simulation", IEEE Sensors J. 2022 (DOI 10.1109/jsen.2022.3193504) | Use these as calibration references for the cross-check; the 2022 Sensors Journal paper compares a real deployment with simulation and is the best anchor |

## 11. Closest prior work for D1, abstract read (OpenAlex record, 2026-11-14)

Nessa, Hussain, Fernando (Ryerson / Toronto Metropolitan University), "Adaptive Latency Reduction in LoRa for Mission Critical Communications in Mines", 2020 IEEE Conference on Communications and Network Security (CNS), DOI 10.1109/cns48642.2020.9162318; also posted 2024 in the TMU repository (DOI 10.32920/27892158.v1). Full text not opened (not open access).
What the abstract states: underground-mine LoRa with traffic types of different QoS; LoRaWAN pure ALOHA does not meet mission-critical latency and reliability; they propose "redundant retransmission aided adaptive latency reduction", in which the ACK timeout is adjusted from the airtime of the previous uplink and the contention stage; simulation only; better data extraction ratio and average delay than LoRaWAN.
Overlap with D1: adaptive retransmission timing for mission-critical LoRa traffic with mixed priorities, evaluated in simulation.
What D1 adds, as far as the abstract shows: per-severity delivery deadlines, an explicit duty-cycle airtime budget, an online Beta estimate of loss, and retry spacing and spreading factor chosen by a precomputed dynamic programme that maximises delivery before the deadline. Whether the full paper also uses deadlines or a duty budget is unknown until it is read.
Required: cite it as the closest prior work; implement a Nessa-style baseline (adaptive ACK timeout from previous airtime plus redundant retransmission) and compare D1 against it; claim only the differences above.

## 12. Journal articles published 2021 or later (OpenAlex, filter: publication date from 2021-01-01, source type journal, sorted by citations; run 2026-11-14; titles from result lists, none opened unless stated)

| Novelty topic | Query (title and abstract) | Count | Closest journal articles (2021+) | Effect on claims |
|---|---|---|---|---|
| LoRa crash or accident alerting | LoRa AND (crash OR accident) AND (alert OR notification) | 32 | "Real-time Internet of LoRa Things (IoLT)-based accident detection and prevention system in vehicular networks towards smart city", Int. J. Communication Systems (Wiley) 2023, DOI 10.1002/dac.5692; "Developing real-time IoT-based public safety alert and emergency response systems", Scientific Reports 2025, DOI 10.1038/s41598-025-13465-7; "Real Time Accident Detection and Emergency Response Using Drones, Machine Learning and LoRa Communication", IJACSA 2025, DOI 10.14569/ijacsa.2025.0160671; "Lane change decision aid and warning system using LoRa-based V2V", BEEI 2023 | LoRa accident-alert systems are published. The system idea is not new; only the evaluated protocol properties can be claimed. Open the IJCS 2023 paper before the others |
| Adaptive or deadline retransmission for critical LoRa traffic | LoRa AND retransmission AND (emergency OR critical) | 10 | "Delay Optimization in LoRaWAN by Employing Adaptive Scheduling Algorithm With Unsupervised Learning", IEEE Access 2023, DOI 10.1109/access.2023.3234188; `"A novel single-channel edge computing LoRa gateway for real-time confirmed messaging"`, Scientific Reports 2024, DOI 10.1038/s41598-024-59058-8; "Downlink Spreading Factor selection in LoRaWAN", Computer Communications 2023, DOI 10.1016/j.comcom.2023.12.013; "Reliability and Energy Consumption of LoRa With Bidirectional Traffic", IEEE Communications Letters 2021, DOI 10.1109/lcomm.2021.3113134 | D1-type adaptive delay and confirmed-messaging work exists in journals; cite these with Nessa et al. 2020 |
| Formal verification of LoRa protocols | (LoRa OR LoRaWAN) AND (Tamarin OR ProVerif OR UPPAAL) | 5 | "A Secure and LoRaWAN Compatible User Authentication Protocol for Critical Applications in the IoT Environment", IEEE TII 2021, DOI 10.1109/tii.2021.3075440; "Security analysis and improvement of key exchange protocol in LoRaWAN network", IJSNET 2025, DOI 10.1504/ijsnet.2025.149892; "MAKA: Multi-Factor Authentication and Key Agreement Scheme for LoRa-Based Smart Grid", IETE J. Research 2023, DOI 10.1080/03772063.2023.2225465 | Formal security analysis of LoRa authentication exists; T2 can claim only a crash-alert protocol with ACK binding, freshness after reboot and timed deadline bounds. No UPPAAL deadline study for LoRa alerts found in these journal results |
| Early or low-latency accelerometer crash detection | (crash detection OR accident detection) AND accelerometer AND (early OR latency) | 15 | Mostly low-tier system papers; "Direction-Aware Telematics Crash Detection and Injury Plausibility Scoring for False Injury Claim Mitigation", IJLTEMAS 2026, DOI 10.51583/ijltemas.2026.150600052 | Direction-aware detection exists; keep impact-side work as supporting |
| Dataset leakage in sensor recognition benchmarks | (leakage OR duplicate) AND (crash, fall detection or activity recognition) AND dataset | 34 | "Human Activity Recognition: A Comparative Study of Validation Methods and Impact of Feature Extraction in Wearable Sensors", Algorithms 2024, DOI 10.3390/a17120556 (validation-method leakage); others are privacy leakage | Validation leakage is studied for HAR; no crash-detection benchmark audit found in these journal results |
| Accelerometer saturation or clipping in impacts | accelerometer AND (saturation OR clipping) AND (impact OR crash) | 22 | None relevant in the top results | No 2021+ journal article on clipping in crash pulses found in these results (the 2022 and 2026 IEEE Sensors J. papers from section 1 remain the closest) |
| Trace-driven LoRaWAN evaluation | LoRaWAN AND (trace-driven OR real-world traces OR measurement dataset) | 0 | none | T1 method may be uncommon in journals; datasets (LoED, Tampere) exist as data papers |
| Automatic crash notification and severity | (automatic crash notification OR eCall) AND (severity OR latency) | 7 | "Expected Effect of Adopting the eCall System on Reducing Traffic-Related Deaths and Social Costs", IEEE ITS Magazine 2022, DOI 10.1109/mits.2022.3155178; "Advanced Automatic Crash Notification Algorithm for Children", Academic Pediatrics 2022; "Motorcycle Crash Severity Estimation for Effective Emergency Response", SAE 2022-28-0399; "Predicting specific injury patterns from crash data ... for next generation eCall", Transportation Research Interdisciplinary Perspectives 2026, DOI 10.1016/j.trip.2026.102109 | Severity-aware crash notification is an active journal topic; cite as application context; no two-stage provisional-then-confirm alert found in these results |
