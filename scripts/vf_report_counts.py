"""V12: counts of PASS, FAIL, FIXED and NOT_RUN per block (V0 to V12) from docs/04_audits/FINAL_VERIFICATION.md. Prints a Markdown table."""
import collections
import re
from pathlib import Path

t = (Path(__file__).resolve().parents[1] / "docs/04_audits/FINAL_VERIFICATION.md").read_text(encoding="utf-8")
c = collections.defaultdict(collections.Counter)
mins = collections.Counter()
for ln in t.splitlines():
    cells = [x.strip() for x in ln.strip().strip("|").split(" | ")]
    if len(cells) == 6 and re.match(r"V\d+", cells[0]) and cells[3] in ("PASS", "FAIL", "FIXED", "NOT_RUN"):
        blk = re.match(r"V\d+", cells[0]).group(0)
        c[blk][cells[3]] += 1
        try:
            mins[blk] += float(cells[5])
        except ValueError:
            pass
rows = ["| Block | PASS | FAIL | FIXED | NOT_RUN | Minutes |", "|---|---|---|---|---|---|"]
tot = collections.Counter()
for b in sorted(c, key=lambda x: int(x[1:])):
    rows.append(f"| {b} | {c[b]['PASS']} | {c[b]['FAIL']} | {c[b]['FIXED']} | {c[b]['NOT_RUN']} | {int(mins[b])} |")
    tot.update(c[b])
rows.append(f"| all | {tot['PASS']} | {tot['FAIL']} | {tot['FIXED']} | {tot['NOT_RUN']} | {int(sum(mins.values()))} |")
print("\n".join(rows))
