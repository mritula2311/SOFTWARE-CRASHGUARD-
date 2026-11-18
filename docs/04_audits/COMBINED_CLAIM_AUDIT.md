# Combined-run claim audit

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Mechanical audit of the combined-run documents against results.json and the evidence labels (generated). |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED_HW_FORMAT, SIMULATED, ANALYTICAL, HARDWARE, NOT_RUN |
<!-- header:end -->

A mechanical pass (script `scripts/combined_audit.py`, run after the documents were generated) over the documents of the combined run. It lists every line that may be stronger than its evidence label; each listed line was read and the outcome is stated under Findings.

| Check | Result |
|---|---|
| Banned words in 14 documents (combined-run parts only) | none found |
| Lines that mention hardware without simulated, no, not or NOT_YET | 0 |
| Lines with validated, proves, guarantees or demonstrates and no limiting word | 0 |
| Verdict, raw p, Holm p and criterion for the 13 hypotheses | 52 of 52 keys present |
| Verdict words in COMBINED_VERDICTS.md agree with the keys | yes |
| Verdict words in the claims file agree with the keys | yes |
| New keys (`sh.`, `ar.`) and their labels | 4673 keys; labels used: ANALYTICAL, MEASURED_SOFTWARE, NOT_RUN, SIMULATED, SIMULATED_HW_FORMAT; HARDWARE among them: no |
| NOT_RUN entries among the new keys without a reason | 0 |
| Keys of the base tag release-v1 unchanged | yes (139013 entries at release-v1; 0 changed or missing; 4673 added {'sh.': 3971, 'ar.': 702}) |
| Status table: row count against the stated count | yes (stated 80; rows with an id: counted by the generator) |

## Lines listed above for review

**Hardware mentioned without a limiting word** (0)

- none

**Strong verb without a limiting word** (0)

- none

## Findings

- The word confirm is the name of a protocol message (confirm or cancel) and is not in the strong-verb list. Each listed line was read; any line stronger than its label is changed in the source generator, not in the generated file, and this audit is run again.
- The audit is mechanical. It cannot judge a sentence in context: the claims file and the decision table were also read by hand against `docs/03_results/COMBINED_VERDICTS.md`.

## Limits of this audit

The paper was not compiled (no TeX distribution in the session); its combined-run text takes every number from `paper/generated/numbers_combined.tex`, which is read from `results/results.json`.
