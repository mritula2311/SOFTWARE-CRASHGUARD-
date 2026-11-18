"""V12: write docs/04_audits/FINAL_REPORT.md (counts come from FINAL_VERIFICATION.md and results.json)."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}
counts = subprocess.run([sys.executable, str(ROOT / "scripts/vf_report_counts.py")], capture_output=True, text=True).stdout.strip()
L = lambda k: int(R[f"vf.ledger.all.{k}"])  # noqa: E731
txt = f"""# Final verification report

<!-- header:start -->
<!-- header:end -->

Branch `verify` from tag `round5-v1`; tag `submit-v1`. Every check is one row in `docs/04_audits/FINAL_VERIFICATION.md`. The minutes in that log are rounded estimates, not stopwatch readings. The SHA-256 of the release archive is in `release/crashguard-submit-v1.zip.sha256` and in the closing message of the run (the archive cannot contain its own hash).

## 1. Counts per block

{counts}

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

{L('preregistered')} preregistered hypotheses in {L('versions')} versions; {L('run')} run; {L('supported')} supported, {L('not_supported')} not supported, {L('partly')} partly, {L('not_run')} not run. In a Holm family: {L('confirmatory_rows')} (of which {L('confirmatory_supported')} supported). `docs/04_audits/HYPOTHESIS_LEDGER.md`.

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
"""
(ROOT / "docs/04_audits/FINAL_REPORT.md").write_text(txt, encoding="utf-8")
print("written")
