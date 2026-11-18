# CrashGuard simulated hardware logs (SIMULATED, not measured)

Generated 2026-11-14 by `hwsim.py` (seed 20261114; numpy only). Run: `python3 hwsim.py OUTDIR`. Same file names and schemas as the repository's `sensor_logs/` and `protocol_logs/` (H1, H2, H3, H4, H5, H7), plus `event_summary.csv`. Every JSON file carries a `data_origin` field saying SIMULATED.

## What this is for
Validating the software pipeline end to end (parsers, window and trigger code, severity estimator, alert encoding, retry logic, security checks) on files shaped like ESP32 + MPU6050 + SW-420 + SX1278 logs, and exercising edge cases that real bench data would also have (quantisation, clipping at +-16 g, DLPF attenuation, bias, chatter, ACK loss, retries).

## What this cannot be used for
- It is not evidence of hardware performance. Do not report any number from these files as measured. Label results MEASURED_SOFTWARE (code ran on files) or SIMULATED, never "hardware".
- It does not test whether real MPU6050, SW-420 or SX1278 units behave like the models below.
- Crash-versus-non-crash separability is a consequence of the event models chosen here (see "Known design effects"), not a finding.

## Models and constants (all ASSUMPTIONS; datasheet-typical values recalled, datasheets not opened in this session)
| Part | Model |
|---|---|
| MPU6050 accel | +-16 g, 2048 LSB/g, 400 ug/rtHz noise, per-axis bias N(0, 0.03 g), 44 Hz second-order low-pass at 1 kHz internal rate, logged at 100 Hz, rounding to LSB, clip at +-16 g |
| MPU6050 gyro | +-2000 dps, 16.4 LSB/dps, 0.005 dps/rtHz noise, bias N(0, 0.6 dps) |
| SW-420 x6 | per-unit threshold U(1.5, 4.0) g on 5 Hz high-passed |a|, 20 ms latch, 0.03% per-sample chatter |
| Crash events (H1) | half-sine pulse on the impact axis, peak lognormal (median 5 g, sigma 0.45, clipped 2 to 40 g), 12 to 45 ms, ring-down 60 to 140 Hz, 12% cross-axis coupling, gyro burst; 10 per side (front, rear, left, right, vertical) |
| Non-crash events (H2) | hand tap, hard braking (0.35 to 0.85 g sustained), lift and place, ramp bump (1.8 to 4.5 g, 40 to 90 ms), rough driving (colored noise plus 1 to 3 bumps); 10 each; they deliberately overlap the weak end of the crash range |
| LoRa (H3, H7) | SX1278 433 MHz, SF7, BW 125 kHz, CR 4/5, 10 dBm; time on air from the Semtech formula (analytical): 97 B alert 169.2 ms, 26 B ACK 61.7 ms; noise floor -117 dBm (6 dB noise figure); log-distance loss (exponent 3.0, shadowing 3.5 dB, +12 dB wall, +3 dB implementation); packet success logistic around -7.5 dB SNR (width 0.9 dB); reported SNR capped near +10 dB and floored at -20 dB; retries at 600 ms timeout, up to 3 |
| H3 edge runs | 100 m behind a wall with extra attenuation 30, 34, 38 and 42 dB, emulating an attenuator or long range; delivery 1.00, 0.74, 0.06, 0.00 |
| Security (H4) | executed software model: HMAC-SHA256 truncated to 8 bytes, monotonic counter, authenticated ACK; no radio. Scenario S06 models a base that does not persist its counter (accepts an old alert after reboot); S08 a car whose counter restarts (rejected, an availability cost) |
| Edge timing (H5) | NOT a measurement: medians carried from the earlier placeholder, lognormal jitter 0.08. Lowest value; replace with real `micros()` timings |
| End-to-end (H7) | 250 ms post-trigger window plus compute, then the airtime above; 97% per-direction delivery assumed |

## Validation checks run on the output
- Rest: |a| mean 0.98 g (bias), axis noise sd about 2.5 mg; no filter start-up artefact (an artefact in the first draft was found and fixed).
- Clipping: maximum logged |a| = 16.0 g; DLPF lowers the logged peak of short pulses (front 2.8 to 16.3 g, median 4.8 g).
- Time on air computed from the formula: 169.2 ms and 61.7 ms. The earlier placeholder files implied about 324 ms for alert plus ACK and listed SNR near -1 to -3 dB at RSSI -83 to -90 dBm; with the noise floor above, that RSSI would give a high SNR, so those placeholder values were not physically consistent.
- H3 at 10, 50 and 100 m (open or wall): delivery 1.00, zero retries. Range alone does not stress the link at these distances; only the edge runs do.
- H7 trigger to ACK: about 520 ms median when delivered first time; retries add about 600 ms each.
- H4: forged tag and tampered field rejected; replayed old alert rejected; spoofed ACK fails verification at the car; replay flood 20 of 20 rejected.

## Known design effects (read before using)
- Peak |a| alone separates the simulated crash and non-crash events with AUC 0.93. That is a property of these event models.
- Bench impacts here are short (12 to 45 ms) compared with real vehicle crash pulses (about 80 to 150 ms); these logs are bench-style.
- All numeric constants should be replaced by values from real datasheets and, when available, measured logs. The files are meant to be overwritten by real captures under the same names.
