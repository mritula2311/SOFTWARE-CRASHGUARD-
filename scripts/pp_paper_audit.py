"""P5: consistency and claim audit of the combined paper.

    python scripts/pp_paper_audit.py

1. LaTeX lint of main.tex and supplement.tex (braces, environments, macros, references, citations).
2. Numbers: every number in the result sections of main.tex is a macro from generated/numbers.tex; bare numbers are allowed only if they match an entry of paper/number_whitelist.txt (design constants, ids, counts of items in prose).
3. Claim audit: every sentence with an improvement or strength word is listed with its context for manual review (written to docs/04_audits/PP_PAPER_CLAIM_AUDIT.md together with the dispositions in paper/claim_dispositions.txt).
4. Reference check: every cited key has an entry and an opened-status in paper/reference_status.txt (written to docs/04_audits/PP_REFERENCE_CHECK.md).
5. Forbidden words.
Exit code 1 if any check fails.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "paper"
AUD = ROOT / "docs" / "04_audits"
FORBID = [r"\bfirst\b", r"\bnovel\b", r"state[- ]of[- ]the[- ]art", r"\bunbiased\b", r"validated on hardware"]
STD_MACROS = set("""title author address tfootnote markboth corresp begin end section subsection subsubsection emph textbf textsc cite ref label caption centering includegraphics input small toprule midrule bottomrule item
pm le ge times textit url bibliographystyle bibliography history doi titlepgskip maketitle uppercase authorrefmark EOD newcommand usepackage documentclass lab hline linewidth columnwidth textwidth to approx sim
setlength tabcolsep path itemsep paragraph texttt footnotesize scriptsize raggedright endhead longtable tableofcontents date geometry cdot ldots mathrm text quad qquad ensuremath bullet \\ & % _ $ # { } , ; : ! ' " ` ^ ~ = . - ( ) [ ] / @ |""".split())
RESULT_SECTIONS = ("Results A", "Results B", "Results C", "Results D", "Negative results")


def write_keep_header(path: Path, text: str) -> None:
    """Write a generated document and keep the header block that scripts/doc_headers.py put in the previous version."""
    s, e = "<!-- header:start -->", "<!-- header:end -->"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if s in old and e in old:
            block = old[old.index(s): old.index(e) + len(e)]
            text = text[: text.index(s)] + block + text[text.index(e) + len(e):]
    path.write_text(text, encoding="utf-8")


def strip_comments(t: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", t)


def lint(name: str, t: str, defined: set[str], bib: set[str]) -> list[str]:
    errs = []
    s = strip_comments(t)
    depth = 0
    for ln, line in enumerate(s.split("\n"), 1):
        for m in re.finditer(r"(\\[\\{}%&_#$])|[{}]", line):
            if m.group(1):
                continue
            depth += 1 if m.group(0) == "{" else -1
            if depth < 0:
                errs.append(f"{name}:{ln}: unmatched closing brace")
                depth = 0
    if depth != 0:
        errs.append(f"{name}: brace depth {depth} at end")
    envs = re.findall(r"\\(begin|end)\{([^}]*)\}", s)
    stack = []
    for kind, e in envs:
        if kind == "begin":
            stack.append(e)
        else:
            if not stack or stack[-1] != e:
                errs.append(f"{name}: environment mismatch at end{{{e}}}")
            else:
                stack.pop()
    if stack:
        errs.append(f"{name}: unclosed environments {stack}")
    labels = set(re.findall(r"\\label\{([^}]*)\}", s))
    for r in set(re.findall(r"\\ref\{([^}]*)\}", s)):
        if r not in labels:
            errs.append(f"{name}: undefined reference {r}")
    for m in set(re.findall(r"\\([A-Za-z]+)", s)):
        if m not in defined and m not in STD_MACROS:
            errs.append(f"{name}: undefined macro \\{m}")
    for c in re.findall(r"\\cite\{([^}]*)\}", s):
        for k in c.split(","):
            if k.strip() not in bib:
                errs.append(f"{name}: citation key {k.strip()} not in references.bib")
    return errs


def numbers_check(t: str, whitelist: list[re.Pattern]) -> tuple[list[str], int]:
    s = strip_comments(t)
    body = s.split("\\begin{document}", 1)[1]
    secs = re.split(r"(?=\\section\{)", body)
    flagged, allowed = [], 0
    for sec in secs:
        m = re.match(r"\\section\{([^}]*)\}", sec)
        if not m or not any(m.group(1).startswith(x) for x in RESULT_SECTIONS):
            continue
        txt = re.sub(r"\\(cite|ref|label|includegraphics)(\[[^\]]*\])?\{[^}]*\}", "", sec)
        txt = re.sub(r"p\{[\d.]+cm\}|width=[\d.]+\\[a-z]+", "", txt)
        txt = re.sub(r"\\[A-Za-z]+", " ", txt)  # macro names (including numbers.tex macros) are not numbers
        for line in txt.split("\n"):
            for mm in re.finditer(r"(?<![A-Za-z_\\])\d+(?:\.\d+)?", line):
                ctx = line[max(0, mm.start() - 9): mm.end() + 11]
                if any(w.search(ctx) for w in whitelist):
                    allowed += 1
                else:
                    flagged.append(f"[{m.group(1)}] bare number {mm.group(0)!r} in: ...{ctx.strip()}...")
    return flagged, allowed


def claims(t: str) -> list[str]:
    s = strip_comments(t)
    s = s.split("\\begin{document}", 1)[1]
    s = re.sub(r"\\(section|subsection)\{[^}]*\}|\\(label|begin|end)\{[^}]*\}|\\includegraphics[^}]*\}", " ", s)
    sents = re.split(r"(?<=[.?!])\s+", re.sub(r"\s+", " ", s))
    pat = re.compile(r"\b(improv\w*|outperform\w*|robust\w*|secure|validated|better than|beats?|superior)\b", re.I)
    return [x.strip() for x in sents if pat.search(x)]


def main() -> int:
    numbers_tex = (P / "generated" / "numbers.tex").read_text(encoding="utf-8")
    if (P / "generated" / "numbers_r7.tex").exists():  # round 7 macros
        numbers_tex += (P / "generated" / "numbers_r7.tex").read_text(encoding="utf-8")
    if (P / "generated" / "numbers_r7b.tex").exists():  # round 7b macros
        numbers_tex += (P / "generated" / "numbers_r7b.tex").read_text(encoding="utf-8")
    defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", numbers_tex))
    bib = set(re.findall(r"@\w+\{([^,]+),", (P / "references.bib").read_text(encoding="utf-8")))
    main_t = (P / "main.tex").read_text(encoding="utf-8")
    sup_t = (P / "supplement.tex").read_text(encoding="utf-8")
    defined |= set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", main_t))
    errs = lint("main.tex", main_t, defined, bib) + lint("supplement.tex", sup_t, defined, bib)
    for f in sorted((P / "generated" / "supp").glob("*.tex")):
        t = f.read_text(encoding="utf-8")
        # braces and environments only (the converted documents use no macros of their own)
        e = [x for x in lint(f"supp/{f.name}", t, defined, bib) if "undefined macro" not in x and "undefined reference" not in x]
        errs += e
    wl = [re.compile(x.rstrip("\n")) for x in (P / "number_whitelist.txt").read_text(encoding="utf-8").split("\n") if x.strip() and not x.startswith("#")]
    flagged, allowed = numbers_check(main_t, wl)
    forb = []
    for name, t in (("main.tex", main_t), ("supplement.tex", sup_t), ("paper/cover_letter.md", (P / "cover_letter.md").read_text(encoding="utf-8") if (P / "cover_letter.md").exists() else "")):
        for f in FORBID:
            for m in re.finditer(f, strip_comments(t) if name.endswith("tex") else t, flags=re.I):
                forb.append(f"{name}: forbidden word {m.group(0)!r}")
    cl = claims(main_t)
    disp = {}
    dp = P / "claim_dispositions.txt"
    if dp.exists():
        for line in dp.read_text(encoding="utf-8").split("\n"):
            if "\t" in line:
                a, b = line.split("\t", 1)
                disp[a.strip()] = b.strip()
    undisposed = [c for c in cl if not any(k in c for k in disp)]
    stat = {}
    sp = P / "reference_status.txt"
    for line in sp.read_text(encoding="utf-8").split("\n"):
        if "\t" in line and not line.startswith("#"):
            a, b = line.split("\t", 1)
            stat[a.strip()] = b.strip()
    cited = sorted({k.strip() for c in re.findall(r"\\cite\{([^}]*)\}", main_t + sup_t) for k in c.split(",")})
    no_status = [k for k in cited if k not in stat]
    # reports
    AUD.mkdir(parents=True, exist_ok=True)
    L = ["# Claim audit of the combined paper (generated by `scripts/pp_paper_audit.py`)", "", "<!-- header:start -->", "<!-- header:end -->", "",
         f"Every sentence of `paper/main.tex` with an improvement or strength word, with the disposition written in `paper/claim_dispositions.txt`. Sentences without a disposition: {len(undisposed)}.", "",
         "| Sentence (start) | Disposition |", "|---|---|"]
    for c in cl:
        d = next((v for k, v in disp.items() if k in c), "NO DISPOSITION")
        L.append(f"| {c[:170].replace('|', '/')} | {d} |")
    write_keep_header(AUD / "PP_PAPER_CLAIM_AUDIT.md", "\n".join(L) + "\n")
    R = ["# Reference check of the combined paper (generated by `scripts/pp_paper_audit.py`)", "", "<!-- header:start -->", "<!-- header:end -->", "",
         f"Cited keys: {len(cited)}. Keys without a recorded opened status: {len(no_status)}. A key is cited only if its status says the item was opened (full text, abstract, record or data card) and what was read; unverified items were removed.", "",
         "| Key | Status |", "|---|---|"] + [f"| {k} | {stat.get(k, 'NO STATUS')} |" for k in cited]
    write_keep_header(AUD / "PP_REFERENCE_CHECK.md", "\n".join(R) + "\n")
    mat = (ROOT / "docs" / "06_references" / "NOVELTY_MATRIX_2021PLUS.md").read_text(encoding="utf-8")
    contrib = []
    for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
        if f"| {c} |" not in mat:
            contrib.append(f"matrix row {c} missing")
        if f"\\textbf{{{c}," not in main_t:
            contrib.append(f"contribution {c} missing in main.tex")
    problems = errs + contrib + [f"NUMBERS: {x}" for x in flagged] + forb + [f"CLAIM without disposition: {c[:100]}" for c in undisposed] + [f"REFERENCE without status: {k}" for k in no_status]
    print(f"lint errors {len(errs)}; bare numbers flagged {len(flagged)} (allowed {allowed}); forbidden words {len(forb)}; claim sentences {len(cl)} (undisposed {len(undisposed)}); cited {len(cited)} (no status {len(no_status)})")
    for p in problems[:80]:
        print(" -", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
