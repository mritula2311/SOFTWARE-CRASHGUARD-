# Release claim audit

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Mechanical claim audit of the top-level documents and the paper against results.json for the release. |
| Evidence labels used | NOT_RUN |
<!-- header:end -->

A separate pass (script `scripts/release_audit.py`, run after the documents were generated) over the top-level documents against `results/results.json`. Documents are fixed; results are not.

| Check | Result |
|---|---|
| Banned words and the word 'unbiased' in 7 documents | none found |
| V7 verdict keys present | 20 of 20 |
| NOT_RUN entries without a reason among new keys | 0 |
| New keys with an unexpected origin label | 0 |
| Status table counts consistent with the V7 verdict keys | yes (status document: 80 hypotheses: 19 supported, 0 partly supported, 51 not supported, 10 not run) |

## Findings

- The mechanical checks found nothing to change. A presentational point stays: the status table lists the carried V7 rows next to the earlier rows they repeat (same criterion and p-value); each carried row says so in its note.
- The cross-validation arm of the PH-A exploratory run did not finish; the Q4 table says so instead of showing a blank.

## Limits of this audit

It is a mechanical pass plus the generator checks. The paper was not compiled (no TeX distribution in the session); its numbers come from `paper/generated/numbers_release.tex`.
