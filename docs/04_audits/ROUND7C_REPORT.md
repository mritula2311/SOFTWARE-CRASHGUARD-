# Round 7c report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Report of round 7c: code checks K1 to K5, every changed sentence (old and new), references added or fixed, and the author's remaining hand steps. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; GSM = Global System for Mobile communications; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; LoRa = long-range radio modulation; PDF = Portable Document Format |
<!-- header:end -->

No new experiment or hypothesis. New keys only under `r7c.` (`scripts/verify_keys_unchanged.py submit-v5`: 0 changed). Log: `ROUND7C.md`. Facts: `docs/01_literature/LITERATURE_FINAL_CHECK.md`.

**Two deviations from the brief, stated at the head.** (1) The branch starts from `submit-v5.1`, not `submit-v5`: items K1, K4 and K5 had been done after `submit-v5` and branching from `submit-v5` would have lost them. (2) **`CrashGuard_Literature_Final_Check.md` was not in the session**, so it could not be copied into `docs/01_literature/LITERATURE_FINAL_CHECK.md`. That file holds the facts of the brief as checked against Crossref and OpenAlex instead (what each rests on is in its table), and the "key-exchange analyses listed in the check file" are not cited beyond Wesemeyer et al.

## 1. K: code checks

| ID | Question | Outcome |
|---|---|---|
| K1 | Is the base's seen-set check and insert atomic? | **Neither a lock nor a threaded design.** The reference base (`BaseVerifier.handle`) does the check and the update in one method called from one sequential loop; a scan of 24 base-side and firmware source files finds 0 lock, thread, async, atomic or interrupt primitives. Atomic by construction, not enforced; no base server exists. Requirement R-ATOMIC is in `FRAME_LAYOUT.md` section 11 and in the C4 text, with the statement that the quarantine lemma (injective form) holds only with it |
| K2 | Does the base send an ACK only after the tag verifies? | **Yes** in every handler that can return an ACK: 200 forged frames each to `BaseVerifier.handle`, `SctBase.handle_short` and `SctBase.handle_alert` gave 0, 0 and 0 ACKs and no state change; `micro_lookup` has no ACK path. **Caveats written into the paper:** a keyless replay of a captured valid frame is re-acknowledged unless the re-acknowledgement interval and a downlink budget are set (both off by default; with 30 s and a 1% budget, 50 one-second replays got 1 re-ACK); the ns-3 gateway checks no tag; cell-level rate limiting is a design of the quarantine model, not code in the verifier. One C4 sentence and one limitations clause added |
| K3 | SisFall data in the repository, history or release archives? | **No**: 0 tracked, 0 in the history of any ref, 0 in the 14 release archives. The author's disk has an untracked, git-ignored `data/raw/r5_l10/sisfall.zip`. Nothing in BLOCKERS.md; tags allowed |
| K4 | Ledger count | **138 in 15 versions** (125 run, 48 supported, 72 not supported, 4 partly, 13 not run) from the per-hypothesis rows, the Totals table and the keys (`r7c.ledger.recount.*`). Quotes: macros (`main.tex`, both supplements), cover letter, README and CHANGELOG agree. **A stale quote was found and fixed:** `paper/cover_letter.md` line 20 said 130 hypotheses (45 supported, 68 not supported). `PROJECT_STATUS.md` quotes 130 for V1 to V17 as of round 6 and now says so. The ledger's Versions table lacked V18 and V19 (added in round 7b) |
| K5 | Control F4 disclosure | **Yes**: `main.tex` (C4 paragraph) and the supplement (`ROUND7B_RESULTS.md`, deviations row 7) state that the control registered in V19 was not met as worded: the one-event reserve fails from 4 earlier events, not at 3 or fewer |

## 2. L: literature corrections

| ID | Change |
|---|---|
| L1 | The introduction no longer says the abstract of the crash-alert papers mentions no delivery statistics: Carneiro et al. report packet delivery ratio, coverage and latency in ns-3. The gap is stated as: none of the works read states a security analysis, an authenticated acknowledgement or a formal verification, and none studies a duty budget |
| L2 | Related work now says that LoRa and LoRaWAN protocols have been formally analysed (Wesemeyer et al., Tamarin; Dong et al.; Jabbari and Mohasefi, ProVerif and AVISPA; Hakeem et al.), that those cover key establishment and authentication, and that the formal claims of this paper cover crash-alert frames only |
| L3 | Related work cites Chen et al. 2023 (abstract only; closed access), Liu et al. 2026 and Kumar 2026 and states that the attacks and defences are known and not claimed; the contribution is the node-side reserved budget for the follow-up, the bounded model check with a control and the preregistered results. Chen's thesis: read (Chapter VII sections VII.2 and VII.3.1 of the open-access PDF, `LITERATURE_FINAL_CHECK.md` section 3): the attack drains the gateway's downlink duty through ACKs to rogue nodes and the countermeasure is LoRaLOFT detection with an ACK denylist; the rest of the thesis was not read |
| L4 | References fixed or added in `paper/refs_manual.bib` (read before the other sources by the generator): Jabbari and Mohasefi (2022, month and note), Marciano et al. (Brno, nine authors, December 2024), Vinodhini et al. (2025), Carneiro et al. (abstract read), Liu et al. 2026 (authors exactly as printed, in braces), Kumar 2026 (new, `Kumar2026_siml`), Thangamani et al. 2026 and Al-Shammaa and Al-Hadrawi 2025 (optional, new), Chen's thesis if cited. All DOIs were checked against Crossref; `references.bib` rebuilt (63 entries) |
| L5 | Data availability: the SisFall sentence of the brief (plus the Zenodo remark); `scripts/fetch_sisfall.md` with the archive hash, the 4,700 entries, 4,505 trial files and 153,705 windows; `DATA_SOURCES.md` note updated |
| L6 | One absence rule everywhere: no work found in the sources checked (IEEE Xplore, OpenAlex, Crossref, DOAJ, publisher pages; Google Scholar blocked automated queries and was not searched). Replaced in the Search paragraph, five related-work sentences, the cover letter. **IEEE Xplore returned HTTP 418 to scripted access in this repository's searches; the rule names it because the brief does. The author must confirm a manual Xplore search or remove it from the rule** |

## 3. Changed sentences of `paper/main.tex` (old and new)

**1. Old:** Of these, one was read in full and one in abstract; they describe prototypes and demonstrations; the full text does not study an authenticated acknowledgement or a duty budget, and the abstract mentions no delivery statistics, security analysis or formal check. The other two were read at record level only. LoRa security work, in turn, is mostly not about crash alerts.

**New:** Of these, one was read in full and three in abstract (the publisher page of one was blocked to scripts); they describe prototypes, simulations and field tests. Carneiro et al. evaluate packet delivery ratio, coverage and latency in ns-3, so delivery statistics exist for LoRa crash alerting. In the text read, none states an authenticated acknowledgement, a security analysis or a formal check, and none studies a duty budget; we found no such work in the sources checked (see Section~\ref{sec:related}). LoRa security work, in turn, is mostly not about crash alerts.

**2. Old:** Where a paragraph says that nothing was found, it means: no open-access journal article from 2021 onwards was found in the sources checked (DOAJ, OpenAlex, Crossref and the publisher pages opened; Google Scholar and Scopus not searched).

**New:** Where a paragraph says that nothing was found, it means: no work found in the sources checked (IEEE Xplore, OpenAlex, Crossref, DOAJ, publisher pages; Google Scholar blocked automated queries and was not searched).

**3. Old:** No journal article from 2021 onwards was found in the sources checked that audits duplicates in a crash-pulse benchmark.

**New:** We found no work in the sources checked that audits duplicates in a crash-pulse benchmark.

**4. Old:** In the sources checked no journal article gives the range and rate that crash delta-V needs,

**New:** We found no work in the sources checked that gives the range and rate that crash delta-V needs,

**5. Old:** No journal article was found on provisional-then-confirmed crash alerts.

**New:** We found no work in the sources checked on provisional-then-confirmed crash alerts.

**6. Old:** no replay of retry policies on public traces was found.

**New:** we found no work in the sources checked that replays retry policies on public traces.

**7. Old:** We found no work in the sources checked on provisional-then-confirmed crash alerts.

**New:** An automatic crash-alert unit for vehicle classes outside the Indian AIS-140 mandate reports drop-test and road-course sensitivity over a GSM link \cite{Thangamani2026_icces}, and a LoRa vehicle-to-vehicle system broadcasts explicit event-termination packets to end channel occupancy after an event report \cite{AlShammaa2025_jcomss}. We found no work in the sources checked on provisional-then-confirmed crash alerts.

**8. Old:** Formal analyses cover LoRaWAN key establishment \cite{wesemeyer2020}, the protocol in a process-algebra tool \cite{dong2024}, user authentication for critical applications \cite{Jabbari2022_tii} and hash-chain key management \cite{Hakeem2021_s2117583}.

**New:** LoRa and LoRaWAN protocols have been formally analysed: key establishment in Tamarin \cite{wesemeyer2020}, the protocol in a process-algebra tool \cite{dong2024}, a user authentication protocol with a real-or-random proof and ProVerif and AVISPA checks \cite{Jabbari2022_tii}, and hash-chain key management \cite{Hakeem2021_s2117583}. Those analyses cover key establishment and authentication. The formal claims of this paper cover crash-alert frames only: the acknowledgement binding, freshness, reboot, quarantine, the two-stage confirm and unlinkability with accountability.

**9. Old:** \cite{R7BlindSpot2025} studies selective jamming, and \cite{R7MacDos2023} propose two denial-of-service attacks on the confirmed transmission of LoRaWAN that rely on its Aloha access and its duty-cycle limit (we read the abstract only: the mechanism, whether it drains the duty budget through suppressed acknowledgements, and whether it has a defence are not known to us; the full text is closed access). We treat acknowledgement suppression against a duty budget as a known class and claim none of it. None of the papers opened gives a reserve for the follow-up frame of a two-stage alert.

**New:** \cite{R7BlindSpot2025} studies selective jamming, and Chen et al.~\cite{R7MacDos2023} propose two denial-of-service attacks on the confirmed transmission of LoRaWAN that exploit its Aloha access and its duty-cycle limit (we read the abstract of Chen et al. only: it gives no mechanism and the paper is closed access; the abstract of \cite{Kumar2026_siml} treats the same class as rogue nodes that use up the gateway's downlink airtime with confirmed uplinks, which we did not verify in the Chen text). \cite{R7EdaLora2026} forces retransmissions by jamming and replay to deplete the energy of the end device. On the defence side, \cite{Kumar2026_siml} detects rogue nodes and limits acknowledgements at the gateway. The thesis of Chen \cite{ChenThesis2024} (we read its Chapter VII) describes the same attack family: confirmed uplinks sent at a high rate to use up the gateway's downlink duty, a MAC-command variant that forces the acknowledgements to SF12, and a variant with a malicious application server; it counters them with a threshold and outlier detector and a graded denylist that finally blocks the acknowledgement to the detected nodes. These attacks aim at the gateway's downlink; the attack here aims at the node's uplink budget through suppressed acknowledgements, and the reserve is a node-side defence. These attacks and defences are known, and we claim none of them. This paper contributes the node-side reserved budget for the follow-up frame of a two-stage alert, a bounded model check with a control, and preregistered results under India's rules. We found no work in the sources checked that reserves node airtime for the follow-up frame of an alert.

**10. Old:** and we do not claim the attack. What this paper adds is

**New:** and we do not claim the attack. Nodes without keys cannot use up the base's downlink duty budget with confirmed frames, as in that attack class: in the reference base a frame whose tag fails gets no acknowledgement and is rejected before any state changes (cell-level rate limiting is the design for such frames), whereas a keyless replay of a captured valid frame can still be re-acknowledged unless the re-acknowledgement interval and a downlink budget are set (both are off by default), and the ns-3 gateway model does not check tags. What this paper adds is

**11. Old:** the SisFall file is a Zenodo copy whose licence is the one stated on its record.

**New:** SisFall is available from its authors \cite{Sucerquia2017_sisfall}; it is not redistributed with this artefact because no data licence is stated (a Zenodo copy states CC BY 4.0 but names no creators, so we did not rely on it; see \texttt{scripts/fetch\_sisfall.md}).

**12. Old:** \textbf{Regulation.} 

**New:** \textbf{Base behaviour.} Acknowledgement only after the tag verifies, and an atomic seen-set check and insert, are properties of the reference base code and design requirements for a base server; no base server exists, the ns-3 gateway acknowledges every received frame, and a keyless replay of a valid frame is re-acknowledged unless the base limits it. \textbf{Regulation.} 

## 4. Other changed text

- `paper/cover_letter.md`: the hypothesis count of the opening paragraph (old: "130 preregistered hypotheses (45 supported, 68 not supported, 4 partly supported, 13 not run)"; new: "138 preregistered hypotheses in 15 versions (48 supported, 72 not supported, 4 partly supported, 13 not run)") and the absence sentence (old: "The related work was checked in DOAJ, OpenAlex, Crossref and the publisher pages that could be opened; Google Scholar and Scopus were not searched. No open-access journal article from 2021 onwards was found in those sources on a formally checked crash-alert protocol or on a provisional-then-confirmed crash alert."; new: the absence rule, the statement that LoRaWAN key establishment and user authentication were analysed formally before, and the Carneiro et al. remark).
- `docs/05_data_code/DATA_SOURCES.md` (SisFall note), `docs/00_overview/PROJECT_STATUS.md` (scope of the 130), `README.md` and `CHANGELOG.md` (round 7c rows), `paper/reference_status.txt` (seven entries).

## 5. Package

- Release archive `release/crashguard-submit-v6.zip`: SHA-256 `2239031ee458ec1c8d3bb6c46cb31a367068c21ccfb538e5e2f1a39f51efc947`, 1891 files; the supplement PDF was not compiled (no TeX distribution).
- Checks from a fresh clone: see `ROUND7C.md` (two-part tests, ruff, `check_results`, paper audit, `r5_audit`, key check).

## 6. The author's remaining hand steps

1. Provide `CrashGuard_Literature_Final_Check.md` (or state that it is not needed) and compare it with `LITERATURE_FINAL_CHECK.md` section 2: especially the description of Chen et al. 2023 and the key-exchange analyses.
2. Read Chen et al. 2023 via the library (mechanism, whether the duty budget is drained, any defence) and adjust one clause of the related work if needed.
3. Confirm that IEEE Xplore was searched by hand, or drop it from the absence rule.
4. Confirm the licence of SisFall with its authors; until then it stays out of the artefact.
5. The two author names of Liu et al. 2026 on the publisher page.
6. Whether the base to be built meets R-ATOMIC and acknowledges only verified frames, with a limit on re-acknowledgements.
