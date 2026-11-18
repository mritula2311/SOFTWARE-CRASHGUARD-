"""Round 7 event engine (docs/02_preregistration/PREREGISTRATION_V18.md section 2.1): one two-stage alert event of one node with a duty layer and two retry policies.

Policies: ``old`` is the shipped policy (FIFO queue per event: flash up to 4 tries, then the confirm up to 4 tries or three unconfirmed cancels; no priority, no withdrawal). ``reserved`` is the
reserved-budget policy (class H frames may spend the whole allowance; class L frames, that is every flash try, may not leave less than the reserve R; under a per-transmission off-time a class-L frame must end
its off-time by the time the follow-up is due; not-yet-started flash tries are withdrawn when the follow-up is ready). The old path with no duty layer reproduces the attempt counts, outcomes and airtime of
``r3_t1.r3_event`` and ``r6_micro.micro_event``; ``tests/test_r7_engine.py`` checks it draw for draw.

Duty models: ``none``; ``H`` (trailing-hour allowance in seconds, exact sliding window); ``T`` (off-time of ``off_factor`` x airtime after every frame: 9 for a 10% per-transmission reading).
Evidence labels: SIMULATED (A1) and TRACE_DRIVEN (A2); the module itself is a model.
"""
from __future__ import annotations

import collections
import math
from dataclasses import dataclass

from crashguard.lora import airtime_ms

T_F = 1.808  # the full decision is ready (1.8 s window plus 8 ms), ar_r3.py and xsim_alert.cc R3_FINAL_S
COMPUTE = 0.008
CANCEL_GAP = 0.3
TRIES = 4
CANCEL_COPIES = 3
PEND_S = 30.0
W_NS3 = 0.32  # receive windows after a frame in the ns-3 application (RX2 0.2 s plus 0.12 s)
MICRO13 = 13
INF = math.inf


def air(n_bytes: int, sf: int) -> float:
    return airtime_ms(n_bytes, sf) / 1000.0


class Duty:
    """Duty layer of one node. ``earliest`` gives the first start >= t that the model permits for a frame of airtime ``a``."""

    def __init__(self, model: str = "none", allowance_s: float = 0.0, off_factor: float = 9.0):
        assert model in ("none", "H", "T")
        self.model, self.allow, self.off_factor = model, allowance_s, off_factor
        self.h: collections.deque = collections.deque()
        self.sum = 0.0
        self.off_until = -INF

    def used(self, t: float) -> float:
        while self.h and self.h[0][0] <= t - 3600.0 + 1e-9:
            self.sum -= self.h.popleft()[1]
        return max(self.sum, 0.0)

    def remaining(self, t: float) -> float:
        return INF if self.model != "H" else self.allow - self.used(t)

    def earliest(self, t: float, a: float) -> float:
        if self.model == "none":
            return t
        if self.model == "T":
            return max(t, self.off_until)
        s, idx, tt = self.used(t), 0, t  # prune up to the real time t only; the look-ahead below does not modify the history
        while True:
            while idx < len(self.h) and self.h[idx][0] <= tt - 3600.0 + 1e-9:
                s -= self.h[idx][1]
                idx += 1
            if s + a <= self.allow + 1e-12:
                return tt
            if idx >= len(self.h):
                return INF  # a frame larger than the allowance never fits
            tt = self.h[idx][0] + 3600.0 + 1e-9

    def record(self, start: float, a: float) -> None:
        self.h.append((start, a))
        self.sum += a
        self.off_until = start + a * (1.0 + self.off_factor)


@dataclass
class Spec:
    E: bool
    F: bool
    tE: float  # decision time of the early exit (s after the trigger)
    sf: int = 7
    policy: str = "old"
    k: int = 4
    micro: int | None = None  # bytes of the micro frame (None: scheme R3, no micro-confirm)
    win: float = W_NS3
    pend: float = PEND_S
    reserve_s: float | None = None  # overrides R (tests)
    n_res: int = 1  # post-hoc variant (not preregistered): the reserve covers the follow-ups of n_res events, R = n_res k A97 + A_M; V18 fixes n_res = 1

    def reserve(self) -> float:
        if self.reserve_s is not None:
            return self.reserve_s
        return self.n_res * self.k * air(97, self.sf) + air(self.micro or MICRO13, self.sf)


def run_event(spec: Spec, duty: Duty, t0: float, uplink_ok, ack_ok, radio_free: float = -INF) -> dict:  # noqa: PLR0912, PLR0915
    """One event triggered at absolute time ``t0``. ``uplink_ok(i)`` tells whether the i-th transmission of the event reaches the base; ``ack_ok(i)`` is asked only for a received confirmed frame and tells whether the
    ACK reaches the node (an attacker that suppresses ACKs returns False). Returns the transmissions and the quantities of the preregistration."""
    sf, R = spec.sf, spec.reserve()
    reserved = spec.policy == "reserved"
    t_pend = t0 + T_F
    tx: list[tuple] = []
    out = dict(arr_f=INF, arr_c=INF, n_f=0, n_c=0, air=0.0, flash_acked=False, follow_start=INF, pend=t_pend, cancel_lost=None, skipped_flash=0, flash_blocked=False)
    i = 0
    rf = radio_free

    def send(kind: str, nbytes: int, ready: float, confirmed: bool, cls: str, t_limit: float = INF) -> tuple[bool, float, bool]:
        """One transmission. Returns (sent, start, received). Class L under the reserved policy is checked here and may be withdrawn."""
        nonlocal i, rf
        a = air(nbytes, sf)
        start = duty.earliest(max(ready, rf), a)
        if reserved and cls == "L":
            if duty.model == "T":
                if start + a * (1.0 + duty.off_factor) > t_pend + 1e-9:
                    return False, start, False
            else:
                if start > t_pend + 1e-9:
                    return False, start, False
                if duty.model == "H" and duty.remaining(start) - a < R - 1e-12:
                    return False, start, False
        if not math.isfinite(start):
            return False, start, False
        duty.record(start, a)
        rf = start + a + spec.win
        ok = bool(uplink_ok(i))
        tx.append((kind, start, a, ok))
        out["air"] += a
        i += 1
        return True, start, ok

    # ---- flash stage (class L)
    flash_ack_t = None
    if spec.E:
        ready = t0 + spec.tE + COMPUTE
        for _ in range(TRIES):
            sent, st, ok = send("flash", 14, ready, True, "L")
            if not sent:
                out["flash_blocked"] = True
                break
            out["n_f"] += 1
            if ok and out["arr_f"] == INF:
                out["arr_f"] = st + air(14, sf)
            if ok and ack_ok(i - 1):
                out["flash_acked"] = True
                flash_ack_t = st + air(14, sf) + spec.win
                break
    # ---- follow-up stage (class H)
    if spec.F:
        for c in range(TRIES):
            a_full = 97
            ready = t_pend
            start_probe = duty.earliest(max(ready, rf), air(a_full, sf))
            micro = spec.micro is not None and flash_ack_t is not None and (start_probe - flash_ack_t) <= spec.pend
            nb = spec.micro if micro else a_full
            sent, st, ok = send("confirm", nb, ready, True, "H")
            if not sent:
                break
            out["n_c"] += 1
            out["follow_start"] = min(out["follow_start"], st)
            if ok and out["arr_c"] == INF:
                out["arr_c"] = st + air(nb, sf)
            if ok and ack_ok(i - 1):
                break
    elif spec.E:
        cl = True
        for c in range(CANCEL_COPIES):
            ready = t_pend + CANCEL_GAP * c
            micro = spec.micro is not None and flash_ack_t is not None and (max(ready, rf) - flash_ack_t) <= spec.pend
            nb = spec.micro if micro else 14
            sent, st, ok = send("cancel", nb, ready, False, "H")
            if not sent:
                break
            out["n_c"] += 1
            out["follow_start"] = min(out["follow_start"], st)
            cl = cl and not ok
        out["cancel_lost"] = cl
    out["end"] = rf
    out["tx"] = tx
    out["follow_delay"] = (out["follow_start"] - t_pend) if math.isfinite(out["follow_start"]) else INF
    return out


def lone_event(spec: Spec, duty: Duty, t0: float, uplink_ok, ack_ok, radio_free: float = -INF) -> dict:
    """E = 0, F = 1: only the full alert (class H)."""
    return run_event(Spec(False, True, 0.0, spec.sf, spec.policy, spec.k, spec.micro, spec.win, spec.pend, spec.reserve_s, spec.n_res), duty, t0, uplink_ok, ack_ok, radio_free)
