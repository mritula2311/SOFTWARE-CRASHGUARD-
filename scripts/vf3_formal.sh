#!/bin/bash
# Finalize F1: the index variants of the micro-confirm models (ProVerif, Tamarin), one process at a time in the foreground. usage: bash scripts/vf3_formal.sh <repo root in WSL>
export PATH=/usr/local/bin:/usr/bin:/bin
export MAUDE_LIB=/opt/maude
ROOT="$1"
OUT="$ROOT/formal/out/vf3"
mkdir -p "$OUT"
cd "$ROOT"
run() {
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
run pv_micro_confirm_index 300 /opt/pv/proverif2.05/proverif formal/proverif/vf3_micro_confirm_index.pv
run tam_micro_confirm_index 600 /opt/tamarin/tamarin-prover formal/vf3_micro_confirm_index.spthy --prove +RTS -N1 -M5g -RTS
