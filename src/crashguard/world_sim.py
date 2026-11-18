"""COPY of ``sct_sim`` for the finishing branch (docs/02_preregistration/PREREGISTRATION_V5.md): the original is untouched. Added, all off by default (tested to reproduce ``sct_sim`` exactly): ``SctParams.p1_retry`` (P1+: severity-table
retry rule with flash and hold) and ``base-reception`` metrics; the world features of block G are added further below. SIMULATED.

V7 release (block A): optional protocol features under ``world["pa"]`` (OS-DR, OS-DR-N, GS-CA, slotted ALOHA and a slot-probability baseline); all off when ``pa`` is absent (tested to reproduce the earlier results exactly).

Original docstring: Event-driven simulation of N cars on one channel for S11 and the UA-SCT study (docs/01_protocol/PROTOCOL_SCT.md, docs/02_preregistration/PREREGISTRATION.md). SIMULATED; every value below is an ASSUMPTION.

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

import hashlib
import heapq
import math
import random
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from crashguard import packet as P
from crashguard import rd_d3 as D3
from crashguard import rd_policy as RP
from crashguard.capacity import CAPTURE_DB, SF_DECAY, SIGMA_CAR_DB, SIGMA_TX_DB, air
from crashguard.lora import airtime_ms
from crashguard.replay import CANCEL_S, COMPUTE_S, MARGIN_S, POLICIES, PROC_S
from crashguard.scheduler import Scheduler

_AIR0 = air
SENS_DBM = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}  # ASSUMED typical 125 kHz sensitivities (docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md A-G4); not from an opened document


def _mk_air(cr: int):
    if cr == 1:
        return _AIR0
    return lambda b, sf: airtime_ms(b, sf, cr=cr) / 1000.0


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
    p1_retry: bool = False  # V5 B2 (P1+): non-severe alerts retry at once after the listen window, as the severity table does (no exponential backoff)


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
    world: dict | None = None  # V5 block G: optional world features (None = the earlier model exactly)


def _policy(cfg: SCfg):
    if cfg.policy == "scheduler":
        return Scheduler(name="scheduler", rho=cfg.sched["rho"], m=cfg.sched["m"], jitter=cfg.sched["jitter"], sf_raise=bool(cfg.sched["sf_raise"])).fresh()
    if cfg.policy == "sct":
        return None
    return POLICIES[cfg.policy].fresh()


def simulate(cfg: SCfg, diag: list | None = None, invariants: bool = False) -> dict:
    rng_arr = random.Random(f"uarr|{cfg.n}|{cfg.sf}|{cfg.hb_period_s}|{cfg.burst}|{cfg.burst_cars}|{cfg.rate_per_car_h}|{cfg.fa_per_car_h}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    rng = random.Random(f"uch|{cfg.policy}|{cfg.n}|{cfg.sf}|{cfg.hb_period_s}|{cfg.burst}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    pol = _policy(cfg)
    S = cfg.sct
    # ---- V5 block G world features (all off when cfg.world is None: the earlier model exactly)
    wd = cfg.world or {}
    WG, WSL, WLBT, WREL = wd.get("geom"), wd.get("slot"), wd.get("lbt"), wd.get("relay")
    WG, WSL, WLBT, WREL = (x if x is None else (x or {"on": 1}) for x in (WG, WSL, WLBT, WREL))  # an empty dict means "on with the defaults"
    WCH = int(wd.get("channels", 1))
    procs = float(wd.get("rx_delay_s", PROC_S))
    air = _mk_air(int(wd.get("cr", 1)))
    sens = {**SENS_DBM, **(wd.get("sens") or {})}
    rng_w = random.Random(f"uw|{cfg.n}|{cfg.sf}|{cfg.burst}|{cfg.burst_cars}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    is_sct = cfg.policy == "sct"
    sf0 = cfg.sf
    limit = cfg.duty * WINDOW_S
    L_AL, L_FL, L_ACK = cfg.alert_len or P.ALERT_LEN, cfg.flash_len or FLASH_LEN, cfg.ack_len or P.ACK_LEN
    tau_hb, tau_al, tau_ack = air(cfg.hb_bytes, sf0), air(L_AL, sf0), air(L_ACK, sf0)
    interval = (tau_al + procs + tau_ack + MARGIN_S) * 0.999
    node_off = [rng_arr.gauss(0.0, SIGMA_CAR_DB) for _ in range(cfg.n)]
    Lvl = None
    Pos: list[tuple[float, float]] = []
    if WG:  # static level of every car at every gateway: transmit power - losses - path loss + log-normal shadowing (assumptions A-G4)
        rr = random.Random(f"ugeom|{cfg.n}|{cfg.label}|{cfg.seed}|{cfg.hour}")
        sep = WG.get("gw_sep_m", 3000.0)
        gws = [(0.0, 0.0)] if int(WG.get("ngw", 1)) == 1 else [(-sep / 2, 0.0), (sep / 2, 0.0)]
        Lvl = []
        for _i in range(cfg.n):
            rad, th = WG.get("R_m", 3000.0) * math.sqrt(rr.random()), rr.random() * 2 * math.pi
            x, y = rad * math.cos(th), rad * math.sin(th)
            Pos.append((x, y))
            row = []
            for gx, gy in gws:
                d = max(math.hypot(x - gx, y - gy), 10.0)
                row.append(WG.get("ptx_dbm", 14.0) - WG.get("extra_loss_db", 10.0) - (WG.get("pl0_db", 25.0) + 10.0 * WG.get("n_exp", 3.0) * math.log10(d)) + rr.gauss(0.0, WG.get("sigma_sh_db", 6.0)))
            Lvl.append(row)
    PA = wd.get("pa")  # V7 block A features (None = the earlier model exactly)
    pa_mode = PA["mode"] if PA else None
    rng_pa = random.Random(f"upa|{cfg.n}|{cfg.sf}|{cfg.burst_cars}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    off_pa = [rng_pa.uniform(-PA.get("eps", 0.005), PA.get("eps", 0.005)) for _ in range(cfg.n)] if PA else []
    RD = wd.get("rd")  # redesign round (V12): D1 table, D2 cluster ACK, Khan jitter; None = the earlier model exactly
    d1tab = RD.get("d1_table") if RD else None
    d1p = RD.get("d1_params") if RD else None
    d2 = RD.get("d2") if RD else None
    d3 = RD.get("d3") if RD else None  # D3 (V12 addendum B): slotted retries with an overheard burst-size estimate, on top of D1
    rtrace = RD.get("trace") if RD else None  # optional list that receives the inputs and outputs of the policy decisions (CV4 differential test)
    assert d3 is None or d1tab is not None, "D3 is defined on top of D1"
    assert d2 is None or d2["thr"] >= 2, "D2 threshold below 2 would act on a single vehicle"
    rng_rd = random.Random(f"urd|{cfg.n}|{cfg.sf}|{cfg.burst_cars}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    rng_d3 = random.Random(f"ud3|{cfg.n}|{cfg.sf}|{cfg.burst_cars}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    off_d3 = [rng_d3.uniform(-D3.EPS_S, D3.EPS_S) for _ in range(cfg.n)] if d3 else []
    cell_nodes: dict = {}
    link_cache: dict = {}
    dyn = cfg.dyn
    dk = dyn["kind"] if dyn else None
    rng_dyn = random.Random(f"udyn|{cfg.n}|{cfg.sf}|{cfg.burst}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    s0d = dyn["s0"] if dyn else 1.0
    nodes = [dict(sync_t=None, win=Window(limit), pending=[], free=0.0, s=s0d, F=0.0, F_t=0.0, tok=(dyn.get("b", 1.0) if dyn else 0.0), tok_t=0.0, b_level=0, b_t=None,
                  beta=(RP.BetaLoss(d1p.n0, d1p.l0, d1p.forget) if d1tab else None), heard=deque(), htx=deque(), cdefer=0) for _ in range(cfg.n)]
    base = dict(win=Window(limit), busy_until=0.0, last_ack={}, rx=deque(), level=0, cl_rx={}, cl_last={}, cl_pend={}, cl_times=deque())
    ack_intervals: list[tuple] = []  # (start, end[, channel]); channel None = every channel
    active: list[dict] = []
    heap: list = []
    seq = [0]
    alerts: list[dict] = []
    st = dict(hb_sched=0, hb_sent=0, hb_rx=0, hb_skipped=0, al_tx=0, al_collided=0, al_deaf=0, flash_tx=0, cancel_tx=0, ack_sent=0, ack_budget_drop=0, node_air_s=0.0, fast_air_s=0.0, normal_air_s=0.0, demoted=0, beacon_tx=0, beacon_air_s=0.0, beacon_skipped=0, relay_tx=0, relay_air_s=0.0, suppressed=0, suppressed_unrx=0, cluster_ack_tx=0, cluster_ack_air_s=0.0, defers=0, d3_slotted=0, d3_alt_sf=0, slot_beacon_tx=0, slot_beacon_air_s=0.0, lbt_wait=0)

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

    def new_alert(node: int, t0: float, sev: int, true: int, t_dec: float, kind: str, cancel_after: float | None, pk: int | None = None, cell=None):
        a = dict(node=node, arrival=t0, kind=kind, sev=sev, true=true, tries=0, t_rx=None, t_ack=None, t_ack_first=None, gave_up=False, airtime_s=0.0, acked=False, flash_acked=False, cell=cell, suppressed=False, id=len(alerts) + 1,
                 sf_used=sf0, rounds=0, cancel_at=None, cancelled_pre=False, transmitted=False, demoted=False, extra=False, fast_used=False, pool_k=pk,
                 n_ok=0, n_lost=0, n_collided=0, n_deaf=0, n_flash=0, cdefer=0, n_duty_wait=0, duty_wait_s=0.0, first_tx=None)
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
        bnodes = rng_arr.sample(range(cfg.n), min(cfg.burst_cars, cfg.n))
        cell_nodes["burst"] = bnodes
        for node in bnodes:
            k = int(crit_idx[rng_arr.randrange(len(crit_idx))]) if len(crit_idx) else 0
            new_alert(node, 600.0 + rng_arr.random() * 10.0, int(ap[k]), int(tp[k]), float(cpool[rng_arr.randrange(len(cpool))]), "crash", None, k, "burst")
    for i in range(cfg.n):
        push(rng_arr.random() * cfg.hb_period_s, "hb", i)

    def overlaps(tx):
        return [o for o in active if o is not tx and o["start"] < tx["end"] and o["end"] > tx["start"] and o["sf"] == tx["sf"] and o["ch"] == tx["ch"]]

    def best_gw(i):
        return max(range(len(Lvl[i])), key=lambda g: Lvl[i][g])

    def start_tx(i, now, kind, a, sf, a_air, fast, ch=None):
        if invariants:
            assert now >= 0.0 and a_air > 0.0, "negative time or airtime"
            assert nodes[i]["win"].used(now) + a_air <= limit + 1e-9, "transmission inside a duty-cycle blackout"
        fade = rng.gauss(0.0, SIGMA_TX_DB)
        gw = best_gw(i) if Lvl else 0
        tx = dict(node=i, start=now, end=now + a_air, sf=sf, kind=kind, alert=a, fade=fade, gw=gw, ch=(rng_w.randrange(WCH) if ch is None and WCH > 1 else (ch or 0)),
                  power=(Lvl[i][gw] + fade) if Lvl else node_off[i] + fade)
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

    def cluster_mode(now: float) -> bool:
        q = base["cl_times"]
        while q and q[0][0] < now - 10.0:
            q.popleft()
        return len({n_ for _t, n_ in q}) >= d2["thr"]  # distinct vehicles heard in the last 10 s

    def sct_sf(a) -> int:
        if RD and RD.get("nessa"):
            return min(12, sf0 + max(0, (a["tries"] - 1) // 2))  # the spreading factor rises by one after each pair of retransmissions
        if d1tab and a["sev"] >= 2:
            return sf0 if a["demoted"] else a.get("d1_sf", sf0)
        if S.sf_raise and is_fast(a) and a["rounds"] >= S.sf_raise_after and sf0 < 12:
            return sf0 + 1
        return sf0

    def node_link(i: int, j: int, sf: int) -> bool:
        """Can node j decode a frame of node i at spreading factor sf (A-2): path loss and shadowing as for the gateway link; no capture."""
        if i == j:
            return False
        key = (min(i, j), max(i, j), sf)
        if key not in link_cache:
            if not Pos:
                link_cache[key] = True
            else:
                rr = random.Random(f"unn|{cfg.n}|{cfg.label}|{cfg.seed}|{cfg.hour}|{key[0]}|{key[1]}")
                d = max(math.hypot(Pos[i][0] - Pos[j][0], Pos[i][1] - Pos[j][1]), 10.0)
                lv = WG.get("ptx_dbm", 14.0) - WG.get("extra_loss_db", 10.0) - (WG.get("pl0_db", 25.0) + 10.0 * WG.get("n_exp", 3.0) * math.log10(d)) + rr.gauss(0.0, WG.get("sigma_sh_db", 6.0))
                link_cache[key] = lv >= sens[sf]
        return link_cache[key]

    def pa_next_slot(i, a, now):
        """GS-CA, slotted ALOHA and the slot-probability baseline (A-4): the next slot on the GPS epoch grid; the own clock offset shifts the transmission by at most eps."""
        K, guard = int(PA["K"]), PA.get("guard", 0.02)
        slot = air(L_AL, sf0) + guard
        E_s = K * slot
        e0 = math.ceil((now - off_pa[i]) / E_s - 1e-9)
        for e_idx in (e0, e0 + 1):
            if pa_mode == "gsca":
                s_ = int(hashlib.sha256(f"{i}|{a['cell']}|{e_idx}".encode()).hexdigest(), 16) % K
            elif pa_mode == "slot_aloha":
                s_ = rng_pa.randrange(K)
            else:
                u_, acc_ = rng_pa.random(), 0.0
                s_ = K - 1
                for m_, pm_ in enumerate(PA["pvec"]):
                    acc_ += pm_
                    if u_ <= acc_:
                        s_ = m_
                        break
            t_ = e_idx * E_s + s_ * slot + off_pa[i]
            if t_ >= now - 1e-9:
                return t_
        return now

    def pa_gap(a, now, t_end, window):
        """OS-DR retry delay (A1): idle cycles drawn geometrically with per-cycle probability q = min(1, 1/N) (closed-form first order of the renewal model), q = 1 inside the last two cycles before the deadline;
        OS-DR-N divides q by (1 + gamma k), k = distinct same-cell neighbours overheard in the last 10 s."""
        Tc = interval / 0.999
        D = PA.get("D_crit", 10.0) if a["sev"] == 3 else PA.get("D_sev", 30.0)
        q = min(1.0, 1.0 / max(PA.get("N", 1.0), 1.0))
        if pa_mode == "osdr_n":
            hrd = nodes[a["node"]].get("heard", {})
            kk = sum(1 for tt in hrd.values() if now - tt <= 10.0)
            q = q / (1.0 + PA.get("gamma", 0.5) * kk)
        rem = D - (t_end + window - a["arrival"])
        if rem < 2 * Tc:
            q = 1.0
        g = 1 if q >= 1.0 else max(1, math.ceil(math.log(max(rng_pa.random(), 1e-12)) / math.log(1.0 - q)))
        return Tc * (g - 1)

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
            if d1tab and is_fast(a) and "d1_sf" not in a:
                pk_ = d1_pick(a, nd, now, 0)
                a["d1_sf"] = pk_[1] if pk_ else sf0
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
            if WSL and not is_fast(a):
                dfr = slot_defer(now, need)
                if dfr > now:
                    push(dfr, "try", i)
                    return
            if WSL and is_fast(a) and slot_synced(nd, now):
                st_t = a.get("slot_t")
                if st_t is None or abs(now - st_t) > 1e-6:
                    a["slot_t"] = slot_pick(now)
                    push(a["slot_t"], "try", i)
                    return
            if PA and pa_mode in ("gsca", "slot_aloha", "tamang") and is_fast(a) and a["sev"] == 3 and a["cell"] is not None and kind == "alert":
                st_p = a.get("pa_slot_t")
                if st_p is None or abs(now - st_p) > 1e-6:
                    a["pa_slot_t"] = pa_next_slot(i, a, now)
                    push(a["pa_slot_t"], "try", i)
                    return
            if not win.ok(now, need, cap):
                w = win.wait_until(now, need, cap)
                a["n_duty_wait"] += 1
                if w == float("inf"):
                    a["duty_wait_s"] = float("inf")
                    return
                a["duty_wait_s"] += w - now
                push(w, "try", i)
                return
            if WLBT and is_fast(a):
                busy = any(o["end"] > now and o["node"] != i and rng_w.random() < WLBT.get("p_sense", 0.7) for o in active if o["start"] <= now)
                if busy and a.get("lbt_n", 0) < WLBT.get("max_tries", 4):
                    a["lbt_n"] = a.get("lbt_n", 0) + 1
                    st["lbt_wait"] += 1
                    push(now + rng_w.uniform(*WLBT.get("backoff_s", (0.05, 0.25))), "try", i)
                    return
                a["lbt_n"] = 0
            a["slot_t"] = None
            a["pa_slot_t"] = None
            ack_air = air(L_ACK, sf)
            fast_flag = is_fast(a)
        else:
            a = min(ready, key=lambda x: pol.key(x, now))
            sf = pol.sf_for(a, sf0, max(limit - win.used(now), 0.0))
            need, ack_air = air(L_AL, sf), air(L_ACK, sf)
            kind = "alert"
            fast_flag = False
            if WSL:
                dfr = slot_defer(now, need)
                if dfr > now:
                    push(dfr, "try", i)
                    return
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
        if a["first_tx"] is None:
            a["first_tx"] = now
        a["fast_used"] = a["fast_used"] or fast_flag
        if kind == "alert":
            a["tries"] += 1
            st["al_tx"] += 1
        else:
            st["flash_tx"] += 1
            a["n_flash"] += 1
        tx = start_tx(i, now, kind, a, sf, need, fast_flag)
        window = procs + ack_air + MARGIN_S
        nd["free"] = tx["end"] + window
        push(tx["end"] + window, "listen_end", (a, kind, tx["end"], window))

    def uplink_outcome(tx) -> str:
        for iv in ack_intervals[-50:]:
            if iv[0] < tx["end"] and iv[1] > tx["start"] and (len(iv) < 3 or iv[2] is None or WCH == 1 or iv[2] == tx["ch"]):
                return "deaf"
        if Lvl and tx["power"] < sens[tx["sf"]]:
            return "lost"  # below the receiver sensitivity at the gateway
        for o in overlaps(tx):
            po = (Lvl[o["node"]][tx["gw"]] + o["fade"]) if Lvl else o["power"]
            if cfg.capture == "none" or tx["power"] < po + wd.get("capture_db", CAPTURE_DB):
                return "collided"
        scale = SF_DECAY ** max(0, tx["sf"] - sf0)
        return "lost" if rng.random() < cfg.p_up * scale else "ok"

    def spacing(a, window: float = 0.0) -> float:
        if RD and RD.get("khan"):
            return rng_rd.uniform(*RD["khan"])
        if RD and RD.get("nessa"):  # Nessa-style baseline (V12 11.1): ACK timeout from the airtime of the alert, doubling per stage, a redundant copy after the first retransmission of each stage
            nz = RD["nessa"]
            t0 = nz["k"] * air(L_AL, sf0)
            n_done = a["tries"]  # alert transmissions so far (the round that just failed included)
            if n_done % 2 == 0:  # the next transmission is the redundant copy of the stage
                return rng_rd.uniform(0.0, nz["A"])
            stg = (n_done - 1) // 2
            ub = t0 * 2.0 ** stg
            lb = t0 * 2.0 ** (stg - 1) if stg >= 1 else t0 / 2.0
            return max(0.0, rng_rd.uniform(lb, ub) - window)
        return S.spacing_crit if a["sev"] == 3 else S.spacing_sev

    def heard_count(nd, now: float) -> int:
        q = nd["heard"]
        while q and q[0] < now - 10.0:
            q.popleft()
        return len(q)

    def d1_pick(a, nd, now: float, j: int):
        """D1 lookup for the alert's next attempt; None when nothing fits before the class deadline or in the budget."""
        c = a["sev"]
        tau = RP.time_left(RP.DEADLINE_S[c], a["arrival"], now)
        bud = d1p.share[c] * max(limit - nd["win"].used(now), 0.0)
        n_h = heard_count(nd, now)
        out = d1tab.lookup(c, j, tau, nd["beta"].mean, n_h, bud)
        if rtrace is not None:
            rtrace.append(("d1", d1tab.sf0, c, j, tau, nd["beta"].mean, n_h, bud, out))
        return out

    def htx_count(nd, now: float) -> int:
        q = nd["htx"]
        while q and q[0][0] < now - D3.HEARD_WINDOW_S:
            q.popleft()
        return len({s_ for _t, s_ in q})

    if WSL:
        n_sl, frame_s = int(WSL.get("n_slots", 8)), float(WSL.get("frame_s", 30.0))
        slot_s = max(0.5, math.ceil(air(L_AL, min(12, sf0 + 1)) / 0.1) * 0.1 + 0.1)
        win_s = n_sl * slot_s
        sync_age = float(WSL.get("sync_age_s", 90.0))

    def slot_defer(now: float, need: float) -> float:
        """Normal-path and heartbeat transmissions avoid the reserved window of every frame."""
        ws = math.floor(now / frame_s) * frame_s
        if now < ws + win_s:
            return ws + win_s
        if now + need > ws + frame_s:
            return ws + frame_s + win_s
        return now

    def slot_synced(nd, now: float) -> bool:
        return nd["sync_t"] is not None and now - nd["sync_t"] <= sync_age

    def slot_pick(now: float) -> float:
        j = math.floor(now / frame_s)
        for jj in (j, j + 1):
            cand = [jj * frame_s + m * slot_s for m in range(n_sl) if jj * frame_s + m * slot_s >= now - 1e-9]
            if cand:
                return cand[rng_w.randrange(len(cand))]
        return now

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
    if WSL:
        k_ = 0
        while k_ * frame_s < cfg.duration_s + HORIZON_S:
            push(k_ * frame_s, "slot_beacon", None)
            k_ += 1

    while heap:
        now, _s, kind, data = heapq.heappop(heap)
        if now > cfg.duration_s + HORIZON_S:
            heapq.heappush(heap, (now, _s, kind, data))  # keep the popped event so that in-flight transmissions are counted by the invariant check
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
        elif kind == "slot_beacon":
            need = air(WSL.get("beacon_bytes", BEACON_LEN), sf0)
            if now >= base["busy_until"] and base["win"].ok(now, need, limit):
                base["win"].add(now, need)
                base["busy_until"] = now + need
                ack_intervals.append((now, now + need, None))
                st["slot_beacon_tx"] += 1
                st["slot_beacon_air_s"] += need
                for ii, nd_ in enumerate(nodes):
                    cov = True if Lvl is None else (max(Lvl[ii]) >= sens[sf0])
                    if cov and rng_w.random() >= cfg.p_down:
                        nd_["sync_t"] = now + need
        elif kind == "relay_tx":
            a, j = data
            if a["acked"] or a["cancelled_pre"]:
                continue
            ndj = nodes[j]
            sfr = a["sf_used"]
            need = air(L_AL, sfr)
            if now < ndj["free"] - 1e-12:
                push(ndj["free"], "relay_tx", data)
                continue
            if not ndj["win"].ok(now, need, limit):
                continue
            st["relay_tx"] += 1
            st["relay_air_s"] += need
            a["airtime_s"] += need
            start_tx(j, now, "relay", a, sfr, need, True)
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
            if WSL and slot_defer(now, tau_hb) > now:
                blocked = True
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
            if tx["alert"] is not None and tx["kind"] in ("alert", "flash"):
                tx["alert"]["n_" + res] += 1
            if tx["kind"] == "hb":
                st["hb_rx"] += int(res == "ok")
                continue
            a = tx["alert"]
            if tx["kind"] == "cancel":
                continue
            if d3 and a is not None and tx["kind"] in ("alert", "flash"):
                for j_ in range(cfg.n):  # vehicles with a pending alert that decoded this frame (path loss and shadowing as for the gateway; no collision model at the vehicle receivers, an assumption)
                    if j_ != tx["node"] and nodes[j_]["pending"] and nodes[j_]["free"] <= tx["start"] + 1e-9 and node_link(tx["node"], j_, tx["sf"]):
                        nodes[j_]["htx"].append((now, tx["node"]))
            if PA and pa_mode == "osdr_n" and a is not None and a.get("cell") is not None and tx["kind"] in ("alert", "flash") and not PA.get("no_nn"):
                for j in cell_nodes.get(a["cell"], []):
                    if j != tx["node"] and node_link(tx["node"], j, tx["sf"]) and nodes[j]["free"] <= tx["start"] + 1e-9:
                        nodes[j].setdefault("heard", {})[tx["node"]] = now
            if res == "ok" and tx["kind"] in ("alert", "flash", "relay"):
                a["rx_n"] = a.get("rx_n", 0) + 1
            if res == "collided":
                st["al_collided"] += 1
            if res == "deaf":
                st["al_deaf"] += 1
            if res != "ok":
                continue
            if a["t_rx"] is None:
                a["t_rx"] = now
            if d2 and a.get("cell") is not None and tx["kind"] in ("alert", "flash"):
                base["cl_rx"].setdefault(a["cell"], {})[a["node"]] = now
                base["cl_times"].append((now, a["node"]))
            if dk == "beacon":
                base["rx"].append(now)
                lv = beacon_level(now)
                if lv != base["level"]:
                    base["level"] = lv
                    send_beacon(now)
            stage = "f" if tx["kind"] == "flash" else "a"
            key = (a["node"], a["id"], stage)
            t_a = now + procs
            ack_air = air(L_ACK, tx["sf"])
            if d2 and a.get("cell") is not None and cluster_mode(now):
                if not base["cl_pend"].get(a["cell"]):
                    base["cl_pend"][a["cell"]] = True
                    push(max(t_a, base["cl_last"].get(a["cell"], -1e9) + d2["tc"]), "cl_send", (a["cell"], tx["sf"], tx["ch"], tx["gw"]))
                continue
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
            ack_intervals.append((t_a, t_a + ack_air, tx["ch"]))
            st["ack_sent"] += 1
            if RD:
                for j_ in range(cfg.n):
                    if j_ != a["node"] and ((not Lvl) or Lvl[j_][tx["gw"]] >= sens[tx["sf"]]) and rng_rd.random() >= cfg.p_down * SF_DECAY ** max(0, tx["sf"] - sf0):
                        nodes[j_]["heard"].append(t_a + ack_air)
            if PA and pa_mode in ("osdr", "osdr_n") and a.get("cell") is not None and not PA.get("no_overhear"):
                for j in cell_nodes.get(a["cell"], []):
                    if j != a["node"] and rng_pa.random() >= cfg.p_down * SF_DECAY ** max(0, tx["sf"] - sf0) and ((not Lvl) or Lvl[j][tx["gw"]] >= sens[tx["sf"]]):
                        push(t_a + ack_air, "ack_heard", (j, a["cell"]))
            reach_dn = (not Lvl) or Lvl[a["node"]][tx["gw"]] >= sens[tx["sf"]]
            if reach_dn and rng.random() >= cfg.p_down * SF_DECAY ** max(0, tx["sf"] - sf0):
                push(t_a + ack_air, "ack_rx", (a, stage))
        elif kind == "cl_send":
            cell, sf_c, ch_c, gw_c = data
            if now < base["busy_until"] - 1e-12:
                push(base["busy_until"] + 1e-6, "cl_send", data)
                continue
            ids = sorted(base["cl_rx"].get(cell, {}), key=lambda x: base["cl_rx"][cell][x])[-int(d2.get("max_ids", 24)):]
            ack_air = air(RP.cluster_ack_len(len(ids), int(d2.get("sig_len", RP.SIG_LEN))), sf_c)
            base["cl_pend"][cell] = False
            if not base["win"].ok(now, ack_air, limit):
                st["ack_budget_drop"] += 1
                continue
            base["cl_last"][cell] = now
            base["win"].add(now, ack_air)
            base["busy_until"] = now + ack_air
            ack_intervals.append((now, now + ack_air, ch_c))
            st["ack_sent"] += 1
            st["cluster_ack_tx"] += 1
            st["cluster_ack_air_s"] += ack_air
            listed = frozenset(ids)
            for j_ in cell_nodes.get(cell, []):
                if ((not Lvl) or Lvl[j_][gw_c] >= sens[sf_c]) and rng_rd.random() >= cfg.p_down * SF_DECAY ** max(0, sf_c - sf0):
                    push(now + ack_air, "cl_heard", (j_, cell, listed))
        elif kind == "cl_heard":
            j_, cell, listed = data
            ndj = nodes[j_]
            gate_on = heard_count(ndj, now) >= d2["thr"]
            ndj["heard"].append(now)
            for b_ in list(ndj["pending"]):
                if b_.get("cell") != cell or b_["acked"] or b_["gave_up"] or b_["sev"] < 2:
                    continue
                if rtrace is not None:
                    rtrace.append(("d2", int(j_ in listed), int(gate_on), b_["cdefer"], int(d2.get("max_defers", 3)), "stop" if j_ in listed else ("defer" if (gate_on and b_["cdefer"] < int(d2.get("max_defers", 3))) else "none")))
                if j_ in listed:
                    if b_["t_ack_first"] is None:
                        b_["t_ack_first"] = now
                        if d1tab:
                            ndj["beta"].update(False)
                    b_["acked"], b_["t_ack"] = True, now
                elif gate_on and b_["cdefer"] < int(d2.get("max_defers", 3)):
                    b_["cdefer"] += 1
                    cap_t = b_["arrival"] + RP.DEADLINE_S[b_["sev"]] - RP.round_s(sf0)
                    u_ = rng_rd.random()
                    ready_before = b_["ready"]
                    du_ = RP.defer_until(b_["sev"], now, b_["arrival"], b_["ready"], u_, d2.get("defer_scale", 1.0))
                    b_["defer_until"] = max(b_["ready"], min(du_, cap_t))
                    b_["ready"] = max(b_["ready"], b_["defer_until"])
                    if rtrace is not None:
                        rtrace.append(("d2defer", b_["sev"], now, b_["arrival"], ready_before, u_, d2.get("defer_scale", 1.0), du_))
                    st["defers"] += 1
                    push(b_["ready"], "try", j_)
        elif kind == "ack_heard":
            j, cl = data  # an authenticated gateway ACK for this event cell was decoded by node j: its retries for the cell stop (A1)
            for b in list(nodes[j]["pending"]):
                if b.get("cell") == cl and not b["acked"] and not b["gave_up"] and b["sev"] >= 2:
                    b["suppressed"] = True
                    nodes[j]["pending"].remove(b)
                    st["suppressed"] += 1
                    st["suppressed_unrx"] += int(b["t_rx"] is None)
        elif kind == "ack_rx":
            a, stage = data
            if a["t_ack_first"] is None:
                a["t_ack_first"] = now
                if d1tab:
                    nodes[a["node"]]["beta"].update(False)
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
            if d1tab and kd in ("flash", "alert") and not (a["acked"] or (kd == "flash" and a["flash_acked"])):
                nd["beta"].update(True)
            if is_sct and not a["demoted"] and a["sev"] >= 2:
                if kd == "flash":
                    a["stage"] = "alert"
                    a["ready"] = now
                elif a["acked"]:
                    nd["pending"].remove(a)
                else:
                    if WREL and kd == "alert" and not a.get("relayed"):
                        a["relayed"] = True
                        for j in rng_w.sample([x for x in range(cfg.n) if x != a["node"]], min(int(WREL.get("k", 3)), cfg.n - 1)):
                            if rng_w.random() < WREL.get("p_hear", 0.5):
                                push(now + rng_w.uniform(*WREL.get("delay_s", (1.0, 5.0))), "relay_tx", (a, j))
                    a["rounds"] += 1
                    if a["tries"] >= S.max_tries[a["sev"]]:
                        a["gave_up"] = True
                        nd["pending"].remove(a)
                    elif d1tab:
                        pick = d1_pick(a, nd, t_end + window, a["rounds"])
                        if pick is None:  # nothing fits before the class deadline or in the budget: the alert continues on the normal path with backoff, never stops
                            a["demoted"] = True
                            a["stage"] = "alert"
                            st["demoted"] += 1
                            a["ready"] = t_end + window + S.backoff_s * 2.0 ** max(a["tries"] - 1, 0) * (1.0 + S.jitter * rng.random())
                        else:
                            a["d1_sf"] = pick[1]
                            a["ready"] = max(t_end + window + pick[0], a.get("defer_until", 0.0))
                            if d3:
                                n_oth = htx_count(nd, t_end + window)
                                if D3.active(d3, n_oth, a["sev"]):
                                    sf_r = D3.alt_sf(a["rounds"], pick[1]) if d3.alt else pick[1]
                                    st_ = D3.slot_time(d3, n_oth + 1, a["node"], a["ready"], off_d3[a["node"]], air(L_AL, sf_r), a["arrival"] + RP.DEADLINE_S[a["sev"]])
                                    if rtrace is not None:
                                        rtrace.append(("d3", sf_r, n_oth, a["node"], a["ready"], off_d3[a["node"]], air(L_AL, sf_r), a["arrival"] + RP.DEADLINE_S[a["sev"]], st_))
                                    if st_ is not None:
                                        a["ready"] = st_
                                        a["d1_sf"] = sf_r
                                        st["d3_slotted"] += 1
                                        st["d3_alt_sf"] += int(sf_r != pick[1])
                            a["stage"] = "flash" if (S.flash and not a["flash_acked"]) else "alert"
                    elif dk == "demote" and a["extra"] and a["sev"] == 2 and a["rounds"] >= dyn["k"]:
                        a["demoted"] = True  # an escalated non-severe event that keeps failing goes back to the normal path; Critical is never demoted
                        a["stage"] = "alert"
                        st["demoted"] += 1
                        a["ready"] = t_end + window + S.backoff_s * 2.0 ** max(a["tries"] - 1, 0) * (1.0 + S.jitter * rng.random())
                    else:
                        a["ready"] = t_end + window + (pa_gap(a, now, t_end, window) if (PA and pa_mode in ("osdr", "osdr_n")) else spacing(a, window)) + bo(a["sev"])
                        a["stage"] = "flash" if (S.flash and not a["flash_acked"]) else "alert"
            elif is_sct:
                if a["acked"]:
                    nd["pending"].remove(a)
                elif a["tries"] >= S.max_tries[a["sev"] if (d1tab and a["sev"] >= 2) else (min(a["sev"], 1) if not a["demoted"] else 1)]:
                    a["gave_up"] = True
                    nd["pending"].remove(a)
                else:
                    a["ready"] = t_end + window + (0.0 if S.p1_retry else S.backoff_s * 2.0 ** (a["tries"] - 1) * (1.0 + S.jitter * rng.random()))
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
    if invariants:
        check_invariants(alerts, heap)
    if diag is not None:
        diag.extend(alerts)
    return summarise(alerts, st, cfg, limit)


def check_invariants(alerts: list[dict], heap: list) -> None:
    """Run-time invariants (V12 CV 3); an AssertionError aborts the run. Events are conserved per alert: transmissions = decoded + lost + collided + deaf + still in flight."""
    inflight: dict = {}
    for _t, _s, k, d in heap:
        if k == "tx_end" and d["alert"] is not None and d["kind"] in ("alert", "flash"):
            inflight[id(d["alert"])] = inflight.get(id(d["alert"]), 0) + 1
    for a in alerts:
        sent = a["tries"] + a["n_flash"]
        got = a["n_ok"] + a["n_lost"] + a["n_collided"] + a["n_deaf"] + inflight.get(id(a), 0)
        assert sent == got, f"events not conserved: sent {sent}, accounted {got}"
        assert a["arrival"] >= 0.0 and (a["ready"] is None or a["ready"] >= 0.0), "negative time"
        if a["t_rx"] is not None:
            assert a["first_tx"] is not None and a["n_ok"] >= 1 and a["t_rx"] >= a["first_tx"] - 1e-9, "delivered packet without a matching send"
        if a["t_ack_first"] is not None:
            assert a["t_rx"] is not None and a["t_ack_first"] >= a["t_rx"] - 1e-9, "ACK before reception"


def summarise(alerts: list[dict], st: dict, cfg: SCfg, limit: float) -> dict:
    df = pd.DataFrame(alerts)
    out: dict = dict(policy=cfg.policy, n=cfg.n, sf=cfg.sf, seed=cfg.seed, hour=cfg.hour, label=cfg.label, **st)
    out["hb_dropped_share"] = 1.0 - st["hb_rx"] / max(st["hb_sched"], 1)
    out["alert_collided_share"] = st["al_collided"] / max(st["al_tx"] + st["flash_tx"], 1)
    out["slot_beacon_duty_share"] = st["slot_beacon_air_s"] / max(limit, 1e-9)
    out["relay_air_share_of_allowance"] = st["relay_air_s"] / (limit * max(cfg.n, 1))
    out["fast_air_share_of_allowance"] = st["fast_air_s"] / (limit * max(cfg.n, 1))
    out["node_air_share"] = st["node_air_s"] / (limit * max(cfg.n, 1))
    if df.empty:
        return out
    crash = df[df.kind == "crash"].copy()
    crash["first"] = crash.t_ack_first - crash.arrival
    crash["full"] = crash.t_ack - crash.arrival
    crash["rx"] = crash.t_rx - crash.arrival
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
            out[f"reach{x}_rx_{name}"] = float((g["rx"] <= x).mean())
        if "rx_n" in g:
            out[f"dup_rx_{name}"] = float((g["rx_n"].fillna(0) - 1).clip(lower=0).mean())
        if g["first"].notna().any():
            out[f"median_lat_s_{name}"] = float(g["first"].median())
            out[f"p95_lat_s_{name}"] = float(g["first"].quantile(0.95))
    if "cell" in crash and len(crash):
        crit = crash[crash.true == 3]
        if len(crit):
            ev = [float((g["first"] <= 10).any()) for _, g in crit[crit.cell.notna()].groupby("cell")] + [float(x) for x in (crit[crit.cell.isna()]["first"] <= 10)]
            out["event_reach10_critical"] = float(np.mean(ev)) if ev else np.nan
    out["suppressed_share"] = st["suppressed"] / max(len(df[df.kind == "crash"]), 1)
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
