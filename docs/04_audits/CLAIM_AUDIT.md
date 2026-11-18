# Independent claim audit (T16, 2026-11-11)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Independent claim audit of round 3. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; KB = kilobyte; NHTSA = National Highway Traffic Safety Administration; SF = spreading factor (LoRa) |
<!-- header:end -->

**Method.** A separate pass (a subagent) read only `docs/03_results/CLAIM_EVIDENCE.md`, `report/novelty_summary.md` and `results/results.json`. It did not see the source code, the decision log, the preregistration or how the claims were produced. It checked wording, origin labels, quoted numbers, overstatement, exploratory flags and contradictions between the two documents. It changed nothing; every fix below was made by the author of the documents, to the wording only. No result was changed.

**Machine checks passed.** Every cited key exists, every origin label matches the `origin` field, every quoted value matches `results.json` to the printed precision (one 0.8 rounding in a flash estimate), and none of the banned words (CLAUDE.md, rule 7) appears.

**70 claims checked, 18 problems reported.** All 18 were checked against `results.json` before acting. Outcome:

| # | Finding | Action |
|---|---|---|
| 1 | HL title says "evaluated end to end" while the hardware row says NOT SUPPORTED | HL title now says the software parts are built and tested and the end-to-end evaluation has not been run |
| 2 | N16 "not better than a severity table" and the burst-simulator result disagree without naming the simulator | N16 title names both simulators and their scenario sets |
| 3 | N28 said H-a, H-b and H-c all hold; T6 said H-c survives all shifts (two fail); H-b's airtime part is PARTIAL | N28, the T6 row and the T14 row reworded |
| 4 | HL and N2 said "no software evidence for impact direction" | HL now cites the front-against-side check on NHTSA tests (N17) |
| 5 | SF "supports the transfer argument" while N23 shows the scale-free features are not invariant | SF title says it is a hypothesis and names the counter-evidence |
| 6 | N19 ranked row quoted seed-42 numbers and a SIMULATED label | now the 5-seed mean and MEASURED_SOFTWARE (timing read from the window length) |
| 7 | N22 and the report said the base ACK budget is never a bottleneck, "at most a few percent" | wrong at high alert rates (up to 0.35 at SF7 and 0.69 at SF12 of the allowance); report and N22 now give the numbers and restrict the claim to the default alert rate |
| 8 | N20 said weighted calibration was not tried; the ranked row used the non-de-duplicated rate; T7 widening margin contains alpha | N20 text, ranked row and T7 wording corrected; "not established" for the margin variant |
| 9 | SUPPORTED and PARTIAL applied differently to simulated and analytical rows | both legends now say what SUPPORTED means for a SIMULATED or ANALYTICAL row |
| 10 | Headline recall 0.900 without the 0.873 on the set without window-level near-duplicates | HL row and the draft paragraph give both (EXPLORATORY) |
| 11 | N14 "no gain at 32 and 64 g" while two intervals clear zero by under a point; tail and 80% target not shown in the claim | wording changed to "no practically meaningful gain"; tail and target already listed under "still missing" |
| 12 | N18 "adds nothing" while the partial association is small and negative with an interval below zero | wording now "no positive added association" |
| 13 | NHTSA high-speed barrier caveat missing from several rows | added to N13, N17, N18, N28 and as a footer to the claim table |
| 14 | N26 "does not help in steady state" holds only against the severity table; single-car result not flagged | wording and EXPLORATORY flags added; spreading-factor raise added to the components that matter |
| 15 | T3 and T8 rows stronger than the numbers (T8 "every cell": 16 of 24) | T3 wording limited to the current-threshold table; T8 row reworded to "most cells" |
| 16 | The C-equivalence row said "equals" while one synthetic N14 check fails | row says equals on the real inputs and names the failing synthetic check |
| 17 | N4: one scenario, no interval, lower all-alert reception not stated; duty limit row lacked "not verified for India" | added to N4 and the duty row |
| 18 | Small items: N25 recall and precision, N21 attack type, "33 NHTSA tests" (should be 176), N10 AP gap, a wildcard key | all corrected |

**Not changed.** The audit's point that N12 is SUPPORTED on simulation only is covered by the new legend. The 15-tree forest against the 56 KB recommended forest is already in the N10 evidence.
