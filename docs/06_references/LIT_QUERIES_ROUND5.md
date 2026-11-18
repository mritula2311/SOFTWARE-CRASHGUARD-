# Literature queries, round 5 (L1 to L5)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Round 5 query log for L1 to L5: OpenAlex queries for journal articles from 2021 and a context search without filters; counts, top titles and the items opened. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ESP32 = a Wi-Fi microcontroller family (Espressif); GPS = Global Positioning System; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; LoRa = long-range radio modulation; MAC = message authentication code; MDPI = Multidisciplinary Digital Publishing Institute; MEMS = micro-electromechanical system; ML = machine learning; MPU6050 = an accelerometer and gyroscope chip |
<!-- header:end -->

Run date 2026-11-15. Database: OpenAlex API (no key, no personal detail sent). Journal scope: `from_publication_date:2021-01-01,primary_location.source.type:journal`; context scope: no filter (older and conference work). IEEE Xplore, Scopus, Google Scholar and TRID were not run. L6 to L10 are added in session 2.

## Topic 21. L1: mounting orientation, gravity and driving direction

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `smartphone AND "orientation" AND (crash OR accident) AND detection` | 5 | ResQ - Accident Detection and Alerts App (2025, Utilitas Mathematica); ResQ: A Sensor-Based Mobile Framework for Automatic Road Accident Dete (2026, International Journal of Adv); Design and Implementation of a Smart Sensor-Based Real-Time Accident D (2026, International Journal of Sci); Smart Armband for Early Detection of Hypothermia and Hypoxia with the  (2021, International Journal Of Sci) |
| context_any | `smartphone AND "orientation" AND (crash OR accident) AND detection` | 24 | A Smartphone Multi-Sensor-Fusion App for Motorcycle Crash Detection an (2026, International Conference on ); Fine-Grained Abnormal Driving Behaviors Detection and Identification w (2016, IEEE Transactions on Mobile ); D3: Abnormal driving behaviors detection and identification using smar (2015, IEEE International Conferenc); Using Smartphones to Monitor Cycling and Automatically Detect Accident (2014, Diva portal (Dalarna Univers) |
| journal_2021plus | `gravity AND (smartphone OR accelerometer) AND (calibration OR alignment) AND vehicle` | 7 | Noise analysis and suppression in a calibration measurement system for (2025, Measurement Science and Tech); Gravity-Aided Transfer Alignment With Enhanced Horizontal Observabilit (2026, IEEE Transactions on Instrum); A method for improving calibration accuracy of the inertial navigation (2025, Measurement Science and Tech); Dual-Antenna GNSS-Aided INS Stationary Alignment With Sensor Parameter (2025, IEEE Transactions on Instrum) |
| context_any | `gravity AND (smartphone OR accelerometer) AND (calibration OR alignment) AND vehicle` | 41 | Speed Estimation using Smartphone Accelerometer Data (2019, Transportation Research Reco); Auto-calibration of accelerometers in erecting missile (2007, Journal of Chinese Inertial ); Adaptive parameter based Particle Swarm Optimisation for accelerometer (2016, IEEE International Conferenc); Calibration of MEMS Accelerometers and Magnetometers for Rotor UAV Att (2015, Advances in engineering rese) |
| journal_2021plus | `accelerometer AND ("coordinate system" OR "reorientation") AND (vehicle OR driving)` | 9 | Reduction of calibration uncertainty due to mounting of three-axis acc (2021, Metrologia); Method of calibration mems accelerometer and magnetometer for increasi (2022, Scientific journal of the Te); RESULTS OF SEMI-NATURAL TESTS OF THE AUTONOMOUS DETERMINATION OF THE V (2022, Bulletin of Kyiv Polytechnic); Vehicles Positioning with the Fusion of Time of Arrival, Angle of Arri (2021, Proceedings of Telecommunica) |
| context_any | `accelerometer AND ("coordinate system" OR "reorientation") AND (vehicle OR driving)` | 88 | Evaluating Reorientation Strategies for Accelerometer Data from Smartp (2016, Lecture notes in computer sc); Applying Neural Networks to Improve the Accuracy of the Directional Co (2024, International Conference on ); Deep neural networks for vehicle driving characterization by means of  (2020, UPM Digital Archive (Technic); Driving analytics using smartphones: Algorithms, comparisons and chall (2017, Transportation Research Part) |

## Topic 22. L2: post-crash corroboration, confirmation stage

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `(crash OR accident) AND detection AND "false alarm" AND ("post-crash" OR "post-impact")` | 5 | Real-Time Two-Wheeler Accident Detection with Automated Emergency Noti (2026, International Journal for Re); IOT-Based Automatic Vehicle Accident Detection and Rescue System (2025, International Journal of Cre); Accident Guardian: A Low-Cost Intelligent Collision-Detection System f (2026, AHFE international); AI-Powered Real-Time Accident Detection via CCTV with Severity-Based E (2026, International Journal of Inn) |
| context_any | `(crash OR accident) AND detection AND "false alarm" AND ("post-crash" OR "post-impact")` | 15 | LifeLink: Multi-Parameter Crash Detection with Adaptive False Alarm Su (2026, International Conference on ); Real-Time Two-Wheeler Accident Detection with Automated Emergency Noti (2026, International Journal for Re); IOT-Based Automatic Vehicle Accident Detection and Rescue System (2025, International Journal of Cre); Accident Guardian: A Low-Cost Intelligent Collision-Detection System f (2026, AHFE international) |
| journal_2021plus | `"accident detection" AND smartphone AND ("speed drop" OR stationary) AND verification` | 0 | none |
| context_any | `"accident detection" AND smartphone AND ("speed drop" OR stationary) AND verification` | 0 | none |
| journal_2021plus | `("two-stage" OR confirmation) AND accident AND detection AND vehicle` | 49 | Drunk Driving Detection Using Two-Stage Deep Neural Network (2021, IEEE Access); Vehicle Accident Alerting System (2024, INTERANTIONAL JOURNAL OF SCI); A Sensor Fusion and Yolo-Based Approach for Real-Time Vehicle Accident (2026, International Research Journ); Vision Guard: Accident Prevention and Detection Device (2026, International Journal of Adv) |
| context_any | `("two-stage" OR confirmation) AND accident AND detection AND vehicle` | 127 | A Confirmation Based Accident Detection System Using IoT for Smart Veh (2024, IEEE World Conference on App); Real-Time Vehicle Damage Classification Based on Accident Detection fr (2025, International Conference on ); Drunk Driving Detection Using Two-Stage Deep Neural Network (2021, IEEE Access); Vehicle Accident Alerting System (2024, INTERANTIONAL JOURNAL OF SCI) |

## Topic 23. L3: wake-on-motion, pre-trigger buffer, sensor energy

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `("wake-up" OR "wake-on-motion") AND accelerometer AND energy AND (crash OR impact)` | 2 | Implementation of TinyML on Accelerometer and Gyroscope-Based Wearable (2026, JURNAL SISTEM DAN TEKNOLOGI ); Deep-Transfer-Learning-Based Intelligent Gunshot Detection and Firearm (2024, IEEE Internet of Things Jour) |
| context_any | `("wake-up" OR "wake-on-motion") AND accelerometer AND energy AND (crash OR impact)` | 5 | SmarTEG: An Autonomous Wireless Sensor Node for High Accuracy Accelero (2019, Sensors); Implementation of TinyML on Accelerometer and Gyroscope-Based Wearable (2026, JURNAL SISTEM DAN TEKNOLOGI ); D-24 Free Communication/Poster - Energy Balance and Weight Control (2013, Medicine & Science in Sports); A Motion Based Power Management Technique for Wireless Sensor Networks (2015, International Workshop on St) |
| journal_2021plus | `("pre-trigger" OR "pre-event") AND accelerometer AND buffer AND (impact OR fall)` | 0 | none |
| context_any | `("pre-trigger" OR "pre-event") AND accelerometer AND buffer AND (impact OR fall)` | 1 | A Motion Based Power Management Technique for Wireless Sensor Networks (2015, International Workshop on St) |
| journal_2021plus | `MPU6050 AND ("motion interrupt" OR "power consumption") AND detection` | 3 | Slopeguard: A Lora-Driven Intelligent Landslide Detection Framework (2026, International Scientific Jou); The application and management of wearable optical sensing technology  (2026, SLAS TECHNOLOGY); HALO-4: The Smart Helmet (2026, International Journal of Inn) |
| context_any | `MPU6050 AND ("motion interrupt" OR "power consumption") AND detection` | 17 | Low-Power Fall Detection System with Location Versatility (2022, Chinese Control Conference (); Slopeguard: A Lora-Driven Intelligent Landslide Detection Framework (2026, International Scientific Jou); Design and Implementation of Fall Detection Equipment for the Elderly  (2022, International Conference on ); SOS-Enabled Wearable for Personal Security with GPS Tracking and Fall  (2025, International Conference on ) |

## Topic 24. L4: spreading factor escalation under retransmission and deadlines

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `LoRa AND "spreading factor" AND retransmission AND (deadline OR latency)` | 2 | Correction: LSML-SF: a lightweight stacked ML approach for spreading f (2026, Frontiers in Artificial Inte); Adaptive Data Rate Optimization in Mobile and Dense LoRaWAN IoT Enviro (2026, IEEE Internet of Things Jour) |
| context_any | `LoRa AND "spreading factor" AND retransmission AND (deadline OR latency)` | 5 | ADEO: An Anomaly Detection and Energy Optimization for Centralized LoR (2026, SSRN Electronic Journal); Burst-MAC: A MAC Protocol for Handling Burst Traffic in LoRa Network (2024, IEEE Real-Time Systems Sympo); MuCode-LoRa: Individual Simulation Runs and Aggregated Summary with Co (2026, Zenodo (CERN European Organi); Correction: LSML-SF: a lightweight stacked ML approach for spreading f (2026, Frontiers in Artificial Inte) |
| journal_2021plus | `LoRaWAN AND "spreading factor" AND (escalation OR fallback OR increase) AND reliability` | 14 | Joint channel and spreading factor selection algorithm for LoRaWAN IoT (2026, Simulation Modelling Practic); Improving reliability and fairness of LoRaWAN-based advanced metering  (2024, Scientia Iranica); Correction: LSML-SF: a lightweight stacked ML approach for spreading f (2026, Frontiers in Artificial Inte); Reliability Evaluation of RSrSF-LoRa and LoRaWAN for Dense Industrial  (2026, Sensors) |
| context_any | `LoRaWAN AND "spreading factor" AND (escalation OR fallback OR increase) AND reliability` | 47 | Improving Reliability and Scalability of LoRaWANs Through Lightweight  (2018, IEEE Internet of Things Jour); Joint channel and spreading factor selection algorithm for LoRaWAN IoT (2026, Simulation Modelling Practic); Experimental Investigation of Spreading Factor, Payload Length and Col (2024, Preprints.org); IRSA Over Spreading Factors for Spatio-Temporal SIC in Scalable LoRaWA (2025, IEEE Symposium on Computers ) |
| journal_2021plus | `LoRaWAN AND ADR AND retransmission AND ("time-critical" OR "low latency" OR alarm)` | 0 | none |
| context_any | `LoRaWAN AND ADR AND retransmission AND ("time-critical" OR "low latency" OR alarm)` | 0 | none |

## Topic 25. L5: cross-layer co-design of detection threshold and network delay

| Scope | Query | Count | Top titles (year, venue) |
|---|---|---:|---|
| journal_2021plus | `("cross-layer" OR "co-design") AND detection AND (LoRa OR wireless) AND "false alarm"` | 7 | Reconfigurable Intelligent Surface-Assisted Cross-Layer Authentication (2025, IEEE Internet of Things Jour); Defense Against False Data Injection and Fault Tolerance Optimization  (2026, Informatica); A New IDS for Detecting DDoS Attacks in Wireless Networks using Spotte (2023, 網際網路技術學刊); An auxiliary detection model for gastrointestinal nursing based on dee (2025, AIP Advances) |
| context_any | `("cross-layer" OR "co-design") AND detection AND (LoRa OR wireless) AND "false alarm"` | 28 | Reputation‐based cross‐layer intrusion detection system for wormhole a (2014, Security and Communication N); One Cross-Layer Anomaly Intrusion Detection System Model for Wireless  (2009, Chuangan jishu xuebao); Cross Layer Based Cooperative Spectrum Sensing for Cognitive Radio Net (2020, International Journal of Eng); QoSRP: A Cross-Layer QoS Channel-Aware Routing Protocol for the Intern (2019, Sensors) |
| journal_2021plus | `("time to awareness" OR "notification time") AND (crash OR accident) AND (IoT OR LoRa)` | 0 | none |
| context_any | `("time to awareness" OR "notification time") AND (crash OR accident) AND (IoT OR LoRa)` | 0 | none |
| journal_2021plus | `("detection threshold" OR "decision threshold") AND "network delay" AND "end-to-end"` | 0 | none |
| context_any | `("detection threshold" OR "decision threshold") AND "network delay" AND "end-to-end"` | 0 | none |

## Items opened

| Item | How it was read | What it does |
|---|---|---|
| Gaitan et al., Metrologia 2021, doi 10.1088/1681-7575/abeccf | OpenAlex record (abstract) | Laboratory calibration of tri-axis accelerometers; mounting misalignment on the calibration instrument; not a vehicle mounting method |
| Zhang et al., IEEE Trans. Instrum. Meas. 2026, doi 10.1109/tim.2026.3731729 | OpenAlex record (abstract) | Gravity-aided transfer alignment for inertial navigation systems with a cubature Kalman filter; heading misalignment under low dynamics |
| ResQ app, Utilitas Mathematica 2025 and ResQ framework, IJARSCT 2026 (doi 10.48175/ijarsct-31811) | OpenAlex records (abstract) | Smartphone accident detection with accelerometer, gyro and GPS; thresholds; a 30 s user confirmation timer; the abstracts state no mounting calibration and no post-event kinematic check |
| Bhadane, IJRASET 2026, doi 10.22214/ijraset.2026.78311 | OpenAlex record (abstract) | MPU6050 and ESP32 at 100 Hz; time-gated thresholds to reject potholes, turns and hard braking; post-impact voice logging; no post-event speed or stillness check in the abstract |
| Alhosani et al., Accident Guardian, AHFE 2026, doi 10.54941/ahfe1007856 | OpenAlex record (abstract) | Aftermarket collision detector with a driver verification step to cancel false alarms; manual, no kinematic corroboration |
| Hallur and Gajendra, Discover Vehicles 2026, doi 10.1007/s44465-026-00047-8 | OpenAlex record (abstract) | Functional safety framework for two-wheelers with sensor fusion, LSTM collision prediction and rider intervention |
| Elsabathi and Tjisyah, J. Sist. Teknol. Inf. 2026 | OpenAlex record (abstract); targets stated, not measured results | Fall detection with a threshold wake-up detector followed by a lightweight network; power target below 5 mA; no pre-trigger buffer in the abstract |
| Casals Ibanez et al., The SF12 Well in LoRaWAN, Sensors 2021, doi 10.3390/s21196478 | OpenAlex record (abstract); MDPI full text not fetched by script | After failed frame delivery devices raise the spreading factor; with link-layer reliability the network can collapse to SF12; end-device-based remedies by simulation |
| Gorrela et al., IEEE Internet Things J. 2026, doi 10.1109/jiot.2026.3659938 | OpenAlex record (abstract) | Adaptive data rate for mobile and dense LoRaWAN with a learning-based mechanism; packet loss and retransmission rates |
| Khalifeh et al., Simul. Model. Pract. Theory 2026, doi 10.1016/j.simpat.2026.103277 | OpenAlex record has an empty abstract; title only, not used for any claim | Joint channel and spreading factor selection |

Absence wording used in the matrix: "no journal article from 2021 onwards found in the sources checked". The record of an item is read at abstract level only; no full text was read in this session.

## Session 2 queries (topics 26 to 31)

Topics 26 (L6 gateway placement) and 27 (L7 forward-secure keys) were run on OpenAlex; topics 28 (L8), 29 (L10), 30 (L11) and 31 (L9) were run on Crossref (plain-text queries, journal articles from 2021-01-01, 8 results each) because OpenAlex returned HTTP 429 for them. The record files are `results/tables/r5_lit_queries.json` and `results/tables/r5_lit_crossref.json`. Crossref gave no abstracts for the items used; their rows rest on titles and are worded accordingly.
