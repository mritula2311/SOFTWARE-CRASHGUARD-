# Round 5 code verification (V16 section 10)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Round 5 code verification: tests, known-answer reproductions, mutation testing and the ns-3 byte-identity check for L1 to L5. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Checks made before any development run: unit and property tests, a known-answer reproduction of an earlier number for each algorithm, hand-written mutants (at least 20 per algorithm, at least 80% killed), the byte-identity check of the ns-3 application, and an independent review against V16. Tests: `tests/test_r5_l1.py` to `tests/test_r5_l5.py`. Mutants: `scripts/r5_mutants.py`, `scripts/r5_mutants_l34.py`, run by `scripts/r5_mutation.py`; tables in `results/tables/r5_mutation_<algorithm>.csv`.

| Algorithm | Tests | Mutants applied | Killed | Share killed | Survivors |
|---|---:|---:|---:|---:|---|
| L1 mounting calibration | 40 | 28 | 26 | 93% | L112, L127 |
| L2 post-event corroboration | 23 | 33 | 31 | 94% | L232, L233 |
| L3 wake-on-motion | 17 | 27 | 27 | 100% | none |
| L4 spreading-factor ladder | 14 | 26 | 26 | 100% | none |
| L5 threshold co-design | 17 | 29 | 28 | 97% | L525 |
| L6 gateway placement | 14 | 26 | 24 | 92% | L618, L619 |
| L7 forward-secure ratchet | 10 | 21 | 21 | 100% | none |
| L8 flood containment | 9 | 23 | 22 | 96% | L818 |
| L9 dispatch rule | 5 | 20 | 18 | 90% | L906, L920 |
| L10 leakage audit | 15 | 23 | 22 | 96% | L1021 |
| L11 mirror-flip detection (added after session 1) | 17 | 32 | 27 | 84% | L1104, L1108, L1109, L1115, L1119 |

## Known-answer reproductions

- **L1 mounting calibration:** bit-exact reproduction of `hwsim_v2.sense` for the identity mounting and of the tilt and mirror variants; the X1 balanced accuracy (`x1.A.r16.balanced_acc`) reproduced by the identity rotation without L1.
- **L2 post-event corroboration:** the baseline arms reproduce `r3.t3.a1.n_provisional_alarms` (2,857), `r3.t3.a1.retraction_share` and the same two keys at the 5% target exactly on the full test split (reads no L2 result).
- **L3 wake-on-motion:** the cache covers every triggered event of the detector cache; the interrupt is never later than the trigger sample for a detected event; the B100 accelerometer features equal the always-on features.
- **L4 spreading-factor ladder:** in ns-3 the ladder with a start margin of -100 dB and k = 1000 gives the output of Z0 byte for byte; `L4INV` prints 0 0; the earlier policies are byte-identical (below).
- **L5 threshold co-design:** the custom link model equals `ar_r3.arrival` for the same random stream; the ns-3 delay extraction is checked on a synthetic run file.
- **L6 gateway placement:** the coverage radius formula gives 3.98 km and 2.51 km as the ns-3 log-distance model does; FARS 2021 loads with 38,000 to 40,500 crashes and fatality weights; greedy maximum coverage checked on small instances against hand answers.
- **L7 forward-secure ratchet:** exhaustive enumeration of 4^0 to 4^10 event sequences; the checks are shown to fire on deliberately broken step functions; Tamarin outcome reader.
- **L8 flood containment:** hand-worked transitions of the state machine; regression values of the exploration and the legitimate replay.
- **L9 dispatch rule:** break-even values checked against the stored round-3 retraction share (0.2405 minutes of delay per dispatch).
- **L10 leakage audit:** UCI HAR published sizes (7,352 and 2,947 windows, 21 and 9 subjects) reproduced from the downloaded archive.
- **L11 mirror-flip detection (added after session 1):** noise-free right-handed turn gives agreement +1; every mirror flip gives -1; rotation invariance; blind spots as derived.

## Surviving mutants

- L1 mounting calibration, L112 (gravity not subtracted in the segment): equivalent: the still-window mean is parallel to the estimated gravity direction, so the projection that removes the vertical part removes it exactly.
- L1 mounting calibration, L127 (rotated gravity not added in the NHTSA part): nearly equivalent for the side rule: a constant offset is removed by the pre-trigger baseline; it can only move the 2 g trigger sample, which is rotation-invariant for the magnitude.
- L2 post-event corroboration, L232 (wrong half): wiring of the held-out half inside `evaluate_heldout`; a test would have to compute held-out numbers, which is not done before the freeze (the pure statistics function `heldout_stats` is tested, and the review checked the wiring).
- L2 post-event corroboration, L233 (equal-budget threshold at twice the budget): wiring of the threshold choice inside `evaluate_heldout` (same reason as L232).
- L5 threshold co-design, L525 (budget loosened): the budget is not binding at the tested false-alarm rate, so a looser integer rounding changes no feasible set.
- L6 gateway placement, L618 (lattice points without a nearby candidate kept): lattice points without a candidate within 100 km are not reached by the tested instances.
- L6 gateway placement, L619 (bisection direction): the tested bisection reaches the same count from either direction on the instances used.
- L8 flood containment, L818 (worst low-confidence count not kept): the maximum low-confidence count is not tied to a state in the tested horizons.
- L9 dispatch rule, L906 (pre-alert time loss): the pre-alert option has a second term whose change does not cross a decision boundary in the tested values.
- L9 dispatch rule, L920 (negative gain allowed): the clipped gain is never negative for the tested inputs.
- L10 leakage audit, L1021 (file identity from the initial 100 bytes): the files of the test archive differ within their initial 100 bytes, so the shortened identity cannot show.
- L11 mirror-flip detection (added after session 1), L1104 (quasi-steady samples ignore the speed change): equivalent for the symmetric synthetic drive (the mean forward acceleration is about zero).
- L11 mirror-flip detection (added after session 1), L1108 (acceleration not scaled to m/s^2): equivalent: scaling the horizontal acceleration does not change the unit vectors of the regressions.
- L11 mirror-flip detection (added after session 1), L1109 (vertical part not removed): equivalent for the tested z-up drives: the vertical part is already near zero.
- L11 mirror-flip detection (added after session 1), L1115 (longitudinal fit not normalised): equivalent: a positive scalar does not change a direction.
- L11 mirror-flip detection (added after session 1), L1119 (speed not multiplied into the yaw rate): equivalent for the tested drives: dropping the speed from the regressor leaves the direction.

## ns-3 application

The earlier policies (p1, quick, d1, r3s, r3t, r3a, lorawan) at SF7 and SF9, extra loss 0.3, seeds 3, 17 and 41 give byte-identical output with the binary built before the change and the binary built after it: 42 runs compared, 0 differences (`scripts/r5_ns3_identity.sh`). The random variable of the new policies is created only for `z0` and `l4`, because creating one in any policy would shift the automatically assigned random streams of the others. The per-run invariants of the new policies are printed as `L4INV <late> <duty>` (transmissions that would end after the deadline, transmissions beyond the duty limit); both must be 0 and are tested.
