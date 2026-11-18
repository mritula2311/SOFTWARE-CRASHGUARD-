"""Round 7b G0.2 and G5 (ANALYTICAL): transmit-power margin and the design notes. Keys r7b.g0.* and r7b.g5.*.

    python -m crashguard.r7b_g0
"""
from __future__ import annotations

import json
from pathlib import Path

from crashguard.lora import airtime_ms
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7b_g0.py"
SF_STEP_DB = (137.0 - 123.0) / 5.0  # simulators' sensitivity step per spreading factor, -123 to -137 dBm over SF7 to SF12 (2.8 dB)


def main() -> None:
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=name, value=v, unit=unit, origin="ANALYTICAL", source_file=SRC, notes=note))

    # G0.2: dipole (2.15 dBi) node, limit 10 mW e.r.p. = 10 dBm e.r.p.
    ptx_sim = 14.0
    dipole_dbi = 2.15
    erp = ptx_sim + dipole_dbi - 2.15
    red = erp - 10.0
    add("r7b.g0.power.sim_ptx_dbm", ptx_sim, "dBm", "transmit power of every stored simulation (ASSUMPTIONS.md)")
    add("r7b.g0.power.max_compliant_ptx_dipole_dbm", ptx_sim - red, "dBm", "a compliant dipole node transmits at most 10 dBm (e.r.p. limit 10 mW, antenna 2.15 dBi = 0 dBd)")
    add("r7b.g0.power.extra_margin_db", red, "dB", "the stored link results assume this much more margin than a compliant dipole node has: an optimistic bound")
    add("r7b.g0.power.sf_step_db", SF_STEP_DB, "dB", "sensitivity step per spreading factor in the simulators")
    add("r7b.g0.power.extra_margin_sf_steps", red / SF_STEP_DB, "SF steps", "4.00 dB / 2.8 dB; the earlier 0.7 of a step (finalize run, vf3.india) is for the 0 dBi case, 1.85 dB")
    # G5.2: pseudonym length
    n_v, m = 1000, 16
    for L in (4, 5):
        p = 1.0 - (1.0 - 2.0 ** (-8 * L)) ** ((n_v - 1) * m)
        add(f"r7b.g5.pseudonym.collision_L{L}", p, "probability", "P = 1 - (1 - 2^-8L)^((n-1) m), n = 1000, m = 16 (V18 formula)")
    for sf in (7, 8, 9):
        # the pseudonym is 4 bytes in the 97-byte alert and the 26-byte ACK; the extra byte makes them 98 and 27 bytes; the flash and cancel carry 2 bytes
        for n0 in (97, 26, 14):
            a0, a1 = airtime_ms(n0, sf), airtime_ms(n0 + 1, sf)
            add(f"r7b.g5.pseudonym.sf{sf}.b{n0}.extra_ms", a1 - a0, "ms", f"airtime of {n0 + 1} bytes minus {n0} bytes, SF{sf}")
    # G5.1: reboot resolution by a table keyed on the pseudonym (design note, not implemented in frozen code)
    boots = 3
    entries = n_v * boots * m
    t_scan = R["r7.b.resync.python.one_frame_s"]
    add("r7b.g5.reboot.scan_s_stored", t_scan, "s", "stored linear scan over all vehicles, 3 boot candidates (boot + 1 to boot + 3) and 16 pseudonyms (r7.b.resync.python.one_frame_s)")
    add("r7b.g5.reboot.table_entries", entries, "entries", "n x 3 x m = 1000 x 3 x 16 (boot + 1 to boot + 3, as r7_pseudo.resync)")
    add("r7b.g5.reboot.prf_s_implied", t_scan / entries, "s", "stored scan time / entries: implied cost of one PRF and compare in the Python reference")
    add("r7b.g5.reboot.table_bytes", entries * 8, "bytes", "8 bytes per entry (4-byte pseudonym, 2-byte vehicle index, 2 bytes of hash-table slack), without the hash-table load factor")
    add("r7b.g5.reboot.refresh_prf_per_match", boots * m, "PRF evaluations", "after a match for one vehicle: recompute its 3 x 16 entries, off the frame path")
    add("r7b.g5.reboot.refresh_s_per_match", boots * m * t_scan / entries, "s", "using the implied Python PRF cost")
    record_many([e for e in ent if e is not None], purge_prefixes=("r7b.g0.", "r7b.g5."))
    print(len(ent), "keys")


if __name__ == "__main__":
    main()
