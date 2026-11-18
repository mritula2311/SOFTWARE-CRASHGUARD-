"""V8.1: list every sentence of main.tex and of the supplement (own text and generated conversions) that uses a claim word. usage: python scripts/vf_claim_scan.py"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = re.compile(r"\b(improv\w*|outperform\w*|better|robust\w*|secur\w*|proved|prove[sd]?|verif\w*|validat\w*|significan\w*|guarantee\w*|real-time)\b", re.I)
files = [ROOT / "paper/main.tex", ROOT / "paper/supplement.tex"] + sorted((ROOT / "paper/generated/supp").glob("*.tex"))
if "strong" in sys.argv:
    WORDS = re.compile(r"(?i)(outperform|robust|significan|guarantee|real-time|improv|better)")
rows = []
for f in files:
    t = re.sub(r"(?<!\\)%.*", "", f.read_text(encoding="utf-8"))
    t = re.sub(r"\\(begin|end)\{[^}]*\}", " ", t)
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\\])", t):
        s = " ".join(s.split())
        m = WORDS.search(s)
        if m:
            rows.append((f.name, m.group(0), s[:260]))
print(len(rows), "sentences")
by = {}
for fn, w, s in rows:
    by.setdefault(fn, []).append((w, s))
for fn, items in by.items():
    print(fn, len(items))
main = [(w, s) for w, s in by.get("main.tex", [])]
if "strong" in sys.argv:
    for fn, w, s in rows:
        print("*", fn, "|", w, "|", s[:230])
    main = []
for w, s in main:
    print("-", w, "|", s)
