"""Final verification run: the four main-text figures that were missing or merged (V7.2), generated from results/results.json only.

    python -m crashguard.vf_figs           # results/figures/vf_*.{png,pdf} (300 dpi), copied to paper/figures/

vf_audit   : C1, recall on the supplied and the de-duplicated VZCrash test sets
vf_proto   : C4, Tamarin and ProVerif outcomes
vf_sim     : C6, critical delivery in two simulators and on measured traces
vf_deploy  : C7, side-rule accuracy on 16 simulated sensor variants and the effect of the mounting calibration
Every colour pair is also separated by a hatch or a mark so that the figures stay readable in greyscale.
"""
from __future__ import annotations

import sys

from crashguard.pp_paper import CB, _save, load


def fig_audit(R: dict) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams["hatch.linewidth"] = 0.4

    sets = [("supplied", "supplied test set", CB["blue"], ""), ("exact", "exact copies removed", CB["sky"], "//"), ("near", "window duplicates also removed", CB["orange"], "xx")]
    metrics = [("sys_recall", "system\nrecall"), ("recall_at_1pct", "recall at the 1%\nfalse-alarm target"), ("recall_at_5pct", "recall at the 5%\nfalse-alarm target")]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw=dict(width_ratios=[1.7, 1]))
    x = np.arange(len(metrics))
    for i, (s, name, c, h) in enumerate(sets):
        v = [R[f"vz.v4.rf15.{s}.{m}"] for m, _ in metrics]
        lo = [R[f"vz.v4.rf15.{s}.{m}_lo"] for m, _ in metrics]
        hi = [R[f"vz.v4.rf15.{s}.{m}_hi"] for m, _ in metrics]
        ax.bar(x + (i - 1) * 0.27, v, 0.26, yerr=[np.array(v) - lo, np.array(hi) - np.array(v)], color=c, hatch=h, edgecolor="black", linewidth=0.5, label=name, capsize=1.5, error_kw=dict(lw=0.6))
        for xi, vi in zip(x + (i - 1) * 0.27, v):
            ax.text(xi, 0.03, f"{vi:.2f}", ha="center", fontsize=5.5, color="white" if c == CB["blue"] else "black", rotation=90, bbox=dict(fc="white", ec="none", pad=0.4, alpha=0.8) if c != CB["blue"] else None)
    ax.set_xticks(x)
    ax.set_xticklabels([n for _, n in metrics], fontsize=6.5)
    ax.set_ylabel("recall (fraction)", fontsize=7)
    ax.set_ylim(0, 1.42)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper center", ncol=1, frameon=False)
    ax.set_title("(a) recall of the 15-tree forest, 95% intervals", fontsize=7.5)
    items = [("cross-split groups\nof identical arrays", R["leakage.exact_hash_groups_across_splits"]), ("events in those groups", R["leakage.cross_split_group_events.total"]),
             ("test events with an exact copy", R["vz.v4.n_events.supplied"] - R["vz.v4.n_events.exact"]), ("triggered test windows\nidentical to a train window", R["dupscan.neardup.n_both"])]
    y = np.arange(len(items))[::-1]
    ax2.barh(y, [v for _, v in items], color=[CB["grey"], CB["grey"], CB["sky"], CB["orange"]], edgecolor="black", linewidth=0.5)
    for yi, (n, v) in zip(y, items):
        ax2.text(v + 20, yi, f"{int(v):,}", va="center", fontsize=6.5)
    ax2.set_yticks(y)
    ax2.set_yticklabels([n for n, _ in items], fontsize=6)
    ax2.set_xlim(0, 1700)
    ax2.set_xlabel("count", fontsize=7)
    ax2.tick_params(labelsize=7)
    ax2.set_title("(b) what was found", fontsize=7.5)
    fig.tight_layout()
    _save(fig, "vf_audit")
    plt.close(fig)


GLYPH = {"verified": ("proved", "✓", CB["blue"]), "proved": ("proved", "✓", CB["blue"]), "falsified": ("attack or trace found", "✗", CB["red"]), "attack found (false)": ("attack or trace found", "✗", CB["red"]),
         "timeout": ("not decided", "?", CB["grey"]), "undecided (timeout)": ("not decided", "?", CB["grey"])}


def fig_proto(R: dict) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    rows_t = [("alert authenticity (L1)", "r3.t2.sec.M1.L1", "r3.t2.sec.M0.L1"), ("acknowledgement authenticity (L2)", "r3.t2.sec.M1.L2", "r3.t2.sec.M0.L2"), ("no cross-vehicle suppression (L3)", "r3.t2.sec.M1.L3", "r3.t2.sec.M0.L3")]
    rows_f = [("replay outside the window (L4)", "r3.t2.sec.fresh.L4"), ("at most once, no base reboot (L4b)", "r3.t2.sec.fresh.L4b"), ("no double acceptance after car reboot (L5)", "r3.t2.sec.fresh.L5_no_double"),
              ("alert ids not reused after car reboot (L5)", "r3.t2.sec.fresh.L5_ids"), ("replay after base reboot (L6)", "r3.t2.sec.fresh.L6")]
    rows_p = [("frozen id, same-second reboot", "a4.a3.proverif.carid_frozen_same_epoch.q1"), ("frozen id, later-second reboot", "a4.a3.proverif.carid_frozen_next_epoch.q1"),
              ("boot counter, any number of boots", "a4.a3.proverif.carid_bootctr_same_epoch.q1"), ("boot counter, write not persisted", "a4.a3.proverif.carid_bootctr_nowrite.q1"), ("frozen id, unbounded time", "a4.a3.proverif.carid_frozen_chain.q1")]
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.6, 9.4)
    ax.axis("off")

    def cell(x, y, key, w=1.0):
        name, g, c = GLYPH[R[key]]
        ax.add_patch(Rectangle((x, y - 0.38), w, 0.76, fc=c, ec="black", lw=0.5, alpha=0.85))
        ax.text(x + w / 2, y, g, ha="center", va="center", fontsize=9, color="white")

    ax.text(0.0, 9.0, "Tamarin, authentication (FORMAL)", fontsize=7.5, weight="bold")
    ax.text(3.95, 8.55, "M1\nper-vehicle key", fontsize=5.8, ha="center", va="bottom")
    ax.text(5.15, 8.55, "M0\nshared key", fontsize=5.8, ha="center", va="bottom")
    y = 7.9
    for n, k1, k0 in rows_t:
        ax.text(0.0, y, n, fontsize=6.3, va="center")
        cell(3.45, y, k1)
        cell(4.65, y, k0)
        y -= 0.85
    ax.text(0.0, y - 0.1, "Tamarin, freshness model (per-vehicle key)", fontsize=7.5, weight="bold")
    y -= 0.85
    for n, k in rows_f:
        ax.text(0.0, y, n, fontsize=6.3, va="center")
        cell(3.45, y, k)
        y -= 0.78
    ax.text(6.3, 9.0, "ProVerif 2.05, car-reboot id lemma (FORMAL)", fontsize=7.5, weight="bold")
    y = 8.1
    for n, k in rows_p:
        ax.text(6.3, y, n, fontsize=6.0, va="center")
        cell(9.2, y, k, 0.6)
        y -= 0.95
    ax.text(6.3, y - 0.2, f"Attack suite: {int(R['sh.s4.scenarios.attacks_accepted'])} of {int(R['sh.s4.scenarios.attack_attempts_counted'])} attempts accepted\n({int(R['sh.s4.suite.total'])} cases; SIMULATED_HW_FORMAT, not firmware)", fontsize=6.3, va="top")
    for i, (txt, g, c) in enumerate([("proved", "✓", CB["blue"]), ("attack or trace found", "✗", CB["red"]), ("not decided (time limit)", "?", CB["grey"])]):
        ax.add_patch(Rectangle((0.0 + i * 2.5, -1.45), 0.5, 0.5, fc=c, ec="black", lw=0.5, alpha=0.85))
        ax.text(0.25 + i * 2.5, -1.2, g, ha="center", va="center", fontsize=8, color="white")
        ax.text(0.65 + i * 2.5, -1.2, txt, fontsize=6.3, va="center")
    _save(fig, "vf_proto")
    plt.close(fig)


def fig_sim(R: dict) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw=dict(width_ratios=[1, 1.05]))
    pol = [("severity table", R["rd.x13.custom.mean_delivery.P1"], R["rd.x13.ns3.mean_delivery.p1"]), ("quick retries", R["rd.x13.custom.mean_delivery.quick"], R["rd.x13.ns3.mean_delivery.quick"]),
           ("Nessa-style", R["rd.x13.custom.mean_delivery.nessa"], R["rd.x13.ns3.mean_delivery.nessa"]), ("D1", R["rd.x13.custom.mean_delivery.D1"], R["rd.x13.ns3.mean_delivery.d1"]),
           ("LoRaWAN standard", R["rd.x13.custom.mean_delivery.khan"], R["rd.x13.ns3.mean_delivery.lorawan"])]
    x = np.arange(len(pol))
    ax.bar(x - 0.2, [p[1] for p in pol], 0.38, label="custom simulator", color=CB["blue"], edgecolor="black", linewidth=0.5)
    ax.bar(x + 0.2, [p[2] for p in pol], 0.38, label="ns-3", color=CB["orange"], hatch="//", edgecolor="black", linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([p[0] for p in pol], rotation=30, ha="right", fontsize=6)
    ax.set_ylabel("critical delivery within 10 s, mean of 32 cells", fontsize=6.5)
    ax.set_ylim(0, 0.95)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper left")
    ax.set_title("(a) two simulators (SIMULATED)", fontsize=7.5)
    pols = [("D1", "D1"), ("quick", "quick"), ("P1", "severity table"), ("khan", "LoRaWAN-style"), ("nessa", "Nessa-style")]
    cols = [CB["sky"], CB["blue"], CB["black"]]
    hat = ["", "//", "xx"]
    for i, g in enumerate("LMH"):
        vals = [R[f"r3.t1.{g}.deliv.{p}"] for p, _ in pols] + [R[f"r3.t1.explore.{g}.deliv.Z0"]]
        ax2.bar(np.arange(len(vals)) + (i - 1) * 0.27, vals, 0.26, label=f"loss group {g}", color=cols[i], hatch=hat[i], edgecolor="black", linewidth=0.5)
    ax2.set_xticks(range(len(pols) + 1))
    ax2.set_xticklabels([n for _, n in pols] + ["no-hold control"], rotation=30, ha="right", fontsize=6)
    ax2.set_ylabel("delivery within 10 s", fontsize=6.5)
    ax2.set_ylim(0, 1.3)
    ax2.tick_params(labelsize=7)
    ax2.legend(fontsize=5.8, ncol=3, loc="upper center", title="L: loss under 10%, M: 10 to 40%, H: 40% or more", title_fontsize=5.8)
    ax2.set_title("(b) measured traces (TRACE_DRIVEN)", fontsize=7.5)
    fig.tight_layout()
    _save(fig, "vf_sim")
    plt.close(fig)


def fig_deploy(R: dict) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    names = ["V00_base", "T_x15", "T_x30", "T_y15", "T_y30", "F_x", "F_y", "S_10Hz", "S_jit1", "S_drop05", "N_x2", "N_x4", "B_08", "P_3", "P_8"]
    acc = [R[f"sh.s2.{n}.side_acc"] for n in names]
    lo = [R[f"sh.s2.{n}.side_acc_lo"] for n in names]
    hi = [R[f"sh.s2.{n}.side_acc_hi"] for n in names]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.8), gridspec_kw=dict(width_ratios=[2.2, 1]))
    x = np.arange(len(names))
    below = [a < 0.90 for a in acc]
    ax.bar(x, acc, 0.7, yerr=[np.array(acc) - lo, np.array(hi) - np.array(acc)], color=[CB["red"] if b else CB["blue"] for b in below], hatch=None, edgecolor="black", linewidth=0.5, capsize=1.2, error_kw=dict(lw=0.5))
    for xi, b in zip(x, below):
        if b:
            ax.text(xi, 0.04, "below 0.90", rotation=90, fontsize=5.5, ha="center", color="white")
    ax.axhline(0.90, color="black", lw=0.8, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=50, ha="right", fontsize=5.8)
    ax.set_ylabel("impact-side accuracy (fraction)", fontsize=7)
    ax.set_ylim(0, 1.08)
    ax.tick_params(labelsize=7)
    ax.set_title("(a) impact-side rule on simulated sensor variants (dashed: 0.90 bound)", fontsize=7.5)
    items = [("raw axes", R["r5.l1.held.sim.pooled_acc_raw"], CB["grey"], ""), ("mounting\ncalibration", R["r5.l1.held.sim.pooled_acc_l1"], CB["blue"], "//")]
    lo2, hi2 = R["r5.l1.held.sim.pooled_acc_l1_lo"], R["r5.l1.held.sim.pooled_acc_l1_hi"]
    for i, (n, v, c, h) in enumerate(items):
        ax2.bar(i, v, 0.6, color=c, hatch=h, edgecolor="black", linewidth=0.5, yerr=None if i == 0 else [[v - lo2], [hi2 - v]], capsize=2)
        ax2.text(i, v + 0.03, f"{v:.2f}", ha="center", fontsize=6.5)
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels([n for n, *_ in items], fontsize=6.5)
    ax2.set_ylim(0, 1.15)
    ax2.set_ylabel("pooled side accuracy, 13 installations", fontsize=6.5)
    ax2.tick_params(labelsize=7)
    ax2.set_title("(b) mounting calibration (V16, L1)", fontsize=7.5)
    fig.tight_layout()
    _save(fig, "vf_deploy")
    plt.close(fig)


def main() -> None:
    R = load()
    fig_audit(R)
    fig_proto(R)
    fig_sim(R)
    fig_deploy(R)
    print("vf figures written")


if __name__ == "__main__":
    main()
    sys.exit(0)
