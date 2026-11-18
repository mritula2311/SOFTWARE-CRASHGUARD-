"""Report sections 4.5 to 4.7: severity (with the range and rate study), security, end-to-end replay."""
from __future__ import annotations

import pandas as pd

from crashguard import config as C
from crashguard.report import Doc, Res, table

RANGES = (16, 32, 64, 100, 200)
RATES = (100, 200, 400, 800, 1600)
CLASS_NAMES = ("Low", "Moderate", "Severe", "Critical")


def severity_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.5 Severity: delta-V, ASI and the sensor range and rate\n")
    a("This section asks what an IMU has to measure for the severity code to work. Delta-V is checked against crash tests, and the effect of the accelerometer range, sample rate and bandwidth is measured on the tests. "
      "VZCrash has no severity labels, so on VZCrash the severity measures are described, not scored. **The classes indicate crash severity (how hard the velocity changed), not injury.**\n")
    a("**Reference and error.** The reference delta-V of a test is the largest resultant of the running integral of the original-rate, unclipped, baseline-removed horizontal acceleration within `300 ms` of the trigger. "
      "The 'error' of a sensor setting is the estimate against this reference, not against a true vehicle velocity change, which the database does not give. "
      "The sensor model is generic and ours: a 4th-order zero-phase low-pass at the front-end bandwidth (260 Hz unless stated), saturation at the range, a digital low-pass at `0.4` of the sample rate, then sampling. It is not the model of any one part.\n")
    d.tab("synthetic", "Severity code on synthetic pulses with known answers (95% intervals on the shares)", "SIMULATED", "severity_synth.*", "The code recovers delta-V and ASI on clean pulses; clipping and low rates bias delta-V low")
    rows = []
    for fs in (100, 50):
        for clip, cn in (("none", "no clipping"), ("on", "clipped at the sensor range")):
            for dur, dn in (("long", "80 ms and longer"), ("short", "shorter (40 ms)")):
                p = f"severity_synth.fs{fs}.clip_{clip}.{dur}"
                rows.append([f"{fs} Hz", cn, dn, r.i(f"{p}.n"), r.f(f"{p}.dv_abs_err_median_pct", 1), r.f(f"{p}.dv_abs_err_p90_pct", 1), r.ci(f"{p}.dv_within_tol_share", 2), r.f(f"{p}.asi_abs_err_median_pct", 1),
                             r.ci(f"{p}.asi_within_tol_share", 2)])
    a(table(["Sample rate", "Clipping", "Pulse duration", "Windows", "Median delta-V error (%)", "90th percentile (%)", "Share within the delta-V tolerance", "Median ASI error (%)", "Share within the ASI tolerance"], rows))
    a(f"Half-sine, triangular and square pulses in front, side and oblique directions, with gravity, noise, a tilted frame and a random sampling phase. The delta-V truth is analytic (half-sine: 2 A T / pi). "
      f"Stated tolerances: {r.f('severity_synth.dv_tolerance_pct', 0)}% for delta-V (the allowance for event data recorders in 49 CFR 563.7) and {r.f('severity_synth.asi_tolerance_pct', 0)}% for ASI, "
      f"claimed for pulses of {r.f('severity_synth.tolerance_min_duration_ms', 0)} ms and longer at 100 Hz. This proves the code, not real-world accuracy.\n")
    d.tab("nhtsa_band", "NHTSA frontal rigid-barrier tests: the physical band v <= delta-V <= 2 v", "MEASURED_SOFTWARE", "nhtsa.band_*, nhtsa.restitution_*", "Delta-V from the original recordings is physically plausible; at 16 g it is not")
    rows = []
    for key, nm in (("orig", "original sample rate, after the 260 Hz front end, unclipped"), ("hz100", "resampled to 100 Hz, unclipped"), ("hz100_clip", "100 Hz and the sensor range (sensor model)")):
        rows.append([nm, f"{r.i(f'nhtsa.band_count.{key}')} of {r.i('nhtsa.n_frontal')}", r.ci(f"nhtsa.band_share.{key}", 2), r.i(f"nhtsa.below_v_count.{key}"), r.i(f"nhtsa.above_2v_count.{key}"),
                     f"{r.f(f'nhtsa.restitution_median.{key}')} ({r.f(f'nhtsa.restitution_p10.{key}')} to {r.f(f'nhtsa.restitution_p90.{key}')})", r.f(f"nhtsa.corr_dv_v.{key}", 2)])
    a(table(["Signal", "Inside the band", "Share with 95% interval", "Below v", "Above 2 v", "Restitution e = delta-V / v - 1: median (10th to 90th percentile)", "Correlation of delta-V with v"], rows))
    a(f"The median peak horizontal acceleration of these tests after the front-end filter is {r.f('nhtsa.peak_g_median', 1)} g, and {r.f('nhtsa.clipped_tests_share', 2)} of the frontal tests exceed the 16 g range.\n")
    d.tab("range_error", "Change in delta-V against the original recording, by sensor range at 100 Hz (95% intervals)", "MEASURED_SOFTWARE", "nhtsa.dv_err_vs_orig_*", "A negative change is an underestimate: the sensor range removes area from strong pulses")
    rows = [[nm, r.ci(f"nhtsa.dv_err_vs_orig_median_pct.{k}", 1), r.ci(f"nhtsa.dv_err_vs_orig_abs_p90_pct.{k}", 1), r.f(f"nhtsa.dv_err_vs_orig_max_abs_pct.{k}", 1), r.ci(f"nhtsa.asi_err_vs_orig_median_pct.{k}", 1)]
            for k, nm in (("hz100", "100 Hz, no clipping (sample rate only)"), ("hz100_r64", "100 Hz, range 64 g"), ("hz100_r32", "100 Hz, range 32 g"), ("hz100_r16", "100 Hz, range 16 g (our sensor)"),
                          ("hz100_r8", "100 Hz, range 8 g"), ("hz100_r16_fe100", "100 Hz, range 16 g, 100 Hz front end (sensitivity)"), ("clip260", "original rate, range 16 g (clipping only)"))]
    a(table(["Sensor model", "Median change in delta-V (%)", "90th percentile of the absolute change (%)", "Largest absolute change (%)", "Median change in ASI (%)"], rows))
    a(f"**Sensor range and rate study.** All {r.i('sevstudy.n_tests')} tests ({r.i('sevstudy.n_frontal')} frontal, {r.i('sevstudy.n_side')} side), range `{{16, 32, 64, 100, 200}}` g by rate `{{100, 200, 400, 800, 1600}}` Hz, 260 Hz front end, "
      "the pulse-release rule of the next paragraph. Error is against the reference delta-V.\n")
    d.tab("range_rate_within10", "Share of tests with delta-V within ±10% of the reference, by range and rate (95% intervals)", "MEASURED_SOFTWARE", "sevstudy.grid.*", "What range and rate the severity code needs")
    rows = [[f"±{rg} g"] + [r.ci(f"sevstudy.grid.r{rg}.f{f}.dv_within10", 2) for f in RATES] for rg in RANGES]
    a(table(["Range"] + [f"`{f} Hz`" for f in RATES], rows))
    d.tab("range_rate_median", "Median and 90th-percentile absolute delta-V error (%), by range and rate", "MEASURED_SOFTWARE", "sevstudy.grid.*", "The 16 g range is the limit; above 64 g the rate matters little")
    rows = [[f"±{rg} g"] + [f"{r.f(f'sevstudy.grid.r{rg}.f{f}.dv_abs_err_median_pct', 1)} / {r.f(f'sevstudy.grid.r{rg}.f{f}.dv_abs_err_p90_pct', 1)}" for f in RATES] for rg in RANGES]
    a(table(["Range"] + [f"`{f} Hz`" for f in RATES], rows))
    d.tab("range_rate_band", "Share of frontal tests inside v <= delta-V <= 2 v, by range and rate", "MEASURED_SOFTWARE", "sevstudy.grid.*band_share", "The physical check agrees with the error study")
    rows = [[f"±{rg} g"] + [r.f(f"sevstudy.grid.r{rg}.f{f}.band_share", 2) for f in RATES] for rg in RANGES]
    a(table(["Range"] + [f"`{f} Hz`" for f in RATES], rows))
    if r.has("sevstudy.needed.point.min_range_g") and r.origin("sevstudy.needed.point.min_range_g") != "NOT_RUN":
        a(f"**Answer.** At least ±{r.f('sevstudy.needed.point.min_range_g', 0)} g and {r.f('sevstudy.needed.point.min_rate_hz', 0)} Hz give delta-V within ±10% on at least 80% of the tests "
          f"({r.i('sevstudy.needed.point.count')} of `25` cells reach 80%; {r.i('sevstudy.needed.ci_lower.count')} also have the lower end of the interval at or above 80%). "
          f"The current setting, ±16 g at 100 Hz, reaches {r.ci('sevstudy.grid.r16.f100.dv_within10', 2)}. At 32 g, the share is {r.f('sevstudy.grid.r32.f400.dv_within10', 2)} at `400 Hz`: not enough on this front end.\n")
    d.tab("frontal_side", "The same study for frontal and side tests separately: share within ±10% at `400 Hz`", "MEASURED_SOFTWARE", "sevstudy.grid_frontal.*, sevstudy.grid_side.*", "Side impacts need the wider range")
    rows = [[f"±{rg} g", r.f(f"sevstudy.grid_frontal.r{rg}.f400.dv_within10", 2), r.f(f"sevstudy.grid_side.r{rg}.f400.dv_within10", 2)] for rg in RANGES]
    a(table(["Range", "Frontal tests", "Side tests"], rows))
    d.tab("bandwidth", "Front-end bandwidth sweep at 1600 Hz sampling: median absolute delta-V error (%) and share within ±10%", "MEASURED_SOFTWARE", "sevstudy.bw.*", "A lower front-end bandwidth lets a smaller range work")
    rows = [[f"`{fe} Hz`"] + [f"{r.f(f'sevstudy.bw.fe{fe}.r{rg}.dv_abs_err_median_pct', 1)} / {r.f(f'sevstudy.bw.fe{fe}.r{rg}.dv_within10', 2)}" for rg in (16, 32, 64, 200)] for fe in (50, 100, 260, 500, 1000)]
    a(table(["Front-end bandwidth", "±16 g", "±32 g", "±64 g", "±200 g"], rows))
    a("A narrower front end smooths the spikes before they reach the range limit, so ±32 g is enough at 100 Hz bandwidth or below, while a wide front end needs the wider range. The front-end filter is our generic model, not a part's measured response.\n")
    parts = [("MPU-6050 +-16 g, 100 Hz (current setting)", 0), ("MPU-6050 +-16 g, 1000 Hz", 1), ("ADXL345 +-16 g, 100 Hz", 2), ("ADXL345 +-16 g, 3200 Hz", 3), ("H3LIS331DL +-100 g, 1000 Hz", 4),
             ("H3LIS331DL +-200 g, 1000 Hz", 5), ("ADXL375 +-200 g, 800 Hz", 6), ("ADXL375 +-200 g, 3200 Hz", 7)]
    d.tab("parts", "Named accelerometers through the same model (range, rate and resolution from the datasheets; 95% intervals)", "MEASURED_SOFTWARE", "sevstudy.part*",
          "Which low-cost parts meet the requirement: the ±100 g and ±200 g parts do, the ±16 g parts do not")
    rows = [[f"`{nm}`", r.ci(f"sevstudy.part{i}.dv_abs_err_median_pct", 1), r.ci(f"sevstudy.part{i}.dv_within10", 2), r.f(f"sevstudy.part{i}.dv_within20", 2), r.f(f"sevstudy.part{i}.band_share", 2)] for nm, i in parts]
    a(table(["Part and setting", "Median absolute error (%)", "Share within ±10%", "Share within ±20%", "Frontal share in the physical band"], rows))
    d.tab("datasheets", "Datasheet values of the four parts (read from the PDFs opened on `2026-11-11`)", "ANALYTICAL", "sevstudy.sheet.*", "Range, resolution and output rate of each part")
    rows = [[k, r.f(f"sevstudy.sheet.{k}.max_range_g", 0), r.f(f"sevstudy.sheet.{k}.resolution_mg_per_count", 3), r.f(f"sevstudy.sheet.{k}.max_odr_hz", 0), f"`{nt}`"]
            for k, nt in (("MPU-6050", "accelerometer low-pass programmable up to 260 Hz; noise 400 ug/sqrt(Hz)"), ("ADXL345", "bandwidth = output rate / 2; noise 0.75 LSB rms (x, y) and 1.1 LSB rms (z) at 100 Hz"),
                          ("ADXL375", "bandwidth = output rate / 2"), ("H3LIS331DL", "bandwidth = output rate / 2; ranges 100, 200 and 400 g"))]
    a(table(["Part", "Largest range (g)", "Resolution at the largest range (mg per count)", "Highest output rate (Hz)", "Other"], rows))
    a("Sensor noise and quantisation are small against the pulses here (quantisation is included in the part runs; noise is not). A recommendation: a ±64 g or wider accelerometer sampled at 200 Hz or faster if severity is to be measured; the MPU-6050 and ADXL345 (±16 g) do not meet it on these tests.\n")
    a(f"**Release rule.** The old rule ended the pulse when horizontal acceleration stayed below 0.5 g for 50 ms. The new rule ends it when it stays below the larger of 0.5 g and a fraction of the pulse peak. "
      f"The fraction was chosen on the {r.i('sevstudy.release.n_tuning')} tuning tests only (median absolute delta-V error at 100 Hz without clipping) and scored once on the {r.i('sevstudy.release.n_heldout')} held-out tests.\n")
    d.tab("release", "Release rule: tuning scores and the held-out result", "MEASURED_SOFTWARE", "sevstudy.release.*", "A release level that follows the pulse peak lowers the delta-V error; the gain clears the interval")
    rows = [[f"`{nm}`", r.f(f"sevstudy.release.tuning.{k}.median_abs_err_pct", 2)] for k, nm in (("abs0.5", "absolute 0.5 g (old rule)"), ("abs1.0", "absolute 1.0 g"), ("abs1.5", "absolute 1.5 g"), ("frac0.02", "0.02 x peak"),
                                                                                         ("frac0.05", "0.05 x peak"), ("frac0.1", "0.1 x peak (chosen)"), ("frac0.15", "0.15 x peak"), ("frac0.2", "0.2 x peak"),
                                                                                         ("frac0.3", "0.3 x peak"), ("frac0.4", "0.4 x peak"))]
    a(table(["Rule", "Median absolute delta-V error on the tuning tests (%)"], rows))
    rows = [["old rule (0.5 g)", r.ci("sevstudy.release.heldout.abs.dv_abs_err_median_pct", 2), r.ci("sevstudy.release.heldout.abs.dv_within10", 2)],
            ["new rule", r.ci("sevstudy.release.heldout.new.dv_abs_err_median_pct", 2), r.ci("sevstudy.release.heldout.new.dv_within10", 2)]]
    a(table(["Held-out tests, 100 Hz, no clipping", "Median absolute error (%)", "Share within ±10%"], rows))
    a(f"The paired difference in the median absolute error (new minus old, same held-out tests) is {r.f('sevstudy.release.heldout.diff_median_abs_err_pct', 2)} points with a 95% interval of {r.f('sevstudy.release.heldout.diff_lo', 2)} to "
      f"{r.f('sevstudy.release.heldout.diff_hi', 2)}: the whole interval is below zero. On VZCrash crash pulses, a share of {r.ci('severity_vzcrash.ci.crash.pulse_cap_share', 2)} still run to the 250 ms cap (descriptive: the noisy dashcam signal rarely stays quiet; "
      f"with the old rule it was {r.f('severity_vzcrash.release0.5.crash.pulse_cap_share', 2)}).\n")
    a("**Rollover.** The gyro-angle flag fires on normal driving, so a drift correction was tried: the gravity direction before the trigger is carried through the crash with the gyro, and the part of the final tilt that the gravity vector at the quiet end of the window does not confirm is removed. "
      "VZCrash has no rollover labels, so this is a false-alarm check, not an accuracy result.\n")
    d.tab("rollover", "Rollover flag rate by VZCrash class, before and after the drift correction (95% intervals)", "MEASURED_SOFTWARE", "severity_vzcrash.rollover.*", "The flag still fires on more than 0.5% of normal driving, so it stays out of the severity class")
    rows = [[c, r.ci(f"severity_vzcrash.rollover.raw.{c}.share", 4), r.ci(f"severity_vzcrash.rollover.corrected.{c}.share", 4), r.f(f"severity_vzcrash.rollover.corrected_applied.{c}.share", 2)] for c in ("crash", "near_miss", "normal_driving")]
    a(table(["Class", "Integrated roll or pitch of 90 degrees or more", "Gravity-frame tilt after the correction", "Share of events where the correction could be applied"], rows))
    a(f"On normal driving the corrected flag still fires on {r.f('severity_vzcrash.rollover.corrected.normal_driving.share', 4)} of events, above 0.5%, so **the rollover flag is kept out of the severity rule** (`SEV_ROLLOVER_IN_CLASS` is off). "
      f"The same share of normal-driving windows reach a tilt of 90 degrees without the correction ({r.f('severity_vzcrash.rollover.tilt.normal_driving.share_ge90', 4)}), so the false alarms are not mainly drift; likely causes are gyro scale or unit differences between devices (the dataset mixes gyro resolutions).\n")
    d.tab("vz_dist", "VZCrash triggered events: severity measures by class (95% intervals on the medians and shares)", "MEASURED_SOFTWARE", "severity_vzcrash.dist.*, severity_vzcrash.ci.*", "Most VZCrash crashes are Low severity by these measures; there are no severity labels")
    rows = []
    for c in ("crash", "near_miss", "normal_driving"):
        p = f"severity_vzcrash.dist.{c}"
        rows.append([c, r.ci(f"severity_vzcrash.ci.{c}.dv_res_kmh.median", 2), r.f(f"{p}.dv_res_kmh.p95", 1), r.ci(f"severity_vzcrash.ci.{c}.asi.median", 3), r.f(f"{p}.asi.p95"),
                     r.f(f"{p}.peak_pulse_g.median", 1), r.ci(f"severity_vzcrash.ci.{c}.pulse_cap_share", 2)])
    a(table(["Class", "Delta-V median (km/h)", "Delta-V 95th percentile", "ASI median", "ASI 95th percentile", "Peak pulse median (g)", "Share of pulses at the maximum length"], rows))
    rows = [[c] + [r.ci(f"severity_vzcrash.ci.class_share.{c}.{n}", 3) for n in CLASS_NAMES] for c in ("crash", "near_miss", "normal_driving")]
    a(table(["Class", "Low", "Moderate", "Severe", "Critical"], rows))
    a(f"{r.i('severity_vzcrash.events_triggered')} triggered events, all splits; no severity labels exist, so no accuracy claim is made. THIV is UNVERIFIED (its flail distances are in doubt) and is left out of the tables and of every claim; it does not enter the class.\n")
    d.tab("score", "Delta-V and ASI used alone as a crash score, de-duplicated test set", "MEASURED_SOFTWARE", "severity_vzcrash.score.*", "ASI separates crashes better than the peak acceleration of the window alone")
    rows = [[nm, r.f(f"severity_vzcrash.score.{k}.ap"), r.f(f"severity_vzcrash.score.{k}.roc_auc")] for k, nm in
            (("asi", "ASI"), ("dv_res_kmh", "Resultant delta-V"), ("peak_pulse_g", "Peak pulse acceleration"), ("mean_pulse_g", "Mean pulse acceleration"),
             ("specific_energy_j_per_kg", "Specific energy"), ("pulse_ms", "Pulse duration"), ("peak_a", "Peak acceleration of the window (baseline)"), ("dv_res_kmh_rel1", "Delta-V with a looser release level (1.0 g, absolute)"),
             ("dv_res_kmh_rel1.5", "Delta-V with a looser release level (1.5 g, absolute)"))]
    a(table(["Score", "AP", "ROC-AUC"], rows))
    a(f"Crashes are {r.f('severity_vzcrash.score_test_crash_share')} of these {r.i('severity_vzcrash.score_test_events')} triggered test events, so an AP near that value means no skill.\n")
    d.tab("thr_sens", "Class mix when each class limit is moved by ±20% (NHTSA tests with the reference delta-V; VZCrash crash events)", "MEASURED_SOFTWARE", "sevstudy.thr.*, severity_vzcrash.thr.*",
          "The class mix depends on the delta-V limits; the VZCrash crash mix hardly moves because almost all crashes are Low")
    variants = ["base"] + [f"{n}.x{s:g}" for n in ("dv_low_moderate", "dv_moderate_severe", "dv_severe_critical", "asi_A_B", "asi_B_C", "asi_C_over") for s in (0.8, 1.2)] + [f"{n}.x{s:g}" for n in ("all_dv", "all_asi") for s in (0.8, 1.2)]
    rows = []
    for v in variants:
        rows.append([f"`{v}`"] + [r.f(f"sevstudy.thr.nhtsa_reference.{v}.share_{n}", 2) for n in CLASS_NAMES] + [r.f(f"severity_vzcrash.thr.vzcrash_crash.{v}.share_{n}", 3) for n in ("Low", "Moderate")])
    a(table(["Limit moved"] + [f"NHTSA reference: {n}" for n in CLASS_NAMES] + ["VZCrash crash: Low", "VZCrash crash: Moderate"], rows))
    a("`dv_low_moderate` is the 24 km/h limit, `dv_moderate_severe` 40 km/h, `dv_severe_critical` 56 km/h; `asi_A_B`, `asi_B_C`, `asi_C_over` are the ASI limits; `x0.8` and `x1.2` move the limit by minus and plus 20%.\n")
    d.tab("c_severity", "C version of the severity code against Python; pure-Python float32 mirror of the C code against Python", "MEASURED_SOFTWARE", "export_severity.*", "The firmware severity code equals the reference")
    rows = []
    for lab, nm in (("vzcrash_test", "VZCrash test windows"), ("nhtsa", "NHTSA windows (100 Hz, sensor model)")):
        p = f"export_severity.{lab}"
        c_ok = r.origin(f"{p}.c.max_abs_diff.dv_res_kmh") != "NOT_RUN"
        rows.append([nm, r.i(f"{p}.windows"), r.sci(f"{p}.c.max_abs_diff.dv_res_kmh") if c_ok else "NOT_RUN (blocked by Windows; see the note)", r.sci(f"{p}.c.max_abs_diff.asi") if c_ok else "NOT_RUN",
                     r.i(f"{p}.c.class_mismatches") if c_ok else "NOT_RUN", r.sci(f"{p}.mirror.max_abs_diff.dv_res_kmh"), r.sci(f"{p}.mirror.max_abs_diff.asi"), r.i(f"{p}.mirror.class_mismatches"), r.i(f"{p}.mirror.rollover_flag_mismatches")])
    a(table(["Windows", "Count", "C: max difference in delta-V (km/h)", "C: max difference in ASI", "C: different class", "Mirror: delta-V", "Mirror: ASI", "Mirror: different class", "Mirror: different rollover flag"], rows))
    a("The C header is `firmware_export/severity.h` (no heap). It was compiled and run on the host; it has not been run on the ESP32. If Windows blocks the compiled program the C columns say NOT_RUN and the mirror columns remain.\n")
    d.fig("sevstudy_range_rate_heatmap", "Median delta-V error, share within ±10%, and physical-band share for each range and sample rate.", "MEASURED_SOFTWARE", "sevstudy.grid.*", "Range and rate study")
    d.fig("sevstudy_bandwidth", "Median absolute delta-V error against front-end bandwidth for four ranges.", "MEASURED_SOFTWARE", "sevstudy.bw.*", "Front-end bandwidth")
    d.fig("nhtsa_validation", "NHTSA frontal tests: delta-V against impact speed with the v and 2 v lines, the change for different sensor ranges, and ASI against peak acceleration.", "MEASURED_SOFTWARE", "nhtsa.*", "Delta-V validation")
    d.fig("severity_synthetic_verification", "Severity code on synthetic pulses: delta-V error against pulse duration.", "SIMULATED", "severity_synth.*", "Code verification")
    d.fig("severity_vzcrash_distributions", "VZCrash triggered events: distributions of delta-V, ASI and THIV (UNVERIFIED, not used in any claim) by class, and the share of each severity class.", "MEASURED_SOFTWARE", "severity_vzcrash.*", "Descriptive severity")


def security_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.6 Security\n")
    d.tab("attacks", "Attack suite (software simulation of the reference verifier)", "SIMULATED", "attacks.*", "Forged, tampered, replayed and spoofed packets are rejected; the retry bug was found and fixed; two limits are documented")
    att = pd.read_csv(C.TABLES / "attacks.csv")
    a(table(["Case", "Expected", "Observed", "Match"], [[x.case, x.expected, x.observed, "yes" if x.match else "NO"] for x in att.itertuples()]))
    a("'reack' means the base sends the identical ACK again without processing the alert a second time. Our own testing found that a strict anti-replay rule blocks the retry of an alert whose ACK was lost (the row marked 'before the fix'); "
      "the idempotent re-ACK repairs this. Documented limits, not fixed: a recorded alert is accepted again if the base loses its counter store; the 32-bit counter cannot wrap without a key change; one key is shared, so anyone holding it can sign for any node. "
      "A property-based test (hypothesis) checks that the counter never goes backwards, that a re-ACK is idempotent, that any single-bit flip and any truncation or padding is rejected, and the parser is fuzzed with random and mutated input: every outcome is accept or reject and nothing crashes. "
      "These are software tests, not measurements on the radios.\n")
    d.tab("flood", "Replay flood against the re-ACK, with and without the limit", "SIMULATED", "attacks.flood.*", "The limit lowers the airtime a flood can cost; it does not remove the cost")
    rows = []
    for tag, nm in (("no_limit", "no limit"), ("with_limit", "one re-ACK per event per retry interval")):
        p = f"attacks.flood.{tag}"
        rows.append([nm, r.i(f"{p}.replayed_packets"), r.i(f"{p}.reacks_sent"), r.f(f"{p}.reack_airtime_s", 1), r.i(f"{p}.reacks_refused_no_budget"), r.i(f"{p}.reacks_refused_by_limit"), r.v(f"{p}.genuine_alert_during_flood"), r.f(f"{p}.budget_left_s", 1)])
    a(table(["Base station", "Replayed packets", "Re-ACKs sent", "Re-ACK airtime (s)", "Refused: no budget", "Refused: limit", "Genuine alert during the flood", "Budget left (s)"], rows))
    a(f"One captured alert is replayed {r.i('attacks.flood.rate_per_s')} times a second for {r.i('attacks.flood.duration_s')} s against a base station at SF7 with {r.f('attacks.flood.base_budget_at_start_s', 0)} s of duty-cycle budget left. "
      "A flood long enough still uses up the budget.\n")
    d.tab("forgery", "Forgery and counter analysis", "ANALYTICAL", "forgery.*, counter.*", "A blind forgery is not feasible within any plausible time; the counter lasts for centuries at the legal rate")
    rows = []
    for sf in (7, 9, 12):
        rows.append([f"SF{sf}", r.f(f"forgery.sf{sf}.airtime_limit.airtime_ms", 1), r.f(f"forgery.sf{sf}.airtime_limit.packets_per_s", 3), r.sci(f"forgery.sf{sf}.airtime_limit.expected_years"), r.sci(f"forgery.sf{sf}.duty_limited.expected_years")])
    a(table(["Spreading factor", "97 B alert airtime (ms)", "Forgery attempts per second at the airtime limit", "Expected years to one accepted forgery, airtime limit", "Same at the 10% duty cycle"], rows))
    a(f"The tag has 64 bits, so one blind attempt is accepted with probability {r.sci('forgery.p_per_attempt')} and one expected success needs {r.sci('forgery.expected_attempts')} attempts. This assumes the key stays secret; it says nothing about key theft. "
      f"The counter has {r.sci('counter.values')} values. At the fastest legal rate (SF7, 10% duty cycle: {r.f('counter.alerts_per_hour.duty_limit_alerts_per_hour.sf7', 0)} alerts per hour) it wraps after {r.f('counter.wrap_years.duty_limit_alerts_per_hour.sf7', 0)} years; "
      f"at one alert per minute after {r.f('counter.wrap_years.one_alert_per_minute.slow', 0)} years. A replay flood and a counter store that is lost are the real limits (above); there is no key rotation.\n")


def _pool_rows(r: Res) -> list[list[str]]:
    rows = []
    for nm, pre in (("VZCrash alerts (real replay mix)", "replay.pool.sev_share"), ("NHTSA tests through the 16 g sensor", "replay.pool.nhtsa16.sev_share")):
        rows.append([nm] + [r.f(f"{pre}.{c.lower()}", 3) for c in CLASS_NAMES])
    rows.append(["Stress mix (assumed)"] + ["`0.4`", "`0.3`", "`0.2`", "`0.1`"])
    return rows


def replay_section(r: Res, d: Doc) -> None:
    a = d.a
    a("### 4.7 End-to-end software replay\n")
    a("Real VZCrash test events are replayed through the whole chain in software: trigger, window, features, the deployed model, the severity class, the cancel window, a signed alert (real HMAC), the duty-cycle limiter, a lossy channel, the base verifier with idempotent re-ACK, and the signed ACK back. "
      "The event pool (model probabilities, severity classes) is MEASURED_SOFTWARE; arrivals, losses and stage times are SIMULATED with the assumptions below. **These are not hardware measurements; hardware test H3 would replace them.**\n")
    a(f"Assumptions: Poisson alert arrivals at a stated rate, each alert a random draw from the events the model called a crash ({r.i('replay.pool.alerts')} alerts, of which {r.i('replay.pool.alerts_false')} are false alarms); "
      f"window fill {r.f('replay.assume.window_fill_s', 1)} s; on-device compute {r.f('replay.assume.compute_s', 2)} s (not measured: NOT_RUN on the ESP32); cancel windows of "
      f"{r.f('replay.assume.cancel_s.low', 0)}, {r.f('replay.assume.cancel_s.moderate', 0)}, {r.f('replay.assume.cancel_s.severe', 0)} and {r.f('replay.assume.cancel_s.critical', 0)} s for Low to Critical; no driver cancels; one node and one base; no collisions. "
      f"Loss is independent per transmission, or a two-state burst model (Gilbert-Elliott: bad-state loss {r.f('replay.assume.ge_loss_bad', 1)}, a burst ends with probability {r.f('replay.assume.ge_p_bg', 1)} per transmission) with the same mean loss; "
      "alert and ACK directions have separate chains. The re-ACK limit is on. Each cell is 100 simulated hours (20 hours for each of five seeds) with bootstrap intervals over hours.\n")
    d.tab("pool", "Severity mix of the alerts the replay sends", "MEASURED_SOFTWARE", "replay.pool.*", "The real VZCrash mix is almost all Low: a severity policy has little to prioritise on this data")
    a(table(["Source", "Low", "Moderate", "Severe", "Critical"], _pool_rows(r)))
    a("The VZCrash mix comes from the deployed model's alerts and the severity code (the rollover flag is out of the class rule). The NHTSA mix shows what the 16 g sensor would report for full-speed crashes. "
      "The stress mix is an assumption (the mix used in the earlier delivery simulation) so that all four classes appear.\n")
    d.tab("replay_main", "Replay with the stress mix at 30% loss: delivery, latency and budget, by spreading factor, loss model and policy", "SIMULATED", "replay.grid.stress.*", "Retries help; the severity table delivers critical alerts; burst loss lowers delivery")
    rows = []
    for sf in (7, 9, 12):
        for kind, kn in (("iid", "independent"), ("ge", "burst")):
            for pol in ("none", "fixed3", "severity"):
                p = f"replay.grid.stress.sf{sf}.{kind}.loss30.{pol}"
                rows.append([f"SF{sf}", kn, pol, r.ci(f"{p}.delivered_all", 2), r.ci(f"{p}.delivered_critical", 2), r.f(f"{p}.median_lat_s_critical", 1), r.f(f"{p}.p95_lat_s_critical", 1), r.f(f"{p}.retries_all", 2),
                             r.f(f"{p}.airtime_share_total", 3)])
    a(table(["SF", "Loss model", "Policy", "Alerts acknowledged", "Critical alerts acknowledged", "Median trigger-to-ACK, critical (s)", "95th percentile (s)", "Mean retries", "Share of the node's duty-cycle budget used"], rows))
    a("Trigger-to-ACK time includes the window fill, the compute time and the cancel window (about 5 s for critical alerts), so it is dominated by those stages; the radio part is the remainder. "
      "Per-class results for every class, loss from 0 to 60%, and the real VZCrash and NHTSA mixes are in `results/tables/replay_grid.csv`.\n")
    d.tab("replay_vz", "Replay with the real VZCrash mix at 30% loss (all alerts are Low): delivery by policy", "SIMULATED", "replay.grid.vzcrash.*", "With the real mix the severity table gives every alert two tries and delivers fewer than the fixed policy")
    rows = []
    for sf in (7, 12):
        for pol in ("none", "fixed3", "severity"):
            p = f"replay.grid.vzcrash.sf{sf}.iid.loss30.{pol}"
            rows.append([f"SF{sf}", pol, r.ci(f"{p}.delivered_all", 2), r.f(f"{p}.median_lat_s_all", 1), r.f(f"{p}.p95_lat_s_all", 1), r.f(f"{p}.retries_all", 2), r.f(f"{p}.airtime_share_total", 3)])
    a(table(["SF", "Policy", "Alerts acknowledged", "Median trigger-to-ACK (s)", "95th percentile (s)", "Mean retries", "Share of budget used"], rows))
    d.tab("replay_base", "Base station already near its duty-cycle budget (2 s left), 60 alerts per hour, 30% loss: critical alerts", "SIMULATED", "replay.sens.stress.basenear_*", "A base near its budget cannot ACK; the policy cannot fix that")
    rows = []
    for sf in (7, 9, 12):
        for pol in ("fixed3", "severity"):
            for tag, nm in (("baseref", "full budget"), ("basenear", "2 s left")):
                p = f"replay.sens.stress.{tag}_sf{sf}.{pol}"
                rows.append([f"SF{sf}", pol, nm, r.f(f"{p}.delivered_critical", 3), r.f(f"{p}.median_lat_s_critical", 1), r.f(f"{p}.base_ack_airtime_share", 3), r.f(f"{p}.never_sent_critical", 3)])
    a(table(["SF", "Policy", "Base budget", "Critical alerts acknowledged", "Median trigger-to-ACK (s)", "Base ACK airtime (share of budget)", "Critical alerts never sent"], rows))
    d.tab("replay_flood", "Replay flood inside the replay pipeline: alerts that arrive during the flood", "SIMULATED", "replay.flood.*", "With the re-ACK limit, genuine alerts during a flood are still served")
    rows = []
    for pool in ("stress", "vzcrash"):
        for tag, nm in (("limit_off", "limit off"), ("limit_on", "limit on")):
            p = f"replay.flood.{pool}.{tag}"
            rows.append([pool, nm, r.ci(f"{p}.delivered_inside", 3), r.ci(f"{p}.delivered_outside", 3), r.f(f"{p}.base_ack_airtime_s", 1), r.f(f"{p}.replayed", 0)])
    a(table(["Mix", "Re-ACK limit", "Alerts acknowledged while the flood runs", "Alerts acknowledged outside it", "Base ACK airtime (s)", "Replayed packets"], rows))
    a(f"A captured alert is replayed {r.f('replay.assume.flood_rate_per_s', 0)} times a second for {r.f('replay.assume.flood_duration_s', 0)} s at SF7 with a base station that has {r.f('replay.assume.flood_base_budget_s', 0)} s of budget left; "
      f"genuine alerts arrive at {r.f('replay.assume.flood_alert_rate_per_h', 0)} per hour with the severity table. The limit is one re-ACK per event per retry interval.\n")
    d.tab("replay_conclusions", "Which conclusions survive when the assumptions change (cells where the interval condition holds, of all cells)", "SIMULATED", "replay.conclusion.*",
          "Retries help everywhere; the severity table protects critical alerts; its airtime saving depends on the mix; burst loss lowers delivery in most cells")
    concl = (("C1_retries_help", "Retries beat no retry (paired interval above zero)"), ("C2_severity_not_worse_for_critical", "Severity table not worse than fixed for critical alerts (lower bound above `-0.02`)"),
             ("C2b_severity_better_for_critical", "Severity table better for critical alerts"), ("C3_severity_costs_low_alerts", "Severity table delivers fewer low alerts"),
             ("C4_burst_lowers_delivery", "Burst loss lowers delivery against independent loss at the same mean"), ("C5_severity_uses_less_airtime", "Severity table uses less of the budget"))
    rows = []
    for k, nm in concl:
        row = [nm]
        for pool in ("stress", "nhtsa16", "vzcrash"):
            if r.has(f"replay.conclusion.{pool}.{k}.holds"):
                row.append(f"{r.i(f'replay.conclusion.{pool}.{k}.holds')} of {r.i(f'replay.conclusion.{pool}.{k}.cells')}")
            else:
                row.append("n/a (no critical alerts in this mix)" if "critical" in k else "n/a")
        rows.append(row)
    a(table(["Conclusion", "Stress mix", "NHTSA mix", "Real VZCrash mix"], rows))
    a("The cells are the grid (three spreading factors, two loss models, six loss levels) and the sensitivity cells (event rate, ACK loss, cancel window, base or node near its budget). "
      "Conclusions that do not hold in every cell are the ones that depend on the assumption: the budget saving of the severity table depends on the mix, and the burst-loss effect is not significant at low loss.\n")
    d.tab("timeline", "Stages from the trigger to the ACK for a lossless exchange at SF7", "ANALYTICAL", "replay.timeline.*, replay.assume.*", "The cancel window dominates the time to the ACK")
    tl = pd.read_csv(C.TABLES / "replay_stage_timeline.csv")
    rows = [[x.sev, f"`{x.window_fill_s:.1f}`", f"`{x.compute_s:.2f}`", f"`{x.cancel_s:.0f}`", f"`{x.alert_airtime_s:.3f}`", f"`{x.base_processing_s:.1f}`", f"`{x.ack_airtime_s:.3f}`", r.f(f"replay.timeline.{x.sev}.total_s", 2)] for x in tl.itertuples()]
    a(table(["Class", "Window fill (s)", "Compute (s)", "Cancel window (s)", "Alert on air (s)", "Base processing (s)", "ACK on air (s)", "Total (s)"], rows))
    a("The stage times are the stated assumptions and the analytical airtime; the table values in the leading columns are the configured constants. H3 on hardware would measure them.\n")
    d.fig("replay_delivery_vs_loss", "Delivery against loss, independent and burst, three policies and three spreading factors.", "SIMULATED", "replay.grid.stress.*", "Delivery against loss")
    d.fig("replay_latency_cdf", "Trigger-to-ACK time per severity class.", "SIMULATED", "results/tables/replay_grid.csv", "Latency per class")
    d.fig("replay_airtime_budget", "Cumulative node airtime during one simulated hour for the three policies.", "SIMULATED", "results/tables/replay_grid.csv", "Duty-cycle use")
    d.fig("replay_stage_timeline", "Pipeline stage timeline by severity class.", "ANALYTICAL", "replay.timeline.*", "Where the time goes")
