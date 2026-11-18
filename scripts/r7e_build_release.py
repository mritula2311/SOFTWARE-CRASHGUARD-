"""Round 7e: build release/crashguard-submit-v6.2.zip from a FRESH clone of a ref, add supplementary_full/, and record the SHA-256, the file count and a manifest.

usage: python scripts/r7_build_release.py <ref> <scratch dir> [supplement_full.pdf]
Same layout as scripts/vf3_build_release.py (submit-v6). The compiled supplement PDF is optional: no TeX distribution is available in this environment, so without a PDF the archive
holds supplement_full.tex and the Markdown sources only, and the manifest says so. Writes release/crashguard-submit-v6.2.zip (git-ignored), .zip.sha256 and release/crashguard-submit-v6.2.manifest.txt.
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

ref, scratch = sys.argv[1], Path(sys.argv[2])
pdf = Path(sys.argv[3]) if len(sys.argv) > 3 else None
if scratch.exists():
    shutil.rmtree(scratch, ignore_errors=True)
subprocess.run(["git", "clone", "-q", "--branch", ref, str(ROOT), str(scratch)], check=True)
commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=scratch, capture_output=True, text=True).stdout.strip()
out = ROOT / "release" / "crashguard-submit-v6.2.zip"
PRE = "crashguard-submit-v6.2/"
subprocess.run(["git", "archive", "--format=zip", f"--prefix={PRE}", "-o", str(out), "HEAD"], cwd=scratch, check=True)
kept = {f for fs in pp_supp.KEPT.values() for f in fs}
moved = [(title, f) for title, _tag, fs in pp_supp.SECTIONS for f in fs if f not in kept]
index = ["# Documents that the supplement leaves out", "",
         "The supplement (`paper/supplement.tex`) holds the ledger, the frame layout, the duty and audit analyses, the formal results, one decision table per round (round 7 included), the assumptions and the data sources. The documents below are left out of it and are kept here.", "",
         "The full supplement source is `supplement_full.tex`" + (" and its compiled form is `supplement_full.pdf`." if pdf else "; **it was not compiled (no TeX distribution in the session)**, so there is no PDF in this archive."), "",
         "| Section of the full supplement | Path in this folder |", "|---|---|"] + [f"| {t} | `{f}` |" for t, f in moved]
with zipfile.ZipFile(out, "a", zipfile.ZIP_DEFLATED) as z:
    base = PRE + "supplementary_full/"
    z.write(scratch / "paper" / "supplement_full.tex", base + "supplement_full.tex")
    if pdf:
        z.write(pdf, base + "supplement_full.pdf")
    z.writestr(base + "INDEX.md", "\n".join(index) + "\n")
    for _t, f in moved:
        src = scratch / f
        assert src.exists(), f
        z.write(src, base + f)
h = hashlib.sha256(out.read_bytes()).hexdigest()
names = [n for n in zipfile.ZipFile(out).namelist() if not n.endswith("/")]
(ROOT / "release" / "crashguard-submit-v6.2.zip.sha256").write_text(f"{h} *release/crashguard-submit-v6.2.zip\n", encoding="utf-8")
prev = {n.split("/", 1)[-1] for n in zipfile.ZipFile(ROOT / "release" / "crashguard-submit-v6.zip").namelist() if not n.endswith("/")}
cur = {n.split("/", 1)[-1] for n in names}
need = ["supplementary_full/supplement_full.tex", "supplementary_full/INDEX.md", "docs/02_preregistration/PREREGISTRATION_V18.md", "docs/02_preregistration/PREREGISTRATION_V19.md", "docs/03_results/ROUND7B_RESULTS.md", "docs/03_results/ROUND7B_DEVIATIONS.md", "docs/04_audits/ROUND7B_REPORT.md", "docs/04_audits/ROUND7C_REPORT.md", "docs/04_audits/ROUND7D_REPORT.md", "docs/04_audits/ROUND7E_REPORT.md", "src/crashguard/r7d_base.py", "tests/test_r7d.py", "tests/test_one_time_guards.py", "docs/04_audits/ROUND7C.md", "docs/01_literature/LITERATURE_FINAL_CHECK.md", "scripts/fetch_sisfall.md", "scripts/r7c_k_checks.py", "docs/04_audits/ROUND7B.md", "formal/r7b_quarantine_pseudo.spthy", "formal/out/r7b/", "paper/refs_manual.bib", "paper/generated/numbers_r7b.tex", "src/crashguard/r7b_formal.py", "tests/test_r7b.py", "results/tables/r7b_attack_cells.json", ".github/workflows/tests.yml", "docs/01_literature/R7_PRIOR_ART.md", "docs/03_results/ROUND7_A.md", "docs/03_results/ROUND7_B.md",
        "docs/03_results/ROUND7_RESULTS.md", "docs/04_audits/ROUND7.md", "docs/04_audits/ROUND7_REPORT.md", "formal/proverif/r7_unlink.pv", "formal/r7_alert_pseudo_fresh_bootctr.spthy", "formal/out/r7/", "firmware_r7/cg_r7.c",
        "results/results.json", "results/tables/r7_attack_cells.json", "paper/main.tex", "paper/supplement.tex", "paper/generated/numbers_r7.tex", "src/crashguard/r7_engine.py", "tests/test_r7_engine.py", "requirements.lock"]
missing = [n for n in need if not any(x.startswith(n) for x in cur)]
bad = [n for n in cur if n.startswith(("data/raw/", "data/simulated_hardware/variants/", ".venv/"))]
lines = [f"commit {commit}", f"ref {ref}", f"sha256 {h}", f"files {len(names)}", f"files in supplementary_full {sum(1 for n in names if '/supplementary_full/' in n)}", f"size {out.stat().st_size}",
         f"files of the submit-v6 release absent now: {len(prev - cur)}", f"files added since the submit-v6 release: {len(cur - prev)}", f"required content missing: {missing}", f"excluded content present: {bad}",
         f"compiled supplement PDF: {'yes' if pdf else 'no (NOT_RUN: no TeX distribution)'}",
         "note: release/*.zip files of earlier rounds are tracked in git at their tags; this archive is not tracked"]
lines += ["", "absent now (submit-v6 release minus this release):"] + sorted(prev - cur)[:40]
(ROOT / "release" / "crashguard-submit-v6.2.manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:11]))
