"""D1: compare the results.json entries of a prefix between the committed file (git HEAD) and the working file, by value, unit, origin and notes.

    python scripts/vf2_compare_prefix.py r6.fp.
Used in the fresh clone after a step was run again (record_many re-orders the file, so a text diff is not meaningful). Exit code 1 if any entry differs.
"""
import json
import subprocess
import sys
from pathlib import Path

prefix = sys.argv[1]
old = json.loads(subprocess.run(["git", "show", "HEAD:results/results.json"], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
new = json.loads(Path("results/results.json").read_text(encoding="utf-8"))
o = {e["name"]: e for e in old if e["name"].startswith(prefix)}
n = {e["name"]: e for e in new if e["name"].startswith(prefix)}
diff = [k for k in sorted(set(o) | set(n)) if k not in o or k not in n or any(json.dumps(o[k].get(f)) != json.dumps(n[k].get(f)) for f in ("value", "unit", "origin", "notes", "source_file"))]
print(f"{prefix}: {len(o)} committed entries, {len(n)} working entries, {len(diff)} differ")
for k in diff[:30]:
    print("DIFF", k, o.get(k, {}).get("value"), n.get(k, {}).get("value"))
sys.exit(1 if diff else 0)
