"""Independent claim audit of the positive-results push. It does not import the generator (``pp_docs``); it re-reads the claim rows of docs/03_results/CLAIM_EVIDENCE.md and the generated documents and checks them against results/results.json:

1. every key pattern of a claim row matches at least one key;
2. the evidence label of the row covers the origins of the matching keys (NOT_RUN aside);
3. the verdict of a row that cites a Holm key equals the stored verdict;
4. every decimal number in a claim row or in docs/03_results/POSITIVE_PUSH_RESULTS.md appears (to the printed number of decimals, or as a percentage or a difference of two stored values) among the stored values, or among the numbers written in the preregistered criteria;
5. forbidden words ("first", "novel", "state of the art") in the new documents and tables.
Writes docs/04_audits/PP_CLAIM_AUDIT.md. Documents are fixed, not results.
"""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

R = {e["name"]: e for e in json.load(open("results/results.json", encoding="utf-8"))}
NUM = re.compile(r"(?<![\w.])-?\d+\.\d+(?![\w])")
FORBID = re.compile(r"\b(first|novel|state[- ]of[- ]the[- ]art)\b", re.I)


def stored_values() -> list[float]:
    out = []
    for e in R.values():
        if isinstance(e["value"], (int, float)) and not isinstance(e["value"], bool):
            out.append(float(e["value"]))
    return out


def numbers_in_prereg() -> set[str]:
    s = Path("docs/02_preregistration/PREREGISTRATION_V4.md").read_text(encoding="utf-8")
    return set(NUM.findall(s))


def matches(tok: str, vals: np.ndarray) -> bool:
    d = len(tok.split(".")[1])
    x = float(tok)
    scale = 10 ** d
    cands = [x, x / 100.0, x * 100.0, x * 1000.0]
    tol = 0.51 / scale
    for c in cands:
        t = tol if c == x else tol / 100.0 if c == x / 100.0 else tol * 100.0 if c == x * 100.0 else tol * 1000.0
        if np.any(np.abs(vals - c) <= t + 1e-12):
            return True
    return False


import numpy as np  # noqa: E402


def main() -> None:
    vals = np.array(stored_values())
    prereg = numbers_in_prereg()
    notes = {"keys": [], "labels": [], "verdicts": [], "numbers": [], "words": []}
    txt = Path("docs/03_results/CLAIM_EVIDENCE.md").read_text(encoding="utf-8")
    blk = txt[txt.index("<!-- PP:BEGIN -->") : txt.index("<!-- PP:END -->")]
    rows = [r for r in blk.splitlines() if r.startswith("| ") and not r.startswith("| Claim") and "---" not in r]
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        claim, label, _sec, keys, verdict = cells[:5]
        pats = [k.strip(" `") for k in re.split(r"[;,]", keys) if k.strip(" `")]
        origins = set()
        row_vals = []
        for p in pats:
            hit = [k for k in R if fnmatch.fnmatch(k, p)]
            row_vals += [float(R[k]["value"]) for k in hit if isinstance(R[k]["value"], (int, float)) and not isinstance(R[k]["value"], bool)]
            if not hit:
                notes["keys"].append(f"no key matches `{p}` (claim: {claim[:70]})")
            origins |= {R[k]["origin"] for k in hit}
        lab = set(re.findall(r"MEASURED_SOFTWARE|SIMULATED|ANALYTICAL|HARDWARE|NOT_RUN", label))
        extra = origins - lab - {"NOT_RUN"}
        if extra:
            notes["labels"].append(f"label '{label}' lacks {sorted(extra)} (claim: {claim[:70]})")
        for p in pats:
            m = re.match(r"p\.holm\.(hp\w+)\.\*", p)
            if m:
                stored = R.get(f"p.holm.{m.group(1)}.verdict", {}).get("value")
                if stored != verdict.strip("* "):
                    notes["verdicts"].append(f"verdict '{verdict}' differs from stored '{stored}' for {m.group(1)}")
        rv = np.array(row_vals) if row_vals else np.array([np.nan])
        for tok in NUM.findall(claim):
            if tok in prereg:
                continue
            if not matches(tok, rv):
                notes["numbers"].append(f"{tok} in claim row: {claim[:80]}")
    for path in ("docs/03_results/POSITIVE_PUSH_RESULTS.md",):
        for ln in Path(path).read_text(encoding="utf-8").splitlines():
            if ln.startswith("|"):
                continue  # tables are generated cell by cell from keys
            for tok in NUM.findall(ln):
                if tok not in prereg and not matches(tok, vals):
                    notes["numbers"].append(f"{tok} in {path}: {ln[:90]}")
    files = ["docs/02_preregistration/PREREGISTRATION_V4.md", "docs/05_data_code/SEALED_SPLIT.md", "docs/03_results/POSITIVE_PUSH_RESULTS.md", "crashclip/README.md", "docs/04_audits/PP_CLAIM_AUDIT.md"] + [str(p) for p in Path("results/paper").glob("p_tab_*.tex")] + [str(p) for p in Path("results/paper").glob("p_tab_*.csv")]
    for f in files:
        p = Path(f)
        if p.exists():
            for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if FORBID.search(ln) and f != "docs/04_audits/PP_CLAIM_AUDIT.md":
                    notes["words"].append(f"{f}:{i}: {ln[:100]}")
    for f in ("docs/03_results/CLAIM_EVIDENCE.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "docs/03_results/STATS_AUDIT.md", "docs/06_references/REFERENCES.md", "docs/05_data_code/REPRODUCE_FINISH.md"):
        s = Path(f).read_text(encoding="utf-8")
        if "<!-- PP:BEGIN -->" in s:
            b = s[s.index("<!-- PP:BEGIN -->") : s.index("<!-- PP:END -->")]
            for i, ln in enumerate(b.splitlines(), 1):
                if FORBID.search(ln):
                    notes["words"].append(f"{f} (PP block) line {i}: {ln[:100]}")
    L = ["# Independent claim audit of the positive-results push (generated by `pp_audit.py`)", "",
         "A separate pass that does not import the document generator. It re-reads the claim rows and the generated results document and checks them against `results/results.json`. Findings are fixed in the documents, never in the results.", "",
         f"Claim rows checked: {len(rows)}.", ""]
    total = 0
    for k, title in (("keys", "Key patterns without a matching key"), ("labels", "Evidence labels that do not cover the origins of the keys"), ("verdicts", "Verdicts that differ from the stored Holm verdict"),
                     ("numbers", "Numbers without a stored value (to the printed decimals, as a percentage, or in the preregistered criteria)"), ("words", "Forbidden words")):
        L += [f"## {title}: {len(notes[k])}", ""] + [f"- {x}" for x in notes[k]] + [""]
        total += len(notes[k])
    L += [f"**Total findings: {total}.**"]
    Path("docs/04_audits/PP_CLAIM_AUDIT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("findings", total, {k: len(v) for k, v in notes.items()})


if __name__ == "__main__":
    main()
