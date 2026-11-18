#!/bin/bash
# R6-4: footprint of the decision path on the ESP32 (Xtensa) with the Espressif GCC 12.2.0 toolchain (user-level install through PlatformIO, no root). usage (WSL): bash scripts/r6_footprint.sh
set -e
cd "$(dirname "$0")/.."
XT=~/.platformio/packages/toolchain-xtensa-esp32/bin/xtensa-esp32-elf
OUT=build/r6fp
rm -rf $OUT && mkdir -p $OUT
CF="-std=c99 -Os -mlongcalls -ffunction-sections -fdata-sections -fstack-usage -ffp-contract=off -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare"
$XT-gcc --version | head -1 > $OUT/toolchain.txt
for f in firmware_rd/cg_rd firmware_rd/tweetnacl firmware_rd/cg_stubs firmware_r6/cg_r6 firmware_r6/cg_r6_anchor; do
  b=$(basename $f)
  $XT-gcc $CF -c $f.c -o $OUT/$b.o 2> $OUT/$b.warn
  $XT-size -A $OUT/$b.o > $OUT/$b.size.txt
  $XT-nm -S --size-sort -C $OUT/$b.o > $OUT/$b.nm.txt
  [ -f $b.su ] && mv $b.su $OUT/$b.su
done
# linked image without the C start-up code (the linker of this toolchain stops with a segmentation fault under --gc-sections in WSL, so unused functions stay in the image; sizes of the used path are taken per function from nm)
$XT-gcc -mlongcalls -nostartfiles -Wl,-e,main -T firmware_r6/esp32_footprint.ld -Wl,-Map=$OUT/image.map -o $OUT/image.elf $OUT/cg_r6.o $OUT/cg_rd.o $OUT/cg_r6_anchor.o $OUT/tweetnacl.o $OUT/cg_stubs.o -Wl,--start-group -lm -lgcc -lc -Wl,--end-group > $OUT/link.txt 2>&1 || echo "LINK_FAILED" >> $OUT/link.txt
if [ -f $OUT/image.elf ]; then $XT-size -A $OUT/image.elf > $OUT/image.size.txt; $XT-nm -S --size-sort -C $OUT/image.elf > $OUT/image.nm.txt; fi
ls $OUT
