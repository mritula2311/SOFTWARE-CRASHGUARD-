"""Figures of the positive-results push (PNG and PDF, 300 dpi, colour-blind-safe palette, axes labelled with units). Every figure is drawn from tables written by the P studies; nothing is recomputed here."""
from __future__ import annotations

import json

import pandas as pd

from crashguard import config as C
from crashguard import plots as P
from crashguard import pp_common as PC

P.style()
import matplotlib.pyplot as plt  # noqa: E402

T = C.TABLES
COL = {"a": "#000000", "b": "#E69F00", "c": "#0072B2", "direct": "#D55E00"}
LAB = {"a": "plain", "b": "fill + ridge", "c": "anchored", "direct": "best deployable direct model"}


def fig_p1() -> None:
    d = pd.read_csv(T / "p1_sealed.csv")
    d = d[d.rate_hz == 100]
    fz = json.load(open(T / "p_freeze_P1.json"))["selection"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for j, (met, yl) in enumerate((("macro_f1", "macro-F1 (sealed fold)"), ("under_triage", "under-triage (true Severe or Critical)"))):
        for k, rg in enumerate(PC.RANGES):
            sel = fz[f"{rg:g}_100"]
            for q, (nm, key) in enumerate((("a", "a"), ("b", "b"), ("c", "c"), ("direct", sel["best_direct"]))):
                r = d[(d.range_g == rg) & (d.model == key) & (d.metric == met)].iloc[0]
                ax[j].errorbar(k + (q - 1.5) * 0.15, r.value, yerr=[[r.value - r.lo], [r.hi - r.value]], fmt="o", color=COL[nm], capsize=3, label=LAB[nm] if k == 0 else None)
        ax[j].set_xticks(range(3))
        ax[j].set_xticklabels([f"+-{int(r)} g" for r in PC.RANGES])
        ax[j].set_xlabel("sensor range (g), 100 Hz")
        ax[j].set_ylabel(yl)
    ax[0].legend(fontsize=7)
    P.save(fig, "p_fig_p1_triage")


def fig_p3() -> None:
    d = pd.read_csv(T / "p3a_risk_coverage.csv")
    fig, ax = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
    for i, rg in enumerate((16.0, 32.0)):
        for est in ("a", "b", "c", "direct"):
            r = d[(d.range_g == rg) & (d.estimator == est)].sort_values("retention")
            if est != "direct":
                ax[0, i].plot(100 * r.retention, r.p90, color=COL[est], label=LAB[est])
            ax[1, i].plot(100 * r.retention, r.under, color=COL[est], label=LAB[est])
        ax[0, i].set_title(f"+-{int(rg)} g, 100 Hz")
        ax[0, i].set_ylabel("90th-percentile delta-V error (%)")
        ax[1, i].set_ylabel("under-triage rate (fraction)")
        ax[1, i].set_xlabel("retained share of events (%)")
    ax[1, 0].legend(fontsize=7)
    P.save(fig, "p_fig_p3a_risk_coverage")


def fig_p4a() -> None:
    d = pd.read_csv(T / "p4a_sweep.csv")
    fz = json.load(open(T / "p_freeze_P4a.json"))
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for q, c, m in (("float", "#0072B2", "o"), ("q16", "#E69F00", "s")):
        r = d[d.q == q]
        ax.scatter(r.flash_bytes / 1000, r.test_ap, s=8, alpha=0.5, color=c, marker=m, label="float32 thresholds" if q == "float" else "16-bit thresholds")
    for key, c, nm in (("reference", "#000000", "reference (10 trees, depth 9, 14 features)"), ("selected", "#D55E00", "selected on validation")):
        k = fz[key]
        r = d[(d.trees == k["trees"]) & (d.depth == k["depth"]) & (d.k == k["k"]) & (d.q == k["q"])].iloc[0]
        ax.scatter([r.flash_bytes / 1000], [r.test_ap], s=90, facecolors="none", edgecolors=c, linewidths=2, label=nm)
    R = {e["name"]: e["value"] for e in json.load(open("results/results.json", encoding="utf-8"))}
    if "p.p4d.dedup.cnn_int8.ap" in R:
        ax.scatter([R["p.p4d.flash_bytes_int8"] / 1000], [R["p.p4d.dedup.cnn_int8.ap"]], marker="*", s=160, color="#CC79A7", label="int8 1D CNN (EXPLORATORY)")
    ax.set_xlabel("flash estimate (kB, analytical)")
    ax.set_ylabel("AP, de-duplicated test (5-seed mean)")
    ax.set_ylim(d.test_ap.min() - 0.005, max(d.test_ap.max(), R.get("p.p4d.dedup.cnn_int8.ap", 0)) + 0.005)
    ax.legend(fontsize=7, loc="lower right")
    P.save(fig, "p_fig_p4a_pareto")


def fig_p2() -> None:
    d = pd.read_csv(T / "p2_sealed.csv")
    d = d[(d.rate_hz == 100)]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    names = ["global", "clipbin", "mode", "weighted", "existing", "cvplus"]
    cols = ["#0072B2", "#009E73", "#CC79A7", "#56B4E9", "#E69F00", "#999999"]
    for k, rg in enumerate(PC.RANGES):
        for q, (n, c) in enumerate(zip(names, cols)):
            r = d[(d.range_g == rg) & (d.variant == n)]
            if len(r):
                ax[0].bar(k + (q - 2.5) * 0.13, r.coverage.iloc[0], width=0.12, color=c, label=n if k == 0 else None)
                ax[1].bar(k + (q - 2.5) * 0.13, min(float(r.width_ratio.iloc[0]), 5.0), width=0.12, color=c)
    ax[0].axhline(0.9, color="k", lw=0.8, ls="--")
    ax[0].set_ylabel("coverage, sealed fold")
    ax[1].set_ylabel("mean upper/lower ratio (capped at 5)")
    for a in ax:
        a.set_xticks(range(3))
        a.set_xticklabels([f"+-{int(r)} g" for r in PC.RANGES])
        a.set_xlabel("sensor range (g), 100 Hz")
    ax[0].legend(fontsize=7, ncol=2)
    P.save(fig, "p_fig_p2_intervals")


def fig_p4c() -> None:
    d = pd.read_csv(T / "p4c_guarantee.csv")
    d = d[d.scheme == "loco"]
    fig, ax = plt.subplots(1, 2, figsize=(9, 3.6))
    for j, a in enumerate((0.01, 0.05)):
        r = d[d.alpha == a]
        ax[j].bar(r.variant, 100 * r.fa, color="#0072B2")
        ax[j].errorbar(r.variant, 100 * r.fa, yerr=[[0] * len(r), 100 * (r.fa_hi - r.fa)], fmt="none", color="k", capsize=3)
        ax[j].axhline(100 * a, color="#D55E00", ls="--", label=f"target {100 * a:g}%")
        ax[j].axhline(100 * (a + 0.01), color="#999999", ls=":", label="target + 1 point")
        ax[j].set_ylabel("false-alarm rate, held-out category (%)")
        ax[j].set_xlabel("calibration variant")
        ax[j].legend(fontsize=7)
    P.save(fig, "p_fig_p4c_guarantee")


def main() -> None:
    for f in (fig_p1, fig_p3, fig_p4a, fig_p2, fig_p4c):
        try:
            f()
            print("ok", f.__name__)
        except FileNotFoundError as e:
            print("skipped", f.__name__, e)


if __name__ == "__main__":
    main()
