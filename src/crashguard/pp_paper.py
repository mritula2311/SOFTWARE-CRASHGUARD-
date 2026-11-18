"""P3 (paper prompt): numbers, tables and figures of the combined paper, generated from ``results/results.json`` only.

    python -m crashguard.pp_paper numbers   # paper/generated/numbers.tex and the table files
    python -m crashguard.pp_paper figures   # results/figures/pp_*.{png,pdf} (300 dpi) copied to paper/figures/

Every number in ``paper/main.tex`` and ``paper/supplement.tex`` is a macro defined here. A macro is a (name, key, format) entry or a derived value computed from keys; a missing key stops the run.
Formats: i = integer with thin spaces, d1..d4 = decimals, p0/p1 = percent without the sign (value times 100), s = text, m = minus sign as math ($-$), sg3/sg4 = signed decimals.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "results.json"
GEN = ROOT / "paper" / "generated"
FIG = ROOT / "results" / "figures"
PFIG = ROOT / "paper" / "figures"
CB = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "red": "#D55E00", "purple": "#CC79A7", "sky": "#56B4E9", "yellow": "#F0E442", "black": "#000000", "grey": "#7F7F7F"}


def load() -> dict:
    return {e["name"]: e["value"] for e in json.loads(RES.read_text(encoding="utf-8"))}


def fmt(v, f: str) -> str:
    if f == "s":
        return str(v).replace("_", r"\_").replace("%", r"\%")
    x = float(v)
    neg = x < 0
    if f == "i":
        s = f"{abs(round(x)):,}".replace(",", r"\,")
    elif f.startswith("d"):
        s = f"{abs(x):.{int(f[1])}f}"
    elif f.startswith("p"):
        s = f"{abs(100 * x):.{int(f[1])}f}"
    elif f.startswith("sg"):
        s = f"{abs(x):.{int(f[2])}f}"
        return ("$-$" if neg else "+") + s
    else:
        raise ValueError(f)
    return ("$-$" + s) if neg else s


def spec(R: dict) -> list[tuple[str, object, str]]:
    """(macro, value or key, format). A string value that is a key of R is read from R."""

    def k(key):
        if key not in R:
            raise KeyError(key)
        return R[key]

    def cfg_range(key):  # 'kx134 +-32 g at 100 Hz' -> 32
        return float(re.search(r"\+-([\d.]+) g", k(key)).group(1))

    S: list[tuple[str, object, str]] = []

    def add(name, v, f):
        S.append((name, k(v) if isinstance(v, str) and v in R else v, f))

    # ---- C1: audit
    add("VzGroups", "leakage.exact_hash_groups_across_splits", "i")
    add("VzGroupEvents", "leakage.cross_split_group_events.total", "i")
    add("VzEvSup", "vz.v4.n_events.supplied", "i")
    add("VzEvNear", "vz.v4.n_events.near", "i")
    add("VzEvExact", "vz.v4.n_events.exact", "i")
    add("VzTestExact", k("vz.v4.n_events.supplied") - k("vz.v4.n_events.exact"), "i")
    add("VzNearBoth", "dupscan.neardup.n_both", "i")
    add("VzNearScanned", "dupscan.neardup.n_scanned", "i")
    add("VzNearShare", k("dupscan.neardup.n_both") / k("dupscan.neardup.n_scanned"), "p1")
    add("VzRecSup", "vz.v4.rf15.supplied.sys_recall", "d3")
    add("VzRecNear", "vz.v4.rf15.near.sys_recall", "d3")
    add("VzROneSup", "vz.v4.rf15.supplied.recall_at_1pct", "d3")
    add("VzROneNear", "vz.v4.rf15.near.recall_at_1pct", "d3")
    # ---- C2: sensing
    add("SevTests", "sevstudy.n_tests", "i")
    add("DvSixteen", "sevstudy.grid.r16.f100.dv_within10", "p1")
    add("DvThirtyTwoA", "sevstudy.grid.r32.f100.dv_within10", "p1")
    add("DvThirtyTwoB", "sevstudy.grid.r32.f200.dv_within10", "p1")
    add("DvSixtyFourA", "sevstudy.grid.r64.f100.dv_within10", "p1")
    add("DvSixtyFourB", "sevstudy.grid.r64.f200.dv_within10", "p1")
    add("ModeFrontReal", cfg_range("p.b2.frontal_barrier.smallest.config"), "i")
    add("ModePoleReal", cfg_range("p.b2.pole.smallest.config"), "i")
    add("ModeFrontN", "p.b2.frontal_barrier.n_records", "i")
    add("ModePoleN", "p.b2.pole.n_records", "i")
    add("ModeSideN", "p.b2.side.n_records", "i")
    add("ModeOtherN", "p.b2.other.n_records", "i")
    add("ModeFrontCfg", "p.b2.frontal_barrier.n_configs_meeting", "i")
    add("ModePoleCfg", "p.b2.pole.n_configs_meeting", "i")
    add("PoolN", "f.c.generator.n_records_fit", "i")
    add("CellsN", "pa.hA1.n_cells", "i")
    add("RefitFrontSyn", "pp.p0.grid.frontal_barrier.synthetic_smallest_range", "i")
    add("RefitFrontStep", "pp.p0.grid.frontal_barrier.step_difference", "i")
    add("RefitHolm", "pp.p0.holm.hc3.p_holm_refit", "d3")
    add("RefitVerdict", "pp.p0.holm.hc3.verdict_refit", "s")
    add("OrigVerdict", "pp.p0.holm.hc3.verdict_original", "s")
    add("RefitPassed", "pp.p0.fidelity.modes_passed", "s")
    add("RefitNFit", "pp.p0.refit.n_records_fit", "i")
    add("RefitNGate", "pp.p0.refit.n_records_gate", "i")
    add("RefitKsFront", max(k(f"pp.p0.fidelity.frontal_barrier.{d}.ks_D_heldout") for d in ("peak_g", "duration_ms", "dv_kmh", "asym", "shape")), "d3")
    add("RefitPoleSyn", "pp.p0.grid.pole.synthetic_smallest_range", "i")
    add("RestMedRest", "n14x.R.r16.M+.median", "d1")
    add("RestMedSpl", "n14x.R.r16.SP.median", "d1")
    add("RestMedPlain", "n14x.R.r16.B.median", "d1")
    add("RestPNinetyRest", "n14x.R.r16.M+.p90", "d1")
    add("RestPNinetyPlain", "n14x.R.r16.B.p90", "d1")
    add("RestPNinetySpl", "n14x.R.r16.SP.p90", "d1")
    add("RestThirtyTwoGain", -k("n14x.R.r32.paired.M+_vs_B.d_median"), "d1")
    add("RestThirtyTwoUpper", "n14x.R.r32.paired.M+_vs_B.d_median_hi", "sg4")
    add("RestThirtyTwoSplLo", "n14x.R.r32.paired.M+_vs_SP.d_median_lo", "d1")
    add("RestThirtyTwoSplHi", "n14x.R.r32.paired.M+_vs_SP.d_median_hi", "sg4")
    add("RestSixtyFourDiff", "n14x.R.r64.paired.M+_vs_B.d_median", "sg3")
    # ---- C3: detection
    add("PfourFlash", "p.p4a.selected.flash_bytes", "i")
    add("PfourRefFlash", "p.p4a.reference.flash_bytes", "i")
    add("PfourRatio", "p.p4a.flash_ratio_selected_over_reference", "p0")
    add("PfourApLoss", "p.p4a.dedup.ap_loss", "d4")
    add("PfourValAp", "p.p4a.selected.val_ap", "d3")
    add("PfourRefValAp", "p.p4a.reference.val_ap", "d3")
    add("PfourRecOne", "p.p4a.selected.test_recall_1pct", "d3")
    add("PfourRefRecOne", "p.p4a.reference.test_recall_1pct", "d3")
    add("PfourConfigs", "p.p4a.n_configurations", "i")
    add("PrevOne", "prev.rf15.t1.pi0p02pct.ppv", "p2")
    add("PrevFive", "prev.rf15.t5.pi0p02pct.ppv", "p2")
    add("EarlyGainOne", "s6.a1.mean5.d.E_minus_F.recall", "sg4")
    add("EarlyGainFive", "s6.a5.mean5.d.E_minus_F.recall", "sg4")
    add("EarlyTimeOne", -k("s6.a1.mean5.d.E_minus_Ep.time") / 1000.0, "d2")
    add("TrigBaseRecall", "n15.baseline.t1.test_recall.mean", "d3")
    # ---- C4: protocol
    add("BmcStates", "f.b1.ext.design.states", "i")
    add("BmcDepth", "f.b1.ext.design.depth", "i")
    add("BmcProps", "f.b1.ext.design.properties_checked", "i")
    add("SuiteTotal", "sh.s4.suite.total", "i")
    add("SuiteAttempts", "sh.s4.scenarios.attack_attempts_counted", "i")
    add("SuiteAccepted", "sh.s4.scenarios.attacks_accepted", "i")
    add("RFourShared", "ar.r4.held.v3.shared_key_event_ack.max_suppressed_fraction", "d2")
    add("RFourPer", "ar.r4.held.v3.per_vehicle_one_compromised.max_suppressed_fraction", "d2")
    add("RFourSharedActions", "ar.r4.held.v3.shared_key_event_ack.attacker_actions_for_max", "i")
    add("ROneAvail", k("ar.r1.hR1a.min_availability"), "p1")
    add("ROneWindow", "ar.r1.design.W_s", "i")
    add("ROneRing", "ar.r1.design.R_entries", "i")
    add("ROneRatio", "ar.r1.hR1c.ratio", "i")
    add("ROneRate", "ar.r1.hR1b.max_replay_rate", "d3")
    add("RTwoGain", "ar.r2.hR2a.mean_gain", "d3")
    add("RTwoCells", "ar.r2.hR2a.cells_gain5_of_16", "i")
    add("RTwoP", "ar.r2.hR2a.p_raw", "d2")
    add("ForgeOne", "v2.e.hE2.log2_attempts_for_1e6_t8", "d1")
    add("ForgeExp", "v2.e.forgery.t8.log2_expected_attempts", "i")
    phr = {"verified": "proved", "falsified": "refuted", "timeout": "not decided within the time limit", "no_result": "not decided", "not_run": "not run"}
    add("VariantBoot", phr[k("pp.c4.variant.car_model.boot.L5_ids")], "s")
    add("VariantFrozen", phr[k("pp.c4.variant.car_model.frozen.L5_ids")], "s")
    add("VariantFull", phr[k("pp.c4.variant.full_model.L5_ids")], "s")
    add("TimedRuns", "r3.t2.timed.duty.runs", "i")
    add("TimedDOneSix", "r3.t2.timed.D1.k6.worst_s", "d2")
    add("TimedQuickFour", "r3.t2.timed.quick.k4.worst_s", "d2")
    # ---- C5: two-stage alert
    add("RThreeEarly", "ar.r3.a1.earlier_median_s_p0", "d2")
    add("RThreeEarlyLoss", "ar.r3.a1.earlier_median_s_p0.3", "d2")
    add("RThreeRetract", "ar.r3.a1.retraction_share", "p1")
    add("RThreeAir", "ar.r3.a1.air_ratio_p0", "p0")
    add("RThreeAirMax", max(k(f"ar.r3.a1.air_ratio_p{p}") for p in ("0", "0.1", "0.3", "0.6")), "p0")
    add("RThreeDelMin", min(k(f"ar.r3.a1.delivery_diff_p{p}") for p in ("0", "0.1", "0.3", "0.6")), "sg3")
    add("RThreeFlashMs", "ar.r3.airtime.flash_ms", "i")
    add("RThreeAlertMs", "ar.r3.airtime.alert_ms", "i")
    add("RThreeEarlyDecMs", "ar.r3.a1.early_median_ms", "i")
    add("TThreeEarlier", "r3.t3.a1.earlier_ms_median", "i")
    add("TThreeRetract", "r3.t3.a1.retraction_share", "p1")
    add("TThreeRetractHi", "r3.t3.a1.retraction_share_hi", "p1")
    add("TThreeFiveRetract", "r3.t3.a5.retraction_share", "p1")
    add("TThreeNhtsaFifty", "r3.t3.nhtsa.frontal.agreement_at_50ms", "p0")
    add("TThreeNhtsaHundred", "r3.t3.nhtsa.frontal.agreement_at_100ms", "p0")
    add("TThreeNhtsaTwo", "r3.t3.nhtsa.frontal.agreement_at_200ms", "p0")
    add("TThreeNhtsaN", "r3.t3.nhtsa.frontal.n_pulses", "i")
    add("TThreeVzN", "r3.t3.vz.n_events", "i")
    add("TThreeVzClass", "r3.t3.vz.class_agreement", "p1")
    add("TOneEarlier", "r3.t1.T1c.H.earlier_median_s", "d2")
    add("TOneAirL", "r3.t1.T1c.L.extra_air_ratio", "p0")
    add("TOneAirH", "r3.t1.T1c.H.extra_air_ratio", "p0")
    add("TOneDelH", "r3.t1.T1c.H.delivery_diff", "sg3")
    from crashguard.lora import airtime_ms

    add("FlashShareSeven", airtime_ms(14, 7) / airtime_ms(97, 7), "p0")
    add("FlashShareNine", airtime_ms(14, 9) / airtime_ms(97, 9), "p0")
    add("NsVerdict", "pp.p1.verdict", "s")
    add("NsRuns", 2 * 2 * 2 * 4 * 60, "i")
    add("NsSupported", "pp.p1.n_tests_supported", "i")
    for sf, W in ((7, "Seven"), (9, "Nine")):
        add(f"NsEarlySf{W}", "pp.p1.sf%d.calib.p0.earlier_median_s" % sf, "d2")
        add(f"NsAirLoSf{W}", min(max(k(f"pp.p1.sf{sf}.{st}.p{p}.extra_air_ratio") for p in ("0", "0.1", "0.3", "0.6")) for st in ("calib", "shipped")), "p0")
        add(f"NsAirHiSf{W}", max(max(k(f"pp.p1.sf{sf}.{st}.p{p}.extra_air_ratio") for p in ("0", "0.1", "0.3", "0.6")) for st in ("calib", "shipped")), "p0")
        add(f"NsDelMinSf{W}", min(min(k(f"pp.p1.sf{sf}.{st}.p{p}.delivery_diff") for p in ("0", "0.1", "0.3", "0.6")) for st in ("calib", "shipped")), "sg3")
        add(f"NsDelMaxSf{W}", max(max(k(f"pp.p1.sf{sf}.{st}.p{p}.delivery_diff") for p in ("0", "0.1", "0.3", "0.6")) for st in ("calib", "shipped")), "sg3")
    add("NsDropMax", max(k(f"pp.p1.sf{sf}.{st}.dropped_share") for sf in (7, 9) for st in ("calib", "shipped")), "p1")
    add("NsDutyMax", max(k(f"pp.p1.sf{sf}.{st}.max_phy_airtime_hour_s") for sf in (7, 9) for st in ("calib", "shipped")), "d1")
    # ---- C6: retry policies
    add("XCustomDOneGain", "rd.x13.custom.d1b.pt", "sg3")
    add("XNsDOneGain", "rd.x13.ns3.d1b.pt", "sg3")
    add("XCustomMinCell", "rd.x13.custom.d1a.min_cell_diff", "sg3")
    add("XNsMinCell", "rd.x13.ns3.d1a.min_cell_diff", "sg3")
    add("XNsCellsFail", "rd.x13.ns3.d1a.cells_failing", "i")
    for nm, key in (("CustomDOne", "rd.x13.custom.mean_delivery.D1"), ("CustomQuick", "rd.x13.custom.mean_delivery.quick"), ("CustomPOne", "rd.x13.custom.mean_delivery.P1"), ("NsDOne", "rd.x13.ns3.mean_delivery.d1"),
                    ("NsQuick", "rd.x13.ns3.mean_delivery.quick"), ("NsPOne", "rd.x13.ns3.mean_delivery.p1"), ("NsLora", "rd.x13.ns3.mean_delivery.lorawan"), ("NsNessa", "rd.x13.ns3.mean_delivery.nessa")):
        add("X" + nm, key, "d3")
    add("TOneN", "r3.t1.n_heldout_devices", "i")
    add("TOneNL", "r3.t1.L.n_devices", "i")
    add("TOneNM", "r3.t1.M.n_devices", "i")
    add("TOneNH", "r3.t1.H.n_devices", "i")
    add("TOneShareH", k("r3.t1.H.n_devices") / k("r3.t1.n_heldout_devices"), "p0")
    for g in "LMH":
        add(f"TOneDiff{g}", "r3.t1.T1a.%s.diff" % g, "sg3")
    for pol, W in (("D1", "DOne"), ("quick", "Quick"), ("P1", "POne"), ("P4", "PFour"), ("P0", "PZero"), ("khan", "Khan"), ("nessa", "Nessa")):
        add(f"TOneDel{W}", "r3.t1.H.deliv.%s" % pol, "p1")
    add("TOneDelZ", "r3.t1.explore.H.deliv.Z0", "p1")
    add("TOneBDiff", "r3.t1.T1b.diff", "sg3")
    add("LinkMedLoss", "pp.c6.links.median_loss", "p0")
    add("LinkMeanLoss", "pp.c6.links.mean_loss", "p0")
    add("LinkAuto", "pp.c6.links.lag1_autocorr", "d2")
    add("LinkCond", "pp.c6.links.p_loss_given_prev_loss", "d2")
    add("LinkPooled", "pp.c6.links.pooled_loss", "d2")
    add("LinkBurst", "pp.c6.links.burst_mean", "d1")
    add("ZMaxAir", "pp.c6.z0.max_air_one_alert_s", "d1")
    add("ZMaxShareOne", "pp.c6.z0.max_air_share_of_1pct_budget", "p1")
    add("ZMaxShareTen", "pp.c6.z0.max_air_share_of_10pct_budget", "p1")
    add("ZAirH", "pp.c6.z0.H.Z0.mean_air_per_alert_s_median", "d2")
    add("DAirH", "pp.c6.z0.H.D1.mean_air_per_alert_s_median", "d2")
    add("ZLate", "pp.c6.z0.invariant_late_delivery", "i")
    # ---- C7: simulated hardware-format logs
    add("ShSideBelow", "sh.s2.hS1.n_variants_below_0.90", "i")
    add("ShFlipAcc", "sh.s2.F_x.side_acc", "d2")
    add("ShHzAcc", "sh.s2.S_10Hz.side_acc", "d2")
    add("ShFar", "sh.s2.supplied.far", "d2")
    add("ShLatency", "sh.s3.h7.supplied.median_first_try_ms", "i")
    add("ShSwRed", "sh.s5.base_range_1.5_4.0.pooled.far_reduction", "d2")
    add("ShSwLoss", "sh.s5.base_range_1.5_4.0.pooled.recall_loss", "d2")
    add("ShFarOk", "sh.s2.hS2.n_variants_far_ok", "i")
    # ---- negatives
    add("NegGateAuc", "ph.gate.FAM.side.auc_D1", "d2")
    add("NegSurrAuc", "ph.surrogate.auc", "d3")
    add("NegSctSevTable", "t4.b.loss60.P1.reach10_critical", "d3")
    add("NegSctSct", "t4.b.loss60.P2.reach10_critical", "d3")
    add("NegOsdrGain", "pa.hA1.n_cells_gain5", "i")
    add("NegOsdrLose", "pa.hA1.n_cells_lose2", "i")
    add("NegConfFar", "p.p4c.loco.a5.V0.false_alarm_rate", "d3")
    add("NegBtwoGain", "f.b2.hB2.n_cells_gain5", "i")
    add("NegBtwoCells", "f.b2.hB2.n_cells", "i")
    add("NegSlotLose", "f.g.g3.hG3a.n_cells_lose2", "i")
    add("AOneAirNine", "a4.a1.ns3.sf9.shipped.p0.extra_air_ratio", "d2")
    add("AOneAirNineR", "a4.a1.ns3.sf9.shipped.p0.extra_air_ratio_r3", "d2")
    add("AOneProv", "a4.a1.trace.hA1b.diff", "p1")
    add("AOneWorst", "a4.a1.ns3.sf9.shipped.p0.6.delivery_diff", "p1")
    add("ATwoGain", "a4.a2.reserve.hA2a.diff", "p1")
    add("ATwoOne", "a4.a2.reserve.share_one_gateway", "p0")
    # ---- round 5 (docs/02_preregistration/PREREGISTRATION_V16.md)
    add("RFiveOneAcc", "r5.l1.held.sim.pooled_acc_l1", "d3")
    add("RFiveOneRaw", "r5.l1.held.sim.pooled_acc_raw", "d2")
    add("RFiveOneNhtsa", "r5.l1.held.nhtsa.bacc_l1", "d3")
    add("RFiveOneNhtsaRaw", "r5.l1.held.nhtsa.bacc_raw", "d2")
    add("RFiveMirrorAcc", "r5.l1.held.M_flip_x.acc_l1", "d2")
    add("RFiveThreeRecB", "r5.l3.held.hL3.recall_b", "d3")
    add("RFiveThreeRecA", "r5.l3.held.hL3.recall_a", "d3")
    add("RFiveThreeRatio", "r5.l3.energy.ratio_lo", "d2")
    add("RFiveThreeShare", "r5.l3.energy.active_share", "d2")
    add("RFiveFourGain", "r5.l4.ns3.edge.mean_diff", "p1")
    add("RFiveTwoFa", "r5.l2.held.hL2a.new_rate", "d4")
    add("RFiveTwoFaBase", "r5.l2.held.hL2a.base_rate", "d4")
    add("RFiveTwoFall", "r5.l2.held.hL2b.pt", "p1")
    add("RFiveSixKTwo", "r5.l6.main.k200.diff_crash_minus_pop", "p1")
    add("RFiveSixKFour", "r5.l6.main.k400.diff_crash_minus_pop", "p1")
    add("RFiveEightQuar", "r5.l8.b.quarantined", "i")
    add("RFiveNineRho", "r5.l9.rho.act_vs_wait", "d2")
    add("RFiveElevenMir", "r5.l11.held.mirror_x.sensitivity", "p0")
    add("RFiveElevenFd", "r5.l11.held.false_detection", "p0")
    add("RFiveElevenAccX", "r5.l11.held.acc_only_x.sensitivity", "p0")
    add("RFiveElevenAccY", "r5.l11.held.acc_only_y.sensitivity", "p0")
    add("RFiveElevenN", "r5.l11.held.n_installations", "i")
    add("RFiveSupp", "r5.verdict.n_supported", "i")
    add("RFiveHar", "r5.l10.har.n_test_windows", "i")
    # ---- final verification run (keys vf.*, scripts/vf_*.py): ledger totals, tool versions, a few supplement numbers
    for nm, key in [("LedgerN", "preregistered"), ("LedgerRun", "run"), ("LedgerSupp", "supported"), ("LedgerNot", "not_supported"), ("LedgerPartly", "partly"), ("LedgerNotRun", "not_run"),
                    ("LedgerConfN", "confirmatory_rows"), ("LedgerConfSupp", "confirmatory_supported"), ("LedgerVersions", "versions")]:
        add(nm, f"r6.ledger.all.{key}", "i")
    for nm, key in [("EnvPython", "python"), ("EnvNumpy", "numpy"), ("EnvScipy", "scipy"), ("EnvSklearn", "scikit-learn"), ("EnvTamarin", "tamarin"), ("EnvMaude", "maude"), ("EnvProverif", "proverif")]:
        add(nm, f"vf.env.{key}", "s")
    add("VzCrashEvents", "leakage.cross_split_group_events.crash", "i")
    add("VzTestExactShare", (k("vz.v4.n_events.supplied") - k("vz.v4.n_events.exact")) / k("vz.v4.n_events.supplied"), "p2")
    add("DvSettingsMeet", "sevstudy.needed.point.count", "i")
    add("DvSettingsAll", sum(1 for key in R if re.fullmatch(r"sevstudy\.grid\.r\d+\.f\d+\.dv_within10", key)), "i")
    add("RFiveFourEdge", "r5.l4.ns3.edge.mean_diff", "d3")
    add("RFiveFourEdgeLo", "r5.l4.ns3.edge.mean_diff_lo", "d3")
    add("RFiveFourWorst", "r5.l4.ns3.edge.worst_cell_lo", "d3")
    add("RFiveSevenSeq", "r5.l7.b.n_sequences", "i")
    add("RFiveEightMax", "r5.l8.a.max_high_confidence_forwards", "i")
    add("RFiveEightStates", "r5.l8.a.states_visited", "i")
    add("RFiveNineRhoLo", "r5.l9.rho.act_vs_wait_lo", "d2")
    add("RFiveNineRhoHi", "r5.l9.rho.act_vs_wait_hi", "d2")
    assert airtime_ms(15, 7) == airtime_ms(14, 7) and airtime_ms(15, 9) == airtime_ms(14, 9), "a 15-byte flash would change the airtime"
    add("FlashAirSeven", airtime_ms(14, 7), "d1")
    add("FlashAirNine", airtime_ms(14, 9), "d1")
    add("NsPatchRuns", sum(k(f"vf.ns3.{c}.identical") for c in ("R3_SF7_calib_p03_r3s", "R3_SF7_calib_p03_r3t", "R3_SF9_calib_p03_r3s", "R3_SF9_calib_p03_r3t")) + k("vf.ns3.D1_n80_p17_sf9_d05_b1.identical"), "i")
    # ---- round 6 (keys r6.*)
    ns = [f"r6.r1.ns3.sf{sf}.{st}.p{p}" for sf in (7, 9) for st in ("calib", "shipped") for p in ("0", "0.1", "0.3", "0.6")]
    add("RSixAirOverRThreeLo", min(k(c + ".air_over_r3") for c in ns), "d2")
    add("RSixAirOverRThreeHi", max(k(c + ".air_over_r3") for c in ns), "d2")
    add("RSixDeliveryGapMax", max(abs(k(c + ".delivery_diff")) for c in ns), "d4")
    add("RSixDeliveryLowerMin", min(k(c + ".delivery_diff_lo") for c in ns), "sg3")
    add("RSixNinePerDelivHi", max(k(c + ".air_per_delivered_over_r3") for c in ns if ".sf9." in c), "d2")
    add("RSixExtraAirMaxSfNine", max(k(c + ".extra_air_ratio") for c in ns if ".sf9." in c), "sg3")
    add("RSixExtraAirMinSfNine", min(k(c + ".extra_air_ratio") for c in ns if ".sf9." in c), "sg3")
    add("RSixTraceAirLowL", "r6.r1.trace.L.air_over_r3", "d2")
    add("RSixTraceAirHighH", "r6.r1.trace.H.air_over_r3", "d2")
    add("RSixSeqGain", "r6.r2.hR6_2.a_pt", "d1")
    add("RSixSeqGainLo", "r6.r2.hR6_2.a_lo", "d1")
    add("RSixSeqRetractRise", "r6.r2.hR6_2.b_pt", "p1")
    add("RSixSeqRetractHi", "r6.r2.hR6_2.b_hi", "p1")
    add("RSixFixedMeanMs", "r6.r2.held.mean_time_fixed_ms", "i")
    add("RSixHeldEvents", "r6.r2.held.n_events", "i")
    add("RSixForestBytes", "r6.fp.rodata.forest_bytes", "i")
    add("RSixFlashBytes", "r6.fp.image.flash_total_bytes", "i")
    add("RSixStackChain", "r6.fp.stack.micro_verify_chain_bytes", "i")
    add("RSixHmacCodeBytes", "r6.fp.code.hmac_sha256_path_bytes", "i")
    add("RSixBoundSevenR", "r6.b.extra.sf7.r3_lower_bound", "d3")
    add("RSixBoundNineR", "r6.b.extra.sf9.r3_lower_bound", "d3")
    add("RSixMicroOverRNine", "r6.b.extra.sf9.micro_over_r3", "d2")
    add("RSixQuarFrames", "r6.f3b.A_count_before_verification.shortest_attack_frames", "i")
    add("RSixRatchetSteps", "r6.f.h3a.ratchet_steps_bound", "i")
    add("RSixSupp", "r6.holm.n_supported", "i")
    add("RSixLedgerAdded", 7, "i")
    # ---- delta verification run (keys vf2.*, r6.ledger.*): audit versions, duty lockout, preemption, frame layout, ledger by round
    add("VzRecExact", "vz.v4.rf15.exact.sys_recall", "d3")
    add("VzROneExact", "vz.v4.rf15.exact.recall_at_1pct", "d3")
    add("VzRecNaive", "vf2.split.naive_random.sys_recall", "d3")
    add("VzROneNaive", "vf2.split.naive_random.recall_at_1pct", "d3")
    add("VzNaiveN", "vf2.split.naive_random.n_pseudo_test_mean", "i")
    add("DutyLockSeven", "vf2.duty.lockout.sf7.flash_s", "d1")
    add("DutyLockNine", "vf2.duty.lockout.sf9.flash_s", "d1")
    add("DutyEarlySeven", "vf2.duty.earliest_confirm.sf7.d1.median_s", "d1")
    add("DutyEarlyNine", "vf2.duty.earliest_confirm.sf9.d1.median_s", "d1")
    add("DutyDue", 1.808, "d3")
    add("DutyCritMs", k("vf2.duty.critical_airtime.d1.median_s") * 1000.0, "d1")
    add("DutyMaxSfTen", "vf2.duty.max_sf_condition_a.d10.median", "i")
    add("DutyStoredShare", "vf2.duty.stored.sf7.r3t.inside_lockout_share", "p0")
    add("PreemptEndNine", "vf2.preempt.saving.sf9.median.last_try_end_s", "d2")
    add("PreemptSaveTen", "vf2.preempt.saving.sf10.median.saved_airtime_s", "d2")
    add("PreemptCases", "vf2.preempt.cases", "i")
    add("FrameForgeSixty", "vf3.layout.forge.trial.n60.expected_years", "i")
    add("FrameForgeOne", "vf3.layout.forge.index.expected_years", "i")
    add("FrameAbstractRows", "vf3.layout.abstraction_rows", "i")
    add("RSixNsFrameBytes", "r6.r1.ns3.params.frame_bytes", "i")
    add("RSixPreregLo", 720, "i")
    add("RSixPreregHi", 780, "i")
    add("RSixFixedMedMs", "r6.r2.held.median_time_fixed_ms", "i")
    add("IndiaMaxSf", "vf3.india.max_sf_condition_a.d10.median", "i")
    add("IndiaErpLumped", "vf3.india.erp.lumped.dbm", "d1")
    add("IndiaReduceZero", "vf3.india.erp.direct.g0.0_l0.0.reduction_db", "d2")
    add("IndiaSfStep", "vf3.india.sf_equivalent_of_reduction_direct_0dbi", "d1")
    groups = {"A": ["V1", "V2", "V3", "V4", "V5"], "B": ["V7", "V11", "V12", "V13"], "C": ["V14"], "D": ["V15"], "E": ["V16"], "F": ["V17"]}
    for g, vs in groups.items():
        for nm, key in [("Pre", "preregistered"), ("Run", "run"), ("Supp", "supported"), ("Not", "not_supported"), ("Partly", "partly"), ("NotRun", "not_run")]:
            add(f"Lg{g}{nm}", sum(k(f"r6.ledger.{v}.{key}") for v in vs), "i")
    return S


def write_numbers(R: dict) -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by crashguard.pp_paper from results/results.json; do not edit"]
    seen = set()
    for name, v, f in spec(R):
        assert name not in seen and re.fullmatch(r"[A-Za-z]+", name), name
        seen.add(name)
        lines.append(f"\\newcommand{{\\{name}}}{{{fmt(v, f)}}}")
    (GEN / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("macros", len(seen))


# ------------------------------------------------------------------------------------------------ figures
def _save(fig, name: str) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    PFIG.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight")
        shutil.copy(FIG / f"{name}.{ext}", PFIG / f"{name}.{ext}")


def fig_arch() -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle

    layers = [("Sensing", [("MPU6050 ±16 g, 100 Hz;\nSW-420 switches", "I"), ("simulated hardware-\nformat logs", "S")]),
              ("Edge detector", [("2 g trigger, 14 features,\n15-tree forest, early exit", "I"), ("impact side\nfrom one IMU", "I")]),
              ("Severity", [("delta-V and ASI estimate,\nclass table", "I"), ("restoration;\nconformal interval", "I")]),
              ("Alert frame", [("97-byte alert, 26-byte ACK,\n14-byte provisional frame\nand CANCEL", "I"), ("two-stage alert (R3)", "S")]),
              ("Freshness and\nauthentication", [("HMAC-SHA256/64,\npersisted counter", "I"), ("GPS-time field (R1);\nper-vehicle ACK keys (R4)", "S")]),
              ("MAC and\nretry policy", [("duty-cycle bucket,\nretry policies", "S"), ("ns-3 and trace replay", "S")]),
              ("Base and ACK", [("reference verifier,\nidempotent re-ACK", "I"), ("ESP32 base with\nSX1278 radio", "D")])]
    col = {"I": CB["blue"], "S": CB["orange"], "D": CB["grey"]}
    lab = {"I": "implemented (code run on data)", "S": "simulated or modelled", "D": "design only"}
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.set_xlim(0, 10.8)
    ax.set_ylim(-0.4, len(layers) * 1.25 + 0.2)
    ax.axis("off")
    for i, (name, els) in enumerate(layers):
        y = (len(layers) - 1 - i) * 1.25 + 0.3
        ax.add_patch(FancyBboxPatch((0.05, y), 2.4, 1.0, boxstyle="round,pad=0.02", fc="#EEEEEE", ec="black", lw=0.8))
        ax.text(1.25, y + 0.5, name, ha="center", va="center", fontsize=7.5, weight="bold")
        for j, (txt, s) in enumerate(els):
            x = 2.7 + j * 4.0
            ax.add_patch(FancyBboxPatch((x, y), 3.85, 1.0, boxstyle="round,pad=0.02", fc=col[s], ec="black", lw=0.8, alpha=0.9))
            ax.text(x + 1.925, y + 0.5, txt, ha="center", va="center", fontsize=6.8, color="white" if s != "S" else "black")
        if i < len(layers) - 1:
            ax.annotate("", xy=(1.25, y - 0.22), xytext=(1.25, y - 0.02), arrowprops=dict(arrowstyle="->", lw=0.8))
    for k, (s, txt) in enumerate(lab.items()):
        ax.add_patch(Rectangle((0.2 + k * 3.6, -0.3), 0.35, 0.25, fc=col[s], ec="black", lw=0.6))
        ax.text(0.7 + k * 3.6, -0.17, txt, fontsize=7, va="center")
    _save(fig, "pp_arch")
    plt.close(fig)


def fig_heat() -> None:
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    d = pd.read_csv(ROOT / "results" / "tables" / "p_b2_table.csv")
    d = d[d.odr_hz <= 1000]
    rates = sorted(d.odr_hz.unique())
    ranges = sorted(d.range_g.unique())
    modes = [("frontal_barrier", "frontal barrier"), ("pole", "pole"), ("side", "side"), ("other", "other")]
    fig, axs = plt.subplots(1, 4, figsize=(7.4, 2.7), sharey=True)
    for ax, (m, nm) in zip(axs, modes):
        M = np.full((len(ranges), len(rates)), np.nan)
        for i, r in enumerate(ranges):
            for j, h in enumerate(rates):
                s = d[(d.range_g == r) & (d.odr_hz == h)][f"{m}_share"]
                if len(s):
                    M[i, j] = s.max()
        im = ax.imshow(M, origin="lower", aspect="auto", vmin=0, vmax=1, cmap="cividis")
        ax.set_xticks(range(len(rates)))
        ax.set_xticklabels([str(int(h)) for h in rates], rotation=60, fontsize=6)
        ax.set_yticks(range(len(ranges)))
        ax.set_yticklabels([f"{r:g}" for r in ranges], fontsize=6)
        ax.set_title(nm, fontsize=8)
        ax.set_xlabel("output data rate (Hz)", fontsize=7)
    axs[0].set_ylabel("range (± g)", fontsize=7)
    fig.colorbar(im, ax=axs, fraction=0.025, pad=0.01, label="share within ±10%\nof reference delta-V")
    _save(fig, "pp_heat")
    plt.close(fig)


def fig_rest(R: dict) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.6))
    labels = [("B", "plain", CB["grey"]), ("SP", "spline", CB["orange"]), ("M+", "restoration", CB["blue"])]
    for ax, stat, yl in ((axs[0], "median", "median delta-V error (%)"), (axs[1], "p90", "90th percentile error (%)")):
        for i, (key, nm, c) in enumerate(labels):
            ax.bar(np.arange(3) + (i - 1) * 0.27, [R[f"n14x.R.r{r}.{key}.{stat}"] for r in (16, 32, 64)], 0.26, label=nm, color=c)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["±16 g", "±32 g", "±64 g"], fontsize=7)
        ax.set_ylabel(yl, fontsize=7)
        ax.tick_params(labelsize=7)
    axs[0].legend(fontsize=6)
    _save(fig, "pp_rest")
    plt.close(fig)


def fig_p4a() -> None:
    import matplotlib.pyplot as plt
    import pandas as pd

    d = pd.read_csv(ROOT / "results" / "tables" / "p4a_sweep_validation.csv")
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for q, c, mk in (("float", CB["grey"], "o"), ("q16", CB["blue"], "s")):
        s = d[d.q == q]
        ax.scatter(s.flash_bytes / 1000.0, s.val_ap, s=6, c=c, marker=mk, label="32-bit float nodes" if q == "float" else "16-bit nodes", alpha=0.7)
    ax.set_xlabel("flash estimate (kB)", fontsize=7)
    ax.set_ylabel("validation average precision", fontsize=7)
    ax.set_ylim(0.85, 0.95)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6)
    _save(fig, "pp_p4a")
    plt.close(fig)


def fig_r3(R: dict) -> None:
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.5), gridspec_kw=dict(width_ratios=[1.6, 1]))
    ax = axs[0]
    tE = R["ar.r3.a1.early_median_ms"] / 1000.0
    a_fl, a_al = R["ar.r3.airtime.flash_ms"] / 1000.0, R["ar.r3.airtime.alert_ms"] / 1000.0
    ax.broken_barh([(0, 1.808)], (2.0, 0.5), color="#DDDDDD")
    ax.text(0.9, 2.25, "full-window decision at 1.8 s", ha="center", va="center", fontsize=6)
    ax.broken_barh([(tE + 0.008, a_fl)], (1.2, 0.5), color=CB["orange"])
    ax.text(tE + 0.008 + a_fl + 0.04, 1.45, "provisional frame (14 B)", fontsize=6, va="center")
    ax.broken_barh([(1.808, a_al)], (0.4, 0.5), color=CB["blue"])
    ax.text(1.808 + a_al + 0.04, 0.65, "full alert (97 B)", fontsize=6, va="center")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks([2.25, 1.45, 0.65])
    ax.set_yticklabels(["window", "two-stage", "single-stage"], fontsize=7)
    ax.set_xlabel("time after the crash (s), SF7, no loss", fontsize=7)
    ax.set_xlim(0, 2.6)
    ax.tick_params(labelsize=7)
    ax = axs[1]
    for sf, c in ((7, CB["blue"]), (9, CB["red"])):
        v = 100 * max(R[f"pp.p1.sf{sf}.{st}.p{p}.extra_air_ratio"] for st in ("calib", "shipped") for p in ("0", "0.1", "0.3", "0.6"))
        ax.bar(f"SF{sf}", v, color=c, width=0.5)
    ax.axhline(40, color="black", ls="--", lw=0.8)
    ax.text(-0.45, 41.5, "limit 40%", fontsize=6, ha="left")
    ax.set_ylabel("extra airtime, two-stage over single (%)", fontsize=7)
    ax.tick_params(labelsize=7)
    _save(fig, "pp_r3")
    plt.close(fig)


def fig_xsim(R: dict) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    pol = [("P1 (severity table)", R["rd.x13.custom.mean_delivery.P1"], R["rd.x13.ns3.mean_delivery.p1"]), ("quick retries", R["rd.x13.custom.mean_delivery.quick"], R["rd.x13.ns3.mean_delivery.quick"]),
           ("Nessa-style", R["rd.x13.custom.mean_delivery.nessa"], R["rd.x13.ns3.mean_delivery.nessa"]), ("D1", R["rd.x13.custom.mean_delivery.D1"], R["rd.x13.ns3.mean_delivery.d1"]),
           ("LoRaWAN standard", R["rd.x13.custom.mean_delivery.khan"], R["rd.x13.ns3.mean_delivery.lorawan"])]
    x = np.arange(len(pol))
    ax.bar(x - 0.2, [p[1] for p in pol], 0.38, label="custom simulator", color=CB["blue"])
    ax.bar(x + 0.2, [p[2] for p in pol], 0.38, label="ns-3", color=CB["orange"])
    ax.set_xticks(x)
    ax.set_xticklabels([p[0] for p in pol], rotation=30, ha="right", fontsize=6)
    ax.set_ylabel("critical delivery within 10 s (mean of 32 cells)", fontsize=6)
    ax.set_ylim(0, 0.9)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6)
    _save(fig, "pp_xsim")
    plt.close(fig)


def fig_t1(R: dict) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    pols = [("D1", "D1"), ("quick", "quick"), ("P1", "P1"), ("P4", "P4"), ("khan", "LoRaWAN-style"), ("nessa", "Nessa-style")]
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for i, g in enumerate("LMH"):
        vals = [R[f"r3.t1.{g}.deliv.{p}"] for p, _ in pols] + [R[f"r3.t1.explore.{g}.deliv.Z0"]]
        ax.bar(np.arange(len(vals)) + (i - 1) * 0.27, vals, 0.26, label=f"group {g}", color=[CB["sky"], CB["blue"], CB["black"]][i])
    ax.set_xticks(range(len(pols) + 1))
    ax.set_xticklabels([n for _, n in pols] + ["no-hold control"], rotation=35, ha="right", fontsize=6)
    ax.set_ylabel("delivery within 10 s", fontsize=7)
    ax.tick_params(labelsize=7)
    ax.set_ylim(0, 1.35)
    ax.legend(fontsize=6, ncol=3, loc="upper center", title="link loss: L below 10%, M 10 to 40%, H 40% or more", title_fontsize=6)
    _save(fig, "pp_t1")
    plt.close(fig)


def write_figures(R: dict) -> None:
    fig_arch()
    fig_heat()
    fig_rest(R)
    fig_p4a()
    fig_r3(R)
    fig_xsim(R)
    fig_t1(R)
    print("figures written")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "numbers"
    R = load()
    if what == "numbers":
        write_numbers(R)
    elif what == "figures":
        write_figures(R)
