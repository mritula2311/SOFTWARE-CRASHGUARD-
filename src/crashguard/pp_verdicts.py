"""Holm correction over the seven preregistered hypotheses of the positive-results push and their verdicts (docs/02_preregistration/PREREGISTRATION_V4.md section 0)."""
from __future__ import annotations

import json

from crashguard import pp_common as PC

HYP = [("H-P1", "p.p1.hP1"), ("H-P2", "p.p2.hP2"), ("H-P3a", "p.p3a.hP3a"), ("H-P3b", "p.p3b.hP3b"), ("H-P4a", "p.p4a.hP4a"), ("H-P4b", "p.p4b.hP4b"), ("H-P4c", "p.p4c.hP4c")]


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def main() -> dict:
    R = {e["name"]: e["value"] for e in json.load(open("results/results.json", encoding="utf-8"))}
    have = [(n, k) for n, k in HYP if f"{k}.p_raw" in R and f"{k}.criterion_met" in R]
    ps = [float(R[f"{k}.p_raw"]) for _, k in have]
    adj = holm(ps) if ps else []
    E = PC.PEntries("holm", "src/crashguard/pp_verdicts.py")
    out = {}
    for (n, k), p, a in zip(have, ps, adj):
        met = int(R[f"{k}.criterion_met"])
        verdict = "SUPPORTED" if met and a < 0.05 else ("MIXED" if met else "NOT SUPPORTED")
        out[n] = dict(p=p, holm=a, criterion=met, verdict=verdict)
        key = n.replace("-", "").lower()
        E.add(f"{key}.p_raw", round(p, 4), "probability")
        E.add(f"{key}.p_holm", round(a, 4), "probability", "Holm over the hypotheses that were run; bootstrap p-values have a floor of 0.001")
        E.add(f"{key}.criterion_met", met, "flag")
        E.add(f"{key}.verdict", verdict, "verdict", "SUPPORTED = criterion met and Holm p < 0.05; MIXED = criterion met, Holm p not below 0.05; NOT SUPPORTED = criterion not met")
    for n, k in HYP:
        if (n, k) not in have:
            E.not_run(n.replace("-", "").lower() + ".verdict", "verdict", "the hypothesis has not been scored (sealed or test split not yet evaluated)")
    E.add("m_hypotheses", len(have), "hypotheses", "number of hypotheses in the Holm family that were scored")
    E.flush()
    return out


if __name__ == "__main__":
    for k, v in main().items():
        print(k, v)
