# Inventory (V0)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Branches, tags, preregistrations, result-key prefixes, release files and documents at the start of the verification run. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED_HW_FORMAT, TRACE_DRIVEN, SIMULATED, FORMAL, ANALYTICAL, HARDWARE, NOT_RUN |
| Abbreviations | ASI = acceleration severity index; NHTSA = National Highway Traffic Safety Administration; THIV = theoretical head impact velocity; UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

## Branches

| Branch | Commit | Subject |
|---|---|---|
| algo4 | 328c4b9 | SHA-256 of the algo4-v1 release archive |
| combined | 5f51c24 | Combined run: R1 to R3 studies, Holm verdicts (family S 2 of 6, family R 5 of 7), decision table, architecture document and diagram, claim audit, docs, paper block, tests |
| final | 6dd1c57 | SHA-256 of the paper-v1 release archive |
| finish | b6bc812 | Release manifest for crashguard-journal-v1 (archive not committed; ignored) |
| journal-push | 02a3859 | TIME_LOG: journal push packaging row (commit time) |
| main | 4c22588 | Clean run 3 reproduces the reference results; comparison and log; decision logged |
| positive-push | 981b124 | Closing: exploratory cross-validation, verification, claim audit, figures, progress; lint |
| redesign | 52b6cf0 | Release archive SHA-256 for redesign-v1.1 |
| release | 2ea085e | Makefile release target, reproduce notes |
| round5 | 5015e51 | Round 5 session 2: held-out results of L6 to L11, decision table, paper addition, audit |
| v2-algorithms | a56d2e0 | Decision log: T13 retry stopped, data/second/ is missing |
| verify | f30e25a | V1: step runner |

## Tags

| Tag | Object type | Peeled commit | Subject of the commit | Archive comment (git archive) | Match |
|---|---|---|---|---|---|
| algo4-v1 | tag | 9a5f8d2 | Round 4: paper additions (two negative-result rows, marked ProVerif paragraph), supplement | 9a5f8d2 | yes |
| baseline-before-8h | commit | ba824f5 | Part B: physics-based severity (delta-V, ASI, THIV, rollover, class), NHTSA validation, C  |  | no archive |
| combined-v1 | tag | 5f51c24 | Combined run: R1 to R3 studies, Holm verdicts (family S 2 of 6, family R 5 of 7), decision |  | archive carries no commit id |
| journal-push-v3 | tag | 02a3859 | TIME_LOG: journal push packaging row (commit time) |  | no archive |
| journal-v1 | commit | b6bc812 | Release manifest for crashguard-journal-v1 (archive not committed; ignored) |  | archive carries no commit id |
| paper-v1 | tag | 707e17b | Part C: Tamarin variant outcome (not decided), supplement text, docs blocks, DECISIONS | 707e17b | yes |
| positive-push-v1 | tag | 981b124 | Closing: exploratory cross-validation, verification, claim audit, figures, progress; lint |  | no archive |
| redesign-v1 | commit | 023d373 | Session 2 close: FRESH-B run once (D3 and H-D4a not supported), X1.3 cross-simulator verdi |  | archive carries no commit id |
| redesign-v1.1 | commit | dc02420 | Header of the regenerated audit document |  | archive carries no commit id |
| release-v1 | commit | 2ea085e | Makefile release target, reproduce notes |  | archive carries no commit id |
| round3-v1 | commit | fd2ac5f | Ruff fix in the Part B audit script |  | no archive |
| round5-v1 | commit | 5015e51 | Round 5 session 2: held-out results of L6 to L11, decision table, paper addition, audit | 5015e51 | yes |
| v1.0-round3 | tag | 4c22588 | Clean run 3 reproduces the reference results; comparison and log; decision logged |  | no archive |

## Preregistration files

| File | Size (bytes) | Title line |
|---|---|---|
| ALGORITHMS.md | 23930 | # Proposed algorithms: baselines, splits, metrics and rules (fixed before any result was looked at) |
| EXPERIMENTS.md | 5293 | # Experiments, metrics and figures |
| EXPERIMENTS_EXTRA.md | 37647 | # Extra software-only experiments X1 to X7 (N17 to N23): baselines, splits, metrics, primary variants and decision rules |
| PREREGISTRATION.md | 18221 | # Preregistration: uncertainty-aware severity-classified transmission (UA-SCT) |
| PREREGISTRATION_V11.md | 21163 | # Preregistration V11: simulated hardware-format validation (Part S) and architecture and protocol candidates (Part R) |
| PREREGISTRATION_V12.md | 42478 | # Preregistration V12: redesign round for the failed protocol and architecture algorithms |
| PREREGISTRATION_V13.md | 13555 | # Preregistration V13: paper items P0 (H-C3 refit) and P1 (two-stage alert in ns-3), and two checks |
| PREREGISTRATION_V14.md | 19352 | # Preregistration V14: round 3, simulator-independent evidence (T1 to T4) |
| PREREGISTRATION_V15.md | 21012 | # Preregistration V15: round 4, three algorithms aimed at mechanisms already exposed (A1 to A3) |
| PREREGISTRATION_V16.md | 54536 | # Preregistration V16: round 5, ten algorithms across the IoT layers and the project strategy (L1 to L10, R, D) |
| PREREGISTRATION_V2.md | 32112 | # Preregistration v2: five algorithm studies (written and committed before any v2 result exists) |
| PREREGISTRATION_V3.md | 20712 | # Preregistration v3: algorithm studies X1 to X3 and X5 to X8 (written and committed before any Block 4 or Block 4b result exists) |
| PREREGISTRATION_V4.md | 28287 | # Preregistration v4: the positive-results push, studies P1 to P4 (written and committed before any model of Blocks 1 to 4 is fitted) |
| PREREGISTRATION_V5.md | 35227 | # Preregistration v5: finishing study (written and committed before any run of Blocks B, C, F and G) |
| PREREGISTRATION_V7.md | 21889 | # Preregistration V7: release study (blocks P, Q and A) |

Addenda found by heading search (`Addendum`) in preregistration and decision files:

- docs\02_preregistration\PREREGISTRATION.md: # Addendum 1 (dated 2026-11-11, committed BEFORE the T1 to T4, T6 and T8 analyses are run)
- docs\02_preregistration\PREREGISTRATION_V12.md: ## 9. Addendum A (2026-11-14, written after the independent code review and before the freeze of D1 and D2; no DEV or FRESH-A result changes any hypothesis)
- docs\02_preregistration\PREREGISTRATION_V12.md: ## 10. Addendum B (2026-11-14, session 2; written before any D3 or D4 development run, before any firmware-path or ns-3 run of D1, and before FRESH-B is drawn)
- docs\02_preregistration\PREREGISTRATION_V12.md: ## 11. Addendum C (2026-11-14, after the redesign-v1 tag; written before any run of the items below)
- docs\02_preregistration\PREREGISTRATION_V16.md: ## 13. Addendum A1 (committed before the initial development run of any algorithm)
- docs\02_preregistration\PREREGISTRATION_V16.md: ## 14. Addendum A2 (after the independent code review, before the initial development run of any algorithm)
- docs\02_preregistration\PREREGISTRATION_V16.md: ## 15. Addendum S2 (session 2: datasets, roles, splits, hashes, designs of L6 to L11; committed before any session-2 run)
- docs\02_preregistration\PREREGISTRATION_V16.md: ### 15.9 Addendum S2.1 (L11; before any L11 run, including the build of any cache)
- docs\02_preregistration\PREREGISTRATION_V16.md: ### 15.10 Addendum S2.2 (L11; before any L11 run)
- docs\02_preregistration\PREREGISTRATION_V4.md: ### Addendum 1 (2026-11-12, written after the P1, P2 and P3 freezes were committed and before the sealed fold was scored; P4a had been scored and P4b was being scored)
- docs\02_preregistration\PREREGISTRATION_V5.md: ### Addendum 1 (2026-11-13; after B1, B2 and B3 were run; nothing in Blocks C, F or G had been run)
- docs\02_preregistration\PREREGISTRATION_V5.md: ### Addendum 2 (2026-11-13; written after Blocks B, C and G were run, and after the sealed F1 run; before the F1 cross-validation runs, the F2 test scoring and the F3 runs were evaluated)
- docs\02_preregistration\PREREGISTRATION_V5.md: ### Addendum 3 (2026-11-13; correction, written when the full test suite flagged the count)

## results.json keys by prefix

Total entries: 146704

| Prefix | Entries |
|---|---|
| s11 | 20803 |
| x6 | 17985 |
| v2 | 13701 |
| replay | 12684 |
| n16 | 11719 |
| f | 10452 |
| x | 4452 |
| t9 | 4250 |
| sh | 3971 |
| s9 | 3868 |
| p | 3858 |
| sel | 3697 |
| t8 | 3489 |
| s10 | 3476 |
| x7 | 1431 |
| x2 | 1361 |
| t3 | 1346 |
| n14s | 1329 |
| x5 | 1314 |
| t13 | 1304 |
| n14x | 1247 |
| s5 | 1143 |
| robust | 1040 |
| s2 | 984 |
| n20c | 967 |
| sevstudy | 959 |
| q | 957 |
| a4 | 748 |
| r3 | 736 |
| n14 | 704 |
| ar | 702 |
| r5 | 659 |
| t1 | 582 |
| rd | 535 |
| ua | 533 |
| severity_vzcrash | 516 |
| t6 | 494 |
| detector | 448 |
| t4 | 416 |
| pa | 371 |
| s13 | 364 |
| x4 | 352 |
| pp | 334 |
| t2 | 333 |
| ph | 290 |
| dupscan | 277 |
| vz | 271 |
| n24 | 236 |
| n15 | 225 |
| s6 | 222 |
| x3 | 215 |
| t7 | 206 |
| x1 | 203 |
| lovso | 160 |
| t10 | 159 |
| t5 | 148 |
| severity_synth | 132 |
| s3 | 120 |
| s4b | 113 |
| cchecks | 109 |
| s4 | 108 |
| nhtsa | 108 |
| s12 | 104 |
| peak_window | 75 |
| attacks | 69 |
| export_severity | 69 |
| hw | 64 |
| trigger_sweep | 60 |
| vzcrash | 39 |
| trigger | 30 |
| pad | 30 |
| forgery | 27 |
| lora | 27 |
| prev | 26 |
| s12x | 22 |
| leakage | 20 |
| ap_by_size | 16 |
| t14 | 16 |
| env | 15 |
| attacks_x | 14 |
| export | 10 |
| confusion3 | 9 |
| counter | 9 |
| gap | 8 |
| scalefree | 8 |
| candidate | 8 |
| lit | 6 |
| features | 4 |
| errors | 3 |

| Origin label | Entries |
|---|---|
| SIMULATED | 99868 |
| MEASURED_SOFTWARE | 39934 |
| SIMULATED_HW_FORMAT | 4013 |
| ANALYTICAL | 1774 |
| TRACE_DRIVEN | 681 |
| FORMAL | 237 |
| NOT_RUN | 141 |
| HARDWARE | 56 |

## Release files

| File | Bytes | SHA-256 | In git? |
|---|---|---|---|
| crashguard-algo4-v1.zip | 35410808 | f37752e040362638a8f48a52f8f616809e61f73093c2132c378cfd72c858bd50 | no |
| crashguard-combined-v1.zip | 53597656 | ce8f2abdc9b313d5150c00229314f61c34ec210b1a9bad95d2a5dc4bcdb975d2 | no |
| crashguard-journal-v1.zip | 49914531 | 1fe37712e1fe3c35030d89d77c5ba8e0387ba1a61b76d26dae7ceff53e9cf36f | no |
| crashguard-paper-v1.zip | 35194846 | 56669aa5f5cb088303b479931f42c5817bf8e44df583a9af3b0e78c22ba8d7ce | no |
| crashguard-redesign-v1.1.zip | 5961447 | 17e5c60ca806a3111bda5dd89dcb30c573b9ea39449a7932fb71bfe51ca3122c | no |
| crashguard-redesign-v1.zip | 5945407 | 3988c4b3aba94028a57b6c38006c38f8ee933cac9d5c254dd0eb71e9438feaf3 | no |
| crashguard-release-v1.zip | 50235222 | 381b9cbd72e0e88fc67aab4d06d2da997c1ed9729683186137abefe33b0da99c | no |
| crashguard-round5-v1.zip | 35656874 | d5ada257468d5dc7bc29a831ecc777405511555c863b1cbce65fc022475e95de | no |

## Documents under docs/ (non-archive)

- **docs\00_overview** (5): ARCHITECTURE.md, CLAIMS_FOR_COVER_LETTER.md, LIMITATIONS.md, PRD.md, PROJECT_STATUS.md
- **docs\01_protocol** (6): ATTACK_CASES.md, PACKET_FORMAT.md, PROTOCOL_MODEL.md, PROTOCOL_SCT.md, PROTOCOL_UA_SCT.md, THREAT_MODEL_SPOOFING.md
- **docs\02_preregistration** (15): ALGORITHMS.md, EXPERIMENTS.md, EXPERIMENTS_EXTRA.md, PREREGISTRATION.md, PREREGISTRATION_V11.md, PREREGISTRATION_V12.md, PREREGISTRATION_V13.md, PREREGISTRATION_V14.md, PREREGISTRATION_V15.md, PREREGISTRATION_V16.md, PREREGISTRATION_V2.md, PREREGISTRATION_V3.md, PREREGISTRATION_V4.md, PREREGISTRATION_V5.md, PREREGISTRATION_V7.md
- **docs\03_results** (39): A4_A3_PROVERIF.md, A4_CODE_VERIFICATION.md, A4_DECISION_TABLE.md, A4_RESULTS.md, ASSUMPTIONS.md, CLAIM_EVIDENCE.md, CODE_VERIFICATION.md, COMBINED_VERDICTS.md, DIAGNOSIS_GSCA.md, DIAGNOSIS_OSDR.md, DIAGNOSIS_R2.md, DIAGNOSIS_SYNTH.md, DIAGNOSIS_UASCT.md, FINISH_RESULTS.md, H_C3_PROVENANCE.md, JOURNAL_RESULTS.md, NEGATIVES_REGISTER.md, PAPER_P1_R3_NS3.md, PH_INTEGRITY_REPORT.md, POSITIVE_PUSH_RESULTS.md, R5_CODE_VERIFICATION.md, REDESIGN_A_RESULTS.md, REDESIGN_B_RESULTS.md, REDESIGN_DECISION_TABLE.md, RELEASE_RESULTS.md, RESULTS_SO_FAR.md, ROUND3_DECISION_TABLE.md, ROUND3_RESULTS.md, ROUND5_DECISION_TABLE.md, ROUND5_RESULTS.md, SIMHW_RESULTS.md, SIMHW_S4_CASES.md, SIMHW_VARIANTS.md, STATS_AUDIT.md, STATUS_REVERIFY.md, V2_RESULTS.md, XSIM_BUILD.md, XSIM_CALIBRATION.md, XSIM_VERDICTS.md
- **docs\04_audits** (18): A4_CLAIM_AUDIT.md, ALGORITHMS_COMPLIANCE.md, CLAIM_AUDIT.md, COMBINED_CLAIM_AUDIT.md, FINAL_VERIFICATION.md, FINISH_AUDIT.md, INVENTORY.md, PP_CLAIM_AUDIT.md, PP_PAPER_CLAIM_AUDIT.md, PP_REFERENCE_CHECK.md, PREREG_V4_AUDIT.md, R5_CLAIM_AUDIT.md, REDESIGN_CLAIM_AUDIT.md, RELEASE_CLAIM_AUDIT.md, ROUND3_CLAIM_AUDIT.md, V2_CLAIM_AUDIT.md, VZCRASH_AUDIT.md, vzcrash_email_draft.md
- **docs\05_architecture** (2): ARCHITECTURE.md, architecture_layers.svg
- **docs\05_data_code** (17): DATA_AND_CODE_STATEMENT.md, DATASET.md, DATASET_FACTS.md, DATASET_FACTS_QUALITY.md, FEATURES.md, FIGURES_TABLES.md, FIRMWARE_SYNC.md, HARDWARE_READINESS.md, HARDWARE_SCHEMA.md, RELEASE_MANIFEST.md, REPRODUCE.md, REPRODUCE_FINISH.md, SEALED_SPLIT.md, SENSOR_DATASHEETS.md, SEVERITY.md, SYNTHETIC_ASSUMPTIONS.md, SYNTHETIC_PROVENANCE.md
- **docs\06_references** (18): CHANGES.md, CLOSEST_PRIOR_WORK.md, CrashGuard_Literature_Status.md, CrashGuard_Literature_Survey_2021plus.md, LIT_QUERIES_2021PLUS.md, LIT_QUERIES_ROUND4.md, LIT_QUERIES_ROUND5.md, LITERATURE_STATUS.md, LITERATURE_STATUS_RELEASE_V1.md, MANUAL_SEARCH_CHECKLIST.md, NOVELTY.md, NOVELTY_MATRIX_2021PLUS.md, NOVELTY_SCAN.md, PRIOR_WORK.md, REFERENCES.md, REFERENCES_2021PLUS.bib, REFERENCES_UNVERIFIED.md, SCOPUS_STRINGS.md
- **docs\07_log** (6): CLEANUP_LOG.md, DECISIONS.md, NOT_RUN.md, PATH_MAP.md, PROGRESS.md, TIME_LOG.md
- **docs\08_hardware** (1): R3_BENCH_PROTOCOL.md
- **docs\09_review** (1): REVIEWER_RESPONSES.md
- **docs** (2): README.md, VZCRASH_AUDIT.md
