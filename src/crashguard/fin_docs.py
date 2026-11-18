"""Documents of the finishing branch, generated from results/results.json (no number typed): docs/03_results/NEGATIVES_REGISTER.md (B4), docs/03_results/FINISH_RESULTS.md (final summary), docs/00_overview/CLAIMS_FOR_COVER_LETTER.md (D3)."""
from __future__ import annotations

from pathlib import Path

from crashguard import fin_sim as FS

R: dict = {}


def v(key: str, f: str = "{:.3f}", default: str = "NOT_RUN") -> str:
    x = R.get(key)
    if x is None or x == "NOT_RUN":
        return default
    if isinstance(x, (int, float)):
        return f.format(x)
    return str(x)


def ci(key: str, f: str = "{:+.3f}") -> str:
    a, lo, hi = R.get(key), R.get(key + "_lo"), R.get(key + "_hi")
    if a is None or lo is None or hi is None:
        return "NOT_RUN"
    return f"{f.format(a)} [{f.format(lo)}, {f.format(hi)}]"


def verdict(name: str) -> str:
    return R.get(f"f.holm.{name}.verdict", "NOT_RUN")


def scheme() -> str:
    return "cv" if "f.f1.cv.hF1.criterion_met" in R else "sealed"


def negatives() -> str:
    rows = [
        ("N20 false-alarm control (conformal guarantee)", "Whether a conformal threshold holds the false-alarm rate at its target on the de-duplicated VZCrash test set.", "NOT SUPPORTED (earlier rounds): rate about 0.053 at the 5% target on the supplied split; at 1% it holds only at 1.96 standard errors.",
         "Validation and test are not exchangeable (inferred); vehicle-size shift breaks it by up to 8 points.", "Yes: T7 variants (NOT SUPPORTED) and P4c variants V1 to V5 (NOT SUPPORTED); F2 rerun of H-P4c NOT_RUN (see F rows).", "No vehicle identifier in VZCrash; exact control costs recall."),
        ("N28 equal-escalation test", "Whether the class-conditional upper-end policy (P3) beats the lowered-threshold table at equal escalation.", f"NO_IMPROVEMENT_FOUND: pool-level mis-triage P3 minus P1e at +-16 g {ci('t1.r16.mis_triage_p3_minus_p1e')} (interval includes zero); decision rule not met at +-16, +-32, +-64 g.",
         "A lowered table reaches the same escalation; the interval adds nothing over it (as found; the cause is not tested further).", f"Yes: B2 (P1+, {verdict('hb2')}), F3 with improved estimates (H-F3a {verdict('hf3a')}).", "Whether any estimate quality makes the interval pay."),
        ("H-P1 (direct classifier)", "Direct ordinal classifier and 1D CNN against the anchored estimator on the sealed fold.", f"NOT SUPPORTED: macro-F1 difference at +-16 g {ci('p.p1.r16.f100.paired.macro_f1_direct_minus_base')}; criterion met in 0 of 3 ranges.",
         "Small sealed fold (186 records, 7 Low) and 913 real pulses (inferred).", f"Yes: F1 with real plus synthetic training, original criterion (H-F1 {verdict('hf1')}); r = 0 control and best ratio are in `f.f1.*`.", "Whether a larger real set would change it."),
        ("H-P2 (anchored interval)", "Whether [plain, plain x q] is narrower than the relative-residual interval at 90% coverage.", f"NOT SUPPORTED: coverage {v('p.p2.r16.f100.global.coverage')} (condition met) but width ratio reduction {v('p.p2.r16.f100.global.width_ratio_reduction_vs_existing')} against 0.20 needed.",
         "A one-sided bound from the plain estimate cannot be much narrower when the plain estimate under-reads by a factor of about 2 (inferred).", f"Yes: F1 (H-F1b {verdict('hf1b')}).", "A narrower interval with 90% coverage."),
        ("H-P3a (abstention)", "Whether abstaining on 30% of events halves under-triage among retained events.", f"NOT SUPPORTED: ratio {v('p.p3a.hP3a.ratio')} (upper end {v('p.p3a.hP3a.ratio_hi')}), needed at most 0.5; retained p90 error {v('p.p3a.hP3a.p90_retained', '{:.1f}')}%.", "The reliability score ranks errors weakly (inferred).", f"Yes: F1 (H-F1c {verdict('hf1c')}).", "A better reliability score."),
        ("H-P3b (abstain as escalation signal)", "Whether abstain routing mis-triages less than the lowered table at equal escalation.", f"NOT SUPPORTED: mis-triage A {v('p.p3b.r16.A.mis_triage')} against lowered table {v('p.p3b.r16.P1e.mis_triage')}.", "The abstain signal is a noisier escalation signal than lowering thresholds (inferred).", f"Yes: F3 (H-F3b {verdict('hf3b')}).", "Same as above."),
        ("H-P4b (augmentation)", "Whether augmentation with merging raises recall at the 1% target on the strict set by 0.02.", f"NOT SUPPORTED: {ci('p.p4b.strict.diff_aug_merge_minus_standard.recall_at_1pct', '{:+.4f}')}.", "Augmented crash copies shift the score distribution against the validation threshold (inferred).", f"Yes: F2 with surrogate windows (H-F2a {verdict('hf2a')}).", "Whether better surrogate windows help."),
        ("H-P4c (calibration under vehicle-size shift)", "Whether group-wise calibration beats the trivial rule by 0.02 recall with the rate held.", "NOT SUPPORTED: no variant gains recall over the trivial rule; variants that bring the rate to the target lose recall (see docs/03_results/POSITIVE_PUSH_RESULTS.md).", "Structure of the vehicle-size categories (inferred).", f"Not re-run: H-F2f {verdict('hf2f')}.", "Whole item open."),
        ("H-X1 (fixed-point forest)", "16-bit forest loses at most 0.005 AP and cuts flash by 30%.", "NOT SUPPORTED: the AP clause held (raw p 0.001); the flash clause fails by arithmetic (22.2% for 16-bit thresholds in the primary layout).", "Arithmetic of the node layout.", f"Yes: F2 AP clause with surrogate training (H-F2d {verdict('hf2d')}); the flash clause cannot change.", "A layout with a larger saving (P4a found one, +37% flash by fewer trees)."),
        ("H-X2 (trigger cascade)", "Whether a cheap cascade raises the crash pass share by 2 points at equal non-crash trigger rate.", f"NOT SUPPORTED: gain {v('x.x2.hX2.gain', '{:.3f}')}.", "Closer to N15 (c), which also found nothing (stated in the preregistration).", f"Not re-run: H-F2c {verdict('hf2c')} (surrogate windows are trigger-aligned).", "A record-level surrogate would be needed."),
        ("H-X3 (group-aware training)", "Whether down-weighting near-identical training windows raises recall at the 1% target by 1 point.", f"NOT SUPPORTED: gain {v('x.x3.hX3.gain', '{:+.4f}')} (lower end {v('x.x3.hX3.gain_lo', '{:+.4f}')}).", "Near-duplicates are few among training windows relative to the whole set (inferred).", f"Yes: F2 (H-F2b {verdict('hf2b')}).", "-"),
        ("H-X5 (rank preservation)", "Spearman correlation of fill + ridge delta-V with the reference at least 0.90.", f"NOT SUPPORTED: {ci('x.x5.hX5.rho_fillridge', '{:.3f}')}; plain estimate {v('x.x5.hX5.rho_plain')}.", "The fill + ridge correction adds noise to the ranking (inferred).", f"Not re-run: H-F1e {verdict('hf1e')}.", "Whole item open."),
        ("H-X6 (anchored estimator)", "p90 error of the anchored estimator against fill + ridge.", "SUPPORTED on split R in the original; the gain has its interval above zero on split A only among G, A, O (so it failed on G and O).", "The estimator over-corrects tests where plain already exceeds the reference (as noted).", f"Not re-run: H-F1d {verdict('hf1d')}.", "G and O."),
        ("H-X7 (two-part fusion)", "Whether a two-part pair reaches 0.80 where neither part alone does.", f"NOT SUPPORTED: {v('x.x7.hX7.n_counting', '{:.0f}')} of {v('x.x7.hX7.n_pairs_rules', '{:.0f}')} pair-rule combinations count.", "Mounting error and synchronisation are not modelled (the test favours the pair); pole and side modes dominate the shortfall (inferred).", "No.", "-"),
        ("H-X8 (sequential rule)", "Whether a sequential rule decides 100 ms earlier than early exit at equal recall.", f"NOT SUPPORTED: median time gain {v('x.x8.hX8.a1.time_gain_ms', '{:.0f}')} ms at the 1% target (lower end {v('x.x8.hX8.a1.time_gain_lo', '{:.0f}')} ms), but at the 5% target the sequential rule is later (median difference {v('x.x8.a5.dedup.diff.time_early_minus_seq_median', '{:.0f}')} ms, early exit minus sequential).", "The 5% target favours the early-exit rule (as measured); why is not tested.", f"Not re-run: H-F2e {verdict('hf2e')}.", "-"),
        ("T4 single-car loss case", "Whether the SCT policy reaches the base as often as the table for a single car at 60% loss.", "PARTIAL (earlier rounds).", "Spacing of retries against loss (inferred).", "Quick retries repair it (earlier round).", "-"),
        ("P3b (as listed above under H-P3b)", "-", "-", "-", "-", "-"),
        ("B2: P1+ against P0 (this round)", "Flash and hold on the severity table.", f"{verdict('hb2')}: {v('f.b2.hB2.n_cells_gain5', '{:.0f}')} of {v('f.b2.hB2.n_cells', '{:.0f}')} held-out cells gain 5 points; {v('f.b2.hB2.n_cells_lose2', '{:.0f}')} loses by more than 2.", "Gain of the full fast path comes from more than flash and hold (inferred: P3 is higher in most cells).", "-", "Which of the remaining parts (upper-end class, pre-emption, reserved share) matter is only partly separated in G2."),
        ("H-G3a slotted fast path (this round)", "Reserved slots for Severe and Critical alerts against pure ALOHA.", f"{verdict('hg3a')}: all {v('f.g.g3.hG3a.n_cells_lose2', '{:.0f}')} of 16 held-out cells lose more than 2 points (pooled {v('f.g.g3.hG3a.pooled_diff.reach10_critical', '{:+.3f}')}).", "8 slots per 30 s frame for a burst of 30 cars (inferred; slot sweep in G5).", "Not tuned (preregistered parameters).", "Other slot structures were not tested."),
        ("H-G3b listen-before-talk (this round)", "LBT for the fast path.", f"{verdict('hg3b')}: {v('f.g.g3.hG3b.n_cells_gain5', '{:.0f}')} of 16 cells gain 5 points; pooled {v('f.g.g3.hG3b.pooled_diff.reach10_critical', '{:+.3f}')}.", "Hidden terminals (sensing probability 0.7, assumed) and the short backoff (inferred).", "-", "433 MHz regulatory status UNVERIFIED."),
        ("H-G3c V2V relay (this round)", "One repeat by a neighbour when the ACK is missing.", f"{verdict('hg3c')}: pooled {v('f.g.g3.hG3c.pooled_diff.reach30_rx_critical', '{:+.3f}')} on reception within 30 s in the 8 cells with loss 40%.", "The relayed copy meets the same loss and collisions as the sender's own retries (inferred).", "-", "-"),
    ]
    t = ["# Negatives register", "", "Generated by `crashguard.fin_docs` from `results/results.json`. One row per negative result. **No original verdict is removed or softened.** Causes marked (inferred) are not tested. A fix is a revised design tested after seeing the negative; it is reported next to the original, never in place of it.", "",
         "| Item | What was tested | Original verdict | Suspected cause | Fix tried and outcome | What remains open |", "|---|---|---|---|---|---|"]
    for r in rows:
        if r[1] == "-" and r[2] == "-":
            continue
        t.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
    t.append("")
    t.append("Layer findings of block G that are negative are the three mechanism rows above and the single-assumption flips in `f.g.g5.flips.*`; the G7 summary is in `docs/03_results/FINISH_RESULTS.md`.")
    return "\n".join(t) + "\n"


def finish() -> str:
    S = scheme()
    L = ["# Finishing round: results (generated)", "", "Branch `finish` from tag `positive-push-v1`; software only; every number read from `results/results.json` by `crashguard.fin_docs`. Labels: MEASURED_SOFTWARE, SIMULATED, ANALYTICAL, NOT_RUN; F rows are EXPLORATORY-REVISED. Design: `docs/02_preregistration/PREREGISTRATION_V5.md` (committed before Blocks B, C, F, G ran; addendum 1 lists the deviations).", "",
         "## Verdicts (Holm over the 18 preregistered hypotheses)", "", "| Hypothesis | Original / what | Raw p | Holm p | Verdict |", "|---|---|---|---|---|"]
    from crashguard.fin_verdicts import HYP
    for name, desc, label, _stem in HYP:
        k = name.replace("-", "").lower()
        L.append(f"| {name} | {desc} ({label}) | {v(f'f.holm.{k}.p_raw')} | {v(f'f.holm.{k}.p_holm')} | {verdict(k)} |")
    L += ["", "## One line per task", "",
          "- **A1** Apache-2.0 licence, NOTICE, CITATION.cff, .zenodo.json; VZCrash statement (CC BY-NC 4.0, revision 42e1482d005c0e545379d6cfa4939486c9fe4249) in every document. **A2** `docs/04_audits/PREREG_V4_AUDIT.md`: no verdict flips. **A3** `docs/07_log/NOT_RUN.md`. **A4** `release/vzcrash_audit_for_authors/` agrees with the package sent.",
          f"- **B1** ({'ANALYTICAL'}) design: {v('f.b1.ext.design.states', '{:,.0f}')} states, C3 fails; pending CANCEL: {v('f.b1.ext.pending_cancel.states', '{:,.0f}')} states, all {v('f.b1.ext.pending_cancel.properties_checked', '{:.0f}')} properties hold; attack cases {v('f.b1.attacks.original_match_with_change', '{:.0f}')} of {v('f.b1.attacks.original_cases', '{:.0f}')} original and {v('f.b1.attacks.extra_match_with_change', '{:.0f}')} of {v('f.b1.attacks.extra_cases', '{:.0f}')} extra (X06 changes by design). Checks the model, not the implementation.",
          f"- **B2** (SIMULATED) H-B2 {verdict('hb2')}: {v('f.b2.hB2.n_cells_gain5', '{:.0f}')} of {v('f.b2.hB2.n_cells', '{:.0f}')} cells gain 5 points, {v('f.b2.hB2.n_cells_lose2', '{:.0f}')} lose more than 2; design grid {v('f.b2.design.diff.P1+_minus_P0.reach10_critical.n_cells_gain5', '{:.0f}')} of {v('f.b2.design.diff.P1+_minus_P0.reach10_critical.n_cells', '{:.0f}')}.",
          f"- **B3** airtime against the formula as transcribed (Semtech document not opened): max difference {v('f.b3.airtime.max_abs_diff_ms', '{:.1e}')} ms; collision probability against 1 - exp(-2G): largest error {v('f.b3.collision.max_abs_err_vs_aloha')} (against the finite-population form {v('f.b3.collision.max_abs_err_vs_finite')}); duty violations 0 in {v('f.b2.runs', '{:,.0f}')} (B2) and {v('f.g.runs', '{:,.0f}')} (G) runs: {v('f.b2.runs_exceeding_duty', '{:.0f}')} and {v('f.g.runs_exceeding_duty', '{:.0f}')}.",
          "- **B4** `docs/03_results/NEGATIVES_REGISTER.md`.",
          f"- **C** (SIMULATED stress test) fidelity passes: {v('f.c.fidelity.modes_passed')}; H-C3 {verdict('hc3')} (frontal barrier: synthetic {v('f.c.grid.frontal_barrier.synthetic_smallest_range', '{:.0f}')} g, real {v('f.c.grid.frontal_barrier.real_smallest_range', '{:.0f}')} g); extension: log-peak shift +0.4 gives {v('f.c.sens.shift0.4.frontal_barrier.smallest_range', '{:.0f}')} g for frontal barrier.",
          f"- **F0** surrogate: {v('f.f2.surrogate.features_matched', '{:.0f}')} of 28 class x feature marginals matched; nearest-neighbour copies {v('f.f2.surrogate.nn_copies', '{:.0f}')}.",
          f"- **F1** ({S}) H-F1 {verdict('hf1')} ({v(f'f.f1.{S}.hF1.n_ranges_met', '{:.0f}')} of 3 ranges); H-F1b {verdict('hf1b')}; H-F1c {verdict('hf1c')}; H-F1d and H-F1e NOT_RUN.",
          f"- **F2** H-F2a {verdict('hf2a')} (gain {ci('f.f2.hF2a.gain', '{:+.4f}')}); H-F2b {verdict('hf2b')} (gain {v('f.f2.hF2b.gain', '{:+.4f}')}); H-F2d {verdict('hf2d')}; H-F2c, H-F2e, H-F2f NOT_RUN.",
          f"- **F3** H-F3a {verdict('hf3a')}; H-F3b {verdict('hf3b')}.",
          f"- **G** baseline on DESIGN: {v('f.g.baseline_policy_chosen_on_design')}; H-G3a {verdict('hg3a')}, H-G3b {verdict('hg3b')}, H-G3c {verdict('hg3c')}; held-out regime map: {v('f.g.g4.held.n_ties', '{:.0f}')} ties of 16 cells, P3 wins {v('f.g.g4.held.p3_wins_cells', '{:.0f}')}.", ""]
    L += ["## F4 summary (original verdict, real-only rerun, real plus synthetic rerun, TSTR)", "",
          "| Hypothesis | Original verdict | Real-only rerun (r = 0) | Real plus synthetic, best ratio [interval] | TSTR | New verdict | Changed? |", "|---|---|---|---|---|---|---|"]
    S_ = S
    L.append(f"| H-F1 (H-P1), +-16 g, macro-F1 difference | NOT SUPPORTED ({ci('p.p1.r16.f100.paired.macro_f1_direct_minus_base')}) | {ci(f'f.f1.{S_}.r16.control_r0.macro_f1_diff')} | {ci(f'f.f1.{S_}.r16.hF1.macro_f1_diff')} (ratio {v(f'f.f1.{S_}.r16.chosen_ratio_dirb')}) | macro-F1 {v(f'f.f1.{S_}.r16.tstr.fe.macro_f1')} (CNN) | {verdict('hf1')} | {'no' if verdict('hf1') == 'NOT SUPPORTED' else 'yes'} |")
    L.append(f"| H-F1b (H-P2) | NOT SUPPORTED (reduction {v('p.p2.r16.f100.global.width_ratio_reduction_vs_existing')}) | see f.f1.{S_}.hF1b | reduction {ci(f'f.f1.{S_}.hF1b.width_ratio_reduction')} | - | {verdict('hf1b')} | {'no' if verdict('hf1b') == 'NOT SUPPORTED' else 'yes'} |")
    L.append(f"| H-F1c (H-P3a) | NOT SUPPORTED (ratio {v('p.p3a.hP3a.ratio')}) | see f.f1.{S_}.hF1c | ratio {ci(f'f.f1.{S_}.hF1c.under_triage_ratio', '{:.3f}')} | anchored TSTR p90 {v(f'f.f1.{S_}.r16.tstr.anchored.p90_abs_error_pct', '{:.1f}')}% | {verdict('hf1c')} | {'no' if verdict('hf1c') == 'NOT SUPPORTED' else 'yes'} |")
    L.append(f"| H-F2a (H-P4b) | NOT SUPPORTED ({v('p.p4b.strict.diff_aug_merge_minus_standard.recall_at_1pct', '{:+.4f}')}) | r = 0 is the control | {ci('f.f2.hF2a.gain', '{:+.4f}')} (ratio {v('f.f2.best_ratio.std')}) | AP {v('f.f2.test.dedup.tstr.ap', '{:.3f}')} | {verdict('hf2a')} | {'no' if verdict('hf2a') == 'NOT SUPPORTED' else 'yes'} |")
    L.append(f"| H-F2b (H-X3) | NOT SUPPORTED ({v('x.x3.hX3.gain', '{:+.4f}')}) | {ci('f.f2.control_gw_r0_minus_std_r0.recall_at_1pct', '{:+.4f}')} | {ci('f.f2.hF2b.gain', '{:+.4f}')} (ratio {v('f.f2.best_ratio.gw')}) | - | {verdict('hf2b')} | {'no' if verdict('hf2b') == 'NOT SUPPORTED' else 'yes'} |")
    L.append(f"| H-F2d (H-X1) | NOT SUPPORTED (flash clause) | AP loss {v('f.f2.hF2d.ap_loss_r0', '{:+.4f}')} | AP loss {v('f.f2.hF2d.ap_loss_best', '{:+.4f}')} (upper {v('f.f2.hF2d.ap_loss_best_hi', '{:+.4f}')}) | - | {verdict('hf2d')} | no (flash clause is arithmetic) |")
    L.append("")
    L.append(f"The F1 rows use the nested cross-validation (main estimate). The sealed-fold rerun, scored once and labelled revised after the negative, gives for H-F1 at +-16 g: ratio 0 control {ci('f.f1.sealed.r16.control_r0.macro_f1_diff')} (the original result, as it must), best ratio {ci('f.f1.sealed.r16.hF1.macro_f1_diff')}; criterion met in {v('f.f1.sealed.hF1.n_ranges_met', '{:.0f}')} of 3 ranges. In the cross-validation the best-ratio model minus the ratio-0 control is {R['f.f1.cv.r16.hF1.macro_f1_diff'] - R['f.f1.cv.r16.control_r0.macro_f1_diff']:+.3f} in macro-F1 at +-16 g (a difference of two point estimates, no interval); in the sealed fold it is {R['f.f1.sealed.r16.hF1.macro_f1_diff'] - R['f.f1.sealed.r16.control_r0.macro_f1_diff']:+.3f}. Neither version meets the original criterion.")
    L.append("")
    L.append("If no verdict changes, that is a reportable finding about the limits of synthetic augmentation in this setting; the table above shows whether it applies.")
    return "\n".join(L) + "\n"


def claims() -> str:
    C = [("A fast path built from flash and hold alone on the severity table (P1+) does not beat fixed retries by 5 points in at least 60% of held-out cells.", "SIMULATED", "Fast-path design", f"H-B2 {verdict('hb2')}"),
         ("The bounded model check finds a CANCEL-reordering counterexample in the design; remembering an unseen CANCEL removes it within the bounds.", "ANALYTICAL (model, not implementation)", "Protocol check", "holds within the bounds"),
         ("On frontal barrier pulses that passed the fidelity check, a synthetic stress test gives the same smallest sensor range as the real pooled records.", "SIMULATED (stress test)", "Synthetic stress test", f"H-C3 {verdict('hc3')} (one mode)"),
         ("Real plus synthetic training data does not change the verdicts of the failed NHTSA-side hypotheses that were rerun.", "MEASURED_SOFTWARE, EXPLORATORY-REVISED", "Negative results", f"H-F1 {verdict('hf1')}, H-F1b {verdict('hf1b')}, H-F1c {verdict('hf1c')}"),
         ("Real plus surrogate training windows does not change the verdicts of H-P4b, H-X3, H-X1 on VZCrash.", "MEASURED_SOFTWARE, EXPLORATORY-REVISED", "Negative results", f"H-F2a {verdict('hf2a')}, H-F2b {verdict('hf2b')}, H-F2d {verdict('hf2d')}"),
         ("Under the stated assumptions, a slotted fast path, listen-before-talk and a V2V relay do not raise critical reach by 5 points in at least 60% of held-out cells.", "SIMULATED", "Protocol layers study", f"H-G3a {verdict('hg3a')}, H-G3b {verdict('hg3b')}, H-G3c {verdict('hg3c')}"),
         ("In the simulated protocol stack the largest single-layer effects on critical reach are capture, hold and SF raise; the effect of tag length 4 against 16 bytes is about 2 points.", "SIMULATED", "Protocol layers study", "descriptive; held-out grid; keys f.g.g2.held.*"),
         ("The VZCrash release contains 217 cross-split identical-array groups; the primary and strict test sets follow from them.", "MEASURED_SOFTWARE", "Near-duplicate audit", "earlier rounds; unchanged"),
         ("A 16-bit 8-tree depth-8 forest keeps AP within 0.0036 of the reference at 37% of its flash estimate.", "MEASURED_SOFTWARE; flash ANALYTICAL", "Compact detector", "H-P4a SUPPORTED (earlier round)")]
    t = ["# Claims for the cover letter (generated; each claim, evidence label, section, verdict)", "", "No claim is stronger than its label. Simulated and synthetic items are statements under stated assumptions. No hardware or field claim is made.", "", "| Claim | Evidence label | Section | Verdict |", "|---|---|---|---|"]
    t += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in C]
    return "\n".join(t) + "\n"


def main() -> None:
    global R
    R = FS.results_map()
    Path("docs/03_results/NEGATIVES_REGISTER.md").write_text(negatives(), encoding="utf-8")
    Path("docs/03_results/FINISH_RESULTS.md").write_text(finish(), encoding="utf-8")
    Path("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md").write_text(claims(), encoding="utf-8")


if __name__ == "__main__":
    main()
