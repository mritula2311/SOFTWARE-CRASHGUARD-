"""Tests of the paper pipeline: number macros, formatting, markdown conversion and the audit script."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pp_md2tex as M  # noqa: E402

from crashguard import pp_paper as PP  # noqa: E402


def test_fmt():
    assert PP.fmt(0.0682, "p1") == "6.8"
    assert PP.fmt(-0.013, "sg3") == "$-$0.013"
    assert PP.fmt(0.021, "sg3") == "+0.021"
    assert PP.fmt(351754, "i") == r"351\,754"
    assert PP.fmt("a_b", "s") == r"a\_b"


def test_macros_are_letters_only_and_every_key_exists():
    R = PP.load()
    names = [n for n, _, _ in PP.spec(R)]
    assert len(names) == len(set(names)) > 150
    assert all(re.fullmatch(r"[A-Za-z]+", n) for n in names)


def test_numbers_tex_matches_results(tmp_path):
    bs = chr(92)
    R = PP.load()
    spec = {n: (v, f) for n, v, f in PP.spec(R)}
    t = (ROOT / "paper" / "generated" / "numbers.tex").read_text(encoding="utf-8")
    for n, (v, f) in list(spec.items())[:40]:
        assert (bs + "newcommand{" + bs + n + "}{" + PP.fmt(v, f) + "}") in t


def test_md2tex_escapes_and_tables():
    out = M.convert("# Title\n\n## Sec\n\nA_b & 5% `x_y` **bold**\n\n| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert r"A\_b \& 5\% \texttt{x\_y} \textbf{bold}" in out
    assert r"\begin{longtable}" in out and r"\section*{Sec}" in out


def test_audit_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pp_paper_audit.py")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-800:]


def test_highlights_length():
    for ln in (ROOT / "paper" / "highlights.md").read_text(encoding="utf-8").split("\n"):
        if ln.startswith("- "):
            assert len(ln[2:].split(" (")[0]) <= 85


def test_results_origin_labels_allowed():
    ok = {"MEASURED_SOFTWARE", "SIMULATED", "SIMULATED_HW_FORMAT", "TRACE_DRIVEN", "FORMAL", "ANALYTICAL", "EMULATED", "NOT_RUN"}
    for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8")):
        if e["name"].startswith("pp."):
            assert e["origin"] in ok
