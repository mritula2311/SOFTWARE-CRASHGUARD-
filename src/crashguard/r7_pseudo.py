"""Round 7 B1 reference implementation of the rotating pseudonym and the base resolver (docs/02_preregistration/PREREGISTRATION_V18.md section 3.1).

Pseudonym p = trunc_L(HMAC-SHA256(k_v, "P" || boot (u32, big endian) || ctr (u32, big endian))). The base keeps, per vehicle, the pseudonyms of the next m counters of the vehicle's current boot and a hash index from
pseudonym to the (vehicle, boot, counter) entries; a frame whose pseudonym matches one or more entries is verified with the tag (the tag decides: HMAC-SHA256(k_v, frame without tag || boot || ctr) truncated to 8 bytes; boot and ctr are the window entry's values and are not sent), the window
moves to the matched counter, and a frame that does not resolve or fails the tag changes nothing (cell-level rate limiting only, not modelled here). After a reboot the boot counter rises; the base tries the boot values
boot + 1 to boot + 3 for an unresolved frame (``resync``).

    python -m crashguard.r7_pseudo bench          # H-R7-B1 (MEASURED_SOFTWARE) and H-R7-B2 (ANALYTICAL with enumeration)

The C routine of the same name is in firmware_r7/cg_r7.c; ``tests/test_r7_pseudo.py`` checks that both give the same pseudonym.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import platform
import random
import struct
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/r7_pseudo.py"
TAG_BYTES = 8


def pseudonym(key: bytes, boot: int, ctr: int, L: int) -> bytes:
    return hmac.new(key, b"P" + struct.pack(">II", boot, ctr), hashlib.sha256).digest()[:L]


def tag(key: bytes, frame: bytes, boot: int, ctr: int) -> bytes:
    """The tag covers the frame bytes and, as associated data that is not sent, the boot counter and the counter of the window entry: of several window entries that share a pseudonym only the true one verifies."""
    return hmac.new(key, frame + struct.pack(">II", boot, ctr), hashlib.sha256).digest()[:TAG_BYTES]


class Base:
    """Resolver for n vehicles with a window of m pseudonyms of L bytes."""

    def __init__(self, keys: list[bytes], m: int, L: int, boot: int = 1):
        self.keys, self.m, self.L = keys, m, L
        self.boot = [boot] * len(keys)
        self.last = [0] * len(keys)  # last accepted counter (window = last + 1 .. last + m)
        self.top = [0] * len(keys)  # highest counter whose pseudonym is in the index
        self.index: dict[bytes, list[tuple[int, int, int]]] = {}
        for v in range(len(keys)):
            self._extend(v, m)

    def _extend(self, v: int, upto: int) -> None:
        for c in range(self.top[v] + 1, upto + 1):
            self.index.setdefault(pseudonym(self.keys[v], self.boot[v], c, self.L), []).append((v, self.boot[v], c))
        self.top[v] = max(self.top[v], upto)

    def resolve(self, frame: bytes) -> tuple[int, int] | None:
        """frame = type byte, pseudonym (L bytes), body, tag (8 bytes). Returns (vehicle, counter) of an accepted frame."""
        p = frame[1:1 + self.L]
        for v, b, c in self.index.get(p, ()):
            if b != self.boot[v] or c <= self.last[v]:
                continue  # stale entry (earlier boot or an already accepted counter)
            if hmac.compare_digest(tag(self.keys[v], frame[:-TAG_BYTES], b, c), frame[-TAG_BYTES:]):
                self.last[v] = c
                self._extend(v, c + self.m)
                return v, c
        return None

    def resync(self, frame: bytes, max_boot_step: int = 3) -> tuple[int, int] | None:
        """Unresolved frame: for every vehicle try the next boot values (the boot counter of a rebooted vehicle is higher); linear in the number of vehicles, run only for frames that did not resolve."""
        p = frame[1:1 + self.L]
        for v, key in enumerate(self.keys):
            for db in range(1, max_boot_step + 1):
                b = self.boot[v] + db
                for c in range(1, self.m + 1):
                    if pseudonym(key, b, c, self.L) == p and hmac.compare_digest(tag(key, frame[:-TAG_BYTES], b, c), frame[-TAG_BYTES:]):
                        self.boot[v], self.last[v], self.top[v] = b, c, 0
                        self._extend(v, c + self.m)
                        return v, c
        return None


def make_frame(key: bytes, boot: int, ctr: int, L: int, payload: bytes) -> bytes:
    body = b"\x01" + pseudonym(key, boot, ctr, L) + payload
    return body + tag(key, body, boot, ctr)


def collision_probability(n: int, m: int, L: int) -> float:
    """H-R7-B2 definition: probability that a frame's pseudonym equals a pseudonym in another vehicle's window, P = 1 - (1 - 2^-8L)^((n - 1) m)."""
    return -math.expm1(((n - 1) * m) * math.log1p(-(2.0 ** (-8 * L))))


def collision_enumeration(n: int, m: int, L: int, trials: int, seed: int) -> tuple[float, int]:
    """Monte Carlo over real pseudonyms: share of sampled frames whose pseudonym appears in another vehicle's window (the pseudonyms are HMAC outputs, so this is the same experiment as the formula)."""
    rng = random.Random(seed)
    keys = [rng.randbytes(32) for _ in range(n)]
    idx: dict[bytes, set[int]] = {}
    for v, k in enumerate(keys):
        for c in range(1, m + 1):
            idx.setdefault(pseudonym(k, 1, c, L), set()).add(v)
    hits = 0
    for _ in range(trials):
        v = rng.randrange(n)
        c = rng.randrange(1, m + 1)
        owners = idx[pseudonym(keys[v], 1, c, L)]
        hits += int(len(owners - {v}) > 0)
    return hits / trials, hits


def bench(n: int = 1000, m: int = 16, L: int = 4, frames: int = 200_000, reps: int = 5, seed: int = 42) -> dict:
    rng = random.Random(seed)
    keys = [rng.randbytes(32) for _ in range(n)]
    base = Base(keys, m, L)
    ctr = [0] * n
    fr = []
    for _ in range(frames):
        v = rng.randrange(n)
        ctr[v] += 1 + (rng.randrange(1, m) if rng.random() < 0.1 else 0)  # 10% of frames follow a loss of up to m - 1 frames
        fr.append((v, make_frame(keys[v], 1, ctr[v], L, rng.randbytes(8))))
    # the frames are rebuilt per repetition because the base state advances
    times = []
    ok = 0
    for r in range(reps):
        base = Base(keys, m, L)
        t0 = time.perf_counter()
        for v, f in fr:
            res = base.resolve(f)
            ok += res is not None and res[0] == v
        times.append((time.perf_counter() - t0) / frames)
    return dict(n=n, m=m, L=L, frames=frames, reps=reps, per_frame_s=times, resolved_share=ok / (frames * reps))


def cpu_name() -> str:
    import subprocess

    try:
        return subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"], capture_output=True, text=True, timeout=60).stdout.strip() or platform.processor()
    except Exception:  # noqa: BLE001
        return platform.processor()


def c_bench(n: int, m: int, L: int, frames: int, reps: int) -> list[float]:
    import subprocess

    cmd = f"cd /mnt/d/crashguard-software/crashguard-software && build/r7/cg_r7_bench {n} {m} {L} {frames} {reps}"
    out = subprocess.run(["wsl", "-u", "root", "bash", "-c", cmd], capture_output=True, text=True, timeout=900).stdout.splitlines()
    rows = [ln.split() for ln in out if ln.strip()]
    assert all(int(r[1]) == frames for r in rows), rows  # every frame resolved to its vehicle
    return [float(r[0]) for r in rows]


def main() -> None:
    from crashguard.results import record_many

    ent: list[dict] = []

    def add(name, v, unit, origin, note=""):
        ent.append(dict(name=f"r7.b.{name}", value=(round(v, 12) if isinstance(v, float) and math.isfinite(v) else v), unit=unit, origin=origin, source_file=SRC, notes=note))

    cpu = cpu_name()
    add("bench.cpu", cpu, "text", "MEASURED_SOFTWARE", "development machine; Python 3.12 (hmac module, OpenSSL) and gcc in WSL (cg_hmac_sha256 of firmware_rd, -O2)")
    worst = 0.0
    for L in (2, 4):
        b = bench(1000, 16, L, 200_000, 5)
        c = c_bench(1000, 16, L, 200_000, 5)
        worst = max(worst, max(b["per_frame_s"]), max(c))
        add(f"bench.python.L{L}.mean_per_frame", sum(b["per_frame_s"]) / 5, "s", "MEASURED_SOFTWARE", "1,000 vehicles, m = 16, 200,000 frames, 5 repetitions: mean")
        add(f"bench.python.L{L}.worst_rep", max(b["per_frame_s"]), "s", "MEASURED_SOFTWARE", "worst repetition")
        add(f"bench.c.L{L}.mean_per_frame", sum(c) / 5, "s", "MEASURED_SOFTWARE", "same routine in C")
        add(f"bench.c.L{L}.worst_rep", max(c), "s", "MEASURED_SOFTWARE", "worst repetition")
        add(f"bench.python.L{L}.resolved_share", b["resolved_share"], "fraction", "MEASURED_SOFTWARE", "frames resolved to their vehicle (10% of frames follow a loss of up to m - 1 frames)")
    add("hR7_B1.worst_mean_per_frame", worst, "s", "MEASURED_SOFTWARE", "largest repetition mean over both builds and L = 2 and 4")
    add("hR7_B1.criterion_met", int(worst <= 1e-3), "flag", "MEASURED_SOFTWARE", "worst mean at most 1 ms")
    add("hR7_B1.p", 1e-300 if worst <= 1e-3 else 1.0, "p-value", "MEASURED_SOFTWARE", "measured bound, not a sampling test (V18)")
    # resynchronisation after a reboot: the unresolved frame is tested against the next three boot values of every vehicle (descriptive)
    rng = random.Random(42)
    keys = [rng.randbytes(32) for _ in range(1000)]
    base = Base(keys, 16, 4)
    f = make_frame(keys[500], 2, 1, 4, b"r" * 8)
    t0 = time.perf_counter()
    assert base.resync(f) == (500, 1)
    add("resync.python.one_frame_s", time.perf_counter() - t0, "s", "MEASURED_SOFTWARE", "first frame of a rebooted vehicle, 1,000 vehicles, m = 16, boot steps 1 to 3, the vehicle at position 500 (average case)")
    # H-R7-B2
    ok_L2 = None
    for L in (1, 2, 3, 4, 5, 6):
        pf = collision_probability(1000, 16, L)
        add(f"hR7_B2.L{L}.p_collision_formula", pf, "probability", "ANALYTICAL", "1 - (1 - 2^-8L)^((n - 1) m), n = 1000, m = 16")
        add(f"hR7_B2.L{L}.extra_candidates_per_frame", 999 * 16 / 2.0 ** (8 * L), "count", "ANALYTICAL", "expected number of other-vehicle window entries with the same pseudonym (each costs one tag check)")
        if L in (2, 4):
            fr, hits = collision_enumeration(1000, 16, L, 200_000, 42)
            add(f"hR7_B2.L{L}.p_collision_enumerated", fr, "fraction", "ANALYTICAL", f"enumeration over 200,000 sampled frames with real HMAC pseudonyms (seed 42): {hits} frames collide")
        if L == 2:
            ok_L2 = pf <= 1e-6
    add("hR7_B2.first_L_meeting_bound", next(L for L in range(1, 9) if collision_probability(1000, 16, L) <= 1e-6), "bytes", "ANALYTICAL", "smallest L with P <= 1e-6")
    add("hR7_B2.criterion_met", int(bool(ok_L2)), "flag", "ANALYTICAL", "P <= 1e-6 at L = 2 (the frame with the smallest L: flash and cancel)")
    add("hR7_B2.p", 1e-300 if ok_L2 else 1.0, "p-value", "ANALYTICAL", "V18: 1e-300 if P <= 1e-6 at L = 2, else 1")
    record_many(ent, purge_prefixes=("r7.b.",))
    print({e["name"]: e["value"] for e in ent if "hR7" in e["name"] or "worst" in e["name"] or "resync" in e["name"]})


if __name__ == "__main__":
    import sys

    main() if len(sys.argv) > 1 and sys.argv[1] == "bench" else print(json.dumps(bench(frames=20000, reps=1), indent=1))
