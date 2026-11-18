"""T15: paper-ready tables (CSV and LaTeX) and figures. Every row cites the results.json key (or keys) it was read from; no number is typed here. Output: results/paper/*.csv, *.tex and figures.

Tables: sensor range against the share within +-10%; clipping methods; interval coverage and width per range; policy comparison with intervals (including the equal-escalation baselines, T1); Pareto curves (T2);
sensitivity sweep (T8); ablations (T9); near-duplicate comparison (T5); null results.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crashguard import config as C

OUT = Path("results/paper")
R = {e["name"]: e for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
MISSING: list[str] = []


def v(key: str):
    e = R.get(key)
    if e is None:
        MISSING.append(key)
        return None
    return e["value"]


def ci(key: str, d: int = 3, lo: str = "_lo", hi: str = "_hi") -> tuple:
    """(value, lo, hi, keys) read from key, key_lo and key_hi."""
    a, b, c = v(key), v(key + lo), v(key + hi)
    f = lambda x: x if (x is None or isinstance(x, str)) else round(float(x), d)  # noqa: E731
    return f(a), f(b), f(c), f"{key}; {key}{lo}; {key}{hi}"


def esc(s: str) -> str:
    return str(s).replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("%", "\\%").replace("&", "\\&").replace("#", "\\#").replace("{", "\\{").replace("}", "\\}")


def write(name: str, df: pd.DataFrame, caption: str, key_col: bool = True) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / f"{name}.csv", index=False)
    cols = list(df.columns)
    lines = ["\\begin{table}[t]", "\\centering", "\\small", f"\\caption{{{esc(caption)}}}", f"\\label{{tab:{name}}}", "\\begin{tabular}{" + "l" * len(cols) + "}", "\\toprule",
             " & ".join(esc(c) for c in cols) + " \\\\", "\\midrule"]
    for _i, row in df.iterrows():
        lines.append(" & ".join("" if (isinstance(x, float) and x != x) else esc(x) for x in row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
    (OUT / f"{name}.tex").write_text("\n".join(lines), encoding="utf-8")


def t_sensor_range() -> None:
    rows = []
    for rg in (16, 32, 64):
        for fs in (100, 200):
            a, lo, hi, k = ci(f"sevstudy.grid.r{rg}.f{fs}.dv_within10", 3)
            rows.append({"Range (g)": f"+-{rg}", "Rate (Hz)": fs, "Share within 10%": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    write("tab_sensor_range", pd.DataFrame(rows), "Share of NHTSA tests whose delta-V is within 10% of the reference, by sensor range and rate (plain integration).")


def t_clipping() -> None:
    rows = []
    for rg in (16, 32, 64):
        for m, nm in (("B", "plain"), ("SP", "spline"), ("M", "fill"), ("M+", "fill + ridge (named primary after earlier results were seen)")):
            for met, lab in (("median", "median error (%)"), ("w10", "within 10%"), ("p90", "90th percentile error (%)")):
                a, lo, hi, k = ci(f"n14x.R.r{rg}.{m}.{met}", 3)
                rows.append({"Range (g)": f"+-{rg}", "Method": nm, "Metric": lab, "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    write("tab_clipping_methods", pd.DataFrame(rows), "Clipping methods, split R (repeated grouped cross-validation, 176 NHTSA tests, 100 Hz).")


def t_intervals() -> None:
    rows = []
    for rg in (16, 32, 64):
        for al, nom in ((10, "90%"), (5, "95%")):
            for var in ("pooled", "cc"):
                a, lo, hi, k = ci(f"ua.r{rg}.a{al}.{var}.coverage", 3)
                w, _, _, kw = ci(f"ua.r{rg}.a{al}.{var}.width", 2)
                rows.append({"Range (g)": f"+-{rg}", "Target": nom, "Version": "class-conditional" if var == "cc" else "pooled", "Coverage": a, "Lower 95%": lo, "Upper 95%": hi, "Mean width (classes)": w,
                             "Origin": "MEASURED_SOFTWARE", "results.json key": f"{k}; {kw}"})
    write("tab_interval_coverage", pd.DataFrame(rows), "Conformal class intervals: two-sided coverage against target and mean width, by sensor range (grouped bootstrap).")


def t_policies() -> None:
    rows = []
    for rg in (16, 32, 64):
        for mode in ("steady", "burst"):
            for pol, nm in (("P0", "P0 fixed 3-retry"), ("P1", "P1 severity table"), ("P2", "P2 SCT"), ("P3", "P3 UA-SCT"), ("P4", "P4 UA-SCT capped")):
                for met in ("mis_triage", "escalation", "reach10_critical", "reach30_critical"):
                    a, lo, hi, k = ci(f"s11.cell.r{rg}.{mode}.base.{pol}.{met}", 3)
                    rows.append({"Range (g)": f"+-{rg}", "Cell": mode, "Policy": nm, "Metric": met, "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "SIMULATED", "results.json key": k})
    for rg in (16, 32, 64):
        for g in ("steady", "burst"):
            for b, a_, lab in (("P3", "P2e", "P3 minus P2e (equal escalation)"), ("P3", "P1e", "P3 minus P1e (equal escalation)")):
                for met in ("reach10_critical", "reach30_critical"):
                    a, lo, hi, k = ci(f"t1.r{rg}.{g}.{b}_minus_{a_}.{met}", 3)
                    rows.append({"Range (g)": f"+-{rg}", "Cell": g, "Policy": lab, "Metric": met, "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "SIMULATED", "results.json key": k})
        a, lo, hi, k = ci(f"t1.r{rg}.mis_triage_p3_minus_p1e", 4)
        rows.append({"Range (g)": f"+-{rg}", "Cell": "pool", "Policy": "P3 minus P1e (equal escalation)", "Metric": "mis_triage", "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    write("tab_policy_comparison", pd.DataFrame(rows), "Policy comparison at the default cell (100 cars, SF7, duty 1%), and at equal escalation (T1).")


def t_pareto() -> None:
    rows = []
    for rg in (16, 32, 64):
        for fam, nm in (("point", "point class (P0, P1, P2), thresholds scaled"), ("interval", "upper end of class interval (P3, P4), alpha varied")):
            a, lo, hi, k = ci(f"t2.r{rg}.{fam}.auc", 4)
            rows.append({"Range (g)": f"+-{rg}", "Family": nm, "Area under mis-triage against escalation": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
        a, lo, hi, k = ci(f"t2.r{rg}.auc_interval_minus_point", 4)
        rows.append({"Range (g)": f"+-{rg}", "Family": "interval minus point (negative = interval better)", "Area under mis-triage against escalation": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    write("tab_pareto", pd.DataFrame(rows), "Trade-off curves (T2): area under the mis-triage against escalation curve, lower is better.")


def t_sweep() -> None:
    rows = []
    for base in ("P1", "P2"):
        for met in ("reach10_critical", "reach30_critical", "mis_triage"):
            row = {"Baseline": base, "Metric": met}
            for k in ("beats", "tie", "loses", "cells"):
                row[k] = v(f"t8.count.P3_vs_{base}.{met}.n_{k}")
            row["Cells where P3 does not beat the baseline"] = v(f"t8.count.P3_vs_{base}.{met}.cells_not_beating")
            row["Origin"] = "SIMULATED"
            row["results.json key"] = f"t8.count.P3_vs_{base}.{met}.n_*"
            rows.append(row)
    write("tab_sensitivity_sweep", pd.DataFrame(rows), "Simulator assumption sweep (T8): cells in which P3 beats, ties or loses against P1 and P2.")
    rows = []
    for mode in ("steady", "burst"):
        for st in ("base", "capture_none", "burst10", "burst60", "hbpayload26", "cars50", "cars200", "sf9", "loss0", "loss20", "loss40", "loss60", "duty0p1"):
            if mode == "steady" and st in ("burst10", "burst60"):
                continue  # burst size is a burst-cell setting only
            a, lo, hi, k = ci(f"t8.diff.{mode}.{st}.P3_minus_P1.reach10_critical", 3)
            if a is None:
                continue
            a2, lo2, hi2, k2 = ci(f"t8.diff.{mode}.{st}.P3_minus_P2.reach10_critical", 3)
            rows.append({"Cell": mode, "Setting": st, "P3 minus P1, reach within 10 s": a, "Lower 95%": lo, "Upper 95%": hi, "P3 minus P2, reach within 10 s": a2, "Lower 95% (P2)": lo2, "Upper 95% (P2)": hi2,
                         "Origin": "SIMULATED", "results.json key": f"{k}; {k2}"})
    write("tab_sweep_cells", pd.DataFrame(rows), "Simulator sweep by cell: critical reach within 10 s, P3 minus P1 and P3 minus P2.")


def t_ablations() -> None:
    rows = []
    for pol in ("P2", "P3"):
        for cell in ("steady_base", "burst_base", "burst_b60", "burst_sf9", "burst_loss30", "steady_fa5"):
            for vn in ("no_flash", "no_hold", "quick_retries", "no_reserve", "no_sf_raise", "no_cancel_msg"):
                a, lo, hi, k = ci(f"t9.diff.{cell}.{pol}.{vn}_minus_full.reach10_critical", 3)
                if a is None:
                    continue
                rows.append({"Policy": pol, "Cell": cell, "Component removed": vn, "Change in reach within 10 s": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "SIMULATED (EXPLORATORY)", "results.json key": k})
    write("tab_ablations", pd.DataFrame(rows), "Ablations of the SCT components (T9, exploratory): change in critical reach within 10 s when one component is removed.")


def t_near_dup() -> None:
    rows = []
    for met, lab in (("recall_f1", "system recall, validation F1 threshold"), ("recall_t1", "recall at 1% false-alarm target"), ("recall_t5", "recall at 5% false-alarm target"), ("ap_model", "AP, triggered events"), ("ap_system", "system AP")):
        for k_, nm in (("std", "standard test set (primary)"), ("strict", "without window-level near-duplicates (sensitivity analysis)")):
            a, lo, hi, k = ci(f"t5.{k_}.{met}", 4)
            rows.append({"Metric": lab, "Test set": nm, "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
        a, lo, hi, k = ci(f"t5.diff_std_minus_strict.{met}", 4)
        rows.append({"Metric": lab, "Test set": "standard minus strict", "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    for which in ("std", "strict"):
        for an in ("a1", "a5"):
            a, lo, hi, k = ci(f"t5.n19.{which}.{an}.recall_gain_ensemble", 4)
            rows.append({"Metric": f"N19 recall gain of the six-forest rule over the single forest ({an[1:]}% target)", "Test set": which, "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
            a, lo, hi, k = ci(f"t5.n19.{which}.{an}.time_diff_ms", 0)
            rows.append({"Metric": f"N19 decision time difference (ms, {an[1:]}% target)", "Test set": which, "Value": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    for var in ("trig_1.5", "trig_2", "trig_2.5", "trig_3"):
        for which in ("std", "strict"):
            for met in ("crash_trigger_rate", "model_level_recall", "system_recall"):
                rows.append({"Metric": f"N9 {met} ({var})", "Test set": which, "Value": v(f"t5.n9.{var}.{which}.{met}"), "Lower 95%": None, "Upper 95%": None, "Origin": "MEASURED_SOFTWARE", "results.json key": f"t5.n9.{var}.{which}.{met}"})
    write("tab_near_duplicates", pd.DataFrame(rows), "Standard test set against the set without window-level near-duplicates (T5; the standard set stays primary).")


def t_nulls() -> None:
    items = [("N20 conformal false-alarm guarantee at alpha 5% (calibration de-duplicated)", "n20c.clean.a5.nall.conformal.fa_mean", "n20c.clean.a5.nall.conformal.fa_mean_lo", "n20c.clean.a5.nall.conformal.fa_mean_hi"),
             ("N24 class rule on delta-V intervals (drop in under-estimation, +-16 g, 90%)", "n24.r16.nom90.under_drop", "n24.r16.nom90.under_drop_lo", "n24.r16.nom90.under_drop_hi"),
             ("N25 precision gain of the prior-shift rule at 0.02% prevalence (recall change)", "s10.rf15.pi0p02pct.b_known.d_recall_vs_a", "s10.rf15.pi0p02pct.b_known.d_recall_vs_a_lo", "s10.rf15.pi0p02pct.b_known.d_recall_vs_a_hi"),
             ("N14 M+ capped minus M+, 90th percentile (+-16 g)", "n14s.cap.R.r16.paired.Mpc_vs_Mp.d_p90", "n14s.cap.R.r16.paired.Mpc_vs_Mp.d_p90_lo", "n14s.cap.R.r16.paired.Mpc_vs_Mp.d_p90_hi"),
             ("UA-SCT P3 minus P1, steady-state critical reach within 10 s (+-16 g)", "s11.diff.r16.steady.P3_minus_P1.reach10_critical", "s11.diff.r16.steady.P3_minus_P1.reach10_critical_lo", "s11.diff.r16.steady.P3_minus_P1.reach10_critical_hi"),
             ("UA-SCT P3 minus P1e, mis-triage at equal escalation (+-16 g)", "t1.r16.mis_triage_p3_minus_p1e", "t1.r16.mis_triage_p3_minus_p1e_lo", "t1.r16.mis_triage_p3_minus_p1e_hi"),
             ("Equal escalation: P3 minus P2e, burst critical reach within 10 s (+-16 g)", "t1.r16.burst.P3_minus_P2e.reach10_critical", "t1.r16.burst.P3_minus_P2e.reach10_critical_lo", "t1.r16.burst.P3_minus_P2e.reach10_critical_hi"),
             ("N19 early exit with the ensemble: recall change (5% target)", "s6.a5.mean5.d.E_minus_Ep.recall", "s6.a5.mean5.d.E_minus_Ep.recall_lo", "s6.a5.mean5.d.E_minus_Ep.recall_hi")]
    rows = []
    for lab, k, kl, kh in items:
        rows.append({"Result": lab, "Value": v(k), "Lower 95%": v(kl), "Upper 95%": v(kh), "Origin": R[k]["origin"] if k in R else "NOT_RUN", "results.json key": k})
    rows.append({"Result": "Second public crash dataset (T13)", "Value": "NOT_RUN", "Lower 95%": None, "Upper 95%": None, "Origin": "NOT_RUN", "results.json key": "t13.second_dataset.analysis"})
    write("tab_null_results", pd.DataFrame(rows), "Results that did not clear their interval, went against the idea, or could not be run.")


def figures() -> None:
    import shutil

    fig_out = OUT / "figures"
    fig_out.mkdir(parents=True, exist_ok=True)
    for name in ("t2_pareto", "s10_ppv_recall", "n14_range_rate", "s5_attack_table"):
        for ext in ("png", "pdf"):
            src = C.FIGURES / f"{name}.{ext}"
            if src.exists():
                shutil.copy(src, fig_out / src.name)


def main() -> None:
    for fn in (t_sensor_range, t_clipping, t_intervals, t_policies, t_pareto, t_sweep, t_ablations, t_near_dup, t_nulls):
        try:
            fn()
        except Exception as err:  # noqa: BLE001 - a table whose inputs do not exist yet is reported, not faked
            print("NOT BUILT", fn.__name__, err)
    figures()
    miss = sorted(set(MISSING))
    (OUT / "missing_keys.txt").write_text("\n".join(miss), encoding="utf-8")
    print(f"wrote {len(list(OUT.glob('*.csv')))} tables to {OUT}; {len(miss)} cited keys were missing (see missing_keys.txt)")


if __name__ == "__main__":
    main()
