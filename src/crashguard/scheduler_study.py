"""N16 study: tune the scheduler on tuning scenarios, evaluate once on held-out scenarios (docs/02_preregistration/ALGORITHMS.md). SIMULATED supporting evidence.

Tuning scenarios (seeds 100 to 104) and held-out scenarios (seeds 200 to 204, different loss settings) are disjoint. The tuning objective is fixed in the document:
J = mean over scenarios of [ weighted delivery by true class (1, 2, 4, 8 / 15 over the classes present) - 0.2 x share of the duty-cycle budget used ].
The estimator comparison (plain, saturation-aware, reference) uses NHTSA tests: the car's priority and cancel window follow the ESTIMATED class, results are reported by the TRUE class.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import severity as S
from crashguard.replay import POLICIES, Scenario, ci_of, run_config
from crashguard.replay_study import paired, stress_pool
from crashguard.scheduler import Scheduler, grid

TUNE_SEEDS = (100, 101, 102, 103, 104)
EVAL_SEEDS = (200, 201, 202, 203, 204)
TUNE_HOURS, EVAL_HOURS = 6, 20
W_CLASS = (1.0, 2.0, 4.0, 8.0)
SRC = "results/tables/n16_heldout_cells.csv"
CLASSES = ("low", "moderate", "severe", "critical")


def tuning_scenarios() -> list[Scenario]:
    out = []
    for kind, loss in (("iid", 0.15), ("iid", 0.35), ("iid", 0.55), ("ge", 0.25), ("ge", 0.45)):
        for sf in (7, 12):
            for rate in (20, 120):
                for base in (360.0, 2.0):
                    out.append(Scenario(f"tune_{kind}{int(loss * 100)}_sf{sf}_r{rate}_b{int(base)}", sf, rate, base_initial_s=base, loss_up=loss, loss_down=loss, kind=kind))
    return out


def heldout_scenarios() -> list[tuple[str, Scenario]]:
    cells: list[tuple[str, Scenario]] = []
    for sf in (7, 9, 12):
        for kind, loss in (("iid", 0.1), ("iid", 0.3), ("iid", 0.5), ("iid", 0.6), ("ge", 0.3), ("ge", 0.5)):
            cells.append(("loss", Scenario(f"loss_{kind}{int(loss * 100)}_sf{sf}", sf, 20, loss_up=loss, loss_down=loss, kind=kind)))
    for sf in (7, 12):
        for up, down in ((0.3, 0.1), (0.3, 0.5)):
            cells.append(("ackloss", Scenario(f"ackloss_{int(up * 100)}_{int(down * 100)}_sf{sf}", sf, 20, loss_up=up, loss_down=down)))
        for rate in (10, 60, 240):
            cells.append(("rate", Scenario(f"rate_{rate}_sf{sf}", sf, rate, loss_up=0.3, loss_down=0.3)))
    for sf in (7, 9, 12):
        cells.append(("basenear", Scenario(f"basenear_sf{sf}", sf, 60, base_initial_s=2.0, loss_up=0.3, loss_down=0.3)))
    return cells


def objective(h: pd.DataFrame) -> float:
    num = den = 0.0
    for i, cls in enumerate(CLASSES):
        c = f"delivered_{cls}"
        if c in h and h[c].notna().any():
            num += W_CLASS[i] * float(h[c].mean())
            den += W_CLASS[i]
    return (num / den if den else 0.0) - 0.2 * float(h.airtime_share_total.mean())


def tune_one(args: tuple[int, Scheduler]) -> tuple[int, float, float]:
    idx, pol = args
    sev = stress_pool()
    js, _js_hot = [], []
    for sc in tuning_scenarios():
        h = run_config(sev, sc, pol, seeds=TUNE_SEEDS, hours=TUNE_HOURS)
        js.append(objective(h))
    return idx, float(np.mean(js)), float(np.min(js))


def tune(workers: int | None = None) -> pd.DataFrame:
    combos = grid()
    with ProcessPoolExecutor(workers or min(8, os.cpu_count() or 1)) as ex:
        res = list(ex.map(tune_one, list(enumerate(combos))))
    rows = []
    for idx, jm, jmin in res:
        p = combos[idx]
        rows.append(dict(name=p.name, rho=p.rho, m=p.m, jitter=p.jitter, sf_raise=p.sf_raise, J_mean=jm, J_min=jmin, n_features=int(p.rho > 0) + int(p.jitter > 0) + int(p.sf_raise)))
    return pd.DataFrame(rows)


def choose(t: pd.DataFrame) -> Scheduler:
    best = t.sort_values(["J_mean", "n_features"], ascending=[False, True]).iloc[0]
    return Scheduler(name="scheduler", rho=float(best.rho), m=float(best.m), jitter=float(best.jitter), sf_raise=bool(best.sf_raise))


def class_pools() -> dict[str, np.ndarray]:
    """(estimated, true) class pairs from the NHTSA tests at +-16 g: plain estimate, saturation-aware estimate (N14, fill plus ridge), and the reference class for both."""
    from crashguard import config as Cfg

    d = pd.read_csv(Cfg.TABLES / "n14_per_test.csv")
    d = d[d.range_g == 16.0]
    true = np.array([S.classify(float(r), float(a), False) for r, a in zip(d.ref, d.ref_asi)])
    plain = d.b_cls.to_numpy().astype(int)
    sat = np.array([S.classify(float(v), float(a), False) for v, a in zip(d["est_M+"], d.m_asi)])
    return {"nhtsa_plain": np.stack([plain, true], 1), "nhtsa_sat": np.stack([sat, true], 1), "nhtsa_oracle": np.stack([true, true], 1)}


def eval_cell(pool: np.ndarray, sc: Scenario, policies: dict) -> dict:
    return {n: run_config(pool, sc, p, seeds=EVAL_SEEDS, hours=EVAL_HOURS) for n, p in policies.items()}


def _row(h: pd.DataFrame, **ident) -> dict:
    row = dict(ident)
    for k in h.columns:
        if k not in ("seed", "hour"):
            row[k] = float(h[k].mean())
    for cls in ("all",) + CLASSES:
        for c in (f"delivered_{cls}", f"median_lat_s_{cls}", f"p95_lat_s_{cls}", f"blocked_{cls}"):
            if c in h:
                p, lo, hi = ci_of(h, c)
                row[c + "_lo"], row[c + "_hi"] = lo, hi
    return row


def main() -> None:
    from crashguard.results import record_many

    C.TABLES.mkdir(parents=True, exist_ok=True)
    ent: list[dict] = []

    def add(name, value, unit="fraction", notes="", s=SRC):
        ent.append(dict(name=f"n16.{name}", value=value, unit=unit, origin="SIMULATED", source_file=s, notes=notes))

    t = tune()
    t.to_csv(C.TABLES / "n16_tuning.csv", index=False)
    best = choose(t)
    for r in t.itertuples():
        add(f"tuning.{r.name}.J_mean", round(float(r.J_mean), 5), "score", "tuning scenarios only (seeds 100 to 104)", "results/tables/n16_tuning.csv")
    add("chosen.rho", best.rho, "fraction of capacity", "chosen on the tuning scenarios", "results/tables/n16_tuning.csv")
    add("chosen.m", best.m, "multiplier", s="results/tables/n16_tuning.csv")
    add("chosen.jitter", best.jitter, "fraction", s="results/tables/n16_tuning.csv")
    add("chosen.sf_raise", int(best.sf_raise), "flag", s="results/tables/n16_tuning.csv")
    add("tuning.scenarios", len(tuning_scenarios()), "scenarios", s="results/tables/n16_tuning.csv")
    policies = {"fixed3": POLICIES["fixed3"], "table": POLICIES["severity"], "scheduler": best}
    no_sf = Scheduler(name="scheduler_nosf", rho=best.rho, m=best.m, jitter=best.jitter, sf_raise=False)
    stress = stress_pool()
    rows, hourly = [], {}
    for fam, sc in heldout_scenarios():
        hh = eval_cell(stress, sc, {**policies, "scheduler_nosf": no_sf} if best.sf_raise else policies)
        for n, h in hh.items():
            rows.append(_row(h, pool="stress", family=fam, scenario=sc.name, policy=n))
        hourly[("stress", sc.name)] = (fam, hh)
    pd.DataFrame(rows).to_csv(C.TABLES / "n16_heldout_cells.csv", index=False)
    cells = pd.DataFrame(rows)
    for r in cells.itertuples():
        for cls in ("all",) + CLASSES:
            for c in ("delivered", "median_lat_s", "p95_lat_s", "retries", "airtime_share", "blocked", "never_sent"):
                v = getattr(r, f"{c}_{cls}", np.nan)
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    add(f"heldout.{r.scenario}.{r.policy}.{c}_{cls}", round(float(v), 5), "seconds" if "lat" in c else "fraction")
            for c in ("delivered", "median_lat_s", "p95_lat_s", "blocked"):
                for suf in ("_lo", "_hi"):
                    v = getattr(r, f"{c}_{cls}{suf}", np.nan)
                    if v is not None and not (isinstance(v, float) and np.isnan(v)):
                        add(f"heldout.{r.scenario}.{r.policy}.{c}_{cls}{suf}", round(float(v), 5), "seconds" if "lat" in c else "fraction")
        add(f"heldout.{r.scenario}.{r.policy}.airtime_share_total", round(float(r.airtime_share_total), 5))
        add(f"heldout.{r.scenario}.{r.policy}.base_ack_airtime_share", round(float(r.base_ack_airtime_share), 5))

    # conclusions on held-out cells (stress pool): paired differences of the scheduler against each baseline
    conc = []
    tests = (("C1_better_critical_than_table", "table", "delivered_critical", lambda d: d[1] > 0), ("C2_better_critical_than_fixed3", "fixed3", "delivered_critical", lambda d: d[1] > 0),
             ("C3_fewer_blocked_critical_than_table", "table", "blocked_critical", lambda d: d[2] < 0), ("C4_lower_p95_latency_critical_than_table", "table", "p95_lat_s_critical", lambda d: d[2] < 0),
             ("C5_low_alerts_not_sacrificed_vs_table", "table", "delivered_low", lambda d: d[1] > -0.05), ("C6_less_budget_than_table", "table", "airtime_share_total", lambda d: d[2] < 0))
    for (pool, name), (fam, hh) in hourly.items():
        for cn, base_name, col, ok in tests:
            d = paired(hh[base_name], hh["scheduler"], col)
            if not np.isnan(d[0]):
                conc.append(dict(pool=pool, scenario=name, family=fam, conclusion=cn, holds=bool(ok(d)), value=d[0], lo=d[1], hi=d[2]))
    cdf = pd.DataFrame(conc)
    cdf.to_csv(C.TABLES / "n16_conclusions.csv", index=False)
    cs = "results/tables/n16_conclusions.csv"
    for cn, g in cdf.groupby("conclusion"):
        add(f"conclusion.{cn}.cells", int(len(g)), "cells", s=cs)
        add(f"conclusion.{cn}.holds", int(g.holds.sum()), "cells", s=cs)
        for f, r in g.groupby("family").holds.agg(["sum", "count"]).iterrows():
            add(f"conclusion.{cn}.family.{f}.holds", int(r["sum"]), "cells", s=cs)
            add(f"conclusion.{cn}.family.{f}.cells", int(r["count"]), "cells", s=cs)
        g.sort_values("value")
        add(f"conclusion.{cn}.mean_difference", round(float(g.value.mean()), 5), "difference", s=cs)
    # effect sizes by true class, pooled over all held-out cells (the same cell, seed and hour for both policies), against both baselines
    from crashguard import boot as B

    eff_rows = []
    for base_name in ("fixed3", "table"):
        for cls in CLASSES:
            for metric in ("delivered", "median_lat_s", "p95_lat_s", "airtime_share"):
                col = f"{metric}_{cls}"
                a_list, b_list = [], []
                for (_pool, _name), (_fam, hh) in hourly.items():
                    if col in hh[base_name] and col in hh["scheduler"]:
                        m = pd.concat([hh[base_name][col].reset_index(drop=True), hh["scheduler"][col].reset_index(drop=True)], axis=1, keys=["a", "b"]).dropna()
                        a_list.append(m.a.to_numpy())
                        b_list.append(m.b.to_numpy())
                if not a_list:
                    continue
                a_arr, b_arr = np.concatenate(a_list), np.concatenate(b_list)
                d0, lo, hi = B.paired_diff(a_arr, b_arr, np.mean)
                eff_rows.append(dict(baseline=base_name, cls=cls, metric=metric, n=len(a_arr), baseline_mean=float(a_arr.mean()), scheduler_mean=float(b_arr.mean()), d=d0, d_lo=lo, d_hi=hi))
                for nm, val in (("d", d0), ("d_lo", lo), ("d_hi", hi), ("baseline_mean", float(a_arr.mean())), ("scheduler_mean", float(b_arr.mean()))):
                    add(f"effect.{base_name}.{cls}.{metric}.{nm}", round(float(val), 5), "seconds" if "lat" in metric else "fraction", notes="scheduler minus baseline, pooled over all held-out stress-mix cells, paired on cell, seed and hour; 95% bootstrap interval", s="results/tables/n16_effects.csv")
                add(f"effect.{base_name}.{cls}.{metric}.n", int(len(a_arr)), "hours", s="results/tables/n16_effects.csv")
    pd.DataFrame(eff_rows).to_csv(C.TABLES / "n16_effects.csv", index=False)

    # headline paired difference over the loss family at SF12 and SF7 (for the report)
    for sfv in (7, 12):
        for loss_tag in ("iid30", "iid50", "ge30"):
            key = ("stress", f"loss_{loss_tag}_sf{sfv}")
            if key in hourly:
                hh = hourly[key][1]
                for base_name in ("table", "fixed3"):
                    for col in ("delivered_critical", "delivered_all", "p95_lat_s_critical", "blocked_critical", "airtime_share_total"):
                        d = paired(hh[base_name], hh["scheduler"], col)
                        for nm, v in (("d", d[0]), ("d_lo", d[1]), ("d_hi", d[2])):
                            if not np.isnan(v):
                                add(f"paired.loss_{loss_tag}_sf{sfv}.scheduler_minus_{base_name}.{col}.{nm}", round(float(v), 5), "difference", s=cs)

    # sf_decay sensitivity (the SF-raise assumption)
    sens = []
    if best.sf_raise:
        for decay in (1.0, 0.4):
            for sfv in (7, 9):
                sc = Scenario(f"sfdecay_{decay:g}_sf{sfv}", sfv, 60, loss_up=0.5, loss_down=0.5, sf_decay=decay)
                hh = eval_cell(stress, sc, {"table": POLICIES["severity"], "scheduler": best, "scheduler_nosf": no_sf})
                d = paired(hh["table"], hh["scheduler"], "delivered_critical")
                d2 = paired(hh["scheduler_nosf"], hh["scheduler"], "delivered_critical")
                sens.append(dict(decay=decay, sf=sfv, d_vs_table=d[0], d_vs_table_lo=d[1], d_vs_table_hi=d[2], d_vs_nosf=d2[0], d_vs_nosf_lo=d2[1], d_vs_nosf_hi=d2[2]))
                for nm, v in (("vs_table", d), ("vs_nosf", d2)):
                    for suf, val in (("", v[0]), ("_lo", v[1]), ("_hi", v[2])):
                        add(f"sf_decay.{decay:g}.sf{sfv}.delivered_critical.scheduler_minus_{nm}{suf}", round(float(val), 5), "difference", s="results/tables/n16_sf_decay.csv")
    pd.DataFrame(sens).to_csv(C.TABLES / "n16_sf_decay.csv", index=False)

    # estimator comparison: priority from the estimated class, results by the true class
    est_rows = []
    pools = class_pools()
    for pname, pool in pools.items():
        for sfv, kind, loss in ((7, "iid", 0.5), (12, "iid", 0.3), (12, "ge", 0.3)):
            sc = Scenario(f"est_{kind}{int(loss * 100)}_sf{sfv}", sfv, 60, loss_up=loss, loss_down=loss, kind=kind)
            hh = eval_cell(pool, sc, {"fixed3": POLICIES["fixed3"], "table": POLICIES["severity"], "scheduler": best})
            for pn, h in hh.items():
                est_rows.append(_row(h, pool=pname, scenario=sc.name, policy=pn))
    edf = pd.DataFrame(est_rows)
    edf.to_csv(C.TABLES / "n16_estimator_cells.csv", index=False)
    es = "results/tables/n16_estimator_cells.csv"
    for r in edf.itertuples():
        for cls in ("all",) + CLASSES:
            for c in ("delivered", "blocked", "median_lat_s", "p95_lat_s"):
                for suf in ("", "_lo", "_hi"):
                    v = getattr(r, f"{c}_{cls}{suf}", np.nan)
                    if v is not None and not (isinstance(v, float) and np.isnan(v)):
                        add(f"estimator.{r.pool}.{r.scenario}.{r.policy}.{c}_{cls}{suf}", round(float(v), 5), "seconds" if "lat" in c else "fraction", s=es)
        add(f"estimator.{r.pool}.{r.scenario}.{r.policy}.airtime_share_total", round(float(r.airtime_share_total), 5), s=es)
    for pname, pool in pools.items():
        for k, cls in enumerate(CLASSES):
            add(f"estimator.{pname}.true_share.{cls}", round(float((pool[:, 1] == k).mean()), 4), "fraction", s=es)
            add(f"estimator.{pname}.est_share.{cls}", round(float((pool[:, 0] == k).mean()), 4), "fraction", s=es)
        add(f"estimator.{pname}.class_agreement", round(float((pool[:, 0] == pool[:, 1]).mean()), 4), "fraction", s=es)
        add(f"estimator.{pname}.underestimated", round(float((pool[:, 0] < pool[:, 1]).mean()), 4), "fraction", s=es)
        add(f"estimator.{pname}.overestimated", round(float((pool[:, 0] > pool[:, 1]).mean()), 4), "fraction", s=es)
    record_many(ent, purge_prefixes=("n16.",))
    figure(cells, edf)
    print(t.sort_values("J_mean", ascending=False).head(6).round(4).to_string(index=False))
    print(cdf.groupby("conclusion").holds.agg(["sum", "count"]))


def figure(cells: pd.DataFrame, edf: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, sfv in zip(axes, (7, 9, 12)):
        for i, pn in enumerate(("fixed3", "table", "scheduler")):
            for kind, ls in (("iid", "-"), ("ge", "--")):
                g = cells[(cells.policy == pn) & cells.scenario.str.startswith(f"loss_{kind}") & cells.scenario.str.endswith(f"_sf{sfv}")].copy()
                g["loss"] = g.scenario.str.extract(rf"loss_{kind}(\d+)_")[0].astype(float)
                g = g.sort_values("loss")
                ax.plot(g.loss, g.delivered_critical * 100, ls=ls, marker="o", ms=3, color=COLORS[i], label=f"{pn}, {'independent' if kind == 'iid' else 'burst'}")
        ax.set_xlabel("Mean packet loss per transmission (%)")
        ax.set_title(f"SF{sfv}", fontsize=9)
    axes[0].set_ylabel("Critical alerts whose ACK reached the car (%)")
    axes[0].legend(fontsize=6)
    fig.suptitle("N16 held-out scenarios (SIMULATED, assumed 40/30/20/10 mix, seeds 200 to 204)", fontsize=9)
    save(fig, "n16_critical_delivery")
    fig, ax = plt.subplots(figsize=(7, 4))
    e = edf[(edf.policy == "scheduler")]
    sc = e.scenario.unique()[0]
    sub = e[e.scenario == sc]
    names = {"nhtsa_plain": "plain estimate", "nhtsa_sat": "saturation-aware", "nhtsa_oracle": "reference class"}
    vals = [float(sub[sub.pool == p].delivered_critical.iloc[0]) if (sub.pool == p).any() and "delivered_critical" in sub else np.nan for p in names]
    ax.bar(list(names.values()), vals, color=COLORS[:3])
    ax.set_ylabel("Truly critical alerts whose ACK reached the car")
    ax.set_title(f"Scheduler, {sc}: priority from the estimated class (SIMULATED)", fontsize=8)
    save(fig, "n16_estimator_effect")


if __name__ == "__main__":
    main()
