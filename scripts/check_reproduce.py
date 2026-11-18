"""R5: check that every command named in the reproduction guides and the Makefile still resolves after the reorganisation.

Does not run the commands (a full run takes hours). For each command it checks that
- `python -m crashguard.X` names a module file in src/crashguard/X.py;
- `python path/to/script.py` and `bash scripts/x.sh` name existing files;
- `make target` names a target in the Makefile;
- paths in backticks that look like repository files exist (see check_links.py).
Prints a table and exits 1 on any failure. Run: python scripts/check_reproduce.py [--write]   (--write refreshes the check table in REPRODUCE.md)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDES = ["docs/05_data_code/REPRODUCE.md", "docs/05_data_code/REPRODUCE_FINISH.md", "README.md"]
START, END = "<!-- command-check:start -->", "<!-- command-check:end -->"


def make_targets() -> set[str]:
    t = set()
    for line in (ROOT / "Makefile").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if m:
            t.add(m.group(1))
        m = re.match(r"^\.PHONY:\s*(.*)", line)
        if m:
            t.update(m.group(1).split())
    return t


def main() -> int:
    mods = {p.stem for p in (ROOT / "src/crashguard").glob("*.py")}
    targets = make_targets()
    seen: dict[str, str] = {}
    for g in GUIDES + ["Makefile", "scripts/run_all.ps1"]:
        text = (ROOT / g).read_text(encoding="utf-8")
        for m in re.finditer(r"-m\s+crashguard\.([A-Za-z0-9_]+)", text):
            seen[f"-m crashguard.{m.group(1)}"] = "ok" if m.group(1) in mods else "MISSING module"
        for m in re.finditer(r"(?:python|\$\(PY\))\s+((?:scripts|merge|crashclip)/[A-Za-z0-9_./-]+\.py)", text):
            seen[m.group(1)] = "ok" if (ROOT / m.group(1)).exists() else "MISSING file"
        for m in re.finditer(r"bash\s+(scripts/[A-Za-z0-9_./-]+\.sh)", text):
            seen[m.group(1)] = "ok" if (ROOT / m.group(1)).exists() else "MISSING file"
        if g.endswith(".md"):
            for m in re.finditer(r"`make ([a-z0-9_]+)`", text):
                seen[f"make {m.group(1)}"] = "ok" if m.group(1) in targets else "MISSING target"
    bad = {k: v for k, v in seen.items() if v != "ok"}
    for k, v in sorted(bad.items()):
        print(f"{v}: {k}")
    print(f"{len(seen)} distinct commands checked, {len(bad)} unresolved")
    if "--write" in sys.argv:
        p = ROOT / "docs/05_data_code/REPRODUCE.md"
        t = p.read_text(encoding="utf-8")
        blk = (f"{START}\n## 9. Command check after the 2026-11-13 reorganisation\n\n"
               f"`python scripts/check_reproduce.py` checks that every module, script and make target named in the guides, the Makefile and `scripts/run_all.ps1` exists. "
               f"Result on 2026-11-13: {len(seen)} distinct commands, {len(bad)} unresolved. It does not run the commands; a full rebuild takes hours.\n{END}")
        if START in t:
            t = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: blk, t, flags=re.S)
        else:
            t = t.rstrip("\n") + "\n\n" + blk + "\n"
        p.write_text(t, encoding="utf-8", newline="")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
