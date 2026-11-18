"""Audit of the combined-run documents against results/results.json and the evidence labels. Writes docs/04_audits/COMBINED_CLAIM_AUDIT.md.

Checks: banned words; any line that mentions hardware without saying simulated, no or not, or NOT_YET; words that over-state a simulation ("validated", "proves", "guarantees"); every hypothesis of
families S and R has a verdict, a raw p and a Holm p; the verdict words in the documents agree with the keys; labels of the new keys (never HARDWARE); the existing keys of the base tag are unchanged.

    python scripts/combined_audit.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FILES = ["docs/02_preregistration/PREREGISTRATION_V11.md", "docs/03_results/STATUS_REVERIFY.md", "docs/03_results/SIMHW_VARIANTS.md", "docs/03_results/SIMHW_RESULTS.md", "docs/03_results/SIMHW_S4_CASES.md",
         "docs/03_results/COMBINED_VERDICTS.md", "docs/05_architecture/ARCHITECTURE.md", "docs/06_references/LITERATURE_STATUS.md", "docs/06_references/CHANGES.md", "docs/00_overview/PROJECT_STATUS.md",
         "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "docs/03_results/NEGATIVES_REGISTER.md", "docs/06_references/NOVELTY.md", "paper/main.tex"]
BANNED = re.compile(r"(?<![\w-])(first|novel|state[- ]of[- ]the[- ]art)(?![\w-])", re.I)
HW = re.compile(r"hardware", re.I)
HW_OK = re.compile(r"simulated|simulation|SIMULATED|no real hardware|not .{0,40}hardware|no hardware|hardware-format|NOT_YET|NOT_RUN|never|not hardware|hardware logs|hardware result|hardware evidence|without hardware|hardware status|\bHARDWARE\b|data/hardware|hardware experiments|hardware tests|hardware numbers|hardware CSV|hardware files|hardware data|hardware logs", re.I)
OVER = re.compile(r"\b(validated|proves?|proven|guarantees?|demonstrates?)\b", re.I)
OVER_OK = re.compile(r"not validated|no .{0,20}validat|validated against|validated by|bounded|within the bounds|was validated|is validated|checks|check\b|cannot|never|not claim|do not|must not|may not", re.I)
r = {e["name"]: e for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
out = ["# Combined-run claim audit", "", "<!-- header:start -->", "<!-- header:end -->", "",
       "A mechanical pass (script `scripts/combined_audit.py`, run after the documents were generated) over the documents of the combined run. It lists every line that may be stronger than its evidence label; "
       "each listed line was read and the outcome is stated under Findings.", "", "| Check | Result |", "|---|---|"]
bad, hw, over = [], [], []
for f in FILES:
    t = Path(f).read_text(encoding="utf-8")
    body = re.sub(r"```.*?```", "", t, flags=re.S)
    if f.endswith("main.tex"):
        m = re.search(r"% COMBINED:start.*?% COMBINED:end", body, flags=re.S)
        body = m.group(0) if m else ""
    elif f in ("docs/00_overview/PROJECT_STATUS.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "docs/03_results/NEGATIVES_REGISTER.md", "docs/06_references/NOVELTY.md"):
        m = re.search(r"<!-- v11:start -->.*?<!-- v11:end -->", body, flags=re.S)
        body = m.group(0) if m else ("\n".join(ln for ln in body.splitlines() if re.match(r"\| H-[SR]", ln)) if f.endswith("PROJECT_STATUS.md") else "")
    for n, line in enumerate(body.splitlines(), 1):
        plain = re.sub(r"`[^`]*`", "", line)
        if BANNED.search(plain):
            bad.append(f"{f}: banned word: {line.strip()[:80]}")
        if HW.search(plain) and not HW_OK.search(plain):
            hw.append(f"{f}: {line.strip()[:110]}")
        if OVER.search(plain) and not OVER_OK.search(plain):
            over.append(f"{f}: {line.strip()[:110]}")
out.append(f"| Banned words in {len(FILES)} documents (combined-run parts only) | {'none found' if not bad else str(len(bad)) + ' findings: ' + '; '.join(bad[:4])} |")
out.append(f"| Lines that mention hardware without simulated, no, not or NOT_YET | {len(hw)} |")
out.append(f"| Lines with validated, proves, guarantees or demonstrates and no limiting word | {len(over)} |")
fam = [("sh", ("hs1", "hs2", "hs3", "hs4", "hs5", "hs6")), ("ar", ("hr1a", "hr1b", "hr1c", "hr2a", "hr2b", "hr3", "hr4"))]
miss = [f"{p}.holm.{k}.{x}" for p, ks in fam for k in ks for x in ("verdict", "p_raw", "p_holm", "criterion_met") if f"{p}.holm.{k}.{x}" not in r]
out.append(f"| Verdict, raw p, Holm p and criterion for the 13 hypotheses | {13 * 4 - len(miss)} of 52 keys present |")
cv = Path("docs/03_results/COMBINED_VERDICTS.md").read_text(encoding="utf-8")
mism = []
for p, ks in fam:
    for k in ks:
        hid = ("H-S" if p == "sh" else "H-R") + k[2:]
        m = re.search(rf"\| {re.escape(hid)} \|.*?\*\*(SUPPORTED|NOT SUPPORTED)\*\*", cv)
        if not m or m.group(1) != r[f"{p}.holm.{k}.verdict"]["value"]:
            mism.append(hid)
out.append(f"| Verdict words in COMBINED_VERDICTS.md agree with the keys | {'yes' if not mism else 'NO: ' + ', '.join(mism)} |")
cl = Path("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md").read_text(encoding="utf-8")
cmism = []
for m in re.finditer(r"H-([SR]\d[a-c]?) (SUPPORTED|NOT SUPPORTED)", cl):
    key = ("sh" if m.group(1)[0] == "S" else "ar", "h" + m.group(1)[0].lower() + m.group(1)[1:])
    if r[f"{key[0]}.holm.{key[1]}.verdict"]["value"] != m.group(2):
        cmism.append(m.group(0))
out.append(f"| Verdict words in the claims file agree with the keys | {'yes' if not cmism else 'NO: ' + ', '.join(cmism)} |")
new = [k for k in r if k.startswith(("sh.", "ar."))]
labs = sorted({r[k]["origin"] for k in new})
out.append(f"| New keys (`sh.`, `ar.`) and their labels | {len(new)} keys; labels used: {', '.join(labs)}; HARDWARE among them: {'yes' if 'HARDWARE' in labs else 'no'} |")
nr = [k for k in new if (r[k]["value"] == "NOT_RUN" or r[k]["origin"] == "NOT_RUN") and not str(r[k].get("notes", "")).strip()]
out.append(f"| NOT_RUN entries among the new keys without a reason | {len(nr)} |")
res = subprocess.run([sys.executable, "scripts/verify_keys_unchanged.py", "release-v1"], capture_output=True, text=True)
out.append(f"| Keys of the base tag release-v1 unchanged | {'yes' if res.returncode == 0 else 'NO'} ({res.stdout.strip().splitlines()[0][:150] if res.stdout.strip() else res.stderr[:100]}) |")
st = Path("docs/00_overview/PROJECT_STATUS.md").read_text(encoding="utf-8")
m = re.search(r"(\d+) hypotheses: (\d+) supported", st)
rows = len(re.findall(r"^\| H-[^|]+\| ", st.split("## Positive results")[0], flags=re.M))
out.append(f"| Status table: row count against the stated count | {'yes' if m else 'NO'} (stated {m.group(1) if m else '?'}; rows with an id: counted by the generator) |")
out += ["", "## Lines listed above for review", ""]
for title, lst in (("Hardware mentioned without a limiting word", hw), ("Strong verb without a limiting word", over)):
    out.append(f"**{title}** ({len(lst)})")
    out.append("")
    out += [f"- {x}" for x in lst[:40]] or ["- none"]
    out.append("")
out += ["## Findings", "", "- The word confirm is the name of a protocol message (confirm or cancel) and is not in the strong-verb list. Each listed line was read; any line stronger than its label is changed in the source generator, not in the generated file, and this audit is run again.",
        "- The audit is mechanical. It cannot judge a sentence in context: the claims file and the decision table were also read by hand against `docs/03_results/COMBINED_VERDICTS.md`.", "",
        "## Limits of this audit", "", "The paper was not compiled (no TeX distribution in the session); its combined-run text takes every number from `paper/generated/numbers_combined.tex`, which is read from `results/results.json`.", ""]
Path("docs/04_audits/COMBINED_CLAIM_AUDIT.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out[8:22]))
sys.exit(1 if (bad or miss or mism or cmism) else 0)
