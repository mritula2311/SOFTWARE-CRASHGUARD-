# Finalize report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Report of the finalize run: what changed, counts, release archive and the author's remaining hand steps. |
| Evidence labels used | NOT_RUN |
| Abbreviations | ACK = acknowledgement frame; DOI = digital object identifier; MAC = message authentication code; PDF = Portable Document Format; WSL = Windows Subsystem for Linux |
<!-- header:end -->

Branch `final2` from tag `submit-v2`; tag `submit-v3`. Every check is a row of `docs/04_audits/FINALIZE.md`. No experiment or hypothesis was added; no tagged result or earlier key changed (`scripts/verify_keys_unchanged.py submit-v2`: 0 changed, 95 `vf3.*` keys added). Nothing was pushed, uploaded or e-mailed, no key was requested, and no `&` job was started in WSL.

## 1. What changed

| Item | Change |
|---|---|
| F1 frame layout | Every DESIGN row of `FRAME_LAYOUT.md` approved as written. The micro-confirm is now 8 bytes: a one-byte pending index (assigned by the base in the low byte of the base counter of the flash ACK, not in the MAC input, so the firmware tag code and the frozen hashes are unchanged) in front of the 7-byte frame of `cg_micro_pack`. The base verifies under one entry. Forgery probability per frame is back to 2^-40 and the expected time to one forgery is 125,764 years at the attacker's ceiling (the 8-byte and 7-byte frames have the same time on air at SF7 to SF12); the rejected lookup by trial would give 2,096 years for 60 entries. ns-3 evaluated 13 bytes, so the 8-byte design stays within the evaluated size and the airtime results are conservative for it (the 13-byte frame costs 1.28 times the 8-byte frame at SF7 and 1.33 times at SF9). The models carry the vehicle and flash tag in the frame, so index variants were written and run: ProVerif proves authenticity, binding to the flash and the micro-cancel property; Tamarin verifies the four lemmas (`formal/proverif/vf3_micro_confirm_index.pv`, `formal/vf3_micro_confirm_index.spthy`, `formal/out/vf3/`). Abstraction row F7 rewritten. |
| F2 Indian rules | The source named in the plan was downloaded and its 8-page text read in full on 2026-11-16; it matches the conditions given: rule 3 row 1 (433.05 to 434.79 MHz, 10 mW e.r.p., duty cycle at most 10%, bandwidth not specified), duty cycle defined over an observation interval that is not stated, rule 5 type approval, no indoor-only condition. Added to `references.bib` (`gsr347`) and `LITERATURE_STATUS.md` section 9 as VERIFIED. Every "unverified" statement in the paper, assumptions table, limitations, status, placeholders, cover letter and related documents was replaced (frozen preregistrations and `src/crashguard/lora.py`, which is in frozen hash lists, were left as they are). C5 now gives the condition with its macro: the evaluated 1% hourly allowance is stricter than 10%; under a per-transmission reading of the 10% the condition holds up to SF9 (the load gate still gives SF7), under a strict 1% per transmission no frame fits and the stored results do not transfer. Type approval is in the limitations. |
| F2 power (a correction to the plan) | The plan says the simulations used 10 dBm. The code uses 14 dBm transmit power with a 10 dB extra loss (`world_sim.py`, `xsim_alert.cc`, `ASSUMPTIONS.md`). Written as found in `docs/03_results/FINALIZE_INDIA_RULES.md` section 3 and in C5: if the 10 dB is transmit-side the radiated power is 1.9 dBm (1.5 mW), inside the limit; if the radio delivers 14 dBm to a 0 dBi antenna the e.r.p. is 11.9 dBm and the 10 mW limit needs a 1.85 dB reduction (4.00 dB for a dipole), about 0.7 of a spreading-factor step of link margin (analytical, nothing simulated). |
| F3 hygiene | The four tracked release zips are untracked (`git rm --cached`, `release/*.zip` ignored); no history rewrite, no tag moved. Repository: 376.76 MiB loose, 83.60 MiB packed for all branches and tags. Largest tracked file 37.4 MB; no file over 50 MB anywhere in history, so no stop was needed (`docs/04_audits/PUSH_SIZE.md`). `paper/REPRODUCE.md` step 13 gives the two test commands. |
| F4 package | Numbers (340 macros), figures, cover letter, highlights, supplement regenerated; claim audit of the 4 changed claim sentences and a consistency sweep (0 lines left, 8 reviewed); main text 15 pages estimated (8 figures, 5 tables, 0 errors, ledger table fits), reduced supplement 36 pages; placeholders updated. |

## 2. What did not run

- **Tests are only partly confirmed.** The whole suite passed earlier the same day (684 passed, 2 skipped). In this run Windows Application Control began to block `lib_lightgbm.dll` in the existing `.venv` (`WinError 4551`), and every test that imports lightgbm failed or could not be collected: in two parts, 656 passed and 2 were skipped, 7 failed and 14 errored (part 1: 56 passed, 4 failed, 13 errors; part 2: 600 passed, 3 failed, 1 collection error). All 21 are `WinError 4551`; none is an assertion failure. The policy was not bypassed. The blocked tests are the redesign simulator and analysis tests, the positive-push model tests and the combined-run tests; none of the code of this run is in them. **The author should rerun the two parts on a machine where lightgbm loads before relying on the 684 figure for this exact commit.**
- The Access class was not compiled here (needs pdfTeX); the page counts use a stand-in class.
- Instruction counts, timing and energy of the decision path stay NOT_RUN (no emulator).
- The index variants of the models were run once; no mutation test of them was made. The control model (tag without T1) was not rerun with an index.

## 3. Known hazards found

- `scripts/pp_make_bib.py` would rebuild `references.bib` without the hand-added entries (`fars`, `geonames`, `gsr347`); do not run it without adding them.
- The earlier stored keys `vf2.layout.forge.*.p_per_frame` hold 0.0 because of a rounding slip; they are not used and not changed (the new `vf3.layout.forge.*` keys are correct).
- The comments in `src/crashguard/lora.py` and `r3_t4.py` still call the Indian limit unverified; `lora.py` is in frozen hash lists and was not touched.
- Whole-suite single-process runs stalled three times earlier in the delta run; use the two-part commands.

## 4. Release

`release/crashguard-submit-v3.zip` (git-ignored), built from a fresh clone of `final2` at the tagged commit, with `supplementary_full/` (full supplement PDF and source, the Markdown sources of the documents the supplement leaves out, and `INDEX.md`). SHA-256 and file count are in `release/crashguard-submit-v3.zip.sha256` and `release/crashguard-submit-v3.manifest.txt`, committed after the build.

## 5. What the author must do by hand, in order

1. Rerun the two test parts of `paper/REPRODUCE.md` step 13 where lightgbm loads (section 2).
2. Say which reading of the 10 dB extra loss holds for the hardware (transmit-side loss, or path loss), and enter the antenna gain and cable loss (`paper/PLACEHOLDERS.md` section B).
3. Fill the placeholders of `paper/PLACEHOLDERS.md` (authors, e-mail, ORCID, biographies, funding, CRediT, interests, acknowledgement wording, AI-tool disclosure, suggested reviewers).
4. Confirm the VZCrash acknowledgement wording and the SisFall licence.
5. Compile on Overleaf with the current Access class and check the page count (`docs/04_audits/FINALIZE_LATEX_LINT.md`).
6. Create the Zenodo deposit from the archive and enter the DOI; then push.

## 6. Push commands (not run)

```
git remote add origin <your repository URL>
git push origin final algo4 round5 round6 verify verify2 final2
git push origin --tags
```

Tags to be pushed include `round3-v1`, `paper-v1`, `algo4-v1`, `round5-v1`, `submit-v1`, `round6-v1`, `submit-v2` and `submit-v3`. About 84 MiB will be sent (`docs/04_audits/PUSH_SIZE.md`).
