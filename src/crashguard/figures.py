"""Figures for S1-S5, trigger sweep and vehicle-size robustness. Reads the CSV tables written by models.py."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard.plots import COLORS, save, style

NAMES = {"rf15": "RF 15 trees, depth 6", "rf200": "RF 200 trees", "lr": "Logistic regression",
         "gbt": "Gradient-boosted trees", "rule": "Rule (peak, duration)"}


def make_figures() -> None:
    style()
    T = C.TABLES
    # S1 class balance
    meta = pd.read_parquet(C.PROCESSED / "events_meta.parquet")
    names = {0: "crash", 1: "near_miss", 2: "normal_driving"}
    ct = meta.groupby(["split", "label"]).size().unstack().loc[["train", "validation", "test"]]
    fig, ax = plt.subplots(figsize=(6, 3.8))
    x = np.arange(3)
    for i, lab in enumerate(ct.columns):
        ax.bar(x + (i - 1) * 0.27, ct[lab], 0.27, label=names[lab], color=COLORS[i])
    ax.set_xticks(x, ct.index)
    ax.set_xlabel("Supplied split")
    ax.set_ylabel("Events (count)")
    ax.legend()
    save(fig, "s1_class_balance")

    # S2 PR curves
    pr = pd.read_csv(T / "s2_pr_curves_seed42.csv")
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    for i, (m, g) in enumerate(pr.groupby("model", sort=False)):
        ax.plot(g.recall, g.precision, label=NAMES[m], color=COLORS[i])
    ax.set_xlabel("Recall (fraction of crashes found)")
    ax.set_ylabel("Precision (fraction of alarms that are crashes)")
    ax.set_title("Triggered, de-duplicated test events, seed 42", fontsize=10)
    ax.legend(fontsize=8)
    save(fig, "s2_pr_curves")

    # S2 3-class confusion (counts, row-normalised colour)
    cm = pd.read_csv(T / "s2_confusion_3class_rf15_seed42.csv").set_index("true_class")
    v = cm.to_numpy()
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    ax.imshow(v / v.sum(axis=1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            ax.text(j, i, f"{v[i, j]:,}", ha="center", va="center", color="black", fontsize=9)
    ax.set_xticks(range(3), ["not triggered", "triggered,\npredicted negative", "triggered,\npredicted crash"], fontsize=8)
    ax.set_yticks(range(3), cm.index)
    ax.set_xlabel("System outcome (RF 15 trees, seed 42, de-duplicated test; colour = row share)")
    ax.set_ylabel("True class")
    ax.grid(False)
    save(fig, "s2_confusion_3class")

    # S3 ablation
    ab = pd.read_csv(T / "s3_ablation_long.csv")
    ab = ab[ab.metric.isin(["ap", "f1op_f1"])]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.8), sharey=False)
    for ax, met, lab in zip(axes, ["ap", "f1op_f1"], ["Average precision (fraction)", "F1 at validation threshold (fraction)"]):
        g = ab[ab.metric == met]
        for i, fs in enumerate(["all", "no_gyro", "scale_free"]):
            h = g[g.fset == fs].set_index("model").loc[["rf15", "rf200", "lr", "gbt"]]
            ax.bar(np.arange(4) + (i - 1) * 0.27, h["mean"], 0.27, yerr=h["std"], label={"all": "all 14", "no_gyro": "no gyro (13)", "scale_free": "scale-free (5)"}[fs], color=COLORS[i], capsize=2)
        ax.set_xticks(range(4), ["RF15", "RF200", "LogReg", "GBT"])
        ax.set_ylabel(lab)
    axes[0].legend(fontsize=8)
    save(fig, "s3_feature_ablation")

    # S4 size vs AP
    sz = pd.read_csv(T / "s4_size_vs_ap.csv")
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (d, g) in enumerate(sz.groupby("depth")):
        ax.errorbar(g.bytes_est / 1024, g.ap_mean, yerr=g.ap_std, marker="o", ms=4, label=f"depth {d}", color=COLORS[i], capsize=2)
    ax.set_xscale("log")
    ax.set_xlabel("Estimated model size (KiB, host estimate from node count)")
    ax.set_ylabel("Average precision (fraction)")
    ax.legend()
    save(fig, "s4_size_vs_ap")

    # S4b depth sweep with Pareto front
    dg = pd.read_csv(T / "s4b_depth_sweep.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for i, (t, g) in enumerate(dg.groupby("trees")):
        ax.plot(g.flash_est / 1024, g.ap_val_mean, marker="o", ms=4, color=COLORS[i], label=f"{t} trees")
        for r in g.itertuples():
            ax.annotate(f"d{r.depth}", (r.flash_est / 1024, r.ap_val_mean), fontsize=6, xytext=(3, 3), textcoords="offset points")
    pf = dg[dg.pareto].sort_values("flash_est")
    ax.step(pf.flash_est / 1024, pf.ap_val_mean, where="post", color="black", lw=1, ls="--", label="Pareto front")
    rc = dg[dg.recommended]
    ax.scatter(rc.flash_est / 1024, rc.ap_val_mean, s=120, facecolors="none", edgecolors="red", label="recommended")
    ax.set_xscale("log")
    ax.set_xlabel("Estimated flash for the forest (KiB, host estimate)")
    ax.set_ylabel("Validation average precision (fraction)")
    ax.legend(fontsize=7)
    save(fig, "s4b_depth_sweep_pareto")

    # S5 reliability
    cal = pd.read_csv(T / "s5_calibration_seed42.csv")
    fig, ax = plt.subplots(figsize=(4.8, 4.4))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect")
    for i, (m, g) in enumerate(cal.groupby("model", sort=False)):
        ax.plot(g.mean_predicted, g.fraction_positive, marker="o", ms=4, label=NAMES[m], color=COLORS[i])
    ax.set_xlabel("Mean predicted crash probability")
    ax.set_ylabel("Fraction of events that are crashes")
    ax.legend(fontsize=8)
    save(fig, "s5_reliability")

    # Trigger sweep
    tr = pd.read_csv(T / "trigger_rates.csv")
    tr = tr[tr.variant != "peak"].assign(g=lambda d: d.variant.str.replace("trig_", "").astype(float))
    sw = pd.read_csv(T / "trigger_sweep_long.csv")
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    for i, (c, g) in enumerate(tr.groupby("cls")):
        axes[0].plot(g.g, g.trigger_rate * 100, marker="o", label=c, color=COLORS[i])
    axes[0].set_xlabel("Trigger threshold (g)")
    axes[0].set_ylabel("Events that trigger (%)")
    axes[0].legend(fontsize=8)
    for i, (met, lab) in enumerate([("sys_f1op_recall", "system recall"), ("sys_f1op_fpr", "system FPR, all negatives"), ("sys_f1op_fpr_near_miss", "system FPR, near_miss")]):
        g = sw[sw.metric == met].assign(g=lambda d: d.variant.str.replace("trig_", "").astype(float)).sort_values("g")
        axes[1].errorbar(g.g, g["mean"] * 100, yerr=g["std"] * 100, marker="o", label=lab, color=COLORS[i + 3], capsize=2)
    axes[1].set_xlabel("Trigger threshold (g)")
    axes[1].set_ylabel("System rate at validation threshold (%)")
    axes[1].legend(fontsize=8)
    save(fig, "trigger_sweep")

    # Vehicle-size robustness
    lv = pd.read_csv(T / "lovso.csv")
    std = pd.read_csv(T / "ap_by_vehicle_size_standard_test.csv")
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    cats = ["Light", "Medium", "Heavy", "Unknown"]
    a = lv[lv.model == "rf15"].set_index("held_out").loc[cats]
    b = std[std.model == "rf15"].set_index("category").loc[cats]
    ax.bar(np.arange(4) - 0.2, b.ap, 0.4, label="standard split (category seen in training)", color=COLORS[0])
    ax.bar(np.arange(4) + 0.2, a.ap_mean, 0.4, yerr=a.ap_std, label="category held out", color=COLORS[1], capsize=2)
    ax.set_xticks(range(4), cats)
    ax.set_xlabel("Vehicle-size category (RF 15 trees)")
    ax.set_ylabel("Average precision (fraction)")
    ax.legend(fontsize=8)
    save(fig, "lovso_vehicle_size")
