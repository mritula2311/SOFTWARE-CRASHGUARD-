"""Block A evaluation (SIMULATED and ANALYTICAL): H-A1, H-A2 on the HELD-OUT grid, regime map, assumption sensitivity, analytical-versus-simulated check of the retry schedule, duty violations.
Writes keys ``pa.*``, tables ``results/tables/pa_*.csv`` and the regime-map figure. H-A3 is written by ``pa_model``.

    python -m crashguard.pa_eval            (after ``pa_sim design`` and ``pa_sim held``)
"""
from __future__ import annotations

import json
import math

import matplotlib
import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard import pa_sim as A
from crashguard import packet as P
from crashguard import world_sim as W
from crashguard.fin_common import Entries
from crashguard.lora import airtime_ms

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SRC = "src/crashguard/pa_eval.py"
OUT = C.PROCESSED


def cell_names(R: pd.DataFrame, b: int | None = None) -> list[dict]:
    sub = R if b is None else R[R.b == b]
    return [dict(cell=c) for c in sorted(sub.cell.unique())]


def add_ci(E: Entries, name: str, tri, unit: str, note: str, origin: str = "SIMULATED") -> None:
    for suf, v in zip(("", "_lo", "_hi"), tri):
        E.add(f"{name}{suf}", None if v != v else round(float(v), 5), unit, origin, note)


def compare(R: pd.DataFrame, cells: list[dict], a: str, b: str, metric: str = "reach10_critical") -> dict:
    return FS.verdict_cells(R, cells, a, b, metric)


def pooled_diff(R: pd.DataFrame, cells: list[dict], a: str, b: str, metric: str):
    names = [c["cell"] for c in cells]
    return G.pooled(G.arr(R, a, metric, names), G.arr(R, b, metric, names))


def main() -> None:
    des = json.loads((OUT / "pa_design.json").read_text(encoding="utf-8"))
    R = pd.read_pickle(OUT / "pa_held.pkl")
    best = des["best_earlier"]
    E = Entries("pa", SRC)
    E.add("design.best_earlier", best, "policy", "SIMULATED", "earlier policy with the highest mean critical reach within 10 s on the DESIGN grid and no duty violation (chosen before the held-out run)")
    for k in ("osdr_N", "gsca_k_cap", "slot_aloha_k_cap", "tamang_k_cap"):
        E.add(f"design.{k}", des[k], "parameter", "SIMULATED", "chosen on the DESIGN grid only")
    for p, v in des["earlier_mean_reach10_critical"].items():
        E.add(f"design.earlier.{p}.mean_reach10_critical", round(v, 5), "fraction", "SIMULATED", "DESIGN grid, mean over cells of the seed mean (not a confirmed finding)")
    E.add("held.runs", int(len(R)), "runs", "SIMULATED", "held-out grid: 32 cells, 30 seeds (18000 + h)")
    E.add("held.duty_exceeded_runs", int(R.duty_exceeded.sum()), "runs", "SIMULATED", "must be 0 (independent re-scan of the transmission logs after every run)")
    allc, burst = cell_names(R), cell_names(R, int(R.b.max()))
    # ---------------- H-A1
    v1 = compare(R, allc, best, "osdr")
    E.add("hA1.n_cells", v1["n_cells"], "cells", "SIMULATED", "held-out cells")
    E.add("hA1.n_cells_gain5", v1["n_gain"], "cells", "SIMULATED", "OS-DR minus the best earlier policy at least 0.05 critical reach within 10 s with the interval above zero")
    E.add("hA1.n_cells_lose2", v1["n_lose"], "cells", "SIMULATED", "cells lost by more than 2 points")
    tri_d = pooled_diff(R, allc, best, "osdr", "node_air_share")
    tri_e = pooled_diff(R, allc, best, "osdr", "escalation")
    add_ci(E, "hA1.duty_use_diff", tri_d, "fraction", "OS-DR minus the best earlier policy, node airtime share of the allowance, mean over cells")
    add_ci(E, "hA1.escalation_diff", tri_e, "fraction", "OS-DR minus the best earlier policy, share of non-severe events escalated to the fast path")
    ok_duty = bool(tri_d[2] <= 0.0)
    ok_esc = bool(tri_e[2] <= 0.0)
    E.add("hA1.duty_not_higher", int(ok_duty), "flag", "SIMULATED", "upper end of the paired interval at most 0")
    E.add("hA1.escalation_not_higher", int(ok_esc), "flag", "SIMULATED", "upper end of the paired interval at most 0")
    E.add("hA1.criterion_met", int(v1["met"] and ok_duty and ok_esc), "flag", "SIMULATED", "reach clause (at least 60% of cells, no cell lost by more than 2 points) AND duty not higher AND escalation not higher")
    E.add("hA1.p_raw", round(float(v1["p"]), 4), "p", "SIMULATED", "cell-quantile rule of PREREGISTRATION_V5 section 0")
    # ---------------- H-A2
    v2o = compare(R, burst, "osdr", "gsca")
    v2t = compare(R, burst, "tamang", "gsca")
    for tag, v in (("vs_osdr", v2o), ("vs_tamang", v2t)):
        E.add(f"hA2.{tag}.n_cells_gain5", v["n_gain"], "cells", "SIMULATED", f"GS-CA minus the comparator at least 0.05 with the interval above zero, {v['n_cells']} burst cells")
        E.add(f"hA2.{tag}.n_cells_lose2", v["n_lose"], "cells", "SIMULATED")
        E.add(f"hA2.{tag}.criterion_met", int(v["met"]), "flag", "SIMULATED")
    E.add("hA2.criterion_met", int(v2o["met"] and v2t["met"]), "flag", "SIMULATED", "GS-CA beats both OS-DR and the slot-probability baseline in at least 60% of the burst cells, no cell lost by more than 2 points")
    E.add("hA2.p_raw", round(float(max(v2o["p"], v2t["p"])), 4), "p", "SIMULATED", "larger of the two cell-quantile p-values")
    # ---------------- descriptive pooled differences (all cells and burst cells)
    pols = [p for p in sorted(R.pol.unique())]
    rows = []
    for metric in ("reach10_critical", "reach10_rx_critical", "event_reach10_critical", "node_air_share", "escalation", "suppressed_share"):
        for pol in pols:
            for scope, cells in (("all", allc), ("burst", burst)):
                names = [c["cell"] for c in cells]
                tri = G.pooled(G.arr(R, pol, metric, names))
                rows.append(dict(metric=metric, policy=pol, scope=scope, mean=tri[0], lo=tri[1], hi=tri[2]))
                if pol in ("best_earlier", best, "osdr", "osdr_n", "gsca", "slot_aloha", "tamang"):
                    add_ci(E, f"cells.{scope}.{pol}.{metric}", tri, "fraction", "mean over held-out cells of the seed mean; 95% interval from resampled seeds")
    pd.DataFrame(rows).to_csv("results/tables/pa_held_summary.csv", index=False)
    # ---------------- secondary comparisons for H-A1 / H-A2 (not used for the verdict)
    for metric in ("reach10_rx_critical", "event_reach10_critical"):
        add_ci(E, f"secondary.osdr_minus_best.{metric}", pooled_diff(R, allc, best, "osdr", metric), "fraction", "OS-DR minus the best earlier policy; secondary, not used for the verdict")
        add_ci(E, f"secondary.gsca_minus_tamang.{metric}", pooled_diff(R, burst, "tamang", "gsca", metric), "fraction", "GS-CA minus the slot-probability baseline, burst cells; secondary")
    # ---------------- regime map (winner by critical reach per held-out cell; a tie when the paired interval to the runner-up includes zero)
    wins = {}
    reg = []
    for c in allc:
        sub = R[R.cell == c["cell"]]
        means = sub.groupby("pol").reach10_critical.mean().sort_values(ascending=False)
        w, r2 = means.index[0], means.index[1]
        st = FS.cell_pair(R, c, r2, w, "reach10_critical", 0.0)
        tie = not (st["lo"] > 0)
        reg.append(dict(cell=c["cell"], winner=w, runner_up=r2, margin=float(means.iloc[0] - means.iloc[1]), tie=int(tie), n=int(sub.n.iloc[0]), p=float(sub.p.iloc[0]), b=int(sub.b.iloc[0]), sf=int(sub.sf.iloc[0]), duty=float(sub.duty.iloc[0])))
        key = "tie" if tie else w
        wins[key] = wins.get(key, 0) + 1
    pd.DataFrame(reg).to_csv("results/tables/pa_regime.csv", index=False)
    for k, v in wins.items():
        E.add(f"regime.wins.{k}", v, "cells", "SIMULATED", "held-out cells won outside ties (a tie: the interval of the paired difference to the runner-up includes zero)")
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    names = sorted(wins, key=lambda k: -wins[k])
    ax.bar(range(len(names)), [wins[k] for k in names], color="#0072B2")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel("held-out cells won (count)")
    ax.set_title("Winner by critical reach within 10 s, held-out grid (32 cells; simulated, assumptions in SYNTHETIC_ASSUMPTIONS.md)", fontsize=8)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"results/figures/pa_regime_map.{ext}", dpi=300)
    plt.close(fig)
    # ---------------- assumption sensitivity (burst cells only; the verdicts H-A1 and H-A2 under each variant)
    sens(E, des, burst, best)
    analytic(E)
    # ---------------- verdict
    E.write()
    print("wins", wins, "| H-A1", int(v1["met"] and ok_duty and ok_esc), "| H-A2", int(v2o["met"] and v2t["met"]))


def sens(E: Entries, des: dict, burst: list[dict], best: str) -> None:
    t = FS.tuned()
    pools = A.pools_real()
    g = dict(A.HELD_A)
    g["b"] = (30,)
    variants = {
        "base": {},
        "A1_A3_no_overhearing_of_ACKs": dict(pa_over=dict(no_overhear=True)),
        "A2_no_neighbour_decoding": dict(pa_over=dict(no_nn=True)),
        "A4_clock_error_50ms": dict(pa_over=dict(eps=0.05)),
        "A4_clock_error_500ms": dict(pa_over=dict(eps=0.5)),
        "A5_capture_3dB": dict(world_over=dict(capture_db=3.0)),
        "A5_capture_10dB": dict(world_over=dict(capture_db=10.0)),
        "A5_shadowing_3dB": dict(world_over=G.g5_variants()["sigma3"]),
        "A5_shadowing_9dB": dict(world_over=G.g5_variants()["sigma9"]),
    }
    rows = []
    for vn, over in variants.items():
        specs = {"best_earlier": dict(kind=best, **over), "osdr": dict(kind="osdr", N=des["osdr_N"], **over), "osdr_n": dict(kind="osdr_n", N=des["osdr_N"], **over),
                 "gsca": dict(kind="gsca", k_cap=des["gsca_k_cap"], **over), "tamang": dict(kind="tamang", k_cap=des["tamang_k_cap"], **over)}
        R = FS.run_jobs(A.make_jobs(g, specs, pools, t))
        cells = cell_names(R)
        v1 = compare(R, cells, "best_earlier", "osdr")
        v2o, v2t = compare(R, cells, "osdr", "gsca"), compare(R, cells, "tamang", "gsca")
        d1 = pooled_diff(R, cells, "best_earlier", "osdr", "reach10_critical")
        d2 = pooled_diff(R, cells, "tamang", "gsca", "reach10_critical")
        rows.append(dict(variant=vn, osdr_minus_best=d1[0], osdr_gain_cells=v1["n_gain"], osdr_lose_cells=v1["n_lose"], hA1_reach_clause=int(v1["met"]), gsca_minus_tamang=d2[0], gsca_gain_vs_osdr=v2o["n_gain"], gsca_gain_vs_tamang=v2t["n_gain"], hA2_clause=int(v2o["met"] and v2t["met"]),
                         duty_exceeded=int(R.duty_exceeded.sum())))
        E.add(f"sens.{vn}.osdr_minus_best", round(float(d1[0]), 5), "fraction", "SIMULATED", "burst held-out cells; OS-DR minus the best earlier policy, critical reach within 10 s")
        E.add(f"sens.{vn}.hA1_reach_clause", int(v1["met"]), "flag", "SIMULATED", "the reach clause of H-A1 under this variant (burst cells only)")
        E.add(f"sens.{vn}.gsca_minus_tamang", round(float(d2[0]), 5), "fraction", "SIMULATED", "GS-CA minus the slot-probability baseline")
        E.add(f"sens.{vn}.hA2_clause", int(v2o["met"] and v2t["met"]), "flag", "SIMULATED")
        E.add(f"sens.{vn}.duty_exceeded_runs", int(R.duty_exceeded.sum()), "runs", "SIMULATED", "must be 0")
    pd.DataFrame(rows).to_csv("results/tables/pa_sensitivity.csv", index=False)
    base_ok = {r["variant"]: (r["hA1_reach_clause"], r["hA2_clause"]) for r in rows}
    flips = [v for v, x in base_ok.items() if x != base_ok["base"]]
    E.add("sens.flips", flips, "list", "SIMULATED", "variants in which the reach clause of H-A1 or H-A2 differs from the base case (an empty list: no conclusion flips)")


def analytic(E: Entries) -> None:
    """Analytical retry schedule against simulation in a controlled scenario: N contenders burst at the same time (10 s window), no background traffic, no geometry (legacy world), pure ALOHA without capture, uplink and downlink loss 0.1,
    SF8, duty 1%. The formula: per attempt cycle the tagged vehicle succeeds with s = (1 - p_up)(1 - p_down) exp(-2 (N - 1) q tau / T_c) (pure ALOHA, vulnerable window two airtimes tau); it makes about q D / T_c + 1 attempts in D (q the per-cycle attempt probability; q = 1 for OS-DR with N = 1);
    P(ack by D) = 1 - (1 - s)^attempts. An approximation (unslotted contention is not exactly cycle aligned); the report states the difference, not a pass."""
    sf, pu, pd_ = 8, 0.1, 0.1
    tau_al, tau_ack = airtime_ms(P.ALERT_LEN, sf) / 1000.0, airtime_ms(P.ACK_LEN, sf) / 1000.0
    Tc = tau_al + W.PROC_S + tau_ack + W.MARGIN_S
    rows = []
    for n_cars in (8, 16, 32):
        for q_par in (1, 2, 4, 8):
            q = min(1.0, 1.0 / q_par)
            s = (1 - pu) * (1 - pd_) * math.exp(-2.0 * (n_cars - 1) * q * tau_al / Tc)  # pure-ALOHA vulnerable window 2 tau_al; the others attempt at rate q per cycle
            att = q * 10.0 / Tc + 1.0
            pred = 1.0 - (1.0 - s) ** att
            sims = []
            for h in range(30):
                cfg = W.SCfg(n=n_cars, sf=sf, policy="sct", seed=21000, hour=h, duty=0.01, hb_period_s=1e9, rate_per_car_h=0.0, burst=True, burst_cars=n_cars, p_up=pu, p_down=pd_, capture="none",
                             sct=FS.p1plus_params(2.0), true_pool=np.array([3]), assigned_pool=np.array([3]), crash_pool=np.array([0.3]), duration_s=1000.0, label=f"pa_an_{n_cars}", world={"pa": dict(mode="osdr", N=q_par, no_overhear=True)})
                r = W.simulate(cfg)
                sims.append(r.get("reach10_critical", np.nan))
            sims = np.array(sims, float)
            rng = np.random.default_rng(42)
            bs = [rng.choice(sims, len(sims)).mean() for _ in range(1000)]
            rows.append(dict(n_cars=n_cars, N_param=q_par, analytic=pred, simulated=float(sims.mean()), sim_lo=float(np.quantile(bs, 0.025)), sim_hi=float(np.quantile(bs, 0.975))))
    df = pd.DataFrame(rows)
    df["diff"] = df.simulated - df.analytic
    df.to_csv("results/tables/pa_analytic_vs_sim.csv", index=False)
    E.add("analytic.mean_abs_diff", round(float(df["diff"].abs().mean()), 4), "fraction", "ANALYTICAL", "mean absolute difference between the formula and the simulation over the 12 controlled scenarios (N cars 8, 16, 32; N parameter 1, 2, 4, 8); an approximation, reported without a pass criterion")
    E.add("analytic.max_abs_diff", round(float(df["diff"].abs().max()), 4), "fraction", "ANALYTICAL", "largest absolute difference over the scenarios")
    E.add("analytic.mean_signed_diff", round(float(df["diff"].mean()), 4), "fraction", "ANALYTICAL", "simulated minus analytic, mean over the scenarios")
    E.add("analytic.scenarios", int(len(df)), "scenarios", "ANALYTICAL", "controlled scenarios (see the docstring of pa_eval.analytic); 30 simulated hours each")
    print(df.round(3).to_string())


if __name__ == "__main__":
    main()
