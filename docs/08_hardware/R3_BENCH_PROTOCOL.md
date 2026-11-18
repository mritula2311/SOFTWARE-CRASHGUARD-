# Bench protocol for the two-stage alert (R3 and D4)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Bench protocol, logging hooks, parser and pre-written outcome sentences for the two-stage alert; hardware row NOT_RUN. |
| Evidence labels used | SIMULATED, NOT_RUN |
| Abbreviations | CSV = comma-separated values; DUMMY = synthetic placeholder data (tests only); ESP32 = a Wi-Fi microcontroller family (Espressif); LoRa = long-range radio modulation; RSSI = received signal strength indicator; SF = spreading factor (LoRa); SNR = signal-to-noise ratio |
<!-- header:end -->

Status of the hardware row of the paper: **NOT_RUN** (`rd.x4.hw_row`). The author runs this protocol; the code here only logs and parses. The parser (`src/crashguard/rd_bench.py`) is tested on a synthetic fixture (`tests/redesign/test_rd_bench.py`, DUMMY DATA); the logging hooks (`firmware_rd/bench/cg_bench_log.h`) were checked for line format on a host stub only and **have not been compiled for the ESP32** (no ESP32 toolchain here).

## 1. Set-up
- One ESP32 car node (accelerometer, LoRa radio) and one base (LoRa radio, listening). Same radio settings on both: SF7, 125 kHz, coding rate 4/5, the frequency used in the earlier bench tests; write them in the run sheet.
- Frames: provisional alert (the frame under test: the 14-byte flash of R3, or the 24-byte frame with an 8-byte tag of D4), confirm (97 bytes), authenticated CANCEL (14 bytes, three transmissions), ACKs as in `docs/01_protocol/PACKET_FORMAT.md`.
- **Clock alignment.** A wire between one GPIO pin of the base and one of the car. Before every tap the base raises the pin; both devices log `SYNC` in the pin interrupt with the captured `micros()`. The parser maps car time to base time per trial from the two `SYNC` values, so no assumption is made about the radio path. If a wire is impossible, stop and write to the supervisor: the alternative (round-trip estimate) adds an error of the order of the airtime and is not accepted for the latency clause.
- Distances: **10 m** line of sight, and **behind one wall** (record the wall type and the distance). Same antennas and orientation in both.
- Taps: for each distance, **30 taps above the trigger threshold** and **30 below** (60 per distance, 120 in all). Mix the order at random (draw the order with a seeded generator and keep the file). Use a calibrated tapping tool or a fixed drop height; record it. Write the operator label (above or below) in `taps.csv` *before* looking at the logs.

## 2. What is logged (one CSV line per event, `trial,role,event,t_us,len,sf,rssi,snr,extra`)
Car: `SYNC`, `TRIGGER` (with peak in mg), `PROV_TX_START`, `PROV_TX_END`, `PROV_ACK_RX` (RSSI, SNR), `CONFIRM_TX_START`, `CONFIRM_TX_END`, `CANCEL_TX_START`, `CANCEL_TX_END`, `FINAL_ACK_RX`, `ACK_TIMEOUT`.
Base: `SYNC`, `PROV_RX` (RSSI, SNR), `PROV_ACK_TX_START/END`, `CONFIRM_RX`, `CANCEL_RX`, `FINAL_ACK_TX_START/END`.
`micros()` wraps every 71.6 minutes; the parser unwraps it. Save the serial output of each device to a file without editing it. Do not edit, trim or "clean" a log; a bad trial is marked in `taps.csv` (`valid=0` with a reason) and stays in the file.

## 3. From logs to tables
```
python -m crashguard.rd_bench car.csv base.csv taps.csv results/tables/hw_r3
```
The summary has, per distance: provisional alerts sent, retractions and the retraction share (R3 clause b, bound 20%), the median of (confirm arrival minus provisional arrival) with a bootstrap interval over trials (R3 clause a: the provisional alert arrives earlier; the simulation gave 1.87 s at loss 0), the extra airtime of the two-stage scheme over a confirm-only counterfactual computed from the logged frame lengths and SF (R3 clause c, bound 40%; D4 H-D4a bound 25%), and the share of tap-above trials delivered within 10 s by the provisional alert and by the confirm. Intervals are over trials, the unit of this bench run.

## 4. Pre-written reading of the outcomes (fixed now, before any log exists)
Let a "clean" run have at least 25 valid above-trigger trials and 25 valid below-trigger trials per distance.
- **A. Clean run; provisional arrives earlier by at least 0.8 s (interval above 0.8 s); retraction share below 20%; extra airtime below 40%; both distances.** Sentence: "In a bench test with one car node and one base (60 taps per placement, 10 m and behind one wall), the provisional alert reached the base a median of X s [lo, hi] before the confirmation; Y% of provisional alerts were retracted; the extra airtime was Z%. This is a bench result with one pair of radios and does not show behaviour on a road."
- **B. Timing clause met, retraction or airtime clause not met.** "The provisional alert arrived a median of X s [lo, hi] before the confirmation, but the retraction share (Y%) or the extra airtime (Z%) was outside the bound set before the test; the two-stage alert is therefore not recommended in this form."
- **C. Timing clause not met (interval includes 0.8 s or lower).** "In the bench test the provisional alert did not arrive at least 0.8 s before the confirmation (median X s [lo, hi]); the simulated gain was not reproduced."
- **D. Behind-the-wall run fails but 10 m passes.** Report both rows separately: "The result held at 10 m (…) and did not hold behind one wall (…)."
- **E. Not a clean run (fewer valid trials, missing sync, edited logs).** "The bench test did not yield enough valid trials to test the two-stage alert; no result is reported." The simulated results stay SIMULATED.
- **Always add:** the radio settings, the number of valid and invalid trials, and that clocks were aligned with a wired pulse.

## 5. What this does not test
Impact detection in a crashed vehicle, antenna placement in a car body, interference from other transmitters, multiple vehicles, long distances, battery or temperature. A bench tap is not a crash.
