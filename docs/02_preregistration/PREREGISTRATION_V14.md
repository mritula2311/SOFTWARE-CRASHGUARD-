# Preregistration V14: round 3, simulator-independent evidence (T1 to T4)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Round 3 (T1 to T4): trace-driven replay, formal proofs and timed checks, two-stage alert on real crash data; hypotheses, thresholds, kill criteria, one Holm family. |
| Evidence labels used | MEASURED_SOFTWARE, TRACE_DRIVEN, SIMULATED, FORMAL, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; CRC = cyclic redundancy check; CSV = comma-separated values; ESP32 = a Wi-Fi microcontroller family (Espressif); GPS = Global Positioning System; NHTSA = National Highway Traffic Safety Administration; RSSI = received signal strength indicator; SCT = severity-classified transmission; SF = spreading factor (LoRa); SNR = signal-to-noise ratio; SX1278 = a 433 MHz LoRa radio chip; UA-SCT = uncertainty-aware SCT; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Date: 2026-11-14. Branch `final` from tag `redesign-v1.1`. Key prefix `r3.`. Committed before any T1, T2 or T3 run. Nothing in this round tunes an algorithm: D1, quick retries, the severity table, UA-SCT, the Nessa-style policy, fixed 3 retries and the standard LoRaWAN-style retry rule are used as frozen in `redesign-v1.1` (`rd_frozen_A.json`, `rd_frozen_C.json`, `rd_policy.py`, `world_sim.py`, `s6_early.py`, `ar_r3.py`). Hardware data (`data/hardware`) is not used.

## 0. Why this round, and what was looked at before this file

D1 lost its effect when moved from the custom simulator to ns-3, so a protocol claim that rests on one simulator is weak. This round uses link traces measured in real networks (TRACE_DRIVEN), proofs and exhaustive checks (FORMAL), and real crash data (MEASURED_SOFTWARE).

Looked at before this file was written, and nothing else: (1) the structure of the data files (column names, number of daily files, number of records of the Brno file: one device, 1,527 messages); (2) the README of LoED. **No loss rate, no autocorrelation and no replay result had been computed.** Every rule below that depends on the data (inclusion, group limits, event model) is fixed from the prompt and from the frozen code, not from the traces.

Labels: TRACE_DRIVEN, FORMAL, MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN. No hardware label is used.

## 1. T1: trace-driven evaluation (TRACE_DRIVEN)

### 1.1 Data

| Dataset | Source | Version and licence | Use |
|---|---|---|---|
| LoED, "The LoRaWAN at the Edge Dataset" (Bhatia, Breza, Marfievici, McCann; DATA '20; arXiv 2010.14211) | Zenodo record 4121430, file `LoED_LoRaWAN_at_edge_dataset.zip`, downloaded 2026-11-14, SHA-256 `8960cc3ad25b8bd3c99a5d9f371b191bae25e2bd5ca8b9f0cedd5fa4452cf3f3`; 188 daily CSV files, 1.5 GB unpacked | CC BY 4.0 (Zenodo record). Nine gateways in central London, 2019 to 2020. Columns used: time, device_address, gateway, crc_status, spreading_factor, rssi, snr, mtype, fcnt | Primary (all hypotheses) |
| "Measurements of LoRaWAN Technology in Urban Scenarios: A Data Descriptor" (Data 2021, 6(6), 62; Brno University of Technology with Tampere University authors) | Zenodo record 6228358, downloaded 2026-11-14; file `exportMessages_2019 LoRaWAN_CRA_1527_original.json` | CC BY 4.0 (Zenodo record); the code mirror is MIT-licensed | Descriptive only: it holds one device (1,527 messages), so no split by device is possible and no hypothesis uses it |

The raw files stay in `data/raw/` (git-ignored). Both licences allow the use; both are cited in the paper.

### 1.2 Loss sequences (rules fixed here)

1. LoED rows with `crc_status = 1`, `device_address != -1` and a valid `fcnt` are kept. Copies of one frame (same device, gateway and `fcnt` within 2 s: antenna or channel duplicates) are merged.
2. **Link = device** (network level): a frame counts as received if at least one of the nine gateways decoded it with a valid CRC. Gaps in the 16-bit frame counter of the union sequence are frames sent and not received by any gateway.
3. Consecutive received counters f, g give a gap of d = (g - f) mod 65536. For 1 <= d <= 100 the d - 1 frames in between are lost. d = 0 is a duplicate (ignored). d > 100, or a counter that decreases from below 60,000 (a reset), starts a new segment: it is not counted as loss (the device was off or silent).
4. Frames of one segment form the 0/1 reception sequence of the link (1 = received). Time stamps of lost frames are interpolated linearly between their received neighbours.
5. **Inclusion:** at least 300 frames (received plus lost) in total over its segments. **Groups by loss rate p (lost / total):** L: p < 0.10; M: 0.10 <= p < 0.40; H: p >= 0.40.
6. **Split:** by device, hashed: `int(sha256("t1|" + device_address).hexdigest(), 16) % 2`; 0 = DEVELOPMENT, 1 = HELD-OUT. Only HELD-OUT devices enter the hypotheses. The DEVELOPMENT half is used to check that the code runs and the invariants hold; no parameter is chosen on it (nothing is tuned).
7. Reported for the HELD-OUT half and for the DEVELOPMENT half: the per-device loss rate distribution (quantiles and group sizes), the lag-1 to lag-10 autocorrelation of the loss indicator, the burst-length distribution, and the ratio P(loss at t+1 | loss at t) / p (1 for independent losses; the custom simulator assumed independent losses), with RSSI and SNR summaries.

### 1.3 Replay (rules fixed here)

Event: a Critical alert at crash instant 0 with deadline 10 s (V7 and V12 convention); delivery means reception at the base before the deadline (the transmission ends no later than 10 s). The alert is ready after the window of 1.8 s plus 0.05 s compute (`replay.COMPUTE_S`, `config.POST_S`) plus the policy's hold: 5 s for the severity table (P1) and for fixed 3 retries (P0), 0 s for the others (as frozen in the SCT machinery).

Start points: for each device, 300 start indices drawn uniformly (seed derived from the device hash and 42) from the positions of its segments that have at least 40 following frames. **Attempt j of an alert sees the reception state of frame s + j** (consecutive frames of the same device). The sub-second spacing of attempts therefore has no effect on the loss state; this is the trace's resolution (frames are seconds to hours apart) and is a stated limit: it favours no policy by design but removes any benefit of spreading retries beyond a fade, and it keeps the frame-to-frame burstiness.

Downlink rule: the ACK of a received attempt is received with probability 1 - p_dl, drawn independently, where p_dl = the link's own loss rate p (symmetric links, as in the custom simulator); the ACK matters for stopping, for D1's loss estimate and for airtime, not for delivery. Spreading-factor changes do not change reception in the replay (the trace fixes the link), but change airtime and the duty budget: this is conservative for policies that raise the SF. Base SF for all policies: 9 (the S-X convention); time on air from `lora.airtime_ms`; duty limit 1% of an hour (36 s of airtime in a sliding hour, nothing else on the node).

Policies (single-link reductions of the frozen ones; no crowd, no flash frame, no sharing of duty with other vehicles; stated):

| Name | Rule |
|---|---|
| D1 | frozen `D1Table(9)` and `BetaLoss` with the frozen parameters of `rd_frozen_A.json`, load bin 0; the Beta posterior is warmed with the 20 frames before the start (a round fails if the uplink or its ACK is lost); budget share 0.5 |
| quick | spacing 0.3 s after the listen window, SF + 1 after 2 rounds, up to 12 tries |
| P1 (severity table) | hold 5 s, retry at once after the listen window, up to 12 tries |
| UA-SCT (P4) | spacing 5 s for Critical, SF + 1 after 2 rounds, up to 12 tries |
| fixed 3 retries (P0) | hold 5 s, retry at once, 4 tries in total |
| standard LoRaWAN-style confirmed uplink (khan) | send at once, retry after the listen window plus a delay U(1, 3) s, up to 8 retries, no SF change |
| Nessa-style | frozen `k = 1`, `A = 1.0 s`; ACK timeout from the airtime, doubling per stage, a redundant copy after the initial retransmission of each stage, SF + 1 after each pair of retransmissions, up to 12 tries |

Tamang-style slotted access needs a burst-size oracle and a crowd, so it is not part of the single-link replay (stated).

### 1.4 Hypotheses (all on HELD-OUT devices, Critical alerts)

Device-level value of a policy: the mean over its 300 start points of the 0/1 delivery before the deadline. Group value: the mean over devices of the group. Paired bootstrap over devices (2,000 resamples, seed 42, the same resampled devices for every policy).

- **H-T1a (three tests: L, M, H).** In every group, D1 is not worse than the best of the six baselines of that group (the baseline with the highest group mean on the same HELD-OUT devices; the harsher choice) by more than 2 points: the upper 95% limit of (best baseline - D1) is at most 0.02. One test per group; each has a one-sided bootstrap p-value (share of resamples with a difference above 0.02).
- **H-T1b.** On HELD-OUT devices of group H (loss at least 40%), D1 beats quick retries by at least 2 points: the point difference is at least 0.02 and the lower 95% limit is above 0; one-sided p = share of resamples with a difference at most 0.
- **H-T1c.** The provisional alert of R3 on the traces stays within the R3 bounds (`ar_r3.py` logic: a 14-byte flash at the early-exit decision time of the stored per-event decisions of `s6_early` at the 1% target, seed 42, then the full alert or a CANCEL sent three times; at most 4 tries per message; the stage that follows uses the next frames): (a) the median paired difference (single-stage alert arrival minus provisional arrival), over crash events that alarm in both stages, is at least 0.8 s in each of the groups L, M and H; (c) extra transmit airtime is under 40% and the event delivery of the two-stage scheme is not lower than that of the single-stage scheme by more than 2 points (lower 95% limit of the difference at least -0.02) in each group. Decision times and decisions are drawn with replacement from the stored events, independent of the link. p-value: the largest of the clause p-values (intersection test).
- Descriptive only (no hypothesis): the full table of all seven policies by group, with intervals; Severe alerts (30 s) are not evaluated.

**Kill criteria (T1).** Fewer than 100 HELD-OUT devices pass inclusion: T1 is reported as underpowered (not supported), and no group-level claim is made for a group with fewer than 20 devices (the test for that group is NOT_RUN). Any failure of the invariant checks (a counted delivery after the deadline, a transmission above the duty limit, a policy using a frame twice) stops the run until the code is fixed, before the HELD-OUT run.

### 1.5 Limits to state

The traces are uplink receptions, not ACK exchanges; downlink loss is modelled from the uplink by the rule above; the devices are not vehicles (they are mostly static sensors) and their duty cycle, payloads and spreading factors differ from the alert node; frame counters count frames sent, so silent periods of an idle gateway can inflate union loss; the frames are seconds to hours apart, so the loss state of retries seconds apart is not observed (section 1.3).

## 2. T2: formal guarantees (FORMAL)

### 2.1 Security model (Tamarin 1.12.0 with Maude 3.5.1, installed in WSL; versions and model files are recorded with the run)

Two models of the alert protocol: **M0**, the earlier design with one shared key for event-level ACKs (a holder of the key can forge an ACK for any vehicle); **M1**, the final design: a per-vehicle key derived from a master key and the vehicle id, the ACK bound to the vehicle id, the alert counter and the freshness value, GPS-time freshness with a window and a seen-set, and a counter fallback after a reboot (the model follows `PACKET_FORMAT.md`, `PROTOCOL_MODEL.md` and PREREGISTRATION_V11 sections 4, R1 and R4). Time is modelled in epochs (a natural-number counter at the base; the window is the current and the previous epoch).

Lemmas with the expected result written here, before the runs:

| Lemma | Statement | Model | Expected |
|---|---|---|---|
| L1 alert authenticity | If the base accepts an alert of vehicle V, V sent it (injective agreement on vehicle, counter and epoch) | M1 | proved |
| L2 ACK authenticity per vehicle | If vehicle V accepts an ACK, the base sent it for V's alert (counter, epoch); no ACK built from the key of another vehicle W is accepted by V | M1 | proved |
| L3 no cross-vehicle suppression | An adversary that holds the key of vehicle W (a compromised node) cannot make a vehicle V != W accept an ACK for V's alert | M1 | proved |
| L3' cell-wide ACK suppression | The same adversary holding the shared key can make an honest vehicle stop its retries without the base having received its alert | M0 | attack found |
| L4 replay outside the window | An alert whose epoch is older than the previous epoch is never accepted | M1 | proved |
| L4b replay inside the window | An alert is accepted at most once while the base's seen-set is intact | M1 | proved |
| L5 car reboot | After a car reboot (counter reset, GPS time continuing) no alert accepted before the reboot is accepted again, and a fresh alert after the reboot is accepted (executability) | M1 | proved |
| L6 base reboot | After a base reboot (seen-set lost) a replay inside the window is not accepted | M1 | **expected refuted** (known residual: the model should find a replay inside the window after a base reboot; V11 gives this event a probability near 2e-5 per window) |

H-T2sec: L1 to L5 are proved on M1, L3' finds the attack on M0 and L6 is refuted as expected. **Kill criterion:** any of L1 to L5 is refuted, or L3' is not found (the model is then wrong or incomplete and is repaired and rerun, with the change listed as a deviation). Tamarin's symbolic model assumes perfect cryptography; nothing here says the implementation is secure. The earlier work cited and not claimed over: Wesemeyer et al. (EuroS&P 2020) and Dong et al. (ISSRE 2024).

### 2.2 Timed guarantees

Tool: UPPAAL is the tool named in the task. Its licence is for academic use after a registration step that this run cannot complete; it is not used. The retry logic of each policy is a deterministic automaton over time on air, listen windows, holds and the duty blackout, so the check is an **exhaustive explicit-state enumeration of all loss patterns of the leading n attempts (n up to 14, 2^n patterns, 1 ms time resolution) with the frozen policy code** (own code, `r3_t2_timed.py`); where a timed-automata model checker (TChecker) can be built in WSL, the model of one policy is also checked in it and the two are compared. The label is FORMAL (exhaustive finite-model check); the tool is named in every table and is not UPPAAL.

Model: one Critical alert, crash at 0, deadline 10 s, ready time as in 1.3, base SF 9, duty limit 1% in a sliding hour, listen window PROC + ACK airtime + margin after every transmission. For k = 0 to 6, the worst-case time to delivery under at most k consecutive lost attempts is the largest, over all loss patterns with no run of more than k consecutive lost uplinks, of the end time of the earliest received uplink (patterns with no reception within the deadline are counted as a missed deadline and listed). The duty check asks whether any reachable transmission exceeds the allowance.

**H-T2.** For every k in 0..6, D1's worst-case delivery time for Critical alerts is not longer than that of quick retries, and no reachable D1 transmission breaches the duty budget. **Kill criterion:** the checker finds a counterexample; it is then reported with the pattern. The severity-table, UA-SCT, fixed-3, Nessa-style and LoRaWAN-style entries are computed for comparison (the cut order allows dropping the severity table).

## 3. T3: two-stage alert from real crash data (MEASURED_SOFTWARE)

Data: the de-duplicated VZCrash test split (24,022 events) with the stored per-event decisions of seed 42 (`results/tables/s6_events_seed42_a1.csv` and `a5.csv`: triggered, alarm of the early-exit rule E, alarm of the full-window forest F, decision time); thresholds were chosen on validation by `s6_early`; no model is refitted here, and **the test split was already scored once by `s6_early` and used again by R3 (`ar_r3`)**. T3 reuses the stored decisions; this is stated, not a new test of the models. NHTSA pulses: the pooled records of `nhtsa.py`.

Measured: (1) time from trigger to the provisional decision (the early-exit decision time) and to the full decision (1,800 ms), on triggered crash events that alarm in both stages; (2) the retraction share (provisional alarms that the full window does not confirm, divided by provisional alarms) at the 1% and 5% false-alarm targets; (3) on NHTSA pulses, the agreement between the severity class computed from the window truncated at each early-exit length (50, 100, 200, 400, 800 ms after the trigger) and the class from the full window (the severity code of `severity.py`, unchanged); weighted by the distribution of the early-exit decision times of crash events when available. Bootstrap over events (2,000 resamples, seed 42), 95% intervals.

- **H-T3a.** The median provisional decision is at least 0.8 s earlier than the full decision (median of 1,800 ms minus the early decision time is at least 800 ms; the lower 95% limit is at least 800 ms) at the 1% target.
- **H-T3b.** The retraction share is under 20% at the 1% target (the upper 95% limit is below 0.20).
- **H-T3c.** The end-to-end earlier arrival (median paired arrival difference of at least 0.8 s) holds in at least two of the three link models: the custom simulator (`ar.r3`, existing), ns-3, and the trace-driven model (H-T1c clause (a)). **ns-3 counts as not holding unless it is run:** the single-paper P1 has not run in this session and the ns-3 application has no two-stage alert, so ns-3 is NOT_RUN unless a two-stage application is built in time.

## 4. T4: post-crash survivability budget (ANALYTICAL, supporting)

From datasheet currents of the ESP32, the SX1278 and the GPS module: record each source; any value from a datasheet that was not opened is marked ASSUMPTION. Compute how many alert attempts per policy a stated backup capacitor or cell can supply and which policies can still meet the Critical deadline on backup energy. No hypothesis unless every input is verified.

## 5. Multiple testing and decision rule

One Holm family of seven tests: H-T1a-L, H-T1a-M, H-T1a-H, H-T1b, H-T1c, H-T3a, H-T3b (at most 10). H-T2sec, H-T2 and H-T3c have no p-value (FORMAL checks and a count rule). A test with a p-value is called supported if its criterion holds at the point level and the Holm-adjusted p is below 0.05.

A protocol claim reaches the main text only if it holds in FORMAL or TRACE_DRIVEN evidence, or in at least two of the three link models. The decision table (T6) lists every hypothesis with result, label, interval, nearest prior work (`NOVELTY_MATRIX_2021PLUS.md`), allowed wording and placement.

## 6. Seeds, code and files

Seed 42 for every draw; no repeated-seed runs are needed because the traces are fixed. Code: `r3_t1.py`, `r3_t2_*.py`, `r3_t3.py`, `r3_t4.py` and the Tamarin files in `formal/`. Results under `r3.` in `results/results.json` and `results/tables/r3_*`.
