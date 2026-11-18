"""Journal-push paper tables (CSV and LaTeX) and figures. Every row cites the results.json keys it was read from; no number is typed here. Output: results/paper/jp_tab_*.csv, .tex and results/paper/figures/jp_fig_*.
Figures are 3.5 inch wide (single column), 300 dpi PNG and vector PDF, Okabe-Ito colours."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard.paper_tables import OUT, write
from crashguard.plots import COLORS, plt, save, style

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
MISSING: list[str] = []


def v(k: str, d: int = 3):
    if k not in R:
        MISSING.append(k)
        return float("nan")
    x = R[k]
    return round(float(x), d) if isinstance(x, (int, float)) else x


def ci(k: str, d: int = 3) -> str:
    return f"{v(k, d):.{d}f} [{v(k + '_lo', d):.{d}f}, {v(k + '_hi', d):.{d}f}]"


METH = {"B": "plain", "SP": "spline", "M": "fill", "M+": "fill + ridge"}


def t_heldout() -> None:
    rows = []
    for rg in (16, 32, 64):
        for m in ("B", "SP", "M", "M+"):
            b = f"t13.heldout.all.r{rg}.{m}"
            rows.append({"Range (g)": f"+-{rg}", "Method": METH[m], "n tests": int(v(f"{b}.n", 0)), "Median abs error (%)": ci(f"{b}.median", 1), "p90 abs error (%)": ci(f"{b}.p90", 1),
                         "Share within 10%": ci(f"{b}.w10"), "Origin": "MEASURED_SOFTWARE", "results.json key": f"{b}.*"})
    write("jp_tab_t13_heldout", pd.DataFrame(rows), "NHTSA tests of other test modes (739 records, 326 make-and-model groups), 100 Hz, methods fitted on the original 176 tests and not refitted. Intervals resample make-and-model groups.")
    rows = []
    for rg in (16, 32, 64):
        for a, b_ in (("M+", "SP"), ("M", "SP"), ("M+", "B")):
            k = f"t13.heldout.all.r{rg}.paired.{a}_vs_{b_}"
            rows.append({"Range (g)": f"+-{rg}", "Comparison": f"{METH[a]} minus {METH[b_]}", "Difference in median abs error (points)": ci(f"{k}.d_median", 2), "Whole interval below zero": "yes" if v(f"{k}.clears", 0) == 1 else "no",
                         "Origin": "MEASURED_SOFTWARE", "results.json key": f"{k}.*"})
    write("jp_tab_t13_paired", pd.DataFrame(rows), "Paired differences on the held-out test modes (negative = the method on the left is better).")
    rows = []
    for rg in (16, 32, 64, 100, 200):
        for f in (100, 200, 400, 800, 1600):
            kh, ko = f"t13.heldout.grid.r{rg}.f{f}.w10", f"sevstudy.grid.r{rg}.f{f}.dv_within10"
            rows.append({"Range (g)": f"+-{rg}", "Rate (Hz)": f, "Share within 10%, held-out modes": ci(kh), "Share within 10%, 176 tests": ci(ko), "Origin": "MEASURED_SOFTWARE", "results.json key": f"{kh}; {ko}"})
    write("jp_tab_t13_grid", pd.DataFrame(rows), "Share of tests within 10% of the reference delta-V by range and rate: held-out test modes (T13a) against the 176 original tests (N13). A cell meets the requirement if its lower interval end is at least 0.80.")


def t_neardup() -> None:
    rows = [("Pairs of near-identical pulses within the 176", "t13.neardup.pairs.within_176.all"), ("of which across make-and-model groups", "t13.neardup.pairs.within_176.cross_make_model"),
            ("Held-out records with a near-identical pulse among the 176", "t13.neardup.tests.heldout_with_duplicate_in_176"), ("Pairs inside the held-out records", "t13.neardup.pairs.within_heldout"),
            ("Test-side pulses with a training-side duplicate, split A", "t13.neardup.split.A.heldout_with_train_duplicate"), ("Same, split G", "t13.neardup.split.G.heldout_with_train_duplicate"),
            ("Same, repeated grouped cross-validation (mean per repeat)", "t13.neardup.split.R.tests_with_cross_fold_duplicate_per_repeat_mean")]
    df = pd.DataFrame([{"Quantity": a, "Value": v(k, 1), "Origin": "MEASURED_SOFTWARE", "results.json key": k} for a, k in rows])
    write("jp_tab_t13_neardup", df, "Near-duplicate NHTSA pulses (T5 rule on original-rate records): counts. Two of the 176 records are the same test channel counted twice.")


def t_leak() -> None:
    rows = []
    for model, name in (("rf15", "15-tree forest"), ("rfsel", "10-tree depth-9 forest")):
        for met, mn in (("sys_recall", "System recall"), ("recall_at_1pct", "Recall at 1% false alarms"), ("recall_at_5pct", "Recall at 5%"), ("ap", "AP")):
            k = f"vz.v4.{model}"
            rows.append({"Model": name, "Metric": mn, "Supplied": ci(f"{k}.supplied.{met}"), "Exact copies removed": ci(f"{k}.exact.{met}"), "Near-duplicates also removed": ci(f"{k}.near.{met}"),
                         "Difference supplied minus near": ci(f"{k}.diff_supplied_minus_near.{met}", 4), "Origin": "MEASURED_SOFTWARE", "results.json key": f"{k}.*.{met}"})
    write("jp_tab_vz_leakage", pd.DataFrame(rows), "VZCrash headline metrics on three test sets (5-seed means, paired bootstrap over supplied test events).")


def t_verdicts() -> None:
    names = {"H-X1": ("Fixed-point forest (16-bit): AP loss at most 0.005 and flash cut at least 30%", "x1"), "H-X2": ("Cheap-trigger cascade raises crash pass share by 2 points at equal non-crash rate", "x2"),
             "H-X3": ("Group-aware training raises recall at 1% false alarms by 1 point (strict set)", "x3"), "H-X5": ("Fill + ridge keeps the rank of delta-V (Spearman at least 0.90, lower end 0.85) at +-16 g", "x5"),
             "H-X6": ("Lower-bound-anchored estimator lowers the 90th-percentile error by 5 points against fill + ridge", "x6"), "H-X7": ("Some real two-part pair reaches 0.80 where neither part alone does", "x7"),
             "H-X8": ("Sequential rule decides 100 ms earlier at equal recall", "x8")}
    rows = [{"Hypothesis": h, "Statement": t, "Verdict": R[f"x.holm.{h}.verdict"], "Raw p": v(f"x.holm.{h}.p_raw"), "Holm p": v(f"x.holm.{h}.p_holm"), "Origin": "MEASURED_SOFTWARE" if h != "H-X1" else "MEASURED_SOFTWARE; flash ANALYTICAL",
             "results.json key": f"x.{k}.*; x.holm.{h}.*"} for h, (t, k) in names.items()]
    write("jp_tab_x_verdicts", pd.DataFrame(rows), "Preregistered hypotheses of Blocks 4 and 4b with Holm correction over the seven (H-X1, H-X2, H-X3, H-X5 to H-X8).")


def t_x5_x6() -> None:
    rows = []
    for rg in (16, 32, 64):
        for m, n in (("plain", "plain"), ("spline", "spline"), ("fillridge", "fill + ridge"), ("tailaware", "tail-aware"), ("asi", "ASI"), ("dirplain", "direction-adjusted plain")):
            b = f"x.x5.r{rg}.f100.{m}"
            rows.append({"Range (g)": f"+-{rg}", "Measure": n, "Spearman with reference delta-V": ci(f"{b}.rho_ref"), "Class accuracy": ci(f"{b}.class_accuracy") if m != "asi" else "", "Weighted kappa": ci(f"{b}.class_kappa") if m != "asi" else "",
                         "Origin": "MEASURED_SOFTWARE", "results.json key": f"{b}.*"})
    write("jp_tab_x5_rank", pd.DataFrame(rows), "Rank preservation (X5): Spearman correlation with the reference delta-V and agreement with the reference class, 100 Hz, out-of-fold on split R (176 NHTSA tests).")
    rows = []
    for sp in ("R", "A", "G", "O"):
        for m, n in (("B", "plain"), ("M+", "fill + ridge"), ("QR", "tail-aware"), ("TRI", "triangle fit"), ("ANC", "anchored")):
            b = f"x.x6.{sp}.r16.{m}"
            rows.append({"Split": sp, "Estimator": n, "Median abs error (%)": ci(f"{b}.median", 1), "p90 abs error (%)": ci(f"{b}.p90", 1), "Share within 10%": ci(f"{b}.w10"), "Under-estimation share": ci(f"{b}.under"),
                         "Origin": "MEASURED_SOFTWARE", "results.json key": f"{b}.*"})
    write("jp_tab_x6_anchored", pd.DataFrame(rows), "Lower-bound-anchored estimator (X6) against the earlier estimators at +-16 g and 100 Hz on four grouped splits (176 NHTSA tests). Under-estimation: estimate below the reference by more than 10%.")


def t_x1_x3_x8() -> None:
    rows = []
    for var, name in (("float", "float32"), ("q16", "16-bit"), ("q8", "8-bit")):
        k = f"x.x1.dedup.{var}"
        rows.append({"Thresholds and leaves": name, "AP": ci(f"{k}.ap", 4), "Recall at 1% false alarms": ci(f"{k}.recall_at_1pct", 4), "Flash, existing layout (KB)": round(v(f"x.x1.flash.primary.{var}.bytes", 0) / 1000, 1),
                     "Flash, implicit left child (KB, exploratory)": round(v(f"x.x1.flash.compact.{var}.bytes", 0) / 1000, 1), "Origin": "MEASURED_SOFTWARE; flash ANALYTICAL", "results.json key": f"{k}.*; x.x1.flash.*"})
    write("jp_tab_x1", pd.DataFrame(rows), "Fixed-point forest (X1): 10-tree depth-9 forest, de-duplicated test set, 5-seed mean. Flash is a host estimate (nodes times bytes), not an ESP32 compile report.")
    rows = []
    for var, name in (("standard", "standard"), ("downweight", "down-weight by group size"), ("merge", "merge (exploratory)")):
        k = f"x.x3.strict.{var}"
        rows.append({"Training": name, "Recall at 1% false alarms (strict set)": ci(f"{k}.recall_at_1pct", 4), "AP": ci(f"{k}.ap", 4), "Origin": "MEASURED_SOFTWARE", "results.json key": f"{k}.*"})
    write("jp_tab_x3", pd.DataFrame(rows), "Group-aware training (X3), 15-tree forest, strict test set, 5-seed mean.")
    rows = []
    for a in ("a1", "a5"):
        for s in ("dedup", "strict"):
            k = f"x.x8.{a}.{s}"
            rows.append({"False-alarm target": "1%" if a == "a1" else "5%", "Test set": s, "Median decision time, early exit (ms)": ci(f"{k}.E_mediant", 0), "Median decision time, sequential (ms)": ci(f"{k}.Q_mediant", 0),
                         "Recall, early exit": ci(f"{k}.E_recall", 4), "Recall, sequential": ci(f"{k}.Q_recall", 4), "Recall, single 1,800 ms forest": ci(f"{k}.F_recall", 4), "Origin": "MEASURED_SOFTWARE", "results.json key": f"{k}.*"})
    write("jp_tab_x8", pd.DataFrame(rows), "Sequential decision rule (X8) against the N19 early-exit rule and the single full-window forest (5-seed means).")


def t_x7() -> None:
    X = pd.read_csv("results/tables/x7_fusion.csv")
    top = pd.concat([X[~X.exploratory].sort_values("w10_lo", ascending=False).head(4), X[X.exploratory].sort_values("w10_lo", ascending=False).head(4)])
    rows = [{"Low-range part": r.low, "High-range part": r.high, "Fusion rule": r.rule + (" (exploratory)" if r.exploratory else ""), "Share within 10% [95% CI]": f"{r.w10:.3f} [{r.w10_lo:.3f}, {r.w10_hi:.3f}]",
             "Low part alone, lower end": round(r.low_alone_w10_lo, 3), "High part alone, lower end": round(r.high_alone_w10_lo, 3), "Extra part": "1 (count; no price)", "Origin": "MEASURED_SOFTWARE",
             "results.json key": "x.x7." + f"{r.low.split()[0]}_r{r.low.split()[1].replace('+-', '')}_f{r.low.split()[3]}+{r.high.split()[0]}_r{r.high.split()[1].replace('+-', '')}_f{r.high.split()[3]}.{r.rule}.w10"} for r in top.itertuples()]
    write("jp_tab_x7", pd.DataFrame(rows), "Two-part fusion (X7), best four preregistered and best four exploratory combinations. No time synchronisation or mounting error is modelled.")


def figures() -> None:
    style()
    plt.rcParams.update({"font.size": 8})
    # X5: rank correlation against range
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    for i, (m, n) in enumerate((("plain", "plain"), ("spline", "spline"), ("fillridge", "fill + ridge"), ("tailaware", "tail-aware"), ("asi", "ASI"))):
        xs = np.array([16, 32, 64])
        y = np.array([v(f"x.x5.r{r}.f100.{m}.rho_ref", 4) for r in xs])
        lo = np.array([v(f"x.x5.r{r}.f100.{m}.rho_ref_lo", 4) for r in xs])
        hi = np.array([v(f"x.x5.r{r}.f100.{m}.rho_ref_hi", 4) for r in xs])
        ax.errorbar(xs * (1 + 0.04 * (i - 2)), y, yerr=[y - lo, hi - y], fmt="o-", ms=3, lw=0.8, capsize=1.5, color=COLORS[[0, 1, 3, 4, 7][i]], label=n)
    ax.axhline(0.90, color="k", ls="--", lw=0.7)
    ax.set_xscale("log")
    ax.set_xticks([16, 32, 64])
    ax.set_xticklabels(["16", "32", "64"])
    ax.minorticks_off()
    ax.set_xlabel("Sensor range (+-g)")
    ax.set_ylabel("Spearman with reference delta-V")
    ax.legend(fontsize=6, frameon=False, loc="lower right")
    save(fig, "jp_fig_x5_rank", OUT / "figures")
    # X6: p90 by estimator, +-16 g, four splits
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    ests = (("B", "plain"), ("M+", "fill + ridge"), ("QR", "tail-aware"), ("ANC", "anchored"))
    w = 0.2
    for i, (m, n) in enumerate(ests):
        ys = [v(f"x.x6.{sp}.r16.{m}.p90", 1) for sp in ("R", "A", "G", "O")]
        lo = [v(f"x.x6.{sp}.r16.{m}.p90_lo", 1) for sp in ("R", "A", "G", "O")]
        hi = [v(f"x.x6.{sp}.r16.{m}.p90_hi", 1) for sp in ("R", "A", "G", "O")]
        ax.bar(np.arange(4) + (i - 1.5) * w, ys, w, yerr=[np.array(ys) - np.array(lo), np.array(hi) - np.array(ys)], color=COLORS[[7, 3, 4, 0][i]], label=n, capsize=1.2, error_kw=dict(lw=0.6))
    ax.set_xticks(range(4))
    ax.set_xticklabels(["R", "A", "G", "O"])
    ax.set_ylim(0, 100)
    ax.set_ylabel("90th-percentile abs delta-V error (%)")
    ax.set_xlabel("Split (see text for R, A, G, O)", fontsize=6)
    ax.legend(fontsize=6, frameon=False, ncol=4, loc="upper center", columnspacing=0.8, handlelength=1.0)
    save(fig, "jp_fig_x6_p90", OUT / "figures")
    # T13a: share within 10% against range at 200 Hz
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    xs = np.array([16, 32, 64, 100, 200])
    for i, (pre, n) in enumerate((("sevstudy.grid.r{r}.f200.dv_within10", "176 original tests"), ("t13.heldout.grid.r{r}.f200.w10", "held-out test modes"))):
        y = np.array([v(pre.format(r=r), 4) for r in xs])
        lo = np.array([v(pre.format(r=r) + "_lo", 4) for r in xs])
        hi = np.array([v(pre.format(r=r) + "_hi", 4) for r in xs])
        ax.errorbar(xs * (1 + 0.03 * (2 * i - 1)), y, yerr=[y - lo, hi - y], fmt="o-", ms=3, lw=0.8, capsize=1.5, color=COLORS[[0, 3][i]], label=n)
    ax.axhline(0.80, color="k", ls="--", lw=0.7)
    ax.set_xscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in xs])
    ax.minorticks_off()
    ax.set_xlabel("Sensor range (+-g), 200 Hz")
    ax.set_ylabel("Share within +-10% of reference")
    ax.legend(fontsize=6, frameon=False, loc="lower right")
    save(fig, "jp_fig_t13_range", OUT / "figures")


def main() -> None:
    for f in (t_heldout, t_neardup, t_leak, t_verdicts, t_x5_x6, t_x1_x3_x8, t_x7, figures):
        f()
    Path("results/paper/missing_keys_jp.txt").write_text("\n".join(sorted(set(MISSING))), encoding="utf-8")
    print("missing keys:", len(set(MISSING)))


if __name__ == "__main__":
    main()
