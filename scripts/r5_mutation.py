"""Hand-written mutation testing of the round-5 modules (V16 section 10): each mutant is one textual change of one module in a temporary copy of the source tree; the algorithm's tests run
against it and the mutant is KILLED if any of them fails. At least 20 mutants per algorithm and at least 80% killed are required before the freeze.

    python scripts/r5_mutation.py l1 [l2 l3 l4 l5]      # default: every algorithm that has a mutant list
"""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from r5_mutants import ALGS  # noqa: E402


def run(cwd: Path, tests: list[str]) -> bool:
    env = {**os.environ, "PYTHONPATH": str(cwd / "src")}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode == 0  # True = all passed = the mutant SURVIVED


def main() -> None:
    names = sys.argv[1:] or list(ALGS)
    sys.path.insert(0, str(ROOT / "src"))
    from crashguard.rd_common import Rec

    for alg in names:
        tests, mutants = ALGS[alg]
        rows = []
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "w"
            shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "dummy"))
            for d in ("data", "results"):
                try:
                    (work / d).symlink_to(ROOT / d, target_is_directory=True)
                except OSError:  # no symlink right on Windows: a directory junction needs none
                    subprocess.run(["cmd", "/c", "mklink", "/J", str(work / d), str(ROOT / d)], capture_output=True, check=False)
            assert run(work, tests), f"baseline tests of {alg} fail on the clean copy"
            for mid, f, old, new, desc in mutants:
                p = work / f
                orig = p.read_bytes().decode("utf-8")
                o = old.replace("\n", "\r\n") if "\r\n" in orig else old
                n = new.replace("\n", "\r\n") if "\r\n" in orig else new
                if o not in orig:
                    rows.append(dict(id=mid, file=f, description=desc, status="NOT_APPLIED"))
                    print(mid, "NOT_APPLIED", flush=True)
                    continue
                p.write_bytes(orig.replace(o, n, 1).encode("utf-8"))
                try:
                    survived = run(work, tests)
                finally:
                    p.write_bytes(orig.encode("utf-8"))
                rows.append(dict(id=mid, file=f, description=desc, status="SURVIVED" if survived else "KILLED"))
                print(mid, rows[-1]["status"], desc, flush=True)
        out = ROOT / f"results/tables/r5_mutation_{alg}.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["id", "file", "description", "status"])
            w.writeheader()
            w.writerows(rows)
        applied = [r for r in rows if r["status"] != "NOT_APPLIED"]
        killed = sum(r["status"] == "KILLED" for r in applied)
        print(f"{alg}: killed {killed} of {len(applied)} ({killed / len(applied):.0%}); not applied {len(rows) - len(applied)}")
        rec = Rec(f"r5.cv.mutation.{alg}.", "scripts/r5_mutation.py", "ANALYTICAL")
        rec.add("mutants", len(applied), "mutants", "hand-written mutants applied")
        rec.add("killed", killed, "mutants", "mutants caught by at least one failing test")
        rec.add("killed_share", killed / len(applied), "fraction", "below 0.80 means the tests must be extended before the freeze")
        rec.add("survivors", ",".join(r["id"] for r in applied if r["status"] == "SURVIVED") or "none", "ids", "")
        rec.write()


if __name__ == "__main__":
    main()
