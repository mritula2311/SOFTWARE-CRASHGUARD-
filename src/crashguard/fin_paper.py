"""D1: paper/generated/numbers.tex (one macro per number, read from results/results.json) and every paper table as LaTeX (paper/generated/tab_*.tex). No number is typed by hand: main.tex uses only these macros and tables.
A macro whose key is missing is defined as 'NOT\\_RUN'. Also writes paper/ABSTRACT_FACTS.md (D3)."""
from __future__ import annotations

from pathlib import Path

from crashguard import fin_sim as FS

R = {}
OUT = Path("paper/generated")


def val(key):
    v = R.get(key)
    return v


def fmt(v, f: str) -> str:
    if v is None or v == "NOT_RUN":
        return r"NOT\_RUN"
    if f == "int":
        return f"{int(round(float(v))):,}".replace(",", r"\,")
    if f == "txt":
        return str(v).replace("_", r"\_").replace("%", r"\%").replace("+-", r"$\pm$")
    if f.startswith("p"):  # p3 = 3 decimals
        return f"{float(v):.{int(f[1:])}f}"
    if f.startswith("s"):  # signed
        return f"{float(v):+.{int(f[1:])}f}"
    return str(v)


# macro -> (key, format, label for ABSTRACT_FACTS or None)
NUM = {
    # B1
    "BoneStates": ("f.b1.ext.design.states", "int", "bounded check: reachable states with the CANCEL-reordering counterexample"),
    "BoneDepth": ("f.b1.ext.design.depth", "int", None),
    "BoneProps": ("f.b1.ext.design.properties_checked", "int", None),
    "BoneAttackOrig": ("f.b1.attacks.original_cases", "int", None),
    "BoneAttackOrigMatch": ("f.b1.attacks.original_match_with_change", "int", None),
    "BoneAttackExtra": ("f.b1.attacks.extra_cases", "int", None),
    "BoneAttackExtraMatch": ("f.b1.attacks.extra_match_with_change", "int", None),
    "BoneTwoStates": ("f.b1.ext2.design.states", "int", None),
    # B2
    "BtwoCells": ("f.b2.hB2.n_cells", "int", None),
    "BtwoGain": ("f.b2.hB2.n_cells_gain5", "int", "H-B2: held-out cells in which P1+ beats P0 by at least 5 points"),
    "BtwoLose": ("f.b2.hB2.n_cells_lose2", "int", None),
    "BtwoPoneplusPone": ("f.b2.heldout.diff.P1+_minus_P1.reach10_critical.n_cells_gain5", "int", None),
    "BtwoDesignGain": ("f.b2.design.diff.P1+_minus_P0.reach10_critical.n_cells_gain5", "int", None),
    "BtwoDesignCells": ("f.b2.design.diff.P1+_minus_P0.reach10_critical.n_cells", "int", None),
    "BtwoBestPt": ("f.b2.heldout.diff.P1+_minus_P0.reach10_critical.n150_p50_b20.pt", "s3", None),
    "BtwoBestLo": ("f.b2.heldout.diff.P1+_minus_P0.reach10_critical.n150_p50_b20.lo", "s3", None),
    "BtwoBestHi": ("f.b2.heldout.diff.P1+_minus_P0.reach10_critical.n150_p50_b20.hi", "s3", None),
    "BtwoPthreeA": ("f.b2.heldout.cell.n75_p10_b20.P3.reach10_critical", "p3", None),
    "BtwoPoneplusA": ("f.b2.heldout.cell.n75_p10_b20.P1+.reach10_critical", "p3", None),
    "BtwoRuns": ("f.b2.runs", "int", None),
    "BtwoDuty": ("f.b2.runs_exceeding_duty", "int", None),
    # B3
    "BthreeAirtime": ("f.b3.airtime.max_abs_diff_ms", "txt", None),
    "BthreeCollAloha": ("f.b3.collision.max_abs_err_vs_aloha", "p3", "simulator check: largest error against 1 - exp(-2G)"),
    "BthreeCollFinite": ("f.b3.collision.max_abs_err_vs_finite", "p3", None),
    # C
    "CModes": ("f.c.fidelity.modes_passed", "txt", None),
    "CFrontPeakD": ("f.c.fidelity.frontal_barrier.peak_g.ks_D", "p2", None),
    "CPoleShapeD": ("f.c.fidelity.pole.shape.ks_D", "p2", None),
    "CSideAsymD": ("f.c.fidelity.side.asym.ks_D", "p2", None),
    "CFrontSyn": ("f.c.grid.frontal_barrier.synthetic_smallest_range", "int", "synthetic stress test: smallest range meeting the 0.80 rule, frontal barrier (g)"),
    "CFrontReal": ("f.c.grid.frontal_barrier.real_smallest_range", "int", None),
    "CFrontShift": ("f.c.sens.shift0.4.frontal_barrier.smallest_range", "int", None),
    "COtherSyn": ("f.c.grid.other.synthetic_smallest_range", "int", None),
    # audit (earlier rounds, stored keys)
    "VzGroups": ("leakage.exact_hash_groups_across_splits", "int", None),
    "VzEvents": ("leakage.cross_split_group_events.total", "int", None),
    "VzTestExact": ("vz.v1.exact.acc.test_events_with_train_or_val_copy", "int", None),
    "VzFlagged": ("dupscan.neardup.n_both", "int", None),
    "VzScanned": ("dupscan.neardup.n_scanned", "int", None),
    "VzPrimary": ("dupscan.rf15.mean5.n_events.dedup", "int", None),
    "VzStrict": ("dupscan.rf15.mean5.n_events.dedup_nd", "int", None),
    # G
    "GRuns": ("f.g.runs", "int", None),
    "GDuty": ("f.g.runs_exceeding_duty", "int", None),
    "GBest": ("f.g.baseline_policy_chosen_on_design", "txt", None),
    "GHeldPzero": ("f.g.g1.held.P0.reach10_critical", "p3", None),
    "GHeldPone": ("f.g.g1.held.P1.reach10_critical", "p3", None),
    "GHeldPoneplus": ("f.g.g1.held.P1+.reach10_critical", "p3", None),
    "GHeldPthree": ("f.g.g1.held.P3.reach10_critical", "p3", None),
    "GHeldPfour": ("f.g.g1.held.P4.reach10_critical", "p3", "simulation: critical reach within 10 s of capped UA-SCT, held-out grid mean"),
    "GSlotGain": ("f.g.g3.hG3a.n_cells_gain5", "int", None),
    "GSlotLose": ("f.g.g3.hG3a.n_cells_lose2", "int", "H-G3a: held-out cells (of 16) in which the slotted fast path loses more than 2 points"),
    "GSlotDiff": ("f.g.g3.hG3a.pooled_diff.reach10_critical", "s3", None),
    "GBeaconShare": ("f.g.g3.slot.beacon_duty_share_of_gateway", "p3", None),
    "GLbtGain": ("f.g.g3.hG3b.n_cells_gain5", "int", None),
    "GLbtDiff": ("f.g.g3.hG3b.pooled_diff.reach10_critical", "s3", None),
    "GRelayGain": ("f.g.g3.hG3c.n_cells_gain5", "int", None),
    "GRelayDiff": ("f.g.g3.hG3c.pooled_diff.reach30_rx_critical", "s3", None),
    "GRelayDup": ("f.g.g3.relay.dup_rx_per_critical_alert", "p3", None),
    "GTies": ("f.g.g4.held.n_ties", "int", None),
    "GPthreeWins": ("f.g.g4.held.p3_wins_cells", "int", None),
    "GSfRaise": ("f.g.g2.held.sf_raise.reach10_critical", "s3", None),
    "GCaptureOff": ("f.g.g2.held.capture_off.reach10_critical", "s3", None),
    "GNoHold": ("f.g.g2.held.no_hold.reach10_critical", "s3", None),
    "GCrFourEight": ("f.g.g2.held.cr_4_8.reach10_critical", "s3", None),
    "GTagSixteen": ("f.g.g2.held.tag_16.reach10_critical", "s3", None),
    "GInteractSfSpaced": ("f.g.g2.held.interaction.sf_raise__spaced_retries.reach10_critical", "s3", None),
    "GFlipsC1": ("f.g.g5.flips.C1_best_minus_P1+", "txt", None),
    "GFlipsC4": ("f.g.g5.flips.C4_relay_minus_base_30s_rx", "txt", None),
    # earlier (tagged) results used in the negative-results table
    "PoneMacroF": ("p.p1.r16.f100.paired.macro_f1_direct_minus_base", "s3", None),
    "PtwoCover": ("p.p2.r16.f100.global.coverage", "p3", None),
    "PtwoReduction": ("p.p2.r16.f100.global.width_ratio_reduction_vs_existing", "p3", None),
    "PfourBGain": ("p.p4b.strict.diff_aug_merge_minus_standard.recall_at_1pct", "s4", None),
    "PfourAConfig": ("p.p4a.selected.config", "txt", None),
    "PfourAFlash": ("p.p4a.selected.flash_bytes", "int", None),
    "PfourARefFlash": ("p.p4a.reference.flash_bytes", "int", None),
    "PthreeBMis": ("p.p3b.r16.A.mis_triage", "p3", None),
    "PthreeBMisLow": ("p.p3b.r16.P1e.mis_triage", "p3", None),
    # F2 / F1 / F3 (EXPLORATORY-REVISED)
    "FtwoAGain": ("f.f2.hF2a.gain", "s4", "F2: recall at the 1% target, best surrogate ratio minus real only (strict set); EXPLORATORY-REVISED"),
    "FtwoALo": ("f.f2.hF2a.gain_lo", "s4", None),
    "FtwoAHi": ("f.f2.hF2a.gain_hi", "s4", None),
    "FtwoBGain": ("f.f2.hF2b.gain", "s4", None),
    "FtwoBRatio": ("f.f2.best_ratio.gw", "txt", None),
    "FtwoARatio": ("f.f2.best_ratio.std", "txt", None),
    "FtwoSurrMatched": ("f.f2.surrogate.features_matched", "int", None),
    "FtwoNNCopies": ("f.f2.surrogate.nn_copies", "int", None),
    "FoneNRanges": ("f.f1.cv.hF1.n_ranges_met", "int", "F1: ranges (of 3) in which real plus synthetic training meets the original H-P1 criterion (nested cross-validation)"),
    "FoneSealedRanges": ("f.f1.sealed.hF1.n_ranges_met", "int", None),
    "FoneMacroSixteen": ("f.f1.cv.r16.hF1.macro_f1_diff", "s3", None),
    "FoneMacroSixteenLo": ("f.f1.cv.r16.hF1.macro_f1_diff_lo", "s3", None),
    "FoneMacroSixteenHi": ("f.f1.cv.r16.hF1.macro_f1_diff_hi", "s3", None),
    "FoneControlSixteen": ("f.f1.cv.r16.control_r0.macro_f1_diff", "s3", None),
    "FoneUtSixteen": ("f.f1.cv.r16.hF1.under_triage_diff", "s3", None),
    "FoneBCover": ("f.f1.cv.hF1b.coverage", "p3", None),
    "FoneBRed": ("f.f1.cv.hF1b.width_ratio_reduction", "p3", None),
    "FoneCRatio": ("f.f1.cv.hF1c.under_triage_ratio", "p3", None),
    "FthreeAMisDiff": ("f.f3.hF3a.pool_mis_triage_diff", "s3", None),
    "FthreeBMisDiff": ("f.f3.hF3b.pool_mis_triage_diff", "s3", None),
    "FthreeRuns": ("f.f3.runs", "int", None),
}


def write_tables() -> None:
    T = {}
    # verdict table (Holm family)
    rows = []
    for name in ("hb2", "hc3", "hf1", "hf1b", "hf1c", "hf1d", "hf1e", "hf2a", "hf2b", "hf2c", "hf2d", "hf2e", "hf2f", "hf3a", "hf3b", "hg3a", "hg3b", "hg3c"):
        n = name.upper().replace("HB2", "H-B2").replace("HC3", "H-C3").replace("HF", "H-F").replace("HG", "H-G")
        v = R.get(f"f.holm.{name}.verdict")
        if v is None:
            continue
        rows.append((n.replace("H-F1B", "H-F1b").replace("H-F1C", "H-F1c").replace("H-F1D", "H-F1d").replace("H-F1E", "H-F1e").replace("H-F2A", "H-F2a").replace("H-F2B", "H-F2b").replace("H-F2C", "H-F2c").replace("H-F2D", "H-F2d").replace("H-F2E", "H-F2e").replace("H-F2F", "H-F2f").replace("H-F3A", "H-F3a").replace("H-F3B", "H-F3b").replace("H-G3A", "H-G3a").replace("H-G3B", "H-G3b").replace("H-G3C", "H-G3c"), R.get(f"f.holm.{name}.p_raw"), R.get(f"f.holm.{name}.p_holm"), v))
    body = "\n".join(f"{a} & {float(b):.3f} & {float(c):.3f} & {d.replace('_', ' ')} \\\\" for a, b, c, d in rows)
    T["verdicts"] = "\\begin{tabular}{llll}\n\\hline\nHypothesis & raw $p$ & Holm $p$ & Verdict \\\\\n\\hline\n" + body + "\n\\hline\n\\end{tabular}\n"
    # G regime/policy table (held-out means)
    pols = ["P0", "P1", "P1e", "P1+", "P1+e", "P2", "P3", "P4", "P3b"]
    lines = []
    for p in pols:
        a = [R.get(f"f.g.g1.{g}.{p}.{m}") for g in ("design", "held") for m in ("reach10_critical", "mis_triage")]
        if None in a:
            continue
        lines.append(f"{p.replace('+', '+')} & " + " & ".join(f"{float(x):.3f}" for x in a) + " \\\\")
    T["g1"] = "\\begin{tabular}{lllll}\n\\hline\nPolicy & reach 10 s (DESIGN) & mis-triage (DESIGN) & reach 10 s (HELD-OUT) & mis-triage (HELD-OUT) \\\\\n\\hline\n" + "\n".join(lines) + "\n\\hline\n\\end{tabular}\n"
    # G2 layer table (held-out)
    rows2 = []
    for v, layer in (("sf_raise", "PHY"), ("cr_4_8", "PHY"), ("spaced_retries", "MAC"), ("no_hold", "MAC"), ("backoff_normal", "MAC"), ("reserved_share", "MAC"), ("preempt", "MAC"), ("capture_off", "MAC"), ("tag_4", "NET"), ("tag_16", "NET"), ("unsigned_ack", "NET"), ("upper_end_class", "APP"), ("abstain_route", "APP")):
        k = f"f.g.g2.held.{v}.reach10_critical"
        if k in R:
            rows2.append(f"{layer} & {v.replace('_', ' ')} & {R[k]:+.3f} [{R[k + '_lo']:+.3f}, {R[k + '_hi']:+.3f}] \\\\")
    T["g2"] = "\\begin{tabular}{lll}\n\\hline\nLayer & Change from P1+ & Critical reach within 10 s, difference [95\\% interval] \\\\\n\\hline\n" + "\n".join(rows2) + "\n\\hline\n\\end{tabular}\n"
    # B2 held-out cells
    rows3 = []
    import re
    cells = sorted({m.group(1) for k in R for m in [re.match(r"f\.b2\.heldout\.cell\.(n\d+_p\d+_b\d+)\.P0\.reach10_critical$", k)] if m})
    for c in cells:
        a = [R.get(f"f.b2.heldout.cell.{c}.{p}.reach10_critical") for p in ("P0", "P1", "P1+", "P3")]
        d = (R.get(f"f.b2.heldout.diff.P1+_minus_P0.reach10_critical.{c}.pt"), R.get(f"f.b2.heldout.diff.P1+_minus_P0.reach10_critical.{c}.lo"), R.get(f"f.b2.heldout.diff.P1+_minus_P0.reach10_critical.{c}.hi"))
        rows3.append(f"{c.replace('_', ' ')} & " + " & ".join(f"{float(x):.3f}" for x in a) + f" & {d[0]:+.3f} [{d[1]:+.3f}, {d[2]:+.3f}] \\\\")
    T["b2"] = "\\begin{tabular}{llllll}\n\\hline\nCell & P0 & P1 & P1+ & P3 & P1+ minus P0 [95\\% interval] \\\\\n\\hline\n" + "\n".join(rows3) + "\n\\hline\n\\end{tabular}\n"
    # C fidelity
    rows4 = []
    for m in ("frontal_barrier", "pole", "side", "other"):
        ds = [R.get(f"f.c.fidelity.{m}.{d}.ks_D") for d in ("peak_g", "duration_ms", "dv_kmh", "asym", "shape")]
        if None in ds:
            continue
        rows4.append(f"{m.replace('_', ' ')} & " + " & ".join(f"{float(x):.2f}" for x in ds) + f" & {'pass' if R.get(f'f.c.fidelity.{m}.passes') else 'fail'} \\\\")
    T["c2"] = "\\begin{tabular}{lllllll}\n\\hline\nMode & peak & duration & $\\Delta V$ & asymmetry & shape & result \\\\\n\\hline\n" + "\n".join(rows4) + "\n\\hline\n\\end{tabular}\n"
    for k, v in T.items():
        (OUT / f"tab_{k}.tex").write_text(v, encoding="utf-8")


def main() -> None:
    global R
    R = FS.results_map()
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["% generated by crashguard.fin_paper from results/results.json; do not edit"]
    for mac, (key, f, _lab) in NUM.items():
        lines.append(f"\\newcommand{{\\{mac}}}{{{fmt(val(key), f)}}}")
    (OUT / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_tables()
    facts = ["# Abstract facts (generated)", "", "Numbers an abstract may use. Each has its results.json key and evidence label. Nothing else should appear as a number in the abstract.", "", "| Fact | Value | Key | Label |", "|---|---|---|---|"]
    for mac, (key, f, lab) in NUM.items():
        if lab:
            e = next((x for x in __import__("json").loads(open("results/results.json", encoding="utf-8").read()) if x["name"] == key), None)
            facts.append(f"| {lab} | {val(key)} | `{key}` | {e['origin'] if e else 'NOT_RUN'} |")
    Path("paper/ABSTRACT_FACTS.md").write_text("\n".join(facts) + "\n", encoding="utf-8")
    miss = [k for _m, (k, _f, _l) in NUM.items() if val(k) is None]
    print("macros", len(NUM), "missing keys", miss)


if __name__ == "__main__":
    main()
