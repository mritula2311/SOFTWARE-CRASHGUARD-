"""Small Markdown to LaTeX converter for the supplement (headings, paragraphs, lists, pipe tables, bold, italic, code, links). Used by crashguard.pp_supp.

It escapes LaTeX special characters, drops HTML comments and the document header block, flattens nested lists and turns pipe tables into longtable environments with equal-width paragraph columns.
"""
from __future__ import annotations

import re

SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
UNI = {"\u2013": "--", "\u2014": "---", "\u2212": "-", "\u2264": r"$\le$", "\u2265": r"$\ge$", "\u00b1": r"$\pm$", "\u00d7": r"$\times$", "\u2192": r"$\to$", "\u2018": "'", "\u2019": "'", "\u201c": "``", "\u201d": "''",
       "\u00a0": " ", "\u2248": r"$\approx$", "\u03b1": r"$\alpha$", "\u03bc": r"$\mu$", "\u2260": r"$\ne$", "\u2208": r"$\in$", "\u2209": r"$\notin$", "\u221e": r"$\infty$", "\u00b0": r"$^\circ$", "\u00b2": r"$^2$",
       "\u00e9": r"\'e", "\u00fc": r"\"u", "\u00f6": r"\"o", "\u00e4": r"\"a", "\u00ed": r"\'i", "\u00e1": r"\'a", "\u00f3": r"\'o", "\u0131": "i", "\u2022": r"$\bullet$", "\u2026": "...", "\u2217": "*", "\u00b7": r"$\cdot$"}


def esc(s: str) -> str:
    out = []
    for ch in s:
        if ch in SPECIAL:
            out.append(SPECIAL[ch])
        elif ch in UNI:
            out.append(UNI[ch])
        elif ord(ch) > 127:
            out.append("?")
        else:
            out.append(ch)
    return "".join(out)


def inline(s: str) -> str:
    """Inline Markdown: code spans, bold, italic, links."""
    parts = re.split(r"(`[^`]*`)", s)
    res = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) >= 2:
            res.append(r"\texttt{" + esc(p[1:-1]).replace(r"\_", r"\_") + "}")
            continue
        p = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", p)
        p = re.sub(r"\[([^\]]*)\]\(([^)]*)\)", lambda m: m.group(1) + " (" + m.group(2) + ")" if m.group(2).startswith("http") else m.group(1), p)
        toks = re.split(r"(\*\*[^*]+\*\*|\*[^*\s][^*]*\*)", p)
        for t in toks:
            if t.startswith("**") and t.endswith("**") and len(t) > 4:
                res.append(r"\textbf{" + esc(t[2:-2]) + "}")
            elif t.startswith("*") and t.endswith("*") and len(t) > 2:
                res.append(r"\emph{" + esc(t[1:-1]) + "}")
            else:
                res.append(esc(t))
    return "".join(res)


def table(rows: list[list[str]]) -> str:
    n = max(len(r) for r in rows)
    w = 0.95 / n
    colspec = "".join(f"p{{{w:.3f}\\linewidth}}" for _ in range(n))
    out = [r"{\scriptsize\raggedright", r"\begin{longtable}{" + colspec + "}", r"\toprule"]
    for i, r in enumerate(rows):
        r = r + [""] * (n - len(r))
        out.append(" & ".join(inline(c.strip()) for c in r) + r" \\")
        if i == 0:
            out += [r"\midrule", r"\endhead"]
    out += [r"\bottomrule", r"\end{longtable}}"]
    return "\n".join(out)


def convert(md: str, level0: int = 0, skip_title: bool = True) -> str:
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S) if "header:start" not in md else re.sub(r"<!-- header:start -->.*?<!-- header:end -->", "", md, flags=re.S)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    in_list = False
    in_code = False
    titled = False
    heads = [r"\section", r"\subsection", r"\subsubsection", r"\paragraph", r"\paragraph", r"\paragraph"]

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(r"\end{itemize}")
            in_list = False

    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            close_list()
            in_code = not in_code
            out.append(r"\begin{verbatim}" if in_code else r"\end{verbatim}")
            i += 1
            continue
        if in_code:
            out.append(ln.encode("ascii", "replace").decode())
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if m:
            close_list()
            lvl = len(m.group(1)) - 1
            if lvl == 0 and skip_title and not titled:
                titled = True
                i += 1
                continue
            lv = min(max(lvl + level0 - (1 if skip_title else 0), 0), 5)
            h = heads[lv]
            out.append(h + "*{" + inline(m.group(2)) + "}" if lv < 3 else h + "{" + inline(m.group(2)) + "}")
            i += 1
            continue
        if ln.strip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            close_list()
            rows = [[c for c in ln.strip().strip("|").split("|")]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(table(rows))
            continue
        m = re.match(r"^\s*([-*]|\d+\.)\s+(.*)$", ln)
        if m:
            if not in_list:
                out.append(r"\begin{itemize}")
                in_list = True
            out.append(r"\item " + inline(m.group(2)))
            i += 1
            continue
        if not ln.strip():
            close_list()
            out.append("")
            i += 1
            continue
        if ln.startswith(">"):
            out.append(inline(ln.lstrip("> ")))
            i += 1
            continue
        if in_list and ln.startswith("  "):
            out.append(inline(ln.strip()))
            i += 1
            continue
        close_list()
        out.append(inline(ln))
        i += 1
    close_list()
    if in_code:
        out.append(r"\end{verbatim}")
    return "\n".join(out) + "\n"
