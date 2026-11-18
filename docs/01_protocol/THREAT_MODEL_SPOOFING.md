# Threat model for X5 (N21): bounded signal added to the accelerometer reading

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Threat model for the bounded-signal study on stored windows (no attack code acts on a sensor). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | MEMS = micro-electromechanical system |
<!-- header:end -->

Written 2026-11-11, before the X5 run. This is a software study on stored dataset windows. **No attack code that acts on a physical sensor is written or used** (no signal generator, no resonance search, no hardware interface, no instructions for building one). The perturbation exists only as an array added to a stored window in memory.

## What the attacker can do
The attacker adds a signal d(t) to the accelerometer reading of the node, on one, two or all three axes, from the start to the end of the 2.8 s window.
- **Amplitude budget epsilon** in {0.1, 0.25, 0.5, 1, 2} g: the largest absolute value of d on any axis at any sample.
- **Bandwidth limit:** d is a sinusoid or a narrow band of at most three sinusoids, with frequencies between 2 and 45 Hz (the node samples at 100 Hz, so nothing above 50 Hz exists in the data), arbitrary phases, and an arbitrary direction vector per sinusoid. A broadband signal is not considered (a plain random-noise attack is included only as the baseline "random" search).
- **Knowledge:** (1) black box: the attacker can query the deployed forest's decision on a modified window (up to 500 queries per window) but does not know its structure; (2) surrogate: the attacker trains a logistic regression or a small neural network on public data (the training windows) and transfers the result to the forest.
- **Timing:** the attacker is present for the whole window; trigger timing is not attacked separately (a quiet vehicle crosses the 2 g trigger as soon as about 1 g is added along the gravity axis, which is analytical and trivial: the trigger is not a defence).

## Goals
- **(a) False crash:** a non-crash window (one that already passes the trigger) is classified as a crash.
- **(b) Hidden crash:** a real crash window is not alarmed.

## What is taken from published work, and what is ours
Opened (2026-11-11): Tu, Lin, Lee and Hei, "Injected and Delivered: Fabricating Implicit Control over Actuation Systems by Spoofing Inertial Sensors", USENIX Security 2018 (opening pages read; arXiv 1806.07558). It states that MEMS gyroscopes are susceptible to resonant acoustic interference, that out-of-band signals injected at resonant frequencies can deliver chosen digital values to the processor (output control, not only biasing), that low-frequency signals in the sensing channel can be shaped by adjusting amplitude and phase, and that 17 of 25 tested devices could be controlled implicitly. It cites Son et al. (2015, drone gyroscope) and Trippel et al. (2017, accelerometer integrity under acoustic attacks); those two were seen only as citations inside this paper and as search snippets, not opened.
- **Taken from published work:** the premise that an attacker can make a MEMS accelerometer or gyroscope report attacker-chosen low-frequency content (output control), and that amplitude and phase are the controllable parameters.
- **Ours:** the budget grid, the restriction to one to three sinusoids between 2 and 45 Hz, the target (a crash detector on a vehicle node), the surrogate and black-box search procedures, the defences and their evaluation on the VZCrash windows. Whether a real speaker could deliver such a signal at such amplitudes to a car-mounted sensor is NOT studied and is not claimed.

## Defences evaluated (parameters chosen on validation windows only)
D1 median filter (3 and 5 samples); D2 plausibility check on delta-V against peak acceleration and on cross-axis share, limits from the training crashes; D3 adversarial training with the same budgets; D4 ensemble with a minimum physics-based delta-V. See `docs/02_preregistration/EXPERIMENTS_EXTRA.md`.
