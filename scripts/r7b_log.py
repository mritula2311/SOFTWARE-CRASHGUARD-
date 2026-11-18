"""Append one row to docs/04_audits/ROUND7B.md: r7_log.py ID check method RESULT evidence"""
import sys
from pathlib import Path
P = Path(__file__).resolve().parents[1] / "docs/04_audits/ROUND7B.md"
HEAD = """# Round 7b log

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | One row per step of round 7b (branch round7b): ID, check, method, result, evidence. |
| Evidence labels used | ANALYTICAL, SIMULATED, FORMAL, MEASURED_SOFTWARE |
| Abbreviations | ACK = acknowledgement frame; PASS, FAIL, NOT_RUN, BLOCKED, INFO |
<!-- header:end -->

| ID | Check | Method | Result | Evidence |
|---|---|---|---|---|
"""
if __name__ == "__main__":
    a = [x.replace("|", "/").replace("\n", " ") for x in sys.argv[1:]]
    assert len(a) == 5 and a[3] in ("PASS", "FAIL", "FIXED", "NOT_RUN", "BLOCKED", "INFO"), a
    if not P.exists():
        P.write_text(HEAD, encoding="utf-8")
    with open(P, "a", encoding="utf-8") as f:
        f.write("| " + " | ".join(a) + " |\n")
