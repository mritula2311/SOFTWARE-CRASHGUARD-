# Placeholders and items the author must supply

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Every placeholder in the paper and every decision, reading or check that only the author can supply. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | ACK = acknowledgement frame; AI = artificial intelligence; DOI = digital object identifier; HTTP = Hypertext Transfer Protocol; IEEE = Institute of Electrical and Electronics Engineers; LoRa = long-range radio modulation; SRIHER = Sri Ramachandra Institute of Higher Education and Research |
<!-- header:end -->

Every item below is something this repository cannot decide or obtain. Nothing here was invented.

## A. Text the author must supply in `paper/main.tex`, `paper/cover_letter.md` and the submission form

| Item | Where | What the author must supply |
|---|---|---|
| Author list, order, affiliations, ORCID | `main.tex` title block | Full list and affiliations (only Mritula S, SRIHER is entered), corresponding author |
| E-mail address | `main.tex` (address and corresp), cover letter | The address to print; none is written in the paper |
| Zenodo DOI for code and derived data | `main.tex` data availability | Create the deposit from the release archive (`release/crashguard-submit-v3.zip`) and enter the DOI; the paper must not claim a DOI before it exists |
| Acknowledgement of the VZCrash authors | `main.tex` acknowledgement | The wording agreed with the dataset authors for their confirmation of the duplicate finding and for crediting it in a corrected release |
| Author contributions (CRediT) | `main.tex` | Roles per author |
| Funding | `main.tex` | Grant numbers or a statement of none |
| Competing interests | `main.tex` | Statement |
| Use of AI tools | `main.tex` | The draft names the assistant and says it was used for code and text drafts under the author's direction. The IEEE Access page (read 2026-11-15) requires disclosure of AI-generated text in the acknowledgements and a citation of the AI system in each section that has such text: list the sections and add the citation |
| Biographies and ORCID | submission form | IEEE Access requires a biography for every author below the references and a public ORCID for the submitting author |
| Suggested reviewers | cover letter and submission form | Names and e-mail addresses (none are proposed here) |
| Date and DOI fields of the template | `main.tex` (`\history`, `\doi`) | Filled by the journal |

## B. Decisions the author must make

Resolved in round 7b (G0.2) and removed from this list: the transmit power (the author chose the conservative reading: the 10 dB is path margin and a compliant dipole node transmits at most 10 dBm). Resolved in the finalize run and removed from this list: the byte layout of the frames (every DESIGN row of `docs/05_architecture/FRAME_LAYOUT.md` was approved, and the micro-confirm gets a one-byte pending index) and the Indian 433 MHz duty-cycle rules (read from G.S.R. 347(E) of 2022). Type approval under rule 5 is a limitation of the paper, not a placeholder.

| Item | Why | Options |
|---|---|---|
| 16-bit short node identifier | uniqueness within the fleet is an assumption of the 14-byte frame and of no model | Keep the assumption stated, or widen the field |
| SisFall licence | the file used is a Zenodo copy (record 22212281, no creators listed, deposited 2026-08-31, licence CC BY 4.0 as stated on the record) | Confirm the licence with the original source (Sucerquia et al., Sensors 2017) or drop the SisFall sentence |
| Formal-model gaps | the 14-byte provisional frame, the cancel frame and a finite seen-set have no formal model (`docs/04_audits/FORMAL_FIELD_CHECK.md`) | Add models in a later study, or keep the stated limit |

## C. Papers to read through the library (author to read via library)

These were read at abstract or record level only, because the full text was closed or the publisher blocked scripted access. No block was bypassed.

| Paper | Depth now | What to check in the full text |
|---|---|---|
| Nessa, Hussain, Fernando, CNS 2020, DOI 10.1109/cns48642.2020.9162318 | abstract | whether the method also uses deadlines or an airtime budget; the Nessa-style baseline of this study is an interpretation of the abstract |
| Vinodhini, Rajkumar, Subramaniam, Int. J. Commun. Syst. 38(1), 2025, DOI 10.1002/dac.5692 | abstract | delivery statistics, security, protocol details (the Wiley page returned a block page) |
| Jabbari and Mohasefi, IEEE TII 18(1), 2022 (online 2021), DOI 10.1109/tii.2021.3075440 | abstract | formal analysis scope and ACK handling |
| One next-generation eCall paper: Hetz et al., Transp. Res. Interdiscip. Perspect. 38, 2026, DOI 10.1016/j.trip.2026.102109 | abstract | whether any provisional-then-confirmed notification is described (the ScienceDirect page returned HTTP 403) |
| Marciano et al., Mechatronika 2024, DOI 10.1109/me61309.2024.10789689 and Carneiro et al., NOMS 2023 | record only | what the systems report |
| Kagai et al., Telecom 7(5):123, 2026 | targeted (survey notes) | the airtime-aware deadline method, for the C6 sentence |

## D. Checks that need a browser or the author's accounts

1. **Google Scholar.** It returned its automated-query block page and was not searched. Run these strings for 2021 onwards and read the top ten for each: "LoRa" "accident" "replay"; "crash notification" "provisional" OR "pre-alert"; "eCall" "early notification" severity; "LoRa" "Tamarin" OR "ProVerif"; "crash detection dataset" leakage OR duplicate. Scopus was not available either.
2. **Journal policy pages.** The IEEE Access author instructions and the current policy on AI-assisted writing: see `docs/04_audits/FINAL_VERIFICATION.md` (row V11.3) for what could be read in this run.
3. **Overleaf compile.** `ieeeaccess.cls` is supplied by Overleaf (the template page may differ from the version assumed here); see `docs/04_audits/LATEX_LINT.md` for the likely errors.
4. **Supervisor review** of the manuscript and the cover letter.
5. **Push and Zenodo.** No remote is configured; the push commands are printed in `docs/04_audits/FINAL_REPORT.md`.
6. **Optional bench run** of the two-stage alert (`docs/08_hardware/R3_BENCH_PROTOCOL.md`, about one hour); it is the one item that only hardware can settle. Do not edit `data/hardware/`.
