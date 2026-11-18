"""Event-driven simulation of N cars on one channel for S11 and the UA-SCT study (docs/01_protocol/PROTOCOL_SCT.md, docs/02_preregistration/PREREGISTRATION.md). SIMULATED; every value below is an ASSUMPTION.

Built from the X6 simulator (``capacity.py``): one 125 kHz channel, equal spreading factor, per-car level N(0, 8 dB) plus fading N(0, 2 dB), capture rule of 6 dB (or pure ALOHA), independent extra loss
on the uplink and downlink, a half-duplex base with a signed 26-byte ACK (one ACK per message per retry interval). Differences from X6:
- **Duty-cycle rule (parameter ``duty``, default 1%; NOT verified for India):** the airtime of a transmitter (each car, and the base station) in any trailing 3,600 s window never exceeds duty x 3,600 s; a
  transmission that would exceed it waits (X6 used a token bucket). Compliance is re-checked after each run by an independent scan of the logged transmissions.
- The alert's class pair (assigned by the policy, true) is drawn from a pool (the NHTSA pairs of ``ua_conformal``); the true class gives the metrics, the assigned class gives the policy's behaviour.
- Ready time = crash instant + early-exit decision time (the N19 distribution of the de-duplicated test set) + compute time + hold; every policy gets the same decision times.
- Optional false alarms (non-crash alerts at a false-alarm target) with a driver who cancels with probability P_CANCEL at 1 to 4 s after the decision.
- Policies: fixed3 (P0), severity table (P1), the N16 scheduler, and ``sct`` (P2, P3 with upper-end classes, P4 with ``fast_cap``) with ablation switches.
"""
from __future__ import annotations

import heapq
import math
import random
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from crashguard import packet as P
from crashguard.capacity import CAPTURE_DB, SF_DECAY, SIGMA_CAR_DB, SIGMA_TX_DB, air
from crashguard.replay import CANCEL_S, COMPUTE_S, MARGIN_S, POLICIES, PROC_S
from crashguard.scheduler import Scheduler

FLASH_LEN = 14
BEACON_LEN = 9  # v2 Study B: 1 level byte plus an 8-byte tag
HORIZON_S = 1800.0
WINDOW_S = 3600.0
P_CANCEL = 0.9
FA_CANCEL_DELAY_S = (1.0, 4.0)
CANCEL_REPEATS, CANCEL_SPACING_S = 3, 2.0


class Window:
    """Trailing-hour airtime of one transmitter: ``limit`` seconds in any 3,600 s window."""

    def __init__(self, limit_s: float):
        self.limit = limit_s
        self.q: deque = deque()  # (start time, airtime, fast flag)
        self.log: list[tuple[float, float]] = []

    def prune(self, now: float) -> None:
        while self.q and self.q[0][0] <= now - WINDOW_S + 1e-9:
            self.q.popleft()

    def used(self, now: float, fast_only: bool = False) -> float:
        self.prune(now)
        return sum(a for _t, a, f in self.q if f or not fast_only)

    def ok(self, now: float, need: float, cap: float) -> bool:
        return self.used(now) + need <= cap + 1e-12

    def wait_until(self, now: float, need: float, cap: float) -> float:
        """Earliest time at which ``need`` fits under ``cap`` (inf if need alone exceeds cap)."""
        if need > cap + 1e-12:
            return float("inf")
        self.prune(now)
        tot = sum(a for _t, a, _f in self.q)
        if tot + need <= cap + 1e-12:
            return now
        for t, a, _f in self.q:
            tot -= a
            if tot + need <= cap + 1e-12:
                return max(now, t + WINDOW_S + 1e-6)
        return now

    def add(self, now: float, air_s: float, fast: bool = False) -> None:
        self.q.append((now, air_s, fast))
        self.log.append((now, air_s))


def max_window_airtime(log: list[tuple[float, float]]) -> float:
    """Largest airtime in any trailing 3,600 s window, computed from the log of (start, airtime) alone (the independent compliance scan)."""
    if not log:
        return 0.0
    log = sorted(log)
    best, tot, j = 0.0, 0.0, 0
    for i, (t, a) in enumerate(log):
        tot += a
        while log[j][0] <= t - WINDOW_S + 1e-9:
            tot -= log[j][1]
            j += 1
        best = max(best, tot)
    return best


@dataclass(frozen=True)
class SctParams:
    h_s: float = 2.0  # hold of Severe alerts (s)
    rho_f: float = 0.35  # share of the hourly allowance reserved for the fast path
    sf_raise: bool = True
    preempt: bool = True
    flash: bool = True
    sev_hold: bool = True  # Critical 0 s and Severe h_s; False = the full cancel window for every class
    reserve: bool = True  # False = no reserved share
    spacing_crit: float = 5.0
    spacing_sev: float = 10.0
    max_tries: tuple = (3, 3, 8, 12)
    sf_raise_after: int = 2
    backoff_s: float = 4.0
    jitter: float = 0.5
    cancel_msg: bool = True  # T9 ablation: False = no authenticated CANCEL message after a driver cancel
    fast_cap: float | None = None  # P4: fast-path airtime in the trailing hour limited to this share of the allowance
    h_c: float = 0.0  # v2 Study F: hold of Critical alerts (s); the default keeps every earlier result unchanged
    hold_all: float | None = None  # v2 Study F: one flat hold for every class (s); None = the class rule


@dataclass
class SCfg:
    n: int
    sf: int
    policy: str
    seed: int
    hour: int = 0
    duty: float = 0.01
    hb_period_s: float = 600.0
    hb_bytes: int = 16
    rate_per_car_h: float = 0.1
    fa_per_car_h: float = 0.0
    burst: bool = False
    burst_cars: int = 30
    p_up: float = 0.1
    p_down: float = 0.1
    capture: str = "db6"
    sct: SctParams = field(default_factory=SctParams)
    sched: dict = field(default_factory=lambda: dict(rho=0.0, m=0.5, jitter=0.0, sf_raise=1))
    true_pool: np.ndarray | None = None  # true classes of the crash pool
    assigned_pool: np.ndarray | None = None  # class the policy assigns to each pool entry (aligned with true_pool)
    crash_pool: np.ndarray | None = None  # decision times (s) of crash events that alarm
    fa_pool: np.ndarray | None = None  # decision times (s) of non-crash events that alarm
    duration_s: float = 3600.0
    label: str = ""
    alert_len: int | None = None  # v2 Study E: message lengths (bytes); None = the packet constants
    flash_len: int | None = None
    ack_len: int | None = None
    dyn: dict | None = None  # v2 Study B: adaptive class decision (kind fixed, controller, bucket, beacon, backoff, demote) with its parameters
    pool_cls: np.ndarray | None = None  # (K, S) class of pool entry k at threshold scale index j
    pool_scales: np.ndarray | None = None  # (S,) threshold scales


def _policy(cfg: SCfg):
    if cfg.policy == "scheduler":
        return Scheduler(name="scheduler", rho=cfg.sched["rho"], m=cfg.sched["m"], jitter=cfg.sched["jitter"], sf_raise=bool(cfg.sched["sf_raise"])).fresh()
    if cfg.policy == "sct":
        return None
    return POLICIES[cfg.policy].fresh()


def simulate(cfg: SCfg) -> dict:
    rng_arr = random.Random(f"uarr|{cfg.n}|{cfg.sf}|{cfg.hb_period_s}|{cfg.burst}|{cfg.burst_cars}|{cfg.rate_per_car_h}|{cfg.fa_per_car_h}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    rng = random.Random(f"uch|{cfg.policy}|{cfg.n}|{cfg.sf}|{cfg.hb_period_s}|{cfg.burst}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    pol = _policy(cfg)
    S = cfg.sct
    is_sct = cfg.policy == "sct"
    sf0 = cfg.sf
    limit = cfg.duty * WINDOW_S
    L_AL, L_FL, L_ACK = cfg.alert_len or P.ALERT_LEN, cfg.flash_len or FLASH_LEN, cfg.ack_len or P.ACK_LEN
    tau_hb, tau_al, tau_ack = air(cfg.hb_bytes, sf0), air(L_AL, sf0), air(L_ACK, sf0)
    interval = (tau_al + PROC_S + tau_ack + MARGIN_S) * 0.999
    node_off = [rng_arr.gauss(0.0, SIGMA_CAR_DB) for _ in range(cfg.n)]
    dyn = cfg.dyn
    dk = dyn["kind"] if dyn else None
    rng_dyn = random.Random(f"udyn|{cfg.n}|{cfg.sf}|{cfg.burst}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    s0d = dyn["s0"] if dyn else 1.0
    nodes = [dict(win=Window(limit), pending=[], free=0.0, s=s0d, F=0.0, F_t=0.0, tok=(dyn.get("b", 1.0) if dyn else 0.0), tok_t=0.0, b_level=0, b_t=None) for _ in range(cfg.n)]
    base = dict(win=Window(limit), busy_until=0.0, last_ack={}, rx=deque(), level=0)
    ack_intervals: list[tuple[float, float]] = []
    active: list[dict] = []
    heap: list = []
    seq = [0]
    alerts: list[dict] = []
    st = dict(hb_sched=0, hb_sent=0, hb_rx=0, hb_skipped=0, al_tx=0, al_collided=0, al_deaf=0, flash_tx=0, cancel_tx=0, ack_sent=0, ack_budget_drop=0, node_air_s=0.0, fast_air_s=0.0, normal_air_s=0.0, demoted=0, beacon_tx=0, beacon_air_s=0.0, beacon_skipped=0)

    def push(t, kind, data):
        seq[0] += 1
        heapq.heappush(heap, (t, seq[0], kind, data))

    def hold_of(sev: int) -> float:
        if is_sct and S.hold_all is not None:
            return S.hold_all
        if is_sct and S.sev_hold:
            return S.h_c if sev == 3 else (S.h_s if sev == 2 else CANCEL_S[sev])
        return CANCEL_S[sev]

    def bo(sev: int) -> float:
        return rng_dyn.random() * dyn["W"][sev] if dk == "backoff" else 0.0

    def dyn_scale(nd, now: float) -> float:
        if dk == "controller":
            nd["F"] *= math.exp(-(now - nd["F_t"]) / 3600.0)
            nd["F_t"] = now
            if nd["F"] > 0.5:
                nd["s"] = min(1.0, nd["s"] + dyn["g"])
            elif nd["F"] < 0.2:
                nd["s"] = max(dyn["s0"], nd["s"] - dyn["g"])
            return nd["s"]
        if dk == "beacon":
            if nd["b_t"] is not None and now - nd["b_t"] <= 300.0:
                return dyn["s0"] + (1.0 - dyn["s0"]) * nd["b_level"] / 3.0
            return dyn["s0"]
        return dyn["s0"]

    def s_idx(sc: float) -> int:
        return int(np.argmin(np.abs(cfg.pool_scales - sc)))

    def new_alert(node: int, t0: float, sev: int, true: int, t_dec: float, kind: str, cancel_after: float | None, pk: int | None = None):
        a = dict(node=node, arrival=t0, kind=kind, sev=sev, true=true, tries=0, t_rx=None, t_ack=None, t_ack_first=None, gave_up=False, airtime_s=0.0, acked=False, flash_acked=False, id=len(alerts) + 1,
                 sf_used=sf0, rounds=0, cancel_at=None, cancelled_pre=False, transmitted=False, demoted=False, extra=False, fast_used=False, pool_k=pk)
        if cancel_after is not None:
            a["cancel_at"] = t0 + t_dec + COMPUTE_S + cancel_after
        alerts.append(a)
        if dyn:  # the class is decided at the decision time from the car's current threshold scale (v2 Study B)
            a["sev"], a["ready"] = -1, None
            push(t0 + t_dec + COMPUTE_S, "decide", a)
        else:
            a["ready"] = t0 + t_dec + COMPUTE_S + hold_of(sev)
            a["stage"] = "flash" if (is_sct and S.flash and sev >= 2) else "alert"
            push(a["ready"], "ready", a)
        if a["cancel_at"] is not None:
            push(a["cancel_at"], "cancel", a)

    tp = np.asarray(cfg.true_pool) if cfg.true_pool is not None else np.array([0, 1, 2, 3])
    ap = np.asarray(cfg.assigned_pool) if cfg.assigned_pool is not None else tp
    crit_idx = np.flatnonzero(tp == 3)
    cpool = cfg.crash_pool if cfg.crash_pool is not None and len(cfg.crash_pool) else np.array([0.3])
    fpool = cfg.fa_pool if cfg.fa_pool is not None and len(cfg.fa_pool) else cpool
    lam = cfg.n * cfg.rate_per_car_h / 3600.0
    t = 0.0
    while lam > 0:
        t += rng_arr.expovariate(lam)
        if t >= cfg.duration_s:
            break
        k = rng_arr.randrange(len(tp))
        new_alert(rng_arr.randrange(cfg.n), t, int(ap[k]), int(tp[k]), float(cpool[rng_arr.randrange(len(cpool))]), "crash", None, k)
    lam_f = cfg.n * cfg.fa_per_car_h / 3600.0
    t = 0.0
    while lam_f > 0:
        t += rng_arr.expovariate(lam_f)
        if t >= cfg.duration_s:
            break
        k = rng_arr.randrange(len(tp))
        cancel = rng_arr.uniform(*FA_CANCEL_DELAY_S) if rng_arr.random() < P_CANCEL else None
        new_alert(rng_arr.randrange(cfg.n), t, int(ap[k]), -1, float(fpool[rng_arr.randrange(len(fpool))]), "fa", cancel, k)
    if cfg.burst:
        for node in rng_arr.sample(range(cfg.n), min(cfg.burst_cars, cfg.n)):
            k = int(crit_idx[rng_arr.randrange(len(crit_idx))]) if len(crit_idx) else 0
            new_alert(node, 600.0 + rng_arr.random() * 10.0, int(ap[k]), int(tp[k]), float(cpool[rng_arr.randrange(len(cpool))]), "crash", None, k)
    for i in range(cfg.n):
        push(rng_arr.random() * cfg.hb_period_s, "hb", i)

    def overlaps(tx):
        return [o for o in active if o is not tx and o["start"] < tx["end"] and o["end"] > tx["start"] and o["sf"] == tx["sf"]]

    def start_tx(i, now, kind, a, sf, a_air, fast):
        tx = dict(node=i, start=now, end=now + a_air, sf=sf, kind=kind, alert=a, power=node_off[i] + rng.gauss(0.0, SIGMA_TX_DB))
        active.append(tx)
        nodes[i]["free"] = tx["end"]
        nodes[i]["win"].add(now, a_air, fast)
        st["node_air_s"] += a_air
        st["fast_air_s" if fast else "normal_air_s"] += a_air
        push(tx["end"], "tx_end", tx)
        return tx

    def is_fast(a) -> bool:
        return is_sct and a["sev"] >= 2 and not a["demoted"]

    def fast_active(nd) -> bool:
        return any(is_fast(x) and not x["acked"] and not x["gave_up"] and not x["cancelled_pre"] for x in nd["pending"])

    def sct_sf(a) -> int:
        if S.sf_raise and is_fast(a) and a["rounds"] >= S.sf_raise_after and sf0 < 12:
            return sf0 + 1
        return sf0

    def try_node(i, now):
        nd = nodes[i]
        win: Window = nd["win"]
        if now < nd["free"] - 1e-12:
            push(nd["free"], "try", i)
            return
        waiting = [a for a in nd["pending"] if not a["acked"] and not a["gave_up"]]
        ready = [a for a in waiting if a["ready"] <= now]
        if not ready:
            if waiting:
                push(min(a["ready"] for a in waiting), "try", i)
            return
        if is_sct:
            fast = [a for a in ready if is_fast(a)]
            if S.preempt and fast_active(nd) and not fast:
                push(min(a["ready"] for a in waiting if is_fast(a)), "try", i)  # the normal path stays silent while a fast alert waits for its retry
                return
            cand = fast if fast else ready
            a = min(cand, key=lambda x: (-x["sev"], x["arrival"]))
            kind = "flash" if a["stage"] == "flash" else "alert"
            sf = sct_sf(a)
            need = air(L_FL if kind == "flash" else L_AL, sf)
            if is_fast(a):
                cap = limit
                if S.fast_cap is not None:
                    if win.used(now, fast_only=True) + need > S.fast_cap * limit + 1e-12:
                        a["demoted"] = True  # the fast-path share is used up: the alert continues on the normal path
                        st["demoted"] += 1
                        a["stage"] = "alert"
                        push(now, "try", i)
                        return
            else:
                cap = limit * (1.0 - S.rho_f) if S.reserve else limit
            if not win.ok(now, need, cap):
                w = win.wait_until(now, need, cap)
                if w == float("inf"):
                    return
                push(w, "try", i)
                return
            ack_air = air(L_ACK, sf)
            fast_flag = is_fast(a)
        else:
            a = min(ready, key=lambda x: pol.key(x, now))
            sf = pol.sf_for(a, sf0, max(limit - win.used(now), 0.0))
            need, ack_air = air(L_AL, sf), air(L_ACK, sf)
            kind = "alert"
            fast_flag = False
            cap = limit * (1.0 - pol.reserve_frac) if (pol.reserve_frac > 0 and a["sev"] < 3) else limit
            if not win.ok(now, need, cap):
                w = win.wait_until(now, need, cap)
                if w == float("inf"):
                    return
                push(w, "try", i)
                return
        a["airtime_s"] += need
        a["sf_used"] = sf
        a["transmitted"] = True
        a["fast_used"] = a["fast_used"] or fast_flag
        if kind == "alert":
            a["tries"] += 1
            st["al_tx"] += 1
        else:
            st["flash_tx"] += 1
        tx = start_tx(i, now, kind, a, sf, need, fast_flag)
        window = PROC_S + ack_air + MARGIN_S
        nd["free"] = tx["end"] + window
        push(tx["end"] + window, "listen_end", (a, kind, tx["end"], window))

    def uplink_outcome(tx) -> str:
        for s_, e_ in ack_intervals[-50:]:
            if s_ < tx["end"] and e_ > tx["start"]:
                return "deaf"
        for o in overlaps(tx):
            if cfg.capture == "none" or tx["power"] < o["power"] + CAPTURE_DB:
                return "collided"
        scale = SF_DECAY ** max(0, tx["sf"] - sf0)
        return "lost" if rng.random() < cfg.p_up * scale else "ok"

    def spacing(a) -> float:
        return S.spacing_crit if a["sev"] == 3 else S.spacing_sev

    def beacon_level(now: float) -> int:
        q = base["rx"]
        while q and q[0] < now - 60.0:
            q.popleft()
        c = len(q)
        return 0 if c < 1 else (1 if c < 5 else (2 if c < 15 else 3))

    def send_beacon(now: float) -> None:
        need = air(BEACON_LEN, sf0)
        if now < base["busy_until"] or not base["win"].ok(now, need, limit):
            st["beacon_skipped"] += 1
            return
        base["win"].add(now, need)
        base["busy_until"] = now + need
        ack_intervals.append((now, now + need))
        st["beacon_tx"] += 1
        st["beacon_air_s"] += need
        for nd_ in nodes:
            if rng_dyn.random() >= cfg.p_down:
                nd_["b_level"], nd_["b_t"] = base["level"], now + need

    if dk == "beacon":
        push(dyn.get("period_s", 120.0), "beacon_tick", None)

    while heap:
        now, _s, kind, data = heapq.heappop(heap)
        if now > cfg.duration_s + HORIZON_S:
            break
        active[:] = [o for o in active if o["end"] > now - 5.0]
        if kind == "decide":
            a = data
            nd = nodes[a["node"]]
            k = a["pool_k"]
            c = int(cfg.pool_cls[k, s_idx(dyn_scale(nd, now))])
            pc = int(cfg.pool_cls[k, s_idx(1.0)])
            extra = pc < 2 <= c
            if dk == "bucket" and extra and c != 3:
                nd["tok"] = min(dyn["b"], nd["tok"] + dyn["r"] * (now - nd["tok_t"]) / 3600.0)
                nd["tok_t"] = now
                if nd["tok"] >= 1.0:
                    nd["tok"] -= 1.0
                else:
                    c, extra = pc, False
            a["sev"], a["extra"] = c, extra
            a["stage"] = "flash" if (S.flash and c >= 2) else "alert"
            a["ready"] = now + hold_of(c) + bo(c)
            push(a["ready"], "ready", a)
        elif kind == "beacon_tick":
            if now < cfg.duration_s + HORIZON_S:
                base["level"] = beacon_level(now)
                send_beacon(now)
                push(now + dyn.get("period_s", 120.0), "beacon_tick", None)
        elif kind == "hb":
            i = data
            if now < cfg.duration_s:
                push(now + cfg.hb_period_s * (0.9 + 0.2 * rng.random()), "hb", i)
            nd = nodes[i]
            st["hb_sched"] += 1
            cap = limit * (1.0 - S.rho_f) if (is_sct and S.reserve) else limit
            blocked = now < nd["free"] or not nd["win"].ok(now, tau_hb, cap)
            if is_sct and S.preempt and fast_active(nd):
                blocked = True
            if blocked:
                st["hb_skipped"] += 1
                continue
            st["hb_sent"] += 1
            start_tx(i, now, "hb", None, sf0, tau_hb, False)
        elif kind == "ready":
            a = data
            if a["cancel_at"] is not None and a["cancel_at"] <= now:
                a["cancelled_pre"] = True  # the driver cancelled inside the hold: nothing is transmitted
                continue
            nodes[a["node"]]["pending"].append(a)
            try_node(a["node"], now)
        elif kind == "cancel":
            a = data
            if a["cancelled_pre"]:
                continue
            nd = nodes[a["node"]]
            if a in nd["pending"]:
                nd["pending"].remove(a)
                if is_sct and S.cancel_msg and a["transmitted"] and a["sev"] >= 2:
                    for k in range(CANCEL_REPEATS):
                        push(now + k * CANCEL_SPACING_S, "cancel_tx", a)
            elif a["ready"] > now:
                a["cancelled_pre"] = True
        elif kind == "cancel_tx":
            a = data
            i = a["node"]
            nd = nodes[i]
            if now < nd["free"] - 1e-12:
                push(nd["free"], "cancel_tx", a)
                continue
            need = air(L_FL, sf0)
            if not nd["win"].ok(now, need, limit):
                continue
            st["cancel_tx"] += 1
            a["airtime_s"] += need
            start_tx(i, now, "cancel", a, sf0, need, True)
        elif kind == "try":
            try_node(data, now)
        elif kind == "tx_end":
            tx = data
            res = uplink_outcome(tx)
            if tx["kind"] == "hb":
                st["hb_rx"] += int(res == "ok")
                continue
            a = tx["alert"]
            if tx["kind"] == "cancel":
                continue
            if res == "collided":
                st["al_collided"] += 1
            if res == "deaf":
                st["al_deaf"] += 1
            if res != "ok":
                continue
            if a["t_rx"] is None:
                a["t_rx"] = now
            if dk == "beacon":
                base["rx"].append(now)
                lv = beacon_level(now)
                if lv != base["level"]:
                    base["level"] = lv
                    send_beacon(now)
            stage = "f" if tx["kind"] == "flash" else "a"
            key = (a["node"], a["id"], stage)
            t_a = now + PROC_S
            ack_air = air(L_ACK, tx["sf"])
            if key in base["last_ack"] and t_a - base["last_ack"][key] < interval:
                continue
            if t_a < base["busy_until"]:
                continue
            if not base["win"].ok(t_a, ack_air, limit):
                st["ack_budget_drop"] += 1
                continue
            base["win"].add(t_a, ack_air)
            base["busy_until"] = t_a + ack_air
            base["last_ack"][key] = t_a
            ack_intervals.append((t_a, t_a + ack_air))
            st["ack_sent"] += 1
            if rng.random() >= cfg.p_down * SF_DECAY ** max(0, tx["sf"] - sf0):
                push(t_a + ack_air, "ack_rx", (a, stage))
        elif kind == "ack_rx":
            a, stage = data
            if a["t_ack_first"] is None:
                a["t_ack_first"] = now
            if stage == "f":
                a["flash_acked"] = True
            elif not a["acked"]:
                a["acked"], a["t_ack"] = True, now
        elif kind == "listen_end":
            a, kd, t_end, window = data
            nd = nodes[a["node"]]
            if a not in nd["pending"]:
                try_node(a["node"], now)
                continue
            if dk == "controller":
                succ = a["acked"] or (kd == "flash" and a["flash_acked"])
                nd["F"] = 0.7 * nd["F"] + 0.3 * (0.0 if succ else 1.0)
            if is_sct and not a["demoted"] and a["sev"] >= 2:
                if kd == "flash":
                    a["stage"] = "alert"
                    a["ready"] = now
                elif a["acked"]:
                    nd["pending"].remove(a)
                else:
                    a["rounds"] += 1
                    if a["tries"] >= S.max_tries[a["sev"]]:
                        a["gave_up"] = True
                        nd["pending"].remove(a)
                    elif dk == "demote" and a["extra"] and a["sev"] == 2 and a["rounds"] >= dyn["k"]:
                        a["demoted"] = True  # an escalated non-severe event that keeps failing goes back to the normal path; Critical is never demoted
                        a["stage"] = "alert"
                        st["demoted"] += 1
                        a["ready"] = t_end + window + S.backoff_s * 2.0 ** max(a["tries"] - 1, 0) * (1.0 + S.jitter * rng.random())
                    else:
                        a["ready"] = t_end + window + spacing(a) + bo(a["sev"])
                        a["stage"] = "flash" if (S.flash and not a["flash_acked"]) else "alert"
            elif is_sct:
                if a["acked"]:
                    nd["pending"].remove(a)
                elif a["tries"] >= S.max_tries[min(a["sev"], 1) if not a["demoted"] else 1]:
                    a["gave_up"] = True
                    nd["pending"].remove(a)
                else:
                    a["ready"] = t_end + window + S.backoff_s * 2.0 ** (a["tries"] - 1) * (1.0 + S.jitter * rng.random())
            else:
                pol.observe(a["acked"])
                if a["acked"]:
                    nd["pending"].remove(a)
                else:
                    a["ready"] = pol.retry_ready(a, t_end, window, rng)
                    if a["tries"] >= pol.max_tries(a):
                        a["gave_up"] = True
                        nd["pending"].remove(a)
            try_node(a["node"], now)
    viol = max([max_window_airtime(nd["win"].log) for nd in nodes] + [max_window_airtime(base["win"].log)])
    st["max_window_airtime_s"] = viol
    st["duty_exceeded"] = int(viol > limit + 1e-9)
    return summarise(alerts, st, cfg, limit)


def summarise(alerts: list[dict], st: dict, cfg: SCfg, limit: float) -> dict:
    df = pd.DataFrame(alerts)
    out: dict = dict(policy=cfg.policy, n=cfg.n, sf=cfg.sf, seed=cfg.seed, hour=cfg.hour, label=cfg.label, **st)
    out["hb_dropped_share"] = 1.0 - st["hb_rx"] / max(st["hb_sched"], 1)
    out["alert_collided_share"] = st["al_collided"] / max(st["al_tx"] + st["flash_tx"], 1)
    out["fast_air_share_of_allowance"] = st["fast_air_s"] / (limit * max(cfg.n, 1))
    out["node_air_share"] = st["node_air_s"] / (limit * max(cfg.n, 1))
    if df.empty:
        return out
    crash = df[df.kind == "crash"].copy()
    crash["first"] = crash.t_ack_first - crash.arrival
    crash["full"] = crash.t_ack - crash.arrival
    sev_true = crash[crash.true >= 2]
    out["n_severe_or_critical"] = len(sev_true)
    out["mis_triage"] = float((sev_true.sev < 2).mean()) if len(sev_true) else np.nan
    nons = crash[crash.true < 2]
    out["n_nonsevere"] = len(nons)
    out["escalation"] = float((nons.sev >= 2).mean()) if len(nons) else np.nan
    out["escalation_used"] = float(nons.fast_used.mean()) if len(nons) else np.nan
    for name, g in {"critical": crash[crash.true == 3], "severe": crash[crash.true == 2], "fast": crash[crash.true >= 2], "normal": crash[crash.true < 2]}.items():
        out[f"n_{name}"] = len(g)
        if not len(g):
            continue
        out[f"delivered_{name}"] = float(g["first"].notna().mean())
        out[f"delivered_full_{name}"] = float(g["full"].notna().mean())
        for x in (5, 10, 30):
            out[f"reach{x}_{name}"] = float((g["first"] <= x).mean())
            out[f"reach{x}_full_{name}"] = float((g["full"] <= x).mean())
        if g["first"].notna().any():
            out[f"median_lat_s_{name}"] = float(g["first"].median())
            out[f"p95_lat_s_{name}"] = float(g["first"].quantile(0.95))
    fa = df[df.kind == "fa"]
    out["n_fa_alerts"] = len(fa)
    out["fa_tx_fast"] = int(((fa.sev >= 2) & fa.transmitted).sum())
    out["fa_cancelled_pre_fast"] = int(((fa.sev >= 2) & fa.cancelled_pre).sum())
    out["fa_rx_share"] = float(fa.t_rx.notna().mean()) if len(fa) else np.nan
    fs_ = fa[fa.sev == 2]
    out["n_fa_sev"] = len(fs_)
    out["fa_rx_share_sev"] = float(fs_.t_rx.notna().mean()) if len(fs_) else np.nan
    out["node_air_per_event_s"] = st["node_air_s"] / max(len(df), 1)
    out["n_alerts"] = len(df)
    return out
