"""Round 6 helpers (docs/02_preregistration/PREREGISTRATION_V17.md section 1): the hashed half of the VZCrash test split, and freeze and run-once guards with their own file results/tables/r6_frozen.json
(the round-5 file is a tagged result and is not touched)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FROZEN = ROOT / "results" / "tables" / "r6_frozen.json"
ALWAYS = ["src/crashguard/r6_common.py"]


def half6(event_id) -> int:
    """V17 section 2: half(id) = int(sha256("r6|" + decimal id), 16) mod 2; half 1 is the held-out half of R6-2."""
    return int(hashlib.sha256(("r6|" + str(int(event_id))).encode()).hexdigest(), 16) % 2


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(p).read_bytes().replace(b"\r\n", b"\n"))  # line endings do not change the hash (Windows and Linux checkouts)
    return h.hexdigest()


def sha256_json(o) -> str:
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def assert_fresh(prefix: str) -> None:
    res = ROOT / "results" / "results.json"
    if res.exists() and any(e["name"].startswith(prefix) for e in json.loads(res.read_text(encoding="utf-8"))):
        raise RuntimeError(f"results with the prefix {prefix} already exist: the held-out run is made once")


def freeze_entry(name: str, files: list[str], params: dict, prefix: str) -> dict:
    assert_fresh(prefix)
    d = dict(files={f: sha256_file(ROOT / f) for f in list(files) + ALWAYS}, params=params, params_sha256=sha256_json(params))
    cur = json.loads(FROZEN.read_text(encoding="utf-8")) if FROZEN.exists() else {}
    cur[name] = d
    FROZEN.write_text(json.dumps(cur, indent=1, sort_keys=True), encoding="utf-8")
    return d


def check_frozen(name: str, prefix: str) -> dict:
    assert_fresh(prefix)
    d = json.loads(FROZEN.read_text(encoding="utf-8"))[name]
    for f, h in d["files"].items():
        if sha256_file(ROOT / f) != h:
            raise RuntimeError(f"{f} changed after the freeze of {name}")
    if sha256_json(d["params"]) != d["params_sha256"]:
        raise RuntimeError(f"parameters of {name} changed after the freeze")
    return d["params"]
