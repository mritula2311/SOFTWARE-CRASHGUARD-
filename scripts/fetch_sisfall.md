# Fetching SisFall (not redistributed with this artefact)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Where to obtain SisFall (not redistributed), where to put it, and what the code expects: archive hash, file list and counts. |
| Evidence labels used | none (this file reports no result) |
<!-- header:end -->

SisFall is not part of the repository, its history or any release archive. It is available from its authors (Sucerquia, López and Vargas-Bonilla, "SisFall: A Fall and Movement Dataset", Sensors 17(1):198, 2017, doi 10.3390/s17010198). No data licence is stated by the authors, so the files are not redistributed here. The author of this repository used a Zenodo copy (record 22212281, doi 10.5281/zenodo.22212281, deposited 2026-08-31); that record states CC BY 4.0 but lists no creators, and the licence has not been confirmed with the authors, so it is not relied on.

Use is limited to the duplicate audit of the study (hypothesis H-L10a, `python -m crashguard.r5_l10 run`, keys `r5.l10.sisfall.*`). Nothing else in the paper depends on SisFall.

## Where to put it

`data/raw/r5_l10/sisfall.zip` (the path is git-ignored; `data/raw/` is never committed).

## What the code expects (from `src/crashguard/r5_l10.py` and the stored keys)

| Item | Expected |
|---|---|
| Archive SHA-256 of the copy that was used | `dd0f9cf14134e95be79d9962855ba3bded13a4dedb3fa96fc265277d459aa6b3` (`docs/05_data_code/DATA_SOURCES.md`; the code checks the leading 8 characters, `dd0f9cf1`) |
| Archive entries | 4,700, under `SisFall_dataset/`: `Readme.txt`, `Supplementary.pdf`, one folder per subject (`SA01` ... and `SE01` ... ) holding trial files, and 39 `desktop.ini` files |
| Trial file names | `<activity>_<subject>_R<repeat>.txt`, for example `D01_SA01_R01.txt` (activities `D01` to `D19` for daily living and `F01` to `F15` for falls) |
| Files used | the trials whose name starts with `D` or `F` in a folder starting with `S` (`SA` and `SE` subjects): **4,505 files** (`r5.l10.sisfall.n_files`) |
| Parsing | comma-separated rows ending in `;`, the three leading columns (ADXL345 raw counts) |
| Windows | 200 samples, step 100: **153,705 windows** (`r5.l10.sisfall.n_windows`) |
| Result to compare | 0 byte-identical trials across subjects, 0 identical windows across the random split and across the subject split (`r5.l10.sisfall.*`) |

A copy from another source can differ in file count or bytes; if the SHA-256 does not match, the code stops, and the stored `r5.l10.*` values were computed on the copy above only.
