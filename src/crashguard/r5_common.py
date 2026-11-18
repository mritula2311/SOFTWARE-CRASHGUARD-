"""Round 5 shared helpers (docs/02_preregistration/PREREGISTRATION_V16.md): hashed halves of the VZCrash test split, Holm over the fixed family of 13, frozen-file hashing.

Result recording uses ``rd_common.Rec`` with the prefix ``r5.``. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from crashguard.rd_common import NB, SEED, Rec, holm, sha256_file, sha256_json, sha256_text  # noqa: F401  (re-exported)

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "results" / "tables"
FROZEN = TABLES / "r5_frozen.json"
FAMILY = ("H-L1", "H-L2a", "H-L2b", "H-L3", "H-L4", "H-L5", "H-L6", "H-L7a", "H-L7b", "H-L8a", "H-L8b", "H-L10a", "H-L10b")  # V16 section 9: 13 hypotheses


def half_of(event_id) -> int:
    """V16 section 2.1: half(id) = int(sha256("r5|" + decimal id), 16) mod 2."""
    return int(hashlib.sha256(("r5|" + str(int(event_id))).encode()).hexdigest(), 16) % 2


def halves(event_ids: np.ndarray) -> np.ndarray:
    return np.array([half_of(e) for e in event_ids], dtype=np.int8)


def holm13(ps: dict[str, float]) -> dict[str, float]:
    """Holm step-down over the family of 13 (V16 section 9): hypotheses not yet tested enter with p = 1, which keeps the adjustment valid and conservative."""
    full = {h: 1.0 for h in FAMILY}
    for k, v in ps.items():
        assert k in full, k
        full[k] = float(v)
    adj = holm(full)
    return {k: adj[k] for k in ps}


ALWAYS = ["src/crashguard/r5_common.py"]  # in every freeze: the half rule, the freeze code and the Holm family


def _git_head() -> str:
    import subprocess

    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


def freeze_entry(name: str, files: list[str], params: dict, data_files: list[str] | None = None) -> dict:
    """Hash of the sources, the cached data and the parameters of one algorithm; stored in ``r5_frozen.json`` before the held-out run, with the git commit. A second freeze of the same algorithm refuses to
    overwrite an entry once held-out keys exist."""
    assert_fresh(name)
    d = dict(files={f: sha256_file(ROOT / f) for f in list(files) + ALWAYS}, data={f: sha256_file(ROOT / f) for f in (data_files or [])}, params=params, params_sha256=sha256_json(params), git_head=_git_head())
    cur = json.loads(FROZEN.read_text(encoding="utf-8")) if FROZEN.exists() else {}
    cur[name] = d
    FROZEN.write_text(json.dumps(cur, indent=1, sort_keys=True), encoding="utf-8")
    return d


def check_frozen(name: str) -> dict:
    """Return the frozen parameters after checking that the source and data hashes still match (raises if a frozen file changed) and that no held-out result of this algorithm exists yet."""
    assert_fresh(name)
    d = json.loads(FROZEN.read_text(encoding="utf-8"))[name]
    for f, h in {**d["files"], **d.get("data", {})}.items():
        if sha256_file(ROOT / f) != h:
            raise RuntimeError(f"{f} changed after the freeze of {name}")
    if sha256_json(d["params"]) != d["params_sha256"]:
        raise RuntimeError(f"parameters of {name} changed after the freeze")
    return d["params"]


def assert_fresh(name: str) -> None:
    """The held-out run is made once: refuse if results.json already holds a held-out key of the algorithm (V16 2.2)."""
    res = ROOT / "results" / "results.json"
    if not res.exists():
        return
    pre = {"l4": "r5.l4.ns3."}.get(name, f"r5.{name}.held")
    if any(e["name"].startswith(pre) for e in json.loads(res.read_text(encoding="utf-8"))):
        raise RuntimeError(f"held-out results of {name} already exist: the held-out run is made once")


def ensure_split_hashes(event_ids: np.ndarray) -> dict:
    """V16 2.1: the hashes of the sorted event-id lists of HALF0 and HALF1 of the test split are written before the first held-out run and checked afterwards."""
    ids = np.sort(np.asarray(event_ids, np.int64))
    h = halves(ids)
    cur = dict(half0=sha256_text(",".join(map(str, ids[h == 0]))), half1=sha256_text(",".join(map(str, ids[h == 1]))), n_half0=int((h == 0).sum()), n_half1=int((h == 1).sum()), rule="int(sha256('r5|'+id),16) mod 2")
    p = TABLES / "r5_split_hashes.json"
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        if old != cur:
            raise RuntimeError("the hashed halves of the test split changed")
    else:
        p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    return cur
