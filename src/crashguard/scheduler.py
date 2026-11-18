"""N16: severity- and budget-aware delivery scheduler (docs/02_preregistration/ALGORITHMS.md lists every rule and parameter before any run). SIMULATED supporting evidence.

Rules (S):
1. Reserve: a fraction ``rho`` of the node's token capacity is kept for critical alerts.
2. Order: waiting alerts are served by effective severity = class + min(age / tau, 0.99) (highest first), so an old low alert can overtake a newer one of the same class
   but never one of a higher class.
3. Retry spacing: after the k-th failed try the next try waits the listening window plus
   m x base_sev x 2^min(k-1, 5) x (1 + jitter x u) x (1 + 2 x (1 - p_hat)), capped at cap_sev; u uniform in [0, 1); p_hat is an exponentially weighted share of successful
   tries (weight 0.3, start 1.0) updated from the ACK feedback after every try.
4. Spreading factor (optional): after 3 consecutive failures of an alert of class moderate or above, its next tries use SF + 1 (at most SF12), but only if the tokens left after
   the send are at least twice the new airtime. ASSUMPTION: the base receives every spreading factor, and the loss per transmission falls by a factor ``sf_decay`` (0.7) per step.
Maximum tries are those of the severity-table baseline (2, 4, 8 and 12 for low, moderate, severe and critical).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from crashguard import packet as P
from crashguard.lora import airtime_ms
from crashguard.replay import Policy

BASE_S = (4.0, 2.0, 1.0, 0.5)  # base spacing by class: low, moderate, severe, critical
CAP_S = (64.0, 32.0, 16.0, 8.0)
TAU_S = 300.0
EWMA_W = 0.3
FAIL_BEFORE_SF = 3


@dataclass
class Scheduler(Policy):
    name: str = "scheduler"
    tries: tuple = (2, 4, 8, 12)
    by_severity: bool = True
    rho: float = 0.0
    m: float = 1.0
    jitter: float = 0.0
    sf_raise: bool = False
    p_hat: float = 1.0
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.reserve_frac = self.rho  # the engine uses reserve_frac for the reservation (wait time and the spend test)

    def key(self, a: dict, now: float):
        eff = a["sev"] + min(max(now - a["arrival"], 0.0) / TAU_S, 0.99)
        return (-eff, a["arrival"])

    def retry_ready(self, a: dict, t_end: float, window: float, rng: random.Random) -> float:
        k = max(a["tries"], 1)  # failed tries so far, this one included
        delay = self.m * BASE_S[a["sev"]] * 2.0 ** min(k - 1, 5) * (1.0 + self.jitter * rng.random()) * (1.0 + 2.0 * (1.0 - self.p_hat))
        return t_end + window + min(delay, CAP_S[a["sev"]])

    def sf_for(self, a: dict, base_sf: int, tokens: float = 0.0) -> int:
        if self.sf_raise and a["sev"] >= 1 and a["tries"] >= FAIL_BEFORE_SF and base_sf < 12:
            new_air = airtime_ms(P.ALERT_LEN, base_sf + 1) / 1000.0
            if tokens - new_air >= 2.0 * new_air:
                return base_sf + 1
        return base_sf

    def observe(self, success: bool) -> None:
        self.p_hat = (1.0 - EWMA_W) * self.p_hat + EWMA_W * (1.0 if success else 0.0)


def grid() -> list[Scheduler]:
    """The 24 parameter combinations tuned on the tuning scenarios."""
    out = []
    for rho in (0.0, 0.2):
        for m in (0.5, 1.0, 2.0):
            for jitter in (0.0, 0.5):
                for sf in (False, True):
                    out.append(Scheduler(name=f"S_rho{rho:g}_m{m:g}_j{jitter:g}_sf{int(sf)}", rho=rho, m=m, jitter=jitter, sf_raise=sf))
    return out
