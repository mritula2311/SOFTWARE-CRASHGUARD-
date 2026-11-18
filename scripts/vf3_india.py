"""Finalize F2: the Indian 433 MHz conditions (G.S.R. 347(E), rule 3 row 1) against the evaluation. Keys vf3.india.* (ANALYTICAL), docs/03_results/FINALIZE_INDIA_RULES.md.

    PYTHONPATH=src python scripts/vf3_india.py
Computed, not copied: the duty condition at 10% per transmission (the stored vf2.duty.* numbers are read and recomputed here with the 8-byte micro frame) and the e.r.p. arithmetic.
e.r.p. = transmit power + antenna gain (dBi) - losses - 2.15 dB (dipole reference), in dBm; the limit is 10 mW = 10 dBm.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard.lora import airtime_ms  # noqa: E402
from crashguard.results import record_many  # noqa: E402

SRC = "scripts/vf3_india.py"
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
T_F, C = 1.808, 0.008
T_E = {"median": R["r6.r2.held.median_time_fixed_ms"] / 1000.0, "mean": R["r6.r2.held.mean_time_fixed_ms"] / 1000.0}
PTX, EXTRA = 14.0, 10.0  # world_sim.py ptx_dbm and extra_loss_db; xsim_alert.cc subtracts 10 dB as well (ASSUMPTIONS.md: transmit power 14.0 dBm)
ent: list[dict] = []


def A(n, sf):
    return airtime_ms(n, sf) / 1000.0


def add(name, v, unit, note="", origin="ANALYTICAL"):
    ent.append(dict(name=f"vf3.india.{name}", value=(v if isinstance(v, float) and 0 < abs(v) < 1e-3 else round(v, 6) if isinstance(v, float) else v), unit=unit, origin=origin, source_file=SRC, notes=note))


def erp(ptx, gain, loss):
    return ptx + gain - loss - 2.15


def mw(dbm):
    return 10 ** (dbm / 10.0)


def main() -> None:
    rows = []
    for d in (0.10, 0.01):
        k = int(d * 100)
        for who, te in T_E.items():
            s_f = te + C
            crit = d * (T_F - s_f)
            ok = [sf for sf in (7, 8, 9, 10, 11, 12) if A(14, sf) <= crit]
            add(f"critical_airtime.d{k}.{who}_s", crit, "s", "largest flash airtime for which the confirm is not delayed: d (T_F - s_f)")
            add(f"max_sf_condition_a.d{k}.{who}", max(ok) if ok else 0, "SF", "largest spreading factor at which the 14-byte flash satisfies the condition (0 = none up to SF12)")
            for sf in (7, 8, 9):
                L = s_f + A(14, sf) / d
                add(f"cond_c8.sf{sf}.d{k}.{who}", int(L - T_F < A(97, sf) - A(8, sf) - 1e-12), "flag", "micro scheme with the 8-byte frame reaches the base before the single-stage alert: L - T_F < A97 - A8, L = s_f + A14 / d")
        rows.append(k)
    # the evaluated allowance against the Indian limit
    add("evaluated_allowance_share", 0.01, "fraction", "hourly allowance used in every simulation (36 s per hour)")
    add("india_limit_share", 0.10, "fraction", "rule 3 row 1: duty cycle at most 10% (observation interval not stated)")
    add("hourly_allowance_india_s", 0.10 * 3600.0, "s", "airtime per hour if the 10% is read over one hour")
    # e.r.p. arithmetic
    add("sim.ptx_dbm", PTX, "dBm", "transmit power in the simulators (ptx_dbm 14.0; ASSUMPTIONS.md); NOT 10 dBm", "MEASURED_SOFTWARE")
    add("sim.extra_loss_db", EXTRA, "dB", "extra loss that the simulators subtract in the link budget (extra_loss_db 10.0; xsim_alert.cc subtracts 10 dB as well)", "MEASURED_SOFTWARE")
    add("limit_erp_dbm", 10.0, "dBm", "10 mW e.r.p.")
    for g, loss in ((0.0, 0.0), (2.15, 0.0), (3.0, 1.0)):
        e = erp(PTX, g, loss)
        add(f"erp.direct.g{g}_l{loss}.dbm", e, "dBm", f"e.r.p. if the radio delivers {PTX:.0f} dBm to an antenna of {g} dBi through {loss} dB of cable and connector loss (no extra loss)")
        add(f"erp.direct.g{g}_l{loss}.mw", mw(e), "mW", "same in mW")
        add(f"erp.direct.g{g}_l{loss}.reduction_db", max(0.0, e - 10.0), "dB", "transmit-power reduction needed to meet 10 mW e.r.p. in that case")
    e_lump = erp(PTX, 0.0, EXTRA)
    add("erp.lumped.dbm", e_lump, "dBm", "e.r.p. if the 10 dB extra loss of the link budget is all transmit-side (antenna efficiency, cable, mounting) and the antenna is 0 dBi")
    add("erp.lumped.mw", mw(e_lump), "mW", "same in mW")
    add("erp.max_gain_for_14dbm_direct_dbi", 10.0 + 2.15 - PTX, "dBi", "largest antenna gain (no cable loss) that keeps 14 dBm at the antenna connector within 10 mW e.r.p.: negative means a loss is needed")
    add("sf_step_db", 3.0, "dB", "sensitivity step per spreading factor in the simulators (-123 to -137 dBm over SF7 to SF12, about 2.8 dB)")
    add("sf_equivalent_of_reduction_direct_0dbi", max(0.0, erp(PTX, 0.0, 0.0) - 10.0) / 2.8, "SF steps", "link-budget cost of the reduction for a 0 dBi antenna with no cable loss, in spreading-factor steps (analytical)")
    record_many(ent, purge_prefixes=("vf3.india.",))
    G = {e["name"][len("vf3.india."):]: e["value"] for e in ent}
    tx = lambda k: G[k]  # noqa: E731
    L = ["# Indian 433 MHz conditions against the evaluation (finalize F2)", "", "<!-- header:start -->", "<!-- header:end -->", "",
         "Generated by `python scripts/vf3_india.py` (keys `vf3.india.*`, ANALYTICAL unless stated). Source: Ministry of Communications (WPC Wing), G.S.R. 347(E), 9 May 2022, *Use of Low Power Radio Frequency Devices in the frequency band 433.05 to 434.79 MHz (Exemption from License) Rules, 2022*, "
         "Gazette of India, Extraordinary, Part II, Section 3(i), No. 332, 11 May 2022. URL: https://eservices.dot.gov.in/sites/default/files/circular-notifications/the-use-of-low-power-radio-frequency-devices-in-the-frequency-band-433.05-to-434.79-mhz-exemption-from-license-rules-2022.pdf. "
         "The full text (8 pages) was opened and read on 16 November 2026 in the finalize run (the PDF was downloaded and its text extracted); it is recorded as VERIFIED in `docs/06_references/LITERATURE_STATUS.md`.", "",
         "## 1. What the rules say (read from the text)", "",
         "| Item | Text of the rules | Use here |", "|---|---|---|",
         "| Rule 3, table row 1 | 433.05 to 434.79 MHz; 10 mW e.r.p.; spectrum access: 10% duty cycle; modulation and bandwidth: not specified; standard reference EN 300 220 | LoRa at 125 kHz falls under this row |",
         "| Rule 3, rows 2 and 3 | row 2: 1 mW e.r.p., power density limit -13 dBm per 10 kHz for wideband modulation above 250 kHz; row 3: 434.04 to 434.79 MHz, 10 mW e.r.p., 25 kHz channels, voice allowed | not used |",
         "| Definition of duty cycle (rule 2) | the ratio, in percent, of the cumulative duration of transmission within an observation interval Tobs | the interval is not stated, so the text does not say whether 10% is per hour or per transmission |",
         "| Definition of e.r.p. (rule 2) | the product of the power supplied to the antenna and its gain relative to a half-wave dipole | e.r.p. = power + gain (dBi) - losses - 2.15 dB |",
         "| Indoor use | the rules supersede the 2012 indoor-only rules and the 2015 rules; no indoor-only condition appears in the 2022 text | no indoor restriction applies |",
         "| Rule 5 | the equipment shall conform to the limits of rule 3 and shall be type approved (application in the form of the annexure to the Central Government) | a deployed node needs type approval |", "",
         "## 2. The evaluated duty model against the limit", "",
         f"Every simulation enforces an hourly allowance of {tx('evaluated_allowance_share') * 100:.0f}% (36 s per hour), stricter than the {tx('india_limit_share') * 100:.0f}% of row 1 ({tx('hourly_allowance_india_s'):.0f} s per hour if the 10% is read over one hour). Two readings of the undefined observation interval:", "",
         "1. **Per hour (or any long interval).** The evaluated allowance is inside the limit; no result changes.",
         f"2. **Per transmission** (the strictest reading, an off-time of T_air (1/d - 1) after each frame on the shared channel). With d = 10% the condition A_f <= d (T_F - s_f) of `DELTA_DUTY_LOCKOUT.md` section 3 allows a flash airtime of at most {tx('critical_airtime.d10.median_s') * 1000:.1f} ms (median decision time) or {tx('critical_airtime.d10.mean_s') * 1000:.1f} ms (mean). "
         f"It holds for the 14-byte flash up to SF{tx('max_sf_condition_a.d10.median')} (median) and SF{tx('max_sf_condition_a.d10.mean')} (mean). With the 8-byte micro frame the micro scheme reaches the base before the single-stage alert (condition C) at SF7 to SF9: "
         + ", ".join(f"SF{sf} {'yes' if tx(f'cond_c8.sf{sf}.d10.median') else 'no'}" for sf in (7, 8, 9)) + ". "
         "The load gate of the gating rule (R6-7) still gives SF7 only.", "",
         f"So the two-stage alert stays feasible at 433 MHz in India under either reading of the 10%. Under a strict 1% per transmission (some other regions) the condition fails at every spreading factor (largest admissible flash airtime {tx('critical_airtime.d1.median_s') * 1000:.1f} ms; `max_sf_condition_a.d1` = {tx('max_sf_condition_a.d1.median')}), and the stored two-stage results do not transfer. The number of channels the node may use is not limited by row 1 (no channel plan is given); the simulations use one channel.", "",
         "## 3. Transmit power and e.r.p.", "",
         f"An assumption of 10 dBm transmit power does not match the code: the simulators use a transmit power of {tx('sim.ptx_dbm'):.0f} dBm (`ptx_dbm`; ASSUMPTIONS.md) and subtract an extra loss of {tx('sim.extra_loss_db'):.0f} dB in the link budget (`extra_loss_db`; `xsim_alert.cc` subtracts 10 dB as well). Which of the two figures is the radiated power depends on what the 10 dB stands for; both cases follow. "
         "e.r.p. (dBm) = transmit power + antenna gain (dBi) - cable and connector loss (dB) - 2.15; the limit is 10 mW = 10 dBm.", "",
         "| Case | e.r.p. (dBm) | e.r.p. (mW) | Reduction of transmit power needed |", "|---|---:|---:|---:|"]
    for g, loss, nm in ((0.0, 0.0, "14 dBm at the antenna, 0 dBi, no loss"), (2.15, 0.0, "14 dBm at the antenna, 2.15 dBi (dipole), no loss"), (3.0, 1.0, "14 dBm at the radio, 3 dBi antenna, 1 dB cable loss")):
        L.append(f"| {nm} | {tx(f'erp.direct.g{g}_l{loss}.dbm'):.2f} | {tx(f'erp.direct.g{g}_l{loss}.mw'):.1f} | {tx(f'erp.direct.g{g}_l{loss}.reduction_db'):.2f} dB |")
    L.append(f"| the 10 dB extra loss of the link budget is all transmit-side, 0 dBi | {tx('erp.lumped.dbm'):.2f} | {tx('erp.lumped.mw'):.2f} | none |")
    L += ["", f"Reading. If the 10 dB extra loss is transmit-side (antenna efficiency, cable, mounting), the radiated power is {tx('erp.lumped.dbm'):.1f} dBm ({tx('erp.lumped.mw'):.1f} mW), inside the limit, and the link budget of the simulations stands. "
          f"If instead the radio delivers 14 dBm to the antenna and the 10 dB is path loss, the 10 mW limit needs the transmit power reduced by {tx('erp.direct.g0.0_l0.0.reduction_db'):.2f} dB for a 0 dBi antenna and by {tx('erp.direct.g2.15_l0.0.reduction_db'):.2f} dB for a dipole; "
          f"every dB of reduction lowers the received level by 1 dB, so the link margin shrinks by the same amount, which is about {tx('sf_equivalent_of_reduction_direct_0dbi'):.1f} spreading-factor step for the 0 dBi case at the simulators' sensitivity step of about 2.8 dB per step. "
          "This is an analytical note: no simulation was rerun with a reduced power, and the author must decide which reading of the 10 dB holds for the hardware.", ""]
    (ROOT / "docs" / "03_results" / "FINALIZE_INDIA_RULES.md").write_text("\n".join(L), encoding="utf-8")
    print({k: v for k, v in G.items() if k.startswith(("max_sf", "erp.lumped", "critical", "erp.direct.g0.0"))})
    assert math.isfinite(G["erp.lumped.dbm"])


if __name__ == "__main__":
    main()
