# Round 6: final report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Round 6 final report: what ran, what did not, what contradicted the documents, integrity checks, push commands. |
| Evidence labels used | ANALYTICAL, NOT_RUN |
| Abbreviations | ESP32 = a Wi-Fi microcontroller family (Espressif); NHTSA = National Highway Traffic Safety Administration; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Branch `round6` (from tag `round5-v1`, with the manuscript of branch `verify` merged in). Tag `round6-v1`. Nothing was pushed, uploaded or sent. No file under `data/hardware` was read. Detail: `docs/03_results/ROUND6_RESULTS.md` (decision table), `ROUND6_R1_MICRO.md`, `ROUND6_R2_SEQUENTIAL.md`, `ROUND6_FOOTPRINT.md`, `ROUND6_BOUNDS.md`, `ROUND6_CODE_VERIFICATION.md`.

## What ran

| Item | Status | Result |
|---|---|---|
| V17 preregistration | committed before any development run | seven hypotheses, one Holm family |
| R6-1 micro-confirm | ns-3 policy `r6m` (16 cells, seeds 1 to 60), LoED traces (half 0), formal models | H-R6-1a, 1b, 1c supported (1a is nearly automatic; the trace part of 1b is zero by construction) |
| R6-2 sequential early exit | frozen after four development iterations, one held-out run | H-R6-2a and H-R6-2b not supported (14.2 ms gain; retractions up 12.6 points) |
| R6-3 formal | ProVerif then Tamarin, bounded quarantine model | H-R6-3a and H-R6-3b supported; variant B of 3b holds by construction, the finding is the attack on variant A |
| R6-4 footprint | Espressif GCC 12.2.0 installed at user level, decision path built for the ESP32 | sizes and stack frames reported; emulator counts, timing and energy NOT_RUN (no emulator) |
| R6-5, R6-7 | bounds, greedy-retry proposition with proof, spreading-factor rule, quarantine indexing | ANALYTICAL |
| R6-6 reframing | manuscript, cover letter, supplement | new title, constrained-node profile, section C8, regime-boundary wording |

Holm over the seven hypotheses: 5 supported. Ledger over all rounds: 130 hypotheses in 13 versions (`docs/04_audits/HYPOTHESIS_LEDGER.md`, keys `r6.ledger.*`).

## What did not run, or ran with a limit

- NHTSA timing check of R6-2: NOT_RUN (cut order of V17).
- Emulated instruction counts, timing and energy of the decision path: NOT_RUN (no ESP32 emulator).
- Custom simulator for R6-1: NOT_RUN (the ns-3 policy is the only implementation of the micro-confirm).
- The ns-3 micro frame has 13 bytes (the smallest frame of the LoRaWAN module); the design frame has 7. At SF7 the two have the same airtime as the 14-byte flash, so the saving is against the 97-byte confirm only. The trace results also report the 7-byte airtime.
- The linker of the Xtensa toolchain stops with a segmentation fault under `--gc-sections` in WSL; the linked image keeps unused functions and the per-function sizes give the used path.
- The paper compiles only with a stand-in class (IEEEtran) here, as in the verification run; the Access class is not available.

## What contradicted the documents

- V17 section 0 quoted a mean decision time of 720 to 780 ms for the fixed early-exit rule. On validation and held-out data it is 112 ms (median 50 ms, floor 50 ms), so the preregistered 200 ms gain of H-R6-2a was out of reach by arithmetic. The hypotheses were kept as written (`docs/07_log/DECISIONS.md`, 2026-11-16).
- With the micro-confirm replacing the 97-byte confirm, the extra airtime against single-stage is negative in most cells, so H-R6-1a would pass trivially; the second statistic (airtime per delivered alert over R3's) is reported.
- The pending-table lifetime (10, 30, 60 s) made no difference in development because the confirm is always sent within 10 s of the acknowledged flash.

## Integrity checks

- No tagged result or earlier key changed: all 146,704 entries of the `round5-v1` file and all 146,841 of `submit-v1` are unchanged (compared by value). Round-6 ledger totals are under `r6.ledger.*`; the `vf.ledger.*` keys are unchanged.
- Earlier ns-3 policies give byte-identical output with the new binary (42 runs, 0 differences).
- Mutation testing: 31 of 31 (R6-2) and 35 of 35 (R6-1) killed; two fresh-context reviews, findings applied before each freeze.
- Banned-word, style, link and paper audits pass; full test suite passed (655 passed, 2 skipped, before the last small test file, which passes).

## The single most important thing to check by hand

The held-out ns-3 comparison of H-R6-1 uses a 13-byte micro frame and a delivery definition that includes the 10 s limit and that removes events dropped in any of the three runs. Read `ROUND6_R1_MICRO.md` section 2 and check that "airtime over R3" (0.46 to 0.77) and "per delivered alert over R3" are the numbers you are willing to quote, and not the extra airtime against single-stage, which is negative in most cells because the micro-confirm replaces the 97-byte confirm.

## Push commands (not run)

```
git remote add origin <your repository URL>
git push origin round6
git push origin round6-v1
```

Release archive: `release/crashguard-round6-v1.zip` (git-ignored), hash in `release/crashguard-round6-v1.zip.sha256`, manifest in `release/crashguard-round6-v1.manifest.txt`.
