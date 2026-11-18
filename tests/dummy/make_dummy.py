"""SYNTHETIC hardware logs for testing the merge path. DUMMY DATA: nothing from here goes into results/.

Usage: python tests/dummy/make_dummy.py [out_dir]   (default: tests/dummy)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SIDES = ["F", "R", "L", "Rt", "V"]
ANGLE = {"F": 0, "L": 90, "R": 180, "Rt": 270, "V": 0}


def make(out: Path, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    rows, eid = [], 1000

    def base(exp, label, side, sev, speed, dist, walls):
        nonlocal eid
        eid += 1
        crash = label == "crash"
        return dict(event_id=eid, experiment=exp, true_label=label, true_side=side, designed_severity=sev, speed_setting=speed,
                    distance_m=dist, walls=walls, rule_sev=int(crash and rng.random() < 0.9), ml_prob=float(np.clip(rng.normal(0.8 if crash else 0.2, 0.15), 0, 1)),
                    pred_side=side if rng.random() < 0.8 else rng.choice(SIDES), angle_deg=(ANGLE[side] + rng.normal(0, 15)) % 360,
                    peak_g=float(abs(rng.normal(1.5 + sev + speed * 0.5, 0.4))),
                    **{f"sw_{k}": int(crash and rng.random() < 0.7) for k in ["fl", "fr", "ml", "mr", "rl"]},
                    sw_first=int(rng.integers(0, 5)), sw_pre_edges=int(rng.integers(0, 3)),
                    classify_us=float(rng.normal(300, 30)), ml_us=float(rng.normal(60, 5)), verify_us=float(rng.normal(900, 50)),
                    airtime_ms=169.2, ack_rtt_ms=float(rng.normal(420, 40)), first_tx_to_ack_ms=float(rng.normal(450, 40)),
                    trigger_to_ack_ms=float(rng.normal(900, 80)), retries=int(rng.integers(0, 3)), delivered=int(rng.random() < 0.9),
                    rssi=float(rng.normal(-80, 5)), snr=float(rng.normal(8, 2)))

    for s in SIDES:  # H1: 10 hits on each of 4 sides + 10 vertical drops
        for _ in range(10):
            rows.append(base("H1", "crash", s, 1, 1, 0, 0))
    for _ in range(30):  # H2: 30 non-crashes (the H1 hits are the crashes)
        rows.append(base("H2", "non_crash", "F", 0, 1, 0, 0))
    for d, w in ((10, 0), (50, 0), (100, 0), (50, 1)):  # H3: 20 alerts each at 10, 50, 100 m, plus an optional wall
        for _ in range(20):
            rows.append(base("H3", "crash", "F", 2, 1, d, w))
    ev = pd.DataFrame(rows)
    ev.to_csv(out / "hw_events.csv", index=False)

    t = np.arange(280) * 10
    wr = []
    for r in ev[ev.experiment.isin(["H1", "H2"])].itertuples():
        a = rng.normal(0, 0.05, (280, 3))
        a[:, 2] += 1.0
        if r.true_label == "crash":
            a[100:112, 0] += rng.uniform(2, 5)
        g = rng.normal(0, 0.1, (280, 3))
        wr.append(pd.DataFrame(dict(event_id=r.event_id, t_ms=t, ax=a[:, 0], ay=a[:, 1], az=a[:, 2], gx=g[:, 0], gy=g[:, 1], gz=g[:, 2])))
    pd.concat(wr).to_csv(out / "hw_windows.csv", index=False)
    cases = [("forged", "reject"), ("tampered", "reject"), ("replay", "reject"), ("spoofed ACK", "reject"), ("base reboot", "reject"), ("ACK-lost retry", "re-ACK")]
    att = [dict(case=c, **{"try": k + 1}, expected=e, observed=("accept" if (c == "forged" and k == 2) else e)) for c, e in cases for k in range(3)]  # one deliberate mismatch
    pd.DataFrame(att).to_csv(out / "hw_attacks.csv", index=False)
    pd.DataFrame([dict(item="flash", bytes=900000), dict(item="RAM", bytes=40000)]).to_csv(out / "hw_memory.csv", index=False)


if __name__ == "__main__":
    make(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/dummy"))
