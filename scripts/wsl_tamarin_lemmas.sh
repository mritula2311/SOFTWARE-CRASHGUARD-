#!/bin/bash
# usage: wsl_tamarin_lemmas.sh <model.spthy (in WSL path)> <outdir in WSL> <timeout_s> <lemma>... ; extra args after "--" go to tamarin
# One Tamarin run per lemma (single-threaded: the default thread count crashed the WSL VM), each with its own time limit; results in <outdir>/<lemma>.txt
export PATH=/usr/local/bin:/usr/bin:/bin
export MAUDE_LIB=/opt/maude
model="$1"; outdir="$2"; tmo="$3"; shift 3
mkdir -p "$outdir"
extra=()
lemmas=()
seen=0
for a in "$@"; do
  if [ "$a" == "--" ]; then seen=1; continue; fi
  if [ $seen -eq 1 ]; then extra+=("$a"); else lemmas+=("$a"); fi
done
cd /tmp
for l in "${lemmas[@]}"; do
  { echo "lemma: $l"; echo "command: tamarin-prover ${extra[*]} --prove=$l $model"; } > "$outdir/$l.txt"
  start=$(date +%s)
  timeout "$tmo" /opt/tamarin/tamarin-prover "${extra[@]}" --prove="$l" "$model" +RTS -N1 -M5g -RTS >> "$outdir/$l.txt" 2>&1
  echo "exit code: $? ; wall time $(( $(date +%s) - start )) s" >> "$outdir/$l.txt"
done
echo finished > "$outdir/DONE"
