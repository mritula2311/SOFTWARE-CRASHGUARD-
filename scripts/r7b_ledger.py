"""Round 7b G6: ledger with V19 (keys r7b.ledger.*, ANALYTICAL) and the ledger document. Idempotent. Also removes duplicated rows that an earlier rerun left in the document (the V18 totals row and three rows of the round-7 table)."""

# ruff: noqa: E402  (the guard below runs before the imports on purpose)
raise SystemExit('r7b_ledger.py is a one-time script that was already applied in round 7b. Running it again would drop the V19 row of the Versions table of the ledger and reorder results/results.json. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard.results import record_many  # noqa: E402

R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
V19 = dict(preregistered=2, run=2, supported=int(R["r7b.decide.hR7b_1.supported"]) + int(R["r7b.decide.hR7b_2.supported"]), partly=0, not_run=0)
V19["not_supported"] = V19["run"] - V19["supported"] - V19["partly"]
ALL = {k: int(R[f"r7.ledger.all.{k}"]) + V19[k] for k in ("preregistered", "run", "supported", "not_supported", "partly", "not_run")}
ALL["versions"] = int(R["r7.ledger.all.versions"]) + 1
ALL["confirmatory_rows"] = int(R["r7.ledger.all.confirmatory_rows"]) + 2
ALL["confirmatory_supported"] = int(R["r7.ledger.all.confirmatory_supported"]) + V19["supported"]
ent = []
for k, v in V19.items():
    ent.append(dict(name=f"r7b.ledger.V19.{k}", value=v, unit="hypotheses", origin="ANALYTICAL", source_file="scripts/r7b_ledger.py", notes="V19 adds H-R7b-1 and H-R7b-2; the formal checks are not hypotheses"))
for k, v in ALL.items():
    ent.append(dict(name=f"r7b.ledger.all.{k}", value=v, unit="hypotheses", origin="ANALYTICAL", source_file="scripts/r7b_ledger.py", notes="r7.ledger.all plus V19"))
record_many(ent, purge_prefixes=("r7b.ledger.",))

p = ROOT / "docs" / "04_audits" / "HYPOTHESIS_LEDGER.md"
b = p.read_bytes().decode("utf-8")
crlf = "\r\n" in b
t = b.replace("\r\n", "\n")
if "## Round 7b (V19)" in t:
    t = t[: t.index("## Round 7b (V19)")].rstrip("\n") + "\n"
lines, out, seen_sec = t.split("\n"), [], False
for ln in lines:
    if ln.startswith("## Round 7 (V18)"):
        seen_sec = True
    if ln.startswith("| all |"):
        out.append("| V19 | {preregistered} | {run} | {supported} | {not_supported} | {partly} | {not_run} |".format(**V19))
        out.append("| all | {preregistered} | {run} | {supported} | {not_supported} | {partly} | {not_run} |".format(**ALL))
        continue
    if ln.startswith("Confirmatory-family rows"):
        out.append(f"Confirmatory-family rows (a Holm p-value in a stated family; V12 counted as one family of 10): {ALL['confirmatory_rows']} rows, {ALL['confirmatory_supported']} supported, {68 + V19['not_supported']} not supported, 3 partly, 12 NOT_RUN (V18 adds five rows to the family: H-R7-A1, A2, B1, B2, B3; V19 adds two: H-R7b-1, H-R7b-2).")
        continue
    if ln.startswith("| V19 |"):
        continue
    out.append(ln)
# remove exact duplicate table rows (keep the first copy), only rows that start with '|' and carry an id
dedup, seen = [], set()
for ln in out:
    if ln.startswith("| V18 | 6 |") or ln.startswith("| H-R7-"):
        if ln in seen:
            continue
        seen.add(ln)
    dedup.append(ln)
sec = [
    "", "", "## Round 7b (V19)", "",
    "`docs/02_preregistration/PREREGISTRATION_V19.md`, committed before any round-7b run (SHA-256 of the file with CRLF read as LF: 6b6f4a0d9085ce455bbb317ff36aaa7e9ec78f1389323ea741c6e2ef1566bd2d). Holm over two hypotheses. The reserve size (four events) was chosen from round-7 data, so this is a confirmation on fresh seeds and not a blind test; the thresholds are those of V18.", "",
    "| ID | Hypothesis | Family | Data role | Result | Holm p | Label | Paper |", "|---|---|---|---|---|---:|---|---|",
    f"| H-R7b-1 | reserve for four events keeps the follow-up within D_max in at least 99% of runs under full ACK suppression, every cell | V19, Holm over 2 | fresh seeds 100 to 105; stored event table | {'SUPPORTED' if R['r7b.decide.hR7b_1.supported'] else 'NOT SUPPORTED'} | {R['r7b.decide.hR7b_1.p']:.2e} | SIMULATED | C4 round-7 paragraph |",
    f"| H-R7b-2 | benign cost of the four-event reserve at most 1 point of delivery and 10% of the median time, every cell | V19, Holm over 2 | LoED half 0, fresh start points (seed 4242); the old policy as control | {'SUPPORTED' if R['r7b.decide.hR7b_2.supported'] else 'NOT SUPPORTED'} | {R['r7b.decide.hR7b_2.p']:.3g} | TRACE_DRIVEN | C4 and the negative-results table |",
]
t = "\n".join(dedup).rstrip("\n") + "\n" + "\n".join(sec) + "\n"
p.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print(V19, ALL)
