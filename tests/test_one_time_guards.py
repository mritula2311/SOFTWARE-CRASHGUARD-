"""Round 7e: one-time scripts refuse to run (they would overwrite the current paper text, ledger or layout)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ["r7c_patch_paper", "r7b_patch_paper", "r7_cover", "r7b_ledger", "vf2_cover", "vf_ledger"]


def _run(args):
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "SYSTEMROOT": "C:\Windows", "PATH": ""})
    return r.returncode, r.stdout + r.stderr


def test_one_time_scripts_refuse():
    for s in SCRIPTS:
        rc, out = _run([f"scripts/{s}.py"])
        assert rc != 0 and "one-time script" in out, (s, rc, out[-300:])


def test_one_time_modules_refuse():
    for m in ("crashguard.r7_layout", "crashguard.pp_submission"):
        rc, out = _run(["-m", m])
        assert rc != 0 and "one-time script" in out, (m, rc, out[-300:])


def test_report_script_needs_arguments():
    rc, out = _run(["scripts/r7c_report.py"])
    assert rc != 0 and "refusing to run" in out
