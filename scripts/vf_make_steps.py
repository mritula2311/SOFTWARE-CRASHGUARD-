"""V1.4: expand Makefile targets into one step per line for scripts/vf_run_steps.py.

usage: python scripts/vf_make_steps.py TARGET [TARGET ...] > steps.txt
Skipped: steps that query the network for literature (lit_search, lit_bib, a4_lit, r5_lit), `$(PY)` is dropped, `for i in 0 1 2 3 4; do ...; done` loops are expanded.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = ("lit_search", "lit_bib", "a4_lit", "r5_lit", "ingest_hardware")
text = (ROOT / "Makefile").read_text(encoding="utf-8")
out = []
for tgt in sys.argv[1:]:
    m = re.search(r"^" + re.escape(tgt) + r":\s*;?\s*(.*)$", text, re.M)
    if not m:
        sys.exit(f"no target {tgt}")
    cmd = m.group(1)
    cmd = re.sub(r"for i in (\d(?: \d)*); do (.*?); done", lambda mm: " && ".join(c.replace("$$i", i) for i in mm.group(1).split() for c in mm.group(2).split(" && ")), cmd)
    for part in cmd.split("&&"):
        part = part.strip().replace("$(PY) ", "").replace("python3 ", "")
        if not part or part.startswith("("):
            continue
        if any(k in part for k in SKIP):
            print("# skipped:", part, file=sys.stderr)
            continue
        out.append(part)
print("\n".join(out))
