"""R4 to R6: documentation hygiene. Every document has a current header block, no banned word or chat tone, no broken link, every documented command resolves."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def test_headers_and_index_are_current():
    r = _run("doc_headers.py", "--check")
    assert r.returncode == 0, r.stdout + r.stderr


def test_wording_and_tone():
    r = _run("doc_style_check.py")
    assert r.returncode == 0, r.stdout[-3000:]


def test_links_resolve():
    r = _run("check_links.py")
    assert r.returncode == 0, r.stdout[-3000:]


def test_documented_commands_resolve():
    r = _run("check_reproduce.py")
    assert r.returncode == 0, r.stdout[-3000:]
