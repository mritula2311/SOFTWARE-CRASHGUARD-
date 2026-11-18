"""Study F (docs/02_preregistration/PREREGISTRATION_V2.md section 5): severity-dependent hold. F1 cost model (ANALYTICAL), F2 simulation check (SIMULATED), F3 sensitivity. Prefix ``v2.f.``.
Cost of a hold h for an alert of class c: p x D_c x h + (1 - p) x C_false x R(h), with R(h) = 0.1 + 0.9 x clip((4 - h) / 3, 0, 1) the chance that a false alert is still sent after the hold (the driver cancels a false
alert with probability 0.9, uniformly 1 to 4 s after the decision: the cancel model of ``sct_sim``). All parameter ranges are assumptions fixed in the preregistration.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import s11_sct as S11
from crashguard import v2_b_study as VB
from crashguard import v2_pools as VP
from crashguard.sct_sim import SctParams
from crashguard.v2_common import Entries

HOLDS = tuple(np.round(np.arange(0.0, 5.0001, 0.5), 2))
RATIOS = (1.0, 10.0, 100.0, 1000.0, 10000.0)
W = (0.01, 0.1, 0.3, 1.0)
P_DEFAULT = float(VB.RES["s10.rf15.pi0p02pct.a.ppv"])
P_SIMMIX = 0.1 / (0.1 + 0.25)
P_SIMMIX_FA1 = 0.1 / (0.1 + 0.05)
SRC = "results/tables/v2_f_cost_model.csv"


def R_of(h: float) -> float:
    return 0.1 + 0.9 * float(np.clip((4.0 - h) / 3.0, 0.0, 1.0))


def cost(h: float, d_over_cf: float, p: float) -> float:
    """Expected cost in units of C_false."""
    return p * d_over_cf * h + (1.0 - p) * R_of(h)


def optimal_hold(d_over_cf: float, p: float) -> float:
    cs = [cost(h, d_over_cf, p) for h in HOLDS]
    return float(HOLDS[int(np.argmin(np.round(cs, 12)))])  # ties go to the smallest hold


def main() -> None:
    workers = min(14, os.cpu_count() or 1)
    ent = Entries("v2.f", SRC, "ANALYTICAL")
    rows = []
    for pn, p in (("ppv", P_DEFAULT), ("simmix", P_SIMMIX), ("simmix_fa1", P_SIMMIX_FA1)):  # the third value is the F3 sensitivity (false-alarm target 1%); H-F1 uses the first two
        for r in RATIOS:
            for c in range(4):
                h = optimal_hold(r * W[c], p)
                rows.append(dict(p_name=pn, p=p, ratio=r, cls=c, weight=W[c], optimal_hold_s=h))
                ent.add(f"opt.{pn}.ratio{int(r)}.class{c}", h, "s", f"model-optimal hold, D/C_false = ratio x weight = {r * W[c]:g}")
    cm = pd.DataFrame(rows)
    cm.to_csv(C.TABLES / "v2_f_cost_model.csv", index=False)
    crit = cm[(cm.cls == 3) & cm.p_name.isin(["ppv", "simmix"])]
    pos = crit[crit.optimal_hold_s > 0]
    ent.add("hF1.criterion_met", int(len(pos) == 0), "flag", "the optimal Critical hold is zero for every ratio and both values of p")
    ent.add("hF1.n_positive", len(pos), "cases", "ratio and p combinations with a positive optimal Critical hold")
    for pn, p in (("ppv", P_DEFAULT), ("simmix", P_SIMMIX)):
        sub = crit[crit.p_name == pn]
        ent.add(f"hF1.{pn}.largest_ratio_with_positive_hold", float(sub[sub.optimal_hold_s > 0].ratio.max()) if (sub.optimal_hold_s > 0).any() else 0.0, "ratio", "per second of delay; 0 = none")
        ent.add(f"hF1.{pn}.crossing_d_over_cf", round(0.9 * (1.0 - p) / (4.0 * p), 3), "ratio", "positive hold is optimal below this D / C_false (the hold is then 4 s)")
    ent.add("p.ppv", P_DEFAULT, "probability", "precision of the 15-tree forest at 0.02% prevalence (s10)")
    ent.add("p.simmix", round(P_SIMMIX, 4), "probability", "real alerts among alerts in the simulator's false-alarm cell (0.1 real, 0.25 false per car-hour)")
    ent.add("p.simmix_fa1", round(P_SIMMIX_FA1, 4), "probability", "the same at the 1% false-alarm target (0.05 false per car-hour); F3 sensitivity")
    # ---------------- F2 / F3 simulation
    params = SctParams(h_s=float(VB.RES["s11.tuned.h_s"]), rho_f=float(VB.RES["s11.tuned.rho_f"]), sf_raise=bool(VB.RES["s11.tuned.sf_raise"]))
    pools = VP.default_pools()
    cells = [dict(name="fa5_steady", group="fa", kw={}, burst=False, loaded=False, fa=0.25), dict(name="fa1_steady", group="fa", kw={}, burst=False, loaded=False, fa=0.05)]
    for c in VB.cells():
        if c["name"].startswith("loadedburst_"):
            cells.append({**c, "name": "fa5_" + c["name"], "group": "fa", "fa": 0.25})
    h_opt_sev = optimal_hold(100.0 * W[2], P_SIMMIX)  # r = 100 as the reference ratio; sev class weight 0.3; simulator mix for p
    h_opt_crit = optimal_hold(100.0 * W[3], P_SIMMIX)
    ent.add("model_optimal.r100.severe_hold", h_opt_sev, "s", "reference ratio 100, p of the simulator mix")
    ent.add("model_optimal.r100.critical_hold", h_opt_crit, "s")
    configs = {
        "a_current": dict(h_s=0.0, h_c=0.0),
        "b_sev2": dict(h_s=2.0, h_c=0.0),
        "b_sev1": dict(h_s=1.0, h_c=0.0),
        "b_sev3": dict(h_s=3.0, h_c=0.0),
        "c_model_optimal": dict(h_s=h_opt_sev, h_c=h_opt_crit),
        "d_flat2": dict(hold_all=2.0),
    }
    jobs = []
    for cell in cells:
        for nm, ov in configs.items():
            sct = SctParams(**{**params.__dict__, **ov})
            for h in range(VB.EVAL_HOURS):
                cfg = VB.make(cell, "P2", dict(kind="fixed", s0=1.0), h, VB.EVAL_SEED, pools, sct)
                cfg.fa_per_car_h = cell["fa"]
                jobs.append((cfg, dict(cell=cell["name"], cfg=nm, hour=h)))
    R = S11.run_jobs(jobs, workers)
    R.to_csv(C.TABLES / "v2_f_runs.csv", index=False)
    sim = Entries("v2.f", "results/tables/v2_f_runs.csv", "SIMULATED")
    sim.add("sim.runs", len(R), "runs")
    sim.add("sim.duty.runs_exceeding_limit", int(R.duty_exceeded.sum()), "runs", "independent scan; must be 0")
    pi = np.bincount(pools["unloaded"]["point"], minlength=4) / len(pools["unloaded"]["point"])
    for cell in cells:
        for nm in configs:
            sub = R[(R.cell == cell["name"]) & (R.cfg == nm)]
            for m in ("reach10_critical", "p95_lat_s_critical", "fa_rx_share_sev", "fa_rx_share", "n_fa_sev"):
                v = sub[m].dropna().to_numpy(float)
                if len(v):
                    rng = np.random.default_rng(C.SEED)
                    dr = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(1000)]
                    sim.ci(f"cell.{cell['name']}.{nm}.{m}", (float(v.mean()), float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "s" if "lat" in m else "fraction", d=5)
            ov = configs[nm]
            hs, hc = ov.get("h_s", 0.0), ov.get("h_c", 0.0)
            holds = [ov["hold_all"]] * 4 if "hold_all" in ov else [10.0, 8.0, hs, hc]  # classes 0 and 1 keep their cancel windows unless a flat hold is set
            fa_rx = float(sub.fa_rx_share.mean())
            real_delay = sum(pi[c] * W[c] * holds[c] for c in range(4))
            sim.add(f"cell.{cell['name']}.{nm}.cost_r100", round((1.0 - P_SIMMIX) * fa_rx + P_SIMMIX * 100.0 * real_delay, 4), "C_false units per alert",
                    "F1 expected cost with the simulated share of false alerts reaching the base (ratio 100, p of the simulator mix, class weights of F1, holds of the configuration)")
    # H-F2
    cell = "fa5_steady"
    sub_a = R[(R.cell == cell) & (R.cfg == "a_current")].sort_values("hour")
    sub_b = R[(R.cell == cell) & (R.cfg == "b_sev2")].sort_values("hour")
    a, b = sub_a.fa_rx_share_sev.to_numpy(float), sub_b.fa_rx_share_sev.to_numpy(float)
    m = ~(np.isnan(a) | np.isnan(b))
    a, b = a[m], b[m]
    rng = np.random.default_rng(C.SEED)
    idx = [rng.integers(0, len(a), len(a)) for _ in range(1000)]
    red = np.array([(a[i].mean() - b[i].mean()) / max(a[i].mean(), 1e-9) for i in idx])
    pt = float((a.mean() - b.mean()) / a.mean())
    sim.ci("hF2.relative_reduction_false_severe_reaching_base", (pt, float(np.quantile(red, 0.025)), float(np.quantile(red, 0.975))), "fraction", "hold 2 s against no hold, steady cell with false alarms at the 5% target", d=4)
    pr = float(max(np.mean(red <= 0.20), 1.0 / 1001))
    ra, rb = sub_a.reach10_critical.to_numpy(float), sub_b.reach10_critical.to_numpy(float)
    d = rb - ra
    dr = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)])
    lo, hi = float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))
    sim.ci("hF2.change_critical_reach10", (float(d.mean()), lo, hi), "fraction", "hold 2 s minus no hold", d=5)
    sim.add("hF2.p_raw", round(pr, 4), "probability", "relative reduction at or below 20%")
    sim.add("hF2.criterion_met", int(pt >= 0.20 and float(np.quantile(red, 0.025)) > 0.20 and not (hi < 0.0)), "flag", "reduction of at least 20% (point, and the lower interval end above 20% for the p-value to count) and the critical-reach interval does not lie entirely below zero")
    # other cells, for the record
    for cell in [c["name"] for c in cells]:
        for nm in ("b_sev1", "b_sev2", "b_sev3", "c_model_optimal", "d_flat2"):
            sa = R[(R.cell == cell) & (R.cfg == "a_current")].sort_values("hour")
            sb = R[(R.cell == cell) & (R.cfg == nm)].sort_values("hour")
            x, y = sa.fa_rx_share_sev.to_numpy(float), sb.fa_rx_share_sev.to_numpy(float)
            mm = ~(np.isnan(x) | np.isnan(y))
            if mm.sum() >= 3 and x[mm].mean() > 0:
                sim.add(f"reduction.{cell}.{nm}", round(float((x[mm].mean() - y[mm].mean()) / x[mm].mean()), 4), "fraction", "relative reduction of false Severe alerts reaching the base against no hold")
            dd = (sb.reach10_critical.to_numpy(float) - sa.reach10_critical.to_numpy(float))
            sim.add(f"reach_change.{cell}.{nm}", round(float(np.nanmean(dd)), 5), "fraction", "critical reach within 10 s against no hold")
    ent.items += sim.items
    ent.flush()
    pd.DataFrame([dict(h="H-F2", p=pr)]).to_csv(C.TABLES / "v2_f_pvalues.csv", index=False)
    print(cm[(cm.p_name == "ppv")].pivot(index="ratio", columns="cls", values="optimal_hold_s").to_string())
    print(cm[(cm.p_name == "simmix")].pivot(index="ratio", columns="cls", values="optimal_hold_s").to_string())
    print("H-F2 reduction", round(pt, 3), [round(float(np.quantile(red, q)), 3) for q in (0.025, 0.975)], "reach change", round(float(d.mean()), 4), (round(lo, 4), round(hi, 4)), "p", pr)
    print(R.groupby(["cell", "cfg"])[["reach10_critical", "fa_rx_share_sev", "fa_rx_share"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
