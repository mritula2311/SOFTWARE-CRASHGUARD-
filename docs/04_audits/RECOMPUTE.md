# Recomputation of the facts the paper states (V1.5)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Facts the paper states, recomputed from the fresh clone: stated value, recomputed value, source key, script, match. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Method. Every macro of the paper (`paper/generated/numbers.tex`, 251 macros) was computed twice with `crashguard.pp_paper.spec`: from the committed `results/results.json` ('paper') and from the `results/results.json` that the fresh clone produced by running the pipeline from the raw data and the stored raw outputs ('fresh clone'). F13 and F14 (Tamarin and ProVerif) are in `docs/04_audits/FORMAL_RERUN.md`; F15's enumeration is also repeated by `scripts/vf_enum_rerun.py`.

Result: 71 of 71 macros of the table below match; 0 of 251 macros differ overall: none.

| ID | Stated (task table) | Macro | Paper (committed) | Recomputed (fresh clone) | Source key | Script | Match |
|---|---|---|---|---|---|---|---|
| F1 | 217 groups, 439 events (426 crash) | `VzGroups` | 217 | 217 | `leakage.*` | `src/crashguard/vz_audit.py` | yes |
| F1 | 217 groups, 439 events (426 crash) | `VzGroupEvents` | 439 | 439 | `leakage.*` | `src/crashguard/vz_audit.py` | yes |
| F1 | 217 groups, 439 events (426 crash) | `VzCrashEvents` | 426 | 426 | `leakage.*` | `src/crashguard/vz_audit.py` | yes |
| F2 | 118 test exact copies (0.49%) | `VzTestExact` | 118 | 118 | `vz.v4.n_events.*` | `src/crashguard/vz_leakage.py` | yes |
| F2 | 118 test exact copies (0.49%) | `VzTestExactShare` | 0.49 | 0.49 | `vz.v4.n_events.*` | `src/crashguard/vz_leakage.py` | yes |
| F3 | 1,305 of 5,863 triggered windows (22.3%) | `VzNearBoth` | 1\,305 | 1\,305 | `dupscan.neardup.*` | `src/crashguard/vz_audit.py` | yes |
| F3 | 1,305 of 5,863 triggered windows (22.3%) | `VzNearScanned` | 5\,863 | 5\,863 | `dupscan.neardup.*` | `src/crashguard/vz_audit.py` | yes |
| F3 | 1,305 of 5,863 triggered windows (22.3%) | `VzNearShare` | 22.3 | 22.3 | `dupscan.neardup.*` | `src/crashguard/vz_audit.py` | yes |
| F4 | recall 0.901 to 0.873; at 1% 0.631 to 0.558 | `VzRecSup` | 0.901 | 0.901 | `vz.v4.rf15.*` | `src/crashguard/vz_leakage.py` | yes |
| F4 | recall 0.901 to 0.873; at 1% 0.631 to 0.558 | `VzRecNear` | 0.873 | 0.873 | `vz.v4.rf15.*` | `src/crashguard/vz_leakage.py` | yes |
| F4 | recall 0.901 to 0.873; at 1% 0.631 to 0.558 | `VzROneSup` | 0.631 | 0.631 | `vz.v4.rf15.*` | `src/crashguard/vz_leakage.py` | yes |
| F4 | recall 0.901 to 0.873; at 1% 0.631 to 0.558 | `VzROneNear` | 0.558 | 0.558 | `vz.v4.rf15.*` | `src/crashguard/vz_leakage.py` | yes |
| F5 | H-C3 refit SUPPORTED, Holm 0.018, KS 0.191 against gate 0.20 | `RefitVerdict` | SUPPORTED | SUPPORTED | `pp.p0.*` | `src/crashguard/pp_p0_refit.py` | yes |
| F5 | H-C3 refit SUPPORTED, Holm 0.018, KS 0.191 against gate 0.20 | `RefitHolm` | 0.018 | 0.018 | `pp.p0.*` | `src/crashguard/pp_p0_refit.py` | yes |
| F5 | H-C3 refit SUPPORTED, Holm 0.018, KS 0.191 against gate 0.20 | `RefitKsFront` | 0.191 | 0.191 | `pp.p0.*` | `src/crashguard/pp_p0_refit.py` | yes |
| F5 | H-C3 refit SUPPORTED, Holm 0.018, KS 0.191 against gate 0.20 | `RefitPassed` | frontal\_barrier,other | frontal\_barrier,other | `pp.p0.*` | `src/crashguard/pp_p0_refit.py` | yes |
| F6 | 0.07 at +-16 g; 0.78 and 0.88 at +-64 g; 14 of 25 settings | `DvSixteen` | 6.8 | 6.8 | `sevstudy.*` | `src/crashguard/severity_study.py` | yes |
| F6 | 0.07 at +-16 g; 0.78 and 0.88 at +-64 g; 14 of 25 settings | `DvSixtyFourA` | 78.4 | 78.4 | `sevstudy.*` | `src/crashguard/severity_study.py` | yes |
| F6 | 0.07 at +-16 g; 0.78 and 0.88 at +-64 g; 14 of 25 settings | `DvSixtyFourB` | 88.1 | 88.1 | `sevstudy.*` | `src/crashguard/severity_study.py` | yes |
| F6 | 0.07 at +-16 g; 0.78 and 0.88 at +-64 g; 14 of 25 settings | `DvSettingsMeet` | 14 | 14 | `sevstudy.*` | `src/crashguard/severity_study.py` | yes |
| F6 | 0.07 at +-16 g; 0.78 and 0.88 at +-64 g; 14 of 25 settings | `DvSettingsAll` | 25 | 25 | `sevstudy.*` | `src/crashguard/severity_study.py` | yes |
| F7 | early exit recall +0.0155 (1%), +0.0015 (5%) | `EarlyGainOne` | +0.0155 | +0.0155 | `s6.*` | `src/crashguard/s6_early.py` | yes |
| F7 | early exit recall +0.0155 (1%), +0.0015 (5%) | `EarlyGainFive` | +0.0015 | +0.0015 | `s6.*` | `src/crashguard/s6_early.py` | yes |
| F8 | median error 11.9% against 23.5% and 25.7%; +-32 g gain 1.3 | `RestMedRest` | 11.9 | 11.9 | `n14x.*` | `src/crashguard/s4_n14.py` | yes |
| F8 | median error 11.9% against 23.5% and 25.7%; +-32 g gain 1.3 | `RestMedSpl` | 23.5 | 23.5 | `n14x.*` | `src/crashguard/s4_n14.py` | yes |
| F8 | median error 11.9% against 23.5% and 25.7%; +-32 g gain 1.3 | `RestMedPlain` | 25.7 | 25.7 | `n14x.*` | `src/crashguard/s4_n14.py` | yes |
| F8 | median error 11.9% against 23.5% and 25.7%; +-32 g gain 1.3 | `RestThirtyTwoGain` | 1.3 | 1.3 | `n14x.*` | `src/crashguard/s4_n14.py` | yes |
| F9 | 1,750 ms earlier; 10.8% retracted; 3% class agreement at 50 ms | `TThreeEarlier` | 1\,750 | 1\,750 | `r3.t3.*` | `src/crashguard/r3_t3.py` | yes |
| F9 | 1,750 ms earlier; 10.8% retracted; 3% class agreement at 50 ms | `TThreeRetract` | 10.8 | 10.8 | `r3.t3.*` | `src/crashguard/r3_t3.py` | yes |
| F9 | 1,750 ms earlier; 10.8% retracted; 3% class agreement at 50 ms | `TThreeNhtsaFifty` | 3 | 3 | `r3.t3.*` | `src/crashguard/r3_t3.py` | yes |
| F10 | 6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9) | `NsSupported` | 6 | 6 | `pp.p1.*` | `src/crashguard/pp_r3_ns3.py` | yes |
| F10 | 6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9) | `NsEarlySfSeven` | 1.87 | 1.87 | `pp.p1.*` | `src/crashguard/pp_r3_ns3.py` | yes |
| F10 | 6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9) | `NsEarlySfNine` | 2.12 | 2.12 | `pp.p1.*` | `src/crashguard/pp_r3_ns3.py` | yes |
| F10 | 6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9) | `NsAirLoSfSeven` | 35 | 35 | `pp.p1.*` | `src/crashguard/pp_r3_ns3.py` | yes |
| F10 | 6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9) | `NsAirHiSfSeven` | 37 | 37 | `pp.p1.*` | `src/crashguard/pp_r3_ns3.py` | yes |
| F10 | 6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9) | `NsAirHiSfNine` | 54 | 54 | `pp.p1.*` | `src/crashguard/pp_r3_ns3.py` | yes |
| F11 | D1 +0.116 custom against +0.021 ns-3 | `XCustomDOneGain` | +0.116 | +0.116 | `rd.x13.*` | `src/crashguard/rd_x13.py` | yes |
| F11 | D1 +0.116 custom against +0.021 ns-3 | `XNsDOneGain` | +0.021 | +0.021 | `rd.x13.*` | `src/crashguard/rd_x13.py` | yes |
| F12 | D1 49.3% against zero-spacing 54.0%; 6.4 s, 17.8% | `TOneDelDOne` | 49.3 | 49.3 | `r3.t1.*, pp.c6.z0.*` | `src/crashguard/r3_t1.py, pp_c6_z0.py` | yes |
| F12 | D1 49.3% against zero-spacing 54.0%; 6.4 s, 17.8% | `TOneDelZ` | 54.0 | 54.0 | `r3.t1.*, pp.c6.z0.*` | `src/crashguard/r3_t1.py, pp_c6_z0.py` | yes |
| F12 | D1 49.3% against zero-spacing 54.0%; 6.4 s, 17.8% | `ZMaxAir` | 6.4 | 6.4 | `r3.t1.*, pp.c6.z0.*` | `src/crashguard/r3_t1.py, pp_c6_z0.py` | yes |
| F12 | D1 49.3% against zero-spacing 54.0%; 6.4 s, 17.8% | `ZMaxShareOne` | 17.8 | 17.8 | `r3.t1.*, pp.c6.z0.*` | `src/crashguard/r3_t1.py, pp_c6_z0.py` | yes |
| F15 | k = 0 to 6, D1 not worse than quick retries | `TimedRuns` | 134\,144 | 134\,144 | `r3.t2.timed.*` | `src/crashguard/r3_t2_timed.py` | yes |
| F15 | k = 0 to 6, D1 not worse than quick retries | `TimedDOneSix` | 9.79 | 9.79 | `r3.t2.timed.*` | `src/crashguard/r3_t2_timed.py` | yes |
| F16 | side accuracy 0.986 against 0.49; NHTSA 0.98; mirror about 0.5 | `RFiveOneAcc` | 0.986 | 0.986 | `r5.l1.*` | `src/crashguard/r5_l1.py` | yes |
| F16 | side accuracy 0.986 against 0.49; NHTSA 0.98; mirror about 0.5 | `RFiveOneRaw` | 0.49 | 0.49 | `r5.l1.*` | `src/crashguard/r5_l1.py` | yes |
| F16 | side accuracy 0.986 against 0.49; NHTSA 0.98; mirror about 0.5 | `RFiveOneNhtsa` | 0.975 | 0.975 | `r5.l1.*` | `src/crashguard/r5_l1.py` | yes |
| F16 | side accuracy 0.986 against 0.49; NHTSA 0.98; mirror about 0.5 | `RFiveMirrorAcc` | 0.50 | 0.50 | `r5.l1.*` | `src/crashguard/r5_l1.py` | yes |
| F17 | recall 0.631 against 0.609; energy ratio 0.25; active share 0.20 | `RFiveThreeRecB` | 0.631 | 0.631 | `r5.l3.*` | `src/crashguard/r5_l3.py` | yes |
| F17 | recall 0.631 against 0.609; energy ratio 0.25; active share 0.20 | `RFiveThreeRecA` | 0.609 | 0.609 | `r5.l3.*` | `src/crashguard/r5_l3.py` | yes |
| F17 | recall 0.631 against 0.609; energy ratio 0.25; active share 0.20 | `RFiveThreeRatio` | 0.25 | 0.25 | `r5.l3.*` | `src/crashguard/r5_l3.py` | yes |
| F17 | recall 0.631 against 0.609; energy ratio 0.25; active share 0.20 | `RFiveThreeShare` | 0.20 | 0.20 | `r5.l3.*` | `src/crashguard/r5_l3.py` | yes |
| F18 | ns-3 edge gain 0.098; worst-cell lower limit -0.009 | `RFiveFourEdge` | 0.098 | 0.098 | `r5.l4.*` | `src/crashguard/r5_l4.py` | yes |
| F18 | ns-3 edge gain 0.098; worst-cell lower limit -0.009 | `RFiveFourWorst` | $-$0.009 | $-$0.009 | `r5.l4.*` | `src/crashguard/r5_l4.py` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveTwoFa` | 0.0095 | 0.0095 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveTwoFaBase` | 0.0062 | 0.0062 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveSixKTwo` | 3.4 | 3.4 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveSixKFour` | 5.6 | 5.6 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveEightQuar` | 1 | 1 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveElevenAccX` | 57 | 57 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F19 | L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89% | `RFiveElevenAccY` | 89 | 89 | `r5.l2.*, l6.*, l8.*, l11.*` | `src/crashguard/r5_l2.py and others` | yes |
| F20 | 1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27) | `RFiveSevenSeq` | 1\,398\,101 | 1\,398\,101 | `r5.l7.*, l8.*, l9.*` | `src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py` | yes |
| F20 | 1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27) | `RFiveEightMax` | 6 | 6 | `r5.l7.*, l8.*, l9.*` | `src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py` | yes |
| F20 | 1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27) | `RFiveEightStates` | 232\,966 | 232\,966 | `r5.l7.*, l8.*, l9.*` | `src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py` | yes |
| F20 | 1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27) | `RFiveNineRho` | 0.24 | 0.24 | `r5.l7.*, l8.*, l9.*` | `src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py` | yes |
| F20 | 1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27) | `RFiveNineRhoLo` | 0.22 | 0.22 | `r5.l7.*, l8.*, l9.*` | `src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py` | yes |
| F20 | 1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27) | `RFiveNineRhoHi` | 0.27 | 0.27 | `r5.l7.*, l8.*, l9.*` | `src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py` | yes |
| F21 | A1 SF9 extra airtime 0.31 to 0.61; +1.4 points; A2 +4.9 points; 52% by one gateway | `AOneAirNine` | 0.61 | 0.61 | `a4.*` | `src/crashguard/a4_a1.py, a4_a2.py` | yes |
| F21 | A1 SF9 extra airtime 0.31 to 0.61; +1.4 points; A2 +4.9 points; 52% by one gateway | `AOneProv` | 1.4 | 1.4 | `a4.*` | `src/crashguard/a4_a1.py, a4_a2.py` | yes |
| F21 | A1 SF9 extra airtime 0.31 to 0.61; +1.4 points; A2 +4.9 points; 52% by one gateway | `ATwoGain` | 4.9 | 4.9 | `a4.*` | `src/crashguard/a4_a1.py, a4_a2.py` | yes |
| F21 | A1 SF9 extra airtime 0.31 to 0.61; +1.4 points; A2 +4.9 points; 52% by one gateway | `ATwoOne` | 52 | 52 | `a4.*` | `src/crashguard/a4_a1.py, a4_a2.py` | yes |
