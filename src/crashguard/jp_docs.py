"""Journal-push documents generated from results.json (no number is typed here): docs/03_results/JOURNAL_RESULTS.md, docs/00_overview/CLAIMS_FOR_COVER_LETTER.md, docs/05_data_code/REPRODUCE_FINISH.md and the journal-push block of docs/00_overview/LIMITATIONS.md.
docs/05_data_code/DATA_AND_CODE_STATEMENT.md is written by hand (it states licences and what is redistributed) and is not touched here."""
from __future__ import annotations

import json
from pathlib import Path

from crashguard.docs_gen import replace_block
from crashguard.jp_claims import CLAIM, HX
from crashguard.report import Res

ALL = json.loads(Path("results/results.json").read_text(encoding="utf-8"))
R = {e["name"]: e["value"] for e in ALL}


def f(k: str, d: int = 3) -> str:
    return f"{R[k]:.{d}f}"


def ci(k: str, d: int = 3) -> str:
    return f"{f(k, d)} [{f(k + '_lo', d)}, {f(k + '_hi', d)}]"


def n(k: str) -> str:
    return f"{int(R[k]):,}"


def not_run_lines() -> list[str]:
    out = []
    for e in ALL:
        if e["origin"] == "NOT_RUN" or e["value"] == "NOT_RUN":
            if e["name"].startswith(("v2.a.a5", "t13.heldout.r64.ridge_alpha")) and "value not finite" in e["notes"]:
                continue
            out.append(f"- `{e['name']}`: {e['notes'][:260]}")
    return out


def results_doc() -> str:
    L = ["# Journal push: results summary (generated from `results/results.json`)", "",
         "Branch `journal-push`, software only (`data/hardware` is not read). Origin labels: MEASURED_SOFTWARE unless stated. Preregistration: `docs/02_preregistration/PREREGISTRATION_V3.md`; decisions and mistakes: `docs/07_log/DECISIONS.md`; claims with allowed wording: `docs/03_results/CLAIM_EVIDENCE.md`.", "",
         "## One line per task", "",
         f"- **T13a (held-out NHTSA modes).** {n('t13.heldout.count.n_used')} records from {n('t13.heldout.count.n_candidates')} candidate tests in {n('t13.heldout.count.n_groups_mm')} make-and-model groups. The 80% criterion is reached in **{n('t13.heldout.grid.criterion.cells_meeting_lower_bound')}** cells (best lower end {f('t13.heldout.grid.r200.f200.w10_lo')} at +-200 g and 200 Hz; {f('t13.heldout.grid.r64.f200.w10_lo')} at +-64 g and 200 Hz). Fill + ridge does not beat the spline at +-16 g ({ci('t13.heldout.all.r16.paired.M+_vs_SP.d_median', 2)} points); it does at +-32 g.",
         f"- **T13c (NHTSA near-duplicates).** {n('t13.neardup.pairs.within_176.all')} pairs among the 176 (the same test channel counted twice), {n('t13.neardup.pairs.heldout_vs_176')} between the held-out records and the 176. The +-16 g result of N14 is unchanged without the flagged tests (exploratory).",
         f"- **Block 2 (sensor selection).** {n('sel.s3.n_meeting')} of {n('sel.s3.n_configs')} configurations meet the rule on the 176 tests; the smallest range is +-{f('sel.s3.smallest_range_g', 0)} g; no +-16 g part meets it; no configuration meets it on the held-out modes. Tables: `results/paper/tab_sel_*`, figure `sel_share_vs_range`.",
         f"- **V1 (independent audit).** Every stored count is reproduced ({n('vz.v1.exact.acc.groups_across_splits')} groups, {n('vz.v1.near.test_windows_both.vs_stored')} flagged windows); **V2** the 'a fifth' ({100 * R['vz.v1.near.share_of_triggered_test_windows']:.1f}% of triggered test windows) and 'about 5%' figures use different denominators; **V3** `docs/04_audits/VZCRASH_AUDIT.md`; **V4** near-duplicate removal lowers recall at the 1% target by {ci('vz.v4.rf15.diff_supplied_minus_near.recall_at_1pct', 4)}.",
         ""]
    L += ["## One line per hypothesis (Holm over the seven)", "", "| Hypothesis | Verdict | Raw p | Holm p | Statement |", "|---|---|---|---|---|"]
    for h in HX:
        L.append(f"| {h} | **{R[f'x.holm.{h}.verdict']}** | {f(f'x.holm.{h}.p_raw')} | {f(f'x.holm.{h}.p_holm')} | {CLAIM[h]} |")
    L += ["", "X4 (labels): the supplied files carry only crash, near_miss and normal_driving and the vehicle size; no direction or severity label (`x.x4.*`).", "",
          "## Negative results (reported in full)", "",
          f"- N13 is not confirmed on other crash modes (T13a); fill + ridge does not beat the spline at +-16 g there; the ridge fitted on the 176 does not carry over ({f('t13.heldout.all.r16.M.median', 1)}% median for fill without the ridge against {f('t13.heldout.all.r16.M+.median', 1)}% with it).",
          f"- X5: the order of severity is not preserved at +-16 g (Spearman {ci('x.x5.hX5.rho_fillridge')}; the plain estimate ranks better, {ci('x.x5.hX5.rho_plain')}); N13 is strengthened.",
          f"- X1: the 16-bit forest keeps AP but the flash estimate falls only {100 * R['x.x1.hX1.flash_reduction_primary']:.1f}% in the existing layout.",
          "- X2: the cascade is the 2 g threshold itself in most held-out categories; no gain.",
          f"- X3: group-aware training changes the 1% recall on the strict set by {ci('x.x3.hX3.gain', 4)}; duplicates in training do not explain the gap.",
          f"- X7: no preregistered pair and fusion rule reaches a lower end of 0.80; a wide-mask rule defined afterwards does for {n('x.x7.hX7.n_counting_exploratory_wide')} combinations (exploratory).",
          "- X8: earlier at the 1% target, slower and lower recall at 5%; the recall gain over the single forest is an ensemble effect.", "",
          "## The one supported hypothesis", "",
          f"H-X6: at +-16 g on split R the lower-bound-anchored estimator has a 90th-percentile error of {f('x.x6.R.r16.ANC.p90', 1)}% against {f('x.x6.R.r16.M+.p90', 1)}% for fill + ridge (gain {ci('x.x6.hX6.p90_gain_R', 1)} points, raw p {f('x.x6.hX6.p_raw')}, Holm {f('x.holm.H-X6.p_holm')}). Cautions: the gain has its interval above zero on split A only among G, A, O; the median is not better than the tail-aware model; the unanchored boosting model accounts for part of the gain (`x.x6.R.r16.paired.GBR_minus_ANC.p90`); the estimator over-corrects the {n('x.x6.lowerbound.r16.n_violations')} tests where the plain estimate already exceeds the reference.", "",
          "## NOT_RUN items and why", ""] + not_run_lines() + ["",
          "## Limitations (paragraph for the paper)", "",
          "All delta-V and sensor results use NHTSA crash tests, most of which are high-speed barrier tests, through a software sensor model whose bandwidth, range, rate, resolution and noise come from data sheets or assumptions; the output rates are data sheet rates, not rates read over I2C or SPI on an ESP32 (NOT_RUN, hardware). The reference delta-V is the integral of the unclipped original-rate channel, not a measured vehicle velocity change. "
          "The held-out test modes are dominated by pole tests, and the methods fitted on the original 176 tests do not carry over to them. Two of the 176 records are the same channel counted twice. VZCrash events were selected on the device before release, its recordings contain exact and window-level duplicates across the supplied splits (audited here), and it has no vehicle identifier, so vehicle-level separation cannot be checked; its licence is CC BY-NC 4.0 (confirmed by the dataset authors on 2026-11-12, Hugging Face revision 42e1482d005c0e545379d6cfa4939486c9fe4249). "
          "Hardware results are not included. The 1% duty limit and every simulator parameter of the delivery studies are assumptions.", "",
          "## Index of generated tables and figures", "",
          "Tables (CSV and LaTeX in `results/paper/`): `jp_tab_t13_heldout`, `jp_tab_t13_paired`, `jp_tab_t13_grid`, `jp_tab_t13_neardup`, `tab_sel_parts`, `tab_sel_sources`, `tab_sel_study`, `tab_sel_study_all`, `jp_tab_vz_leakage`, `jp_tab_x1`, `jp_tab_x3`, `jp_tab_x5_rank`, `jp_tab_x6_anchored`, `jp_tab_x7`, `jp_tab_x8`, `jp_tab_x_verdicts`, `vz_audit_cross_split_groups.csv`. "
          "Figures (PNG at 300 dpi and PDF, 3.5 inch wide): `sel_share_vs_range`, `jp_fig_x5_rank`, `jp_fig_x6_p90`, `jp_fig_t13_range`. Commands: `docs/05_data_code/REPRODUCE_FINISH.md`."]
    return "\n".join(L) + "\n"


def claims_doc() -> str:
    r = Res()
    from crashguard.jp_claims import jp_rows

    L = ["# Claims for the cover letter (generated)", "", "Each claim with its evidence label and the section of `docs/03_results/JOURNAL_RESULTS.md` and the results keys that support it. Wording that may be used is in `docs/03_results/CLAIM_EVIDENCE.md` (allowed wording table). Nothing here is a hardware result.", "",
         "| Claim | Evidence label | Section | Keys | Verdict |", "|---|---|---|---|---|"]
    sec = {"T13a": "One line per task: T13a", "T13c": "T13c", "Sensor": "Block 2", "V1": "V1 to V4", "V4": "V1 to V4"}
    for claim, label, src, _cmd, ver in jp_rows(r):
        s = next((v for k, v in sec.items() if claim.startswith(k)), "One line per hypothesis")
        L.append(f"| {claim} | {label} | {s} | `{src}` | **{ver}** |")
    return "\n".join(L) + "\n"


REPRO = [
    ("jp_tab_t13_heldout, jp_tab_t13_paired, jp_tab_t13_grid", "python -m crashguard.t13_harvest && python -m crashguard.t13_heldout && python -m crashguard.jp_paper_tables", "t13.heldout.*"),
    ("jp_tab_t13_neardup", "python -m crashguard.t13_neardup && python -m crashguard.jp_paper_tables", "t13.neardup.*"),
    ("tab_sel_parts, tab_sel_sources, tab_sel_study, tab_sel_study_all, figure sel_share_vs_range, docs/05_data_code/SENSOR_DATASHEETS.md", "python -m crashguard.sel_study && python -m crashguard.sel_tables", "sel.*"),
    ("vz_audit_cross_split_groups.csv, docs/04_audits/VZCRASH_AUDIT.md", "python -m crashguard.vz_audit && python -m crashguard.vz_leakage && python -m crashguard.vz_docs", "vz.v1.*, vz.v4.*"),
    ("jp_tab_vz_leakage", "python -m crashguard.vz_leakage && python -m crashguard.jp_paper_tables", "vz.v4.*"),
    ("jp_tab_x1", "python -m crashguard.x1_fixedpoint && python -m crashguard.jp_paper_tables", "x.x1.*"),
    ("jp_tab_x3", "python -m crashguard.x3_groupaware && python -m crashguard.jp_paper_tables", "x.x3.*"),
    ("jp_tab_x5_rank, figure jp_fig_x5_rank", "python -m crashguard.x_common && python -m crashguard.x5_rank && python -m crashguard.jp_paper_tables", "x.x5.*"),
    ("jp_tab_x6_anchored, figure jp_fig_x6_p90", "python -m crashguard.x_common && python -m crashguard.x6_anchored && python -m crashguard.jp_paper_tables", "x.x6.*"),
    ("jp_tab_x7", "python -m crashguard.x7_fusion && python -m crashguard.jp_paper_tables", "x.x7.*"),
    ("jp_tab_x8", "python -m crashguard.x8_sequential && python -m crashguard.jp_paper_tables", "x.x8.*"),
    ("X2 (no table; keys only)", "python -m crashguard.x2_cascade", "x.x2.*"),
    ("X4 (no table; keys only)", "python -m crashguard.x4_labels", "x.x4.*"),
    ("jp_tab_x_verdicts", "python -m crashguard.x_verdicts && python -m crashguard.jp_paper_tables", "x.holm.*"),
    ("figure jp_fig_t13_range", "python -m crashguard.jp_paper_tables", "t13.heldout.grid.*, sevstudy.grid.*"),
    ("docs/03_results/CLAIM_EVIDENCE.md (journal-push rows), docs/03_results/STATS_AUDIT.md", "python -m crashguard.claim_table && python -m crashguard.stats_audit", "all"),
    ("docs/03_results/JOURNAL_RESULTS.md, docs/00_overview/CLAIMS_FOR_COVER_LETTER.md, this file", "python -m crashguard.jp_docs", "all"),
]


def repro_doc() -> str:
    L = ["# Reproduce the journal-push tables and figures", "", "Run from the repository root with `$env:PYTHONPATH = \"src\"` (PowerShell) or `PYTHONPATH=src`, in the project virtual environment (`.venv`). The earlier pipeline (`docs/05_data_code/REPRODUCE.md`: data, features, models, NHTSA severity steps) must have been run beforehand, because these modules read its outputs (`data/processed/`, `results/results.json`). "
         "The NHTSA harvest needs network access to the public NHTSA API; downloaded files are cached in `data/raw/nhtsa/` (git-ignored). The VZCrash files must be in `data/raw/data/` (gated dataset; never commit them).", "",
         "Order: `t13_harvest`, `t13_heldout`, `t13_neardup`, `sel_study`, `sel_tables`, `vz_audit`, `vz_leakage`, `vz_docs`, `x_common`, `x1_fixedpoint`, `x2_cascade`, `x3_groupaware`, `x4_labels`, `x5_rank`, `x6_anchored`, `x7_fusion`, `x8_sequential`, `x_verdicts`, `jp_paper_tables`, `claim_table`, `stats_audit`, `jp_docs`, `check_results`. `scripts/run_all.ps1` and the Makefile `journal` target run them in this order.", "",
         "| Table or figure | Command | Results keys |", "|---|---|---|"]
    L += [f"| {a} | `{b}` | `{c}` |" for a, b, c in REPRO]
    L += ["", "Checks: `python -m crashguard.check_results` (0 errors), `python -m pytest -q`, `python -m ruff check src tests`.", "",
          "Not reproducible here: anything that needs the author's hardware (`data/hardware/`), the Windows compiled-C checks when Application Control blocks them (recorded as NOT_RUN with the reason), and downloads while the NHTSA API or the data sheet hosts are unreachable."]
    return "\n".join(L) + "\n"


def main() -> None:
    Path("docs/03_results/JOURNAL_RESULTS.md").write_text(results_doc(), encoding="utf-8")
    Path("docs/00_overview/CLAIMS_FOR_COVER_LETTER.md").write_text(claims_doc(), encoding="utf-8")
    Path("docs/05_data_code/REPRODUCE_FINISH.md").write_text(repro_doc(), encoding="utf-8")
    lim = ["", "## Journal push (generated; details in docs/03_results/JOURNAL_RESULTS.md)", "",
           "26. **Held-out NHTSA modes** are dominated by pole tests, and the N13 and N14 findings were not confirmed on them.",
           "27. **Two of the 176 NHTSA records are one channel counted twice.** The tagged results were not re-run.",
           "28. **Sensor selection uses data sheet output rates and a software model.** The read rate on an ESP32 and any mounting or synchronisation effect are NOT_RUN or not modelled.",
           "29. **VZCrash has duplicates across the supplied splits and no vehicle identifier.** Window-level duplicates affect about a fifth of triggered test windows and about 30% of crash test events; the exact-copy test events are under 1% of all test events.",
           "30. **X6 is the only supported Block 4 hypothesis** and its gain is partly due to the anchoring and the boosting model; it holds on two of four splits and is not better in the median than the tail-aware model."]
    replace_block(Path("docs/00_overview/LIMITATIONS.md"), "<!-- jp_limits:start -->", "<!-- jp_limits:end -->", "\n".join(lim))
    print("wrote docs/03_results/JOURNAL_RESULTS.md, docs/00_overview/CLAIMS_FOR_COVER_LETTER.md, docs/05_data_code/REPRODUCE_FINISH.md and the limitations block")


if __name__ == "__main__":
    main()
