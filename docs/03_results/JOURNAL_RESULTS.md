# Journal push: results summary (generated from `results/results.json`)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-13 |
| Owner | Mritula S |
| Scope | Results of the journal push (generated). |
| Evidence labels used | MEASURED_SOFTWARE, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; AP = average precision; CSV = comma-separated values; EN = European standard; ESP32 = a Wi-Fi microcontroller family (Espressif); FMVSS = Federal Motor Vehicle Safety Standards; HTTP = Hypertext Transfer Protocol; I2C = inter-integrated circuit bus; LoRa = long-range radio modulation; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; PNG = Portable Network Graphics; SPI = serial peripheral interface; SW-420 = a vibration switch module |
<!-- header:end -->

Branch `journal-push`, software only (`data/hardware` is not read). Origin labels: MEASURED_SOFTWARE unless stated. Preregistration: `docs/02_preregistration/PREREGISTRATION_V3.md`; decisions and mistakes: `docs/07_log/DECISIONS.md`; claims with allowed wording: `docs/03_results/CLAIM_EVIDENCE.md`.

## One line per task

- **T13a (held-out NHTSA modes).** 739 records from 1,340 candidate tests in 326 make-and-model groups. The 80% criterion is reached in **0** cells (best lower end 0.794 at +-200 g and 200 Hz; 0.775 at +-64 g and 200 Hz). Fill + ridge does not beat the spline at +-16 g (1.31 [-1.41, 4.37] points); it does at +-32 g.
- **T13c (NHTSA near-duplicates).** 2 pairs among the 176 (the same test channel counted twice), 0 between the held-out records and the 176. The +-16 g result of N14 is unchanged without the flagged tests (exploratory).
- **Block 2 (sensor selection).** 30 of 99 configurations meet the rule on the 176 tests; the smallest range is +-64 g; no +-16 g part meets it; no configuration meets it on the held-out modes. Tables: `results/paper/tab_sel_*`, figure `sel_share_vs_range`.
- **V1 (independent audit).** Every stored count is reproduced (217 groups, 1,305 flagged windows); **V2** the 'a fifth' (22.3% of triggered test windows) and 'about 5%' figures use different denominators; **V3** `docs/04_audits/VZCRASH_AUDIT.md`; **V4** near-duplicate removal lowers recall at the 1% target by 0.0727 [0.0641, 0.0809].

## One line per hypothesis (Holm over the seven)

| Hypothesis | Verdict | Raw p | Holm p | Statement |
|---|---|---|---|---|
| H-X1 | **NOT SUPPORTED** | 0.001 | 0.007 | X: the 16-bit fixed-point forest loses at most 0.005 AP and cuts the flash estimate by 30% (preregistered, Holm-corrected) |
| H-X2 | **NOT SUPPORTED** | 1.000 | 1.000 | X: a cheap-trigger cascade raises the share of crashes passing the trigger by 2 points over a 2 g threshold at an equal non-crash trigger rate |
| H-X3 | **NOT SUPPORTED** | 0.275 | 1.000 | X: group-aware training raises recall at the 1% false-alarm target on the strict test set by 1 point |
| H-X5 | **NOT SUPPORTED** | 1.000 | 1.000 | X: a +-16 g sensor with fill + ridge preserves the rank of delta-V (Spearman at least 0.90, lower end 0.85) |
| H-X6 | **SUPPORTED** | 0.001 | 0.007 | X: a lower-bound-anchored estimator lowers the 90th-percentile delta-V error by 5 points against fill + ridge at +-16 g |
| H-X7 | **NOT SUPPORTED** | 1.000 | 1.000 | X: a real two-part pair reaches 0.80 within +-10% where neither part alone does (preregistered fusion rules) |
| H-X8 | **NOT SUPPORTED** | 1.000 | 1.000 | X: a sequential rule decides 100 ms earlier than the early-exit rule at equal or better recall |

X4 (labels): the supplied files carry only crash, near_miss and normal_driving and the vehicle size; no direction or severity label (`x.x4.*`).

## Negative results (reported in full)

- N13 is not confirmed on other crash modes (T13a); fill + ridge does not beat the spline at +-16 g there; the ridge fitted on the 176 does not carry over (13.7% median for fill without the ridge against 18.0% with it).
- X5: the order of severity is not preserved at +-16 g (Spearman 0.751 [0.678, 0.805]; the plain estimate ranks better, 0.841 [0.791, 0.875]); N13 is strengthened.
- X1: the 16-bit forest keeps AP but the flash estimate falls only 22.2% in the existing layout.
- X2: the cascade is the 2 g threshold itself in most held-out categories; no gain.
- X3: group-aware training changes the 1% recall on the strict set by 0.0011 [-0.0022, 0.0045]; duplicates in training do not explain the gap.
- X7: no preregistered pair and fusion rule reaches a lower end of 0.80; a wide-mask rule defined afterwards does for 3 combinations (exploratory).
- X8: earlier at the 1% target, slower and lower recall at 5%; the recall gain over the single forest is an ensemble effect.

## The one supported hypothesis

H-X6: at +-16 g on split R the lower-bound-anchored estimator has a 90th-percentile error of 27.5% against 58.5% for fill + ridge (gain 31.0 [20.2, 37.8] points, raw p 0.001, Holm 0.007). Cautions: the gain has its interval above zero on split A only among G, A, O; the median is not better than the tail-aware model; the unanchored boosting model accounts for part of the gain (`x.x6.R.r16.paired.GBR_minus_ANC.p90`); the estimator over-corrects the 2 tests where the plain estimate already exceeds the reference.

## NOT_RUN items and why

- `export.benchmark_us_per_call`: needs the ESP32; sketch is built, not yet measured
- `x1.A.r16.angle_err.oblique_magnitude.median_deg`: 3 held-out oblique tests, fewer than 10
- `x1.A.r32.angle_err.oblique_magnitude.median_deg`: 3 held-out oblique tests, fewer than 10
- `x1.A.r64.angle_err.oblique_magnitude.median_deg`: 3 held-out oblique tests, fewer than 10
- `x1.G.r16.angle_err.oblique_magnitude.median_deg`: 2 held-out oblique tests, fewer than 10
- `x1.G.r32.angle_err.oblique_magnitude.median_deg`: 2 held-out oblique tests, fewer than 10
- `x1.G.r64.angle_err.oblique_magnitude.median_deg`: 2 held-out oblique tests, fewer than 10
- `x2.limit.tti_pelvg.status`: TTI(d) and pelvis limits of the old SID dummy are not in the current FMVSS 214 text that was opened; no share against them is computed
- `ua.b1.fill_ridge.f200.r16`: the fill and ridge constants (pulse-fit offsets in samples, saturation level, ridge strength) were tuned at 100 Hz and are not re-tuned at 200 Hz; the plain estimate is reported at 200 Hz instead
- `ua.b1.fill_ridge.f200.r32`: the fill and ridge constants (pulse-fit offsets in samples, saturation level, ridge strength) were tuned at 100 Hz and are not re-tuned at 200 Hz; the plain estimate is reported at 200 Hz instead
- `ua.b1.fill_ridge.f200.r64`: the fill and ridge constants (pulse-fit offsets in samples, saturation level, ridge strength) were tuned at 100 Hz and are not re-tuned at 200 Hz; the plain estimate is reported at 200 Hz instead
- `s12.ATT.design.L1_no_ack_in_terminal_state`: not checked in this bound set
- `s12.ATT.strict_anti_replay.L1_no_ack_in_terminal_state`: not checked in this bound set
- `s12.REBB.design.L1_no_ack_in_terminal_state`: not checked in this bound set
- `s12.REBB.base_no_persistence.L1_no_ack_in_terminal_state`: not checked in this bound set
- `s12.REBC.design.L1_no_ack_in_terminal_state`: not checked in this bound set
- `s12.REBC.car_no_persistence.L1_no_ack_in_terminal_state`: not checked in this bound set
- `hw.lora_pdr`: the transmitter total is missing, so a delivery ratio cannot be computed
- `hw.H1`: impact side (10 hits x 4 sides + 10 vertical drops): hw_events.csv not found
- `hw.H2`: crash vs not-crash (H1 hits + 30 non-crashes) and transfer from VZCrash: hw_events.csv not found
- `hw.H3`: LoRa delivery (20 alerts each at 10, 50 and 100 m, optional wall): hw_events.csv not found
- `hw.H4`: security (forged, tampered, replay, spoofed ACK, base reboot, ACK-lost retry; 3 tries each): hw_events.csv not found
- `hw.H5`: edge cost (compile report + logged microseconds): hw_events.csv not found
- `hw.H6`: SW-420 ablation (re-analysis of H1 and H2): hw_events.csv not found
- `hw.H2.transfer`: transfer from VZCrash needs hw_events.csv and hw_windows.csv: hw_events.csv not found
- `t13.second_dataset.analysis`: searched 2026-11-11 for a second public vehicle crash-test or crash-pulse set; the candidates found were: the Bridge of Knowledge dataset of vehicle centre-of-gravity accelerations from EN 1317 TB32 impacts (page blocked by an access check, not opened), the Fr
- `t6.external_scale`: no delta-V severity scale from an opened source: the candidate pages (Traffic Injury Prevention articles, National Academies report, BASt, SWOV) returned HTTP 403, 404 or an access check; snippets mention categories below 24, 24 to 48 and above 48 km/h but wer
- `t3.r64.s0p1.break_even_ratio_hi`: upper end infinite: some resamples have no mis-triage gain
- `t3.r64.s0p3.break_even_ratio_hi`: upper end infinite: some resamples have no mis-triage gain
- `t3.r64.sobs.break_even_ratio_hi`: upper end infinite: some resamples have no mis-triage gain
- `t3.r64.s0p9.break_even_ratio_hi`: upper end infinite: some resamples have no mis-triage gain
- `t13.heldout.grid.criterion.min_range_g`: lowest range with a cell meeting the criterion; NOT_RUN value = no cell meets it; value not finite
- `t13.heldout.grid.criterion.min_rate_hz_at_min_range`: value not finite
- `sel.caveat.esp32_read_rate`: effective I2C or SPI read rate of each part on an ESP32 was not measured: hardware item; the study uses the datasheet output data rate

## Limitations (paragraph for the paper)

All delta-V and sensor results use NHTSA crash tests, most of which are high-speed barrier tests, through a software sensor model whose bandwidth, range, rate, resolution and noise come from data sheets or assumptions; the output rates are data sheet rates, not rates read over I2C or SPI on an ESP32 (NOT_RUN, hardware). The reference delta-V is the integral of the unclipped original-rate channel, not a measured vehicle velocity change. The held-out test modes are dominated by pole tests, and the methods fitted on the original 176 tests do not carry over to them. Two of the 176 records are the same channel counted twice. VZCrash events were selected on the device before release, its recordings contain exact and window-level duplicates across the supplied splits (audited here), and it has no vehicle identifier, so vehicle-level separation cannot be checked; its licence is CC BY-NC 4.0 (confirmed by the dataset authors on 2026-11-12, Hugging Face revision 42e1482d005c0e545379d6cfa4939486c9fe4249). Hardware results are not included. The 1% duty limit and every simulator parameter of the delivery studies are assumptions.

## Index of generated tables and figures

Tables (CSV and LaTeX in `results/paper/`): `jp_tab_t13_heldout`, `jp_tab_t13_paired`, `jp_tab_t13_grid`, `jp_tab_t13_neardup`, `tab_sel_parts`, `tab_sel_sources`, `tab_sel_study`, `tab_sel_study_all`, `jp_tab_vz_leakage`, `jp_tab_x1`, `jp_tab_x3`, `jp_tab_x5_rank`, `jp_tab_x6_anchored`, `jp_tab_x7`, `jp_tab_x8`, `jp_tab_x_verdicts`, `vz_audit_cross_split_groups.csv`. Figures (PNG at 300 dpi and PDF, 3.5 inch wide): `sel_share_vs_range`, `jp_fig_x5_rank`, `jp_fig_x6_p90`, `jp_fig_t13_range`. Commands: `docs/05_data_code/REPRODUCE_FINISH.md`.
