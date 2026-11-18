"""Append one row to docs/04_audits/FINAL_VERIFICATION.md: vf_log.py ID check method RESULT evidence minutes"""
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "docs/04_audits/FINAL_VERIFICATION.md"
HEAD = """# Final verification log

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | One row per check of the final verification run (branch verify): ID, check, method, result, evidence, minutes. |
| Evidence labels used | none (this file reports no result of its own) |
| Abbreviations | PASS, FAIL, FIXED, NOT_RUN as defined in the run prompt |
<!-- header:end -->

| ID | Check | Method | Result | Evidence | Minutes |
|---|---|---|---|---|---|
"""
if __name__ == "__main__":
    a = [x.replace("|", "/") for x in sys.argv[1:]]
    assert len(a) == 6 and a[3] in ("PASS", "FAIL", "FIXED", "NOT_RUN"), a
    if not P.exists():
        P.write_text(HEAD, encoding="utf-8")
    with open(P, "a", encoding="utf-8") as f:
        f.write("| " + " | ".join(a) + " |\n")
