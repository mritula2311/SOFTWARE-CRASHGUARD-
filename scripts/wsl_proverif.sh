#!/bin/bash
# usage: wsl_proverif.sh <model.pv (WSL path)> <outfile (WSL path)> [timeout_s]   (run inside WSL; ProVerif 2.05 built in /opt/pv/proverif2.05)
tmo="${3:-600}"
{
  echo "tool: $(/opt/pv/proverif2.05/proverif -help 2>&1 | head -1)"
  echo "command: proverif $1"
  start=$(date +%s)
  timeout "$tmo" /opt/pv/proverif2.05/proverif "$1"
  echo "exit code: $? ; wall time $(( $(date +%s) - start )) s"
} > "$2" 2>&1
