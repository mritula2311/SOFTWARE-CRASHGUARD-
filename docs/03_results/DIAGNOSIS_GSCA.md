# Diagnosis: GS-CA burst failures

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Share of GS-CA burst failures from collisions, link loss and duty-cycle blocking (generated). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; GS-CA = GPS-slotted critical alerts; OS-DR = overhear-and-suppress retries with deadlines |
<!-- header:end -->

## 3. GS-CA in the 16 held-out burst cells: collisions, link loss or duty-cycle blocking

Re-run of the 16 held-out burst cells (30 hours each) with per-alert counters on; the re-run reproduces the stored `reach10_critical` of every run (mismatches: 0). Critical alerts only. An alert is a failure when it does not reach the base within 10 s.

**Failed Critical alerts by primary cause** (the transmission outcome that dominates the alert; 'not sent by 10 s' = still waiting for its slot, hold, retry gap or duty-cycle room):

| policy | alerts | reached in 10 s | reached late | collided | gateway deaf (sending an ACK) | link loss | not sent by 10 s (duty wait) | not sent by 10 s (other) |
|---|---|---|---|---|---|---|---|---|
| P4+lbt | 15607 | 0.282 | 0.255 | 0.320 | 0.040 | 0.096 | 0.006 | 0.000 |
| gsca | 15607 | 0.214 | 0.248 | 0.423 | 0.002 | 0.109 | 0.001 | 0.003 |
| osdr | 15607 | 0.224 | 0.052 | 0.508 | 0.101 | 0.113 | 0.001 | 0.001 |
| P1 | 15607 | 0.122 | 0.082 | 0.672 | 0.004 | 0.115 | 0.000 | 0.005 |

**Outcome of every transmission of a Critical alert:**

| policy | transmissions | decoded | collided | gateway deaf | link loss |
|---|---|---|---|---|---|
| P4+lbt | 88445 | 0.139 | 0.478 | 0.219 | 0.164 |
| gsca | 236984 | 0.054 | 0.665 | 0.106 | 0.175 |
| osdr | 98549 | 0.085 | 0.443 | 0.131 | 0.341 |
| P1 | 131835 | 0.031 | 0.719 | 0.094 | 0.156 |

For GS-CA, **0.54** of the failed Critical alerts failed mainly through a collision or a deaf gateway. Collisions are the main cause, so a redesign of the slotted access can still help (D3 is kept).


Transmissions per Critical alert: GS-CA 15.2, P4+lbt 5.7, OS-DR 6.3, P1 8.4. GS-CA is built on the severity-table retry rule (immediate retries, up to 12), so it puts about 2.7 times as many frames on the channel as P4+lbt; its collided share of transmissions is 0.66 against 0.48. **Mechanism (stated from these counts; the slot-count explanation, K = 4 slots for 30 vehicles, is inferred and was not isolated):** slotting did not reduce the number of competing frames, and the design-grid choice of 4 slots leaves several vehicles per slot.

