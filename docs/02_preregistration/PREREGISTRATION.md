# Preregistration: uncertainty-aware severity-classified transmission (UA-SCT)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Hypotheses H-a to H-c for UA-SCT, written before the runs. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; ASI = acceleration severity index; CV = cross-validation; DoT = Department of Telecommunications (India); LoRa = long-range radio modulation; NHTSA = National Highway Traffic Safety Administration; SCT = severity-classified transmission; SF = spreading factor (LoRa); UA-SCT = uncertainty-aware SCT; WPC = Wireless Planning and Coordination wing (India) |
<!-- header:end -->

Written 2026-11-11 and committed BEFORE any UA-SCT, SCT or class-interval run of this study. The primary metrics, hypotheses, baselines, seeds and analysis below are not changed after the runs. Any scenario or variant added later is labelled EXPLORATORY in results.json (`exploratory` in the key or note) and in the report. Software only: no hardware log is read, H1 to H8 are untouched. Every number is labelled MEASURED_SOFTWARE (NHTSA tests and the VZCrash-based pools), SIMULATED, ANALYTICAL or NOT_RUN; a step that cannot run is NOT_RUN with its reason.

## 0. What was already seen before this document (disclosure)
- The N16 and X6 results: the scheduler did not beat the severity table in steady state (critical delivery +0.006 [-0.000, +0.012]); in a burst of 30 critical alerts at SF7 with 100 cars it did (0.87 against 0.25).
- S5 (held-out burst sweep, 12 settings) and S9 (grouped CV+ intervals of the delta-V estimate at +-16, +-32 and +-64 g: coverage about nominal, intervals wide at +-16 g, the "class below plus flag" rule increased under-estimation). S9 was planned in `docs/02_preregistration/EXPERIMENTS_EXTRA.md` before it was run. The conformal class intervals of this study (section 3) are a different construction (ordinal classes, one-sided upper bound) and have NOT been run.
- The distribution of NHTSA reference classes (counts only, no estimator error): 48 tests below 30 km/h reference delta-V, 16 at 30 to 45, 19 at 45 to 60, 93 at 60 or more.

## 1. Question
The severity estimate has uncertainty (sensor range, clipping, estimator error). If the transmission class is taken from the UPPER end of a conformal interval over the ordered severity classes, fewer Severe and Critical events travel through the slow normal path, at the price of more escalations of non-severe events to the fast path.

## 2. Data and the point estimate (B1)
- 176 NHTSA crash tests (116 frontal, 60 side), the existing sensor model at +-16, +-32 and +-64 g. Point estimate of resultant delta-V: **fill + ridge (the N14 primary, named after earlier results were seen)** at 100 Hz, which is the rate the estimator constants (pulse-fit grid, release rule) were built for. At 200 Hz the plain estimator is run for all three ranges (descriptive); fill + ridge at 200 Hz is run only if the estimator code accepts that rate unchanged, otherwise NOT_RUN with the reason.
- Class: maximum of the delta-V class (24, 40, 56 km/h limits) and the ASI class (1.0, 1.4, 1.9) as in `severity.classify`; the ASI is that of the filled window (a point value). True class: the same rule on the reference delta-V and reference ASI.
- Groups: make and model (132 groups; primary split). Tests with identical recordings (2 identical-signal pairs found by hash) are merged into one group before any split so a duplicate cannot sit on both sides. Splits: the repeated grouped 5-fold cross-validation of split R (5 repeats, seed 42 + repeat). Inside each outer training set the groups are split at random into tuning (60%) and calibration (40%); the point estimator (family, level, release fraction, ridge strength) is fitted on the tuning groups only; the calibration groups are disjoint from tuning and test groups.

## 3. Conformal class intervals (B2)
Ordinal classes 0 to 3. Prediction c_hat = class of the point estimate. Scores on the calibration tests: two-sided s = |c_true - c_hat|; one-sided s_up = max(0, c_true - c_hat). Split-conformal quantile q = the ceil((n + 1)(1 - alpha))-th smallest score (the interval is the whole range when that index exceeds n). Two-sided interval [c_hat - q, c_hat + q]; upper end U = min(3, c_hat + q_up). Two versions: **pooled** (one q) and **class-conditional** (one q per predicted class, Mondrian; where a predicted class has fewer than 10 calibration tests the pooled q is used and this is counted). alpha = 0.10 (primary) and 0.05 (secondary, pre-registered). Reported per sensor range: coverage of the two-sided interval and the one-sided validity P(c_true <= U) with grouped (make and model) bootstrap 95% intervals (1,000 resamples), mean interval width in classes, share of tests whose upper end is above the point class, and the number of calibration tests per class. "Holds" = nominal coverage inside the 95% interval of the empirical coverage.

## 4. Policies (B3), all in one simulator with the same payloads, ACK, retry limits and duty-cycle rule
- **P0** fixed 3-retry baseline (4 tries, one queue, no severity).
- **P1** severity table: point class selects the maximum tries (2, 4, 8, 12) and the service order; cancel window by class (10, 8, 6, 5 s). **The strong baseline.**
- **P2** SCT with the point class: fast path for Severe and Critical, two-stage flash (14 bytes), authenticated CANCEL, reserved duty share (docs/01_protocol/PROTOCOL_SCT.md).
- **P3** UA-SCT: as P2 but the class is the upper end U of the one-sided class-conditional conformal interval (alpha = 0.10).
- **P4** UA-SCT with a cap: P3 with the fast-path airtime limited to a fraction phi of the duty budget (phi tuned on the tuning scenarios from 0.1, 0.25, 0.5; the rule: the smallest phi that keeps critical reach within 10 s within 2 points of P3 on the tuning scenarios).
SCT parameters (hold of Severe alerts h_s in 0, 1, 2, 3 s; reserved share 0.2, 0.35, 0.5; spreading-factor raise on or off) are tuned for P2 on the tuning scenarios only (objective: critical-and-severe reach within 10 s minus a penalty of 2 per point by which normal-path delivery falls more than 5 points below the severity table) and the same parameters are used for P3 and P4. Held-out scenarios are scored once.

## 5. Simulator (B4)
LoRa 433 MHz, one 125 kHz channel, coding rate 4/5, SF7 and SF9 (SF12 only in the sensitivity), 97-byte alert, 14-byte flash and CANCEL, 26-byte ACK, 16-byte heartbeat, airtime from the Semtech formula. **Duty-cycle limit is a parameter, default 1%, applied as: the airtime of a transmitter in any trailing 3,600 s window never exceeds duty x 3,600 s (node and base station each); a transmission that would exceed it waits.** The 1% default and every other regulatory value (including the 10% sensitivity) are NOT verified for India (WPC/DoT not checked). 100 cars by default, background heartbeats every 600 s, Poisson crashes (0.1 per car per hour, a stress value), the burst scenario (a burst of simultaneous crashes within 10 s). Crash classes come from the NHTSA pairs of section 3 (assigned class by policy, true class from the reference), not from a stress mix. Decision times come from the N19 early-exit distribution (seed 42, 5% target). Capture rule 6 dB; independent loss 10% each way; fading as in X6. Every value is an ASSUMPTION of the simulator. Tuning scenarios (seeds 1000 to 1002, intermediate parameter values) and held-out scenarios (**40 seeds per cell**, seeds 3000 to 3039) are disjoint. Sensor range is a scenario factor (+-16, +-32, +-64 g).
Held-out cells: sensor range {16, 32, 64} x {steady, burst}; steady: cars {50, 100, 200}, SF {7, 9}; burst size {10, 30, 60} critical alerts, cars 100; heartbeat period {60, 600 s}; channel loss {10%, 30%}; duty {1% default, 10% sensitivity}. One factor changes at a time from the default (100 cars, SF7, 600 s, 10% loss, 1% duty, burst 30, range 16 g).

## 6. Metrics (B5), in this order; the leading metric is primary
1. **Mis-triage rate**: share of true Severe or Critical crash alerts that are delivered through the normal path (assigned class below Severe). Primary inference: grouped (make and model) bootstrap over the NHTSA pairs (1,000 resamples, MEASURED_SOFTWARE); the simulated value per cell is secondary.
2. **Critical delivery ratio within a deadline**: share of true Critical crash alerts with a signed ACK within 10 s and within 30 s of the crash instant.
3. Critical 95th-percentile latency (delivered alerts only; read with item 2).
4. Airtime per event, share of the duty budget used; **escalation fraction** = share of true Low or Moderate crash alerts assigned to the fast path (the cost of using the upper bound).
5. Share of runs in which the duty limit is exceeded (must be 0; checked by an independent scan of the logged transmissions, not by the enforcement rule).
All differences are paired by scenario seed with 95% bootstrap intervals over seeds (and, for pool-level quantities, over groups). An improvement counts only if the whole interval is on the favourable side of zero.

## 7. Hypotheses and what counts against them (B6)
- **H-a.** At +-16 g, P3 has a lower mis-triage rate than P1 (the grouped-bootstrap interval of P3 minus P1 is below zero). *Counts against H-a:* the interval contains zero or is above zero; or the interval is below zero but the reduction is under 2 points (reported as not meaningful).
- **H-b.** The cost of P3 is more escalations of non-severe events to the fast path, and P4 bounds the fast-path airtime. *Counts against H-b:* the escalation fraction of P3 minus P1 has an interval containing zero (no cost to bound), or P4's fast-path airtime share exceeds phi in any cell, or P4 lowers critical reach within 10 s below P3's by more than 5 points in the held-out cells.
- **H-c.** The gain shrinks at +-64 g because the intervals are narrower. *Counts against H-c:* the mean interval width at +-64 g is not below that at +-16 g (interval of the difference not below zero), or the mis-triage reduction of P3 relative to P1 at +-64 g is not smaller than at +-16 g (interval of the difference in reductions not below zero).
- **Secondary expectation (B7), also preregistered:** if the gain exists it appears in mis-triage and in bursts rather than in steady-state critical delivery. Reported either way. P2 against P1 and P3 against P1 are reported side by side; a null result is reported in the same detail as a success.

## 8. Analysis to be run, in order (and nothing else counts as the preregistered analysis)
1. `crashguard.ua_conformal`: class conformal intervals (section 3) per range, alpha 0.10 and 0.05, the NHTSA pair pools per policy.
2. `crashguard.s11_sct`: tuning of the SCT parameters and phi on the tuning scenarios, then the held-out cells for P0 to P4 (section 5), the metrics of section 6, the three hypotheses.
3. The ablations of SCT (no preemption, no flash, no severity-dependent hold, no reserved share, no spreading-factor raise) are EXPLORATORY.
4. Part A items (N20 with calibration de-duplicated by recording group; attack-suite count; W3; X6 burst sweep with capture none and 6 dB, burst 10, 30 and 60, heartbeat payload 16 and 26 bytes, cars 50, 100, 200, SF 7 and 9) are not part of the hypotheses; they are reported with the interval rules above.
5. Part C (bounded model check) is ANALYTICAL and reports a check of the model within its bounds, not a proof of the implementation.

---

# Addendum 1 (dated 2026-11-11, committed BEFORE the T1 to T4, T6 and T8 analyses are run)

This addendum fixes the analyses of the closing block. It changes no primary metric, no primary test set and no earlier result. Anything not written here (T5, T7, T9 to T13) is EXPLORATORY and labelled so in `results.json` and the report. What was already seen before this addendum: all UA-SCT results of the main study (mis-triage of P3 against P1 at +-16 g about 3 to 5 points lower, escalation about 50 points higher, little change in critical delivery over SCT, SCT gains in bursts, a spaced-retry table recovers most of the 30 s gain), the S9 class rule result, and the single-car result (SCT worse than the table at 60% loss).

## A1.1 T1: equal-escalation comparison
- **Escalation** = the share of true Low or Moderate crash alerts whose assigned class is Severe or Critical (fast path), as in section 6 of this document.
- **Lowered-threshold baselines.** P1e (severity table) and P2e (plain SCT) use the point estimates of P1 and P2 with every class boundary divided by a factor f in (0, 1]: class_f = classify(delta-V_hat / f, ASI_hat / f) (delta-V limits 24, 40, 56 km/h and ASI levels 1.0, 1.4, 1.9 all scaled). f is found per sensor range by bisection on the pooled held-out (test, repeat) rows of the class-interval run (class-conditional, alpha 0.10) so that P1e and P2e escalate the same share of true non-severe rows as P3, within 0.5 points; no simulated outcome is used to choose f.
- **Comparison.** P3 minus P2e and P3 minus P1e on the held-out cells and seeds of section 5 (40 paired seeds, all three ranges, steady and burst cells): mis-triage (pool level, grouped bootstrap, 1,000 resamples; simulated values as secondary), critical reach within 10 s and 30 s, critical 95th-percentile latency (delivered alerts only; read with delivery), airtime share. 95% bootstrap intervals over seeds (inside every cell), averaged over cells as in section 6.
- **Decision rule.** "P3 still wins at equal escalation" only if (i) the pool-level interval of mis-triage (P3 minus P2e) is entirely below zero at +-16 g AND (ii) in both steady and burst cells the lower end of the interval of critical reach within 10 s (P3 minus P2e) is above -0.02. Otherwise it is reported that P3 does not win at equal escalation, and which part failed. The same rule is applied against P1e and at +-32 g and +-64 g (reported, not decisive).

## A1.2 T2: trade-off curves
- **Families.** Point-class family for P0, P1 and P2 (their class assignment is the same): f on the grid 0.40, 0.45, ..., 1.60 (25 values, f = 1 is the current rule). Interval family for P3 and P4 (P4 differs from P3 only by an airtime cap, so its curve in mis-triage and escalation coincides with P3's): class-conditional one-sided upper end with alpha on the grid 0.50, 0.40, 0.30, 0.20, 0.15, 0.10, 0.07, 0.05, 0.03, 0.02, 0.01. All grid points are plotted and none is selected afterwards.
- **Axes and area.** x = escalation (share of true non-severe events sent to the fast path), y = mis-triage (share of true Severe or Critical events assigned a class below Severe). Both families are closed with the endpoints (0, 1) and (1, 0); area under the curve by the trapezoid rule over [0, 1], lower is better; 95% grouped (make and model) bootstrap interval for each area and for the area difference (interval family minus point family), 1,000 resamples, at +-16, +-32 and +-64 g.

## A1.3 T3: expected-cost view
- **Cost per crash event** = C_u x [true Severe or Critical and assigned below Severe] + C_o x [true Low or Moderate and assigned Severe or Critical]. Expected cost per crash event = s x mis-triage x C_u + (1 - s) x escalation x C_o with s = the share of true Severe or Critical events among the pooled rows (observed; NHTSA, not representative); s is also varied (0.1, 0.3, observed, 0.9).
- **Break-even ratio** r* = C_u / C_o at which P3 and P1 cost the same: r* = (1 - s) (escalation_P3 - escalation_P1) / (s (mis-triage_P1 - mis-triage_P3)), with a 95% grouped bootstrap interval; P3 is cheaper when C_u / C_o is above r*. P2 has the class assignment of P1, so its class-cost break-even is the same; a delivery term (EXPLORATORY): C_l x [true Critical alert without a signed ACK within 10 s] with C_l = C_u from the simulation separates P2 from P1. Shown for ratios 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000, not one ratio.

## A1.4 T4: two clarifications (no new hypothesis)
- (a) Define under-estimation (S9: share of tests whose reported class is below the reference class, under the lower-bound rule of S9) and mis-triage (H-a: share of true Severe or Critical events assigned below Severe, under the upper-end rule of the class intervals), give both per true class and per range, from the stored arrays; the two rules differ (lower bound against upper end), so both statements hold.
- (b) Single car, 60% loss both ways, SF7, 20 alerts per hour, 40 seeds: report the setup, compute the expected share of alerts acknowledged within 10 s analytically from the number of retry rounds that fit, and confirm the cause by running SCT with quick retries (spacing 0.3 s) as an EXPLORATORY variant.

## A1.5 T6: severity-threshold sensitivity
All three delta-V limits (24, 40, 56 km/h) shifted together by -2, -1, +1 and +2 km/h, and each limit shifted alone by the same amounts (16 settings, ASI levels unchanged); reference and assigned classes both use the shifted limits; the estimator, calibration (alpha 0.10 class-conditional), mis-triage comparison (P3 minus P1 at +-16 g) and the H-c quantities are recomputed. H-a "survives" a setting if the pool-level interval of the mis-triage difference is below zero and its point value is below -0.02; H-c "survives" if the interval of (reduction at +-16 g minus reduction at +-64 g) is above zero and the interval of the width difference is below zero. A delta-V severity scale from a source that was opened is used as an additional setting only if such a source is found; otherwise NOT_RUN.

## A1.6 T8: simulator assumption sweep
UA-SCT policies P0 to P4 at +-16 g, one factor at a time from the default (100 cars, SF7, heartbeat 600 s with 16 bytes, 10% loss, capture 6 dB, burst 30, duty 1%): capture none; burst 10 and 60; heartbeat payload 26 bytes; cars 50 and 200; SF9; loss 0%, 20%, 40%, 60%; duty 0.1%. Steady and burst cells where the factor applies; 40 paired seeds. "P3 beats P1 (or P2)" in a cell for a metric only if the whole paired 95% interval lies on the favourable side (critical reach within 10 s and within 30 s: above zero; mis-triage: below zero). Cells are counted; a result that holds in one corner only is reported as such.
