"""Round 7: descriptive B3 items (frame sizes and airtime, footprint of the node PRF), the Holm decision over the five confirmatory hypotheses of V18, and the results document.

    python -m crashguard.r7_decide        # keys r7.b.desc.*, r7.decision.*, docs/03_results/ROUND7_RESULTS.md

Holm (alpha = 0.05) over H-R7-A1, H-R7-A2, H-R7-B1, H-R7-B2, H-R7-B3; a missing hypothesis enters with p = 1. H-R7-A3 and the descriptive items are outside the family.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

from crashguard import r7_engine as E
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7_decide.py"
ALPHA = 0.05


def keys() -> dict:
    return {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}


def footprint() -> dict:
    d = ROOT / "build" / "r7fp"
    out: dict = {}
    sz = (d / "cg_r7.size.txt").read_text(encoding="utf-8")
    out["text_bytes"] = sum(int(m.group(1)) for m in re.finditer(r"^\.text\.\w+\s+(\d+)", sz, re.M))
    out["literal_bytes"] = sum(int(m.group(1)) for m in re.finditer(r"^\.literal\.\w+\s+(\d+)", sz, re.M))
    out["data_bss_bytes"] = sum(int(m.group(1)) for m in re.finditer(r"^\.(?:data|bss)\s+(\d+)", sz, re.M))
    su = {}
    for f in ("cg_r7.su", "cg_rd.su"):
        for ln in (d / f).read_text(encoding="utf-8").splitlines():
            m = re.match(r".*:\d+:\d+:(\w+)\s+(\d+)\s+\w+", ln)
            if m:
                su[m.group(1)] = int(m.group(2))
    out["stack_pseudonym"] = su["cg_r7_pseudonym"]
    out["stack_hmac"] = su["cg_hmac_sha256"]
    out["stack_sha256"] = su["cg_sha256"]
    nm = (d / "cg_rd.nm.txt").read_text(encoding="utf-8")
    out["hmac_text"] = int(re.search(r"^\S+ (\w+) T cg_hmac_sha256", nm, re.M).group(1), 16)
    out["sha256_text"] = int(re.search(r"^\S+ (\w+) T cg_sha256", nm, re.M).group(1), 16)
    return out


def holm(ps: list[tuple[str, float]]) -> dict:
    order = sorted(ps, key=lambda x: x[1])
    res = {}
    stop = False
    for i, (n, p) in enumerate(order):
        thr = ALPHA / (len(order) - i)
        ok = (not stop) and p <= thr
        stop = stop or not ok
        res[n] = dict(p=p, threshold=thr, rejected=ok)
    return res


def main() -> None:  # noqa: PLR0915
    K = keys()
    ent: list[dict] = []

    def add(name, v, unit, origin, note=""):
        ent.append(dict(name=name, value=(round(v, 9) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin=origin, source_file=SRC, notes=note))

    # ---- B3 descriptive: frame sizes and airtime
    sizes = {"alert": (97, 97), "ack": (26, 26), "flash": (14, 14), "flash_with_boot_byte": (15, 14), "cancel": (14, 14), "micro": (8, 8)}
    for n, (b, a) in sizes.items():
        add(f"r7.b.desc.bytes.{n}.before", b, "bytes", "ANALYTICAL", "FRAME_LAYOUT.md")
        add(f"r7.b.desc.bytes.{n}.after", a, "bytes", "ANALYTICAL", "pseudonym replaces the id; boot and counter leave the frame (recovered from the window entry); the freed bytes carry encrypted fields (alert) or a 2-byte coarse cell (flash)")
    for sf in (7, 8, 9):
        for nb in (97, 105, 14, 15):
            add(f"r7.b.desc.air.sf{sf}.b{nb}", E.air(nb, sf), "s", "ANALYTICAL", "time on air; 105 = alert with a 16-byte AEAD tag instead of the 8-byte tag")
        add(f"r7.b.desc.air.sf{sf}.aead16_extra", E.air(105, sf) - E.air(97, sf), "s", "ANALYTICAL", "airtime added by a 16-byte tag (8 bytes more) on the alert")
        add(f"r7.b.desc.air.sf{sf}.flash15_to_14", E.air(15, sf) - E.air(14, sf), "s", "ANALYTICAL", "airtime change of the flash when the boot byte is dropped (negative or zero)")
    fp = footprint()
    for k, v in fp.items():
        add(f"r7.b.desc.fp.{k}", v, "bytes", "MEASURED_SOFTWARE", "Espressif GCC 12.2.0 -Os for Xtensa, compile only (scripts/r7_footprint.sh); no emulator, so instruction counts and energy are NOT_RUN")
    add("r7.b.desc.fp.instructions", "NOT_RUN", "count", "NOT_RUN", "no ESP32 emulator in this environment")
    add("r7.b.desc.fp.energy", "NOT_RUN", "J", "NOT_RUN", "no hardware")
    record_many(ent, purge_prefixes=("r7.b.desc.",))
    K = keys()

    # ---- Holm
    a1 = [(k, v) for k, v in K.items() if re.match(r"r7\.a1\.sim\.\w+\.sf\d\.reserved\.primary\.p_ge_099$", k)]
    p_a1 = max(v for _, v in a1) if a1 else 1.0
    cells_a1 = {k.split("sim.")[1].rsplit(".reserved", 1)[0]: K[k.replace("p_ge_099", "lo95")] for k, _ in a1}
    p_a2 = float(K.get("r7.a2.hR7_A2.p", 1.0))
    p_b1 = max(float(K.get("r7.b.hR7_B1.p", 1.0)), 1e-300) if K.get("r7.b.hR7_B1.criterion_met") == 1 else 1.0
    p_b2 = 1e-300 if K.get("r7.b.hR7_B2.criterion_met") == 1 else 1.0
    p_b3 = 1e-300 if K.get("r7.formal.b.hR7_B3.criterion_met") == 1 else 1.0
    H = holm([("H-R7-A1", p_a1), ("H-R7-A2", p_a2), ("H-R7-B1", p_b1), ("H-R7-B2", p_b2), ("H-R7-B3", p_b3)])
    crit = {"H-R7-A1": all(v >= 0.99 for v in cells_a1.values()) and bool(cells_a1), "H-R7-A2": K.get("r7.a2.hR7_A2a.criterion_met") == 1 and K.get("r7.a2.hR7_A2b.criterion_met") == 1,
            "H-R7-B1": K.get("r7.b.hR7_B1.criterion_met") == 1, "H-R7-B2": K.get("r7.b.hR7_B2.criterion_met") == 1, "H-R7-B3": K.get("r7.formal.b.hR7_B3.criterion_met") == 1}
    ent = []
    nsup = 0
    for h, r in H.items():
        sup = bool(crit[h]) and r["rejected"]
        nsup += int(sup)
        add(f"r7.decision.{h}.p", r["p"], "p-value", "MEASURED_SOFTWARE", "")
        add(f"r7.decision.{h}.holm_threshold", r["threshold"], "alpha", "ANALYTICAL")
        add(f"r7.decision.{h}.criterion_met", int(bool(crit[h])), "flag", "ANALYTICAL")
        add(f"r7.decision.{h}.supported", int(sup), "flag", "ANALYTICAL", "criterion met and rejected by Holm")
    add("r7.decision.n_supported", nsup, "hypotheses", "ANALYTICAL", "of the five of the Holm family")
    record_many(ent, purge_prefixes=("r7.decision.",))


    # ---- ledger keys (V18) and totals over all versions
    R2 = keys()
    ent = []
    led = dict(preregistered=6, run=6, supported=nsup, not_supported=sum(1 for h in ("H-R7-A1", "H-R7-A2", "H-R7-B2") if not (bool(crit[h]) and H[h]["rejected"])), partly=0, not_run=0)
    for kk, vv in led.items():
        add(f"r7.ledger.V18.{kk}", vv, "hypotheses", "ANALYTICAL", "H-R7-A3 is descriptive: counted as preregistered and run, with no verdict")
    for kk in ("preregistered", "run", "supported", "not_supported", "partly", "not_run"):
        add(f"r7.ledger.all.{kk}", int(R2[f"r6.ledger.all.{kk}"]) + led[kk], "hypotheses", "ANALYTICAL", "r6.ledger.all plus V18")
    add("r7.ledger.all.versions", int(R2["r6.ledger.all.versions"]) + 1, "versions", "ANALYTICAL")
    add("r7.ledger.all.confirmatory_rows", int(R2["r6.ledger.all.confirmatory_rows"]) + 5, "rows", "ANALYTICAL", "the five members of the V18 Holm family")
    add("r7.ledger.all.confirmatory_supported", int(R2["r6.ledger.all.confirmatory_supported"]) + nsup, "rows", "ANALYTICAL")
    record_many(ent, purge_prefixes=("r7.ledger.",))

    # ---- document
    L = ["# Round 7 results and decision table", "", "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-16 |", "| Owner | Mritula S |",
         "| Scope | Round 7 (V18): verdict of each hypothesis with its Holm threshold, the numbers behind it, and the limits. |", "| Evidence labels used | SIMULATED, TRACE_DRIVEN, FORMAL, ANALYTICAL, MEASURED_SOFTWARE, NOT_RUN |",
         "| Abbreviations | ACK = acknowledgement frame; CPU = central processing unit; SF = spreading factor (LoRa) |", "<!-- header:end -->", "",
         "Generated by `python -m crashguard.r7_decide` from `results/results.json` (keys `r7.*`). Hypotheses are reported as written in `docs/02_preregistration/PREREGISTRATION_V18.md`.", "",
         "| Hypothesis | Criterion met | p | Holm threshold | Verdict |", "|---|---|---:|---:|---|"]
    for h, r in H.items():
        sup = bool(crit[h]) and r["rejected"]
        L.append(f"| {h} | {'yes' if crit[h] else 'no'} | {r['p']:.3g} | {r['threshold']:.4g} | {'supported' if sup else 'not supported'} |")
    L += ["", f"Supported: {nsup} of 5. H-R7-A3 is descriptive (see `ROUND7_A.md`).", ""]
    (ROOT / "docs" / "03_results" / "ROUND7_RESULTS.md").write_text("\n".join(L), encoding="utf-8")
    print({h: (crit[h], H[h]["rejected"]) for h in H}, "supported", nsup)


if __name__ == "__main__":
    main()
