# Synthetic assumptions (blocks C and G)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Numbered assumptions behind every synthetic pulse, surrogate window and simulated scenario. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; CRC = cyclic redundancy check; NHTSA = National Highway Traffic Safety Administration; SF = spreading factor (LoRa); UA-SCT = uncertainty-aware SCT; V2V = vehicle-to-vehicle |
<!-- header:end -->

Every synthetic pulse, surrogate window and simulated scenario in the finishing branch rests on the numbered lines below. Values are the values used. Source "NHTSA pool" = summary statistics of the 913 pooled NHTSA records (`data/processed/pp_pool.joblib`); "assumed" = our choice, no document opened. **All of it is a stress test or a simulation. None of it is an unbiased sample of real crashes or real radio links, and none of it substitutes for real data.** Captions of every figure and table that use it read: "synthetic stress test, assumptions in SYNTHETIC_ASSUMPTIONS.md".

## C. Synthetic crash pulses (`crashguard.fin_synth`, `crashguard.fin_c`)

| No. | Assumption | Value | Source |
|---|---|---|---|
| A-C1 | Pulse families and their mix | half-sine, triangle (peak at fraction a of the duration), multi-peak (2 or 3 half-sine bumps, amplitudes U(0.5, 1)); probability 1/3 each | assumed |
| A-C2 | Joint distribution of (log peak resultant, log duration at 10% of the peak, logit asymmetry, log delta-V) per mode | Gaussian copula (correlation of normal scores) with the empirical 101-point quantile marginals of the real pulses of the mode; modes frontal barrier, pole, side, other | NHTSA pool (all 913 records for block C; the training rows of a run for block F) |
| A-C3 | Pulse shape given the drawn values | blend of the family shape with a plateau of 0.105 of the peak plus a narrow spike (half-width parameter 0.03 of the pulse length) at the asymmetry position; the blend weight is chosen so that area / (peak x duration) equals the value implied by the drawn delta-V (km/h = 35.304 x g s), clipped to [0.12, 0.62] | assumed (real pulses have area ratios of 0.25 to 0.33, below the 0.5 to 0.64 of single smooth shapes) |
| A-C4 | Direction | unit vector of the real velocity change drawn from the records of the mode, plus a 5 degree Gaussian jitter | NHTSA pool |
| A-C5 | High-frequency noise | band-limited (1.5 kHz) Gaussian noise inside the pulse, relative level log-normal with the median and spread of the real pulses of the mode (median 0.19 to 0.40 of the peak); 2 mg noise elsewhere | NHTSA pool |
| A-C6 | Sampling and window | 10 kHz, 0.6 s, 0.1 s quiet before the pulse, z axis noise only | assumed |
| A-C7 | Calibration | the log peak and log duration means are shifted (three pilot rounds of 300 pulses, seeds 900000 and up, never used elsewhere) so that the measured geometric medians of the generated pulses equal the real ones; delta-V is not shifted (decided after an initial look at fidelity: shifting it distorted its narrow upper tail) | assumed procedure |
| A-C8 | Descriptors | 300 Hz low-pass of the horizontal resultant after removing the pre-trigger mean, from the trigger sample, 0.5 s; duration = width at 10% of the peak; asymmetry = time of the peak over the duration; shape = area / (peak x duration); delta-V = the N13 reference (300 ms) | repository definition |
| A-C9 | Stress extension (EXPLORATORY) | log-peak shift of +0.2, +0.4, +0.6 (delta-V follows) to represent more severe crashes than the real tests cover | assumed |
| A-C10 | Fidelity rule | two-sample Kolmogorov-Smirnov statistic at most 0.20 for each of five descriptors; in-sample (the generator is fitted to the same records) | preregistered |

Fidelity outcome (read from `results.json`, keys `f.c.fidelity.*`): frontal barrier and other pass; pole fails (shape descriptor), side fails (asymmetry and peak). Only frontal barrier and other are used in C3, F and G. The pole result of the real-data requirement table is therefore not tested against synthetic pulses.
The synthetic file: `results/synthetic/synthetic_pulses_5000_params.csv` (mode, family, seed, descriptors; each pulse is regenerated exactly by `crashguard.fin_synth.make_pulse` with seed 42 + k and the generator parameters `results/synthetic/generator_params_all913.json`) and the 2 kHz waveforms in the release archive.

<!-- G section is appended below by the protocol study -->

## G. Protocol layers study (`crashguard.world_sim`, `crashguard.fin_g`)

All lines are fixed in `docs/02_preregistration/PREREGISTRATION_V5.md` (committed before the runs). "Assumed" = no document opened; the receiver sensitivities are NOT taken from a Semtech document (it could not be opened). The India duty limit and the regulatory status of listen-before-talk at 433 MHz are UNVERIFIED.

| No. | Assumption | Value | Source |
|---|---|---|---|
| A-G1 | Crash arrivals and burst | Poisson 0.1 per car per hour; a burst of b Critical events within 10 s at 600 s (b = 20 on the DESIGN grid, 30 on the HELD-OUT grid) | assumed (stress parameter, as in the UA-SCT study) |
| A-G2 | Severity mix | pairs (true class, assigned class) of 1,500 synthetic pulses of the modes that passed C2 (frontal barrier, other) in the mode proportion of the real pool, +-16 g and +-32 g, 100 Hz; true class from the reference delta-V; assigned class from the plain estimate; upper class from plain x q (q = conformal quantile of reference / plain on the real development and validation records, 90% target); abstain = clipped share above the 70th percentile of the real development and validation rows; the mix is mostly Critical (true classes at +-16 g: 45 Low, 301 Moderate, 424 Severe, 730 Critical) | synthetic pulses (C block) and NHTSA pool |
| A-G3 | Vehicle density | n cars share one gateway cell (grid values) | assumed |
| A-G4 | Geometry and path loss | cars uniform in a disc of radius 3 km; one gateway at the centre (two at +-1.5 km in G5); PL(d) = 25 dB + 10 x 3.0 x log10(d / 1 m); 14 dBm transmit power; 10 dB vehicle and body loss; static log-normal shadowing sigma 6 dB per car and gateway; per-transmission fading 2 dB; reception needs a level above the sensitivity of the SF (SF7 -123, SF8 -126, SF9 -129, SF10 -132 dBm) | assumed |
| A-G5 | Capture | 6 dB at equal SF and channel; other SFs orthogonal with the loss factor 0.7 per SF step of the earlier study | assumed (earlier study) |
| A-G6 | Extra loss | independent loss p on uplink and downlink (grid values) | assumed |
| A-G7 | PHY | 125 kHz, coding rate 4/5 (4/8 in G2), 8-symbol preamble, explicit header, CRC on; SF 7 to 10 | repository airtime formula (formula as transcribed; Semtech document not opened) |
| A-G8 | Duty limit | 1% and 0.1% of any trailing hour per transmitter, gateway included | assumed; the Indian limit was read on 2026-11-16 (10% at most, observation interval not stated; `docs/03_results/FINALIZE_INDIA_RULES.md`) |
| A-G9 | ACK timing | ACK starts 0.1 s after the uplink ends (0.5 s and 1.0 s in G5); the car listens 0.1 s + ACK airtime + 0.1 s margin | assumed |
| A-G10 | Channels | 1 (3 in G5); the gateway is half-duplex on the channel it transmits on | assumed |
| A-G11 | Tag length | 8 bytes (4 and 16 in G2 and G5): the lengths of alert, flash, CANCEL and ACK change by the difference | assumed layout |
| A-G12 | Slotted fast path | 9-byte beacon every 30 s; frame 30 s; reserved window of 8 slots of max(0.5 s, ceil(alert airtime / 0.1 s) x 0.1 s + 0.1 s); fast-path transmissions at the start of a uniformly chosen slot of the next window; normal and heartbeat traffic avoid the window; synchronised if a beacon was heard in the last 90 s; beacon charged to the gateway duty; CANCEL messages are not slotted | assumed (beacon coordination assumed) |
| A-G13 | Listen-before-talk | each ongoing transmission detected with probability 0.7; busy: wait U(0.05, 0.25) s, at most 4 times, then transmit | assumed; 433 MHz regulatory status UNVERIFIED |
| A-G14 | V2V relay | 3 other cars each hear an alert with probability 0.5; if the sender has no ACK after its listen window, each hearing car repeats the alert once after U(1, 5) s; charged to the relayer's duty | assumed |
| A-G15 | Receivers | per-gateway reception; with two gateways the ACK goes through the best gateway | assumed |

Simplifications stated: collisions are evaluated at the best gateway of the transmitting car; the gateway's receive chain is half-duplex only on the channel of its ACK; a relay is triggered by the sender's missing ACK (neighbours are assumed to share that view). Grids: DESIGN n {75, 150} x loss {10%, 30%} x SF {7, 9} x duty {1%, 0.1%}, burst 20, seeds 6000 + h; HELD-OUT n {100, 200} x loss {20%, 40%} x SF {8, 10} x duty {1%, 0.1%}, burst 30, seeds 8000 + h; 30 seeds per cell.

<!-- physics:start -->
## Physics generator (block P, assumptions P-1 to P-14)

Source of every value: **fitted** = hyper-parameter found by moment matching to the DEVELOPMENT fold of the pooled NHTSA records (Nelder-Mead on the mismatch of the moments of log peak, log duration, log delta-V, asymmetry, shape ratio, log noise level and three correlations); **measured** = a statistic of the development rows (test speed, reference delta-V); **assumed** = a value chosen here, with no opened source. The Kmec et al. (2021) values are not used.

| Id | Item | Value or equation | Source |
|---|---|---|---|
| P-1 | Contact model | relative closing motion of the reduced mass mu = kappa m_v: z'' = -a_v g / kappa; the struck vehicle decelerates at a_v = F / m_v (in g); m_v cancels from the dynamics | physics |
| P-2 | Loading curve, PH-A | a(z) = a_p z / x1 for z < x1; a_p (1 + h (z - x1) / x_l) up to the crush limit x_l; plus a_p k_b (z - x_l) / x1 beyond it (bottoming out); k_b ~ U(6, 14), h ~ U(0.2, 2.0) | shape assumed; a_p, x1, x_l fitted |
| P-3 | Damper (Kelvin), PH-A | c = 2 zeta sqrt(k1 kappa), k1 = a_p g / x1, in loading only; zeta lognormal, spread 0.3 | mean fitted, spread assumed |
| P-4 | Unloading and restitution | linear unloading from the point of maximum crush to a permanent crush z_perm = z_max - 2 e^2 W_L / F_max (energy restitution); no force after separation | physics; e below |
| P-5 | Closing speed v0 | lognormal, mean and sd of the log test speed of the development rows of the mode (rows with speed up to 5 km/h treated as missing and replaced by the median) | measured |
| P-6 | Restitution e, barrier and pole | median of (reference delta-V / test speed) - 1, sd of that ratio, clipped to 0 to 0.6 | measured |
| P-7 | Restitution e, side and other | N(0.10, 0.05) | assumed |
| P-8 | Mass ratio kappa | barrier and pole: 1 (fixed obstacle); side and other: median ratio / (1 + e), log-sd of the ratio | measured and derived; moving-barrier reading assumed |
| P-9 | Vehicle mass | lognormal, median 1,600 kg, log-sd 0.22; used only for energy bookkeeping, not by the dynamics | assumed |
| P-10 | Compartment response | causal second-order Butterworth low-pass of the crush force, cut-off lognormal (median fitted, spread 0.3, bounded 10 to 500 Hz) | median fitted, rest assumed |
| P-11 | Structural vibration | (a) damped modal response to the force jerk at 45, 110, 260, 540, 1100 Hz, damping 0.04 to 0.06, weights 0.3 to 1.0; (b) six resonators from 350 to 1800 Hz, damping 0.05, each struck by 8 impulses at random instants of the pulse; mix 0.4 and 0.9; total rms = vib x peak, vib lognormal | frequencies, damping, weights, mix assumed; vib fitted |
| P-12 | Sensor mount | causal second-order Butterworth low-pass, cut-off U(1200, 2200) Hz (PH-B: U(900, 1600) Hz) | assumed |
| P-13 | Crush limits of the consistency check | frontal barrier 0.9 m, pole 0.9 m, side 0.35 m, other 0.9 m | assumed |
| P-14 | Sampling and noise | 10 kHz, 0.7 s, contact starts at 0.1 s, white sensor noise 0.002 g per axis, impact direction taken from development rows with 5 degrees of jitter | as `fin_synth`; assumed |
| P-15 | PH-B (alternative) | acceleration law a_p (1 - exp(-z / z0)), z0 = 0.25 (kappa v0^2 / 2) / (a_p g); viscous term with Maxwell relaxation exp(-t / tau_m), tau_m ~ U(5, 30) ms; three structural modes at 80, 400, 900 Hz | assumed shape; a_p fitted |

<!-- physics:end -->
