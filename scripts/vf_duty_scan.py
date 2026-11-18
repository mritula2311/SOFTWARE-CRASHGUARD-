"""V3.3: scan every stored ns-3 run for a duty-cycle breach (DUTY line: airtime used, limit, both in seconds per hour). Keys vf.duty.*"""
from pathlib import Path

from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[1]
ent = []
for d in ["r3ns3_out", "xsim_out", "a4_ns3_out", "r5_l4_out"]:
    n = viol = empty = 0
    for f in (ROOT / "data" / "processed" / d).rglob("*.txt"):
        n += 1
        txt = f.read_text(errors="replace")
        if not txt.strip():
            empty += 1
            continue
        for line in txt.splitlines():
            t = line.split()
            if t and t[0] == "DUTY" and len(t) >= 3 and float(t[1]) > float(t[2]) + 1e-9:
                viol += 1
    print(d, n, empty, viol)
    for nm, v in [("runs", n), ("empty_runs", empty), ("breaches", viol)]:
        ent.append(dict(name=f"vf.duty.{d}.{nm}", value=v, unit="runs", origin="SIMULATED", source_file="scripts/vf_duty_scan.py", notes="stored ns-3 run files; an empty file is a run that crashed inside the module"))
record_many(ent, purge_prefixes=("vf.duty.",))
