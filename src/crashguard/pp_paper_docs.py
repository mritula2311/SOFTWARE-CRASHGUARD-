"""Part C documents: marker blocks ``pp`` in README.md (status row), PROJECT_STATUS.md, CLAIMS_FOR_COVER_LETTER.md and NEGATIVES_REGISTER.md. Numbers are read from results/results.json.

    python -m crashguard.pp_paper_docs
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
S, E = "<!-- pp:start -->", "<!-- pp:end -->"


def put(path: str, text: str, after_marker: str | None = None) -> None:
    p = ROOT / path
    t = p.read_text(encoding="utf-8").replace("\r\n", "\n")
    block = f"{S}\n{text.strip()}\n{E}"
    if S in t:
        a, b = t.index(S), t.index(E) + len(E)
        t = t[:a] + block + t[b:]
    elif after_marker and after_marker in t:
        i = t.index(after_marker)
        j = t.index("\n", i)
        t = t[:j] + "\n" + block + t[j:]
    else:
        t = t.rstrip("\n") + "\n\n" + block + "\n"
    p.write_text(t, encoding="utf-8")


def main() -> None:
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    v = R["pp.p1.verdict"]
    sup = R["pp.p1.n_tests_supported"]
    air9 = 100 * max(R[f"pp.p1.sf9.{s}.p{p}.extra_air_ratio"] for s in ("calib", "shipped") for p in ("0", "0.1", "0.3", "0.6"))
    air7 = 100 * max(R[f"pp.p1.sf7.{s}.p{p}.extra_air_ratio"] for s in ("calib", "shipped") for p in ("0", "0.1", "0.3", "0.6"))
    hc3 = R["pp.p0.holm.hc3.verdict_refit"]
    var = R.get("pp.c4.variant.summary", "NOT_RUN")
    row = ("| Part C: combined journal paper (`paper/main.tex`, supplement, figures, cover letter) | Written and audited in software, not compiled here (no TeX distribution; upload `paper/` to Overleaf). Preregistered in `docs/02_preregistration/PREREGISTRATION_V13.md` before the runs. "
           f"H-C3 refit on the development fold: {hc3} (frontal barrier only). Two-stage alert in ns-3: {v} ({sup} of 8 tests supported; extra airtime {air7:.0f}% at SF7 and {air9:.0f}% at SF9 against a 40% limit). "
           "Audit reports: `docs/04_audits/PP_PAPER_CLAIM_AUDIT.md`, `docs/04_audits/PP_REFERENCE_CHECK.md`. No hardware data. |")
    put("README.md", row, after_marker="| Round 3 (journal literature check")
    put("docs/00_overview/PROJECT_STATUS.md", f"""## Part C (combined paper)

- **P0, H-C3 refit** (SIMULATED): generator refitted on the 543 development records, gated on the 370 held-out records; frontal barrier and other pass the gate, the frontal duration statistic is {max(R[f'pp.p0.fidelity.frontal_barrier.{d}.ks_D_heldout'] for d in ('peak_g', 'duration_ms', 'dv_kmh', 'asym', 'shape')):.3f} against 0.20. Verdict {hc3} (Holm p {R['pp.p0.holm.hc3.p_holm_refit']}); the paper uses this verdict. See `docs/03_results/H_C3_PROVENANCE.md`.
- **P1, two-stage alert in ns-3** (SIMULATED): {v}; {sup} of 8 preregistered tests supported; clause (c) fails at SF9 (extra airtime {air9:.0f}%). See `docs/03_results/PAPER_P1_R3_NS3.md`.
- **Zero-spacing control** valid (`pp.c6.z0.valid` = {R['pp.c6.z0.valid']}): within the deadline and within the hourly allowance.
- **Boot-epoch variant of the car-reboot lemma** (FORMAL, design variant): {var}.
- **Paper:** `paper/main.tex`, `paper/supplement.tex`, `paper/generated/numbers.tex` (every number a macro), figures in `paper/figures/`, cover letter, highlights, graphical abstract, `paper/REPRODUCE.md`.
""")
    put("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md", f"""## Part C (combined paper) claims

| Claim | Evidence label | Section | Verdict |
|---|---|---|---|
| The H-C3 stress test, refitted on the development fold and gated on held-out records, gives the same smallest range as the real records for frontal-barrier pulses ({R['pp.p0.grid.frontal_barrier.synthetic_smallest_range']:g} g); the pole mode failed the gate and is not tested. | SIMULATED | Results A, C2 | H-C3 {hc3} (refit) |
| The two-stage alert arrives {R['pp.p1.sf7.calib.p0.earlier_median_s']:.2f} s (SF7) and {R['pp.p1.sf9.calib.p0.earlier_median_s']:.2f} s (SF9) earlier in ns-3 with delivery not worse; its extra airtime is {air7:.0f}% at SF7 and {air9:.0f}% at SF9 against a 40% limit. | SIMULATED | Results C, C5 | ns-3 verdict {v} |
| On measured links with loss of 40% or more a control that retries at once delivers {100 * R['r3.t1.explore.H.deliv.Z0']:.1f}% against {100 * R['r3.t1.H.deliv.D1']:.1f}% for D1; the control respects the deadline and the hourly allowance. | TRACE_DRIVEN | Results C, C6 | exploratory; D1 is not a contribution |
""")
    put("docs/03_results/NEGATIVES_REGISTER.md", f"""## Part C additions

- **Two-stage alert, SF9 airtime.** Extra airtime {air9:.0f}% against the 40% limit in ns-3 at SF9 (SF7: {air7:.0f}%); the flash costs a larger share of the alert's airtime at SF9 (`pp.p1.sf9.*.extra_air_ratio`). Clause (c) of H-R3 fails there.
- **H-C3 refit passes narrowly.** The frontal-barrier duration statistic is close to the gate; the pole mode fails it (`pp.p0.fidelity.*`).
- **Trace population.** Held-out LoED devices are mostly weak links (median loss {100 * R['pp.c6.links.median_loss']:.0f}%); delivery results on traces are statements about that population (`pp.c6.links.*`).
- **Car-reboot lemma.** Variant check: {var}.
""")
    print("docs blocks written")


if __name__ == "__main__":
    main()
