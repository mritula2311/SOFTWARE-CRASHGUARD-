# Formal models rerun (V2.1, V2.2)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Outcome, wall time and peak memory of every Tamarin and ProVerif run repeated in the verification run. |
| Evidence labels used | none (this file reports no result) |
<!-- header:end -->

Rerun on 2026-11-15 with `scripts/vf_formal_rerun.sh` (one process per lemma, one thread, 5 GB heap limit, Tamarin 1.12.0, Maude 3.5.1, ProVerif 2.05, WSL2 Ubuntu 24.04). Raw outputs: `formal/rerun_vf/`. Stored outcomes of the paper: `results.json` keys `r3.t2.sec.*` and `a4.a3.proverif.*`.

| Group | Lemma or model | Outcome | Wall time (s) | Peak memory (MB) | Command |
|---|---|---|---|---|---|
| auth | executable | trace found (exists-trace lemma verified) | 0 | 32 | `tamarin-prover  --prove=executable formal/crash_alert_auth.spthy +RTS -N1 -M5g -RTS ; time` |
| auth | executable_M0 | trace found (exists-trace lemma verified) | 1 | 32 | `tamarin-prover -D=M0 --prove=executable formal/crash_alert_auth.spthy +RTS -N1 -M5g -RTS ;` |
| auth | L1_alert_authenticity | proved | 0 | 30 | `tamarin-prover  --prove=L1_alert_authenticity formal/crash_alert_auth.spthy +RTS -N1 -M5g ` |
| auth | L1_alert_authenticity_M0 | attack or trace found | 1 | 31 | `tamarin-prover -D=M0 --prove=L1_alert_authenticity formal/crash_alert_auth.spthy +RTS -N1 ` |
| auth | L2_ack_authenticity | proved | 0 | 30 | `tamarin-prover  --prove=L2_ack_authenticity formal/crash_alert_auth.spthy +RTS -N1 -M5g -R` |
| auth | L2_ack_authenticity_M0 | attack or trace found | 0 | 31 | `tamarin-prover -D=M0 --prove=L2_ack_authenticity formal/crash_alert_auth.spthy +RTS -N1 -M` |
| auth | L3_no_cross_vehicle_suppression | proved | 1 | 30 | `tamarin-prover  --prove=L3_no_cross_vehicle_suppression formal/crash_alert_auth.spthy +RTS` |
| auth | L3_no_cross_vehicle_suppression_M0 | attack or trace found | 0 | 32 | `tamarin-prover -D=M0 --prove=L3_no_cross_vehicle_suppression formal/crash_alert_auth.spthy` |
| bootctr | executable_after_car_reboot | trace found (exists-trace lemma verified) | 65 | 3195 | `tamarin-prover  --prove=executable_after_car_reboot formal/crash_alert_fresh_bootctr.spthy` |
| bootctr | executable_ts | trace found (exists-trace lemma verified) | 6 | 221 | `tamarin-prover  --prove=executable_ts formal/crash_alert_fresh_bootctr.spthy +RTS -N1 -M5g` |
| bootctr | L5_car_alert_ids_unique | undecided (time limit or memory) | 951 | 5578 | `tamarin-prover  --prove=L5_car_alert_ids_unique formal/crash_alert_fresh_bootctr.spthy +RT` |
| carid | L5_car_alert_ids_unique | undecided (time limit or memory) | 300 | 5301 | `tamarin-prover  --prove=L5_car_alert_ids_unique formal/crash_alert_carid.spthy +RTS -N1 -M` |
| carid | L5_car_alert_ids_unique_BOOT | undecided (time limit or memory) | 300 | 5301 | `tamarin-prover -D=BOOT --prove=L5_car_alert_ids_unique formal/crash_alert_carid.spthy +RTS` |
| fresh | executable_after_car_reboot | trace found (exists-trace lemma verified) | 49 | 2452 | `tamarin-prover  --prove=executable_after_car_reboot formal/crash_alert_fresh.spthy +RTS -N` |
| fresh | executable_ts | trace found (exists-trace lemma verified) | 2 | 65 | `tamarin-prover  --prove=executable_ts formal/crash_alert_fresh.spthy +RTS -N1 -M5g -RTS ; ` |
| fresh | L4_replay_outside_window | proved | 263 | 4895 | `tamarin-prover  --prove=L4_replay_outside_window formal/crash_alert_fresh.spthy +RTS -N1 -` |
| fresh | L4b_at_most_once | proved | 2 | 69 | `tamarin-prover  --prove=L4b_at_most_once formal/crash_alert_fresh.spthy +RTS -N1 -M5g -RTS` |
| fresh | L5_car_alert_ids_unique | undecided (time limit or memory) | 300 | 5380 | `tamarin-prover  --prove=L5_car_alert_ids_unique formal/crash_alert_fresh.spthy +RTS -N1 -M` |
| fresh | L5_no_double_accept_with_car_reboot | proved | 3 | 79 | `tamarin-prover  --prove=L5_no_double_accept_with_car_reboot formal/crash_alert_fresh.spthy` |
| fresh | L6_base_reboot_replay | attack or trace found | 4 | 97 | `tamarin-prover  --prove=L6_base_reboot_replay formal/crash_alert_fresh.spthy +RTS -N1 -M5g` |
| fresh | L7_no_time_alert_can_be_stale | trace found (exists-trace lemma verified) | 15 | 667 | `tamarin-prover  --prove=L7_no_time_alert_can_be_stale formal/crash_alert_fresh.spthy +RTS ` |
| prov | executable_alert | trace found (exists-trace lemma verified) | 0 | 33 | `tamarin-prover  --prove=executable_alert formal/crash_alert_prov.spthy +RTS -N1 -M5g -RTS ` |
| prov | executable_prov | trace found (exists-trace lemma verified) | 0 | 33 | `tamarin-prover  --prove=executable_prov formal/crash_alert_prov.spthy +RTS -N1 -M5g -RTS ;` |
| prov | executable_prov_repeat | trace found (exists-trace lemma verified) | 1 | 32 | `tamarin-prover  --prove=executable_prov_repeat formal/crash_alert_prov.spthy +RTS -N1 -M5g` |
| prov | P1_prov_authenticity | proved | 1 | 32 | `tamarin-prover  --prove=P1_prov_authenticity formal/crash_alert_prov.spthy +RTS -N1 -M5g -` |
| prov | P2_ack_authenticity | proved | 0 | 33 | `tamarin-prover  --prove=P2_ack_authenticity formal/crash_alert_prov.spthy +RTS -N1 -M5g -R` |
| prov | P3_no_cross_vehicle_suppression | proved | 1 | 32 | `tamarin-prover  --prove=P3_no_cross_vehicle_suppression formal/crash_alert_prov.spthy +RTS` |
| prov | P4_no_type_confusion_alert | proved | 0 | 33 | `tamarin-prover  --prove=P4_no_type_confusion_alert formal/crash_alert_prov.spthy +RTS -N1 ` |
| prov_fresh | executable_ts | trace found (exists-trace lemma verified) | 2 | 64 | `tamarin-prover  --prove=executable_ts formal/crash_alert_prov_fresh.spthy +RTS -N1 -M5g -R` |
| prov_fresh | L4_replay_outside_window | proved | 259 | 4764 | `tamarin-prover  --prove=L4_replay_outside_window formal/crash_alert_prov_fresh.spthy +RTS ` |
| prov_fresh | L4b_at_most_once | proved | 2 | 69 | `tamarin-prover  --prove=L4b_at_most_once formal/crash_alert_prov_fresh.spthy +RTS -N1 -M5g` |
| prov_fresh | L5_no_double_accept_with_car_reboot | proved | 2 | 79 | `tamarin-prover  --prove=L5_no_double_accept_with_car_reboot formal/crash_alert_prov_fresh.` |
| prov_fresh | L6_base_reboot_replay | attack or trace found | 3 | 98 | `tamarin-prover  --prove=L6_base_reboot_replay formal/crash_alert_prov_fresh.spthy +RTS -N1` |
| prov_nodomain | P4_no_type_confusion_alert | attack or trace found | 1 | 32 | `tamarin-prover  --prove=P4_no_type_confusion_alert formal/crash_alert_prov_nodomain.spthy ` |
| proverif | carid_bootctr_nowrite | attack found (false) | 0 | 8 | `proverif formal/proverif/carid_bootctr_nowrite.pv ; time limit 320 s` |
| proverif | carid_bootctr_same_epoch | proved; proved | 0 | 9 | `proverif formal/proverif/carid_bootctr_same_epoch.pv ; time limit 320 s` |
| proverif | carid_frozen_chain | undecided (time limit) | 320 | 1303 | `proverif formal/proverif/carid_frozen_chain.pv ; time limit 320 s` |
| proverif | carid_frozen_next_epoch | proved | 0 | 9 | `proverif formal/proverif/carid_frozen_next_epoch.pv ; time limit 320 s` |
| proverif | carid_frozen_same_epoch | attack found (false); proved | 0 | 9 | `proverif formal/proverif/carid_frozen_same_epoch.pv ; time limit 320 s` |
| ratchet | forward_secrecy | undecided (time limit or memory) | 280 | 5777 | `tamarin-prover  --prove=forward_secrecy formal/ratchet.spthy +RTS -N1 -M5g -RTS ; time lim` |
| ratchet3 | ack_binding | undecided (time limit or memory) | 281 | 5424 | `tamarin-prover  --prove=ack_binding formal/ratchet3.spthy +RTS -N1 -M5g -RTS ; time limit ` |
| ratchet3 | authenticity | undecided (time limit or memory) | 280 | 5432 | `tamarin-prover  --prove=authenticity formal/ratchet3.spthy +RTS -N1 -M5g -RTS ; time limit` |
| ratchet3 | executable | undecided (time limit or memory) | 280 | 5301 | `tamarin-prover  --prove=executable formal/ratchet3.spthy +RTS -N1 -M5g -RTS ; time limit 2` |
| ratchet3 | forward_secrecy | undecided (time limit or memory) | 280 | 5538 | `tamarin-prover  --prove=forward_secrecy formal/ratchet3.spthy +RTS -N1 -M5g -RTS ; time li` |
