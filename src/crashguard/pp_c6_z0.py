"""Zero-spacing control check (docs/02_preregistration/PREREGISTRATION_V13.md section 3). Keys ``pp.c6.z0.*``.

Reads the stored held-out T1 replay (``data/processed/r3_t1_held.pkl``) and reports, for the exploratory control Z0 (retry at once, no hold, base spreading factor, 12 tries) and for D1, the airtime per alert and per device
as a share of the hourly budget of the 1% duty limit (36 s) and of the 10% limit named in the paper prompt (360 s), the largest possible airtime of one Z0 alert, and the deadline invariant. No replay is rerun.

    python -m crashguard.pp_c6_z0
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np

from crashguard import r3_t1 as T
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/pp_c6_z0.py"


def links() -> None:
    """Descriptive statistics of the held-out link population, copied from ``results/tables/r3_t1_descriptive.json`` (written by r3_t1_extract; TRACE_DRIVEN). Keys ``pp.c6.links.*``."""
    s = json.loads((ROOT / "results" / "tables" / "r3_t1_descriptive.json").read_text(encoding="utf-8"))["stats"]["held"]
    ent = []

    def add(name, value, unit, notes):
        ent.append(dict(name=f"pp.c6.links.{name}", value=round(value, 5) if isinstance(value, float) else value, unit=unit, origin="TRACE_DRIVEN", source_file=SRC, notes=notes))

    add("n_devices", int(s["n_devices"]), "devices", "HELD-OUT devices (r3_t1_descriptive.json)")
    add("median_loss", float(s["loss_quantiles"]["0.5"]), "fraction", "median over devices of the lost share of frames (frame-counter gaps: gateway reception, not link loss alone)")
    add("mean_loss", float(s["mean_loss"]), "fraction", "mean over devices")
    add("pooled_loss", float(s["pooled_loss"]), "fraction", "lost frames over all frames")
    add("lag1_autocorr", float(s["autocorr"]["1"]), "1", "lag-1 autocorrelation of the loss indicator")
    add("p_loss_given_prev_loss", float(s["p_loss_given_prev_loss"]), "fraction", "probability that a frame is lost after a lost frame")
    add("burst_mean", float(s["burst_runs"]["mean"]), "frames", "mean length of runs of lost frames")
    record_many(ent, purge_prefixes=("pp.c6.links.",))


def main() -> None:
    d = pickle.loads((ROOT / "data" / "processed" / "r3_t1_held.pkl").read_bytes())
    res = d["res"]
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="TRACE_DRIVEN"):
        ent.append(dict(name=f"pp.c6.z0.{name}", value=round(value, 6) if isinstance(value, float) else value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    a97 = T.air(97, T.SF0)
    max_alert = 12 * a97
    add("air_97B_base_sf_s", a97, "s", "time on air of the 97-byte alert at the base spreading factor (SF9)", "ANALYTICAL")
    add("max_air_one_alert_s", max_alert, "s", "12 transmissions of the 97-byte alert at the base spreading factor (the most a Z0 alert can send)", "ANALYTICAL")
    add("max_air_share_of_1pct_budget", max_alert / T.LIMIT_S, "fraction", "of the 36 s hourly budget of the 1% limit", "ANALYTICAL")
    add("max_air_share_of_10pct_budget", max_alert / (10 * T.LIMIT_S), "fraction", "of the 360 s hourly budget of the 10% limit named in the paper prompt", "ANALYTICAL")
    add("alerts_per_hour_to_exhaust_1pct_worst_case", float(np.floor(T.LIMIT_S / max_alert)) + 1.0, "alerts", "worst-case Z0 alerts in one hour that would pass the 36 s budget", "ANALYTICAL")
    add("invariant_late_delivery", int(d["inv"]["late_delivery"]), "count", "deliveries after the 10 s deadline over all policies including Z0 (must be 0)")
    add("invariant_duty_exceeded", int(d["inv"]["duty_exceeded"]), "count", "transmissions blocked by the 36 s hourly budget over all policies including Z0 (must be 0); each replayed alert starts with an empty hour")
    n_bad = 0
    for g, lo, hi in T.GROUPS:
        idx = [r for r in res if lo <= r["p"] < hi]
        for pol in ("Z0", "D1", "quick"):
            a = np.array([r["mean_air"][pol] for r in idx])
            add(f"{g}.{pol}.mean_air_per_alert_s_median", float(np.median(a)), "s", f"median over {len(idx)} held-out devices of the mean transmit airtime per alert")
            add(f"{g}.{pol}.mean_air_per_alert_s_p95", float(np.quantile(a, 0.95)), "s", "95th percentile over devices")
            add(f"{g}.{pol}.mean_air_per_alert_s_max", float(a.max()), "s", "largest over devices")
            add(f"{g}.{pol}.share_of_1pct_budget_per_alert_median", float(np.median(a)) / T.LIMIT_S, "fraction", "mean airtime of one alert as a share of the 36 s hourly budget")
        z = np.array([r["mean_air"]["Z0"] for r in idx])
        n_bad += int((z > T.LIMIT_S).sum())
        add(f"{g}.Z0.alerts_per_hour_to_exhaust_median_device", float(T.LIMIT_S / max(float(np.median(z)), 1e-9)), "alerts", "alerts of the median device's mean size per hour that would use the whole 36 s budget")
    valid = (max_alert <= T.LIMIT_S) and d["inv"]["late_delivery"] == 0 and d["inv"]["duty_exceeded"] == 0 and n_bad == 0
    add("n_devices_mean_air_above_budget", n_bad, "devices", "held-out devices whose mean Z0 airtime per alert exceeds the 36 s budget")
    add("valid", int(valid), "flag", "Z0 is valid if no single Z0 alert can exceed the 1% hourly budget and the deadline invariant holds (V13 section 3)")
    add("deliv_Z0_minus_D1_H", float(R["r3.t1.explore.H.deliv.Z0"]) - float(R["r3.t1.H.deliv.D1"]), "fraction", "delivery of Z0 minus D1 in group H (links with 40% loss or more), from the stored keys")
    record_many(ent, purge_prefixes=("pp.c6.z0.",))
    links()
    print("valid", valid, "max alert air", round(max_alert, 2), "n_bad", n_bad)


if __name__ == "__main__":
    main()
