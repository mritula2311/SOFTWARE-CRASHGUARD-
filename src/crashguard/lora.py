"""LoRa airtime (Semtech SX127x formula) and duty-cycle budget (S8). All values are ANALYTICAL.

The 10% duty cycle for 433 MHz in India comes from a secondary summary and is NOT verified against the
WPC/DoT notification (docs/06_references/NOVELTY.md). It is a parameter here.
"""
from __future__ import annotations

import math

import pandas as pd

from crashguard import config as C
from crashguard.packet import ACK_LEN, ALERT_LEN
from crashguard.results import record_many

DUTY = 0.10


def airtime_ms(payload_bytes: int, sf: int = 7, bw_hz: int = 125_000, cr: int = 1, preamble: int = 8,
               explicit_header: bool = True, crc: bool = True, low_dr_opt: bool | None = None) -> float:
    """Time on air in ms. ``cr`` is 1..4 for coding rate 4/5..4/8. Low data-rate optimisation is automatic when the symbol is > 16 ms."""
    t_sym = (2**sf) / bw_hz * 1000.0
    de = (t_sym > 16.0) if low_dr_opt is None else low_dr_opt
    ih = 0 if explicit_header else 1
    num = 8 * payload_bytes - 4 * sf + 28 + 16 * int(crc) - 20 * ih
    n_payload = 8 + max(math.ceil(num / (4 * (sf - 2 * int(de)))) * (cr + 4), 0)
    return (preamble + 4.25) * t_sym + n_payload * t_sym


def alerts_per_hour(payload_bytes: int, sf: int, duty: float = DUTY, **kw) -> int:
    """Whole transmissions that fit in the one-hour duty-cycle budget."""
    return int(math.floor(3600.0 * duty / (airtime_ms(payload_bytes, sf, **kw) / 1000.0)))


def main() -> None:
    src = "src/crashguard/lora.py"
    ref = airtime_ms(ALERT_LEN, 7)
    rows, ent = [], []
    for sf in range(7, 13):
        a, k = airtime_ms(ALERT_LEN, sf), airtime_ms(ACK_LEN, sf)
        rows.append(dict(sf=sf, alert_airtime_ms=a, ack_airtime_ms=k, alerts_per_hour=alerts_per_hour(ALERT_LEN, sf),
                         acks_per_hour=alerts_per_hour(ACK_LEN, sf), alert_plus_ack_per_hour=int(3600 * DUTY // ((a + k) / 1000))))
        ent += [dict(name=f"lora.sf{sf}.alert_airtime_ms", value=round(a, 2), unit="ms", origin="ANALYTICAL", source_file=src, notes="97 B, 125 kHz, CR 4/5, 8-symbol preamble, explicit header, CRC"),
                dict(name=f"lora.sf{sf}.ack_airtime_ms", value=round(k, 2), unit="ms", origin="ANALYTICAL", source_file=src, notes="26 B, same settings"),
                dict(name=f"lora.sf{sf}.alerts_per_hour", value=alerts_per_hour(ALERT_LEN, sf), unit="alerts/h", origin="ANALYTICAL", source_file=src, notes=f"{DUTY:.0%} duty cycle, alert transmissions only, no retries"),
                dict(name=f"lora.sf{sf}.alert_plus_ack_per_hour", value=rows[-1]["alert_plus_ack_per_hour"], unit="exchanges/h", origin="ANALYTICAL", source_file=src, notes="the node sends the alert and the base sends the ACK; each side has its own budget, so this is a lower bound for the node")]
    ent.append(dict(name="lora.check_sf7_97B_ms", value=round(ref, 2), unit="ms", origin="ANALYTICAL", source_file=src, notes="documented value is about 169 ms"))
    ent.append(dict(name="lora.check_passes", value=bool(abs(ref - 169.0) < 1.0), unit="bool", origin="ANALYTICAL", source_file=src, notes="within 1 ms of 169 ms"))
    ent.append(dict(name="lora.duty_cycle_assumed", value=DUTY, unit="fraction", origin="ANALYTICAL", source_file=src, notes="NOT verified against WPC/DoT"))
    C.TABLES.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(C.TABLES / "s8_airtime_duty.csv", index=False)
    record_many(ent)
    make_figures()
    print(pd.DataFrame(rows).round(1).to_string(index=False), f"\ncheck 97 B SF7: {ref:.2f} ms")


def make_figures() -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    from crashguard.plots import COLORS, save, style

    style()
    fig, ax = plt.subplots(figsize=(6, 4))
    sizes = np.arange(10, 128)
    for i, sf in enumerate(range(7, 13)):
        ax.plot(sizes, [airtime_ms(int(b), sf) for b in sizes], label=f"SF{sf}", color=COLORS[i % len(COLORS)])
    ax.axvline(ALERT_LEN, color="gray", ls="--")
    ax.text(ALERT_LEN + 1, ax.get_ylim()[1] * 0.5, "97 B alert", rotation=90, fontsize=8)
    ax.set_yscale("log")
    ax.set_xlabel("Payload (bytes)")
    ax.set_ylabel("Time on air (ms), 125 kHz, CR 4/5")
    ax.legend(ncol=2, fontsize=8)
    save(fig, "s8_airtime_curve")
    t = pd.read_csv(C.TABLES / "s8_airtime_duty.csv")
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    ax.bar([f"SF{s}" for s in t.sf], t.alerts_per_hour, color=COLORS[0])
    for i, v in enumerate(t.alerts_per_hour):
        ax.text(i, v, str(v), ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("Spreading factor")
    ax.set_ylabel("97 B alerts per hour at 10% duty cycle (count)")
    save(fig, "s8_alerts_per_hour")


if __name__ == "__main__":
    main()
