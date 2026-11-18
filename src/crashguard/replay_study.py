"""The replay study: grids over spreading factor, loss model and policy; sensitivity; replay flood; conclusions that survive; figures. SIMULATED.

Built on ``replay.py`` (the engine). The event pool is MEASURED_SOFTWARE; arrivals, loss and timing are simulated with the assumptions listed there.
Hour-level results (20 simulated hours for each of the 5 seeds = 100 hours per cell) feed bootstrap 95% intervals. Policy comparisons are paired: the
arrivals depend only on scenario, seed and hour, so two policies see the same alerts.
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard.lora import airtime_ms
from crashguard.replay import (CANCEL_S, COMPUTE_S, GE_LOSS_BAD, GE_P_BG, POLICIES, SEV_NAMES, Scenario, ci_of, load_pool, run_config, simulate)
from crashguard import boot as B

POLICY_NAMES = ("none", "fixed3", "severity")
LOSSES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
HEADLINE_LOSSES = (0.0, 0.3, 0.6)
SFS = (7, 9, 12)
HOURS = 20
CLASS_KEYS = ("all", "low", "moderate", "severe", "critical")
SRC = "results/tables/replay_grid.csv"
FLOOD = (40.0, 120.0, 20.0)  # start (s), duration (s), replayed packets per second
FLOOD_BASE_S = 30.0  # base station budget left when the flood starts (s)
FLOOD_ALERTS_PER_H = 120


def stress_pool(n: int = 1000) -> np.ndarray:
    """ASSUMED mix 40% low, 30% moderate, 20% severe, 10% critical (the mix used in the earlier delivery simulation)."""
    return np.repeat([0, 1, 2, 3], [int(n * p) for p in (0.4, 0.3, 0.2, 0.1)])


def pools() -> dict[str, np.ndarray]:
    pool = load_pool()
    out = {"vzcrash": pool[pool.alert].sev.to_numpy(), "stress": stress_pool()}
    try:
        from crashguard import severity_study as SS

        tests = SS.load_tests()
        if tests:
            out["nhtsa16"] = SS._rows(tests, range_g=C.MPU_RANGE_G, fs=float(C.FS_HZ)).cls.to_numpy()
    except Exception:  # NHTSA data not available: the pool is simply absent, never faked
        pass
    return out


def _cell_row(h: pd.DataFrame, **ident) -> dict:
    row = dict(ident)
    for k in h.columns:
        if k not in ("seed", "hour"):
            row[k] = float(h[k].mean())
    for cl in CLASS_KEYS:
        for c in (f"delivered_{cl}", f"median_lat_s_{cl}"):
            if c in h:
                p, lo, hi = ci_of(h, c)
                row[c + "_lo"], row[c + "_hi"] = lo, hi
    return row


def grid_rows(pool_name: str, sev: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """Main grid: spreading factor x loss model x loss level x policy."""
    rows, hourly = [], {}
    for sf in SFS:
        for kind in ("iid", "ge"):
            for loss in LOSSES:
                sc = Scenario(f"grid_sf{sf}_{kind}_{int(loss * 100)}", sf, 20, loss_up=loss, loss_down=loss, kind=kind)
                for pn in POLICY_NAMES:
                    h = run_config(sev, sc, POLICIES[pn], hours=HOURS)
                    rows.append(_cell_row(h, pool=pool_name, sf=sf, kind=kind, loss=loss, policy=pn))
                    hourly[(pool_name, sf, kind, loss, pn)] = h
    return pd.DataFrame(rows), hourly


def sensitivity_rows(pool_name: str, sev: np.ndarray) -> tuple[pd.DataFrame, dict]:
    """Event rate, base station near its budget, separate ACK loss, cancel-window scale, node near its budget."""
    cells: list[tuple[str, Scenario]] = []
    for sf in (7, 12):
        for rate in (10, 60, 120, 240):
            cells.append(("rate", Scenario(f"rate_sf{sf}_{rate}", sf, rate, loss_up=0.3, loss_down=0.3)))
    for sf in SFS:
        cells.append(("basenear", Scenario(f"basenear_sf{sf}", sf, 60, base_initial_s=2.0, loss_up=0.3, loss_down=0.3)))
        cells.append(("baseref", Scenario(f"baseref_sf{sf}", sf, 60, loss_up=0.3, loss_down=0.3)))
    for sf in (7, 12):
        for up, down in ((0.3, 0.1), (0.3, 0.5), (0.1, 0.5), (0.5, 0.1)):
            cells.append(("ackloss", Scenario(f"ackloss_sf{sf}_{int(up * 100)}_{int(down * 100)}", sf, 20, loss_up=up, loss_down=down)))
        for cs in (0.5, 2.0):
            cells.append(("cancel", Scenario(f"cancel_sf{sf}_{cs:g}", sf, 20, loss_up=0.3, loss_down=0.3, cancel_scale=cs)))
        cells.append(("nodenear", Scenario(f"nodenear_sf{sf}", sf, 60, node_initial_s=36.0, loss_up=0.3, loss_down=0.3)))
    rows, hourly = [], {}
    for fam, sc in cells:
        for pn in POLICY_NAMES:
            h = run_config(sev, sc, POLICIES[pn], hours=HOURS)
            rows.append(_cell_row(h, pool=pool_name, family=fam, scenario=sc.name, sf=sc.sf, rate=sc.rate_per_h, loss_up=sc.loss_up, loss_down=sc.loss_down, policy=pn))
            hourly[(pool_name, sc.name, pn)] = h
    return pd.DataFrame(rows), hourly


def flood_rows(pool_name: str, sev: np.ndarray) -> pd.DataFrame:
    """Replay flood inside the same pipeline: a captured alert replayed 20 times per second for 120 s from t = 40 s, base budget 30 s, re-ACK limit on and off."""
    rows = []
    for limit in (False, True):
        sc = Scenario(f"flood_{'limit' if limit else 'free'}", 7, FLOOD_ALERTS_PER_H, base_initial_s=FLOOD_BASE_S, loss_up=0.1, loss_down=0.1, reack_limit=limit, flood=FLOOD)
        for seed in C.SEEDS:
            for h in range(HOURS):
                al = simulate(sev, sc, POLICIES["severity"], random.Random(f"arr|flood|{seed}|{h}"), random.Random(f"ch|flood|{limit}|{seed}|{h}"))
                d = pd.DataFrame(al)
                if d.empty:
                    continue
                inside = (d.arrival >= 40.0) & (d.arrival < 160.0)
                rows.append(dict(pool=pool_name, limit=limit, seed=seed, hour=h, n_inside=int(inside.sum()),
                                 delivered_inside=float(d[inside].t_ack.notna().mean()) if inside.any() else np.nan,
                                 delivered_outside=float(d[~inside].t_ack.notna().mean()) if (~inside).any() else np.nan,
                                 base_ack_airtime_s=float(d.base_airtime_s.iloc[0]), replayed=float(d.flood_replayed.iloc[0])))
    return pd.DataFrame(rows)


def paired(h_a: pd.DataFrame, h_b: pd.DataFrame, col: str) -> tuple[float, float, float]:
    """Paired bootstrap difference (b minus a) of an hour-level metric on the same arrivals; hours where either side is missing are dropped."""
    if col not in h_a or col not in h_b:
        return (float("nan"),) * 3
    m = pd.concat([h_a[col].reset_index(drop=True), h_b[col].reset_index(drop=True)], axis=1, keys=["a", "b"]).dropna()
    return B.paired_diff(m.a.to_numpy(), m.b.to_numpy(), np.mean) if len(m) else (float("nan"),) * 3


def _eval_cell(cell: str, pool: str, h: dict, family: str) -> list[dict]:
    out = []

    def put(cn, d, holds):
        out.append(dict(cell=cell, family=family, pool=pool, conclusion=cn, holds=bool(holds), value=d[0], lo=d[1], hi=d[2]))

    d = paired(h["none"], h["fixed3"], "delivered_all")
    put("C1_retries_help", d, d[1] > 0)
    d = paired(h["fixed3"], h["severity"], "delivered_critical")
    if not np.isnan(d[0]):
        put("C2_severity_not_worse_for_critical", d, d[1] > -0.02)
        put("C2b_severity_better_for_critical", d, d[1] > 0)
    d = paired(h["fixed3"], h["severity"], "delivered_low")
    if not np.isnan(d[0]):
        put("C3_severity_costs_low_alerts", d, d[2] < 0)
    d = paired(h["fixed3"], h["severity"], "airtime_share_total")
    put("C5_severity_uses_less_airtime", d, d[2] < 0)
    return out


def conclusions(hourly: dict, sens_hourly: dict) -> pd.DataFrame:
    """Five conclusions tested in every cell of the grid and of the sensitivity set; 'holds' means the interval condition is met in that cell."""
    rows = []
    for (pool, sf, kind, loss, pn) in hourly:
        if pn != "none" or loss == 0.0:
            continue
        h = {p: hourly[(pool, sf, kind, loss, p)] for p in POLICY_NAMES}
        rows += _eval_cell(f"{pool}|grid|sf{sf}|{kind}|loss{int(loss * 100)}", pool, h, "grid")
    names: dict = {}
    for (pool, sname, pn), hh in sens_hourly.items():
        names.setdefault((pool, sname), {})[pn] = hh
    for (pool, sname), h in names.items():
        rows += _eval_cell(f"{pool}|{sname}", pool, h, sname.split("_")[0])
    for (pool, sf, kind, loss, pn), h_ge in hourly.items():  # C4: burst against independent loss at the same mean loss (unpaired intervals must not overlap)
        if kind != "ge" or pn != "fixed3" or loss == 0.0:
            continue
        a, b = ci_of(hourly[(pool, sf, "iid", loss, pn)], "delivered_all"), ci_of(h_ge, "delivered_all")
        rows.append(dict(cell=f"{pool}|grid|sf{sf}|loss{int(loss * 100)}", family="grid", pool=pool, conclusion="C4_burst_lowers_delivery", holds=bool(b[2] < a[1]),
                         value=b[0] - a[0], lo=b[1] - a[2], hi=b[2] - a[1]))
    return pd.DataFrame(rows)


def stage_timeline() -> pd.DataFrame:
    """Per class: the stages from the trigger to the ACK for a lossless exchange at SF7 (ANALYTICAL from the stated stage times)."""
    air, air_ack = airtime_ms(P.ALERT_LEN, 7) / 1000.0, airtime_ms(P.ACK_LEN, 7) / 1000.0
    return pd.DataFrame([dict(sev=SEV_NAMES[s], window_fill_s=C.POST_S, compute_s=COMPUTE_S, cancel_s=CANCEL_S[s], alert_airtime_s=air, base_processing_s=0.1, ack_airtime_s=air_ack)
                         for s in range(4)])


def figures(grid: pd.DataFrame, example: dict, timeline: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for j, sf in enumerate(SFS):
        ax = axes[j]
        for i, pn in enumerate(POLICY_NAMES):
            for kind, ls in (("iid", "-"), ("ge", "--")):
                g = grid[(grid.pool == "stress") & (grid.sf == sf) & (grid.policy == pn) & (grid.kind == kind)].sort_values("loss")
                ax.plot(g.loss * 100, g.delivered_all * 100, ls=ls, marker="o", ms=3, color=COLORS[i], label=f"{pn}, {'independent' if kind == 'iid' else 'burst'}")
        ax.set_xlabel("Mean packet loss per transmission (%)")
        ax.set_title(f"SF{sf}", fontsize=9)
    axes[0].set_ylabel("Alerts whose ACK reached the car (%)")
    axes[0].legend(fontsize=6)
    fig.suptitle("Replay delivery against loss (SIMULATED; assumed severity mix 40/30/20/10)", fontsize=9)
    save(fig, "replay_delivery_vs_loss")
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharex=True, sharey=True)
    for ax, pn in zip(axes, ("severity", "fixed3")):
        d = example[pn]
        for i, s in enumerate(SEV_NAMES):
            x = np.sort(d[(d.sev == i) & d.lat.notna()].lat.to_numpy())
            if len(x):
                ax.step(x, np.arange(1, len(x) + 1) / len(x), where="post", color=COLORS[i], label=f"{s} (n={len(x)})")
        ax.set_xlabel("Time from trigger to ACK (s)")
        ax.set_title(f"policy: {pn}", fontsize=9)
    axes[0].set_ylabel("Share of delivered alerts (cumulative)")
    axes[0].legend(fontsize=7)
    fig.suptitle("Replay latency: SF7, 30% independent loss each way, 20 alerts per hour, 100 simulated hours (SIMULATED)", fontsize=9)
    save(fig, "replay_latency_cdf")
    fig, ax = plt.subplots(figsize=(6.5, 4))
    for i, pn in enumerate(POLICY_NAMES):
        tl = example["timeline_" + pn]
        if tl:
            ax.step(np.array([x[0] for x in tl]) / 60, np.cumsum([x[1] for x in tl]), where="post", color=COLORS[i], label=pn)
    ax.axhline(360.0, color="gray", ls=":", lw=0.8)
    ax.set_xlabel("Time (minutes)")
    ax.set_ylabel("Cumulative node airtime (s); dotted = 10% of one hour")
    ax.legend(fontsize=7)
    ax.set_title("One simulated hour: SF12, 120 alerts per hour, 30% loss (SIMULATED)", fontsize=8)
    save(fig, "replay_airtime_budget")
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    cols = ["window_fill_s", "compute_s", "cancel_s", "alert_airtime_s", "base_processing_s", "ack_airtime_s"]
    labels = ["window fill", "compute", "cancel window", "alert on air", "base processing", "ACK on air"]
    for i, r in enumerate(timeline.itertuples()):
        left = 0.0
        for j, c in enumerate(cols):
            v = getattr(r, c)
            ax.barh(i, v, left=left, color=COLORS[j], label=labels[j] if i == 0 else None)
            left += v
    ax.set_yticks(range(len(timeline)), timeline.sev)
    ax.set_xlabel("Seconds after the trigger (lossless exchange at SF7; stage times are stated assumptions or analytical)")
    ax.legend(fontsize=7, ncol=3)
    save(fig, "replay_stage_timeline")


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    pool = load_pool()
    pl = pools()
    ent: list[dict] = []

    def add(name, value, unit, origin="SIMULATED", notes="", s=SRC):
        ent.append(dict(name=f"replay.{name}", value=value, unit=unit, origin=origin, source_file=s, notes=notes))

    al = pool[pool.alert]
    pp = "data/processed/replay_pool.parquet"
    add("pool.events", int(len(pool)), "events", "MEASURED_SOFTWARE", "triggered, de-duplicated VZCrash test events", pp)
    add("pool.alerts", int(len(al)), "alerts", "MEASURED_SOFTWARE", "events the deployed model called a crash (true crashes and false alarms)", pp)
    add("pool.alerts_false", int((al.y == 0).sum()), "alerts", "MEASURED_SOFTWARE", "alerts for non-crash events", pp)
    for k in range(4):
        add(f"pool.sev_share.{SEV_NAMES[k]}", round(float((al.sev == k).mean()), 4), "fraction", "MEASURED_SOFTWARE", "severity class of the alerts the model raised, with the rollover rule as configured", pp)
        if "nhtsa16" in pl:
            add(f"pool.nhtsa16.sev_share.{SEV_NAMES[k]}", round(float((pl["nhtsa16"] == k).mean()), 4), "fraction", "MEASURED_SOFTWARE", "NHTSA tests through the 16 g, 100 Hz sensor model", "results/tables/sevstudy_tests.csv")
    add("pool.threshold", round(float(pool.threshold.iloc[0]), 5), "probability", "MEASURED_SOFTWARE", "deployed model, validation threshold", pp)
    for k, v in (("compute_s", COMPUTE_S), ("window_fill_s", C.POST_S)):
        add(f"assume.{k}", v, "seconds", "ANALYTICAL", "stated assumption; on-device compute time is NOT_RUN (needs the ESP32)", "src/crashguard/replay.py")
    for k in range(4):
        add(f"assume.cancel_s.{SEV_NAMES[k]}", CANCEL_S[k], "seconds", "ANALYTICAL", "cancel window by class, inside the 5 to 10 s range of docs/00_overview/ARCHITECTURE.md", "src/crashguard/replay.py")
    add("assume.ge_p_bg", GE_P_BG, "probability", "ANALYTICAL", "Gilbert-Elliott: chance per transmission that the bad state ends", "src/crashguard/replay.py")
    for k, v, u in (("flood_rate_per_s", FLOOD[2], "packets/s"), ("flood_duration_s", FLOOD[1], "seconds"), ("flood_start_s", FLOOD[0], "seconds"), ("flood_base_budget_s", FLOOD_BASE_S, "seconds"),
                    ("flood_alert_rate_per_h", FLOOD_ALERTS_PER_H, "alerts/h")):
        add(f"assume.{k}", v, u, "ANALYTICAL", "scenario constant of the replay flood", "src/crashguard/replay_study.py")
    add("assume.ge_loss_bad", GE_LOSS_BAD, "probability", "ANALYTICAL", "Gilbert-Elliott: loss in the bad state; loss in the good state is 0", "src/crashguard/replay.py")

    grids, hourlies = [], {}
    for name, sev in pl.items():
        g, hh = grid_rows(name, sev)
        grids.append(g)
        hourlies.update(hh)
    grid = pd.concat(grids, ignore_index=True)
    grid.to_csv(C.TABLES / "replay_grid.csv", index=False)
    sens, sens_h = [], {}
    for name, sev in pl.items():
        s_, hh = sensitivity_rows(name, sev)
        sens.append(s_)
        sens_h.update(hh)
    sens = pd.concat(sens, ignore_index=True)
    sens.to_csv(C.TABLES / "replay_sensitivity.csv", index=False)

    keep = [c for c in grid.columns if c.startswith(("delivered_", "median_lat_s_", "p95_lat_s_", "retries_", "airtime_share_", "never_sent_", "waited_budget_", "n_", "received_"))]
    for r in grid[grid.loss.isin(HEADLINE_LOSSES)].itertuples():
        base = f"{r.pool}.sf{r.sf}.{r.kind}.loss{int(r.loss * 100)}.{r.policy}"
        for c in keep:
            v = getattr(r, c, np.nan)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                add(f"grid.{base}.{c}", round(float(v), 5), "seconds" if "lat_s" in c else ("alerts per hour" if c.startswith("n_") else "fraction"))
    for r in grid.itertuples():
        base = f"{r.pool}.sf{r.sf}.{r.kind}.loss{int(r.loss * 100)}.{r.policy}"
        for c in ("delivered_all", "delivered_all_lo", "delivered_all_hi", "delivered_critical", "delivered_critical_lo", "delivered_critical_hi"):
            v = getattr(r, c, np.nan)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                add(f"grid.{base}.{c}", round(float(v), 5), "fraction")
    for r in sens.itertuples():
        base = f"sens.{r.pool}.{r.scenario}.{r.policy}"
        for c in ("delivered_all", "delivered_critical", "delivered_low", "median_lat_s_all", "median_lat_s_critical", "airtime_share_total", "base_ack_airtime_share", "never_sent_all",
                  "waited_budget_critical", "never_sent_critical"):
            v = getattr(r, c, np.nan)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                add(f"{base}.{c}", round(float(v), 5), "seconds" if "lat_s" in c else "fraction", s="results/tables/replay_sensitivity.csv")

    conc = conclusions(hourlies, sens_h)
    conc.to_csv(C.TABLES / "replay_conclusions.csv", index=False)
    cs = "results/tables/replay_conclusions.csv"
    for (cn, pool_name), g in conc.groupby(["conclusion", "pool"]):
        add(f"conclusion.{pool_name}.{cn}.cells", int(len(g)), "cells", s=cs)
        add(f"conclusion.{pool_name}.{cn}.holds", int(g.holds.sum()), "cells", s=cs)
        for f, r in g.groupby("family").holds.agg(["sum", "count"]).iterrows():
            add(f"conclusion.{pool_name}.{cn}.family.{f}.holds", int(r["sum"]), "cells", s=cs)
            add(f"conclusion.{pool_name}.{cn}.family.{f}.cells", int(r["count"]), "cells", s=cs)

    fl = pd.concat([flood_rows(name, pl[name]) for name in ("stress", "vzcrash")], ignore_index=True)
    fl.to_csv(C.TABLES / "replay_flood.csv", index=False)
    fs = "results/tables/replay_flood.csv"
    for (pool_name, limit), g in fl.groupby(["pool", "limit"]):
        tag = "limit_on" if limit else "limit_off"
        for col in ("delivered_inside", "delivered_outside", "base_ack_airtime_s", "replayed"):
            p_, lo, hi = ci_of(g, col)
            add(f"flood.{pool_name}.{tag}.{col}", round(p_, 4), "fraction" if "delivered" in col else ("seconds" if "airtime" in col else "packets"), s=fs)
            if "delivered" in col:
                add(f"flood.{pool_name}.{tag}.{col}_lo", round(lo, 4), "fraction", s=fs)
                add(f"flood.{pool_name}.{tag}.{col}_hi", round(hi, 4), "fraction", s=fs)

    example: dict = {}
    sev = pl["stress"]
    for pn in ("severity", "fixed3"):
        recs: list = []
        for h in range(100):
            recs += simulate(sev, Scenario("cdf", 7, 20, loss_up=0.3, loss_down=0.3), POLICIES[pn], random.Random(f"arr|cdf|{h}"), random.Random(f"ch|cdf|{pn}|{h}"))
        d = pd.DataFrame(recs)
        d["lat"] = d.t_ack - d.arrival
        example[pn] = d
    for pn in POLICY_NAMES:
        tl: list = []
        simulate(sev, Scenario("air", 12, 120, loss_up=0.3, loss_down=0.3), POLICIES[pn], random.Random("arr|air|0"), random.Random(f"ch|air|{pn}"), timeline=tl)
        example["timeline_" + pn] = tl
    timeline = stage_timeline()
    timeline.to_csv(C.TABLES / "replay_stage_timeline.csv", index=False)
    for r in timeline.itertuples():
        total = r.window_fill_s + r.compute_s + r.cancel_s + r.alert_airtime_s + r.base_processing_s + r.ack_airtime_s
        add(f"timeline.{r.sev}.total_s", round(float(total), 4), "seconds", "ANALYTICAL", "lossless exchange at SF7 from the stated stage times", "results/tables/replay_stage_timeline.csv")
    record_many(ent, purge_prefixes=("replay.",))
    figures(grid, example, timeline)
    print(grid[(grid.pool == "stress") & (grid.loss == 0.3)][["sf", "kind", "policy", "delivered_all", "delivered_critical", "median_lat_s_all", "airtime_share_total"]].round(3).to_string())
    print(conc.groupby(["pool", "conclusion"]).holds.agg(["sum", "count"]))


if __name__ == "__main__":
    main()
