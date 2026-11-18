"""T3: expected-cost view (definitions: docs/02_preregistration/PREREGISTRATION.md, Addendum 1, section A1.3, committed before this was run).

Cost per crash event = C_u x [true Severe or Critical assigned below Severe] + C_o x [true Low or Moderate assigned Severe or Critical]; expected cost = s x mis-triage x C_u + (1 - s) x escalation x C_o,
s = share of true Severe or Critical events among the pooled rows (observed, NHTSA, not representative; also varied). Break-even ratio r* = C_u / C_o at which P3 and P1 cost the same, with a grouped
(make and model) bootstrap interval. P2 has the class assignment of P1, so its class-cost break-even is the same; the delivery term (EXPLORATORY) separates P2 from P1 in the simulation.
MEASURED_SOFTWARE (class costs) and SIMULATED (delivery term).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import ua_core as U

RATIOS = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0)
SHARES = (("0p1", 0.1), ("0p3", 0.3), ("obs", None), ("0p9", 0.9))
SRC = "results/tables/t3_cost.csv"


def _tag(r: float) -> str:
    return f"{r:g}".replace(".", "p")


def main() -> None:
    from crashguard.results import record_many

    core = U.build()
    refc = U.ref_classes(core)
    grp = core.grp
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"t3.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    rows = []
    for rg in (16.0, 32.0, 64.0):
        iv = U.interval_classes(core, rg, 0.10, "cc")
        mp, ep = U.mis_esc(iv["c_hat"], refc)
        mu, eu = U.mis_esc(iv["up"], refc)
        packed = np.stack([mp.T, mu.T, ep.T, eu.T], axis=1)  # (n, 4, R)
        valid_sev = ~np.isnan(mp)
        s_obs = float(valid_sev.sum() / (valid_sev.sum() + (~np.isnan(ep)).sum()))
        add(f"r{rg:g}.s_observed", round(s_obs, 4), "fraction", "share of true Severe or Critical events among the pooled held-out rows (NHTSA; not representative of real crashes)")

        def means(z):
            return np.array([np.nanmean(z[:, k]) for k in range(4)]), z

        def stat_be(z, s_fixed=None):
            m = np.array([np.nanmean(z[:, k]) for k in range(4)])
            sv = (~np.isnan(z[:, 0])).sum()
            nv = (~np.isnan(z[:, 2])).sum()
            s = sv / (sv + nv) if s_fixed is None else s_fixed
            dm, de = m[0] - m[1], m[3] - m[2]
            return float((1 - s) * de / (s * dm)) if dm > 0 else float("inf")

        # equal-escalation point-class baseline P1e (threshold factor f from T1, chosen without any simulated outcome)
        import json as _json

        res_ = {e["name"]: e["value"] for e in _json.loads(open("results/results.json", encoding="utf-8").read())}
        f_ = float(res_[f"t1.r{rg:g}.f"])
        me_, ee_ = U.mis_esc(U.point_classes(core, rg, scale=f_), refc)
        packed_e = np.stack([me_.T, mu.T, ee_.T, eu.T], axis=1)
        for tag, s_fix in SHARES:
            p, lo, hi = B.ci_grouped(packed, grp, lambda z, s=s_fix: stat_be(z, s))
            sv = s_obs if s_fix is None else s_fix
            add(f"r{rg:g}.s{tag}.break_even_ratio", round(p, 3), "C_u / C_o", f"ratio at which P3 and P1 cost the same, share of true Severe or Critical events s = {sv:.3f}; P3 is cheaper above it; grouped bootstrap interval")
            add(f"r{rg:g}.s{tag}.break_even_ratio_lo", round(lo, 3), "C_u / C_o", "95% grouped bootstrap interval")
            add(f"r{rg:g}.s{tag}.break_even_ratio_hi", round(hi, 3) if np.isfinite(hi) else "NOT_RUN", "C_u / C_o", "95% grouped bootstrap interval" if np.isfinite(hi) else "upper end infinite: some resamples have no mis-triage gain", "MEASURED_SOFTWARE" if np.isfinite(hi) else "NOT_RUN")
        # expected cost per crash event, in units of C_o, for a range of ratios; P0, P1, P2 share the point classes, P3 and P4 the upper end
        for tag, s_fix in SHARES:
            sv = s_obs if s_fix is None else s_fix
            for r in RATIOS:
                def cost(z, k_m, k_e, r=r, sv=sv):
                    return float(sv * np.nanmean(z[:, k_m]) * r + (1 - sv) * np.nanmean(z[:, k_e]))

                for pol, km, ke in (("P1", 0, 2), ("P3", 1, 3)):
                    p, lo, hi = B.ci_grouped(packed, grp, lambda z, km=km, ke=ke: cost(z, km, ke))
                    add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost.{pol}", round(p, 4), "C_o per crash event", "expected cost; P0 and P2 have the cost of P1, P4 that of P3 (class assignment only)")
                    add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost.{pol}_lo", round(lo, 4), "C_o per crash event", "95% grouped bootstrap interval")
                    add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost.{pol}_hi", round(hi, 4), "C_o per crash event", "95% grouped bootstrap interval")
                d_e = B.ci_grouped(packed_e, grp, lambda z: cost(z, 1, 3) - cost(z, 0, 2))
                add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost_diff_p3_minus_p1e", round(d_e[0], 4), "C_o per crash event", "negative = P3 is cheaper than the table with thresholds lowered to the same escalation (T1); grouped bootstrap interval")
                add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost_diff_p3_minus_p1e_lo", round(d_e[1], 4), "C_o per crash event", "95% grouped bootstrap interval")
                add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost_diff_p3_minus_p1e_hi", round(d_e[2], 4), "C_o per crash event", "95% grouped bootstrap interval")
                d = B.ci_grouped(packed, grp, lambda z: cost(z, 1, 3) - cost(z, 0, 2))
                add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost_diff_p3_minus_p1", round(d[0], 4), "C_o per crash event", "negative = P3 is cheaper; grouped bootstrap interval")
                add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost_diff_p3_minus_p1_lo", round(d[1], 4), "C_o per crash event", "95% grouped bootstrap interval")
                add(f"r{rg:g}.s{tag}.ratio{_tag(r)}.cost_diff_p3_minus_p1_hi", round(d[2], 4), "C_o per crash event", "95% grouped bootstrap interval")
                rows.append(dict(range_g=rg, s=tag, ratio=r, cost_p1=cost(np.nan_to_num(packed, nan=np.nan), 0, 2), cost_p3=cost(packed, 1, 3), diff_lo=d[1], diff_hi=d[2]))
    # delivery term (EXPLORATORY, simulation): cost of a true Critical alert without a signed ACK within 10 s, C_l = C_u, default cells at +-16 g
    s11 = pd.read_csv(C.TABLES / "s11_sct.csv")
    pi_crit = float((refc == 3).mean())
    add("pi_critical_tests", round(pi_crit, 4), "fraction", "share of the 176 tests whose reference class is Critical")
    for mode in ("steady", "burst"):
        g = s11[(s11.range_g == 16.0) & (s11["mode"] == mode) & (s11.scen == "base")]
        for pol in ("P0", "P1", "P2", "P3", "P4"):
            miss = float(1.0 - g[g.pol == pol].reach10_critical.mean())
            add(f"delivery.{mode}.{pol}.share_critical_not_reached_10s", round(miss, 4), "fraction", "EXPLORATORY: 1 minus the mean critical reach within 10 s, default cell at +-16 g; the delivery cost term is C_l x pi_critical x this share with C_l = C_u", "SIMULATED")
    pd.DataFrame(rows).to_csv(C.TABLES / "t3_cost.csv", index=False)
    record_many(ent, purge_prefixes=("t3.",))
    g = {e["name"]: e["value"] for e in ent}
    for rg in (16.0, 32.0, 64.0):
        print(rg, "break-even (observed share)", [g[f"t3.r{rg:g}.sobs.break_even_ratio{s}"] for s in ("", "_lo", "_hi")], "s", g[f"t3.r{rg:g}.s_observed"])


if __name__ == "__main__":
    main()
