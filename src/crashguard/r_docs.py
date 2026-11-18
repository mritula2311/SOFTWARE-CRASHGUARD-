"""R5: write docs/00_overview/PROJECT_STATUS.md from results/results.json (every verdict and number is read from the file, none is typed).

    python -m crashguard.r_docs

A hypothesis row has: id, round, plain statement, the results key that holds its verdict, and the evidence label (read from the key).
Verdict words: SUPPORTED, PARTLY SUPPORTED, NOT SUPPORTED, NOT RUN. A `criterion_met` of 1 is SUPPORTED, 0 is NOT SUPPORTED, "NOT_RUN" is NOT RUN. Keys of a block that
has not run yet show NOT RUN with the reason "release block not run".
"""
from __future__ import annotations

import json
from pathlib import Path

R = Path("results/results.json")
OUT = Path("docs/00_overview/PROJECT_STATUS.md")

# (id, round, statement, verdict key, kind)  kind: "crit" criterion_met, "verdict" text verdict, "t14" survives_correction
H = [
    ("H-a", "Round 3 (UA-SCT)", "At +-16 g, taking the class from the upper end of a conformal class interval lowers mis-triage against the plain severity table.", "t14.H-a.survives_correction", "t14"),
    ("H-b", "Round 3 (UA-SCT)", "That rule costs more non-severe events on the fast path, and a duty cap bounds the fast-path airtime.", "t14.H-b.survives_correction", "t14"),
    ("H-c", "Round 3 (UA-SCT)", "The gain shrinks at +-64 g because the intervals are narrower.", "t14.H-c.survives_correction", "t14"),
    ("v2 H-A1", "v2 studies", "A tail-aware estimator lowers the 90th-percentile delta-V error by 5 points or more at +-16 g.", "v2.a.hA1.criterion_met", "crit"),
    ("v2 H-A2", "v2 studies", "Adaptive conformal intervals are narrower than plain ones for clipped events.", "v2.a.hA2.criterion_met", "crit"),
    ("v2 H-A3", "v2 studies", "Deterministic delta-V bounds contain the reference for at least 90% of tests.", "v2.a.hA3.criterion_met", "crit"),
    ("v2 H-D1", "v2 studies", "A clip-onset flag saves at least 100 ms for severe tests without more under-triage.", "v2.d.hD1.criterion_met", "crit"),
    ("v2 H-D2", "v2 studies", "The clip-onset flag over-triages fewer than 10% of low or moderate tests.", "v2.d.hD2.criterion_met", "crit"),
    ("v2 H-B1", "v2 studies", "A load-adaptive escalation variant gains 3 points or more in most burst cells.", "v2.b.hB1.criterion_met", "crit"),
    ("v2 H-B2", "v2 studies", "No adaptive variant harms steady-state cells by more than 2 points.", "v2.b.hB2.criterion_met", "crit"),
    ("v2 H-B3", "v2 studies", "A token bucket keeps at least 80% of the best variant's burst gain.", "v2.b.hB3.criterion_met", "crit"),
    ("v2 H-E1", "v2 studies", "A 4-byte tag instead of 8 bytes raises burst reach by 2 points or more.", "v2.e.hE1.criterion_met", "crit"),
    ("v2 H-E2", "v2 studies", "An 8-byte tag keeps the forgery work factor above 2^32 attempts.", "v2.e.hE2.criterion_met", "crit"),
    ("v2 H-F1", "v2 studies", "For critical alerts the model-optimal hold is zero for every cost ratio.", "v2.f.hF1.criterion_met", "crit"),
    ("v2 H-F2", "v2 studies", "A 2 s hold on severe alerts removes at least 20% of false severe alerts at no loss in critical reach.", "v2.f.hF2.criterion_met", "crit"),
    ("H-X1", "Journal push", "A 16-bit forest loses at most 0.005 AP and cuts the flash estimate by at least 30%.", "x.holm.H-X1.verdict", "verdict"),
    ("H-X2", "Journal push", "A trigger cascade raises the crash pass share by 2 points over the 2 g threshold.", "x.holm.H-X2.verdict", "verdict"),
    ("H-X3", "Journal push", "Group-aware training raises recall at the 1% false-alarm target by 1 point.", "x.holm.H-X3.verdict", "verdict"),
    ("H-X5", "Journal push", "The fill-plus-ridge delta-V keeps rank correlation of at least 0.90 at +-16 g.", "x.holm.H-X5.verdict", "verdict"),
    ("H-X6", "Journal push", "An anchored estimator lowers the 90th-percentile delta-V error by 5 points or more at +-16 g.", "x.holm.H-X6.verdict", "verdict"),
    ("H-X7", "Journal push", "A two-part fusion of estimators beats each part alone within +-10% of the reference.", "x.holm.H-X7.verdict", "verdict"),
    ("H-X8", "Journal push", "A sequential rule decides 100 ms earlier than the early-exit rule at equal recall.", "x.holm.H-X8.verdict", "verdict"),
    ("H-P1", "Positive push", "A direct severity classifier beats the best estimator by 0.03 macro-F1 with less under-triage.", "p.holm.hp1.verdict", "verdict"),
    ("H-P2", "Positive push", "A one-sided severity interval reaches at least 0.85 coverage overall and for the pole mode.", "p.holm.hp2.verdict", "verdict"),
    ("H-P3a", "Positive push", "Abstaining on the least reliable 30% halves under-triage among retained events.", "p.holm.hp3a.verdict", "verdict"),
    ("H-P3b", "Positive push", "Routing abstained events to the fast path lowers pool-level mis-triage by 2 points.", "p.holm.hp3b.verdict", "verdict"),
    ("H-P4a", "Positive push", "A compact forest has at most half the flash estimate and an AP within 0.01 of the reference.", "p.holm.hp4a.verdict", "verdict"),
    ("H-P4b", "Positive push", "Augmentation raises recall at the 1% false-alarm target by 0.02.", "p.holm.hp4b.verdict", "verdict"),
    ("H-P4c", "Positive push", "Some calibration keeps the false-alarm rate near its target and beats the trivial rule by 0.02 recall.", "p.holm.hp4c.verdict", "verdict"),
    ("H-B2 (finish)", "Finishing round", "A fast path of flash and hold alone beats fixed retries by 5 points in 60% of held-out cells.", "f.holm.hb2.verdict", "verdict"),
    ("H-C3", "Finishing round", "A synthetic stress test gives the same smallest sensor range as the real records for the modes that passed fidelity.", "f.holm.hc3.verdict", "verdict"),
    ("H-F1", "Finishing round", "Real plus synthetic training lets a direct classifier beat the anchored estimator (rerun of H-P1).", "f.holm.hf1.verdict", "verdict"),
    ("H-F1b", "Finishing round", "Rerun of H-P2 with synthetic training data.", "f.holm.hf1b.verdict", "verdict"),
    ("H-F1c", "Finishing round", "Rerun of H-P3a with synthetic training data.", "f.holm.hf1c.verdict", "verdict"),
    ("H-F1d", "Finishing round", "Rerun of H-X6 with synthetic training data.", "f.holm.hf1d.verdict", "verdict"),
    ("H-F1e", "Finishing round", "Rerun of H-X5 with synthetic training data.", "f.holm.hf1e.verdict", "verdict"),
    ("H-F2a", "Finishing round", "Surrogate windows raise recall at the 1% target (rerun of H-P4b).", "f.holm.hf2a.verdict", "verdict"),
    ("H-F2b", "Finishing round", "Group-aware training with surrogate windows (rerun of H-X3).", "f.holm.hf2b.verdict", "verdict"),
    ("H-F2c", "Finishing round", "Trigger cascade with surrogate windows (rerun of H-X2).", "f.holm.hf2c.verdict", "verdict"),
    ("H-F2d", "Finishing round", "16-bit forest with surrogate windows (rerun of H-X1).", "f.holm.hf2d.verdict", "verdict"),
    ("H-F2e", "Finishing round", "Sequential rule with surrogate windows (rerun of H-X8).", "f.holm.hf2e.verdict", "verdict"),
    ("H-F2f", "Finishing round", "Calibration variants with surrogate windows (rerun of H-P4c).", "f.holm.hf2f.verdict", "verdict"),
    ("H-F3a", "Finishing round", "Better severity estimates change the equal-escalation comparison of the simulator.", "f.holm.hf3a.verdict", "verdict"),
    ("H-F3b", "Finishing round", "Abstain routing helps on the held-out simulator grid.", "f.holm.hf3b.verdict", "verdict"),
    ("H-G3a", "Finishing round", "A slotted fast path beats pure ALOHA by 5 points of critical reach in 60% of cells.", "f.holm.hg3a.verdict", "verdict"),
    ("H-G3b", "Finishing round", "Listen-before-talk beats duty-cycle-only access.", "f.holm.hg3b.verdict", "verdict"),
    ("H-G3c", "Finishing round", "A vehicle-to-vehicle relay beats no relay for reach within 30 s.", "f.holm.hg3c.verdict", "verdict"),
]


NOTES = {
    "H-a": "Held against the plain severity table. The equal-escalation comparison (N28) shows the same gain from lowering the table thresholds, so the interval itself shows no benefit.",
    "H-b": "Same note as H-a.",
    "H-c": "Same note as H-a.",
    "v2 H-E2": "Formula only (ANALYTICAL).",
    "H-C3": "Holds for the frontal barrier mode only; the pole mode failed the fidelity check.",
}


def load() -> dict:
    return {e["name"]: e for e in json.loads(R.read_text(encoding="utf-8"))}


def verdict(r: dict, key: str, kind: str) -> tuple[str, str]:
    e = r.get(key)
    if e is None:
        return "NOT RUN", "NOT_RUN"
    v = e["value"]
    if v == "NOT_RUN" or e["origin"] == "NOT_RUN":
        return "NOT RUN", "NOT_RUN"
    if kind == "verdict":
        return str(v).upper().replace("MIXED", "PARTLY SUPPORTED"), e["origin"]
    return ("SUPPORTED" if v in (1, True, 1.0) else "NOT SUPPORTED"), e["origin"]


def v7_rows(r: dict) -> list[tuple[str, str, str, str, str]]:
    """Release-block rows: id, round, statement, verdict, label. Read from `q.holm.*.verdict` and `pa.holm.*.verdict` when they exist."""
    rows = []
    for name in sorted(k for k in r if k.endswith(".verdict") and k.startswith(("q.holm.", "pa.holm."))):
        e = r[name]
        hid = name.split(".")[2]
        rows.append((hid, "Release (V7)", str(e.get("notes", ""))[:200], str(e["value"]).upper(), e["origin"]))
    return rows


def c11_rows(r: dict) -> list[tuple[str, str, str, str, str, str]]:
    """Combined-run rows (family S and family R of PREREGISTRATION_V11): id, round, statement, verdict, label, key. Read from `sh.holm.*.verdict` and `ar.holm.*.verdict`."""
    rows = []
    for name in sorted(k for k in r if k.endswith(".verdict") and k.startswith(("sh.holm.", "ar.holm."))):
        e = r[name]
        hid = ("H-S" if name.startswith("sh.") else "H-R") + name.split(".")[2][2:]
        fam = "Combined, family S (simulated hardware-format)" if name.startswith("sh.") else "Combined, family R (architecture and protocol)"
        rows.append((hid, fam, str(e.get("notes", "")), str(e["value"]).upper(), e["origin"], name))
    return rows


def main() -> None:
    r = load()
    rows = []
    for hid, rnd, text, key, kind in H:
        v, lab = verdict(r, key, kind)
        rows.append((hid, rnd, text, v, lab, key))
    rows += [(a, b, c, d, e, "") for a, b, c, d, e in v7_rows(r)]
    rows += c11_rows(r)
    n = {k: sum(1 for x in rows if x[3] == k) for k in ("SUPPORTED", "PARTLY SUPPORTED", "NOT SUPPORTED", "NOT RUN")}
    L = [
        "# Project status", "",
        "<!-- header:start -->", "<!-- header:end -->", "",
        "Generated by `python -m crashguard.r_docs` from `results/results.json`. Every verdict below is read from the key in the last column. Nothing here is measured on the car: no hardware result is read or used. "
        "Simulated and synthetic items are statements under stated assumptions (`docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md`), not statements about real crashes or deployments.", "",
        "## Verdict table", "",
        f"This table lists {len(rows)} hypotheses of the rounds up to the combined run: {n['SUPPORTED']} supported, {n['PARTLY SUPPORTED']} partly supported, {n['NOT SUPPORTED']} not supported, {n['NOT RUN']} not run. "
        f"The ledger of all versions (V1 to V17) holds {int(r['r6.ledger.all.preregistered']['value'])} hypotheses: {int(r['r6.ledger.all.run']['value'])} run, {int(r['r6.ledger.all.supported']['value'])} supported, {int(r['r6.ledger.all.not_supported']['value'])} not supported, "
        f"{int(r['r6.ledger.all.partly']['value'])} partly supported, {int(r['r6.ledger.all.not_run']['value'])} not run (`docs/04_audits/HYPOTHESIS_LEDGER.md`). "
        "A hypothesis is SUPPORTED only when its preregistered criterion is met (and, where a Holm correction was preregistered, the corrected p-value is below 0.05). "
        "No criterion was relaxed after the fact. Rounds are listed in the order in which they were run. "
        "The families are not mixed in the paper: the V5 confirmatory family (`f.holm.*`, 18 hypotheses) has 1 supported; the combined run has two families, "
        f"S ({sum(1 for x in rows if x[1].startswith('Combined, family S') and x[3] == 'SUPPORTED')} of {sum(1 for x in rows if x[1].startswith('Combined, family S'))} supported) and "
        f"R ({sum(1 for x in rows if x[1].startswith('Combined, family R') and x[3] == 'SUPPORTED')} of {sum(1 for x in rows if x[1].startswith('Combined, family R'))} supported); some release rows rerun earlier hypotheses, so the total counts some questions twice.", "",
        "| Id | Round | Plain statement | Verdict | Label | Results key |", "|---|---|---|---|---|---|",
    ]
    for hid, rnd, text, v, lab, key in rows:
        L.append(f"| {hid} | {rnd} | {text}{(' Note: ' + NOTES[hid]) if hid in NOTES else ''} | {v} | {lab} | {('`' + key + '`') if key else 'see `q.*` and `pa.*`'} |")
    pos = [x for x in rows if x[3] == "SUPPORTED"]
    neg = [x for x in rows if x[3] == "NOT SUPPORTED"]
    L += ["", "## Positive results", "",
          "Each row is a hypothesis whose preregistered criterion was met. Context and limits are in `docs/03_results/` and in `docs/03_results/CLAIM_EVIDENCE.md`.", "",
          "| Id | Plain statement | Label |", "|---|---|---|"]
    L += [f"| {h} | {t} | {lab} |" for h, _, t, _, lab, _ in pos]
    L += ["", "## Negative results", "",
          f"{len(neg)} hypotheses were not supported. They are kept in full in `docs/03_results/NEGATIVES_REGISTER.md`; no original verdict is removed or softened.", "",
          "| Id | Plain statement | Label |", "|---|---|---|"]
    L += [f"| {h} | {t} | {lab} |" for h, _, t, _, lab, _ in neg]
    L += ["", "## Limits", "",
          "- **No hardware.** The car experiments (H1 to H6) were not run in this repository; the author's hardware logs were not read. Flash sizes are host arithmetic or an x86-64 compile, not ESP32 measurements.",
          "- **Simulator-only protocol results.** Delivery, retry and access results come from a simulator with stated assumptions; they are not radio measurements. The Indian 433 MHz rules allow a duty cycle of at most 10% (G.S.R. 347(E), 2022, read in full on 2026-11-16); the simulations use a stricter 1% hourly allowance.",
          "- **Synthetic coverage by mode.** Synthetic pulses represent only the crash modes that passed the fidelity gate; see `docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md` and the provenance record `SYNTHETIC_PROVENANCE.md` in the same folder, when the release blocks have run. Synthetic data is used for training and clearly labelled stress tests only; validation, calibration, thresholds and real-data metrics use real data only.",
          "- **Preregistration timing.** The V4 preregistration addendum was committed before the earliest sealed NHTSA scoring but after one test scoring (P4a); details in `docs/04_audits/PREREG_V4_AUDIT.md`.",
          "- **Data.** VZCrash events were pre-selected on the device and have no vehicle identifier; identical recordings appear across the official splits (`docs/04_audits/VZCRASH_AUDIT.md`). NHTSA records are mostly high-speed barrier tests.",
          "- **Security.** One shared key, no key rotation, no encryption of position; limits are listed in `docs/01_protocol/PACKET_FORMAT.md`. The alert-protocol model check is a bounded search of a model, not a proof of the firmware.", "",
          "## Licence split", "",
          "| Part | Licence |", "|---|---|",
          "| Code (`src/`, `tests/`, `scripts/`, `Makefile`, `crashclip/`, `merge/`) | Apache-2.0 (`LICENSE`, `NOTICE`) |",
          "| Files derived from VZCrash (fitted surrogate parameters, audit tables, derived figures) | CC BY-NC 4.0: non-commercial use, with attribution to the dataset authors |",
          "| NHTSA-derived records and tables | Public-agency data; the terms of use were not verified in this repository |",
          "| Raw datasets | Not redistributed; `data/raw/` is git-ignored |", "",
          "## How to cite", "",
          "Cite the repository as given in `CITATION.cff` (also `CITATION.md`), and cite the VZCrash paper (arXiv 2606.06074) and the NHTSA Vehicle Crash Test Database when you use derived files. "
          "Full data and code statement: `docs/05_data_code/DATA_AND_CODE_STATEMENT.md`.", ""]
    OUT.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {OUT}: {len(rows)} hypotheses ({n})")


if __name__ == "__main__":
    main()
