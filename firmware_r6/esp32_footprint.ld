/* linker script for the footprint image only (ESP32 memory ranges; not a bootable image) */
MEMORY { iram : ORIGIN = 0x40080000, LENGTH = 128K
         dram : ORIGIN = 0x3FFB0000, LENGTH = 128K
         irom : ORIGIN = 0x400D0000, LENGTH = 3M
         drom : ORIGIN = 0x3F400000, LENGTH = 4M }
SECTIONS {
  .text : { *(.literal .text .literal.* .text.*) } > irom
  .rodata : { *(.rodata .rodata.* .rodata1) } > drom
  .data : { *(.data .data.*) } > dram
  .bss : { *(.bss .bss.* COMMON) } > dram
}
