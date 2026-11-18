"""Datasheet values of the accelerometers in the sensor-selection study (ANALYTICAL: values read from the documents named below, never from memory).

Each entry lists the URL that was opened, the date it was opened, and the revision printed in the document. Documents were opened as PDF copies on 2026-11-12 (local copies in
``data/raw/refs/sel/``, git-ignored, because redistribution rights are not checked). Where a value could not be read, the field says so. The simulated sensor chain is ``severity_study.sensor_signal``
(4th-order zero-phase low-pass at the part's bandwidth, saturation at the full-scale range, resampling at the output data rate, quantisation at the least significant bit), with optional white noise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

OPENED = "2026-11-12"


@dataclass
class Part:
    key: str
    name: str
    url: str
    opened: str
    document: str
    ranges_g: tuple
    mg_per_lsb: dict  # range (g) -> mg per least significant bit
    bits: str
    odrs_hz: tuple  # output data rates used in the study (a subset of what the part offers)
    odr_offered: str
    bandwidth: str  # as printed
    bw_rule: float  # model bandwidth = bw_rule x ODR, or a fixed number of Hz if above 1 (see bw_hz)
    noise_text: str
    noise_ug_rthz: float | None  # density used for the optional noise model (micro-g per root hertz); None = not read, no noise applied
    interface: str
    study_ranges: tuple = ()
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def bw_hz(self, odr: float) -> float:
        return self.bw_rule if self.bw_rule > 1 else self.bw_rule * odr


PARTS: list[Part] = [
    Part("mpu6050", "MPU-6050", "https://www.haoyuelectronics.com/Attachment/GY-521/mpu6050.pdf", OPENED, "InvenSense MPU-6000/MPU-6050 Product Specification, Rev 3.3, 2012-05-16 (a Rev 3.2 copy was also opened: https://alliance.seas.upenn.edu/~medesign/wiki/uploads/Guides/MPU6050_datasheet.pdf)",
         (2, 4, 8, 16), {2: 1000 / 16384, 4: 1000 / 8192, 8: 1000 / 4096, 16: 1000 / 2048}, "16", (100, 1000), "accelerometer sample rate 4 to 1000 Hz (programmable)",
         "low-pass filter programmable 5 to 260 Hz", 260.0, "power spectral density 400 ug/rtHz at 10 Hz, +-2 g, ODR 1 kHz (the unit prefix is lost in the PDF text; read as micro-g)", 400.0, "I2C (MPU-6050); SPI also on MPU-6000",
         (2, 4, 8, 16), "Bandwidth in the model is 260 Hz (filter off) at both rates; the part's sample rate is 1 kHz at most"),
    Part("adxl345", "ADXL345", "https://people.ece.ubc.ca/edc/7660.jan2018/ADXL345.pdf", OPENED, "Analog Devices ADXL345 Data Sheet, Rev. E (copy hosted by UBC ECE)",
         (2, 4, 8, 16), {2: 3.9, 4: 3.9, 8: 3.9, 16: 3.9}, "10 to 13 (full resolution, 3.9 mg/LSB at every range)", (100, 400, 1600, 3200), "0.1 to 3200 Hz",
         "bandwidth = ODR/2", 0.5, "0.75 LSB rms (x, y) and 1.1 LSB rms (z) at ODR 100 Hz, all ranges in full resolution", 0.75 * 3.9 / (50.0 ** 0.5), "SPI (3- or 4-wire), I2C",
         (2, 4, 8, 16), "Noise density derived from 0.75 LSB rms x 3.9 mg/LSB at bandwidth 50 Hz (x, y axes); the z value is higher and is not used"),
    Part("adxl375", "ADXL375", "not recorded in the 2026-11-11 session (local copy data/raw/refs/adxl375.pdf, opened 2026-11-11)", "2026-11-11",
         "Analog Devices ADXL375 Data Sheet, Rev. B (distributor copy; the extracted text is garbled in the specification table, so only the values listed here were read)",
         (200,), {200: 49.0}, "not read (scale factor 49 mg/LSB as printed)", (100, 400, 1600, 3200), "up to 3200 Hz", "bandwidth is the -3 dB frequency and is half the output data rate (footnote 5)", 0.5,
         "not read", None, "SPI (3- or 4-wire), I2C", (200,), "Source URL not recorded in the earlier session: the URL field is therefore NOT verified. Bits and noise were not read"),
    Part("h3lis331dl", "H3LIS331DL", "https://static.chipdip.ru/lib/447/DOC029447674.pdf", OPENED, "STMicroelectronics H3LIS331DL data sheet DS9012, Rev 4, October 2022 (distributor copy)",
         (100, 200, 400), {100: 49.0, 200: 98.0, 400: 195.0}, "12-bit representation as printed (16-bit data output in the feature list)", (100, 400, 1000), "0.5 Hz to 1 kHz (50, 100, 400, 1000 Hz in normal mode)",
         "system bandwidth = ODR/2", 0.5, "noise density 15 mg/rtHz as printed (FS bit 00); the unit is used as printed and is large for a MEMS part, so it is not cross-checked", 15000.0, "I2C, SPI", (100, 200, 400),
         "Noise value used as printed; no other source was opened to check it"),
    Part("lis3dh", "LIS3DH", "https://cdn-shop.adafruit.com/datasheets/LIS3DH.pdf", OPENED, "STMicroelectronics LIS3DH data sheet, Doc ID 17530 Rev 1, May 2010 (copy hosted by Adafruit; the earliest revision, a later one may differ)",
         (2, 4, 8, 16), {2: 1.0, 4: 2.0, 8: 4.0, 16: 12.0}, "12 (left-justified in 16 bits; mg/digit as printed)", (100, 400, 1250, 5000), "1, 10, 25, 50, 100, 200, 400 Hz, 1.6 kHz (low power), 1.25 kHz normal or 5 kHz low power",
         "system bandwidth = ODR/2", 0.5, "noise density 220 ug/rtHz at FS 2 g, normal mode, ODR 100 Hz", 220.0, "I2C, SPI", (2, 4, 8, 16), "1.25 kHz is the normal-mode rate and 5 kHz the low-power rate; both are used as bandwidth ODR/2"),
    Part("kx134", "KX134-1211", "https://fscdn.rohm.com/kionix/en/datasheet/kx134-1211-e.pdf", OPENED, "Kionix KX134-1211 Specifications, Rev. 4.0, 24-Nov-2021",
         (8, 16, 32, 64), {8: 1000 / 4096, 16: 1000 / 2048, 32: 1000 / 1024, 64: 1000 / 512}, "16", (100, 400, 1600, 6400, 25600), "0.781 Hz to 25600 Hz",
         "output bandwidth ODR/9 or ODR/2", 0.5, "noise 1.6 mg rms, density 300 ug/rtHz (ODR 50 Hz, GSEL 0)", 300.0, "I2C, SPI", (8, 16, 32, 64), "ODR/2 (the wider of the two bandwidth settings) is used in the model"),
    Part("adxl372", "ADXL372", "https://datasheet.chipsmall.com/ADXL372BCCZ-RL/497167.pdf", OPENED, "Analog Devices ADXL372 Data Sheet, Rev. 0, 2017 (distributor copy)",
         (200,), {200: 100.0}, "12", (400, 800, 1600, 3200, 6400), "400 to 6400 Hz", "low-pass 200 Hz to ODR/2 (user selectable, 4-pole)", 0.5, "3.5 LSB rms normal operation at 3200 Hz ODR, 1600 Hz bandwidth",
         3.5 * 100.0 / (1600.0 ** 0.5), "SPI, limited I2C", (200,), "Bandwidth ODR/2 used in the model (the widest setting)"),
    Part("lsm6dsk320x", "LSM6DSK320X (high-g channel)", "https://components101.com/sites/default/files/2026-10/DS_lsm6dsk320x-compressed.pdf", OPENED, "STMicroelectronics LSM6DSK320X data sheet DS15060, Rev 1, July 2026 (distributor copy). The part named in the task, LSM6DSV32X, could not be opened (its ST datasheet URL timed out), so it is NOT in the table",
         (32, 64, 128, 256, 320), {32: 0.976, 64: 1.952, 128: 3.904, 256: 7.808, 320: 10.417}, "16 (mg/LSB as printed)", (480, 960, 1920, 3840, 7680), "480 Hz to 7.68 kHz (high-g channel)",
         "not read for the high-g channel; ODR/2 is assumed in the model", 0.5, "density 1000 ug/rtHz (high-g channel, high-performance mode, FS +-32 to +-320 g)", 1000.0, "SPI, I2C, I3C", (32, 64, 128, 256, 320),
         "Dual-channel part: the low-g channel (+-2 to +-16 g, 0.061 to 0.488 mg/LSB) is used in the pair study. Bandwidth is an assumption"),
]
BY_KEY = {p.key: p for p in PARTS}
