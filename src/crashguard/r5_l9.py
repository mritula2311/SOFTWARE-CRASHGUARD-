"""L9 (docs/02_preregistration/PREREGISTRATION_V16.md section 15.5): provisional-dispatch decision rule (ANALYTICAL on MEASURED_SOFTWARE inputs; descriptive, no hypothesis test, no superiority claim).

    python -m crashguard.r5_l9

Per provisional alert: it is retracted with probability ``r`` (the stored T3 retraction share at the 1% target) and otherwise reaches the responders ``g`` minutes before the confirm. Costs are in units of one
minute of delay: a false dispatch costs ``rho``; a retracted pre-alert costs a fraction ``F_PRE`` of a dispatch and a pre-alert captures a fraction ``PHI`` of the time gain (both stated assumptions).
Act on the provisional alert: expected cost r rho. Wait for the confirm: expected cost (1 - r) g. Pre-alert only: expected cost F_PRE r rho + (1 - r) (1 - PHI) g.
"""
from __future__ import annotations

import json
import sys

import numpy as np

F_PRE, PHI = 0.1, 0.5
SEED, NB = 42, 2000


def thresholds(r: float, g_min: float, f_pre: float = F_PRE, phi: float = PHI) -> dict:
    """Break-even ratios rho: act is better than wait below ``act_vs_wait``; pre-alert is better than act above ``pre_vs_act``; pre-alert is better than wait below ``pre_vs_wait``."""
    a = (1.0 - r) * g_min / r
    return dict(act_vs_wait=a, pre_vs_act=a * (1.0 - phi) / (1.0 - f_pre), pre_vs_wait=a * phi / f_pre)


def best_option(rho: float, r: float, g_min: float, f_pre: float = F_PRE, phi: float = PHI) -> str:
    cost = {"act": r * rho, "wait": (1.0 - r) * g_min, "pre": f_pre * r * rho + (1.0 - r) * (1.0 - phi) * g_min}
    return min(sorted(cost), key=lambda k: cost[k])


def sd_from_interval(lo: float, hi: float) -> float:
    return (hi - lo) / (2.0 * 1.96)


def boot(r: float, r_lo: float, r_hi: float, g_ms: float, g_lo: float, g_hi: float, seed: int = SEED, nb: int = NB) -> dict:
    rng = np.random.default_rng(seed)
    rr = np.clip(rng.normal(r, sd_from_interval(r_lo, r_hi), nb), 1e-6, 1 - 1e-6)
    gg = np.maximum(rng.normal(g_ms, sd_from_interval(g_lo, g_hi), nb), 0.0) / 60000.0
    t = thresholds(rr, gg)
    return {k: (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) for k, v in t.items()}


def run() -> None:
    from crashguard import r5_common as R5
    from crashguard import r5_guard as G

    G.verify("l9", "r5.l9.rho")
    r = {e["name"]: e["value"] for e in json.loads((R5.ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    rs, rl, rh = r["r3.t3.a1.retraction_share"], r["r3.t3.a1.retraction_share_lo"], r["r3.t3.a1.retraction_share_hi"]
    g, gl, gh = r["r3.t3.a1.earlier_ms_median"], r["r3.t3.a1.earlier_ms_median_lo"], r["r3.t3.a1.earlier_ms_median_hi"]
    t = thresholds(rs, g / 60000.0)
    b = boot(rs, rl, rh, g, gl, gh)
    rec = R5.Rec("r5.l9.", "src/crashguard/r5_l9.py", "ANALYTICAL")
    rec.add("input.retraction_share", rs, "fraction", "stored T3 value at the 1% target (r3.t3.a1.*), MEASURED_SOFTWARE input", origin="MEASURED_SOFTWARE")
    rec.add("input.time_gain_ms", g, "ms", "stored median time gain of the provisional alert (r3.t3.a1.earlier_ms_median)", origin="MEASURED_SOFTWARE")
    for k, v in t.items():
        rec.add(f"rho.{k}", v, "minutes of delay per dispatch", "break-even cost ratio: cost of a false dispatch in units of one minute of delay")
        rec.add(f"rho.{k}_lo", b[k][0], "minutes of delay per dispatch", "95% interval from resampling the two inputs from their stored intervals (normal approximation, seed 42)")
        rec.add(f"rho.{k}_hi", b[k][1], "minutes of delay per dispatch")
    rec.add("assumption.f_pre", F_PRE, "fraction", "cost of a retracted pre-alert as a fraction of a dispatch (stated assumption)")
    rec.add("assumption.phi", PHI, "fraction", "share of the time gain that a pre-alert captures (an assumption that V16 15.5 does not state; stated here and in DECISIONS.md)")
    rec.add("note.median_gain", "the stored gain is a median (the early-exit checkpoints are discrete); the expected-cost formula strictly needs a mean", "text")
    rec.add("l2_used", 0, "bool", "L2 did not pass, so no corroboration is used")
    rec.write()
    print(json.dumps(dict(thresholds=t, interval=b), indent=1))


def freeze() -> None:
    from crashguard import r5_guard as G

    d = G.freeze("l9", ["src/crashguard/r5_l9.py"], dict(F_PRE=F_PRE, PHI=PHI), None, "r5.l9.rho")
    print("frozen l9", d["params_sha256"][:16])


def main() -> None:
    {"freeze": freeze, "run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()


if __name__ == "__main__":
    main()
