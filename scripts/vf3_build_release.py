"""F4.5: build release/crashguard-submit-v3.zip from a FRESH clone of a ref, add supplementary_full/, and record the SHA-256, the file count and a manifest.

usage: python scripts/vf2_build_release.py <ref> <scratch dir> <supplement_full.pdf>
The archive is `git archive` of the cloned commit plus supplementary_full/: supplement_full.tex and its PDF (built outside the repository), the Markdown sources of every document that the supplement
leaves out (same relative paths) and an INDEX.md. Writes release/crashguard-submit-v3.zip (git-ignored), release/crashguard-submit-v3.zip.sha256 and release/crashguard-submit-v3.manifest.txt.
"""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard import pp_supp  # noqa: E402

ref, scratch, pdf = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
if scratch.exists():
    shutil.rmtree(scratch, ignore_errors=True)
subprocess.run(["git", "clone", "-q", "--branch", ref, str(ROOT), str(scratch)], check=True)
commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=scratch, capture_output=True, text=True).stdout.strip()
out = ROOT / "release" / "crashguard-submit-v3.zip"
PRE = "crashguard-submit-v3/"
subprocess.run(["git", "archive", "--format=zip", f"--prefix={PRE}", "-o", str(out), "HEAD"], cwd=scratch, check=True)
kept = {f for fs in pp_supp.KEPT.values() for f in fs}
moved = [(title, f) for title, _tag, fs in pp_supp.SECTIONS for f in fs if f not in kept]
index = ["# Documents that the supplement leaves out", "",
         "The supplement (`paper/supplement.tex`) holds the ledger, the frame layout, the duty and audit analyses, the formal results, one decision table per round, the assumptions, the data sources and the bench protocol. "
         "The compiled full supplement is `supplement_full.pdf` (source `supplement_full.tex`, built from `paper/supplement_full.tex` with the files of `paper/generated/`). The Markdown sources of the documents below are in this folder under the same relative path.", "",
         "| Section of the full supplement | Path in this folder |", "|---|---|"] + [f"| {t} | `{f}` |" for t, f in moved]
with zipfile.ZipFile(out, "a", zipfile.ZIP_DEFLATED) as z:
    base = PRE + "supplementary_full/"
    z.write(scratch / "paper" / "supplement_full.tex", base + "supplement_full.tex")
    z.write(pdf, base + "supplement_full.pdf")
    z.writestr(base + "INDEX.md", "\n".join(index) + "\n")
    for _t, f in moved:
        src = scratch / f
        assert src.exists(), f
        z.write(src, base + f)
h = hashlib.sha256(out.read_bytes()).hexdigest()
names = [n for n in zipfile.ZipFile(out).namelist() if not n.endswith("/")]
(ROOT / "release" / "crashguard-submit-v3.zip.sha256").write_text(f"{h} *release/crashguard-submit-v3.zip\n", encoding="utf-8")
prev = {n.split("/", 1)[-1] for n in zipfile.ZipFile(ROOT / "release" / "crashguard-submit-v2.zip").namelist() if not n.endswith("/")}
cur = {n.split("/", 1)[-1] for n in names}
need = ["supplementary_full/supplement_full.pdf", "supplementary_full/supplement_full.tex", "supplementary_full/INDEX.md", "docs/05_architecture/FRAME_LAYOUT.md", "docs/04_audits/FINALIZE.md", "docs/04_audits/FINALIZE_REPORT.md",
        "formal/out/vf3/", "results/results.json", "paper/main.tex", "paper/supplement.tex", "paper/PLACEHOLDERS.md", "requirements.lock", "xsim/ns3/patches/", "tests/test_frame_layout.py", "docs/03_results/FINALIZE_INDIA_RULES.md", "docs/04_audits/PUSH_SIZE.md"]
missing = [n for n in need if not any(x.startswith(n) for x in cur)]
bad = [n for n in cur if n.startswith(("data/raw/", "data/simulated_hardware/variants/", ".venv/"))]
lines = [f"commit {commit}", f"ref {ref}", f"sha256 {h}", f"files {len(names)}", f"files in supplementary_full {sum(1 for n in names if '/supplementary_full/' in n)}", f"size {out.stat().st_size}",
         f"files of the submit-v2 release absent now: {len(prev - cur)}", f"files added since the submit-v2 release: {len(cur - prev)}", f"required content missing: {missing}", f"excluded content present (raw data, variants): {bad}",
         "note: release/*.zip files of earlier rounds are tracked in git at these tags (inherited from round 6); this archive is not tracked"]
lines += ["", "absent now (submit-v2 release minus this release):"] + sorted(prev - cur)[:40]
(ROOT / "release" / "crashguard-submit-v3.manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:11]))
