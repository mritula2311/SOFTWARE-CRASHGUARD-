# CrashGuard: literature survey of open-access journal work, 2021 onwards (15 November 2026)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Survey of open-access journal work from 2021 onwards per contribution, as supplied on 2026-11-15, with the changes it asks for in the paper. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; DOI = digital object identifier; GSM = Global System for Mobile communications; IEEE = Institute of Electrical and Electronics Engineers; IMU = inertial measurement unit; LoRa = long-range radio modulation; MDPI = Multidisciplinary Digital Publishing Institute; MEMS = micro-electromechanical system; MQTT = Message Queuing Telemetry Transport; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; SAE = Society of Automotive Engineers |
<!-- header:end -->

## How this was done
- **Sources searched:**
  - DOAJ (Directory of Open Access Journals) API: 2021+ articles, abstract-field queries per contribution.
  - OpenAlex: journals 2021+, from the earlier passes recorded in the literature status, sections 8 to 12.
  - The 24 PDFs in the claude.ai Project.
  - Publisher pages (MDPI, IEEE Xplore, Springer, Wiley), opened in the user's Chrome.
- **Not searched:**
  - **Google Scholar:** it returned its automated-query block page with no CAPTCHA offered. It was not bypassed, and no user credentials were used. Scholar needs no login, so credentials would not have helped.
  - **OpenAlex in this pass:** its free daily budget was used up during this pass, after the earlier runs.
  - **Scopus:** not available.
- **Read depth:**
  - **Full text** means the whole article was read.
  - **Targeted** means the abstract plus the passages matching the claim terms (replay, counter, formal, ACK, leakage).
  - **Abstract** means only the abstract.
- **Wording rule for absence:** "no open-access journal article from 2021 onwards found in the sources checked (DOAJ, OpenAlex, project PDFs; Google Scholar and Scopus not searched)".

## Closest work per contribution

### C4: authenticated alert protocol with formal proofs (Tamarin, ProVerif)
| Work | Read | What it does | Difference from CrashGuard |
|---|---|---|---|
| Manuel and Daimi, "Implementing cryptography in LoRa based communication devices for unmanned ground vehicle applications", SN Applied Sciences 3:397, 2021, DOI 10.1007/s42452-021-04377-y (open access) | Full text | Raw LoRa link (no LoRaWAN) with AES-128 then HMAC-SHA256 (encrypt-then-MAC) on downlink commands; uplink location uses bit rotation, complement and an 8-bit XOR key; tested with a robot at 1.2 miles | No counter, nonce or timestamp, so no replay protection. No authenticated ACK. No reboot handling. No formal verification. This is the closest LoRa peer-to-peer security design, and it shows the gap that C4 addresses |
| Manuel, Faied, Krishnan, `"A Novel LoRa LPWAN-Based Communication Architecture for Search and Rescue Missions"`, IEEE Access 10, 2022, DOI 10.1109/ACCESS.2022.3178437 (open access, project PDF) | Full text | Robot control over raw LoRa reusing the 2021 cryptography protocol; time analysis selects SF10 with BW 250 kHz | Same security limits as the 2021 paper; no formal analysis |
| Alkhaiwani and Alsamani, "A Framework and IoT-Based Accident Detection System to Securely Report an Accident and the Driver's Private Information", Sustainability 15:8314, 2023, DOI 10.3390/su15108314 (open access, project PDF) | Full text | Airbag and vibration sensors, Raspberry Pi; location encrypted with ECIES and sent by MQTT over GSM; server forwards SMS to responders; compares ECIES and RSA timings | Confidentiality only. No replay protection, ACK authentication or formal verification. Not LoRa. The "authentication phase" is not specified. The closest secure crash-reporting system |
| "Hybrid Machine Learning Anomaly Detection and Lightweight Zero Trust Authentication for LoRaWAN Networks", IEEE Access, 2026, DOI 10.1109/ACCESS.2026.3660731 (open access) | Targeted | LoRaWAN anomaly detection plus zero-trust authentication; ACK spoofing listed among attacks; simulation-based evaluation calibrated with measurements; the authors say their scoring is not formally derived | Empirical, not formal. Not a crash-alert protocol. Cite for ACK spoofing as a recognised threat |
| Earlier, from the literature status: Farha et al., IEEE TMC 2020 (timestamp replay protection after restart, ZigBee); Wesemeyer et al., EuroS&P 2020 and Dong et al., ISSRE 2024 (LoRaWAN formal verification); Jabbari and Mohasefi, IEEE TII 2021 (LoRaWAN authentication for critical applications); DG-LoRa, Sensors 2021 (group ACK, no security discussion) | Abstract or full text as recorded there | | Keep citing |

Reading: no open-access journal article from 2021 onwards was found, in the sources checked, that gives a formally verified authenticated crash-alert protocol with per-vehicle ACK binding and reboot freshness. C4 holds with that wording.

### C5: two-stage (provisional, then confirm or cancel) crash alert
- DOAJ query for crash, accident or fall with early warning, provisional or two-stage, with cancel, retraction or false alarm, with notification: 0 results.
- OpenAlex journals 2021+ (earlier pass): 25 results, none a provisional-then-confirm crash alert.
- Application context: next-generation eCall injury prediction (Transportation Research Interdisciplinary Perspectives, 2026); "Motorcycle Crash Severity Estimation for Effective Emergency Response" (SAE 2022).
- Reading: none found in the sources checked. eCall literature was not read in full, and it is the most likely place a reviewer will point. Search Scholar by hand for "eCall early notification" and "provisional crash notification" before submission.

### C6: retry policies across simulators and real traces
| Work | Read | Relevance |
|---|---|---|
| `"Adaptive Execution Timing for Offline First Quorum Coordination in LoRa Mesh Networks"`, Telecom 7(5):123, 2026 (MDPI, open access) | Targeted | Adapts slot spacing and deadlines to LoRa airtime at runtime, with a bounded retry; four SX1276 nodes, 2,514 rounds. A schedule derived from replayed traces at fixed SF12 is much slower than adaptive timing (11.3 s against 3.4 s median). "Crash" here means node crash faults. Closest recent work on airtime-aware deadlines; cite in C6 |
| "Developing real-time IoT-based public safety alert and emergency response systems", Scientific Reports 2025 (project PDF; already opened in the final run) | Full text earlier | Application context |
| Nessa et al., CNS 2020 (adaptive ACK timeout, mission-critical LoRa) | Abstract | Closest retry prior work; still not opened in full |

### C1: benchmark leakage audit
| Work | Read | Relevance |
|---|---|---|
| "Dual-Filter IMU Sensor Fusion Framework With Leakage-Free Imbalance Handling for Real-Time Road Surface Anomaly Classification", IEEE Access, 2026, DOI 10.1109/ACCESS.2026.3712035 (open access) | Abstract | Names leakage from oversampling before the train-test split in IMU road-surface classification. That is a method-induced leak, not duplicate records across a published dataset's splits |
| "Leakage-Resistant Evaluation of Gait Mat and Multisensor Biomechanical Features ...", Bioengineering, 2026, DOI 10.3390/bioengineering13090965 | Title | Subject-level leakage control in another sensor domain |
| Earlier: activity-recognition validation-method study (Algorithms 2024); pothole benchmark leakage preprint (2026) | Abstract | Neighbouring audits |
| Round 5 L10: UCI HAR and SisFall showed no cross-split identical windows | Project result | Narrows C1 to VZCrash |

Reading: leakage is a live topic in IMU and biomechanics journals from 2025 to 2026, so C1 should be framed as a data-quality audit of one named crash benchmark, citing these as the wider concern. No crash-benchmark duplicate audit was found in the sources checked.

### C2: accelerometer range for crash pulses
- DOAJ: 11 results for accelerometer with crash, collision or impact and saturation, measurement range, clipping or full-scale. None addresses vehicle crash-pulse range requirements.
- Nearest are high-g MEMS accelerometer design papers (for example Sensors 2024, DOI 10.3390/s24175540) and an open high-bandwidth IMU logger (Journal of Open Hardware, 2025).
- Earlier closest: Dima and Covaciu 2017; Jao and Shkel 2022; Zhang et al. 2026.
- Reading: no change; keep "quantification on public NHTSA pulses, frontal barrier only".

### C3: compact embedded detector
- DOAJ: 4 results, all low-tier system papers: a motorcycle IoT detector (2025), deep-learning severity analysis (Foundations of Computing and Decision Sciences, 2024), and MEMS accident detection (2022).
- Reading: no closer work. Keep C3 as a measured trade-off, not a new method.

### C7: mounting calibration
- DOAJ: 4 results, all inertial-navigation initial alignment (marine and INS), plus a lane-keeping misalignment study.
- Reading: automatic IMU alignment is standard in navigation. Cite it, and present L1 as an application to crash nodes with a measured effect, not a new alignment method.

### LoRa crash-alert systems (context for the introduction)
| Work | Read | What it does |
|---|---|---|
| Vinodhini et al., "Real-time Internet of LoRa Things (IoLT)-based accident detection and prevention system in vehicular networks towards smart city", Int. J. Communication Systems 38, 2025, DOI 10.1002/dac.5692 | Abstract | LoRa with ultrasonic edge sensors to detect abnormal events and route an ambulance to the nearest hospital using the cloud; no security or protocol evaluation stated in the abstract |
| "Vehicle-Based Disaster Alerting System Using LoRa Communication", IJIRT 12(1), 2025 (project PDF) | Full text | Prototype broadcasting disaster alerts to vehicles over LoRa, Firebase and satellite; no evaluation of delivery, security or latency beyond a demo |
| Carneiro et al., NOMS 2023; Marciano et al., 2024 | Record only | Earlier crash-response papers over LoRa |

Reading: LoRa accident-alert systems exist, but the ones read report demos without delivery statistics, security analysis or formal checks. Use this as the motivating gap.

## What changes in the paper
1. **C4 related work:** cite Manuel and Daimi 2021, Manuel et al. 2022, Alkhaiwani and Alsamani 2023, and the 2026 IEEE Access zero-trust paper. Say exactly what each lacks:
   - Manuel and Daimi, and Manuel et al.: no replay protection, no authenticated ACK, no formal proof.
   - Alkhaiwani and Alsamani: confidentiality only.
   - The zero-trust paper: empirical, not formal.
2. **C6:** cite the Telecom 2026 airtime-adaptive deadline paper as the closest recent work on airtime-aware deadlines.
3. **C1:** frame the audit as one instance of a live concern, citing the 2025 and 2026 IMU and biomechanics leakage papers, and keep it to VZCrash.
4. **C7:** cite inertial-navigation initial-alignment work, and present L1 as an application.
5. **Introduction:** use the LoRa accident-alert systems as the motivating gap. They are demos without delivery statistics, security analysis or verification.
6. **Absence statements:** use the wording rule above everywhere.

## Still recommended before submission
1. **Search Google Scholar yourself** for these strings, published since 2021, and send the top 10 titles for each to the author:
   - "LoRa" "accident" "replay"
   - "crash notification" "provisional" OR "pre-alert"
   - "eCall" "early notification" severity
   - "LoRa" "Tamarin" OR "ProVerif"
   - "crash detection dataset" leakage OR duplicate
2. **Read in full through your library:**
   - Nessa et al., CNS 2020;
   - Vinodhini et al., IJCS 2025;
   - Jabbari and Mohasefi, IEEE TII 2021;
   - one next-generation eCall paper.
