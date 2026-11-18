# Diagnosis: R2 frame-size sign test

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Power of the 16-cell sign test for the R2 frame-size effect (generated). |
| Evidence labels used | ANALYTICAL |
<!-- header:end -->

## 4. R2 frame size: power of the 16-cell sign test (ANALYTICAL)

The effect met the 5-point threshold in 10 of 16 held-out cells; the exact one-sided sign test gives p = 0.227. At level 0.05 the test needs at least 12 of 16 cells. Power if each cell independently shows the effect with probability q:

| q | power of the sign test at 0.05 | power at 0.05 with 10 or more cells needed (this was the observed count) |
|---|---|---|
| 0.625 | 0.223 | |
| 0.75 | 0.630 | |
| 0.9 | 0.983 | |
| 1.0 | 1.000 | |

The observed rate of 10 of 16 (q = 0.625) gives a power of about 0.22: the test would miss an effect of this size most of the time. The 16 cells are not independent draws of an effect (they share the same 30 simulated hours per grid), and a sign test discards the size of the effect. D4 therefore uses a paired bootstrap over events, which uses every event.

