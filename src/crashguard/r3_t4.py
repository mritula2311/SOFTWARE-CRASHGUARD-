"""T4 (docs/02_preregistration/PREREGISTRATION_V14.md section 4): post-crash survivability budget, ANALYTICAL (supporting; no hypothesis).

    python -m crashguard.r3_t4

After a crash the node may lose vehicle power. From datasheet currents (sources below; ASSUMPTION where a value was not read in an opened document) the energy of one Critical alert schedule is computed for each
policy (the schedule of the frozen policy code of ``r3_t1.replay_alert`` when every uplink is lost until the 10 s deadline, and when the first k uplinks are lost), and the smallest backup capacitor that supplies it.

Inputs read in documents opened on 2026-11-15 (saved under data/raw/t4_datasheets, git-ignored):
  * SX1276/77/78/79 datasheet, Rev. 4 March 2015 (Semtech; copy hosted by Adafruit): Table 6 IDDT +20 dBm PA_BOOST 120 mA, +17 dBm PA_BOOST 87 mA, +13 dBm RFO 29 mA, +7 dBm RFO 20 mA (typical);
    Table 10 IDDR_L LoRa receive, LnaBoost off, bands 2 and 3, BW 125 kHz: 11.5 mA (typical); sleep 0.2 uA.
  * ESP32 Series Datasheet v5.3 (Espressif), Table 4-2: Modem-sleep (CPU on, radio off) 160 MHz dual-core 27 to 44 mA (the upper value is used); Deep-sleep 10 uA (RTC timer and memory).
  * u-blox NEO-6 data sheet GPS.G6-HW-09005-E, Table 11 (NEO-6M, 3.0 V): acquisition 47 mA, tracking 39 mA (maximum performance mode), maximum supply current 67 mA.
ASSUMPTIONS (not read in an opened document): supply voltage 3.3 V at the three parts; converter efficiency 0.85; the capacitor is usable from 5.0 V down to 3.0 V; no ESR loss; the GPS is already tracking; the node is
awake from the crash to the end of the schedule; the SX1278 module (Ra-02) matches the datasheet currents. The 433 MHz transmit power allowed in India is not verified (see NOTICE of the project), so four levels are shown.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np

from crashguard import r3_t1 as T
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r3_t4.py"
V = 3.3
EFF = 0.85
V_HI, V_LO = 5.0, 3.0
I_TX_MA = {7: 20.0, 13: 29.0, 17: 87.0, 20: 120.0}
I_RX_MA = 11.5
I_ESP_MA = 44.0
I_GPS_MA = 39.0
CAPS_F = (0.22, 0.47, 1.0, 2.2)
K_LIST = (0, 2, 4, 6)


class Worst:
    def uniform(self, a: float, b: float) -> float:
        return b

    def random(self) -> float:
        return 1.0


def schedule(pol: str, k: int | None) -> dict:
    """Transmissions of one Critical alert: all uplinks lost (k = None) or the first k lost and the next received. Returns the list (sf, start, airtime), the end time and whether delivered."""
    r = np.array(([0] * (k if k is not None else 60)) + [1] * 60, np.uint8)
    # a 12-round history of no recent failure for D1
    r = np.concatenate([np.ones(12, np.uint8), r])
    tr: list = []
    t, n, used = T.replay_alert(pol, r, 12, Worst(), 0.0, 0.0, tr)
    end = max((s + a for _sf, s, a in tr), default=0.0)
    return dict(tx=tr, t_rx=t, n=n, end=end, delivered=math.isfinite(t))


def energy_j(sch: dict, p_dbm: int) -> dict:
    tx_s = sum(a for _sf, _s, a in sch["tx"])
    rx_s = sum(T.listen_window(sf) for sf, _s, _a in sch["tx"]) if not sch["delivered"] else sum(T.listen_window(sf) for sf, _s, _a in sch["tx"][:-1])
    # awake time: from the crash (t = 0) to the end of the last transmission (delivered) or to the 10 s deadline (not delivered)
    t_awake = sch["end"] if sch["delivered"] else max(sch["end"], T.DEADLINE)
    e_tx = V * I_TX_MA[p_dbm] / 1000.0 * tx_s
    e_rx = V * I_RX_MA / 1000.0 * rx_s
    e_base = V * (I_ESP_MA + I_GPS_MA) / 1000.0 * t_awake
    return dict(e_tx=e_tx, e_rx=e_rx, e_base=e_base, total=(e_tx + e_rx + e_base) / EFF, tx_s=tx_s, t_awake=t_awake)


def cap_energy_j(c_f: float) -> float:
    return 0.5 * c_f * (V_HI**2 - V_LO**2)  # energy between the two voltages; the converter efficiency is applied to the load energy in energy_j


def main() -> None:
    T.init_ctx()
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        if isinstance(value, float):
            value = round(value, 5)
        ent.append(dict(name=f"r3.t4.{name}", value=value, unit=unit, origin="ANALYTICAL", source_file=SRC, notes=notes))

    out: dict = {"policies": {}, "caps": {c: cap_energy_j(c) for c in CAPS_F}}
    for c in CAPS_F:
        add(f"cap{c:g}F.usable_j", cap_energy_j(c), "J", f"{c:g} F between {V_HI} V and {V_LO} V (ASSUMPTIONS: window, no ESR); the converter efficiency {EFF} (ASSUMPTION) is applied to the load energy")
    for p_dbm in (13, 17, 20):
        for pol in T.POLICIES:
            row = {}
            for k in (None,) + K_LIST:
                sch = schedule(pol, k)
                e = energy_j(sch, p_dbm)
                key = "all_lost" if k is None else f"k{k}"
                row[key] = dict(energy_j=e["total"], n_tx=len(sch["tx"]), delivered=sch["delivered"], t_rx=(sch["t_rx"] if sch["delivered"] else None), airtime_s=e["tx_s"])
                add(f"p{p_dbm}.{pol}.{key}.energy_j", e["total"], "J", f"energy drawn from the backup store for the schedule, {len(sch['tx'])} transmissions, delivered={sch['delivered']}; TX {I_TX_MA[p_dbm]} mA, RX {I_RX_MA} mA, ESP32 {I_ESP_MA} mA, GPS {I_GPS_MA} mA at {V} V (ASSUMPTION), efficiency {EFF} (ASSUMPTION)")
                add(f"p{p_dbm}.{pol}.{key}.c_min_f", 2.0 * e["total"] / (V_HI**2 - V_LO**2), "F", "smallest capacitor (5.0 V to 3.0 V window) that supplies this schedule")
            out["policies"].setdefault(str(p_dbm), {})[pol] = row
    for p_dbm in (13, 17, 20):
        for pol in T.POLICIES:
            for c in CAPS_F:
                ok = out["policies"][str(p_dbm)][pol]["all_lost"]["energy_j"] <= cap_energy_j(c)
                add(f"p{p_dbm}.{pol}.runs_full_schedule_on_{c:g}F", int(ok), "flag", "the capacitor supplies the whole all-lost schedule up to the 10 s deadline")
    add("hypothesis.status", "NOT_RUN", "status", "no hypothesis is tested: the converter efficiency, the supply voltage and the voltage window are assumptions")
    ent[-1]["origin"] = "NOT_RUN"
    record_many(ent, purge_prefixes=("r3.t4.",))
    (ROOT / "results" / "tables" / "r3_t4.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    for p_dbm in (17,):
        print("TX", p_dbm, "dBm")
        for pol in T.POLICIES:
            a = out["policies"][str(p_dbm)][pol]
            print(pol, {k: (round(v["energy_j"], 2), v["n_tx"], v["delivered"]) for k, v in a.items()})
    print({c: round(e, 2) for c, e in out["caps"].items()})
    random.seed(0)


if __name__ == "__main__":
    main()
