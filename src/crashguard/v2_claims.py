"""Claim rows and allowed wording for the v2 studies (docs/02_preregistration/PREREGISTRATION_V2.md), added to the claim table of docs/03_results/CLAIM_EVIDENCE.md by ``claim_table``. Verdicts are read from ``v2.holm.verdict.*``; the wording
is generated from results.json so that no number is typed here."""
from __future__ import annotations

from crashguard.report import Res

LABEL = {"H-A1": "MEASURED_SOFTWARE", "H-A2": "MEASURED_SOFTWARE", "H-A3": "MEASURED_SOFTWARE", "H-B1": "SIMULATED", "H-B2": "SIMULATED", "H-B3": "SIMULATED", "H-D1": "MEASURED_SOFTWARE", "H-D2": "MEASURED_SOFTWARE",
         "H-E1": "SIMULATED", "H-E2": "ANALYTICAL", "H-F1": "ANALYTICAL", "H-F2": "SIMULATED"}
CLAIM = {
    "H-A1": "v2 A: a quantile boosting model on clipping descriptors and pulse-family features lowers the 90th-percentile delta-V error against fill + ridge at +-16 g (preregistered, Holm-corrected)",
    "H-A2": "v2 A: adaptive conformal intervals are narrower than plain split-conformal intervals where clipping is mild, with coverage within 2 points of 90%",
    "H-A3": "v2 A: the deterministic bounds (plain estimate; pulse-family upper bound) contain the reference delta-V for at least 90% of tests at +-16 g",
    "H-B1": "v2 B: a load-adaptive escalation variant raises critical reach within 10 s by 3 points over a matched fixed lowered-threshold rule in most burst cells",
    "H-B2": "v2 B: no adaptive variant harms steady cells or the single-car 60% loss case by more than 2 points",
    "H-B3": "v2 B: the per-car token bucket achieves at least 80% of the best variant's gain",
    "H-D1": "v2 D: the clip-onset flag detects Severe or Critical events at least 100 ms before the full-pulse decision with no more under-triage than the early-exit analogue",
    "H-D2": "v2 D: the clip-onset flag flags fewer than 10% of non-severe events",
    "H-E1": "v2 E: a 4-byte tag raises critical reach within 10 s by 2 points over an 8-byte tag in the burst cells",
    "H-E2": "v2 E: an 8-byte tag keeps the duty-capped forgery work factor above 2^32 attempts",
    "H-F1": "v2 F: the model-optimal hold of Critical alerts is zero for every cost ratio in the grid",
    "H-F2": "v2 F: a 2 s hold of Severe alerts cuts false Severe alerts reaching the base by at least 20% with no significant loss in critical reach",
}
SOURCE = {"H-A1": "v2.a.hA1.*", "H-A2": "v2.a.hA2.*, v2.a.a5.*", "H-A3": "v2.a.hA3.*, v2.a.a2.*", "H-B1": "v2.b.hB1.*, v2.b.gain.*", "H-B2": "v2.b.hB2.*", "H-B3": "v2.b.hB3.*", "H-D1": "v2.d.hD1.*", "H-D2": "v2.d.hD2.*",
          "H-E1": "v2.e.hE1.*", "H-E2": "v2.e.hE2.*, v2.e.forgery.*", "H-F1": "v2.f.hF1.*, v2.f.opt.*", "H-F2": "v2.f.hF2.*"}
CMD = {"H-A1": "python -m crashguard.v2_a_study", "H-A2": "python -m crashguard.v2_a_study", "H-A3": "python -m crashguard.v2_a_study", "H-B1": "python -m crashguard.v2_b_study", "H-B2": "python -m crashguard.v2_b_study",
       "H-B3": "python -m crashguard.v2_b_study", "H-D1": "python -m crashguard.v2_d_study", "H-D2": "python -m crashguard.v2_d_study", "H-E1": "python -m crashguard.v2_e_study", "H-E2": "python -m crashguard.v2_e_study",
       "H-F1": "python -m crashguard.v2_f_study", "H-F2": "python -m crashguard.v2_f_study"}


def v2_rows(r: Res) -> list[tuple]:
    rows = []
    for h in LABEL:
        k = f"v2.holm.verdict.{h}"
        if k not in r.r:
            continue
        rows.append((CLAIM[h], LABEL[h], SOURCE[h], CMD[h], r.r[k]["value"]))
    return rows


def wording(r: Res) -> str:
    """Allowed and not allowed wording per v2 hypothesis."""
    f = lambda k, d=3: f"{r.r[k]['value']:.{d}f}"  # noqa: E731
    ci = lambda k, d=3: f"{f(k, d)} [{f(k + '_lo', d)} to {f(k + '_hi', d)}]"  # noqa: E731
    v = lambda h: r.r[f"v2.holm.verdict.{h}"]["value"]  # noqa: E731
    rows = [
        ("H-A1", v("H-A1"), f"On 176 NHTSA crash tests, at +-16 g and 100 Hz, a quantile boosting model on clipping descriptors and pulse-family features has a 90th-percentile delta-V error of {f('v2.a.R.r16.QR.p90', 1)}% against {f('v2.a.R.r16.M+.p90', 1)}% for fill + ridge on repeated grouped cross-validation (difference {ci('v2.a.hA1.R.p90_reduction_Mplus_minus_QR', 1)} points); the gain is {f('v2.a.hA1.A.p90_reduction_Mplus_minus_QR', 1)} points on the make/model hold-out split A (interval {f('v2.a.hA1.A.p90_reduction_Mplus_minus_QR_lo', 1)} to {f('v2.a.hA1.A.p90_reduction_Mplus_minus_QR_hi', 1)}); of the three fixed splits only the original-rule split O has its whole interval above zero.",
         "That the estimator works on a real sensor or on crashes unlike the NHTSA tests; that it is the best estimator (plain gradient boosting has a lower 90th percentile on split R, EXPLORATORY; it is not shown better than the triangle fit alone or than ridge on all features); that it fixes the large-error tail."),
        ("H-A2", v("H-A2"), f"Normalised-score intervals bring coverage in the lowest clipped-fraction tercile to {f('v2.a.a5.r16.iii.bin_low.coverage', 2)} (plain: {f('v2.a.a5.r16.i.bin_low.coverage', 2)}) by being wider there (median relative width {f('v2.a.a5.r16.iii.bin_low.width_rel', 2)} against {f('v2.a.a5.r16.i.bin_low.width_rel', 2)}); they are narrower in the middle and highest terciles ({f('v2.a.a5.r16.iii.bin_mid.width_rel', 2)} and {f('v2.a.a5.r16.iii.bin_high.width_rel', 2)} against {f('v2.a.a5.r16.i.bin_mid.width_rel', 2)} and {f('v2.a.a5.r16.i.bin_high.width_rel', 2)}); the tests that never clip are covered {f('v2.a.a5.r16.iii.bin_none.coverage', 2)} of the time.",
         "That adaptive intervals are narrower or tighter where clipping is mild."),
        ("H-A3", v("H-A3"), f"At +-16 g the plain estimate is above the reference delta-V for {f('v2.a.a2.r16.lower_exceeds_ref_1p00', 0)} of 176 tests (but for {f('v2.a.a2.r32.lower_exceeds_ref_1p00', 0)} at +-32 g and {f('v2.a.a2.r64.lower_exceeds_ref_1p00', 0)} at +-64 g, so it is not a guarantee); the interval from the plain estimate to the pulse-family upper bound contains the reference for {f('v2.a.a2.r16.containment', 2)} of tests.",
         "Guaranteed bounds; an upper bound on delta-V from the unclipped part of the pulse."),
        ("H-B1", v("H-B1"), f"In the simulator, none of five load-adaptive escalation variants raised critical reach within 10 s by 3 points over a matched fixed lowered-threshold rule in the burst cells (best mean gain {f('v2.b.hB3.best_mean_gain', 4)}); the beacon variant lowered it in cells (for example {ci('v2.b.gain.loadedburst_sf9.V3.reach10_critical', 3)} in the loaded SF9 cell). No tested variant reached a 3-point gain in these simulated cells.",
         "That adaptive escalation improves delivery; that where escalations go matters (not shown)."),
        ("H-B2", v("H-B2"), f"The largest point harm of any variant in a steady or single-car cell is {f('v2.b.hB2.worst_point_harm', 3)} (graceful demotion, single car at 60% loss); its interval includes 2 points. For no variant does a whole interval of harm lie above 2 points, but some upper 95% bounds do (beacon variant in the steady cell with loss 0.3, demotion in the single-car cell); two variants are worse than their baseline with the whole interval below zero in some burst cells.",
         "That adaptive variants are safe in steady state."),
        ("H-B3", v("H-B3"), f"Not evaluable because H-B1 is not met (the token bucket's mean gain is {f('v2.b.hB3.bucket_mean_gain', 4)} against {f('v2.b.hB3.best_mean_gain', 4)} for the best variant).", "Any claim that a simple rule suffices."),
        ("H-D1", v("H-D1"), f"Among the Severe or Critical tests it flags ({f('v2.d.R.r16.f100.D2.detection', 2)} of them), the clip-onset flag saves a median of {f('v2.d.hD1.median_time_saved_ms', 0)} ms (interval {f('v2.d.hD1.median_time_saved_ms_lo', 0)} to {f('v2.d.hD1.median_time_saved_ms_hi', 0)}); the running delta-V threshold flags {f('v2.d.R.r16.f100.II.detection', 2)} and saves {f('v2.d.R.r16.f100.II.median_time_saved_ms', 0)} ms, so the flag is earlier where it fires but misses {f('v2.d.hD1.under_triage_D2_minus_analogue', 2)} more of the Severe or Critical tests.",
         "That the clip onset gives an early severity flag of 100 ms or more."),
        ("H-D2", v("H-D2"), f"The clip-onset flag has an over-triage of {ci('v2.d.hD2.over_triage', 3)}; the raw p-value is {f('v2.holm.H-D2.p_raw', 3)} (Holm-adjusted {f('v2.holm.H-D2.p_holm', 3)}) and the interval reaches {f('v2.d.hD2.over_triage_hi', 3)}.", "That the over-triage is below 10% with confidence."),
        ("H-E1", v("H-E1"), f"Dropping the tag from 8 to 4 bytes changes critical reach within 10 s by {ci('v2.e.hE1.gain_t4_minus_t8', 4)} in the simulated burst cells (about one point).", "That a shorter tag gives a capacity gain of 2 points or more."),
        ("H-E2", v("H-E2"), f"With a truncated HMAC and a secret key, an 8-byte tag needs about 2^{f('v2.e.hE2.log2_attempts_for_1e6_t8', 0)} forgery attempts for a probability of 1e-6 (a count of attempts, not capped by the duty limit); the smallest tag with both work factors above 2^32 is {f('v2.e.e3.smallest_tag_bytes_above_2p32', 0)} bytes. The duty limit does not bind an attacker.",
         "A cryptographic proof; that the key cannot be recovered."),
        ("H-F1", v("H-F1"), f"In the cost model a positive Critical hold is optimal when D / C_false is below {f('v2.f.hF1.ppv.crossing_d_over_cf', 0)} at the precision of the deployed forest at 0.02% prevalence.", "That a zero Critical hold is optimal for any cost ratio."),
        ("H-F2", v("H-F2"), f"In the simulator, a 2 s hold of Severe alerts reduces the share of false Severe alerts reaching the base by a relative {ci('v2.f.hF2.relative_reduction_false_severe_reaching_base', 2)}; critical reach within 10 s changes by {ci('v2.f.hF2.change_critical_reach10', 3)} (a loss of up to {-float(r.r['v2.f.hF2.change_critical_reach10_lo']['value']) * 100:.1f} points is not excluded); the delay to true Severe alerts is not measured.", "That the hold is free in the field (the cancel model and every cost are assumptions)."),
    ]
    out = ["", "## Allowed wording for the v2 claims (generated)", "", "| Hypothesis | Verdict | Allowed wording | Not allowed |", "|---|---|---|---|"]
    out += [f"| {h} | **{vd}** | {a} | {n} |" for h, vd, a, n in rows]
    out += ["", "Studies A and D use 176 NHTSA tests (mostly high-speed barrier tests, not representative of all real crashes); B, H-E1 and F2 are simulations with assumed values, H-E2 and F1 are formulas; the 1% duty limit is not verified for India. Study C is NOT_RUN (see `docs/03_results/V2_RESULTS.md`)."]
    return "\n".join(out)
