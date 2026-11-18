"""Round 7b G6: ledger macros, the ledger table row and the version text in main.tex and the cover letter (idempotent)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rw(path, fn):
    b = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in b
    s = fn(b.replace("\r\n", "\n"))
    path.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


def main_tex(s):
    if "LgHPre" in s:
        return s
    s = s.replace("(V1 to V18, with addenda; H-R7-A3 of V18 is descriptive and has no verdict)", "(V1 to V19, with addenda; H-R7-A3 of V18 is descriptive and has no verdict)", 1)
    old = "Round 7 (V18) & \\LgGPre{} & \\LgGRun{} & \\LgGSupp{} & \\LgGNot{} & \\LgGPartly{} & \\LgGNotRun{}\\\\\\midrule"
    assert old in s
    new = old.replace("\\\\\\midrule", "\\\\") + "\nRound 7b (V19) & \\LgHPre{} & \\LgHRun{} & \\LgHSupp{} & \\LgHNot{} & \\LgHPartly{} & \\LgHNotRun{}\\\\\\midrule"
    return s.replace(old, new, 1)


def cover(s):
    old = "136 hypotheses were preregistered in 14 versions; 123 were run, 47 are supported, 71 not supported, 4 partly supported and 13 not run"
    return s.replace(old, "138 hypotheses were preregistered in 15 versions; 125 were run, 48 are supported, 72 not supported, 4 partly supported and 13 not run")


rw(ROOT / "paper" / "main.tex", main_tex)
rw(ROOT / "paper" / "cover_letter.md", cover)
print("ok")
