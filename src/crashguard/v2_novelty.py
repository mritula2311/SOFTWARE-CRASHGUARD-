"""Novelty points N29 to N34 for the v2 studies (docs/02_preregistration/PREREGISTRATION_V2.md), added to ``novelty``. Status comes from the verdicts in ``v2.holm.verdict.*``; evidence lines are read from results.json. Prior work: only
sources opened in earlier rounds are named; Jao and Shkel 2022 and Zhang et al. 2026 could not be opened and are not cited for any result."""
from __future__ import annotations

from crashguard.report import Res

PIDS = ("N29", "N30", "N31", "N32", "N33", "N34")


def verdict(r: Res, h: str) -> str:
    e = r.r.get(f"v2.holm.verdict.{h}")
    return e["value"] if e else "MISSING"


def status(r: Res, pid: str) -> str:
    v = lambda h: verdict(r, h)  # noqa: E731
    if pid == "N29":
        return "SUPPORTED" if v("H-A1") == "SUPPORTED" else "NO_IMPROVEMENT_FOUND"
    if pid == "N30":
        return "SUPPORTED" if v("H-A2") == "SUPPORTED" and v("H-A3") == "SUPPORTED" else ("PARTIAL" if "SUPPORTED" in (v("H-A2"), v("H-A3")) else "NO_IMPROVEMENT_FOUND")
    if pid == "N31":
        return "SUPPORTED" if v("H-D1") == "SUPPORTED" else "NO_IMPROVEMENT_FOUND"
    if pid == "N32":
        return "SUPPORTED" if v("H-B1") == "SUPPORTED" else "NO_IMPROVEMENT_FOUND"
    if pid == "N33":
        return "PARTIAL" if v("H-E2") == "SUPPORTED" and v("H-E1") != "SUPPORTED" else ("SUPPORTED" if v("H-E1") == "SUPPORTED" and v("H-E2") == "SUPPORTED" else "NO_IMPROVEMENT_FOUND")
    if pid == "N34":
        return "PARTIAL" if v("H-F2") == "SUPPORTED" else "NO_IMPROVEMENT_FOUND"
    return "NOT_YET"


def points(r: Res, Point) -> list:
    nhtsa = "NHTSA tests are mostly high-speed barrier tests and are not representative of all real crashes"
    return [
        Point("N29", f"Tail-aware clipping estimator: a quantile boosting model on clipping descriptors and pulse-family features lowers the `90th`-percentile delta-V error against fill + ridge at +-16 g on repeated grouped cross-validation (interval above zero) and, as point estimates above 5 points, on two of three fixed splits (only one of them with its interval above zero) (preregistered; {nhtsa}); plain gradient boosting, tried as an EXPLORATORY variant, has a lower `90th` percentile still", "extra", "SUPPORTED",
              ["v2.a.hA1.R.p90_reduction_Mplus_minus_QR", "v2.holm.verdict.H-A1"],
              [("v2.a.R.r16.M+.p90", 1), ("v2.a.R.r16.QR.p90", 1), ("v2.a.R.r16.GBR.p90", 1), ("v2.a.R.r16.M+.median", 1), ("v2.a.R.r16.QR.median", 1), ("v2.a.R.r16.QR.w10", 3), ("v2.a.hA1.R.p90_reduction_Mplus_minus_QR", 1), ("v2.a.hA1.R.p90_reduction_Mplus_minus_QR_lo", 1),
               ("v2.a.hA1.R.p90_reduction_Mplus_minus_QR_hi", 1), ("v2.a.hA1.G.p90_reduction_Mplus_minus_QR", 1), ("v2.a.hA1.A.p90_reduction_Mplus_minus_QR", 1), ("v2.a.hA1.O.p90_reduction_Mplus_minus_QR", 1), ("v2.holm.H-A1.p_holm", 4)],
              "A real saturated pulse from the sensor; crashes unlike the NHTSA tests; the split A (make/model hold-out) gain is small and its interval reaches zero.",
              "Spline restoration of clipped acceleration (Chan et al. 2023, opened) is the earlier baseline; Jao and Shkel 2022 and Zhang et al. 2026 could not be opened and are not used. A triangle fit and a Gaussian-process fill appear only as our own implementations of the idea.",
              "High. Standard boosting on engineered features; the value is the measured tail error and the honest comparison, not the method."),
        Point("N30", f"Deterministic bounds and adaptive conformal intervals for the clipped delta-V estimate: the plain estimate is a lower bound for almost every test at +-16 g (not at `+-32 g` and `+-64 g`), but the pulse-family upper bound does not contain the reference for enough tests and normalised-score intervals are wider, not narrower, where clipping is mild (preregistered; {nhtsa})", "extra", "NO_IMPROVEMENT_FOUND",
              ["v2.a.a2.r16.containment", "v2.a.hA2.coverage_iii"],
              [("v2.a.a2.r16.containment", 3), ("v2.a.a2.r16.containment_lo", 3), ("v2.a.a2.r16.containment_hi", 3), ("v2.a.a2.r16.lower_exceeds_ref_1p00", -1), ("v2.a.a2.r16.upper_below_ref", -1), ("v2.a.a5.r16.i.bin_low.coverage", 3), ("v2.a.a5.r16.iii.bin_low.coverage", 3),
               ("v2.a.a5.r16.i.bin_low.width_rel", 3), ("v2.a.a5.r16.iii.bin_low.width_rel", 3), ("v2.a.hA2.low_tercile.relwidth_iii_minus_i", 3), ("v2.a.hA2.coverage_iii", 3)],
              "A pulse-shape family that bounds the unclipped part of real saturated pulses from above; a difficulty model that is calibrated on more than `176` tests.",
              "Conformal prediction around severity estimates (CHOIR, abstract opened, police records) and jackknife+ and CV+ (abstracts opened) are the earlier sources; no source opened bounds clipped delta-V from a pulse family.",
              "Low as a contribution; a negative result with the reasons (the upper bound is not an upper bound)."),
        Point("N31", f"Clip-onset early severity flag: the time from the trigger to the earliest near-full-scale sample flags only part of the Severe or Critical events at +-16 g, with a median time saved under 100 ms, and it misses more Severe or Critical tests than a running delta-V threshold (preregistered; {nhtsa}; events that never clip cannot be flagged)", "extra", "NO_IMPROVEMENT_FOUND",
              ["v2.d.hD1.median_time_saved_ms", "v2.d.hD2.over_triage"],
              [("v2.d.hD1.median_time_saved_ms", 0), ("v2.d.hD1.median_time_saved_ms_lo", 0), ("v2.d.hD1.median_time_saved_ms_hi", 0), ("v2.d.hD1.under_triage_D2_minus_analogue", 3), ("v2.d.hD2.over_triage", 3), ("v2.d.R.r16.f100.D2.detection", 3),
               ("v2.d.R.r16.f100.II.detection", 3), ("v2.d.R.r16.f100.II.median_time_saved_ms", 0), ("v2.d.r16.f100.share_never_clip", 3)],
              "Early-flag timing on the ESP32 and on non-barrier crashes; the N19 forests were not applied to severity (they classify crash against non-crash on VZCrash).",
              "Early-exit classification is standard (snippets only); the N19 result on VZCrash decides about a second earlier. No source opened uses the clip onset as an early flag.",
              "Low as a contribution; a negative result."),
        Point("N32", "Load-adaptive escalation: five variants (a per-car controller, a token bucket, a base-station beacon, severity-scaled backoff, graceful demotion) do not raise critical reach within 10 s by 3 points over a matched fixed lowered-threshold rule in the simulated burst cells (small gains in a few cells); the beacon variant lowers it in some cells (SIMULATED; preregistered; every channel and traffic value is an assumption)", "extra", "NO_IMPROVEMENT_FOUND",
              ["v2.b.hB1.criterion_met", "v2.b.hB3.best_mean_gain"],
              [("v2.b.hB1.V1.mean_gain_burst_cells", 4), ("v2.b.hB1.V2.mean_gain_burst_cells", 4), ("v2.b.hB1.V3.mean_gain_burst_cells", 4), ("v2.b.hB1.V4.mean_gain_burst_cells", 4), ("v2.b.hB1.V5.mean_gain_burst_cells", 4),
               ("v2.b.hB2.worst_point_harm", 3), ("v2.b.duty.runs_exceeding_limit", -1)],
              "Hardware with several nodes; a network-level admission rule (the per-car rules have no competing candidates in a burst).",
              "Priority and urgent-packet handling in LoRaWAN (Tamang et al. 2022, opened), interrupt-style warning delivery (Shao, Liew and Liang 2020, abstract opened) and the earlier N26 results.",
              "Low as a contribution; no tested variant reached a 3-point gain in these simulated cells (the unloaded burst cells hold almost no competing escalations by design)."),
        Point("N33", "Authentication-tag length: an 8-byte tag keeps the forgery work factor (a count of attempts, which the duty limit does not cap) far above 2^32 attempts (ANALYTICAL; truncated HMAC, secret key, no proof), and a 4-byte tag raises critical reach within 10 s in simulated bursts by less than one point (SIMULATED), so there is no capacity reason to shorten the tag", "extra", "PARTIAL",
              ["v2.e.hE2.log2_attempts_for_1e6_t8", "v2.e.hE1.gain_t4_minus_t8"],
              [("v2.e.hE2.log2_attempts_for_1e6_t8", 1), ("v2.e.forgery.t4.sf7.log2_attempts_for_1e6", 1), ("v2.e.forgery.t4.sf7.hours_for_1e6_dutycap", 1), ("v2.e.e3.smallest_tag_bytes_above_2p32", -1), ("v2.e.hE1.gain_t4_minus_t8", 4), ("v2.e.hE1.gain_t4_minus_t8_lo", 4), ("v2.e.hE1.gain_t4_minus_t8_hi", 4)],
              "A real attacker's rate (the duty limit does not bind one), key management, and the firmware; no cryptographic proof is claimed.",
              "Truncating a tag is a known trade-off (named in the task); no source was opened for this study.",
              "Low as a contribution; the value is a quantified curve for this alert protocol."),
        Point("N34", "Severity-dependent hold: a 2 s hold of Severe alerts cuts the share of false Severe alerts that reach the base without a significant loss in critical reach (SIMULATED; cancel model and costs are assumptions), while the cost model puts the optimal Critical hold at zero only above a cost ratio that depends on the precision (ANALYTICAL)", "extra", "PARTIAL",
              ["v2.f.hF2.relative_reduction_false_severe_reaching_base", "v2.f.hF1.n_positive"],
              [("v2.f.hF2.relative_reduction_false_severe_reaching_base", 3), ("v2.f.hF2.relative_reduction_false_severe_reaching_base_lo", 3), ("v2.f.hF2.relative_reduction_false_severe_reaching_base_hi", 3), ("v2.f.hF2.change_critical_reach10", 4),
               ("v2.f.hF1.ppv.crossing_d_over_cf", 1), ("v2.f.hF1.simmix.crossing_d_over_cf", 2), ("v2.f.hF1.n_positive", -1)],
              "Real driver cancel behaviour, real costs of a false alert and of a delay; hardware.",
              "No source opened; the cancel window by class is a design value of the repository (docs/01_protocol/PROTOCOL_SCT.md).",
              "Low as a contribution; a design result that follows from the assumed cancel model."),
    ]


def keyev(r: Res) -> dict:
    f = r.f  # marked numbers: the novelty test requires every number to come from results.json
    return {
        "N29": f"+-16 g, split R: `90th`-percentile error {f('v2.a.R.r16.QR.p90', 1)}% against {f('v2.a.R.r16.M+.p90', 1)}% (fill + ridge); median {f('v2.a.R.r16.QR.median', 1)}% against {f('v2.a.R.r16.M+.median', 1)}%",
        "N30": f"bounds contain the reference for {f('v2.a.a2.r16.containment', 2)} of tests at +-16 g; adaptive interval width in the lowest tercile {f('v2.a.a5.r16.iii.bin_low.width_rel', 2)} against {f('v2.a.a5.r16.i.bin_low.width_rel', 2)} (plain)",
        "N31": f"median time saved {f('v2.d.hD1.median_time_saved_ms', 0)} ms; detection {f('v2.d.R.r16.f100.D2.detection', 2)} against {f('v2.d.R.r16.f100.II.detection', 2)} for the running delta-V threshold",
        "N32": f"best mean gain over the burst cells {f('v2.b.hB3.best_mean_gain', 4)} (matched baselines); SIMULATED",
        "N33": f"8-byte tag: 2^{f('v2.e.hE2.log2_attempts_for_1e6_t8', 0)} attempts for a forgery probability of `1e-6`; 4-byte gain in critical reach {f('v2.e.hE1.gain_t4_minus_t8', 4)}",
        "N34": f"false Severe alerts reaching the base reduced by {f('v2.f.hF2.relative_reduction_false_severe_reaching_base', 2)} with a 2 s hold; critical reach change {f('v2.f.hF2.change_critical_reach10', 4)}",
    }


PRIOR_SHORT = {"N29": "Chan 2023 spline restoration (opened); other named papers not opened", "N30": "CHOIR; jackknife+ and CV+ (abstracts opened)", "N31": "Early-exit classification (snippets); N19", "N32": "Tamang 2022; Shao 2020 (abstract)",
               "N33": "Truncated tags are a known trade-off; no source opened", "N34": "None opened"}
HW = {"N29": "A real saturated pulse from the sensor", "N30": "A wider test set including non-barrier crashes", "N31": "H5 timing on the ESP32 and non-barrier crashes", "N32": "H3 with several nodes",
      "N33": "Firmware and key management; no hardware plan item", "N34": "Real driver cancel behaviour; H3"}
ROLE = {"N29": "supporting evidence (MEASURED_SOFTWARE)", "N30": "negative result", "N31": "negative result", "N32": "negative result (SIMULATED)", "N33": "quantified trade-off (ANALYTICAL and SIMULATED)", "N34": "supporting evidence (SIMULATED)"}
