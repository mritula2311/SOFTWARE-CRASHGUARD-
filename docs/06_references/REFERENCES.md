# References (checked list)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Checked reference list; a field is filled only if read in an opened document. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ASI = acceleration severity index; CV = cross-validation; DOI = digital object identifier; ESV = Enhanced Safety of Vehicles (conference); GAN = generative adversarial network; HIC = head injury criterion; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; IMU = inertial measurement unit; IOP = Institute of Physics; LoRa = long-range radio modulation; MAC = message authentication code; NCAP = New Car Assessment Programme; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; SAE = Society of Automotive Engineers; SD = standard deviation |
<!-- header:end -->

Every work cited in the journal-push documents and tables. A field is filled only if it was read in a document that was opened, on the date given; `NOT VERIFIED` marks every field that was not. "Opened" means that the page or PDF itself was read, not a search-result summary. Entries that could not be opened are listed at the end and support nothing.

Fields: A = authors, T = title, V = venue, Y = year, Vol = volume, P = pages or article number, DOI.

## Datasets and databases

| Key | Work | A | T | V | Y | Vol | P | DOI | Address | Opened | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | VZCrash paper | Bianconcini et al. (full author list NOT VERIFIED) | "VZCrash: A Large-Scale IMU Dataset of Ego-Vehicle Crashes" | arXiv 2606.06074; the dataset card says it was accepted and presented at the 2026 IEEE ITSC (proceedings details NOT VERIFIED) | 2026 (June) | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | https://arxiv.org/abs/2606.06074 | read in full 2026-11-10 (`docs/06_references/PRIOR_WORK.md`) | The paper states no licence. |
| R2 | VZCrash dataset card | the dataset authors (NOT VERIFIED beyond the card) | VZCrash dataset card | Hugging Face dataset `vzc-research-chapter/VZCrash` | 2026 | - | - | - | https://huggingface.co/datasets/vzc-research-chapter/VZCrash | card text in `data/raw/card/README.md`, read 2026-11-10 and 2026-11-12 | The card's metadata gives `license: cc-by-nc-4.0`. |
| R3 | NHTSA Vehicle Crash Test Database (NRD API) | US National Highway Traffic Safety Administration | Vehicle crash test database, public API | NHTSA | catalogue fetched 2026-11-12 | - | - | - | https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/swagger-ui/index.html | API reached 2026-11-12 (7,965 tests listed, 7,758 with instrumentation information) | "Public domain" is the statement of the project's own `docs/05_data_code/DATASET.md`; the NHTSA terms page was not opened here. |

## Accelerometer data sheets (opened 2026-11-12 unless stated)

| Key | Part | Document | Address opened | Revision printed | Notes |
|---|---|---|---|---|---|
| R4 | MPU-6050 | InvenSense MPU-6000/MPU-6050 Product Specification | https://www.haoyuelectronics.com/Attachment/GY-521/mpu6050.pdf | Rev 3.3, 2012-05-16 (a Rev 3.2 copy was also opened: https://alliance.seas.upenn.edu/~medesign/wiki/uploads/Guides/MPU6050_datasheet.pdf) | Distributor and university copies, not the manufacturer's site. |
| R5 | ADXL345 | Analog Devices ADXL345 Data Sheet | https://people.ece.ubc.ca/edc/7660.jan2018/ADXL345.pdf | Rev. E | University copy. |
| R6 | ADXL375 | Analog Devices ADXL375 Data Sheet | NOT VERIFIED: the address was not recorded when the local copy was opened on 2026-11-11 | Rev. B | Table text garbled; noise not read. |
| R7 | ADXL372 | Analog Devices ADXL372 Data Sheet | https://datasheet.chipsmall.com/ADXL372BCCZ-RL/497167.pdf | Rev. 0 (2017) | Distributor copy. |
| R8 | H3LIS331DL | STMicroelectronics H3LIS331DL data sheet DS9012 | https://static.chipdip.ru/lib/447/DOC029447674.pdf | Rev 4, October 2022 | Distributor copy. |
| R9 | LIS3DH | STMicroelectronics LIS3DH data sheet, Doc ID 17530 | https://cdn-shop.adafruit.com/datasheets/LIS3DH.pdf | Rev 1, May 2010 | Earliest revision; a later one may differ. |
| R10 | KX134-1211 | Kionix (ROHM) KX134-1211 Specifications | https://fscdn.rohm.com/kionix/en/datasheet/kx134-1211-e.pdf | Rev. 4.0, 24-Nov-2021 | |
| R11 | LSM6DSK320X | STMicroelectronics LSM6DSK320X data sheet DS15060 | https://components101.com/sites/default/files/2026-10/DS_lsm6dsk320x-compressed.pdf | Rev 1, July 2026 | Not the LSM6DSV32X named in the task, whose ST page timed out. |

## Patents and papers that were opened

| Key | A | T | V | Y | Vol | P | DOI | Address | Opened | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| R12 | Andres et al. (inventors R. M. Andres and D. A. McConnell; assignee Continental Automotive Systems US) | "Clipped sensor data estimator" | US patent 7,643,921 B2 | granted 2010-01-05 | - | - | - | local copy `data/raw/refs/us7643921.pdf` (address NOT VERIFIED) | 2026-11-11 | Slope extrapolation of clipped samples. |
| R13 | Chan et al. (full author list NOT VERIFIED) | "Evaluation of a Restoration Algorithm Applied to Clipped Tibial Acceleration Signals" | Sensors | 2023 | 23 (10) per the project's `spline_restore.py` (NOT re-verified) | 4609 per the same (NOT re-verified) | NOT VERIFIED | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10222349/ | opened in an earlier round (`docs/06_references/PRIOR_WORK.md`); title seen again in a search listing 2026-11-12 | The algorithm of Ruder et al. (not opened) is the one reported. |
| R14 | Wang and Zhao (given names NOT VERIFIED) | "HEROS-GAN: Honed-Energy Regularized and Optimal Supervised GAN for Enhancing Accuracy and Range of Low-Cost Accelerometers" | arXiv 2502.18064 | 2025 | - | - | NOT VERIFIED | https://arxiv.org/pdf/2502.18064 | summary page 2026-11-11; title from a search listing 2026-11-12 | |
| R15 | Stigson, Kullgren and Rosen | "Injury Risk Functions in Frontal Impacts Using Data from Crash Pulse Recorders" | Annals of Advances in Automotive Medicine | 2012 | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | https://pmc.ncbi.nlm.nih.gov/articles/PMC3503411/ | 2026-11-12 (abstract level) | 489 real frontal crashes; delta-V predicts injury risk. |
| R16 | NOT VERIFIED (authors not read) | IRCOBI 2020 paper IRC-20-79 on front crash rating programs with the Hybrid III dummy (title read only partly) | IRCOBI Conference | 2020 | - | IRC-20-79 | NOT VERIFIED | https://www.ircobi.org/wordpress/downloads/irc20/pdf-files/79.pdf | 2026-11-12 (abstract and introduction) | |
| R17 | Renault, Bondu, Cornuejols and Lemaire | "Early Classification of Time Series: A Survey and Benchmark" | Transactions on Machine Learning Research (per the arXiv page) | 2025 | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | https://arxiv.org/abs/2406.18332 | 2026-11-12 | |
| R18 | Achenchabe, Bondu, Cornuejols and Dachraoui | "Early Classification of Time Series. Cost-based Optimization Criterion and Algorithms" | arXiv 2005.09945 (venue NOT VERIFIED) | 2020 (revised 2021) | - | - | NOT VERIFIED | https://arxiv.org/abs/2005.09945 | 2026-11-12 | |
| R19 | Wu, Der and Keogh | "When is Early Classification of Time Series Meaningful?" | arXiv 2102.11487 (venue NOT VERIFIED) | 2021 (revised 2022) | - | - | NOT VERIFIED | https://arxiv.org/abs/2102.11487 | 2026-11-12 | |
| R20 | Taccari et al. (full list NOT VERIFIED) | "Classification of crash and near-crash events from dashcam videos and telematics data" | IEEE ITSC | 2018 | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | https://leotac.github.io/pdfs/itsc2018.pdf | read in full 2026-11-10 (`docs/06_references/PRIOR_WORK.md`) | |
| R21 | Kubin, Bianconcini, Coimbra de Andrade, Simoncini, Taccari and Sambo | "Deep Crash Detection from Vehicular Sensor Data with Multimodal Self-Supervision" | IEEE Transactions on Intelligent Transportation Systems | 2021 | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED | PDF text read (`docs/06_references/PRIOR_WORK.md`) | |
| R22 | Nouzovsky, Kohout, Vrtal and Novacek | "Dynamic tests of the culvert face within crashtests" | Acta Polytechnica CTU Proceedings | 2022 | 39 | 41-48 | 10.14311/APP.2022.39.0041 | https://doi.org/10.14311/APP.2022.39.0041 | read 2026-11-11 (`docs/05_data_code/SEVERITY.md`) | Source of the ASI class limits. |

## Cited from earlier rounds (opened 2026-11-11; fields exactly as recorded in `docs/06_references/NOVELTY_SCAN.md` section 1; all other fields NOT VERIFIED)

| Key | Work | Address or identifier | Opened as |
|---|---|---|---|
| R23 | Rafe and Das, CHOIR (groupwise and weighted conformal prediction for ordinal injury severity), 2026 | arXiv 2609.11592 | abstract page |
| R24 | Barber, Candes, Ramdas and Tibshirani, jackknife+ and CV+ | arXiv 1905.02928 | abstract page |
| R25 | Saerens, Latinne and Decaestecker, 2002, Neural Computation (prior-shift adjustment) | NOT VERIFIED | abstract page |
| R26 | Elkan, 2001, IJCAI (cost-sensitive decision rule) | NOT VERIFIED | summary page |
| R27 | Tamang et al., 2022, Sensors (LoRaWAN for factory alarms) | PMC8948738 | full page |
| R28 | Shao, Liew and Liang, 2020 (interrupt-and-access MAC for V2X warnings) | arXiv 2003.01906 | abstract page |
| R29 | Asteriou et al., 2024 (adaptive spatial scheduling of event traffic in LoRaWAN) | PMC11014082 | full page |
| R30 | Gao, Li and Ma, 2019, Sensors (Scyther analysis of the LoRaWAN join procedure) | PMC6928866 | full page |
| R31 | Dong et al., 2024, ISSRE (CSP model of LoRaWAN in PAT) | NOT VERIFIED | abstract page (ECNU record) |
| R32 | Wesemeyer et al., 2020, EuroS&P (LoRaWAN key establishment verification) | NOT VERIFIED | output record, no abstract |
| R33 | Reaz and Wunder, 2024 (Tamarin analysis of a permission voucher protocol) | arXiv 2412.16224 | abstract page |

## Named in the task or found only in search results: NOT opened, NOT used as support

| Work | What happened |
|---|---|
| Wusk and Gabler, 25th ESV, paper 25-0407 (delta-V, ASI and OLC weakly related to dummy injury criteria in frontal NCAP tests; R squared 0.006 to 0.056) | Named in the task as opened on 2026-11-12. In this session only a search listing of a TRID record (https://trid.trb.org/view/1482281, "Evaluation of Vehicle-Based Crash Severity Metrics Using Event Data Recorders") was seen and the page could not be fetched. Every number about it comes from the task text and is NOT VERIFIED. |
| Jao and Shkel 2022 (triangular-function reconstruction with Gaussian-process regression) | Searches on 2026-11-11 and 2026-11-12 did not return it. |
| Zhang et al. 2026 (peak-aware saturation compensation) | Searches on 2026-11-11 and 2026-11-12 did not return it. |
| Ruder et al. (spline restoration of clipped tibial signals) | Known only through Chan et al. |
| STMicroelectronics LSM6DSV32X data sheet and page | The ST address timed out. |
| Wald 1945 (sequential probability ratio test) | Mentioned as the origin of the test used in X8; not opened. |

<!-- PP:BEGIN -->
## Positive-results push (opened 2026-11-12 unless stated)

Fields: A = authors, T = title, V = venue, Y = year. A field is filled only if it appeared on the page that was opened; NOT VERIFIED marks the rest.

| Key | A | T | V | Y | Address opened | Not verified |
|---|---|---|---|---|---|---|
| P-R1 | Angelopoulos, Bates, Fisch, Lei, Schuster | Conformal Risk Control | arXiv 2208.02814 (the page lists ICLR 2024 in the search result only; the abstract page itself gives arXiv, latest version June 2025) | 2022 (submitted 2022-08-04) | https://arxiv.org/abs/2208.02814 | pages, DOI, ICLR details |
| P-R2 | Geifman, El-Yaniv | Selective Classification for Deep Neural Networks | arXiv 1705.08500 | 2017 (submitted 2017-05-23) | https://arxiv.org/abs/1705.08500 | proceedings details |
| P-R3 | Rafe, Das | CHOIR: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata | arXiv 2609.11592 (submitted 2026-09-10, revised 2026-10-01) | 2026 | https://arxiv.org/abs/2609.11592 | pages, DOI, peer-reviewed venue |
| P-R4 | Barber, Candes, Ramdas, Tibshirani | Predictive inference with the jackknife+ | arXiv 1905.02928 | 2019 (submitted 2019-05-08) | https://arxiv.org/abs/1905.02928 | journal details |
| P-R5 | emlearn project | emlearn (README) | GitHub repository | NOT VERIFIED | https://github.com/emlearn/emlearn | authors, version, licence, year |
| P-R6 | NHTSA (publisher, per the catalogue entry) | Vehicle Crash Test Database (data.gov catalogue entry) | catalog.data.gov; licence/rights field reads "public"; use constraint: not intended to support general consumer safety issues; last modified 2026-09-03; the entry describes tests from 1981 to 2015 | 2026 (entry) | https://catalog.data.gov/dataset/vehicle-crash-test-database | whether the same terms apply to the later tests fetched through the NRD API; nhtsa.gov pages returned HTTP 403 on 2026-11-12 and were not opened |
| P-R7 | Wusk, Gabler | (25th ESV paper 17-0407, delta-V, ASI and OLC against injury criteria) | NHTSA ESV proceedings | 2017 (conference number only) | NOT OPENED: https://www-nrd.nhtsa.dot.gov/pdf/ESV/Proceedings/25/25ESV-000407.pdf returned HTTP 403 | everything; only the author's description is used and no number |
| P-R8 | Jao, Shkel (2022); Zhang et al. (2026) | named by the author | - | - | NOT FOUND by search on 2026-11-11 and 2026-11-12 | everything; not cited |

Earlier references (datasets, data sheets, patents, papers) are in the table above this block.
<!-- PP:END -->

<!-- finish:start -->

## Finishing branch (2026-11-13)

| Key | Source | Opened | Use |
|---|---|---|---|
| F-R1 | IEEEtran.cls V1.8b (2015/08/26), CTAN mirror https://mirrors.ctan.org/macros/latex/contrib/IEEEtran/IEEEtran.cls | 2026-11-13 (downloaded) | paper class file in `paper/`; LPPL; no TeX distribution was available to compile |
| F-R2 | Semtech time-on-air formula (no note number may be cited) | NOT opened (redirect; two timeouts) | none; `lora.airtime_ms` is tested against the formula as transcribed |
| F-R3 | VZCrash dataset, Hugging Face revision 42e1482d005c0e545379d6cfa4939486c9fe4249 | user-supplied statement 2026-11-12 (author reply): CC BY-NC 4.0, the downloaded copy corresponds to this revision, identifiers or hashes may be cited | licence statement; not independently verified here |
| F-R4 | data.gov catalogue entry for the NHTSA Vehicle Crash Test Database | opened earlier (rights field reads "public"); nhtsa.gov terms pages returned HTTP 403 | NHTSA terms are not verified |

Unverified fields of other entries: `docs/06_references/REFERENCES_UNVERIFIED.md`.
<!-- finish:end -->

## Release additions (opened 2026-11-14; metadata only unless stated)

| Work | Fields verified | Source opened | Not verified |
|---|---|---|---|
| Tamang et al., Fast Transmission of Massive Concurrent Alarm Messages in LoRaWAN, MSWiM 2023, DOI 10.1145/3616388.3617542 | title, lead author, year, venue, DOI (OpenAlex record) | https://api.openalex.org (opened 2026-11-14) | abstract and full text |
| Khan, Jurdak and Portmann, A Model for Reliable Uplink Transmissions in LoRaWAN, DCOSS-IoT 2019, DOI 10.1109/dcoss.2019.00042 | title, authors, year, venue, DOI (OpenAlex record) | https://api.openalex.org (opened 2026-11-14) | abstract and full text |
| Rafe and Das, CHOIR: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata, arXiv 2609.11592 | title, authors, dates, opening two abstract sentences | https://arxiv.org/abs/2609.11592 (opened 2026-11-14) | the paper body, its results |

<!-- combined:start -->
## Combined run additions (2026-11-14)

Source: `docs/06_references/LITERATURE_STATUS.md` (sections 1 and 9). VERIFIED means the status file says the item was opened or read, with the fields listed there; a blank field is not verified.

| Key | Work | Fields verified | Status | Not verified |
|---|---|---|---|---|
| C-R1 | Wusk and Gabler, NHTSA ESV (PDF 25ESV-000407) | Virginia Tech; 140 frontal NCAP tests at about 56 km/h; delta-V, OLC, ASI against HIC, chest and pelvis criteria; R squared 0.006 to 0.056 | VERIFIED | year, DOI, given names |
| C-R2 | Stitzel et al., ESV paper 17-0319 | OTDA automatic crash notification; 38,970 NASS-CDS occupants; undertriage 20% to 11%, overtriage 54% to 34% | VERIFIED | year (from paper number) |
| C-R3 | Jao and Shkel, IEEE Sensors J. 22(1), 695 to 706, 2022, DOI 10.1109/JSEN.2021.3130120 | title, venue, pages, DOI; triangle approximation with Gaussian-process regression | VERIFIED (Xplore, 2026-11-13) | |
| C-R4 | Zhang et al., IEEE Sensors J. 26(19), 29298 to 29306, 2026, DOI 10.1109/JSEN.2026.3724900 | title, venue, pages, DOI; PEAR-VAE for saturation compensation | VERIFIED (Xplore, 2026-11-13) | given names |
| C-R5 | Sechaud, Jacques, Abry, Tachella, arXiv 2602.22279 | title, authors, topic (saturated data, audio and images) | VERIFIED | |
| C-R6 | Sisinni et al., IEEE WFCS 2021, pp. 15 to 18, DOI 10.1109/WFCS46889.2021.9483609 | title, authors, venue, pages, DOI | VERIFIED (record) | abstract |
| C-R7 | Sisinni, Carvalho, Ferrari, Flammini, Gidlund, IEEE Trans. Industrial Informatics ("Adding Redundancy to LoRaWAN for Emergency Communications at the Factory Floor") | title, venue, authors as listed | PARTLY VERIFIED | volume, year (2021 online or 2022), pages, DOI (10.1109/tii.2021.3124054 seen in a listing only), abstract |
| C-R8 | Dong, Zhu, Chen, Ge, ISSRE 2024, pp. 535 to 546, DOI 10.1109/ISSRE62328.2024.00057 | title, venue, pages, DOI; CSP models in PAT | VERIFIED (record) | |
| C-R9 | Wesemeyer, Boureanu, Smith, Treharne, EuroS&P 2020, DOI 10.1109/EuroSP48549.2020.00034 | title, authors, venue, DOI | VERIFIED (Xplore) | |
| C-R10 | Tamang, Heusse, Abrardo, Duda, ACM MSWiM 2023, DOI 10.1145/3616388.3617542 | title, authors, venue, slotted alarm access, 500 ms goal, SF7 to SF10 | VERIFIED | |
| C-R11 | Beltramelli et al., "LoRa beyond ALOHA", arXiv 2002.10732; and "Energy efficiency of slotted LoRaWAN communication with out-of-band synchronization", arXiv 2012.07579 | title, authors, content as listed | VERIFIED | dates |
| C-R12 | Khan, Jurdak, Portmann, DCOSS 2019, arXiv 2009.09397 | title, authors, Markov model of confirmed uplink | VERIFIED | |
| C-R13 | Liu, Fan, Xiang, Yang, arXiv 2605.23588 (2026) | title, authors, TDMA overlay, 20-node testbed | VERIFIED | date |
| C-R14 | Loh, Raffeck, Metzger, Hossfeld, WiMob 2021, pp. 313 to 318, DOI 10.1109/wimob52687.2021.9606388 | title, authors, venue, pages, DOI | VERIFIED (record) | |
| C-R15 | Kmec, Pavelka, Soltes, MM Science Journal, June 2021, DOI 10.17973/MMSJ.2021_6_2021013 | title, authors, venue, Kelvin model of a 56.17 km/h NCAP test | VERIFIED | stiffness and damping units look inconsistent: do not reuse the numbers |
| C-R16 | Rafe and Das, CHOIR, arXiv 2609.11592; Wei, Miyazaki, Sato, Traffic Injury Prevention 2025, DOI 10.1080/15389588.2025.2538725 | title, authors, dates, abstracts | VERIFIED (OpenAlex record and abstract) | paper text |
| C-R17 | Dima and Covaciu, IOP Conf. Ser.: Mater. Sci. Eng. 252, 012007 (CAR2017), DOI 10.1088/1757-899X/252/1/012007 | title, authors, venue, year, DOI, abstract (two accelerometers with different input ranges; 32-bit microcontroller; SD logger; filters from standards) | VERIFIED (abstract page opened 2026-11-14) | the range values, full text |
| C-R18 | DiMasi, Analysis of Automobile Crash Test Data and Recommendations for Acquiring and Filtering Accelerometer Data, DOT-TSC-NHTSA-75-2, June 1975 | title, author, date, report number, abstract | VERIFIED (record opened 2026-11-14, https://rosap.ntl.bts.gov/view/dot/11947) | PDF text |
| C-R19 | IEEE Std 1616-2004 (MVEDR), published 2005-02-10, Inactive-Reserved, superseded by 1616-2021 | title, dates, status, scope | VERIFIED (record opened 2026-11-14, https://standards.ieee.org/ieee/1616/3401) | standard text |
| C-R20 | Carneiro, Batista, Hirata Junior, Ullah, "A crash response system using LoRa-based V2X communications", IEEE/IFIP NOMS 2023, DOI 10.1109/NOMS56928.2023.10154409 | title, four authors, venue, year, DOI | VERIFIED (record, https://repositorio.usp.br/item/003148109) | abstract and content: cite only as existing prior work |

Not cited (UNVERIFIED): Marciano 2024 (not found), Minhas IEEE Access 2026 (not found), Mostefa ICCSM 2023 (listing only), the 2012 rear-end crash pulse generator paper (listing only), Kullgren, Lie and Tingvall 1995 (listing only), the 2026 fall-detection leakage audit (403), the ZigBee timestamp paper (empty page), Perkovic or Belani MeditCom 2023 (author doubtful), FC-HMAC (the DOI resolves to a different record), SAE J211 (not found), "Chen et al. GLOBECOM 2023" (not found).
<!-- combined:end -->

<!-- final-a:start -->
## Final run, Part A additions (opened 2026-11-14; abstract level through the OpenAlex record, metadata from Crossref)

Journal articles from 2021 onwards found with the queries in `LIT_QUERIES_2021PLUS.md`, plus the earlier-supplied items that were re-checked in Crossref. Full BibTeX with DOIs: `REFERENCES_2021PLUS.bib` (51 entries, all DOIs found in Crossref). A DOI found in Crossref confirms the metadata, not the content; content statements in the novelty matrix rest on the abstract only, and records without an abstract are marked there.

| Year | Title | Venue | DOI |
|---|---|---|---|
| 2020 | `Timestamp Scheme to Mitigate Replay Attacks in Secure ZigBee Networks` | IEEE Transactions on Mobile Computing | 10.1109/tmc.2020.3006905 |
| 2021 | `A data-driven, kinematic feature-based, near real-time algorithm for injury severity prediction of vehicle occupants` | Accident Analysis &amp; Prevention | 10.1016/j.aap.2021.106149 |
| 2021 | `Delta-v slope as an indicator of injury` | Traffic Injury Prevention | 10.1080/15389588.2021.1982615 |
| 2021 | `Reliability and Energy Consumption of LoRa With Bidirectional Traffic` | IEEE Communications Letters | 10.1109/lcomm.2021.3113134 |
| 2021 | `DG-LoRa: Deterministic Group Acknowledgment Transmissions in LoRa Networks for Industrial IoT Applications` | Sensors | 10.3390/s21041444 |
| 2021 | `A Key Management Protocol Based on the Hash Chain Key Generation for Securing LoRaWAN Networks` | Sensors | 10.3390/s21175838 |
| 2021 | `Reconstructing Vehicle and Occupant Motion from EDR Data in High Yaw Velocity Crashes` | SAE Technical Paper Series | 10.4271/2021-01-0892 |
| 2021 | `Prediction of Occupant Injuries for Improved eCall Efficiency` | International Journal of Vehicle Structures and Systems | 10.4273/ijvss.13.3.10 |
| 2022 | `Advanced Automatic Crash Notification Algorithm for Children` | Academic Pediatrics | 10.1016/j.acap.2022.02.016 |
| 2022 | `A Novel Session Key Update Scheme for LoRaWAN` | IEEE Access | 10.1109/access.2022.3200397 |
| 2022 | `A Reconstruction Filter for Saturated Accelerometer Signals Due to Insufficient FSR in Foot-Mounted Inertial Navigation System` | IEEE Sensors Journal | 10.1109/jsen.2021.3130120 |
| 2022 | `Comparative Analysis of an Urban LoRaWAN Deployment: Real World Versus Simulation` | IEEE Sensors Journal | 10.1109/jsen.2022.3193504 |
| 2022 | `A Secure and LoRaWAN Compatible User Authentication Protocol for Critical Applications in the IoT Environment` | IEEE Transactions on Industrial Informatics | 10.1109/tii.2021.3075440 |
| 2022 | `Adding Redundancy to LoRaWAN for Emergency Communications at the Factory Floor` | IEEE Transactions on Industrial Informatics | 10.1109/tii.2021.3124054 |
| 2022 | `A Configurable Mathematical Model for Single-Gateway LoRaWAN Performance Analysis` | IEEE Transactions on Wireless Communications | 10.1109/twc.2021.3136029 |
| 2022 | `LoED: LoRa and Edge Computing based System Architecture for Sustainable Forest Monitoring` | International Journal of Engineering Trends and Technology | 10.14445/22315381/ijett-v70i5p211 |
| 2022 | `TinyML-Based Fall Detection for Connected Personal Mobility Vehicles` | Computers, Materials &amp; Continua | 10.32604/cmc.2022.022610 |
| 2022 | `Motorcycle Crash Severity Estimation for Effective Emergency Response` | SAE Technical Paper Series | 10.4271/2022-28-0399 |
| 2023 | `Real‐time Internet of LoRa Things (IoLT)‐based accident detection and prevention system in vehicular networks towards smart city` | International Journal of Communication Systems | 10.1002/dac.5692 |
| 2023 | `MAKA: Multi-Factor Authentication and Key Agreement Scheme for LoRa-Based Smart Grid Communication Services` | IETE Journal of Research | 10.1080/03772063.2023.2225465 |
| 2023 | `Delay Optimization in LoRaWAN by Employing Adaptive Scheduling Algorithm With Unsupervised Learning` | IEEE Access | 10.1109/access.2023.3234188 |
| 2023 | `Mobility Adaptive Data Rate Based on Kalman Filter for LoRa-Empowered IoT Applications` | 2023 IEEE 20th Consumer Communications &amp; Networking Conference (CCNC) | 10.1109/ccnc51644.2023.10060330 |
| 2023 | `Expected Effect of Adopting the eCall System on Reducing Traffic-Related Deaths and Social Costs` | IEEE Intelligent Transportation Systems Magazine | 10.1109/mits.2022.3155178 |
| 2023 | `Lane change decision aid and warning system using LoRa-based vehicle-to-vehicle communication technology` | Bulletin of Electrical Engineering and Informatics | 10.11591/eei.v12i4.4662 |
| 2023 | `Evaluation of a Restoration Algorithm Applied to Clipped Tibial Acceleration Signals` | Sensors | 10.3390/s23104609 |
| 2024 | `Downlink Spreading Factor selection in LoRaWAN` | Computer Communications | 10.1016/j.comcom.2023.12.013 |
| 2024 | `Probabilistic performance evaluation of the class-A device in LoRaWAN protocol on the MAC layer` | Performance Evaluation | 10.1016/j.peva.2024.102446 |
| 2024 | `A novel single-channel edge computing LoRa gateway for real-time confirmed messaging` | Scientific Reports | 10.1038/s41598-024-59058-8 |
| 2024 | `A Lightweight Pre-Crash Occupant Injury Prediction Model Distills Knowledge From Its Post-Crash Counterpart` | Journal of Biomechanical Engineering | 10.1115/1.4063033 |
| 2024 | `Human Activity Recognition: A Comparative Study of Validation Methods and Impact of Feature Extraction in Wearable Sensors` | Algorithms | 10.3390/a17120556 |
| 2024 | `An Adaptive Data Rate Algorithm for Power-Constrained End Devices in Long Range Networks` | Mathematics | 10.3390/math12213371 |
| 2024 | `Integrating Fairness in Current Consumption of End Devices in Time-Slotted LoRa-based Wireless Sensor Network` | FUOYE Journal of Engineering and Technology | 10.4314/fuoyejet.v9i2.9 |
| 2025 | `Developing real-time IoT-based public safety alert and emergency response systems` | Scientific Reports | 10.1038/s41598-025-13465-7 |
| 2025 | `Privacy-Preserving Lightweight LoRaWAN Authentication Protocol for IoT Applications` | IEEE Internet of Things Journal | 10.1109/jiot.2025.3593886 |
| 2025 | `Enhanced Adaptive Data Rate and Power Control for Resilient and Energy-Efficient LoRaWAN` | IEEE Internet of Things Journal | 10.1109/jiot.2025.3609239 |
| 2025 | `Real Time Accident Detection and Emergency Response Using Drones, Machine Learning and LoRa Communication` | International Journal of Advanced Computer Science and Applications | 10.14569/ijacsa.2025.0160671 |
| 2025 | `Security analysis and improvement of key exchange protocol in LoRaWAN network` | International Journal of Sensor Networks | 10.1504/ijsnet.2025.149892 |
| 2025 | `Computer modelling of LoRa network parameters using the FLoRa simulator` | Technologies and Engineering | 10.30857/2786-5371.2025.1.7 |
| 2025 | `Performance Evaluation of a Mesh-Topology LoRa Network` | Sensors | 10.3390/s25051602 |
| 2025 | `U-Bend Accident Prevention Through Lora Communication` | Journal on Electronic and Automation Engineering | 10.46632/jeae/4/2/1 |
| 2026 | `A terrain-aware Fresnel zone simulator for LoRa link feasibility in non-Urban areas` | Internet of Things | 10.1016/j.iot.2026.102012 |
| 2026 | `Evaluating pre-impact fall detection: A user-independent assessment of deep learning models on the KFall dataset` | Measurement | 10.1016/j.measurement.2026.123369 |
| 2026 | `Predicting specific injury patterns from crash data: a GIDAS-based and manufacturer-independent logistic regression approach for next generation eCall` | Transportation Research Interdisciplinary Perspectives | 10.1016/j.trip.2026.102109 |
| 2026 | `High-optimized crash severity prediction: a calibrated, leakage-aware ensemble stacking framework for deployment-ready decision making` | Scientific Reports | 10.1038/s41598-026-73854-4 |
| 2026 | `A Signal-Aware Framework for Data Quality Assessment and Missing Data Mitigation in LoRaWAN Environmental IoT Networks` | IEEE Access | 10.1109/access.2026.3746655 |
| 2026 | `Peak-Aware Saturation Compensation for Low-Range Accelerometer Channels in Transient Impact Sensing` | IEEE Sensors Journal | 10.1109/jsen.2026.3724900 |
| 2026 | `Gateway-level Early Warning of LoRaWAN Link Degradation Using LoED Measurements` | Journal of Telecommunications and Information Technology | 10.26636/jtit.2026.4.2789 |
| 2026 | `Auditing Multimodal Fusion Benchmarks: Leakage, Attribution, and Calibration in Elderly Fall Detection` | Machine Learning and Knowledge Extraction | 10.3390/make8100298 |
| 2026 | `Direction-Aware Telematics Crash Detection and Injury Plausibility Scoring for False Injury Claim Mitigation` | International Journal of Latest Technology in Engineering Management &amp; Applied Science | 10.51583/ijltemas.2026.150600052 |
| 2026 | `Smart Vehicle Safety System Using IoT and Machine Learning for Accident Detection and Adaptive Cruise Control` | International Journal of Creative and Open Research in Engineering and Management | 10.55041/ijcope.v2i5.043 |
| 2026 | `Development of an Integrated Disaster Detector and Alert System` | Pantao (International Journal of the Humanities and Social Sciences) | 10.69651/pijhss05021060 |
<!-- final-a:end -->

<!-- vf:start -->
## Final verification run additions (2026-11-15)

Entries are in `REFERENCES_VF.bib` (built from Crossref records by `scripts/vf_make_bib_entries.py`; precedence over the older entries). New keys: Manuel2021_sn, Manuel2022_access, Alkhaiwani2023_su, Abdelhady2026_access, Kagai2026_telecom, Kumar2026_access, Yang2026_bioeng, Marciano2024_me, Jabbari2022_tii, Vinodhini2025_dac5692 (replaces Vinodhini2023_dac5692), Hetz2026_trip, Jameian2021_rsn, Liu2022_isprs, Meier2013_tamarin, Blanchet2016_proverif, Magrin2017_ns3lora, Riley2010_ns3, Sucerquia2017_sisfall, Dima2017_iop, loed_data20, sniffer, sisfall_zenodo, ucihar, fars, geonames, proverif. Corrected entries: Carneiro2023, dong2024, tamang2023, nessa2020, wesemeyer2020, khan2019 (full author names and DOI from Crossref), loed (author name), vzcrash (author list, revision), choir (title). The check against Crossref is in `docs/04_audits/REFERENCE_CHECK_VF.md`.
<!-- vf:end -->
