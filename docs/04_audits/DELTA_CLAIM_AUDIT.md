# Claim audit of the changed text (delta verification D5.1)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Claim audit of the sentences changed in the delta verification run: strong words mapped to evidence labels, keys and ledger rows. |
| Evidence labels used | MEASURED_SOFTWARE, SIMULATED, FORMAL, ANALYTICAL, NOT_RUN |
<!-- header:end -->

Method. Every sentence of `paper/main.tex` that is new or changed since `round6-v1` and contains a strong or claim word (proved, verified, secure, supported, holds, fails, attack, cannot, never, recommend, if and only if, and similar) was listed with `scripts/vf_claim_scan.py` logic restricted to the difference. Each is mapped to its evidence label and to the key, document or ledger row that supports it. The same wording rules were applied to the cover letter (generated blocks of `scripts/vf2_cover.py`), the README rows, `CHANGELOG.md` and the supplement documents added in this run. No sentence needed to be weakened beyond the edits already made; two sentences were reworded during the audit (marked).

| # | Sentence (short) | Strong word | Label | Evidence | Verdict |
|---|---|---|---|---|---|
| 1 | Abstract: micro-confirm airtime and delivery in the sixteen ns-3 cells | proved (ratchet) | SIMULATED; FORMAL | `r6.r1.ns3.*` (ledger V17 H-R6-1a and 1b supported, Holm over seven); `r6.f.h3a.*` (ProVerif, three steps) | holds; the abstract now says "in the sixteen ns-3 cells" and no trace delivery claim |
| 2 | Contribution C4: boot-counter design proved in ProVerif; layout; quarantine counter after verification | proved, verification | FORMAL | `FORMAL_RERUN.md` (ProVerif boot counter proved, Tamarin undecided); `FRAME_LAYOUT.md`; `r6.f3b.*` | holds as worded (Tamarin limit stated) |
| 3 | Ledger table by round | hold | ANALYTICAL | `r6.ledger.V*.*` sums; totals equal `r6.ledger.all.*` (checked by the macros) | holds |
| 4 | Vehicle-grouped split cannot be built | cannot | MEASURED_SOFTWARE | `DATASET_FACTS.md` (no vehicle or trip id), `DECISIONS.md` 2026-11-15 | holds |
| 5 | Naive random re-split gives a recall close to the supplied one | none | MEASURED_SOFTWARE, descriptive | `vf2.split.naive_random.*` (test split not read) | holds; labelled illustrative; no family |
| 6 | C1 table rows | none | MEASURED_SOFTWARE | `vz.v4.*`, `vf2.split.*` | holds |
| 7 | Layout is a design proposal, tested against the encoders, no firmware implements it | no firmware | ANALYTICAL | `tests/test_frame_layout.py` (18 tests); `FRAME_LAYOUT.md` row labels CODE and DESIGN | holds |
| 8 | Quarantine by a key-less attacker with two frames in one slot | attacker | FORMAL (bounded) | `r6.f3b.A_count_before_verification.*` (334 states; shortest attack 2 frames in slot 0); rerun in the fresh clone | holds for the bound and the modelled mechanism |
| 9 | Attack on a rule as modelled, not on the implementation | attack | FORMAL (bounded) | base code verifies the tag before anything else and has no quarantine counter (`sct_protocol.py`, `packet.py`; `ROUND6_BOUNDS.md` section 4) | holds |
| 10 | Two-counter design fix | fail, never | design recommendation | `ROUND6_BOUNDS.md` section 4; not tested beyond variant B | worded as a design fix, not as a result |
| 11 | With the counter after verification no key-less frame reaches the victim's counters; by construction | holds, attacker | FORMAL (bounded) | `r6.f3b.B_count_after_verification.*` (7 states, no quarantine) | holds; "by construction" is stated |
| 12 | Confirm not later than single-stage if and only if A_f <= d (T_F - s_f) | if and only if | ANALYTICAL | `DELTA_DUTY_LOCKOUT.md` section 3, derivation steps (a) to (e); both directions follow from max(T_F, L) | holds under the stated model (called a condition, not a theorem) |
| 13 | Critical airtime, lockouts, condition up to SF9 at 10% | holds | ANALYTICAL | `vf2.duty.*` (computed from `lora.airtime_ms`); recomputed independently in `vf2_recompute_r6.py` for the airtime | holds |
| 14 | Preemption is a design recommendation | recommendation | design | `xsim_alert.cc` (R3Next: FIFO; policy r3a preempts) | holds |
| 15 | Enumeration: preemption adds no end state; stuck state only if every final-stage frame is lost | shows | FORMAL (bounded, untimed) | `vf2.preempt.*`; `tests/test_vf2_preempt.py` | holds for the model; time, duty and several vehicles are outside it (stated) |
| 16 | Micro-confirm delivery supported in the sixteen ns-3 cells only; trace groups zero by construction | supported | SIMULATED | `r6.r1.ns3.*`; `ROUND6_R1_MICRO.md` section 3 | holds (reworded in this run from "and on traces") |
| 17 | Micro-confirm lemmas; control attacked in both tools | cannot, attacked | FORMAL | `DELTA_FORMAL_RERUN.md` (6 of 6 verdicts equal to the stored run) | holds; assumption of lookup by (vehicle, provisional tag) added |
| 18 | Preregistration quoted 720 to 780 ms; the value is 112 ms (median 50) | validation | MEASURED_SOFTWARE | `r6.r2.held.mean_time_fixed_ms`, `median_time_fixed_ms`; `DECISIONS.md` 2026-11-16 | holds; the error is disclosed |
| 19 | Hypotheses kept as written; neither supported | supported | MEASURED_SOFTWARE | ledger V17 H-R6-2a and 2b not supported | holds |
| 20 | Executed instructions, timing and energy NOT_RUN | NOT_RUN | NOT_RUN | `r6.fp.emulated.*`, `r6.fp.energy.*` | holds |
| 21 | One gating rule | hold | ANALYTICAL | `DELTA_DUTY_LOCKOUT.md` section 5 | worded as a design rule, not a tested hypothesis |
| 22 | Load gate: SF7 passes and SF9 fails in the two cells run | fails | SIMULATED | `r6.b.check.*` (inflation 1.05 at SF7, 1.42 at SF9 against headroom 1.19 and 1.05) | holds |
| 23 | Negatives by layer are in the release archive; the ledger gives each verdict | supported | ANALYTICAL | `supplementary_full/` list in the supplement | holds |
| 24 | Threats: freshness of the 14-byte frame not modelled; layout is a proposal; duty model not evaluated | hold, no firmware | none | `FRAME_LAYOUT.md` section 8 rows F2, F6; `DELTA_DUTY_LOCKOUT.md` | holds |

## Other documents

| Document | Changed statement | Check |
|---|---|---|
| `paper/cover_letter.md` | Round 6 and ledger paragraphs | generated from keys by `scripts/vf2_cover.py`; micro airtime quoted over the two-stage alert, the negative extra airtime is not offered as a gain, the trace groups are not evidence, the 13-byte frame and the preregistration error are stated |
| `README.md` | Round 6 row, delta row, 0.901 sentence | same wording rules; the 0.901 sentence points to `DELTA_AUDIT_METHOD.md` |
| `docs/00_overview/PROJECT_STATUS.md` | totals sentence | now gives the 130-hypothesis ledger beside the 80 of the older verdict table |
| `docs/05_architecture/FRAME_LAYOUT.md` | all | rows labelled CODE or DESIGN; "design proposal" stated; no claim about firmware |
| `docs/03_results/DELTA_DUTY_LOCKOUT.md` | all | ANALYTICAL; "condition" and "proposition", never "theorem"; stored results do not transfer to an off-time region |
| `docs/03_results/DELTA_AUDIT_METHOD.md` | all | DESCRIPTIVE; row (d) labelled illustrative |

Words checked in all new and changed text: the banned words of `CLAUDE.md` (none, by `scripts/doc_style_check.py` and `scripts/pp_paper_audit.py`), the word "theorem" (none), and "if and only if" (only item 12 and the two items of the duty document, each derived both ways).

## Independent reviewer pass (D5.4)

A reviewer in a fresh context read the compiled main text and returned ten weakest points. Each was checked against the code and the results before any change; no document change alters a result.

| # | Point (short) | Action |
|---|---|---|
| 1 | Trace replay cannot test retry spacing | applied: the C6 finding and the conclusion now say the replay does not represent spacing and cannot show whether adaptive spacing adds anything at second scale |
| 2 | C1: operating point, causal wording, "behaves like a random one", acknowledgement stated as fact | applied: operating point stated; the fall is "consistent with leakage but also with removing easy events"; the random-re-split sentence now says it is a different population and not a test of leakage; the dataset authors' acknowledgement is marked as recorded by the author with pending wording. Intervals for the 1% recall are in the supplement audit table |
| 3 | Micro-confirm proofs assume the lookup the 7-byte frame lacks; ratchet not in a frame | applied: "the lookup by trial is outside the proof"; abstract says no frame field carries a ratchet step; the forgery years state the attacker's ceiling |
| 4 | Footprint against the flash estimate; linked image | applied in part: the text now names the built forest (the 15-tree headline forest, not the 16-bit compact variant of C3). The linked-flash figure stays, with the unused-function caveat required by the run plan |
| 5 | Boot counter truncation; label of the 8-case enumeration | applied in part: the 8-bit truncation is stated as outside the proof; the enumeration keeps the FORMAL label that the run plan prescribes, and the text says bounded and untimed |
| 6 | Three "earlier" figures; false-alarm load | applied: the figures are defined and the exclusion of false-alarm load is stated; "fixed rule" is defined where C8 introduces it |
| 7 | Lockout limit missing from the abstract; gating rule from two cells | applied: one clause in the abstract; the rule is called an interpolation from two simulated cells |
| 8 | 121 against 117; "preregistered" | applied: the Holm-family count is reconciled in one sentence; the abstract says author-preregistered |
| 9 | C2: records not independent; crash-test sensor locations | applied: one sentence in C2 |
| 10 | Undefined internal identifiers; order of C7 and C8; stuck state | applied in part: C7 now precedes C8 and the stuck provisional state is in the threats; the internal version and policy identifiers (V16, L11, r3t, r6m) are still used in a few places and are defined in the supplement ledger, which is left to the author's final read |
