"""V1.4: prepare the fresh clone for the later-round targets.

usage: python scripts/vf_clone_prep.py <clone root> <original root>
1. Saves the clone's committed results.json as results/results_committed.json.
2. Removes the entries of the rounds that are recomputed (prefixes r5., a4., r3., pp., rd.) from the clone's results.json, because their held-out steps refuse to run when their keys already exist (the held-out run is made once).
   The committed frozen files (results/tables/*_frozen.json, hashes of code and parameters) are kept: a step stops if the code differs from the frozen one.
3. Copies the stored raw outputs of the network simulator runs (they are simulator output files, not summaries) from the original data/processed, so that ns-3 is not run for every step again;
   100 of them were repeated separately (docs/03_results/VF_NS3_RERUN.md).
"""
import json
import shutil
import sys
from pathlib import Path

clone, orig = Path(sys.argv[1]), Path(sys.argv[2])
res = clone / "results" / "results.json"
shutil.copy(res, clone / "results" / "results_committed.json")
R = json.loads(res.read_text(encoding="utf-8"))
PRE = tuple(sys.argv[3:]) or ("r5.", "a4.", "r3.", "pp.", "rd.")
keep = [e for e in R if not e["name"].startswith(PRE)]
res.write_text(json.dumps(keep), encoding="utf-8")
print("entries", len(R), "kept", len(keep), "removed", len(R) - len(keep))
for d in ["r3ns3_out", "a4_ns3_out", "r5_l4_out", "xsim_out"]:
    src = orig / "data" / "processed" / d
    dst = clone / "data" / "processed" / d
    if src.exists() and not dst.exists():
        shutil.copytree(src, dst)
        print("copied", d)
