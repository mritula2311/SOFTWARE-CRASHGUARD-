"""R1: inventory of every Markdown file and every non-code file in the repository (read-only).

Writes the inventory section of the cleanup log. Run BEFORE any file is moved:
    python scripts/repo_inventory.py docs/CLEANUP_LOG.md

Rules used here (stated in the log as well):
- "code" = tracked .py/.sh/.ps1/.yml files and the Makefile; "tests" = tracked files under tests/.
- "results.json" refs are a plain text search for the path or the file name in results/results.json.
- data/hardware/ is out of scope for this release and its content is never opened; only git metadata is used.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUP_DIRS = [
    "results/figures", "results/tables", "results/paper/figures", "results/paper", "results/synthetic", "results/surrogate",
    "c_bundle/forest_10x9", "c_bundle/forest_15x6", "c_bundle/n14_sat_synthetic", "c_bundle/severity_synthetic",
    "crashclip/baselines", "release/vzcrash_audit_for_authors", "paper/generated", "data/hardware",
]
# status decided by a person, with the replacing document and the reason (everything not listed is "current")
SUPERSEDED = {
    "docs/CLAIMS_FOR_COVER_LETTER_V1.md": ("superseded", "docs/CLAIMS_FOR_COVER_LETTER.md", "older generated claim list from the journal-v1 push; the current list covers all rounds"),
    "docs/ALL_DOCS_COMBINED.md": ("duplicate", "docs/README.md (index) and the individual documents", "concatenation of every document; generated copy, not a source"),
    "docs/CLAUDE_CODE_PROMPT.md": ("scratch", "CLAUDE.md and docs/PRD.md", "the first build prompt; its content is in CLAUDE.md and the PRD"),
    "docs/FIRST_PROMPT.md": ("scratch", "CLAUDE.md and docs/PRD.md", "the first message of the first session; no content that the PRD lacks"),
    "docs/MANUAL_SEARCH_CHECKLIST.md": ("superseded", "docs/06_references/SCOPUS_STRINGS.md", "the checklist for the author to run searches; replaced by the search-string file with a results table"),
    "docs/RESULTS_SO_FAR.md": ("current", "", "author-supplied hardware progress notes (not read by this release; external numbers)"),
    "REPRODUCE.md": ("current", "", "main reproduction guide (scope: the main pipeline)"),
    "docs/REPRODUCE.md": ("current", "", "reproduction guide for the finishing round (scope: branch finish)"),
}
TEXT_SUFFIX = {".md", ".txt", ".py", ".sh", ".ps1", ".yml", ".yaml", ".json", ".tex", ".cff", ".toml", ".cfg", ".ino", ".c", ".h"}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def last_date(path: str) -> str:
    return git("log", "-1", "--format=%cs", "--", path).strip() or "uncommitted"


def is_code(p: str) -> bool:
    return p.endswith((".py", ".sh", ".ps1", ".yml")) or p == "Makefile"


def main(out: str) -> None:
    files = [f for f in git("ls-files").splitlines() if f]
    hw = [f for f in files if f.startswith("data/hardware/")]
    files = [f for f in files if not f.startswith("data/hardware/")]
    results_text = (ROOT / "results/results.json").read_text(encoding="utf-8", errors="replace")
    texts: dict[str, str] = {}
    for f in files:
        p = ROOT / f
        if p.suffix.lower() in TEXT_SUFFIX or p.name in ("Makefile", "NOTICE", "LICENSE"):
            if p.stat().st_size < 3_000_000 and f != "results/results.json" and not f.startswith("results/"):
                texts[f] = p.read_text(encoding="utf-8", errors="replace")
    code_files = [f for f in texts if is_code(f)]
    test_files = [f for f in texts if f.startswith("tests/")]
    md_files = [f for f in texts if f.endswith(".md")]

    def refs(path: str) -> tuple[int, int, int, int]:
        base = Path(path).name
        r = int(path in results_text or base in results_text) if len(base) > 6 else 0
        c = sum(1 for f in code_files if f != path and (path in texts[f] or base in texts[f]))
        t = sum(1 for f in test_files if f != path and (path in texts[f] or base in texts[f]))
        d = sum(1 for f in md_files if f != path and (path in texts[f] or base in texts[f]))
        return r, c, t, d

    grouped: dict[str, list[str]] = defaultdict(list)
    single: list[str] = []
    for f in files:
        if (f.startswith(("src/", "tests/")) and f.endswith(".py")):
            continue  # code
        g = next((d for d in GROUP_DIRS if f.startswith(d + "/") and "/" not in f[len(d) + 1:]), None)
        if g:
            grouped[g].append(f)
        elif is_code(f) and not f.startswith(".github"):
            continue  # code, listed by the code inventory (counts only)
        else:
            single.append(f)

    L: list[str] = []
    L += ["# Cleanup log", "",
          "Status: current. Date: 2026-11-13. Owner: Mritula S. Scope: release branch, Block R (repository reorganisation). Evidence labels: none (no result is produced here).", "",
          "This file is written in three parts. Part 1 is the inventory taken BEFORE any file was moved (paths are the old paths). Part 2 lists the moves, deletions and rewrites. Part 3 lists the checks run after the move.", "",
          "## Part 1. Inventory (before any move)", "",
          "Columns: size in bytes; date of the last commit that touched the file; references from `results/results.json` (R), code (C, count of code files), tests (T), other Markdown documents (D); status is one of current, superseded, duplicate, scratch.", "",
          f"Counts: {len(files) + len(hw)} tracked files in total; {sum(1 for f in files if f.endswith('.md'))} Markdown files; the code files under `src/` and `tests/` are counted but not listed. "
          f"`data/hardware/` ({len(hw)} tracked files) is out of scope for this release: its content was not opened and it is not changed; it is listed in the group table only.", "",
          "### 1a. Markdown files and single non-code files", "",
          "| Path | Bytes | Last commit | R | C | T | D | Status | Replaced by / note |", "|---|---:|---|---:|---:|---:|---:|---|---|"]
    for f in sorted(single):
        size = (ROOT / f).stat().st_size
        r, c, t, d = refs(f)
        status, repl, note = SUPERSEDED.get(f, ("current", "", ""))
        if f.endswith((".log", ".txt")) and Path(f).parent == Path(".") and f != "requirements.txt":
            if status == "current":
                status, repl, note = ("scratch", "", "run log or comparison output from an earlier session; kept as evidence in the archive, not deleted")
        if f.endswith(".gitkeep"):
            status, note = "scratch", "empty placeholder; redundant when the directory has other tracked files"
        L.append(f"| `{f}` | {size} | {last_date(f)} | {r} | {c} | {t} | {d} | {status} | {(repl + ' ' + note).strip()} |")
    L += ["", "### 1b. Directories of generated or bundled files (one row per directory)", "",
          "| Directory | Files | Bytes | Last commit | R | C | T | D | Status | Note |", "|---|---:|---:|---|---:|---:|---:|---:|---|---|"]
    for g in GROUP_DIRS:
        fs = grouped.get(g, [])
        if g == "data/hardware":
            L.append(f"| `{g}/` | {len(hw)} | n/a | n/a | n/a | n/a | n/a | n/a | out of scope | not opened in this release (rule: software only) |")
            continue
        size = sum((ROOT / f).stat().st_size for f in fs)
        rr = cc = tt = dd = 0
        for f in fs:
            r, c, t, d = refs(f)
            rr, cc, tt, dd = rr + r, cc + c, tt + t, dd + d
        L.append(f"| `{g}/` | {len(fs)} | {size} | {max((last_date(f) for f in fs), default='')} | {rr} | {cc} | {tt} | {dd} | current | generated output or bundle; tagged result files are not edited |")
    L += ["", "R, C, T and D in 1b are the sum of per-file reference counts.", "", "### 1c. Byte-identical duplicates among tracked files", "",
          "| SHA-256 (first 16) | Paths | Decision |", "|---|---|---|"]
    by_hash: dict[str, list[str]] = defaultdict(list)
    for f in files:
        if f.startswith("src/") and f.endswith(".py"):
            continue
        by_hash[hashlib.sha256((ROOT / f).read_bytes()).hexdigest()].append(f)
    for h, fs in sorted(by_hash.items()):
        if len(fs) > 1 and Path(fs[0]).name != ".gitkeep" and (ROOT / fs[0]).stat().st_size > 0:
            L.append(f"| `{h[:16]}` | {', '.join(f'`{x}`' for x in fs)} | kept: copies are inputs of different steps (tagged results, the CrashClip package, the C bundle); removing one breaks a generator or a tagged file |")
    L += ["", "### 1d. Empty files", "", "| Path | Decision |", "|---|---|"]
    for f in files:
        if (ROOT / f).stat().st_size == 0:
            keep = f.startswith("results/")
            L.append(f"| `{f}` | {'kept: tagged generated output (written empty by a script on purpose)' if keep else 'delete if the directory has other tracked files (placeholder), see Part 2'} |")
    Path(out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote", out, len(single), "single files,", sum(len(v) for v in grouped.values()), "grouped")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/CLEANUP_LOG.md")
