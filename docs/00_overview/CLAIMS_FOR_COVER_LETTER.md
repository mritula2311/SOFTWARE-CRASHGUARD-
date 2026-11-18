# Claims for the cover letter (generated; each claim, evidence label, section, verdict)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Each claim with its evidence label, section and verdict; no claim is stronger than its label. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED_HW_FORMAT, TRACE_DRIVEN, SIMULATED, FORMAL, ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; AUC = area under the ROC curve; ESP32 = a Wi-Fi microcontroller family (Espressif); GS-CA = GPS-slotted critical alerts; NHTSA = National Highway Traffic Safety Administration; OS-DR = overhear-and-suppress retries with deadlines; SF = spreading factor (LoRa); SW-420 = a vibration switch module; UA-SCT = uncertainty-aware SCT; V2V = vehicle-to-vehicle |
<!-- header:end -->

No claim is stronger than its label. Simulated and synthetic items are statements under stated assumptions. No hardware or field claim is made.

| Claim | Evidence label | Section | Verdict |
|---|---|---|---|
| A fast path built from flash and hold alone on the severity table (P1+) does not beat fixed retries by 5 points in at least 60% of held-out cells. | SIMULATED | Fast-path design | H-B2 NOT SUPPORTED |
| The bounded model check finds a CANCEL-reordering counterexample in the design; remembering an unseen CANCEL removes it within the bounds. | ANALYTICAL (model, not implementation) | Protocol check | holds within the bounds |
| On frontal barrier pulses that passed the fidelity check, a synthetic stress test gives the same smallest sensor range as the real pooled records. | SIMULATED (stress test) | Synthetic stress test | H-C3 SUPPORTED (one mode) |
| Real plus synthetic training data does not change the verdicts of the failed NHTSA-side hypotheses that were rerun. | MEASURED_SOFTWARE, EXPLORATORY-REVISED | Negative results | H-F1 NOT SUPPORTED, H-F1b NOT SUPPORTED, H-F1c NOT SUPPORTED |
| Real plus surrogate training windows does not change the verdicts of H-P4b, H-X3, H-X1 on VZCrash. | MEASURED_SOFTWARE, EXPLORATORY-REVISED | Negative results | H-F2a NOT SUPPORTED, H-F2b NOT SUPPORTED, H-F2d NOT SUPPORTED |
| Under the stated assumptions, a slotted fast path, listen-before-talk and a V2V relay do not raise critical reach by 5 points in at least 60% of held-out cells. | SIMULATED | Protocol layers study | H-G3a NOT SUPPORTED, H-G3b NOT SUPPORTED, H-G3c NOT SUPPORTED |
| In the simulated protocol stack the largest single-layer effects on critical reach are capture, hold and SF raise; the effect of tag length 4 against 16 bytes is about 2 points. | SIMULATED | Protocol layers study | descriptive; held-out grid; keys f.g.g2.held.* |
| The VZCrash release contains 217 cross-split identical-array groups; the primary and strict test sets follow from them. | MEASURED_SOFTWARE | Near-duplicate audit | earlier rounds; unchanged |
| A 16-bit 8-tree depth-8 forest keeps AP within 0.0036 of the reference at 37% of its flash estimate. | MEASURED_SOFTWARE; flash ANALYTICAL | Compact detector | H-P4a SUPPORTED (earlier round) |

<!-- v7:start -->
## Release (V7) claims

| Claim | Evidence label | Section | Verdict |
|---|---|---|---|
| Physics-based generators with stated assumptions were built and checked against real data; none of them passes the realism gate (point AUC at most 0.60) in any mode, so none trains a confirmatory rerun. | SIMULATED | Physics generator integrity report | gate failed |
| With no gated synthetic data, the real-only reruns of H-P1, H-P2 and H-P3a give the same verdicts as the original studies. | MEASURED_SOFTWARE | Release results, Q4 table | unchanged |
| Under the stated assumptions, overhear-and-suppress retries (OS-DR) and GPS-slotted critical alerts (GS-CA) do not raise critical reach within 10 s by 5 points in 60% of held-out cells. | SIMULATED | Release results, block A | H-A1 and H-A2 NOT SUPPORTED |
| In a bounded model, one forged event-level acknowledgement from a holder of the shared key stops every vehicle of a cell; the per-vehicle acknowledgement needs one forged frame per vehicle. | ANALYTICAL (model, not implementation) | Release results, block A | H-A3 NOT SUPPORTED |

<!-- v7:end -->

<!-- v11:start -->
## Combined run (V11) claims

Claims about simulated hardware-format logs carry the label SIMULATED_HW_FORMAT: code run on simulated logs generated from stated sensor and link models; no real hardware measurements are reported.

| Claim | Evidence label | Section | Verdict |
|---|---|---|---|
| In simulation, a 14-byte provisional alert from the early-exit rule reaches the base about 1.9 s before the full-window alert, with 11% of provisional alerts retracted and 38% extra airtime. | SIMULATED | Two-stage alert | H-R3 SUPPORTED |
| In a bounded model, one forged event-level ACK from a key holder stops every vehicle; with per-vehicle keys and an ACK bound to vehicle and counter, a compromised node stops only itself, at one extra key derivation per new vehicle id and no extra bytes. | ANALYTICAL (model, not firmware) | Per-vehicle ACK keys | H-R4 SUPPORTED |
| A GPS-time freshness field with a 10 s window accepted at least 99.7% of valid alerts after a car reboot in the simulation; persisting no counter cuts flash writes about 17 times at 100 alerts and 12 boots per car and year. | SIMULATED; ANALYTICAL | Freshness field | H-R1a SUPPORTED, H-R1c SUPPORTED |
| The replay bound inside the window needs a ring larger than the alerts per window: with the ring chosen on the design grid the rate reached 0.033 at the held-out burst. | SIMULATED | Freshness field | H-R1b NOT SUPPORTED |
| In simulated bursts a 24-byte frame delivered more critical alerts within 10 s than the 97-byte frame (mean gain 0.075), and the 97-byte frame with an 8-byte tag is dominated in forgery effort, time on air and delivery; the preregistered sign test over 16 cells was not significant. | SIMULATED; ANALYTICAL | Frame and tag length | H-R2a NOT SUPPORTED, H-R2b SUPPORTED |
| On simulated hardware-format logs the impact-side rule failed under an axis-sign flip and at 10 Hz sampling and held 0.90 under tilts up to 30 degrees, noise x4, bias sd 0.08 g, jitter and dropped samples; the 2 g trigger alone has a false-alarm rate of about 0.6 on bench non-crash events. | SIMULATED_HW_FORMAT | Simulated hardware-format validation | H-S1 NOT SUPPORTED, H-S2 NOT SUPPORTED |
| In the model, the trigger-to-ACK latency is about 519 ms (250 ms window, 97-byte alert, 26-byte ACK, SF7), so a sub-500 ms statement fails for this configuration. | SIMULATED_HW_FORMAT | Latency decomposition | H-S4 SUPPORTED |
| The repository's 58 security cases and the nine simulated scenarios behave as designed in software (0 of 289 attack attempts accepted); the reference verifier persists its counter; the firmware was not tested. | SIMULATED_HW_FORMAT | Security on simulated scenarios | H-S5 SUPPORTED |
| On simulated link logs, UA-SCT and fixed-3 differ by less than 0.012 in critical reach within 10 s at four edge runs, but the 34 dB interval is too wide to show a difference below 0.02. | SIMULATED_HW_FORMAT | Policies on link logs | H-S3 NOT SUPPORTED |
| In simulated bench events SW-420 confirmation removed 0.29 of the false alarms and cost 0.04 of the crash recall; the balance depends on the assumed switch sensitivity. | SIMULATED_HW_FORMAT | SW-420 confirmation | H-S6 NOT SUPPORTED |

<!-- v11:end -->

## Redesign round (V12) claims

- Allowed: "A loss-adaptive retry table (D1) designed from a diagnosis of the severity-table failure was tested once on a fresh simulated grid. The severity table is a weak baseline in this simulator, and most of the gain over it is also available from quick retries (D1 better than quick retries by about 3.6 points); against the best of seven baselines per cell D1 is not reliably better. In ns-3 D1's gain over the severity table was about 2 points and did not meet its bound, so the gain is simulator-dependent." (not for the abstract; the abstract must not state D1 against the severity table)
- Allowed: "In a bounded model with two vehicles, a node holding only a vehicle key could not make another vehicle stop retrying under the gateway-signed cluster ACK; a stolen gateway key is outside the claim."
- Allowed: "The firmware decision path (host build, double precision) matched the Python reference in 10,000 random histories; no ESP32 build, emulator or device measurement is reported."
- Not allowed: any burst-delivery gain for D2 or D3, any airtime gain for the 24-byte provisional frame (D4), any claim that D1 is better in general, any hardware or timing claim, any statement that no prior work exists (use "no study found in the sources checked"; aggregated ACKs for LoRaWAN exist in the literature).

<!-- r3:start -->
## Round 3 (V14) claims

Labels: TRACE_DRIVEN = measured link traces replayed in software; FORMAL = proof or exhaustive model check. No claim is stronger than its label; nothing here is a hardware or field claim.

| Claim | Evidence label | Section | Verdict |
|---|---|---|---|
| On measured London loss sequences, a table-driven retry policy was not worse than six other retry rules on single-link delivery within 10 s; the replay has no crowd and its delivery follows the number of attempts that fit before the deadline. | TRACE_DRIVEN | Round 3, H-T1a (L, M, H) | SUPPORTED, SUPPORTED, SUPPORTED |
| On links with 40% loss or more, D1 delivered 6.7 points more than quick retries on the replay; a no-hold control that retries at once delivered 54.0 against D1's 49.3, so the gain is retry timing, not a mechanism shown by the traces. | TRACE_DRIVEN | Round 3, H-T1b | SUPPORTED |
| On the same measured traces, a 14-byte provisional flash arrived about 1.9 s before the full alert with about a third more airtime. | TRACE_DRIVEN | Round 3, H-T1c | SUPPORTED |
| In a single-link timing model, D1 delivers within 10 s after up to six lost uplinks where quick retries do not, and never exceeds the 1% hourly allowance. | FORMAL (exhaustive enumeration of the frozen code; not UPPAAL) | Round 3, H-T2 (timed) | SUPPORTED (FORMAL) |
| A Tamarin model of a crash-alert protocol with per-vehicle keys and an ACK bound to the vehicle: authenticity, per-vehicle ACK binding, window and seen-set properties proved; a replay after a base reboot is possible; one reboot lemma not completed. | FORMAL | Round 3, H-T2sec | PARTLY SUPPORTED |
| On the de-duplicated VZCrash test split, the early-exit rule decides a median of 1.75 s before the full window (a stored seed-42 decision set that R3 already used). | MEASURED_SOFTWARE | Round 3, H-T3a | SUPPORTED |
| At the 1% false-alarm target, about 1 in 9 provisional alarms was withdrawn by the full window. | MEASURED_SOFTWARE | Round 3, H-T3b | SUPPORTED |
| The earlier arrival of the provisional alert holds in the custom simulator and on the measured traces; ns-3 was not run for this alert. | SIMULATED and TRACE_DRIVEN | Round 3, H-T3c | SUPPORTED |
| A severity class from the window truncated at 50 ms agrees with the full-window class for about 3% of frontal NHTSA pulses; at 200 ms for 98%. | MEASURED_SOFTWARE | Round 3, T3 class agreement | NHTSA frontal pulses |
<!-- r3:end -->

<!-- pp:start -->
## Part C (combined paper) claims

| Claim | Evidence label | Section | Verdict |
|---|---|---|---|
| The H-C3 stress test, refitted on the development fold and gated on held-out records, gives the same smallest range as the real records for frontal-barrier pulses (32 g); the pole mode failed the gate and is not tested. | SIMULATED | Results A, C2 | H-C3 SUPPORTED (refit) |
| The two-stage alert arrives 1.87 s (SF7) and 2.12 s (SF9) earlier in ns-3 with delivery not worse; its extra airtime is 37% at SF7 and 54% at SF9 against a 40% limit. | SIMULATED | Results C, C5 | ns-3 verdict PARTLY |
| On measured links with loss of 40% or more a control that retries at once delivers 54.0% against 49.3% for D1; the control respects the deadline and the hourly allowance. | TRACE_DRIVEN | Results C, C6 | exploratory; D1 is not a contribution |
<!-- pp:end -->
