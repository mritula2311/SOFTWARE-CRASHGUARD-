#!/bin/bash
# object sizes of the firmware path for the HOST (x86-64), -Os
cd "$(dirname "$0")"
mkdir -p ../build/fw/os
for f in cg_rd tweetnacl; do gcc -std=c99 -Os -ffp-contract=off -c $f.c -o ../build/fw/os/$f.o 2>/dev/null; size ../build/fw/os/$f.o | tail -1; done
