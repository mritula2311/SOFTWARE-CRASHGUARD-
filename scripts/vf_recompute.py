"""V1.5: RECOMPUTE.md. Compare the values the paper states (macros of the committed paper/generated/numbers.tex) with the same macros computed from the results.json of the fresh clone.

usage: PYTHONPATH=src python scripts/vf_recompute.py <fresh clone root>
The fresh clone's results.json was produced by its own run of the pipeline from raw data and stored raw outputs (see docs/04_audits/FINAL_VERIFICATION.md rows V1.4 and V1.5).
"""
import json
import sys
from pathlib import Path

from crashguard import pp_paper as P

ROOT = Path(__file__).resolve().parents[1]
clone = Path(sys.argv[1])
R_clone = {e["name"]: e["value"] for e in json.loads((clone / "results/results.json").read_text(encoding="utf-8"))}
R_here = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}


R_clone.update({k: v for k, v in R_here.items() if k.startswith("vf.")})  # keys of this verification run are not recomputed by the pipeline


def macros(R):
    out = {}
    for name, v, f in P.spec(R):
        out[name] = P.fmt(v, f)
    return out


try:
    M_clone = macros(R_clone)
except KeyError as e:
    sys.exit(f"the fresh clone lacks result key {e}")
M_here = macros(R_here)
KEYSRC = {}
for name, v, f in P.spec(R_here):
    KEYSRC[name] = ""
FACTS = [
    ("F1", "217 groups, 439 events (426 crash)", ["VzGroups", "VzGroupEvents", "VzCrashEvents"], "leakage.*", "src/crashguard/vz_audit.py"),
    ("F2", "118 test exact copies (0.49%)", ["VzTestExact", "VzTestExactShare"], "vz.v4.n_events.*", "src/crashguard/vz_leakage.py"),
    ("F3", "1,305 of 5,863 triggered windows (22.3%)", ["VzNearBoth", "VzNearScanned", "VzNearShare"], "dupscan.neardup.*", "src/crashguard/vz_audit.py"),
    ("F4", "recall 0.901 to 0.873; at 1% 0.631 to 0.558", ["VzRecSup", "VzRecNear", "VzROneSup", "VzROneNear"], "vz.v4.rf15.*", "src/crashguard/vz_leakage.py"),
    ("F5", "H-C3 refit SUPPORTED, Holm 0.018, KS 0.191 against gate 0.20", ["RefitVerdict", "RefitHolm", "RefitKsFront", "RefitPassed"], "pp.p0.*", "src/crashguard/pp_p0_refit.py"),
    ("F6", "0.07 at +-16 g; 0.78 and 0.88 at +-64 g; 14 of 25 settings", ["DvSixteen", "DvSixtyFourA", "DvSixtyFourB", "DvSettingsMeet", "DvSettingsAll"], "sevstudy.*", "src/crashguard/severity_study.py"),
    ("F7", "early exit recall +0.0155 (1%), +0.0015 (5%)", ["EarlyGainOne", "EarlyGainFive"], "s6.*", "src/crashguard/s6_early.py"),
    ("F8", "median error 11.9% against 23.5% and 25.7%; +-32 g gain 1.3", ["RestMedRest", "RestMedSpl", "RestMedPlain", "RestThirtyTwoGain"], "n14x.*", "src/crashguard/s4_n14.py"),
    ("F9", "1,750 ms earlier; 10.8% retracted; 3% class agreement at 50 ms", ["TThreeEarlier", "TThreeRetract", "TThreeNhtsaFifty"], "r3.t3.*", "src/crashguard/r3_t3.py"),
    ("F10", "6 of 8; 1.87 s and 2.12 s earlier; extra airtime 35 to 37% (SF7), 54% (SF9)", ["NsSupported", "NsEarlySfSeven", "NsEarlySfNine", "NsAirLoSfSeven", "NsAirHiSfSeven", "NsAirHiSfNine"], "pp.p1.*", "src/crashguard/pp_r3_ns3.py"),
    ("F11", "D1 +0.116 custom against +0.021 ns-3", ["XCustomDOneGain", "XNsDOneGain"], "rd.x13.*", "src/crashguard/rd_x13.py"),
    ("F12", "D1 49.3% against zero-spacing 54.0%; 6.4 s, 17.8%", ["TOneDelDOne", "TOneDelZ", "ZMaxAir", "ZMaxShareOne"], "r3.t1.*, pp.c6.z0.*", "src/crashguard/r3_t1.py, pp_c6_z0.py"),
    ("F15", "k = 0 to 6, D1 not worse than quick retries", ["TimedRuns", "TimedDOneSix"], "r3.t2.timed.*", "src/crashguard/r3_t2_timed.py"),
    ("F16", "side accuracy 0.986 against 0.49; NHTSA 0.98; mirror about 0.5", ["RFiveOneAcc", "RFiveOneRaw", "RFiveOneNhtsa", "RFiveMirrorAcc"], "r5.l1.*", "src/crashguard/r5_l1.py"),
    ("F17", "recall 0.631 against 0.609; energy ratio 0.25; active share 0.20", ["RFiveThreeRecB", "RFiveThreeRecA", "RFiveThreeRatio", "RFiveThreeShare"], "r5.l3.*", "src/crashguard/r5_l3.py"),
    ("F18", "ns-3 edge gain 0.098; worst-cell lower limit -0.009", ["RFiveFourEdge", "RFiveFourWorst"], "r5.l4.*", "src/crashguard/r5_l4.py"),
    ("F19", "L2 0.0062 to 0.0095; L6 +1.8 to +5.6; L8b 1 of 2,000; L11 57% and 89%", ["RFiveTwoFa", "RFiveTwoFaBase", "RFiveSixKTwo", "RFiveSixKFour", "RFiveEightQuar", "RFiveElevenAccX", "RFiveElevenAccY"], "r5.l2.*, l6.*, l8.*, l11.*", "src/crashguard/r5_l2.py and others"),
    ("F20", "1,398,101 sequences; at most 6 forwards over 232,966 states; break-even 0.24 (0.22 to 0.27)", ["RFiveSevenSeq", "RFiveEightMax", "RFiveEightStates", "RFiveNineRho", "RFiveNineRhoLo", "RFiveNineRhoHi"], "r5.l7.*, l8.*, l9.*", "src/crashguard/r5_l7.py, r5_l8.py, r5_l9.py"),
    ("F21", "A1 SF9 extra airtime 0.31 to 0.61; +1.4 points; A2 +4.9 points; 52% by one gateway", ["AOneAirNine", "AOneProv", "ATwoGain", "ATwoOne"], "a4.*", "src/crashguard/a4_a1.py, a4_a2.py"),
]
rows, bad = [], 0
for fid, stated, names, key, script in FACTS:
    for n in names:
        a, b = M_here.get(n), M_clone.get(n)
        ok = a == b
        bad += not ok
        rows.append((fid, stated, n, a, b, key, script, "yes" if ok else "NO"))
allbad = sorted(n for n in M_here if M_here[n] != M_clone.get(n))
out = ["# Recomputation of the facts the paper states (V1.5)", "", "<!-- header:start -->", "<!-- header:end -->", "",
       f"Method. Every macro of the paper (`paper/generated/numbers.tex`, {len(M_here)} macros) was computed twice with `crashguard.pp_paper.spec`: from the committed `results/results.json` ('paper') and from the `results/results.json` that the fresh clone produced by running the pipeline from the raw data and the stored raw outputs ('fresh clone'). F13 and F14 (Tamarin and ProVerif) are in `docs/04_audits/FORMAL_RERUN.md`; F15's enumeration is also repeated by `scripts/vf_enum_rerun.py`.", "",
       f"Result: {sum(1 for r in rows if r[-1] == 'yes')} of {len(rows)} macros of the table below match; {len(allbad)} of {len(M_here)} macros differ overall: {', '.join(allbad) if allbad else 'none'}.", "",
       "| ID | Stated (task table) | Macro | Paper (committed) | Recomputed (fresh clone) | Source key | Script | Match |", "|---|---|---|---|---|---|---|---|"]
out += [f"| {i} | {s} | `{n}` | {a} | {b} | `{k}` | `{sc}` | {m} |" for i, s, n, a, b, k, sc, m in rows]
(ROOT / "docs/04_audits/RECOMPUTE.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(len(rows), "rows;", len(allbad), "macros differ", allbad[:20])
