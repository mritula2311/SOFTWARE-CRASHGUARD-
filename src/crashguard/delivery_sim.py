"""Event-driven delivery simulation under a duty-cycle token bucket (S9). Origin: SIMULATED.

One node sends 97 B alerts and waits for a 26 B ACK. Each uplink and each ACK is lost independently with
probability ``loss``. Airtime is paid from a token bucket that refills at the duty-cycle rate.

ASSUMPTIONS (design choices of this simulation, not firmware values; match them to firmware v2):
- Severity mix of alerts: low 40%, moderate 30%, severe 20%, critical 10%.
- Fixed policy: 1 try + 3 retries for every alert, first come first served.
- Severity policy: maximum tries low 2, moderate 4, severe 8, critical 12; the radio serves the most severe waiting alert first.
- After each try the node listens for rx_window = 100 ms processing + ACK airtime + 100 ms; a retry follows at once.
- The base station's own duty cycle for ACKs is not modelled. No collisions, a single node.
- The cancel countdown (5 to 10 s by severity) is not included in either policy.
- Verifier mode. "strict_same_counter" is the behaviour before the fix: a retry repeats the packet and the base rejects
  every repeat as a replay, so once the base has the alert but the ACK was lost, no ACK is ever sent. "reack" is the
  idempotent re-ACK (docs/01_protocol/PACKET_FORMAT.md): a repeat of a recent alert gets the same ACK again. ACK loss applies in both.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard.lora import DUTY, airtime_ms
from crashguard.packet import ACK_LEN, ALERT_LEN
from crashguard.results import record_many

SEV_NAMES = ("low", "moderate", "severe", "critical")
SEV_PROBS = (0.4, 0.3, 0.2, 0.1)
MAX_TRIES = {"fixed3": (4, 4, 4, 4), "severity": (2, 4, 8, 12)}
MODES = ("strict_same_counter", "reack")
LOSSES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6)
PROC_S = 0.1
MARGIN_S = 0.1


def retry_interval_s(sf: int) -> float:
    """Shortest spacing between two tries of the same alert: its airtime plus the ACK listening window."""
    return airtime_ms(ALERT_LEN, sf) / 1000.0 + PROC_S + airtime_ms(ACK_LEN, sf) / 1000.0 + MARGIN_S


@dataclass(frozen=True)
class Scenario:
    name: str
    sf: int
    alerts_per_hour: float
    bucket_capacity_s: float
    bucket_initial_s: float
    note: str


SCENARIOS = (
    Scenario("A_sf7_normal", 7, 20, 360.0, 360.0, "SF7, 20 alerts/h, full hourly budget (360 s)"),
    Scenario("B_sf12_normal", 12, 20, 360.0, 360.0, "SF12, 20 alerts/h, full hourly budget"),
    Scenario("C_sf12_scarce", 12, 60, 360.0, 36.0, "SF12, 60 alerts/h burst, only 36 s of budget at the start (rest used by other traffic)"),
)


def simulate(sc: Scenario, policy: str, loss: float, rng: random.Random, duration_s: float = 3600.0, mode: str = "reack") -> list[dict]:
    """One simulated hour. Returns one record per alert."""
    air = airtime_ms(ALERT_LEN, sc.sf) / 1000.0
    air_ack = airtime_ms(ACK_LEN, sc.sf) / 1000.0
    window = PROC_S + air_ack + MARGIN_S
    t, alerts = 0.0, []
    rate = sc.alerts_per_hour / 3600.0
    while True:
        t += rng.expovariate(rate)
        if t >= duration_s:
            break
        sev = rng.choices(range(4), weights=SEV_PROBS)[0]
        alerts.append(dict(arrival=t, sev=sev, tries=0, ready=t, t_rx=None, t_ack=None, gave_up=False))
    maxt = MAX_TRIES[policy]
    tokens, t_tok, now, idx = sc.bucket_initial_s, 0.0, 0.0, 0
    pending: list[dict] = []
    while idx < len(alerts) or pending:
        while idx < len(alerts) and alerts[idx]["arrival"] <= now:
            pending.append(alerts[idx])
            idx += 1
        ready = [a for a in pending if a["ready"] <= now]
        if not ready:
            nxt = [a["ready"] for a in pending] + ([alerts[idx]["arrival"]] if idx < len(alerts) else [])
            now = max(now, min(nxt))
            continue
        a = min(ready, key=(lambda x: x["arrival"]) if policy == "fixed3" else (lambda x: (-x["sev"], x["arrival"])))
        tokens = min(sc.bucket_capacity_s, tokens + DUTY * (now - t_tok))
        t_tok = now
        if tokens < air:
            wait = (air - tokens) / DUTY
            now += wait
            tokens, t_tok = air, now  # exact: avoids a rounding loop where the clock stops advancing
            continue
        tokens -= air
        a["tries"] += 1
        t_end = now + air
        up = rng.random() >= loss
        first_rx = up and a["t_rx"] is None
        if first_rx:
            a["t_rx"] = t_end
        replies = up and (mode == "reack" or first_rx)  # strict: the base rejects repeats, so it sends no ACK for them
        if replies and rng.random() >= loss:
            a["t_ack"] = t_end + PROC_S + air_ack
            pending.remove(a)
        else:
            a["ready"] = t_end + window
            if a["tries"] >= maxt[a["sev"]]:
                a["gave_up"] = True
                pending.remove(a)
        now = t_end + window
    for a in alerts:
        a["airtime_s"] = a["tries"] * air
    return alerts


def summarise(alerts: list[dict]) -> dict:
    df = pd.DataFrame(alerts)
    out: dict[str, float] = {"alerts": float(len(df))}
    if df.empty:
        return out
    groups = {"all": df, **{s: df[df.sev == i] for i, s in enumerate(SEV_NAMES)}}
    for name, g in groups.items():
        if len(g) == 0:
            continue
        out[f"received_{name}"] = float(g.t_rx.notna().mean())
        out[f"acked_{name}"] = float(g.t_ack.notna().mean())
        if g.t_ack.notna().any():
            out[f"median_ack_s_{name}"] = float((g.t_ack - g.arrival).median())
            out[f"p95_ack_s_{name}"] = float((g.t_ack - g.arrival).quantile(0.95))
    out["tries_mean"] = float(df.tries.mean())
    out["airtime_s_total"] = float(df.airtime_s.sum())
    return out


def run(trials: int = 100) -> pd.DataFrame:
    rows = []
    for sc in SCENARIOS:
        for policy in MAX_TRIES:
            for mode in MODES:
                for loss in LOSSES:
                    for seed in (C.SEED,) + C.SEEDS:
                        rng = random.Random(f"{sc.name}-{policy}-{mode}-{loss}-{seed}")
                        per = [summarise(simulate(sc, policy, loss, rng, mode=mode)) for _ in range(trials)]
                        m = pd.DataFrame(per).mean(numeric_only=True)
                        rows.append(dict(scenario=sc.name, policy=policy, mode=mode, loss=loss, seed=seed, **m.to_dict()))
    return pd.DataFrame(rows)


def main(trials: int = 100) -> None:
    df = run(trials)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.TABLES / "s9_delivery_runs.csv", index=False)
    rep = df[df.seed.isin(C.SEEDS)]
    metrics = [c for c in df.columns if c not in ("scenario", "policy", "mode", "loss", "seed")]
    agg = rep.groupby(["scenario", "policy", "mode", "loss"])[metrics].agg(["mean", "std"])
    agg.columns = [f"{a}.{b}" for a, b in agg.columns]
    agg = agg.reset_index()
    agg.to_csv(C.TABLES / "s9_delivery_summary.csv", index=False)
    src = "results/tables/s9_delivery_summary.csv"
    ent = []
    for sc in SCENARIOS:
        ent.append(dict(name=f"s9.{sc.name}.description", value=sc.note, unit="text", origin="SIMULATED", source_file=src,
                        notes="simulation assumptions are listed in src/crashguard/delivery_sim.py"))
    for _, r in agg.iterrows():
        for col in agg.columns[4:]:
            if np.isnan(r[col]):
                continue
            ent.append(dict(name=f"s9.{r['scenario']}.{r['policy']}.{r['mode']}.loss{int(round(r['loss'] * 100))}.{col}", value=round(float(r[col]), 5),
                            unit="seconds" if "_s_" in col or col.startswith("airtime") else ("count" if col.startswith(("tries", "alerts")) else "fraction"),
                            origin="SIMULATED", source_file=src, notes=f"mean of {trials} simulated hours per seed; mean and std over seeds {C.SEEDS}"))
    ent.append(dict(name="s9.trials_per_seed", value=trials, unit="simulated hours", origin="SIMULATED", source_file=src))
    record_many(ent)
    make_figures(agg)
    show = agg[agg.loss.isin([0.0, 0.3, 0.6])][["scenario", "policy", "mode", "loss", "received_all.mean", "acked_all.mean", "received_critical.mean", "median_ack_s_critical.mean", "airtime_s_total.mean"]]
    print(show.round(3).to_string(index=False))


def make_figures(agg_all: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt
    agg = agg_all[agg_all["mode"] == "reack"]

    from crashguard.plots import COLORS, save, style

    style()
    names = {"fixed3": "fixed, 3 retries", "severity": "severity-aware"}
    fig, axes = plt.subplots(2, 3, figsize=(11, 6), sharey="row")
    for j, sc in enumerate(SCENARIOS):
        for row, (cls, lab) in enumerate([("all", "all alerts"), ("critical", "critical alerts")]):
            ax = axes[row, j]
            for i, pol in enumerate(MAX_TRIES):
                g = agg[(agg.scenario == sc.name) & (agg.policy == pol)].sort_values("loss")
                ax.errorbar(g.loss * 100, g[f"received_{cls}.mean"] * 100, yerr=g[f"received_{cls}.std"] * 100, marker="o", ms=4, capsize=2,
                            label=names[pol], color=COLORS[i])
            ax.set_xlabel("Packet loss per transmission (%)")
            if j == 0:
                ax.set_ylabel(f"Reached the base, {lab} (%)")
            if row == 0:
                ax.set_title(sc.note, fontsize=7)
    axes[0, 0].legend(fontsize=8)
    save(fig, "s9_delivery_vs_loss")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=False)
    for j, sc in enumerate(SCENARIOS):
        ax = axes[j]
        for i, pol in enumerate(MAX_TRIES):
            g = agg[(agg.scenario == sc.name) & (agg.policy == pol) & (agg.loss == 0.3)].iloc[0]
            vals = [g.get(f"median_ack_s_{s}.mean", float("nan")) for s in SEV_NAMES]
            ax.bar([k + (i - 0.5) * 0.38 for k in range(4)], vals, 0.38, label=names[pol], color=COLORS[i])
        ax.set_xticks(range(4), SEV_NAMES)
        ax.set_xlabel("Severity (loss 30%)")
        if j == 0:
            ax.set_ylabel("Median time from alert to ACK (s)")
        ax.set_title(sc.name, fontsize=8)
    axes[0].legend(fontsize=8)
    save(fig, "s9_ack_time_by_severity")
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for j, sc in enumerate(SCENARIOS):
        ax = axes[j]
        k = 0
        for pol in MAX_TRIES:
            for mode, ls in (("strict_same_counter", "--"), ("reack", "-")):
                g = agg_all[(agg_all.scenario == sc.name) & (agg_all.policy == pol) & (agg_all["mode"] == mode)].sort_values("loss")
                ax.plot(g.loss * 100, g["acked_all.mean"] * 100, ls=ls, marker="o", ms=3, color=COLORS[k // 2],
                        label=f"{names[pol]}, {'re-ACK' if mode == 'reack' else 'strict (before fix)'}")
            k += 2
        ax.set_xlabel("Packet loss per transmission (%)")
        ax.set_title(sc.name, fontsize=8)
        if j == 0:
            ax.set_ylabel("Alerts whose ACK reached the car (%)")
    axes[0].legend(fontsize=6)
    save(fig, "s9_ack_strict_vs_reack")


if __name__ == "__main__":
    main()
