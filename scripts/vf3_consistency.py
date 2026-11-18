"""D5.2: consistency sweep of the delta verification run. For each fact, every line of the listed documents that mentions its topic must contain a canonical value (a number or a macro) or be listed for review.

    python scripts/vf3_consistency.py       (writes docs/04_audits/FINALIZE_CONSISTENCY.md)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}
DOCS = ["README.md", "CHANGELOG.md", "docs/00_overview/PROJECT_STATUS.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "paper/highlights.md", "paper/cover_letter.md", "paper/ABSTRACT_FACTS.md",
        "paper/main.tex", "paper/supplement.tex", "paper/REPRODUCE.md", "paper/PLACEHOLDERS.md"]
TITLE = "Measuring, Deciding and Reporting Crashes on Constrained LPWAN Nodes"


def n(key, d=0):
    v = R[key]
    return f"{v:,.{d}f}" if d == 0 else f"{v:.{d}f}"


FACTS = [
    ("T1 ledger: preregistered, versions", r"\d+ (preregistered )?hypotheses.{0,70}(version|preregistered|ledger|run)|ledger.{0,70}\d+ hypotheses", [n("r6.ledger.all.preregistered"), n("r6.ledger.all.versions"), r"\LedgerN", "LedgerVersions", "Ledger"]),
    ("T2 ledger: supported, not supported", r"\d+ supported, \d+ (partly|not) supported|\d+ supported \(|\d+ not supported, \d+ partly", [n("r6.ledger.all.supported"), n("r6.ledger.all.not_supported"), "Ledger", "Lg"]),
    ("T3 micro frame bytes", r"13[- ]byte|13 bytes", ["7", "8", "design", "RSixNsFrameBytes"]),
    ("T4 micro airtime over the two-stage alert", r"micro.{0,80}airtime|airtime.{0,60}micro", ["0.46", "0.77", "RSixAirOverRThree", "RSixNinePerDeliv", "R3", "two-stage", "RSixMicroOverRNine", "7-byte", "13 bytes", "14-byte", "per delivered"]),
    ("T5 0.901 is the supplied-split recall", r"0\.901|VzRecSup", ["supplied", "VzRecNear", "VzROne", "Vz"]),
    ("T6 R6-2 premise error", r"720 to 780|RSixPreregLo", ["112", "RSixFixedMeanMs", "median", "mean decision time", "disclos"]),
    ("T7 layout still open (stale statements)", r"not yet specified|layout .{0,30}(open|unspecified)|byte layout of the freshness field.{0,40}not", ["Now specified", "closed", "was missing", "FRAME_LAYOUT", "resolved", "B5"]),
    ("T8 title", r"Measuring, Deciding|What a Low-Cost Crash-Alert Node Must Measure", [TITLE]),
    ("T9 lockout and duty model", r"off-time|lockout", ["hourly", "DutyLock", "DutyCrit", "ANALYTICAL", "evaluated", "do not transfer", "not evaluated", "DELTA_DUTY", "Future work", "DELTA DUTY", "Duty lockout"]),
    ("T10 preemption", r"preempt", ["design recommendation", "r3a", "FIFO", "PreemptSave", "PreemptEnd", "enumerat", "vf2.preempt", "recommend", "vf2_preempt"]),
    ("T11 quarantine", r"quarantine", ["verification", "two counters", "RSixQuarFrames", "verified", "L8", "by construction", "per-cell", "bounded", "model", "exploration"]),
    ("T12 hardware claim", r"physical hardware|hardware measurement", ["No", "no ", "not", "NOT", "separately", "design only", "Software only"]),
    ("T14 micro frame size (stale 7-byte statements)", r"7-byte micro|micro.{0,50}7-byte|7-byte (design|frame)", ["8-byte", "7-byte core", "7-byte frame of", "cg_micro_pack", "7-byte lookup", "trial", "evaluated", "historical", "Round 6", "round-6"]),
    ("T15 Indian rules still called unverified", r"UNVERIFIED|not verified.{0,60}(India|433)|(India|433).{0,80}not verified|secondary summary", ["superseded", "Superseded", "G.S.R", "read in full", "full text", "VERIFIED:", "frozen", "historical"], ["README.md", "paper/main.tex", "paper/supplement.tex", "paper/cover_letter.md", "paper/PLACEHOLDERS.md", "docs/03_results/ASSUMPTIONS.md", "docs/00_overview/LIMITATIONS.md", "docs/00_overview/PROJECT_STATUS.md", "paper/REPRODUCE.md"]),
    ("T13 part numbers in the paper body", r"ESP32|SX1278|SW-420", ["ESP32-class", "profile", "target"], ["paper/main.tex"]),
]
out = []
rows = []
for name, topic, canon, *scope in FACTS:
    pat = re.compile(topic, re.I)
    found = 0
    bad = []
    for d in (scope[0] if scope else DOCS):
        p = ROOT / d
        if not p.exists():
            continue
        for ln, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if pat.search(line):
                found += 1
                if not any(c in line for c in canon):
                    bad.append((d, ln, " ".join(line.split())[:150]))
    rows.append((name, found, len(bad)))
    out += [(name, *b) for b in bad]
REVIEWED = {("README.md", 28): "family-level count of the combined run (two Holm families), a different quantity",
            ("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", 20): "a claim about the H-C3 stress test, not a count",
            ("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", 90): "a claim about the H-C3 stress test, not a count",
            ("docs/00_overview/PROJECT_STATUS.md", 92): "H-R2a is about a 7 or 8 byte tag of a 40-byte frame, not the micro frame",
            ("docs/00_overview/PROJECT_STATUS.md", 181): "same hypothesis row",
            ("paper/main.tex", 26): "the abstract line contains '97-byte', which the pattern matches; the abstract states no 7-byte micro frame",
            ("docs/00_overview/LIMITATIONS.md", 31): "unverified severity constants (ASI filter, THIV), unrelated to the Indian rules",
            ("README.md", 14): "project description of the software-only study, no hardware result is claimed"}
reviewed = [(a, b, c, d, REVIEWED[(b, c)]) for a, b, c, d in out if (b, c) in REVIEWED]
out = [o for o in out if (o[1], o[2]) not in REVIEWED]
# the title is the same in the cover letter, the supplement and the manuscript
title_ok = {d: TITLE in (ROOT / d).read_text(encoding="utf-8") for d in ("paper/main.tex", "paper/supplement.tex", "paper/cover_letter.md")}
L = ["# Consistency sweep of the finalize run", "", "<!-- header:start -->", "<!-- header:end -->", "",
     "Generated by `python scripts/vf3_consistency.py`. For each fact, every line of README, CHANGELOG, project status, claims for the cover letter, highlights, cover letter, abstract facts, manuscript, supplement, REPRODUCE and PLACEHOLDERS that mentions the topic must contain a canonical value (number or macro of the fact) or is listed for review.", "",
     "| Fact | Lines that mention it | Lines to review |", "|---|---:|---:|"] + [f"| {a} | {b} | {c} |" for a, b, c in rows]
L += ["", f"Title in the manuscript, the supplement and the cover letter: {', '.join(f'{k} {chr(121) + chr(101) + chr(115) if v else chr(78) + chr(79)}' for k, v in title_ok.items())}.", "", "## Lines reviewed and found not to be a conflict", ""]
L += ["| Fact | Document | Line | Reason |", "|---|---|---:|---|"] + [f"| {a} | `{b}` | {c} | {e} |" for a, b, c, d, e in reviewed]
L += ["", "## Lines to review", ""]
L += ["| Fact | Document | Line | Text |", "|---|---|---:|---|"] + [f"| {a} | `{b}` | {c} | {d.replace('|', '/')} |" for a, b, c, d in out]
(ROOT / "docs/04_audits/FINALIZE_CONSISTENCY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(len(out), "lines to review;", len(reviewed), "reviewed;", title_ok)
for o in out[:60]:
    print(o)
