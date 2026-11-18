"""T2: trade-off curves, mis-triage against the share of non-severe events escalated (definitions: docs/02_preregistration/PREREGISTRATION.md, Addendum 1, section A1.2, committed before this was run).

Point-class family (P0, P1, P2 share the class assignment): every class boundary divided by f on a 25-point grid. Interval family (P3, P4; P4 differs only by an airtime cap, so its curve coincides):
class-conditional one-sided upper end with alpha on an 11-point grid. All points are kept; the curves are closed with (0, 1) and (1, 0); area by the trapezoid rule, lower is better;
95% grouped (make and model) bootstrap intervals for each area and for the difference. MEASURED_SOFTWARE on 176 NHTSA tests, no simulation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import ua_core as U

F_VALUES = np.round(np.arange(0.40, 1.6001, 0.05), 2)
MATCH = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7)
ALPHAS = (0.50, 0.40, 0.30, 0.20, 0.15, 0.10, 0.07, 0.05, 0.03, 0.02, 0.01)
SRC = "results/tables/t2_pareto.csv"


def curve_arrays(core: U.Core, rg: float) -> dict:
    refc = U.ref_classes(core)
    out = {}
    pts = []
    for f in F_VALUES:
        pts.append(("point", float(f), U.mis_esc(U.point_classes(core, rg, scale=float(f)), refc)))
    for a in ALPHAS:
        pts.append(("interval", a, U.mis_esc(U.interval_classes(core, rg, a, "cc")["up"], refc)))
    for fam in ("point", "interval"):
        sel = [p for p in pts if p[0] == fam]
        # x (n, K, R) escalation indicators and y (n, K, R) mis-triage indicators, tests as the first axis (the bootstrap resamples tests)
        out[fam] = dict(params=[p[1] for p in sel], mis=np.stack([p[2][0].T for p in sel], axis=1), esc=np.stack([p[2][1].T for p in sel], axis=1))
    return out


def curve_and_auc(mis: np.ndarray, esc: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    x = np.nanmean(esc, axis=(0, 2))
    y = np.nanmean(mis, axis=(0, 2))
    return x, y, U.auc(x, y)


def main() -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style
    from crashguard.results import record_many

    core = U.build()
    grp = core.grp
    ent: list[dict] = []
    rows = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"t2.{name}", value=value, unit=unit, origin="MEASURED_SOFTWARE", source_file=SRC, notes=notes))

    style()
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.8))
    for ax, rg in zip(axes, (16.0, 32.0, 64.0)):
        ca = curve_arrays(core, rg)
        res = {}
        for fam in ("point", "interval"):
            d = ca[fam]
            x, y, a_ = curve_and_auc(d["mis"], d["esc"])
            res[fam] = (x, y, a_)
            for p_, xi, yi in zip(d["params"], x, y):
                rows.append(dict(range_g=rg, family=fam, parameter=p_, escalation=xi, mis_triage=yi))
                add(f"r{rg:g}.{fam}.p{p_:g}.escalation", round(float(xi), 4), "fraction", "pooled held-out rows")
                add(f"r{rg:g}.{fam}.p{p_:g}.mis_triage", round(float(yi), 4), "fraction", "pooled held-out rows")
            # bootstrap of the area: resample tests (make and model groups) jointly for both families
        packed = np.concatenate([np.concatenate([ca["point"]["mis"], ca["point"]["esc"]], axis=1), np.concatenate([ca["interval"]["mis"], ca["interval"]["esc"]], axis=1)], axis=1)
        kp, ki = len(ca["point"]["params"]), len(ca["interval"]["params"])

        def areas(z, kp=kp, ki=ki):
            x_pt, y_pt = np.nanmean(z[:, kp:2 * kp], axis=(0, 2)), np.nanmean(z[:, :kp], axis=(0, 2))
            o = 2 * kp
            x_iv, y_iv = np.nanmean(z[:, o + ki:o + 2 * ki], axis=(0, 2)), np.nanmean(z[:, o:o + ki], axis=(0, 2))
            out = [U.auc(x_pt, y_pt), U.auc(x_iv, y_iv)]
            for xs, ys in ((x_pt, y_pt), (x_iv, y_iv)):  # EXPLORATORY: mis-triage at matched escalation by linear interpolation inside the range the family reaches
                order = np.argsort(xs)
                lo_, hi_ = xs[order][0], xs[order][-1]
                out += [float(np.interp(g_, xs[order], ys[order])) if lo_ <= g_ <= hi_ else float("nan") for g_ in MATCH]
            return out

        draws = []
        for idx in B._gidx(B.group_members(grp), B.N_BOOT, B.SEED):
            draws.append(areas(packed[idx]))
        draws = np.array(draws)
        for k_, fam in enumerate(("point", "interval")):
            lo, hi = np.quantile(draws[:, k_], [0.025, 0.975])
            add(f"r{rg:g}.{fam}.auc", round(res[fam][2], 4), "area", "area under mis-triage against escalation over [0, 1], lower is better")
            add(f"r{rg:g}.{fam}.auc_lo", round(float(lo), 4), "area", "95% grouped bootstrap interval")
            add(f"r{rg:g}.{fam}.auc_hi", round(float(hi), 4), "area", "95% grouped bootstrap interval")
        for j_, g_ in enumerate(MATCH):
            for fam_i, fam in ((0, "point"), (1, "interval")):
                col = draws[:, 2 + fam_i * len(MATCH) + j_]
                add(f"r{rg:g}.matched.x{int(g_ * 100)}.{fam}.mis_triage", round(float(np.nanmedian(col)), 4) if np.isfinite(col).any() else "NOT_RUN", "fraction", "EXPLORATORY: mis-triage at this escalation by linear interpolation of the family's curve (median of the bootstrap draws); NOT_RUN where the family does not reach this escalation")
            dcol = draws[:, 2 + len(MATCH) + j_] - draws[:, 2 + j_]
            if np.isfinite(dcol).sum() > 100:
                add(f"r{rg:g}.matched.x{int(g_ * 100)}.interval_minus_point", round(float(np.nanmedian(dcol)), 4), "fraction", "EXPLORATORY: interval family minus point-class family at matched escalation; negative = the interval family is better")
                add(f"r{rg:g}.matched.x{int(g_ * 100)}.interval_minus_point_lo", round(float(np.nanquantile(dcol, 0.025)), 4), "fraction", "95% grouped bootstrap interval")
                add(f"r{rg:g}.matched.x{int(g_ * 100)}.interval_minus_point_hi", round(float(np.nanquantile(dcol, 0.975)), 4), "fraction", "95% grouped bootstrap interval")
        d_ = draws[:, 1] - draws[:, 0]
        add(f"r{rg:g}.auc_interval_minus_point", round(res["interval"][2] - res["point"][2], 4), "area", "interval family minus point-class family; negative = the interval family is better")
        add(f"r{rg:g}.auc_interval_minus_point_lo", round(float(np.quantile(d_, 0.025)), 4), "area", "95% grouped bootstrap interval")
        add(f"r{rg:g}.auc_interval_minus_point_hi", round(float(np.quantile(d_, 0.975)), 4), "area", "95% grouped bootstrap interval")
        for fam, col, lab in (("point", COLORS[0], "P0, P1, P2: point class, thresholds scaled"), ("interval", COLORS[1], "P3, P4: upper end of the class interval")):
            x, y, _a = res[fam]
            o = np.argsort(x)
            ax.plot(np.r_[0, x[o], 1], np.r_[1, y[o], 0], marker="o", ms=3.5, lw=1.3, color=col, label=lab)
        ax.set_title(f"+-{rg:g} g")
        ax.set_xlabel("Non-severe events sent to the fast path (fraction)")
        ax.set_ylabel("Severe or Critical events through the normal path (fraction)")
        ax.set_xlim(-0.02, 1.02)
        ax.set_ylim(-0.02, 1.02)
    axes[0].legend(fontsize=6.5, loc="upper right")
    save(fig, "t2_pareto")
    pd.DataFrame(rows).to_csv(C.TABLES / "t2_pareto.csv", index=False)
    record_many(ent, purge_prefixes=("t2.",))
    for rg in (16.0, 32.0, 64.0):
        g = {e["name"]: e["value"] for e in ent}
        print(rg, "AUC point", g[f"t2.r{rg:g}.point.auc"], "interval", g[f"t2.r{rg:g}.interval.auc"], "diff", [g[f"t2.r{rg:g}.auc_interval_minus_point{s}"] for s in ("", "_lo", "_hi")])


if __name__ == "__main__":
    main()
