# Bounded model check of the alert protocol (written 2026-11-11 before the runs; results are appended by `python -m crashguard.protocol_check`)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Bounded model check of the alert protocol (explicit-state search, within stated bounds). |
| Evidence labels used | ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; TLC = the TLA+ model checker |
<!-- header:end -->

**Status.** A bounded exhaustive search of a MODEL of the protocol (send, retry, signed ACK, CANCEL, two-stage flash, counter and replay window, re-ACK, reboots, an attacker). Origin ANALYTICAL (bounded model check). It checks the model within the stated bounds. It is NOT a proof of the firmware or of the reference code (`verifier.py`, `sct_protocol.py`). TLC (TLA+) was NOT run: the tool jar could not be fetched in this environment, so the check is an explicit-state level-by-level search written in Python (`src/crashguard/protocol_model.py`); no result is claimed for TLC.

## 1. Participants and assumptions
Car, base station, attacker. Perfect cryptography: only the car can produce a message whose tag is valid; the attacker can replay any captured message to the base or to the car, and can inject messages with an invalid tag (forged alerts, forged CANCEL, spoofed ACKs). The channel can lose a message, deliver in any order, and (through the attacker) duplicate a message. Timers are non-deterministic: the car may send or retry at any time within its limits, but only after its previous copy of the same message has left the channel (delivered or lost), which is what a timeout means. The shared key is secret (a holder of the key can forge anything; not modelled).

## 2. State
- **Car:** counter (1 to `cmax`), phase (idle, active, done = valid ACK received, cancelled), alert sends so far (at most `max_tries`), flash sends (at most `max_flash`), event serial (a ghost number used only to state the properties), the persisted counter, whether the flash and the alert were acknowledged.
- **Base:** last accepted flash counter, last accepted alert counter, the last `recent` accepted messages with their re-ACK counts (budget `reack_max` per message), the set of cancelled counters, and a persisted copy.
- **Network:** messages in flight to the base and to the car (at most `max_inflight` each), every message ever sent by an honest party (what the attacker can replay).
- **Ghost:** the log of accepted messages with the serial of the car event they came from.

## 3. Actions
Car: start an event (counter + 1), send flash, send alert (retry), receive an ACK (accepted only if the tag is valid and the counter matches; stops retries when it is the ACK of the alert), driver cancel (sends a CANCEL), reboot with or without counter persistence (a persisted counter is written before the initial send). Base: receive a message and apply the rules of `sct_protocol.SctBase` (valid tag; flash and alert counters strictly increasing separately; exact repeats of a remembered message are re-ACKed within the budget; CANCEL only for a known counter), reboot with or without persistence. Channel: lose a message. Attacker: replay, inject an invalid-tag message, spoof an ACK, at most `max_att` actions.

## 4. Properties (written before running)
- **S1** A replayed or forged alert is never accepted as a new alert: every accepted message has a valid tag and comes from a car event that has not been accepted before.
- **S2** A spoofed ACK never makes the car stop retrying: the car reaches the done phase only if the base has accepted an alert of the car's current event.
- **S3** A retransmission of an accepted alert that the base still remembers is acknowledged, not rejected, and the re-ACK budget is never exceeded.
- **S4** Accepted counters (separately for flash and alert) are strictly increasing over the whole run.
- **L1** (liveness, bounded) With a restricted environment (no attacker, no CANCEL, no reboot, at most `max_loss` lost messages) every maximal execution ends with the car holding a valid ACK of its alert.
- **L1b** A legitimate opening message of a new car event is never refused as a replay (checked in the reboot runs).
- **L2** After a base reboot without counter persistence, the properties that fail are stated with a counterexample; the same for a car reboot without counter persistence.
- **C1** CANCEL is accepted only with a valid signature. **C2** No send happens after a valid ACK (a valid ACK stops retries).

## 5. Variants and bounds
Variants: the design (idempotent re-ACK, both sides persist counters); strict anti-replay without the re-ACK (the earlier finding: a lost ACK is never repaired); base reboot without persistence; car reboot without persistence; the fixes (counter persisted before the initial send; base persists on accept). Copies of a message in flight are counted (each copy can be lost or delivered on its own) and a full channel blocks the sender instead of dropping silently. Bound sets, chosen so that each search is complete in minutes in Python (the combined bounds (counters up to 4, 3 retries, 6 attacker actions, reboots and several events together) exceed the 4 million state limit of this implementation, so the bounds are split; ATT has the asked bounds for the attacker, 3 retries and counters up to 4):
- **ATT** (attacker): counters up to 4, one event, 3 alert sends, 1 flash send, 6 attacker actions, 1 lost message, at most 3 messages in flight per direction, no reboots.
- **REBB** (base reboot): counters up to 4, one event, 3 alert sends, 1 flash send, 4 attacker actions, 1 lost message, 3 in flight, one base reboot.
- **REBC** (car reboot): counters up to 4, two events, 3 alert sends, 4 attacker actions, 1 lost message, 3 in flight, one car reboot; flash and CANCEL switched off in this run to keep the search complete. (A initial version of this bound set, both reboots together with two events, flash and 3 attacker actions, was truncated at 4 million states and gave no result; it was replaced by REBB and REBC. This is logged in `docs/07_log/DECISIONS.md`.)
- **LIVE** (liveness): counters up to 4, two events, 3 alert sends, 2 flash sends, 2 lost messages, 4 in flight, no attacker, no CANCEL, no reboot.
A property that holds is stated as "holds within these bounds"; it says nothing about larger bounds.

## 6. Cross-check with the simulated attack suite
The abstract base rule (`protocol_model.base_rule`) is run on the sequences of a mapped subset of the attack cases of `docs/01_protocol/ATTACK_CASES.md` and its decisions are compared with the observed outcomes of the reference verifier in `results/tables/attacks.csv`. Disagreements are listed in the results section below, not hidden.

<!-- results:start -->

## 7. Results (generated by `python -m crashguard.protocol_check`; ANALYTICAL, bounded model check, not a proof of the implementation)

| Bounds | Variant | States | Depth | S1 | S2 | S3 | S4 | L1 | C1 | C2 | L1b |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ATT | design | 2,733,655 | 29 | holds | holds | holds | holds | not checked here | holds | holds | holds |
| ATT | strict_anti_replay | 759,600 | 25 | holds | holds | holds | holds | not checked here | holds | holds | holds |
| REBB | design | 1,448,162 | 26 | holds | holds | holds | holds | not checked here | holds | holds | holds |
| REBB | base_no_persistence | 3,799,806 | 28 | **FAILS** (6 steps) | holds | holds | **FAILS** (6 steps) | not checked here | holds | holds | holds |
| REBC | design | 359,071 | 25 | holds | holds | holds | holds | not checked here | holds | holds | **FAILS** (7 steps) |
| REBC | car_no_persistence | 188,541 | 22 | holds | **FAILS** (6 steps) | holds | holds | not checked here | holds | holds | holds |
| LIVE | design | 1,373 | 16 | holds | holds | holds | holds | holds | holds | holds | holds |
| LIVE | strict_anti_replay | 701 | 13 | holds | holds | holds | holds | **FAILS** (11 steps) | holds | holds | holds |

Property names: S1 replay or forgery accepted as new; S2 spoofed ACK stops retries; S3 repeat not acknowledged or budget exceeded; S4 accepted counters not increasing; L1 no ACK in a terminal state; C1 CANCEL accepted without a valid signature; C2 send after a valid ACK. 'holds' = no counterexample within the bounds.

### Counterexamples (shortest traces, plain steps)

**REBB / base_no_persistence / S1_replay_or_forgery_accepted_as_new** (shortest counterexample, 6 steps):
1. car starts event
2. car sends flash
3. base receives ('F', 1, 1, True) -> accept
4. base reboots
5. attacker replays ('F', 1, 1, True) to the base
6. base receives ('F', 1, 1, True) -> accept
**REBB / base_no_persistence / S4_accepted_counters_not_increasing** (shortest counterexample, 6 steps):
1. car starts event
2. car sends flash
3. base receives ('F', 1, 1, True) -> accept
4. base reboots
5. attacker replays ('F', 1, 1, True) to the base
6. base receives ('F', 1, 1, True) -> accept
**REBC / design / L1b_legit_new_event_rejected_as_replay** (shortest counterexample, 7 steps):
1. car starts event
2. car sends alert
3. car reboots
4. car starts event
5. car sends alert
6. base receives ('A', 2, 2, True) -> accept
7. base receives ('A', 1, 1, True) -> reject_counter
**REBC / car_no_persistence / S2_spoofed_ack_stops_retries** (shortest counterexample, 6 steps):
1. car starts event
2. car sends alert
3. car reboots
4. car starts event
5. base receives ('A', 1, 1, True) -> accept
6. car receives ('K', 'A', 1, 1, True)
**LIVE / strict_anti_replay / L1_no_ack_in_terminal_state** (shortest counterexample, 11 steps):
1. car starts event
2. car sends flash
3. car sends alert
4. base receives ('A', 1, 1, True) -> accept
5. car sends alert
6. ACK lost
7. base receives ('A', 1, 1, True) -> reject_counter
8. car sends alert
9. base receives ('A', 1, 1, True) -> reject_counter
10. base receives ('F', 1, 1, True) -> accept
11. car receives ('K', 'F', 1, 1, True)

### Cross-check with the attack suite (13 of 14 mapped cases agree)

| Case id | Case | Model | Reference (observed) | Agree |
|---|---|---|---|---|
| 02 | Valid alert | accept | accept | yes |
| 04 | Forged tag | reject_tag | reject_tag | yes |
| 11 | Replay (same packet again): not processed again, same ACK re-sent | reack | reack | yes |
| 13 | Strict verifier (before the fix): ACK lost, car retries the same packet | reject_counter | reject_counter | yes |
| 14 | ACK lost, car retries same packet: re-ACKed | reack | reack | yes |
| 16 | Old counter, different content: rejected | reject_counter | reject_counter | yes |
| 17 | Same counter, different content (event changed): rejected | reack | reject_counter | **NO** |
| 18 | Replay of an alert older than the re-ACK window: rejected | reject_counter | reject_counter | yes |
| 19 | Retry of the same event with a fresh counter | accept | accept | yes |
| 30 | Base reboot, counter persisted: replay not processed again | reack | reack | yes |
| 32 | Base reboot, counter lost: replay | accept | accept | yes |
| 25 | Spoofed ACK (attacker key) | reject | reject | yes |
| 27 | Old ACK replayed for a later alert | reject | reject | yes |
| 28 | Genuine ACK for the waiting alert | accept | accept | yes |

Disagreements: case 17 (Same counter, different content (event changed): rejected): the model decides reack, the reference reject_counter. The model has no event id: it keys the re-ACK memory by counter only, while the reference verifier keys it by (node, event, counter). This is an abstraction gap of the model, not a result about the verifier.
<!-- results:end -->

<!-- ext:start -->

## 8. Extension T12: the flash message and CANCEL after a delayed ACK (ANALYTICAL; generated by `python -m crashguard.protocol_check_ext`)

Bounds EXT: counters up to 4, one event, 3 alert sends, 1 flash send, one CANCEL send, 3 attacker actions, 1 lost message, 3 messages in flight, no reboots; delivery in any order, ACKs may arrive after the CANCEL. This checks the model, not the implementation.

| Variant | States | Depth | S1 | S2 | S3 | S4 | C1 | C2 | C3 | C4 | F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| design | 351,754 | 23 | holds | holds | holds | holds | holds | holds | **FAILS** (5 steps) | holds | holds |
| keep_pending_cancel | 351,754 | 23 | holds | holds | holds | holds | holds | holds | holds | holds | holds |

Property names: C3 a delivered CANCEL is lost when it arrives before its alert; C4 a late valid ACK restarts sending after CANCEL; F1 an ACK of the flash ends the alert retries. 'holds' = no counterexample within the bounds.

### Counterexamples

**design / C3_cancel_lost_by_reordering** (shortest counterexample, 5 steps):
1. car starts event
2. car sends alert
3. driver cancels, car sends CANCEL
4. base receives ('X', 1, 1, True) -> reject_unknown
5. base receives ('A', 1, 1, True) -> accept

The design refuses a CANCEL for a counter it has not seen; if the CANCEL overtakes its alert (reordering), the alert is accepted afterwards and the event stays active although the driver cancelled (attack-suite case X06 shows the same behaviour in the reference code). The fix (remember such a CANCEL) removes it within the bounds. Not changed in the reference code or the firmware in this round.
<!-- ext:end -->
