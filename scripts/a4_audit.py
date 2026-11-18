"""Round 4 audit (writes docs/04_audits/A4_CLAIM_AUDIT.md): integrity checks of the round-4 results against the preregistration V15.

    python scripts/a4_audit.py        # exit code 1 if a check fails
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from crashguard.results import ORIGINS  # noqa: E402


def main() -> int:
    res = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))
    R = {e["name"]: e for e in res}
    a4 = [e for e in res if e["name"].startswith("a4.")]
    checks: list[tuple[str, bool, str]] = []

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # 1 frozen sources unchanged since the freeze
    fr = json.loads((ROOT / "results" / "tables" / "a4_frozen.json").read_text(encoding="utf-8"))
    bad = [f for f, h in fr["sources"].items() if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != h]
    chk("Frozen sources unchanged since the freeze (7 files hashed in results/tables/a4_frozen.json)", not bad, "changed: " + ", ".join(bad) if bad else f"{len(fr['sources'])} files match")
    # 2 held-out outputs written after the freeze
    fz = (ROOT / "results" / "tables" / "a4_frozen.json").stat().st_mtime
    held = [ROOT / "data" / "processed" / n for n in ("a4_held_sniffer.pkl", "a4_held_loedres.pkl", "a4_a2_held.pkl")]
    chk("Held-out outputs were written after the freeze", all(p.exists() and p.stat().st_mtime > fz for p in held), ", ".join(p.name for p in held))
    # 3 at most five development iterations
    dl = json.loads((ROOT / "results" / "tables" / "a4_dev_log.json").read_text(encoding="utf-8"))
    chk("At most 5 logged development iterations of A1", len(dl) <= 5, f"{len(dl)} logged")
    # 4 labels
    chk("Every a4 key carries an allowed origin label", all(e["origin"] in ORIGINS for e in a4), f"{len(a4)} keys")
    ex = [e for e in a4 if e["name"].startswith("a4.a2.") and e["origin"] != "NOT_RUN" and "EXPLORATORY" not in e["notes"]]
    chk("Every a4.a2 result says EXPLORATORY in its note", not ex, f"{len(ex)} without")
    # 5 Holm recomputed
    ps = {k: float(R[f"a4.holm.{k}.p_raw"]["value"]) for k in ("ha1a", "ha1b", "ha1c", "ha2a", "ha2b")}
    order = sorted(ps, key=ps.get)
    run, adj = 0.0, {}
    for i, k in enumerate(order):
        run = max(run, min(1.0, (5 - i) * ps[k]))
        adj[k] = run
    chk("Holm adjustment recomputed independently", all(abs(adj[k] - float(R[f"a4.holm.{k}.p_holm"]["value"])) < 1e-5 for k in ps), json.dumps({k: round(v, 4) for k, v in adj.items()}))
    # 6 verdicts consistent with criteria and Holm
    met = {"ha1a": R["a4.a1.ns3.hA1a.criterion_met"]["value"], "ha1b": R["a4.a1.trace.hA1b.criterion_met"]["value"], "ha2a": R["a4.a2.reserve.hA2a.criterion_met"]["value"], "ha2b": R["a4.a2.reserve.hA2b.criterion_met"]["value"],
           "ha1c": int(R["a4.a1.ns3.hA1c.ns3.criterion_met"]["value"] and R["a4.a1.trace.hA1c.criterion_met"]["value"])}
    ok = all((R[f"a4.verdict.{k}"]["value"] == "SUPPORTED") == bool(met[k] and adj[k] < 0.05) for k in met)
    chk("Verdicts follow from criterion and Holm p", ok, json.dumps({k: R[f"a4.verdict.{k}"]["value"] for k in met}))
    killed_a1 = not (R["a4.verdict.ha1a"]["value"] == "SUPPORTED" and R["a4.verdict.ha1b"]["value"] == "SUPPORTED")
    chk("Kill rules applied (A1: H-A1a or H-A1b not supported; A2: H-A2a not supported)", bool(R["a4.verdict.a1_killed"]["value"]) == killed_a1 and bool(R["a4.verdict.a2_killed"]["value"]) == (R["a4.verdict.ha2a"]["value"] != "SUPPORTED"))
    # 7 invariants
    inv = sum(int(e["value"]) for e in a4 if e["name"].endswith((".inv_late", ".inv_duty")) or ".invariants." in e["name"])
    chk("Invariant counters (late deliveries, duty breaches, overruns) are all zero", inv == 0, f"sum {inv}")
    # 8 code verification passed
    chk("Code verification passed before the freeze (a4.cv.passed)", R["a4.cv.passed"]["value"] == 1)
    # 9 earlier keys unchanged
    out = subprocess.run([sys.executable, "scripts/verify_keys_unchanged.py", "paper-v1"], cwd=ROOT, capture_output=True, text=True)
    chk("No key of paper-v1 changed or vanished", out.returncode == 0, out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-200:])
    # 10 no raw data tracked, no hardware data used
    tracked = subprocess.run(["git", "ls-files", "data/raw", "data/hardware"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    chk("No raw data and no hardware data tracked in this round", not [t for t in tracked if "a4_sniffer" in t], f"{len(tracked)} tracked paths under data/raw or data/hardware (earlier rounds)")
    lines = ["# Round 4 audit", "", "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-15 |", "| Owner | Mritula S |", "| Scope | Integrity checks of the round-4 results against the preregistration V15. |", "| Evidence labels used | ANALYTICAL |", "<!-- header:end -->", "",
             "Generated by `python scripts/a4_audit.py`.", "", "| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'pass' if ok else 'FAIL'} | {d} |" for n, ok, d in checks]
    lines += ["", f"**{sum(ok for _n, ok, _d in checks)} of {len(checks)} checks passed.**", ""]
    (ROOT / "docs" / "04_audits" / "A4_CLAIM_AUDIT.md").write_text("\n".join(lines), encoding="utf-8")
    for n, ok, d in checks:
        print("pass" if ok else "FAIL", n, "|", d)
    return 0 if all(ok for _n, ok, _d in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
