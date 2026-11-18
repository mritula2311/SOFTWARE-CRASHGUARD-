# Build record of the ns-3 cross-check simulator

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Build record of the ns-3 lorawan cross-check simulator: versions, commit hashes and status. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; MAC = message authentication code |
<!-- header:end -->

Built in WSL2 (Ubuntu, g++ and cmake from the system packages) outside the repository, in `~/ns3work/ns-3-dev`.

| Item | Version | Commit |
|---|---|---|
| ns-3 | ns-3.48 (tag, as named by `src/lorawan/NS3-VERSION`) | d2add90b452d600cfb4859baed8e9ea633519447 |
| signetlabdei lorawan module | v0.3.7 plus 2 commits (`git describe`: v0.3.7-2-ge45b4af) | e45b4af428c92f30b2e6c201055809110758125f |

Local changes to the module (all in the ns-3 source tree, recorded here and not in this repository):
1. `model/logical-lora-channel.cc`: the include of the ns-3 log header was added (the file did not compile against ns-3.48 without it).
2. `model/gateway-lora-phy.cc` and `model/end-device-lora-phy.cc`: the sensitivity tables were set to the values of the custom simulator (-123, -126, -129, -132, -134.5, -137 dBm for SF7 to SF12) for the calibration; the shipped values are -130, -132.5, -135, -137.5, -140, -142.5 dBm (gateway) and -124, -127, -130, -133, -135, -137 dBm (end device).

3. Session 2: `model/network-scheduler.cc` and `model/class-a-end-device-lorawan-mac.cc`: the receive-window delays are run-time variables (`g_xsimRx1`, `g_xsimRx2`; defaults 1 s and 2 s, the LoRaWAN class A values). The application sets 0.1 s and 0.2 s for the policies p1, quick and d1 (the custom simulator's 0.1 s processing delay) and keeps 1 s and 2 s for the standard LoRaWAN baseline.

4. Paper session (2026-11-15): `model/logical-lora-channel-helper.cc`, functions `GetWaitTime(uint32_t)`, `AddEvent(Time, uint32_t)` and `GetTxPowerForChannel(uint32_t)`: a frequency outside the known sub-bands (the RX2 frequency 869.525 MHz in the ALOHA region, whose only sub-band is 868.0 to 868.6 MHz) now gives a wait of 0, no duty-cycle bookkeeping and 14 dBm. The shipped code dereferenced a null pointer there (`NS_ASSERT_MSG` is compiled out in the optimized build): `SubBand::GetNextTransmissionTime` inside `GatewayStatus::IsAvailableForTransmission`, found with gdb. The crash occurs when the gateway is busy at the RX1 opportunity and the network scheduler tries RX2; it hit about 0.2% of the earlier runs and 17% of the two-stage runs at SF7 (many short frames). The change alters nothing in runs that did not crash. RX2 downlinks are therefore not duty-limited in the ns-3 runs of this paper (the ACK airtime is short; the effect is not quantified).
5. Paper session: the application `xsim/ns3/xsim_alert.cc` gained the policies `r3s` and `r3t` (the two-stage alert), the options `--radius`, `--rate` and `--events`, and a guard that never sends from inside the MAC's outcome callback. Existing policies are unchanged.

Status: built and running (the module's example programs, the calibration scenario `xsim/ns3/xsim_calib.cc` and, in session 2, the alert scenario `xsim/ns3/xsim_alert.cc`, which compiles the D1 part of the firmware C path `firmware_rd/cg_rd.c` with `CG_NO_CRYPTO`). Calibration results: `docs/03_results/XSIM_CALIBRATION.md`. The D1 application and the cross-simulator verdict table (X1.3): `docs/03_results/XSIM_VERDICTS.md`. Known problem: about 0.2% of the alert-scenario runs crash inside the module (a segmentation fault right after the confirmed-uplink outcome callback returns, found with a debug trace; same arguments crash again; the cause in the module was not found); these runs are dropped for all policies of that cell and hour.

## Patch file and build record (final verification run, 2026-11-15)

The local changes to the lorawan module are now stored as a patch in the repository: `xsim/ns3/patches/lorawan-v0.3.7-2-ge45b4af-local.patch` (output of `git diff` in `src/lorawan`, 8 files, 34 insertions, 11 deletions; SHA-256 `852f0f8dd489582a7c8d3a81ea8eb2f5b7964690b8cf5ba91e3368efea54e02c`). Apply it to the module at commit e45b4af with `git apply`. Besides items 1 to 4 above it holds two small changes to `model/simple-end-device-lora-phy.cc` and `model/simple-gateway-lora-phy.cc` (a run-time sensitivity offset `g_xsimSensDelta[6]` used by the sensitivity analysis; zero by default) and the `class-a-end-device-lorawan-mac.cc` receive-window variables of item 3. The scratch `CMakeLists.txt` of the build is `xsim/ns3/scratch_CMakeLists.txt`; `xsim/ns3/xsim_alert.cc`, `xsim/ns3/xsim_calib.cc`, `firmware_rd/cg_rd.c` and `firmware_rd/cg_rd.h` are byte-identical to the files in the ns-3 `scratch/` folder.

Build record: g++ 13.3.0 and cmake 3.28.3 (Ubuntu 24.04 in WSL2); `libns3.48-lorawan-optimized.so` SHA-256 `b9eb31027510c710b0d312fc623928c4d51a84deb09b17452f78b00daa0efa0e`; `ns3.48-xsim_alert-optimized` SHA-256 `ad984fad3ad9ec6088e2064556aadbe5231420743ec9c652bd34c2ddec197bbd`.

The null-pointer fix of item 4 (the RX2 frequency outside the known sub-bands) is part of this patch and of this build. Check: 100 runs (R3 cells at SF7 and SF9 with extra loss 0.3, both policies, seeds 1 to 20, and one D1 cell of the S-X grid, hours 0 to 19) were run again in this build and every output file is byte-identical to the stored one (`docs/03_results/VF_NS3_RERUN.md`, keys `vf.ns3.*`).
