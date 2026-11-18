"""Freeze and run-once guards for the session-2 algorithms whose result keys do not start with ``r5.<name>.held`` (L7, L8, L9, L10); data-hash checks against V16 section 15.1.

``check_once(prefix)`` raises if results.json already holds a key with the prefix. ``freeze(name, files, params, data_files)`` stores the hashes with ``r5_common.freeze_entry`` and ``verify(name)``
checks them before the run. ``check_data(expected)`` compares downloaded files with the SHA-256 prefixes of section 15.1.
"""
from __future__ import annotations

import json

from crashguard import r5_common as R5

ROOT = R5.ROOT


def check_once(prefix: str) -> None:
    res = ROOT / "results" / "results.json"
    if res.exists() and any(e["name"].startswith(prefix) for e in json.loads(res.read_text(encoding="utf-8"))):
        raise RuntimeError(f"results with the prefix {prefix} already exist: the run is made once")


def freeze(name: str, files: list[str], params: dict, data_files: list[str] | None = None, prefix: str = "") -> dict:
    if prefix:
        check_once(prefix)
    return R5.freeze_entry(name, files, params, data_files)


def verify(name: str, prefix: str) -> dict:
    check_once(prefix)
    return R5.check_frozen(name)


def check_data(expected: dict[str, str]) -> None:
    """``expected`` maps a repository-relative path to the start of its SHA-256 (V16 section 15.1); raises on a mismatch or a missing file."""
    for f, h in expected.items():
        got = R5.sha256_file(ROOT / f)
        if not got.startswith(h):
            raise RuntimeError(f"{f}: SHA-256 {got[:12]} does not match {h} of V16 section 15.1")
