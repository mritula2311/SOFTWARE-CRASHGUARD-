"""V11.2: compile paper/main.tex and paper/supplement.tex with Tectonic, outside the repository, as a lint and a page-count estimate.

usage: python scripts/vf_shim_compile.py <work dir> <tectonic.exe>

Tectonic is an XeTeX engine and cannot run the IEEE Access class `ieeeaccess.cls` (it uses pdfTeX primitives), so main.tex is compiled with the class IEEEtran (journal option,
two columns, Times) and shims for the Access-only commands. The page count is therefore an ESTIMATE for the Access layout; the supplement (article class) is compiled as it is.
The IEEE Access template files are not stored in the repository.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
work, tect = Path(sys.argv[1]), sys.argv[2]
if work.exists():
    shutil.rmtree(work)
shutil.copytree(ROOT / "paper", work)
s = (work / "main.tex").read_text(encoding="utf-8")
shim = (
    "\\documentclass[journal]{IEEEtran}\n\\usepackage{times}\n"
    "\\newcommand{\\history}[1]{}\\newcommand{\\doi}[1]{}\\newcommand{\\tfootnote}[1]{}\\newcommand{\\corresp}[1]{}\\newcommand{\\titlepgskip}{\\relax}\\newcommand{\\EOD}{}\n"
    "\\newcommand{\\authorrefmark}[1]{}\\newcommand{\\address}[2][]{}\\newcommand{\\headeretal}{et al.}"
)
s = s.replace("\\documentclass{ieeeaccess}", shim).replace("\\titlepgskip=-15pt", "")
s = re.sub(r"\\address\[1\]\{[^}]*\}", "", s)
s = s.replace("begin{keywords}", "begin{IEEEkeywords}").replace("end{keywords}", "end{IEEEkeywords}")
(work / "main_shim.tex").write_text(s, encoding="utf-8")
for name in ("main_shim.tex", "supplement.tex", "supplement_full.tex"):
    r = subprocess.run([tect, "-X", "compile", "--keep-logs", name], cwd=work, capture_output=True, text=True)
    errs = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith("error")]
    pdf = work / name.replace(".tex", ".pdf")
    pages = "?"
    if pdf.exists():
        import pypdf

        pages = len(pypdf.PdfReader(str(pdf)).pages)
    log = (work / name.replace(".tex", ".log")).read_text(encoding="utf-8", errors="replace")
    print(name, "pages", pages, "errors", errs[:3], "undefined refs/citations", len(re.findall(r"(Citation|Reference|Label).{0,40}undefined", log, re.I)), "overfull boxes", len(re.findall(r"Overfull", log)))
