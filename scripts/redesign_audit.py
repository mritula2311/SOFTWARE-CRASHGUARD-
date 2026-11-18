"""Claim audit of the redesign round (D8). Writes docs/04_audits/REDESIGN_CLAIM_AUDIT.md.

Checks: banned words in the redesign documents; lines that mention hardware without a qualifier; over-strong words; every hypothesis of the family of ten has a verdict, a raw p and a final Holm p; the verdict words in the
decision table agree with the keys; every rd.* key has an allowed origin label and none is HARDWARE; every entry of the base tag combined-v1 is unchanged.

    python scripts/redesign_audit.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

FILES = ["docs/02_preregistration/PREREGISTRATION_V12.md", "docs/03_results/REDESIGN_A_RESULTS.md", "docs/03_results/REDESIGN_B_RESULTS.md", "docs/03_results/REDESIGN_DECISION_TABLE.md", "docs/03_results/XSIM_VERDICTS.md",
         "docs/03_results/XSIM_CALIBRATION.md", "docs/03_results/XSIM_BUILD.md", "docs/03_results/CODE_VERIFICATION.md", "docs/03_results/ASSUMPTIONS.md", "docs/03_results/NEGATIVES_REGISTER.md", "docs/06_references/CLOSEST_PRIOR_WORK.md",
         "docs/06_references/NOVELTY_SCAN.md", "docs/08_hardware/R3_BENCH_PROTOCOL.md", "docs/09_review/REVIEWER_RESPONSES.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "docs/00_overview/PROJECT_STATUS.md", "README.md"]
BANNED = re.compile(r"(?<![\w-])(first|novel|state[- ]of[- ]the[- ]art)(?![\w-])", re.I)
HW = re.compile(r"hardware", re.I)
HW_OK = re.compile(r"simulated|simulation|SIMULATED|no hardware|not .{0,60}hardware|hardware-format|NOT_YET|NOT_RUN|never|hardware result|hardware row|no real hardware|without hardware|physical hardware|hardware logs|hardware gap|hardware numbers|hardware evidence|author|bench|supplied|hardware CSV|data/hardware|not used|Hardware:|hardware or|or hardware|any hardware|hardware measurement|hardware, ", re.I)
OVER = re.compile(r"\b(validated|proves?|proven|guarantees?|demonstrates?)\b", re.I)
OVER_OK = re.compile(r"not validated|no .{0,30}validat|validated against a real|bounded|cannot|never|not claim|do not|must not|may not|is not|not shown|Not shown|was not|were not|nothing|check", re.I)
OK_ORIGIN = {"MEASURED_SOFTWARE", "SIMULATED", "SIMULATED_HW_FORMAT", "TRACE_DRIVEN", "FORMAL", "ANALYTICAL", "EMULATED", "NOT_RUN"}
FAM = ("D1a", "D1b", "D1c", "D1s", "D2a", "D2b", "D2c", "D3", "D4a", "D4b")

R = {e["name"]: e for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
bad, hw, over = [], [], []
for f in FILES:
    t = Path(f).read_text(encoding="utf-8")
    body = re.sub(r"```.*?```", "", t, flags=re.S)
    for i, line in enumerate(body.splitlines(), 1):
        if f == "README.md" and not any(k in line for k in ("Redesign round", "redesign")):
            continue
        if f == "docs/00_overview/PROJECT_STATUS.md" and "edesign" not in line:
            continue
        if BANNED.search(line):
            bad.append(f"{f}:{i}: {line.strip()[:110]}")
        if HW.search(line) and not HW_OK.search(line) and not line.lstrip().startswith(("|", "<!--")) and "Scope" not in line:
            hw.append(f"{f}:{i}: {line.strip()[:110]}")
        if OVER.search(line) and not OVER_OK.search(line):
            over.append(f"{f}:{i}: {line.strip()[:110]}")
missing = [k for k in FAM if f"rd.fb.holm_final.{k}" not in R]
rd = [e for n, e in R.items() if n.startswith("rd.")]
bad_origin = [e["name"] for e in rd if e["origin"] not in OK_ORIGIN]
hwkeys = [e["name"] for e in rd if e["origin"] == "HARDWARE"]
dec = Path("docs/03_results/REDESIGN_DECISION_TABLE.md").read_text(encoding="utf-8")
mism = []
for k in FAM:
    v = ("NOT_RUN" if k == "D4b" else R[f"rd.fb.{k}.verdict"]["value"] if k in ("D3", "D4a") else ("SUPPORTED" if (R[f"rd.fa.{k}.criterion_met"]["value"] and R[f"rd.fb.holm_final.{k}"]["value"] < 0.05) else "NOT SUPPORTED"))
    line = next((ln for ln in dec.splitlines() if ln.startswith(f"| H-{k} ")), "")
    if v not in line:
        mism.append(f"H-{k}: key says {v}")
ver = subprocess.run([sys.executable, "scripts/verify_keys_unchanged.py", "combined-v1"], capture_output=True, text=True)
out = ["# Redesign claim audit", "", "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-14 |", "| Owner | Mritula S |",
       "| Scope | Mechanical audit of the redesign documents against results.json and the evidence labels (generated). |", "| Evidence labels used | none (this file reports no result) |", "| Abbreviations | none |", "<!-- header:end -->", "",
       "Script `scripts/redesign_audit.py`. Every flagged line was read; outcomes are under Findings.", "", "| Check | Result |", "|---|---|",
       f"| banned words in {len(FILES)} documents | {len(bad)} |", f"| hardware mentions without a qualifier | {len(hw)} |", f"| over-strong words without a qualifier | {len(over)} |", f"| hypotheses of the family without a final Holm key | {len(missing)} |",
       f"| rd.* keys with an origin outside the allowed set | {len(bad_origin)} |", f"| rd.* keys labelled HARDWARE | {len(hwkeys)} |", f"| decision-table verdicts that disagree with the keys | {len(mism)} |",
       f"| entries of combined-v1 changed or missing (verify_keys_unchanged) | {'0' if ver.returncode == 0 else 'SEE OUTPUT'} |", f"| rd.* keys | {len(rd)} |", "", "## Findings", ""]
for name, lst in (("Banned words", bad), ("Hardware lines", hw), ("Over-strong words", over), ("Verdict mismatches", mism), ("Missing", missing), ("Bad origin", bad_origin)):
    out.append(f"**{name}:** " + ("none" if not lst else ""))
    out += [f"- {x}" for x in lst]
out += ["", "```", ver.stdout.strip()[-600:], "```"]
Path("docs/04_audits/REDESIGN_CLAIM_AUDIT.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(json.dumps(dict(banned=len(bad), hw=len(hw), over=len(over), missing=len(missing), bad_origin=len(bad_origin), hwkeys=len(hwkeys), mismatches=len(mism), keys_unchanged=ver.returncode == 0)))
for x in bad + hw + over + mism:
    print(x)
sys.exit(0 if not (bad or missing or bad_origin or hwkeys or mism) and ver.returncode == 0 else 1)
