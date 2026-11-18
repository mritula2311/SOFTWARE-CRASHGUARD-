"""Counts of PASS, FAIL, FIXED, NOT_RUN and BLOCKED per block (D0 to D7) from docs/04_audits/DELTA_VERIFICATION.md. Prints a Markdown table."""
import collections
import re
from pathlib import Path

t = (Path(__file__).resolve().parents[1] / "docs/04_audits/DELTA_VERIFICATION.md").read_text(encoding="utf-8")
c = collections.defaultdict(collections.Counter)
for ln in t.splitlines():
    cells = [x.strip() for x in ln.strip().strip("|").split(" | ")]
    if len(cells) == 5 and re.match(r"D\d+", cells[0]) and cells[3] in ("PASS", "FAIL", "FIXED", "NOT_RUN", "BLOCKED"):
        c[re.match(r"D\d+", cells[0]).group(0)][cells[3]] += 1
cols = ("PASS", "FAIL", "FIXED", "NOT_RUN", "BLOCKED")
rows = ["| Block | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
tot = collections.Counter()
for b in sorted(c, key=lambda x: int(x[1:])):
    rows.append(f"| {b} | " + " | ".join(str(c[b][k]) for k in cols) + " |")
    tot.update(c[b])
rows.append("| all | " + " | ".join(str(tot[k]) for k in cols) + " |")
print("\n".join(rows))
