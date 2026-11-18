"""R6-4 (PREREGISTRATION_V17 section 6): reads the build artifacts of ``scripts/r6_footprint.sh`` (Espressif GCC 12.2.0 for Xtensa ESP32, -Os, -mlongcalls, -fstack-usage; run in WSL) and writes keys r6.fp.* and
docs/03_results/ROUND6_FOOTPRINT.md. Sizes are build artifacts (MEASURED_SOFTWARE). Executed instructions (emulator) and any energy estimate: NOT_RUN (no emulator is installed here).

    wsl bash scripts/r6_footprint.sh ; python -m crashguard.r6_footprint
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
B = ROOT / "build" / "r6fp"
SRC = "src/crashguard/r6_footprint.py"
KEEP = ROOT / "results" / "tables" / "r6_footprint"


def nm_sizes(p: Path) -> dict[str, int]:
    out = {}
    for ln in p.read_text().splitlines():
        m = re.match(r"([0-9a-f]+) ([0-9a-f]+) (\w) (.+)$", ln)
        if m:
            out[m.group(4)] = int(m.group(2), 16)
    return out


def su(p: Path) -> dict[str, int]:
    out = {}
    for ln in p.read_text().splitlines():
        parts = ln.split("\t")
        out[parts[0].split(":")[-1]] = int(parts[1])
    return out


def section_sizes(p: Path) -> dict[str, int]:
    out = {}
    for ln in p.read_text().splitlines():
        m = re.match(r"(\S+)\s+(\d+)\s+(\d+)$", ln)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def main() -> None:
    nm = {}
    for f in ("cg_rd", "cg_r6", "tweetnacl"):
        nm.update(nm_sizes(B / f"{f}.nm.txt"))
    stack = {}
    for f in ("cg_rd", "cg_r6", "tweetnacl"):
        stack.update(su(B / f"{f}.su"))
    img = section_sizes(B / "image.size.txt")
    r6 = section_sizes(B / "cg_r6.size.txt")
    tool = (B / "toolchain.txt").read_text().strip()
    forest_rodata = sum(v for k, v in r6.items() if k.startswith(".rodata"))
    chain = ["cg_micro_verify", "cg_micro_tag", "cg_hmac_sha256", "cg_sha256", "sha_block"]
    ent = []

    def add(name, v, unit, note, origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"r6.fp.{name}", value=v, unit=unit, origin=origin, source_file=SRC, notes=note))

    add("toolchain", tool, "text", "compiler used (Espressif crosstool-NG, installed at user level through PlatformIO)")
    add("flags", "-std=c99 -Os -mlongcalls -ffunction-sections -fdata-sections -fstack-usage -ffp-contract=off", "text", "compile flags")
    add("code.micro_tag_bytes", nm["cg_micro_tag"], "bytes", ".text of cg_micro_tag (object file, before linking; literals are extra)")
    add("code.micro_pack_bytes", nm["cg_micro_pack"], "bytes", ".text")
    add("code.micro_verify_bytes", nm["cg_micro_verify"], "bytes", ".text")
    add("code.hmac_sha256_path_bytes", nm["cg_hmac_sha256"] + nm["cg_sha256"] + nm["sha_block"], "bytes", ".text of cg_hmac_sha256, cg_sha256 and sha_block")
    add("code.forest_function_bytes", nm["cg_forest"], "bytes", ".text of the 15-tree forest evaluation")
    add("rodata.forest_bytes", forest_rodata, "bytes", "15 trees, 1,749 nodes: feature, threshold, left, right and root arrays (const, flash)")
    add("code.alert_encode_bytes", nm["cg_encode_alert"], "bytes", ".text of the 97-byte alert encoder")
    add("code.freshness_bytes", nm["cg_fresh_accept"], "bytes", ".text of the freshness rule")
    add("image.text_bytes", img[".text"], "bytes", "linked image (no start-up code, newlib memcpy, floor and ceil and the Ed25519 verifier included; the linker could not discard unused functions)")
    add("image.rodata_bytes", img[".rodata"], "bytes", "linked image .rodata")
    add("image.bss_bytes", img[".bss"], "bytes", "linked image static RAM (.bss) of the footprint anchor; caller-owned structures (the freshness ring, keys) come on top")
    add("image.data_bytes", img.get(".data", 0), "bytes", "linked image initialised RAM")
    add("image.flash_total_bytes", img[".text"] + img[".rodata"] + img.get(".data", 0), "bytes", ".text + .rodata + .data of the linked image")
    for fn in ("cg_micro_verify", "cg_micro_tag", "cg_hmac_sha256", "cg_sha256", "sha_block", "cg_forest", "cg_encode_alert", "cg_fresh_accept", "cg_tag_ok", "cg_cluster_check"):
        add(f"stack.{fn}_bytes", stack[fn], "bytes", "-fstack-usage frame of this function (static)")
    add("stack.micro_verify_chain_bytes", sum(stack[f] for f in chain), "bytes", "sum of the frames cg_micro_verify > cg_micro_tag > cg_hmac_sha256 > cg_sha256 > sha_block (upper bound of the call chain; windowed-register spills not counted)")
    add("emulated.instructions_per_decision", "NOT_RUN", "status", "no ESP32 emulator is installed here (no QEMU with the Xtensa target, no root)", "NOT_RUN")
    add("emulated.instructions_per_hmac", "NOT_RUN", "status", "same reason", "NOT_RUN")
    add("energy.analytical_estimate", "NOT_RUN", "status", "needs instruction or cycle counts; none are available", "NOT_RUN")
    record_many(ent, purge_prefixes=("r6.fp.",))
    KEEP.mkdir(parents=True, exist_ok=True)
    for f in B.iterdir():
        if f.suffix in (".txt", ".su", ".map", ".warn"):
            shutil.copy(f, KEEP / f.name)
    rows = [(e["name"][len("r6.fp.") :], e["value"], e["unit"], e["notes"]) for e in ent]
    L = ["# Round 6, R6-4: ESP32 build footprint of the decision path", "", "<!-- header:start -->", "<!-- header:end -->", "",
         f"Generated by `python -m crashguard.r6_footprint` from `scripts/r6_footprint.sh` (keys `r6.fp.*`). Compiler: {tool}. Sizes are build artifacts of the C decision path "
         "(`firmware_rd/cg_rd.c`, `firmware_r6/cg_r6.c`, `firmware_export/crashguard_rf.h`, `firmware_rd/tweetnacl.c`) compiled for the Xtensa ESP32 target; they are not measurements on a board. "
         "Raw outputs are in `results/tables/r6_footprint/`. Executed instructions, timing and energy are NOT_RUN: no emulator is installed here. "
         "The code uses double-precision arithmetic in the time-on-air and loss-estimate functions, which the ESP32 runs in software; a single-precision port is NOT_RUN (stated in `firmware_rd/cg_rd.h`).", "",
         "| Quantity | Value | Unit | Note |", "|---|---:|---|---|"]
    for n, v, u, note in rows:
        L.append(f"| {n} | {v} | {u} | {note} |")
    L += ["", "## Reading", "",
          f"1. The forest is {forest_rodata:,} bytes of constant data in flash (about {forest_rodata / 1024:.1f} KiB); the HMAC path and the micro-confirm code are a few hundred bytes of code.",
          "2. The largest stack frame is `cg_hmac_sha256` (it builds the padded inner and outer messages on the stack); the chain of the micro-confirm check needs "
          f"{sum(stack[f] for f in chain)} bytes by this static sum.",
          "3. The linker of this toolchain stopped with a segmentation fault under `--gc-sections` in WSL, so the linked image keeps unused functions; the per-function rows give the size of the used path.", ""]
    (ROOT / "docs" / "03_results" / "ROUND6_FOOTPRINT.md").write_text("\n".join(L), encoding="utf-8")
    print({n: v for n, v, _u, _n in rows if n.startswith(("image.flash", "rodata", "stack.micro", "code.micro"))})


if __name__ == "__main__":
    main()
