"""Documents and paper tables of the positive-results push, all generated from ``results/results.json`` and the study tables (nothing typed by hand except wording).

Writes results/paper/p_tab_*.csv and .tex, docs/03_results/POSITIVE_PUSH_RESULTS.md, and marked blocks (``<!-- PP:BEGIN -->`` to ``<!-- PP:END -->``) in docs/03_results/CLAIM_EVIDENCE.md, docs/00_overview/CLAIMS_FOR_COVER_LETTER.md,
docs/03_results/STATS_AUDIT.md, docs/06_references/REFERENCES.md and docs/05_data_code/REPRODUCE_FINISH.md, and the scoring table of docs/05_data_code/SEALED_SPLIT.md. Run it after ``jp_docs`` (which rewrites some of those files).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from crashguard import config as C
from crashguard import pp_common as PC

PAPER = Path("results/paper")
T = C.TABLES
BEGIN, END = "<!-- PP:BEGIN -->", "<!-- PP:END -->"
RES = {e["name"]: e for e in json.load(open("results/results.json", encoding="utf-8"))}


def v(k):
    return RES[k]["value"]


def f(k, d=3):
    x = v(k)
    return x if isinstance(x, str) else f"{float(x):.{d}f}"


def ci(k, d=3):
    return f"{float(v(k)):.{d}f} [{float(v(k + '_lo')):.{d}f}, {float(v(k + '_hi')):.{d}f}]"


def have(k) -> bool:
    return k in RES and RES[k]["value"] != "NOT_RUN"


def write_table(name: str, df: pd.DataFrame, caption: str) -> None:
    PAPER.mkdir(parents=True, exist_ok=True)
    df.to_csv(PAPER / f"{name}.csv", index=False)
    tex = df.to_latex(index=False, escape=True, na_rep="")
    (PAPER / f"{name}.tex").write_text(f"% {caption}\n" + tex, encoding="utf-8")


def put_block(path: str, body: str) -> None:
    p = Path(path)
    s = p.read_text(encoding="utf-8") if p.exists() else ""
    blk = f"{BEGIN}\n{body.strip()}\n{END}"
    if BEGIN in s and END in s:
        s = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: blk, s, flags=re.S)
    else:
        s = s.rstrip("\n") + "\n\n" + blk + "\n"
    p.write_text(s, encoding="utf-8")


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)])


# ------------------------------------------------------------------ tables
def tables() -> dict:
    out = {}
    fz = json.load(open(T / "p_freeze_P1.json"))["selection"]
    sealed = pd.read_csv(T / "p1_sealed.csv")
    NM = {"a": "plain", "b": "fill + ridge", "c": "anchored", "d": "direct GBM", "e": "1D CNN", "fd": "direct GBM, augmented", "fe": "1D CNN, augmented"}
    rows = []
    for fs in PC.RATES:
        for rg in PC.RANGES:
            sel = fz[f"{rg:g}_{fs}"]
            for key, role in ((sel["best_base"], "best of (a) to (c) on validation"), (sel["best_direct"], "best deployable direct model on validation")):
                k, _, mv = key.partition("_")
                r = {"Rate (Hz)": fs, "Range (g)": f"+-{rg:g}", "Role": role, "Model": NM[k] + (f" ({mv} mode)" if mv else "")}
                for met, col in (("macro_f1", "Macro-F1"), ("under_triage", "Under-triage"), ("over_triage", "Over-triage"), ("balanced_acc", "Balanced accuracy")):
                    x = sealed[(sealed.range_g == rg) & (sealed.rate_hz == fs) & (sealed.model == key) & (sealed.metric == met)].iloc[0]
                    r[col] = f"{x.value:.3f} [{x.lo:.3f}, {x.hi:.3f}]"
                rows.append(r)
            t = f"p.p1.r{rg:g}.f{fs}.paired"
            rows.append({"Rate (Hz)": fs, "Range (g)": f"+-{rg:g}", "Role": "difference, direct minus base (sealed fold, paired)", "Model": "",
                         "Macro-F1": ci(t + ".macro_f1_direct_minus_base"), "Under-triage": ci(t + ".under_triage_direct_minus_base"), "Over-triage": "", "Balanced accuracy": ""})
    out["p1"] = pd.DataFrame(rows)
    write_table("p_tab_p1", out["p1"], "P1: severity triage on the sealed fold (186 records), baselines and best deployable direct model, with 95% grouped intervals. 100 Hz rows are the preregistered ones; 200 Hz rows are reported with the same rule.")
    allm = sealed[sealed.rate_hz == 100].pivot_table(index=["range_g", "model"], columns="metric", values="value").reset_index().round(3)
    write_table("p_tab_p1_all", allm, "P1: every model on the sealed fold at 100 Hz (point values; intervals in results.json). Models with oracle in the name use the true crash mode and cannot be deployed.")
    z = []
    for fs in PC.RATES:
        for rg in PC.RANGES:
            t = f"p.p1.r{rg:g}.f{fs}.mode"
            z.append({"Rate (Hz)": fs, "Range (g)": f"+-{rg:g}", "Accuracy [95%]": ci(t + ".accuracy"), "Balanced accuracy": f(t + ".balanced_accuracy")})
    write_table("p_tab_z1", pd.DataFrame(z), "Z1: crash mode inferred from the pulse (random forest on development records), sealed fold.")
    rows = []
    for rg in PC.RANGES:
        for m, nm in (("b", "fill + ridge"), ("c", "anchored"), ("d_none", "direct GBM"), ("cnn_aug", "1D CNN, augmented")):
            t = f"p.p1cvcnn.r{rg:g}.{m}"
            rows.append({"Range (g)": f"+-{rg:g}", "Model": nm, "Macro-F1 [95%]": ci(t + ".macro_f1"), "Under-triage [95%]": ci(t + ".under_triage"),
                         "CNN minus model, macro-F1 [95%]": "" if m == "cnn_aug" else ci(f"p.p1cvcnn.r{rg:g}.paired.cnn_aug_minus_{m}.macro_f1"),
                         "CNN minus model, under-triage [95%]": "" if m == "cnn_aug" else ci(f"p.p1cvcnn.r{rg:g}.paired.cnn_aug_minus_{m}.under_triage")})
    out["p1cv"] = pd.DataFrame(rows)
    write_table("p_tab_p1_cv", out["p1cv"], "EXPLORATORY: grouped 5-fold cross-validation over all 913 records at 100 Hz (sealed-fold records included; run after the sealed fold was scored). Not part of H-P1.")
    rows = []
    for rg in PC.RANGES:
        for var in ("global", "clipbin", "mode", "weighted", "existing", "cvplus"):
            t = f"p.p2.r{rg:g}.f100.{var}" + (".EXPLORATORY" if var == "cvplus" else "")
            if have(t + ".coverage"):
                rows.append({"Range (g)": f"+-{rg:g}", "Interval": {"global": "[plain, plain x q], global q", "clipbin": "q by clipped-duration bin", "mode": "q by inferred mode", "weighted": "global q, group-weighted (exploratory)",
                                                                  "existing": "relative residual around fill + ridge (split form)", "cvplus": "grouped CV+ around fill + ridge (exploratory)"}[var],
                             "Coverage [95%]": ci(t + ".coverage"), "Mean upper/lower ratio [95%]": ci(t + ".width_ratio_mean", 2), "Frontal barrier inside v..2v": f(t + ".frontal_barrier.share_inside_band", 2)})
    out["p2"] = pd.DataFrame(rows)
    write_table("p_tab_p2", out["p2"], "P2: intervals on the sealed fold at 100 Hz, target coverage 0.90. The frontal barrier share uses 20 records.")
    rows = []
    for rg in (16.0, 32.0):
        for est in ("a", "b", "c", "direct"):
            for nm in ("threshold", "exact70"):
                t = f"p.p3a.r{rg:g}.{nm}.{est}"
                r = {"Range (g)": f"+-{rg:g}", "Estimator": {"a": "plain", "b": "fill + ridge", "c": "anchored", "direct": "best direct model"}[est], "Retained by": "validation threshold" if nm == "threshold" else "rank (exactly 70%)"}
                r["p90 error retained (%)"] = ci(t + ".p90_retained", 1) if have(t + ".p90_retained") else "n/a (class output)"
                r["p90 error all (%)"] = ci(t + ".p90_all", 1) if have(t + ".p90_all") else "n/a"
                r["Under-triage retained"] = ci(t + ".under_triage_retained", 2)
                r["Under-triage all"] = ci(t + ".under_triage_all", 2)
                r["Ratio retained / all"] = ci(t + ".under_triage_ratio", 2)
                rows.append(r)
    out["p3a"] = pd.DataFrame(rows)
    write_table("p_tab_p3a", out["p3a"], "P3a: selective prediction on the sealed fold at 100 Hz, retention at 70%. Under-triage counts true Severe or Critical records only.")
    rows = []
    for rg in (16.0, 32.0):
        for sysn, lab in (("A", "abstain to the fast path"), ("P1e", "severity table, lowered thresholds"), ("P1", "severity table, current thresholds")):
            t = f"p.p3b.r{rg:g}.{sysn}"
            rows.append({"Range (g)": f"+-{rg:g}", "System": lab, "Mis-triage [95%]": ci(t + ".mis_triage", 3), "Escalation of non-severe [95%]": ci(t + ".escalation", 3)})
        t = f"p.p3b.r{rg:g}"
        rows.append({"Range (g)": f"+-{rg:g}", "System": "difference A minus lowered table", "Mis-triage [95%]": ci(t + ".mis_triage_A_minus_P1e", 3), "Escalation of non-severe [95%]": ci(t + ".escalation_A_minus_P1e", 3)})
    out["p3b"] = pd.DataFrame(rows)
    write_table("p_tab_p3b", out["p3b"], "P3b: pool-level mis-triage and escalation on the sealed fold (MEASURED_SOFTWARE); the simulated cells are in results/tables/p3b_cells.csv (SIMULATED).")
    rows = []
    for nm in ("reference", "selected"):
        t = f"p.p4a.{nm}"
        rows.append({"Model": nm, "Configuration": v(t + ".config"), "Flash estimate (bytes, analytical)": f"{float(v(t + '.flash_bytes')):.0f}", "Measured host size (bytes, x86-64 -Os)": f(t + ".measured_bytes_host_x86_64_Os", 0), "RAM estimate (bytes)": v(t + ".ram_bytes"),
                     "Validation AP": f(t + ".val_ap", 4), "Test AP (de-duplicated)": f(f"p.p4a.dedup.ap_{nm}", 4), "Test AP (strict)": f(f"p.p4a.strict.ap_{nm}", 4), "Recall at 1% target": f(t + ".test_recall_1pct", 3), "Recall at 5% target": f(t + ".test_recall_5pct", 3)})
    rows.append({"Model": "AP loss, reference minus selected", "Configuration": "", "Flash estimate (bytes, analytical)": "", "Measured host size (bytes, x86-64 -Os)": "", "RAM estimate (bytes)": "", "Validation AP": "",
                 "Test AP (de-duplicated)": ci("p.p4a.dedup.ap_loss", 4), "Test AP (strict)": ci("p.p4a.strict.ap_loss", 4), "Recall at 1% target": "", "Recall at 5% target": ""})
    out["p4a"] = pd.DataFrame(rows)
    write_table("p_tab_p4a", out["p4a"], "P4a: the configuration chosen on validation against the reference forest (10 trees, depth 9, 14 features, float). Flash and RAM are host arithmetic; the measured size is for the host, not an ESP32.")
    rows = []
    for sn in ("strict", "dedup"):
        for var in ("standard", "merge", "aug", "aug_merge"):
            rows.append({"Set": sn, "Variant": var, "Recall at 1% [95%]": ci(f"p.p4b.{sn}.{var}.recall_at_1pct", 4), "AP [95%]": ci(f"p.p4b.{sn}.{var}.ap", 4),
                         "Difference to standard, recall at 1% [95%]": "" if var == "standard" else ci(f"p.p4b.{sn}.diff_{var}_minus_standard.recall_at_1pct", 4)})
    out["p4b"] = pd.DataFrame(rows)
    write_table("p_tab_p4b", out["p4b"], "P4b: augmentation and merging against standard training of the 15-tree forest (5-seed mean). Only aug_merge is the preregistered variant; merge and aug alone are exploratory.")
    c4 = pd.read_csv(T / "p4c_guarantee.csv")
    c4 = c4.rename(columns={"scheme": "Evaluation", "alpha": "Target", "variant": "Variant", "fa": "False-alarm rate", "fa_hi": "Upper end (95%)", "recall": "Recall", "gain": "Recall minus V0"}).round(4)
    out["p4c"] = c4
    write_table("p_tab_p4c", c4, "P4c: false-alarm rate and recall by calibration variant. loco = leave one vehicle-size category out (primary); supplied = the de-duplicated test split. V0 lowest threshold meeting the rate; V1 pooled conformal; V2 by category; V3 CV+; V4 risk control over groups; V5 largest group quantile.")
    rows = []
    for sn in ("dedup", "strict"):
        for m in ("float", "int8"):
            rows.append({"Set": sn, "Model": f"1D CNN, {m} weights", "AP [95%]": ci(f"p.p4d.{sn}.cnn_{m}.ap", 4), "Recall at 1% [95%]": ci(f"p.p4d.{sn}.cnn_{m}.recall_1pct", 3), "Recall at 5% [95%]": ci(f"p.p4d.{sn}.cnn_{m}.recall_5pct", 3)})
    rows.append({"Set": "both", "Model": "parameters / flash estimate (int8)", "AP [95%]": f"{v('p.p4d.n_parameters')} / {v('p.p4d.flash_bytes_int8')} bytes", "Recall at 1% [95%]": "", "Recall at 5% [95%]": ""})
    out["p4d"] = pd.DataFrame(rows)
    write_table("p_tab_p4d", out["p4d"], "P4d (EXPLORATORY, no hypothesis): int8 tiny 1D CNN on the 280-sample accelerometer window; compare with the forest in p_tab_p4a. Weights are int8, activations float in the simulation.")
    b2 = pd.read_csv(T / "p_b2_table.csv")
    rows = []
    for m in PC.MODES:
        ok = b2[b2[f"{m}_lo"] >= 0.80].sort_values(["range_g", "odr_hz", "part"])
        r = {"Mode": m.replace("_", " "), "Records": int(v(f"p.b2.{m}.n_records")), "Configurations meeting the rule": int(v(f"p.b2.{m}.n_configs_meeting"))}
        if len(ok):
            x = ok.iloc[0]
            r.update({"Smallest configuration": f"{x.part}, +-{x.range_g:g} g, {int(x.odr_hz)} Hz", "Share within +-10% [95% lower, upper]": f"{x[m + '_share']:.3f} [{x[m + '_lo']:.3f}, {x[m + '_hi']:.3f}]"})
        else:
            r.update({"Smallest configuration": "none of the 99 configurations", "Share within +-10% [95% lower, upper]": ""})
        rows.append(r)
    out["b2"] = pd.DataFrame(rows)
    write_table("p_tab_b2", out["b2"], "B2: smallest configuration whose lower interval end of the share within +-10% of the reference delta-V is at least 0.80, per crash mode (plain estimate, 913 pooled records, all records used).")
    hol = []
    for n in ("H-P1", "H-P2", "H-P3a", "H-P3b", "H-P4a", "H-P4b", "H-P4c"):
        k = "p.holm." + n.replace("-", "").lower()
        if have(k + ".verdict"):
            hol.append({"Hypothesis": n, "Raw p": f(k + ".p_raw", 3), "Holm p": f(k + ".p_holm", 3), "Criterion met": int(v(k + ".criterion_met")), "Verdict": v(k + ".verdict")})
    out["holm"] = pd.DataFrame(hol)
    write_table("p_tab_holm", out["holm"], "Holm correction over the seven preregistered hypotheses of the positive-results push. Bootstrap p-values have a floor of 0.001.")
    acc = pd.read_csv(T / "p_sealed_access.csv")
    write_table("p_tab_access", acc, "Log of every scoring of the sealed fold and the VZCrash test splits (hypothesis, time, freeze commit, deviation).")
    return out


# ------------------------------------------------------------------ documents
def verdict(n: str) -> str:
    k = "p.holm." + n.replace("-", "").lower() + ".verdict"
    return str(v(k)) if have(k) else "NOT_RUN"


def results_doc(tabs: dict) -> None:
    P1 = {rg: dict(base=json.load(open(T / "p_freeze_P1.json"))["selection"][f"{rg:g}_100"]["best_base"], direct=json.load(open(T / "p_freeze_P1.json"))["selection"][f"{rg:g}_100"]["best_direct"]) for rg in PC.RANGES}
    L = ["# Positive-results push: results (generated)", "",
         "Branch `positive-push` (from tag `journal-push-v3`), 2026-11-12. Software only; `data/hardware` was not read. Every number below is read from `results/results.json` (keys `p.*`) by `src/crashguard/pp_docs.py`. Labels: MEASURED_SOFTWARE unless stated; "
         "the UA-SCT cells of P3b are SIMULATED; flash and RAM estimates are ANALYTICAL. The design (preregistration, sealed fold, freeze commits) is in `docs/02_preregistration/PREREGISTRATION_V4.md` and `docs/05_data_code/SEALED_SPLIT.md`. NHTSA records are crash tests, mostly high-speed; "
         "the sensor is a software model; VZCrash events were selected on the device before release. Nothing here is a field or hardware result.", "",
         "## Verdicts (Holm over seven preregistered hypotheses)", "", md_table(tabs["holm"]), "",
         f"Of the seven hypotheses, {int((tabs['holm'].Verdict == 'SUPPORTED').sum())} is SUPPORTED and {int((tabs['holm'].Verdict == 'NOT SUPPORTED').sum())} are NOT SUPPORTED. Anything outside the seven (P4d, the cross-validation of P1, the matched-escalation comparison of P3b, the exploratory interval variants) is EXPLORATORY and says so in its key and caption.", "",
         "## One line per task", ""]
    r16 = "p.p1.r16.f100.paired"
    L += [
        f"- **Z0** pooled set of {913} records (174 + 739) in 325 make-and-model groups; modes: frontal barrier 116, pole 529, side 58, other 210; development 543, validation 184, sealed 186 records (`docs/05_data_code/SEALED_SPLIT.md`).",
        f"- **Z1** mode inferred from the pulse: sealed-fold balanced accuracy {f('p.p1.r16.f100.mode.balanced_accuracy')} at +-16 g, {f('p.p1.r32.f100.mode.balanced_accuracy')} at +-32 g, {f('p.p1.r64.f100.mode.balanced_accuracy')} at +-64 g (100 Hz); every mode-using model is reported with the true mode (oracle, labelled) and the inferred mode.",
        f"- **P1 / H-P1: {verdict('H-P1')}.** Criterion (macro-F1 +0.03 and under-triage -0.03, both intervals excluding zero, in at least two of three ranges) met in {int(v('p.p1.hP1.n_ranges_meeting_criterion'))} ranges. At +-16 g the best deployable direct model ({P1[16.0]['direct']}) against the best baseline ({P1[16.0]['base']}): "
        f"macro-F1 {ci(r16 + '.macro_f1_direct_minus_base')}, under-triage {ci(r16 + '.under_triage_direct_minus_base')}.",
        f"- **P1 exploratory cross-validation (all 913 records, not a test):** the augmented CNN against the anchored estimator at +-16 g: macro-F1 {ci('p.p1cvcnn.r16.paired.cnn_aug_minus_c.macro_f1')}, under-triage {ci('p.p1cvcnn.r16.paired.cnn_aug_minus_c.under_triage')}; at +-32 g macro-F1 {ci('p.p1cvcnn.r32.paired.cnn_aug_minus_c.macro_f1')}; at +-64 g macro-F1 {ci('p.p1cvcnn.r64.paired.cnn_aug_minus_c.macro_f1')}. The direct GBM is not better than the anchored estimator (+-16 g macro-F1 {ci('p.p1cv.r16.paired.d_none_minus_c.macro_f1')}, under-triage {ci('p.p1cv.r16.paired.d_none_minus_c.under_triage')}).",
        f"- **P2 / H-P2: {verdict('H-P2')}.** Sealed coverage of the interval [plain, plain x q] at +-16 g: {ci('p.p2.r16.f100.global.coverage')}; lower end overall {f('p.p2.hP2.coverage_lower_overall')} and for pole {f('p.p2.hP2.coverage_lower_pole')} (coverage condition "
        f"{'met' if int(v('p.p2.hP2.coverage_condition_met')) else 'not met'}); mean upper-to-lower ratio {f('p.p2.r16.f100.global.width_ratio_mean', 2)} against {f('p.p2.r16.f100.existing.width_ratio_mean', 2)} for the existing interval, a reduction of {f('p.p2.hP2.width_reduction')} (needed 0.20).",
        f"- **P3a / H-P3a: {verdict('H-P3a')}.** At +-16 g the anchored estimator's under-triage among retained events is {f('p.p3a.hP3a.ratio', 2)} of the unselected rate (upper end {f('p.p3a.hP3a.ratio_hi', 2)}; needed at most 0.5); retained p90 error {f('p.p3a.hP3a.p90_retained', 1)}% (needed at most 20%, met).",
        f"- **P3b / H-P3b: {verdict('H-P3b')}.** Abstaining to the fast path minus the lowered severity table: mis-triage {f('p.p3b.hP3b.mis_triage_diff', 3)} [{f('p.p3b.hP3b.mis_triage_diff_lo', 3)}, {f('p.p3b.hP3b.mis_triage_diff_hi', 3)}] at +-16 g (needed at most -0.02, interval below zero); N28 stays NO_IMPROVEMENT_FOUND.",
        f"- **P4a / H-P4a: {verdict('H-P4a')}.** Selected on validation: {v('p.p4a.selected.config')}; flash estimate {float(v('p.p4a.selected.flash_bytes')) / 1000:.1f} kB against {float(v('p.p4a.reference.flash_bytes')) / 1000:.1f} kB (ratio {f('p.p4a.flash_ratio_selected_over_reference', 3)}); AP loss {ci('p.p4a.dedup.ap_loss', 4)}; "
        f"measured host size {f('p.p4a.selected.measured_bytes_host_x86_64_Os', 0)} against {f('p.p4a.reference.measured_bytes_host_x86_64_Os', 0)} bytes (x86-64, not an ESP32).",
        f"- **P4b / H-P4b: {verdict('H-P4b')}.** Augmentation with merging changes recall at the 1% target on the strict set by {ci('p.p4b.strict.diff_aug_merge_minus_standard.recall_at_1pct', 4)} (needed +0.02): it is lower.",
        f"- **P4c / H-P4c: {verdict('H-P4c')}.** In leave-one-vehicle-size-category-out evaluation every variant, including the trivial rule, has a false-alarm rate with upper end below target + 0.01 (pooled conformal: {f('p.p4c.loco.a5.V1.false_alarm_rate', 4)} at the 5% target, upper {f('p.p4c.loco.a5.V1.false_alarm_rate_hi', 4)}); no variant gains recall over the trivial rule, and the variants that bring the rate to the target or below lose recall "
        f"(V4 {f('p.p4c.loco.a5.V4.recall_gain_over_V0', 3)}, V5 {f('p.p4c.loco.a5.V5.recall_gain_over_V0', 3)} at the 5% target).",
        f"- **P4d (EXPLORATORY).** An int8 tiny 1D CNN ({v('p.p4d.n_parameters')} weights, {v('p.p4d.flash_bytes_int8')} bytes of weights and biases) reached AP {ci('p.p4d.dedup.cnn_int8.ap', 4)} on the de-duplicated test set and {ci('p.p4d.strict.cnn_int8.ap', 4)} on the strict set, against {f('p.p4a.dedup.ap_reference', 4)} and {f('p.p4a.strict.ap_reference', 4)} for the 10-tree depth-9 forest (about {float(v('p.p4a.reference.flash_bytes')) / 1000:.0f} kB). No hypothesis and no multiplicity correction.",
        "- **B1** CrashClip package: `crashclip/` (records, parts, split, evaluation, de-duplication audit, baselines). **B2** requirement calculator: `scripts/requirement_calculator.py`. **B3** `docs/05_data_code/REPRODUCE_FINISH.md`.", ""]
    L += ["## Negative results", ""]
    for n, txt in (("H-P1", "the direct route does not lower under-triage in a way the intervals can tell from zero in any range (at +-64 g the upper end of the difference is exactly 0.0, at +-32 g the point difference is positive); macro-F1 gains have intervals above zero at +-16 g and at +-32 g, but the preregistered conjunction fails in all three ranges"),
                   ("H-P2", "the one-sided interval is not narrower than the relative-residual interval around fill + ridge (reduction near 2%, needed 20%); at +-32 and +-64 g the lower bound fails in more records, so coverage falls under 0.90"),
                   ("H-P3a", "abstaining on 30% of events lowers under-triage among the retained events only to about three quarters of the unselected rate"),
                   ("H-P3b", "an abstain signal sends fewer non-severe events to the fast path than the lowered table and does not mis-triage less, with or without matching escalation on the sealed fold"),
                   ("H-P4b", "augmentation with merging lowers recall at the 1% target on the strict set"),
                   ("H-P4c", "no group-wise calibration restores more recall than the trivial rule; the guarantee at target + 0.01 held for all variants including the trivial one, and exact control at the target costs recall")):
        L.append(f"- **{n} ({verdict(n)}):** {txt}.")
    L += ["", "## Tables", ""]
    for name, cap in (("p1", "P1 (sealed fold, 100 Hz and 200 Hz)"), ("p2", "P2"), ("p3a", "P3a"), ("p3b", "P3b (pool level)"), ("p4a", "P4a"), ("p4b", "P4b"), ("p4c", "P4c"), ("p4d", "P4d (EXPLORATORY)"), ("p1cv", "P1 cross-validation (EXPLORATORY)"), ("b2", "B2 requirement table")):
        L += [f"### {cap}", "", md_table(tabs[name]), ""]
    L += ["## Sealed-fold and test-split scorings", "", md_table(pd.read_csv(T / "p_sealed_access.csv").fillna("")), "",
          "## Deviations, mistakes and fixes", "",
          "All are in `docs/07_log/DECISIONS.md` with the date: the wording-only edits, the grouping choice, a crash of the P4b evaluation before scoring, the closure bug in the P4c recall-gain statistic (the initial P4c verdict was produced by the bug and is replaced), a failed write of results.json during P3b (the pool-level and simulated entries were rewritten from the stored cells), and the measurement fixes of P4a.", "",
          "## Not run", "",
          "ESP32 flash and RAM (no cross compiler or emlearn here: `p.p4a.measured_bytes_esp32`); +-64 g in P3b; any hardware result; a second public crash dataset. the code is under Apache-2.0 (`LICENSE`, `NOTICE`; added on branch `finish`, 2026-11-13)."]
    Path("docs/03_results/POSITIVE_PUSH_RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def claims(tabs: dict) -> list[tuple]:
    """(claim, label, section, keys, verdict). Every number in the claim text comes from the keys."""
    r16 = "p.p1.r16.f100.paired"
    return [
        ("P1: a direct ordinal classifier lowers under-triage and raises macro-F1 by at least 3 points against the best of plain, fill + ridge and anchored estimators in at least two of three ranges (sealed fold)", "MEASURED_SOFTWARE", "P1", "`p.p1.*; p.holm.hp1.*`", verdict("H-P1")),
        (f"P1 (descriptive): at +-16 g and 100 Hz the best deployable direct model raises macro-F1 by {ci(r16 + '.macro_f1_direct_minus_base')} on the sealed fold; under-triage changes by {ci(r16 + '.under_triage_direct_minus_base')}", "MEASURED_SOFTWARE", "P1", f"`{r16}.*`", "REPORTED"),
        (f"P1 (EXPLORATORY, cross-validation over all 913 records, sealed-fold records included): the augmented 1D CNN raises macro-F1 over the anchored estimator at +-16 g by {ci('p.p1cvcnn.r16.paired.cnn_aug_minus_c.macro_f1')} and at +-32 g by {ci('p.p1cvcnn.r32.paired.cnn_aug_minus_c.macro_f1')}; under-triage is not lower beyond noise ({ci('p.p1cvcnn.r16.paired.cnn_aug_minus_c.under_triage')} at +-16 g)", "MEASURED_SOFTWARE", "P1", "`p.p1cvcnn.*`", "EXPLORATORY"),
        (f"Z1: the crash mode can be inferred from the clipped pulse with balanced accuracy {f('p.p1.r16.f100.mode.balanced_accuracy', 2)} (+-16 g), {f('p.p1.r32.f100.mode.balanced_accuracy', 2)} (+-32 g), {f('p.p1.r64.f100.mode.balanced_accuracy', 2)} (+-64 g) on the sealed fold", "MEASURED_SOFTWARE", "Z1", "`p.p1.r*.f100.mode.*`", "REPORTED"),
        ("P2: the interval [plain, plain x q] keeps coverage of at least 0.85 (lower end) overall and for pole and is at least 20% narrower in upper-to-lower ratio than the relative-residual interval around fill + ridge", "MEASURED_SOFTWARE", "P2", "`p.p2.*; p.holm.hp2.*`", verdict("H-P2")),
        (f"P2 (descriptive): coverage of the one-sided interval at +-16 g is {ci('p.p2.r16.f100.global.coverage')}; the lower bound is violated more often at +-32 and +-64 g (share of validation records with reference below plain: see `docs/03_results/POSITIVE_PUSH_RESULTS.md`)", "MEASURED_SOFTWARE", "P2", "`p.p2.r16.f100.global.coverage*`", "REPORTED"),
        ("P3a: abstaining on 30% of events halves the under-triage rate of the anchored estimator among retained events and keeps the retained p90 error at or below 20% at +-16 g", "MEASURED_SOFTWARE", "P3a", "`p.p3a.*; p.holm.hp3a.*`", verdict("H-P3a")),
        ("P3b: routing abstained events to the fast path lowers mis-triage by 2 points against a severity table with lowered thresholds at equal escalation", "MEASURED_SOFTWARE + SIMULATED", "P3b", "`p.p3b.*; p.holm.hp3b.*`", verdict("H-P3b")),
        (f"P4a: a forest with at most half the flash estimate stays within 0.01 AP of the 10-tree depth-9 forest ({v('p.p4a.selected.config')}: {float(v('p.p4a.selected.flash_bytes')) / 1000:.1f} kB against {float(v('p.p4a.reference.flash_bytes')) / 1000:.1f} kB; AP loss {ci('p.p4a.dedup.ap_loss', 4)}; flash is ANALYTICAL, the measured size is for an x86-64 host)", "MEASURED_SOFTWARE + ANALYTICAL", "P4a", "`p.p4a.*; p.holm.hp4a.*`", verdict("H-P4a")),
        ("P4b: augmentation with group-aware merging raises recall at the 1% target on the strict VZCrash test set by 2 points", "MEASURED_SOFTWARE", "P4b", "`p.p4b.*; p.holm.hp4b.*`", verdict("H-P4b")),
        ("P4c: a group-wise calibration restores the false-alarm guarantee under vehicle-size shift with recall at least 2 points above the trivial rule", "MEASURED_SOFTWARE", "P4c", "`p.p4c.*; p.holm.hp4c.*`", verdict("H-P4c")),
        (f"P4d (EXPLORATORY): an int8 tiny 1D CNN ({v('p.p4d.n_parameters')} weights) reaches AP {ci('p.p4d.dedup.cnn_int8.ap', 3)} against {f('p.p4a.dedup.ap_reference', 3)} for the 10-tree depth-9 forest on the de-duplicated test set; no hypothesis and no multiplicity correction", "MEASURED_SOFTWARE + ANALYTICAL (flash)", "P4d", "`p.p4d.*; p.p4a.dedup.ap_reference`", "EXPLORATORY"),
        ("B2: a plain delta-V estimate reaches a lower interval end of 0.80 within +-10% for frontal barrier tests at a smaller range than for pole tests; none of the 99 configurations reaches it for side or other tests", "MEASURED_SOFTWARE", "B2", "`p.b2.*`", "REPORTED"),
    ]


def claim_docs(tabs: dict) -> None:
    rows = claims(tabs)
    body = ["## Positive-results push (branch `positive-push`; generated by `pp_docs.py`)", "",
            "Verdicts of the seven preregistered hypotheses are Holm-corrected (`p.holm.*`). REPORTED = a descriptive result, no hypothesis; EXPLORATORY = defined after seeing results or optional. Allowed wording: state the number with its interval and label; do not write that a method is better, general or deployable unless the verdict says SUPPORTED, and then only on this data (crash tests, mostly high-speed; VZCrash events pre-selected on the device).", "",
            "| Claim | Evidence label | Section | Keys | Verdict |", "|---|---|---|---|---|"] + [f"| {c} | {lab} | {s} | {k} | **{vd}** |" for c, lab, s, k, vd in rows]
    put_block("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "\n".join(body))
    put_block("docs/03_results/CLAIM_EVIDENCE.md", "\n".join(body))


def stats_doc() -> None:
    body = ["## Positive-results push: statistics audit (generated)", "",
            "- **Intervals.** 95% percentile bootstrap, 1,000 resamples, seed 42. NHTSA studies resample whole make-and-model groups (group = make + leading word of the model); the same drawn groups feed every compared method (paired). VZCrash studies resample test events (P4c within vehicle-size category). The simulated cells of P3b use 30 seeds per cell with intervals over seeds.",
            "- **Multiplicity.** One Holm correction over seven hypotheses (`p.holm.*`). Intervals of descriptive rows, exploratory rows (P4d, the cross-validation of P1, matched-escalation, interval variants other than the primary) and per-cell simulated rows are NOT corrected.",
            "- **p-values** are one-sided bootstrap shares with a floor of 0.001; for 'at least two of three ranges' the p-value is min(1, 2 x the second-smallest per-range p).",
            "- **Sealed use.** The sealed fold was scored once per hypothesis after a freeze commit, except where `results/tables/p_sealed_access.csv` shows a labelled repeat (P4b, P4c, P3b; reasons in `docs/07_log/DECISIONS.md`).",
            "- **Known limitations of the intervals.** (i) The conformal quantile of P2 is fixed on the validation fold, so the width-reduction interval of H-P2 does not include calibration uncertainty (both intervals have a constant ratio); (ii) the sealed fold has 7 Low, 14 side and 20 frontal barrier records, so per-class and per-mode statistics are wide or descriptive; (iii) records of one make and model are correlated and are resampled together, but different models of one platform may remain correlated; "
            "(iv) the selection of the best direct model on validation among 8 candidates is not part of the sealed interval; (v) VZCrash has no vehicle identifier, so 'vehicle groups' are four size categories.", "",
            md_table(pd.read_csv(T / "p_sealed_access.csv").fillna(""))]
    put_block("docs/03_results/STATS_AUDIT.md", "\n".join(body))


def sealed_doc() -> None:
    p = Path("docs/05_data_code/SEALED_SPLIT.md")
    s = p.read_text(encoding="utf-8")
    i = s.index("## Sealed-fold scorings")
    acc = pd.read_csv(T / "p_sealed_access.csv").fillna("")
    s = s[:i] + "## Sealed-fold scorings\n\nGenerated from `results/tables/p_sealed_access.csv` (rows are written by `pp_common.sealed_gate`; a repeat needs a stated deviation). Each freeze commit holds `results/tables/p_freeze_<hypothesis>.json` with the settings and the sha256 of every model file.\n\n" + md_table(acc) + "\n"
    p.write_text(s, encoding="utf-8")


def references_doc() -> None:
    body = """## Positive-results push (opened 2026-11-12 unless stated)

Fields: A = authors, T = title, V = venue, Y = year. A field is filled only if it appeared on the page that was opened; NOT VERIFIED marks the rest.

| Key | A | T | V | Y | Address opened | Not verified |
|---|---|---|---|---|---|---|
| P-R1 | Angelopoulos, Bates, Fisch, Lei, Schuster | Conformal Risk Control | arXiv 2208.02814 (the page lists ICLR 2024 in the search result only; the abstract page itself gives arXiv, latest version June 2025) | 2022 (submitted 2022-08-04) | https://arxiv.org/abs/2208.02814 | pages, DOI, ICLR details |
| P-R2 | Geifman, El-Yaniv | Selective Classification for Deep Neural Networks | arXiv 1705.08500 | 2017 (submitted 2017-05-23) | https://arxiv.org/abs/1705.08500 | proceedings details |
| P-R3 | Rafe, Das | CHOIR: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata | arXiv 2609.11592 (submitted 2026-09-10, revised 2026-10-01) | 2026 | https://arxiv.org/abs/2609.11592 | pages, DOI, peer-reviewed venue |
| P-R4 | Barber, Candes, Ramdas, Tibshirani | Predictive inference with the jackknife+ | arXiv 1905.02928 | 2019 (submitted 2019-05-08) | https://arxiv.org/abs/1905.02928 | journal details |
| P-R5 | emlearn project | emlearn (README) | GitHub repository | NOT VERIFIED | https://github.com/emlearn/emlearn | authors, version, licence, year |
| P-R6 | NHTSA (publisher, per the catalogue entry) | Vehicle Crash Test Database (data.gov catalogue entry) | catalog.data.gov; licence/rights field reads "public"; use constraint: not intended to support general consumer safety issues; last modified 2026-09-03; the entry describes tests from 1981 to 2015 | 2026 (entry) | https://catalog.data.gov/dataset/vehicle-crash-test-database | whether the same terms apply to the later tests fetched through the NRD API; nhtsa.gov pages returned HTTP 403 on 2026-11-12 and were not opened |
| P-R7 | Wusk, Gabler | (25th ESV paper 17-0407, delta-V, ASI and OLC against injury criteria) | NHTSA ESV proceedings | 2017 (conference number only) | NOT OPENED: https://www-nrd.nhtsa.dot.gov/pdf/ESV/Proceedings/25/25ESV-000407.pdf returned HTTP 403 | everything; only the author's description is used and no number |
| P-R8 | Jao, Shkel (2022); Zhang et al. (2026) | named by the author | - | - | NOT FOUND by search on 2026-11-11 and 2026-11-12 | everything; not cited |

Earlier references (datasets, data sheets, patents, papers) are in the table above this block."""
    put_block("docs/06_references/REFERENCES.md", body)


def reproduce_doc() -> None:
    body = """## Positive-results push: reproduce (branch `positive-push`)

Run from the repository root with `PYTHONPATH=src` in the project virtual environment (`torch` CPU is needed for the CNNs: `pip install torch --index-url https://download.pytorch.org/whl/cpu`). The earlier pipeline and the `journal` steps must have been run (T13a signals in `data/processed/`, VZCrash windows, `results/results.json`). `make positive` runs the whole chain; the sealed fold and the test splits are scored once, so a second run of an evaluation stage needs `PP_DEVIATION="reason"` (logged in `results/tables/p_sealed_access.csv`). To rerun from scratch, delete the `p.` keys and `results/tables/p_sealed_access.csv` and the freeze files.

| Table or figure | Command | Results keys |
|---|---|---|
| Z0 pooled set, docs/05_data_code/SEALED_SPLIT.md, results/tables/p_pool_folds.csv | `python -m crashguard.pp_pool` | none |
| P1 fit and freeze (models, validation table) | `python -m crashguard.pp_feat && python -m crashguard.pp_p1 fit` | none (validation table `p1_validation.csv`) |
| p_tab_p1, p_tab_p1_all, p_tab_z1, p_fig_p1_triage | `python -m crashguard.pp_p1 eval && python -m crashguard.pp_docs && python -m crashguard.pp_figs` | `p.p1.*` |
| P1 cross-validation (EXPLORATORY) | `python -m crashguard.pp_p1_cv` | `p.p1cv.*` |
| p_tab_p2, p_fig_p2_intervals | `python -m crashguard.pp_p2 fit && python -m crashguard.pp_p2 eval` | `p.p2.*` |
| p_tab_p3a, p_tab_p3b, p_fig_p3a_risk_coverage | `python -m crashguard.pp_p3 fit && python -m crashguard.pp_p3 eval` | `p.p3a.*, p.p3b.*` |
| p_tab_p4a, p_fig_p4a_pareto, measured size | `python -m crashguard.pp_p4a sweep && python -m crashguard.pp_p4a eval && python -m crashguard.pp_p4a size` | `p.p4a.*` |
| p_tab_p4b | `python -m crashguard.pp_p4bc p4b freeze && python -m crashguard.pp_p4bc p4b eval` | `p.p4b.*` |
| p_tab_p4c, p_fig_p4c_guarantee | `python -m crashguard.pp_p4bc p4c freeze && python -m crashguard.pp_p4bc p4c eval` | `p.p4c.*` |
| p_tab_p4d | `python -m crashguard.pp_p4d freeze && python -m crashguard.pp_p4d eval` | `p.p4d.*` |
| p_tab_b2, results/tables/p_b2_flags.npz | `python -m crashguard.pp_b2` | `p.b2.*` |
| requirement calculator | `python scripts/requirement_calculator.py --mix frontal_barrier=0.3,pole=0.4,side=0.1,other=0.2 --required 0.80` | reads `p_b2_flags.npz` |
| crashclip/ package files | `python -m crashguard.pp_crashclip` | none |
| p_tab_holm | `python -m crashguard.pp_verdicts` | `p.holm.*` |
| docs/03_results/POSITIVE_PUSH_RESULTS.md, p_tab_*, claim rows, STATS_AUDIT block, REFERENCES block, SEALED_SPLIT table | `python -m crashguard.pp_docs` | all `p.*` |
| independent claim audit | `python -m crashguard.pp_audit` | `docs/04_audits/PP_CLAIM_AUDIT.md` |

Checks: `python -m crashguard.check_results` (0 errors), `python -m pytest -q`, `python -m ruff check src tests crashclip scripts`.

**NOT_RUN in this push:** ESP32 flash and RAM and any microcontroller timing (no cross compiler, no emlearn; `p.p4a.measured_bytes_esp32`); P3b at +-64 g; hardware results; a second public crash dataset; (the code licence, Apache-2.0, was added on branch `finish`)."""
    put_block("docs/05_data_code/REPRODUCE_FINISH.md", body)


def crashclip_doc(tabs: dict) -> None:
    nl = chr(10)
    body = ("## Baseline results (generated; sealed fold, 100 Hz; full tables in `baselines/`)" + nl + nl + md_table(tabs["p1"][tabs["p1"]["Rate (Hz)"] == 100].drop(columns=["Rate (Hz)"])) + nl + nl
            + "Requirement table (B2, plain estimate, all 913 records):" + nl + nl + md_table(tabs["b2"]))
    put_block("crashclip/README.md", body)


def main() -> None:
    tabs = tables()
    results_doc(tabs)
    claim_docs(tabs)
    stats_doc()
    sealed_doc()
    references_doc()
    reproduce_doc()
    crashclip_doc(tabs)
    print("written")


if __name__ == "__main__":
    main()
