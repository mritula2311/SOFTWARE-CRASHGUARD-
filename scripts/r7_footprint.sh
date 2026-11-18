#!/bin/bash
# Round 7 B3: flash and RAM footprint of the node pseudonym routine on the ESP32 (Xtensa) with the Espressif GCC 12.2.0 toolchain, as scripts/r6_footprint.sh (compile only; no emulator, so instruction counts and energy are NOT_RUN).
# usage (WSL, from the repository root): bash scripts/r7_footprint.sh
set -e
cd "$(dirname "$0")/.."
XT=~/.platformio/packages/toolchain-xtensa-esp32/bin/xtensa-esp32-elf
OUT=build/r7fp
rm -rf $OUT && mkdir -p $OUT
CF="-std=c99 -Os -mlongcalls -ffunction-sections -fdata-sections -fstack-usage -ffp-contract=off -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare"
$XT-gcc --version | head -1 > $OUT/toolchain.txt
for f in firmware_rd/cg_rd firmware_r7/cg_r7; do
  b=$(basename $f)
  $XT-gcc $CF -c $f.c -o $OUT/$b.o 2> $OUT/$b.warn
  $XT-size -A $OUT/$b.o > $OUT/$b.size.txt
  $XT-nm -S --size-sort -C $OUT/$b.o > $OUT/$b.nm.txt
  [ -f $b.su ] && mv $b.su $OUT/$b.su
done
ls $OUT
