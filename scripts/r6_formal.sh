#!/bin/bash
# R6-1 and R6-3: run the round-6 prover models in WSL, one process at a time (foreground), with time and peak memory. usage: bash scripts/r6_formal.sh <repo root in WSL>
# Outputs: formal/out/r6/<name>.txt (first lines: command; last line: exit code, wall time, peak memory)
export PATH=/usr/local/bin:/usr/bin:/bin
export MAUDE_LIB=/opt/maude
ROOT="$1"
OUT="$ROOT/formal/out/r6"
mkdir -p "$OUT"
cd "$ROOT"
run() { # name timeout command...
  local name="$1" t="$2"; shift 2
  local f="$OUT/$name.txt"
  { echo "command: $*"; } > "$f"
  local start=$(date +%s)
  /usr/bin/time -v -o "$f.time" timeout "$t" "$@" >> "$f" 2>&1
  local rc=$?
  echo "exit code: $rc ; wall time $(( $(date +%s) - start )) s ; peak memory $(grep 'Maximum resident' "$f.time" | awk '{print int($6/1024)}') MB" >> "$f"
  rm -f "$f.time"
  echo "$name rc=$rc"
}
PV=/opt/pv/proverif2.05/proverif
TAM=/opt/tamarin/tamarin-prover
run pv_micro_confirm 300 $PV formal/proverif/r6_micro_confirm.pv
run pv_micro_confirm_control 300 $PV formal/proverif/r6_micro_confirm_control.pv
run pv_ratchet_auth 300 $PV formal/proverif/r6_ratchet_auth.pv
run pv_ratchet_secrecy 300 $PV formal/proverif/r6_ratchet_secrecy.pv
run tam_micro_confirm 300 $TAM formal/r6_micro_confirm.spthy --prove +RTS -N1 -M5g -RTS
run tam_micro_confirm_control 300 $TAM -D=CONTROL formal/r6_micro_confirm.spthy --prove +RTS -N1 -M5g -RTS
