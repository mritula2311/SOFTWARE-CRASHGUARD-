"""Run a list of pipeline steps one after another in the fresh clone and log time and exit code of each.

Usage (from the clone root):  python scripts/vf_run_steps.py LOGFILE STEP [STEP ...]
A STEP is `-m module args` or `script.py args` or `-c "code"` written as one quoted string.
The interpreter is the one running this script. A failing step is recorded and the run continues.
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time


def main() -> int:
    log, steps = sys.argv[1], sys.argv[2:]
    bad = 0
    for s in steps:
        t0 = time.time()
        args = shlex.split(s, posix=False) if not s.startswith("-c ") else ["-c", s[3:].strip().strip('"')]
        r = subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        rec = dict(step=s, rc=r.returncode, seconds=round(time.time() - t0, 1), tail=(r.stdout + r.stderr)[-1500:])
        with open(log, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{r.returncode}] {s}  {rec['seconds']} s", flush=True)
        bad += r.returncode != 0
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
