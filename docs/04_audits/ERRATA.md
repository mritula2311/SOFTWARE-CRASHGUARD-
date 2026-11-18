# Errata

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Stored values that are known to be wrong, with the reason and what reads them; no stored value is changed. |
| Evidence labels used | none (this file reports no result) |
<!-- header:end -->

## E1. `vf2.layout.forge.*.p_per_frame` are 0.0

| Item | Statement |
|---|---|
| Keys | `vf2.layout.forge.n1.p_per_frame`, `vf2.layout.forge.n10.p_per_frame`, `vf2.layout.forge.n60.p_per_frame`, `vf2.layout.forge.n1000.p_per_frame` |
| Stored value | 0.0 in each |
| Cause | a rounding slip in the generator of the verify2 run (the probability n x 2^-40 is about 1e-12 and was rounded to 0.0) |
| Correct values | n x 2^-40: 9.09e-13 (n = 1), 9.09e-12 (10), 5.46e-11 (60), 9.09e-10 (1,000); the keys `vf3.layout.forge.index.p_per_frame` and `vf3.layout.forge.trial.n{10,60,1000}.p_per_frame` hold them |
| Readers | none. A search of `src/`, `scripts/`, `tests/` and `paper/` (round 7b, G0.5) finds no code, macro or text that reads a `vf2.layout.forge.*.p_per_frame` key. The `vf2.layout.forge.*.expected_years` keys are a different set and are read only by `scripts/vf2_final_report.py` (a record of the verify2 run). The paper macros `FrameForgeOne` and `FrameForgeSixty` read the `vf3.` keys |
| Action | the keys stay as stored (rule: no stored result changes); the finalize log already says they are not used (`docs/04_audits/FINALIZE.md`, row F1.3) |
