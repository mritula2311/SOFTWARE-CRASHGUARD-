"""E gate: every results.json entry of the base tag still exists with the same value, unit, origin and notes; list the entries added since.

    python scripts/verify_keys_unchanged.py [tag]      (default journal-v1)
Exit code 1 if any old entry changed or vanished. New keys (prefixes r., ph., q., pa.) are allowed and counted.
"""
import json
import subprocess
import sys
from pathlib import Path

tag = sys.argv[1] if len(sys.argv) > 1 else "journal-v1"
old = json.loads(subprocess.run(["git", "show", f"{tag}:results/results.json"], capture_output=True, text=True, encoding="utf-8", check=True).stdout)
new = json.loads(Path("results/results.json").read_text(encoding="utf-8"))
nm = {e["name"]: e for e in new}
bad = [e["name"] for e in old if e["name"] not in nm or any(json.dumps(nm[e["name"]].get(k)) != json.dumps(e.get(k)) for k in ("value", "unit", "origin", "notes", "source_file"))]
old_names = {e["name"] for e in old}
added = [k for k in nm if k not in old_names]
pre = {}
for k in added:
    p = k.split(".")[0] + "."
    pre[p] = pre.get(p, 0) + 1
print(f"{len(old)} entries at {tag}; {len(bad)} changed or missing; {len(added)} added {pre}")
for b in bad[:20]:
    print("CHANGED", b)
sys.exit(1 if bad else 0)
