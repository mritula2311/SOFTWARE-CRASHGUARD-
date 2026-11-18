"""X1.2: calibration of the custom simulator against ns-3 (lorawan module) on baseline scenarios (docs/02_preregistration/PREREGISTRATION_V12.md section 8). Keys ``rd.x1.*``.

Scenario: one gateway, N vehicles uniform in a disc of radius 3,000 m, one spreading factor, 97-byte frames every 30 s on average, unconfirmed or confirmed uplink, one transmission and no retry, loss only from path loss,
shadowing, fading, sensitivity and collisions (no extra random loss). The ns-3 program is `xsim/ns3/xsim_calib.cc`; it is run in WSL. The custom side uses `world_sim.simulate` with the severity-less single-try policy.

    python -m crashguard.rd_xsim custom      # custom simulator cells, writes data/processed/rd_xsim_custom.json
    python -m crashguard.rd_xsim ns3 <label> # ns-3 cells (needs the build in WSL), writes data/processed/rd_xsim_ns3_<label>.json
    python -m crashguard.rd_xsim table <label>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

NS = (1, 10, 50, 100)
SFS = (7, 9)
MODES = ("unconfirmed", "confirmed")
RADIUS_M = 3000.0
PERIOD_S = 30.0
OUT = Path("data/processed")


SENS_SHIPPED = {7: -130.0, 8: -132.5, 9: -135.0, 10: -137.5, 11: -140.0, 12: -142.5}  # ns-3 shipped gateway sensitivities (setting b of V12 11.3)


def custom_cell(n: int, sf: int, confirmed: bool, hours: int = 60, seed0: int = 77000, shipped: bool = False) -> dict:
    from crashguard import fin_g as G
    from crashguard import world_sim as W

    sent = rx = ack = 0
    for h in range(hours):
        if confirmed:
            cfg = W.SCfg(n=n, sf=sf, policy="none", seed=seed0, hour=h, duty=1.0, hb_period_s=1e9, hb_bytes=97, rate_per_car_h=3600.0 / PERIOD_S, p_up=0.0, p_down=0.0, label=f"x1c_{n}_{sf}", world=dict(G.WORLD, **(dict(sens=SENS_SHIPPED) if shipped else {})),
                         true_pool=np.array([3]), assigned_pool=np.array([3]), crash_pool=np.array([0.0]))
            diag: list = []
            W.simulate(cfg, diag=diag)
            al = [a for a in diag if a["kind"] == "crash" and a["transmitted"]]
            sent += len(al)
            rx += sum(a["t_rx"] is not None for a in al)
            ack += sum(a["acked"] for a in al)
        else:
            cfg = W.SCfg(n=n, sf=sf, policy="none", seed=seed0, hour=h, duty=1.0, hb_period_s=PERIOD_S, hb_bytes=97, rate_per_car_h=0.0, p_up=0.0, p_down=0.0, label=f"x1u_{n}_{sf}", world=dict(G.WORLD, **(dict(sens=SENS_SHIPPED) if shipped else {})))
            r = W.simulate(cfg)
            sent += int(r["hb_sent"])
            rx += int(r["hb_rx"])
    return dict(n=n, sf=sf, mode="confirmed" if confirmed else "unconfirmed", sent=sent, received=rx, acked=ack, pdr=rx / max(sent, 1), ack_share=(ack / max(sent, 1)) if confirmed else None)


RUN_SCRIPT = """#!/bin/bash
# usage: run_cell.sh nDevices sf confirmed radius simTime period runs
cd ~/ns3work/ns-3-dev
for r in $(seq 1 $7); do
  ./build/scratch/ns3.48-xsim_calib-optimized --nDevices=$1 --sf=$2 --confirmed=$3 --radius=$4 --simTime=$5 --period=$6 --seed=$r --sensShipped=${8:-0}
done
"""


def ns3_cell(n: int, sf: int, confirmed: bool, runs: int = 60, sim_time: int = 3600, shipped: bool = False) -> dict:
    """``runs`` ns-3 runs (seeds 1 to runs) in one WSL call; each run has its own random placement and shadowing draw."""
    subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", "cat > ~/ns3work/run_cell.sh"], input=RUN_SCRIPT.encode("utf-8"), capture_output=True)  # bytes: Windows text mode would add carriage returns
    cmd = f"bash ~/ns3work/run_cell.sh {n} {sf} {int(confirmed)} {RADIUS_M:g} {sim_time} {PERIOD_S:g} {runs} {int(shipped)}"
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-lc", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.replace(chr(0), "")
    found = re.findall(r"RESULT\s+([\d.]+)\s+([\d.]+)", out)
    if len(found) < 0.9 * runs:
        raise RuntimeError(f"expected about {runs} RESULT lines, got {len(found)}: {out[-300:]}")  # a few runs may end without a result line; the number that did is recorded
    sent = sum(int(float(x)) for x, _ in found)
    rx = sum(int(float(y)) for _, y in found)
    return dict(n=n, sf=sf, mode="confirmed" if confirmed else "unconfirmed", sent=sent, received=rx, pdr=rx / max(sent, 1), runs=runs, runs_ok=len(found))


def main() -> None:
    what = sys.argv[1]
    if what == "custom":
        rows = [custom_cell(n, sf, c == "confirmed") for n in NS for sf in SFS for c in MODES]
        (OUT / "rd_xsim_custom.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    elif what == "supp":  # supplementary, larger samples for the single-vehicle cells (placement dominates the variance); reported next to, never in place of, the main table
        rows_c = [custom_cell(1, sf, c == "confirmed", hours=300) for sf in SFS for c in MODES]
        rows_n = [ns3_cell(1, sf, c == "confirmed", runs=300) for sf in SFS for c in MODES]
        (OUT / "rd_xsim_supp.json").write_text(json.dumps(dict(custom=rows_c, ns3=rows_n), indent=1), encoding="utf-8")
    elif what == "custom_b":  # setting (b): shipped sensitivities in both simulators
        rows = [custom_cell(n, sf, c == "confirmed", shipped=True) for n in NS for sf in SFS for c in MODES]
        (OUT / "rd_xsim_custom_b.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    elif what == "ns3_b":
        rows = [ns3_cell(n, sf, c == "confirmed", shipped=True) for n in NS for sf in SFS for c in MODES]
        (OUT / "rd_xsim_ns3_b.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    elif what == "ns3":
        label = sys.argv[2]
        rows = [ns3_cell(n, sf, c == "confirmed") for n in NS for sf in SFS for c in MODES]
        (OUT / f"rd_xsim_ns3_{label}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
