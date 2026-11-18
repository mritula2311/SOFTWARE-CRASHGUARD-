"""T6: severity-threshold sensitivity (definitions: docs/02_preregistration/PREREGISTRATION.md, Addendum 1, section A1.5, committed before this was run).

The three delta-V class limits (24, 40, 56 km/h) are shifted together by -2, -1, +1, +2 km/h and each alone by the same amounts (ASI levels unchanged); the reference and the assigned classes both use the shifted limits;
the class-conditional intervals (alpha 0.10) are recalibrated; H-a (mis-triage of P3 minus P1 at +-16 g, pool level: interval below zero and point below -0.02) and H-c (reduction at +-16 g minus at +-64 g above zero and
the width at +-64 g narrower) are recomputed. No delta-V severity scale from an opened source was available (the candidate pages returned HTTP 403 or 404, or an access check): that extra setting is NOT_RUN.
MEASURED_SOFTWARE on 176 NHTSA tests.
"""
from __future__ import annotations

import numpy as np

from crashguard import boot as B
from crashguard import ua_core as U

SHIFTS = (-2.0, -1.0, 1.0, 2.0)
SRC = "results/tables/t6_thresholds.csv"


def settings() -> list[tuple[str, tuple[float, float, float]]]:
    out = [("base", U.DV_LIMITS)]
    for d in SHIFTS:
        out.append((f"all{d:+g}".replace("+", "p").replace("-", "m"), tuple(x + d for x in U.DV_LIMITS)))
    for k, nm in enumerate(("low", "mid", "high")):
        for d in SHIFTS:
            lim = list(U.DV_LIMITS)
            lim[k] += d
            out.append((f"{nm}{d:+g}".replace("+", "p").replace("-", "m"), tuple(lim)))
    return out


def main() -> None:
    import pandas as pd

    from crashguard import config as C
    from crashguard.results import record_many

    core = U.build()
    grp = core.grp
    nm_ = lambda z: float(np.nanmean(z))  # noqa: E731
    ent: list[dict] = []
    rows = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"t6.{name}", value=value, unit=unit, origin="MEASURED_SOFTWARE", source_file=SRC, notes=notes))

    for tag, lim in settings():
        refc = U.ref_classes(core, lim)
        add(f"{tag}.limits", ",".join(f"{x:g}" for x in lim), "km/h", "delta-V class limits used for the reference and the assigned classes")
        red = {}
        width = {}
        for rg in (16.0, 32.0, 64.0):
            iv = U.interval_classes(core, rg, 0.10, "cc", limits=lim)
            mp, ep = U.mis_esc(iv["c_hat"], refc)
            mu, eu = U.mis_esc(iv["up"], refc)
            p, lo, hi = B.paired_diff_grouped(mp.T, mu.T, grp, nm_)  # upper minus point
            add(f"{tag}.r{rg:g}.mis_triage_upper_minus_point", round(p, 4), "fraction", "pool-level paired difference, grouped bootstrap")
            add(f"{tag}.r{rg:g}.mis_triage_upper_minus_point_lo", round(lo, 4), "fraction", "95% grouped bootstrap interval")
            add(f"{tag}.r{rg:g}.mis_triage_upper_minus_point_hi", round(hi, 4), "fraction", "95% grouped bootstrap interval")
            add(f"{tag}.r{rg:g}.mis_triage_point", round(float(np.nanmean(mp)), 4), "fraction", "")
            add(f"{tag}.r{rg:g}.escalation_point", round(float(np.nanmean(ep)), 4), "fraction", "")
            add(f"{tag}.r{rg:g}.escalation_upper", round(float(np.nanmean(eu)), 4), "fraction", "")
            add(f"{tag}.r{rg:g}.n_severe_or_critical_tests", int((refc >= 2).sum()), "tests", "tests whose reference class is Severe or Critical under these limits")
            red[rg] = (mp, mu)
            width[rg] = (iv["hi"] - iv["lo"] + 1).astype(float)
            width[rg][iv["c_hat"] < 0] = np.nan
            if rg == 16.0:
                ha = hi < 0 and p < -0.02
                add(f"{tag}.H_a_survives", int(ha), "flag", "pool-level interval of (upper minus point) below zero and point value below -0.02 at +-16 g")
        # H-c: reduction (point minus upper) at +-16 g minus that at +-64 g, and width at +-64 g minus +-16 g
        r16 = red[16.0][0] - red[16.0][1]
        r64 = red[64.0][0] - red[64.0][1]
        p, lo, hi = B.paired_diff_grouped(r64.T, r16.T, grp, nm_)
        pw, lw, hw = B.paired_diff_grouped(width[16.0].T, width[64.0].T, grp, nm_)
        add(f"{tag}.hc.reduction_16_minus_64", round(p, 4), "fraction", "paired, grouped bootstrap")
        add(f"{tag}.hc.reduction_16_minus_64_lo", round(lo, 4), "fraction", "95% grouped bootstrap interval")
        add(f"{tag}.hc.reduction_16_minus_64_hi", round(hi, 4), "fraction", "95% grouped bootstrap interval")
        add(f"{tag}.hc.width_64_minus_16", round(pw, 3), "classes", "paired, grouped bootstrap")
        add(f"{tag}.hc.width_64_minus_16_hi", round(hw, 3), "classes", "upper end of the 95% grouped bootstrap interval")
        hc = lo > 0 and hw < 0
        add(f"{tag}.H_c_survives", int(hc), "flag", "interval of (reduction at +-16 g minus at +-64 g) above zero and the interval of the width difference below zero")
        rows.append(dict(setting=tag, limits=lim, h_a=int(ent[-8]["value"] if False else 0)))
    add("external_scale", "NOT_RUN", "", "no delta-V severity scale from an opened source: the candidate pages (Traffic Injury Prevention articles, National Academies report, BASt, SWOV) returned HTTP 403, 404 or an access check; snippets mention categories below 24, 24 to 48 and above 48 km/h but were not opened and are not used")
    ent[-1]["origin"] = "NOT_RUN"
    pd.DataFrame([dict(name=e["name"], value=e["value"]) for e in ent]).to_csv(C.TABLES / "t6_thresholds.csv", index=False)
    record_many(ent, purge_prefixes=("t6.",))
    g = {e["name"]: e["value"] for e in ent}
    for tag, _l in settings():
        print(tag, g[f"t6.{tag}.limits"], "H-a", g[f"t6.{tag}.H_a_survives"], [g[f"t6.{tag}.r16.mis_triage_upper_minus_point{s}"] for s in ("", "_hi")], "H-c", g[f"t6.{tag}.H_c_survives"])


if __name__ == "__main__":
    main()
