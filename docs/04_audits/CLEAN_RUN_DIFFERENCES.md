# Fresh-clone run: what was rebuilt and every difference (V1.3, V1.4)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | What the fresh-clone run rebuilt, the result keys that differ and why, the tracked files that differ, and the failed steps with their causes. |
| Evidence labels used | NOT_RUN |
| Abbreviations | PDF = Portable Document Format; PNG = Portable Network Graphics; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Setup. A fresh `git clone` of branch `verify` at `D:\crashguard-verify\clone`, outside the working copy. The environment was created only from `requirements.lock` (with hashes). `data/raw` is a directory junction to the original raw files (15 GB, git-ignored); `data/processed` was rebuilt from raw in the clone. The Windows Application Control policy blocked the LightGBM DLL in the new virtual environment, so the pipeline was run with the original interpreter (the same pinned versions; `pip freeze` differs only by `cryptography`, `cffi` and `pycparser`, which the lock now includes) and the sources of the clone. No policy was bypassed.

## What ran

| Part | Steps | Time | Result |
|---|---|---|---|
| Core (features, split, models, export) | 6 | 9 min | features and event metadata byte-identical to the committed files |
| `make all` (early rounds) | 92 | 296 min | 90 passed; `vz_leakage` failed once on a sporadic Application Control block of an sklearn extension and passed on rerun; `check_results` fails because the host C compiler (zig) is blocked, so 33 compiler-dependent keys are absent |
| Later targets (`positive finish release combined round3 paper round4 round5 round5s2 report`) | 172 | 2.5 h | 127 passed, 45 failed; causes below |
| Round 5 repeated after clearing its keys (the held-out guard refuses a second run while the keys exist) | 40 | 6 min | 657 of 659 `r5.*` keys recomputed; 0 numeric differences |

## Result keys

- Early rounds: of 143,677 shared keys, 33 are absent in the clone (host C compiler blocked: `export_severity.*`, `export.*`, `candidate.*`) and 21 differ. Fifteen of the 21 are `s4b.*.header_bytes` (+13 bytes: the size of a generated C header text, not a result); five are `export_severity` size values; one is `t14.n_intervals_reported_total` (15,006 against 14,700: a count of intervals in `results.json` at the moment the audit runs, which depends on the other keys present).
- `r3.*` (736), `pp.*` (334), `rd.*` (535): 0 missing, 0 differ after the steps rewrote them. `a4.*` (748): 2 differ, `a4.cv.passed` and `a4.cv.ns3_byte_identical` (1 against 0), because the clone's older `a4_verify.py` called a hard-coded WSL path that does not exist in the clone; the paths are derived in the working copy now.
- `r5.*` (659): 2 absent (`r5.l1.held.sim.pooled_acc_l1_cluster_lo` and `cluster_lo_met`, which no module of the round writes; they were added to the committed file by a later patch) and one text key, `r5.l7.a.model_sha256`, differs (the SHA-256 of a model file whose line endings differ in the clone).
- All 251 macros of the paper's `numbers.tex` are identical when computed from the fresh clone (`docs/04_audits/RECOMPUTE.md`).

## Tracked files that differ in the clone (171)

| Class | Files | Explanation |
|---|---|---|
| Figure files (PNG, PDF) | 76 | byte differences from rendering metadata; figures are regenerated from `results.json` and the paper figures were checked by eye |
| Frozen-parameter files (`*_frozen.json`, `p_freeze_*.json`) | 9 | contain the hash of the code files and the git head at freeze time; the clone has other line endings and a different head |
| Tables with extra columns | 11 | the current code writes 5 to 20 more columns than the committed tables; every column present in both is numerically identical (0 cells differ at 1e-6) |
| `s4b_depth_sweep*.csv` | 2 | 15 and 75 cells differ by at most 0.04% (header size, as above) |
| `stats_audit*.csv`, `f_scored_log.csv` | 3 | audit rows that depend on the keys present, and one more appended log row per run |
| Generated documents (`docs/`, `report/`) | about 60 | headers, dates, test-count lines and the failed-step statuses below; no number of a result changed |

## The 45 failed steps

| Cause | Steps | Consequence |
|---|---|---|
| Sealed-fold guard: V4 steps (`pp_p1` to `pp_p4d`) refuse a second scoring of the sealed fold and the freeze step needs a git identity in the clone | 14 | the V4 positive-push results cannot be recomputed from a clean clone by design; the stored `p.*` and `pp.p*` keys stand. NOT_RUN |
| Held-out guard: `r5_*` steps refused while `r5.*` keys existed | 22 | repeated after clearing the keys (table above) |
| `pa_sim held`: `AttributeError: 'collections.deque' object has no attribute 'values'` in a worker | 1 (+1 dependent: `pa_eval`) | a regression: the V7 protocol-candidate code (block A) is not compatible with the later `world_sim.py`; see `docs/04_audits/BLOCKERS.md` |
| `ph_gates fit` and `gates`: `data/processed/ph_real_desc.parquet` is read but no module writes it | 2 | `make release` is not self-contained; the cache was made by hand; see `BLOCKERS.md` |
| `fin_g all`: the process pool was terminated; `fin_g_eval` then lacks `f_g5.pkl` | 2 | a sporadic environment failure (memory or policy block); not rerun |
| `a4_mutation.py`: baseline tests fail on the clean copy; `a4_audit.py`: 5 tracked files under `data/hardware` (the author's log files; not used and not edited in this run) | the audit rule is about raw data and hardware data; the files were already tracked at tag `round5-v1` |
| `pp_paper_audit.py` in the clone: macros of an older paper missing | 1 | the clone is at the commit before the paper was rewritten; the audit passes in the working copy |
