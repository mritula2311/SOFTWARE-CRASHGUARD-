"""P6: submission package: paper/cover_letter.md, paper/highlights.md, paper/graphical_abstract.svg and paper/REPRODUCE.md, with every number read from results/results.json.

    python -m crashguard.pp_submission
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / "paper"


def _keep_header(path: Path, text: str) -> str:
    """Keep the header block that scripts/doc_headers.py put into the previous version of a generated Markdown file."""
    s, e = "<!-- header:start -->", "<!-- header:end -->"
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if s in old and e in old:
            block = old[old.index(s): old.index(e) + len(e)]
            first_line, rest = text.split("\n", 1)
            return first_line + "\n\n" + block + "\n" + rest
    return text


def main() -> None:
    raise SystemExit('pp_submission.py is a one-time script that was already applied in the paper run. Running it again would overwrite paper/REPRODUCE.md and paper/highlights.md with older text. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    n = dict(groups=int(R["leakage.exact_hash_groups_across_splits"]), r1s=R["vz.v4.rf15.supplied.recall_at_1pct"], r1n=R["vz.v4.rf15.near.recall_at_1pct"],
             front=R["p.b2.frontal_barrier.smallest.config"].split("+-")[1].split(" g")[0], pole=R["p.b2.pole.smallest.config"].split("+-")[1].split(" g")[0],
             early=R["ar.r3.a1.earlier_median_s_p0"], air9=100 * max(R[f"pp.p1.sf9.{s}.p{p}.extra_air_ratio"] for s in ("calib", "shipped") for p in ("0", "0.1", "0.3", "0.6")),
             air7=100 * max(R[f"pp.p1.sf7.{s}.p{p}.extra_air_ratio"] for s in ("calib", "shipped") for p in ("0", "0.1", "0.3", "0.6")),
             dc=R["rd.x13.custom.d1b.pt"], dn=R["rd.x13.ns3.d1b.pt"], z0=100 * R["r3.t1.explore.H.deliv.Z0"], d1=100 * R["r3.t1.H.deliv.D1"], tearly=int(R["r3.t3.a1.earlier_ms_median"]))
    lg = {k: int(R[f'vf.ledger.all.{k}']) for k in ('preregistered', 'supported', 'not_supported', 'partly', 'not_run')}
    hl = [f"Audit finds {n['groups']} duplicate groups across VZCrash splits; recall falls once removed",
          f"Delta-V needs +-{n['front']} g (frontal) and +-{n['pole']} g (pole) on crash-test pulses",
          "Shared-key ACKs can be suppressed; per-vehicle binding and a boot counter are proved",
          f"Two-stage alert arrives about {n['early']:.1f} s early; its airtime cost depends on the SF",
          "Retry-policy gains differ between simulators; a no-hold control wins on real traces"]
    assert all(len(h) <= 85 for h in hl), [len(h) for h in hl]
    (P / "highlights.md").write_text(_keep_header(P / "highlights.md", "# Highlights\n\n" + "\n".join(f"- {h} ({len(h)} characters)" for h in hl) + "\n"), encoding="utf-8")

    ledger_n, ledger_s, ledger_ns, ledger_p, ledger_nr = lg["preregistered"], lg["supported"], lg["not_supported"], lg["partly"], lg["not_run"]
    cover = f"""# Cover letter (draft)

To the Editor, IEEE Access

Title: What a Low-Cost Crash-Alert Node Must Measure and How It Should Report: A Preregistered Software Evaluation of Sensing, Detection and Authenticated LoRa Alert Delivery

We submit this manuscript for consideration as a regular paper in IEEE Access.

**What the paper adds.** It evaluates the components of a low-cost crash-alert node in one preregistered study, with an evidence label on every result, and it reports every one of the {ledger_n} preregistered hypotheses ({ledger_s} supported, {ledger_ns} not supported, {ledger_p} partly supported, {ledger_nr} not run). It reports (C1) a duplicate audit of a public crash dataset ({n['groups']} cross-split groups of identical arrays; recall at the 1% false-alarm target goes from {n['r1s']:.3f} to {n['r1n']:.3f} when duplicates are removed); (C2) the accelerometer range that delta-V needs by crash mode (+-{n['front']} g for frontal-barrier and +-{n['pole']} g for pole pulses); (C3) a compact detector trade-off; (C4) Tamarin proofs of alert authenticity, per-vehicle acknowledgement binding and freshness properties for a per-vehicle-key design, the acknowledgement-suppression attack on the shared-key design, and a ProVerif result: alert-identifier reuse when a car reboots inside the same second, with a boot-counter fix proved in the symbolic model; (C5) a two-stage alert whose provisional decision comes a median {n['tearly']} ms earlier on real pulses, with its airtime cost; (C6) an evaluation of retry policies in two simulators and on measured LoRaWAN traces (an evaluation finding, not a new policy); (C7) deployment requirements from simulated hardware-format logs, a mounting calibration with its limit, and a wake-on-motion estimate. The related work was checked in DOAJ, OpenAlex, Crossref and the publisher pages that could be opened; Google Scholar and Scopus were not searched. No open-access journal article from 2021 onwards was found in those sources on a formally checked crash-alert protocol or on a provisional-then-confirmed crash alert.

**What is negative.** The paper reports its negative results in full (the main table in the paper and a list of all {ledger_ns} in the supplement): the advantage of an adaptive retry table over a severity table is {n['dc']:+.3f} in the custom simulator and {n['dn']:+.3f} in ns-3, and on measured traces a control that retries at once delivers {n['z0']:.1f}% against {n['d1']:.1f}% for the table; the two-stage alert costs {n['air7']:.0f}% extra airtime at SF7 and {n['air9']:.0f}% at SF9 against a 40% design bound; no synthetic-pulse generator passed the realism gate; trigger-aware training, conformal class rules, short frames, overhear-and-suppress retries, slotted fast paths, receiver diversity and a mirror-flip test did not meet their preregistered criteria. The car-reboot identifier lemma was not decided in Tamarin and is reported as such.

**Limits.** No measurement on physical hardware is reported; hardware results are collected separately by the author. The results are statements about code run on public data, simulations, replayed traces, proofs and formulas, each with its label.

**Why IEEE Access.** The paper is a long, evaluation-heavy systems study that spans sensing, embedded detection, wireless protocol design and formal checking, and it gives space to negative results and to the assumptions behind them. These are the kinds of material a broad-scope open-access journal can carry in full.

**Data and code.** All simulation and analysis code, the formal models, the ns-3 patch, the preregistrations, the hypothesis ledger and the derived data will be released (code under Apache-2.0; derived VZCrash data under CC BY-NC 4.0 with attribution; raw third-party data are not redistributed). A Zenodo DOI will be added on release.

Suggested reviewers: (left blank for the author)

Sincerely,
Mritula S (SRIHER)
"""
    # the cover letter has been written by hand since round 6 (new title, round-6 paragraph, delta verification wording); the generator keeps the old text only in this module and does not overwrite the file
    _ = cover

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="360" viewBox="0 0 1000 360" font-family="Arial, Helvetica, sans-serif">
<rect width="1000" height="360" fill="#ffffff"/>
<text x="500" y="34" text-anchor="middle" font-size="20" font-weight="bold">Sense, decide, report: what a low-cost crash-alert node needs</text>
<g font-size="14">
<rect x="30" y="70" width="280" height="200" rx="10" fill="#0072B2"/>
<text x="170" y="100" text-anchor="middle" fill="#fff" font-weight="bold" font-size="17">1  Sense</text>
<text x="170" y="135" text-anchor="middle" fill="#fff">+-{n['front']} g frontal, +-{n['pole']} g pole</text>
<text x="170" y="160" text-anchor="middle" fill="#fff">{n['groups']} duplicate groups in the benchmark</text>
<text x="170" y="185" text-anchor="middle" fill="#fff">recall at 1% target: {n['r1s']:.2f} to {n['r1n']:.2f}</text>
<text x="170" y="255" text-anchor="middle" fill="#fff" font-size="12">MEASURED_SOFTWARE</text>
<rect x="360" y="70" width="280" height="200" rx="10" fill="#E69F00"/>
<text x="500" y="100" text-anchor="middle" font-weight="bold" font-size="17">2  Decide</text>
<text x="500" y="135" text-anchor="middle">compact forest, 16-bit nodes</text>
<text x="500" y="160" text-anchor="middle">provisional decision {n['tearly']} ms earlier</text>
<text x="500" y="185" text-anchor="middle">no severity class in the provisional frame</text>
<text x="500" y="255" text-anchor="middle" font-size="12">MEASURED_SOFTWARE, SIMULATED</text>
<rect x="690" y="70" width="280" height="200" rx="10" fill="#009E73"/>
<text x="830" y="100" text-anchor="middle" fill="#fff" font-weight="bold" font-size="17">3  Report</text>
<text x="830" y="135" text-anchor="middle" fill="#fff">ACK bound to the vehicle (Tamarin)</text>
<text x="830" y="160" text-anchor="middle" fill="#fff">two-stage alert: {n['early']:.1f} s earlier</text>
<text x="830" y="185" text-anchor="middle" fill="#fff">extra airtime {n['air7']:.0f}% (SF7), {n['air9']:.0f}% (SF9)</text>
<text x="830" y="255" text-anchor="middle" fill="#fff" font-size="12">FORMAL, SIMULATED, TRACE_DRIVEN</text>
</g>
<text x="500" y="310" text-anchor="middle" font-size="14">Preregistered; every result labelled; negatives reported. No physical hardware measurement.</text>
</svg>
"""
    (P / "graphical_abstract.svg").write_text(svg, encoding="utf-8")

    rep = """# How to reproduce the paper

Everything in the paper is built from `results/results.json`; nothing is typed by hand except the prose. The steps below were run from a fresh clone in the final verification run and, for the round-6 steps, in the delta verification run (`docs/04_audits/DELTA_VERIFICATION.md`) (times are from that run on a 16-core Windows 11 machine with 16 GB in WSL2).

1. **Clone and environment.** `git clone <repo> crashguard && cd crashguard && git checkout submit-v3`. Python 3.12.10; `python -m venv .venv && .venv/Scripts/pip install --require-hashes -r requirements.lock` (about 3 minutes; the lock includes `cryptography` since the verification run). Set `PYTHONPATH=src`. Versions used: numpy 1.26.4, scipy 1.13.1, scikit-learn 1.5.1, LightGBM 4.4.0. On a machine whose application-control policy blocks the LightGBM DLL in a new virtual environment, use any interpreter with the same pinned versions.
2. **Raw data (not in the repository).** Put the files in `data/raw/`: VZCrash (Hugging Face `vzc-research-chapter/VZCrash`, revision 42e1482d005c0e545379d6cfa4939486c9fe4249, CC BY-NC 4.0, gated), the NHTSA crash-test pulses (`python -m crashguard.nhtsa` downloads them), LoED (Zenodo 4121430), the LoRaWAN sniffer set (Zenodo 7919213), the FARS 2019 to 2022 files, GeoNames `cities15000`, UCI HAR and SisFall. `python scripts/vf_data_check.py` checks the SHA-256 of every file and of the split (about 2 minutes). Sources, licences and hashes: `docs/05_data_code/DATA_SOURCES.md`.
3. **Core pipeline** (about 9 minutes): `python -m crashguard.features && python -m crashguard.split && python -m crashguard.models && python -m crashguard.export_c`. The features and event metadata are byte-identical to the committed run.
4. **All software studies.** `make all` (Windows: `scripts/run_all.ps1`; the clean run of the verification run took several hours, most of it in the T-block studies). The later rounds: `make positive finish release combined round3 paper round4 round5 round5s2 report` (`scripts/vf_make_steps.py` expands the targets one step per line and `scripts/vf_run_steps.py` runs them and logs time and exit code). Steps that query literature services are not part of the numbers.
5. **ns-3** (WSL2 Ubuntu 24.04, g++ 13.3.0, cmake 3.28.3): build ns-3.48 with the lorawan module at commit e45b4af, apply `xsim/ns3/patches/lorawan-v0.3.7-2-ge45b4af-local.patch`, copy `xsim/ns3/*` and `firmware_rd/cg_rd.*` into `scratch/` (`docs/03_results/XSIM_BUILD.md`). `python scripts/vf_ns3_rerun.py` repeats 100 runs and compares every output with the stored one (about 1 minute).
6. **Formal models** (Tamarin 1.12.0, Maude 3.5.1, ProVerif 2.05 in WSL): `wsl bash scripts/vf_formal_rerun.sh <repo root in WSL>`; about 75 minutes, one process per lemma, peak 5.8 GB. `python scripts/vf_formal_summary.py` writes `docs/04_audits/FORMAL_RERUN.md`. Enumerations: `python scripts/vf_enum_rerun.py` (about 40 seconds).
7. **Simulated hardware-format logs.** `python -m crashguard.hwsim_v2 <dir>` regenerates the 19 variants and 30 sensitivity sets (about 1 minute); `python scripts/vf_simhw_check.py <dir>` compares hashes with `docs/03_results/SIMHW_VARIANTS.md`.
8. **Paper.** `make paper` (or `python -m crashguard.pp_paper numbers`, `python -m crashguard.pp_paper figures`, `python -m crashguard.vf_figs`, `python -m crashguard.pp_supp`, `python scripts/pp_make_bib.py`, `python scripts/vf_ledger.py`, `python scripts/vf_negatives.py`). Every table is in `paper/main.tex` (macros of `paper/generated/numbers.tex`) and every figure is made from `results.json` by `pp_paper.py` or `vf_figs.py`.
9. **Compile.** Upload `paper/` to Overleaf (class `ieeeaccess.cls` of the IEEE Access template, version 2026-05-13). A local check with Tectonic: `python scripts/vf_shim_compile.py <work dir> <tectonic.exe>` (about 2 minutes; the Access class itself needs pdfTeX).
10. **Checks.** `python -m pytest -q` (about 8 minutes), `ruff check src scripts tests`, `python -m crashguard.check_results`, `python scripts/doc_style_check.py`, `python scripts/check_links.py`, `python scripts/pp_paper_audit.py`, `python scripts/r5_audit.py` (it accepts a Windows checkout whose line endings differ from the frozen hashes).
11. **Round 6 and the delta verification.** In a fresh clone with `data/processed` and the raw ns-3 run files in place: `python scripts/vf2_recompute_r6.py` (260 stored values recomputed), `python scripts/vf2_ns3_rerun.py 15` (180 ns-3 runs, byte comparison; WSL), `wsl bash scripts/r6_footprint.sh` then `python -m crashguard.r6_footprint` and `python scripts/vf2_compare_prefix.py r6.fp.`, `wsl bash scripts/r6_formal.sh <repo root in WSL>` then `python scripts/vf2_formal_doc.py <clone>`; `python scripts/vf2_record.py <clone> 29 29 277 277` writes `docs/04_audits/RECOMPUTE_R6.md`. The analyses of the run: `python -m crashguard.vf2_preempt`, `python scripts/vf2_duty.py`, `python -m crashguard.vf2_split_sens`, `python -m crashguard.vf2_split_doc`, `python -m crashguard.frame_layout_doc`, `python scripts/vf2_cover.py`.
12. **Supplement.** `python -m crashguard.pp_supp` writes the reduced `paper/supplement.tex` (about 35 pages) and `paper/supplement_full.tex`; the release archive carries the full supplement and the other documents under `supplementary_full/` (`python scripts/vf2_build_release.py`).
13. **Test suite in two parts.** The whole suite can stall on some machines when it runs in one process (a multiprocessing test stopped three times at the same early point in the finalize run, and the same tests pass alone). Run it in two parts from the repository root with `PYTHONPATH=src`: `python -m pytest -q -p no:cacheprovider tests/redesign` (73 tests, about 1 minute) and `python -m pytest -q -p no:cacheprovider tests --ignore=tests/redesign` (about 3.5 minutes; two tests are skipped when the host C compiler is blocked or data is absent). Both together passed 684 tests with 2 skipped.
"""
    (P / "REPRODUCE.md").write_text(_keep_header(P / "REPRODUCE.md", rep), encoding="utf-8")
    print("submission package written")


if __name__ == "__main__":
    main()
