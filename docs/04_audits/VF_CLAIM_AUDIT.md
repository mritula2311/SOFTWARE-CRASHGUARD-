# Claim and number audit of the final manuscript (V8.1 to V8.3, V8.5)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Claim words, bare numbers, contribution sentences and cross-document consistency of the final manuscript. |
| Evidence labels used | FORMAL, ANALYTICAL |
| Abbreviations | ACK = acknowledgement frame; LoRa = long-range radio modulation; NHTSA = National Highway Traffic Safety Administration |
<!-- header:end -->

Method. `scripts/vf_claim_scan.py` lists every sentence of `paper/main.tex`, `paper/supplement.tex` and the generated supplement files that contains improves, outperforms, better, robust, secure, proved, verified, validated, significant, guarantee or real-time (221 sentences; 20 in `main.tex`). `scripts/pp_paper_audit.py` checks that every number of the result sections is a macro of `paper/generated/numbers.tex` (0 bare numbers, 144 whitelisted design constants). `scripts/vf_consistency.py` checks that the same number appears in the paper, README, project status, claims file, highlights and graphical abstract.

## V8.1 Claim words in `main.tex`

| Sentence (shortened) | Word | Evidence label | Ledger row | Verdict |
|---|---|---|---|---|
| Tamarin proves alert authenticity, per-vehicle acknowledgement binding and freshness-window properties | proves | FORMAL | V14 H-T2sec (PARTLY) | kept; the sentence names the per-vehicle-key design and the symbolic model |
| ProVerif ... proves a boot-counter fix | proves | FORMAL | V15 A3 (not a hypothesis) | kept; restricted to the car-side model; the introduction now says that Tamarin did not decide the same lemma |
| alert authenticity, acknowledgement authenticity and no cross-vehicle suppression are proved (M1) | proved | FORMAL | V14 H-T2sec | kept |
| window, at-most-once and no-double-acceptance properties are proved | proved | FORMAL | V14 H-T2sec | kept |
| identifiers are not reused with a boot counter, for any number of boots | proves | FORMAL | V15 A3 | kept with the persisted-write assumption stated |
| ... every number is labelled: ... proved or enumerated | proved | FORMAL | none | descriptive |
| LoRa security work is mostly not about crash alerts | security | none | none | context sentence about the literature |
| Manuel et al. use no counter or nonce, no authenticated acknowledgement, no formal proof | security | none | none | comparison with the full text read |
| Thresholds were chosen on validation data only | validation | none | none | the data split, not a claim of validity |
| Original verdicts are not softened | better (inside the table text) | none | none | not a claim |
| the study gives requirements, not a validated product | validated | none | none | negation; kept |
| "A bounded model ... verifier" | verifier | ANALYTICAL | V5 B1 | kept; labelled a model, not the implementation |

No sentence in `main.tex` says improves, outperforms, robust, significant, guarantee or real-time. The generated supplement files contain such words only inside the repository's own decision tables, where they appear in qualified or negated form (for example, "D1 is not shown to be better" and "an implementation guarantee from the Tamarin models" listed as something the study does not support). The 12 remaining hits in `lit_NOVELTY_MATRIX_2021PLUS.tex` quote prior work.

## V8.2 Bare numbers

`scripts/pp_paper_audit.py`: 0 bare numbers in the result sections. The numbers added in this run are macros: the ledger totals (`LedgerN` and the others), the tool versions (`EnvPython` and the others), `VzCrashEvents`, `VzTestExactShare`, `DvSettingsMeet`, `DvSettingsAll`, `FlashAirSeven`, `FlashAirNine`, `NsPatchRuns` and the V16 supplement numbers. Design constants (15-tree forest, 80% rule, 13 to 15 bytes, 95% required, 433 MHz, 1% limit) are in `paper/number_whitelist.txt`.

## V8.3 Contribution sentences against the novelty matrix

| Contribution | Main-text sentence | Allowed wording (`NOVELTY_MATRIX_2021PLUS.md`) | Fixed |
|---|---|---|---|
| C1 | VZCrash contains cross-split groups ...; no identical windows in two activity-recognition benchmarks | audit of VZCrash; leakage audits exist for other sensor benchmarks | no |
| C2 | range and rate for delta-V within 10% by crash mode; restoration as a limited fix | quantification on public NHTSA pulses, frontal barrier only | no |
| C3 | a compact forest and its flash cost | a measured trade-off, not a new method | the earlier text also listed trigger-aware evaluation and prevalence; they are now in "Other detector results" |
| C4 | per-vehicle binding, freshness after a reboot, boot counter | symbolic model with per-vehicle ACK binding and freshness; the frozen design needs the counter or a one-second assumption | yes: the earlier draft said two provers agree; Tamarin did not decide that lemma, so the sentence now says proved in ProVerif only |
| C5 | provisional frame without a class; airtime bound at SF7, not SF9 | as in the matrix | no |
| C6 | an evaluation finding, not a new policy | as in the matrix | no |
| C7 | application of gravity-referenced alignment; mirror flips not recovered; wake-on-motion with an active-share caveat | an application, not a new method | no |

## V8.5 Consistency sweep

`scripts/vf_consistency.py` compared ten facts (F1, F2, F3, F4, F9 to F12, F16, F17) across the paper, README, project status, claims file, highlights, graphical abstract and abstract facts. 32 lines mention a topic without a canonical value; all were read: they are topic words in lines about other quantities (for example, hypotheses that mention "recall at the 1% target" without a value), not conflicting numbers. Differences found and fixed in this run:

| Where | Before | After |
|---|---|---|
| `paper/references.bib` (LoED) | Bhatia, Lavanya | Bhatia, Laksh (Zenodo, arXiv and the data descriptor) |
| `paper/references.bib` (Vinodhini) | year 2023 with volume 38 | print year 2025 (volume 38), online 2023, from Crossref |
| `paper/references.bib` (CHOIR, VZCrash) | an earlier title; author list not verified | title and authors from the arXiv pages |
| `paper/highlights.md` | third highlight named Tamarin only | names the per-vehicle binding and the boot counter |
| Abstract (253 words) | over the limit | 246 words |
| Introduction | "two provers agree" on the boot counter | ProVerif proves it; Tamarin did not decide it |
