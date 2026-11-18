# Changelog

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Release history of the repository, newest entry on top. |
| Evidence labels used | FORMAL |
| Abbreviations | ACK = acknowledgement frame; CI = confidence interval; ESP32 = a Wi-Fi microcontroller family (Espressif); GS-CA = GPS-slotted critical alerts; OS-DR = overhear-and-suppress retries with deadlines; SW-420 = a vibration switch module |
<!-- header:end -->

## Round 7e (branch `round7c`, tag `submit-v6.2`)

- One-time scripts that would overwrite current text now refuse to run (listed in `paper/REPRODUCE.md` item 15); `pp_submission` removed from `make paper`.
- Round 7d (before it): R-REACK requirement and reference configuration (`submit-v6.1`).

## Round 7c (branch `round7c`, tags `round7c-v1` and `submit-v6`)

- Literature corrections only (no experiment, no hypothesis): introduction, formal-verification wording, availability related work, references added or fixed, one absence rule, SisFall not redistributed.
- Code checks: the seen-set is atomic only by construction (requirement written); the reference base sends an ACK only after the tag verifies (with a replay caveat); no SisFall data file in the repository, its history or any release archive; ledger recount 138 in 15 versions (one stale quote in the cover letter fixed).

## Round 7b (branch `round7b`, tags `round7b-v1` and `submit-v5`)

- Close-out items applied (tests note and CI file, transmit power reading, micro-confirm index behaviour, bibliography generator, errata).
- V19: the reserve for four events on fresh seeds. H-R7b-1 supported, H-R7b-2 not supported; bounded check with up to five earlier events; the choice of four came from round-7 data.
- Prior art: the attack class is known (Chen et al. 2023, abstract only); the claim is narrowed to the defence, the model check and the preregistered results.
- Quarantine lemma with pseudonyms: ProVerif race trace explained, Tamarin model with an atomic seen-set verifies it; deviations listed; ledger 138 hypotheses in 15 versions.

## Round 7 (branch `round7`, tag `round7-v1`)

- `PREREGISTRATION_V18.md` (five hypotheses in one Holm family, one descriptive) committed before any run, after the literature gate (`docs/01_literature/R7_PRIOR_ART.md`). New modules `r7_*.py`, models `formal/proverif/r7_*.pv` and `formal/r7_alert_pseudo_fresh_bootctr.spthy`, `firmware_r7/`; the old policy and every earlier key are unchanged (`verify_keys_unchanged.py`: 0 changed, only `r7.` keys added).
- Results: 2 of 5 supported (H-R7-B1, H-R7-B3); H-R7-A1, H-R7-A2 and H-R7-B2 not supported; H-R7-A3 descriptive. Post-run exploration (outside the family): the reserve sized for four events.
- Manuscript: two C4 paragraphs and one C5 paragraph, related work, negative-results rows, ledger row, supplement section; the contributions stay eight; cover letter and highlights updated.

## Round 6 (branch `round6`, tag `round6-v1`)

- `PREREGISTRATION_V17.md` (seven hypotheses, one Holm family) committed before any development run; new modules `r6_*.py`, ns-3 policy `r6m` (earlier policies byte-identical), formal models `formal/proverif/r6_*.pv` and `formal/r6_micro_confirm.spthy`, ESP32 build footprint (`firmware_r6/`, `scripts/r6_footprint.sh`), tests and mutation testing (`tests/test_r6_*.py`, `scripts/r6_mutation.py`).
- Results: 5 of 7 supported; H-R6-2a and H-R6-2b not supported. No tagged result or earlier key changed; the ledger totals of round 6 are under `r6.ledger.*`, the `vf.ledger.*` keys of the verification run are unchanged.
- Manuscript: reframed around a constrained-node profile, new title, section C8, negative results as regime boundaries; cover letter updated.

## Round 5 (branch `round5`, tag `round5-v1`)

- `PREREGISTRATION_V16.md` (L1 to L10, addenda A1, A2, S2, S2.1, S2.2); new modules `r5_*.py` for L1 to L11, tests, mutation testing, ns-3 policies `z0` and `l4` (earlier policies byte-identical), Tamarin models `formal/ratchet.spthy` and `ratchet3.spthy`, results documents, `R5_CODE_VERIFICATION.md`, `R5_CLAIM_AUDIT.md`.
- Held-out results: L1, L3, L4 (ns-3 only), L7b and L8a (FORMAL, with stated limits) supported; L2, L5, L6, L8b, L10a not supported; H-L7a undecided (Tamarin heap exhausted); L11 (added after the initial session, own family) not supported. No tagged result and no earlier key changed.
- Paper: marked round-5 addition in the results section, three negative-result rows, supplement section.


## algo4-v1 (2026-11-15, branch `algo4`, from tag `paper-v1`)

- Round 4: preregistration V15 before any run; A1 (24-byte provisional frame repeated until a verified ACK; ns-3 policy `r3a`, trace engine, 24-byte frame codec), A2 (receiver diversity on LoED per-gateway traces, EXPLORATORY), A3 (ProVerif 2.05 models of the car-reboot id lemma), A4 (literature rows A1 to A3), code verification (43 tests, known-answer reproductions of round-3 numbers, 39 of 40 mutants killed), frozen hashes, fresh sniffer dataset (Zenodo 7919213). Result: 0 of 5 tests supported, A1 and A2 killed; formal rerun of the 24-byte frame proved; paper gets two negative-result rows and a marked ProVerif paragraph. No key of `paper-v1` changed.

## redesign-v1 (2026-11-14, branch `redesign`, from tag `combined-v1`)

- Redesign round for the failed protocol and architecture algorithms: diagnosis (D0), D1 loss-adaptive deadline policy and D2 gateway-signed cluster ACK (FRESH-A), D3 slotted retries and D4 short provisional frame (FRESH-B), preregistration V12 with addenda, code verification (unit, property, invariant, differential, mutation, independent review, known answers), ns-3 calibration and cross-check, C firmware decision path (host build), bench kit, reviewer pack, decision table, literature scan. Addendum C items added after the tag (ADDED-AFTER-SESSION-1): Nessa-style baseline on FRESH-A and in ns-3, calibration under two sensitivity settings, numpy compatibility shim. New result keys `rd.*`; no tagged result or earlier key changed.

## combined-v1 (2026-11-14, branch `combined`, from tag `release-v1`)

- Combined run: Part V (31 headline numbers re-derived, 5 mismatches reported, none in the paper), Part L (literature status of 2026-11-13 and what was opened on 2026-11-14), Part S (simulated hardware-format validation: schema loader, 19 fault variants from `hwsim_v2.py`, failure map, policies on link logs, latency decomposition, security cases, SW-420), Part R (reboot-resilient freshness, frame and tag length, two-stage alert, per-vehicle ACK keys), architecture document and diagram, decision table, claim audit. New keys `sh.` and `ar.`; no existing key changed (`scripts/verify_keys_unchanged.py release-v1`). Command: `make combined`.

## Unreleased (branch `release`, from tag `journal-v1`)

- 2026-11-13, Block R: documents reorganised into `docs/00_overview` to `docs/07_log` and `docs/archive` (`git mv`, history kept); header block on every document; documentation index; README and project status rewritten from `results/results.json`; link, wording, spelling and command checks added. No result file changed (hash comparison in `docs/07_log/CLEANUP_LOG.md`).

- 2026-11-14, Blocks P, Q, A, L: physics generators PH-A and PH-B with integrity gates (none passes), real-only reruns (unchanged), protocol candidates OS-DR, OS-DR-N and GS-CA on the held-out grid (not supported) with a bounded model check, literature status and search strings. New key prefixes `ph.`, `q.`, `pa.`; no earlier key changed (`scripts/verify_keys_unchanged.py`).

## journal-v1 (2026-11-13)

- Finishing round: licence split, audits, protocol check rerun, synthetic stress test, reruns with synthetic training data, protocol-layer study on simulated data, paper skeleton, release manifest. See `docs/03_results/FINISH_RESULTS.md`.

## Earlier tags

- `positive-push-v1`, `journal-push-v3`, `v1.0-round3`, `baseline-before-8h`: see `docs/03_results/POSITIVE_PUSH_RESULTS.md`, `docs/03_results/JOURNAL_RESULTS.md`, `docs/03_results/CLAIM_EVIDENCE.md` and `docs/07_log/DECISIONS.md`.

## Delta verification run (branch `verify2`, from tag `round6-v1`, tag `submit-v2`)

- Recomputed the round-6 numbers from a fresh clone (260 rows, 180 ns-3 runs, the ESP32 footprint build, the six prover runs and the quarantine exploration); every value equals the stored one. New keys `vf2.*` only; no tagged result changed.
- Added `docs/05_architecture/FRAME_LAYOUT.md` (generated from `src/crashguard/frame_layout.py`, 18 tests): byte layout of every frame, working flow, the retry-queue behaviour, and a 16-row table of the abstractions between layout, formal models and ns-3 (closes blocker B5).
- Added the duty-lockout analysis (`docs/03_results/DELTA_DUTY_LOCKOUT.md`, `scripts/vf2_duty.py`), the preemption enumeration (`src/crashguard/vf2_preempt.py`), the audit procedure and split sensitivity (`docs/03_results/DELTA_AUDIT_METHOD.md`).
- Fixed: the header of `ROUND6_RESULTS.md` (empty at `round6-v1`), `scripts/r5_audit.py` (line-ending tolerant), two lint findings.
- Manuscript: wording of the round-6 claims (D3), the three-part hook and the constrained-node profile checked, new paragraphs on the duty model, the retry queue and the quarantine rule, ledger by round, part numbers named once. Supplement trimmed; the full supplement and the other documents are in `supplementary_full/` of the release archive.
