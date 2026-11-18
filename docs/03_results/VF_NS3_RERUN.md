# ns-3 rerun against the stored runs (V3.2)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Rerun of R3 cells at SF7 and SF9 and one D1 cell in the patched ns-3 build, compared run by run with the stored outputs. |
| Evidence labels used | none (this file reports no result) |
<!-- header:end -->

Build: `ns3.48-xsim_alert-optimized` SHA-256 ad984fad3ad9ec6088e2064556aadbe5231420743ec9c652bd34c2ddec197bbd; `libns3.48-lorawan-optimized.so` SHA-256 b9eb31027510c710b0d312fc623928c4d51a84deb09b17452f78b00daa0efa0e; D1 table `rd_fw_d1_sf9.bin` SHA-256 96cc49f62e8538d4da31e7f0ad26ae15c22100cfab5b50c774a8cfcd2dc62de5. Patch: `xsim/ns3/patches/lorawan-v0.3.7-2-ge45b4af-local.patch` (includes the RX2 sub-band null-pointer fix).

Each run is compared byte for byte with the stored file (the application is deterministic for a given seed and arguments). 'Stored empty' means the stored run crashed inside the module (the known 0.2% of runs).

| Cell | Runs | Identical to stored | Stored empty | Rerun empty |
|---|---|---|---|---|
| R3 SF7 calib p0.3 r3s | 20 | 20 | 0 | 0 |
| R3 SF7 calib p0.3 r3t | 20 | 20 | 0 | 0 |
| R3 SF9 calib p0.3 r3s | 20 | 20 | 0 | 0 |
| R3 SF9 calib p0.3 r3t | 20 | 20 | 0 | 0 |
| D1 n80_p17_sf9_d0.5_b1 | 20 | 20 | 0 | 0 |
