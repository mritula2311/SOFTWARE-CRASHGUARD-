# Round 7 report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Round 7 report: literature gate, A and B results, formal outcomes, paper changes, hand steps, push commands. |
| Evidence labels used | SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; ESP32 = a Wi-Fi microcontroller family (Espressif); IEEE = Institute of Electrical and Electronics Engineers |
<!-- header:end -->

Written for: the author, who decides what goes into the submission and what is pushed. Step-by-step log: `docs/04_audits/ROUND7.md`. Decision table: `docs/03_results/ROUND7_RESULTS.md`; details: `ROUND7_A.md`, `ROUND7_B.md`. Preregistration: `docs/02_preregistration/PREREGISTRATION_V18.md` (SHA-256 of the file with CRLF read as LF: 4433428af0a9617a9f990ef055d06ef58d9fcd5eaf9ac042bd6a8259d3fc3eef, committed as b8405d1 before any round-7 run).

## 1. Result in one table

| Hypothesis | Verdict | What the numbers say |
|---|---|---|
| H-R7-A1 reserve keeps the follow-up on time in at least 99% of runs under full ACK suppression | **not supported** | At the load that exhausts the shipped policy under a 1% allowance, the reserve of one event keeps it on time in 70.4%, 26.8% and 35.2% of runs at SF7, SF8, SF9 (the shipped policy: 2.1%, 0.6%, 0.1%). Under a 10% allowance and under a 10% per-transmission off-time the reserve gives 100% (the shipped policy: 85.3%, 56.3%, 24.3% and 0%) |
| H-R7-A2 benign cost at most 1 point of delivery and 10% of the median time | **not supported** (A2b alone supported) | Delivery falls 2.36 points (lower limit 2.43) in the high-loss trace group under a 10% off-time; 0.39 points under the hourly allowance; median time ratio 1.000 in every cell |
| H-R7-A3 gating rule with the reserve | descriptive | The enabling spreading factor does not move (SF7) under all three duty models |
| H-R7-B1 resolution at most 1 ms per frame | **supported** | at most 23.1 microseconds (Python), 3.1 microseconds (C) at 1,000 vehicles and a window of 16 |
| H-R7-B2 collision probability at most 1e-6 | **not supported** | 0.216 at 2 bytes, 3.7e-6 at 4 bytes; 1.5e-8 at 5 bytes |
| H-R7-B3 diff-equivalence proved and the fixed-id control fails | **supported** | proved for two alerts and for unboundedly many; both controls fail with a trace |

Holm over five (A1, A2, B1, B2, B3): 2 supported. The paper reports all of them, as written.

## 2. L0, the literature gate

Four databases (OpenAlex, Crossref, DOAJ, arXiv) with the strings of the brief plus eight targeted strings; the IEEE Xplore open page returned only a page shell without results, so no IEEE hit count exists (nothing was bypassed). Full text opened: Pélissier et al. (WiSec 2024), Dossa et al. (arXiv 2025), Suciu et al. (2019), Pélissier et al. (WiSec 2022); abstracts of twelve more. **Neither stop rule was triggered.** The assistant's findings were confirmed: Pélissier et al. propose sequential and resolvable pseudonyms, argue unlinkability informally for a passive observer, and handle replay through the frame counter; Dossa et al. study reactive jamming with no energy or duty accounting and no defence. Closest to A at abstract level: the MAC-layer denial-of-service paper for confirmed transmission (IEEE Communications Letters 2023): **its full text was not read**; open it before submission. Claims written before running: A is claimed only for the two-stage alert with analytical, formal and simulated checks, not as a new attack; B claims a formal model, compatibility with replay protection and quarantine, and not the pseudonym idea.

## 3. A: duty-budget reserve

- **The attack in the shipped policy** (ANALYTICAL): the caps (4 flash tries, 4 confirm tries) make one fully suppressed event cost 0.86 s (SF7), 1.52 s (SF8), 2.79 s (SF9) of airtime; the attacker needs at most 0.57 to 0.60 of that to jam the acknowledgements. Spending a trailing-hour allowance of 1% takes 42, 24 and 13 such events in an hour (418, 237, 129 at 10%): one event every 86 s at SF7. This needs sustained triggers; **how often a detector produces them was not measured**, so it is a regime, not a measured threat. Under a 10% per-transmission off-time the effect is immediate: the confirm starts 0.10, 1.55 and 4.84 s late (SF7, SF8, SF9, median decision time).
- **Policy**: reserve R = four confirm copies plus the micro-confirm; only confirm, micro-confirm and cancel frames spend it; flash tries are withdrawn when the follow-up is due; under an off-time a flash try must end its off-time before the follow-up is due. D_max (hourly) = A14 + 0.32 s: 0.37, 0.40, 0.48 s at SF7 to SF9; 0 under the off-time.
- **Formal (bounded enumeration)**: 1,139,264 configurations per policy. Invariant 1: 0 violations. Invariant 2 while the reserve is intact: 0 violations in 889,376 runs. Control: the shipped policy violates it (162,752 runs). The unconditional form fails for the reserved policy with two earlier events (31,488 runs): the earlier follow-ups spend the reserve. **The enumeration bounds differ from V18** (B 16 to 40 and at most two earlier events instead of B 24 to 60 and three), and an earlier run with a window of 10 steps was replaced before anything was reported because earlier events never shared a window (log A2.2).
- **Why H-R7-A1 fails**: with a 1% allowance and n* earlier suppressed events, the flash frames were admitted while the reserve was full, and the follow-ups of the earlier events then used the reserve. A reserve sized for four events (R = 16 confirm copies plus the micro frame) gives 100% at every cell (post-run, outside the family) and costs 8% (SF7) to 24% (SF9) of the 1% allowance.
- **Benign cost**: the time reserve admits 3 flash tries at SF7 under the off-time (2 at SF8, 1 at SF9, none from SF10), which costs 2.4 points of delivery on lossy links. SF8 and SF9 benign cost: NOT_RUN (no loss trace; ns-3 policy files are frozen).
- **Not done**: the ns-3 ACK-drop hook (cut by the preregistered order; it needs a new ns-3 policy and was already NOT_RUN by decision D5). No result is measured on hardware.

## 4. B: pseudonymous ids

- **Design** (`ROUND7_B.md`, `FRAME_LAYOUT.md` section 9): p = leading L bytes of HMAC-SHA256(k_v, "P", boot, ctr), L = 2 (flash, cancel) or 4 (alert, ACK); boot, counter and event id leave the clear; position and payload encrypted; the tag covers boot and counter as unsent associated data; the base holds a window of 16 pseudonyms per vehicle and a hash index; quarantine, seen-set and boot-counter rules act on the resolved id. Frame sizes do not change (the 15-byte flash becomes 14).
- **A defect found by running it**: without the counter in the tag, two window entries of one vehicle with equal 16-bit pseudonyms are ambiguous (the C benchmark resolved 199,911 of 200,000 frames at L = 2). Fixed; Python and C resolve all frames; the ProVerif models were rerun.
- **Formal** (ProVerif 2.05, Tamarin 1.12.0; run times 0 to 42 s): diff-equivalence holds for two alerts and for unboundedly many; the fixed-id control and a variant that sends the boot counter in clear fail with traces. Authenticity, unique ids with the boot counter (the no-write control fails), micro-confirm binding and micro-cancel (the control without T1 fails) and no framing by the quarantine counter (the rule-A control fails) hold in ProVerif; the injective forms are not provable in ProVerif (table semantics) and are covered by Tamarin L4, L4b, L5 (verified), L6 (refuted, as in C4), L7 and both executability lemmas (verified). **The injective no-framing form for the quarantine is not proved.** Tamarin observational equivalence was not attempted (the item at the head of the cut order).
- **Measured / analytic**: resolution at most 23.1 microseconds per frame (Python), 3.1 (C) on an Intel Core Ultra 7 255H; the frame after a reboot costs 84 ms in Python (a linear scan; **a design item to fix before any implementation**). Node routine on the ESP32 target: 94 bytes of code plus 4 of literals, no static data, deepest stack path 1,184 bytes (compile only; instructions and energy NOT_RUN).
- **Limits**: position, timing, frame length and radio fingerprints stay visible; an attacker with a vehicle key is outside the model; the window is abstracted as a table entry per sent alert.

## 5. Paper changes

`paper/main.tex`: two paragraphs in C4, one in C5, one in related work, three rows in the negative-results table, one ledger row, one abstract sentence, two clauses in the contribution bullets (the contributions stay eight; 8 figures and 5 tables as before). Every new number is a macro of `paper/generated/numbers_r7.tex` (96 macros, `src/crashguard/r7_paper.py`); nine new references with a status line. Supplement: a round-7 section (V18, results, A, B, prior art), `FRAME_LAYOUT.md` section 9 and rows F17 to F20, the ledger (136 preregistered, 123 run, 47 supported, 71 not supported, 4 partly, 13 not run; H-R7-A3 is descriptive and counted in the preregistered and run columns only). Cover letter block and highlight 3 regenerated (`scripts/r7_cover.py`). Audit: lint 0 errors, bare numbers 0, forbidden words 0. **The paper was not compiled** (no TeX distribution).

## 6. What contradicted the documents or the brief

- The tag `submit-v3.1` does not exist; `round7` starts from the head of `final2` (two documents after `submit-v3`).
- The brief's directories `docs/02_prereg` and `docs/01_literature`: V18 is in the existing `docs/02_preregistration`; the prior-art file is in the new `docs/01_literature`.
- The brief's framing, that the attacker makes the node retry until the budget is gone, holds only for sustained triggers under the shipped caps; the immediate effect is the lockout under a per-transmission off-time.
- V18 itself uses the words the wording rules forbid (in a sentence that quotes them and in prose). It is kept byte-identical to its hash, so `scripts/doc_style_check.py` skips that one file, with the reason in the script.
- An earlier run of the formal enumeration used a window too short to show the limit (replaced, logged).

## 7. For the author

1. **Most important**: read the H-R7-A1 result in `ROUND7_A.md` section 3 and decide how the paper frames the reserve. The registered design (one event) fails at a 1% allowance; the design that works (four events) was found after the run. The paper says so, but a reviewer may prefer a preregistered re-test of the four-event reserve, which this round did not do.
2. Open the MAC-layer denial-of-service paper (IEEE Communications Letters 2023) in full; if it already has a duty-budget reserve, the A claim has to be narrowed to the two-stage alert only (the claims are written that way already).
3. Decide on the resolution of a rebooted vehicle (84 ms): an index by boot window or a short boot hint in the flash.
4. Confirm the author names and venues of the references marked "not verified" in `paper/references.bib` (four of the nine new ones), and compile the paper on Overleaf.
5. Push (nothing was pushed): the commands are in the section below and in the release step of the log.

## 8. Release

See `release/crashguard-submit-v4.manifest.txt` and `release/crashguard-submit-v4.zip.sha256` (the archive is not tracked). Tags: `round7-v1` and `submit-v4`. Push commands for every branch and tag are printed at the end of the session and listed in `docs/04_audits/ROUND7.md` (row REL.5).

<!-- r7b_deviations:start -->
## Deviations from the registered plans (round 7 and round 7b)

| No. | Where | Deviation | Effect |
|---:|---|---|---|
| 1 | Round 7, base | Round 7 branched from the head of `final2`, not from `submit-v3.1`: that tag does not exist (round 7b checked: no tag, no commit of the close-out prompt). `submit-v3` differs from the head of `final2` by two documents | none on a result; the close-out items that were missing were applied in round 7b (G0) |
| 2 | Round 7, A bounded check | The enumeration used bounds that differ from the V18 text: allowance 16 to 40 units, a window of 30 steps, at most 2 earlier events (V18 text: 24 to 60 units, at most 3 earlier events). An earlier run with a window of 10 steps was too short for earlier events to share a window, so the unconditional form could not fail; it was replaced before anything was reported | run 1 (window 10): no result reported. Run 2 (reported in round 7): 1,139,264 configurations per policy, Invariant 1 and the conditional Invariant 2 hold, the one-event reserve fails the unconditional form only with 2 earlier events. Round 7b (V19) adds a third enumeration with allowances 40, 44, 48, a window of 70 steps and up to 5 earlier events |
| 3 | Round 7, A1.5 | The ns-3 ACK-drop hook was cut: the ns-3 policy files are frozen, so the attack was simulated with the event engine `r7_engine` (checked draw for draw against `r3_event` and `micro_event`), not in ns-3 | the A1 results are SIMULATED by the engine; ns-3 is NOT_RUN for this item |
| 4 | Round 7, documents | `scripts/doc_style_check.py` skips `PREREGISTRATION_V18.md` because the file is frozen at its committed SHA-256 (its wording is not edited after the runs); V19 is not skipped and passes the check | the style tool has not checked the wording of V18 (it may contain words that the rules ban; for example, V18 uses the banned word once for a transmission) |
| 5 | Round 7, B1 | The tag-coverage defect was found by the C benchmark, not by a model: at 2-byte pseudonyms two window entries of one vehicle can share a pseudonym, and a tag that does not cover the counter accepts the earlier entry (199,911 of 200,000 frames resolved). The tag now covers boot and counter as unsent associated data; the models were rerun | the fix is confined to the pseudonym variant (FRAME_LAYOUT.md section 10.3); the ProVerif and Tamarin results quoted are for the fixed design |
| 6 | Round 7b, G0 | The brief's "about 0.7 of a spreading-factor step" belongs to the 0 dBi case (1.85 dB). For the dipole case (4.00 dB) the same arithmetic gives 1.4 steps at the simulators' 2.8 dB per step; the paper uses the computed value | wording and key `r7b.g0.power.extra_margin_sf_steps` |
| 7 | Round 7b, V19 | Control F4 as written (the k = 1 policy violates the unconditional Invariant 2 with at most 3 earlier events) is not met: in the 70-step window the one-event reserve fails from 4 earlier events. The control works at the bound of 4 (k = 1 fails at an allowance of 40, k = 4 does not). The k = 4 policy fails from 5 earlier events (V19 expected 4) | reported as found in `ROUND7B_RESULTS.md`; no check was changed after the run |
| 8 | Round 7b, G3 | The round-7 report called the injective no-framing lemma "not proved". The exact status is a ProVerif trace of two base threads racing on the seen-set, plus the absence of any Tamarin quarantine model; a Tamarin model with an atomic seen-set was added and verifies both forms | the paper says the property holds with an atomic seen-set |
| 9 | Round 7b, V19 | The size of the reserve (four events) was chosen from round-7 data; the registered confirmation uses fresh seeds and unchanged thresholds | confirmation, not a blind test; stated in V19 section 0 and in the paper |
<!-- r7b_deviations:end -->
