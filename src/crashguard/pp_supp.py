"""P4: the supplement (paper/supplement.tex) from the generated result documents of the repository.

    python -m crashguard.pp_supp

The documents named below are generated from results/results.json by their own generators (and checked by the audits of their rounds); this module converts them to LaTeX (scripts/pp_md2tex.py) without changing a number.
Numbers typed in supplement.tex itself come from generated/numbers.tex.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import pp_md2tex as M  # noqa: E402

OUT = ROOT / "paper" / "generated" / "supp"
SECTIONS = [
    ("Hypothesis ledger and preregistration summary", "ledger", ["docs/04_audits/HYPOTHESIS_LEDGER.md"]),
    ("Frame layout, working flow and the formal abstraction table", "layout", ["docs/05_architecture/FRAME_LAYOUT.md"]),
    ("Duty lockout after the provisional flash and the gating rule", "duty", ["docs/03_results/DELTA_DUTY_LOCKOUT.md"]),
    ("Duplicate audit as a procedure and split sensitivity", "audit", ["docs/03_results/DELTA_AUDIT_METHOD.md"]),
    ("Negative results by layer", "negs", ["docs/04_audits/NEGATIVES_BY_LAYER.md"]),
    ("Formal models: reruns and comparison with the frame layout", "formal", ["docs/04_audits/FORMAL_RERUN.md", "docs/04_audits/DELTA_FORMAL_RERUN.md", "docs/04_audits/FORMAL_FIELD_CHECK.md"]),
    ("Data sources, licences and hashes", "data", ["docs/05_data_code/DATA_SOURCES.md"]),
    ("ns-3 patch check", "nspatch", ["docs/03_results/VF_NS3_RERUN.md"]),
    ("Assumptions of every simulation (Table S1)", "assumptions", ["docs/03_results/ASSUMPTIONS.md", "docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md"]),
    ("Preregistrations V5 to V14 with their addenda", "prereg", ["docs/02_preregistration/PREREGISTRATION_V5.md", "docs/02_preregistration/PREREGISTRATION_V7.md", "docs/02_preregistration/PREREGISTRATION_V11.md",
                                                                  "docs/02_preregistration/PREREGISTRATION_V12.md", "docs/02_preregistration/PREREGISTRATION_V13.md", "docs/02_preregistration/PREREGISTRATION_V14.md"]),
    ("Hypothesis tables by family, with counts", "hyp", ["docs/00_overview/PROJECT_STATUS.md", "docs/03_results/STATUS_REVERIFY.md"]),
    ("Retry-policy and protocol candidates D1 to D4 and R1 to R4: full tables", "dr", ["docs/03_results/REDESIGN_DECISION_TABLE.md", "docs/03_results/REDESIGN_A_RESULTS.md", "docs/03_results/REDESIGN_B_RESULTS.md",
                                                                                      "docs/03_results/COMBINED_VERDICTS.md"]),
    ("Simulator calibration and cross-simulator verdicts", "xsim", ["docs/03_results/XSIM_CALIBRATION.md", "docs/03_results/XSIM_VERDICTS.md", "docs/03_results/XSIM_BUILD.md"]),
    ("V14 and V13: traces, formal checks, two-stage alert, energy budget", "round3", ["docs/03_results/ROUND3_RESULTS.md", "docs/03_results/ROUND3_DECISION_TABLE.md", "docs/03_results/PAPER_P1_R3_NS3.md", "docs/03_results/H_C3_PROVENANCE.md"]),
    ("V15: short repeated provisional alert, receiver diversity, second prover (negative results)", "round4", ["docs/02_preregistration/PREREGISTRATION_V15.md", "docs/03_results/A4_RESULTS.md", "docs/03_results/A4_DECISION_TABLE.md", "docs/03_results/A4_A3_PROVERIF.md", "docs/03_results/A4_CODE_VERIFICATION.md"]),
    ("V16: ten algorithms and one added after the initial session (L1 to L11)", "round5", ["docs/02_preregistration/PREREGISTRATION_V16.md", "docs/03_results/ROUND5_RESULTS.md", "docs/03_results/ROUND5_DECISION_TABLE.md", "docs/03_results/R5_CODE_VERIFICATION.md"]),
    ("V17: round 6 (micro-confirm, formal extensions, sequential exit, footprint, bounds)", "round6", ["docs/02_preregistration/PREREGISTRATION_V17.md", "docs/03_results/ROUND6_RESULTS.md", "docs/03_results/ROUND6_R1_MICRO.md", "docs/03_results/ROUND6_R2_SEQUENTIAL.md", "docs/03_results/ROUND6_FOOTPRINT.md", "docs/03_results/ROUND6_BOUNDS.md"]),
    ("V18: round 7 (duty-budget reserve, pseudonymous ids)", "round7", ["docs/02_preregistration/PREREGISTRATION_V18.md", "docs/03_results/ROUND7_RESULTS.md", "docs/03_results/ROUND7_A.md", "docs/03_results/ROUND7_B.md", "docs/01_literature/R7_PRIOR_ART.md"]),
    ("V19: round 7b (four-event reserve on fresh seeds) and deviations", "round7b", ["docs/02_preregistration/PREREGISTRATION_V19.md", "docs/03_results/ROUND7B_RESULTS.md", "docs/03_results/ROUND7B_DEVIATIONS.md"]),
    ("Simulated hardware-format variants and failure maps", "simhw", ["docs/03_results/SIMHW_VARIANTS.md", "docs/03_results/SIMHW_RESULTS.md"]),
    ("Synthetic-generator realism gate", "synth", ["docs/03_results/PH_INTEGRITY_REPORT.md", "docs/05_data_code/SYNTHETIC_PROVENANCE.md", "docs/03_results/DIAGNOSIS_SYNTH.md"]),
    ("Code-verification report", "codever", ["docs/03_results/CODE_VERIFICATION.md"]),
    ("Reviewer-response pack", "reviewer", ["docs/09_review/REVIEWER_RESPONSES.md"]),
    ("Bench protocol for the two-stage alert", "bench", ["docs/08_hardware/R3_BENCH_PROTOCOL.md"]),
    ("Literature search log and novelty matrix (journal articles from 2021)", "lit", ["docs/06_references/LIT_QUERIES_2021PLUS.md", "docs/06_references/NOVELTY_MATRIX_2021PLUS.md", "docs/01_literature/LITERATURE_FINAL_CHECK.md"]),
]


# D4.2 (delta verification): the supplement keeps the preregistration summary and ledger, the frame layout and formal abstraction table, the duty and audit analyses, the formal results, one decision table per round,
# the assumptions table, the data sources and the bench protocol. Every other converted document is in the release archive under supplementary_full/ (paper/supplement_full.tex and its PDF, and the Markdown sources).
KEPT: dict[str, list[str]] = {
    "ledger": ["docs/04_audits/HYPOTHESIS_LEDGER.md"],
    "layout": ["docs/05_architecture/FRAME_LAYOUT.md"],
    "duty": ["docs/03_results/DELTA_DUTY_LOCKOUT.md"],
    "audit": ["docs/03_results/DELTA_AUDIT_METHOD.md"],
    "formal": ["docs/04_audits/FORMAL_RERUN.md", "docs/04_audits/DELTA_FORMAL_RERUN.md"],
    "round3": ["docs/03_results/ROUND3_DECISION_TABLE.md"],
    "round4": ["docs/03_results/A4_DECISION_TABLE.md"],
    "round5": ["docs/03_results/ROUND5_DECISION_TABLE.md"],
    "round6": ["docs/03_results/ROUND6_RESULTS.md", "docs/03_results/ROUND6_BOUNDS.md"],
    "round7": ["docs/03_results/ROUND7_RESULTS.md", "docs/03_results/ROUND7_A.md", "docs/03_results/ROUND7_B.md"],
    "round7b": ["docs/03_results/ROUND7B_RESULTS.md", "docs/03_results/ROUND7B_DEVIATIONS.md"],
    "assumptions": ["docs/03_results/ASSUMPTIONS.md"],
    "data": ["docs/05_data_code/DATA_SOURCES.md"],
    "bench": ["docs/08_hardware/R3_BENCH_PROTOCOL.md"],
}
KEPT_TITLES = {"round3": "Round 3 (V14): decision table", "round4": "Round 4 (V15): decision table", "round5": "Round 5 (V16): decision table", "round6": "Round 6 (V17): decision table and bounds", "round7": "Round 7 (V18): duty-budget reserve and pseudonymous ids", "round7b": "Round 7b (V19): four-event reserve and deviations"}

HEAD = r"""% Supplement of the combined paper. Generated by crashguard.pp_supp; the included files in generated/supp/ are conversions of the repository's result documents.
\documentclass[10pt,a4paper]{article}
\usepackage[margin=1.8cm]{geometry}
\usepackage{booktabs,longtable,amsmath,amssymb,graphicx,url,textcomp}
\input{generated/numbers.tex}
\input{generated/numbers_r7.tex}
\input{generated/numbers_r7b.tex}
\title{Supplement to: Measuring, Deciding and Reporting Crashes on Constrained LPWAN Nodes: Benchmark Audit, Sensing Bounds, Formally Verified Alerting and Trace-Driven Evaluation}
\author{Mritula S}
\date{}
\begin{document}
\maketitle
\tableofcontents

\section{Scope, labels and versions}
This supplement holds the hypothesis ledger with the preregistration summary, the frame layout with the table of abstractions between the formal models and the layout, the duty-lockout analysis, the duplicate-audit procedure, the formal results, one decision table per round, the assumptions of the simulations, the data sources and the bench protocol. Everything else (the full preregistrations, the other result tables, the code-verification reports, the literature log and the reviewer-response pack) is in the release archive under \texttt{supplementary\_full/}, with the compiled full supplement (\texttt{supplement\_full.pdf}); the last section lists the paths. Every result carries one evidence label: MEASURED\_SOFTWARE, SIMULATED, SIMULATED\_HW\_FORMAT, TRACE\_DRIVEN, FORMAL, ANALYTICAL, EMULATED or NOT\_RUN. No label claims a hardware measurement. The included tables are converted from the repository's generated documents without changing a number; where a document and \texttt{results/results.json} could differ, the stored value wins.

\textbf{Hypothesis counts.} \LedgerN{} hypotheses were preregistered in \LedgerVersions{} versions; \LedgerRun{} were run; \LedgerSupp{} are supported, \LedgerNot{} not supported, \LedgerPartly{} partly supported and \LedgerNotRun{} not run. Each version has its own Holm family and the families are never merged. The ledger with one row per hypothesis follows in the section on the ledger; versions V6 and V8 to V10 do not exist as files.

\textbf{Tools.} Tamarin 1.12.0 with Maude 3.5.1 (WSL, single thread, 5 GB, one run per lemma with a time limit); the model files are \texttt{formal/crash\_alert\_auth.spthy}, \texttt{formal/crash\_alert\_fresh.spthy} and the design variant \texttt{formal/crash\_alert\_fresh\_bootctr.spthy} and the car-side model \texttt{formal/crash\_alert\_carid.spthy} (design variant with a boot counter; the id lemma was not decided in any formulation), with outputs in \texttt{formal/out/}. Round 4 added the Tamarin models \texttt{formal/crash\_alert\_prov.spthy} and \texttt{formal/crash\_alert\_prov\_fresh.spthy} and ProVerif 2.05 (built from source in WSL) with the models in \texttt{formal/proverif/}. ns-3.48 with the lorawan module (commit e45b4af, local changes in the build record included below). Python with pinned requirements (\texttt{requirements.lock}); seed 42 and seeds 0 to 4.

\textbf{Two-stage alert in ns-3 (P1).} \NsRuns{} runs; \NsSupported{} of 8 preregistered tests supported; the ns-3 verdict is \NsVerdict{}; the largest share of dropped events in a cell is \NsDropMax\% and the largest trailing-hour airtime of any vehicle is \NsDutyMax{} s against a 36 s allowance.
"""


def build(sections: list[tuple[str, str, list[str]]], full: bool) -> str:
    body = [HEAD if not full else HEAD.replace(r"\section{Scope, labels and versions}", r"\section{Scope, labels and versions (full supplement)}")]
    for title, tag, files in sections:
        body.append(f"\n\\section{{{M.esc(title)}}}")
        for f in files:
            p = ROOT / f
            if not p.exists():
                body.append(f"\n\\paragraph{{Missing}} {M.esc(f)}\n")
                continue
            name = f"{tag}_{p.stem}.tex"
            (OUT / name).write_text(M.convert(p.read_text(encoding="utf-8"), level0=1), encoding="utf-8")
            body.append(f"\n\\subsection{{{M.esc(p.stem.replace('_', ' '))}}}\n\\input{{generated/supp/{name}}}")
    return "\n".join(body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    full_body = build(SECTIONS, True) + "\n\\end{document}\n"
    (ROOT / "paper" / "supplement_full.tex").write_text(full_body, encoding="utf-8")
    reduced = [(KEPT_TITLES.get(tag, title), tag, KEPT[tag]) for title, tag, files in SECTIONS if tag in KEPT]
    seen, merged = set(), []
    for title, tag, files in reduced:  # one section per tag
        if tag in seen:
            continue
        seen.add(tag)
        merged.append((title, tag, files))
    text = build(merged, False)
    kept_files = {f for _t, _g, fs in merged for f in fs}
    rows = [(title, f) for title, _tag, fs in SECTIONS for f in fs if f not in kept_files]
    text += "\n\\section{Documents in the release archive}\nThe documents below are in the release archive under \\texttt{supplementary\\_full/}, at the path shown, and in \\texttt{supplement\\_full.pdf} (built from \\texttt{paper/supplement\\_full.tex}).\n\n"
    text += "{\\footnotesize\\begin{itemize}\\setlength{\\itemsep}{0pt}\n"
    text += "\n".join(f"\\item {M.esc(t)}: \\path{{supplementary_full/{f}}}" for t, f in rows)
    text += "\n\\end{itemize}}\n\n\\end{document}\n"
    (ROOT / "paper" / "supplement.tex").write_text(text, encoding="utf-8")
    print("supplement written:", len(merged), "sections kept,", len(rows), "documents moved to supplementary_full/")


if __name__ == "__main__":
    main()
