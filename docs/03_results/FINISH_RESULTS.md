# Finishing round: results (generated)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Results of the finishing round (generated). |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | AP = average precision; CNN = convolutional neural network; TSTR = train on synthetic, test on real; V2V = vehicle-to-vehicle |
<!-- header:end -->

Branch `finish` from tag `positive-push-v1`; software only; every number read from `results/results.json` by `crashguard.fin_docs`. Labels: MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN; F rows are EXPLORATORY-REVISED. Design: `docs/02_preregistration/PREREGISTRATION_V5.md` (committed before Blocks B, C, F, G ran; addendum 1 lists the deviations).

## Verdicts (Holm over the 18 preregistered hypotheses)

| Hypothesis | Original / what | Raw p | Holm p | Verdict |
|---|---|---|---|---|
| H-B2 | P1+ against P0 (flash and hold on the severity table) (SIMULATED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-C3 | synthetic requirement matches the real one within one range step (SIMULATED) | 0.001 | 0.018 | SUPPORTED |
| H-F1 | H-P1: direct classifier against the anchored estimator (EXPLORATORY-REVISED) | 0.788 | 1.000 | NOT SUPPORTED |
| H-F1b | H-P2: anchored interval (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-F1c | H-P3a: abstention at 70% retention (EXPLORATORY-REVISED) | 0.781 | 1.000 | NOT SUPPORTED |
| H-F1d | H-X6 on splits G and O (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT_RUN |
| H-F1e | H-X5 rank preservation (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT_RUN |
| H-F2a | H-P4b: augmentation, recall at the 1% target (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-F2b | H-X3: group-aware training (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-F2c | H-X2: trigger cascade (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT_RUN |
| H-F2d | H-X1: fixed-point forest (AP and flash) (EXPLORATORY-REVISED) | 0.001 | 0.018 | NOT SUPPORTED |
| H-F2e | H-X8: sequential rule (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT_RUN |
| H-F2f | H-P4c: calibration over the trivial rule (EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT_RUN |
| H-F3a | N28: P3 against the lowered table at equal escalation (SIMULATED, EXPLORATORY-REVISED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-F3b | H-P3b: abstain routing against the lowered table (SIMULATED, EXPLORATORY-REVISED) | 0.930 | 1.000 | NOT SUPPORTED |
| H-G3a | slotted fast path against pure ALOHA (SIMULATED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-G3b | listen-before-talk against duty-cycle-only access (SIMULATED) | 1.000 | 1.000 | NOT SUPPORTED |
| H-G3c | V2V relay against no relay (SIMULATED) | 1.000 | 1.000 | NOT SUPPORTED |

## One line per task

- **A1** Apache-2.0 licence, NOTICE, CITATION.cff, .zenodo.json; VZCrash statement (CC BY-NC 4.0, revision 42e1482d005c0e545379d6cfa4939486c9fe4249) in every document. **A2** `docs/04_audits/PREREG_V4_AUDIT.md`: no verdict flips. **A3** `docs/07_log/NOT_RUN.md`. **A4** `release/vzcrash_audit_for_authors/` agrees with the package sent.
- **B1** (ANALYTICAL) design: 351,754 states, C3 fails; pending CANCEL: 351,754 states, all 9 properties hold; attack cases 48 of 48 original and 9 of 10 extra (X06 changes by design). Checks the model, not the implementation.
- **B2** (SIMULATED) H-B2 NOT SUPPORTED: 2 of 12 cells gain 5 points, 1 lose more than 2; design grid 2 of 16.
- **B3** airtime against the formula as transcribed (Semtech document not opened): max difference 5.7e-14 ms; collision probability against 1 - exp(-2G): largest error 0.012 (against the finite-population form 0.006); duty violations 0 in 5,040 (B2) and 75,360 (G) runs: 0 and 0.
- **B4** `docs/03_results/NEGATIVES_REGISTER.md`.
- **C** (SIMULATED stress test) fidelity passes: frontal_barrier,other; H-C3 SUPPORTED (frontal barrier: synthetic 32 g, real 32 g); extension: log-peak shift +0.4 gives 64 g for frontal barrier.
- **F0** surrogate: 14 of 28 class x feature marginals matched; nearest-neighbour copies 0.
- **F1** (cv) H-F1 NOT SUPPORTED (0 of 3 ranges); H-F1b NOT SUPPORTED; H-F1c NOT SUPPORTED; H-F1d and H-F1e NOT_RUN.
- **F2** H-F2a NOT SUPPORTED (gain +0.0000 [+0.0000, +0.0000]); H-F2b NOT SUPPORTED (gain +0.0011); H-F2d NOT SUPPORTED; H-F2c, H-F2e, H-F2f NOT_RUN.
- **F3** H-F3a NOT SUPPORTED; H-F3b NOT SUPPORTED.
- **G** baseline on DESIGN: P4; H-G3a NOT SUPPORTED, H-G3b NOT SUPPORTED, H-G3c NOT SUPPORTED; held-out regime map: 9 ties of 16 cells, P3 wins 0.

## F4 summary (original verdict, real-only rerun, real plus synthetic rerun, TSTR)

| Hypothesis | Original verdict | Real-only rerun (r = 0) | Real plus synthetic, best ratio [interval] | TSTR | New verdict | Changed? |
|---|---|---|---|---|---|---|
| H-F1 (H-P1), +-16 g, macro-F1 difference | NOT SUPPORTED (+0.169 [+0.046, +0.291]) | +0.053 [+0.004, +0.096] | +0.070 [+0.021, +0.117] (ratio fe_0,fe_1,fe_5) | macro-F1 0.666 (CNN) | NOT SUPPORTED | no |
| H-F1b (H-P2) | NOT SUPPORTED (reduction 0.018) | see f.f1.cv.hF1b | reduction +0.031 [+0.006, +0.053] | - | NOT SUPPORTED | no |
| H-F1c (H-P3a) | NOT SUPPORTED (ratio 0.744) | see f.f1.cv.hF1c | ratio 0.793 [0.682, 0.895] | anchored TSTR p90 30.0% | NOT SUPPORTED | no |
| H-F2a (H-P4b) | NOT SUPPORTED (-0.0175) | r = 0 is the control | +0.0000 [+0.0000, +0.0000] (ratio 0.000) | AP 0.878 | NOT SUPPORTED | no |
| H-F2b (H-X3) | NOT SUPPORTED (+0.0011) | +0.0011 [-0.0021, +0.0042] | +0.0011 [-0.0021, +0.0042] (ratio 0.000) | - | NOT SUPPORTED | no |
| H-F2d (H-X1) | NOT SUPPORTED (flash clause) | AP loss +0.0000 | AP loss +0.0000 (upper +0.0000) | - | NOT SUPPORTED | no (flash clause is arithmetic) |

The F1 rows use the nested cross-validation (main estimate). The sealed-fold rerun, scored once and labelled revised after the negative, gives for H-F1 at +-16 g: ratio 0 control +0.169 [+0.046, +0.291] (the original result, as it must), best ratio +0.133 [+0.020, +0.247]; criterion met in 0 of 3 ranges. In the cross-validation the best-ratio model minus the ratio-0 control is +0.017 in macro-F1 at +-16 g (a difference of two point estimates, no interval); in the sealed fold it is -0.036. Neither version meets the original criterion.

If no verdict changes, that is a reportable finding about the limits of synthetic augmentation in this setting; the table above shows whether it applies.
