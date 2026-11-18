# Diagnosis: synthetic generators

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Status of the synthetic-generator diagnosis (generated). |
| Evidence labels used | NOT_RUN |
| Abbreviations | AUC = area under the ROC curve |
<!-- header:end -->

## 5. Synthetic generators

No generator-v3 run and no `GEN_DIAGNOSIS.md` exist in this repository, and its G1 step is not defined in any file here, so the G1 step is NOT_RUN. The earlier diagnosis is in `docs/03_results/PH_INTEGRITY_REPORT.md`: the physics generators PH-A and PH-B and the refit family generator fail the realism gate in every mode, and the VZCrash-style surrogate fails the discriminator gate (AUC 0.995). D5 consequence: no generator passed for any mode, so no synthetic data is used in this round.

