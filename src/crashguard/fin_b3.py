"""B3: simulator sanity checks (docs/02_preregistration/PREREGISTRATION_V5.md B3). (i) airtime against the time-on-air formula as TRANSCRIBED (the Semtech document could not be opened on 2026-11-13: redirect, then two timeouts;
no Semtech number is cited), (ii) simulated collision probability of unconfirmed periodic traffic with no capture against 1 - exp(-2G), (iii) duty-cycle limit never exceeded (counted in the other modules).
Mismatches are limitations; the simulator is not tuned."""
from __future__ import annotations

import math


from crashguard.fin_common import Entries
from crashguard.lora import airtime_ms
from crashguard import world_sim as W
from crashguard.capacity import air


def toa_formula(pl: int, sf: int, bw: float = 125e3, cr: int = 1, npre: int = 8, ih: int = 0, crc: int = 1) -> float:
    """Independent transcription: Tsym = 2^SF / BW; DE = 1 if Tsym > 16 ms; payloadSymbNb = 8 + max(ceil((8 PL - 4 SF + 28 + 16 CRC - 20 IH) / (4 (SF - 2 DE))) (CR + 4), 0); Tpacket = (npre + 4.25 + payloadSymbNb) Tsym (ms)."""
    ts = 2**sf / bw * 1000
    de = 1 if ts > 16 else 0
    nsym = 8 + max(math.ceil((8 * pl - 4 * sf + 28 + 16 * crc - 20 * ih) / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (npre + 4.25 + nsym) * ts


def collision_check(seeds: int = 6) -> list[dict]:
    rows = []
    tau = air(16, 7)
    T = 10.0
    for n in (2, 5, 10, 20, 40, 60, 90, 120, 150, 180):
        sent = rx = 0
        for s in range(seeds):
            cfg = W.SCfg(n=n, sf=7, policy="fixed3", seed=s, hb_period_s=T, rate_per_car_h=0.0, capture="none", p_up=0.0, p_down=0.0, duration_s=3600.0, label="b3")
            o = W.simulate(cfg)
            sent += o["hb_sent"]
            rx += o["hb_rx"]
        G = n * tau / T
        rows.append(dict(n=n, G=G, sim=1 - rx / sent, aloha=1 - math.exp(-2 * G), finite=1 - (1 - 2 * tau / T) ** (n - 1), sent=sent))
    return rows


def main() -> None:
    E = Entries("f.b3", "src/crashguard/fin_b3.py")
    err = 0.0
    for pl in (14, 16, 26, 97):
        for sf in (7, 8, 9):
            e = abs(airtime_ms(pl, sf) - toa_formula(pl, sf))
            err = max(err, e)
    E.add("airtime.max_abs_diff_ms", err, "ms", "ANALYTICAL", "lora.airtime_ms against the formula as transcribed in fin_b3.toa_formula, SF7 to SF9, 125 kHz, CR 4/5, payloads 14, 16, 26, 97 bytes; the Semtech document was NOT opened (stated)")
    rows = collision_check()
    for r in rows:
        k = f"collision.n{r['n']}"
        E.add(f"{k}.G", round(r["G"], 4), "load", "SIMULATED", "offered load n x airtime / period")
        E.add(f"{k}.sim", round(r["sim"], 5), "fraction", "SIMULATED", f"collision probability of unconfirmed 16-byte heartbeats, SF7, no capture, {r['sent']} transmissions")
        E.add(f"{k}.aloha", round(r["aloha"], 5), "fraction", "ANALYTICAL", "1 - exp(-2G)")
        E.add(f"{k}.finite", round(r["finite"], 5), "fraction", "ANALYTICAL", "1 - (1 - 2 tau / T)^(n - 1), finite population, random phases")
    ae = [abs(r["sim"] - r["aloha"]) for r in rows]
    fe = [abs(r["sim"] - r["finite"]) for r in rows]
    E.add("collision.max_abs_err_vs_aloha", round(max(ae), 5), "fraction", "SIMULATED", "over the loads above")
    E.add("collision.max_abs_err_vs_finite", round(max(fe), 5), "fraction", "SIMULATED", "over the loads above")
    E.write()
    for r in rows:
        print(r["n"], round(r["G"], 3), round(r["sim"], 4), round(r["aloha"], 4), round(r["finite"], 4))
    print("airtime max diff ms", err)


if __name__ == "__main__":
    main()
