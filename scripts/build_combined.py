"""Build release/crashguard-combined-v1.zip: the release file set (`crashguard.fin_release.files`) plus the supplied simulated hardware-format files (`data/simulated_hardware/`, without the regenerable variants).
Hashes of every file are inside the archive (HASHES.sha256); the SHA-256 of the archive is printed. No raw third-party data, no processed data and no `data/hardware/` folder.
Run: python scripts/build_combined.py"""
import hashlib
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, "src")
from crashguard import fin_release as FR  # noqa: E402

OUT = Path("release/crashguard-combined-v1.zip")
files = [p for p in FR.files() if p != OUT and p != FR.OUT and "crashguard-release-v1" not in p.as_posix()]
sim = [p for p in sorted(Path("data/simulated_hardware").rglob("*")) if p.is_file() and "variants" not in p.parts and "__pycache__" not in p.parts]
files = sorted(set(files) | set(sim))
h = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for p in files:
        z.write(p, p.as_posix())
    z.writestr("HASHES.sha256", "\n".join(f"{v}  {k}" for k, v in sorted(h.items())) + "\n")
print(len(files), "files;", OUT.stat().st_size, "bytes; sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())
bad = [k for k in h if k.startswith((".venv", "data/raw", "data/processed", "data/hardware/")) or (k.endswith(".pdf") and "literature" in k)]
print("excluded-path check:", "ok" if not bad else bad[:3])
