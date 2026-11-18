"""T10: airtime and energy accounting. ANALYTICAL tables (Semtech formula, ``lora.airtime_ms``) and SIMULATED per-event totals from the held-out default cells. NOT measured.

ASSUMPTIONS (ours, not datasheet-verified): supply 3.3 V; transmit current 120 mA; receive current 12 mA (while the car listens for an ACK after every try: processing 0.1 s + ACK airtime + margin 0.1 s);
sleep and idle current ignored; 125 kHz, coding rate 4/5, 8-symbol preamble, explicit header, CRC on; no collisions and no duty waits in the formulas. The energy figures are estimates from these assumptions and must not
be read as measurements.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard.lora import airtime_ms
from crashguard.replay import MARGIN_S, PROC_S

SFS = (7, 8, 9, 10, 11, 12)
V_SUPPLY, I_TX_A, I_RX_A = 3.3, 0.120, 0.012
FLASH = 14
SRC = "results/tables/t10_airtime.csv"
MAX_TRIES = {"P0": 4, "P1": 12, "P2": 12, "P3": 12}


def expected_tries(q: float, cap: int) -> float:
    """Expected number of tries until the first success with per-try success q, capped at ``cap`` tries."""
    return float(sum((1 - q) ** k for k in range(cap)))


def main() -> None:
    from crashguard.results import record_many

    ent: list[dict] = []
    rows = []

    def add(name, value, unit, notes="", origin="ANALYTICAL"):
        ent.append(dict(name=f"t10.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    add("assumption.supply_v", V_SUPPLY, "V", "ASSUMPTION, not datasheet-verified")
    add("assumption.i_tx_ma", I_TX_A * 1000, "mA", "ASSUMPTION, not datasheet-verified")
    add("assumption.i_rx_ma", I_RX_A * 1000, "mA", "ASSUMPTION, not datasheet-verified; receive current while listening for an ACK")
    for sf in SFS:
        for nm, n in (("flash_cancel", FLASH), ("alert", P.ALERT_LEN), ("ack", P.ACK_LEN), ("heartbeat16", 16)):
            a = airtime_ms(n, sf) / 1000.0
            add(f"airtime.sf{sf}.{nm}_s", round(a, 5), "s", f"Semtech formula, {n} bytes")
            rows.append(dict(sf=sf, message=nm, bytes=n, airtime_s=a))
        add(f"listen_window.sf{sf}_s", round(PROC_S + airtime_ms(P.ACK_LEN, sf) / 1000.0 + MARGIN_S, 5), "s", "receive window after every try: processing + ACK airtime + margin")
    # ---- expected airtime and energy per crash event under per-message loss (no collisions, no duty waits)
    for sf in (7, 9, 12):
        a_al, a_fl, a_ack = airtime_ms(P.ALERT_LEN, sf) / 1000.0, airtime_ms(FLASH, sf) / 1000.0, airtime_ms(P.ACK_LEN, sf) / 1000.0
        win = PROC_S + a_ack + MARGIN_S
        for loss in (0.0, 0.1, 0.3, 0.6):
            q = (1 - loss) ** 2  # message and its ACK
            for pol, cap in (("P1", 12), ("P0", 4)):
                tries = expected_tries(q, cap)
                t_tx, t_rx = tries * a_al, tries * win
                add(f"event.sf{sf}.loss{int(loss * 100)}.{pol}.airtime_s", round(t_tx, 4), "s", f"expected transmit airtime per crash event: {tries:.3f} expected alert tries of at most {cap}; message and ACK must both get through")
                add(f"event.sf{sf}.loss{int(loss * 100)}.{pol}.energy_mj", round(1000 * V_SUPPLY * (I_TX_A * t_tx + I_RX_A * t_rx), 3), "mJ", "ASSUMED currents; estimate, not a measurement")
            # SCT: a round sends the flash (until its ACK) and the alert; rounds until the alert is acknowledged (at most 12)
            rounds = expected_tries(q, 12)
            fl_sends = expected_tries(q, 12)  # the flash is repeated each round until its own ACK, same per-try success
            fl_sends = min(fl_sends, rounds)
            t_tx = rounds * a_al + fl_sends * a_fl
            t_rx = (rounds + fl_sends) * win
            for pol in ("P2", "P3"):
                add(f"event.sf{sf}.loss{int(loss * 100)}.{pol}.airtime_s", round(t_tx, 4), "s", f"expected transmit airtime per crash event: {rounds:.3f} expected alert rounds and {fl_sends:.3f} flash sends; no CANCEL")
                add(f"event.sf{sf}.loss{int(loss * 100)}.{pol}.energy_mj", round(1000 * V_SUPPLY * (I_TX_A * t_tx + I_RX_A * t_rx), 3), "mJ", "ASSUMED currents; estimate, not a measurement")
    # ---- simulated per-event totals from the held-out default cells (SIMULATED)
    s11 = pd.read_csv(C.TABLES / "s11_sct.csv")
    a_al, a_fl, a_ack = airtime_ms(P.ALERT_LEN, 7) / 1000.0, airtime_ms(FLASH, 7) / 1000.0, airtime_ms(P.ACK_LEN, 7) / 1000.0
    win = PROC_S + a_ack + MARGIN_S
    for mode in ("steady", "burst"):
        g = s11[(s11.range_g == 16.0) & (s11["mode"] == mode) & (s11.scen == "base")]
        for pol in ("P0", "P1", "P2", "P3", "P4"):
            h = g[g.pol == pol]
            n_ev = (h.n_fast + h.n_normal).to_numpy(float)
            tx = (h.al_tx * a_al + h.flash_tx * a_fl + h.cancel_tx * a_fl).to_numpy(float) / n_ev
            rx = ((h.al_tx + h.flash_tx) * win).to_numpy(float) / n_ev
            en = 1000 * V_SUPPLY * (I_TX_A * tx + I_RX_A * rx)
            add(f"sim.{mode}.{pol}.airtime_per_event_s", round(float(tx.mean()), 4), "s", "SIMULATED: mean transmit airtime of alert, flash and CANCEL messages per crash event (heartbeats excluded), SF7, default cell, +-16 g, 40 seeds", "SIMULATED")
            add(f"sim.{mode}.{pol}.energy_per_event_mj", round(float(en.mean()), 3), "mJ", "SIMULATED counts with ASSUMED currents; estimate, not a measurement", "SIMULATED")
            add(f"sim.{mode}.{pol}.tries_per_event", round(float(((h.al_tx + h.flash_tx).to_numpy(float) / n_ev).mean()), 3), "transmissions", "alert and flash transmissions per crash event", "SIMULATED")
    pd.DataFrame(rows).to_csv(C.TABLES / "t10_airtime.csv", index=False)
    record_many(ent, purge_prefixes=("t10.",))
    g = {e["name"]: e["value"] for e in ent}
    print({k: g[k] for k in g if k.startswith("t10.sim.burst")})
    print(np.round([g[f"t10.airtime.sf{sf}.alert_s"] for sf in SFS], 3))


if __name__ == "__main__":
    main()
