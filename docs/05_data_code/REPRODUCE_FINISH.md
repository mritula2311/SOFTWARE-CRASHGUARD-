# Reproduce the journal-push tables and figures

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Commands for the journal-push and finishing-round tables and figures. |
| Evidence labels used | NOT_RUN |
| Abbreviations | CPU = central processing unit; ESP32 = a Wi-Fi microcontroller family (Espressif); NHTSA = National Highway Traffic Safety Administration; RAM = random-access memory |
<!-- header:end -->

Run from the repository root with `$env:PYTHONPATH = "src"` (PowerShell) or `PYTHONPATH=src`, in the project virtual environment (`.venv`). The earlier pipeline (`docs/05_data_code/REPRODUCE.md`: data, features, models, NHTSA severity steps) must have been run beforehand, because these modules read its outputs (`data/processed/`, `results/results.json`). The NHTSA harvest needs network access to the public NHTSA API; downloaded files are cached in `data/raw/nhtsa/` (git-ignored). The VZCrash files must be in `data/raw/data/` (gated dataset; never commit them).

Order: `t13_harvest`, `t13_heldout`, `t13_neardup`, `sel_study`, `sel_tables`, `vz_audit`, `vz_leakage`, `vz_docs`, `x_common`, `x1_fixedpoint`, `x2_cascade`, `x3_groupaware`, `x4_labels`, `x5_rank`, `x6_anchored`, `x7_fusion`, `x8_sequential`, `x_verdicts`, `jp_paper_tables`, `claim_table`, `stats_audit`, `jp_docs`, `check_results`. `scripts/run_all.ps1` and the Makefile `journal` target run them in this order.

| Table or figure | Command | Results keys |
|---|---|---|
| jp_tab_t13_heldout, jp_tab_t13_paired, jp_tab_t13_grid | `python -m crashguard.t13_harvest && python -m crashguard.t13_heldout && python -m crashguard.jp_paper_tables` | `t13.heldout.*` |
| jp_tab_t13_neardup | `python -m crashguard.t13_neardup && python -m crashguard.jp_paper_tables` | `t13.neardup.*` |
| tab_sel_parts, tab_sel_sources, tab_sel_study, tab_sel_study_all, figure sel_share_vs_range, docs/05_data_code/SENSOR_DATASHEETS.md | `python -m crashguard.sel_study && python -m crashguard.sel_tables` | `sel.*` |
| vz_audit_cross_split_groups.csv, docs/04_audits/VZCRASH_AUDIT.md | `python -m crashguard.vz_audit && python -m crashguard.vz_leakage && python -m crashguard.vz_docs` | `vz.v1.*, vz.v4.*` |
| jp_tab_vz_leakage | `python -m crashguard.vz_leakage && python -m crashguard.jp_paper_tables` | `vz.v4.*` |
| jp_tab_x1 | `python -m crashguard.x1_fixedpoint && python -m crashguard.jp_paper_tables` | `x.x1.*` |
| jp_tab_x3 | `python -m crashguard.x3_groupaware && python -m crashguard.jp_paper_tables` | `x.x3.*` |
| jp_tab_x5_rank, figure jp_fig_x5_rank | `python -m crashguard.x_common && python -m crashguard.x5_rank && python -m crashguard.jp_paper_tables` | `x.x5.*` |
| jp_tab_x6_anchored, figure jp_fig_x6_p90 | `python -m crashguard.x_common && python -m crashguard.x6_anchored && python -m crashguard.jp_paper_tables` | `x.x6.*` |
| jp_tab_x7 | `python -m crashguard.x7_fusion && python -m crashguard.jp_paper_tables` | `x.x7.*` |
| jp_tab_x8 | `python -m crashguard.x8_sequential && python -m crashguard.jp_paper_tables` | `x.x8.*` |
| X2 (no table; keys only) | `python -m crashguard.x2_cascade` | `x.x2.*` |
| X4 (no table; keys only) | `python -m crashguard.x4_labels` | `x.x4.*` |
| jp_tab_x_verdicts | `python -m crashguard.x_verdicts && python -m crashguard.jp_paper_tables` | `x.holm.*` |
| figure jp_fig_t13_range | `python -m crashguard.jp_paper_tables` | `t13.heldout.grid.*, sevstudy.grid.*` |
| docs/03_results/CLAIM_EVIDENCE.md (journal-push rows), docs/03_results/STATS_AUDIT.md | `python -m crashguard.claim_table && python -m crashguard.stats_audit` | `all` |
| docs/03_results/JOURNAL_RESULTS.md, docs/00_overview/CLAIMS_FOR_COVER_LETTER.md, this file | `python -m crashguard.jp_docs` | `all` |

Checks: `python -m crashguard.check_results` (0 errors), `python -m pytest -q`, `python -m ruff check src tests`.

Not reproducible here: anything that needs the author's hardware (`data/hardware/`), the Windows compiled-C checks when Application Control blocks them (recorded as NOT_RUN with the reason), and downloads while the NHTSA API or the data sheet hosts are unreachable.

<!-- PP:BEGIN -->
## Positive-results push: reproduce (branch `positive-push`)

Run from the repository root with `PYTHONPATH=src` in the project virtual environment (`torch` CPU is needed for the CNNs: `pip install torch --index-url https://download.pytorch.org/whl/cpu`). The earlier pipeline and the `journal` steps must have been run (T13a signals in `data/processed/`, VZCrash windows, `results/results.json`). `make positive` runs the whole chain; the sealed fold and the test splits are scored once, so a second run of an evaluation stage needs `PP_DEVIATION="reason"` (logged in `results/tables/p_sealed_access.csv`). To rerun from scratch, delete the `p.` keys and `results/tables/p_sealed_access.csv` and the freeze files.

| Table or figure | Command | Results keys |
|---|---|---|
| Z0 pooled set, docs/05_data_code/SEALED_SPLIT.md, results/tables/p_pool_folds.csv | `python -m crashguard.pp_pool` | none |
| P1 fit and freeze (models, validation table) | `python -m crashguard.pp_feat && python -m crashguard.pp_p1 fit` | none (validation table `p1_validation.csv`) |
| p_tab_p1, p_tab_p1_all, p_tab_z1, p_fig_p1_triage | `python -m crashguard.pp_p1 eval && python -m crashguard.pp_docs && python -m crashguard.pp_figs` | `p.p1.*` |
| P1 cross-validation (EXPLORATORY) | `python -m crashguard.pp_p1_cv` | `p.p1cv.*` |
| p_tab_p2, p_fig_p2_intervals | `python -m crashguard.pp_p2 fit && python -m crashguard.pp_p2 eval` | `p.p2.*` |
| p_tab_p3a, p_tab_p3b, p_fig_p3a_risk_coverage | `python -m crashguard.pp_p3 fit && python -m crashguard.pp_p3 eval` | `p.p3a.*, p.p3b.*` |
| p_tab_p4a, p_fig_p4a_pareto, measured size | `python -m crashguard.pp_p4a sweep && python -m crashguard.pp_p4a eval && python -m crashguard.pp_p4a size` | `p.p4a.*` |
| p_tab_p4b | `python -m crashguard.pp_p4bc p4b freeze && python -m crashguard.pp_p4bc p4b eval` | `p.p4b.*` |
| p_tab_p4c, p_fig_p4c_guarantee | `python -m crashguard.pp_p4bc p4c freeze && python -m crashguard.pp_p4bc p4c eval` | `p.p4c.*` |
| p_tab_p4d | `python -m crashguard.pp_p4d freeze && python -m crashguard.pp_p4d eval` | `p.p4d.*` |
| p_tab_b2, results/tables/p_b2_flags.npz | `python -m crashguard.pp_b2` | `p.b2.*` |
| requirement calculator | `python scripts/requirement_calculator.py --mix frontal_barrier=0.3,pole=0.4,side=0.1,other=0.2 --required 0.80` | reads `p_b2_flags.npz` |
| crashclip/ package files | `python -m crashguard.pp_crashclip` | none |
| p_tab_holm | `python -m crashguard.pp_verdicts` | `p.holm.*` |
| docs/03_results/POSITIVE_PUSH_RESULTS.md, p_tab_*, claim rows, STATS_AUDIT block, REFERENCES block, SEALED_SPLIT table | `python -m crashguard.pp_docs` | all `p.*` |
| independent claim audit | `python -m crashguard.pp_audit` | `docs/04_audits/PP_CLAIM_AUDIT.md` |

Checks: `python -m crashguard.check_results` (0 errors), `python -m pytest -q`, `python -m ruff check src tests crashclip scripts`.

**NOT_RUN in this push:** ESP32 flash and RAM and any microcontroller timing (no cross compiler, no emlearn; `p.p4a.measured_bytes_esp32`); P3b at +-64 g; hardware results; a second public crash dataset; (the code licence, Apache-2.0, was added on branch `finish`).
<!-- PP:END -->

## Finishing branch (`finish`, from tag `positive-push-v1`; keys `f.*`)

Run from the repository root with `PYTHONPATH=src` and the virtual environment (`.venv/Scripts/python` on Windows). **Never run two commands that write `results/results.json` at the same time** (the file is rewritten whole). Order matters where noted. Seeds: 42 and 0 to 4; simulation seeds are in `docs/02_preregistration/PREREGISTRATION_V5.md` section 0. Heavy steps use 12 to 14 worker processes.

| Output | Command | Notes |
|---|---|---|
| A: audit package for the VZCrash authors (`release/vzcrash_audit_for_authors/`) | `python -m crashguard.fin_a4` | needs `data/processed` tables from the earlier rounds; no raw data written |
| A: `docs/07_log/NOT_RUN.md` | `python -m crashguard.fin_a3` | |
| B1: `f.b1.*` (bounded check, attack cases with the CANCEL option) | `python -m crashguard.fin_b1` | about 15 s |
| B2: `f.b2.*`, `results/tables/f_b2.csv`, table `paper/generated/tab_b2.tex` | `python -m crashguard.fin_b2` | 5,040 runs |
| B3: `f.b3.*` | `python -m crashguard.fin_b3` | about 1 minute |
| C: `f.c.*`, `results/synthetic/*` (fidelity figure `c_fig_fidelity.png/pdf`, parameters, `modes_passed.json`, 5,000-pulse parameter file, grid tables), `release/synthetic_pulses/*.npz` | `python -m crashguard.fin_c` | builds `data/processed/f_real_desc.parquet` on the initial call; about 40 minutes |
| F1 runs (`data/processed/f1_runs.pkl`) | `python -m crashguard.fin_f1` (all runs) or `python -m crashguard.fin_f1 sealed` | about 16 minutes per run, 6 runs |
| F1 evaluation: `f.f1.*` | `python -m crashguard.fin_f1_eval` | |
| F2 surrogate generator, `results/surrogate/*`, `f.f2.*` | `python -m crashguard.fin_f2` | needs `windows_cache`; about 40 minutes |
| F3: `f.f3.*`, `results/tables/f_f3.csv` | `python -m crashguard.fin_f3` | needs the five cross-validation runs of F1 |
| G pools and runs (`data/processed/f_g*.pkl`) | `python -m crashguard.fin_g pairs`, then `python -m crashguard.fin_g all` | 75,360 runs |
| G evaluation: `f.g.*`, regime map `results/figures/f_g_regime_map.png/pdf`, tables | `python -m crashguard.fin_g_eval` | |
| Holm and verdicts: `f.holm.*` | `python -m crashguard.fin_verdicts` | after every step above |
| Documents: `docs/03_results/NEGATIVES_REGISTER.md`, `docs/03_results/FINISH_RESULTS.md`, `docs/00_overview/CLAIMS_FOR_COVER_LETTER.md` | `python -m crashguard.fin_docs` | |
| Paper numbers and tables: `paper/generated/numbers.tex`, `tab_*.tex`, `paper/ABSTRACT_FACTS.md` | `python -m crashguard.fin_paper` | `paper/main.tex` was not compiled (no TeX distribution here) |
| `docs/06_references/REFERENCES_UNVERIFIED.md` | `python -m crashguard.fin_refs` | |
| `docs/04_audits/FINISH_AUDIT.md` | `python -m crashguard.fin_audit` | |
| Release archive and `docs/05_data_code/RELEASE_MANIFEST.md` | `python -m crashguard.fin_release` | |
| Checks | `python -m crashguard.check_results`, `python -m pytest -q`, `ruff check src tests` | |
