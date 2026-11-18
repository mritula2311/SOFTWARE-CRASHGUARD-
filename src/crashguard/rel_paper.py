"""Release numbers for the paper: paper/generated/numbers_release.tex, every macro read from results/results.json (none typed). Run: python -m crashguard.rel_paper"""
from __future__ import annotations

import json
from pathlib import Path

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}


def g(k: str, d: int = 3) -> str:
    x = R.get(k)
    return r"NOT\_RUN" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def main() -> None:
    gates = [R[k] for k in R if k.startswith("ph.gate.") and k.endswith(".passed")]
    auc_min = min([R[k] for k in R if k.startswith("ph.gate.") and k.endswith((".auc_D1", ".auc_D2"))])
    macros = {
        "RelGatesTotal": len(gates), "RelGatesPassed": sum(int(x) for x in gates), "RelAucMin": f"{auc_min:.3f}", "RelSurrAuc": g("ph.surrogate.auc"),
        "RelAOneGain": g("pa.hA1.n_cells_gain5", 0), "RelAOneLose": g("pa.hA1.n_cells_lose2", 0), "RelATwoGainOsdr": g("pa.hA2.vs_osdr.n_cells_gain5", 0), "RelATwoGainTam": g("pa.hA2.vs_tamang.n_cells_gain5", 0),
        "RelAnalyticDiff": g("pa.analytic.mean_abs_diff"), "RelDutyRuns": g("pa.held.duty_exceeded_runs", 0),
    }
    lines = [r"\newcommand{\%s}{%s}" % (k, v) for k, v in macros.items()]
    Path("paper/generated/numbers_release.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", len(lines), "macros")


if __name__ == "__main__":
    main()
