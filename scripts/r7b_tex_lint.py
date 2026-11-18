"""Round 7b G6: static lint of paper/main.tex, paper/supplement.tex and paper/supplement_full.tex (no TeX distribution here, so nothing is compiled): balanced braces, balanced environments, undefined macros
(a macro that is used and defined neither in a numbers file, in the file itself nor in the standard set), \\input files that exist, \\cite keys that exist in references.bib.
"""
import re
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "paper"
STD = set("""textbf emph textit cite ref label caption section subsection subsubsection begin end item input path url footnote tfootnote title author address corresp markboth
documentclass usepackage maketitle centering footnotesize small tiny toprule midrule bottomrule hline cline multicolumn multirow includegraphics newcommand renewcommand def date uppercase authorrefmark
history doi titlepgskip keywords abstract bibliography bibliographystyle appendix tableofcontents newpage clearpage href texttt textsc textrm textsf mathrm mathbf mathit text frac le ge leq geq times cdot pm
approx ldots dots sim to rightarrow leftarrow in sum prod sqrt log exp max min Pr alpha beta delta Delta epsilon lambda mu sigma tau pi theta rho omega Omega Sigma ell nu phi chi psi gamma kappa eta
quad qquad hspace vspace noindent par linewidth textwidth columnwidth hfill vfill rule bigskip medskip smallskip ensuremath mbox tabular longtable endhead endfirsthead endfoot endlastfoot textasciitilde
textless textgreater textbackslash textregistered textcopyright textdegree textmu texttrademark ss i c u v ae oe slash lVert rVert lceil rceil lfloor rfloor mid neq ne equiv propto infty partial nabla
cup cap subset subseteq setminus emptyset forall exists neg land lor Rightarrow Leftrightarrow leftrightarrow mapsto circ bullet star ast oplus otimes langle rangle left right big Big bigg Bigg
tilde hat bar vec dot ddot overline underline widehat widetilde operatorname mathcal mathbb mathsf mathtt boldsymbol bm ref pageref eqref autoref nameref S P d e E N R Z Q C F G H K L M T V W X Y B A D
printbibliography addbibresource sloppy fussy raggedright raggedleft flushleft flushright center verb lstinline lstlisting scriptsize large Large LARGE huge Huge normalsize footnotetext thanks
phantom hphantom vphantom ldots cdots vdots ddots checkmark nolinebreak linebreak pagebreak nopagebreak allowbreak seqsplit protect relax expandafter csname endcsname@ if fi else ifx@ makeatletter makeatother
paragraph subparagraph arabic roman Roman alph Alph value setcounter addtocounter stepcounter refstepcounter thepage thesection newtheorem theoremstyle graphicspath DeclareMathOperator
IEEEoverridecommandlockouts IEEEauthorblockN IEEEauthorblockA IEEEkeywords IEEEPARstart IEEEtriggeratref IEEEtriggercmd IEEEcompsoctitleabstractindextext
""".split())


def strip_comments(t: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", t)


def main() -> int:
    bad = 0
    defs: set[str] = set()
    for n in P.glob("generated/numbers*.tex"):
        defs |= set(re.findall(r"\\(?:new|renew|provide)command\{\\(\w+)\}", n.read_text(encoding="utf-8")))
    bib = (P / "references.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    for f in ("main.tex", "supplement.tex", "supplement_full.tex"):
        raw = (P / f).read_text(encoding="utf-8")
        t = strip_comments(raw)
        local = set(re.findall(r"\\(?:new|renew|provide)command\*?\{?\\(\w+)", t)) | set(re.findall(r"\\def\\(\w+)", t))
        depth = 0
        for ch in re.sub(r"\\[{}]", "", t):
            depth += (ch == "{") - (ch == "}")
            if depth < 0:
                print(f, "closing brace without opening")
                bad += 1
                depth = 0
        if depth:
            print(f, "unbalanced braces:", depth)
            bad += 1
        st = []
        for k, e in re.findall(r"\\(begin|end)\{(\w+\*?)\}", t):
            if k == "begin":
                st.append(e)
            elif not st or st.pop() != e:
                print(f, "environment mismatch at", e)
                bad += 1
        if st:
            print(f, "unclosed environments", st)
            bad += 1
        used = set(re.findall(r"\\([A-Za-z]+)", t))
        und = sorted(m for m in used if m not in STD and m not in defs and m not in local)
        und = [m for m in und if m.startswith(("Rsev", "Lg", "Ledger"))]
        if und:
            print(f, "undefined number macros:", und)
            bad += len(und)
        for m in re.findall(r"\\input\{([^}]+)\}", t):
            if not (P / m).exists():
                print(f, "missing input", m)
                bad += 1
        for grp in re.findall(r"\\cite\{([^}]*)\}", t):
            for k in grp.split(","):
                if k.strip() not in keys:
                    print(f, "cite key not in references.bib:", k.strip())
                    bad += 1
        print(f, "checked")
    print("lint problems:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
