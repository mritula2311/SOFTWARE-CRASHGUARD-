# Diagnosis: OS-DR false suppression

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Which OS-DR losing cells involve suppression of an undelivered alert, and what triggers it (generated). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; OS-DR = overhear-and-suppress retries with deadlines |
<!-- header:end -->

## 2. OS-DR against the best earlier policy (P4 with listen-before-talk)

Metric of H-A1: Critical reach within 10 s as seen by the sender (`reach10_critical`), held-out grid (32 cells), paired by hour. A cell is losing when the point difference is below -0.02.

Cells with a loss of more than 2 points: **8 of 32**; cells with a gain of at least 5 points: 10.

| cell | burst | P4+lbt | OS-DR | difference [95%] | suppressions per hour | of which on alerts the base never received | share false |
|---|---|---|---|---|---|---|---|
| n100_p20_sf8_d0.1_b30 | yes | 0.310 | 0.250 | -0.060 [-0.088, -0.033] | 18.9 | 15.4 | 0.81 |
| n100_p20_sf8_d1_b1 | no | 0.819 | 0.779 | -0.040 [-0.113, +0.000] | 0.0 | 0.0 | nan |
| n100_p20_sf8_d1_b30 | yes | 0.360 | 0.239 | -0.121 [-0.146, -0.095] | 18.9 | 15.3 | 0.81 |
| n100_p40_sf8_d0.1_b30 | yes | 0.226 | 0.188 | -0.038 [-0.066, -0.009] | 19.4 | 15.9 | 0.82 |
| n100_p40_sf8_d1_b30 | yes | 0.274 | 0.204 | -0.070 [-0.099, -0.040] | 19.9 | 16.5 | 0.83 |
| n200_p20_sf8_d0.1_b30 | yes | 0.315 | 0.250 | -0.065 [-0.088, -0.040] | 19.1 | 15.9 | 0.83 |
| n200_p20_sf8_d1_b30 | yes | 0.377 | 0.279 | -0.097 [-0.127, -0.068] | 19.1 | 15.4 | 0.81 |
| n200_p40_sf8_d1_b30 | yes | 0.284 | 0.211 | -0.073 [-0.106, -0.037] | 19.1 | 16.2 | 0.85 |

Across all 16 burst cells, **0.88** of suppressed alerts had never been received by the base (false suppression); 1 of the 8 losing cells have no burst, so no suppression happened there (its difference is not distinguishable from zero).

**Trigger (from the code, `world_sim.py`, event `ack_heard`):** a vehicle decodes any gateway ACK that is addressed to another vehicle of the same event cell and then removes its own pending Severe and Critical alerts of that cell. The ACK names the other vehicle, not this one, so it proves nothing about this vehicle's own alert. The ACK is also event-level under one shared key, which is the forgery path found in H-A3.

**Mechanism:** suppression is based on a proxy (another vehicle's ACK) for the state that matters (this vehicle's alert reached the base). In a burst, the early ACKs are heard by everybody, so vehicles whose alerts collided stop and are never delivered. One losing cell has no burst; there OS-DR never suppresses, its interval reaches zero, and with about 100 Critical events per cell a 30-hour estimate of this size is compatible with noise, so no mechanism is claimed for it.

