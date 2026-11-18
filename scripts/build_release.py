"""E: build release/crashguard-release-v1.zip (code, tests, scripts, docs, results tables and figures, paper, hashes inside the archive). No raw third-party data, no processed data, no hardware folder, no literature PDFs.
Reuses the file rules of crashguard.fin_release. Run: python scripts/build_release.py"""
import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, "src")
from crashguard import fin_release as FR  # noqa: E402

OUT = Path("release/crashguard-release-v1.zip")
files = [p for p in FR.files() if p != OUT and p != FR.OUT]
h = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files:
        z.write(p, p.as_posix())
    z.writestr("HASHES.sha256", "\n".join(f"{v}  {k}" for k, v in sorted(h.items())) + "\n")
print(len(files), "files;", OUT.stat().st_size, "bytes; sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())
bad = [k for k in h if k.startswith(("data/", ".venv")) or "hardware" in k or k.endswith(".pdf") and "literature" in k]
print("excluded-path check:", "ok" if not bad else bad[:3])
