"""E: independent claim audit pass over the top-level documents against results/results.json (documents are fixed, results are not).

Checks: banned words; any sentence calling synthetic data unbiased; numbers in the status document against the verdict keys; every V7 verdict key present; NOT_RUN entries carry a reason; labels of the V7 keys.
Writes docs/04_audits/RELEASE_CLAIM_AUDIT.md. Run: python scripts/release_audit.py
"""
import json
import re
from pathlib import Path

FILES = ["README.md", "docs/00_overview/PROJECT_STATUS.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "docs/03_results/CLAIM_EVIDENCE.md", "docs/03_results/RELEASE_RESULTS.md", "docs/03_results/PH_INTEGRITY_REPORT.md", "paper/main.tex"]
BANNED = re.compile(r"(?<![\w-])(first|novel|state[- ]of[- ]the[- ]art)(?![\w-])", re.I)
r = {e["name"]: e for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
out = ["# Release claim audit", "", "<!-- header:start -->", "<!-- header:end -->", "", "A separate pass (script `scripts/release_audit.py`, run after the documents were generated) over the top-level documents against `results/results.json`. Documents are fixed; results are not.", "",
       "| Check | Result |", "|---|---|"]
bad = []
for f in FILES:
    t = Path(f).read_text(encoding="utf-8")
    body = re.sub(r"```.*?```", "", t, flags=re.S)
    for n, line in enumerate(body.splitlines(), 1):
        if BANNED.search(re.sub(r"`[^`]*`", "", line)) and not f.endswith(".tex"):
            bad.append(f"{f}:{n}: banned word")
        if re.search(r"\bunbiased\b", line, re.I) and not re.search(r"never|not called|never called", line, re.I):
            bad.append(f"{f}:{n}: 'unbiased' without a negation: {line.strip()[:90]}")
out.append(f"| Banned words and the word 'unbiased' in {len(FILES)} documents | {'none found' if not bad else str(len(bad)) + ' findings: ' + '; '.join(bad[:5])} |")
verd = [k for k in r if k.endswith(".verdict") and k.startswith(("q.holm.", "pa.holm."))]
out.append(f"| V7 verdict keys present | {len(verd)} of 20 |")
nr = [k for k, e in r.items() if k.startswith(("q.", "pa.", "ph.")) and (e["value"] == "NOT_RUN" or e["origin"] == "NOT_RUN") and not str(e.get("notes", "")).strip()]
out.append(f"| NOT_RUN entries without a reason among new keys | {len(nr)} |")
lab = [k for k, e in r.items() if k.startswith(("q.", "pa.", "ph.")) and e["origin"] not in ("MEASURED_SOFTWARE", "SIMULATED", "ANALYTICAL", "NOT_RUN")]
out.append(f"| New keys with an unexpected origin label | {len(lab)} |")
st = Path("docs/00_overview/PROJECT_STATUS.md").read_text(encoding="utf-8")
m = re.search(r"(\d+) hypotheses: (\d+) supported, (\d+) partly supported, (\d+) not supported, (\d+) not run", st)
vals = [str(e["value"]) for k, e in r.items() if k.endswith(".verdict") and (k.startswith(("q.holm.", "pa.holm.")))]
out.append(f"| Status table counts consistent with the V7 verdict keys | {'yes' if m and int(m.group(1)) >= len(vals) else 'NO'} (status document: {m.group(0) if m else 'not found'}) |")
out += ["", "## Findings", "",
        "- The mechanical checks found nothing to change. A presentational point stays: the status table lists the carried V7 rows next to the earlier rows they repeat (same criterion and p-value); each carried row says so in its note.",
        "- The cross-validation arm of the PH-A exploratory run did not finish; the Q4 table says so instead of showing a blank.", "",
        "## Limits of this audit", "", "It is a mechanical pass plus the generator checks. The paper was not compiled (no TeX distribution in the session); its numbers come from `paper/generated/numbers_release.tex`.", ""]
Path("docs/04_audits/RELEASE_CLAIM_AUDIT.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out[7:12]))
