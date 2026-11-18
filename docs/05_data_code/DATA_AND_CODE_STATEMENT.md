# Data and code statement

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Licence split, data sources, what was and was not read, and how to obtain the data. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED_HW_FORMAT, SIMULATED, ANALYTICAL, HARDWARE, NOT_RUN |
| Abbreviations | DOI = digital object identifier; HTTP = Hypertext Transfer Protocol; ISO = International Organization for Standardization; NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Software-only results. The author's hardware logs (`data/hardware/`) were not read for any result here.

## Licence split (read this before the tables)

- **Code** (`src/`, `tests/`, `scripts/`, `Makefile`, `crashclip/`, `merge/`): Apache License 2.0, copyright 2026 Mritula S (`LICENSE`, `NOTICE`). The licence covers code only.
- **VZCrash-derived artefacts** (the surrogate-generator parameters of block F0, audit lists, event hashes and identifiers): CC BY-NC 4.0 with attribution to the VZCrash authors (Bianconcini et al., arXiv 2606.06074). They carry their own licence file in the folder that holds them.
- **Data of third parties** keep their own terms and are not redistributed here (table below).
- No DOI exists for this repository. `CITATION.cff` and `.zenodo.json` hold metadata only.

## Datasets

| Dataset | Used for | Licence | Redistributed here? |
|---|---|---|---|
| VZCrash (Bianconcini et al., arXiv 2606.06074; Hugging Face `vzc-research-chapter/VZCrash`) | detector, duplicate audit, leakage sensitivity, X1 to X4 and X8, surrogate generator | **CC BY-NC 4.0.** Author reply of 2026-11-12 (user-supplied statement, recorded in `docs/07_log/DECISIONS.md`): the dataset is released under CC BY-NC 4.0, the downloaded copy corresponds to Hugging Face revision `42e1482d005c0e545379d6cfa4939486c9fe4249`, and the authors allow event identifiers or hashes to be cited in a paper. Non-commercial use; cite the paper. | **No.** `data/raw/` is git-ignored. `results/paper/vz_audit_cross_split_groups.csv`, `results/tables/vz_audit_*.csv` and `release/vzcrash_audit_for_authors/` hold event identifiers, split and class labels, vehicle-size labels and one-way SHA-256 hashes; they hold no samples and are CC BY-NC 4.0. |
| NHTSA Vehicle Crash Test Database (public API, https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/swagger-ui/index.html) | N13, N14, T13a, T13c, sensor selection, X5 to X7, synthetic pulse generator fits | The data.gov catalogue entry was opened and its rights field reads "public". The nhtsa.gov terms pages returned HTTP 403, so **the NHTSA terms are not verified**. The data keep their own terms; the Apache-2.0 licence does not apply to them. | **No raw files.** The ISO MME zips and metadata are cached in `data/raw/nhtsa/` (git-ignored). Derived tables list test numbers, make, model, year and computed values (`results/tables/`). The 5,000-pulse synthetic file is generated, not NHTSA data (it is fitted to summary ranges of NHTSA pulses). |
| Accelerometer data sheets (Analog Devices, InvenSense/TDK, STMicroelectronics, Kionix/ROHM) | sensor table | Manufacturers' documents; copyright of their owners. | **No.** Local copies in `data/raw/refs/` are git-ignored; the repository stores the values read, with address, date and revision (`docs/05_data_code/SENSOR_DATASHEETS.md`, `docs/06_references/REFERENCES.md`). |

## What is released

Code (Apache-2.0), generated tables and figures (`results/`), documents (`docs/`), and `results/results.json` with the origin label of every number (MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, HARDWARE, NOT_RUN). Citation: `CITATION.cff` (metadata only; no DOI is claimed).

## How to rebuild

`docs/05_data_code/REPRODUCE_FINISH.md` (one command per table and figure) and `docs/05_data_code/REPRODUCE.md` (full pipeline). Seeds: 42, and 0 to 4 for repeated runs. Pinned versions: `requirements.txt` and `requirements.lock`.

## Not available or not done

See `docs/07_log/NOT_RUN.md` (every NOT_RUN item with its reason, and every source that could not be opened).

## Simulated hardware-format files (combined run, 2026-11-14)

`data/simulated_hardware/` holds log files in the format of the hardware logs (sensor logs of H1 and H2; protocol logs of H3, H4, H5 and H7; `event_summary.csv`). They were SIMULATED by `hwsim.py` (seed 20261114, numpy only) from stated sensor and link models; they are not measurements and are labelled SIMULATED_HW_FORMAT wherever a result uses them. The author supplied no hardware log for this run, and `data/hardware/` was not read. A SHA-256 manifest is in `data/simulated_hardware/MANIFEST.sha256`; the fault variants of Part S are made by `src/crashguard/hwsim_v2.py` (variants and seeds in `docs/03_results/SIMHW_VARIANTS.md`). The files are meant to be overwritten by real captures under the same names.
