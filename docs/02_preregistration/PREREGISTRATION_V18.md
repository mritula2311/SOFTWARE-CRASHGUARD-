# Preregistration V18: round 7 (duty-budget reserve and unlinkable pseudonymous ids)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Preregistration V18 (round 7): duty-budget reserve and pseudonymous ids; hypotheses, thresholds, seeds and the Holm family, committed before any run. |
| Evidence labels used | MEASURED_SOFTWARE, TRACE_DRIVEN, SIMULATED, FORMAL, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; CPU = central processing unit; CRC = cyclic redundancy check; RAM = random-access memory; SF = spreading factor (LoRa) |
<!-- header:end -->

Committed before any run of round 7 (after the literature gate `docs/01_literature/R7_PRIOR_ART.md`, whose stop rules were not triggered). Branch `round7` from the head of `final2` (the tag `submit-v3.1` named in the brief does not exist; `submit-v3` differs from the head by two documents). Key prefix `r7.`. Nothing here changes a stored result, a frozen file or an earlier verdict; the old policy stays the default and the reserved policy is behind a flag in new modules. One Holm family of five hypotheses (H-R7-A1, H-R7-A2, H-R7-B1, H-R7-B2, H-R7-B3); H-R7-A3 is descriptive. The paper reports the total over all versions (V1 to V17 are in the ledger; V18 adds six hypotheses, one of them descriptive).

## 0. What was read before this file

1. **The shipped retry policy** (`xsim/ns3/xsim_alert.cc`, policies r3t and r6m; `src/crashguard/r3_t1.py`; `docs/05_architecture/FRAME_LAYOUT.md` section 6). One FIFO queue per event: flash (14 bytes, at most 4 tries, each followed by the receive windows, 0.32 s in ns-3), then the confirm (97 bytes, or the 13-byte micro-confirm in r6m when the flash was acknowledged and the entry is pending; at most 4 tries) or three cancels (14 bytes, unconfirmed, 0.3 s apart). Nothing is withdrawn when the full decision is ready; no frame type has priority; there is no back-off between tries beyond the receive windows. A transmission waits (`WaitUntil`) until the trailing-hour airtime plus its own airtime is within the allowance, with no deadline on the wait. Heartbeats are unconfirmed, so ACK suppression does not affect them. The firmware in `firmware_rd/` and `firmware_r6/` has no two-stage queue; the policy exists in the simulators and the trace replay only.
2. **The duty models of the stored results.** Hourly allowance (1%, 36 s per trailing hour) in every stored simulation; no per-transmission off-time (`docs/03_results/DELTA_DUTY_LOCKOUT.md`). The lockout analysis for an off-time of A (1/d - 1) after each frame, and the link-aware gating rule (load gate: SF7 only; lockout gate: condition A_f <= d (T_F - s_f)), are the baseline of H-R7-A3.
3. **A reserve already exists in a rejected policy.** `xsim_alert.cc` policy r3a (V15, not supported) keeps a reserve of 4 full-alert airtimes for the confirm against provisional repeats (`g_reserve`). It was not analysed against an attacker, has no formal check and is not the default. It is cited as prior design in the supplement.
4. **Frame layout** (`FRAME_LAYOUT.md`): the identifier is the 32-bit node id in the alert and the ACK, the 16-bit short id in the flash and the cancel, and none in the 8-byte micro frame (a one-byte pending index names the entry). Position (latitude and longitude, 4 bytes each) is in clear only in the 97-byte alert; the micro frame carries a 1-byte offset; the flash carries none.

## 1. Decisions that fix an ambiguity of the brief (logged in `docs/07_log/DECISIONS.md`)

| ID | Ambiguity | Decision |
|---|---|---|
| D1 | The brief says retries of the "full alert" may not spend the reserve, and a confirm draws from the reserve first, but the confirm is the full alert. | Two classes. **Class H** (reserve-eligible): confirm, micro-confirm, micro-cancel, cancel, and a full alert that has no flash (it is the only alert of the event); any copy of these. **Class L**: every flash try and every other frame. Class L may never reduce the remaining allowance below the reserve R. |
| D2 | What a reserve means under a per-transmission off-time (no accumulated budget). | A **time reserve**: a class-L frame may start only if the off-time it causes ends no later than the time the follow-up is due (T_F + 8 ms); a class-L try that is not yet started is withdrawn when the follow-up is ready. The first flash is subject to the same rule (it is skipped, and the event becomes single-stage, if it would lock the sub-band past T_F). |
| D3 | Size of the reserve. | R = k A_97 + A_M with k = 4 (the retry cap of the confirm) and A_M the airtime of the 13-byte micro frame of the stored simulations (conservative against the 8-byte design). Sensitivity: k = 2 (descriptive). |
| D4 | "Seeds fixed in V18" for a model with no random number inside an event. | Randomness is in the event row (from the stored event table), the target time and the prior event times; 6 seed sets (42 and 0 to 4) of 200 runs each per cell. |
| D5 | The trace replay is at SF7 only (the measured LoED loss sequences are SF7). | H-R7-A2 is evaluated at SF7. SF8 and SF9 benign cost is NOT_RUN (no trace at these SFs, and the ns-3 policy is not edited because it is frozen); the ns-3 hook (A1.5) is cut by the preregistered cut order only if time runs short, and is otherwise NOT_RUN for the same reason: the existing ns-3 policy files stay untouched. |
| D6 | Which LoED devices. | Half 0, the development half, exactly as R6-1's trace part; the held-out half 1 of R3 is not touched. Devices with fewer than 20 per loss group are NOT_RUN for that group. |

## 2. A: duty-budget exhaustion and the reserved-budget policy

### 2.1 Models (all enforced in `src/crashguard/r7_engine.py`; the old path with no duty layer must reproduce `r3_t1.r3_event` and `r6_micro.micro_event` draw for draw)

- **Frames and airtime.** 14 bytes (flash, cancel), 97 bytes (confirm), 13 bytes (micro, ns-3 size), 26 bytes (ACK). Time on air from `crashguard.lora.airtime_ms` (125 kHz, coding rate 4/5, explicit header, CRC, 8 preamble symbols). Receive windows W = 0.32 s after each frame in the ns-3-like engine (A1), and the trace replay's own WIN3 = 0.1 + A_ACK + 0.1 s in the trace part (A2). Decision times: early at the stored t_E (+ 8 ms), full at T_F = 1.808 s. Deadline 10 s.
- **Duty models.** H1: trailing-hour allowance 36 s. H10: trailing-hour allowance 360 s. T10: off-time 9 A after every frame (10% per transmission, one sub-band, one channel). The hourly sliding window is exact (every start and airtime is kept).
- **Old policy** (default): as in section 0.1; a frame waits for the duty model (hourly: until the trailing-hour use plus its airtime is within the allowance; T10: until the off-time ends); the confirm waits behind the flash stage (FIFO).
- **Reserved policy** (flag): D1 to D3. Class H frames may use any remaining allowance; class L frames need remaining >= R after they are sent (hourly) or off-time end <= T_F + 8 ms (T10); not-yet-started flash tries are withdrawn when the follow-up is ready. All other behaviour is the old policy's.
- **Attacker.** Suppresses each ACK independently with probability q (q = 1: every ACK), so every unacknowledged frame is retried to its cap. It cannot forge a tag (C4). Frames that it injects and that fail the tag trigger only cell-level rate limiting at the base (the two-tier quarantine fix); they are not sent by the node and do not touch the node's budget, so the engine has no such frame. The attacker is assumed not to be bound by any duty limit; its cost is ANALYTICAL (section 2.2).
- **Pending time and D_max.** The follow-up becomes pending at T_F + 8 ms (or at the decision for a lone alert). D is the start of its first transmission minus that time. D_max is the analytic bound of section 2.2.

### 2.2 A1 (ANALYTICAL, then SIMULATED)

ANALYTICAL, from the airtime formula for SF7 to SF9: attacker transmit cost per suppressed ACK (the airtime of the ACK it jams, 26 bytes, as an upper bound; reactive jamming needs fewer symbols per Dossa et al., not used as a number); node airtime per fully suppressed event (flash path 4 A_14 + 4 A_97, cancel path 4 A_14 + 3 A_14, micro path); the number n* of consecutive fully suppressed events at which the trailing-hour allowance of the old policy is spent, n* = ceil(B / W_e) with B the allowance and W_e the node airtime per fully suppressed two-stage event; the time at which the next follow-up can be sent (hourly: when the oldest frames leave the window; T10: the off-time chain); the bound D_max of the reserved policy: hourly D_max = A_14 + W (a flash tried just before T_F cannot be withdrawn), T10 D_max = 0 after the guard (a class-L frame whose off-time does not end before T_F is not sent); the k-th copy of the follow-up is sent by D_max + (k - 1) (A_c + W) (hourly) or D_max + (k - 1) max(A_c + W, 9 A_c) (T10).

SIMULATED: the engine of section 2.1 (the existing trace replay logic extended with the duty layers; ns-3 is not edited).

### 2.3 A2 (FORMAL, then ANALYTICAL)

FORMAL: exhaustive enumeration of a bounded model (`src/crashguard/r7_formal.py`): a frame queue of at most 3 events (each flash, confirm or cancel, micro), a budget counter in integer units with refill, and attacker-chosen ACK outcomes. Invariant 1: no class-L frame is sent when it would leave less than R of the allowance. Invariant 2: whenever the follow-up of the event under test becomes pending **and the reserve is intact (remaining allowance >= R) at that time**, it is sent within D_max of becoming pending under every attacker ACK pattern. Bounds (written before the run): allowance 24 to 60 units in steps, flash 1 unit, confirm 4 units, micro 1 unit, k in {1, 2}, up to 3 earlier events, 2 tries per frame in the abstraction, window refill once at the end of each step block, hourly model; T10 modelled as a one-step off-time. Control: the old policy must violate Invariant 2 in the same space; if it does not, the report says so and explains. The condition "reserve intact" is a stated limit: after several earlier follow-ups have spent the reserve (class-H frames of earlier events), the guarantee does not apply, and the enumeration reports the smallest number of earlier events at which Invariant 2 is violated for the reserved policy (a counterexample trace is stored).

### 2.4 Hypotheses of A

**H-R7-A1 (confirmatory, SIMULATED).** Under full ACK suppression (q = 1) at SF7, SF8 and SF9 and under H1, H10 and T10, the reserved policy sends the follow-up within D_max in at least 99% of runs, at the **primary stress**: n_prior = n*_old(SF, d) prior fully suppressed two-stage events (rows with E = 1 and F = 1 from the stored event table, times uniform in the preceding hour with a minimum gap equal to the duration of a fully suppressed event plus 1 s; a cell whose n_prior events do not fit in the hour is reported INFEASIBLE and not counted as supported or failed; T10 cells have no prior events), against the old policy's rate in the same runs. Target event rows: uniform over the stored rows with E = 1 (confirm path F = 1 or cancel path F = 0). 1,200 runs per cell (6 seed sets of 200). Supported iff the lower 95% one-sided Clopper-Pearson bound of the reserved policy's rate is at least 0.99 in every feasible cell. Reported as written whatever the old policy's rate. p-value: the one-sided exact binomial p-value of rate <= 0.99 for the worst feasible cell (intersection-union).
Descriptive companions (not in the family): q = 0.5; n_prior in {0, ceil(n*/2), 2 n*}; k = 2; the boundary n_H* (the number of earlier follow-ups at which the reserved policy fails).

**H-R7-A2 (confirmatory, TRACE_DRIVEN), two parts.** With no attack, on the LoED half-0 trace groups (L, M, H) at SF7, for the R3 scheme (full confirm) and the R6-1 scheme (micro-confirm), under H1, H10 and T10, 300 start points per device, the paired comparison reserved minus old:
- **H-R7-A2a:** the delivery of crash events falls by at most 1 percentage point. Supported iff the one-sided 95% lower bound of (reserved - old) is at least -0.01 in every cell with at least 20 devices (cluster bootstrap over devices, 2,000 resamples, seed 42; p = (count + 1)/(resamples + 1) of the worst cell).
- **H-R7-A2b:** the median time to first alert (first arrival of the flash or the confirm among delivered crash events) rises by at most 10%. Supported iff the one-sided 95% upper bound of the ratio reserved/old of the median is at most 1.10 in every such cell (same bootstrap).
The old path with no duty layer is first checked against the stored `r6.r1.trace.*` delivery and airtime keys (regression); a mismatch stops the part. The comparison "against the old policy" uses the old policy under the same duty model (an old policy under T10 is new behaviour, not a stored result). SF8 and SF9: NOT_RUN (D5).

**H-R7-A3 (DESCRIPTIVE, ANALYTICAL).** Re-derive the link-aware gating rule with the reserve (load gate with the allowance reduced by R; lockout gate with the time reserve). Report for SF7 to SF12 whether the spreading factor at which the two-stage alert is enabled moves, and by how many steps, under H1, H10 and T10. No threshold.

If H-R7-A2 fails, the benign cost is reported as an operating-regime boundary with the cell where it fails.

## 3. B: unlinkable pseudonymous vehicle ids

### 3.1 Design (B1)

Pseudonym p = trunc_L(PRF(k_v, "P" || boot || ctr)), PRF = HMAC-SHA256, k_v the per-vehicle key of R4, boot the boot counter, ctr the alert counter (the pending index of the micro frame is unchanged). L = 2 bytes where the frame has the 16-bit short id (flash, cancel), L = 4 bytes where it has the 32-bit node id (alert, ACK). The base keeps, per vehicle, a window of the next m pseudonyms (m = 16) and a hash index from pseudonym to the vehicle list; a frame whose pseudonym matches one or more entries is verified with the existing tag under each candidate (the tag, not the pseudonym, decides). After a match the window moves to the matched counter. Desynchronisation: after a reboot the boot counter changes, and the base resyncs by testing the pseudonym window for boot' in {boot, boot + 1, ..., boot + 3} (the flash carries the low 8 bits of the boot counter; a frame that does not resolve is treated as unresolved, triggers only cell-level rate limiting, and a full alert that resolves re-synchronises the vehicle). Accountability: per-vehicle quarantine, the boot-counter rule and the seen-set apply to the resolved real id at the base. Position: unlinkable ids do not hide position; the position fields of the full alert are encrypted with an AEAD (AES-128-GCM-style 16-byte tag costs bytes; a constrained variant with an 8-byte tag), the flash carries at most a coarse cell; the byte and airtime costs are ANALYTICAL; responders get the position from the base, not from the air. Out of scope: radio fingerprinting, timing correlation, an attacker that holds a vehicle key.

### 3.2 Formal results (B2, FORMAL)

ProVerif diff-equivalence (`choice[]`): two alerts of the same vehicle against two alerts of two vehicles, with an active network attacker (it controls the channel, may replay and inject, knows the public data), for 2 and for an unbounded number of sessions (replication). Control: the fixed-id design must fail (the attacker sees the id). A ProVerif failure is inspected: a real attack is a finding; a spurious one is reported "not proven". Tamarin observational equivalence is attempted only if time remains (first item of the cut order). The C4 lemmas are rerun with the pseudonym: authenticity, freshness and anti-replay, the boot-counter fix, micro-confirm binding with the index, quarantine on resolved ids; every lemma must still hold; run times are recorded.

### 3.3 Hypotheses of B

**H-R7-B1 (confirmatory, MEASURED_SOFTWARE).** Pseudonym resolution (hash lookup and tag verification, window advance) adds at most 1 ms per frame at the base for 1,000 vehicles and m = 16, on the development machine (the CPU is recorded). Measured as the mean time per resolved frame over 200,000 frames, 5 repetitions, the worst repetition used (Python reference and a C build of the same routine); supported iff the worst mean is at most 1 ms. p-value: 1 if the worst mean exceeds 1 ms, else 1e-300 (a measured bound, not a sampling test).

**H-R7-B2 (ANALYTICAL, with enumeration).** The probability that a frame's pseudonym collides with a pseudonym in another vehicle's window, at L bytes, n = 1,000 vehicles and m = 16, is at most 10^-6 per frame. Definition: P = 1 - (1 - 2^-8L)^((n - 1) m). Checked by exact enumeration of a random sample of the pseudonym space (Monte Carlo with the stated seeds) at L = 2 and L = 4, and by the formula for L = 1 to 6. **Expected from the formula before the run: P = 0.2164 at L = 2 and 3.7e-6 at L = 4, so the hypothesis is expected not to hold at the frame-size-preserving lengths; it holds from L = 5 (1.5e-8).** The tag decides a collision, so a collision costs one extra tag check and not a misattribution (the misattribution probability is the tag forgery probability, 2^-64 per candidate for the 8-byte tag and 2^-40 for the micro tag); this is reported next to the result. B2 enters the family as an ANALYTICAL hypothesis with p = 1e-300 if P <= 1e-6 at the L of the frame with the smallest L (L = 2), and p = 1 otherwise.

**Descriptive (no threshold):** frame sizes before and after (unchanged by construction for the pseudonym; the AEAD position field adds its tag and nonce bytes); airtime change at SF7 to SF9; flash and RAM footprint of the node PRF as MEASURED_SOFTWARE build artifacts as in R6-4 (`scripts/r6_footprint.sh`; instruction counts and energy NOT_RUN: no emulator).

**H-R7-B3 (FORMAL).** In ProVerif, the pseudonym design satisfies diff-equivalence for the alert (two vehicles against one), and the fixed-id control does not. p = 1e-300 if proved and the control fails, otherwise 1.

## 4. The family and the verdict rules

Holm over five hypotheses: H-R7-A1, H-R7-A2 (both parts enter as one hypothesis, p = the larger of the two p-values), H-R7-B1, H-R7-B2, H-R7-B3. H-R7-A3 and the descriptive items are outside the family. Seed 42; seeds 0 to 4 for the repeated runs; intervals are 95%. A part that is not run is NOT_RUN with the reason and enters with p = 1. Every number in the paper comes from a macro; no "first", "novel", "state of the art" or "theorem"; "if and only if" only when derived both ways.

## 5. Outputs, guards and cut order

Keys `r7.*` only (`results/results.json`; no existing key changes; `scripts/verify_keys_unchanged.py` against `submit-v3` is run at the end). Code: `src/crashguard/r7_*.py`, `scripts/r7_*`, `tests/test_r7_*.py`, `formal/proverif/r7_*.pv`. Documents: `docs/03_results/ROUND7_*.md`, `docs/04_audits/ROUND7.md`, `docs/04_audits/ROUND7_REPORT.md`. Run-once guard for A2: `results/tables/r7_held_started.json` is written before the A2 run; a second run stops. No push, upload, e-mail, key request, use of `data/hardware` or background job.

Cut order, if time runs short: (1) the Tamarin equivalence attempt; (2) the ns-3 ACK-drop hook (already NOT_RUN by D5); (3) the B3 footprint measurement. Never cut: L0, this file, A2.2 with its control, A3, B2.1 in ProVerif with its control, B2.2, P.
