"""R6-5 and R6-7 (docs/02_preregistration/PREREGISTRATION_V17.md sections 7 and 8): exact airtime, attempts that fit before a deadline, the extra airtime of the two-stage alert as a bound
that depends on the spreading factor, the micro-confirm analytic part and its tag-length analysis. Keys ``r6.b.*`` (ANALYTICAL; the transmissions per retracted event come from stored ns-3 outputs).

    python -m crashguard.r6_bounds

Nothing here is a hypothesis test. Every formula is written in docs/03_results/ROUND6_BOUNDS.md next to its inputs.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard.lora import airtime_ms
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r6_bounds.py"
SFS = (7, 8, 9, 10, 11, 12)
FRAMES = {"micro": 7, "flash": 14, "ack": 26, "alert": 97}
ALLOWANCE_S = 0.01 * 3600.0  # hourly allowance of the ns-3 application and the custom simulator (xsim_alert.cc g_limit = duty x 3600)
RX_DELAY_S = 0.2  # the node knows an attempt failed when the second receive window (0.2 s in the policies p1, quick, d1) has passed
TAG_BYTES = 5


def A(n: int, sf: int) -> float:
    return airtime_ms(n, sf) / 1000.0


def load_keys() -> dict:
    return {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}


def transmissions_per_retracted(sf: int) -> float:
    """Mean airtime of a retracted event (early alarm, no full-window alarm) in the loss-free ns-3 cells divided by the airtime of a 14-byte frame: transmissions per retracted event (stored raw outputs)."""
    from crashguard import pp_r3_ns3 as P

    ev = pd.read_csv(ROOT / "results" / "tables" / "s6_events_seed42_a1.csv")
    tr = ev[ev.triggered].reset_index(drop=True)
    E = pd.DataFrame(dict(E=tr.alarm_E.astype(int), F=tr.alarm_F.astype(int), y=tr.y.astype(int)))
    vals = []
    for s in range(1, 61):
        d, _, _ = P.load(P.fname(sf, "calib", 0.0, "r3t", s), E)
        d = d[(d.dropped == 0) & (d.E == 1) & (d.F == 0)]
        if len(d):
            vals.append(d.air.mean())
    return float(np.mean(vals)) / A(14, sf)


def main() -> None:
    R = load_keys()
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"r6.b.{name}", value=(round(v, 6) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin="ANALYTICAL", source_file=SRC, notes=note))

    rho = R["ar.r3.a1.retraction_share"]
    add("input.retraction_share", rho, "fraction", "stored: share of provisional alarms withdrawn by the full window at the 1% target (ar.r3.a1.retraction_share)")
    add("input.allowance_s_per_hour", ALLOWANCE_S, "s", "1% of an hour (the duty model of the ns-3 application and the custom simulator is an hourly allowance, not a per-transmission off-time)")
    rows = []
    for sf in SFS:
        a = {k: A(n, sf) for k, n in FRAMES.items()}
        for k, v in a.items():
            add(f"air.sf{sf}.{k}_s", v, "s", f"time on air of {FRAMES[k]} bytes at SF{sf}, 125 kHz, CR 4/5, explicit header, CRC, 8 preamble symbols")
        tcyc = a["alert"] + RX_DELAY_S + a["ack"]
        for D in (10, 30):
            kt = int(math.floor((D - a["alert"]) / tcyc)) + 1 if D >= a["alert"] else 0
            add(f"attempts.sf{sf}.d{D}.time_limited", kt, "attempts", f"floor((D - A97) / (A97 + {RX_DELAY_S} s + A26)) + 1 for D = {D} s")
        for nm in ("alert", "flash", "micro"):
            add(f"attempts.sf{sf}.{nm}.per_hour_allowance", int(math.floor(ALLOWANCE_S / a[nm])), "frames", f"floor(36 s / A) for the {FRAMES[nm]}-byte frame")
        lb_ratio = a["flash"] / a["alert"]
        m_r = transmissions_per_retracted(sf) if sf in (7, 9) else float("nan")
        rows.append((sf, a, lb_ratio, m_r))
    m_r7, m_r9 = rows[0][3], rows[2][3]
    add("input.transmissions_per_retracted.sf7", m_r7, "frames", "mean airtime of a retracted event in the loss-free ns-3 cells over A14 (stored raw outputs, seeds 1 to 60)")
    add("input.transmissions_per_retracted.sf9", m_r9, "frames", "same at SF9")
    m_r = 0.5 * (m_r7 + m_r9)
    add("input.transmissions_per_retracted", m_r, "frames", "mean of the two; used for every SF (an assumption: the count of frames does not depend on SF)")
    for sf, a, lb, _ in rows:
        # lower bound of the extra airtime of the two-stage alert (no collisions, no retries): per provisional alarm, (1 - rho) confirmed events cost A14 + A97 against A97, rho retracted events cost m_r x A14 against nothing
        lbound = lb * (1.0 + rho * (m_r - 1.0) / (1.0 - rho))
        add(f"extra.sf{sf}.r3_lower_bound", lbound, "ratio", "(A14/A97) x (1 + rho (m_r - 1)/(1 - rho)); a lower bound of the two-stage extra airtime: retries and collisions only add")
        add(f"extra.sf{sf}.flash_share", lb, "ratio", "A14 / A97")
        # micro-confirm: per provisional alarm, (1-rho) confirmed: A14 + A7 against A97; rho retracted: A14 + (m_r - 1) x A7 against nothing
        num = (1 - rho) * (a["flash"] + a["micro"]) + rho * (a["flash"] + (m_r - 1) * a["micro"])
        den = (1 - rho) * a["alert"]
        add(f"extra.sf{sf}.micro_lower_bound", num / den - 1.0, "ratio", "two-stage total with the 7-byte micro-confirm over the single-stage total of 97-byte alerts, minus one (negative: the micro-confirm replaces the full alert and drops its content)")
        r3_tot = (1 - rho) * (a["flash"] + a["alert"]) + rho * m_r * a["flash"]
        add(f"extra.sf{sf}.micro_over_r3", num / r3_tot, "ratio", "airtime per provisional alarm of the micro scheme over that of R3's two-stage scheme (the second statistic of H-R6-1a)")
    for sf in (7, 9):
        for st in ("calib", "shipped"):
            obs = R[f"pp.p1.sf{sf}.{st}.p0.extra_air_ratio"]
            lbv = R[f"r6.b.extra.sf{sf}.r3_lower_bound"] if f"r6.b.extra.sf{sf}.r3_lower_bound" in R else next(e["value"] for e in ent if e["name"] == f"r6.b.extra.sf{sf}.r3_lower_bound")
            add(f"check.sf{sf}.{st}.observed_loss_free", obs, "ratio", "stored ns-3 value (pp.p1) at extra loss 0")
            add(f"check.sf{sf}.{st}.inflation_over_bound", obs / lbv, "ratio", "observed / lower bound: the factor that retries and collisions add in ns-3")
    cross = [sf for sf, a, lb, _ in rows if next(e["value"] for e in ent if e["name"] == f"r6.b.extra.sf{sf}.r3_lower_bound") >= 0.40]
    add("rule.sf_where_lower_bound_reaches_40pct", cross[0] if cross else 0, "SF", "smallest SF whose lower bound reaches 0.40 (0 = none up to SF12)")
    # tag-length analysis of the micro-confirm
    fr = 0.01 * 3600.0 / A(7, 7)
    add("forge.max_frames_per_hour_sf7", fr, "frames", "36 s / A7 at SF7: the attacker's frame ceiling at the 1% allowance")
    for tb in (4, 5, 6, 8):
        p = 2.0 ** (-8 * tb)
        add(f"forge.tag{tb}.p_per_attempt", p, "probability", "2^-(8 x tag bytes)")
        add(f"forge.tag{tb}.p_per_year_at_ceiling", min(1.0, p * fr * 8766), "probability", "attempts per year at the ceiling times p (every frame assumed to hit a pending flash: an upper bound)")
        add(f"forge.tag{tb}.expected_years", 1.0 / (p * fr * 8766), "years", "1 / (p x frames per year)")
    record_many(ent, purge_prefixes=("r6.b.",))
    # table for the document
    out = ["| SF | A7 | A14 | A26 | A97 (s) | attempts in 10 s | attempts in 30 s | A14/A97 | R3 bound | micro bound | micro over R3 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    G = {e["name"]: e["value"] for e in ent}
    for sf in SFS:
        g = lambda n: G[f"r6.b.{n}"]  # noqa: E731
        out.append(f"| {sf} | {g(f'air.sf{sf}.micro_s'):.4f} | {g(f'air.sf{sf}.flash_s'):.4f} | {g(f'air.sf{sf}.ack_s'):.4f} | {g(f'air.sf{sf}.alert_s'):.4f} | {g(f'attempts.sf{sf}.d10.time_limited')} | {g(f'attempts.sf{sf}.d30.time_limited')} | "
                   f"{g(f'extra.sf{sf}.flash_share'):.3f} | {g(f'extra.sf{sf}.r3_lower_bound'):.3f} | {g(f'extra.sf{sf}.micro_lower_bound'):.3f} | {g(f'extra.sf{sf}.micro_over_r3'):.3f} |")
    (ROOT / "docs" / "03_results" / "_r6_bounds_table.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    for k in ("r6.b.check.sf7.calib.inflation_over_bound", "r6.b.check.sf9.calib.inflation_over_bound", "r6.b.input.transmissions_per_retracted", "r6.b.rule.sf_where_lower_bound_reaches_40pct", "r6.b.forge.tag5.expected_years", "r6.b.forge.tag4.p_per_year_at_ceiling"):
        print(k, G[k])


if __name__ == "__main__":
    main()
