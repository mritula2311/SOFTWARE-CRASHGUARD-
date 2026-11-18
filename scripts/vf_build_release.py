"""V11.6 and V1.6: build the release archive from a FRESH clone of a ref, compare it with the working copy's `git archive` and with the committed round-5 release, write the hash and a manifest.

usage: python scripts/vf_build_release.py <ref> <scratch dir>
Writes release/crashguard-submit-v1.zip (git-ignored), release/crashguard-submit-v1.zip.sha256 and release/crashguard-submit-v1.manifest.txt.
"""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ref, scratch = sys.argv[1], Path(sys.argv[2])
if scratch.exists():
    shutil.rmtree(scratch, ignore_errors=True)
subprocess.run(["git", "clone", "-q", "--branch", ref if not ref.startswith("HEAD") else "verify", str(ROOT), str(scratch)], check=True)
out = ROOT / "release" / "crashguard-submit-v1.zip"
subprocess.run(["git", "archive", "--format=zip", "--prefix=crashguard-submit-v1/", "-o", str(out), "HEAD"], cwd=scratch, check=True)
h = hashlib.sha256(out.read_bytes()).hexdigest()
names = zipfile.ZipFile(out).namelist()
(ROOT / "release" / "crashguard-submit-v1.zip.sha256").write_text(f"{h} *release/crashguard-submit-v1.zip\n", encoding="utf-8")
# same archive from the working copy at the same commit
commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=scratch, capture_output=True, text=True).stdout.strip()
tmp = ROOT / "release" / "_wc.zip"
subprocess.run(["git", "archive", "--format=zip", "--prefix=crashguard-submit-v1/", "-o", str(tmp), commit], cwd=ROOT, check=True)
same_wc = zipfile.ZipFile(tmp).namelist() == names
tmp.unlink()
old = zipfile.ZipFile(ROOT / "release" / "crashguard-round5-v1.zip").namelist()
pre = old[0] if old[0].startswith("crashguard-") and old[0].endswith("/") else ""
oldn = {n[len(pre):] for n in old if not n.endswith("/")}
newn = {n.split("/", 1)[-1] for n in names if not n.endswith("/")}
need = ["xsim/ns3/patches/", "formal/crash_alert_auth.spthy", "formal/crash_alert_fresh_bootctr.spthy", "formal/proverif/carid_frozen_same_epoch.pv", "formal/rerun_vf/", "docs/02_preregistration/PREREGISTRATION_V16.md",
        "results/results.json", "paper/main.tex", "paper/supplement.tex", "docs/04_audits/HYPOTHESIS_LEDGER.md", "docs/04_audits/FINAL_VERIFICATION.md", "paper/PLACEHOLDERS.md", "requirements.lock"]
missing = [n for n in need if not any(x.startswith(n) for x in newn)]
bad = [n for n in newn if n.startswith(("data/raw/", "data/simulated_hardware/variants/", ".venv/"))]
lines = [f"commit {commit}", f"sha256 {h}", f"files {len(newn)}", f"size {out.stat().st_size}",
         f"identical file list from the working copy: {same_wc}", f"files of the round-5 release absent now: {len(oldn - newn)}", f"files added since the round-5 release: {len(newn - oldn)}",
         f"required content missing: {missing}", f"excluded content present (raw data, variants): {bad}"]
lines += ["", "absent now (round-5 release minus this release):"] + sorted(oldn - newn)[:40]
(ROOT / "release" / "crashguard-submit-v1.manifest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:9]))
