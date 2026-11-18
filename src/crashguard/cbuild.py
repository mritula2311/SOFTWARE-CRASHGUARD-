"""Build and run the C equivalence checks in a fixed place, with retries.

Windows Application Control sometimes blocks a freshly built program ("An Application Control policy has blocked this file"). The checks are therefore built
into a fixed folder (``build/``) with a fixed file name per check, and each run is tried up to ``ATTEMPTS`` times with growing waits; if the project folder is
blocked, the same fixed name is tried in the system temp folder. If the program still cannot be run anywhere, ``BlockedError`` carries the reason, the caller records NOT_RUN with that reason, and the pure-Python mirror of the C logic
(``c_mirror.py``) is the check that remains. Nothing is ever copied forward from an older run.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from crashguard.export_c import find_compiler

BUILD = Path("build")
ATTEMPTS = 5
BACKOFF_S = (1.0, 2.0, 4.0, 8.0, 16.0)


class BlockedError(RuntimeError):
    """The compiled program could not be run (blocked by the operating system) after all attempts."""


def compiler_name() -> str:
    cc = find_compiler()
    if cc is None:
        raise RuntimeError("no C compiler found")
    return "zig cc (clang)" if len(cc) > 1 else cc[0]


def locations() -> list[Path]:
    """Where to build: the fixed project folder first, then a fixed folder in the system temp directory (Application Control may allow one and block the other)."""
    import tempfile

    return [BUILD, Path(tempfile.gettempdir()) / "crashguard_build"]


def compile_and_run(tag: str, source: str, include_dir: Path, args: list[Path], sleep=time.sleep) -> str:
    """Compile ``source`` as <folder>/<tag>.exe and run it with ``args``, up to ATTEMPTS times per folder (see ``locations``). Returns a text naming the compiler and the
    folder it ran from. Raises RuntimeError on a compile error (a real defect) and BlockedError if the program cannot be run anywhere."""
    cc = find_compiler()
    if cc is None:
        raise RuntimeError("no C compiler found")
    name = "zig cc (clang)" if len(cc) > 1 else cc[0]
    last: Exception | None = None
    tried = []
    for folder in locations():
        folder.mkdir(parents=True, exist_ok=True)
        src, exe = folder / f"{tag}.c", folder / f"{tag}.exe"
        src.write_text(source)
        r = subprocess.run([*cc, "-O2", "-std=c99", f"-I{include_dir.resolve()}", str(src), "-o", str(exe), "-lm"], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        tried.append(str(folder))
        for k in range(ATTEMPTS):
            try:
                subprocess.run([str(exe.resolve()), *[str(a) for a in args]], check=True)
                return f"{name}, run from {folder}"
            except OSError as err:  # blocked by Application Control
                last = err
                sleep(BACKOFF_S[min(k, len(BACKOFF_S) - 1)])
    raise BlockedError(f"{tag}.exe could not be run after {ATTEMPTS} attempts in each of {', '.join(tried)} (blocked by the operating system?): {last}")
