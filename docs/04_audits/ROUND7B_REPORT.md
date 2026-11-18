# Round 7b report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Report of round 7b: close-out items, the re-test of the four-event reserve (V19), prior art, quarantine lemma status, deviations, design notes and the package. |
| Evidence labels used | TRACE_DRIVEN, SIMULATED, ANALYTICAL, NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; CI = confidence interval; IEEE = Institute of Electrical and Electronics Engineers; MAC = message authentication code; PDF = Portable Document Format; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Log with every step: `ROUND7B.md`. Results: `docs/03_results/ROUND7B_RESULTS.md`. Preregistration: `docs/02_preregistration/PREREGISTRATION_V19.md`. Keys `r7b.*` only (no existing key, stored result or frozen file changed: `scripts/verify_keys_unchanged.py submit-v4` reports 0 changed or missing).

## Summary

- **G0 (close-out items):** none of the five was on the tip of round 7. All applied now.
- **G1 (V19):** H-R7b-1 **supported**; H-R7b-2 **not supported** (as expected in V19 before the run). Holm over two. The reserve size was chosen from round-7 data, so this is a confirmation on fresh seeds and not a blind test.
- **G2:** the full text of Chen, Ben-Othman and Mokdad (2023) is closed access: **abstract only; the author is to open it via the institutional library.** The claim for the attack is narrowed everywhere; four references verified against Crossref.
- **G3:** the quarantine lemma status is none of the three cases of the brief; it is a ProVerif trace of a race on the seen-set (see below), and a Tamarin model with an atomic seen-set verifies the lemma.
- **G4:** the five deviations are listed (plus four more of this round) in `ROUND7B_DEVIATIONS.md`, in this report (section 6) and in the supplement.
- **G5:** both design notes written (ANALYTICAL); verdict of H-R7-B2 unchanged.
- **Not done:** the paper and supplement PDF were not compiled (no TeX distribution); nothing is measured on hardware; the CI file was not executed (no remote).

## 1. G0: what was missing, what was applied

| Item | Found | Action |
|---|---|---|
| 1 tests note and CI | `paper/REPRODUCE.md` had the two-part commands but no WSL or Linux note; `.github/workflows/tests.yml` did not exist (only `c_checks.yml`) | applied: REPRODUCE.md item 14 and `tests.yml` (two parts, `ubuntu-latest`, no secrets; **not executed**: no remote) |
| 2 transmit power | not applied: the paper said the radiated power "must stay within 10 mW"; PLACEHOLDERS still listed the row | applied, conservative reading: a compliant dipole node transmits at most 10 dBm; the stored link results (14 dBm) are an optimistic bound on margin by up to 4.00 dB; protocol, security and duty-cycle results do not use transmit power; ASSUMPTIONS.md, limitations and the duty paragraph updated; row removed from PLACEHOLDERS. **Correction to the brief:** 4.00 dB is about 1.4 spreading-factor steps at the simulators' 2.8 dB per step (the 0.7 of the brief is the 0 dBi case, 1.85 dB); the paper uses the computed 1.4 (`r7b.g0.power.*`) |
| 3 micro-confirm index | the index byte is outside the MAC input, the code rejects on a miss (`frame_layout.micro_lookup`), and tests cover it; this was not written as one statement | applied: FRAME_LAYOUT.md section 10.1. Reject on a miss, no trial fallback, so the n x 2^-40 bound does not apply; changing the index equals dropping the frame; 2^-40 per frame stays |
| 4 bibliography | `pp_make_bib.py` dropped `gsr347` and the nine round-7 entries when rerun (ten keys missing); `fars` and `geonames` survived through `REFERENCES_VF.bib` | applied: `paper/refs_manual.bib` (read before the other sources) holds the hand-added entries; rebuilt `references.bib` has 60 entries, identical to the previous file entry for entry before the G2.4 corrections |
| 5 errata | not present | applied: `ERRATA.md` E1; the four `vf2.layout.forge.*.p_per_frame` keys are 0.0; a search finds no reader (the paper reads the `vf3.` keys) |

## 2. G1: the four-event reserve (V19)

V19 was committed before any run (commit `3879320`; SHA-256 of the file, CRLF read as LF: `6b6f4a0d9085ce455bbb317ff36aaa7e9ec78f1389323ea741c6e2ef1566bd2d`).

| Hypothesis | Result | Verdict |
|---|---|---|
| H-R7b-1 (SIMULATED, seeds 100 to 105, 9 cells of 1,200 runs) | k = 4 policy: 100% in every cell; worst lower 95% limit 99.75%; p = 5.8e-06 | **SUPPORTED** |
| H-R7b-2 (TRACE_DRIVEN, fresh start points, 18 cells) | delivery criterion fails in 2 cells (group H, both schemes, 10% off-time: -2.36 points, lower limit -2.42); time criterion holds in all 18 | **NOT SUPPORTED** |

At the 1% allowance on the same draws: shipped policy 2%, 1% and 0% at SF7, SF8 and SF9; reserve for one event 73%, 30%, 36% (the V18 failure reproduced); two events 92%, 59%, 77%; three events 99.8%, 89%, 100%; four events 100%. The four-event reserve takes about 8% of the 1% allowance at SF7 and about 24% at SF9. India's 10% rules are the main deployment regime (every reserve size passes the 10% allowance and the 10% off-time cells); 1% is the stricter case.

**Trade-off curve (DESCRIPTIVE):** benign delivery against k = 1 to 4 is flat (group H, 10% off-time: -2.36 points at every k; hourly allowances: -0.40 at every k). Reason: the replay runs each event with a fresh duty state, so the reserve never binds, and the cost comes from the withdrawal rule and the time guard under the off-time, which do not depend on k. A cost that grows with k under sustained load was not run (NOT_RUN).

**Formal check** (`r7b_formal.py`; bounds exactly as in V19 section 3: allowance 40, 44, 48; window 70 steps; costs flash 1, confirm 4 with 2 tries, micro 1; reserve 9 for one event and 33 for four; earlier events 0 to 5; gaps 0 and 2; every ACK outcome; target confirm or cancel; the off-time model once per m): F1 (the reserve rule) and F2 (conditional Invariant 2) hold with 0 violations for k = 1 and k = 4; F3 holds (k = 4, at most 3 earlier events, 0 unconditional violations); the shipped policy violates Invariant 2. **F4 as written is not met:** the k = 1 policy has no unconditional violation with at most 3 earlier events; it fails from 4 earlier events (allowance 40: 983,040 violating configurations), where the k = 4 policy still holds, and k = 4 fails from 5 earlier events (V19 expected 4). The reason is the scale of the abstraction: 70 steps hold about four events, so the old and the one-event policies do not fail earlier. The control works at the bound of 4.

## 3. G2: prior art

Chen, Ben-Othman and Mokdad, IEEE Communications Letters 27(11):3123-3126, 2023: the Crossref record is verified; OpenAlex reports no open copy; nothing was bypassed. **Abstract only; author to open via the institutional library.** The abstract says: the Aloha access and the duty-cycle limit expose LoRaWAN to denial of service; two attacks on the confirmed transmission are proposed; simulation shows lower packet success and network energy efficiency with fewer attackers than a baseline. The abstract does not state the exact mechanism, whether the duty budget is drained by ACK suppression, or whether a defence is proposed: **these three are unknown to us** and must be read from the full text.

Claim rewritten (abstract, contributions, related work, C4 paragraph, cover letter): the attack class is known (Chen et al. 2023 and the energy-depletion papers of the literature gate); CrashGuard contributes the reserved-budget defence for a two-stage alert, the bounded model check with its control, and the preregistered results under India's rules. The attack is not described as new.

References checked against Crossref (`paper/reference_status.txt` updated, none dropped): Chen et al. (record verified, full text not read); Liu et al. 2026 (IEEE Internet of Things Journal 13(18):42080-42092; two author names have given and family swapped in the record, kept as printed, publisher page not opened); Mechler et al. (ACM WiSec 2025, pp. 256-261); Nafees et al. (ACM CCS 2020, pp. 2117-2119); also Mikhaylov et al. (ARES 2019, pp. 1-6) and Suciu et al. (published as ADHOC-NOW 2018, not 2019).

## 4. G3: quarantine lemma with pseudonyms

Exact status. ProVerif (`r7_lemmas_quarantine.pv`) **proves the non-injective no-framing form** and reports the injective form **false with a trace**. The trace has two copies of the base thread that both read the seen-set before either inserts: a race between the check and the insert, not a replay across time and not a forgery. Round 7 had no Tamarin quarantine model, so "not proved" was true but incomplete. This is a finding (a requirement on the base: the seen-set check and insert must be one atomic step), not a time-out and not only a wording problem.

Fix attempt (inside the time limit): `formal/r7b_quarantine_pseudo.spthy`, Tamarin 1.12.0, each lemma under 3 s. With an atomic seen-set: executability, non-injective and **injective no-framing verified**. Controls: no seen-set (the race) falsifies the injective form and keeps the non-injective form (reproduces ProVerif); a strike before the tag check falsifies both. Limits: a separate small model (no window advance, no reboot), and atomicity is assumed, not derived.

The paper states which lemmas hold with pseudonyms and in which tool (FRAME_LAYOUT.md section 10.2, C4 paragraph) and says the quarantine keeps its no-framing property with pseudonyms **if the base applies the seen-set atomically**; it does not say "still works" without that condition.

Does the tag-covers-boot-and-counter fix touch a frozen file? **No.** It lives in `r7_pseudo.py`, `firmware_r7/`, `formal/proverif/r7_*.pv` and the pseudonym Tamarin model, all new; `git diff --name-status submit-v3 submit-v4` lists no modified file in `xsim/`, `firmware_*`, earlier `formal/` models or frozen modules, and `r5_audit` passes. The base design is unchanged (its tag already covers every preceding byte); FRAME_LAYOUT.md section 10.3 and abstraction row F21 say so.

## 5. G5: design notes (ANALYTICAL; nothing implemented in frozen code)

**Reboot resolution.** Replace the linear scan (84.4 ms in the Python reference: 1,000 vehicles x boot + 1 to boot + 3 x 16 pseudonyms = 48,000 PRF evaluations, about 1.76 microseconds each) by a hash table from pseudonym to (vehicle, boot, counter) that holds the pseudonyms of the next three boot values of every vehicle. Per frame: one expected O(1) lookup, then the tag check. Memory: 48,000 entries at 8 bytes = 384,000 bytes before the load factor. Upkeep: after a match for one vehicle, 3 x 16 = 48 PRF evaluations (about 0.08 ms in Python) off the frame path; the initial build equals one scan. The table is built when the base sees a boot-counter change for a vehicle.

**Pseudonym length.** A collision costs one extra tag verification, not a security failure, because the tag decides (the misattribution probability is the tag forgery probability, 2^-64 for the 8-byte tag, 2^-40 for the micro tag). With the V18 formula (1,000 vehicles, window 16): 3.7e-06 at 4 bytes (H-R7-B2 failed against 1e-06) and 1.5e-08 at 5 bytes. The extra byte adds 5.12 ms to the 26-byte ACK at SF7 (10.24 ms at SF8, 20.48 ms at SF9) and nothing to the 97-byte alert at SF7 to SF9; the 14-byte flash gains 10.24 ms only at SF8. The verdict of H-R7-B2 is not changed.

## 6. G4: deviations

See `ROUND7B_DEVIATIONS.md` (also in the supplement). In short: (1) round 7 branched from the head of `final2` because `submit-v3.1` does not exist; (2) the A bounded check of round 7 used allowance 16 to 40, a window of 30 and at most 2 earlier events (an attempt with a window of 10 was too short and was replaced); round 7b adds a third enumeration; (3) the ns-3 ACK-drop hook was cut because the ns-3 policy files are frozen (the engine replaced it); (4) `doc_style_check.py` skips V18 because V18 is frozen, so V18 wording is unchecked; (5) the tag-coverage defect was found by the C benchmark and the models were rerun. Added in round 7b: the 0.7 against 1.4 step correction, F4 not met as written, the exact quarantine status, and the post-hoc choice of k.

## 7. Package

Ledger: 138 hypotheses in 15 versions (V19 adds two: 1 supported, 1 not supported); 125 run, 48 supported, 72 not supported, 4 partly, 13 not run. The ledger document also had duplicated rows from an earlier rerun (one V18 totals row and three round-7 rows); they were removed. The release archive, checks from a fresh clone and the tags are recorded in `ROUND7B.md`.

## 8. What the author should check by hand

1. Open Chen et al. (2023) in the library and read the mechanism, whether it drains the duty budget through ACK suppression, and whether it proposes a defence; then adjust one sentence of the related work if needed.
2. Whether the base (or the base simulator) really applies the seen-set check and insert atomically, since the quarantine result depends on it.
3. The two author names of Liu et al. (2026) on the publisher page.

<!-- r7c_addendum:start -->
## 9. Round 7c (no new experiment; keys `r7c.*`)

1. **Atomicity of the base (code reading).** Neither a lock nor a threaded design: the reference base (`BaseVerifier.handle`) does the check and the update in one method, called from one sequential loop; a scan of 24 base-side and firmware source files finds no concurrency primitive (`r7c.atomic.*`); nothing enforces atomicity and no base server exists. Written as design requirement R-ATOMIC in `FRAME_LAYOUT.md` section 11 and in the C4 paragraph; the quarantine lemma (injective form) holds only with it.
2. **Control F4.** The paper (C4 paragraph) now says that the control registered in V19 was not met as worded (the one-event reserve fails from four earlier events, not at most three) and that the expectation for the four-event reserve was off by one; the supplement has it in `ROUND7B_RESULTS.md` and in deviations row 7.
3. **Ledger recount** (`scripts/r7c_ledger_recount.py`, keys `r7c.ledger.recount.*`): the per-hypothesis rows of `HYPOTHESIS_LEDGER.md` give 138 preregistered, 125 run, 48 supported, 72 not supported, 4 partly, 13 not run in 15 versions, equal to the Totals table in every version and in total and to the keys `r7b.ledger.all.*`. One row, the V13 re-test of H-C3, is counted under V5 by the ledger's own rule. Quoted in the cover letter, `main.tex` and both supplements through the macros `LedgerN` and the others (138, 15), and in `CHANGELOG.md` and section 7 above; older quotes (136 and 14, 130 and 13) are in documents of earlier rounds and are labelled with their round. The Versions table of the ledger lacked rows for V18 and V19 (added).
<!-- r7c_addendum:end -->
