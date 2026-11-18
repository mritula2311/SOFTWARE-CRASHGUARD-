# Literature status

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Literature status supplied with the combined run, what that run opened (URL and date), the narrowing of claims and the resolved reference defects. |
| Evidence labels used | ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; ASI = acceleration severity index; DOI = digital object identifier; ECE = Economic Commission for Europe; ESV = Enhanced Safety of Vehicles (conference); GSM = Global System for Mobile communications; HIC = head injury criterion; HMAC = hash-based message authentication code; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; IMU = inertial measurement unit; IOP = Institute of Physics; LPWAN = low-power wide-area network; LoRa = long-range radio modulation; MAC = message authentication code; MIC = message integrity code (LoRaWAN); ML = machine learning; MQTT = Message Queuing Telemetry Transport; NCAP = New Car Assessment Programme; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; PMC = PubMed Central; SAE = Society of Automotive Engineers; URL = uniform resource locator; WPC = Wireless Planning and Coordination wing (India) |
<!-- header:end -->

Sections 1 to 8 are the literature status supplied with the combined run (checked 2026-11-13, extended 2026-11-14), copied as supplied. An item is OPENED only if its content was read in a session. Section 9 is new: what the combined run itself tried to open on 2026-11-14. The earlier version of this file is kept as `LITERATURE_STATUS_RELEASE_V1.md`; the differences are in `CHANGES.md`. Nothing here is a claim that prior work is absent.

How sections 1 to 8 were made: web searches and page fetches from a cloud session. IEEE Xplore was searched on 2026-11-13 in the author's Chrome (section 5). Scopus needs a login and was not run. Crossref and OpenAlex API calls, ResearchGate, HAL and X-MOL pages were blocked, so some fields are unverified.

## 1. Opened and verified (cite these; fields as read)

| Short name | Fields read | Used for | Notes |
|---|---|---|---|
| Wusk and Gabler, NHTSA ESV 25-0407 (nrd.nhtsa.gov PDF) | Virginia Tech; 140 frontal NCAP tests at about 56 km/h; delta-V, OLC, ASI against HIC, chest and pelvis criteria; R squared 0.006 to 0.056 | X5, injury-criteria caveat | Year and DOI not read; authors' given names not read |
| US 7,643,921 (Continental Automotive Systems) | Inventors Andres and McConnell; granted 2010-01-05; filed 2005-08-26; claim 1: estimated slope below 100% of actual slope beyond the sensor limit | Clipping restoration prior art | Not a lower-bound constraint |
| Sechaud, Jacques, Abry, Tachella, arXiv 2602.22279 (Feb 2026) | Self-supervised reconstruction from saturated data, audio declipping and HDR images | General saturation-reconstruction prior art | Not accelerometers or crashes |
| HEROS-GAN, arXiv 2502.18064 | Extends 8 g to 16 g range of smartphone accelerometers; LASED shaking dataset; no crash or delta-V | Range-extension prior art | Authors and date not read |
| Evaluation of a restoration algorithm applied to clipped tibial acceleration signals (Sensors, May 2023; DOAJ record) | Spline restoration of clipped signals from a plus-minus 16 g sensor against a plus-minus 200 g reference; peak differences about -1.4 g | Spline baseline prior art | Authors not read |
| Stitzel et al., ESV paper 17-0319 (nrd.nhtsa.gov PDF 25ESV-000319) | Wake Forest; OTDA advanced automatic crash notification; inputs delta-V (longitudinal and lateral), rollover quarter turns, belt, airbags; 38,970 NASS-CDS occupants 2000 to 2011; undertriage 20% to 11%, overtriage 54% to 34% nationwide estimate | Application context for severity-based notification | Cite as the ESV paper; year from paper number, confirm |
| Sisinni, Bellagente, Depari, Carvalho, Flammini, Pasetti, Rinaldi, Ferrari, "Investigating redundancy of LoRaWAN for emergency notifications in industrial plants", IEEE WFCS 2021, pp. 15 to 18, DOI 10.1109/WFCS46889.2021.9483609 (IRIS Brescia record) | Title, authors, venue, pages, DOI | LoRaWAN emergency redundancy | Abstract not read. This is what was cited as "Carvalho 2021": Carvalho is a co-author, not the lead author |
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

Google Scholar returned its automated-query block on all four queries from the author's Chrome. It was not bypassed, so Google Scholar was NOT searched. Instead OpenAlex was re-queried with fielded title-and-abstract filters, and Crossref was tried once (its relevance ranking returned book chapters only). Titles are from result lists; none opened.

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

## 9. What the combined run tried to open (2026-11-14, WebFetch and WebSearch)

A page counts as OPENED only if the page itself was fetched and read. A search-result summary is recorded as SEEN IN SEARCH and does not make an item verified. No API key was requested and no one was contacted.

| Item | Result | URL tried | Status |
|---|---|---|---|
| Dima and Covaciu, "Solutions for acceleration measurement in vehicle crash tests", IOP Conf. Ser.: Mater. Sci. Eng. 252, 012007, CAR2017 (Pitesti, 8 to 10 Nov 2017) | Landing page opened: title, authors, venue, year, DOI, abstract (two accelerometers with different input ranges; 32-bit microcontroller; SD-card logger; filters recommended in standards). The input range values are not in the abstract. | https://iopscience.iop.org/article/10.1088/1757-899X/252/1/012007 | OPENED (abstract page) |
| DiMasi, "Analysis of Automobile Crash Test Data and Recommendations for Acquiring and Filtering Accelerometer Data", DOT-TSC-NHTSA-75-2 (HS-801-521), 1 June 1975 | Record opened: title, author, date, report number, abstract (frequency content of cabin deceleration, filter guidance, resonance of accelerometer packages, polynomial fitting as an alternative to analog filtering). The PDF itself was not read. | https://rosap.ntl.bts.gov/view/dot/11947 | OPENED (record and abstract) |
| IEEE Std 1616-2004, Motor Vehicle Event Data Recorder (MVEDR) | IEEE SA record opened: published 2005-02-10, Inactive-Reserved (superseded by 1616-2021 on 2021-03-25); defines output data compatibility and export protocols, not which elements are recorded. The standard text was not read. | https://standards.ieee.org/ieee/1616/3401 | OPENED (record) |
| Carneiro, Batista, Hirata Junior, Ullah, "A crash response system using LoRa-based V2X communications", IEEE/IFIP NOMS 2023, DOI 10.1109/NOMS56928.2023.10154409 | University of Sao Paulo repository record opened: title, four authors, venue, year, DOI. No abstract; full text private. | https://repositorio.usp.br/item/003148109 | OPENED (record only); abstract NOT read; claim only that the paper exists |
| FC-HMAC, Zenodo DOI 10.5281/zenodo.20515930 | The DOI now resolves to a different record: "Indexed Fragment Authentication with an Authenticated Recovery Control Plane for DTN LPWAN Convergence Layers: Reproducibility Artifact" (A. Chao, version v2, 23 Oct 2026), which says it supersedes the v1 record "FC-HMAC, July 2026". No abstract and no tag length are on the page. The v1 record was not opened. | https://zenodo.org/doi/10.5281/zenodo.20515930 | OPENED, but it is not the FC-HMAC v1 record. Tag length and design UNVERIFIED; do not cite FC-HMAC content |
| 2026 fall-detection leakage audit, MAKE 8(10) 298, DOI 10.3390/make8100298 | doi.org redirects to mdpi.com, which returned HTTP 403. A web search for the exact title did not return it. | https://www.mdpi.com/2504-4990/8/10/298 | NOT OPENED. UNVERIFIED |
| ZigBee timestamp replay paper, IEEE TMC 2020, DOI 10.1109/tmc.2020.3006905 | doi.org redirects to ieeexplore.ieee.org/document/9133288, which returned an empty page. | https://ieeexplore.ieee.org/document/9133288/ | NOT OPENED. UNVERIFIED |
| Sisinni et al., TII, "Adding Redundancy to LoRaWAN for Emergency Communications at the Factory Floor" | Seen in search listings only: a listing gives DOI 10.1109/tii.2021.3124054 (2021 online) and lists authors Sisinni, Carvalho, Ferrari, Flammini. This differs from "18(10), 2022" in section 1 and from the author list there (Gidlund). Abstract not opened. | none opened | SEEN IN SEARCH. Year, volume and DOI UNVERIFIED |
| Marciano et al. 2024, "Improving Safety Roads with LoRa Communication Devices: Features and Limitations" | A search for the exact title and author found nothing. The nearest hit was a 2024 preprint on LoRa vehicle-to-vehicle communication by Cortes, Carvalho and Pires (preprints.org 202405.1291), a different paper. | none opened | NOT FOUND. Title or author may be wrong. UNVERIFIED; do not cite |
| Mostefa et al., "Formal Validation of ADR Protocol in LoraWan Network Using Event-b", ICCSM 2023 | Seen in a search listing only (Smart City Gnosys): DOI 10.1109/ICCSM60247.2023.00011; Event-B and Rodin model of server-side ADR logic. Not opened. | none opened | SEEN IN SEARCH. UNVERIFIED |
| Minhas et al., IEEE Access 2026, "Toward the Design and Development of Intelligent Transportation Devices" | Search returned nothing for this title. | none opened | NOT FOUND. UNVERIFIED |
| "Modeling of a Rear-End Crash Pulse Generator", Adv. Mater. Res. 630, pp. 360 to 365, 2012 | Seen in a search listing: ANSYS/LS-DYNA model of an ECE R44 sled pulse generator, sled at 30 km/h, 680 kg, three PU tubes. scientific.net returned HTTP 403. | https://www.scientific.net/AMR.630.360 | SEEN IN SEARCH. UNVERIFIED |
| Kullgren, Lie, Tingvall, "Crash Pulse Recorder (CPR) - validation in full scale crash tests", Accident Analysis and Prevention 27(5), 717 to 727, 1995 | Seen in a search listing (reference lists, SWOV record). The SWOV page showed a bot check. | https://swov.nl/en/publicatie/crash-pulse-recorder-validation-full-scale-crash-tests | SEEN IN SEARCH. UNVERIFIED |
| "An Investigation of a Replay Attack on LoRaWAN Wearable Devices", MeditCom 2023 | A conference report lists this title as a presentation by Hrvoje Belani, not "Perkovic". No abstract or text found. The author name in section 8 is therefore doubtful. | none opened | SEEN IN SEARCH. Author UNVERIFIED; do not cite |
| SAE J211 | Search returned nothing about J211. | none | NOT OPENED. UNVERIFIED |

Summary: of the 14 items named in the run prompt, 3 were opened (the 1975 report, IEEE Std 1616-2004 record, Carneiro record), 1 DOI resolved to a different record (FC-HMAC), and 10 stay UNVERIFIED (4 seen in search only, 2 not found, 2 blocked, 1 empty page, 1 not found at all). Dima and Covaciu was opened as an extra. In total the status file now lists 24 verified rows in section 1, CHOIR and Wei et al. through OpenAlex, and these 4 opened pages.

## 10. Narrowing applied to the claims

Each line says what exists, so the paper does not claim more than the sources checked support. Absence is worded only as "no study found in the sources checked (IEEE Xplore, OpenAlex; Scopus, Google Scholar and TRID not run)".

- Conformal severity prediction exists (CHOIR, Rafe and Das; Wei et al. 2025). Not claimed as new. What is checked here is conformal intervals from crash-pulse features mapped to an alert class under an airtime budget.
- Sensor range guidance for crash tests exists (Dima and Covaciu 2017; DiMasi 1975, opened; the SAE J211 lineage, not opened). The range result is a quantification on a public pulse set, not an initial look at range.
- Crash pulse generators and recorders exist (a 2012 rear-end generator; 1990s recorders; seen in search, not opened). The physics generators here are stated-assumption lumped-parameter pulses that failed the realism gate and are not used.
- Saturation reconstruction exists (Jao and Shkel 2022; Zhang et al. 2026; Sechaud et al. 2026; US 7,643,921; the tibial spline study). The clipping result is a narrow evaluation on one pulse set.
- Leakage audits exist in neighbouring sensor tasks (pothole detection preprint, 2026; a fall-detection audit that was not opened). The VZCrash audit is a data-quality finding on one named dataset.
- Timestamp replay protection exists (ZigBee, IEEE TMC 2020, not opened) and LoRaWAN frame counters exist. The reboot-resilience candidate (R1) is a quantified trade-off in the alert setting, not a new replay-protection idea.
- Truncated MACs on LoRa exist (the 4-byte LoRaWAN MIC; a Zenodo record on fragment authentication that was not read). No study was found, in the sources checked, on tag length against burst delivery for single-packet alerts.
- Per-device keys are standard in LoRaWAN. R4 is a design correction found by the bounded check, not a new key scheme.
- No crash-alert two-stage (provisional, then confirm or cancel) design was found in the sources checked.

## 11. Reference defects resolved

| Defect | Resolution |
|---|---|
| "Carvalho 2021" | Replaced by Sisinni et al., WFCS 2021 (DOI 10.1109/WFCS46889.2021.9483609); Carvalho is a co-author. The TII paper is listed with its year, volume and DOI UNVERIFIED (section 9). |
| "Chen et al., GLOBECOM 2023" | NOT FOUND. Removed from citable lists. Dong et al., ISSRE 2024 is cited only as the formal-verification work it is, not as a substitute for the missing title. |
| Semtech application note number | No number is cited. Airtime is tested against the formula as transcribed in `lora.py` (ANALYTICAL). |
| India 433 MHz limit | Superseded: the official notification was opened on 2026-11-16 (section 9). The status written here was true on 2026-11-14. |
| "Marciano 2024" | Not found (section 9). Not cited. |
| "Perkovic MeditCom 2023" | Author name doubtful (a report credits Belani). Not cited. |
| FC-HMAC Zenodo DOI | Resolves to a different record. Not cited. |

<!-- final-a:start -->
## 12. Supplied with the final run (Appendix A sections 9 to 12, copied in short form) and what the final run checked

The final-run prompt supplied sections 9 to 12 of its Appendix A. They are kept here as supplied, with the reading depth the supplier stated; the sentence "Nothing here is a claim that prior work is absent" applies to all of them. The numbering below is the supplier's (S9 to S12), to avoid clashing with sections 9 to 11 above.

**S9. Verification added 2026-11-14 (supplier read OpenAlex records in a browser).**

| Item | Fields read | Note |
|---|---|---|
| Marciano et al., "Improving Safety Roads with LoRa Communication Devices: Features and Limitations", 2024, DOI 10.1109/me61309.2024.10789689 | Title, year, DOI, nine authors | Venue and abstract not read. Open before citing |
| Perkovic, Sabic, Zovko, Solic, "An Investigation of a Replay Attack on LoRaWAN Wearable Devices", IEEE MeditCom 2023, DOI 10.1109/meditcom58224.2023.10266648 | Title, authors, year, DOI | Lead author Toni Perkovic. Abstract not read. Conference paper (context) |
| Minhas et al., "Toward the Design and Development of Intelligent Transportation Devices", IEEE Access 14, 2026, DOI 10.1109/access.2026.3694624 | Title, authors, year, DOI | Abstract not read; relevance unknown |
| Farha et al., "Timestamp Scheme to Mitigate Replay Attacks in Secure ZigBee Networks", IEEE TMC, DOI 10.1109/tmc.2020.3006905 | Authors, venue, year, DOI, abstract | ZigBee frame counters are insufficient after a coordinator restart; timestamp countermeasure. The final run re-read the abstract through OpenAlex (record date 2020-01-01, so pre-2021 on the record) |

Consequence for R1: the problem and a timestamp countermeasure are published for ZigBee; R1 is an application and quantification for a LoRa crash-alert link, in the supplement.

**S10. Prior art for the redesign round (OpenAlex, supplier run, titles from lists).** Retransmission adaptive or deadline (40 hits): Nessa et al. (CNS 2020), Farhad et al. (CCNC 2023), a 2021 TechRxiv paper, Alshaer et al. (IEEE IoT J. 2025). MDP retries for emergency alerts: 1 hit, not relevant. Priority with duty cycle and deadline: 0. Overhearing with ACK: 1, not relevant. Simulator validation (26): Citoni et al. (IEEE Sensors J. 2022) is the anchor for real-against-simulation comparison; Magrin et al. (TWC 2021) is the analytical model. The final run opened the abstracts of Citoni, Magrin, Farhad and Alshaer (OpenAlex records, 2026-11-14).

**S11. Closest prior work for D1 (supplier read the abstract).** Nessa, Hussain, Fernando, "Adaptive Latency Reduction in LoRa for Mission Critical Communications in Mines", IEEE CNS 2020, DOI 10.1109/cns48642.2020.9162318: ACK timeout adjusted from the airtime of the previous uplink and the contention stage, plus redundant retransmission; simulation only. Full text not opened (neither by the supplier nor in this run). D1 is described as adding per-severity deadlines, a duty budget, an online loss estimate and a precomputed table; whether the paper also uses deadlines or a duty budget is unknown. A Nessa-style baseline is already implemented from a secondary description (`CLOSEST_PRIOR_WORK.md`).

**S12. Journal articles from 2021 (supplier OpenAlex pass, 2026-11-14, titles from lists).** Topics and counts: LoRa crash alerting 32; adaptive or deadline retransmission 10; formal verification of LoRa 5; early accelerometer crash detection 15; leakage in sensor benchmarks 34; accelerometer saturation in impacts 22; trace-driven LoRaWAN 0; automatic crash notification 7. The final run reran the same family of queries (`LIT_QUERIES_2021PLUS.md`): counts 32, 10, 5, 22 and 7 match for the five queries that were rerun with the supplier's wording; the leakage and trace-driven queries were reworded (the supplier's wording is not stored), so their counts differ (54 and 15, and 5, 11 and 6).

**What the final run opened (2026-11-14).** About 50 OpenAlex records at abstract level (`LIT_QUERIES_2021PLUS.md`, last table); Crossref metadata for 51 DOIs (`REFERENCES_2021PLUS.bib`). IEEE Xplore returned HTTP 418 to a scripted request and was not bypassed; Scopus, Google Scholar and TRID not run. No full text of a journal article was read. The claim-by-claim reading is in `NOVELTY_MATRIX_2021PLUS.md`. Items found that change a claim: DG-LoRa (group acknowledgment, Sensors 2021) for D2; Sisinni et al. (TII 2022) and the bidirectional-traffic letter (IEEE Commun. Lett. 2021) for D1; PEAR-VAE (2026) and Chan et al. (Sensors 2023) for C4; a 2026 journal paper that uses LoED records for link-degradation prediction (T1 context). Name clash: a 2022 forest-monitoring paper titled "LoED" is not the Imperial dataset.
<!-- final-a:end -->

<!-- vf:start -->
## 13. Survey pass and reference verification (final verification run, 2026-11-15)

Source: `CrashGuard_Literature_Survey_2021plus.md` and `CrashGuard_Literature_Status.md` (copied here without change of content) and the checks below. Read depth: full text, targeted (abstract and the passages that match the claim terms), abstract, record (title, authors, venue, DOI only).

| Item | Depth | Where used | Note |
|---|---|---|---|
| Manuel and Daimi, SN Applied Sciences 3:397, 2021, DOI 10.1007/s42452-021-04377-y | full text (survey) | C4 related work | encrypt-then-MAC over raw LoRa; no counter, nonce or timestamp; no authenticated ACK; no formal proof |
| Manuel, Faied, Krishnan, IEEE Access 10:57596 to 57607, 2022, DOI 10.1109/ACCESS.2022.3178437 | full text (survey) | C4 | same cryptography reused; no formal analysis |
| Alkhaiwani and Alsamani, Sustainability 15(10):8314, 2023, DOI 10.3390/su15108314 | full text (survey) | C4 | ECIES over MQTT and GSM; confidentiality only |
| Abdelhady, Ghandoura, Motwakel, Alajmi, IEEE Access 14:18387 to 18407, 2026, DOI 10.1109/ACCESS.2026.3660731 | targeted (survey); abstract re-read | C4 | empirical zero-trust framework for LoRaWAN; ACK spoofing among the attacks |
| Kagai, Branch, But, Allen, Telecom 7(5):123, 2026, DOI 10.3390/telecom7050123 | targeted (survey) | C6 | airtime-aware adaptive slot timing in a LoRa mesh |
| Kumar, Lohani, Acharya, IEEE Access 14:106379 to 106399, 2026, DOI 10.1109/ACCESS.2026.3712035 | abstract | C1 | leakage from oversampling before the split (method-induced) |
| Yang and Ha, Bioengineering 13(9):965, 2026, DOI 10.3390/bioengineering13090965 | full text (Europe PMC, 2026-11-15) | C1 | audit of a public gait dataset: 14 metadata errors, one opposing-label duplicate payload, no cross-partition subject errors |
| Vinodhini, Rajkumar, Subramaniam, Int. J. Commun. Syst. 38(1), 2025 (online 2023), DOI 10.1002/dac.5692 | abstract | introduction | Crossref gives print year 2025, volume 38; earlier notes said 2023; the Wiley page blocked scripted access |
| Carneiro et al., NOMS 2023; Marciano et al., Mechatronika 2024 | record | introduction | not read beyond the record |
| Jabbari and Mohasefi, IEEE TII 18(1):56 to 65, 2022 (online 2021), DOI 10.1109/tii.2021.3075440 | abstract | C4 | closed access |
| Hetz et al., Transp. Res. Interdiscip. Perspect. 38:102109, 2026, DOI 10.1016/j.trip.2026.102109 | abstract | C5 context | ScienceDirect returned HTTP 403; open access under CC BY-NC-ND per OpenAlex |
| Liu and Tsai, ISPRS Archives XLIII-B1-2022:227, DOI 10.5194/isprs-archives-XLIII-B1-2022-227-2022; Jameian and Safarinejadian, IET Radar Sonar Navig. 2021, DOI 10.1049/rsn2.12045 | abstract (DOAJ) | C7 | initial alignment of strapdown inertial navigation; the DOAJ query returned 13 records for 2021 onwards |

Attempts to read full texts (V5.7), 2026-11-15, no block bypassed:
- Nessa et al., CNS 2020: closed access (OpenAlex `closed`); the Toronto Metropolitan University repository record (DOI 10.32920/27892158.v1) lists no public file. Stays at abstract level.
- Vinodhini et al. 2025: the Wiley page returned a Cloudflare block page (HTTP 403) to scripted access. Stays at abstract level.
- Jabbari and Mohasefi 2021: closed access. Stays at abstract level.
- Next-generation eCall (Hetz et al. 2026): the ScienceDirect page returned HTTP 403. Stays at abstract level.
These four are listed in `paper/PLACEHOLDERS.md` (section C) for the author to read through the library.

Correction found by the Crossref check: the LoED authors in the paper's bibliography were given as Bhatia, Lavanya; the Zenodo record, the arXiv page and the data descriptor give Bhatia, Laksh. The VZCrash author list is now the one on the arXiv page (five authors) and the dataset revision is the one on the Hugging Face card.

Wording for every absence statement: no open-access journal article from 2021 onwards was found in the sources checked (DOAJ, OpenAlex, Crossref and the publisher pages opened; Google Scholar and Scopus not searched).
<!-- vf:end -->

## 9. Indian 433 MHz rules (finalize run, 2026-11-16)

| Item | Status |
|---|---|
| Ministry of Communications (WPC Wing), G.S.R. 347(E), 9 May 2022, *Use of Low Power Radio Frequency Devices in the frequency band 433.05 to 434.79 MHz (Exemption from License) Rules, 2022*, Gazette of India, Extraordinary, Part II, Section 3(i), No. 332, 11 May 2022 (BibTeX key `gsr347`) | VERIFIED: the PDF (8 pages) was downloaded from https://eservices.dot.gov.in/sites/default/files/circular-notifications/the-use-of-low-power-radio-frequency-devices-in-the-frequency-band-433.05-to-434.79-mhz-exemption-from-license-rules-2022.pdf and its text read on 2026-11-16: rule 2 (definitions of e.r.p. and of duty cycle over an observation interval), rule 3 table row 1 (433.05 to 434.79 MHz, 10 mW e.r.p., 10% duty cycle, bandwidth not specified), rows 2 and 3, rule 5 (type approval), and the supersession of the 2012 indoor rules. Read depth: full text. The text is partly in Hindi; the English text was read |
