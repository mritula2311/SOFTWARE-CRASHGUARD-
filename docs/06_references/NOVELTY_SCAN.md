# Novelty scan (round 3, 2026-11-11)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Candidate contributions, closest prior work and what was opened. |
| Evidence labels used | NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; ASI = acceleration severity index; CNN = convolutional neural network; CV = cross-validation; EDR = event data recorder; ESV = Enhanced Safety of Vehicles (conference); GAN = generative adversarial network; GPS = Global Positioning System; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; IIHS = Insurance Institute for Highway Safety; KB = kilobyte; LPWAN = low-power wide-area network; LoRa = long-range radio modulation; MAC = message authentication code; MIC = message integrity code (LoRaWAN); NCAP = New Car Assessment Programme; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; SAE = Society of Automotive Engineers; SCT = severity-classified transmission; UA-SCT = uncertainty-aware SCT; URL = uniform resource locator |
<!-- header:end -->

Candidate contribution ideas that are not N1 to N23, testable in software, with the closest prior work, the experiment, the risk and scores from 1 to 5 for (a) distance from the closest prior work, (b) feasibility in three hours, (c) strength of the existing evidence at the time of the scan. Scores were assigned before the S11 and UA-SCT runs. Only sources that were opened and read support anything here; snippet-only sources are labelled and support nothing. A source missing from this list is not proof that none exists. Wording rules: the banned words of `CLAUDE.md` (rule 7) are not used; no claim beyond the evidence.

## 1. Prior work that was opened (all on 2026-11-11, abstract or summary page unless stated)
| Source | Opened as | What it shows | Used for |
|---|---|---|---|
| CHOIR, Rafe and Das, arXiv 2609.11592 (submitted September 2026) | abstract page | Groupwise and weighted conformal prediction with conformal risk control returns contiguous ordinal injury-severity intervals on 4.04 million Texas police records; pooled calibration under-covers motorcyclists and unrestrained drivers; no delta-V, sensor saturation or regression interval | N24, N28 |
| Barber, Candes, Ramdas and Tibshirani, jackknife+ and CV+ (arXiv 1905.02928) | abstract page | Distribution-free predictive intervals for any symmetric algorithm under exchangeability; K-fold CV+ | N24 (the interval construction) |
| Saerens, Latinne and Decaestecker 2002, Neural Computation | abstract page | EM adjustment of classifier outputs to new class priors without retraining; a test for a prior change | N25 |
| Elkan 2001, IJCAI | summary page | The cost-matrix decision rule: predict the class with the lowest expected cost; thresholds follow from the costs | N25 |
| Tamang et al. 2022, Sensors (PMC8948738) | full page | LoRaWAN for factory alarms: urgent packets are unconfirmed, retransmissions are not allowed, separate sub-bands for urgent and regular packets, control packets assign spreading factors | N26, N28 |
| Shao, Liew and Liang 2020, arXiv 2003.01906 | abstract page | An interrupt-and-access MAC for sporadic, crowded, ultra-time-critical warning messages in V2X; warning messages override ordinary traffic | N26 |
| Asteriou et al. 2024, adaptive spatial scheduling for event traffic in LoRaWAN (PMC11014082) | full page | Learning-automaton scheduling of event traffic with time penalties for recently scheduled nodes | N26, N16 |
| Gao, Li and Ma 2019, Sensors (PMC6928866) | full page | Scyther analysis of the LoRaWAN join procedure; replay is the most popular threat; a failing claim in v1.1 | N27 |
| Dong et al. 2024, ISSRE (ECNU record) | abstract page | CSP model in PAT for LoRaWAN with replay, denial of service, ACK spoofing, bit flipping and man-in-the-middle attacks | N27 |
| Wesemeyer et al. 2020, EuroS&P (REF 2021 output record) | output record, no abstract | Verification of the LoRaWAN key establishment (join procedure) with theorem-proving tools; findings reflected in the specification | N27 |
| Reaz and Wunder 2024, arXiv 2412.16224 | abstract page | Tamarin analysis of a permission voucher protocol (replay prevention); not LoRaWAN | N27 (tool precedent only) |
| Wang and Zhao 2025, HEROS-GAN (arXiv 2502.18064) | summary page | A GAN extends a clipped low-cost accelerometer from +-8 g to +-16 g; no crash delta-V, no uncertainty intervals | N14 (neighbouring work, not a baseline) |
| Chan et al. 2023, Sensors (PMC10222349); Tadic and Vukajlovic 2016; Ebert et al. 2016; Katsidimas et al. 2023; Tomic et al. 2020; Wei et al. 2023; Zhong and Nie 2024 | opened in earlier rounds (`docs/06_references/PRIOR_WORK.md`) | see that file | N1, N2, N4, N10, N13, N14, N16 |

**Named by the author, NOT used.** Jao and Shkel 2022 and Zhang et al. 2026 (saturation reconstruction): searches on 2026-11-11 did not return them, so they could not be opened. Chen et al., GLOBECOM 2023 (LoRaWAN verification): not found. Carvalho et al. (LoRaWAN redundancy for emergency traffic): found only as search-result summaries (the publisher and repository pages returned HTTP 403 or unreadable content); the summaries describe a transparent redundant channel for critical traffic with a reported reliability up to 99.5%, which is NOT used for any claim. Wesemeyer et al. 2020 was opened only as a record without abstract. Other snippet-only sources: the RAC Foundation eCall statistics (HTTP 403), the Mondrian conformal literature (Vovk et al., search summary), conformal prediction for censored outcomes (search summary), the unisi alarm-message paper (HTTP 403).

## 2. Candidates
| Id | Claim in one sentence | Why it follows from a result we have | Closest prior work (query, date, opened or snippet) | Software experiment and baseline | Risk | (a) | (b) | (c) | Sum |
|---|---|---|---|---|---|---|---|---|---|
| M1 (S9, N24) | At +-16 g the delta-V point estimate is often wrong, so an alert should carry a calibrated interval or an "at least" statement | N14: median error 12 to 26% at +-16 g | CHOIR (opened); jackknife+ (opened); conformal for clipped sensors: search "conformal prediction regression censored clipped saturated sensor", 2026-11-11, snippet only | Grouped CV+ intervals around fill + ridge; baseline: the point class | Wide intervals; class rule may lower the class | 3 | 4 | 4 | 11 |
| M2 (S10, N25) | A threshold chosen at about 16% crashes gives about 1% precision at real prevalence; set it for the deployment prevalence and a cost model | `prev.*`: precision about 1% at 0.02% prevalence | Saerens 2002 (opened); Elkan 2001 (opened); query "smartphone crash detection false alarms prevalence", 2026-11-11, snippets only | Resampled populations; prior-shift, cost and target-precision thresholds against the existing rule | Established methods; assumed costs | 2 | 5 | 5 | 12 |
| M3 (S11, N26) | Severe and Critical alerts should go out fast with a short authenticated flash and still reach | N16 scheduler beat the table only in bursts | Tamang 2022 (opened); Shao 2020 (opened); Wei 2023, Tomic 2020 (opened earlier); query "LoRa emergency alert priority classes duty cycle reservation", 2026-11-11 | SCT against fixed 3-try, severity table and scheduler, ablations | Gain may be retry spacing only | 3 | 3 | 3 | 9 |
| M4 (S12, N27) | The counter, retry, re-ACK and reboot rules satisfy safety and liveness properties under a bounded attacker | 48 attack cases; the retry finding | Gao 2019, Dong 2024, Wesemeyer 2020 record, Reaz 2024 (opened); query "formal verification LoRaWAN Tamarin ProVerif replay counter", 2026-11-11 | Bounded explicit-state search; counterexamples for the variants | Model not firmware; bounds small | 3 | 4 | 4 | 11 |
| U1 (UA-SCT, N28) | Taking the transmission class from the upper end of a conformal class interval lowers mis-triage | S9: intervals are calibrated; point class under-estimates in about 19% of tests at +-16 g | CHOIR (opened); Tamang 2022 (opened); no source combines the two (searches above) | P0 to P4 on NHTSA class pairs; preregistered | Many escalations; small delivery gain | 4 | 3 | 3 | 10 |
| O1 | Calibrating the false-alarm threshold per vehicle-size category (Mondrian) restores the false-alarm rate in the Heavy category | N20: Heavy category false-alarm rate 13% against alpha 5% | Mondrian conformal (Vovk, search summary, snippet only); CHOIR groupwise (opened) | Category-conditional calibration against pooled; decision rule on the Heavy category | Small calibration sets per category | 3 | 5 | 4 | 12 |
| O2 | Trigger-aligned window-level duplicates are far more common than exact duplicates and lower the headline recall | S2 scan | No leakage audit of trigger-aligned windows opened | Implemented as S2 (extends N8) | Not independent of the exact-hash result | 3 | 5 | 5 | 13 |
| O3 | A severity table with exponentially spaced retries matches most of what SCT gains in bursts | S5: the burst-tuned scheduler is "table plus spacing" | Exponential back-off is textbook; no opened source compares it with a fast path | Spaced-retry table (P1b) against SCT on the held-out cells | May equal SCT | 2 | 5 | 5 | 12 |
| O4 | An optimal cancel window per class follows from the delivery latency and the driver's cancel probability | N16 uses fixed windows 10, 8, 6, 5 s | eCall cancel windows (RAC Foundation, HTTP 403; manufacturer manuals in search summaries, snippet only) | Expected-harm model over hold time | No measured driver behaviour | 3 | 4 | 2 | 9 |
| O5 | Retraining on a window-level de-duplicated training set changes the strict-test recall | S2: 1,192 additional duplicate test windows | None opened | Retrain, score the strict test set once | Small expected effect | 3 | 4 | 4 | 11 |

## 3. Does any own idea score higher than the author's four (M1 to M4)?
The best of M1 to M4 is M2 with 12. O2 scores 13 but it is already implemented (S2) as an extension of N8, so it is not an extra contribution. O1 and O3 score 12 (a tie with M2). O3 has the highest feasibility and a decision rule that can be fixed in advance, so it was implemented as **S13** (`docs/02_preregistration/EXPERIMENTS_EXTRA.md`, rule written before the run). O1 also qualifies on feasibility but only one idea was implemented.

## 4. What S13 found
SCT improves critical reach within 10 s in bursts over the spaced-retry table at every sensor range (the decision rule of S13 is met); the spaced-retry table by itself recovers most of the reach within 30 s. Numbers: `results.json` keys `s13.*`, reported in `report/software_results.md`.

## 5. What the closing block found (T1 to T13, 2026-11-11)
- **U1 (UA-SCT, N28).** At the same escalation the severity table with lowered thresholds does as well as UA-SCT on mis-triage (T1), the interval family has the larger trade-off area (T2), and UA-SCT is cheaper than the table only if a missed severe event costs several times a false escalation (T3). The idea therefore scores lower than it did before the test: the part that is not just a choice of threshold shows no benefit. The status of N28 is NO_IMPROVEMENT_FOUND beyond thresholds.
- **N26 (SCT).** The flash and the severity hold carry the gain in the ablations (T9); the reserved duty share and the CANCEL message change nothing in critical reach in the cells tested. Faster retries repair the single-car weakness but lower reach when many cars share the channel (T4, T9).
- **N27.** A CANCEL that overtakes its alert is lost in the design; remembering it fixes the model (T12). The firmware does not yet do this.
- **No new source was opened for this block.** A second public dataset (T13) and an external delta-V severity scale (T6) could not be opened and are recorded as NOT_RUN.

## 6. v2 studies (branch `v2-algorithms`, 2026-11-12)
No new paper was opened for the v2 studies. The prior work named in the task (Jao and Shkel 2022; Zhang et al. 2026) could not be opened in round 3 and is still not used; Chan et al. 2023 (opened in an earlier round) is the spline baseline. The triangle fit and the Gaussian-process fill in Study A are our own implementations of the ideas described in the task, not their code or results. N29 to N34 in `report/novelty_summary.md` therefore state only the earlier opened sources (CHOIR and jackknife+ for the interval study; Tamang 2022 and Shao 2020 for the delivery studies) and say "none opened" where nothing was opened. The results: N29 supported on the NHTSA tests (tail error), N30, N31 and N32 no improvement found, N33 and N34 partial (analytical and simulated).

## 7. Journal-push studies X5 to X8 (branch `journal-push`, 2026-11-12; written before the studies were run)
Only sources that were opened in this session are listed as opened. "Search summary" means that a search result listed the page or a model-written summary of it, and the page itself was not read; it supports nothing here. No search can show that nothing exists; "remains" below means only "not found in what was opened".

**Sources opened on 2026-11-12.**
| Source | Opened as | What it shows | Used for |
|---|---|---|---|
| Stigson, Kullgren and Rosen 2012, Annals of Advances in Automotive Medicine, "Injury Risk Functions in Frontal Impacts Using Data from Crash Pulse Recorders" (https://pmc.ncbi.nlm.nih.gov/articles/PMC3503411/) | page (abstract level) | 489 real frontal crashes with on-board recorders; delta-V is a strong predictor (10% MAIS2+ risk at 28 km/h, 50% at 48 km/h); no crash-test dummy criteria | X5 context: delta-V ranks real injury risk; dummy criteria are a different question |
| IRCOBI 2020 paper IRC-20-79 on front crash rating programs with the Hybrid III dummy (https://www.ircobi.org/wordpress/downloads/irc20/pdf-files/79.pdf; title and authors not read, only the abstract and introduction) | PDF, opening pages | Dummy and vehicle metrics from NCAP and IIHS tests were weak or mixed predictors of NASS-CDS thoracic injury once delta-V and age were controlled; none of the dummy-metric findings significant at 0.05 for both soft- and hard-tissue injury | X5: supports the warning that dummy criteria relate weakly to real outcomes |
| Renault, Bondu, Cornuejols and Lemaire 2024/2025, "Early Classification of Time Series: A Survey and Benchmark", TMLR (https://arxiv.org/abs/2406.18332) | abstract page | Taxonomy of early-classification methods that trade decision time against misclassification cost; nine algorithms compared. The abstract does not say whether sequential probability ratio tests are covered | X8 context |
| Achenchabe, Bondu, Cornuejols and Dachraoui 2020/2021, "Early Classification of Time Series. Cost-based Optimization Criterion and Algorithms" (https://arxiv.org/abs/2005.09945) | abstract page | A cost that adds a delay cost to the misclassification cost; non-myopic stopping | X8 context |
| Wu, Der and Keogh 2021/2022, "When is Early Classification of Time Series Meaningful?" (https://arxiv.org/abs/2102.11487) | abstract page | Argues that early classification suffers from an under-specified problem and many false alarms | X8 context |
| STMicroelectronics LSM6DSK320X data sheet DS15060 Rev 1, July 2026 (https://components101.com/sites/default/files/2026-10/DS_lsm6dsk320x-compressed.pdf) | PDF, specification tables | One chip with a low-g channel (to +-16 g) and a high-g channel (to +-320 g) | X7 prior art (a dual-range part exists) |
| US 7,643,921 (Continental), opened 2026-11-11 (local text `data/raw/refs/us7643921.txt`) | patent text | Extrapolation of clipped acceleration samples with a slope below 100% of the measured slope | X6 closest prior work |
| HEROS-GAN, arXiv 2502.18064; Chan et al. 2023, Sensors (PMC10222349) | opened on 2026-11-11 (section 1 above) | A learned range extension of a low-cost accelerometer; spline restoration of clipped tibial signals | X6 neighbouring work and baseline |

**Not opened.** Wusk and Gabler (25th ESV, paper 25-0407, named in the task as opened on 2026-11-12): in this session a search listed a TRID record (https://trid.trb.org/view/1482281, "Evaluation of Vehicle-Based Crash Severity Metrics Using Event Data Recorders") and the page could not be fetched; its numbers (140 frontal NCAP tests, R squared 0.006 to 0.056) come from the task text and are NOT verified here. Jao and Shkel 2022 and Zhang et al. 2026: two searches on 2026-11-12 did not return them. The ST page for the LSM6DSV32X (named in the task) timed out; the data sheet that was opened is for the LSM6DSK320X, a different part.

| Study | Search queries (2026-11-12) | Closest prior work (opened) | What remains if the study works (not found in what was opened) |
|---|---|---|---|
| X5 rank preservation of a clipped sensor | "Wusk Gabler NHTSA ESV 25-0407 delta-V ASI OLC dummy injury criteria frontal NCAP"; "Wusk Gabler delta-V injury risk frontal crash test dummy criteria weak correlation ESV 2025" | Stigson 2012 (delta-V ranks real injury risk); IRCOBI 2020 (dummy metrics weak) | A measurement of how a low-range, low-rate sensor model changes the ORDER of severity and class agreement on real crash pulses; no source opened does this |
| X6 lower-bound-anchored estimator | "Jao Shkel 2022 triangular function reconstruction saturated accelerometer Gaussian process regression"; "Zhang 2026 peak-aware saturation compensation accelerometer clipped impact signal" | US 7,643,921 (slope extrapolation); Chan 2023 (spline); HEROS-GAN (learned range extension) | A learned correction factor that is constrained to be at least 1 on a delta-V estimate, evaluated on real crash pulses with grouped splits; the patent and the spline use fixed rules |
| X7 two-part fusion | search results for dual-range parts were part of the datasheet search ("LSM6DSV32X datasheet pdf +-320 g high-g accelerometer") | LSM6DSK320X data sheet (a dual-range chip exists) | Only the quantified requirement table (which pairs of real parts reach 80% within 10%), not a fusion method |
| X8 sequential rule with error control | "sequential probability ratio test early time series classification accelerometer impact detection decision time false alarm control" | The three early-classification papers above (abstract level) | A sequential rule whose thresholds are set on validation for a stated per-event false-alarm rate, compared with the earlier early-exit rule on the same forests; the opened papers are about general benchmarks and costs, not this data |

---

# Scope notes of the positive-results push (written 2026-11-12, before the studies P1 to P4 ran)

Only sources that were opened (page or abstract fetched on the date) support anything here. "Snippet" means a search-result summary only: it supports nothing and no number from it is used.

## Sources opened on 2026-11-12
| Source | URL | What it shows | Used for |
|---|---|---|---|
| Angelopoulos, Bates, Fisch, Lei, Schuster, Conformal Risk Control (arXiv 2208.02814, ICLR 2024; v4 June 2025) | https://arxiv.org/abs/2208.02814 | Extends conformal prediction to control the expected value of a monotone loss; generalises split conformal; extensions to distribution shift | P4c (V4: risk control with group-level calibration), P2 |
| Geifman and El-Yaniv, Selective Classification for Deep Neural Networks (arXiv 1705.08500, 2017) | https://arxiv.org/abs/1705.08500 | Reject option with a threshold on a confidence score to reach a chosen risk; risk-coverage curve | P3a |
| Rafe and Das, CHOIR (arXiv 2609.11592, submitted 2026-09-10, revised 2026-10-01) | https://arxiv.org/abs/2609.11592 | Group-wise conformal intervals on the KABCO scale for 4.04 million Texas police records; no accelerometer data | P2 (distinction), P4c |
| Barber, Candes, Ramdas, Tibshirani, Jackknife+ (arXiv 1905.02928) | https://arxiv.org/abs/1905.02928 | Predictive intervals for any symmetric algorithm; K-fold CV+ | P4c (V3) |
| emlearn repository README | https://github.com/emlearn/emlearn | Converts scikit-learn random forests and decision trees to C99 for microcontrollers; stated footprints from 2 KB flash | P4a (prior tool; not installed here) |
| US 7,643,921 (Continental), opened 2026-11-11 (local text `data/raw/refs/us7643921.txt`) | patent text | Extrapolates clipped samples with a slope set below 100% of the measured slope | P2, X6 (distinction) |
| Earlier rounds | `docs/06_references/PRIOR_WORK.md`, the opened-sources table above | HEROS-GAN, Chan et al. 2023 (clipped signal restoration), Tadic 2016, others | P1, P2 |

**Not opened, not used.** Jao and Shkel 2022 and Zhang et al. 2026: two more searches on 2026-11-12 ("Jao Shkel ...", "Zhang 2026 accelerometer saturation ...") returned neighbouring work only (HEROS-GAN, tibial signal restoration) and no such paper; they are named by the author and cannot be distinguished from by reading. Wusk and Gabler, 25th ESV paper 17-0407: the NHTSA address (https://www-nrd.nhtsa.dot.gov/pdf/ESV/Proceedings/25/25ESV-000407.pdf) appeared in a search result but the fetch returned HTTP 403, so it was not opened; the statement that delta-V and ASI are only weakly related to dummy injury criteria is used only as the author's description of it (unverified here) and no number from it is used. Search of 2026-11-12 for monotone-constrained ordinal classification of crash severity from clipped sensor signals returned police-record ordinal classification only (snippet; Zhu, Wang and Li 2021, not opened).

## P1 (direct ordinal triage from clipped-signal descriptors and a CNN)
Queries: "monotone constrained gradient boosting ordinal classification crash severity clipped accelerometer direct classification versus delta-V regression"; "Jao Shkel low-g accelerometer high-g shock saturation extension range machine learning"; "Zhang 2026 accelerometer saturation crash detection delta-V estimation ..." (all 2026-11-12). Closest prior work opened: HEROS-GAN (range extension by a GAN, no severity class), Chan et al. 2023 (spline restoration of clipped tibial signals), US 7,643,921 (extrapolation rule). What would remain new if H-P1 holds: skipping delta-V and classifying the severity class directly from clipping descriptors on a pooled, sealed set of 913 crash-test records with mode inferred from the pulse. If it fails, the result is "the direct route is not better than binning an estimate on this set".

## P2 (interval from a physical lower bound)
Queries: "Conformal Risk Control Angelopoulos ...", "conformal prediction crash injury severity police records CHOIR" (2026-11-12). Closest: CHOIR (police records, ordinal intervals, no sensor), jackknife+/CV+ (our earlier N24 interval), US 7,643,921 (a slope rule, no interval). Difference: a one-sided interval [plain, plain x q] that uses the fact that clipping makes the plain estimate a lower bound, with q conformal on the ratio. Expected weakness: the lower bound fails more often at +-32 and +-64 g.

## P3 (selective prediction and abstain as an escalation signal)
Queries: "Selective classification for deep neural networks Geifman El-Yaniv risk-coverage" (2026-11-12). Closest: Geifman and El-Yaniv 2017 (the risk-coverage framework; not specific to sensors). Difference: the reliability score comes from clipping descriptors, and the abstain event is routed to a fast alert path in a LoRa protocol simulator. P3b retries the equal-escalation test that N28 failed with a different signal; if it fails again N28 stays NO_IMPROVEMENT_FOUND.

## P4 (VZCrash detector: memory, augmentation, false-alarm guarantee)
Queries: "Conformal Risk Control ...", "emlearn" repository page (2026-11-12). Closest: emlearn (tree-to-C export), conformal risk control, CV+. Earlier results of this project (X1 quantisation, X3 group-aware training, X4 conformal false-alarm control) are the nearest items and are cited as such; P4 re-tests them with a Pareto sweep, augmentation and group-wise calibration. VZCrash events carry no vehicle identifier, so "vehicle groups" are the four vehicle-size categories; this limits what P4c can show.

## Release scope (2026-11-14); wording: "no study found in the sources checked"

| Point | Sources actually opened | Closest prior work | Scope of any claim |
|---|---|---|---|
| Conformal severity interval | arXiv 2609.11592 abstract | CHOIR (Rafe and Das) | No novelty claim: conformal severity prediction with coverage guarantees is prior art |
| Physics-based pulse generator checked against real data by a discriminator | no new source opened | not searched beyond the repository's references | No claim; the generators fail the realism gate (`docs/03_results/PH_INTEGRITY_REPORT.md`) |
| Overhear-and-suppress retries, GPS-slotted critical alerts | OpenAlex records of Tamang et al. and Khan et al. (metadata only) | Tamang et al. (slotted concurrent alarms), Khan et al. (confirmed-uplink model) | No claim: both candidates are negative results under the stated assumptions |
| Retry-schedule formula | none | | Reported as an approximation that overestimates collisions (`pa.analytic.*`) |

## Combined run (2026-11-14): literature narrowing and prior-art check for architecture candidates

Source: `docs/06_references/LITERATURE_STATUS.md` (sections 5 to 11). Wording: "no study found in the sources checked (IEEE Xplore, OpenAlex; Scopus, Google Scholar and TRID not run)".

| Point | What exists (status) | What stays open or narrow |
|---|---|---|
| Sensor range requirement (N13) | Dima and Covaciu 2017 (two accelerometers with different ranges; abstract opened), DiMasi 1975 (frequency content and filtering; abstract opened), SAE J211 lineage (not opened) | A quantification on 176 public NHTSA pulses with a stated accuracy rule; not an initial look at range |
| Clipping restoration (N14) | spline (tibial study), slope extrapolation (US 7,643,921), triangle with Gaussian process (Jao and Shkel 2022), PEAR-VAE (Zhang et al. 2026), Sechaud et al. 2026 | a narrow evaluation on one pulse set, with no gain at +-64 g and a small gain at +-32 g |
| Conformal severity | CHOIR (Rafe and Das), Wei et al. 2025 (tabular crash records) | intervals from crash-pulse features mapped to an alert class under an airtime budget |
| Dataset leakage | pothole benchmark audit (2026 preprint); a fall-detection audit (not opened) | a data-quality audit of one named crash dataset |
| Crash pulse generators and recorders | 2012 rear-end generator and 1990s recorders (listings only); NHTSA EDR comparisons | stated-assumption pulses that failed the realism gate; not used |
| Reboot-resilient freshness (R1) | timestamp replay protection for ZigBee (TMC 2020, not opened); LoRaWAN frame counters; a LoRaWAN replay-attack study (author name doubtful) | a quantified availability and flash-write trade-off for an alert protocol; the idea itself is not new |
| Security-airtime co-design (R2) | 4-byte LoRaWAN MIC; FC-HMAC (record not read) | no study found on tag length against burst delivery for single-packet alerts |
| Two-stage alert (R3) | none for crash alerts in the sources checked | not a claim of absence |
| Per-vehicle ACK keys (R4) | per-device keys are standard in LoRaWAN | a design correction found by the bounded check |
| Burst access | Tamang et al. 2023 remains the closest | baseline in every comparison |

Named in the earlier text above as "not opened, NOT used": Jao and Shkel 2022 and Zhang et al. 2026 are now VERIFIED (Xplore, 2026-11-13); "Chen et al., GLOBECOM 2023" stays not found.

## Redesign round scan (D7, session 2, 2026-11-14)
Sources searched: web search with short queries (standard mode); the OpenAlex API returned HTTP 503 (service unavailable) on all five queries and was not used; **IEEE Xplore, Scopus, Google Scholar and TRID were not run.** Only search summaries and abstracts were read for the items below; "opened" means nothing beyond that. Counts are not available from web search; the titles returned are listed.

| Query topic | Closest items found (abstract or summary level) | Consequence for the redesigns |
|---|---|---|
| Loss-adaptive or deadline-aware retransmission for LoRa emergency traffic (D1) | LoRa-REP, "Emergency Communication in IoT Scenarios by Means of a Transparent LoRaWAN Enhancement" (message replication for emergency messages); LoraHART (opportunistic retransmission window in a TDMA superframe); a LoRa survey (arXiv 1908.10195) stating that static retransmission timers degrade performance and that dynamic timers were not addressed; Long-Lived LoRa (arXiv 2008.09019, sliding-window retransmission counts for energy planning); an ECRTS 2025 paper on deadline guarantees under ideal channels | Retransmission for emergency LoRa traffic exists. D1 is **not** claimed to be unique; its difference (per-class deadline table solved offline, duty budget, Beta loss estimate, load index) is stated only as a difference. Not implemented as extra baselines: none was opened in full and none gives an implementable rule from the summary. |
| Gateway-signed or aggregated ACK for LoRa (D2) | A2S2-LoRaWAN, "Time-slotted ALOHA-based LoRaWAN scheduling with aggregated acknowledgement approach" (EURECOM, FRUCT 2019); DG-LoRa, a group acknowledgement listing several device addresses (PMC7922967); a note that a lost aggregated ACK makes every affected node retransmit | **An aggregated ACK listing devices already exists in the LoRaWAN literature.** D2 cannot claim the aggregation. What these summaries do not show (not verified in full text): a gateway signature with a key vehicles do not hold, the rule "stop only if listed, defer otherwise", and the load gate. D2 is a negative result in this repository anyway (H-D2b). |
| Overhear and suppress or defer in LPWAN (D2) | Patents on alarm relaying by overhearing (the opposite effect: overhearing triggers a relay) and on repeating LoRa alarm frames at short intervals; a paper on implicit overhearing for multi-hop LoRa (PMC10145716) | No study found in the sources checked that defers or suppresses a node's own alert retries after overhearing; this is not a claim that none exists. |
| Slotted access from GPS time for alarms in LoRa (D3) | Tamang et al., MSWiM 2023 (slotted time after an event, random slot, abstract level); "Synchronous LoRa Communication by Exploiting Large-Area Out-of-Band Synchronization" (arXiv 2012.07480); a deterministic TDMA-on-LoRaWAN arXiv paper; LoRaWAN Class B beacons synchronised to GPS time | Slotted alarm access is known (the Tamang-style baseline is in the grid). D3 is a negative result (FRESH-B). |
| Provisional alert for crash alerting (D4) | US patent 9758120 (cloud-based accident notification: a provisional alarm under 40 bytes to a server, forwarded to emergency services unless cancelled; mobile broadband, not LoRa); ResQMesh (2026 conference paper, hybrid LoRa and cloud disaster alerts with an SOS verification engine) | A provisional-then-cancel crash alert is described in a patent over another network. No LoRa crash-alert version found in the sources checked (not a claim that none exists). |

Items for the author to open in full: A2S2-LoRaWAN (EURECOM publication 6039), DG-LoRa (PMC7922967), LoraHART, LoRa-REP, US 9758120, and the five papers of `CLOSEST_PRIOR_WORK.md`.

<!-- final-a:start -->
## Final run, Part A (2026-11-14): journal articles from 2021, 13 topics

Method, counts and opened items: `LIT_QUERIES_2021PLUS.md`. Per-claim result: `NOVELTY_MATRIX_2021PLUS.md`. Summary: LoRa accident alert systems are published in journals (topic 1, 32 hits), so the system idea is not claimed; retry and confirmed-messaging schemes for urgent LoRa traffic are published (topic 2), so D1 stays a supplement item with the Nessa-style baseline; aggregated acknowledgment exists (DG-LoRa, Sensors 2021), which closes D2 as a claim; formal analyses of LoRaWAN authentication exist (topic 5) but none with UPPAAL deadline bounds was found; no journal article from 2021 onwards was found in the sources checked on policy replay on public traces (topic 7), range requirements on real crash pulses (topic 9), duplicate audits of crash-pulse benchmarks (topic 10), synthetic crash-pulse generation (topic 12) or post-power-loss alert energy (topic 13). Scopus, Google Scholar and TRID not run; IEEE Xplore not run in this session (HTTP 418).
<!-- final-a:end -->
