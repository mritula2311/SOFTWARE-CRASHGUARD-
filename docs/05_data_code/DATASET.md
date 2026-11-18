# Dataset

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-11 |
| Owner | Mritula S |
| Scope | Datasets used, links, licences and what must be verified. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | AP = average precision; FPR = false-positive rate; HIC = head injury criterion; IIHS = Insurance Institute for Highway Safety; IMU = inertial measurement unit; ISO = International Organization for Standardization; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; RAM = random-access memory |
<!-- header:end -->

## VZCrash (primary training data)
- Dataset: https://huggingface.co/datasets/vzc-research-chapter/VZCrash
- Paper: https://arxiv.org/abs/2606.06074 (PDF https://arxiv.org/pdf/2606.06074)
- Licence: CC BY-NC 4.0, so non-commercial use only, and the paper must be cited.

### Beliefs to verify (from project notes, NOT yet confirmed)
| Item | Belief |
|---|---|
| Size | about 190,000 events, 31,090 verified crashes |
| Signal | IMU at 100 Hz, units of g |
| Axes | X forward, Y left, Z up (the same as the CrashGuard mounting) |
| Labels | binary crash / non-crash; no severity, no impact direction |
| Paper baseline | server-side models, best AP reported as 97.56%; no microcontroller deployment |

Claude Code must confirm or correct each row in `docs/05_data_code/DATASET_FACTS.md`. **Done on 2026-11-10; several beliefs were wrong:** labels are three-class, not binary; each event is a 16 s window (1600 samples at 100 Hz, 415 events differ); gyro is in deg/s with two resolutions; there is no vehicle or trip ID; access is gated on Hugging Face. See `docs/05_data_code/DATASET_FACTS.md`.

### How the dataset is used (decided 2026-11-10, see DECISIONS.md)
- near_miss is a negative class; FPR on near_miss is reported separately.
- A firmware-style window (earliest sample above `TRIGGER_G`, 1.0 s before to 1.8 s after) is cut from the 16 s event. Events that never trigger count as predicted negative at system level. `TRIGGER_G = 2.0 g` and `MPU_RANGE_G = 16 g` are placeholders in `src/crashguard/config.py` until confirmed from firmware v2.
- 15 events with a raw peak above 16 g are dropped; signals are clipped to the sensor range.
- The supplied train / validation / test splits are used. The paper states they are separated by vehicle; the release has no vehicle ID, so this cannot be checked. A near-duplicate check found cross-split duplicates (see DECISIONS.md); the primary test set leaves them out and the supplied split is reported as a secondary result.
- Every VZCrash event was already selected on the device by threshold heuristics (paper, Section II), so our trigger is a second trigger on pre-selected events.

## Author's scale-model data (`data/hardware/hw_events.csv`)
This file will be collected with firmware v2 during experiments E1–E8. See HARDWARE_SCHEMA.md. It is the only source for impact-side and severity labels.

<!-- nhtsa:start -->

## NHTSA Vehicle Crash Test Database (severity validation)
Downloaded 2026-11-11 from the public NHTSA NRD API (https://nrd.api.nhtsa.dot.gov/nhtsa/vehicle/swagger-ui/index.html), US government data (public domain). The ISO MME zip of each test (ISO/TS 13499) is cached in `data/raw/nhtsa/` (git-ignored); accelerations are converted from m/s^2 to g. Channels: vehicle-CG accelerometer if the test has one, otherwise the front sill accelerometer, vehicle axes, status ok. The per-channel TSV links were not used (the server returned the same file for every channel of some tests). Sensor-like processing (assumed): 260 Hz front-end low-pass, clip to +-16 g, 40 Hz low-pass, resample to 100 Hz. Tests are used only if the chosen channel shows a crash pulse (peak above 5 g); 668 candidate tests were skipped for that or another reason (listed in `results/tables/nhtsa_excluded.csv`).

| Test | Kind | Vehicle | Impact speed (km/h) | Channel | Axes | Original rate (Hz) |
|---|---|---|---|---|---|---|
| 3161 | frontal | 1997.0 THOMAS CONVENTIONAL | 48.3 | VEHICLE CG | XYZ | 12500 |
| 3211 | frontal | 1999.0 ACURA 3.5 RL | 48.6 | VEHICLE CG | XY | 12500 |
| 3212 | frontal | 2000.0 MERCURY SABLE | 48.4 | VEHICLE CG | XY | 12500 |
| 3213 | frontal | 1999.0 FORD E150 VAN | 48.4 | VEHICLE CG | XY | 12500 |
| 3222 | frontal | 1999.0 CHEVROLET BLAZER | 48.6 | VEHICLE CG | XYZ | 12500 |
| 3224 | frontal | 2000.0 FORD TAURUS | 48.3 | VEHICLE CG | XY | 12500 |
| 3255 | frontal | 1991.0 DODGE CARAVAN | 32.4 | VEHICLE CG | XYZ | 12500 |
| 3259 | frontal | 1988.0 CHEVROLET PICKUP | 40.3 | VEHICLE CG | XYZ | 12500 |
| 3311 | frontal | 1999.0 MITSUBISHI MONTERO SPORT | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3312 | frontal | 1999.0 MERCEDES ML320 | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3314 | frontal | 1999.0 LEXUS RX300 | 64 | VEHICLE CG | XYZ | 10000 |
| 3315 | frontal | 1999.0 LEXUS GS400 | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3316 | frontal | 2000.0 CHEVROLET IMPALA | 63.9 | VEHICLE CG | XYZ | 10000 |
| 3317 | frontal | 2000.0 BUICK LESABRE | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3318 | frontal | 2000.0 DODGE INTREPID | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3319 | frontal | 1999.0 BUICK PARK AVENUE | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3320 | frontal | 1999.0 CHRYSLER LHS | 64.7 | VEHICLE CG | XYZ | 10000 |
| 3321 | frontal | 2000.0 CADILLAC SEVILLE | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3322 | frontal | 1999.0 NISSAN QUEST | 64 | VEHICLE CG | XYZ | 10000 |
| 3323 | frontal | 1999.0 FORD WINDSTAR | 64 | VEHICLE CG | XYZ | 10000 |
| 3324 | frontal | 1999.0 HONDA ODYSSEY | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3325 | frontal | 1999.0 VOLKSWAGEN JETTA | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3326 | frontal | 1999.0 KIA SEPHIA | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3327 | frontal | 1999.0 MAZDA 323-PROTEGE | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3328 | frontal | 2000.0 DODGE NEON | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3329 | frontal | 1999.0 SAAB 9-3 | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3330 | frontal | 1999.0 HYUNDAI SONATA | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3331 | frontal | 1999.0 JEEP GRAND CHEROKEE | 66 | VEHICLE CG | XYZ | 10000 |
| 3332 | frontal | 2000.0 SUBARU LEGACY | 64 | VEHICLE CG | XYZ | 10000 |
| 3333 | frontal | 1999.0 DAEWOO LEGANZA | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3334 | frontal | 2000.0 NISSAN ALTIMA | 63.9 | VEHICLE CG | XYZ | 10000 |
| 3335 | frontal | 1999.0 PONTIAC GRAND AM | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3336 | frontal | 1999.0 CHEVROLET MALIBU | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3337 | frontal | 1999.0 MAZDA 626 | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3338 | frontal | 2000.0 SATURN LS2 | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3347 | frontal | 1999.0 SAAB 9-5 | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3348 | frontal | 1999.0 CADILLAC CATERA | 64.2 | VEHICLE CG | XZ | 10000 |
| 3349 | frontal | 1999.0 AUDI A6 | 64.6 | VEHICLE CG | XYZ | 10000 |
| 3350 | frontal | 2000.0 BMW 328 I | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3351 | frontal | 2000.0 VOLVO S80 | 63.9 | VEHICLE CG | XYZ | 10000 |
| 3364 | frontal | 2000.0 MAZDA MPV | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3366 | frontal | 2000.0 TOYOTA AVALON | 64.3 | VEHICLE CG | XYZ | 10000 |
| 3367 | frontal | 2000.0 LINCOLN LS | 64 | VEHICLE CG | XYZ | 10000 |
| 3368 | frontal | 2000.0 NISSAN SENTRA | 64 | VEHICLE CG | XYZ | 10000 |
| 3369 | frontal | 2000.0 NISSAN MAXIMA | 63.7 | VEHICLE CG | XYZ | 10000 |
| 3370 | frontal | 2000.0 ISUZU RODEO | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3371 | frontal | 1997.0 DODGE NEON | 64 | VEHICLE CG | XYZ | 10000 |
| 3372 | frontal | 1998.0 TOYOTA AVALON | 64.5 | VEHICLE CG | XYZ | 10000 |
| 3373 | frontal | 1998.0 NISSAN FRONTIER | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3374 | frontal | 1998.0 JEEP WRANGLER | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3375 | frontal | 1998.0 VOLKSWAGEN BEETLE | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3376 | frontal | 1998.0 JEEP CHEROKEE | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3377 | frontal | 1998.0 KIA SPORTAGE | 64.6 | VEHICLE CG | XYZ | 10000 |
| 3378 | frontal | 1998.0 TOYOTA RAV4 | 64.6 | VEHICLE CG | XYZ | 10000 |
| 3379 | frontal | 1998.0 ISUZU AMIGO | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3380 | frontal | 1998.0 HONDA CR-V | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3381 | frontal | 1999.0 SUBARU FORESTER | 64.4 | VEHICLE CG | XYZ | 10000 |
| 3509 | frontal | 2000.0 NISSAN XTERRA | 64.6 | VEHICLE CG | XYZ | 10000 |
| 3510 | frontal | 2001.0 ISUZU TROOPER II | 64.2 | VEHICLE CG | XYZ | 10000 |
| 3511 | frontal | 2001.0 BMW X5 | 64.8 | VEHICLE CG | XYZ | 10000 |
| 3512 | frontal | 2001.0 MITSUBISHI MONTERO | 64.5 | VEHICLE CG | XYZ | 10000 |
| 3513 | frontal | 2000.0 ISUZU TROOPER II | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3523 | side | 1998.0 CHEVROLET CAVALIER | 61.6 | VEHICLE CG | XYZ | 10000 |
| 3525 | side | 2001.0 LEXUS IS300 | 62 | VEHICLE CG | XYZ | 10000 |
| 3526 | side | 2001.0 TOYOTA ECHO | 61.5 | VEHICLE CG | XYZ | 10000 |
| 3527 | side | 2000.0 PONTIAC GRAND AM | 62.1 | VEHICLE CG | XYZ | 10000 |
| 3530 | side | 2001.0 MAZDA TRIBUTE | 62 | VEHICLE CG | XYZ | 10000 |
| 3531 | side | 2001.0 MAZDA MILLENIA | 62.1 | VEHICLE CG | XYZ | 10000 |
| 3535 | side | 2001.0 TOYOTA CELICA | 62 | VEHICLE CG | XYZ | 10000 |
| 3544 | side | 2001.0 MERCURY COUGAR | 62.12 | VEHICLE CG | XYZ | 20000 |
| 3545 | side | 2001.0 FORD MUSTANG | 61.96 | VEHICLE CG | XYZ | 20000 |
| 3550 | side | 2001.0 HYUNDAI ACCENT | 62.1 | VEHICLE CG | XYZ | 10000 |
| 3555 | side | 2001.0 DODGE DAKOTA | 61.5 | VEHICLE CG | XYZ | 12500 |
| 3556 | side | 2001.0 HONDA CIVIC | 61.6 | VEHICLE CG | XYZ | 12500 |
| 3559 | side | 2001.0 KIA SPECTRA | 52.95 | VEHICLE CG | XYZ | 20000 |
| 3560 | side | 2001.0 LEXUS RX300 | 61.64 | VEHICLE CG | XYZ | 20000 |
| 3561 | side | 2001.0 DODGE GRAND CARAVAN | 62.12 | VEHICLE CG | XYZ | 20000 |
| 3564 | side | 2001.0 DODGE CARAVAN | 61.8 | VEHICLE CG | XYZ | 20000 |
| 3568 | side | 2001.0 CHRYSLER SEBRING CONVERTIBLE | 62.4 | VEHICLE CG | XYZ | 10000 |
| 3569 | side | 2001.0 KIA OPTIMA | 52.95 | VEHICLE CG | XYZ | 20000 |
| 3570 | side | 2001.0 KIA RIO | 61.5 | VEHICLE CG | XYZ | 20000 |
| 3571 | side | 2001.0 AUDI TT | 62.1 | VEHICLE CG | XYZ | 10000 |
| 3572 | side | 2001.0 VOLVO S60 | 53.3 | VEHICLE CG | XYZ | 10000 |
| 3575 | side | 2001.0 CHEVROLET IMPALA | 61.96 | VEHICLE CG | XYZ | 20000 |
| 3596 | side | 2001.0 DODGE STRATUS | 62 | VEHICLE CG | XYZ | 20000 |
| 3619 | side | 2001.0 NISSAN PATHFINDER | 61.79 | VEHICLE CG | XYZ | 10000 |
| 3620 | side | 2001.0 BUICK PARK AVENUE | 61.3 | VEHICLE CG | XYZ | 10000 |
| 3651 | side | 2001.0 MAZDA MIATA | 61.8 | VEHICLE CG | XYZ | 10000 |
| 3652 | side | 2001.0 SUBARU FORESTER | 61.25 | VEHICLE CG | XYZ | 10000 |
| 3668 | side | 2000.0 NISSAN MAXIMA | 53.1 | VEHICLE CG | XYZ | 10000 |
| 3668 | side | nan IIHS MDB VERSION 3 | 53.1 | VEHICLE CG | XYZ | 10000 |
| 3669 | side | 1999.0 CADILLAC DE VILLE | 52.9 | VEHICLE CG | XYZ | 10000 |
| 3674 | side | 2001.0 TOYOTA TACOMA | 61.93 | VEHICLE CG | XYZ | 10000 |
| 3675 | side | 2001.0 BUICK CENTURY | 61.3 | VEHICLE CG | XYZ | 12500 |
| 3679 | side | 1999.0 CHEVROLET PRIZM | 52.9 | VEHICLE CG | XYZ | 10000 |
| 3697 | side | 1999.0 TOYOTA COROLLA | 53.85 | VEHICLE CG | XYZ | 10000 |
| 3698 | side | 1999.0 TOYOTA CAMRY | 54.23 | VEHICLE CG | XYZ | 10000 |
| 3731 | side | 2001.0 MITSUBISHI ECLIPSE | 62.1 | VEHICLE CG | XYZ | 10000 |
| 3742 | frontal | 2001.0 HYUNDAI ELANTRA | 64.1 | VEHICLE CG | XYZ | 10000 |
| 3783 | frontal | 2001.0 DODGE GRAND CARAVAN | 48.3 | VEHICLE CG | XYZ | 12500 |
| 3785 | frontal | 2001.0 TOYOTA ECHO | 48.5 | VEHICLE CG | XYZ | 12500 |
| 3786 | frontal | 2001.0 CHEVROLET IMPALA | 48.2 | VEHICLE CG | XYZ | 12500 |
| 3787 | frontal | 2001.0 HONDA ACCORD | 48.1 | VEHICLE CG | XYZ | 12500 |
| 3796 | frontal | 2001.0 FORD F150 PICKUP | 48 | VEHICLE CG | XYZ | 12500 |
| 3797 | side | 2002.0 SATURN L100 | 62.3 | VEHICLE CG | XYZ | 10000 |
| 3799 | side | 2001.0 FORD FOCUS | 62.1 | VEHICLE CG | XYZ | 10000 |
| 3800 | side | 2002.0 FORD ESCAPE | 62 | VEHICLE CG | XYZ | 10000 |
| 3803 | side | 2002.0 CHEVROLET IMPALA | 61.6 | VEHICLE CG | XYZ | 10000 |
| 3819 | side | 2001.0 BUICK LESABRE | 62 | VEHICLE CG | XYZ | 10000 |
| 3835 | side | 2002.0 CHEVROLET TRAILBLAZER | 61.74 | VEHICLE CG | XYZ | 10000 |
| 3846 | side | 2002.0 CHEVROLET MALIBU | 61.96 | VEHICLE CG | XYZ | 10000 |
| 3847 | side | 2002.0 TOYOTA RAV4 | 61.73 | VEHICLE CG | XYZ | 10000 |
| 3852 | side | 2002.0 BUICK RENDEZVOUS | 62.28 | VEHICLE CG | XYZ | 20000 |
| 3853 | side | 2002.0 JEEP LIBERTY | 61.5 | VEHICLE CG | XYZ | 20000 |
| 3875 | side | 2002.0 HONDA ODYSSEY | 61.6 | VEHICLE CG | XY | 10000 |
| 3876 | side | 2002.0 LEXUS ES300 | 62.2 | VEHICLE CG | XYZ | 12500 |
| 3899 | side | 2002.0 TOYOTA TUNDRA | 61.8 | VEHICLE CG | XY | 10000 |
| 3900 | side | 2002.0 KIA SEDONA | 61.81 | VEHICLE CG | XYZ | 10000 |
| 3903 | side | 2002.0 ACURA MDX | 62.1 | VEHICLE CG | XYZ | 12500 |
| 3904 | side | 2002.0 MITSUBISHI MONTERO SPORT | 62 | VEHICLE CG | XYZ | 12500 |
| 3904 | side | 1999.0 OTHER OTHER | 62 | VEHICLE CG | XYZ | 12500 |
| 3906 | side | 2002.0 NISSAN ALTIMA | 61.69 | VEHICLE CG | XYZ | 12500 |
| 3908 | side | 2002.0 ISUZU AXIOM | 61.96 | VEHICLE CG | XYZ | 20000 |
| 3951 | side | 2002.0 MITSUBISHI LANCER | 61.8 | VEHICLE CG | XYZ | 10000 |
| 4075 | side | 2002.0 ACURA RSX | 61.96 | VEHICLE CG | XYZ | 20000 |
| 4076 | side | 2002.0 FORD THUNDERBIRD | 61.86 | VEHICLE CG | XYZ | 12500 |
| 4077 | side | 2002.0 DAEWOO NUBIRA | 62 | VEHICLE CG | XYZ | 10000 |
| 4078 | side | 2002.0 HYUNDAI SONATA | 62 | VEHICLE CG | XYZ | 10000 |
| 4206 | frontal | 1998.0 AUDI A8 | 56.2 | VEHICLE CG | XYZ | 10000 |
| 4321 | frontal | 2001.0 FORD ESCAPE | 40.1 | VEHICLE CG | XYZ | 12500 |
| 4377 | frontal | 2002.0 DODGE NEON | 56 | VEHICLE CG | XYZ | 12500 |
| 4431 | frontal | 2002.0 NISSAN ALTIMA | 56.1 | VEHICLE CG | XYZ | 12500 |
| 4439 | frontal | 2002.0 NISSAN QUEST | 56 | VEHICLE CG | XYZ | 12500 |
| 4441 | frontal | 2003.0 LINCOLN NAVIGATOR | 56 | VEHICLE CG | XYZ | 12500 |
| 4447 | frontal | 2002.0 AUDI A4 | 64.4 | VEHICLE CG | XYZ | 10000 |
| 4448 | frontal | 2002.0 SUZUKI AERIO | 64.3 | VEHICLE CG | XYZ | 10000 |
| 4449 | frontal | 2003.0 TOYOTA COROLLA | 64.2 | VEHICLE CG | XYZ | 10000 |
| 4450 | frontal | 2003.0 HONDA ACCORD | 64.2 | VEHICLE CG | XYZ | 10000 |
| 4451 | frontal | 2002.0 MINI COOPER | 64.4 | VEHICLE CG | XYZ | 10000 |
| 4669 | frontal | 2003.0 TOYOTA SIENNA | 56 | VEHICLE CG | XYZ | 12500 |
| 4734 | frontal | 2001.0 VOLKSWAGEN POLO | 55.9 | VEHICLE CG | XYZ | 20000 |
| 4870 | frontal | 2003.0 TOYOTA AVALON | 56.65 | VEHICLE CG | XYZ | 10000 |
| 4873 | frontal | 2003.0 CHEVROLET TRAILBLAZER | 56.65 | VEHICLE CG | XYZ | 10000 |
| 4874 | frontal | 2003.0 CADILLAC SEVILLE | 56.49 | VEHICLE CG | XYZ | 10000 |
| 4963 | frontal | 1996.0 CHRYSLER CONCORDE | 56.4 | VEHICLE CG | XYZ | 12500 |
| 4990 | frontal | 1996.0 DODGE CARAVAN | 56.3 | VEHICLE CG | XYZ | 12500 |
| 5034 | frontal | 2002.0 FORD EXPLORER | 56.3 | VEHICLE CG | XYZ | 12500 |
| 5036 | frontal | 2002.0 CHEVROLET TRAILBLAZER | 56.7 | VEHICLE CG | XY | 12500 |
| 5061 | frontal | 2002.0 DODGE RAM | 56.4 | VEHICLE CG | XY | 12500 |
| 5062 | frontal | 2004.0 HONDA ACCORD | 56.6 | VEHICLE CG | XYZ | 12500 |
| 5073 | frontal | 2002.0 TOYOTA TUNDRA | 56.3 | VEHICLE CG | XYZ | 12500 |
| 5144 | frontal | 2004.0 HONDA ODYSSEY | 56.4 | VEHICLE CG | XYZ | 12500 |
| 5211 | frontal | 2004.0 JEEP LIBERTY | 56.1 | VEHICLE CG | XYZ | 12500 |
| 5654 | frontal | 2006.0 DODGE STRATUS | 56 | VEHICLE CG | XZ | 12500 |
| 5666 | frontal | 2006.0 SUZUKI VERONA | 56.1 | VEHICLE CG | XYZ | 12500 |
| 5680 | frontal | 2006.0 SUZUKI FORENZA | 55.9 | VEHICLE CG | XYZ | 12500 |
| 5710 | frontal | 2001.0 HONDA CIVIC | 56.2 | VEHICLE CG | XYZ | 12500 |
| 5711 | frontal | 2003.0 CHEVROLET SILVERADO | 56.2 | VEHICLE CG | XYZ | 12500 |
| 5712 | frontal | 2002.0 FORD FOCUS | 56.2 | VEHICLE CG | XYZ | 12500 |
| 5717 | frontal | 2006.0 MITSUBISHI GALANT | 55.8 | VEHICLE CG | XYZ | 12500 |
| 5760 | frontal | 2005.0 CHRYSLER TOWN AND COUNTRY | 56.24 | VEHICLE CG | XYZ | 10000 |
| 5765 | frontal | 2005.0 SUZUKI VITARA | 40.27 | VEHICLE CG | XYZ | 10000 |
| 5768 | frontal | 2005.0 KIA SEDONA | 40.27 | VEHICLE CG | XYZ | 10000 |
| 5769 | frontal | 2005.0 HYUNDAI TUCSON | 40.12 | VEHICLE CG | XYZ | 10000 |
| 5797 | frontal | 2006.0 HYUNDAI SONATA | 40.28 | VEHICLE CG | XYZ | 10000 |
| 5801 | frontal | 2006.0 HONDA OTHER | 56.57 | VEHICLE CG | XYZ | 10000 |
| 5802 | frontal | 2006.0 HONDA RIDGELINE | 40.1 | VEHICLE CG | XYZ | 10000 |
| 5803 | frontal | 2006.0 FORD OTHER | 56.68 | VEHICLE CG | XYZ | 10000 |
| 5804 | frontal | 2006.0 FORD FUSION | 40.33 | VEHICLE CG | XYZ | 10000 |
| 5807 | frontal | 2006.0 DODGE GRAND CARAVAN | 56.04 | VEHICLE CG | XYZ | 10000 |
| 5808 | frontal | 2006.0 HONDA ODYSSEY | 40.4 | VEHICLE CG | XYZ | 10000 |
| 5810 | frontal | 2006.0 HONDA CIVIC | 40.17 | VEHICLE CG | XYZ | 10000 |
| 5813 | frontal | 2006.0 SUBARU IMPREZA | 40.3 | VEHICLE CG | XYZ | 10000 |
| 5878 | frontal | 2007.0 FORD FIVE HUNDRED | 55.9 | VEHICLE CG | XYZ | 12500 |
| 5880 | frontal | 2007.0 MAZDA MAZDA6 | 56 | VEHICLE CG | XYZ | 12500 |
| 5881 | frontal | 2006.0 FORD F250 PICKUP | 40.2 | VEHICLE CG | XYZ | 12500 |

<!-- nhtsa:end -->

<!-- injury:start -->

### NHTSA dummy injury criteria used in X2 (generated by `python -m crashguard.injury`)

Source: the `OCCUPANT` records of the NHTSA test metadata (public domain). Field meanings: NHTSA Biomechanics Data Reference Guide, version 4.b, volume II (opened). A recorded zero is treated as 'not computed'. A criterion is analysed only where at least 20 tests have it. Test numbers per cell:

- frontal, position 01, HIC (interval T2 - T1 in the data): 51 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4734, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5654, 5666, 5680, 5710, 5711, 5712, 5717, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 01, chest peak 3 ms (g): 50 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5654, 5666, 5680, 5710, 5711, 5712, 5717, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 01, femur compression (N): 50 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5654, 5666, 5680, 5710, 5711, 5712, 5717, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 01, CSI: 50 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5654, 5666, 5680, 5710, 5711, 5712, 5717, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 02, HIC (interval T2 - T1 in the data): 46 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5710, 5711, 5712, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 02, chest peak 3 ms (g): 46 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5710, 5711, 5712, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 02, femur compression (N): 46 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5710, 5711, 5712, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- frontal, position 02, CSI: 46 tests: 3161, 3211, 3212, 3213, 3222, 3224, 3783, 3785, 3786, 3787, 3796, 4321, 4377, 4431, 4439, 4441, 4669, 4870, 4873, 4874, 4990, 5034, 5036, 5061, 5062, 5073, 5144, 5211, 5710, 5711, 5712, 5760, 5765, 5768, 5769, 5797, 5801, 5802, 5803, 5804, 5807, 5808, 5810, 5813, 5878, 5880
- side, position 01, HIC (interval T2 - T1 in the data): 59 tests: 3523, 3525, 3526, 3527, 3530, 3531, 3535, 3544, 3545, 3550, 3555, 3559, 3560, 3561, 3564, 3568, 3569, 3570, 3571, 3572, 3575, 3596, 3619, 3620, 3651, 3652, 3668, 3669, 3674, 3675, 3679, 3697, 3698, 3731, 3797, 3799, 3800, 3803, 3819, 3835, 3846, 3847, 3852, 3853, 3875, 3876, 3899, 3900, 3903, 3904, 3906, 3908, 3951, 4075, 4076, 4077, 4078
- side, position 01, TTI(d): 58 tests: 3523, 3525, 3526, 3527, 3530, 3531, 3535, 3544, 3545, 3550, 3555, 3556, 3559, 3560, 3561, 3564, 3568, 3569, 3570, 3571, 3572, 3575, 3596, 3619, 3620, 3651, 3652, 3668, 3669, 3674, 3675, 3679, 3731, 3797, 3799, 3800, 3803, 3819, 3835, 3846, 3847, 3852, 3853, 3875, 3876, 3899, 3900, 3903, 3904, 3906, 3908, 3951, 4075, 4076, 4077, 4078
- side, position 01, pelvis peak lateral (g): 58 tests: 3523, 3525, 3526, 3527, 3530, 3531, 3535, 3544, 3545, 3550, 3555, 3556, 3559, 3560, 3561, 3564, 3568, 3569, 3570, 3571, 3572, 3575, 3596, 3619, 3620, 3651, 3652, 3668, 3669, 3674, 3675, 3679, 3731, 3797, 3799, 3800, 3803, 3819, 3835, 3846, 3847, 3852, 3853, 3875, 3876, 3899, 3900, 3903, 3904, 3906, 3908, 3951, 4075, 4076, 4077, 4078
- side, position 04, HIC (interval T2 - T1 in the data): 56 tests: 3523, 3525, 3526, 3527, 3530, 3531, 3535, 3544, 3545, 3550, 3555, 3556, 3559, 3560, 3561, 3564, 3568, 3569, 3570, 3572, 3575, 3596, 3619, 3620, 3652, 3668, 3669, 3675, 3679, 3697, 3698, 3731, 3797, 3799, 3800, 3803, 3819, 3835, 3846, 3847, 3852, 3853, 3875, 3876, 3899, 3900, 3903, 3904, 3906, 3908, 3951, 4075, 4077, 4078
- side, position 04, TTI(d): 52 tests: 3523, 3525, 3526, 3527, 3530, 3531, 3535, 3544, 3545, 3550, 3555, 3556, 3559, 3560, 3561, 3564, 3568, 3569, 3570, 3572, 3575, 3596, 3619, 3620, 3652, 3668, 3669, 3675, 3679, 3731, 3797, 3799, 3800, 3803, 3819, 3835, 3846, 3847, 3852, 3853, 3876, 3900, 3903, 3904, 3906, 3908, 3951, 4075, 4077, 4078
- side, position 04, pelvis peak lateral (g): 54 tests: 3523, 3525, 3526, 3527, 3530, 3531, 3535, 3544, 3545, 3550, 3555, 3556, 3559, 3560, 3561, 3564, 3568, 3569, 3570, 3572, 3575, 3596, 3619, 3620, 3652, 3668, 3669, 3675, 3679, 3731, 3797, 3799, 3800, 3803, 3819, 3835, 3846, 3847, 3852, 3853, 3875, 3876, 3899, 3900, 3903, 3904, 3906, 3908, 3951, 4075, 4077, 4078

<!-- injury:end -->
