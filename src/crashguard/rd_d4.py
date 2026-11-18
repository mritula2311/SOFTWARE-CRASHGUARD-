"""D4: short provisional frame in the two-stage alert, H-D4a (V12 addendum B, section 10.3). ANALYTICAL on the stored de-duplicated test events of the 1% false-alarm operating point
(`results/tables/s6_events_seed42_a1.csv`, the events and decisions of `s6_early`; nothing is refitted).

Extra transmit airtime of a two-stage scheme over the single-stage alert, by spreading factor and loss per direction, with the tries counted as in `ar_r3.py` (at most 4 tries, a try succeeds with probability
(1 - p)^2 for the exchange):
    single = sum over events with a full-window alarm (F) of  A_alert * tries(p)
    two    = sum over (E and F): (A_prov + A_alert) * tries(p)  +  sum over (E and not F): A_prov * tries(p) + 3 * A_cancel  +  sum over (not E and F): A_alert * tries(p)
    extra  = two / single - 1
with A_x the time on air of the frame at the cell's spreading factor. Variants: R3 as registered (14-byte provisional flash), D4 (24-byte provisional frame with an 8-byte tag), and the 97-byte provisional
frame of the task wording. The CANCEL stays the 14-byte authenticated frame, three transmissions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard.lora import airtime_ms

EVENTS = "results/tables/s6_events_seed42_a1.csv"
TRIES = 4
CANCEL_TX = 3
A_CANCEL_BYTES = 14
ALERT = 97
VARIANTS = dict(r3_flash14=14, d4_prov24=24, prov97=97)
LIMIT = 0.25
NB = 2000


def exp_tries(p: float) -> float:
    q = (1 - p) ** 2
    return float(sum((1 - q) ** k for k in range(TRIES)))


def load_events(path: str = EVENTS) -> dict:
    ev = pd.read_csv(path)
    tr = ev[ev.triggered]
    return dict(E=tr.alarm_E.to_numpy(bool), F=tr.alarm_F.to_numpy(bool), y=tr.y.to_numpy(int), n=len(tr))


def per_event(E: np.ndarray, F: np.ndarray, sf: int, p: float, prov_bytes: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-event single-stage and two-stage airtime (s)."""
    a_al, a_pr, a_ca = (airtime_ms(b, sf) / 1000.0 for b in (ALERT, prov_bytes, A_CANCEL_BYTES))
    t = exp_tries(p)
    single = np.where(F, a_al * t, 0.0)
    two = np.where(E & F, (a_pr + a_al) * t, 0.0) + np.where(E & ~F, a_pr * t + CANCEL_TX * a_ca, 0.0) + np.where(~E & F, a_al * t, 0.0)
    return single, two


def ratio(single: np.ndarray, two: np.ndarray) -> float:
    return float(two.sum() / single.sum() - 1.0)


def cell_test(ev: dict, sf: int, p: float, prov_bytes: int, seed: int = 42, nb: int = NB) -> dict:
    """Bootstrap over events: point estimate, 95% interval, one-sided upper 95% bound and the p-value of H0: extra airtime >= 0.25."""
    single, two = per_event(ev["E"], ev["F"], sf, p, prov_bytes)
    n = len(single)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, (nb, n))
    b = two[idx].sum(1) / single[idx].sum(1) - 1.0
    return dict(sf=sf, p=p, pt=ratio(single, two), lo=float(np.quantile(b, 0.025)), hi=float(np.quantile(b, 0.975)), ub95=float(np.quantile(b, 0.95)), p_value=float((b >= LIMIT).sum() + 1) / (nb + 1))


def run_grid(ev: dict, sfs: list[int], losses: list[float]) -> dict:
    out = {}
    for name, nbytes in VARIANTS.items():
        out[name] = {f"sf{sf}_p{int(round(p * 100))}": cell_test(ev, sf, p, nbytes) for sf in sfs for p in losses}
    return out
