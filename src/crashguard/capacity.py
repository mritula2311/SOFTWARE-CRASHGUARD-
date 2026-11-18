"""X6 (N22): many-car LoRa capacity (docs/02_preregistration/EXPERIMENTS_EXTRA.md, written before this was run).

ANALYTICAL: pure-ALOHA success probability with and without the capture effect, and the base station's own limit (ACKs per hour in its 10% duty cycle).
SIMULATED: an event-driven simulation of N cars on one channel and one spreading factor with Poisson crash alerts, periodic unconfirmed heartbeats, an optional burst, a half-duplex base
that sends signed ACKs from its own duty-cycle token bucket, and the three delivery policies (fixed 3-retry, severity table, the N16 scheduler with its tuned parameters, not re-tuned).

ASSUMPTIONS (every one is ours; none is measured): one 125 kHz channel, all cars at the same spreading factor (the scheduler's optional spreading-factor raise moves a car to the next
factor, which is treated as orthogonal to the others and with the N16 loss factor 0.7 per step); heartbeat payload 16 bytes, unconfirmed; alert 97 bytes confirmed with a 26-byte ACK;
per-car mean received level N(0, 8 dB) and per-transmission fading N(0, 2 dB); a packet survives an overlap if its level exceeds every overlapping packet by 6 dB (capture);
independent extra loss 10% uplink and 10% downlink; the base cannot receive while it sends an ACK and sends at most one ACK per event per retry interval; severity mix 40/30/20/10 percent
(low, moderate, severe, critical) as a stress mix; alert rate per car is a stated stress parameter, not a real crash rate.
"""
from __future__ import annotations

import heapq
import math
import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import packet as P
from crashguard.lora import DUTY, airtime_ms
from crashguard.replay import CANCEL_S, COMPUTE_S, MARGIN_S, POLICIES, PROC_S
from crashguard.scheduler import Scheduler

HB_BYTES = 16
CAP_S = 360.0
MIX = (0.4, 0.3, 0.2, 0.1)
CAPTURE_DB, SIGMA_CAR_DB, SIGMA_TX_DB = 6.0, 8.0, 2.0
P_UP, P_DOWN = 0.10, 0.10
SF_DECAY = 0.7
N_GRID = (1, 5, 10, 20, 50, 100, 200, 350, 500)
SFS = (7, 9, 12)
HB_PERIODS_S = (600.0, 60.0)
ALERT_RATE_PER_CAR_H = 0.1  # stress parameter
BURST = dict(at_s=600.0, window_s=10.0, cars=30)
HOURS_PER_CONFIG = 10


def air(bytes_: int, sf: int) -> float:
    return airtime_ms(bytes_, sf) / 1000.0


def qfun(x: float) -> float:
    return 0.5 * math.erfc(x / math.sqrt(2.0))


# ---------------------------------------------------------------- ANALYTICAL
def aloha_success(n_cars: int, sf: int, hb_period_s: float, alert_rate_per_car_h: float, packet: str = "alert", capture: bool = False) -> float:
    """Probability that one uplink packet is not destroyed by another packet (pure ALOHA, equal spreading factor). Overlaps are Poisson with mean
    mu = sum over other packet types of rate x (own airtime + other airtime). With capture, each overlapping packet is survived with probability q = Q(capture_db / (sqrt(2) sigma_tx_total)),
    where the level difference of two packets has variance 2 (sigma_car^2 + sigma_tx^2); success = exp(-mu (1 - q))."""
    tau_h, tau_a = air(HB_BYTES, sf), air(P.ALERT_LEN, sf)
    tau = tau_a if packet == "alert" else tau_h
    lam_h = max(n_cars - 1, 0) / hb_period_s if packet == "alert" else max(n_cars - 1, 0) / hb_period_s
    lam_a = max(n_cars - 1, 0) * alert_rate_per_car_h / 3600.0
    mu = lam_h * (tau + tau_h) + lam_a * (tau + tau_a)
    q = qfun(CAPTURE_DB / math.sqrt(2.0 * (SIGMA_CAR_DB ** 2 + SIGMA_TX_DB ** 2))) if capture else 0.0
    return math.exp(-mu * (1.0 - q))


def base_ack_limit_per_hour(sf: int) -> float:
    """ACKs per hour that fit in the base station's duty cycle (steady state), and the extra ACKs from its full initial bucket."""
    return DUTY * 3600.0 / air(P.ACK_LEN, sf)


def n_cars_at_ack_limit(sf: int, alert_rate_per_car_h: float, acks_per_alert: float = 1.0) -> float:
    return base_ack_limit_per_hour(sf) / (alert_rate_per_car_h * acks_per_alert)


# ---------------------------------------------------------------- SIMULATION
@dataclass
class Cfg:
    n: int
    sf: int
    hb_period_s: float
    policy: str
    rate_per_car_h: float = ALERT_RATE_PER_CAR_H
    burst: bool = False
    seed: int = 0
    hour: int = 0
    mix: tuple = MIX
    # overrides used by the S5 sensitivity sweep; the defaults reproduce the X6 runs exactly
    p_up: float = P_UP
    p_down: float = P_DOWN
    burst_cars: int = BURST["cars"]
    capture: str = "db6"  # "db6": a packet survives an overlap if its level exceeds every overlapping packet by CAPTURE_DB; "none": any overlap destroys it (pure ALOHA)
    hb_bytes: int = HB_BYTES


def make_policy(name: str, sched_params: dict):
    if name == "scheduler":
        return Scheduler(name="scheduler", rho=sched_params["rho"], m=sched_params["m"], jitter=sched_params["jitter"], sf_raise=bool(sched_params["sf_raise"]))
    return POLICIES[name]


def simulate(cfg: Cfg, sched_params: dict, duration_s: float = 3600.0) -> dict:
    rng_arr = random.Random(f"arr|{cfg.n}|{cfg.sf}|{cfg.hb_period_s}|{cfg.burst}|{cfg.seed}|{cfg.hour}")  # arrivals and heartbeat phases: the same for every policy
    rng = random.Random(f"ch|{cfg.policy}|{cfg.n}|{cfg.sf}|{cfg.hb_period_s}|{cfg.burst}|{cfg.seed}|{cfg.hour}")
    pol = make_policy(cfg.policy, sched_params).fresh()
    sf0 = cfg.sf
    tau_hb, tau_al, tau_ack = air(cfg.hb_bytes, sf0), air(P.ALERT_LEN, sf0), air(P.ACK_LEN, sf0)
    interval = (tau_al + PROC_S + tau_ack + MARGIN_S) * 0.999
    node_off = [rng_arr.gauss(0.0, SIGMA_CAR_DB) for _ in range(cfg.n)]
    nodes = [dict(tokens=CAP_S, t_tok=0.0, pending=[], free=0.0, tx_pending=False) for _ in range(cfg.n)]
    base = dict(tokens=CAP_S, t_tok=0.0, busy_until=0.0, last_ack={})
    ack_intervals: list[tuple[float, float]] = []
    active: list[dict] = []  # recent uplink transmissions
    heap: list = []
    seq = [0]

    def push(t, kind, data):
        seq[0] += 1
        heapq.heappush(heap, (t, seq[0], kind, data))

    alerts: list[dict] = []
    stats = dict(hb_sent=0, hb_rx=0, al_tx=0, al_collided=0, al_deaf=0, ack_sent=0, ack_budget_drop=0, ack_busy_drop=0, ack_rate_drop=0, hb_skipped=0)

    def new_alert(node: int, t: float, sev: int):
        a = dict(node=node, arrival=t, ready=t + C.POST_S + COMPUTE_S + CANCEL_S[sev], sev=sev, true=sev, tries=0, t_rx=None, t_ack=None, gave_up=False, airtime_s=0.0, acked=False, id=len(alerts) + 1, sf_used=sf0)
        alerts.append(a)
        push(a["ready"], "ready", a)

    # arrivals
    lam = cfg.n * cfg.rate_per_car_h / 3600.0
    t = 0.0
    while lam > 0:
        t += rng_arr.expovariate(lam)
        if t >= duration_s:
            break
        new_alert(rng_arr.randrange(cfg.n), t, rng_arr.choices(range(4), weights=cfg.mix)[0])
    if cfg.burst:
        for node in rng_arr.sample(range(cfg.n), min(cfg.burst_cars, cfg.n)):
            new_alert(node, BURST["at_s"] + rng_arr.random() * BURST["window_s"], 3)
    for i in range(cfg.n):
        push(rng_arr.random() * cfg.hb_period_s, "hb", i)

    def refill(nd, now):
        nd["tokens"] = min(CAP_S, nd["tokens"] + DUTY * (now - nd["t_tok"]))
        nd["t_tok"] = now

    def overlaps(tx):
        return [o for o in active if o is not tx and o["start"] < tx["end"] and o["end"] > tx["start"] and o["sf"] == tx["sf"]]

    def start_tx(i, now, kind, a, sf, a_air):
        tx = dict(node=i, start=now, end=now + a_air, sf=sf, kind=kind, alert=a, power=node_off[i] + rng.gauss(0.0, SIGMA_TX_DB))
        active.append(tx)
        nodes[i]["free"] = tx["end"]
        push(tx["end"], "tx_end", tx)
        return tx

    def try_node(i, now):
        nd = nodes[i]
        if now < nd["free"] - 1e-12:
            push(nd["free"], "try", i)
            return
        ready = [a for a in nd["pending"] if a["ready"] <= now]
        if not ready:
            nxt = [a["ready"] for a in nd["pending"]]
            if nxt:
                push(min(nxt), "try", i)
            return
        a = min(ready, key=lambda x: pol.key(x, now))
        refill(nd, now)
        sf = pol.sf_for(a, sf0, nd["tokens"])
        a_air, ack_air = air(P.ALERT_LEN, sf), air(P.ACK_LEN, sf)
        if not pol.may_spend(a, nd["tokens"], a_air, CAP_S):
            need = a_air - nd["tokens"] if pol.reserve_frac <= 0 or a["sev"] == 3 else (a_air + pol.reserve_frac * CAP_S - nd["tokens"])
            push(now + max(need, 1e-6) / DUTY, "try", i)
            return
        nd["tokens"] -= a_air
        a["tries"] += 1
        a["airtime_s"] += a_air
        a["sf_used"] = sf
        stats["al_tx"] += 1
        tx = start_tx(i, now, "alert", a, sf, a_air)
        window = PROC_S + ack_air + MARGIN_S
        nd["free"] = tx["end"] + window
        push(tx["end"] + window, "listen_end", (a, tx["end"], window))

    def uplink_outcome(tx) -> str:
        if tx["end"] - tx["start"] <= 0:
            return "ok"
        for s, e in ack_intervals[-50:]:
            if s < tx["end"] and e > tx["start"]:
                return "deaf"
        for o in overlaps(tx):
            if cfg.capture == "none" or tx["power"] < o["power"] + CAPTURE_DB:
                return "collided"
        scale = SF_DECAY ** max(0, tx["sf"] - sf0)
        return "lost" if rng.random() < cfg.p_up * scale else "ok"

    while heap:
        now, _s, kind, data = heapq.heappop(heap)
        if now > duration_s + 1800.0:
            break
        active[:] = [o for o in active if o["end"] > now - 5.0]
        if kind == "hb":
            i = data
            if now < duration_s:
                push(now + cfg.hb_period_s * (0.9 + 0.2 * rng.random()), "hb", i)
            nd = nodes[i]
            refill(nd, now)
            if now < nd["free"] or nd["tokens"] < tau_hb:
                stats["hb_skipped"] += 1
                continue
            nd["tokens"] -= tau_hb
            stats["hb_sent"] += 1
            start_tx(i, now, "hb", None, sf0, tau_hb)
        elif kind == "ready":
            nodes[data["node"]]["pending"].append(data)
            try_node(data["node"], now)
        elif kind == "try":
            try_node(data, now)
        elif kind == "tx_end":
            tx = data
            res = uplink_outcome(tx)
            if tx["kind"] == "hb":
                stats["hb_rx"] += int(res == "ok")
                continue
            a = tx["alert"]
            if res == "collided":
                stats["al_collided"] += 1
            if res == "deaf":
                stats["al_deaf"] += 1
            if res != "ok":
                continue
            if a["t_rx"] is None:
                a["t_rx"] = now
            # base ACK: at most one per event per retry interval, paid from the base bucket, half-duplex
            key = (a["node"], a["id"])
            t_a = now + PROC_S
            ack_air = air(P.ACK_LEN, tx["sf"])
            if key in base["last_ack"] and t_a - base["last_ack"][key] < interval:
                stats["ack_rate_drop"] += 1
                continue
            base["tokens"] = min(CAP_S, base["tokens"] + DUTY * (now - base["t_tok"]))
            base["t_tok"] = now
            if t_a < base["busy_until"]:
                stats["ack_busy_drop"] += 1
                continue
            if base["tokens"] < ack_air:
                stats["ack_budget_drop"] += 1
                continue
            base["tokens"] -= ack_air
            base["busy_until"] = t_a + ack_air
            base["last_ack"][key] = t_a
            ack_intervals.append((t_a, t_a + ack_air))
            stats["ack_sent"] += 1
            if rng.random() >= cfg.p_down * SF_DECAY ** max(0, tx["sf"] - sf0):
                push(t_a + ack_air, "ack_rx", a)
        elif kind == "ack_rx":
            a = data
            if not a["acked"]:
                a["acked"], a["t_ack"] = True, now
        elif kind == "listen_end":
            a, t_end, window = data
            nd = nodes[a["node"]]
            pol.observe(a["acked"])
            if a["acked"]:
                nd["pending"].remove(a)
            else:
                a["ready"] = pol.retry_ready(a, t_end, window, rng)
                if a["tries"] >= pol.max_tries(a):
                    a["gave_up"] = True
                    nd["pending"].remove(a)
            try_node(a["node"], now)
    return summarise(alerts, stats, cfg, duration_s)


def summarise(alerts: list[dict], stats: dict, cfg: Cfg, duration_s: float) -> dict:
    df = pd.DataFrame(alerts)
    out: dict = dict(rate=cfg.rate_per_car_h, n=cfg.n, sf=cfg.sf, hb_period_s=cfg.hb_period_s, policy=cfg.policy, burst=cfg.burst, seed=cfg.seed, hour=cfg.hour, alerts=len(df), **stats)
    out["hb_delivery"] = stats["hb_rx"] / max(stats["hb_sent"], 1)
    out["alert_tx_collided_share"] = stats["al_collided"] / max(stats["al_tx"], 1)
    out["ack_budget_drops"] = stats["ack_budget_drop"]
    if df.empty:
        return out
    df["lat"] = df.t_ack - df.arrival
    for name, g in {"all": df, **{c: df[df.true == i] for i, c in enumerate(("low", "moderate", "severe", "critical"))}}.items():
        if len(g):
            out[f"n_{name}"] = len(g)
            out[f"delivered_{name}"] = float(g.acked.mean())
            out[f"received_{name}"] = float(g.t_rx.notna().mean())
            out[f"reach30_{name}"] = float((g.lat <= 30.0).mean())  # ACK received within 30 s of the alert's creation (the cancel window is inside this time)
            if g.lat.notna().any():
                out[f"median_lat_s_{name}"] = float(g.lat.median())
                out[f"p95_lat_s_{name}"] = float(g.lat.quantile(0.95))
    out["node_airtime_share"] = float(df.airtime_s.sum() / (duration_s * DUTY * max(cfg.n, 1)))
    out["base_ack_airtime_share"] = stats["ack_sent"] * air(P.ACK_LEN, cfg.sf) / (duration_s * DUTY)
    return out


def _run(args) -> dict:
    cfg, sp = args
    return simulate(cfg, sp)


def main() -> None:
    import json

    from crashguard.results import record_many

    res = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    sp = dict(rho=res["n16.chosen.rho"], m=res["n16.chosen.m"], jitter=res["n16.chosen.jitter"], sf_raise=res["n16.chosen.sf_raise"])
    ent: list[dict] = []
    src = "results/tables/x6_capacity.csv"

    def add(name, value, unit, origin="SIMULATED", notes=""):
        ent.append(dict(name=f"x6.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    # ---- analytical
    arows = []
    for sf in SFS:
        add(f"analytic.sf{sf}.alert_airtime_s", round(air(P.ALERT_LEN, sf), 4), "s", "ANALYTICAL")
        add(f"analytic.sf{sf}.ack_airtime_s", round(air(P.ACK_LEN, sf), 4), "s", "ANALYTICAL")
        add(f"analytic.sf{sf}.heartbeat_airtime_s", round(air(HB_BYTES, sf), 4), "s", "ANALYTICAL")
        add(f"analytic.sf{sf}.base_acks_per_hour", round(base_ack_limit_per_hour(sf), 1), "acks per hour", "ANALYTICAL", "steady state of the 10% duty cycle; the full initial bucket adds 360 s of airtime once")
        for hb in HB_PERIODS_S:
            add(f"analytic.sf{sf}.hb{hb:g}.cars_at_ack_limit", round(n_cars_at_ack_limit(sf, ALERT_RATE_PER_CAR_H), 1), "cars", "ANALYTICAL", f"cars whose alerts at {ALERT_RATE_PER_CAR_H} per car per hour need all of the base's ACK budget (one ACK per alert)")
            for n in N_GRID:
                for cap in (False, True):
                    v = aloha_success(n, sf, hb, ALERT_RATE_PER_CAR_H, "alert", cap)
                    add(f"analytic.sf{sf}.hb{hb:g}.n{n}.alert_success.{'capture' if cap else 'aloha'}", round(v, 5), "fraction", "ANALYTICAL")
                    arows.append(dict(sf=sf, hb=hb, n=n, capture=cap, alert_success=v, hb_success=aloha_success(n, sf, hb, ALERT_RATE_PER_CAR_H, "hb", cap)))
    pd.DataFrame(arows).to_csv(C.TABLES / "x6_aloha.csv", index=False)
    # ---- simulation
    jobs = []
    for sf in SFS:
        for hb in HB_PERIODS_S:
            for n in N_GRID:
                if hb == 60.0 and sf != 7 and n > 100:
                    continue  # the 60 s heartbeat at the slow spreading factors saturates the channel already at small N
                if hb == 600.0 and n in (50, 100, 200) and sf in (7, 12):
                    for rate in (2.0, 10.0):
                        for pol in ("fixed3", "severity", "scheduler"):
                            for seed in C.SEEDS:
                                for h in range(HOURS_PER_CONFIG // len(C.SEEDS)):
                                    jobs.append((Cfg(n=n, sf=sf, hb_period_s=hb, policy=pol, rate_per_car_h=rate, seed=seed, hour=h), sp))
                for burst in (False, True):
                    if burst and (hb != 600.0 or n < 50):
                        continue
                    for pol in ("fixed3", "severity", "scheduler"):
                        for seed in C.SEEDS:
                            for h in range(HOURS_PER_CONFIG // len(C.SEEDS) or 1):
                                jobs.append((Cfg(n=n, sf=sf, hb_period_s=hb, policy=pol, burst=burst, seed=seed, hour=h), sp))
    with ProcessPoolExecutor(max_workers=12) as ex:
        rows = list(ex.map(_run, jobs, chunksize=4))
    R = pd.DataFrame(rows)
    R.to_csv(C.TABLES / "x6_capacity.csv", index=False)
    keys = ["rate", "sf", "hb_period_s", "n", "burst", "policy"]
    metric_cols = [c for c in R.columns if c.startswith(("delivered_", "median_lat_s_", "p95_lat_s_", "received_")) or c in ("hb_delivery", "alert_tx_collided_share", "base_ack_airtime_share", "node_airtime_share", "ack_budget_drops", "ack_busy_drop", "ack_rate_drop", "al_deaf")]
    for k, g in R.groupby(keys):
        rate, sf, hb, n, burst, pol = k
        tag = f"sim.sf{sf}.hb{hb:g}.n{n}.r{rate:g}.{'burst' if burst else 'steady'}.{pol}"
        add(f"{tag}.hours", int(len(g)), "hours")
        for c in metric_cols:
            v = g[c].dropna().to_numpy(float)
            if len(v):
                p = B.ci(v, np.mean)
                add(f"{tag}.{c}", round(p[0], 4), "fraction" if not c.startswith(("median", "p95")) else "s")
                add(f"{tag}.{c}_lo", round(p[1], 4), "fraction" if not c.startswith(("median", "p95")) else "s")
                add(f"{tag}.{c}_hi", round(p[2], 4), "fraction" if not c.startswith(("median", "p95")) else "s")
    # paired differences between policies for critical delivery (same arrivals: same seed and hour)
    for (rate, sf, hb, n, burst), g in R.groupby(["rate", "sf", "hb_period_s", "n", "burst"]):
        for base_pol in ("severity", "fixed3"):
            a = g[g.policy == base_pol].sort_values(["seed", "hour"])
            b = g[g.policy == "scheduler"].sort_values(["seed", "hour"])
            if "delivered_critical" in g and len(a) == len(b) and len(a) > 1 and a.delivered_critical.notna().all() and b.delivered_critical.notna().all():
                d = B.paired_diff(a.delivered_critical.to_numpy(float), b.delivered_critical.to_numpy(float), np.mean)
                tag = f"sim.sf{sf}.hb{hb:g}.n{n}.r{rate:g}.{'burst' if burst else 'steady'}.critical_delivery_diff_scheduler_minus_{base_pol}"
                add(tag, round(d[0], 4), "fraction")
                add(tag + "_lo", round(d[1], 4), "fraction")
                add(tag + "_hi", round(d[2], 4), "fraction")
    record_many(ent, purge_prefixes=("x6.",))
    pd.set_option("display.width", 220)
    show = R[(R.hb_period_s == 600.0) & (~R.burst)].groupby(["rate", "sf", "n", "policy"]).agg(crit=("delivered_critical", "mean"), allr=("delivered_all", "mean"), hb=("hb_delivery", "mean"), coll=("alert_tx_collided_share", "mean"),
                                                                                         ackshare=("base_ack_airtime_share", "mean"))
    print(show.round(3).to_string())


if __name__ == "__main__":
    main()
