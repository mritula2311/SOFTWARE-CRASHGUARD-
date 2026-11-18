# Limitations (plain list)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | Plain list of what the software work cannot show and the assumptions a reader must know. |
| Evidence labels used | ANALYTICAL, NOT_RUN |
| Abbreviations | ASI = acceleration severity index; EN = European standard; ESP32 = a Wi-Fi microcontroller family (Espressif); NHTSA = National Highway Traffic Safety Administration; THIV = theoretical head impact velocity |
<!-- header:end -->

Every item is something this software work cannot show, or an assumption a reader must know. Numbers behind each item are in `results/results.json` and the report; none are repeated here.

## Placeholders and settings
1. **Trigger level and sensor range are placeholders.** `TRIGGER_G` (2.0 g) and `MPU_RANGE_G` (16 g) in `src/crashguard/config.py` are not confirmed from firmware v2. The window lengths (`PRE_S`, `POST_S`) are placeholders too. Every system-level result is a function of them; the trigger sweep shows how much.
2. **The packet layout is a proposal.** Little-endian byte order, the counter persisted in flash, and a 97-byte alert are assumptions to be matched with the firmware (`docs/05_data_code/FIRMWARE_SYNC.md`).

## Data
3. **VZCrash events were pre-selected on the device.** The dataset authors say every event was triggered by threshold heuristics before release. The trigger in this work is a second stage on already-selected events; trigger rates and system-level numbers do not describe continuous driving, where false alarms would be far more frequent.
4. **No vehicle or trip ID.** The paper states vehicle-level splits; the release has no vehicle ID, so this cannot be checked. Identical recordings were found across splits and removed from the primary test set. The validation split may also repeat training events and was not corrected.
5. **Duplicates.** Exact and near-identical recordings (a 32-bin summary and an L-infinity distance) were found; other forms of repetition, such as the same vehicle at different times, cannot be detected without an ID.
6. **No severity, direction or rollover labels in VZCrash.** Severity measures on VZCrash are descriptive. The rollover flag is a false-alarm check, not an accuracy result.
7. **A small crash-test set.** The NHTSA tests are cars in frontal barrier and side impactor tests, a few dozen per speed class; the held-out parts have a few dozen tests, so intervals are wide. The reference delta-V is a defined integral (the largest running integral in 300 ms), not a measured vehicle velocity change.

## Severity
8. **Full-scale severity thresholds.** The class limits (24, 40 and 56 km/h) and the class names are our choice, informed by cited literature, not a published four-class scale. The class mix moves when each limit moves by 20% (Table in the report).
9. **The MPU-6050 range is +-16 g.** It clips full-speed crash pulses and underestimates delta-V. The severity study needs at least +-64 g sampled at 200 Hz for delta-V within 10% on 80% of tests; the saturation-aware estimator repairs a +-16 g sensor only partly.
10. **The sensor model is generic and ours.** A zero-phase low-pass at the front-end bandwidth, saturation, a digital low-pass at 0.4 of the sample rate and sampling. It is not the response of any one part; noise is not modelled (quantisation is, for the named parts). The datasheet values were read from PDFs opened on 2026-11-11; two of the four lack a noise figure in what was read.
11. **Unverified constants** (`docs/05_data_code/SEVERITY.md`): the 13 Hz four-pole ASI pre-filter; the THIV flail-space distances (0.6 m used; one read source gives 0.8 m); the class names and cut points. The ASI level C limit was read in a secondary source, not in EN 1317-2 itself. THIV is reported but does not enter the class.
12. **The rollover flag is not used for the class.** Both the integrated-angle flag and the gravity-corrected flag fire on more than 0.5% of normal driving.
13. **The release rule is tuned on a small set.** The fraction of the pulse peak was chosen on the NHTSA tuning tests; on VZCrash many pulses still run to the 250 ms cap because dashcam signals rarely stay quiet.

## Detector and proposed methods
14. **No improvement from N15.** The trigger-aware methods did not raise system recall beyond the interval; the learned trigger collapsed to a level rule.
15. **N14 helps a +-16 g sensor only partly** and has no effect where pulses do not saturate. It depends on the pulse family and saturation level chosen on a small tuning set.
16. **N16 is supporting evidence from a simulation.** It gains little over the severity table in most held-out cells; the spreading-factor effect rests on an assumed loss factor.

## Simulation
17. **Assumptions of the replay and the scheduler:** Poisson arrivals, independent or Gilbert-Elliott losses with stated parameters, assumed stage times (window fill, compute time, cancel windows), one node and one base, no collisions, the base receives all spreading factors, the real VZCrash severity mix is almost all Low, so a stress mix is used where classes must differ. These are not hardware measurements; hardware test H3 would replace them.
18. **Compute time on the ESP32 is not measured.** Sizes are host estimates (nodes x bytes, object code size on the host, static array counts). `benchmark_rf.ino` is built but not run.

## Security
19. **Replay flood.** A sustained flood can still use up the base station's duty-cycle budget; the per-event re-ACK limit reduces the cost but does not remove it.
20. **Key handling.** One shared key on both nodes, no key rotation, no per-node keys; a recorded alert is accepted again if the base loses its counter store; the 32-bit counter cannot wrap without a key change. Alerts are authenticated but not encrypted, so position is readable over the air.
21. **A blind forgery** needs about 2^64 attempts (ANALYTICAL); this says nothing about key theft or side channels.

## Hardware and regulation
22. **The 433 MHz band (India).** The conditions are read from G.S.R. 347(E) of 2022 (rule 3 row 1: 10 mW e.r.p., duty cycle at most 10%, no bandwidth limit; the observation interval is not stated; rule 5: type approval is required). The evaluation used a stricter 1% hourly allowance. A deployed node would need type approval under rule 5. See `docs/03_results/FINALIZE_INDIA_RULES.md`.
23. **The scale model is not a car.** Its impact forces are not real-vehicle forces; scale-model severity would be impact strength, not injury. Severity against impact strength and runs at 200 m are not in the minimum hardware plan.

## Environment
24. **Compiled C checks can be blocked** by Windows Application Control. Then the result is NOT_RUN with the reason, and a pure-Python float32 mirror of the C code is the remaining check.
25. **The lock file was built from the working environment** (`requirements.lock`), for Python 3.12 on Windows 11 AMD64; other platforms may differ in the last digit.

## C checks and the N14 estimator (round 3, S7)
The C code of the N14 saturation-aware estimator (`cg_severity_sat`) equals the Python reference on the 224 real and mixed windows of the pipeline and on 47 of 48 synthetic clipped pulses. On the 48th (a half-sine pulse of 20 g and 40 ms with 2 saturated samples out of 5 pulse samples) the pulse-fit grid search has two cells with the same cost (equal to 3e-14 relative): the filled delta-V is 18.8 km/h in Python and 27.9 km/h in single-precision C, because the tie is broken differently. The fit is under-determined when a pulse has very few samples, and both answers fit the data equally well; the firmware was not changed in this round. The synthetic check therefore FAILS by its pass rule (it is kept, not removed) and is listed in `docs/04_audits/ALGORITHMS_COMPLIANCE.md` (W3).

<!-- jp_limits:start -->

## Journal push (generated; details in docs/03_results/JOURNAL_RESULTS.md)

26. **Held-out NHTSA modes** are dominated by pole tests, and the N13 and N14 findings were not confirmed on them.
27. **Two of the 176 NHTSA records are one channel counted twice.** The tagged results were not re-run.
28. **Sensor selection uses data sheet output rates and a software model.** The read rate on an ESP32 and any mounting or synchronisation effect are NOT_RUN or not modelled.
29. **VZCrash has duplicates across the supplied splits and no vehicle identifier.** Window-level duplicates affect about a fifth of triggered test windows and about 30% of crash test events; the exact-copy test events are under 1% of all test events.
30. **X6 is the only supported Block 4 hypothesis** and its gain is partly due to the anchoring and the boosting model; it holds on two of four splits and is not better in the median than the tail-aware model.
<!-- jp_limits:end -->
