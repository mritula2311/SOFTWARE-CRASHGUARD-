# Prompt for Claude Code — CrashGuard software pipeline

<!-- header:start -->
| Field | Value |
|---|---|
| Status | archived (superseded) |
| Date | 2026-11-10 |
| Owner | Mritula S |
| Scope | The initial build prompt for the software pipeline. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN |
| Replaced by | `CLAUDE.md and docs/00_overview/PRD.md` |
| Reason | their content is in the project rules and the PRD |
| Abbreviations | ACK = acknowledgement frame; CRC = cyclic redundancy check; CSV = comma-separated values; DUMMY = synthetic placeholder data (tests only); ESP32 = a Wi-Fi microcontroller family (Espressif); IMU = inertial measurement unit; LoRa = long-range radio modulation; PDF = Portable Document Format; RAM = random-access memory; SF = spreading factor (LoRa); SW-420 = a vibration switch module |
<!-- header:end -->

Paste everything below the line into Claude Code, started in an empty project folder.

---

You are building the complete **software and data-science part** of CrashGuard, an ESP32-based vehicle crash detection and LoRa alert system (B.Tech final project, journal-paper target). I will merge your outputs with hardware measurements I collect separately. Work autonomously, step by step, and keep going until every deliverable below exists and passes its checks.

## 0. Non-negotiable rules

1. **Never invent results.** Every number in any table, figure or text must come from code you ran in this session. If something cannot be run (no data, no hardware), write `NOT RUN` and say why. No placeholder metrics, no "typical" values.
2. **Label every result's origin** in the output files: `MEASURED_SOFTWARE` (computed from a dataset), `SIMULATED` (from a simulation with stated assumptions), `ANALYTICAL` (from a formula), or `NOT_RUN`. Hardware results are not yours to produce.
3. **Fixed seeds** (seed = 42, plus 5 repeated seeds for any stochastic comparison) and a `requirements.txt` with pinned versions. Everything reproducible from one command: `make all`.
4. **Split by vehicle/trip, never by random window.** If the dataset has no vehicle or trip ID, say so in the report and use the most independent grouping available (for example by device or by time block), and state this limitation.
5. Write in simple, plain language in all reports. State limitations honestly. Do not say "first" or "novel" in any generated text.
6. Dataset licence is CC BY-NC 4.0: non-commercial use only, cite the source. Put this in the README.

## 1. Dataset

- **Dataset (Hugging Face):** https://huggingface.co/datasets/vzc-research-chapter/VZCrash
- **Paper:** https://arxiv.org/abs/2606.06074 (PDF: https://arxiv.org/pdf/2606.06074)
- What I believe about it (from my notes, **verify before relying on it**): about 190,000 events, 31,090 verified crashes; IMU at 100 Hz in units of g; axes X forward, Y left, Z up; binary crash / non-crash labels; no impact-direction or severity labels.

Steps:
1. Download with `huggingface_hub` / `datasets` into `data/raw/` (not committed to git). If access fails, stop and tell me exactly what failed and what I should download by hand; do not substitute fake data.
2. Read the dataset card and the paper. Write `docs/dataset_facts.md` listing: file format, columns, units, sampling rate, window length, label definition, any vehicle/trip/device ID, class balance, and licence. Mark each fact `CONFIRMED_FROM_DATA` or `CONFIRMED_FROM_CARD/PAPER`. If anything differs from my beliefs above, say so clearly at the top of the file.
3. Run data-quality checks (missing values, constant signals, outliers, duplicated events, sampling-rate consistency) and save a short summary.

## 2. Features and models

1. Build fixed windows around the trigger (target 2.8 s at 100 Hz; adapt to what the dataset provides and document it). Compute **14 window features** and document each one in `docs/features.md` (suggested: peak |a|, peak along each axis, RMS, jerk peak, energy, duration above threshold, zero-crossings, kurtosis, post-impact quiet level, and similar). Mark which features are **scale-free** (independent of absolute g level, for example ratios and normalised shapes) as the `scale_free` subset.
2. Train and compare, on vehicle/trip-held-out splits:
   - Random forest, 15 trees, max depth 6 (the model that must fit on an ESP32).
   - Larger random forest (for reference).
   - Logistic regression.
   - Gradient-boosted trees (LightGBM or sklearn).
   - A simple rule-based detector (peak threshold plus duration), tuned on the training split only.
3. Metrics on the held-out test set: average precision, precision, recall, F1, false-positive rate at a fixed recall of 0.95, ROC-AUC, confusion matrix, precision-recall curve. Report mean ± std over 5 seeds. Choose the decision threshold on a validation split, never on the test set.
4. Run an ablation: all 14 features vs the `scale_free` subset only.
5. Error analysis: list the 20 most confident false positives and false negatives (event IDs only, plus the feature values) and describe common patterns in plain language.
6. Calibration check (reliability curve) for the 15-tree model.

## 3. Microcontroller export and footprint

1. Export the 15-tree depth-6 model to **plain C** (`firmware_export/crashguard_rf.h`): no dynamic memory, integer or float thresholds in `const` arrays, one `predict_prob(const float features[14])` function.
2. Verify the C code gives **identical** predictions to the Python model on the whole test set (compile with gcc, run, compare). Report the maximum difference.
3. Estimate flash and RAM from the compiled size (`size` output) and the number of nodes. These are `ANALYTICAL` or host estimates, not ESP32 measurements. Say so.
4. Create a tiny Arduino sketch `firmware_export/benchmark_rf.ino` that I can flash to the ESP32 to time `predict_prob` over 1,000 calls and print microseconds. Do not report any ESP32 timing yourself.

## 4. Alert protocol and security (software-only checks)

1. Implement in Python, with unit tests, the 97-byte alert packet and the signed ACK: fields for node ID, event ID, monotonic counter, timestamp, severity, impact side, angle, latitude, longitude, peak g, model probability, and a 64-bit truncated HMAC-SHA256 tag. Document the byte layout in `docs/packet_format.md`.
2. Write an **attack test suite** that sends these cases to a Python reference verifier and records accepted/rejected: valid, forged tag, tampered field, replayed packet, old counter, spoofed ACK, base reboot with counter persisted, base reboot with counter lost. Save the table. This validates the **design**, not the firmware; label it `SIMULATED`.

## 5. LoRa airtime and delivery simulation

1. Implement the Semtech LoRa airtime formula. Parameters are inputs (SF, bandwidth, coding rate, preamble, header, CRC). Default SF7, 125 kHz, CR 4/5, preamble 8, explicit header, CRC on. Reproduce: a 97-byte payload at SF7 should be about 169 ms; if it is not, find out why.
2. Compute the maximum alerts per hour under a 10% duty-cycle limit for SF7–SF12 (`ANALYTICAL`).
3. Simulate the severity-aware delivery policy over a range of packet loss probabilities (0–60%) with a token-bucket duty-cycle limiter:
   - Low: cancel window 10 s, 3 tries then stop.
   - Moderate: 10 s, retries for about 2.5 min.
   - Severe: 10 s, retry until ACK.
   - Critical: 5 s, retry until ACK.
   - Heartbeats use only spare airtime budget.
   Compare against a naive policy (fixed 3 retries, no priorities). Report delivery rate, time to ACK, and whether critical alerts still get through when the budget is nearly used up. The loss model is an assumption: state it, and label all results `SIMULATED`. These curves will later be compared with my measured hardware delivery rates.

## 6. Hardware-merge interface

I will supply hardware logs later. Make this easy:
1. Define the expected CSV schemas in `docs/hardware_schema.md` and write `merge/ingest_hardware.py` that reads them if present and prints `NOT_RUN` if absent. Schemas:
   - `hw_events.csv`: event_id, true_label, true_side, raw window columns (t_ms, ax, ay, az, gx, gy, gz), sw_fl, sw_fr, sw_ml, sw_mr, sw_rl, rule_sev, ml_prob, classify_us, ml_us, verify_us, airtime_ms, ack_rtt_ms, trigger_to_ack_ms, retries, rssi, snr, distance_m.
   - `hw_protocols.csv`: protocol, latency_ms, throughput_bps, packet_bytes, loss_pct.
2. When `hw_events.csv` is present, the script must run: the transfer test (train on VZCrash, test on my data, all features vs `scale_free`), the crash/no-crash metrics, the 5-class impact-side confusion matrix and angle error, severity vs peak-g correlation, delivery rate by distance and severity, the latency breakdown, and the SW-420 ablation (false alarms and misses with vs without vibration confirmation). Test the script on a **clearly labelled synthetic dummy file** kept in `tests/dummy/`, and make sure no output from the dummy file can be mistaken for a real result (watermark every figure from it with "DUMMY DATA").

## 7. Outputs

```
crashguard-software/
  README.md                 how to run, licence and citation, limitations
  Makefile                  make data / features / train / export / security / lora / report / all
  requirements.txt
  src/  tests/  merge/  firmware_export/  docs/
  results/
    results.json            every number, each with its origin label
    tables/*.csv            one CSV per table
    figures/*.png and *.pdf (dpi 300, colour-blind-safe, axes labelled with units)
  report/
    software_results.md     plain-language results section for the paper
```

Figures to produce: class balance; precision-recall curves for all models; confusion matrix for the 15-tree model; feature importance; all-features vs scale-free comparison; calibration curve; model size vs performance; LoRa airtime vs payload and SF; alerts per hour at 10% duty; delivery rate vs packet loss for the policy vs naive; time to ACK by severity; the attack test table as an image.

`report/software_results.md` must contain: what was run, the tables, the figures with captions, a section "What these results do and do not show", and a section "Still needed from hardware".

## 8. Checks before you finish

- `make all` runs from a clean checkout; all tests pass.
- Every number in `report/software_results.md` appears in `results/results.json` with the same value.
- No file contains a metric labelled as measured that was not computed by code in the repo.
- The C model matches Python predictions exactly (or you report the difference).
- Give me a final summary: what ran, what did not, anything about the dataset that contradicted my assumptions, and the single most important thing I should check by hand.

Work in small, committed steps. If you hit a decision that could change the science (for example, the dataset has no vehicle IDs), choose the most conservative option, write it in `docs/decisions.md`, and continue.
