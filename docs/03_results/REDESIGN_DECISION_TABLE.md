# Redesign decision table (D8)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | One row per redesign hypothesis: original result, diagnosis, fresh result, verdict, prior work, allowed wording, placement (generated). |
| Evidence labels used | NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; GS-CA = GPS-slotted critical alerts; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; LoRa = long-range radio modulation; OS-DR = overhear-and-suppress retries with deadlines; UA-SCT = uncertainty-aware SCT |
<!-- header:end -->

Rule (D8): a redesign enters the main paper only if it is supported in the custom simulator AND agrees in the established simulator; supported ones are described as "v2 designed from a diagnosis of v1 failure, tested once on a fresh held-out grid". Failed ones go to the negatives register. Final Holm p-values: `REDESIGN_B_RESULTS.md`. Every table caption points to `ASSUMPTIONS.md`.

| Id | Original result | Diagnosis | Redesign | Fresh held-out result (95% interval) | Verdict | Nearest prior work | Allowed wording | Placement |
|---|---|---|---|---|---|---|---|---|
| H-D1a | UA-SCT lost to the severity table in some cells (`DIAGNOSIS_UASCT.md`) | static table; 5 s spacing leaves too few tries at high loss; gain only from lowered thresholds | D1 loss-adaptive deadline table | FRESH-A: smallest per-cell gain +0.026; ns-3 on S-X: smallest -0.013, 8 cells fail | SUPPORTED in the custom simulator; **differs in ns-3 (simulator-dependent)** | retry limits and timeouts in LoRaWAN and Khan et al.; the 2020 mines paper not opened | In the custom simulator D1 did not lose to the severity table in any of 64 cells; in ns-3 it did in some cells. | supplement |
| H-D1b | same; quick retries won at high loss | same | D1 | FRESH-A +0.162 [+0.159, +0.164]; S-X: custom +0.116, ns-3 +0.021 | SUPPORTED in the custom simulator; **not met in ns-3** | as above | D1 raised delivery by about 16 points at loss of 40% or more in the custom simulator; the gain was about 2 points in ns-3 and is simulator-dependent. | supplement; not in the abstract |
| H-D1c | duty limit | airtime within budget | D1 budget in the table | 0 runs above the limit in both simulators | SUPPORTED | LoRaWAN duty rules (regulatory value not verified) | D1 stayed inside the duty limit in every simulated run. | supplement |
| H-D1s | (strict baseline) | six baselines per cell; Nessa-style added after Session 1 (ADDED-AFTER-SESSION-1) | D1 | FRESH-A six baselines: smallest -0.003, mean +0.031; **with the Nessa-style baseline added (ADDED-AFTER-SESSION-1, not in the Holm family): smallest -0.031, mean +0.022, 16 cells below the bound**; S-X not met in both simulators | SUPPORTED on FRESH-A with six baselines; **NOT SUPPORTED with seven (ADDED-AFTER-SESSION-1)**; not met on S-X | Nessa et al. CNS 2020 (secondary description), Tamang-style slots, quick retries | Against the best baseline of each cell D1 is not shown to be better: the gain over the best of seven is about 2 points on average and negative in some cells. D1 is better than the severity table, and than quick retries by about 3.6 points, but not reliably better than the best baseline per cell. | supplement |
| H-D2a | OS-DR lost in 8 of 32 cells | 0.88 of suppressed alerts had never reached the base | D2 gateway-signed cluster ACK, stop only if listed, defer otherwise | smallest per-cell change -0.001 | SUPPORTED | aggregated or group ACKs for LoRaWAN exist (A2S2-LoRaWAN, DG-LoRa; abstract level) | D2 did not lose delivery in any cell. | supplement |
| H-D2b | same | same | D2 | burst gain +0.011 [+0.011, +0.012] against 5 points required | NOT SUPPORTED | as above | No claim of a burst gain. Negative result. | negatives register |
| H-D2c | event ACK under a shared key can be forged by a key holder | shared key | gateway-signed listing | bounded model: no vehicle-key holder stops another vehicle; stolen gateway key is outside the claim | SUPPORTED | none found in the sources checked (not a claim of absence) | In a bounded model (2 vehicles, small bounds) a holder of only a vehicle key could not make another vehicle stop retrying. | supplement |
| H-D3 | GS-CA lost in all 16 burst cells | 0.54 of failures were collisions or a deaf gateway; fixed K put 2.7 times as many frames on the channel | D3 slotted retries, burst size from overheard frames | gain +0.001 [+0.000, +0.001] against 5 points required; no harm | NOT SUPPORTED | Tamang et al. MSWiM 2023 (abstract level); synchronous LoRa (arXiv 2012.07480) | No claim. Slotting without an oracle rarely activates because vehicles rarely overhear each other in this channel model (inferred). | negatives register |
| H-D4a | R3 extra airtime 38% against a 40% bound; R2 frame effect not significant (power 0.22) | R3's provisional frame is already a 14-byte flash; a 24-byte frame is longer | D4 24-byte provisional frame with 8-byte tag | extra airtime 0.410 to 0.496; 0 of 48 cells below 0.25 | NOT SUPPORTED | US 9758120 (provisional crash alarm over cellular, patent) | No claim. The short provisional frame did not lower the extra airtime of the two-stage alert. | negatives register |
| H-D4b | as H-D4a | as H-D4a | D4 | not run | NOT_RUN | as above | No claim. | NOT_RUN list |

## D1 against the baselines (A1 and A2)

- **The severity table is a weak baseline here** (it waits 5 s before the initial Critical send and retries without spacing). **Most of D1's gain over it is also available from quick retries:** D1 minus quick retries is +0.036 [+0.035, +0.037] over the FRESH-A cells, against +0.162 over the severity table at loss of 40% or more. The abstract and the claims use D1 against the best baseline per cell, not against the table.
- **Nessa-style baseline (ADDED-AFTER-SESSION-1; implemented from a secondary description, parameters k = 1, A = 1 s chosen on the DEV grid):** D1 minus Nessa-style +0.050 [+0.049, +0.051] pooled over the 64 FRESH-A cells; D1 is better by at least 2 points in 75% of the cells (73% with the lower bound above 2 points); range per cell -0.031 to +0.129. By the reading rule fixed in V12 11.1 D1 is better than Nessa-style on average. Nessa-style is the best of the seven baselines in 17 cells, and H-D1s with seven baselines is **not met** (16 cells below the -2 point bound).
- Reading: D1 is not claimed as an improvement over the best baseline per cell, and it is not claimed over prior work in general (the CNS 2020 paper was not opened).

## Reading

- **Main paper:** nothing from the redesign round passes the D8 rule. D1 is supported in the custom simulator but does not agree in ns-3 on H-D1a and H-D1b, so it goes to the supplement with the simulator-dependence stated.
- **Negative results kept:** D2 (H-D2b), D3, D4 (`NEGATIVES_REGISTER.md`), next to the original failures they were meant to fix.
- **Hardware:** none. The bench protocol for the two-stage alert is ready (`docs/08_hardware/R3_BENCH_PROTOCOL.md`); the row is NOT_RUN until the author supplies real logs.
- Absence statements use the form "no study found in the sources checked" (web search; IEEE Xplore, OpenAlex (HTTP 503), Scopus, Google Scholar and TRID not run).

## Disclosures carried into the paper (A7)

- The fresh grids share the finite pool of real class pairs and early-exit decision times with development; freshness holds for arrivals, channel draws and geometry.
- The bounded model of H-D2c is exhaustive for 2 vehicles at the preregistered bounds; for 3 vehicles the bounds were reduced (attacker actions at most 2, losses at most 1, one send per vehicle).
- The test statistic is the more conservative of the event bootstrap and the hour-clustered bootstrap.
- Three older tests had failed on numpy-2 attribute errors (`np.trapz`); a compatibility shim replaces the calls without changing any value and the three tests now pass.
- The calibration of the custom simulator against ns-3 missed its own criterion (one cell at 5.4 points in setting (a)); both sensitivity settings are reported in `XSIM_CALIBRATION.md`.
- The Nessa-style baseline was implemented from a secondary description and added after Session 1 (ADDED-AFTER-SESSION-1); it is outside the Holm family.
