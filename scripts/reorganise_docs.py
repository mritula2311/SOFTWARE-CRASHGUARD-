"""R2/R3: move documents into the target structure with `git mv`, then rewrite every path reference.

One-off script, kept so the move can be audited (`docs/07_log/CLEANUP_LOG.md`, Part 2). Idempotent for the rewrite step.
Not rewritten on purpose: `results/` (tagged results, hash-checked), `release/` (the audit package sent to the dataset authors),
`data/`, `c_bundle/`, the cleanup log itself and the archived run logs.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

D = "docs/"
MAP: dict[str, str] = {}


def put(folder: str, names: list[str]) -> None:
    for n in names:
        MAP[f"{D}{n}"] = f"{D}{folder}/{n}"


put("00_overview", ["CLAIMS_FOR_COVER_LETTER.md", "PRD.md", "ARCHITECTURE.md", "LIMITATIONS.md"])
put("01_protocol", ["PROTOCOL_UA_SCT.md", "PROTOCOL_SCT.md", "PROTOCOL_MODEL.md", "PACKET_FORMAT.md", "ATTACK_CASES.md", "THREAT_MODEL_SPOOFING.md"])
put("02_preregistration", ["PREREGISTRATION.md", "PREREGISTRATION_V2.md", "PREREGISTRATION_V3.md", "PREREGISTRATION_V4.md", "PREREGISTRATION_V5.md",
                           "EXPERIMENTS.md", "EXPERIMENTS_EXTRA.md", "ALGORITHMS.md"])
put("03_results", ["JOURNAL_RESULTS.md", "POSITIVE_PUSH_RESULTS.md", "V2_RESULTS.md", "FINISH_RESULTS.md", "NEGATIVES_REGISTER.md", "CLAIM_EVIDENCE.md",
                   "STATS_AUDIT.md", "RESULTS_SO_FAR.md"])
put("04_audits", ["VZCRASH_AUDIT.md", "PREREG_V4_AUDIT.md", "PP_CLAIM_AUDIT.md", "CLAIM_AUDIT.md", "V2_CLAIM_AUDIT.md", "FINISH_AUDIT.md",
                  "ALGORITHMS_COMPLIANCE.md", "vzcrash_email_draft.md"])
put("05_data_code", ["DATA_AND_CODE_STATEMENT.md", "SYNTHETIC_ASSUMPTIONS.md", "SEALED_SPLIT.md", "DATASET.md", "DATASET_FACTS.md", "DATASET_FACTS_QUALITY.md",
                     "FEATURES.md", "SEVERITY.md", "SENSOR_DATASHEETS.md", "FIGURES_TABLES.md", "FIRMWARE_SYNC.md", "HARDWARE_SCHEMA.md",
                     "HARDWARE_READINESS.md", "RELEASE_MANIFEST.md"])
put("06_references", ["REFERENCES.md", "REFERENCES_UNVERIFIED.md", "NOVELTY_SCAN.md", "NOVELTY.md", "PRIOR_WORK.md", "MANUAL_SEARCH_CHECKLIST.md"])
put("07_log", ["DECISIONS.md", "NOT_RUN.md", "TIME_LOG.md", "CLEANUP_LOG.md"])
put("archive", ["CLAIMS_FOR_COVER_LETTER_V1.md", "ALL_DOCS_COMBINED.md", "CLAUDE_CODE_PROMPT.md", "FIRST_PROMPT.md"])
MAP["docs/REPRODUCE.md"] = "docs/05_data_code/REPRODUCE_FINISH.md"
MAP["REPRODUCE.md"] = "docs/05_data_code/REPRODUCE.md"
MAP["PROGRESS.md"] = "docs/07_log/PROGRESS.md"
ARCHIVE_LOGS = ["b2.log", "cmp1.txt", "cmp2.txt", "cmp3.txt", "fin_c.log", "fin_f1.log", "fin_f1_cv.log", "fin_f2.log", "fin_g.log", "p1_cv.log",
                "p1_cv_cnn.log", "p1_fit.log", "p4a_eval.log", "p4a_sweep.log", "p4b_eval.log", "p4c_eval.log", "p4c_eval2.log", "p4d.log", "pc.log",
                "rerun_prefix.log", "run1.log", "run2.log", "run3.log", "s11.log", "sel_study.log", "t13_harvest.log", "t13_heldout.log", "t13_neardup.log",
                "t4.log", "t5.log", "t7.log", "t8.log", "vz_audit.log", "vz_leakage.log", "x1.log", "x5.log", "x7.log", "x8.log", "x_common.log"]
for n in ARCHIVE_LOGS:
    MAP[n] = f"docs/archive/logs/{n}"

SKIP_PREFIX = ("results/", "release/", "data/", "c_bundle/", ".git/", ".venv/", "build/", "docs/archive/logs/", "docs/07_log/CLEANUP_LOG.md",
               "docs/07_log/PATH_MAP.md", "scripts/repo_inventory.py", "scripts/reorganise_docs.py", "docs/CLEANUP_LOG.md", "RESEARCH PAPERS/")
TEXT_SUFFIX = {".md", ".py", ".sh", ".ps1", ".yml", ".yaml", ".tex", ".cff", ".toml", ".cfg", ".txt"}
TEXT_NAMES = {"Makefile", "NOTICE"}


def git(*a: str) -> None:
    subprocess.run(["git", *a], cwd=ROOT, check=True)


def do_moves() -> list[tuple[str, str]]:
    done = []
    for old, new in MAP.items():
        if not (ROOT / old).exists():
            continue
        (ROOT / new).parent.mkdir(parents=True, exist_ok=True)
        git("mv", old, new)
        done.append((old, new))
    return done


def rewrite_text(text: str) -> str:
    # docs/NAME.md first (longest first so that docs/REPRODUCE.md is handled before the bare root name)
    for old in sorted(MAP, key=len, reverse=True):
        new = MAP[old]
        if old.endswith((".log", ".txt")):
            continue
        pat = re.compile(r"(?<![\w/.-])" + re.escape(old) + r"(?![\w])")
        text = pat.sub(new, text)
    return text


def do_rewrite() -> list[str]:
    changed = []
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
    for f in files:
        if f.startswith(SKIP_PREFIX):
            continue
        p = ROOT / f
        if not p.exists() or not (p.suffix.lower() in TEXT_SUFFIX or p.name in TEXT_NAMES):
            continue
        t = p.read_text(encoding="utf-8")
        n = rewrite_text(t)
        if n != t:
            p.write_text(n, encoding="utf-8", newline="")
            changed.append(f)
    return changed


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("all", "move"):
        moved = do_moves()
        print(len(moved), "moved")
    if mode in ("all", "rewrite"):
        ch = do_rewrite()
        print(len(ch), "files rewritten")
