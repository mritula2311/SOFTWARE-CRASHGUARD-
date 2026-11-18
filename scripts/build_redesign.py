"""Build release/crashguard-redesign-v1.1.zip: code, tests, documents, results and the freeze and grid files of the redesign round. Hashes of every file are inside the archive (HASHES.sha256); the SHA-256 of the archive is
printed and written to release/crashguard-redesign-v1.1.zip.sha256. No raw or processed data, no data/hardware, no build output.   Run: python scripts/build_redesign.py"""
import hashlib
import subprocess
import zipfile
from pathlib import Path

OUT = Path("release/crashguard-redesign-v1.1.zip")
ROOTS = ["src", "scripts", "tests", "docs", "firmware_rd", "firmware_export", "xsim", "merge", "crashclip", "c_bundle", "paper"]
FILES = ["README.md", "CHANGELOG.md", "CLAUDE.md", "LICENSE", "NOTICE", "CITATION.cff", "CITATION.md", "Makefile", "requirements.txt", "requirements.lock", "results/results.json"]
TABLES = ["results/tables/" + n for n in ("rd_dev_log.csv", "rd_dev_checks.csv", "rd_frozen_A.json", "rd_fresh_A_grid.json", "rd_fresh_A_done.json", "rd_fresh_a_cells.csv", "rd_frozen_B.json", "rd_fresh_B_grid.json", "rd_fresh_B_done.json", "rd_mutation.csv", "rd_mutation_b.csv", "rd_fw_diff.json")]
SKIP = ("__pycache__", ".pyc", "tests/dummy/", "docs/literature/", "build/")


def main() -> None:
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    sel = [f for f in tracked if (f.split("/")[0] in ROOTS or f in FILES or f in TABLES) and not any(s in f for s in SKIP) and Path(f).exists()]
    for f in FILES + TABLES:
        if f not in sel and Path(f).exists():
            sel.append(f)
    OUT.parent.mkdir(exist_ok=True)
    hashes = []
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(set(sel)):
            b = Path(f).read_bytes()
            hashes.append(f"{hashlib.sha256(b).hexdigest()}  {f}")
            z.writestr(f, b)
        z.writestr("HASHES.sha256", "\n".join(hashes) + "\n")
    h = hashlib.sha256(OUT.read_bytes()).hexdigest()
    Path(str(OUT) + ".sha256").write_text(f"{h}  {OUT.name}\n")
    print(len(hashes), "files", h)


if __name__ == "__main__":
    main()
