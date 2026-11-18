#!/bin/bash
# usage: wsl_run_tamarin.sh <model.spthy> <outfile> [extra tamarin args...]   (run inside WSL; Tamarin 1.12.0 in /opt/tamarin, Maude 3.5.1 in /opt/maude)
export PATH=/usr/local/bin:/usr/bin:/bin
export MAUDE_LIB=/opt/maude
model="$1"; out="$2"; shift 2
{
  /opt/tamarin/tamarin-prover --version 2>&1 | grep -E "Tamarin version|Maude version"
  echo "command: tamarin-prover $* --prove $model"
  timeout 3000 /opt/tamarin/tamarin-prover "$@" --prove "$model"
  echo "exit code: $?"
} > "$out" 2>&1
