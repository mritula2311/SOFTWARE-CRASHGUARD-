# Abstract facts (generated)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Numbers an abstract may use, each with its key and label (generated). |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL |
| Abbreviations | UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

Numbers an abstract may use. Each has its results.json key and evidence label. Nothing else should appear as a number in the abstract.

| Fact | Value | Key | Label |
|---|---|---|---|
| bounded check: reachable states with the CANCEL-reordering counterexample | 351754 | `f.b1.ext.design.states` | ANALYTICAL |
| H-B2: held-out cells in which P1+ beats P0 by at least 5 points | 2 | `f.b2.hB2.n_cells_gain5` | SIMULATED |
| simulator check: largest error against 1 - exp(-2G) | 0.01224 | `f.b3.collision.max_abs_err_vs_aloha` | SIMULATED |
| synthetic stress test: smallest range meeting the 0.80 rule, frontal barrier (g) | 32.0 | `f.c.grid.frontal_barrier.synthetic_smallest_range` | SIMULATED |
| simulation: critical reach within 10 s of capped UA-SCT, held-out grid mean | 0.213 | `f.g.g1.held.P4.reach10_critical` | SIMULATED |
| H-G3a: held-out cells (of 16) in which the slotted fast path loses more than 2 points | 16 | `f.g.g3.hG3a.n_cells_lose2` | SIMULATED |
| F2: recall at the 1% target, best surrogate ratio minus real only (strict set); EXPLORATORY-REVISED | 0.0 | `f.f2.hF2a.gain` | MEASURED_SOFTWARE |
| F1: ranges (of 3) in which real plus synthetic training meets the original H-P1 criterion (nested cross-validation) | 0 | `f.f1.cv.hF1.n_ranges_met` | MEASURED_SOFTWARE |
