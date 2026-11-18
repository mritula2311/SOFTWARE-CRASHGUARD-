# Round 6: code verification

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Round 6 code verification: tests, mutation testing, known-answer checks and fresh-context reviews per algorithm. |
| Evidence labels used | none (this file reports no result) |
<!-- header:end -->

Rule 5 of `docs/02_preregistration/PREREGISTRATION_V17.md` section 1: unit and property tests, at least 20 mutants with at least 80% killed, a known-answer reproduction and a review in a fresh context, before each freeze.

| Item | Tests | Mutants (killed) | Known answer | Fresh-context review |
|---|---:|---:|---|---|
| R6-2 sequential rule (`src/crashguard/r6_seq.py`) | 29 in `tests/test_r6_seq.py` | 31 of 31 (`results/tables/r6_mutation_r2.csv`) | the fixed rule's share decided at 50 ms reproduces the stored R3 figure within 0.01, on the R3 set of crash events | findings on the selection objective, development log content, test objects in development runs, the freeze file list and test strength; all applied before the freeze except the two limits stated in `ROUND6_R2_SEQUENTIAL.md` |
| R6-1 micro-confirm analysis and trace replay (`src/crashguard/r6_micro.py`) | 21 in `tests/test_r6_micro.py` (including a deterministic ns-3 check) | 35 of 35 (`results/tables/r6_mutation_r1.csv`) | the stored P1 cell (SF9, shipped, loss 0.3) is reproduced when the micro run is the R3 run; the trace micro event equals R3's delivery on 300 random traces | findings on frame size at expiry, the 10 s limit, the per-delivered airtime statistic, a held-out marker and file naming; all applied before the freeze |
| ns-3 policy `r6m` (`xsim/ns3/xsim_alert.cc`) | `tests/test_r6_micro.py` (lifetime 0.0001 s gives the R3 run line for line; lifetime 30 s sends micro frames) | covered by the line-for-line check | earlier policies byte-identical with the previous binary: 42 runs, 0 differences (`scripts/r5_ns3_identity.sh`) | as above |
| Micro-confirm tag in C (`firmware_r6/cg_r6.c`) | `tests/test_r6_firmware.py` | not mutated (stated) | 200 random keys, ids and counters match Python's `hmac` tag byte for byte; a flipped bit is rejected | not reviewed separately |
| Formal models (`formal/proverif/r6_*.pv`, `formal/r6_micro_confirm.spthy`) | control models (a tag without T1) are attacked in both provers | not applicable | outputs in `formal/out/r6/` | not reviewed in a fresh context (stated) |

Limits. The quarantine exploration (`src/crashguard/r6_quarantine.py`) and the airtime helper of the bounds have small tests (`tests/test_r6_other.py`) and no mutation run. Variant B of H-R6-3b holds by construction of the model (frames that fail verification are dropped before the counters), so the proof of B is trivial and the content of the hypothesis is the attack on variant A. Full suite before the last small test file: 655 passed, 2 skipped.
