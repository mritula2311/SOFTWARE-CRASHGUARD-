"""Round 7: LaTeX macros for the numbers of the new C4 and C5 text (paper/generated/numbers_r7.tex), generated from results/results.json (keys r7.*).

    python -m crashguard.r7_paper

Every number that the round-7 text of paper/main.tex and paper/supplement.tex quotes is a macro defined here; a missing key stops the run. The existing generators (pp_paper, rel_paper) are not touched.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper" / "generated" / "numbers_r7.tex"
SFN = {7: "Seven", 8: "Eight", 9: "Nine"}


def load() -> dict:
    return {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", "\\,")


def spec(R: dict) -> list[tuple[str, str]]:
    S: list[tuple[str, str]] = []

    def k(key):
        assert key in R, key
        return R[key]

    def add(name, key_or_val, f):
        v = k(key_or_val) if isinstance(key_or_val, str) and key_or_val in R else key_or_val
        S.append((name, {"i": lambda x: thousands(int(x)), "d1": lambda x: f"{float(x):.1f}", "d2": lambda x: f"{float(x):.2f}", "d3": lambda x: f"{float(x):.3f}", "pct": lambda x: f"{100 * float(x):.1f}", "pct0": lambda x: f"{100 * float(x):.0f}",
                           "ms": lambda x: f"{1000 * float(x):.1f}", "us": lambda x: f"{1e6 * float(x):.1f}", "e": lambda x: f"{float(x):.2e}".replace("e-0", "e-").replace("e+0", "e+"), "t": str, "pp": lambda x: f"{100 * float(x):.2f}"}[f](v)))

    for sf, n in SFN.items():
        for m, mn in (("H1", "One"), ("H10", "Ten")):
            add(f"RsevNstar{mn}Sf{n}", f"r7.a.{m}.sf{sf}.n_star", "i")
        add(f"RsevNHLimitSf{n}", f"r7.a.H1.sf{sf}.n_h_limit", "i")
        add(f"RsevNodeAirSf{n}", f"r7.a.sf{sf}.node_air_event_confirm_path", "d2")
        add(f"RsevAttackRatioSf{n}", f"r7.a.sf{sf}.attacker_cost_ratio", "d2")
        add(f"RsevDmaxHSf{n}", f"r7.a.H1.sf{sf}.dmax_first", "d2")
        add(f"RsevSatDelaySf{n}", f"r7.a.H1.sf{sf}.sat_delay", "d1")
        add(f"RsevTtenOldDelaySf{n}", f"r7.a.T10.sf{sf}.median.old_confirm_delay", "d2")
        add(f"RsevTtenFlashTriesSf{n}", f"r7.a.T10.sf{sf}.median.reserved_flash_tries", "i")
        for m, mn in (("H1", "One"), ("H10", "Ten"), ("T10", "TT")):
            for pol, pn in (("old", "Old"), ("reserved", "Res")):
                add(f"RsevAoneRate{mn}{pn}Sf{n}", f"r7.a1.sim.{m}.sf{sf}.{pol}.primary.rate", "pct")
        add(f"RsevPostFourSf{n}", f"r7.a1.posthoc.H1.sf{sf}.nres4.rate", "pct0")
        add(f"RsevPostTwoSf{n}", f"r7.a1.posthoc.H1.sf{sf}.nres2.rate", "pct0")
        add(f"RsevPostOneSf{n}", f"r7.a1.posthoc.H1.sf{sf}.nres1.rate", "pct0")
    from crashguard.r7_engine import MICRO13, air

    for sf, n in SFN.items():
        R4 = 4 * 4 * air(97, sf) + air(MICRO13, sf)
        add(f"RsevReserveFourSf{n}", R4, "d1")
        add(f"RsevReserveFourShareSf{n}", R4 / 36.0, "pct0")
    add("RsevGapSfSeven", 3600.0 / k("r7.a.H1.sf7.n_star"), "i")
    add("RsevFormRuns", "r7.formal.total.reserved.runs", "i")
    add("RsevFormOldCond", "r7.formal.total.old.inv2_violations_conditional", "i")
    add("RsevFormOldUnc", "r7.formal.total.old.inv2_violations_unconditional", "i")
    add("RsevFormResCond", "r7.formal.total.reserved.inv2_violations_conditional", "i")
    add("RsevFormResUnc", "r7.formal.total.reserved.inv2_violations_unconditional", "i")
    add("RsevFormCondRuns", "r7.formal.total.reserved.conditional_runs", "i")
    add("RsevFormMinEarlier", "r7.formal.reserved_min_earlier_events_unconditional_violation", "i")
    add("RsevATwoHTenDelta", abs(k("r7.a2.H.R3.T10.delivery_diff")), "pp")
    add("RsevATwoHTenLo", abs(k("r7.a2.H.R3.T10.delivery_diff_lo95")), "pp")
    add("RsevATwoHHourDelta", abs(k("r7.a2.H.R3.H1.delivery_diff")), "pp")
    add("RsevATwoMMax", abs(k("r7.a2.M.R3.T10.delivery_diff")), "pp")
    add("RsevATwoRatioMax", 1.0, "d2")
    add("RsevATwoNDevices", "r7.a2.H.n_devices", "i")
    add("RsevBoneWorstUs", "r7.b.hR7_B1.worst_mean_per_frame", "us")
    add("RsevBoneCUs", "r7.b.bench.c.L4.worst_rep", "us")
    add("RsevBoneResyncMs", "r7.b.resync.python.one_frame_s", "ms")
    add("RsevBtwoLTwo", "r7.b.hR7_B2.L2.p_collision_formula", "d3")
    add("RsevBtwoLFour", "r7.b.hR7_B2.L4.p_collision_formula", "e")
    add("RsevBtwoLFive", "r7.b.hR7_B2.L5.p_collision_formula", "e")
    add("RsevBtwoLTwoCandidates", "r7.b.hR7_B2.L2.extra_candidates_per_frame", "d2")
    add("RsevBtwoLMeet", "r7.b.hR7_B2.first_L_meeting_bound", "i")
    add("RsevFpText", "r7.b.desc.fp.text_bytes", "i")
    add("RsevFpStack", R["r7.b.desc.fp.stack_pseudonym"] + R["r7.b.desc.fp.stack_hmac"] + R["r7.b.desc.fp.stack_sha256"], "i")
    add("RsevAeadExtraSfSeven", "r7.b.desc.air.sf7.aead16_extra", "ms")
    add("RsevAeadExtraSfNine", "r7.b.desc.air.sf9.aead16_extra", "ms")
    add("RsevTamLfourS", "r7.formal.b.tam.L4_replay_outside_window.wall_time_s", "i")
    add("RsevTamExecS", "r7.formal.b.tam.executable_after_car_reboot.wall_time_s", "i")
    for nm, key in (("GPre", "preregistered"), ("GRun", "run"), ("GSupp", "supported"), ("GNot", "not_supported"), ("GPartly", "partly"), ("GNotRun", "not_run")):
        add(f"Lg{nm}", f"r7.ledger.V18.{key}", "i")
    add("RsevSupported", "r7.decision.n_supported", "i")
    add("RsevHypotheses", 5, "i")
    return S


def main() -> None:
    R = load()
    lines = ["% generated by crashguard.r7_paper from results/results.json (keys r7.*); do not edit"]
    seen = set()
    for name, v in spec(R):
        assert name not in seen and re.fullmatch(r"[A-Za-z]+", name), name
        seen.add(name)
        lines.append(f"\\newcommand{{\\{name}}}{{{v}}}")
    for nm, key in (("LedgerN", "preregistered"), ("LedgerRun", "run"), ("LedgerSupp", "supported"), ("LedgerNot", "not_supported"), ("LedgerPartly", "partly"), ("LedgerNotRun", "not_run"), ("LedgerConfN", "confirmatory_rows"), ("LedgerConfSupp", "confirmatory_supported"), ("LedgerVersions", "versions")):
        lines.append("\\renewcommand{\\" + nm + "}{" + thousands(int(R[f"r7.ledger.all.{key}"])) + "}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("macros", len(seen))


if __name__ == "__main__":
    main()
