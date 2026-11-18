"""V8.5: consistency sweep. For each key fact, every line of the listed documents that mentions the topic must also contain a canonical value of the fact.
A line that mentions the topic without a canonical value is listed for review (it may be a different quantity).
usage: python scripts/vf_consistency.py   (writes docs/04_audits/CONSISTENCY_SWEEP.md)"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}
DOCS = ["README.md", "docs/00_overview/PROJECT_STATUS.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "paper/highlights.md", "paper/cover_letter.md", "paper/graphical_abstract.svg", "paper/ABSTRACT_FACTS.md", "paper/main.tex", "paper/supplement.tex"]


def f3(x):
    return f"{x:.3f}"


FACTS = [
    ("F1 cross-split groups", r"cross-split group|duplicate group|identical arrays", [str(int(R["leakage.exact_hash_groups_across_splits"]))]),
    ("F2 exact copies in test", r"exact cop(y|ies)", ["118", "0.49", "0.5%"]),
    ("F3 window-identical share", r"window-identical|identical to a (training|train)", ["1,305", "1305", "22.3", "5,863", "5863", r"1\\,305", r"5\\,863", "VzNear"]),
    ("F4 recall at the 1% target", r"recall at the 1% (false-alarm )?target|recall at 1%", [f3(R["vz.v4.rf15.supplied.recall_at_1pct"]), f3(R["vz.v4.rf15.near.recall_at_1pct"]), "VzROne"]),
    ("F9 median earlier", r"1[.,]?750 ms|median.*earlier", ["1750", "1,750", "1.75", "TThreeEarlier"]),
    ("F10 SF9 extra airtime", r"SF9.*(extra )?airtime|extra airtime.*SF9", ["54", "NsAirHiSfNine"]),
    ("F11 D1 gain across simulators", r"D1 .*(custom|ns-3)", ["0.116", "0.021", "+0.116", "+0.021", "XCustomDOneGain", "XNsDOneGain"]),
    ("F12 LoED control", r"zero-spacing|no-hold|retries at once", ["54.0", "49.3", "TOneDelZ", "TOneDelDOne"]),
    ("F16 L1 side accuracy", r"side accuracy|mounting calibration", ["0.986", "0.99", "0.49", "0.98", "RFiveOne"]),
    ("F17 L3 recall", r"wake-on-motion|L3", ["0.631", "0.609", "0.25", "0.247", "RFiveThree"]),
]
out = []
for name, topic, canon in FACTS:
    pat = re.compile(topic, re.I)
    for d in DOCS:
        p = ROOT / d
        if not p.exists():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pat.search(line) and not any(c in line for c in canon):
                out.append((name, d, n, " ".join(line.split())[:170]))
print(len(out), "lines to review")
for o in out:
    print(o)
(ROOT / "docs/04_audits/_consistency_raw.txt").write_text("\n".join(map(str, out)), encoding="utf-8")
