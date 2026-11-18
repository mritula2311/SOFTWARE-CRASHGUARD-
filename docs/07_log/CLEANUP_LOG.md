# Cleanup log

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Inventory before the reorganisation, every move, deletion and rewrite, and the checks after it. |
| Evidence labels used | NOT_RUN |
| Abbreviations | FPR = false-positive rate; IEEE = Institute of Electrical and Electronics Engineers |
<!-- header:end -->

Status: current. Date: 2026-11-13. Owner: Mritula S. Scope: release branch, Block R (repository reorganisation). Evidence labels: none (no result is produced here).

This file is written in three parts. Part 1 is the inventory taken BEFORE any file was moved (paths are the old paths). Part 2 lists the moves, deletions and rewrites. Part 3 lists the checks run after the move.

## Part 1. Inventory (before any move)

Columns: size in bytes; date of the last commit that touched the file; references from `results/results.json` (R), code (C, count of code files), tests (T), other Markdown documents (D); status is one of current, superseded, duplicate, scratch.

Counts: 831 tracked files in total; 74 Markdown files; the code files under `src/` and `tests/` are counted but not listed. `data/hardware/` (5 tracked files) is out of scope for this release: its content was not opened and it is not changed; it is listed in the group table only.

### 1a. Markdown files and single non-code files

| Path | Bytes | Last commit | R | C | T | D | Status | Replaced by / note |
|---|---:|---|---:|---:|---:|---:|---|---|
| `.gitattributes` | 35 | 2026-11-11 | 0 | 0 | 0 | 0 | current |  |
| `.github/workflows/c_checks.yml` | 1107 | 2026-11-11 | 0 | 1 | 0 | 4 | current |  |
| `.gitignore` | 271 | 2026-11-13 | 0 | 0 | 0 | 0 | current |  |
| `.zenodo.json` | 814 | 2026-11-13 | 0 | 2 | 0 | 6 | current |  |
| `CITATION.cff` | 770 | 2026-11-13 | 0 | 2 | 0 | 6 | current |  |
| `CITATION.md` | 301 | 2026-11-10 | 0 | 1 | 0 | 1 | current |  |
| `CLAUDE.md` | 3863 | 2026-11-10 | 0 | 4 | 1 | 9 | current |  |
| `LICENSE` | 11357 | 2026-11-13 | 0 | 2 | 0 | 6 | current |  |
| `NOTICE` | 967 | 2026-11-13 | 0 | 3 | 0 | 7 | current |  |
| `PROGRESS.md` | 15391 | 2026-11-13 | 0 | 3 | 1 | 6 | current |  |
| `README.md` | 13701 | 2026-11-13 | 1 | 14 | 2 | 8 | current |  |
| `REPRODUCE.md` | 30833 | 2026-11-12 | 0 | 9 | 2 | 12 | current | main reproduction guide (scope: the main pipeline) |
| `b2.log` | 430 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `c_bundle/manifest.json` | 2364 | 2026-11-11 | 1 | 5 | 1 | 0 | current |  |
| `cmp1.txt` | 2477 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `cmp2.txt` | 2630 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `cmp3.txt` | 1947 | 2026-11-12 | 0 | 0 | 0 | 2 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `crashclip/README.md` | 7817 | 2026-11-12 | 1 | 14 | 2 | 8 | current |  |
| `crashclip/parts.json` | 8114 | 2026-11-12 | 0 | 1 | 0 | 1 | current |  |
| `crashclip/records.csv` | 57866 | 2026-11-12 | 0 | 3 | 1 | 1 | current |  |
| `crashclip/split.json` | 874 | 2026-11-12 | 0 | 1 | 0 | 1 | current |  |
| `docs/ALGORITHMS.md` | 23332 | 2026-11-11 | 0 | 15 | 0 | 13 | current |  |
| `docs/ALGORITHMS_COMPLIANCE.md` | 24657 | 2026-11-11 | 0 | 1 | 0 | 4 | current |  |
| `docs/ALL_DOCS_COMBINED.md` | 817255 | 2026-11-13 | 0 | 3 | 1 | 2 | duplicate | docs/README.md (index) and the individual documents concatenation of every document; generated copy, not a source |
| `docs/ARCHITECTURE.md` | 2244 | 2026-11-10 | 1 | 2 | 0 | 2 | current |  |
| `docs/ATTACK_CASES.md` | 8753 | 2026-11-11 | 0 | 4 | 0 | 7 | current |  |
| `docs/CLAIMS_FOR_COVER_LETTER.md` | 2366 | 2026-11-13 | 0 | 5 | 0 | 2 | current |  |
| `docs/CLAIMS_FOR_COVER_LETTER_V1.md` | 7173 | 2026-11-13 | 0 | 1 | 0 | 2 | superseded | docs/CLAIMS_FOR_COVER_LETTER.md older generated claim list from the journal-v1 push; the current list covers all rounds |
| `docs/CLAIM_AUDIT.md` | 4293 | 2026-11-11 | 0 | 2 | 0 | 5 | current |  |
| `docs/CLAIM_EVIDENCE.md` | 44294 | 2026-11-12 | 0 | 9 | 0 | 15 | current |  |
| `docs/CLAUDE_CODE_PROMPT.md` | 10113 | 2026-11-10 | 0 | 0 | 0 | 1 | scratch | CLAUDE.md and docs/PRD.md the first build prompt; its content is in CLAUDE.md and the PRD |
| `docs/DATASET.md` | 22307 | 2026-11-11 | 0 | 4 | 0 | 9 | current |  |
| `docs/DATASET_FACTS.md` | 4945 | 2026-11-10 | 0 | 0 | 0 | 5 | current |  |
| `docs/DATASET_FACTS_QUALITY.md` | 2184 | 2026-11-10 | 0 | 1 | 0 | 2 | current |  |
| `docs/DATA_AND_CODE_STATEMENT.md` | 3522 | 2026-11-13 | 0 | 2 | 0 | 4 | current |  |
| `docs/DECISIONS.md` | 110241 | 2026-11-13 | 1 | 26 | 1 | 25 | current |  |
| `docs/EXPERIMENTS.md` | 4681 | 2026-11-11 | 0 | 2 | 0 | 5 | current |  |
| `docs/EXPERIMENTS_EXTRA.md` | 36643 | 2026-11-11 | 0 | 19 | 0 | 7 | current |  |
| `docs/FEATURES.md` | 2199 | 2026-11-10 | 0 | 5 | 0 | 6 | current |  |
| `docs/FIGURES_TABLES.md` | 32155 | 2026-11-11 | 0 | 3 | 0 | 4 | current |  |
| `docs/FINISH_AUDIT.md` | 3004 | 2026-11-13 | 0 | 1 | 0 | 3 | current |  |
| `docs/FINISH_RESULTS.md` | 6003 | 2026-11-13 | 0 | 2 | 0 | 6 | current |  |
| `docs/FIRMWARE_SYNC.md` | 4954 | 2026-11-11 | 0 | 3 | 0 | 5 | current |  |
| `docs/FIRST_PROMPT.md` | 454 | 2026-11-10 | 0 | 0 | 0 | 1 | scratch | CLAUDE.md and docs/PRD.md the first message of the first session; no content that the PRD lacks |
| `docs/HARDWARE_READINESS.md` | 3562 | 2026-11-11 | 0 | 2 | 0 | 4 | current |  |
| `docs/HARDWARE_SCHEMA.md` | 1575 | 2026-11-10 | 0 | 2 | 0 | 6 | current |  |
| `docs/JOURNAL_RESULTS.md` | 10355 | 2026-11-13 | 0 | 1 | 0 | 5 | current |  |
| `docs/LIMITATIONS.md` | 8183 | 2026-11-12 | 0 | 2 | 0 | 2 | current |  |
| `docs/MANUAL_SEARCH_CHECKLIST.md` | 15540 | 2026-11-11 | 0 | 2 | 0 | 9 | superseded | docs/06_references/SCOPUS_STRINGS.md the checklist for the author to run searches; replaced by the search-string file with a results table |
| `docs/NEGATIVES_REGISTER.md` | 8087 | 2026-11-13 | 0 | 2 | 0 | 6 | current |  |
| `docs/NOT_RUN.md` | 7612 | 2026-11-13 | 0 | 3 | 0 | 5 | current |  |
| `docs/NOVELTY.md` | 16588 | 2026-11-12 | 0 | 3 | 0 | 5 | current |  |
| `docs/NOVELTY_SCAN.md` | 22890 | 2026-11-12 | 0 | 2 | 0 | 10 | current |  |
| `docs/PACKET_FORMAT.md` | 6320 | 2026-11-11 | 0 | 6 | 0 | 10 | current |  |
| `docs/POSITIVE_PUSH_RESULTS.md` | 22134 | 2026-11-13 | 0 | 3 | 0 | 7 | current |  |
| `docs/PP_CLAIM_AUDIT.md` | 694 | 2026-11-12 | 0 | 2 | 0 | 4 | current |  |
| `docs/PRD.md` | 7272 | 2026-11-10 | 0 | 0 | 0 | 3 | current |  |
| `docs/PREREGISTRATION.md` | 17503 | 2026-11-11 | 0 | 15 | 0 | 8 | current |  |
| `docs/PREREGISTRATION_V2.md` | 31577 | 2026-11-12 | 0 | 17 | 1 | 7 | current |  |
| `docs/PREREGISTRATION_V3.md` | 20120 | 2026-11-12 | 0 | 11 | 0 | 5 | current |  |
| `docs/PREREGISTRATION_V4.md` | 27537 | 2026-11-12 | 0 | 16 | 1 | 5 | current |  |
| `docs/PREREGISTRATION_V5.md` | 34387 | 2026-11-13 | 1 | 15 | 1 | 5 | current |  |
| `docs/PREREG_V4_AUDIT.md` | 5599 | 2026-11-13 | 0 | 2 | 0 | 3 | current |  |
| `docs/PRIOR_WORK.md` | 40609 | 2026-11-11 | 0 | 2 | 0 | 13 | current |  |
| `docs/PROTOCOL_MODEL.md` | 13086 | 2026-11-11 | 1 | 6 | 0 | 5 | current |  |
| `docs/PROTOCOL_SCT.md` | 6817 | 2026-11-11 | 0 | 6 | 0 | 6 | current |  |
| `docs/PROTOCOL_UA_SCT.md` | 6340 | 2026-11-11 | 0 | 0 | 0 | 2 | current |  |
| `docs/REFERENCES.md` | 13733 | 2026-11-13 | 0 | 4 | 0 | 6 | current |  |
| `docs/REFERENCES_UNVERIFIED.md` | 2496 | 2026-11-13 | 0 | 2 | 0 | 3 | current |  |
| `docs/RELEASE_MANIFEST.md` | 1015 | 2026-11-13 | 0 | 1 | 0 | 2 | current |  |
| `docs/REPRODUCE.md` | 9639 | 2026-11-13 | 0 | 9 | 2 | 11 | current | reproduction guide for the finishing round (scope: branch finish) |
| `docs/RESULTS_SO_FAR.md` | 1318 | 2026-11-10 | 0 | 0 | 0 | 1 | current | author-supplied hardware progress notes (not read by this release; external numbers) |
| `docs/SEALED_SPLIT.md` | 8687 | 2026-11-12 | 0 | 5 | 1 | 7 | current |  |
| `docs/SENSOR_DATASHEETS.md` | 3687 | 2026-11-12 | 0 | 4 | 0 | 6 | current |  |
| `docs/SEVERITY.md` | 12406 | 2026-11-11 | 1 | 9 | 0 | 11 | current |  |
| `docs/STATS_AUDIT.md` | 12045 | 2026-11-12 | 0 | 6 | 0 | 5 | current |  |
| `docs/SYNTHETIC_ASSUMPTIONS.md` | 8265 | 2026-11-13 | 1 | 6 | 0 | 4 | current |  |
| `docs/THREAT_MODEL_SPOOFING.md` | 3690 | 2026-11-11 | 0 | 2 | 0 | 7 | current |  |
| `docs/TIME_LOG.md` | 5914 | 2026-11-12 | 0 | 1 | 0 | 1 | current |  |
| `docs/V2_CLAIM_AUDIT.md` | 3664 | 2026-11-12 | 0 | 0 | 0 | 2 | current |  |
| `docs/V2_RESULTS.md` | 18606 | 2026-11-12 | 0 | 4 | 1 | 7 | current |  |
| `docs/VZCRASH_AUDIT.md` | 9252 | 2026-11-13 | 0 | 2 | 0 | 6 | current |  |
| `docs/vzcrash_email_draft.md` | 3656 | 2026-11-13 | 0 | 2 | 0 | 4 | current |  |
| `fin_c.log` | 1153 | 2026-11-13 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `fin_f1.log` | 87 | 2026-11-13 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `fin_f1_cv.log` | 70 | 2026-11-13 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `fin_f2.log` | 5210 | 2026-11-13 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `fin_g.log` | 20 | 2026-11-13 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `firmware_export/.gitkeep` | 0 | 2026-11-10 | 0 | 0 | 0 | 0 | scratch | empty placeholder; redundant when the directory has other tracked files |
| `firmware_export/benchmark_rf.ino` | 2940 | 2026-11-10 | 1 | 6 | 0 | 7 | current |  |
| `firmware_export/crashguard_rf.h` | 55404 | 2026-11-10 | 1 | 6 | 1 | 4 | current |  |
| `firmware_export/crashguard_rf_candidate.h` | 169560 | 2026-11-11 | 1 | 5 | 0 | 3 | current |  |
| `firmware_export/severity.h` | 18833 | 2026-11-11 | 1 | 12 | 0 | 10 | current |  |
| `merge/.gitkeep` | 0 | 2026-11-10 | 0 | 0 | 0 | 0 | scratch | empty placeholder; redundant when the directory has other tracked files |
| `p1_cv.log` | 4475 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p1_cv_cnn.log` | 3553 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p1_fit.log` | 761 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p4a_eval.log` | 49 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p4a_sweep.log` | 332 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p4b_eval.log` | 423 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p4c_eval.log` | 1397 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p4c_eval2.log` | 1857 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `p4d.log` | 681 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `paper/ABSTRACT_FACTS.md` | 1338 | 2026-11-13 | 0 | 2 | 0 | 2 | current |  |
| `paper/IEEEtran.cls` | 281957 | 2026-11-13 | 0 | 1 | 0 | 3 | current |  |
| `paper/main.tex` | 9068 | 2026-11-13 | 0 | 2 | 0 | 4 | current |  |
| `pc.log` | 1136 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `report/.gitkeep` | 0 | 2026-11-10 | 0 | 0 | 0 | 0 | scratch | empty placeholder; redundant when the directory has other tracked files |
| `report/novelty_summary.md` | 129529 | 2026-11-12 | 0 | 4 | 0 | 13 | current |  |
| `report/software_results.md` | 213502 | 2026-11-11 | 0 | 4 | 0 | 12 | current |  |
| `requirements.lock` | 159940 | 2026-11-11 | 1 | 2 | 0 | 5 | current |  |
| `requirements.txt` | 377 | 2026-11-12 | 1 | 3 | 0 | 7 | current |  |
| `rerun_prefix.log` | 8905 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `results/results.json` | 34307136 | 2026-11-13 | 1 | 73 | 7 | 47 | current |  |
| `run1.log` | 97563 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `run2.log` | 97406 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `run3.log` | 110582 | 2026-11-12 | 0 | 0 | 0 | 2 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `s11.log` | 6712 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `sel_study.log` | 10040 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `src/crashguard/.gitkeep` | 0 | 2026-11-10 | 0 | 0 | 0 | 0 | scratch | empty placeholder; redundant when the directory has other tracked files |
| `t13_harvest.log` | 235 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `t13_heldout.log` | 3966 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `t13_neardup.log` | 2696 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `t4.log` | 1080 | 2026-11-11 | 0 | 1 | 1 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `t5.log` | 896 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `t7.log` | 2485 | 2026-11-11 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `t8.log` | 1017 | 2026-11-11 | 0 | 2 | 1 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `tests/dummy/.gitkeep` | 0 | 2026-11-10 | 0 | 0 | 0 | 0 | scratch | empty placeholder; redundant when the directory has other tracked files |
| `tests/dummy/README.md` | 170 | 2026-11-10 | 1 | 14 | 2 | 8 | current |  |
| `vz_audit.log` | 5833 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `vz_leakage.log` | 121 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `x1.log` | 1263 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `x5.log` | 3386 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `x7.log` | 13352 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `x8.log` | 3659 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |
| `x_common.log` | 257 | 2026-11-12 | 0 | 0 | 0 | 0 | scratch | run log or comparison output from an earlier session; kept as evidence in the archive, not deleted |

### 1b. Directories of generated or bundled files (one row per directory)

| Directory | Files | Bytes | Last commit | R | C | T | D | Status | Note |
|---|---:|---:|---|---:|---:|---:|---:|---|---|
| `results/figures/` | 82 | 9096397 | 2026-11-13 | 0 | 2 | 0 | 31 | current | generated output or bundle; tagged result files are not edited |
| `results/tables/` | 212 | 71994182 | 2026-11-13 | 109 | 299 | 5 | 72 | current | generated output or bundle; tagged result files are not edited |
| `results/paper/figures/` | 14 | 1060525 | 2026-11-12 | 0 | 2 | 0 | 1 | current | generated output or bundle; tagged result files are not edited |
| `results/paper/` | 106 | 472234 | 2026-11-12 | 0 | 7 | 0 | 19 | current | generated output or bundle; tagged result files are not edited |
| `results/synthetic/` | 7 | 1618722 | 2026-11-13 | 1 | 6 | 0 | 8 | current | generated output or bundle; tagged result files are not edited |
| `results/surrogate/` | 3 | 11835 | 2026-11-13 | 1 | 15 | 2 | 8 | current | generated output or bundle; tagged result files are not edited |
| `c_bundle/forest_10x9/` | 4 | 848436 | 2026-11-11 | 1 | 17 | 4 | 4 | current | generated output or bundle; tagged result files are not edited |
| `c_bundle/forest_15x6/` | 4 | 350280 | 2026-11-11 | 1 | 17 | 4 | 4 | current | generated output or bundle; tagged result files are not edited |
| `c_bundle/n14_sat_synthetic/` | 4 | 183734 | 2026-11-11 | 1 | 23 | 3 | 10 | current | generated output or bundle; tagged result files are not edited |
| `c_bundle/severity_synthetic/` | 4 | 1005923 | 2026-11-11 | 1 | 23 | 3 | 10 | current | generated output or bundle; tagged result files are not edited |
| `crashclip/baselines/` | 11 | 2130448 | 2026-11-12 | 8 | 32 | 0 | 7 | current | generated output or bundle; tagged result files are not edited |
| `release/vzcrash_audit_for_authors/` | 5 | 195313 | 2026-11-13 | 0 | 3 | 0 | 3 | current | generated output or bundle; tagged result files are not edited |
| `paper/generated/` | 6 | 6829 | 2026-11-13 | 0 | 1 | 0 | 4 | current | generated output or bundle; tagged result files are not edited |
| `data/hardware/` | 5 | n/a | n/a | n/a | n/a | n/a | n/a | out of scope | not opened in this release (rule: software only) |

R, C, T and D in 1b are the sum of per-file reference counts.

### 1c. Byte-identical duplicates among tracked files

| SHA-256 (first 16) | Paths | Decision |
|---|---|---|
| `2221fa575289684e` | `crashclip/baselines/p1_sealed_by_mode.csv`, `results/tables/p1_sealed_by_mode.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `25e93157285c6ba2` | `results/figures/s10_ppv_recall.pdf`, `results/paper/figures/s10_ppv_recall.pdf` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `26d5ec5f07b6c398` | `crashclip/baselines/p2_sealed.csv`, `results/tables/p2_sealed.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `2b9d3c2cd39df399` | `crashclip/baselines/p3a_risk_coverage.csv`, `results/tables/p3a_risk_coverage.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `2cb7aef3503b4a97` | `crashclip/baselines/p1_sealed.csv`, `results/tables/p1_sealed.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `549daf496f5e30ae` | `results/tables/v2_a_metrics.csv`, `results/tables/v2_a_run1_insample_residuals_metrics.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `57cce40bdfeb8f0b` | `c_bundle/forest_10x9/harness.c`, `c_bundle/forest_15x6/harness.c` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `5ddd3f61b2790247` | `crashclip/baselines/p1_validation.csv`, `results/tables/p1_validation.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `60fa5930abe38cd2` | `results/figures/s10_ppv_recall.png`, `results/paper/figures/s10_ppv_recall.png` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `614c1f938dbc92d7` | `results/figures/t2_pareto.pdf`, `results/paper/figures/t2_pareto.pdf` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `713335820314f113` | `crashclip/baselines/p4a_sweep.csv`, `results/tables/p4a_sweep.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `7f744fec5a6ab6f4` | `crashclip/baselines/p3b_cells.csv`, `results/tables/p3b_cells.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `85d70d1144fa1d11` | `c_bundle/n14_sat_synthetic/severity.h`, `c_bundle/severity_synthetic/severity.h`, `firmware_export/severity.h` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `955dcf8d6eb7bcb4` | `crashclip/baselines/p4c_guarantee.csv`, `results/tables/p4c_guarantee.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `a00b999cebda4509` | `crashclip/baselines/p4b_augmentation.csv`, `results/tables/p4b_augmentation.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `aa4988019e6e3a4a` | `c_bundle/forest_10x9/crashguard_rf.h`, `firmware_export/crashguard_rf_candidate.h` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `c368fe90992832b3` | `crashclip/baselines/p_b2_table.csv`, `results/tables/p_b2_table.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `c398d37ce1b91214` | `c_bundle/forest_15x6/crashguard_rf.h`, `firmware_export/crashguard_rf.h` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `c5f0b8a652f4433c` | `results/figures/v2_e_tag_curve.png`, `results/paper/figures/v2_e_tag_curve.png` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `e362af88db1e31cb` | `results/figures/v2_e_tag_curve.pdf`, `results/paper/figures/v2_e_tag_curve.pdf` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `fbbb8876f6612057` | `release/vzcrash_audit_for_authors/groups_with_array_hashes.csv`, `results/paper/vz_audit_cross_split_groups.csv`, `results/tables/vz_audit_cross_split_groups.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `fcf7019bc666bf92` | `crashclip/baselines/p4d_cnn.csv`, `results/tables/p4d_cnn.csv` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |
| `fe6a3ec2f5bb34bc` | `results/figures/t2_pareto.png`, `results/paper/figures/t2_pareto.png` | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |

### 1d. Empty files

| Path | Decision |
|---|---|
| `firmware_export/.gitkeep` | delete if the directory has other tracked files (placeholder), see Part 2 |
| `merge/.gitkeep` | delete if the directory has other tracked files (placeholder), see Part 2 |
| `report/.gitkeep` | delete if the directory has other tracked files (placeholder), see Part 2 |
| `results/paper/missing_keys.txt` | kept: tagged generated output (written empty by a script on purpose) |
| `results/paper/missing_keys_jp.txt` | kept: tagged generated output (written empty by a script on purpose) |
| `results/paper/missing_keys_v2.txt` | kept: tagged generated output (written empty by a script on purpose) |
| `src/crashguard/.gitkeep` | delete if the directory has other tracked files (placeholder), see Part 2 |
| `tests/dummy/.gitkeep` | delete if the directory has other tracked files (placeholder), see Part 2 |

## Part 2. Moves, deletions and rewrites

### 2a. Moves (`git mv`, history kept; `git log --follow` works)

Source: `scripts/reorganise_docs.py` (kept so the move can be audited). The full old-to-new table is in `docs/07_log/PATH_MAP.md`.

- 65 documents moved into `docs/00_overview` to `docs/07_log` and `docs/archive`.
- 39 run logs and comparison outputs moved from the repository root to `docs/archive/logs/` (none is read by code; none is deleted).
- `REPRODUCE.md` (root) became `docs/05_data_code/REPRODUCE.md` (main pipeline); `docs/REPRODUCE.md` became `docs/05_data_code/REPRODUCE_FINISH.md` (finishing round). They cover different scopes, so they were kept apart, not merged.
- `PROGRESS.md` (root) became `docs/07_log/PROGRESS.md`.
- `scripts/combine_docs.py` became `docs/archive/combine_docs.py` and was removed from `make report` and `scripts/run_all.ps1`; its output `docs/ALL_DOCS_COMBINED.md` is archived.
- Deviation from the inventory (1a): `MANUAL_SEARCH_CHECKLIST.md` is kept in `docs/06_references/` as current, not archived, because generated text in the code points to it and it holds the IEEE Xplore strings; `SCOPUS_STRINGS.md` is added next to it in Block L.
- Archived with a SUPERSEDED header (the header block names the replacement and the reason): `CLAIMS_FOR_COVER_LETTER_V1.md`, `ALL_DOCS_COMBINED.md`, `CLAUDE_CODE_PROMPT.md`, `FIRST_PROMPT.md`.

### 2b. Deletions

| Path | Reason | SHA-256 |
|---|---|---|
| `firmware_export/.gitkeep` | empty placeholder; the directory has other tracked files | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `merge/.gitkeep` | empty placeholder; the directory has other tracked files | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `report/.gitkeep` | empty placeholder; the directory has other tracked files | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `src/crashguard/.gitkeep` | empty placeholder; the directory has other tracked files | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `tests/dummy/.gitkeep` | empty placeholder; the directory has other tracked files | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Not deleted, with the reason: byte-identical copies listed in 1c (they are inputs of different steps or tagged results); the empty files under `results/paper/` (tagged generated output); `build/` and the caches (ignored by git, regenerated by the tests and the C checks, referenced by code). No document was deleted.

### 2c. Rewrites

- Every path to a moved document was rewritten with the old-to-new map in 203 files: code (`src/`, `tests/`, `scripts/`), the Makefile, `scripts/run_all.ps1`, `CLAUDE.md`, `NOTICE`, `crashclip/README.md`, `paper/main.tex` and the documents. Not rewritten on purpose: `results/` (tagged; its notes keep the old paths, mapped in `PATH_MAP.md`), `release/vzcrash_audit_for_authors/` (sent to the dataset authors), `data/`, `c_bundle/`.
- Code changes beyond path strings (minimal): `attack_doc.py` and `tests/test_consistency.py` now search `docs/` recursively and skip `docs/archive/`; `fin_release.py` no longer lists two moved files separately; `docs_gen.py`, `repro_table.py`, `fin_a3.py`, `compliance.py` cut text at a word boundary through the new `textutil.clip` (a plain slice had cut words in half, for example `erro`); `report_part4.py` spelling (`reuse`).
- `docs/VZCRASH_AUDIT.md` stays at its old path as a short redirect note, because the dataset authors were given that path by email on 2026-11-12.
- Wording only: the banned ordinal word was replaced by a plain synonym in 18 current documents (no number, hypothesis or criterion changed); sentences that quoted the banned words now point to rule 7 of `CLAUDE.md`. Superseded text under `docs/archive/` is left as it was.
- New tools: `scripts/repo_inventory.py`, `scripts/reorganise_docs.py`, `scripts/doc_meta.py`, `scripts/doc_headers.py` (header block and index), `scripts/doc_style_check.py` (banned words, emoji, first-person tone, spelling with codespell), `scripts/check_links.py`, `scripts/check_reproduce.py`, `src/crashguard/r_docs.py` (project status from `results.json`), `tests/test_release_docs.py`.
- Scope of the header block: every Markdown document except `CLAUDE.md` (tool configuration), tagged files under `results/`, the audit package for the dataset authors, `data/` (including `data/hardware/`, which was not opened), `RESEARCH PAPERS/` and the archived run logs.
- Number provenance: numbers in generated documents come from `results/results.json` by construction; hand-written documents were not re-derived line by line in this block (the claim audit in Block E covers README, PROJECT_STATUS, the claim lists and the paper).

## Part 3. Checks after the move (2026-11-13)

| Check | Result |
|---|---|
| `check_results` | 0 errors (94 NOT_RUN entries with a stated reason, as before) |
| Tests | 263 passed, 1 skipped before the last wording fix (baseline before the move: 259 passed, 2 skipped; four new documentation tests added) |
| ruff | clean |
| Link check (`scripts/check_links.py`) | 0 problems over every Markdown link and backticked repository path |
| Wording, tone, emoji (`scripts/doc_style_check.py`) | 0 findings |
| Spelling (codespell with `scripts/spell_ignore.txt`) | 0 findings; ignored on purpose: FPR, SOM, `restor*` (a search wildcard), German words in cited titles, a vehicle name |
| Commands in the guides and the Makefile (`scripts/check_reproduce.py`) | 145 distinct commands resolve to an existing module, script or target; the commands were not re-run (a full rebuild takes hours) |
| `results/results.json` SHA-256 | `b9eeae1e3327ebea735c4d563616aa98665aaa54657296c09f52e1db78b96324`, identical before and after |
| Tracked files under `results/`, `release/`, `c_bundle/` | byte-identical to tag `journal-v1` (sha256 comparison) |
| Other tracked files that differ from the tag outside `docs/` | `crashclip/README.md` and `paper/main.tex` (path rewrite), `paper/ABSTRACT_FACTS.md` (header block), `firmware_export/.gitkeep` (empty placeholder removed) |
