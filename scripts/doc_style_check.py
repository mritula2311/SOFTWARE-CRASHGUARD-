"""R4: style checks over every tracked Markdown document: forbidden words, emoji, first-person chat tone, missing header block, spelling.

    python scripts/doc_style_check.py            # all checks except spelling
    python scripts/doc_style_check.py --spell    # also run codespell (python -m codespell_lib)

Scope: every tracked or new Markdown file except `docs/archive/` (superseded text is kept as it was), CLAUDE.md (it states the wording rules, so it names the
words), tagged files under results/, the audit package sent to the dataset authors, data/, and RESEARCH PAPERS/.
Exit code 1 when anything is found.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_PREFIX = ("docs/archive/", "results/", "release/vzcrash_audit_for_authors/", "data/", "RESEARCH PAPERS/", ".venv/", "docs/07_log/CLEANUP_LOG.md")
SKIP_FILES = {"CLAUDE.md", "docs/02_preregistration/PREREGISTRATION_V18.md"}  # V18 is kept byte-identical to its committed hash (SHA-256 recorded in docs/04_audits/ROUND7.md); its wording is not edited after the runs
LETTERS = {"docs/04_audits/vzcrash_email_draft.md"}  # a draft letter is first person by nature
BANNED = re.compile(r"(?<![\w-])(first|novel|state[- ]of[- ]the[- ]art)(?![\w-])", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌⚠]")
FIRST_PERSON = re.compile(r"(?<![\w'])(I(?= (?:am|have|will|would|did|do|was|can|think|use|used|ran|made|found|checked))|I'll|I'm|I've|my|me|let me|let's)(?![\w'])")
HEADER = "<!-- header:start -->"


def files() -> list[str]:
    run = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.split("\n")  # noqa: E731
    fs = set(x for x in run("ls-files", "*.md") + run("ls-files", "--others", "--exclude-standard", "*.md") if x)
    return sorted(f for f in fs if f not in SKIP_FILES and not f.startswith(SKIP_PREFIX) and (ROOT / f).exists())


def main() -> int:
    bad: list[str] = []
    fs = files()
    for f in fs:
        text = (ROOT / f).read_text(encoding="utf-8", errors="replace")
        if HEADER not in text:
            bad.append(f"{f}: no header block")
        in_code = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            plain = re.sub(r"`[^`]*`", "", line)
            if not in_code:
                for m in BANNED.finditer(plain):
                    bad.append(f"{f}:{n}: forbidden word '{m.group(0)}': {line.strip()[:110]}")
                for m in (FIRST_PERSON.finditer(plain) if f not in LETTERS else []):
                    bad.append(f"{f}:{n}: first-person wording '{m.group(0)}': {line.strip()[:110]}")
            for m in EMOJI.finditer(line):
                bad.append(f"{f}:{n}: emoji/symbol {m.group(0)!r}")
    for b in bad:
        print(b)
    print(f"checked {len(fs)} documents; {len(bad)} findings")
    rc = 1 if bad else 0
    if "--spell" in sys.argv:
        ignore = ROOT / "scripts/spell_ignore.txt"
        cmd = [sys.executable, "-m", "codespell_lib", "--quiet-level", "2", "--ignore-regex", "pre-selected|re-use", *fs]
        if ignore.exists():
            cmd += ["--ignore-words", str(ignore)]
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        print(out.stdout.strip() or "spelling: no findings")
        if out.returncode:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
