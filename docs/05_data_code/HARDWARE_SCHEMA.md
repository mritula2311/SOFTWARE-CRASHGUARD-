# Hardware data files (`data/hardware/`): author-supplied, read-only

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | Schema of the hardware data files (author-supplied, read-only). |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | CoAP = Constrained Application Protocol; HTTP = Hypertext Transfer Protocol; LoRa = long-range radio modulation; MQTT = Message Queuing Telemetry Transport; RAM = random-access memory; TCP = Transmission Control Protocol |
<!-- header:end -->

## Already measured (included)
| File | Content |
|---|---|
| `protocols.csv` | HTTP/MQTT/CoAP results from the progress report (ranges as min/max) |
| `tcp.csv` | TCP connection measurements |
| `lora_packets.csv` | LoRa test and telemetry packet observations |
| `lora_gateway.csv` | Gateway counter snapshots |

## To be collected (firmware v2 event log)
`hw_events.csv`: one row per event:
- `event_id`, `experiment` (H1–H6, see EXPERIMENTS.md; older logs with E-IDs are mapped), `true_label` (crash / non_crash), `true_side` (F/R/L/Rt/V), `distance_m`, `walls` (`designed_severity` and `speed_setting` may stay in the log but are not analysed: severity against impact strength was dropped from the plan)
- `rule_sev`, `ml_prob`, `pred_side`, `angle_deg`, `peak_g`
- `sw_fl`, `sw_fr`, `sw_ml`, `sw_mr`, `sw_rl` (0/1 fired within −100/+300 ms), `sw_first`, `sw_pre_edges`
- `classify_us`, `ml_us`, `verify_us`, `airtime_ms`, `ack_rtt_ms`, `first_tx_to_ack_ms`, `trigger_to_ack_ms`, `retries`, `delivered` (0/1), `rssi`, `snr`

`hw_windows.csv`: raw windows: `event_id`, `t_ms`, `ax`, `ay`, `az`, `gx`, `gy`, `gz` (in g and rad/s).

`hw_attacks.csv`: `case`, `expected`, `observed`.

`hw_memory.csv`: `item` (flash/RAM), `bytes`, from the Arduino compile report.

Rules:
- Units are in the column names or in this file.
- Missing values are left empty, never filled with zero.
- Transmitter and gateway counts must both be logged so that a delivery ratio can be computed.
