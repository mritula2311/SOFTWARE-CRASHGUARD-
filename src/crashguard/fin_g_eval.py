"""Block G evaluation: G1 tables, G2 layer attribution, G3 hypotheses, G4 regime map, G5 sensitivity, G6 regression summary, G7 findings (SIMULATED; docs/02_preregistration/PREREGISTRATION_V5.md section G).
Reads data/processed/f_g*.pkl written by ``crashguard.fin_g``; writes keys f.g.* and results/tables/f_g_*.csv and results/figures/f_g_regime_map.*."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard.fin_common import Entries

OUT = Path("data/processed")
SRC = "results/tables/f_g_cells.csv"
LAT = "p95_lat_s_critical"


def cat(pt, lo, hi) -> int:
    return 1 if lo > 0 else (-1 if hi < 0 else 0)


def add_ci(E: Entries, name: str, tri, unit="fraction", note=""):
    pt, lo, hi = tri
    for suf, v in (("", pt), ("_lo", lo), ("_hi", hi)):
        E.add(name + suf, None if v != v else round(float(v), 5), unit, "SIMULATED", note if not suf else "95% interval, seeds resampled inside each cell")


def g1_eval(E: Entries, R1: pd.DataFrame) -> dict:
    rows = []
    for grid in ("design", "held"):
        sub = R1[R1.grid == grid]
        cells = sorted(sub.cell.unique())
        for pol in sorted(sub.pol.unique()):
            for m in G.METS:
                if m not in sub:
                    continue
                a = G.arr(sub, pol, m, cells)
                tri = G.pooled(a) if not np.isnan(a).all() else (np.nan,) * 3
                add_ci(E, f"g1.{grid}.{pol}.{m}", tri, "s" if "lat" in m else "fraction", "mean over cells of the seed mean (design grid: not a confirmed finding)" if grid == "design" else "mean over cells of the seed mean (HELD-OUT grid)")
                rows.append(dict(grid=grid, pol=pol, metric=m, pt=tri[0], lo=tri[1], hi=tri[2]))
        for c in cells:
            for pol in sorted(sub.pol.unique()):
                g = sub[(sub.cell == c) & (sub.pol == pol)]
                rows.append(dict(grid=grid, pol=pol, metric="cell:" + c + ":reach10_critical", pt=float(g.reach10_critical.mean()), lo=np.nan, hi=np.nan))
    pd.DataFrame(rows).to_csv("results/tables/f_g1_cells.csv", index=False)
    return {r["pol"]: r["pt"] for r in rows if r["grid"] == "design" and r["metric"] == "reach10_critical"}


def g2_eval(E: Entries, R2: pd.DataFrame, names: dict) -> None:
    for grid in ("design", "held"):
        sub = R2[R2.grid == grid]
        cells = sorted(sub.cell.unique())
        base = G.arr(sub, "base", "reach10_critical", cells)
        effects = {}
        for v, layer in names.items():
            if v in ("base",) or v.startswith("fa_"):
                continue
            for m in ("reach10_critical", "reach30_critical", LAT, "node_air_share"):
                a, b = G.arr(sub, "base", m, cells), G.arr(sub, v, m, cells)
                tri = G.pooled(a, b)
                add_ci(E, f"g2.{grid}.{v}.{m}", tri, "s" if "lat" in m else "fraction", f"{v} minus base (P1+), layer {layer}")
                if m == "reach10_critical":
                    effects[v] = (layer, tri)
        # interactions: (AB - A) - (B - base)
        for v in [x for x in names if "+" in x and x not in ("P1+",)]:
            if names[v] != "INTERACTION":
                continue
            A, B = v.split("+", 1)
            a_ = G.arr(sub, v, "reach10_critical", cells) - G.arr(sub, A, "reach10_critical", cells) - G.arr(sub, B, "reach10_critical", cells) + base
            add_ci(E, f"g2.{grid}.interaction.{A}__{B}.reach10_critical", G.pooled(a_), "fraction", "(AB - A) - (B - base): zero means the effects add")
        # layer summary
        for layer in ("PHY", "MAC", "NET", "APP"):
            es = [(v, t) for v, (lay, t) in effects.items() if lay == layer]
            if es:
                v, t = max(es, key=lambda x: abs(x[1][0]))
                E.add(f"g2.{grid}.layer.{layer}.largest_effect_variant", v, "variant", "SIMULATED", "largest absolute effect on critical reach within 10 s in the layer")
                E.add(f"g2.{grid}.layer.{layer}.largest_effect", round(t[0], 5), "fraction", "SIMULATED")
                E.add(f"g2.{grid}.layer.{layer}.largest_effect_category", cat(*t), "sign", "SIMULATED", "+1 interval above zero, -1 below, 0 includes zero")
        # CANCEL on false alarms
        on, off = G.arr(sub, "fa_cancel_on", "fa_tx_fast", cells), G.arr(sub, "fa_cancel_off", "fa_tx_fast", cells)
        add_ci(E, f"g2.{grid}.cancel_off_minus_on.fa_tx_fast", G.pooled(on, off), "count", "false-alarm fast transmissions per run, CANCEL message off minus on (false alarms 0.25 per car-hour)")
        add_ci(E, f"g2.{grid}.cancel_off_minus_on.reach10_critical", G.pooled(G.arr(sub, "fa_cancel_on", "reach10_critical", cells), G.arr(sub, "fa_cancel_off", "reach10_critical", cells)), "fraction")


def g3_eval(E: Entries, R3: pd.DataFrame) -> dict:
    cells_all = sorted(R3.cell.unique())
    res = {}
    for hyp, mech, metric, cells in (("hG3a", "slot", "reach10_critical", cells_all), ("hG3b", "lbt", "reach10_critical", cells_all), ("hG3c", "relay", "reach30_rx_critical", [c for c in cells_all if "_p40_" in c])):
        v = FS.verdict_cells(R3, [dict(cell=c) for c in cells], "base", mech, metric)
        E.add(f"g3.{hyp}.n_cells", v["n_cells"], "cells", "SIMULATED")
        E.add(f"g3.{hyp}.n_cells_gain5", v["n_gain"], "cells", "SIMULATED", "gain of at least 5 points with the interval above zero")
        E.add(f"g3.{hyp}.n_cells_lose2", v["n_lose"], "cells", "SIMULATED", "point difference below -0.02")
        E.add(f"g3.{hyp}.criterion_met", int(v["met"]), "flag", "SIMULATED")
        E.add(f"g3.{hyp}.p_raw", round(v["p"], 4), "p", "SIMULATED")
        sub = R3
        a, b = G.arr(sub, "base", metric, cells), G.arr(sub, mech, metric, cells)
        add_ci(E, f"g3.{hyp}.pooled_diff.{metric}", G.pooled(a, b), "fraction", f"{mech} minus base, mean over {len(cells)} held-out cells")
        for m in ("reach30_critical", "reach10_critical", "node_air_share", "mis_triage", LAT):
            add_ci(E, f"g3.{hyp}.pooled_diff.{m}", G.pooled(G.arr(sub, "base", m, cells_all), G.arr(sub, mech, m, cells_all)), "s" if "lat" in m else "fraction", f"{mech} minus base, all 16 held-out cells")
        res[hyp] = v
    sb = R3[R3.pol == "slot"]
    E.add("g3.slot.beacon_duty_share_of_gateway", round(float((sb.slot_beacon_air_s / (sb.duty * 5400.0)).mean()), 4), "fraction", "SIMULATED", "beacon airtime over the gateway's duty allowance for the 5,400 s simulated (ASSUMED beacon of 9 bytes every 30 s; beacons are skipped when the allowance is used)")
    E.add("g3.slot.beacon_airtime_s_per_hour", round(float(sb.slot_beacon_air_s.mean() * 3600.0 / 5400.0), 3), "s", "SIMULATED", "gateway beacon airtime per hour of simulated time")
    rl = R3[R3.pol == "relay"]
    E.add("g3.relay.extra_airtime_share_of_allowance", round(float(rl.relay_air_share_of_allowance.mean()), 5), "fraction", "SIMULATED", "relay airtime over the per-car allowance")
    E.add("g3.relay.relay_tx_per_run", round(float(rl.relay_tx.mean()), 2), "tx", "SIMULATED")
    E.add("g3.relay.dup_rx_per_critical_alert", round(float(rl.dup_rx_critical.mean()), 4), "fraction", "SIMULATED", "extra gateway receptions per critical alert (duplicate-alert rate)")
    E.add("g3.base.dup_rx_per_critical_alert", round(float(R3[R3.pol == "base"].dup_rx_critical.mean()), 4), "fraction", "SIMULATED", "same, no relay (repeats of the sender's own retries)")
    sub_l = R3[R3.pol == "lbt"]
    E.add("g3.lbt.waits_per_run", round(float(sub_l.lbt_wait.mean()), 2), "waits", "SIMULATED", "listen-before-talk backoffs per run (ASSUMED sensing probability 0.7)")
    return res


def g4_eval(E: Entries, R1: pd.DataFrame, R3: pd.DataFrame, best: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pal = {"P0": "#999999", "P1": "#E69F00", "P1e": "#F0E442", "P1+": "#56B4E9", "P1+e": "#009E73", "P2": "#0072B2", "P3": "#D55E00", "P4": "#CC79A7", "P3b": "#000000", "P1+f": "#88CCEE", "P3f": "#AA4499",
           f"{best}+slot": "#44AA99", f"{best}+lbt": "#117733", f"{best}+relay": "#882255"}
    rows = []
    fig, axs = plt.subplots(1, 2, figsize=(13, 5))
    for ax, (grid, gd) in zip(axs, (("design", G.DESIGN), ("held", G.HELD))):
        sub = R1[R1.grid == grid].copy()
        if grid == "held":
            ex = R3[R3.pol.isin(["slot", "lbt", "relay"])].copy()
            ex["pol"] = best + "+" + ex.pol
            sub = pd.concat([sub, ex], ignore_index=True)
        cells = G.cells_of(gd)
        pols = sorted(sub.pol.unique())
        for ci, c in enumerate(cells):
            means = {p: float(sub[(sub.cell == c["name"]) & (sub.pol == p)].reach10_critical.mean()) for p in pols}
            order = sorted(pols, key=lambda p: -means[p])
            w, r2 = order[0], order[1]
            tri = G.pooled(G.arr(sub, r2, "reach10_critical", [c["name"]]), G.arr(sub, w, "reach10_critical", [c["name"]]))
            tie = not (tri[1] > 0)
            rows.append(dict(grid=grid, cell=c["name"], n=c["n"], p=c["p"], sf=c["sf"], duty=c["duty"], best=w, runner_up=r2, margin=tri[0], lo=tri[1], hi=tri[2], tie=tie, best_reach10=means[w]))
            rcol = int(np.argmax([(c["sf"], c["duty"]) == k for k in itertools_pairs(gd)]))
            ccol = int(np.argmax([(c["n"], c["p"]) == k for k in itertools_np(gd)]))
            ax.add_patch(plt.Rectangle((ccol, 3 - rcol), 1, 1, color=pal.get(w, "#cccccc"), hatch="//" if tie else None, ec="k", lw=0.5))
            ax.text(ccol + 0.5, 3 - rcol + 0.5, f"{w}\n{tri[0]:+.2f}", ha="center", va="center", fontsize=6)
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.set_xticks(np.arange(4) + 0.5)
        ax.set_xticklabels([f"n={n}, loss {int(p * 100)}%" for n, p in itertools_np(gd)], fontsize=7, rotation=20)
        ax.set_yticks(np.arange(4) + 0.5)
        ax.set_yticklabels([f"SF{sf}, duty {d * 100:g}%" for sf, d in reversed(itertools_pairs(gd))], fontsize=7)
        ax.set_title(f"{'DESIGN grid (not a confirmed finding)' if grid == 'design' else 'HELD-OUT grid'}: best policy by critical reach within 10 s\n(hatched = tie; simulated, assumptions in SYNTHETIC_ASSUMPTIONS.md)", fontsize=8)
    Path("results/figures").mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"results/figures/f_g_regime_map.{ext}", dpi=300)
    plt.close(fig)
    T = pd.DataFrame(rows)
    T.to_csv("results/tables/f_g_regime_map.csv", index=False)
    for grid in ("design", "held"):
        t = T[T.grid == grid]
        E.add(f"g4.{grid}.n_cells", len(t), "cells", "SIMULATED")
        E.add(f"g4.{grid}.n_ties", int(t.tie.sum()), "cells", "SIMULATED", "best policy beats the runner-up by less than its interval")
        for p, k in t[~t.tie].best.value_counts().items():
            E.add(f"g4.{grid}.wins.{p}", int(k), "cells", "SIMULATED", "cells won outside ties")
        E.add(f"g4.{grid}.p3_wins_cells", int(((t.best == "P3") & ~t.tie).sum()), "cells", "SIMULATED", "cells where P3 (UA-SCT) is the best policy outside ties")


def itertools_pairs(g):
    return [(sf, d) for sf in g["sf"] for d in g["duty"]]


def itertools_np(g):
    return [(n, p) for n in g["n"] for p in g["p"]]


def g5_eval(E: Entries, R5: pd.DataFrame, R5r: pd.DataFrame) -> None:
    cells = sorted(R5.cell.unique())
    concl = {"C1_best_minus_P1+": ("P1+", "base", "reach10_critical"), "C2_slot_minus_base": ("base", "slot", "reach10_critical"), "C3_lbt_minus_base": ("base", "lbt", "reach10_critical"), "C4_relay_minus_base_30s_rx": ("base", "relay", "reach30_rx_critical")}
    base_cat = {}
    flips: dict = {k: [] for k in concl}
    for v in sorted(R5.variant.unique(), key=lambda x: (x != "base", x)):
        sub = R5[R5.variant == v]
        for k, (a, b, m) in concl.items():
            tri = G.pooled(G.arr(sub, a, m, cells), G.arr(sub, b, m, cells))
            add_ci(E, f"g5.{v}.{k}", tri, "fraction", "held-out cells, one assumption varied")
            c = cat(*tri)
            E.add(f"g5.{v}.{k}.category", c, "sign", "SIMULATED", "+1 interval above zero, -1 below, 0 includes zero")
            if v == "base":
                base_cat[k] = c
            elif c != base_cat[k]:
                flips[k].append(v)
    for v, sub in (("range32", R5r),):
        tri = G.pooled(G.arr(sub, "P1+", "reach10_critical", cells), G.arr(sub, "base", "reach10_critical", cells))
        add_ci(E, f"g5.{v}.C1_best_minus_P1+", tri, "fraction", "severity mix of +-32 g pairs instead of +-16 g")
        if cat(*tri) != base_cat["C1_best_minus_P1+"]:
            flips["C1_best_minus_P1+"].append(v)
    for k, vs in flips.items():
        E.add(f"g5.flips.{k}", ",".join(vs) or "none", "variants", "SIMULATED", "variants in which the category of the conclusion differs from the base world")
        E.add(f"g5.flips.{k}.n", len(vs), "variants", "SIMULATED")


def tag_forgery(E: Entries) -> None:
    for tl in (4, 8, 16):
        E.add(f"g6.tag{tl}.forgery_prob_per_try", 2.0 ** (-8 * tl), "probability", "ANALYTICAL", "random tag guess, perfect HMAC assumed")
        E.add(f"g6.tag{tl}.expected_successes_in_200000_tries", 200000 * 2.0 ** (-8 * tl), "count", "ANALYTICAL", "the budget of attack case X03")
    E.add("g6.relay.model_check", "no separate run: a relayed copy is an honest duplicate of a message already in the model (the attacker's replay and the channel's duplication cover it); inferred, not model-checked", "text", "ANALYTICAL")
    E.add("g6.slot_lbt.model_check", "timing only: no message rule changes; not in the model; inferred", "text", "ANALYTICAL")
    E.add("g6.cancel.model_check", "design: C3 fails (351,754 states); pending cancel: all 9 properties hold; attack cases: 48 of 48 original, 9 of 10 extra (X06 changes by design); see f.b1.*", "text", "ANALYTICAL")


def main() -> None:
    R1 = pd.read_pickle(OUT / "f_g1.pkl")
    R2 = pd.read_pickle(OUT / "f_g2.pkl")
    R3 = pd.read_pickle(OUT / "f_g3.pkl")
    R5 = pd.read_pickle(OUT / "f_g5.pkl")
    R5r = pd.read_pickle(OUT / "f_g5r.pkl")
    best = json.loads((OUT / "f_g_best.json").read_text())["best"]
    t = FS.tuned()
    E = Entries("f.g", SRC)
    E.add("baseline_policy_chosen_on_design", best, "policy", "SIMULATED", "highest mean critical reach within 10 s on the DESIGN grid among P0, P1, P1e, P1+, P1+e, P2, P3, P4, P3b; fixed before the held-out run")
    allR = pd.concat([R1, R2, R3, R5, R5r], ignore_index=True)
    E.add("runs", int(len(allR)), "runs", "SIMULATED", "all block G runs")
    E.add("runs_exceeding_duty", int(allR.duty_exceeded.sum()), "runs", "SIMULATED", "independent scan of logged transmissions; must be 0")
    g1_eval(E, R1)
    names = {v: lay for v, (lay, *_r) in G.g2_variants(t).items()}
    g2_eval(E, R2, names)
    g3_eval(E, R3)
    g4_eval(E, R1, R3, best)
    g5_eval(E, R5, R5r)
    tag_forgery(E)
    E.write()
    print("runs", len(allR), "duty exceeded", int(allR.duty_exceeded.sum()), "best", best)


if __name__ == "__main__":
    main()
