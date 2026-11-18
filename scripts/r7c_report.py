"""Round 7c: write docs/04_audits/ROUND7C_REPORT.md. The changed sentences of paper/main.tex are read from scripts/r7c_changes.json (old and new, written by scripts/r7c_patch_paper.py); the other changes are listed here.

    python scripts/r7c_report.py <sha256 of the release archive> <file count>     (pass NOT_BUILT NOT_BUILT before the archive exists)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) < 3:  # refuse without arguments
    raise SystemExit("usage: r7c_report.py <sha256 of the release archive> <file count>; refusing to run without them, because the report would lose the recorded hash")
sha, nfiles = sys.argv[1:3]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}
changes = json.loads((ROOT / "scripts/r7c_changes.json").read_text(encoding="utf-8"))
thesis = (ROOT / "scripts/r7c_thesis_status.txt").read_text(encoding="utf-8").strip() if (ROOT / "scripts/r7c_thesis_status.txt").exists() else "not read"
HEAD = """# Round 7c report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Round 7c (branch round7c from tag submit-v5.1): code checks K1 to K5, literature corrections L1 to L6 with every changed sentence (old and new), references added or fixed, and the author's remaining hand steps. |
| Evidence labels used | ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; DoS = denial of service; PDR = packet delivery ratio |
<!-- header:end -->

No new experiment or hypothesis. New keys only under `r7c.` (`scripts/verify_keys_unchanged.py submit-v5`: 0 changed). Log: `ROUND7C.md`. Facts: `docs/01_literature/LITERATURE_FINAL_CHECK.md`.

**Two deviations from the brief, stated at the head.** (1) The branch starts from `submit-v5.1`, not `submit-v5`: items K1, K4 and K5 had been done after `submit-v5` and branching from `submit-v5` would have lost them. (2) **`CrashGuard_Literature_Final_Check.md` was not in the session**, so it could not be copied into `docs/01_literature/LITERATURE_FINAL_CHECK.md`. That file holds the facts of the brief as checked against Crossref and OpenAlex instead (what each rests on is in its table), and the "key-exchange analyses listed in the check file" are not cited beyond Wesemeyer et al.

"""
K = f"""## 1. K: code checks

| ID | Question | Outcome |
|---|---|---|
| K1 | Is the base's seen-set check and insert atomic? | **Neither a lock nor a threaded design.** The reference base (`BaseVerifier.handle`) does the check and the update in one method called from one sequential loop; a scan of {int(R['r7c.atomic.files_scanned'])} base-side and firmware source files finds {int(R['r7c.atomic.concurrency_primitive_hits'])} lock, thread, async, atomic or interrupt primitives. Atomic by construction, not enforced; no base server exists. Requirement R-ATOMIC is in `FRAME_LAYOUT.md` section 11 and in the C4 text, with the statement that the quarantine lemma (injective form) holds only with it |
| K2 | Does the base send an ACK only after the tag verifies? | **Yes** in every handler that can return an ACK: 200 forged frames each to `BaseVerifier.handle`, `SctBase.handle_short` and `SctBase.handle_alert` gave {int(R['r7c.k2.verifier.acks_for_forged'])}, {int(R['r7c.k2.sct_short.acks_for_forged'])} and {int(R['r7c.k2.sct_alert.acks_for_forged'])} ACKs and no state change; `micro_lookup` has no ACK path. **Caveats written into the paper:** a keyless replay of a captured valid frame is re-acknowledged unless the re-acknowledgement interval and a downlink budget are set (both off by default; with 30 s and a 1% budget, 50 one-second replays got {int(R['r7c.k2.verifier.reacks_with_limit_on_50_replays'])} re-ACK); the ns-3 gateway checks no tag; cell-level rate limiting is a design of the quarantine model, not code in the verifier. One C4 sentence and one limitations clause added |
| K3 | SisFall data in the repository, history or release archives? | **No**: {int(R['r7c.k3.tracked_sisfall_data_files'])} tracked, {int(R['r7c.k3.history_sisfall_data_files'])} in the history of any ref, {int(R['r7c.k3.release_zip_sisfall_data_files'])} in the 14 release archives. The author's disk has an untracked, git-ignored `data/raw/r5_l10/sisfall.zip`. Nothing in BLOCKERS.md; tags allowed |
| K4 | Ledger count | **138 in 15 versions** (125 run, 48 supported, 72 not supported, 4 partly, 13 not run) from the per-hypothesis rows, the Totals table and the keys (`r7c.ledger.recount.*`). Quotes: macros (`main.tex`, both supplements), cover letter, README and CHANGELOG agree. **A stale quote was found and fixed:** `paper/cover_letter.md` line 20 said 130 hypotheses (45 supported, 68 not supported). `PROJECT_STATUS.md` quotes 130 for V1 to V17 as of round 6 and now says so. The ledger's Versions table lacked V18 and V19 (added in round 7b) |
| K5 | Control F4 disclosure | **Yes**: `main.tex` (C4 paragraph) and the supplement (`ROUND7B_RESULTS.md`, deviations row 7) state that the control registered in V19 was not met as worded: the one-event reserve fails from 4 earlier events, not at 3 or fewer |

"""
L = ["## 2. L: literature corrections", "",
     "| ID | Change |", "|---|---|",
     "| L1 | The introduction no longer says the abstract of the crash-alert papers mentions no delivery statistics: Carneiro et al. report packet delivery ratio, coverage and latency in ns-3. The gap is stated as: none of the works read states a security analysis, an authenticated acknowledgement or a formal verification, and none studies a duty budget |",
     "| L2 | Related work now says that LoRa and LoRaWAN protocols have been formally analysed (Wesemeyer et al., Tamarin; Dong et al.; Jabbari and Mohasefi, ProVerif and AVISPA; Hakeem et al.), that those cover key establishment and authentication, and that the formal claims of this paper cover crash-alert frames only |",
     f"| L3 | Related work cites Chen et al. 2023 (abstract only; closed access), Liu et al. 2026 and Kumar 2026 and states that the attacks and defences are known and not claimed; the contribution is the node-side reserved budget for the follow-up, the bounded model check with a control and the preregistered results. Chen's thesis: {thesis} |",
     "| L4 | References fixed or added in `paper/refs_manual.bib` (read before the other sources by the generator): Jabbari and Mohasefi (2022, month and note), Marciano et al. (Brno, nine authors, December 2024), Vinodhini et al. (2025), Carneiro et al. (abstract read), Liu et al. 2026 (authors exactly as printed, in braces), Kumar 2026 (new, `Kumar2026_siml`), Thangamani et al. 2026 and Al-Shammaa and Al-Hadrawi 2025 (optional, new), Chen's thesis if cited. All DOIs were checked against Crossref; `references.bib` rebuilt (63 entries) |",
     "| L5 | Data availability: the SisFall sentence of the brief (plus the Zenodo remark); `scripts/fetch_sisfall.md` with the archive hash, the 4,700 entries, 4,505 trial files and 153,705 windows; `DATA_SOURCES.md` note updated |",
     "| L6 | One absence rule everywhere: no work found in the sources checked (IEEE Xplore, OpenAlex, Crossref, DOAJ, publisher pages; Google Scholar blocked automated queries and was not searched). Replaced in the Search paragraph, five related-work sentences, the cover letter. **IEEE Xplore returned HTTP 418 to scripted access in this repository's searches; the rule names it because the brief does. The author must confirm a manual Xplore search or remove it from the rule** |",
     "", "## 3. Changed sentences of `paper/main.tex` (old and new)", ""]
for i, (old, new) in enumerate(changes, 1):
    L += [f"**{i}. Old:** {old}", "", f"**New:** {new}", ""]
L += ["## 4. Other changed text", "",
      "- `paper/cover_letter.md`: the hypothesis count of the opening paragraph (old: \"130 preregistered hypotheses (45 supported, 68 not supported, 4 partly supported, 13 not run)\"; new: \"138 preregistered hypotheses in 15 versions (48 supported, 72 not supported, 4 partly supported, 13 not run)\") and the absence sentence (old: \"The related work was checked in DOAJ, OpenAlex, Crossref and the publisher pages that could be opened; Google Scholar and Scopus were not searched. No open-access journal article from 2021 onwards was found in those sources on a formally checked crash-alert protocol or on a provisional-then-confirmed crash alert.\"; new: the absence rule, the statement that LoRaWAN key establishment and user authentication were analysed formally before, and the Carneiro et al. remark).",
      "- `docs/05_data_code/DATA_SOURCES.md` (SisFall note), `docs/00_overview/PROJECT_STATUS.md` (scope of the 130), `README.md` and `CHANGELOG.md` (round 7c rows), `paper/reference_status.txt` (seven entries).", "",
      "## 5. Package", "",
      f"- Release archive `release/crashguard-submit-v6.zip`: SHA-256 `{sha}`, {nfiles} files; the supplement PDF was not compiled (no TeX distribution).",
      "- Checks from a fresh clone: see `ROUND7C.md` (two-part tests, ruff, `check_results`, paper audit, `r5_audit`, key check).", "",
      "## 6. The author's remaining hand steps", "",
      "1. Provide `CrashGuard_Literature_Final_Check.md` (or state that it is not needed) and compare it with `LITERATURE_FINAL_CHECK.md` section 2: especially the description of Chen et al. 2023 and the key-exchange analyses.",
      "2. Read Chen et al. 2023 via the library (mechanism, whether the duty budget is drained, any defence) and adjust one clause of the related work if needed.",
      "3. Confirm that IEEE Xplore was searched by hand, or drop it from the absence rule.",
      "4. Confirm the licence of SisFall with its authors; until then it stays out of the artefact.",
      "5. The two author names of Liu et al. 2026 on the publisher page.",
      "6. Whether the base to be built meets R-ATOMIC and acknowledges only verified frames, with a limit on re-acknowledgements.", ""]
(ROOT / "docs/04_audits/ROUND7C_REPORT.md").write_text(HEAD + K + "\n".join(L), encoding="utf-8")
print("report written", len(changes), "changed sentences")
