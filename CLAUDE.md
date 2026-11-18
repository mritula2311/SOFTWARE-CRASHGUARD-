# CLAUDE.md — instructions for Claude Code in this repo

You are building the **software and data-science part** of CrashGuard, an ESP32 crash-detection and LoRa-alert system. It is a B.Tech final-year project by Mritula S (SRIHER) and is being written up as a journal paper. Hardware results are collected separately by the author and merged later through `merge/`.

Read these before writing code, in this order:
1. `docs/00_overview/PRD.md`: what to build and what counts as done.
2. `docs/00_overview/ARCHITECTURE.md`: modules and data flow.
3. `docs/05_data_code/DATASET.md`: dataset link, licence and what must be verified.
4. `docs/02_preregistration/EXPERIMENTS.md`: every experiment, metric and figure.
5. `docs/01_protocol/PACKET_FORMAT.md`, `docs/05_data_code/FEATURES.md` and `docs/05_data_code/HARDWARE_SCHEMA.md`: exact specs.
6. `docs/06_references/NOVELTY.md`: what may and may not be claimed.

## Hard rules (read every session)
1. **Never invent results.** Every number in any output must come from code run in this repo. If something can't be run, write `NOT_RUN` and the reason. No placeholder or "typical" values, ever.
2. **Label every result's origin** in `results/results.json`. Use one of:
   - `MEASURED_SOFTWARE`: computed from a dataset.
   - `SIMULATED`: produced by a simulation with stated assumptions.
   - `ANALYTICAL`: from a formula.
   - `HARDWARE`: from the author's logs in `data/hardware/`.
   - `NOT_RUN`.
3. **Hardware numbers are the author's.** Read them from `data/hardware/*.csv`. Never edit, "clean up" or extend those files.
4. **Split by vehicle/trip, never by random window.** If there is no such ID, use the most independent grouping available and record the choice in `docs/07_log/DECISIONS.md`.
5. **Reproducibility.** Seed 42, plus seeds 0–4 for repeated runs; pinned `requirements.txt`; `make all` rebuilds everything from a clean checkout.
6. **Choose thresholds on the validation split only.** The test set is touched once per model.
7. **Wording.** Use plain, simple language in reports. Do not use the words "first", "novel" or "state-of-the-art" in generated text, and do not overstate maturity. Built-but-unmeasured items are called "built, not yet measured".
8. **Dummy data.** Anything in `tests/dummy/` is synthetic. Every figure produced from it must carry a "DUMMY DATA" watermark, and none of its outputs go into `results/`.
9. **Licence.** VZCrash is CC BY-NC 4.0: non-commercial use, and it must be cited. Never commit raw data (`data/raw/` is git-ignored).
10. **Science-changing decisions.** If something could change the science (missing labels, different sampling rate, class imbalance handling), take the conservative option, log it in `docs/07_log/DECISIONS.md` with the date and the reason, and continue.

## Working style
- Work in small steps, with one commit per completed module. Use clear commit messages.
- Write tests alongside code (`pytest`). Do not move to the next PRD milestone until the current one's tests pass.
- Make figures with matplotlib at 300 dpi, saved as both PNG and PDF. Use colour-blind-safe colours and label every axis with units.
- After each milestone, update the "Status" table in `README.md`.
- At the end of a session, give a short summary: what ran, what didn't, anything that contradicted the docs, and the single most important thing for the author to check by hand.

## Commands
```
make setup      # create venv, install requirements
make data       # download + verify VZCrash, write docs/05_data_code/DATASET_FACTS.md
make features   # windows + 14 features -> data/processed/
make train      # all models, 5 seeds -> results/
make export     # C export of 15-tree RF + equivalence test
make security   # packet + attack suite
make lora       # airtime, duty-cycle, delivery simulation
make merge      # hardware ingest (NOT_RUN if no hardware CSVs)
make report     # report/software_results.md + figures
make all        # everything above, in order
make test       # pytest
```
