"""End-to-end software replay of VZCrash test events (and NHTSA tests) through the whole alert chain. SIMULATED except where stated.

Chain, per event: trigger (config) -> 2.8 s window -> 14 features -> deployed 15-tree forest (seed 42, threshold from validation) -> physics severity class
-> cancel window by class -> signed 97 B alert (real HMAC) -> duty-cycle token bucket -> lossy LoRa channel -> base verifier (counter check, idempotent re-ACK,
re-ACK limit, base ACK budget) -> signed 26 B ACK -> lossy channel back -> node checks the ACK.

MEASURED_SOFTWARE: the event pool (model probabilities, severity classes) is computed from the real events with the real code.
SIMULATED: arrivals, channel loss, timing. These are NOT hardware measurements; hardware test H3 would replace them.

ASSUMPTIONS (ours; every one is listed in docs/02_preregistration/ALGORITHMS.md and the report):
- Alert arrivals are Poisson at a stated rate; each alert is a random draw (with replacement) from the pool of events the model called a crash (true crashes and false alarms).
- Window fill = POST_S from config.py; on-device compute time COMPUTE_S (not measured: H1 would measure it); cancel window by class 10, 8, 6 and 5 s
  (the 5 to 10 s range of docs/00_overview/ARCHITECTURE.md, longer for lower classes); no driver cancels in the base run.
- Loss: independent per transmission, or a two-state Gilbert-Elliott chain per direction with the same mean loss (good state loss 0, bad state loss 0.9,
  mean bad-burst length 1 / P_BG transmissions); alert (uplink) and ACK (downlink) have separate chains and may have different mean loss.
- One node, one base, no collisions. Node airtime is paid from a token bucket (10% duty cycle, 360 s capacity); the base pays for ACKs from its own bucket.
- After each try the node listens for PROC_S + ACK airtime + MARGIN_S, then retries at once (same bytes, same counter: the idempotent re-ACK design).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import packet as P
from crashguard import severity as S
from crashguard import verifier as V
from crashguard.lora import DUTY, airtime_ms

KEY = b"crashguard-replay-key-32-bytes!!"
NODE_ID = 7
COMPUTE_S = 0.05
CANCEL_S = (10.0, 8.0, 6.0, 5.0)
PROC_S, MARGIN_S = 0.1, 0.1
GE_P_BG, GE_LOSS_BAD, GE_LOSS_GOOD = 0.3, 0.9, 0.0
SEV_NAMES = tuple(n.lower() for n in C.SEV_NAMES)  # low, moderate, severe, critical
POOL_PATH = C.PROCESSED / "replay_pool.parquet"


# ------------------------------------------------------------------ event pool (MEASURED_SOFTWARE)
def build_pool(seed: int = C.SEED) -> pd.DataFrame:
    """Run every triggered, de-duplicated VZCrash test event through trigger, window, features, model and severity."""
    from crashguard import detector_extra as D
    from crashguard import robustness as R
    from crashguard.features import compute_features
    from crashguard.models import op_thresholds

    tr, va, te = D.frames_full()
    va_trig = va[va.triggered]
    scorer, _ = D.fit("rf15", seed, tr, va_trig)
    thr, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
    tt = te[te.triggered].reset_index(drop=True)
    events = R.load_events(set(tt.event_id))
    order = {e[0]: i for i, e in enumerate(events)}
    tt = tt.assign(_o=tt.event_id.map(order)).sort_values("_o").reset_index(drop=True)
    events = [events[order[e]] for e in tt.event_id]
    wa, wg, trig = R.windows_for(events, dict(kind="baseline"), seed)
    assert trig.all() and len(wa) == len(tt)
    feats = pd.DataFrame(compute_features(wa, wg), columns=list(C.FEATURES))
    prob = scorer(feats.assign(**{"_": 0}))
    rows = []
    for i in range(len(wa)):
        r = S.severity(wa[i], C.FS_HZ, C.PRE_N, wg[i])
        rows.append(dict(dv_kmh=r["dv_res_kmh"], asi=r["asi"], sev=int(r["severity_class"]), rollover=bool(r["rollover"]), pulse_ms=r["pulse_ms"], peak_g=float(np.linalg.norm(wa[i], axis=1).max())))
    pool = pd.concat([tt[["event_id", "label", "vehiclesize", "y"]].reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    pool["prob"] = prob
    pool["alert"] = pool.prob >= thr
    pool["threshold"] = thr
    return pool


def load_pool() -> pd.DataFrame:
    if POOL_PATH.exists():
        return pd.read_parquet(POOL_PATH)
    pool = build_pool()
    POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    pool.to_parquet(POOL_PATH)
    return pool


# ------------------------------------------------------------------ channel
class Channel:
    """Per-direction loss: independent (``iid``) or Gilbert-Elliott (``ge``) with the same mean loss."""

    def __init__(self, kind: str, loss_up: float, loss_down: float, rng: random.Random):
        self.kind, self.rng, self.p_bg = kind, rng, GE_P_BG
        self.mean = {"up": loss_up, "down": loss_down}
        self.state: dict[str, int] = {}
        self.p_gb: dict[str, float] = {}
        for d, m in self.mean.items():
            self.state[d] = 0
            if kind == "ge" and m > 0:
                pi = min(m / GE_LOSS_BAD, 0.999)  # stationary share of time in the bad state, so that the mean loss equals m
                self.p_gb[d] = GE_P_BG * pi / (1 - pi)
                self.state[d] = 1 if rng.random() < pi else 0  # 1 = bad

    def lost(self, d: str, scale: float = 1.0) -> bool:
        """One transmission; ``scale`` multiplies the loss probability (a higher spreading factor, N16)."""
        m = self.mean[d]
        if m <= 0:
            return False
        if self.kind == "iid":
            return self.rng.random() < m * scale
        if self.state[d] == 1:
            if self.rng.random() < self.p_bg:
                self.state[d] = 0
        elif self.rng.random() < self.p_gb[d]:
            self.state[d] = 1
        return self.rng.random() < (GE_LOSS_BAD if self.state[d] == 1 else GE_LOSS_GOOD) * scale


# ------------------------------------------------------------------ policies
@dataclass
class Policy:
    """Delivery policy: maximum tries per estimated severity class, service order, spacing between tries."""

    name: str
    tries: tuple = (4, 4, 4, 4)
    by_severity: bool = False  # serve the most severe waiting alert first
    reserve_frac: float = 0.0  # share of the node's token capacity that only critical alerts may use (Algorithm 3)
    extra: dict = field(default_factory=dict)

    def max_tries(self, a: dict) -> int:
        return self.tries[a["sev"]]

    def key(self, a: dict, now: float):
        return (-a["sev"], a["arrival"]) if self.by_severity else (a["arrival"],)

    def retry_ready(self, a: dict, t_end: float, window: float, rng: random.Random) -> float:
        return t_end + window

    def sf_for(self, a: dict, base_sf: int, tokens: float = 0.0) -> int:
        return base_sf

    def may_spend(self, a: dict, tokens: float, need: float, capacity: float) -> bool:
        if self.reserve_frac > 0 and a["sev"] < 3:
            return tokens - need >= self.reserve_frac * capacity
        return tokens >= need

    def observe(self, success: bool) -> None:
        """Feedback after every try (an ACK reached the car or not). The baseline policies ignore it."""

    def fresh(self) -> Policy:
        """A copy with its learned state reset, so that one simulated hour never leaks into the next."""
        import copy

        return copy.deepcopy(self)


POLICIES = {
    "none": Policy("none", (1, 1, 1, 1)),
    "fixed3": Policy("fixed3", (4, 4, 4, 4)),
    "severity": Policy("severity", (2, 4, 8, 12), by_severity=True),
}


@dataclass(frozen=True)
class Scenario:
    name: str
    sf: int
    rate_per_h: float
    node_initial_s: float = 360.0
    base_initial_s: float = 360.0
    loss_up: float = 0.3
    loss_down: float = 0.3
    kind: str = "iid"
    cancel_scale: float = 1.0
    reack_limit: bool = True
    flood: tuple | None = None  # (start_s, duration_s, rate_per_s)
    sf_decay: float = 0.7  # ASSUMPTION (N16): per-transmission loss is multiplied by this for every spreading-factor step above the scenario's own


def simulate(pool_sev: np.ndarray, sc: Scenario, policy: Policy, rng_arr: random.Random, rng_ch: random.Random, duration_s: float = 3600.0,
             timeline: list | None = None) -> list[dict]:
    """One simulated hour with real packets and the real verifier. Returns one record per alert."""
    policy = policy.fresh()
    chan = Channel(sc.kind, sc.loss_up, sc.loss_down, rng_ch)
    pool_arr = np.asarray(pool_sev)
    air_of = lambda sf: airtime_ms(P.ALERT_LEN, sf) / 1000.0  # noqa: E731
    air_ack_of = lambda sf: airtime_ms(P.ACK_LEN, sf) / 1000.0  # noqa: E731
    interval = (air_of(sc.sf) + PROC_S + air_ack_of(sc.sf) + MARGIN_S) * 0.999
    ver = V.BaseVerifier(KEY, reack_interval_s=interval if sc.reack_limit else None, budget=V.DutyBudget(initial_s=sc.base_initial_s), sf=sc.sf)
    alerts, t = [], 0.0
    rate = sc.rate_per_h / 3600.0
    while True:
        t += rng_arr.expovariate(rate)
        if t >= duration_s:
            break
        k = rng_arr.randrange(len(pool_arr))
        sev = int(pool_arr[k][0]) if pool_arr.ndim == 2 else int(pool_arr[k])  # the class the car estimates and puts in the alert
        true = int(pool_arr[k][1]) if pool_arr.ndim == 2 else sev  # the class a reference measurement gives (results are reported by this one)
        ready = t + C.POST_S + COMPUTE_S + CANCEL_S[sev] * sc.cancel_scale
        alerts.append(dict(arrival=t, ready=ready, first_ready=ready, sev=sev, true=true, tries=0, t_rx=None, t_ack=None, gave_up=False, airtime_s=0.0, wait_s=0.0, counter=None,
                           raw=None, sf_used=sc.sf, first_tx=None))
    alerts.sort(key=lambda a: a["arrival"])
    for i, a in enumerate(alerts):
        a["event_id"] = i + 1
    cap = 360.0
    tokens, t_tok, now, _idx, counter = sc.node_initial_s, 0.0, 0.0, 0, 0
    pending: list[dict] = []
    by_ready = sorted(alerts, key=lambda a: a["ready"])
    # flood setup: an old accepted alert is captured and replayed at a fixed rate from the start of the flood
    fl_next, fl_dt, fl_end, captured = None, None, None, None
    if sc.flood:
        start, dur, frate = sc.flood
        cap_alert = P.Alert(NODE_ID, 0, 0, 0)
        captured = P.encode_alert(cap_alert, KEY)
        ver.handle(captured, now=0.0)
        ver.last_ack_at.pop((NODE_ID, 0), None)
        fl_next, fl_dt, fl_end = start, 1.0 / frate, start + dur
    flood_stats = dict(replayed=0)

    def inject(until: float) -> None:
        nonlocal fl_next
        while fl_next is not None and fl_next <= until and fl_next < fl_end:
            ver.handle(captured, now=fl_next)
            flood_stats["replayed"] += 1
            fl_next += fl_dt
    ridx = 0
    while ridx < len(by_ready) or pending:
        while ridx < len(by_ready) and by_ready[ridx]["ready"] <= now:
            pending.append(by_ready[ridx])
            ridx += 1
        ready = [a for a in pending if a["ready"] <= now]
        if not ready:
            nxt = [a["ready"] for a in pending] + ([by_ready[ridx]["ready"]] if ridx < len(by_ready) else [])
            now = max(now, min(nxt))
            continue
        a = min(ready, key=lambda x: policy.key(x, now))
        tokens = min(cap, tokens + DUTY * (now - t_tok))
        t_tok = now
        sf = policy.sf_for(a, sc.sf, tokens)
        air, air_ack = air_of(sf), air_ack_of(sf)
        window = PROC_S + air_ack + MARGIN_S
        if not policy.may_spend(a, tokens, air, cap):
            need = air - tokens if policy.reserve_frac <= 0 or a["sev"] == 3 else (air + policy.reserve_frac * cap - tokens)
            wait = max(need, 1e-6) / DUTY
            a["wait_s"] += wait
            now += wait
            tokens, t_tok = min(cap, tokens + DUTY * wait), now
            continue
        tokens -= air
        if a["tries"] == 0:
            counter += 1
            a["counter"] = counter
            a["first_tx"] = now
            al = P.Alert(NODE_ID, a["event_id"], counter, int(a["arrival"] * 1000) & 0xFFFFFFFF, severity=a["sev"], delta_v_kmh_x100=0)
            a["raw"] = P.encode_alert(al, KEY)
        a["tries"] += 1
        a["airtime_s"] += air
        a["sf_used"] = sf
        t_end = now + air
        if timeline is not None:
            timeline.append((now, air, a["sev"]))
        inject(t_end)
        ver.ack_airtime_s = air_ack
        loss_scale = sc.sf_decay ** max(0, sf - sc.sf)
        up_lost = chan.lost("up", loss_scale)
        acked = False
        if not up_lost:
            dec, ack = ver.handle(a["raw"], now=t_end)
            if dec in (V.ACCEPT, V.ACCEPT_NO_ACK) and a["t_rx"] is None:
                a["t_rx"] = t_end
            if ack is not None and not chan.lost("down", loss_scale) and V.node_accepts_ack(ack, KEY, NODE_ID, a["event_id"], a["counter"]):
                a["t_ack"] = t_end + PROC_S + air_ack
                acked = True
        policy.observe(acked)
        if acked:
            pending.remove(a)
        else:
            a["ready"] = policy.retry_ready(a, t_end, window, rng_ch)
            if a["tries"] >= policy.max_tries(a):
                a["gave_up"] = True
                pending.remove(a)
        now = t_end + window
    inject(duration_s + 3600.0)
    for a in alerts:
        a.pop("raw", None)
        a["flood_replayed"] = flood_stats["replayed"]
        a["base_acks"] = ver.acks_sent
        a["base_airtime_s"] = ver.ack_airtime_total_s
    return alerts


def summarise(alerts: list[dict], duration_s: float = 3600.0) -> dict:
    df = pd.DataFrame(alerts)
    out: dict[str, float] = {"alerts": float(len(df))}
    if df.empty:
        return out
    df["lat"] = df.t_ack - df.arrival
    cls = "true" if "true" in df else "sev"  # results are reported by the reference class when the estimated class can differ
    groups = {"all": df, **{s: df[df[cls] == i] for i, s in enumerate(SEV_NAMES)}}
    for name, g in groups.items():
        if len(g) == 0:
            continue
        out[f"n_{name}"] = float(len(g))
        out[f"delivered_{name}"] = float(g.t_ack.notna().mean())
        out[f"received_{name}"] = float(g.t_rx.notna().mean())
        out[f"retries_{name}"] = float((g.tries - 1).clip(lower=0).mean())
        out[f"airtime_share_{name}"] = float(g.airtime_s.sum() / (duration_s * DUTY))
        out[f"never_sent_{name}"] = float((g.tries == 0).mean())
        out[f"waited_budget_{name}"] = float((g.wait_s > 1.0).mean())
        out[f"blocked_{name}"] = float(((g.tries == 0) | (g.wait_s > 1.0)).mean())
        if g.lat.notna().any():
            out[f"median_lat_s_{name}"] = float(g.lat.median())
            out[f"p95_lat_s_{name}"] = float(g.lat.quantile(0.95))
    out["airtime_share_total"] = float(df.airtime_s.sum() / (duration_s * DUTY))
    out["base_ack_airtime_share"] = float(df.base_airtime_s.iloc[0] / (duration_s * DUTY))
    out["flood_replayed"] = float(df.flood_replayed.iloc[0])
    return out


def run_config(pool_sev: np.ndarray, sc: Scenario, policy: Policy, seeds=C.SEEDS, hours: int = 20) -> pd.DataFrame:
    """Hour-level summaries: rows (seed, hour). Arrivals depend only on scenario, seed and hour (paired across policies); channel draws also on the policy."""
    rows = []
    for seed in seeds:
        for h in range(hours):
            rng_arr = random.Random(f"arr|{sc.name}|{seed}|{h}")
            rng_ch = random.Random(f"ch|{sc.name}|{policy.name}|{seed}|{h}")
            rows.append(dict(seed=seed, hour=h, **summarise(simulate(pool_sev, sc, policy, rng_arr, rng_ch))))
    return pd.DataFrame(rows)


def ci_of(df: pd.DataFrame, col: str) -> tuple[float, float, float]:
    x = df[col].dropna().to_numpy()
    return B.ci(x, np.mean) if len(x) else (float("nan"),) * 3
