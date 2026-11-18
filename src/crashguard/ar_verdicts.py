"""Verdicts of the combined run: Holm correction over family S (6 hypotheses) and family R (7 hypotheses), written as `sh.holm.*` and `ar.holm.*` keys, and the decision table
`docs/03_results/COMBINED_VERDICTS.md` (verdict, effect size with interval, nearest prior work, allowed wording, main paper or supplement).

SUPPORTED needs the preregistered criterion met on the held-out data AND a Holm-adjusted p-value below 0.05 (docs/02_preregistration/PREREGISTRATION_V11.md section 1).

    python -m crashguard.ar_verdicts
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard.results import record_many

R = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
OUT = Path("docs/03_results/COMBINED_VERDICTS.md")
SRC = "src/crashguard/ar_verdicts.py"

# id, family, statement, criterion key, p key, label of the evidence
S_FAM = [
    ("hs1", "H-S1", "The impact-side rule keeps side accuracy at or above 0.90 in every sensor variant of the simulated logs.", "sh.s2.hS1.criterion_met", "sh.s2.hS1.p_raw", "SIMULATED_HW_FORMAT"),
    ("hs2", "H-S2", "The 2 g trigger gives crash recall of at least 0.90 and a non-crash false-alarm rate of at most 0.10 in every sensor variant.", "sh.s2.hS2.criterion_met", "sh.s2.hS2.p_raw", "SIMULATED_HW_FORMAT"),
    ("hs3", "H-S3", "On link logs calibrated from the four edge runs, UA-SCT delivers at least as often as fixed-3 minus 0.02, within the duty allowance.", "sh.s3.hS3.criterion_met", "sh.s3.hS3.p_raw", "SIMULATED_HW_FORMAT"),
    ("hs4", "H-S4", "The median trigger-to-ACK latency of first-try deliveries is at least 500 ms (a sub-500 ms statement fails for this window, alert and ACK).", "sh.s3.hS4.criterion_met", "sh.s3.hS4.p_raw", "SIMULATED_HW_FORMAT"),
    ("hs5", "H-S5", "No attack of the repository's suite and the simulated scenarios is accepted, and the reference verifier persists its counter.", "sh.s4.hS5.criterion_met", "sh.s4.hS5.p_raw", "SIMULATED_HW_FORMAT"),
    ("hs6", "H-S6", "SW-420 confirmation lowers the non-crash false-alarm rate by at least 0.02 and loses at most 0.02 of the crash recall.", "sh.s5.hS6.criterion_met", "sh.s5.hS6.p_raw", "SIMULATED_HW_FORMAT"),
]
R_FAM = [
    ("hr1a", "H-R1a", "After a car reboot GTF accepts at least 99% of valid alerts (clock drift up to 5 s, GPS loss up to 40%).", "ar.r1.hR1a.criterion_met", "ar.r1.hR1a.p_raw", "SIMULATED"),
    ("hr1b", "H-R1b", "GTF replay acceptance is zero outside the window and at most 1% inside it, at the held-out burst loads.", "ar.r1.hR1b.criterion_met", "ar.r1.hR1b.p_raw", "SIMULATED"),
    ("hr1c", "H-R1c", "GTF cuts flash writes per year at least 10 times against persisting every alert counter.", "ar.r1.hR1c.criterion_met", "ar.r1.hR1c.p_raw", "ANALYTICAL"),
    ("hr2a", "H-R2a", "A frame of at most 40 bytes with a 7 or 8 byte tag raises burst delivery by 5 points over the 97-byte frame.", "ar.r2.hR2a.criterion_met", "ar.r2.hR2a.p_raw", "SIMULATED"),
    ("hr2b", "H-R2b", "The 97-byte frame with an 8-byte tag is dominated, in forgery effort, time on air and delivery, by a frame with a tag of at least 8 bytes.", "ar.r2.hR2b.criterion_met", "ar.r2.hR2b.p_raw", "SIMULATED"),
    ("hr3", "H-R3", "A provisional flash from the early-exit rule reaches the base at least 0.8 s earlier, with under 20% retractions, under 40% extra airtime and no delivery loss.", "ar.r3.hR3.criterion_met", "ar.r3.hR3.p_raw", "SIMULATED"),
    ("hr4", "H-R4", "With per-vehicle ACK keys a forged ACK from a compromised node stops only that node, at one extra KDF per new id and no extra bytes.", "ar.r4.hR4.criterion_met", "ar.r4.hR4.p_raw", "ANALYTICAL"),
]


def holm(ps: list[float]) -> list[float]:
    m = len(ps)
    order = np.argsort(ps)
    adj = np.zeros(m)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj.tolist()


def verdicts(fam: list, prefix: str) -> tuple[list[dict], list[dict]]:
    ps = [float(R[p]) for *_x, _c, p, _l in fam]
    adj = holm(ps)
    rows, ent = [], []
    for (key, hid, text, ck, pk, lab), p, pa in zip(fam, ps, adj):
        crit = int(R[ck])
        v = "SUPPORTED" if crit == 1 and pa < 0.05 else "NOT SUPPORTED"
        rows.append(dict(key=key, id=hid, text=text, crit=crit, p=p, p_holm=pa, verdict=v, label=lab))
        for nm, val, unit in (("p_raw", p, "p"), ("p_holm", pa, "p"), ("criterion_met", crit, "flag"), ("verdict", v, "text")):
            ent.append(dict(name=f"{prefix}.holm.{key}.{nm}", value=float(f"{val:.4g}") if isinstance(val, float) else val, unit=unit, origin=lab if nm == "verdict" else lab, source_file=SRC,
                            notes=text if nm == "verdict" else ("criterion on the held-out data" if nm == "criterion_met" else "")))
    ent.append(dict(name=f"{prefix}.holm.family_size", value=len(fam), unit="hypotheses", origin="ANALYTICAL", source_file=SRC, notes="Holm correction over this family, alpha 0.05"))
    return rows, ent


def pooled_gain_ci() -> tuple[float, float, float]:
    """Exploratory (not a verdict): pooled paired gain of 24/8 over 97/8 in reach10_critical over the 16 held-out cells and 30 hours, bootstrap over the (cell, hour) pairs."""
    d = pd.read_csv("results/tables/ar_r2_held.csv")
    a = d[d.pol == "24/8"].set_index(["cell", "hour"]).reach10_critical
    b = d[d.pol == "97/8"].set_index(["cell", "hour"]).reach10_critical
    x = (a - b).dropna().to_numpy(float)
    rng = np.random.default_rng(42)
    bm = x[rng.integers(0, len(x), (2000, len(x)))].mean(axis=1)
    return float(x.mean()), float(np.quantile(bm, 0.025)), float(np.quantile(bm, 0.975))


def g(k, nd=3):
    v = R[k]
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def main() -> None:
    srows, sent = verdicts(S_FAM, "sh")
    rrows, rent = verdicts(R_FAM, "ar")
    pg = pooled_gain_ci()
    ent = sent + rent
    ent.append(dict(name="ar.r2.exploratory.pooled_gain_24_8_over_97_8", value=round(pg[0], 5), unit="fraction", origin="SIMULATED", source_file=SRC, notes="EXPLORATORY, not a verdict: pooled paired gain in reach10_critical over 16 held-out cells x 30 hours"))
    ent.append(dict(name="ar.r2.exploratory.pooled_gain_24_8_over_97_8_lo", value=round(pg[1], 5), unit="fraction", origin="SIMULATED", source_file=SRC, notes="95% bootstrap interval over (cell, hour) pairs"))
    ent.append(dict(name="ar.r2.exploratory.pooled_gain_24_8_over_97_8_hi", value=round(pg[2], 5), unit="fraction", origin="SIMULATED", source_file=SRC, notes="95% bootstrap interval over (cell, hour) pairs"))
    record_many(ent)
    V = {r["key"]: r for r in srows + rrows}
    rule3 = 1.0 - 0.05 ** (1.0 / float(R["sh.s4.scenarios.attack_attempts_counted"]))
    # effect sizes and wording per hypothesis: (effect text, nearest prior work, allowed wording, placement)
    info = {
        "hs1": (f"3 of 16 sets below 0.90: x flip {g('sh.s2.F_x.side_acc')} [{g('sh.s2.F_x.side_acc_lo')}, {g('sh.s2.F_x.side_acc_hi')}], y flip {g('sh.s2.F_y.side_acc')}, 10 Hz {g('sh.s2.S_10Hz.side_acc')}; base {g('sh.s2.V00_base.side_acc')}",
                "Impact direction from one IMU is the repository's own rule (`direction.py`); crash-pulse recorders exist (a 1995 validation study, seen in a listing only and not verified)",
                "On simulated hardware-format logs the side rule failed under an axis-sign flip and at 10 Hz sampling and held 0.90 under tilts up to 30 degrees, noise x4 and bias 0.08 g.", "supplement"),
        "hs2": (f"false-alarm rate of the 2 g trigger {g('sh.s2.V00_base.far')} [{g('sh.s2.V00_base.far_lo')}, {g('sh.s2.V00_base.far_hi')}] in the base variant; recall ok in 15 of 16 sets (not at 10 Hz)",
                "none needed (a check of a threshold on bench events)", "On simulated bench events the 2 g trigger alone does not separate crash from non-crash (false-alarm rate about 0.6); this says nothing about vehicle crashes.", "supplement"),
        "hs3": (f"UA-SCT minus fixed-3 at 30, 34, 38, 42 dB: {g('sh.s3.hS3.H3-edge-30db.diff_P4_minus_P0', 4)}, {g('sh.s3.hS3.H3-edge-34db.diff_P4_minus_P0', 4)} [{g('sh.s3.hS3.H3-edge-34db.diff_lo', 3)}, {g('sh.s3.hS3.H3-edge-34db.diff_hi', 3)}], {g('sh.s3.hS3.H3-edge-38db.diff_P4_minus_P0', 4)}, {g('sh.s3.hS3.H3-edge-42db.diff_P4_minus_P0', 4)}; largest airtime share {g('sh.s3.hS3.max_node_air_share', 3)} of the allowance",
                "Tamang et al. 2023 (slotted alarms), Khan et al. 2019 (retry model), Sisinni et al. 2021 and 2022 (redundancy): baselines, not duplicated",
                "On link logs simulated from stated models, no difference between UA-SCT and fixed-3 critical reach within 10 s was shown to be smaller than 0.02 (the 34 dB interval is wide); the severity table reached the base more often within 10 s at 34 dB.", "supplement; negative register"),
        "hs4": (f"median {g('sh.s3.h7.supplied.median_first_try_ms', 0)} ms, p95 {g('sh.s3.h7.supplied.p95_first_try_ms', 0)} ms; lower bound {g('sh.s3.h7.analytic.lower_bound_ms', 1)} ms before compute", "Carneiro et al. 2023 (LoRa crash response, record only); the sub-500 ms style claim is not attributed to a source",
                "In the model, trigger-to-ACK latency is about 520 ms for a 250 ms post-trigger window, a 97-byte alert and a 26-byte ACK at SF7; each retry adds about 600 ms. This is a statement about the model, not the radio.", "supplement (methods note)"),
        "hs5": (f"0 of {R['sh.s4.scenarios.attack_attempts_counted']} attack attempts accepted (95% upper bound {100 * rule3:.2f}%); suite {R['sh.s4.suite.total']} cases, all as expected", "Dong et al. 2024 and Wesemeyer et al. 2020 verify LoRaWAN; the alert suite is a different small protocol",
                "The repository's attack suite and the nine simulated scenarios behave as designed in software; the ESP32 firmware was not tested (NOT_RUN).", "supplement (methods)"),
        "hs6": (f"false-alarm reduction {g('sh.s5.base_range_1.5_4.0.pooled.far_reduction')} [{g('sh.s5.base_range_1.5_4.0.pooled.far_reduction_lo')}, {g('sh.s5.base_range_1.5_4.0.pooled.far_reduction_hi')}], recall loss {g('sh.s5.base_range_1.5_4.0.pooled.recall_loss')} [{g('sh.s5.base_range_1.5_4.0.pooled.recall_loss_lo')}, {g('sh.s5.base_range_1.5_4.0.pooled.recall_loss_hi')}]; the sign of the criterion flips with the switch threshold range",
                "a vibration-sensor accident paper of the project literature (08, SW-420 in three levels; `CLAIM_EVIDENCE.md` N7); no benchmark found", "In simulated bench events SW-420 confirmation removed 0.29 of the false alarms and cost 0.04 of the crash recall; the balance depends on the assumed switch sensitivity.", "supplement; negative register"),
        "hr1a": (f"smallest availability {g('ar.r1.hR1a.min_availability', 4)} over 16 held-out cells; W = {R['ar.r1.design.W_s']} s", "ZigBee timestamp replay protection (IEEE TMC 2020, not opened); LoRaWAN frame counters; a LoRaWAN replay-attack study",
                 "In the simulation, a GPS-time freshness field with a 10 s window accepted at least 99.6% of valid alerts after a car reboot in every held-out cell (base clock drift up to 5 s, car time error up to 4 s, GPS loss up to 40%).", "supplement"),
        "hr1b": (f"largest replay rate inside W {g('ar.r1.hR1b.max_replay_rate', 4)} (cells over 1%: {R['ar.r1.hR1b.cells_over_1pct']}); with a 512-entry ring {g('ar.r1.sensitivity.R512.max_replay_rate', 4)}", "as R1a", "The ring size chosen on the design grid (256) was too small for the held-out burst of 300 alerts per window (rate 1.7 to 3.0%); a 512-entry ring met the bound. The ring must be sized above the number of alerts per window.", "supplement; negative register"),
        "hr1c": (f"{g('ar.r1.hR1c.ratio', 1)}x at 100 alerts and 12 boots per car and year (sensitivity table in `ar.r1.hR1c.sensitivity.*`)", "none specific", "Under stated rates, persisting no counter cuts flash writes about 17 times; the ratio is below 10 for fewer than 60 alerts per car and year at 12 boots.", "supplement"),
        "hr2a": (f"chosen on design: {R['ar.r2.hR2a.chosen_frame']}; {R['ar.r2.hR2a.cells_gain5_of_16']} of 16 held-out cells gain at least 5 points; mean gain {g('ar.r2.hR2a.mean_gain', 3)} (exploratory pooled {pg[0]:.3f} [{pg[1]:.3f}, {pg[2]:.3f}]); the sign test over 16 cells gives p {g('ar.r2.hR2a.p_raw', 3)}",
                 "FC-HMAC (Zenodo record not read); the 4-byte LoRaWAN MIC; no study on tag length against burst delivery of single-packet alerts found in the sources checked",
                 "In simulated bursts a 24-byte frame delivered more critical alerts within 10 s than the 97-byte frame; the preregistered sign test over 16 cells did not reach significance, and the shorter frame drops fields (position) that were not designed here.", "supplement; negative register (criterion met, test not significant)"),
        "hr2b": (f"dominating frames (tag >= 8 bytes): {R['ar.r2.hR2b.dominating_frames']}; point-estimate Pareto set (tag >= 7): {R['ar.r2.hR2b.pareto_set_tag_ge7']}", "as R2a", "In the simulation the 97-byte frame with an 8-byte tag is not on the Pareto front of forgery effort, time on air and burst delivery.", "supplement"),
        "hr3": (f"earlier by {g('ar.r3.a1.earlier_median_s_p0', 2)} s [{g('ar.r3.a1.earlier_median_s_p0_lo', 2)}, {g('ar.r3.a1.earlier_median_s_p0_hi', 2)}] at loss 0; retractions {g('ar.r3.a1.retraction_share')} [{g('ar.r3.a1.retraction_share_lo')}, {g('ar.r3.a1.retraction_share_hi')}]; extra airtime {g('ar.r3.a1.air_ratio_p0')} [{g('ar.r3.a1.air_ratio_p0_lo')}, {g('ar.r3.a1.air_ratio_p0_hi')}] at loss 0",
                "No crash-alert version of a provisional-then-confirm design found in the sources checked (not a claim of absence); early-exit classification of time series exists (Achenchabe et al., opened)",
                "In simulation on de-duplicated VZCrash test events, a 14-byte provisional alert from the early-exit rule reached the base about 1.9 s before the full-window alert, 11% of provisional alerts were retracted and the extra airtime was 38%. Timing is the window length, not measured on the ESP32. The single-stage baseline waits for the full window; an early-exit single-stage alert would be as fast but has no cancel path.", "main paper"),
        "hr4": (f"suppressed fraction 1.0 (shared key, event ACK) to {g('ar.r4.held.v3.per_vehicle_one_compromised.max_suppressed_fraction')} = 1/3 with one compromised vehicle, none of the honest vehicles; 0 extra bytes; one KDF per new id", "Per-device keys are standard in LoRaWAN; the shared-key counterexample is from `pa_model.py`",
                "A bounded-model check found that a forged event-level ACK from a key holder stops every vehicle; per-vehicle keys with the ACK bound to the vehicle and counter limit the effect to the compromised vehicle. This is a design correction, not a new key scheme; a holder of the master key is outside the claim.", "main paper"),
    }
    L = ["# Decision table of the combined run (Parts S and R)", ""] + ["<!-- header:start -->", "<!-- header:end -->", ""]
    L += ["Generated by `python -m crashguard.ar_verdicts`. SUPPORTED needs the preregistered criterion on the held-out data and a Holm-adjusted p-value below 0.05 (family S: 6 hypotheses; family R: 7). "
          "Two clean counts for the paper: **family S (simulated hardware-format validation): "
          f"{sum(r['verdict'] == 'SUPPORTED' for r in srows)} supported, {sum(r['verdict'] != 'SUPPORTED' for r in srows)} not supported of 6. Family R (architecture and protocol candidates): "
          f"{sum(r['verdict'] == 'SUPPORTED' for r in rrows)} supported, {sum(r['verdict'] != 'SUPPORTED' for r in rrows)} not supported of 7.** These two families are not mixed with the earlier 67 hypotheses of `PROJECT_STATUS.md` or with the V5 family of 18.", "",
          "Everything in Part S is SIMULATED_HW_FORMAT: code run on simulated hardware-format logs generated from stated sensor and link models; no real hardware measurements are reported. "
          "A candidate enters the main paper only if all its hypotheses are supported; the others go to the supplement, and the failed hypotheses to `docs/03_results/NEGATIVES_REGISTER.md`.", "",
          "| Id | Statement | Label | Criterion met | Raw p | Holm p | Verdict | Effect size and interval | Nearest prior work (Part L) | Allowed wording | Placement |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in srows + rrows:
        e, prior, wording, place = info[r["key"]]
        L.append(f"| {r['id']} | {r['text']} | {r['label']} | {'yes' if r['crit'] else 'no'} | {r['p']:.3g} | {r['p_holm']:.3g} | **{r['verdict']}** | {e} | {prior} | {wording} | {place} |")
    L += ["", "## Candidate level", "", "| Candidate | Hypotheses | Verdicts | Placement |", "|---|---|---|---|",
          f"| R1 reboot-resilient freshness (GTF) | H-R1a, H-R1b, H-R1c | {V['hr1a']['verdict']}, {V['hr1b']['verdict']}, {V['hr1c']['verdict']} | supplement; H-R1b to the negatives register (ring sizing) |",
          f"| R2 security-airtime co-design | H-R2a, H-R2b | {V['hr2a']['verdict']}, {V['hr2b']['verdict']} | supplement; H-R2a to the negatives register |",
          f"| R3 two-stage alert | H-R3 | {V['hr3']['verdict']} | main paper |", f"| R4 per-vehicle ACK keys | H-R4 | {V['hr4']['verdict']} | main paper |", "",
          "Kill criteria: none fired. R1: drift of 2 s or less costs no availability and the time-stamped replay window is bounded by W. R2: a gain of at least 5 points exists and non-dominated frames exist. R3: all three clauses held. R4: the model found no other path that stops all vehicles from one compromised node. "
          "A kill criterion is not the same as a SUPPORTED verdict: H-R1b and H-R2a failed their preregistered criterion or test.", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print({r["id"]: (r["verdict"], round(r["p"], 5), round(r["p_holm"], 5)) for r in srows + rrows})
    print("pooled gain", pg)


if __name__ == "__main__":
    main()
