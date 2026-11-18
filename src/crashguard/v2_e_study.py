"""Study E (docs/02_preregistration/PREREGISTRATION_V2.md section 4): authentication-tag length against capacity. E1 forgery model (ANALYTICAL), E2 burst-cell simulation with the message lengths implied by each tag length (SIMULATED), E3 table and figure.
Prefix ``v2.e.``. The tag is a truncated HMAC-SHA256 with a secret key; truncating a tag is a known trade-off and no cryptographic proof is claimed. The duty limit (1%) is not verified for India and does not bind an attacker.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import s11_sct as S11
from crashguard import v2_b_study as VB
from crashguard import v2_pools as VP
from crashguard.capacity import air
from crashguard.sct_sim import SctParams
from crashguard.v2_common import Entries, mean_of_cells, paired_diffs

TAGS = (4, 6, 8, 12, 16)
SFS = (7, 8, 9)
ALERT_BODY, FLASH_BODY, ACK_BODY = 89, 6, 18
THRESH = 2.0 ** 32
SRC = "results/tables/v2_e_forgery.csv"


def forgery_table() -> pd.DataFrame:
    rows = []
    for t in TAGS:
        bits = 8 * t
        p_one = 2.0 ** (-bits)
        n6 = math.log1p(-1e-6) / math.log1p(-p_one) if bits < 52 else 1e-6 * 2.0 ** bits  # attempts for a success probability of 1e-6 (the series for very small p_one)
        for sf in SFS:
            tau = air(ALERT_BODY + t, sf)
            rate = math.floor(0.01 * 3600.0 / tau)
            rows.append(dict(tag_bytes=t, sf=sf, alert_bytes=ALERT_BODY + t, airtime_s=tau, attempts_per_hour_dutycap=rate, attempts_per_hour_uncapped=3600.0 / tau, p_forgery_per_attempt_log2=-bits,
                             attempts_for_1e6=n6, log2_attempts_for_1e6=math.log2(n6), expected_attempts_log2=bits - 1,
                             hours_for_1e6_dutycap=n6 / rate, years_expected_dutycap=2.0 ** (bits - 1) / rate / 8766.0, hours_for_1e6_uncapped=n6 / (3600.0 / tau)))
    return pd.DataFrame(rows)


def main() -> None:
    workers = min(14, os.cpu_count() or 1)
    ent = Entries("v2.e", SRC, "ANALYTICAL")
    ft = forgery_table()
    ft.to_csv(C.TABLES / "v2_e_forgery.csv", index=False)
    for r in ft.itertuples():
        k = f"forgery.t{r.tag_bytes}.sf{r.sf}"
        ent.add(f"{k}.airtime_s", round(r.airtime_s, 5), "s", "Semtech formula, 125 kHz, coding rate 4/5, explicit header, CRC on")
        ent.add(f"{k}.attempts_per_hour_dutycap", int(r.attempts_per_hour_dutycap), "frames per hour", "single transmitter limited to 1% duty (the limit does not bind a real attacker)")
        ent.add(f"{k}.attempts_per_hour_uncapped", round(r.attempts_per_hour_uncapped, 1), "frames per hour", "back-to-back frames; sensitivity")
        ent.add(f"{k}.log2_attempts_for_1e6", round(r.log2_attempts_for_1e6, 3), "log2 attempts", "attempts for a success probability of 1e-6")
        ent.add(f"{k}.hours_for_1e6_dutycap", float(f"{r.hours_for_1e6_dutycap:.4g}"), "hours")
        ent.add(f"{k}.years_expected_dutycap", float(f"{r.years_expected_dutycap:.4g}"), "years", "expected time to one forgery at the duty-capped rate")
    for t in TAGS:
        ent.add(f"forgery.t{t}.log2_expected_attempts", 8 * t - 1, "log2 attempts", "expected attempts 2^(8t-1)")
    he2 = all(row.log2_attempts_for_1e6 > 32 and row.expected_attempts_log2 > 32 for row in ft[ft.tag_bytes == 8].itertuples())
    ent.add("hE2.criterion_met", int(he2), "flag", "at 8 bytes, attempts for 1e-6 success and expected attempts both above 2^32, at SF7 to SF9")
    ent.add("hE2.log2_attempts_for_1e6_t8", round(float(ft[ft.tag_bytes == 8].log2_attempts_for_1e6.iloc[0]), 3), "log2 attempts")
    mins = [t for t in range(1, 17) if math.log2(1e-6 * 2.0 ** (8 * t)) > 32 and 8 * t - 1 > 32]
    ent.add("e3.smallest_tag_bytes_above_2p32", min(mins), "bytes", "smallest tag with both work factors above 2^32 (analytic, any length 1 to 16; the simulation covers 4, 6, 8, 12, 16)")
    # ---------------- E2 simulation
    params = SctParams(h_s=float(VB.RES["s11.tuned.h_s"]), rho_f=float(VB.RES["s11.tuned.rho_f"]), sf_raise=bool(VB.RES["s11.tuned.sf_raise"]))
    pools = VP.default_pools()
    cl = [c for c in VB.cells() if c["group"] == "burst"]
    jobs = []
    for ack_too in (False, True):
        for t in TAGS:
            for pol in ("P1", "P2"):
                for cell in cl:
                    for h in range(VB.EVAL_HOURS):
                        cfg = VB.make(cell, pol, None if pol == "P1" else dict(kind="fixed", s0=1.0), h, VB.EVAL_SEED, pools, params)
                        cfg.alert_len, cfg.flash_len, cfg.ack_len = ALERT_BODY + t, FLASH_BODY + t, (ACK_BODY + t if ack_too else None)
                        jobs.append((cfg, dict(cell=cell["name"], cfg=f"{pol}_t{t}" + ("_ack" if ack_too else ""), hour=h, tag=t, pol=pol, ack_too=ack_too)))
    R = S11.run_jobs(jobs, workers)
    R.to_csv(C.TABLES / "v2_e_runs.csv", index=False)
    sim = Entries("v2.e", "results/tables/v2_e_runs.csv", "SIMULATED")
    sim.add("sim.runs", len(R), "runs")
    sim.add("sim.duty.runs_exceeding_limit", int(R.duty_exceeded.sum()), "runs", "independent scan; must be 0")
    unl = [c["name"] for c in cl if not c["name"].startswith("loaded")]
    allc = [c["name"] for c in cl]
    for ack_too, sfx in ((False, ""), (True, "_ack")):
        for pol in ("P1", "P2"):
            for t in TAGS:
                sub = R[(R.cfg == f"{pol}_t{t}{sfx}")]
                for m in ("reach10_critical", "reach30_critical", "node_air_share", "alert_collided_share", "fast_air_share_of_allowance"):
                    sim.add(f"cells.{pol}.t{t}{sfx}.{m}", round(float(sub[m].mean()), 5), "fraction", "mean over the 10 burst cells and 40 seeds")
        for pol in ("P1", "P2"):
            for t in (4, 6, 12, 16):
                for grp, cs in (("unloaded", unl), ("all", allc)):
                    for m in ("reach10_critical", "reach30_critical"):
                        d = paired_diffs(R, cs, f"{pol}_t8{sfx}", f"{pol}_t{t}{sfx}", m)
                        p, dr = mean_of_cells(d)
                        sim.ci(f"gain.{pol}.t{t}_minus_t8{sfx}.{grp}.{m}", (p, float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "fraction", "mean over cells of the paired seed-mean difference", d=5)
    d = paired_diffs(R, unl, "P2_t8", "P2_t4", "reach10_critical")
    p, dr = mean_of_cells(d)
    ph = float(max(np.mean(dr <= 0.02), 1.0 / 1001))
    sim.ci("hE1.gain_t4_minus_t8", (p, float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "fraction", "P2, 7 unloaded burst cells", d=5)
    sim.add("hE1.p_raw", round(ph, 4), "probability", "gain at or below 0.02")
    sim.add("hE1.criterion_met", int(p >= 0.02 and float(np.quantile(dr, 0.025)) > 0.0), "flag", "gain of at least 2 points with the interval above zero")
    # per-cell gain for the record
    for cell in unl:
        dd = paired_diffs(R, [cell], "P2_t8", "P2_t4", "reach10_critical")
        if dd:
            sim.add(f"hE1.cell.{cell}.gain", round(float(dd[0].mean()), 5), "fraction")
    ent.items += sim.items
    ent.flush()
    pd.DataFrame([dict(h="H-E1", p=ph)]).to_csv(C.TABLES / "v2_e_pvalues.csv", index=False)
    # ---------------- E3 table and figure
    rows = []
    for t in TAGS:
        sub = R[R.cfg == f"P2_t{t}"]
        r_ = ft[(ft.tag_bytes == t) & (ft.sf == 9)].iloc[0]
        rows.append(dict(tag_bytes=t, alert_bytes=ALERT_BODY + t, log2_expected_attempts=8 * t - 1, log2_attempts_for_1e6=r_.log2_attempts_for_1e6, years_expected_dutycap_sf9=r_.years_expected_dutycap,
                         reach10_critical_P2=float(sub[sub.cell.isin(unl)].reach10_critical.mean()), reach30_critical_P2=float(sub[sub.cell.isin(unl)].reach30_critical.mean())))
    pd.DataFrame(rows).to_csv(C.TABLES / "v2_e_curve.csv", index=False)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        e3 = pd.DataFrame(rows)
        fig, ax = plt.subplots(figsize=(6.2, 3.8))
        ax.plot(e3.tag_bytes, e3.log2_expected_attempts, "o-", color="#0072B2", label="forgery work factor (log2 expected attempts)")
        ax.axhline(32, color="#999999", ls="--", lw=1)
        ax.text(4.1, 33, "2^32 attempts", fontsize=8, color="#555555")
        ax.set_xlabel("Authentication tag length (bytes)")
        ax.set_ylabel("log2 expected forgery attempts (bits)", color="#0072B2")
        ax2 = ax.twinx()
        ax2.plot(e3.tag_bytes, e3.reach10_critical_P2 * 100, "s-", color="#D55E00", label="critical reach within 10 s (7 unloaded burst cells, SIMULATED)")
        ax2.set_ylabel("Critical alerts acknowledged within 10 s (%)", color="#D55E00")
        ax.set_title("Tag length against forgery work and burst delivery", fontsize=10)
        fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(C.FIGURES / f"v2_e_tag_curve.{ext}", dpi=300)
        plt.close(fig)
    except Exception as e:  # noqa: BLE001
        print("figure not written:", e)
    print(pd.DataFrame(rows).round(4).to_string())
    print("H-E1", round(p, 4), [round(float(np.quantile(dr, q)), 4) for q in (0.025, 0.975)], "p", ph, "| H-E2", he2)
    print(json.dumps({k: round(float(v), 3) for k, v in R[R.cfg.str.startswith("P2_t") & ~R.cfg.str.endswith("_ack")].groupby("cfg").reach10_critical.mean().items()}))


if __name__ == "__main__":
    main()
