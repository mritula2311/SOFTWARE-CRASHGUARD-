"""V2.3: rerun the exhaustive enumerations without writing any stored key and compare with results.json.
 - F15: r3_t2_timed.main() is run on a copy of results.json (the module writes r3.t2.timed.*; the file is restored afterwards and compared key by key)
 - L7b: r5_l7.enumerate_all()   - L8a: r5_l8.explore()
usage: python scripts/vf_enum_rerun.py"""
import json
import shutil
import time
from pathlib import Path

from crashguard import r5_l7, r5_l8
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results" / "results.json"
d0 = {e["name"]: e["value"] for e in json.loads(RES.read_text(encoding="utf-8"))}
out, ent = [], []

t = time.time()
r = r5_l7.enumerate_all()
ok7 = r["n_sequences"] == d0["r5.l7.b.n_sequences"] and all(r["violations"][k] == d0[f"r5.l7.b.violations.{k}"] for k in r["violations"]) and r["n_gap_above_window"] == d0["r5.l7.b.n_gap_above_window"]
out.append(("L7b", f"{r['n_sequences']} sequences, violations {r['violations']}", "stored" if ok7 else "DIFFERENT", round(time.time() - t, 1)))
t = time.time()
a = r5_l8.explore()
ok8 = a["max_high"] == d0["r5.l8.a.max_high_confidence_forwards"] and a["states_visited"] == d0["r5.l8.a.states_visited"] and a["max_low"] == d0["r5.l8.a.max_low_confidence_forwards"]
out.append(("L8a", f"max high {a['max_high']}, max low {a['max_low']}, states {a['states_visited']}", "stored" if ok8 else "DIFFERENT", round(time.time() - t, 1)))

bak = RES.with_suffix(".json.vfbak")
shutil.copy(RES, bak)
t = time.time()
from crashguard import r3_t2_timed as T2  # noqa: E402

T2.main()
d1 = {e["name"]: e["value"] for e in json.loads(RES.read_text(encoding="utf-8"))}
shutil.copy(bak, RES)
bak.unlink()
diff = [k for k in d0 if k.startswith("r3.t2.timed") and (k not in d1 or d1[k] != d0[k])]
out.append(("F15", f"{sum(1 for k in d0 if k.startswith('r3.t2.timed'))} keys, duty runs {d1.get('r3.t2.timed.duty.runs')}, breaches {d1.get('r3.t2.timed.duty.breaches')}", "stored" if not diff else f"DIFFERENT {diff[:3]}", round(time.time() - t, 1)))
for name, det, res, sec in out:
    print(name, det, res, sec, "s")
    ent.append(dict(name=f"vf.enum.{name}.reproduced", value=int(res == "stored"), unit="bool", origin="FORMAL", source_file="scripts/vf_enum_rerun.py", notes=f"{det}; {sec} s"))
record_many(ent, purge_prefixes=("vf.enum.",))
