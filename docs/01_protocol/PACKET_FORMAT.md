# Alert packet (97 bytes) and ACK

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Alert packet (97 bytes), ACK (26 bytes), authentication tag and counter rules. |
| Evidence labels used | ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; CRC = cyclic redundancy check; GPS = Global Positioning System; LoRa = long-range radio modulation; RAM = random-access memory; SW-420 = a vibration switch module |
<!-- header:end -->

The byte layout below is a **proposal for software tests**. Align it with firmware v2 and correct this file if the firmware differs. The total must equal what the firmware sends.

| Off | Size | Field | Type |
|---|---|---|---|
| 0 | 1 | version | u8 |
| 1 | 1 | msg_type (1 = alert, 2 = ACK, 3 = heartbeat) | u8 |
| 2 | 4 | node_id | u32 |
| 6 | 4 | event_id | u32 |
| 10 | 4 | counter (monotonic, persisted in flash) | u32 |
| 14 | 4 | timestamp_ms | u32 |
| 18 | 1 | severity (0 low, 1 moderate, 2 severe, 3 critical) | u8 |
| 19 | 1 | impact_side (0 F, 1 R, 2 L, 3 Rt, 4 V) | u8 |
| 20 | 2 | angle_deg×10 | u16 |
| 22 | 4 | lat ×1e7 | i32 |
| 26 | 4 | lon ×1e7 | i32 |
| 30 | 2 | peak_g ×100 | u16 |
| 32 | 2 | ml_prob ×10000 | u16 |
| 34 | 1 | rule_sev | u8 |
| 35 | 1 | sw_mask (5 SW-420 bits) | u8 |
| 36 | 1 | sw_first | u8 |
| 37 | 1 | rollover flag | u8 |
| 38 | 2 | delta_v_kmh ×100 (resultant delta-V from the severity code, 0 to 655.35 km/h) | u16 |
| 40 | 2 | asi ×100 (acceleration severity index) | u16 |
| 42 | 47 | reserved / extended telemetry (zeros if unused) | bytes |
| 89 | 8 | tag = HMAC-SHA256(key, bytes 0..88)[:8] | bytes |

**ACK**: version, msg_type = 2, node_id, acked event_id, acked counter, base counter, and an 8-byte tag. It is signed with the same key.

Security properties:
- **Provided**: integrity, authenticity, and replay rejection (counter > last seen).
- **Not provided**: confidentiality. GPS position is readable over the air.

LoRa airtime for 97 B at SF7 / 125 kHz / CR 4/5 / 8-symbol preamble / explicit header / CRC is about 169 ms (ANALYTICAL).

## Software reference implementation (src/crashguard/packet.py, 2026-11-10)
- Byte order is little-endian (an assumption; check against firmware v2).
- ACK layout: offset 0 version (u8), 1 msg_type = 2 (u8), 2 node_id (u32), 6 acked event_id (u32), 10 acked counter (u32), 14 base counter (u32), 18 tag (8 bytes) = 26 bytes. The tag covers bytes 0 to 17.
- **Retry and replay rule (changed 2026-11-10, found by our own testing).** A strict rule "accept only if counter > last seen" blocks a legitimate retry: when the base received an alert but the ACK was lost, the car repeats the same packet and the base rejects it as a replay, so the car never gets its ACK. The reference verifier now keeps the last 16 accepted (node_id, event_id, counter) entries together with their ACK bytes. An alert that matches one of them exactly and has a valid tag gets the identical ACK again (decision `reack`) and is not processed a second time (no new alert, base counter unchanged). Any other counter that is not above the last seen one, including the same counter with different content, is rejected. The size of the list (16) is a design choice that firmware flash and RAM must confirm.
- Side effect: a flood of replayed packets makes the base spend airtime on ACKs and can use up its duty-cycle budget, so that a genuine alert gets no ACK. **Mitigation (added 2026-11-10):** the base sends at most one ACK per (node_id, event_id) per retry interval (the car's shortest spacing between two tries: alert airtime plus the ACK listening window, about 0.43 s at SF7), and every ACK it sends is paid from the base station's duty-cycle budget (token bucket, refilled at the duty-cycle rate). A repeat inside the interval gets no ACK (`reack_limited`); a repeat when the budget is empty gets none either (`reack_no_budget`). The limit reduces the cost of a flood but does not remove it: a long enough flood still uses the budget. The reference verifier keeps the mitigation optional (off by default) so that the unmitigated behaviour can be tested; firmware should switch it on. A retry interval shorter than the car's real retry spacing would block genuine retries, so firmware must use the real value.
- A retry may also use a fresh counter; this is accepted as a new alert and the base must de-duplicate by event_id.
- Known gap (software test, `make security`): if the base loses its stored counter, a recorded alert is accepted again.

## Severity fields (added 2026-11-10)
Bytes 38 to 41 now carry `delta_v_kmh x100` and `asi x100` (both u16, little-endian), taken from the reserved bytes, so the alert is still 97 bytes and the tag still covers bytes 0 to 88 (changing either value after signing is rejected; see the attack suite). The existing `severity` byte (offset 18, 0 low to 3 critical) holds the class from `docs/05_data_code/SEVERITY.md`, and `rollover` (offset 37) the rollover flag. These describe crash severity, not diagnosed injury. Values above 655.35 are clipped.

<!-- security:start -->
## Forgery, counter and flood analysis (generated from `results/results.json`)

- **Blind forgery (ANALYTICAL).** The tag has 64 bits: one random-tag attempt is accepted with probability 5.421e-20; one expected success needs 1.845e+19 attempts. At the airtime limit (back-to-back 97 B packets) that is 9.891e+10 years at SF7 and 2.303e+12 years at SF12; at the 10% duty cycle ten times longer. This assumes the key stays secret.
- **Counter.** 32 bits (4.295e+09 values), advancing once per new alert. At the fastest legal rate (SF7, 10% duty cycle: 2127 alerts per hour) it wraps after 230 years; at one alert a minute after 8166 years. After the largest value no new alert is accepted: the key must be rotated (there is no epoch field in this layout). The attack suite has a case for it.
- **Replay flood.** The idempotent re-ACK makes the base transmit for replayed packets. The limit (one ACK per event per retry interval, every ACK paid from the duty-cycle budget) lowers the cost but a long enough flood still uses up the budget (attack suite and the replay study).
- **Shared key.** One key on both nodes: any holder can sign an alert for any node id (an attack-suite case documents it). No key rotation, no per-node keys, no encryption (position is readable).
- **Property tests and fuzzing.** `tests/test_security_properties.py` (hypothesis): the counter never goes backwards for any input stream, a re-ACK is idempotent, any single-bit flip of an alert or an ACK is rejected, truncated or padded packets are rejected, and the parser never crashes on random or mutated bytes (every outcome is accept or reject).
<!-- security:end -->
