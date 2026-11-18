"""Paper-ready CSV and LaTeX tables of the v2 studies (docs/02_preregistration/PREREGISTRATION_V2.md). Every row names the ``results.json`` key it was read from; no number is typed here. Output: results/paper/v2_tab_*.csv and .tex,
results/paper/missing_keys_v2.txt (empty when every cited key exists)."""
from __future__ import annotations

import shutil

import pandas as pd

from crashguard import config as C
from crashguard import paper_tables as PT
from crashguard.paper_tables import MISSING, ci, v, write

VN = {"V1": "controller", "V2": "token bucket", "V3": "beacon-assisted", "V4": "severity-scaled backoff", "V5": "graceful demotion"}


def t_estimators() -> None:
    rows = []
    for rg in (16, 32, 64):
        for m, nm in (("B", "plain"), ("SP", "spline"), ("M", "fill"), ("M+", "fill + ridge"), ("TRI", "triangle fit (our implementation of the idea)"), ("GP", "Gaussian-process fill (our implementation of the idea)"),
                      ("AVG", "pulse-family average"), ("RIDGE", "ridge on all features (EXPLORATORY)"), ("GBR", "gradient boosting (EXPLORATORY)"), ("QR", "tail-aware, median quantile model (primary)")):
            row = {"Range (g)": f"+-{rg}", "Estimator": nm}
            keys = []
            for met, lab in (("median", "Median error (%)"), ("p90", "90th percentile (%)"), ("p95", "95th percentile (%)"), ("w10", "Within 10%")):
                a, lo, hi, k = ci(f"v2.a.R.r{rg}.{m}.{met}", 3)
                row[lab], row[lab + " lower"], row[lab + " upper"] = a, lo, hi
                keys.append(k)
            row["Origin"], row["results.json key"] = "MEASURED_SOFTWARE", " | ".join(keys)
            rows.append(row)
    write("v2_tab_estimators", pd.DataFrame(rows), "Study A: clipping estimators, split R (repeated grouped cross-validation, 176 NHTSA tests, 100 Hz). Errors are absolute delta-V errors; intervals are 95% grouped bootstrap.")


def t_bounds() -> None:
    rows = []
    for rg in (16, 32, 64):
        a, lo, hi, k = ci(f"v2.a.a2.r{rg}.containment", 3)
        rows.append({"Range (g)": f"+-{rg}", "Containment": a, "Lower 95%": lo, "Upper 95%": hi, "Tests with a clipped sample": v(f"v2.a.a2.r{rg}.n_saturated"), "Plain estimate above the reference": v(f"v2.a.a2.r{rg}.lower_exceeds_ref_1p00"),
                     "Upper bound below the reference": v(f"v2.a.a2.r{rg}.upper_below_ref"), "Mean width (km/h)": v(f"v2.a.a2.r{rg}.width_kmh_mean"), "Origin": "MEASURED_SOFTWARE", "results.json key": k})
    write("v2_tab_bounds", pd.DataFrame(rows), "Study A2: share of the 176 tests whose reference delta-V lies between the plain estimate (lower bound) and the pulse-family upper bound.")


def t_intervals() -> None:
    rows = []
    for rg in (16, 32, 64):
        for k, nm in (("i", "plain split conformal"), ("ii", "conformalized quantile regression"), ("iii", "normalised score (adaptive)")):
            for b, bn in (("", "all"), ("bin_none", "never clipped"), ("bin_low", "lowest tercile"), ("bin_mid", "middle tercile"), ("bin_high", "highest tercile")):
                pre = f"v2.a.a5.r{rg}.{k}" + (f".{b}" if b else "")
                if f"{pre}.coverage" not in PT.R:
                    continue
                row = {"Range (g)": f"+-{rg}", "Interval": nm, "Clipped-fraction bin": bn, "Coverage": v(f"{pre}.coverage"), "Mean width (km/h)": v(f"{pre}.width_kmh") if f"{pre}.width_kmh" in PT.R else None,
                       "Median relative width": v(f"{pre}.width_rel") if f"{pre}.width_rel" in PT.R else None, "Origin": "MEASURED_SOFTWARE", "results.json key": pre + ".coverage"}
                rows.append(row)
    write("v2_tab_intervals", pd.DataFrame(rows), "Study A5: coverage and width of the 90% intervals on held-out vehicles, overall and by clipped-fraction bin (split R).")


def t_abstention() -> None:
    rows = []
    for rg in (16, 32, 64):
        rows.append({"Range (g)": f"+-{rg}", "Share flagged": v(f"v2.a.a6.r{rg}.share_flagged"), "p90 error unflagged (%)": v(f"v2.a.a6.r{rg}.unflagged.p90_err") if f"v2.a.a6.r{rg}.unflagged.p90_err" in PT.R else None,
                     "p90 error flagged (%)": v(f"v2.a.a6.r{rg}.flagged.p90_err") if f"v2.a.a6.r{rg}.flagged.p90_err" in PT.R else None, "Origin": "MEASURED_SOFTWARE (EXPLORATORY)", "results.json key": f"v2.a.a6.r{rg}.share_flagged"})
    write("v2_tab_abstention", pd.DataFrame(rows), "Study A6: abstention flag (clipped fraction above the 75th training percentile or interval width above the 75th calibration percentile).")


def t_onset() -> None:
    rows = []
    for rg in (16, 32, 64):
        for fs in (100, 200):
            for rn, nm in (("D2", "clip-onset flag"), ("II", "running delta-V reaches 40 km/h (severity analogue of the early-exit rule)"), ("I", "full-pulse class"), ("PK", "early-peak threshold")):
                pre = f"v2.d.R.r{rg}.f{fs}.{rn}"
                d, dlo, dhi, k1 = ci(f"{pre}.detection", 3)
                o, olo, ohi, k2 = ci(f"{pre}.over_triage", 3)
                rows.append({"Range (g)": f"+-{rg}", "Rate (Hz)": fs, "Rule": nm, "Detection": d, "Detection lower": dlo, "Detection upper": dhi, "Over-triage": o, "Over-triage lower": olo, "Over-triage upper": ohi,
                             "Median time saved (ms)": v(f"{pre}.median_time_saved_ms") if f"{pre}.median_time_saved_ms" in PT.R else None, "Share never clipping": v(f"v2.d.r{rg}.f{fs}.share_never_clip"), "Origin": "MEASURED_SOFTWARE", "results.json key": f"{k1} | {k2}"})
    write("v2_tab_onset_flag", pd.DataFrame(rows), "Study D: clip-onset early flag against the comparators (split R, 176 NHTSA tests); detection = share of reference Severe or Critical tests flagged, over-triage = share of Low or Moderate tests flagged.")


def t_adaptive() -> None:
    rows = []
    cells = ["burst_base", "burst_burst10", "burst_burst60", "burst_cars50", "burst_cars200", "burst_sf9", "burst_capnone", "loadedburst_base", "loadedburst_cars200", "loadedburst_sf9", "steady_base", "steady_cars200",
             "steady_loss30", "single_loss60", "mixed_cars200"]
    for c in cells:
        for vv, nm in VN.items():
            a, lo, hi, k = ci(f"v2.b.gain.{c}.{vv}.reach10_critical", 4)
            rows.append({"Cell": c, "Variant": nm, "Critical reach within 10 s, variant minus matched baseline": a, "Lower 95%": lo, "Upper 95%": hi, "Origin": "SIMULATED", "results.json key": k})
    write("v2_tab_adaptive", pd.DataFrame(rows), "Study B: adaptive escalation variants against matched fixed lowered-threshold baselines (40 paired seeds per cell; every value an assumption of the simulator).")


def t_sens() -> None:
    rows = []
    for nm in sorted({k.split(".mean_gain_burst_cells")[0] for k in PT.R if k.startswith("v2.b.sens.") and k.endswith(".mean_gain_burst_cells")}):
        pre = nm
        rows.append({"Setting": pre.replace("v2.b.sens.", ""), "Mean gain over the burst cells": v(pre + ".mean_gain_burst_cells"), "Largest cell gain": v(pre + ".max_cell_gain"), "Cells with interval above zero": v(pre + ".cells_with_interval_above_zero"),
                     "Origin": "SIMULATED (EXPLORATORY)", "results.json key": pre + ".mean_gain_burst_cells"})
    write("v2_tab_sensitivity", pd.DataFrame(rows), "Study B5: one-at-a-time parameter sweeps on the ten burst cells (EXPLORATORY).")


def t_tags() -> None:
    rows = []
    for t in (4, 6, 8, 12, 16):
        rows.append({"Tag bytes": t, "log2 expected forgery attempts": v(f"v2.e.forgery.t{t}.log2_expected_attempts"), "log2 attempts for 1e-6 (SF7)": v(f"v2.e.forgery.t{t}.sf7.log2_attempts_for_1e6"),
                     "Frames per hour at 1% duty (SF9)": v(f"v2.e.forgery.t{t}.sf9.attempts_per_hour_dutycap"), "Expected years to one forgery (SF9, duty-capped)": v(f"v2.e.forgery.t{t}.sf9.years_expected_dutycap"),
                     "Critical reach within 10 s (P2, 10 burst cells)": v(f"v2.e.cells.P2.t{t}.reach10_critical"), "Origin": "ANALYTICAL (forgery) and SIMULATED (reach)", "results.json key": f"v2.e.forgery.t{t}.*; v2.e.cells.P2.t{t}.reach10_critical"})
    write("v2_tab_tag_length", pd.DataFrame(rows), "Study E: authentication-tag length against forgery work factor and burst delivery. The duty limit does not bind an attacker; no proof is claimed.")


def t_hold() -> None:
    rows = []
    for pn in ("ppv", "simmix", "simmix_fa1"):
        for r in (1, 10, 100, 1000, 10000):
            rows.append({"p": pn, "C_delay / C_false per second": r, **{f"Optimal hold class {c} (s)": v(f"v2.f.opt.{pn}.ratio{r}.class{c}") for c in range(4)}, "Origin": "ANALYTICAL", "results.json key": f"v2.f.opt.{pn}.ratio{r}.class*"})
    write("v2_tab_hold_cost_grid", pd.DataFrame(rows), "Study F1: model-optimal hold per class over the cost-ratio grid, for the three values of p.")
    rows = []
    for cell in ("fa5_steady", "fa1_steady", "fa5_loadedburst_base", "fa5_loadedburst_cars200", "fa5_loadedburst_sf9"):
        for cfg, nm in (("a_current", "current (Severe 0 s)"), ("b_sev2", "Severe 2 s"), ("c_model_optimal", "model-optimal at ratio 100"), ("d_flat2", "flat 2 s for all classes")):
            a, lo, hi, k = ci(f"v2.f.cell.{cell}.{cfg}.fa_rx_share_sev", 4)
            r, rlo, rhi, k2 = ci(f"v2.f.cell.{cell}.{cfg}.reach10_critical", 4)
            rows.append({"Cell": cell, "Hold rule": nm, "False Severe alerts reaching the base": a, "Lower 95%": lo, "Upper 95%": hi, "Critical reach within 10 s": r, "Reach lower": rlo, "Reach upper": rhi,
                         "Origin": "SIMULATED", "results.json key": f"{k} | {k2}"})
    write("v2_tab_hold_sim", pd.DataFrame(rows), "Study F2: false Severe alerts reaching the base and critical reach, by hold rule (40 paired seeds per cell; every value an assumption of the simulator).")


def t_verdicts() -> None:
    rows = []
    for h in ("H-A1", "H-A2", "H-A3", "H-B1", "H-B2", "H-B3", "H-D1", "H-D2", "H-E1", "H-E2", "H-F1", "H-F2"):
        e = PT.R[f"v2.holm.verdict.{h}"]
        rows.append({"Hypothesis": h, "Verdict": e["value"], "Reason": e["notes"], "Raw p": v(f"v2.holm.{h}.p_raw") if f"v2.holm.{h}.p_raw" in PT.R else None, "Holm-adjusted p": v(f"v2.holm.{h}.p_holm") if f"v2.holm.{h}.p_holm" in PT.R else None,
                     "Origin": e["origin"], "results.json key": f"v2.holm.verdict.{h}"})
    write("v2_tab_verdicts", pd.DataFrame(rows), "v2 hypotheses: verdicts and Holm-adjusted p-values (nine tested hypotheses; H-B3, H-E2 and H-F1 are decided by rule).")


def main() -> None:
    MISSING.clear()
    for fn in (t_estimators, t_bounds, t_intervals, t_abstention, t_onset, t_adaptive, t_sens, t_tags, t_hold, t_verdicts):
        fn()
    (PT.OUT / "missing_keys_v2.txt").write_text("\n".join(sorted(set(MISSING))), encoding="utf-8")
    fig = C.FIGURES / "v2_e_tag_curve.png"
    if fig.exists():
        (PT.OUT / "figures").mkdir(parents=True, exist_ok=True)
        for ext in ("png", "pdf"):
            shutil.copy(C.FIGURES / f"v2_e_tag_curve.{ext}", PT.OUT / "figures" / f"v2_e_tag_curve.{ext}")
    print(f"wrote v2 tables to {PT.OUT}; {len(set(MISSING))} cited keys were missing")


if __name__ == "__main__":
    main()
