# Final verification report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Summary of the final verification run: counts per block, failures, blockers, recompute mismatches, formal outcomes, ledger totals, page and figure counts, references, release hash, author to-do list. |
| Evidence labels used | NOT_RUN |
| Abbreviations | DOI = digital object identifier; GPS = Global Positioning System; OS-DR = overhear-and-suppress retries with deadlines |
<!-- header:end -->

Branch `verify` from tag `round5-v1`; tag `submit-v1`. Every check is one row in `docs/04_audits/FINAL_VERIFICATION.md`. The minutes in that log are rounded estimates, not stopwatch readings. The SHA-256 of the release archive is in `release/crashguard-submit-v1.zip.sha256` and in the closing message of the run (the archive cannot contain its own hash).

## 1. Counts per block

| Block | PASS | FAIL | FIXED | NOT_RUN | Minutes |
|---|---|---|---|---|---|
| V0 | 2 | 0 | 0 | 0 | 17 |
| V1 | 5 | 1 | 2 | 0 | 735 |
| V2 | 5 | 0 | 0 | 0 | 170 |
| V3 | 4 | 0 | 1 | 0 | 117 |
| V4 | 2 | 0 | 0 | 0 | 105 |
| V5 | 5 | 0 | 0 | 0 | 210 |
| V6 | 2 | 0 | 0 | 0 | 160 |
| V7 | 2 | 0 | 0 | 0 | 150 |
| V8 | 0 | 0 | 3 | 0 | 105 |
| V9 | 3 | 0 | 1 | 0 | 95 |
| V10 | 3 | 0 | 1 | 0 | 100 |
| V11 | 7 | 0 | 0 | 0 | 150 |
| V12 | 1 | 0 | 0 | 0 | 20 |
| all | 41 | 1 | 8 | 0 | 2134 |

Block V1 has its rows under the ids V1.1a to V1.5 (in the table they are counted with V1). One row is FAIL (V1.3c, the blockers below); the others are PASS or FIXED. No row is NOT_RUN except the parts named in section 2.

## 2. Failures that could not be fixed, with the consequence for the paper

- **Regression in the V7 protocol-candidate code** (B1): the held-out grid of OS-DR cannot be rerun at the current simulator. The stored `pa.*` values stand; the paper's negative-table row for OS-DR rests on them. The size of any change is unknown.
- **`make release` needs a hand-made cache** (B2), the **V4 steps cannot be repeated** by design (B3), the **host C compiler is blocked** here (B4), the **freshness layout is not specified** (B5) and the **Access class cannot be compiled here** (B6). Details in `docs/04_audits/BLOCKERS.md`; none changes a number in the paper.
- The positive-push V4 results, the C equivalence checks and the V7 protocol block are therefore marked as not recomputed from the clean clone.

## 3. Blockers

Six, B1 to B6, in `docs/04_audits/BLOCKERS.md`.

## 4. Recompute mismatches and how they were resolved

All 251 macros of the paper are identical when computed from the fresh clone (`docs/04_audits/RECOMPUTE.md`, 71 rows for facts F1 to F12 and F16 to F21). Differences in the result file (`docs/04_audits/CLEAN_RUN_DIFFERENCES.md`): 33 keys absent because the compiler is blocked, 21 early-round keys that differ (header text size, one interval count; no result), 2 `a4.cv.*` flags (a hard-coded path, since fixed), 2 `r5.*` keys no module writes and one hash of a text file (line endings). No value in the paper changed.

## 5. Formal reruns

Tamarin 1.12.0 and ProVerif 2.05 give the stored outcomes: the shared-key design has the acknowledgement-suppression attack, the per-vehicle design proves authenticity, acknowledgement binding and the freshness lemmas, the car-reboot identifier lemma is not decided in Tamarin, ProVerif finds the reuse attack on the frozen design inside the same GPS second and proves the boot-counter variant, and the non-persisting control fails. The retry-policy enumeration, the L7b enumeration (1,398,101 sequences) and the L8a bounded model reproduce. Five mismatches between the models and the frame layout are in `docs/04_audits/FORMAL_FIELD_CHECK.md`.

## 6. Hypothesis ledger

123 preregistered hypotheses in 12 versions; 110 run; 40 supported, 66 not supported, 4 partly, 13 not run. In a Holm family: 114 (of which 36 supported). `docs/04_audits/HYPOTHESIS_LEDGER.md`.

## 7. Page and figure count

Main text: 12 pages (an estimate with the class IEEEtran, which stands in for the Access class that cannot run under Tectonic), 8 figures and 5 tables; the supplement has 154 pages. See `docs/04_audits/LATEX_LINT.md`.

## 8. References

50 entries; 45 have a DOI (3 of them Zenodo or DataCite DOIs checked there); 12 older entries were corrected; 0 mismatches against Crossref after the fix (`docs/04_audits/REFERENCE_CHECK_VF.md`). Four papers stay at abstract level (blocked or closed).

## 9. Release

`release/crashguard-submit-v1.zip`, built from a fresh clone of tag `submit-v1`; SHA-256 and file count in `release/crashguard-submit-v1.zip.sha256` and `release/crashguard-submit-v1.manifest.txt`.

## 10. What the author must do by hand, in order

1. Fill the placeholders of `paper/PLACEHOLDERS.md` (authors, e-mail, ORCID, biographies, funding, CRediT, interests, acknowledgement wording, AI-tool disclosure with the section list, suggested reviewers).
2. Decide the byte layout of the freshness field and the boot counter (B5) and the SisFall licence question.
3. Read through the library: Nessa 2020, Vinodhini 2025, Jabbari and Mohasefi, one next-generation eCall paper (Hetz et al. 2026), and the two record-level papers (Carneiro 2023, Marciano 2024).
4. Run the five Google Scholar strings and read the top results.
5. Upload `paper/` to Overleaf and compile with the Access class of the 2026-05-13 template; fix any float placement; check the page count.
6. Supervisor review of the manuscript and the cover letter.
7. Add a remote, push the branches `final`, `algo4`, `round5`, `verify` and all tags, and create the Zenodo deposit from the release archive (commands below).
8. Submit.
9. Optional: the one-hour bench run of the two-stage alert (`docs/08_hardware/R3_BENCH_PROTOCOL.md`).

Push commands (no remote exists yet; nothing was pushed):

```
git remote add origin <url>
git push origin final algo4 round5 verify
git push origin --tags
```
