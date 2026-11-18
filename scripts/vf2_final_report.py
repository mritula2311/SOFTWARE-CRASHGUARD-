"""D6.5: write docs/04_audits/DELTA_FINAL_REPORT.md (counts come from DELTA_VERIFICATION.md and results.json).

    python scripts/vf2_final_report.py [tests passed] [tests failed] [tests skipped]
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}
counts = subprocess.run([sys.executable, str(ROOT / "scripts/vf2_report_counts.py")], capture_output=True, text=True).stdout.strip()
tp, tf, ts = (sys.argv[1:4] + ["?", "?", "?"])[:3]
sha = (ROOT / "release" / "crashguard-submit-v2.zip.sha256").read_text(encoding="utf-8").split()[0] if (ROOT / "release" / "crashguard-submit-v2.zip.sha256").exists() else "NOT_BUILT"
man = (ROOT / "release" / "crashguard-submit-v2.manifest.txt").read_text(encoding="utf-8").splitlines() if (ROOT / "release" / "crashguard-submit-v2.manifest.txt").exists() else []
files = next((x.split()[1] for x in man if x.startswith("files ")), "?")
L = lambda k: int(R[f"r6.ledger.all.{k}"])  # noqa: E731
txt = f"""# Delta verification report

<!-- header:start -->
<!-- header:end -->

Branch `verify2` from tag `round6-v1`; tag `submit-v2`. Every check is one row in `docs/04_audits/DELTA_VERIFICATION.md`. No experiment, algorithm or hypothesis was added; no tagged result or earlier key changed (`scripts/verify_keys_unchanged.py` against `round6-v1` and `submit-v1`: 0 changed; only `vf2.*` keys were added). Nothing was pushed, uploaded or e-mailed, no API key was requested, no file under `data/hardware` was read, and no background `&` job was started in WSL.

## 1. Counts per block

{counts}

D6 (package) and the reviewer pass (D5.4) are recorded in their own rows at the end of the log. The row of D2 that records the frame layout is PASS because the layout, its tests and the abstraction table exist; the DESIGN rows of the layout are a proposal that the author must confirm (section 5).

## 2. What was recomputed from the fresh clone

All 260 round-6 rows (the 16 ns-3 cells, the R6-2 held-out analysis, the bounds and the forgery table) match the stored keys; 180 ns-3 runs are byte-identical; the footprint build (Espressif GCC 12.2.0) gives the same 29 keys (forest data 15,771 bytes, linked flash 33,559 bytes, stack chain 1,568 bytes); the six prover runs and the quarantine exploration give the stored verdicts; all 277 macros of `numbers.tex` are identical. Detail: `docs/04_audits/RECOMPUTE_R6.md`, `docs/04_audits/DELTA_FORMAL_RERUN.md`.

Defects found in the tagged state, none touching a stored result: the header of `docs/03_results/ROUND6_RESULTS.md` was empty (a repository test failed at `round6-v1`; fixed), and the frozen-hash audit of round 5 broke on a Windows checkout through line endings (`scripts/r5_audit.py` made tolerant). Tests in the working copy: {tp} passed, {tf} failed, {ts} skipped (the host C compiler is blocked once in a while by the Windows Application Control policy, B4).

## 3. The frame-layout resolution (blocker B5)

`docs/05_architecture/FRAME_LAYOUT.md` (generated from `src/crashguard/frame_layout.py`; 18 tests) gives the byte layout of the alert (97 bytes), ACK (26), flash and cancel (14, and 15 with a boot byte), and the micro-confirm and micro-cancel (7), with the freshness field (GPS seconds, or epoch and counter without a fix), the sequence in the second, the boot counter, the tag lengths and the domain separation. Rows are marked CODE (an encoder fixes them) or DESIGN (a choice made here). The 16-row table of section 8 reconciles layout, formal models and ns-3 frames: rows F1 to F5 are the five mismatches of `FORMAL_FIELD_CHECK.md`, F6 its gap, F7 to F16 are new. Every row is resolved by a document change or a stated abstraction; no stored result changed.

Findings made while writing it: the 7-byte micro frame carries neither the vehicle nor the provisional tag, so the base finds the pending entry by trial and the forgery probability per frame is up to n times 2^-40 (expected years {R['vf2.layout.forge.n1.expected_years']:,.0f} for n = 1 and {R['vf2.layout.forge.n60.expected_years']:,.0f} for n = 60); the ns-3 micro frame (13 bytes) has the airtime of the 14-byte flash at SF7.

## 4. Third-review items (D7)

- **Duty lockout.** Every evaluated simulator and replay enforces only an hourly allowance; the ns-3 module's sub-band duty is 1 and it has one channel; no 433 MHz plan exists in the code. The lockout trap therefore does not arise in any stored result. For a region with a per-transmission off-time the condition is A_f <= d (T_F - s_f) (ANALYTICAL; at 1% no frame fits, at 10% up to SF{int(R['vf2.duty.max_sf_condition_a.d10.median'])}); all stored two-stage events at SF7 and SF9 would have been delayed, so the stored results do not transfer. It is merged with the spreading-factor rule as one gating rule (`docs/03_results/DELTA_DUTY_LOCKOUT.md`).
- **Quarantine.** Stated in section C4: failed-tag frames may only feed a per-cell rate limit; per-vehicle quarantine only for authenticated misbehaviour; bounded exhaustive exploration in Python found the attack (2 frames in one slot) and confirmed the fix by construction; no general claim.
- **Preemption.** The evaluated node does not preempt (FIFO queue; only policy r3a does). Recommended as a design change; airtime saving 0 s at SF7 to SF9; bounded enumeration shows it adds no end state; a stuck pre-alert exists only if every final-stage frame is lost, with or without preemption, and a base timeout removes it.
- **Audit and split.** 0.901 is the recall on the test split as supplied; three stored versions plus one illustrative random re-split are in `docs/03_results/DELTA_AUDIT_METHOD.md`; no vehicle-grouped split can be built.

## 5. Remaining blockers

B1 to B4 and B6 as in `docs/04_audits/BLOCKERS.md` (unchanged). B5 is closed by a document. New: B7 (line-ending sensitivity of the round-5 audit, tool fixed) and B8 (empty header at the tag, fixed). Not blockers but open: the DESIGN rows of the frame layout await the author; the ns-3 micro frame stays at 13 bytes; instruction counts, timing and energy of the decision path are NOT_RUN (no emulator); the Access class has not been compiled here.

## 6. Release

`release/crashguard-submit-v2.zip` (git-ignored), built from a fresh clone of the final commit of `verify2`, with `supplementary_full/` (the full supplement as `supplement_full.pdf` and `.tex`, the Markdown sources of every document the supplement leaves out, and `INDEX.md`). SHA-256 and file count are in `release/crashguard-submit-v2.zip.sha256` and `release/crashguard-submit-v2.manifest.txt` (committed after the archive was built, so that the archive does not contain its own hash).

## 7. What the author must do by hand, in order

1. Read `docs/05_architecture/FRAME_LAYOUT.md` section 2 and confirm or change every row marked DESIGN (freshness field at offset 10, sequence in byte 42, boot counter in bytes 43 to 46, the no-time flag, the 15-byte flash, the bit positions of micro byte 0), and decide whether to add a one-byte vehicle index to the micro frame (section 7 of that file).
2. Fill the placeholders of `paper/PLACEHOLDERS.md` (authors, e-mail, ORCID, biographies, funding, CRediT, interests, acknowledgement wording, AI-tool disclosure with the section list, suggested reviewers).
3. Read `paper/main.tex` sections C5 and C8 and the cover letter once: the micro-confirm numbers to quote are the airtime over the two-stage alert and per delivered alert, never the negative extra airtime against single-stage; check that you are willing to state that the stored two-stage results do not transfer to a per-transmission off-time region.
4. Check the India 433 MHz duty-cycle and listen-before-talk rules and the number of sub-bands a node may use there (UNVERIFIED), and enter them or keep the wording.
5. Confirm the VZCrash acknowledgement wording and the SisFall licence (`paper/PLACEHOLDERS.md` section B).
6. Compile on Overleaf with the current Access class (`docs/04_audits/DELTA_LATEX_LINT.md`), check the page count and the ledger table width, and make the PDF that matches the source.
7. Create the Zenodo deposit from `release/crashguard-submit-v2.zip`, enter the DOI, then push.

## 8. Push commands (not run)

```
git remote add origin <your repository URL>
git push origin final algo4 round5 round6 verify verify2
git push origin --tags
```

Tags to be pushed: `round3-v1`, `paper-v1`, `algo4-v1`, `round5-v1`, `submit-v1`, `round6-v1`, `submit-v2` and the earlier ones. The release archives of earlier rounds are tracked in git at these tags (inherited from round 6, about 37 MB each); the archive of this run is not tracked.
"""
(ROOT / "docs" / "04_audits" / "DELTA_FINAL_REPORT.md").write_text(txt, encoding="utf-8")
print("written")
