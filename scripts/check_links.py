"""R4/R6: link check over every tracked Markdown file (relative links and backticked repository paths).

- Markdown links `[text](target)`: a relative target must exist (anchors are not checked; http(s) and mailto links are listed only with --external).
- Backticked repository paths such as `docs/03_results/CLAIM_EVIDENCE.md` that look like a path to a Markdown, CSV, JSON, PNG, PDF, TeX or Python file
  must exist, unless the file is listed in the "legacy path" map (`docs/07_log/PATH_MAP.md`), which records old paths on purpose.
Exit code 1 when anything is broken. Run: python scripts/check_links.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
TICK = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|csv|json|png|pdf|tex|py|sh|ps1|ino|h|c|yml|txt|cff))`")
SKIP_FILES = {"docs/07_log/CLEANUP_LOG.md", "docs/07_log/PATH_MAP.md"}
# a dated log entry that names a script by its old location on purpose
LEGACY_OK = {"scripts/combine_docs.py"}
SKIP_PREFIX = ("docs/archive/", "results/", "data/", "RESEARCH PAPERS/", "release/vzcrash_audit_for_authors/")
# things that are generated or produced at run time and legitimately absent from a clean checkout
GENERATED_OK = re.compile(r"^(data/|build/|release/crashguard|release/synthetic_pulses/|results/|report/|paper/generated/|\.venv|c_checks|docs/literature/)")


def tracked_md() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.split()
    new = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", "*.md"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.split()
    return sorted(set(out + new))


def main() -> int:
    bad: list[str] = []
    n_links = n_ticks = 0
    for f in tracked_md():
        if f in SKIP_FILES or f.startswith(SKIP_PREFIX):
            continue
        p = ROOT / f
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in LINK.finditer(text):
            t = m.group(1)
            if t.startswith(("http://", "https://", "mailto:", "#")):
                continue
            n_links += 1
            t = t.split("#")[0]
            if t and not (p.parent / t).exists() and not (ROOT / t).exists():
                bad.append(f"{f}: broken link ({t})")
        for m in TICK.finditer(text):
            t = m.group(1)
            if "/" not in t or t.startswith(("src/crashguard/",)) and not t.endswith(".py"):
                continue
            if GENERATED_OK.match(t) or "*" in t or "<" in t or t in LEGACY_OK:
                continue
            n_ticks += 1
            if not any((b / t).exists() for b in (ROOT, p.parent, ROOT / "results", ROOT / "src")):
                bad.append(f"{f}: missing path in backticks ({t})")
    for b in bad:
        print(b)
    print(f"checked {n_links} links and {n_ticks} backticked paths; {len(bad)} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
