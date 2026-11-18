"""Redesign policies D1 (loss-adaptive deadline policy) and D2 (gated, authenticated overhear-and-defer). Pure logic: no simulator import, so the simulator hook, the unit tests and the firmware-path
implementation (D6) can all call the same functions. Design: docs/02_preregistration/PREREGISTRATION_V12.md.

D1. The node keeps a Beta posterior of the per-round failure probability from its own ACK history (a round = one transmission and its listen window). For each severity class (Severe, Critical) a dynamic
programme, solved offline, gives the retry gap and spreading factor that maximise the probability that the base receives the alert before the class deadline, under an airtime budget. The table is indexed by
(class, failed attempts so far j, time left, loss bin, load bin, budget units).

D2. The gateway signs a cluster ACK (event id, freshness, vehicle ids received) with a key vehicles do not hold (Ed25519; vehicles hold only the public key). A vehicle stops only if its own id is listed in
a verified cluster ACK; if it verifies one that does not list it, it defers by a class-dependent interval, never stops. Active only when the overheard rate is at or above a load threshold.
"""
from __future__ import annotations

import math
import struct
from collections import deque
from dataclasses import dataclass, field

import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from crashguard.lora import airtime_ms

SF_DECAY = 0.7  # per spreading-factor step above the base, from capacity.py (an ASSUMPTION of the simulator, reused by the table)
PROC_S, MARGIN_S = 0.1, 0.1  # replay.PROC_S, replay.MARGIN_S
ALERT_LEN, ACK_LEN = 97, 26
DEADLINE_S = {2: 30.0, 3: 10.0}  # Severe, Critical (V7 and V12 convention)


def air_s(nbytes: int, sf: int) -> float:
    return airtime_ms(nbytes, sf) / 1000.0


def round_s(sf: int, nbytes: int = ALERT_LEN) -> float:
    """Transmission plus listen window."""
    return air_s(nbytes, sf) + PROC_S + air_s(ACK_LEN, sf) + MARGIN_S


# ------------------------------------------------------------------------------------------------ deadline arithmetic
def time_left(deadline_s: float, t_event: float, now: float) -> float:
    return deadline_s - (now - t_event)


def retry_allowed(deadline_s: float, t_event: float, t_start: float, airtime: float) -> bool:
    """A table-driven retry may be scheduled only if its transmission ends no later than the class deadline."""
    return t_start + airtime <= t_event + deadline_s + 1e-12


# ------------------------------------------------------------------------------------------------ Beta loss estimate
@dataclass
class BetaLoss:
    """Beta(a, b) posterior of the round failure probability. Prior mean ``l0`` with strength ``n0``; forgetting factor applied to the counts before every update."""

    n0: float = 6.0
    l0: float = 0.3
    forget: float = 0.97
    a: float = field(init=False)
    b: float = field(init=False)

    def __post_init__(self) -> None:
        self.a, self.b = self.n0 * self.l0, self.n0 * (1.0 - self.l0)

    def update(self, failed: bool) -> None:
        a0, b0 = self.n0 * self.l0, self.n0 * (1.0 - self.l0)
        self.a = a0 + (self.a - a0) * self.forget
        self.b = b0 + (self.b - b0) * self.forget
        if failed:
            self.a += 1.0
        else:
            self.b += 1.0

    @property
    def mean(self) -> float:
        return self.a / (self.a + self.b)


# ------------------------------------------------------------------------------------------------ D1 table
L_EDGES = np.array([0.10, 0.20, 0.30, 0.40, 0.55, 0.70, 0.85])  # 8 loss bins
L_CENTRES = np.array([0.05, 0.15, 0.25, 0.35, 0.475, 0.625, 0.775, 0.925])
LOAD_EDGES = np.array([1, 4, 10])  # overheard ACKs in the last 10 s: 0 | 1-3 | 4-9 | >= 10
GAPS = (0.0, 0.25, 0.5, 1.0, 2.0, 3.5)
SF_STEPS = (0, 1, 2)
J_MAX = 8
NB_MAX = 8
TAU_STEP = {2: 1.0, 3: 0.25}


@dataclass(frozen=True)
class D1Params:
    n0: float = 6.0  # prior strength (also used inside the table to update the loss belief after each failure)
    l0: float = 0.3
    forget: float = 0.97
    rho: tuple = (0.0, 0.10, 0.30, 0.50)  # chance that a quick retry meets the same crowd, per load bin
    g0: float = 1.0  # time scale (s) over which that chance decays with the gap
    share: tuple = (0.0, 0.0, 0.3, 0.5)  # share of the remaining hourly allowance one event may plan with (Severe 0.3, Critical 0.5)


def loss_bin(l_hat: float) -> int:
    return int(np.searchsorted(L_EDGES, l_hat, side="right"))


def load_bin(n_heard: int) -> int:
    return int(np.searchsorted(LOAD_EDGES, n_heard, side="right"))


def budget_units(budget_s: float, unit_s: float) -> int:
    return int(max(0, min(NB_MAX, math.floor(budget_s / unit_s + 1e-9))))


class D1Table:
    """Offline solution for one base spreading factor."""

    def __init__(self, sf0: int, params: D1Params = D1Params(), alert_len: int = ALERT_LEN):
        self.sf0, self.p, self.alert_len = sf0, params, alert_len
        self.unit_s = air_s(alert_len, sf0)
        self.sfs = [min(12, sf0 + k) for k in SF_STEPS]
        self.acts = [(g, k) for g in GAPS for k in range(len(SF_STEPS))]
        self.A: dict[int, np.ndarray] = {}
        self.V: dict[int, np.ndarray] = {}
        for c in (2, 3):
            self._solve(c)

    def _solve(self, c: int) -> None:
        P = self.p
        dt = TAU_STEP[c]
        nT = int(round(DEADLINE_S[c] / dt)) + 1
        nL, nQ = len(L_CENTRES), 4
        V = np.zeros((J_MAX + 2, nT, nL, nQ, NB_MAX + 1))
        A = np.full((J_MAX + 1, nT, nL, nQ, NB_MAX + 1), -1, dtype=np.int16)
        rho = np.array(P.rho)[None, :, None]
        for j in range(J_MAX, -1, -1):
            lj = (P.n0 * L_CENTRES + min(j, J_MAX)) / (P.n0 + min(j, J_MAX))  # belief after j failures within the event
            p_hat = 1.0 - np.sqrt(1.0 - lj)  # symmetric split of the round failure into the two directions
            for t in range(nT):
                tau = t * dt
                best = np.zeros((nL, nQ, NB_MAX + 1))
                bact = np.full((nL, nQ, NB_MAX + 1), -1, dtype=np.int16)
                for ai, (g, k) in enumerate(self.acts):
                    s = self.sfs[k]
                    delta = s - self.sf0
                    a_tx = air_s(self.alert_len, s)
                    if g + a_tx > tau + 1e-12:
                        continue
                    units = int(math.ceil(a_tx / self.unit_s - 1e-9))
                    base = (1.0 - p_hat * SF_DECAY ** delta)[:, None, None]
                    coll = 0.0 if (delta > 0 or j == 0) else rho * math.exp(-g / P.g0)
                    r = base * (1.0 - coll) * np.ones((nL, nQ, NB_MAX + 1))
                    tau_next = tau - (g + round_s(s, self.alert_len))
                    t_next = int(math.floor(tau_next / dt + 1e-9)) if tau_next >= 0 else -1
                    val = np.empty((nL, nQ, NB_MAX + 1))
                    feas = np.zeros((nL, nQ, NB_MAX + 1), dtype=bool)
                    for nb in range(units, NB_MAX + 1):
                        feas[:, :, nb] = True
                        nxt = V[j + 1][t_next][:, :, nb - units] if (t_next >= 0 and j < J_MAX) else 0.0
                        val[:, :, nb] = r[:, :, nb] + (1.0 - r[:, :, nb]) * nxt
                    better = feas & (val > best + 1e-12)
                    best = np.where(better, val, best)
                    bact = np.where(better, ai, bact)
                V[j][t] = best
                A[j][t] = bact
            # ties keep the first (smallest gap, base spreading factor) action: strict improvement above
        self.V[c], self.A[c] = V, self._monotone(A)

    def _monotone(self, A: np.ndarray) -> np.ndarray:
        """Projection that makes urgency monotone: the retry gap never grows when less time is left (axis 1) and never grows when the loss is higher (axis 2). It takes the largest non-decreasing (in time left) and
        non-increasing (in loss) lower envelope of the gap, iterated to a fixed point; a shorter gap keeps every action feasible. The spreading factor of the DP action is kept."""
        gaps = np.array([g for g, _k in self.acts])
        ks = np.array([k for _g, k in self.acts])
        feas = A >= 0
        G = np.where(feas, gaps[np.clip(A, 0, None)], np.inf)
        while True:
            G2 = np.minimum.accumulate(G[:, ::-1], axis=1)[:, ::-1]  # suffix minimum over time left
            G2 = np.minimum.accumulate(G2, axis=2)  # prefix minimum over loss bins
            if np.array_equal(G2, G):
                break
            G = G2
        out = np.full(A.shape, -1, dtype=np.int16)
        k_of = np.where(feas, ks[np.clip(A, 0, None)], 0)
        for ai, (g, k) in enumerate(self.acts):
            out[feas & (G == g) & (k_of == k)] = ai
        # entries whose projected gap has no action with the original spreading factor (cannot happen: the gap set is shared by all k)
        assert ((out >= 0) == feas).all()
        return out

    def lookup(self, c: int, j: int, tau_s: float, l_hat: float, n_heard: int, budget_s: float) -> tuple[float, int] | None:
        """(gap in s, spreading factor) or None when no table-driven attempt fits (deadline, budget)."""
        if tau_s <= 0:
            return None
        dt = TAU_STEP[c]
        t = min(int(math.floor(tau_s / dt + 1e-9)), self.A[c].shape[1] - 1)
        ai = int(self.A[c][min(j, J_MAX), t, loss_bin(l_hat), load_bin(n_heard), budget_units(budget_s, self.unit_s)])
        if ai < 0:
            return None
        g, k = self.acts[ai]
        return g, self.sfs[k]

    def size_bytes(self) -> int:
        return int(sum(a.size for a in self.A.values()))  # one byte per entry in firmware


# ------------------------------------------------------------------------------------------------ D2: cluster ACK
MSG_CLUSTER_ACK = 4
_HDR = "<BBIIB"  # type, version, event id, freshness (GPS s), count
CLUSTER_FRESH_S = 10
SIG_LEN = 64


def cluster_ack_len(m: int, sig_len: int = SIG_LEN) -> int:
    return struct.calcsize(_HDR) + 2 * m + sig_len


def new_gateway_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def encode_cluster_ack(sk: Ed25519PrivateKey, event_id: int, fresh_s: int, ids: list[int]) -> bytes:
    ids = sorted(set(int(i) & 0xFFFF for i in ids))
    if len(ids) > 255:
        raise ValueError("too many ids")
    body = struct.pack(_HDR, MSG_CLUSTER_ACK, 1, event_id & 0xFFFFFFFF, fresh_s & 0xFFFFFFFF, len(ids)) + b"".join(struct.pack("<H", i) for i in ids)
    return body + sk.sign(body)


@dataclass
class ClusterVerdict:
    action: str  # 'stop' | 'defer' | 'ignore'
    reason: str


class ClusterAckVerifier:
    """Vehicle side. Holds only the gateway PUBLIC key. Keeps a ring of digests of frames already processed (replay of a processed frame is ignored)."""

    def __init__(self, pk: Ed25519PublicKey, ring: int = 16):
        self.pk, self.seen = pk, deque(maxlen=ring)

    def check(self, frame: bytes, my_id: int, my_event: int, now_gps_s: float, window_s: int = CLUSTER_FRESH_S) -> ClusterVerdict:
        hl = struct.calcsize(_HDR)
        if len(frame) < hl + SIG_LEN:
            return ClusterVerdict("ignore", "short")
        body, sig = frame[:-SIG_LEN], frame[-SIG_LEN:]
        try:
            self.pk.verify(sig, body)
        except InvalidSignature:
            return ClusterVerdict("ignore", "bad_signature")
        typ, ver, ev, fresh, m = struct.unpack_from(_HDR, body)
        if typ != MSG_CLUSTER_ACK or ver != 1 or len(body) != hl + 2 * m:
            return ClusterVerdict("ignore", "malformed")
        if ev != (my_event & 0xFFFFFFFF):
            return ClusterVerdict("ignore", "other_event")
        if abs(now_gps_s - fresh) > window_s:
            return ClusterVerdict("ignore", "stale")
        if sig in self.seen:
            return ClusterVerdict("ignore", "replay")
        self.seen.append(sig)
        ids = {struct.unpack_from("<H", body, hl + 2 * i)[0] for i in range(m)}
        return ClusterVerdict("stop", "listed") if (my_id & 0xFFFF) in ids else ClusterVerdict("defer", "not_listed")


DEFER_S = {2: 4.0, 3: 1.0}  # defer interval after a verified cluster ACK that does not list the vehicle (Severe, Critical); a design constant of V12


def defer_until(cls: int, now: float, t_event: float, ready: float, jitter_u: float, scale: float = 1.0) -> float:
    """New ready time after a defer: at least the old one, pushed by a jittered class interval, never later than the class deadline minus one round at the base SF is enforced by the caller."""
    return max(ready, now + DEFER_S[cls] * scale * (0.5 + 0.5 * jitter_u))


class NodeState:
    """What the vehicle keeps for one event under D2: pending flag; stop only through a listed id; defer count bounded (a defer never becomes a stop)."""

    def __init__(self, my_id: int, event: int, cls: int, t_event: float):
        self.my_id, self.event, self.cls, self.t_event = my_id, event, cls, t_event
        self.pending, self.verified_ack, self.defers = True, False, 0

    def on_verdict(self, v: ClusterVerdict) -> None:
        if v.action == "stop":
            self.pending, self.verified_ack = False, True
        elif v.action == "defer":
            self.defers += 1  # the vehicle stays pending
