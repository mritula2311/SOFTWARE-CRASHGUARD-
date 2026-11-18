"""Known-answer test of the micro-confirm tag in C (firmware_r6/cg_r6.c, host build in WSL) against Python's hmac module: tag = HMAC-SHA256(K, 'M' || T1 || byte0 || byte1 || boot counter)[:5]."""
import hashlib
import hmac
import random
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def wsl(cmd: str, stdin: str | None = None) -> str:
    try:
        r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd], capture_output=True, text=True, input=stdin, timeout=300)
    except Exception:  # noqa: BLE001
        pytest.skip("WSL not available")
    if r.returncode != 0:
        pytest.skip("host gcc not available: " + r.stderr[:100])
    return r.stdout


def test_micro_tag_matches_python_hmac_and_verification_rejects_a_flipped_bit():
    from crashguard import rd_firmware as F

    root = F.wsl_path(ROOT)
    wsl(f"mkdir -p {root}/build/r6fp && cd {root} && gcc -std=c99 -O2 -o build/r6fp/cg_r6_cli firmware_r6/cg_r6.c firmware_r6/cg_r6_cli.c firmware_rd/cg_rd.c firmware_rd/cg_stubs.c firmware_rd/tweetnacl.c -lm")
    rnd = random.Random(7)
    lines, expect = [], []
    for _ in range(200):
        key = bytes(rnd.randrange(256) for _ in range(rnd.choice([16, 32, 64])))
        t1 = bytes(rnd.randrange(256) for _ in range(8))
        b0, b1, boot = rnd.randrange(256), rnd.randrange(256), rnd.randrange(2**32)
        lines.append(f"{key.hex()} {t1.hex()} {b0} {b1} {boot}")
        tag = hmac.new(key, b"M" + t1 + bytes([b0, b1]) + boot.to_bytes(4, "big"), hashlib.sha256).digest()[:5]
        expect.append(bytes([b0, b1]) + tag)
    out = wsl(f"{root}/build/r6fp/cg_r6_cli", "\n".join(lines) + "\n").splitlines()
    assert len(out) == 200
    for o, e in zip(out, expect):
        frame, ok, flipped = o.split()
        assert frame == e.hex() and ok == "1" and flipped == "0"
