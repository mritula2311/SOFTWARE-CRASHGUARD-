# Preregistration V17: round 6 (micro-confirm, sequential early exit, prover extensions, bounds)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Round 6 (micro-confirm, sequential early exit, prover extensions, bounds): designs, hypotheses, thresholds, data roles and kill criteria, committed before any run. |
| Evidence labels used | MEASURED_SOFTWARE, TRACE_DRIVEN, SIMULATED, FORMAL, ANALYTICAL, EMULATED, NOT_RUN |
| Abbreviations | ASI = acceleration severity index; CRC = cyclic redundancy check; ESP32 = a Wi-Fi microcontroller family (Espressif); HMAC = hash-based message authentication code; NHTSA = National Highway Traffic Safety Administration; RAM = random-access memory; SF = spreading factor (LoRa) |
<!-- header:end -->

Committed before any development run of round 6. Branch `round6` from tag `round5-v1`; key prefix `r6.`. Nothing here changes a stored result or an earlier verdict. One Holm family of seven hypotheses; the paper reports the total over all versions (the ledger of the verification run lists 123 hypotheses of V1 to V16; V17 adds seven).

## 0. What was checked before this file, and what it corrects

1. **The median of the fixed early exit cannot be improved.** The stored decision time of the fixed early-exit rule is 50 ms at the median (`r3.t3.a1.provisional_ms_median`; 66.9% of provisional alarms are decided at the earliest checkpoint, 50 ms; mean about 720 to 780 ms over seeds, `s6.a1.*`). A hypothesis that the median is 200 ms earlier is therefore impossible by arithmetic (the detector has checkpoints at 50, 100, 200, 400, 800 and 1,800 ms only). H-R6-2a is stated on the **mean** decision time among events that raise a provisional alarm under both rules; the median is reported and is bounded below by 50 ms.
2. **The micro-confirm saves airtime only through the payload.** Exact time on air (explicit header, CRC, 8 preamble symbols, bandwidth 125 kHz, coding rate 4/5; `crashguard.lora.airtime_ms`): at SF9, 6 to 8 bytes take 123.9 ms, 9 to 12 bytes 144.4 ms, 13 to 14 bytes 164.9 ms, 97 bytes 533.5 ms; at SF7, 6 to 8 bytes 36.1 ms, 13 to 14 bytes 46.3 ms, 97 bytes 169.2 ms. A 7-byte micro-confirm is 25% shorter than the 14-byte provisional frame at SF9 and 22% shorter at SF7, so the gain is the replacement of the 97-byte confirm, not of the flash.
3. **Content is lost, and a comparator would hide it.** A micro-confirm carries the class and a position offset; it does not carry delta-V, ASI, peak, switch bits or the reserved telemetry of the 97-byte alert. With the micro-confirm in place of the full alert the two-stage total is shorter than the single-stage total, so the extra airtime of the R3 definition is negative and H-R6-1a would pass trivially. H-R6-1a is therefore preregistered with the R3 definition AND with a second reported statistic, the airtime per delivered crash alert relative to R3's two-stage total; the loss of content is a stated limit of the design.
4. **The duty model.** The ns-3 application and the custom simulator use an hourly allowance (`g_limit = duty x 3600 s` of airtime in any trailing hour; `xsim_alert.cc` line 859), not a per-transmission off-time. See section 8.1.
5. **The quarantine counter exists only in the L8 model.** `r5_l8.process` is keyed on the vehicle and has no verification stage: every alert counts toward its strikes. The implemented base verifier (`sct_protocol.SctBase`, `packet.py`) checks the tag before anything else and has no quarantine counter. See section 8.3.

## 1. Integrity rules

1. V17 is committed before any development run of round 6.
2. At most five logged development iterations per algorithm (R6-1, R6-2), each logged in `docs/07_log/DECISIONS.md`.
3. The configuration is frozen by hash (`r5_common.freeze_entry`) before the held-out run; the held-out run is made once.
4. No data that served as held-out for the same question is used as held-out here (section 2).
5. Code verification for R6-1 and R6-2: unit and property tests, at least 20 mutants of the new code with at least 80% killed, one known-answer reproduction, and a review in a fresh context. Nothing reads `data/hardware`.
6. Seed 42. Intervals are 95% bootstrap intervals. A p-value is (count + 1)/(resamples + 1) with 2,000 resamples (floor 0.0005); a FORMAL hypothesis has p = 1e-300 if proved and 1 otherwise. Holm over the seven hypotheses; a missing hypothesis enters with p = 1.

## 2. Data roles

| Question | Development | Held-out | Note |
|---|---|---|---|
| R6-1 ns-3 | ns-3 development seeds 101 to 120, SF9 and SF7, both settings, losses 0 and 0.3 | ns-3 seeds 1 to 60, the 16 cells of the R3 run (SF7 and SF9, two sensitivity settings, extra loss 0, 0.1, 0.3, 0.6), the same events and arrivals as R3 | fresh seeds are not available for the same events; the comparison with R3 is paired (same seed) |
| R6-1 traces | LoED half 1 of the V14 device split (the HELD-OUT half of round 3) is NOT used | **LoED half 0 (the DEVELOPMENT half of round 3, never a held-out set for any question)**, devices grouped L, M, H as in V14 | the sniffer set (Zenodo 7919213) is not used: all its devices were the held-out set of H-A1b |
| R6-2 | VZCrash train and validation (frozen detector family, `r5_det`), NHTSA frontal pulses for timing only | VZCrash test events with `int(sha256('r6|' + id), 16) mod 2 = 1` (HALF1 of a new hash) of the de-duplicated test set | **no VZCrash event is unused as held-out**: the test split was scored by `s6_early`, `r3_t3` and V16. This half was evaluated by other hypotheses (not for the sequential rule); the risk is that the detector's operating point was chosen on validation data only, which is unchanged, so the optimism is small but not zero |
| R6-3 | none (formal) | none | |

## 3. R6-1: chained micro-confirm

**Frames (fixed here).** Provisional frame: the existing 14 bytes (`sct_protocol`, tag T1 of 8 bytes, 16-bit short node id, 16-bit counter). **Micro-confirm and micro-cancel: 7 bytes.** Byte 0: type bit (0 confirm, 1 cancel), 3-bit severity class (for a cancel the reason), 2-bit event type, 1-bit position-offset flag, 1 spare bit. Byte 1: position offset, signed 4-bit east and 4-bit north in units of 128 m relative to the last position the base holds for the vehicle (heartbeat or earlier alert), present when the flag is set. Bytes 2 to 6: truncated tag of **5 bytes** = HMAC-SHA256(K_vehicle, "M" || T1 || byte 0 || byte 1 || boot counter)[:5]. The ASCII letter "M" separates the micro-confirm from the other frame types. The base keeps a pending table keyed by T1 for 30 s after it acknowledges a provisional frame.

**Tag length.** Per forgery attempt 2^-40. The ceiling of the attacker's rate at the 1% limit and SF7 is 36 s / 36.1 ms = 997 frames per hour (8.7 million per year); the expected time to one accepted forgery of a micro-confirm for a pending flash is then 2^40 / 8.7e6 = 1.3e5 years if every frame hit a pending flash, and the pending window (30 s) makes it much larger. An 8-byte tag (2^-64) is the repository's analysis for the 97-byte alert; a 4-byte tag would give 0.8% per year at that ceiling, which is rejected. The 5-byte choice is analytical (ANALYTICAL) and is repeated in `r6.r1.forge.*`.

**Fallback.** If the node has not received the acknowledgement of its provisional frame when the confirm is due, it sends the full 97-byte confirm as in R3 (so delivery is never lower than R3's by construction of the rule; H-R6-1b tests it). A micro-confirm whose T1 is not pending is rejected and the node's retry then sends the full alert after the next unacknowledged attempt.

**Design choices allowed in development (at most five iterations):** the spacing of micro-confirm retries and the pending-table lifetime (10, 30, 60 s). Nothing else.

**Simulators.** New ns-3 policy `r6m` in `xsim/ns3/xsim_alert.cc` (earlier policies must stay byte-identical, checked by `scripts/r5_ns3_identity.sh`). The custom simulator is NOT used (NOT_RUN: the ns-3 application is the only implementation of the micro-confirm). Trace replay: as `r3_t1` with attempt j of the micro-confirm seeing the state of frame s + j.

### Hypotheses

- **H-R6-1a** (SIMULATED). At SF9, in each of the 8 ns-3 cells (two settings, four extra losses), the upper 95% limit of the two-stage extra airtime (R3 definition: two-stage total over single-stage total minus one) is at most 0.40. Also reported: the ratio against R3's two-stage total.
- **H-R6-1b** (SIMULATED and TRACE_DRIVEN). In each of the 16 ns-3 cells and each of the 3 LoED loss groups, the lower 95% limit of (final critical delivery within 10 s of the micro-confirm scheme minus that of R3) is at least -0.01.
- **H-R6-1c** (FORMAL). In Tamarin and ProVerif models (symbolic, per-vehicle key, Dolev-Yao, node compromise by key reveal): (i) a micro-confirm is accepted only if it binds to a provisional frame that the same vehicle sent; (ii) it cannot be replayed onto another provisional frame or another vehicle; (iii) a micro-cancel cannot be forged by the holder of another vehicle's key; and (iv) a control model whose tag omits T1 finds an attack on (i) or (ii). All four must hold for the hypothesis to be supported.

**Kill criterion:** H-R6-1a or H-R6-1c fails.

## 4. R6-2: sequential early exit

**Rule.** At each checkpoint m in {50, 100, 200, 400, 800} ms the running log-likelihood ratio S_m = sum over checkpoints up to m of log( f1_m(s_m) / f0_m(s_m) ) is compared with an upper threshold A (send the provisional frame) and a lower threshold B (stop: no provisional frame, the 1,800 ms decision decides). f1_m and f0_m are class-conditional score densities of the frozen per-length forests, estimated on the development split only (histogram with 20 equal-count bins, add-one smoothing). Scores are the stored `r5_det` per-length scores (seed 42). No new detector. A and B are chosen on development so that the provisional false-alarm rate (share of non-crash events with a provisional alarm) equals that of the fixed early-exit rule on the same development split within 0.1 point; among those pairs the one with the smallest mean decision time is taken. Up to five development iterations (histogram bins 10, 20, 40; smoothing; the grid of A and B).

**Reference.** The fixed early-exit rule of `s6_early` / `r3_t3` at the same operating point (1% target).

### Hypotheses

- **H-R6-2a** (MEASURED_SOFTWARE). Among held-out crash events that raise a provisional alarm under both rules, the mean decision time of the sequential rule is at least 200 ms earlier than the fixed rule's; the lower 95% limit of the mean difference is at least 200 ms. The median (floor 50 ms) is reported and is not tested. NHTSA frontal pulses give a second, descriptive timing check (their scores come from the same forests).
- **H-R6-2b** (MEASURED_SOFTWARE). The retraction share (provisional alarms withdrawn by the full window) rises by at most 2 points: the upper 95% limit of (sequential minus fixed) at the same provisional false-alarm rate is at most 0.02.

**Kill criterion:** either fails.

## 5. R6-3: formal extensions

- **H-R6-3a** (FORMAL). Forward secrecy under a hash ratchet K_{i+1} = H(K_i, label), one step per acknowledged alert and one per boot epoch: compromise of K_n does not allow forging or reading alerts sent under K_i for i < n. Order of work: ProVerif before Tamarin (`formal/proverif/`), then Tamarin with at most 3 ratchet steps (the bound is stated with the result; the earlier model of L7a ran out of the 5 GB heap). Supported if one prover proves it within the stated bound; the bound is part of the result.
- **H-R6-3b** (FORMAL). In a bounded model (3 vehicles, an attacker without any vehicle key that may send up to 4 frames per slot over 6 slots), the quarantine rule cannot be triggered for a vehicle V by frames that fail tag verification. Two variants are modelled: **(A)** the counter counts every frame carrying the claimed id before verification (the rule as the L8 model reads), and **(B)** the counter counts only verified frames. The model must find the attack for (A) and prove (B). Supported if (B) is proved; (A)'s attack is reported as a finding, with the design fix (a per-cell counter for unverified frames used only for flood defence, never quarantining a vehicle, plus a per-vehicle rate limit applied after verification).

## 6. R6-4: embedded footprint (no hypothesis)

Build the decision path (trigger, forest, framing, HMAC, freshness, micro-confirm) for the ESP32 with the Espressif toolchain if it can be installed without root and without bypassing a policy; report flash and static RAM from the map file and the stack usage from `-fstack-usage` (MEASURED_SOFTWARE: build artifacts). If an emulator runs it, executed instructions per decision and per HMAC are EMULATED; no time or energy conversion beyond an ANALYTICAL estimate with each datasheet current cited. If the toolchain cannot be installed here, the result is NOT_RUN with the reason.

## 7. R6-5: operating-regime bounds (no hypothesis; ANALYTICAL and empirical boundaries)

Tables of exact airtime and of the maximum number of attempts that fit before each class deadline under the hourly 1% allowance, for SF7 to SF9 and frame sizes 7, 14 and 97 bytes; the extra-airtime ratio of the two-stage scheme (flash plus full confirm; flash plus micro-confirm) as a function of SF; the spreading factor at which the 40% bound is crossed (section 8.2). Empirical boundaries are stated as measured limits with intervals from stored keys: the sensing range by crash mode, the trace finding on attempts within the deadline, and the L11 accelerometer-only flip limit.

## 8. R6-7: analysis and documents (no new empirical hypothesis)

1. **Greedy retries.** Duty model (verified in section 0): an hourly allowance. The proposition is proved for the per-transmission off-time model and for the hourly allowance, under the stated assumptions, and compared with the LoED and sniffer-set results; the wording is 'dominant under the stated assumptions'.
2. **Spreading-factor rule.** Derived from the exact airtime formula and checked against the ns-3 cells already run (SF7 pass, SF9 fail).
3. **Quarantine indexing.** Reading of the code (section 0) and the two-counter design note (section 5).
4. Wording limits: 'none of the estimators tested recovers pole and side impacts'; 'dominant under the stated assumptions'; 'an observability and sufficiency evaluation for single-point low-cost sensing'.

## 9. R6-6: documents only

System profile and abstract, introduction with three measured problems, title, negatives as regime boundaries, target venues. No result changes. The manuscript lives on the branch `verify` (the verification run rewrote it); the reframing is applied there and recorded in `docs/07_log/DECISIONS.md`.

## 10. Not adopted from the external review

Six items are not adopted; each is recorded with its reason in `docs/07_log/DECISIONS.md` (delta-V as a constraint of its own estimate; a Gilbert-Elliott retry MDP under a non-binding duty budget; pile-up slotting; a Wahba calibration for mirror flips; emulator energy claimed at cycle precision; impossibility claims drawn from empirical failures).

## 11. Cut order

If time runs short: (1) R6-4 beyond the build, (2) the NHTSA timing check of R6-2, (3) the Tamarin run of H-R6-3a after ProVerif, (4) the trace part of R6-1. A part that is not run is NOT_RUN with the reason; its hypothesis enters the Holm family with p = 1.
