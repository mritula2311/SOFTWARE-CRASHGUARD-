"""V1.4: classify the tracked files that differ after the fresh run (git working tree of the clone against its commit).
usage: python scripts/vf_diff_classify.py <clone root>"""
import collections
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

clone = Path(sys.argv[1])
files = [ln[3:].strip().strip('"') for ln in subprocess.run(["git", "status", "--short"], cwd=clone, capture_output=True, text=True).stdout.splitlines() if not ln.startswith("??")]


def old(p):
    return subprocess.run(["git", "show", f"HEAD:{p}"], cwd=clone, capture_output=True).stdout


def num_equal(a, b, tol=1e-6):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(num_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(num_equal(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(a - b) <= tol * max(1.0, abs(a))
    return a == b


cat = collections.defaultdict(list)
for f in files:
    p = clone / f
    ext = p.suffix.lower()
    if ext in (".png", ".pdf"):
        cat["figure bytes (rendering metadata)"].append(f)
    elif ext == ".csv":
        try:
            import io

            a = pd.read_csv(io.BytesIO(old(f)))
            b = pd.read_csv(p)
            same = a.shape == b.shape and all((num_equal(a[c].tolist(), b[c].tolist()) if a[c].dtype != object else a[c].equals(b[c])) for c in a.columns)
            cat["csv numerically equal (1e-6)" if same else "csv DIFFERENT"].append(f)
        except Exception as e:  # noqa: BLE001
            cat["csv unreadable"].append(f"{f} ({type(e).__name__})")
    elif ext == ".json":
        try:
            same = num_equal(json.loads(old(f)), json.loads(p.read_text(encoding="utf-8")))
            cat["json numerically equal" if same else "json DIFFERENT"].append(f)
        except Exception as e:  # noqa: BLE001
            cat["json unreadable"].append(f"{f} ({type(e).__name__})")
    elif ext == ".md":
        cat["markdown (generated document)"].append(f)
    else:
        cat["other"].append(f)
for k, v in cat.items():
    print(k, len(v))
    if "DIFFERENT" in k or k == "other" or "unreadable" in k:
        for x in v:
            print("   ", x)
(clone / "_diff_classes.json").write_text(json.dumps(cat), encoding="utf-8")
