# Accelerometer data sheets opened for the sensor-selection study

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-12 |
| Owner | Mritula S |
| Scope | Accelerometer data sheets opened for the sensor-selection study. |
| Evidence labels used | NOT_RUN |
| Abbreviations | ECE = Economic Commission for Europe; ESP32 = a Wi-Fi microcontroller family (Espressif); I2C = inter-integrated circuit bus; NHTSA = National Highway Traffic Safety Administration; ODR = output data rate; PDF = Portable Document Format; SPI = serial peripheral interface; URL = uniform resource locator |
<!-- header:end -->

Documents were opened as PDF copies on 2026-11-12 (the ADXL375 copy on 2026-11-11). Local copies are in `data/raw/refs/` and `data/raw/refs/sel/` (git-ignored: redistribution rights were not checked). Values in `src/crashguard/sel_parts.py` and in `results/paper/tab_sel_parts.*` were read from these documents. No price is given: no vendor page was opened.

| Part | Address opened | Date opened | Document | Notes |
|---|---|---|---|---|
| MPU-6050 | https://www.haoyuelectronics.com/Attachment/GY-521/mpu6050.pdf | 2026-11-12 | InvenSense MPU-6000/MPU-6050 Product Specification, Rev 3.3, 2012-05-16 (a Rev 3.2 copy was also opened: https://alliance.seas.upenn.edu/~medesign/wiki/uploads/Guides/MPU6050_datasheet.pdf) | Bandwidth in the model is 260 Hz (filter off) at both rates; the part's sample rate is 1 kHz at most |
| ADXL345 | https://people.ece.ubc.ca/edc/7660.jan2018/ADXL345.pdf | 2026-11-12 | Analog Devices ADXL345 Data Sheet, Rev. E (copy hosted by UBC ECE) | Noise density derived from 0.75 LSB rms x 3.9 mg/LSB at bandwidth 50 Hz (x, y axes); the z value is higher and is not used |
| ADXL375 | not recorded in the 2026-11-11 session (local copy data/raw/refs/adxl375.pdf, opened 2026-11-11) | 2026-11-11 | Analog Devices ADXL375 Data Sheet, Rev. B (distributor copy; the extracted text is garbled in the specification table, so only the values listed here were read) | Source URL not recorded in the earlier session: the URL field is therefore NOT verified. Bits and noise were not read |
| H3LIS331DL | https://static.chipdip.ru/lib/447/DOC029447674.pdf | 2026-11-12 | STMicroelectronics H3LIS331DL data sheet DS9012, Rev 4, October 2022 (distributor copy) | Noise value used as printed; no other source was opened to check it |
| LIS3DH | https://cdn-shop.adafruit.com/datasheets/LIS3DH.pdf | 2026-11-12 | STMicroelectronics LIS3DH data sheet, Doc ID 17530 Rev 1, May 2010 (copy hosted by Adafruit; the earliest revision, a later one may differ) | 1.25 kHz is the normal-mode rate and 5 kHz the low-power rate; both are used as bandwidth ODR/2 |
| KX134-1211 | https://fscdn.rohm.com/kionix/en/datasheet/kx134-1211-e.pdf | 2026-11-12 | Kionix KX134-1211 Specifications, Rev. 4.0, 24-Nov-2021 | ODR/2 (the wider of the two bandwidth settings) is used in the model |
| ADXL372 | https://datasheet.chipsmall.com/ADXL372BCCZ-RL/497167.pdf | 2026-11-12 | Analog Devices ADXL372 Data Sheet, Rev. 0, 2017 (distributor copy) | Bandwidth ODR/2 used in the model (the widest setting) |
| LSM6DSK320X (high-g channel) | https://components101.com/sites/default/files/2026-10/DS_lsm6dsk320x-compressed.pdf | 2026-11-12 | STMicroelectronics LSM6DSK320X data sheet DS15060, Rev 1, July 2026 (distributor copy). The part named in the task, LSM6DSV32X, could not be opened (its ST datasheet URL timed out), so it is NOT in the table | Dual-channel part: the low-g channel (+-2 to +-16 g, 0.061 to 0.488 mg/LSB) is used in the pair study. Bandwidth is an assumption |

**Part named in the task but not opened:** LSM6DSV32X (ST). The ST data sheet address timed out. The data sheet that was opened is for the LSM6DSK320X, which has a low-g channel (to +-16 g) and a high-g channel (to +-320 g); it is NOT claimed to be the same part.

**Caveats stated in every table row:** C1: the output data rate is the datasheet rate, not a measured I2C or SPI read rate on an ESP32 (NOT_RUN, hardware); C2: NHTSA tests are mostly high-speed barrier crashes; C3: the sensor is a software model (bandwidth, range, rate, resolution); C4: noise is white at the datasheet density where one was read, none otherwise.
