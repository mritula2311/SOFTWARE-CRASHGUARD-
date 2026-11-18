"""D3: gated slotted retries with an overheard burst-size estimate (docs/02_preregistration/PREREGISTRATION_V12.md addendum B, section 10.2). Pure logic, no simulator import, so that the simulator hook,
the unit and property tests and the firmware-path implementation (D6, C) all use the same definitions.

A vehicle that has to retry a Critical alert and has overheard at least ``thr3`` other vehicles in the last 10 s picks a slot on a time grid shared through GPS time: S = clip(ceil(N_hat / m), 2, S_max)
slots of length (time on air of the alert at the retry's spreading factor + guard), epoch = S slots, epoch counter e = floor((t - own clock offset) / epoch length), slot = SHA-256(e as 4 bytes
little-endian || vehicle id as 2 bytes little-endian) mod S (the "GPS second" of the preregistration is replaced by the epoch counter derived from GPS time, so that epochs shorter than a second do not share
a slot; logged in DECISIONS.md before any DEV run). A slot only delays a retry: it is never later than the class deadline (else the D1 time is used), and it never stops an alert.
"""
from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass

GUARD_S = 0.02
EPOCH_CAP_S = 5.0
EPS_S = 0.005  # clock offset bound (as GS-CA)
S_MAX = 12
HEARD_WINDOW_S = 10.0


@dataclass(frozen=True)
class D3Params:
    thr3: int = 3  # distinct other vehicles overheard in the last 10 s needed to switch the slots on
    m: float = 2.0  # vehicles per slot
    alt: bool = True  # alternate spreading factor on even retries


def n_slots(n_hat: int, m: float, slot_s: float) -> int:
    """S = clip(ceil(N_hat / m), 2, S_max) with S limited so that S * slot <= the 5 s epoch cap (at least 2 slots)."""
    s_cap = max(2, min(S_MAX, int(math.floor(EPOCH_CAP_S / slot_s + 1e-9))))
    return int(min(max(2, math.ceil(n_hat / m - 1e-9)), s_cap))


def slot_index(epoch: int, vehicle_id: int, s: int) -> int:
    h = hashlib.sha256(struct.pack("<IH", epoch & 0xFFFFFFFF, vehicle_id & 0xFFFF)).digest()
    return int.from_bytes(h, "big") % s


def active(p: D3Params, n_heard_others: int, cls: int) -> bool:
    return cls == 3 and n_heard_others >= p.thr3


def alt_sf(j: int, sf_d1: int) -> int:
    """Spreading factor of retry j (j >= 1): the D1 choice on odd j, one step up on even j, at most 12."""
    return min(12, sf_d1 + 1) if (j % 2 == 0 and j >= 2) else sf_d1


def slot_time(p: D3Params, n_hat: int, vehicle_id: int, t_min: float, offset_s: float, air_alert_s: float, deadline_end: float) -> float | None:
    """Start time of the chosen slot: the first slot of the vehicle's hashed index whose start is at or after ``t_min`` (the D1 retry time), looking at most two epochs ahead. None when it would end after
    ``deadline_end`` (absolute class deadline): the caller then keeps the D1 time. ``n_hat`` counts the vehicle itself."""
    slot = air_alert_s + GUARD_S
    s = n_slots(n_hat, p.m, slot)
    ep = s * slot
    e0 = int(math.floor((t_min - offset_s) / ep + 1e-12))
    for e in (e0, e0 + 1, e0 + 2):
        t = e * ep + slot_index(e, vehicle_id, s) * slot + offset_s
        if t >= t_min - 1e-12:
            return t if t + air_alert_s <= deadline_end + 1e-12 else None
    return None
