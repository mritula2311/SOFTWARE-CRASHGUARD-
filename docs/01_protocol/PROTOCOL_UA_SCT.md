# UA-SCT: uncertainty-aware Severity-Classified Transmission (protocol note, 2026-11-11)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Uncertainty-aware severity-classified transmission: the class interval and escalation rule. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; ASI = acceleration severity index; DoT = Department of Telecommunications (India); NHTSA = National Highway Traffic Safety Administration; SCT = severity-classified transmission; UA-SCT = uncertainty-aware SCT; WPC = Wireless Planning and Coordination wing (India) |
<!-- header:end -->

Software design only. Nothing here is implemented in firmware or measured on radios; every timing is an ASSUMPTION; the duty-cycle limit is a parameter and NOT verified for India (WPC/DoT not checked). Byte layouts of the flash, CANCEL, alert and ACK are those of `docs/01_protocol/PROTOCOL_SCT.md` and `docs/01_protocol/PACKET_FORMAT.md`; this note adds how the class is chosen and what the car does.

## 1. Idea
The severity estimate has uncertainty (sensor range, clipping, estimator error). A conformal interval over the ordered severity classes turns that uncertainty into a transmission class: the car reports the UPPER end of the interval, so a Severe or Critical event is less likely to travel through the slow normal path. The price is more escalations of non-severe events to the fast path.

## 2. Class selection (on the car)
1. Point class c_hat = class of the estimated delta-V (fill + ridge when the sensor clips) and ASI, by `severity.classify` (delta-V limits 24, 40, 56 km/h; ASI levels 1.0, 1.4, 1.9).
2. Offline, on a calibration set of tests whose make-and-model groups are disjoint from the tuning and test groups, the conformal quantile q_up[k] of the one-sided score max(0, c_true - c_hat) is computed for every predicted class k (class-conditional; the pooled quantile where a class has fewer than 10 calibration tests) for the target coverage (alpha = 0.10 primary). The four integers q_up[0..3] are stored in the firmware.
3. Transmission class U = min(3, c_hat + q_up[c_hat]). U is the class of the flash and of the alert; the point class and the interval ends (lower, upper) go into the reserved bytes of the alert (offsets 42 to 45: point class, lower class, upper class, coverage code), covered by the tag. No length changes (97 bytes).

## 3. Messages
FLASH, CANCEL (14 bytes), ALERT (97 bytes), ACK (26 bytes), heartbeat (16 bytes, unconfirmed): see `docs/01_protocol/PROTOCOL_SCT.md`. The flash and the alert of one event carry the same 32-bit counter. Authentication is the shared-key HMAC-SHA256 truncated to 8 bytes (a holder of the key can forge anything).

## 4. Car state machine
| State | Event | Action | Next state |
|---|---|---|---|
| IDLE | trigger and detector decision (early exit) | compute c_hat and U | HOLD |
| HOLD | hold time h(U) elapsed (Critical 0 s; Severe h_s; Moderate and Low the full cancel window) | none | SEND_FAST if U is Severe or Critical, else SEND_NORMAL |
| HOLD | driver cancels before the hold ends | nothing was sent | IDLE |
| SEND_FAST | enter | preempt the normal path; send FLASH (if no signed ACK for it yet), listen, send ALERT, listen | WAIT_FAST |
| WAIT_FAST | signed ACK of the alert | stop | DONE |
| WAIT_FAST | no ACK | wait 5 s (Critical) or 10 s (Severe); from the third round raise the spreading factor one step (parameter); at most 12 (Critical) or 8 (Severe) alert tries | SEND_FAST or GAVE_UP |
| WAIT_FAST | driver cancels after a send | send CANCEL three times, 2 s apart, stop retries | CANCELLED |
| SEND_NORMAL | enter | send ALERT; at most 3 tries with exponential back-off (4 s, doubling) and jitter | DONE or GAVE_UP |
| any | duty limit | a transmission that would exceed duty x 3,600 s in the trailing hour waits | same state |
| any | fast-path cap (P4 only) | when the fast-path airtime in the trailing hour would exceed the share phi of the allowance, the alert is demoted to the normal path | SEND_NORMAL |
Replay and ACK rules on the base station are those of `docs/01_protocol/PROTOCOL_MODEL.md`.

## 5. Parameters
| Parameter | Meaning | Value or how set |
|---|---|---|
| alpha | miscoverage of the class interval | 0.10 (primary), 0.05 (secondary) |
| q_up[0..3] | conformal quantiles per predicted class | computed offline from the calibration set (`crashguard.ua_conformal`), four integers in firmware |
| h_s | hold of Severe alerts | chosen on tuning scenarios from 0, 1, 2, 3 s (`results.json`: `s11.tuned.h_s`) |
| rho_f | share of the hourly airtime allowance only the fast path may use | chosen from 0.2, 0.35, 0.5 (`s11.tuned.rho_f`) |
| phi | P4 cap on the fast-path airtime share | smallest of 0.1, 0.25, 0.5 within 2 points of P3 on tuning scenarios (`s11.tuned.phi`) |
| spacing | retry spacing | 5 s Critical, 10 s Severe |
| max tries | alert sends | 12 Critical, 8 Severe, 3 normal path |
| duty | duty-cycle limit | parameter, 1% default, NOT verified for India |
| spreading factor | channel setting | 7 (default), 9; raise by one step after the second failed round (parameter) |

## 6. Policies compared (all in `crashguard.sct_sim`)
P0 fixed 3-retry; P1 severity table (point class); P2 SCT (point class); P3 UA-SCT (class U); P4 UA-SCT with the fast-path cap. The preregistered hypotheses and the analysis are in `docs/02_preregistration/PREREGISTRATION.md`; results are in `report/software_results.md` (round 3) and `results/results.json` (`ua.*`, `s11.*`).

## 7. Known weaknesses (from the runs)
- Taking the upper end sends many more non-severe events to the fast path.
- At the same escalation, the severity table with its thresholds lowered does as well as P3 on mis-triage (T1); the interval family has the larger trade-off area (T2); P3 costs less than P1 only if a missed severe event costs several times a false escalation (T3). The conformal interval therefore adds no measured benefit beyond choosing lower thresholds.
- Faster retries (0.3 s spacing) repair the single-car weakness at high loss but lower critical reach within 30 s when many cars share the channel (T4, T9).
- In the ablations the reserved duty share and the CANCEL message change nothing in critical reach in the cells tested; the flash and the severity hold carry the gain (T9, EXPLORATORY).
- The bounded model shows that a CANCEL that overtakes its alert is lost by the design; remembering a valid CANCEL for a counter not yet seen fixes the model (T12). The firmware does not yet do this.
- The fixed 5 s retry spacing is worse than immediate retries for a single car at high loss (EXPLORATORY result).
- NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes; the class distribution of real traffic is unknown.
- CANCEL is not acknowledged; the short node id and the 16-bit counter window are proposals.
