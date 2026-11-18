"""Claim table of docs/03_results/CLAIM_EVIDENCE.md: one row per claim with its label, the source (results.json keys or file), the command that produces it and a verdict computed from results.json.

Verdicts: SUPPORTED (the claim as worded has software evidence and, where a decision rule was fixed in advance, meets it), PARTIAL (software or simulation evidence only, or a part of the claim fails), NOT SUPPORTED (tried; the
claim does not clear its interval or the preregistered rule). No hardware result is used. The table is written between markers; the rest of the file is hand-written.
"""
from __future__ import annotations

from pathlib import Path

from crashguard import novelty as N
from crashguard import jp_claims as JP
from crashguard import v2_claims as V2
from crashguard.docs_gen import replace_block
from crashguard.report import Res

DOC = Path("docs/03_results/CLAIM_EVIDENCE.md")
START, END = "<!-- claims:start -->", "<!-- claims:end -->"


def _v(r: Res, k: str):
    e = r.r.get(k)
    return e["value"] if e and isinstance(e["value"], (int, float)) and not isinstance(e["value"], bool) else None


def _lt(x, y) -> bool:
    return x is not None and x < y


def verdicts(r: Res) -> list[tuple]:
    pts = {p.pid: p for p in N.points(r)}
    st = {k: N.status_of(r, p) for k, p in pts.items()}
    mp = {"SUPPORTED": "SUPPORTED", "PARTIAL": "PARTIAL", "NO_IMPROVEMENT_FOUND": "NOT SUPPORTED", "NOT_YET": "NOT SUPPORTED"}
    ha = _lt(_v(r, "ua.r16.a10.cc.paired.mis_triage_upper_minus_point_hi"), 0) and _lt(_v(r, "ua.r16.a10.cc.paired.mis_triage_upper_minus_point"), -0.02)
    hb = (_v(r, "ua.r16.a10.cc.paired.escalation_upper_minus_point_lo") or 0) > 0 and (_v(r, "s11.diff.r16.burst.P4_minus_P3.reach10_critical_lo") or -1) > -0.05
    hc = (_v(r, "ua.hc.reduction_16_minus_64_lo") or 0) > 0 and _lt(_v(r, "ua.hc.width_64_minus_16_hi"), 0)
    steady_gain = (_v(r, "s11.diff.r16.steady.P3_minus_P1.reach10_critical_lo") or -1) > 0
    burst_gain = (_v(r, "s11.diff.r16.burst.P2_minus_P1.reach10_critical_lo") or -1) > 0
    p3p2 = (_v(r, "s11.diff.r16.burst.P3_minus_P2.reach30_critical_lo") or -1) > 0
    duty0 = _v(r, "s11.duty.runs_exceeding_limit") == 0
    cov = all((_v(r, f"ua.r{rg}.a10.cc.coverage_hi") or 0) >= 0.9 and (_v(r, f"ua.r{rg}.a10.cc.coverage_lo") or 1) >= 0.9 for rg in (16, 32, 64))
    a4 = r.r.get("s5.a4.scheduler_vs_severity.delivered_critical.settings_where_not_better", {}).get("value") == "none"
    cc = _v(r, "s12.crosscheck.agree"), _v(r, "s12.crosscheck.cases")
    holm = all(_v(r, f"t14.{h}.survives_correction") == 1 for h in ("H-a", "H-b", "H-c"))
    t1_win = any(_v(r, f"t1.r{rg}.decision.p3_wins_at_equal_escalation") == 1 for rg in (16, 32, 64))
    t2_win = all((_v(r, f"t2.r{rg}.auc_interval_minus_point_hi") or 1) < 0 for rg in (16, 32, 64))
    be_lo = _v(r, "t3.r16.sobs.break_even_ratio_lo")
    t3e = all((_v(r, f"t3.r16.sobs.ratio{t}.cost_diff_p3_minus_p1e_hi") or 1) < 0 for t in ("1", "10", "100"))
    t4b = (_v(r, "t4.b.loss60.P2.reach10_critical_lo") or 0) >= (_v(r, "t4.b.loss60.P1.reach10_critical_hi") or 1)
    t4q = (_v(r, "t4.b.loss60.P2_quick.reach10_critical_lo") or 0) >= (_v(r, "t4.b.loss60.P1.reach10_critical_hi") or 1)
    t5 = (_v(r, "t5.diff_std_minus_strict.recall_f1_lo") or 0) > 0
    t6a = all(_v(r, f"t6.{k}.H_a_survives") == 1 for k in ("base", "allm2", "allm1", "allp1", "allp2", "midm2", "midp2"))
    t6c = all(_v(r, f"t6.{k}.H_c_survives") == 1 for k in ("base", "allm2", "allm1", "allp1", "allp2", "midm2", "midp2"))
    t7 = any(_v(r, f"t7.b.a5.{k}.holds") == 1 for k in ("size_groupwise", "widened_margin"))
    t8n, t8c = _v(r, "t8.count.P3_vs_P1.reach10_critical.n_beats"), _v(r, "t8.count.P3_vs_P1.reach10_critical.n_cells")
    t9 = all((_v(r, f"t9.diff.burst_base.P2.{v}_minus_full.reach10_critical_hi") or 1) < 0 for v in ("no_flash", "no_hold"))
    t9r = all(_v(r, f"t9.diff.{c}.P2.no_reserve_minus_full.reach10_critical") == 0 for c in ("steady_base", "burst_base", "burst_b60", "burst_sf9", "burst_loss30", "steady_fa5"))
    t12 = _v(r, "s12x.EXT.design.C3_cancel_lost_by_reordering") == 0 and _v(r, "s12x.EXT.keep_pending_cancel.C3_cancel_lost_by_reordering") == 1
    ax = _v(r, "attacks_x.cases_total") == _v(r, "attacks_x.cases_matching_expected")
    return [
        ("Identical recordings occur across the supplied VZCrash splits (N8)", "MEASURED_SOFTWARE", "leakage.*", "python -m crashguard.split", "SUPPORTED" if _v(r, "leakage.exact_hash_groups_across_splits") else "NOT SUPPORTED"),
        ("Trigger-aligned window-level near-duplicates are far more common than exact duplicates and lower the headline recall (N8 extension)", "MEASURED_SOFTWARE", "dupscan.*", "python -m crashguard.s2_dedup",
         "SUPPORTED" if (_v(r, "dupscan.rf15.mean5.diff_supplied_minus_dedup_nd.sys_recall_lo") or 0) > 0 else "NOT SUPPORTED"),
        ("The conformal false-alarm guarantee holds on the de-duplicated test set (N20, calibration de-duplicated by recording group)", "MEASURED_SOFTWARE", "n20c.*", "python -m crashguard.s3_conformal", mp[st["N20"]] if st["N20"] != "SUPPORTED" else "SUPPORTED"),
        ("Fill + ridge lowers the delta-V error at +-16 g against plain and spline restoration (N14; named primary after earlier results were seen)", "MEASURED_SOFTWARE", "n14x.*, n14s.*", "python -m crashguard.saturation_splits; python -m crashguard.s4_n14", mp[st["N14"]]),
        ("Fill + ridge reaches the N13 target of 80% within 10% at +-16 g", "MEASURED_SOFTWARE", "n14x.R.r16.M+.w10", "python -m crashguard.saturation_splits", "SUPPORTED" if (_v(r, "n14x.R.r16.M+.w10") or 0) >= 0.8 else "NOT SUPPORTED"),
        ("M+ capped improves the tail (exploratory)", "MEASURED_SOFTWARE", "n14s.cap.*", "python -m crashguard.s4_n14", "SUPPORTED" if _v(r, "n14s.cap.R.r16.paired.Mpc_vs_Mp.tail_improves") == 1 else "NOT SUPPORTED"),
        ("The early-exit rule saves about a second of decision time (N19)", "MEASURED_SOFTWARE (timing from window length)", "s6.*", "python -m crashguard.s6_early", "SUPPORTED" if _lt(_v(r, "s6.a5.mean5.d.E_minus_Ep.time_hi"), 0) and _lt(_v(r, "s6.a1.mean5.d.E_minus_Ep.time_hi"), 0) else "NOT SUPPORTED"),
        ("The early-exit recall gain over the single full-length forest is an early-exit effect (N19)", "MEASURED_SOFTWARE", "s6.*", "python -m crashguard.s6_early", "NOT SUPPORTED"),
        ("The scheduler beats the severity table in bursts across the A4 sweep, X6 simulator (N16, N22)", "SIMULATED (exploratory)", "s5.*", "python -m crashguard.s5_burst", "PARTIAL" if a4 else "NOT SUPPORTED"),
        ("Conformal intervals around the clipped delta-V estimate have about nominal coverage (N24)", "MEASURED_SOFTWARE", "n24.*", "python -m crashguard.s9_conformal_dv", "PARTIAL"),
        ("The class rule on those intervals lowers under-estimation (N24)", "MEASURED_SOFTWARE", "n24.*", "python -m crashguard.s9_conformal_dv", mp[st["N24"]]),
        ("A prevalence-adaptive threshold raises precision within five points of recall at prevalence of one per cent or lower (N25)", "MEASURED_SOFTWARE with assumed costs", "s10.*", "python -m crashguard.s10_adaptive", mp[st["N25"]]),
        ("UA-SCT B2: the class intervals reach the target coverage at every sensor range (conservative, not exact)", "MEASURED_SOFTWARE", "ua.r*.a10.cc.coverage", "python -m crashguard.ua_conformal", "PARTIAL" if cov else "NOT SUPPORTED"),
        ("H-a: P3 lowers mis-triage against P1 at +-16 g (reduction of more than two points; the reduction comes from escalating more events, see T1)", "MEASURED_SOFTWARE + SIMULATED", "ua.r16.a10.cc.paired.*, s11.diff.*", "python -m crashguard.ua_conformal; python -m crashguard.s11_sct", "SUPPORTED" if ha else "NOT SUPPORTED"),
        ("H-b: the cost of P3 is more fast-path escalations, and P4 bounds the fast-path airtime", "SIMULATED", "ua.*escalation*, s11.diff.*P4_minus_P3*", "python -m crashguard.s11_sct", "PARTIAL" if hb else "NOT SUPPORTED"),
        ("H-c: the gain shrinks at +-64 g because the intervals are narrower", "MEASURED_SOFTWARE", "ua.hc.*", "python -m crashguard.ua_conformal", "SUPPORTED" if hc else "NOT SUPPORTED"),
        ("B7: P3 raises critical delivery in steady state", "SIMULATED", "s11.diff.r16.steady.P3_minus_P1.*", "python -m crashguard.s11_sct", "SUPPORTED" if steady_gain else "NOT SUPPORTED"),
        ("B7: P2 (SCT) raises critical reach within 10 s in bursts against the severity table", "SIMULATED", "s11.diff.r16.burst.P2_minus_P1.*", "python -m crashguard.s11_sct", "PARTIAL" if burst_gain else "NOT SUPPORTED"),
        ("P3 raises critical reach within 30 s over P2 in bursts", "SIMULATED", "s11.diff.r16.burst.P3_minus_P2.*", "python -m crashguard.s11_sct", "SUPPORTED" if p3p2 else "NOT SUPPORTED"),
        ("SCT improves on a severity table with spaced retries in bursts (N26)", "SIMULATED", "s13.*", "python -m crashguard.s13_spaced_table", mp[st["N26"]]),
        ("The assumed duty-cycle limit (1% default; not verified for India) is never exceeded in any simulated run (independent scan)", "SIMULATED", "s11.duty.*", "python -m crashguard.s11_sct", "SUPPORTED" if duty0 else "NOT SUPPORTED"),
        ("The alert protocol model satisfies the replay, forgery, spoofed-ACK, counter and CANCEL properties within its bounds (N27)", "ANALYTICAL (bounded model check)", "s12.*", "python -m crashguard.protocol_check", mp[st["N27"]]),
        ("The abstract base rule agrees with the reference verifier on the mapped attack cases", "ANALYTICAL vs SIMULATED", "s12.crosscheck.*", "python -m crashguard.protocol_check", "PARTIAL" if cc[0] != cc[1] else "SUPPORTED"),
        ("The attack suite behaves as designed", "SIMULATED", "attacks.cases_total, attacks.cases_matching_expected, docs/01_protocol/ATTACK_CASES.md", "python -m crashguard.attacks; python -m crashguard.attack_doc",
         "SUPPORTED" if _v(r, "attacks.cases_total") == _v(r, "attacks.cases_matching_expected") else "PARTIAL"),
        ("The C code of the forests, severity.h and the N14 estimator equals the Python reference on the real inputs (differences below 5e-5; gcc under WSL; Windows rows NOT_RUN where blocked); one synthetic saturated-pulse check of the N14 estimator fails", "MEASURED_SOFTWARE", "cchecks.*, export.*, candidate.*", "scripts/c_checks.sh; python -m crashguard.merge_c_checks",
         "PARTIAL" if r.r.get("cchecks.wsl2_ubuntu_gcc.all_passed", {}).get("value") is False else "SUPPORTED"),
        ("The preregistered tests of H-a, H-b (the escalation part) and H-c still hold after a Holm correction over the three hypotheses (T14); the airtime-cap part of H-b is PARTIAL (the cap barely binds)", "MEASURED_SOFTWARE", "t14.*", "python -m crashguard.stats_audit", "SUPPORTED" if holm else "NOT SUPPORTED"),
        ("T1: at the same escalation P3 lowers mis-triage beyond what lowering the thresholds of the plain table does (preregistered rule)", "MEASURED_SOFTWARE + SIMULATED", "t1.*", "python -m crashguard.t1_equal_escalation", "SUPPORTED" if t1_win else "NOT SUPPORTED"),
        ("T2: the interval family has a smaller mis-triage against escalation trade-off area than the point-class family", "MEASURED_SOFTWARE", "t2.*", "python -m crashguard.t2_pareto", "SUPPORTED" if t2_win else "NOT SUPPORTED"),
        ("T3: P3 costs less than P1 when a missed severe event costs several times a false escalation (break-even ratio above the observed-mix value; not against the equal-escalation table)", "MEASURED_SOFTWARE (assumed costs)", "t3.*", "python -m crashguard.t3_cost",
         "PARTIAL" if be_lo is not None and not t3e else ("SUPPORTED" if t3e else "NOT SUPPORTED")),
        ("T4: SCT reaches the base as often as the table for a single car at 60% loss; with quick retries it does", "SIMULATED + ANALYTICAL", "t4.b.*", "python -m crashguard.t4_clarify", "PARTIAL" if (not t4b and t4q) else ("SUPPORTED" if t4b else "NOT SUPPORTED")),
        ("T5: the headline recall is lower on the test set without window-level near-duplicates (the standard set stays primary)", "MEASURED_SOFTWARE (exploratory)", "t5.*", "python -m crashguard.t5_strict", "SUPPORTED" if t5 else "NOT SUPPORTED"),
        ("T6: H-a survives every shift of the delta-V class limits tested; H-c survives all but two (all limits down by 2 km/h, the middle limit down by 2 km/h)", "MEASURED_SOFTWARE", "t6.*", "python -m crashguard.t6_thresholds", "PARTIAL" if t6a and not t6c else ("SUPPORTED" if t6a and t6c else "NOT SUPPORTED")),
        ("T7: a conformal variant restores the N20 false-alarm guarantee at alpha 5%", "MEASURED_SOFTWARE (exploratory)", "t7.b.*", "python -m crashguard.t7_conformal_variants", "SUPPORTED" if t7 else "NOT SUPPORTED"),
        ("T8: P3 beats P1 in critical reach within 10 s in most cells of the simulator sweep (not in every cell: it loses in steady cells at high loss)", "SIMULATED", "t8.count.*", "python -m crashguard.t8_sweep",
         "SUPPORTED" if (t8n is not None and t8c and t8n > t8c / 2) else "NOT SUPPORTED"),
        ("T9: the flash and the severity hold carry the SCT gain in bursts", "SIMULATED (exploratory)", "t9.diff.*", "python -m crashguard.t9_ablations", "SUPPORTED" if t9 else "NOT SUPPORTED"),
        ("T9: the reserved duty share changes critical reach in the cells tested", "SIMULATED (exploratory)", "t9.diff.*.no_reserve_minus_full.*", "python -m crashguard.t9_ablations", "NOT SUPPORTED" if t9r else "PARTIAL"),
        ("T12: a CANCEL that overtakes its alert is lost in the design and kept when the base remembers it (model)", "ANALYTICAL (bounded model check)", "s12x.*", "python -m crashguard.protocol_check_ext", "SUPPORTED" if t12 else "NOT SUPPORTED"),
        ("T11: the ten designed test cases behave as expected (not independent attackers)", "SIMULATED", "attacks_x.*", "python -m crashguard.attacks_extra", "SUPPORTED" if ax else "PARTIAL"),
        ("T13: the finding repeats on a second public dataset", "NOT_RUN", "t13.*", "python -m crashguard.t13_second_dataset", "NOT SUPPORTED"),
        ("The integrated system is evaluated end to end on hardware", "NOT_RUN", "hw.*", "merge/ingest_hardware.py", "NOT SUPPORTED"),
    ]


def render(r: Res) -> str:
    lines = ["## Claim table (generated by `python -m crashguard.claim_table` from `results/results.json`)", "",
             "| Claim | Label | Source (keys or file) | Command | Verdict |", "|---|---|---|---|---|"]
    for claim, label, src, cmd, ver in verdicts(r) + V2.v2_rows(r) + JP.jp_rows(r):
        lines.append(f"| {claim} | {label} | `{src}` | `{cmd}` | **{ver}** |")
    lines += ["", "SUPPORTED = the claim as worded has software evidence and meets any rule fixed in advance (for a SIMULATED or ANALYTICAL row it holds in that simulation or model, not in the field); PARTIAL = part of the claim fails, or it rests on a simulation with assumed values that the claim goes beyond; NOT SUPPORTED = tried and not cleared, or no evidence. No hardware result is used. Rows about delta-V classes (N14, N24, H-a to H-c, T1 to T3, T6) use NHTSA crash tests, mostly high-speed barrier tests, which are not representative of all real crashes. Rows from the T block marked EXPLORATORY were not preregistered. The v2 rows (preregistered in docs/02_preregistration/PREREGISTRATION_V2.md) also use MIXED = one part of a two-part criterion holds, or the criterion holds but the Holm-adjusted p-value is not below 0.05."]
    lines.append(V2.wording(r))
    lines.append(JP.wording(r))
    return "\n".join(lines)


def main() -> None:
    r = Res()
    replace_block(DOC, START, END, render(r))
    print(f"wrote the claim table into {DOC}")


if __name__ == "__main__":
    main()
