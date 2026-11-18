# Physics-based severity (src/crashguard/severity.py)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Physics-based severity (delta-V, acceleration severity index, class) and its sources. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED |
| Abbreviations | ASI = acceleration severity index; EDR = event data recorder; EN = European standard; ESV = Enhanced Safety of Vehicles (conference); IMU = inertial measurement unit; MPU = motion processing unit (an IMU part family); NASS = National Automotive Sampling System; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; SAE = Society of Automotive Engineers; THIV = theoretical head impact velocity |
<!-- header:end -->

Written 2026-11-10. The code computes crash severity from one triggered IMU window. **The classes indicate crash severity (how hard the vehicle's velocity changed), not diagnosed injury.**

Source status: **READ** = the passage was read in a document fetched for this work. **SNIPPET** = seen only in a web-search result snippet, not read in the full text. **OURS** = our design value, not from a standard. **UNVERIFIED** = could not be confirmed from a primary or standard text; treat as an assumption.

## Input
Window of about 2.8 s at 100 Hz (1.0 s before the trigger, 1.8 s after), accelerometer in g (x forward, y left, z up), gyro in deg/s. The accelerometer is clipped to the sensor range before use. Output keys carry their units in the name.

## Steps, formulas and sources
| Step | Formula or rule | Source and status |
|---|---|---|
| Gravity / orientation removal | `a_lin[i] = a[i] - mean(a[0 : trigger])` per axis | OURS (the usual pre-crash zeroing of EDR and IMU data). Leaks gravity if the vehicle rotates during the crash |
| Pulse detection | Starts at the trigger sample. Ends at the earliest sample from which horizontal `h = sqrt(ax^2 + ay^2)` stays below `release_g` (0.5 g) for `release_ms` (50 ms), or after `max_pulse_ms` (250 ms), or at the window end. Only the pulse is integrated | Release 0.5 g and 50 ms: OURS. 250 ms cap: NHTSA EDR work says 250 ms records 95% of crash pulses (SNIPPET, [NHTSA, Recording Automotive Crash Event Data](https://www.nhtsa.gov/DOT/NHTSA/NRD/Articles/EDR/PDF/Research/Recording_Automotive_Crash_Event_Data.pdf)) |
| Delta-V | `dv = integral of a_lin dt` over the pulse, trapezoidal: `dt * (sum(a) - (a_first + a_last) / 2)`. Longitudinal (x), lateral (y), resultant `sqrt(dvx^2 + dvy^2)`; m/s and km/h (x 3.6) | Definition of delta-V as the integral of acceleration; event data recorders must report longitudinal delta-V to +-10% (SNIPPET, [49 CFR 563.7](https://www.law.cornell.edu/cfr/text/49/563.7)). Trapezoidal rule: textbook |
| ASI | `ASI(t) = sqrt((ax/12 g)^2 + (ay/9 g)^2 + (az/10 g)^2)`, `ASI = max_t`, with 50 ms moving averages of the accelerations | 12 g, 9 g, 10 g and 50 ms: READ (Nasution et al. 2009 as quoted in [Baltic J. Road and Bridge Eng. 6(1), 2011](https://bjrbe-journals.rtu.lv/bjrbe/article/download/bjrbe.2011.01/139/352)). The EN 1317-2:1998 standard itself was not available. Moving average here is causal (last 50 ms), whole window: OURS |
| ASI pre-filter | 4-pole phase-less Butterworth, 13 Hz (implemented as a 2nd-order filter run forward and backward, zero initial state, no padding) | **UNVERIFIED**: SNIPPET only ([MATEC Web Conf. 338, 01025](https://www.matec-conferences.org/10.1051/matecconf/202133801025), full text not readable here). The forward-backward form is our implementation choice |
| ASI levels | A: ASI <= 1.0 (with THIV <= 33 km/h); B: ASI <= 1.4 (with PHD <= 20 g) | READ ([Shojaati, STRC 2003](https://strc.ch/2003/shojaati.pdf), table 1; the Baltic J. paper also gives 1.0 recommended and 1.4 acceptable) |
| ASI level C | ASI <= 1.9 | READ in a secondary source (2026-11-11): Nouzovsky et al., Acta Polytechnica CTU Proceedings 39 (2022), table 1 ('C: 1.4 < ASI <= 1.9') and the text 'must fulfil the ASI value lower than 1.9'. The EN 1317-2 standard itself was not opened |
| THIV | Head is a free particle; relative velocity `v_r = -integral a dt`, relative position `s = integral v_r dt` from the trigger; the head hits when `|s_x| >= 0.6 m` or `|s_y| >= 0.3 m`; `THIV = |v_r|` then, in km/h | Concept READ (Baltic J. 2011: head moves freely until it strikes the vehicle interior; THIV <= 33 km/h for level A, Shojaati 2003). **UNVERIFIED and in doubt**: the 0.6 m and 0.3 m flail-space distances. The Baltic J. paper (read 2026-11-11) gives a longitudinal head distance of 800 mm, a transversal distance of 300 mm and 600 mm from the centre of gravity to the head, so 0.6 m longitudinal is not confirmed and the standard's yaw-rotation term (NOT implemented). If the head never hits within the window, THIV is 0 and `thiv_hit` is false |
| Related occupant criteria | Occupant impact velocity <= 9 m/s preferred, <= 12 m/s maximum; ridedown acceleration <= 15 g preferred, <= 20 g maximum | READ ([FHWA crash test protocol reports, NCHRP 350 criteria](https://www.fhwa.dot.gov/guardrailsafety/et31crashtestprotocols.pdf)); shown for context, not used |
| Peak and mean pulse acceleration, duration, specific energy | Peak = max `h` over the pulse (g). Duration = pulse length (ms). Mean = resultant delta-V / duration (g). Specific energy = `0.5 * dv_res^2` (J/kg) | OURS (plain definitions; specific energy is kinetic energy per unit mass) |
| Rollover | Roll (about x) and pitch (about y) = integral of `(gyro - mean(gyro before trigger))` from the trigger; rollover if the largest absolute angle reaches 90 degrees | 90 degrees about the longitudinal or lateral axis is the NASS-CDS rollover definition (SNIPPET, [NAP report 10308](https://www.nationalacademies.org/read/10308/chapter/4) and NHTSA ESV paper). The MPU range clips fast rotation (2000 deg/s), so the angle is an underestimate |

## Severity classes (rules)
Class = the larger of the delta-V class and the ASI class. A rollover is always Critical. All limits are in `src/crashguard/config.py`.

| Class | Resultant delta-V | ASI (EN 1317-2 level) | Other |
|---|---|---|---|
| Low | below 24 km/h | <= 1.0 (A) | |
| Moderate | 24 to below 40 km/h | <= 1.4 (B) | |
| Severe | 40 to below 56 km/h | <= 1.9 (C) | |
| Critical | 56 km/h or more | above 1.9 | rollover, always |

Where the delta-V limits come from (all SNIPPET; the class names and the exact cut points are OURS and **UNVERIFIED** as a published scale):
- 24 km/h (15 mph): lowest severity band in NASS-CDS reporting (below 24 km/h, 24 to 48, above 48) and the delta-V an advanced automatic collision notification system uses as a condition ([SAE 2022-01-0835 abstract](https://saemobilus.sae.org/articles/injury-delta-v-front-near-side-far-side-rear-impacts-analysis-1994-2015-nass-cds-2022-01-1008), [FISITA 2016 paper](https://go.fisita.com/store/papers/FISITA2016/F2016-APSH-001)).
- 40 km/h: in NASS data for belted occupants in frontal crashes, about 69% of MAIS 3+ injuries happen at delta-V of 40 km/h or less, and in head-on crashes a delta-V of 40 km/h gave about a 50% risk of moderate to fatal injury for occupants aged 65 and over ([NHTSA, older occupant injury in low and moderate severity crashes](https://www.nhtsa.gov/document/older-occupant-injury-low-moderate-severity-crashes); Gabler and co-workers as summarised in the search result).
- 56 km/h (35 mph): the New Car Assessment Program full-frontal rigid-barrier test speed, so crashes at or above it are at or beyond the benchmark severity ([NHTSA test reports, e.g. v14316](https://nrd-static.nhtsa.dot.gov/reports/vehdb/v10000/v14300/v14316R001.pdf)).
- Delta-V as a predictor of serious injury: Kononen, Flannagan and Wang 2011, Accident Analysis and Prevention 43(1):112-122 ([SWOV record](https://swov.nl/en/publicatie/identification-and-validation-logistic-regression-model-predicting-serious-injuries)). Injury risk also depends on crash direction, belt use, age and vehicle type, which a single IMU cannot see, so the classes are not injury predictions.

The mapping of ASI levels A, B and C onto Low, Moderate and Severe is OURS: EN 1317-2 levels were written for vehicle-barrier tests, not for classifying road crashes.

## Known limits
- A dashcam is not at the vehicle's centre of gravity, so ASI and THIV are not the EN 1317 values. They are indicators computed with the same formulas.
- At 100 Hz, delta-V is biased low for short pulses, and clipping at +-16 g removes area from strong pulses; the size of both biases is measured in the report (synthetic pulses and NHTSA crash tests).
- VZCrash has no severity label, so no accuracy claim is made on it.
- The pulse starts at the trigger sample, so the part of the pulse before the trigger is missed (a small, systematic underestimate).

## Not verified
1. (Settled 2026-11-11 in a secondary source: ASI level C limit 1.9, see below.)
2. The 13 Hz four-pole phase-less Butterworth pre-filter.
3. THIV flail-space distances (0.6 m and 0.3 m in the code; a read source says 0.8 m and 0.3 m), and the yaw term. THIV is not used in the severity class, only reported.
4. The class names and cut points as a published severity scale.
5. The 0.5 g and 50 ms release rule and the causal moving average (OURS).
6. Several supporting numbers are from search snippets only (marked SNIPPET).

Validation: synthetic pulses (SIMULATED), NHTSA crash tests (MEASURED_SOFTWARE) and the VZCrash distributions are in `report/software_results.md`, with keys `severity_synth.*`, `nhtsa.*` and `severity_vzcrash.*` in `results/results.json`.

## Verification of constants, 2026-11-11
Attempt: open primary or standard texts. The EN 1317-1/2 standards are paywalled and were not opened. What was opened (downloaded and text-searched):
- **ASI level C <= 1.9: now READ in a secondary source.** Nouzovsky, Kohout, Vrtal and Novacek, "Dynamic tests of the culvert face within crashtests", Acta Polytechnica CTU Proceedings 39:41-48 (2022), CC BY 4.0, https://doi.org/10.14311/APP.2022.39.0041, table 1: A: ASI <= 1.0; B: 1.0 < ASI <= 1.4 and THIV <= 33 km/h; C: 1.4 < ASI <= 1.9. It cites EN 1317. Status: READ (secondary). The code comment is updated.
- **13 Hz four-pole phase-less Butterworth pre-filter: still UNVERIFIED.** The statement appears in search-result summaries of Polish and Romanian papers (acta.fih.upt.ro 2016 and a Gdansk University of Technology paper). The ACTA 2016 paper was downloaded (4 pages) and has no such text; the Gdansk paper could not be reached. Kept as UNVERIFIED with a `# UNVERIFIED` mark in `config.py`.
- **THIV flail-space distances 0.6 m and 0.3 m: not confirmed, and one source differs.** The Baltic J. Road and Bridge Eng. paper (downloaded and read) states, for THIV and PHD: longitudinal distance from head to vehicle 800 mm, transversal 300 mm, and 600 mm from the vehicle centre of gravity to the head. Our code uses 0.6 m longitudinal. THIV does not enter the severity class (class = delta-V and ASI, plus rollover), so the class is not affected; the reported THIV value is. A sensitivity check with 0.8 m is run in the report. Status: UNVERIFIED, contradicted by one read source.
- **Class names and delta-V cut points (24, 40, 56 km/h): OURS.** No published four-class scale with these names was found. They stay a design choice, documented with their supporting references above, and the threshold sensitivity (plus or minus 20%) is reported in the report.

<!-- phase2:start -->
## Phase 2 updates (generated from `results/results.json`)

- **Release rule.** The pulse ends when horizontal acceleration stays below max(0.5 g, 0.10 x pulse peak) for 50 ms (or after 250 ms). The fraction was chosen on the 118 NHTSA tuning tests (median absolute delta-V error 3.45% against 6.69% for the old rule) and scored once on the 58 held-out tests: 3.76% against 7.53%, paired difference -3.76 points with a 95% interval of -10.25 to -1.36. On VZCrash crash pulses 0.67 still run to the 250 ms cap (descriptive).
- **Rollover.** A drift-corrected flag (gravity direction carried through the crash by the gyro, corrected by the gravity vector at the quiet end of the window) still fires on 0.0177 of VZCrash normal driving (the integrated-angle flag: 0.0203), above the 0.5% limit set in advance, so the flag is reported but kept out of the class rule (`SEV_ROLLOVER_IN_CLASS` is off). VZCrash has no rollover labels, so this is a false-alarm check.
- **Range and rate.** At least +-64 g and 200 Hz give delta-V within 10% of the reference on 80% of 176 NHTSA tests (260 Hz front end); +-16 g at 100 Hz reaches 0.07. Details, bandwidth sweep and named parts are in the report.
- **Constants.** The ASI level C limit 1.9 was read in a secondary source (Acta Polytechnica CTU Proceedings 39, 2022). The 13 Hz filter and the THIV flail distances stay UNVERIFIED; THIV is not used in any claim.
- **N14.** The saturation-aware estimator (pulse family triangle, saturation level 0.7 of the range) is in `severity.h`; see `docs/02_preregistration/ALGORITHMS.md` and the report.
<!-- phase2:end -->
