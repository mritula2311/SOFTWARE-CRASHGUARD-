# Round 7e report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Report of round 7e: one-time scripts that refuse to run, the probe that found them, and the submit-v6.2 archive. |
| Evidence labels used | NOT_RUN |
| Abbreviations | PDF = Portable Document Format |
<!-- header:end -->

No new experiment, no new key, no change to a result or a frozen file. This is the last code change before submission.

## 1. One-time scripts

Every script that writes paper text, the ledger or the layout was rerun in a scratch clone at `submit-v6.1`, and the result was compared with the committed files.

| Script | Rerun result | Action |
|---|---|---|
| `scripts/r7c_patch_paper.py` | stops with an assertion error (the sentence it looks for was replaced in round 7d) | **refuses to run** |
| `scripts/r7b_patch_paper.py` | appends the round-7b block to the cover letter a second time (its guard tests lower case, the block starts with a capital) | **refuses to run** |
| `scripts/r7_cover.py` | resets the cover-letter hypothesis counts to 136 in 14 versions | **refuses to run** |
| `scripts/r7b_ledger.py` | drops the V19 row of the ledger's Versions table and reorders `results/results.json` | **refuses to run** |
| `scripts/vf2_cover.py` | overwrites the cover-letter blocks with older counts | **refuses to run** |
| `scripts/vf_ledger.py` | rewrites the ledger with the counts of the verification run (130 in 13 versions) and rewrites keys | **refuses to run** |
| `crashguard.r7_layout` | deletes sections 10 to 12 of `FRAME_LAYOUT.md` (R-ATOMIC and R-REACK included) and ledger rows | **refuses to run** (inside `main`) |
| `crashguard.pp_submission` | overwrites `paper/REPRODUCE.md` and `paper/highlights.md` with older text | **refuses to run**; removed from the `paper` target of the Makefile |
| `scripts/r7c_report.py` | with no arguments it wrote `NOT_BUILT` over the recorded archive hash | now requires the hash and file count |
| `scripts/r7_patch_paper.py`, `scripts/r7_patch_paper2.py`, `scripts/r7b_patch_power.py`, `scripts/r7b_patch_ledger_paper.py`, `scripts/r7d_patch_paper.py`, `scripts/patch_world_sim_pa.py`, `scripts/pp_make_bib.py` | a rerun changes nothing | left as they are |

The refusal is a `SystemExit` with a message at the top of each file (after the docstring), so the code stays in place for the audit trail and no document link breaks. `tests/test_one_time_guards.py` checks all of them. Not guarded, listed only: `scripts/vf_negatives.py`, `scripts/vf_final_report.py`, `scripts/vf2_final_report.py` regenerate documents of earlier rounds from the stored keys; they rewrite those documents but not the current paper text. `scripts/r7c_changes.json` and `scripts/r7d_changes.json` are the old and new sentences recorded for the reports.

## 2. Checks and archive

Fresh clone, checks and archive: see `ROUND7C.md` rows E1 to E4. The archive name follows the tag: `release/crashguard-submit-v6.2.zip` (the brief named v6.1; the guard change is a new commit, so the tag and the archive are v6.2). The archive is built from the commit that holds the guards; the commit that records the archive's SHA-256 and file count (in this report and in `paper/REPRODUCE.md`) differs from it only in those documents.

## 3. Archive record

- `release/crashguard-submit-v6.2.zip`: SHA-256 `c4ddd510c2b0f011080fc494c9dd784a6673d040bd84c1132d7cf27a8030f00e`, **1,902 files** (48 in `supplementary_full/`), 38,562,627 bytes; built from a fresh clone at commit `215fe04`; 11 files added since the submit-v6 archive and none absent; the supplement PDF is NOT_RUN (no TeX distribution). Also recorded in `paper/REPRODUCE.md` item 16 and in `release/crashguard-submit-v6.2.manifest.txt`.
- Checks from the fresh clone at `215fe04`: two-part tests 73 passed, then 637 passed with 2 skipped; ruff clean; `check_results` 0 errors; paper audit 0 lint errors, 0 bare numbers, 0 forbidden words, 0 undisposed claims; TeX lint 0; `r5_audit` no problems; `verify_keys_unchanged` against `submit-v6.1`: 0 changed, 0 added.
- The tag `submit-v6.2` is on the commit after `215fe04`, which changes only the documents and the two record files (`.sha256`, `.manifest.txt`) named in REPRODUCE.md item 16.
