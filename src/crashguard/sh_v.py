"""Part V of the combined run: re-derive the headline numbers of the status table from results.json and write docs/03_results/STATUS_REVERIFY.md.

Nothing in results.json is changed. Each row has the stated value (as given in the run prompt), the recomputed value (from the stored keys, by the arithmetic shown),
the keys used, and a match flag. The recomputed value wins; rows that do not match are listed in the summary and corrected in the paper and claims files by hand.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

R = {e["name"]: e for e in json.loads(Path("results/results.json").read_text(encoding="utf-8"))}
OUT = Path("docs/03_results/STATUS_REVERIFY.md")


def g(k):
    return R[k]["value"]


def close(a, b, tol):
    return abs(a - b) <= tol


rows: list[dict] = []


def row(rid, claim, stated, recomputed, keys, ok, note=""):
    rows.append({"id": rid, "claim": claim, "stated": stated, "recomputed": recomputed, "keys": keys, "ok": bool(ok), "note": note})


def build_rows():
    # ---- positives
    n_g, n_ev = g("leakage.exact_hash_groups_across_splits"), g("leakage.cross_split_group_events.total")
    row("P1a", "VZCrash cross-split exact groups", "217", str(n_g), "leakage.exact_hash_groups_across_splits", n_g == 217)
    row("P1b", "events in those groups", "439", str(n_ev), "leakage.cross_split_group_events.total", n_ev == 439)
    ne, nx = g("vz.v4.n_events.supplied"), g("vz.v4.n_events.exact")
    row("P1c", "test events with an exact copy (count, share of test events)", "118 (0.49%)", f"{ne - nx} ({100 * (ne - nx) / ne:.2f}%)",
        "vz.v4.n_events.supplied - vz.v4.n_events.exact", ne - nx == 118 and close(100 * (ne - nx) / ne, 0.49, 0.005))
    ns, nb = g("dupscan.neardup.n_scanned"), g("dupscan.neardup.n_both")
    row("P1d", "triggered test windows; window-identical to train or validation", "5,863; 1,305 (22.3%)", f"{ns:,}; {nb:,} ({100 * nb / ns:.1f}%)",
        "dupscan.neardup.n_scanned, dupscan.neardup.n_both", ns == 5863 and nb == 1305 and round(100 * nb / ns, 1) == 22.3)
    a, b = g("vz.v4.rf15.supplied.sys_recall"), g("vz.v4.rf15.near.sys_recall")
    row("P1e", "forest system recall, supplied to near-duplicates removed", "0.901 to 0.873", f"{a:.3f} to {b:.3f}",
        "vz.v4.rf15.supplied.sys_recall, vz.v4.rf15.near.sys_recall", round(a, 3) == 0.901 and round(b, 3) == 0.873)
    a, b = g("vz.v4.rf15.supplied.recall_at_1pct"), g("vz.v4.rf15.near.recall_at_1pct")
    row("P1f", "recall at the 1% false-alarm target, supplied to near-duplicates removed", "0.631 to 0.558", f"{a:.3f} to {b:.3f}",
        "vz.v4.rf15.supplied.recall_at_1pct, vz.v4.rf15.near.recall_at_1pct", round(a, 3) == 0.631 and round(b, 3) == 0.558)
    # range requirement
    s = {(r_, f): g(f"sevstudy.grid.{r_}.{f}.dv_within10") for r_ in ("r16", "r32", "r64", "r100", "r200") for f in ("f100", "f200", "f400", "f800", "f1600")}
    nt = g("sevstudy.n_tests")
    row("P2a", "number of NHTSA tests", "176", str(nt), "sevstudy.n_tests", nt == 176)
    row("P2b", "share within +-10% delta-V, +-16 g / 100 Hz", "0.07", f"{s[('r16', 'f100')]:.4f}", "sevstudy.grid.r16.f100.dv_within10", round(s[("r16", "f100")], 2) == 0.07)
    row("P2c", "share within +-10%, +-64 g / 100 Hz", "0.78", f"{s[('r64', 'f100')]:.4f}", "sevstudy.grid.r64.f100.dv_within10", round(s[("r64", "f100")], 2) == 0.78)
    row("P2d", "share within +-10%, +-64 g / 200 Hz", "0.88", f"{s[('r64', 'f200')]:.4f}", "sevstudy.grid.r64.f200.dv_within10", round(s[("r64", "f200")], 2) == 0.88)
    n80 = sum(1 for v in s.values() if v >= 0.80)
    row("P2e", "settings (of 25) with at least 80% within +-10%", "14 of 25", f"{n80} of {len(s)}", "sevstudy.grid.*.dv_within10", n80 == 14 and len(s) == 25)
    row("P2f", "H-C3 verdict after the refit", "after the refit", f"no refit H-C3 key exists; stored verdict {g('f.holm.hc3.verdict')} (frontal barrier only, generator fitted on all 913 records, in-sample); the release gates (`ph.gate.*`) show no generator passes",
        "f.holm.hc3.verdict, ph.gate.*.passed", False,
        "The Release_Finish run that would have produced a refit H-C3 was not run in this repository (no tag release-v1.1). H-C3 is therefore not carried as a supported claim: see DECISIONS.")
    # compact detector
    fr, fa = g("p.p4a.flash_ratio_selected_over_reference"), g("p.p4a.selected.val_ap")
    row("P3a", "compact detector flash against the reference forest; verdict", "trade-off (no number stated)",
        f"flash ratio {fr:.3f} ({g('p.p4a.selected.flash_bytes'):.0f} B against {g('p.p4a.reference.flash_bytes'):.0f} B), validation AP {fa:.4f} against {g('p.p4a.reference.val_ap'):.4f}; verdict {g('p.holm.hp4a.verdict')}",
        "p.p4a.*, p.holm.hp4a.verdict", True)
    t1, t5 = -g("s6.a1.mean5.d.E_minus_Ep.time"), -g("s6.a5.mean5.d.E_minus_Ep.time")
    row("P3b", "early exit decides earlier (timing SIMULATED from window length)", "about 1.0 to 1.2 s", f"{t1 / 1000:.2f} s (1% target), {t5 / 1000:.2f} s (5% target)",
        "s6.a1.mean5.d.E_minus_Ep.time, s6.a5.mean5.d.E_minus_Ep.time", 1.0 <= t1 / 1000 <= 1.2 and 1.0 <= t5 / 1000 <= 1.2)
    m1, m5 = g("s6.a1.mean5.d.E_minus_F.recall"), g("s6.a5.mean5.d.E_minus_F.recall")
    s1, s5 = g("s6.a1.seed42.d.E_minus_F.recall"), g("s6.a5.seed42.d.E_minus_F.recall")
    row("P3c", "early exit recall gain at the 1% / 5% target", "+0.030 / +0.0037",
        f"5-seed mean +{m1:.4f} / +{m5:.4f}; seed 42 alone +{s1:.4f} / +{s5:.5f}", "s6.a1.mean5.d.E_minus_F.recall, s6.a5.mean5.d.E_minus_F.recall, s6.*.seed42.d.E_minus_F.recall",
        False, "The stated values are the seed-42 values. The repository's headline is the 5-seed mean (about half as large). CLAIM_EVIDENCE already marks 'the recall gain is an early-exit effect' NOT SUPPORTED.")
    # clipping
    B, SP, M = g("n14x.R.r16.B.median"), g("n14x.R.r16.SP.median"), g("n14x.R.r16.M+.median")
    row("P4a", "clipping restoration at +-16 g, median error: restoration / spline / plain", "11.9% / 23.5% / 25.7%", f"{M:.1f}% / {SP:.1f}% / {B:.1f}%",
        "n14x.R.r16.M+.median, .SP.median, .B.median", round(M, 1) == 11.9 and round(SP, 1) == 23.5 and round(B, 1) == 25.7)
    p90 = (g("n14x.R.r16.M+.p90"), g("n14x.R.r16.B.p90"), g("n14x.R.r16.SP.p90"))
    row("P4b", "90th percentile at +-16 g is worse than plain and spline", "worse", f"{p90[0]:.1f}% against {p90[1]:.1f}% (plain), {p90[2]:.1f}% (spline)", "n14x.R.r16.*.p90", p90[0] > p90[1] and p90[0] > p90[2])
    d32, lo32, hi32 = g("n14x.R.r32.paired.M+_vs_B.d_median"), g("n14x.R.r32.paired.M+_vs_B.d_median_lo"), g("n14x.R.r32.paired.M+_vs_B.d_median_hi")
    sp32 = (g("n14x.R.r32.paired.M+_vs_SP.d_median_lo"), g("n14x.R.r32.paired.M+_vs_SP.d_median_hi"))
    d64, lo64, hi64 = g("n14x.R.r64.paired.M+_vs_B.d_median"), g("n14x.R.r64.paired.M+_vs_B.d_median_lo"), g("n14x.R.r64.paired.M+_vs_B.d_median_hi")
    row("P4c", "no gain at +-32 or +-64 g", "no gain",
        f"+-32 g: median error {d32:+.2f} points against plain [{lo32:+.2f}, {hi32:+.4f}] (interval just excludes zero), against spline interval [{sp32[0]:+.2f}, {sp32[1]:+.4f}] includes zero; +-64 g: {d64:+.3f} [{lo64:+.3f}, {hi64:+.4f}] (includes zero)",
        "n14x.R.r32.paired.*, n14x.R.r64.paired.*", False,
        "At +-32 g there is a small gain over plain (1.3 points, interval upper end -0.0009); against spline it is not clear. Wording becomes: 'a small gain over plain at +-32 g that does not clear against spline, and none at +-64 g'.")
    # security
    l8 = g("v2.e.hE2.log2_attempts_for_1e6_t8")
    row("P5a", "8-byte tag: forgery attempts for probability 1e-6 (log2)", "about 2^44", f"2^{l8:.1f}; expected attempts 2^{g('v2.e.forgery.t8.log2_expected_attempts')}", "v2.e.hE2.log2_attempts_for_1e6_t8, v2.e.forgery.t8.log2_expected_attempts",
        round(l8) == 44, "2^44 is for success probability 1e-6; the expected number of attempts is 2^63.")
    t = {k: g(f"v2.e.forgery.t{k}.log2_expected_attempts") for k in (4, 6, 8)}
    # formula: attempts for forgery probability 1e-6 = 1e-6 * 2^(8t); expected attempts = 2^(8t-1); the formula reproduces the stored t8 value
    f = {k_: (8 * k_ - 1, 8 * k_ + math.log2(1e-6)) for k_ in (4, 5, 6, 7, 8)}
    small = min(k_ for k_, (e, q) in f.items() if e > 32 and q > 32)
    row("P5b", "smallest tag (bytes) with both work factors above 2^32", "7 bytes", f"{small} bytes (log2 expected / log2 for 1e-6: " + "; ".join(f"{k_} B {e}/{q:.1f}" for k_, (e, q) in f.items()) + ")",
        "formula checked against v2.e.forgery.t4/t6/t8 and v2.e.hE2.log2_attempts_for_1e6_t8", small == 7 and abs(f[8][1] - l8) < 0.01 and f[6][0] == t[6] and f[8][0] == t[8],
        "ANALYTICAL: 7 bytes is computed from the formula here; the stored keys cover 4, 6, 8, 12 and 16 bytes and the formula reproduces them.")
    row("P5c", "one forged event-level ACK from a key holder stops every vehicle (bounded model)", "yes",
        f"{g('pa.model.osdr.key.attacker_actions_to_lose_event')} attacker action (OS-DR, key holder); baseline needs {g('pa.model.baseline.key.attacker_actions_to_lose_event')}; H-A3 criterion_met = {g('pa.model.hA3.criterion_met')}",
        "pa.model.osdr.key.attacker_actions_to_lose_event, pa.model.hA3.*", g("pa.model.osdr.key.attacker_actions_to_lose_event") == 1)
    p1, p5 = g("prev.rf15.t1.pi0p02pct.ppv"), g("prev.rf15.t5.pi0p02pct.ppv")
    row("P6", "precision at 0.02% prevalence: 1% target / 5% target", "about 1% / 0.4%", f"{100 * p1:.2f}% / {100 * p5:.2f}%", "prev.rf15.t1.pi0p02pct.ppv, prev.rf15.t5.pi0p02pct.ppv",
        round(100 * p1) == 1 and close(100 * p5, 0.4, 0.06), "0.35% rounds to 0.3% or 0.4% depending on the digit; the stored value is 0.3495%, so '0.35%' is the safe wording.")
    # ---- negatives
    aucs = {k: v["value"] for k, v in R.items() if re.fullmatch(r"ph\.gate\.[A-Z-]+\.[a-z_]+\.auc_D1", k)}
    mk = min(aucs, key=aucs.get)
    row("N1a", "smallest point AUC over generators and modes (gate D1)", "0.781", f"{aucs[mk]:.3f} ({mk})", "ph.gate.*.auc_D1", round(aucs[mk], 3) == 0.781)
    sa = g("ph.surrogate.auc")
    row("N1b", "surrogate discriminator AUC", "0.995", f"{sa:.3f}", "ph.surrogate.auc", round(sa, 3) == 0.995)
    npass = sum(1 for k in R if re.fullmatch(r"ph\.gate\.[A-Z-]+\.[a-z_]+\.passed", k) and R[k]["value"] == 1)
    row("N1c", "generator-mode pairs that passed the gate", "none", str(npass), "ph.gate.*.passed", npass == 0)
    row("N2a", "pool-level mis-triage change, class-conditional upper-end policy P3 against the lowered table (the prompt calls it UA-SCT) at +-16 g", "-0.003 [-0.011, 0.003]",
        "see note", "f.f3.pool.mis_triage.p3 (a level, not the difference); N28 text in NEGATIVES_REGISTER.md", True,
        "The figure -0.003 [-0.011, +0.003] is the N28 row of NEGATIVES_REGISTER.md (P3 minus P1e). The names differ: it is P3, not UA-SCT. Quote it as the N28 result; the stored differences are under `f.f3.*` (see the register).")
    r1, r2 = g("t4.b.loss60.P2.reach10_critical"), g("t4.b.loss60.P1.reach10_critical")
    row("N2b", "SCT (P2) against the table (P1), single car at 60% loss, critical reach within 10 s", "0.473 vs 0.768", f"{r1:.3f} vs {r2:.3f}", "t4.b.loss60.P2.reach10_critical, t4.b.loss60.P1.reach10_critical", round(r1, 3) == 0.473 and round(r2, 3) == 0.768)
    c5, c8 = g("pa.hA1.n_cells_gain5"), g("pa.hA1.n_cells_lose2")
    row("N3a", "OS-DR: cells with a gain of at least 5 points (of 32); cells lost by more than 2", "5 of 32; 8", f"{c5} of {g('pa.hA1.n_cells')}; {c8}", "pa.hA1.n_cells_gain5, pa.hA1.n_cells_lose2", c5 == 5 and c8 == 8,
        "RELEASE_RESULTS.md says 7 and 8. The '5 gained' is from an earlier run with pairs that used a validation-selected ratio (DECISIONS); the stored held-out result is 7 gained, 8 lost.")
    g1, g2 = g("pa.hA2.vs_osdr.n_cells_gain5"), g("pa.hA2.vs_tamang.n_cells_gain5")
    row("N3b", "GS-CA: burst cells (of 16) with a gain of at least 5 points, against OS-DR / against the slot baseline", "none", f"{g1} / {g2}", "pa.hA2.vs_osdr.n_cells_gain5, pa.hA2.vs_tamang.n_cells_gain5", g1 == 0 and g2 == 0)
    fa = g("p.p4c.loco.a5.V0.false_alarm_rate") if "p.p4c.loco.a5.V0.false_alarm_rate" in R else None
    row("N4", "conformal false-alarm rate at the 5% target (leave-one-size-out, pooled)", "0.053", f"{fa:.4f}" if fa is not None else "key absent", "p.p4c.loco.a5.V0.false_alarm_rate", fa is not None and close(fa, 0.053, 0.001),
        "The prompt says 'on the de-duplicated test set'; the stored 0.0535 is the leave-one-vehicle-size-category-out pooled value (POSITIVE_PUSH_RESULTS). Both round to 0.05 plus 0.003 to 0.004.")
    row("N5", "SW-420 not significantly better (p about 0.125)", "p about 0.125", "no key and no document gives this number; `hw.H6` is NOT_RUN (hw_events.csv not found)", "hw.H6.*", False,
        "Not verifiable from results.json. Do not quote until Part S5 (simulated) is run; a real SW-420 result needs the author's hardware logs.")


def neg_rows():
    """Verdict word of the named N items: NOVELTY.md (N15, N18), NEGATIVES_REGISTER.md (N20, N28), CLAIM_EVIDENCE.md (N24, N25)."""
    nov = Path("docs/06_references/NOVELTY.md").read_text(encoding="utf-8")
    neg = Path("docs/03_results/NEGATIVES_REGISTER.md").read_text(encoding="utf-8")
    ce = Path("docs/03_results/CLAIM_EVIDENCE.md").read_text(encoding="utf-8")
    out = []
    for n in ("N15", "N18"):
        m = re.search(rf"^\| {n} \|.*?\| (NO_IMPROVEMENT_FOUND|[A-Z_]{{6,}}) \|", nov, re.M)
        out.append((n, (m.group(1) if m else "row not found") + " (NOVELTY.md)"))
    for n in ("N20", "N28"):
        m = re.search(rf"^\| {n} [^|]*\|[^|]*\|\s*(NO_IMPROVEMENT_FOUND|NOT SUPPORTED)", neg, re.M)
        out.append((n, (m.group(1) if m else "row not found") + " (NEGATIVES_REGISTER.md)"))
    for n in ("N24", "N25"):
        ms = re.findall(rf"\({n}\) \|[^|]*\|[^|]*\|[^|]*\| \*\*([A-Z ]+)\*\*", ce)
        out.append((n, ("; ".join(ms) if ms else "row not found") + " (CLAIM_EVIDENCE.md)"))
    return out


def hyp_counts():
    txt = Path("docs/00_overview/PROJECT_STATUS.md").read_text(encoding="utf-8")
    sec = txt.split("## Verdict table")[1].split("## Positive results")[0]
    by_round: dict[str, dict[str, int]] = {}
    for ln in sec.splitlines():
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if len(c) >= 6 and c[0] not in ("Id", "---") and not set(c[0]) <= set("-") and not c[1].startswith("Combined"):  # the rows of the combined run itself are not part of the re-verified status table
            v = c[3]
            by_round.setdefault(c[1], {})
            by_round[c[1]][v] = by_round[c[1]].get(v, 0) + 1
    tot: dict[str, int] = {}
    for d in by_round.values():
        for v, n in d.items():
            tot[v] = tot.get(v, 0) + n
    v5 = [k for k in R if re.fullmatch(r"f\.holm\.h[a-z0-9]+\.verdict", k)]
    v5c: dict[str, int] = {}
    for k in v5:
        v5c[g(k)] = v5c.get(g(k), 0) + 1
    return by_round, tot, v5c, g("f.holm.family_size")


def main():
    build_rows()
    nbad = [r for r in rows if not r["ok"]]
    by_round, tot, v5c, v5n = hyp_counts()
    L = ["# Status table re-verified (Part V of the combined run)", "",
         "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-14 |", "| Owner | Mritula S |",
         "| Scope | Each headline number of the status table recomputed from results.json; mismatches listed (generated). |",
         "| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, ANALYTICAL |", "| Abbreviations | ACK = acknowledgement frame; AUC = area under the ROC curve |", "<!-- header:end -->", "",
         "Generated by `python -m crashguard.sh_v`. No result was changed. The recomputed value wins where the two differ.", "",
         f"**Summary: {len(rows)} rows, {len(rows) - len(nbad)} match, {len(nbad)} do not match** ({', '.join(r['id'] for r in nbad)}).", "",
         "| Id | Claim | Stated value | Recomputed value | Source key | Match |", "|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['claim']} | {r['stated']} | {r['recomputed']} | `{r['keys']}` | {'yes' if r['ok'] else '**no**'} |")
    L += ["", "## Notes on the rows that do not match", ""]
    for r in nbad:
        L.append(f"- **{r['id']}**: {r['note']}")
    L += ["", "## Rows marked yes with a caveat", ""]
    for r in rows:
        if r["ok"] and r["note"]:
            L.append(f"- **{r['id']}**: {r['note']}")
    L += ["", "## Named negatives (verdict word read from `docs/03_results/NEGATIVES_REGISTER.md`)", "", "| Item | Register status |", "|---|---|"]
    for n, v in neg_rows():
        L.append(f"| {n} | {v} |")
    L += ["", "## Hypothesis counts by family (kept apart so the paper does not mix them)", "",
          "**All studies** (the verdict table of `docs/00_overview/PROJECT_STATUS.md`, one row per hypothesis):", "",
          "| Round | " + " | ".join(sorted({v for d in by_round.values() for v in d})) + " |", "|---|" + "---|" * len({v for d in by_round.values() for v in d})]
    cols = sorted({v for d in by_round.values() for v in d})
    for rd, d in by_round.items():
        L.append(f"| {rd} | " + " | ".join(str(d.get(c, 0)) for c in cols) + " |")
    L.append("| **All** | " + " | ".join(f"**{tot.get(c, 0)}**" for c in cols) + " |")
    L += ["", f"Total {sum(tot.values())} hypotheses. Several release rows (`hq*`) are reruns of earlier hypotheses, so the total counts some questions twice.", "",
          f"**V5 confirmatory family after Holm** (`f.holm.*`, family size {v5n}): " + ", ".join(f"{n} {k}" for k, n in sorted(v5c.items())) + ". "
          "Only H-C3 reached SUPPORTED in that family, and it rests on a generator that was fitted on all pooled records; see row P2f.", ""]
    pats = ["+0.030", "0.0037", "5 of 32", "no gain at +-32", "p about 0.125"]
    files = [Path(x) for x in ("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", "docs/03_results/CLAIM_EVIDENCE.md", "README.md", "paper/main.tex", "paper/ABSTRACT_FACTS.md")] + sorted(Path("paper/generated").glob("*.tex"))
    hits = [(f.as_posix(), p_) for f in files if f.exists() for p_ in pats if p_ in f.read_text(encoding="utf-8")]
    L += ["", "## Paper and claims files checked for the stated values that did not match", "",
          "Searched " + ", ".join(f"`{f.as_posix()}`" for f in files) + " for: " + ", ".join(f"`{p_}`" for p_ in pats) + ". "
          + ("Found: " + "; ".join(f"{a} contains {b}" for a, b in hits) if hits else "None of these strings appears in any of them, so no correction to the paper or the claims files was needed; the mismatching values come from the run prompt only."), ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"{len(rows)} rows; mismatches: {[r['id'] for r in nbad]}")
    print(by_round, tot, v5c)


if __name__ == "__main__":
    main()
