"""Compare two results.json files: print every entry whose value differs by more than a relative tolerance (default 1e-6), and entries present in only one file.

Usage: python scripts/compare_results.py A/results/results.json B/results/results.json [tolerance]
Exit code 1 if anything differs. The env.* entries (Python version, platform) are compared like all others.
"""
from __future__ import annotations

import json
import sys


def load(p: str) -> dict:
    return {e["name"]: e for e in json.load(open(p, encoding="utf-8"))}


def main() -> int:
    a, b = load(sys.argv[1]), load(sys.argv[2])
    tol = float(sys.argv[3]) if len(sys.argv) > 3 else 1e-6
    bad = []
    for k in sorted(set(a) | set(b)):
        if k not in a or k not in b:
            bad.append((k, a.get(k, {}).get("value", "ABSENT"), b.get(k, {}).get("value", "ABSENT")))
            continue
        x, y = a[k]["value"], b[k]["value"]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) and not isinstance(y, bool):
            if abs(x - y) > tol * max(1.0, abs(x)):
                bad.append((k, x, y))
        elif x != y or a[k]["origin"] != b[k]["origin"]:
            bad.append((k, str(x)[:60], str(y)[:60]))
    print(f"{len(a)} entries in A, {len(b)} in B, {len(bad)} differ (relative tolerance {tol:g})")
    for k, x, y in bad[:200]:
        print(f"  {k}: {x} | {y}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
