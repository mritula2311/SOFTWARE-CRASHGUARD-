"""Report subsection 4.10 (continued): X5 sensor spoofing, X6 many-car capacity, X7 physical scaling (N21 to N23). Numbers only through the ``Res`` helpers; hand-typed numbers only inside backticks."""
from __future__ import annotations

from crashguard.report import Doc, Res, table

AMPS = (0.25, 0.5, 1.0, 2.0, 4.0)
TAUS = (0.25, 0.5, 1.0, 2.0)


def _g(x: float) -> str:
    return f"{x:g}"


def x7_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N23. Scale-model transfer by physical scaling of VZCrash events (X7)\n")
    a("Every de-duplicated test event was transformed as `b + a (x(t / tau) - b)` (`b` = the per-axis median, i.e. gravity, kept; time stretched by `tau` and resampled at `100` Hz; for `tau` below `1` a zero-phase `45` Hz low-pass applied beforehand), clipped at the sensor range, re-triggered (the trigger moves with the amplitude) and re-featured. "
      f"The deployed forest (all `14` features) and the same forest on the `5` scale-free features, both trained on unscaled data, are applied unchanged with their validation thresholds ({r.i('x7.n_events')} test events). "
      "**This is a plausibility check. It cannot predict performance on the author's car; the hardware transfer test (H2) is the real test.** The gyro is only resampled in time (its amplitude is not scaled), which is an assumption.\n")
    d.tab("x7_grid", "X7: system recall, false-alarm rate and system AP over the amplitude (a) and time-scale (tau) grid, all features against scale-free features (mean over seeds 0 to 4)", "MEASURED_SOFTWARE", "x7.filtered.*",
          "Amplitude matters far more than time scale; the scale-free subset is not invariant")
    rows = []
    for av in AMPS:
        for tv in TAUS:
            p = f"x7.filtered.a{_g(av)}.tau{_g(tv)}"
            rows.append([_g(av), _g(tv), r.f(f"{p}.all.recall.mean", 3), r.f(f"{p}.scale_free.recall.mean", 3), r.f(f"{p}.all.fa.mean", 3), r.f(f"{p}.scale_free.fa.mean", 3), r.f(f"{p}.all.sys_ap.mean", 3), r.f(f"{p}.scale_free.sys_ap.mean", 3),
                         r.f(f"{p}.all.trig_rate_crash.mean", 3)])
    a(table(["a", "tau", "Recall, all", "Recall, scale-free", "False-alarm rate, all", "False-alarm rate, scale-free", "System AP, all", "System AP, scale-free", "Crashes that pass the trigger"], rows))
    a(f"At a = `1` and tau = `1` the transform changes nothing, and the numbers equal the headline detector (system recall {r.f('x7.filtered.a1.tau1.all.recall.seed42', 3)}, false-alarm rate {r.f('x7.filtered.a1.tau1.all.fa.seed42', 3)} for seed 42): a check that the pipeline is correct. "
      f"Halving the amplitude cuts the recall to {r.f('x7.filtered.a0.5.tau1.all.recall.mean', 2)} (all features) because many crashes no longer pass the `2` g trigger; doubling it raises the false-alarm rate to {r.f('x7.filtered.a2.tau1.all.fa.mean', 3)}; at a = `4` about half of all non-crash events alarm. "
      f"The scale-free subset loses less recall at a = `0.5` ({r.f('x7.filtered.a0.5.tau1.scale_free.recall.mean', 2)}) but gains no robustness in AP at large a ({r.f('x7.filtered.a4.tau1.scale_free.sys_ap.mean', 2)} against {r.f('x7.filtered.a4.tau1.all.sys_ap.mean', 2)}), so it does not make the detector invariant. "
      "A scale model would therefore need its amplitude matched to real-crash amplitudes (or a re-tuned trigger), which is what H2 tests.\n")
    d.tab("x7_inv", "X7: median relative change of each feature when only the amplitude (x2) or only the time scale (x2) changes", "MEASURED_SOFTWARE", "x7.invariance.*", "Which features are actually invariant")
    rows = []
    for f in ("peak_a", "peak_ax", "peak_ay", "peak_az", "rms_a", "jerk_peak", "energy", "dur_above", "peak_ratio_xy", "horiz_share", "kurtosis_a", "crest", "post_quiet", "gyro_peak"):
        rows.append([f, r.f(f"x7.invariance.amplitude_x2.{f}", 3), r.f(f"x7.invariance.time_scale_x2.{f}", 3)])
    a(table(["Feature", "Amplitude x2", "Time scale x2"], rows))
    a("The three peak features scale with the amplitude and not with time; jerk scales with both; the duration above `2` g and the energy depend on both. The five scale-free features are only nearly invariant: they are not exactly so because gravity is part of the magnitude, and because the window is re-cut at the moved trigger. "
      "The peak features are unchanged by a time scale, as expected.\n")
    d.tab("x7_nyquist", "X7: the Nyquist problem: share of triggered crash windows whose time above 2 g is shorter than 40 ms, and its median (a = 1)", "MEASURED_SOFTWARE", "x7.filtered.a1.*", "Shortening the pulse puts it below what a 100 Hz sensor resolves")
    rows = []
    for tv in TAUS:
        p = f"x7.filtered.a1.tau{_g(tv)}.all"
        pu = f"x7.unfiltered.a1.tau{_g(tv)}.all"
        rows.append([_g(tv), r.f(f"{p}.short_pulse_share.mean", 2), r.f(f"{p}.median_dur_ms.mean", 0), r.f(f"{p}.recall.mean", 3), r.f(f"{pu}.recall.mean", 3), r.f(f"{pu}.fa.mean", 3)])
    a(table(["tau", "Crash windows with time above 2 g under 40 ms", "Median time above 2 g (ms)", "Recall (low-pass applied beforehand)", "Recall (no low-pass, aliased)", "False-alarm rate (no low-pass)"], rows))
    a("For tau below `1` the pulses are compressed below about `40` ms, where a `100` Hz sensor with a `40` Hz filter cannot resolve them; the low-pass hides the problem (the pulse is smoothed) and without it the result aliases. A faster sensor sampling rate on the scale model would be needed to keep the pulse shape.\n")


EPS = (0.1, 0.25, 0.5, 1.0, 2.0)
PIPES = (("baseline", "baseline forest"), ("D1_median", "D1 median filter"), ("D2_plausibility", "D2 delta-V and cross-axis plausibility"), ("D3_adversarial_training", "D3 adversarial training"), ("D4_physics_ensemble", "D4 minimum delta-V (physics ensemble)"))


def x5_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N21. Robustness to a bounded signal added to the accelerometer (X5)\n")
    a("Threat model and limits are in `docs/01_protocol/THREAT_MODEL_SPOOFING.md`: an attacker adds a signal of at most epsilon g per axis made of one to three sinusoids between `2` and `45` Hz to a stored window. **Simulation on dataset windows only; no attack code for a physical sensor was written.** "
      "The premise that a MEMS accelerometer or gyroscope can be made to report attacker-chosen low-frequency content comes from published work on acoustic and resonant injection (Tu et al., USENIX Security 2018, opened; it cites Son et al. 2015 and Trippel et al. 2017, which were not opened); "
      "the budget grid, the sinusoid restriction, the targets, the search and surrogate attacks, the defences and the evaluation on VZCrash windows are ours. Whether a real transmitter could deliver such a signal to a sensor in a car is not studied. "
      f"Attacked windows: {r.i('x5.n_attacked.a')} triggered non-crash windows (goal a: classified as a crash) and {r.i('x5.n_attacked.b')} crash windows (goal b: not alarmed), a fixed random sample of the de-duplicated test set; nothing was tuned on them. "
      "Attacks: random search (`100` bounded mixtures), a structured grid (`196` single sinusoids), and a projected-gradient attack on a logistic or small neural surrogate, transferred to the forest. A black-box search counts a window as attacked if any candidate works.\n")
    d.tab("x5_base", "X5: attack success against the deployed forest, by budget and attack, net of what the forest already does without an attack", "MEASURED_SOFTWARE", "x5.net.*", "A structured sinusoid search succeeds at 0.5 g or more; surrogate transfer is weaker")
    rows = []
    for goal, gn in (("a", "a: non-crash window alarmed"), ("b", "b: crash window missed")):
        for e in EPS:
            p = f"x5.net.{goal}.baseline.eps{e:g}"
            rows.append([gn, f"{e:g} g", r.f(f"x5.asr.{goal}.baseline.eps{e:g}.none", 3), r.f(p + ".random", 3), r.f(p + ".structured", 3), r.f(p + ".transfer_logistic", 3), r.f(p + ".transfer_mlp", 3), r.f(p + ".any", 3)])
    a(table(["Goal", "Epsilon", "Already true without an attack", "Random search (net)", "Structured search (net)", "Surrogate: logistic (net)", "Surrogate: network (net)", "Any attack (net)"], rows))
    a(f"Net success is the share of windows that were not already in the wanted state and are moved into it. A large share of triggered non-crash windows ({r.f('x5.asr.a.baseline.eps0.1.none', 2)}) is already alarmed at the validation threshold, which is why the net figure is shown. "
      f"A structured sinusoid search turns {r.f('x5.net.a.baseline.eps0.5.structured', 2)} of the rest into alarms at `0.5` g and almost all at `1` g or more; hiding a crash is much harder (net {r.f('x5.net.b.baseline.eps0.5.any', 2)} at `0.5` g and {r.f('x5.net.b.baseline.eps2.any', 2)} at `2` g). "
      "The trigger is no obstacle: a quiet vehicle crosses `2` g when about `1` g is added along gravity (analytical).\n")
    d.tab("x5_def", "X5: defences: attack success with any attack (95% intervals over windows), the paired difference from the baseline, and the clean cost", "MEASURED_SOFTWARE", "x5.asr.*, x5.diff.*, x5.clean.*", "Defences help against the false-crash goal at small budgets and cost on the hidden-crash goal")
    rows = []
    for pk, pn in PIPES:
        for e in (0.25, 0.5, 1.0, 2.0):
            da = f"x5.asr.a.{pk}.eps{e:g}.any"
            db = f"x5.asr.b.{pk}.eps{e:g}.any"
            diff_a = r.ci(f"x5.diff.a.{pk}.eps{e:g}.any", 3) if pk != "baseline" else "-"
            diff_b = r.ci(f"x5.diff.b.{pk}.eps{e:g}.any", 3) if pk != "baseline" else "-"
            rows.append([pn, f"{e:g} g", r.ci(da, 3), diff_a, r.ci(db, 3), diff_b])
    a(table(["Pipeline", "Epsilon", "Goal a: alarmed after attack [95%]", "Difference from the baseline [95%]", "Goal b: missed after attack [95%]", "Difference from the baseline [95%]"], rows))
    rows = []
    for pk, pn in PIPES:
        rows.append([pn, r.ci(f"x5.clean.{pk}.recall", 3), r.ci(f"x5.clean.{pk}.fa", 4)])
    a(table(["Pipeline", "Clean system recall [95%]", "Clean system false-alarm rate [95%]"], rows))
    a(f"Parameters from validation: median filter of {r.i('x5.d1.chosen_k')} samples; plausibility limits at the {r.f('x5.d2.quantile', 2)} quantile of the training crashes (delta-V over peak at least {r.f('x5.d2.ratio_min_kmh_per_g', 2)} km/h per g, horizontal share at least {r.f('x5.d2.horiz_share_min', 2)}); minimum delta-V {r.f('x5.d4.dv_min_kmh', 0)} km/h; adversarial training on {r.i('x5.d3.n_attacked_training_windows')} attacked training windows. "
      "**Decision rule** (attack success below the baseline's by an interval that excludes zero AND a clean recall loss under `0.02`): D4 meets it against goal a at `0.5` g (difference "
      f"{r.ci('x5.diff.a.D4_physics_ensemble.eps0.5.any', 3)}, clean recall loss {r.f('x5.clean_recall_loss.D4_physics_ensemble', 3)}); D2 meets it against goal a at `0.5` g by a small margin; D1 does not (clean recall loss {r.f('x5.clean_recall_loss.D1_median', 3)}); D3 does not. "
      "No defence helps at `1` g or more. **Every defence that lowers the false-crash goal raises the hidden-crash goal** (the differences for goal b are positive for D1, D2 and D4), and adversarial training makes hiding a crash much easier at `1` g and `2` g. "
      "The clean recall loss is measured at each pipeline's own validation threshold (maximum F1), not at a fixed `5%` false-alarm target as the plan said; D1 and D4 also lower the clean false-alarm rate, so part of their recall loss is that trade. "
      "Verdict: at most a partial, budget-limited gain against false crashes with a cost on hidden crashes: no improvement found as a general defence.\n")


def x6_section(r: Res, d: Doc) -> None:
    a = d.a
    a("#### N22. Many-car LoRa capacity (X6)\n")
    a("**ANALYTICAL.** Pure-ALOHA success of an alert packet and the base station's own limit, then an **event-driven SIMULATION** of `N` cars on one channel with Poisson alerts, periodic unconfirmed heartbeats, an optional burst of `30` critical alerts within `10` s, a half-duplex base that pays each ACK from its own `10%` duty-cycle bucket, and the three delivery policies (the scheduler with its N16 parameters, not re-tuned). "
      "Every assumption is listed in the module docstring (`src/crashguard/capacity.py`): one channel, one spreading factor, heartbeat payload `16` bytes, a `6` dB capture rule, `10%` extra loss each way, a `0.1` alerts per car per hour stress rate and a `40/30/20/10` severity mix. None of it is measured.\n")
    d.tab("x6_analytic", "X6: airtime and the base station's ACK budget by spreading factor (ANALYTICAL)", "ANALYTICAL", "x6.analytic.*", "At SF12 the base can send only a couple of hundred ACKs per hour")
    rows = []
    for sf in (7, 9, 12):
        p = f"x6.analytic.sf{sf}"
        rows.append([f"SF{sf}", r.f(p + ".alert_airtime_s", 3), r.f(p + ".ack_airtime_s", 3), r.f(p + ".heartbeat_airtime_s", 3), r.f(p + ".base_acks_per_hour", 0), r.f(f"x6.analytic.sf{sf}.hb600.cars_at_ack_limit", 0)])
    a(table(["Spreading factor", "97 B alert (s)", "26 B ACK (s)", "16 B heartbeat (s)", "ACKs per hour in the base's 10% duty cycle", "Cars whose alerts (0.1 per car per hour) would use all of it"], rows))
    d.tab("x6_aloha", "X6: probability that an alert is not destroyed by another packet (pure ALOHA, and with the capture effect), heartbeat every 600 s", "ANALYTICAL", "x6.analytic.*", "Collision risk is small at SF7 and large at SF12 with frequent heartbeats")
    rows = []
    for sf in (7, 9, 12):
        for hb in (600, 60):
            row = [f"SF{sf}", f"{hb} s"]
            for n in (10, 100, 500):
                row.append(f"{r.f(f'x6.analytic.sf{sf}.hb{hb}.n{n}.alert_success.aloha', 3)} / {r.f(f'x6.analytic.sf{sf}.hb{hb}.n{n}.alert_success.capture', 3)}")
            rows.append(row)
    a(table(["Spreading factor", "Heartbeat period", "N = 10 (no capture / capture)", "N = 100", "N = 500"], rows))
    d.tab("x6_sim", "X6: simulated critical-alert delivery and heartbeat delivery against the number of cars, by spreading factor and policy (heartbeat every 600 s, 0.1 alerts per car per hour; mean over 10 simulated hours)", "SIMULATED", "x6.sim.*", "The channel, not the base's ACK budget, limits delivery; SF12 breaks down first")
    rows = []
    for sf in (7, 9, 12):
        for n in (20, 100, 200, 500):
            for pol in ("fixed3", "severity", "scheduler"):
                p = f"x6.sim.sf{sf}.hb600.n{n}.r0.1.steady.{pol}"
                if r.has(p + ".delivered_critical"):
                    rows.append([f"SF{sf}", str(n), pol, r.ci(p + ".delivered_critical", 3), r.f(p + ".delivered_all", 3), r.f(p + ".hb_delivery", 3), r.f(p + ".alert_tx_collided_share", 3), r.f(p + ".base_ack_airtime_share", 3)])
    a(table(["Spreading factor", "Cars", "Policy", "Critical alerts acknowledged [95%]", "All alerts acknowledged", "Heartbeats received", "Alert transmissions lost to collisions", "Share of the base's duty budget used for ACKs"], rows))
    d.tab("x6_burst", "X6: a burst of 30 critical alerts within 10 s (SF7, heartbeat every 600 s): critical alerts acknowledged and the scheduler's paired gain", "SIMULATED", "x6.sim.*burst*", "Immediate retries collide; spaced retries recover most of the burst")
    rows = []
    for n in (50, 100, 200, 350, 500):
        row = [str(n)]
        for pol in ("fixed3", "severity", "scheduler"):
            row.append(r.ci(f"x6.sim.sf7.hb600.n{n}.r0.1.burst.{pol}.delivered_critical", 3))
        row.append(r.ci(f"x6.sim.sf7.hb600.n{n}.r0.1.burst.critical_delivery_diff_scheduler_minus_severity", 3))
        row.append(r.f(f"x6.sim.sf7.hb600.n{n}.r0.1.burst.scheduler.p95_lat_s_critical", 1))
        row.append(r.f(f"x6.sim.sf7.hb600.n{n}.r0.1.burst.severity.p95_lat_s_critical", 1))
        rows.append(row)
    a(table(["Cars", "Fixed policy", "Severity table", "Scheduler", "Scheduler minus severity table [95%]", "Scheduler p95 latency of critical alerts (s)", "Severity table p95 latency (s)"], rows))
    a(f"**What changes with the assumptions.** (1) The base station's ACK budget is not the bottleneck anywhere in the grid: at the default alert rate of `0.1` per car per hour the base used at most {r.f('x6.sim.sf12.hb600.n350.r0.1.burst.fixed3.base_ack_airtime_share', 3)} of its duty allowance, and at the higher rates up to {r.f('x6.sim.sf7.hb600.n200.r10.steady.scheduler.base_ack_airtime_share', 2)} of it at SF7 and {r.f('x6.sim.sf12.hb600.n50.r10.steady.fixed3.base_ack_airtime_share', 2)} at SF12; no simulated hour had an ACK dropped for budget (largest count {r.f('x6.sim.sf9.hb600.n500.r0.1.steady.severity.ack_budget_drops', 0)} for the cell checked); the analytic limit is {r.f('x6.analytic.sf12.base_acks_per_hour', 0)} ACKs per hour at SF12 and {r.f('x6.analytic.sf7.base_acks_per_hour', 0)} at SF7, so it would bind at the car counts in the analytic table, far above the sizes simulated. "
      "A higher alert rate (`2` and `10` alerts per car per hour, `50` to `200` cars) uses a larger part of the budget (the shares above) without dropping an ACK for budget at SF7; at SF12 delivery collapses with collisions and long packets while the base uses more than half of its allowance, so the two limits are not separated there. "
      "(2) At the default alert rate and SF7 the channel is the earlier limit: at SF12 with `100` or more cars most heartbeats and many alerts collide, and critical delivery falls (see the table); at SF7 critical delivery stays near one up to `500` cars in the steady state. The heartbeat rate matters: a `60` s heartbeat saturates the slower spreading factors at small `N` (the analytic table). "
      "(3) In a burst, immediate retries collide again and again: the fixed policy and the severity table acknowledge only a quarter to a third of the critical alerts at SF7, while the scheduler's spaced retries acknowledge most of them, at the cost of a longer latency (a tradeoff the table shows). This is the one condition in which the scheduler clearly beats the severity table, and it rests on the assumed capture rule and burst size. "
      "(4) The spreading factor decides everything else: the same car count that is harmless at SF7 breaks at SF12. All of this is simulation under the stated assumptions; hardware test H3 and a multi-node field test would be needed.\n")
