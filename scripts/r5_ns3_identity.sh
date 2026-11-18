#!/bin/bash
# Code verification of the ns-3 change of round 5 (V16 section 10): the earlier policies give byte-identical output with the old and the new binary on three seeds.
# usage (in WSL): bash scripts/r5_ns3_identity.sh <old binary> <events file>
OLD="$1"
EV="$2"
cd ~/ns3work/ns-3-dev || exit 1
NEW=./build/scratch/ns3.48-xsim_alert-optimized
bad=0
n=0
for pol in p1 quick d1 r3s r3t r3a lorawan; do
  for seed in 3 17 41; do
    for sf in 7 9; do
      args="--n=60 --sf=$sf --p=0.3 --radius=1500 --rate=10 --duty=0.01 --seed=$seed --policy=$pol --events=$EV --sensShipped=1"
      a=$($OLD $args 2>/dev/null | md5sum | cut -c1-32)
      b=$($NEW $args 2>/dev/null | md5sum | cut -c1-32)
      n=$((n+1))
      if [ "$a" != "$b" ]; then echo "DIFF $pol seed $seed sf $sf"; bad=$((bad+1)); fi
    done
  done
done
echo "compared $n runs, $bad differences"
