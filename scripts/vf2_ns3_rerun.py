"""D1: rerun round-6 ns-3 cells (policy r6m, and r3s and r3t beside it) and compare every output file byte for byte with the stored one.

    PYTHONPATH=src python scripts/vf2_ns3_rerun.py [seeds per cell, default 15]

Cells: SF7 and SF9, both sensing settings, extra loss 0.3, seeds 1..N, policies r3s, r3t, r6m (pending lifetime of the freeze). The application is deterministic for a given seed and arguments,
so a rerun in the same build must reproduce the stored file. Outputs go to data/processed/vf2_ns3_out (git-ignored); the summary goes to results/tables/vf2_ns3_rerun.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard import r6_micro as M  # noqa: E402
from crashguard import rd_firmware as F  # noqa: E402

OUT = ROOT / "data" / "processed" / "vf2_ns3_out"
JOBS = ROOT / "data" / "processed" / "vf2_ns3_jobs"


def main() -> None:
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    pend = json.loads((ROOT / "results" / "tables" / "r6_frozen.json").read_text(encoding="utf-8"))["r1"]["params"]["pend_s"]
    OUT.mkdir(parents=True, exist_ok=True)
    JOBS.mkdir(parents=True, exist_ok=True)
    pairs, jobs = [], []
    for sf in M.SFS:
        for st, sh in M.SETTINGS.items():
            for s in range(1, n_seeds + 1):
                for pol, pe, src in (("r3s", None, M.R3OUT), ("r3t", None, M.R3OUT), ("r6m", pend, M.OUT)):
                    stored = M.fname_new(src, sf, st, 0.3, pol, s, pe)
                    new = OUT / stored.name
                    jobs.append((new, M.args_for(sf, sh, 0.3, s, pol, pe)))
                    pairs.append((f"sf{sf} {st} p0.3 {pol}", stored, new))
    (JOBS / "job.sh").write_bytes(M.JOB_SCRIPT.replace("{NS}", M.NS_BIN).encode("utf-8"))
    workers = 12
    procs = []
    for k in range(workers):
        ch = jobs[k::workers]
        if not ch:
            continue
        jf = JOBS / f"jobs_{k}.txt"
        jf.write_bytes(("\n".join(f"{F.wsl_path(o)}|{a}" for o, a in ch) + "\n").encode("utf-8"))
        procs.append(subprocess.Popen(["wsl", "-d", "Ubuntu", "--", "bash", F.wsl_path(JOBS / "job.sh"), F.wsl_path(jf)], env={**os.environ, "MSYS_NO_PATHCONV": "1"}))
    for p in procs:
        p.wait()
    by: dict[str, list[int]] = {}
    for cell, stored, new in pairs:
        c = by.setdefault(cell, [0, 0, 0, 0])
        c[0] += 1
        a = stored.read_bytes() if stored.exists() else None
        b = new.read_bytes() if new.exists() else None
        c[1] += int(a is not None and a == b)
        c[2] += int(a is not None and len(a) == 0)
        c[3] += int(b is not None and len(b) == 0)
    tot = [sum(v[i] for v in by.values()) for i in range(4)]
    (ROOT / "results" / "tables" / "vf2_ns3_rerun.json").write_text(json.dumps(dict(pend_s=pend, seeds_per_cell=n_seeds, cells=by, total=dict(runs=tot[0], identical=tot[1], stored_empty=tot[2], rerun_empty=tot[3])), indent=1), encoding="utf-8")
    for k, v in by.items():
        print(k, v)
    print("total runs", tot[0], "identical", tot[1], "stored empty", tot[2], "rerun empty", tot[3])


if __name__ == "__main__":
    main()
