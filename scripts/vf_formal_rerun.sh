#!/bin/bash
# V2: rerun the formal models cited in the paper (run inside WSL, foreground, one process at a time).
#   usage: bash scripts/vf_formal_rerun.sh <repo root in WSL> [group ...]
# groups: auth fresh bootctr prov carid ratchet proverif   (default: all)
# For each Tamarin lemma: one process, one thread (+RTS -N1 -M5g), its own time limit, peak memory from /usr/bin/time -v.
# Outputs: formal/rerun_vf/<group>/<lemma>.txt  (first lines: lemma, command; last lines: exit code, wall time, peak memory)
export PATH=/usr/local/bin:/usr/bin:/bin
export MAUDE_LIB=/opt/maude
ROOT="$1"; shift
GROUPS_WANTED="${*:-auth fresh bootctr prov carid ratchet proverif}"
OUT="$ROOT/formal/rerun_vf"
TAM=/opt/tamarin/tamarin-prover
PV=/opt/pv/proverif2.05/proverif

run_tam() { # group model define timeout lemma
  local g="$1" m="$2" d="$3" t="$4" l="$5" f
  mkdir -p "$OUT/$g"
  f="$OUT/$g/${l}${d:+_${d#-D=}}.txt"
  { echo "lemma: $l"; echo "command: tamarin-prover $d --prove=$l formal/$m +RTS -N1 -M5g -RTS ; time limit $t s"; } > "$f"
  cd "$ROOT"
  start=$(date +%s)
  /usr/bin/time -v -o "$f.time" timeout "$t" $TAM $d --prove="$l" "formal/$m" +RTS -N1 -M5g -RTS >> "$f" 2>&1
  rc=$?
  echo "exit code: $rc ; wall time $(( $(date +%s) - start )) s ; peak memory $(grep 'Maximum resident' "$f.time" | awk '{print int($6/1024)}') MB" >> "$f"
  rm -f "$f.time"
  echo "$g $m $d $l rc=$rc"
}

for g in $GROUPS_WANTED; do
  case $g in
    auth)
      for l in executable L1_alert_authenticity L2_ack_authenticity L3_no_cross_vehicle_suppression; do
        run_tam auth crash_alert_auth.spthy "-D=M0" 300 $l
        run_tam auth crash_alert_auth.spthy "" 300 $l
      done;;
    fresh)
      for l in executable_ts executable_after_car_reboot L4_replay_outside_window L4b_at_most_once L5_no_double_accept_with_car_reboot L6_base_reboot_replay L7_no_time_alert_can_be_stale; do
        run_tam fresh crash_alert_fresh.spthy "" 600 $l
      done
      run_tam fresh crash_alert_fresh.spthy "" 300 L5_car_alert_ids_unique;;
    bootctr)
      for l in executable_ts executable_after_car_reboot; do run_tam bootctr crash_alert_fresh_bootctr.spthy "" 300 $l; done
      run_tam bootctr crash_alert_fresh_bootctr.spthy "" 950 L5_car_alert_ids_unique;;
    prov)
      for l in executable_prov executable_prov_repeat executable_alert P1_prov_authenticity P2_ack_authenticity P3_no_cross_vehicle_suppression P4_no_type_confusion_alert; do
        run_tam prov crash_alert_prov.spthy "" 300 $l
      done
      run_tam prov_nodomain crash_alert_prov_nodomain.spthy "" 300 P4_no_type_confusion_alert
      for l in executable_ts L4_replay_outside_window L4b_at_most_once L5_no_double_accept_with_car_reboot L6_base_reboot_replay; do
        run_tam prov_fresh crash_alert_prov_fresh.spthy "" 600 $l
      done;;
    carid)
      run_tam carid crash_alert_carid.spthy "" 300 L5_car_alert_ids_unique
      run_tam carid crash_alert_carid.spthy "-D=BOOT" 300 L5_car_alert_ids_unique;;
    ratchet)
      run_tam ratchet ratchet.spthy "" 280 forward_secrecy
      for l in executable forward_secrecy authenticity ack_binding; do run_tam ratchet3 ratchet3.spthy "" 280 $l; done;;
    proverif)
      mkdir -p "$OUT/proverif"; cd "$ROOT"
      for m in carid_frozen_same_epoch carid_frozen_next_epoch carid_bootctr_same_epoch carid_bootctr_nowrite carid_frozen_chain; do
        f="$OUT/proverif/$m.txt"
        { echo "tool: $($PV -help 2>&1 | head -1)"; echo "command: proverif formal/proverif/$m.pv ; time limit 320 s"; } > "$f"
        start=$(date +%s)
        /usr/bin/time -v -o "$f.time" timeout 320 $PV "formal/proverif/$m.pv" >> "$f" 2>&1
        rc=$?
        echo "exit code: $rc ; wall time $(( $(date +%s) - start )) s ; peak memory $(grep 'Maximum resident' "$f.time" | awk '{print int($6/1024)}') MB" >> "$f"
        rm -f "$f.time"
        echo "proverif $m rc=$rc"
      done;;
  esac
done
echo finished > "$OUT/DONE_$(echo $GROUPS_WANTED | tr ' ' '_')"
