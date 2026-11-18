"""Append name==version with all PyPI file hashes to requirements.lock (used once in V1 for cryptography)."""
import json
import sys
import urllib.request
from pathlib import Path

lock = Path(__file__).resolve().parents[1] / "requirements.lock"
lines = []
for spec in sys.argv[1:]:
    name, ver = spec.split("==")
    d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{name}/{ver}/json"))
    hs = sorted({f["digests"]["sha256"] for f in d["urls"]})
    lines.append(f"{name}=={ver} \\")
    lines += [f"    --hash=sha256:{h} \\" for h in hs[:-1]] + [f"    --hash=sha256:{hs[-1]}"]
txt = lock.read_text(encoding="utf-8")
if not txt.endswith("\n"):
    txt += "\n"
lock.write_text(txt + "\n".join(lines) + "\n", encoding="utf-8")
print("added", sys.argv[1:])
