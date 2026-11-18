"""P0 (docs/02_preregistration/PREREGISTRATION_V13.md section 1): refit of the H-C3 stress test on the NHTSA development fold only. Keys ``pp.p0.*``.

The generator code, settings and seeds are those of ``fin_c`` (unchanged). Fitted to the 543 development records. The fidelity gate compares the generator with the real validation and sealed records of each mode
(five KS statistics at most 0.20); the grid, the 0.80 rule, the ladder and the criterion are those of V5 H-C3. The stored original (``f.c.*``, ``f.holm.hc3.*``) is read and shown beside the refit, never changed.

    python -m crashguard.pp_p0_refit
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from scipy.stats import ks_2samp

from crashguard import fin_c as C
from crashguard import fin_synth as G
from crashguard.fin_common import Entries

SRC = "src/crashguard/pp_p0_refit.py"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "synthetic"
PROV = ROOT / "docs" / "03_results" / "H_C3_PROVENANCE.md"
CAP = "synthetic stress test, generator refitted on the development fold only, assumptions in SYNTHETIC_ASSUMPTIONS.md"
HYP18 = ["hb2", "hc3", "hf1", "hf1b", "hf1c", "hf1d", "hf1e", "hf2a", "hf2b", "hf2c", "hf2d", "hf2e", "hf2f", "hf3a", "hf3b", "hg3a", "hg3b", "hg3c"]


def main() -> None:
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    df = C.real_desc()
    dev = df[df["fold"] == "dev"].reset_index(drop=True)
    held = df[df["fold"].isin(["val", "test"])].reset_index(drop=True)
    par = C.fit_params(dev)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "generator_params_dev543.json").write_text(json.dumps(par, indent=1), encoding="utf-8")
    E = Entries("pp.p0", SRC)
    E.add("refit.n_records_fit", int(len(dev)), "records", "MEASURED_SOFTWARE", "NHTSA development fold only (fold == dev)")
    E.add("refit.n_records_gate", int(len(held)), "records", "MEASURED_SOFTWARE", "real validation and sealed records read by the fidelity gate only")
    passed, rows = [], []
    for m in G.MODES:
        S = [s for s in (G.descriptors(G.make_pulse(par, m, C.SEED0_FID + k)) for k in range(C.N_FID)) if s]
        S = pd.DataFrame(S)
        rh, rd = held[held["mode"] == m], dev[dev["mode"] == m]
        ok = True
        for d in G.DESC:
            kh, kd = ks_2samp(rh[d], S[d]), ks_2samp(rd[d], S[d])
            E.add(f"fidelity.{m}.{d}.ks_D_heldout", round(float(kh.statistic), 4), "statistic", "SIMULATED", f"two-sample KS, real validation and sealed n={len(rh)} against synthetic n={len(S)} ({CAP}); used for the gate")
            E.add(f"fidelity.{m}.{d}.ks_D_dev", round(float(kd.statistic), 4), "statistic", "SIMULATED", f"same against the development fold n={len(rd)} (in-sample); reported, not used for the decision")
            ok &= bool(kh.statistic <= C.D_MAX)
            rows.append((m, d, len(rh), float(kh.statistic), float(kd.statistic), R.get(f"f.c.fidelity.{m}.{d}.ks_D")))
        E.add(f"fidelity.{m}.passes", int(ok), "flag", "SIMULATED", f"all five held-out KS statistics at most {C.D_MAX}")
        if ok:
            passed.append(m)
    E.add("fidelity.modes_passed", ",".join(passed) or "none", "modes", "SIMULATED", CAP)
    lad = C.ladder()
    T = C.grid(par, list(G.MODES), C.N_GRID, C.SEED0_GRID, None)
    hc3 = {}
    for m in G.MODES:
        T[m].to_csv(OUT / f"pp_p0_grid_{m}.csv", index=False)
        s = C.smallest(T[m])
        rs = C.real_smallest(m, R)
        tag = "" if m in passed else "EXPLORATORY: the mode failed the held-out fidelity gate; "
        E.add(f"grid.{m}.synthetic_smallest_range", s[0] if s else "NOT_RUN", "g", "SIMULATED" if s else "NOT_RUN", f"{tag}smallest range with lower interval end >= 0.80 (1,000 synthetic pulses; {CAP})")
        E.add(f"grid.{m}.real_smallest_range", rs if rs else "NOT_RUN", "g", "MEASURED_SOFTWARE" if rs else "NOT_RUN", "p.b2.* (pooled records), unchanged")
        if s and rs:
            step = abs(lad.index(s[0]) - lad.index(rs))
            E.add(f"grid.{m}.step_difference", step, "rungs", "SIMULATED", f"{tag}difference on the ladder of ranges")
            if m in passed:
                hc3[m] = step
    overlap = [m for m in ("frontal_barrier", "pole") if m in passed]
    E.add("hC3.overlapping_modes_passed", ",".join(overlap) or "none", "modes", "SIMULATED", "overlapping modes (frontal barrier, pole) that passed the held-out gate")
    if overlap and all(m in hc3 for m in overlap):
        met = all(hc3[m] <= 1 for m in overlap)
        E.add("hC3.criterion_met", int(met), "flag", "SIMULATED", "smallest synthetic range within one range step of the real result for every overlapping mode that passed the gate")
        p = 0.001 if met else 1.0
        verdict_basis = "evaluated"
    else:
        met, p = False, 1.0
        E.add("hC3.criterion_met", "NOT_RUN", "flag", "NOT_RUN", "no overlapping mode passed the held-out fidelity gate, or the real or synthetic result is missing; counted as not supported in the family (p = 1)")
        verdict_basis = "not_run"
    E.add("hC3.p_raw", p, "p", "SIMULATED", "preregistered convention for an agreement criterion (0.001 if it holds, 1.0 otherwise)")
    # Holm over the 18 hypotheses of V5, with the refit p for H-C3 and the stored p for the others
    ps = {h: float(R[f"f.holm.{h}.p_raw"]) for h in HYP18}
    ps["hc3"] = p
    order = sorted(ps, key=lambda h: ps[h])
    m18 = len(order)
    run = 0.0
    holm = {}
    for rank, h in enumerate(order):
        run = max(run, (m18 - rank) * ps[h])
        holm[h] = min(1.0, run)
    verdict = "NOT_RUN" if verdict_basis == "not_run" else ("SUPPORTED" if met and holm["hc3"] < 0.05 else "MIXED" if met else "NOT SUPPORTED")
    E.add("holm.hc3.p_holm_refit", round(holm["hc3"], 4), "p", "SIMULATED", "Holm over the 18 hypotheses of V5 with the refit p-value for H-C3")
    E.add("holm.hc3.verdict_refit", verdict, "verdict", "NOT_RUN" if verdict == "NOT_RUN" else "SIMULATED", "the verdict the paper uses (refit on the development fold only)")
    E.add("holm.hc3.verdict_original", R["f.holm.hc3.verdict"], "verdict", "SIMULATED", "stored original (generator fitted to all 913 records, in-sample); not used by the paper")
    for h in HYP18:
        if h != "hc3":
            E.add(f"holm.{h}.p_holm_with_refit", round(holm[h], 4), "p", "SIMULATED", "Holm-adjusted p of the V5 family after replacing the H-C3 p-value by the refit p-value; the stored verdicts of these hypotheses are not changed")
    E.write()
    # provenance document: refit block
    L = ["## Refit results", "", "Generated by `python -m crashguard.pp_p0_refit` (SIMULATED, MEASURED_SOFTWARE). The paper uses the refit verdict only.", "",
         f"Generator fitted to the development fold only ({len(dev)} records); gate against the real validation and sealed records ({len(held)}). Parameter file `results/synthetic/generator_params_dev543.json`.", "",
         "| Mode | Descriptor | Held-out records | KS D (held-out, refit gate) | KS D (development, in-sample) | KS D (original, all 913, in-sample) |", "|---|---|---:|---:|---:|---:|"]
    for m, d, n, kh, kd, ko in rows:
        L.append(f"| {m} | {d} | {n} | {kh:.3f} | {kd:.3f} | {'' if ko is None else f'{float(ko):.3f}'} |")
    L += ["", "| Item | Original (913 records, in-sample) | Refit (543 records, held-out gate) |", "|---|---|---|",
          f"| Modes passing the gate | {R['f.c.fidelity.modes_passed']} | {','.join(passed) or 'none'} |",
          f"| Frontal barrier: smallest synthetic range (g) | {R.get('f.c.grid.frontal_barrier.synthetic_smallest_range')} | {(C.smallest(T['frontal_barrier']) or ['none'])[0]} |",
          f"| Pole: smallest synthetic range (g) | not tested (failed gate) | {(C.smallest(T['pole']) or ['none'])[0]}{'' if 'pole' in passed else ' (EXPLORATORY, failed the gate)'} |",
          f"| Real smallest range, frontal barrier / pole (g) | {R.get('f.c.grid.frontal_barrier.real_smallest_range')} / 64 | same |",
          f"| H-C3 criterion met | {R['f.c.hC3.criterion_met']} | {'NOT_RUN' if verdict_basis == 'not_run' else int(met)} |",
          f"| H-C3 Holm-adjusted p (18 hypotheses) | {R['f.holm.hc3.p_holm']} | {round(holm['hc3'], 4)} |",
          f"| H-C3 verdict | {R['f.holm.hc3.verdict']} | {verdict} |"]
    text = PROV.read_text(encoding="utf-8")
    a, b = text.index("<!-- p0:start -->"), text.index("<!-- p0:end -->")
    PROV.write_text(text[:a] + "<!-- p0:start -->\n" + "\n".join(L) + "\n" + text[b:], encoding="utf-8")
    print("passed", passed, "step differences", hc3, "verdict", verdict, "holm", round(holm["hc3"], 4))
    print({m: C.smallest(T[m]) for m in G.MODES})


if __name__ == "__main__":
    main()
