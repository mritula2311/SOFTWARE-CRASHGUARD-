# Independent audit of the v2 claims (2026-11-12)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | Independent claim audit of the v2 studies. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
<!-- header:end -->

**Method.** A separate pass (a subagent) read only the v2 rows and allowed-wording table of `docs/03_results/CLAIM_EVIDENCE.md`, `docs/03_results/V2_RESULTS.md`, points N29 to N34 of `report/novelty_summary.md` and `results/results.json`. It did not see the code, the preregistration or the decision log, and it changed nothing. All fixes below were made to the wording by the author; no result was changed.

**Machine checks passed.** Every quoted number, interval, p-value, Holm value and origin label matches its `v2.` key; no cited key is missing or NOT_RUN; the banned words do not appear; verdict words agree across the three documents.

**About 55 claims checked; 14 wording problems and 1 label observation.** All were checked against `results.json` before acting.

| # | Finding | Action |
|---|---|---|
| 1 | The intro swapped the origins of E1 and E2 | H-E1 (capacity simulation) is SIMULATED, H-E2 (forgery work factor) is ANALYTICAL; intro, closing lines and the claim table footer corrected |
| 2 | N29 said "on two of three fixed splits" while only split O has its whole interval above zero | Title, V2_RESULTS and allowed wording say so |
| 3 | "The plain estimate is a lower bound in practice" holds at +-16 g only (it fails for 16 tests at +-32 g and 20 at +-64 g) | Wording limited to +-16 g and the failures stated |
| 4 | H-B2 text gave only the largest point harm; cells where a variant is worse with the whole interval below zero were missing (beacon in two cells, demotion in one) | A generated line now lists every such cell; the text says which part of H-B2 holds |
| 5 | N32 "closes the question for per-car rules" and "do not raise" were stronger than the simulation | "No tested variant reached a 3-point gain in these simulated cells" |
| 6 | "A measurable capacity gain was not found" while the 4-byte gain is about one point (interval 0.4 to 1.4) | "A gain of 2 points or more was not found", the interval is shown |
| 7 | H-D2 wording said the result "does not survive the Holm correction" while the raw p-value is already 0.055 | Raw and adjusted p-values and the interval end (0.115) are shown |
| 8 | The 86 ms time saved is over the flagged tests only (56% of Severe or Critical tests); the analogue flags 69% and saves 55 ms | Added to V2_RESULTS, the claim wording and N31 |
| 9 | H-A2: the never-clipped tests are covered about 5% of the time by every interval, and the adaptive intervals are narrower in the middle and highest terciles; the width figures are medians | Added |
| 10 | H-A1: not shown better than the triangle fit (interval includes zero); ridge on all features not compared with it | Added to the allowed and not-allowed wording; the ridge comparison is stated as not made |
| 11 | H-F2 gave a bare 0.32; a loss of up to 2.9 points in critical reach is not excluded; the delay to Severe alerts is not measured | Wording says relative reduction, the possible loss and the missing delay |
| 12 | N33 and the claim row said "duty-capped forgery work factor" although the attempt count is not capped by the duty limit | Wording changed; the years in the table are for a single duty-limited transmitter, not an attacker |
| 13 | H-B3 "not evaluable" without the numbers | Bucket mean gain and best mean gain added (the 80% rule would fail anyway) |
| 14 | 0.55 is the containment of [plain, upper]; the upper bound alone contains the reference for 99 of 176 tests | Wording says "the interval from the plain estimate to the pulse-family upper bound" |
| 15 | Holm p-value keys were labelled MEASURED_SOFTWARE for simulated hypotheses | Each key now carries its hypothesis's origin |
