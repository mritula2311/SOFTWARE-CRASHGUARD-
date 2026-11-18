"""Append one row to docs/04_audits/FINALIZE.md: vf3_log.py ID check method RESULT evidence"""
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "docs/04_audits/FINALIZE.md"
HEAD = """# Finalize log

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | One row per check of the finalize run (branch final2, from submit-v2): ID, check, method, result, evidence. |
| Evidence labels used | none (this file reports no result of its own) |
| Abbreviations | PASS, FAIL, FIXED, NOT_RUN, BLOCKED |
<!-- header:end -->

| ID | Check | Method | Result | Evidence |
|---|---|---|---|---|
"""
if __name__ == "__main__":
    a = [x.replace("|", "/").replace("\n", " ") for x in sys.argv[1:]]
    assert len(a) == 5 and a[3] in ("PASS", "FAIL", "FIXED", "NOT_RUN", "BLOCKED"), a
    if not P.exists():
        P.write_text(HEAD, encoding="utf-8")
    with open(P, "a", encoding="utf-8") as f:
        f.write("| " + " | ".join(a) + " |\n")
