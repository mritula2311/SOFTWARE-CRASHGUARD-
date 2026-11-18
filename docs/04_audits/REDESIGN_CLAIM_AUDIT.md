# Redesign claim audit

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Mechanical audit of the redesign documents against results.json and the evidence labels (generated). |
| Evidence labels used | HARDWARE |
<!-- header:end -->

Script `scripts/redesign_audit.py`. Every flagged line was read; outcomes are under Findings.

| Check | Result |
|---|---|
| banned words in 17 documents | 0 |
| hardware mentions without a qualifier | 1 |
| over-strong words without a qualifier | 3 |
| hypotheses of the family without a final Holm key | 0 |
| rd.* keys with an origin outside the allowed set | 0 |
| rd.* keys labelled HARDWARE | 0 |
| decision-table verdicts that disagree with the keys | 0 |
| entries of combined-v1 changed or missing (verify_keys_unchanged) | 0 |
| rd.* keys | 535 |

## Findings

**Banned words:** none
**Hardware lines:** 
- docs/03_results/ASSUMPTIONS.md:15: (reproduced in `lora.py`; the datasheet itself was not re-opened in the redesign round, so it is listed as "fo
**Over-strong words:** 
- docs/03_results/NEGATIVES_REGISTER.md:18: | N20 false-alarm control (conformal guarantee) | Whether a conformal threshold holds the false-alarm rate at 
- docs/06_references/NOVELTY_SCAN.md:116: ## P4 (VZCrash detector: memory, augmentation, false-alarm guarantee)
- docs/06_references/NOVELTY_SCAN.md:123: | Conformal severity interval | arXiv 2609.11592 abstract | CHOIR (Rafe and Das) | No novelty claim: conformal
**Verdict mismatches:** none
**Missing:** none
**Bad origin:** none

```
143686 entries at combined-v1; 0 changed or missing; 535 added {'rd.': 535}
```
