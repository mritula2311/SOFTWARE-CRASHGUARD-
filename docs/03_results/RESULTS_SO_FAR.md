# Hardware results so far (from the progress report, Nov 2026)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | Hardware progress notes supplied by the author (external numbers; not read or used by software results). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; CoAP = Constrained Application Protocol; ESP32 = a Wi-Fi microcontroller family (Espressif); GPS = Global Positioning System; HTTP = Hypertext Transfer Protocol; LoRa = long-range radio modulation; MQTT = Message Queuing Telemetry Transport; RSSI = received signal strength indicator; SNR = signal-to-noise ratio; SX1278 = a 433 MHz LoRa radio chip; TCP = Transmission Control Protocol |
<!-- header:end -->

## Protocols (ESP32 over Wi-Fi; MQTT via the HiveMQ public broker)
| Metric | HTTP | MQTT | CoAP |
|---|---|---|---|
| Latency | 2–3 ms | 1 ms | 1 ms |
| Throughput | 405–792 bps | 1184–1272 bps | 560–632 bps |
| Packet size | 152–198 B | 148–159 B | 70–79 B |
| Loss | 0% | 0% | 0% |

TCP: connect 40 ms, average latency 2 ms, 78 B, 312 bps, 0% loss.

## LoRa (2× ESP32 + SX1278 Ra-02, 433 MHz)
- Test packets: sequences 7, 8, 9; 26 B; RSSI −27 dBm; SNR 9.5–10.0 dB.
- Telemetry packet: 78 B; RSSI −28 dBm; SNR 10.25 dB; payload `M|NODE01|NODE01-22|30|106343|2.023|-1.350|10.034|-0.0184|0.0048|-0.0027|10.325`.
- Gateway snapshot 1 (23 s): 5 valid, 5 unique, 0 duplicates, 2 invalid, 5 ACKs sent, 0 failed.
- Gateway snapshot 2 (108 s): 21 valid, 21 unique, 0 duplicates, 2 invalid, 21 ACKs sent, 0 failed.

## Known gaps
- No range test; no PDR (the transmitter total is missing); end-to-end ACK delivery is unverified.
- No LoRa latency or throughput measurements.
- Sensor noise and calibration are not measured. The resting |a| of about 10.3 m/s² is about 5% above g.
- GPS fix was not always available.
- Vibration-sensor count: the report says 6 and the firmware plan says 5. **Confirm.**
- No crash has been classified yet.
