"""Round 7c item 1: is the base's seen-set check-and-insert atomic? Scan the base-side code for concurrency primitives and record the result (keys r7c.atomic.*, ANALYTICAL: a reading of code, no run).

    python scripts/r7c_atomic_scan.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard.results import record_many  # noqa: E402

BASE_FILES = ["src/crashguard/verifier.py", "src/crashguard/sct_protocol.py", "src/crashguard/r5_l8.py", "src/crashguard/r7_pseudo.py", "src/crashguard/frame_layout.py", "src/crashguard/packet.py"]
C_DIRS = ["firmware_rd", "firmware_r6", "firmware_r7", "firmware_export", "xsim/ns3"]
PY_PRIM = re.compile(r"\b(threading|Lock|RLock|Semaphore|asyncio|async def|await|multiprocessing|concurrent\.futures|queue\.Queue|socketserver|ThreadPool)\b")
C_PRIM = re.compile(r"\b(pthread_\w+|std::mutex|std::atomic|std::thread|_Atomic|volatile|__sync_\w+|__atomic_\w+|xSemaphore\w*|portENTER_CRITICAL|disable_irq|ISR)\b")
hits: list[tuple[str, int, str]] = []
for f in BASE_FILES:
    for n, ln in enumerate((ROOT / f).read_text(encoding="utf-8", errors="replace").split("\n"), 1):
        if PY_PRIM.search(ln):
            hits.append((f, n, ln.strip()[:100]))
nfiles = len(BASE_FILES)
for d in C_DIRS:
    for p in sorted((ROOT / d).rglob("*")):
        if p.suffix in (".c", ".h", ".cc", ".cpp") and "tweetnacl" not in p.name:
            nfiles += 1
            for n, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
                if C_PRIM.search(ln) and "cg_sink" not in ln:  # the two volatile sinks of firmware_r6/cg_r6_anchor.c keep the compiler from removing code in the footprint build; they are not synchronisation
                    hits.append((str(p.relative_to(ROOT)), n, ln.strip()[:100]))
for h in hits:
    print(h)
print("files scanned:", nfiles, "primitive hits:", len(hits))
# the check and the insert in the reference base are in one method with no call between them that can yield
src = (ROOT / "src/crashguard/verifier.py").read_text(encoding="utf-8")
i = src.index("if a.counter <= self.last.get")
j = src.index("self.last[a.node_id] = a.counter")
between = src[i:j]
one_method = "def " not in between
ent = [
    dict(name="r7c.atomic.files_scanned", value=nfiles, unit="files", origin="ANALYTICAL", source_file="scripts/r7c_atomic_scan.py", notes="base-side Python modules and every C/C++ source of firmware_rd, firmware_r6, firmware_r7, firmware_export and xsim/ns3 (tweetnacl excluded)"),
    dict(name="r7c.atomic.concurrency_primitive_hits", value=len(hits), unit="lines", origin="ANALYTICAL", source_file="scripts/r7c_atomic_scan.py", notes="lock, thread, async, atomic, volatile or interrupt primitives in those files; 0 means neither a lock nor a thread exists there"),
    dict(name="r7c.atomic.verifier_check_insert_in_one_call_without_yield", value=int(one_method), unit="flag", origin="ANALYTICAL", source_file="scripts/r7c_atomic_scan.py", notes="BaseVerifier.handle: the counter check and the update are consecutive statements of one method"),
    dict(name="r7c.atomic.enforced", value=0, unit="flag", origin="ANALYTICAL", source_file="scripts/r7c_atomic_scan.py", notes="atomicity holds only because the reference code is called from one sequential loop; nothing enforces it; no base server implementation exists in the repository"),
]
record_many(ent, purge_prefixes=("r7c.atomic.",))
print({e["name"]: e["value"] for e in ent})
