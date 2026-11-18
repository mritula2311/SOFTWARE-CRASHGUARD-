# Security cases (S4): one list

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | The one list of security cases: 58 repository cases and the nine simulated scenarios (generated). |
| Evidence labels used | SIMULATED_HW_FORMAT |
| Abbreviations | ACK = acknowledgement frame; ASI = acceleration severity index |
<!-- header:end -->

The repository's suite has 58 cases: 48 in `attacks.run_cases` (`attacks.cases_total`) and 10 in `attacks_extra.run_cases`. 58 behave as expected. Categories: attack, must fail 39, control or format check 15, documented gap 4. The figures 30 and 38 from earlier notes are not found in any current file or key. Origin of every row: SIMULATED_HW_FORMAT (the real code run in software; no radio).

| Suite | # | Case | Expected | Observed | Match | Category |
|---|---|---|---|---|---|---|
| base | 0 | packet length | 97 | 97 | yes | control or format check |
| base | 1 | ACK length | 26 | 26 | yes | control or format check |
| base | 2 | Valid alert | accept | accept | yes | control or format check |
| base | 3 | Valid alert gets a valid ACK | True | True | yes | control or format check |
| base | 4 | Forged tag | reject_tag | reject_tag | yes | attack, must fail |
| base | 5 | Alert signed with the wrong key | reject_tag | reject_tag | yes | attack, must fail |
| base | 6 | Tampered field (severity) | reject_tag | reject_tag | yes | attack, must fail |
| base | 7 | Tampered field (counter) | reject_tag | reject_tag | yes | attack, must fail |
| base | 8 | Tampered field (delta-V, bytes 38-39) | reject_tag | reject_tag | yes | attack, must fail |
| base | 9 | Tampered field (ASI, bytes 40-41) | reject_tag | reject_tag | yes | attack, must fail |
| base | 10 | Delta-V and ASI fields round-trip in the 97-byte alert | True | True | yes | control or format check |
| base | 11 | Replay (same packet again): not processed again, same ACK re-sent | reack | reack | yes | control or format check |
| base | 12 | Replay leaves the base state unchanged | True | True | yes | attack, must fail |
| base | 13 | Strict verifier (before the fix): ACK lost, car retries the same packet | reject_counter | reject_counter | yes | attack, must fail |
| base | 14 | ACK lost, car retries same packet: re-ACKed | reack | reack | yes | control or format check |
| base | 15 | The re-ACK is accepted by the car | True | True | yes | control or format check |
| base | 16 | Old counter, different content: rejected | reject_counter | reject_counter | yes | attack, must fail |
| base | 17 | Same counter, different content (event changed): rejected | reject_counter | reject_counter | yes | attack, must fail |
| base | 18 | Replay of an alert older than the re-ACK window: rejected | reject_counter | reject_counter | yes | attack, must fail |
| base | 19 | Retry of the same event with a fresh counter | accept | accept | yes | control or format check |
| base | 20 | Forged alert does not advance the counter | True | True | yes | attack, must fail |
| base | 21 | Wrong length (truncated) | reject_length | reject_length | yes | attack, must fail |
| base | 22 | Wrong message type (alert with type 2) | reject_type | reject_type | yes | attack, must fail |
| base | 23 | Wrong version | reject_version | reject_version | yes | attack, must fail |
| base | 24 | Valid ACK fed to the base as an alert (reflection) | reject_length | reject_length | yes | attack, must fail |
| base | 25 | Spoofed ACK (attacker key) | reject | reject | yes | attack, must fail |
| base | 26 | Spoofed ACK (random tag) | reject | reject | yes | attack, must fail |
| base | 27 | Old ACK replayed for a later alert | reject | reject | yes | attack, must fail |
| base | 28 | Genuine ACK for the waiting alert | accept | accept | yes | control or format check |
| base | 29 | Alert bytes presented as an ACK | reject | reject | yes | attack, must fail |
| base | 30 | Base reboot, counter persisted: replay not processed again | reack | reack | yes | control or format check |
| base | 31 | Base reboot, counter persisted: older replay rejected | reject_counter | reject_counter | yes | attack, must fail |
| base | 32 | Base reboot, counter lost: replay | accept | accept | yes | documented gap |
| base | 33 | Replay flood, no limit: the base keeps ACKing until its duty-cycle budget is gone | budget exhausted | budget exhausted | yes | documented gap |
| base | 34 | Replay flood, no limit: a genuine alert arriving during the flood gets no ACK | accept_no_ack | accept_no_ack | yes | documented gap |
| base | 35 | Replay flood, with limit: at most one re-ACK per retry interval | True | True | yes | attack, must fail |
| base | 36 | Replay flood, with limit: the base never runs out of budget | True | True | yes | attack, must fail |
| base | 37 | Replay flood, with limit: a genuine alert arriving during the flood is ACKed | accept | accept | yes | attack, must fail |
| base | 38 | Replay flood, with limit: re-ACK airtime is lower than without the limit | True | True | yes | attack, must fail |
| base | 39 | Limit on: a retry inside the retry interval is not re-ACKed | reack_limited | reack_limited | yes | attack, must fail |
| base | 40 | Limit on: a genuine retry one interval after the ACK is still re-ACKed | reack | reack | yes | control or format check |
| base | 41 | Every single-bit flip of a valid alert is rejected | True | True | yes | attack, must fail |
| base | 42 | Truncated or padded alerts (every other length) are rejected | True | True | yes | attack, must fail |
| base | 43 | All-zero packet of the alert length is rejected | reject_version | reject_version | yes | attack, must fail |
| base | 44 | All-ones packet of the alert length is rejected | reject_version | reject_version | yes | attack, must fail |
| base | 45 | Every single-bit flip of a valid ACK is rejected by the node | True | True | yes | attack, must fail |
| base | 46 | Counter exhausted (largest value seen): a node whose counter wraps to 0 is rejected | reject_counter | reject_counter | yes | attack, must fail |
| base | 47 | Alert for another node_id signed with the shared key is accepted | accept | accept | yes | documented gap |
| extension | 0 | Flash with the 16-bit counter wrapped to 0 after counter 65535 | accept_flash | accept_flash | yes | control or format check |
| extension | 1 | Replay of an old flash (true counter 5) after the counter passed 65,536 | reject_counter | reject_counter | yes | attack, must fail |
| extension | 2 | Random 8-byte tags on a valid alert body (200,000 tries, bounded budget) | 0 accepted | 0 accepted | yes | attack, must fail |
| extension | 3 | Valid ACK arrives late, after the car retried, while it still waits for that alert | accept | accept | yes | control or format check |
| extension | 4 | Valid ACK of alert 1 arrives after the car moved on to alert 2 | reject | reject | yes | attack, must fail |
| extension | 5 | The same CANCEL delivered twice | cancelled,cancelled | cancelled,cancelled | yes | control or format check |
| extension | 6 | CANCEL arrives before the alert it cancels | reject_unknown_event; event not cancelled | reject_unknown_event; event not cancelled | yes | attack, must fail |
| extension | 7 | Flash of a second node whose short id equals the initial node's (counter 10 against 50) | reject_counter | reject_counter | yes | attack, must fail |
| extension | 8 | A 14-byte flash given to the alert handler and a 97-byte alert given to the flash handler | reject_length,reject_length | reject_length,reject_length | yes | attack, must fail |
| extension | 9 | A valid ACK of the flash (event id 0xFFFFFFFF) presented to a node waiting for the alert of event 1 | reject | reject | yes | attack, must fail |

## Scenarios S01 to S09 of the simulated H4 file, re-run on the real verifier (10 attempts each)

| Scenario | Attempts | Attacks accepted | Decisions |
|---|---|---|---|
| S01 valid alert (control) | 10 | 0 | accept x10 |
| S02 forged tag (wrong key) | 10 | 0 | reject_tag x10 |
| S03 tampered field | 10 | 0 | reject_tag x10 |
| S04 replay of an old alert | 10 | 0 | reack x10 |
| S05 spoofed ACK to the car | 10 | 0 | car rejects ACK x10 |
| S06 base reboot, counter persisted | 10 | 0 | reject_counter x10 |
| S06m base reboot, counter NOT persisted (model of a defect) | 10 | 10 | accept x10 |
| S07 ACK lost, same packet again | 10 | 0 | reack x10 |
| S08 car counter restarted (availability cost) | 10 | 0 | reject_counter x10 |
| S09 replay flood, 20 repeats | 10 | 0 | 0 of 20 accepted x10 |

S06m is the model of a base that does not persist its counter: it accepts the old alert, as the simulated model said. It is not counted as an attack on the repository's verifier.

## Outcomes recorded in the supplied `security_H4.json` (the simulated model, 10 attempts per scenario)

| Case | Scenario | Base result |
|---|---|---|
| S01 | valid_alert_control | accepted x10 |
| S02 | forged_tag_wrong_key | rejected_bad_tag x10 |
| S03 | tampered_field_one_byte | rejected_bad_tag x10 |
| S04 | replayed_old_alert | rejected_replay x10 |
| S05 | spoofed_ack_to_car | n/a (car-side verify) x10 |
| S06 | base_rebooted_mid_retry | accepted x10 |
| S07 | ack_lost_then_retry | rejected_replay_reacked x10 |
| S08 | car_rebooted_counter_state | rejected_replay x10 |
| S09 | replay_flood_20_in_10s | 20 of 20 rejected x10 |
