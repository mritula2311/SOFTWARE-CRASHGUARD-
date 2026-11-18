#!/bin/bash
# Host build of the D6 firmware decision path (gcc in WSL). Output: build/fw/cg_rd_cli
set -e
cd "$(dirname "$0")"
mkdir -p ../build/fw
gcc -std=c99 -O2 -ffp-contract=off -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -o ../build/fw/cg_rd_cli cg_rd.c cg_rd_cli.c cg_stubs.c tweetnacl.c -lm
echo built ../build/fw/cg_rd_cli
