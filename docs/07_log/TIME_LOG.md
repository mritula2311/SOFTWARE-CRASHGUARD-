# Time log (round 3 closing block, T1 to T17)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | Time log of the round-3 closing block. |
| Evidence labels used | NOT_RUN |
| Abbreviations | CNN = convolutional neural network; CV = cross-validation |
<!-- header:end -->

| Time | Task | Note |
|---|---|---|
| 2026-11-11 19:56 | start | clean run 2 still running; T1 to T4 addendum being written |
| 2026-11-11 21:43 | run 2 done and committed | two clean runs agree except the Windows compiled-C checks; T1 to T12 modules written; starting T1 to T4 runs |
| 2026-11-11 22:00 | T1 done | P3 does not win at equal escalation; committed below |
| 2026-11-11 22:00 | T2 done | interval family not better than point family at matched escalation |
| 2026-11-11 22:03 | T3 done | break-even ratio at +-16 g about 4 against P1; no difference against P1e |
| 2026-11-11 22:06 | T4 done | both statements hold (lower-bound rule vs upper end); single car cause: 5 s spacing, confirmed with quick retries |
| 2026-11-11 22:07 | T5, T13 done | strict set recall 0.873; T13 NOT_RUN (no second dataset could be opened) |
| 2026-11-11 22:08 | T6 done | H-a survives 17 of 17 settings; H-c 15 of 17 |
| 2026-11-11 22:35 | T8 done | P3 beats P1 on reach within 10 s in 16 of 24 cells, ties 6, loses 2; against P2 beats 11, ties 13, loses 0; no run above the duty limit (5,760) |
| 2026-11-11 22:36 | T10, T11, T12 done | T11: 10 of 10 designed cases as expected (two document known weaknesses); T12: C3 fails for the design (CANCEL before alert), holds with the fix |
| 2026-11-11 22:59 | T9 done | flash and hold carry the gain; reserve and CANCEL message show no effect on reach; quick retries cost reach in bursts (about 24 min run) |
| 2026-11-11 23:03 | T14, T15 done | Holm: H-a 0.004, H-b below 0.002, H-c 0.018; 10 paper tables and 2 figures, no missing keys |
| 2026-11-11 23:12 | report section for T1 to T14, novelty N26/N28, claim table, compliance rows, run_all and Makefile steps | N28 now NO_IMPROVEMENT_FOUND beyond thresholds; 218 tests pass; ruff clean |
| 2026-11-11 23:24 | T16 done | independent audit: 18 problems, all fixed in wording; docs/04_audits/CLAIM_AUDIT.md |
| 2026-11-11 23:26 | third clean run started | scripts/run_all.ps1 -Clean in the background (log run3.log) to check that the T-block steps rebuild in order; a reference copy of results.json was saved initial |
| 2026-11-12 02:16 | third clean run done | 0 of 99,639 shared entries differ beyond 1e-6 except the 25 Windows compiled-C checks; comparison in docs/archive/logs/cmp3.txt, log in docs/archive/logs/run3.log |
| 2026-11-12 04:02 | v2 preregistration committed (55a17e2) | docs/02_preregistration/PREREGISTRATION_V2.md, before any v2 result |
| 2026-11-12 04:15 | Study A done | H-A1 supported (p90 reduction 16.1 points on split R); run 1 used in-sample residuals for the difficulty model, re-run with cross-fitted residuals (logged) |
| 2026-11-12 04:15 | Study D done | median time saved 86 ms (under 100); the flag misses more Severe or Critical tests than the running delta-V analogue |
| 2026-11-12 04:37 | Study B done | no adaptive variant gains 3 points in any burst cell; a module that re-read results.json on every config made the initial attempt slow (about 20 minutes lost); fixed by reading it once; the run takes 45 s |
| 2026-11-12 04:37 | Studies E and F done (B5 sensitivity at 04:45) | H-E1 gain under 1 point; H-F2 reduction 32%; H-F1 fails for ratios 1 and 10 at the forest's precision |
| 2026-11-12 04:50 | verdicts, V2_RESULTS.md, claim rows, novelty points N29 to N34, paper tables, tests (228 pass), run_all and Makefile steps | Study C NOT_RUN with the reason |
| 2026-11-12 05:52 | journal push: T13a selection record committed (f936442) | criteria and decision rules before any held-out signal was read; 1,340 candidate tests |
| 2026-11-12 06:21 | T13a and T13c done | 739 held-out records; the 80% criterion is reached in no cell; fill + ridge does not beat the spline at +-16 g there; two repeated records found among the 176 |
| 2026-11-12 06:28 | Block 3 code and rules committed | independent VZCrash audit reproduces every stored count |
| 2026-11-12 06:34 | PREREGISTRATION_V3 and novelty-scope notes committed (e9abb7d) | before any Block 4 result |
| 2026-11-12 06:36 | Blocks 2 and 3 done | sensor table (8 parts, 99 configurations), VZCRASH_AUDIT.md, leakage sensitivity |
| 2026-11-12 06:47 | X5 and X6 done | H-X5 not met (rank correlation 0.75); H-X6 criterion met (p90 gain 31 points) |
| 2026-11-12 07:05 | X1, X2, X3, X4, X7, X8 and Holm verdicts done | only H-X6 supported; one crash-mask mistake in X2 fixed (logged) |
| 2026-11-12 07:34 | Block 5 packaging and determinism check | tables, figures, REFERENCES.md, statements, claims, docs/05_data_code/REPRODUCE.md, 236 tests pass, ruff clean; 9,258 entries identical on a second run |
| 2026-11-12 08:07 | Z0 | pooled set (913 records) and sealed split written; commit follows |
| 2026-11-12 08:37 | P4a | test scoring done once for the sweep; freeze commit 1a3aff90 |
| 2026-11-12 08:38 | P4a | validation sweep, freeze (1a3aff9), test scoring once, measured host size; H-P4a criterion met |
| 2026-11-12 08:41 | P4b | test split scored once per model and seed; freeze commit 7a42da37 |
| 2026-11-12 08:42 | P1 sealed | sealed fold scored once for P1; freeze commit 1d225110 |
| 2026-11-12 08:42 | P4c | test split scored once per model and seed; freeze commit ab6239f4 |
| 2026-11-12 08:42 | P2 sealed | sealed fold scored once for P2; freeze commit 505ac57f |
| 2026-11-12 08:43 | P3a sealed | sealed fold scored once for P3a; freeze commit 23015883 |
| 2026-11-12 08:54 | P4c | test split scored once per model and seed; freeze commit ab6239f4 |
| 2026-11-12 09:12 | P3b sealed | sealed fold scored once for P3b; freeze commit 015e2b5a |
| 2026-11-12 09:15 | P4d | EXPLORATORY int8 CNN scored once per seed; freeze commit 35f77661 |
| 2026-11-12 09:21 | P1 to P4c | all seven preregistered hypotheses scored: H-P4a supported, six not supported; P4d exploratory result; deviations logged |
| 2026-11-12 09:32 | closing | exploratory CV, determinism check, claim audit, docs, tables, figures |
