#!/usr/bin/env python3
"""Compare the output of one compiled C check with its expected values. Standard library only (runs on a bare Linux runner).

usage: c_compare.py <bundle dir> <check name> <C output file>   -> prints one JSON object
The C programs write float32 rows; the expected values are float64 rows (``expected.bin``). Numeric fields pass if the largest absolute difference is within the tolerance
of the manifest; discrete fields (``exact_fields``) must be identical. ``decision_mismatches`` (forests) counts rows whose crash decision at the check's threshold differs.
"""
import array
import json
import sys
from pathlib import Path


def load(path: Path, code: str) -> array.array:
    a = array.array(code)
    with open(path, "rb") as f:
        a.frombytes(f.read())
    return a


def main() -> int:
    bundle, name, out_path = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    man = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    chk = next(c for c in man["checks"] if c["name"] == name)
    n, k, fields = chk["n_rows"], chk["n_out"], chk["fields"]
    got = load(out_path, "f")
    want = load(bundle / chk["dir"] / "expected.bin", "d")
    res = dict(name=name, n_rows=n, rows_returned=len(got) // k if k else 0, fields={}, passes=False)
    if len(got) != n * k or len(want) != n * k:
        res["reason"] = f"output has {len(got)} values, expected {n * k}"
        print(json.dumps(res))
        return 1
    ok = True
    for j, f in enumerate(fields):
        diffs = [abs(got[i * k + j] - want[i * k + j]) for i in range(n)]
        fr = dict(max_abs_diff=max(diffs) if diffs else 0.0)
        if f in chk["exact_fields"]:
            fr["mismatches"] = sum(1 for d in diffs if d != 0.0)
            fr["passes"] = fr["mismatches"] == 0
        elif f in chk["tolerance"]:
            fr["tolerance"] = chk["tolerance"][f]
            fr["passes"] = fr["max_abs_diff"] <= chk["tolerance"][f]
        else:
            fr["passes"] = True  # reported, no pass rule (not one of the checked fields)
        ok &= fr["passes"]
        res["fields"][f] = fr
    if "decision_threshold" in chk:
        t = chk["decision_threshold"]
        res["decision_mismatches"] = sum(1 for i in range(n) if (got[i] >= t) != (want[i] >= t))
    res["passes"] = bool(ok)
    print(json.dumps(res))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
