# Architecture

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | Modules and data flow of the system and of the software pipeline. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; CSV = comma-separated values; HMAC = hash-based message authentication code; RF = random forest |
<!-- header:end -->

## System (hardware + software)
```
CAR NODE (ESP32)                                   BASE STATION (ESP32)
MPU6050 100 Hz ─┐                                  verify HMAC + counter
5x SW-420 ──────┼─> window (2.8 s) ─> 14 features  ─> signed ACK
NEO-6M GPS ─────┘      │                                │
                       ├─> rule engine (severity)        ├─> dashboard / ThingSpeak
                       ├─> RF model  (crash prob)        ├─> event log (dataset)
                       └─> direction (first 60 ms)       └─> responder alert
                  cancel window (5-10 s by severity)
                  sign (HMAC-SHA256/64 + counter) ─> LoRa 433 MHz, duty-cycle token bucket
```

## Software modules (`src/crashguard/`)
| Module | Responsibility | Input → Output |
|---|---|---|
| `data.py` | Download, verify, load VZCrash | HF dataset → `data/processed/events.parquet` |
| `features.py` | Windowing + 14 features | events → `features.parquet` |
| `split.py` | Group-held-out splits | features → split indices |
| `models.py` | Train and evaluate the five models over 5 seeds | features → `results/` |
| `export_c.py` | RF → C header, equivalence test | model → `firmware_export/` |
| `packet.py` | 97-byte alert + ACK encode/decode, HMAC | dict ↔ bytes |
| `verifier.py` | Reference base-station verifier, counter store | bytes → accept/reject |
| `attacks.py` | Attack suite | → `tables/attacks.csv` |
| `lora.py` | Airtime, duty-cycle budget | params → ms, alerts/h |
| `delivery_sim.py` | Event-driven delivery simulation | policy, loss → delivery stats |
| `results.py` | Single writer for `results.json` with origin labels | any → json |
| `plots.py` | Shared figure style | |
| `report.py` | Builds `report/software_results.md` | results.json → md |
| `merge/ingest_hardware.py` | Hardware CSV ingest + E1–E8 analysis | `data/hardware` → results |

## Rules for code
- Only `results.py` writes `results.json`. Each entry has the form `{"name","value","unit","origin","source_file","notes"}`.
- Analysis code must not hard-code numbers, except design constants from the specs (packet sizes, policy timings).
