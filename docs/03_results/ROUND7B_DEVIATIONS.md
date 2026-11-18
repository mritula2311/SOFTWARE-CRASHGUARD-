# Round 7b deviations from the registered plans

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Every deviation of round 7 and round 7b from the registered plans, with its effect. |
| Evidence labels used | SIMULATED, NOT_RUN |
<!-- header:end -->

| No. | Where | Deviation | Effect |
|---:|---|---|---|
| 1 | Round 7, base | Round 7 branched from the head of `final2`, not from `submit-v3.1`: that tag does not exist (round 7b checked: no tag, no commit of the close-out prompt). `submit-v3` differs from the head of `final2` by two documents | none on a result; the close-out items that were missing were applied in round 7b (G0) |
| 2 | Round 7, A bounded check | The enumeration used bounds that differ from the V18 text: allowance 16 to 40 units, a window of 30 steps, at most 2 earlier events (V18 text: 24 to 60 units, at most 3 earlier events). An earlier run with a window of 10 steps was too short for earlier events to share a window, so the unconditional form could not fail; it was replaced before anything was reported | run 1 (window 10): no result reported. Run 2 (reported in round 7): 1,139,264 configurations per policy, Invariant 1 and the conditional Invariant 2 hold, the one-event reserve fails the unconditional form only with 2 earlier events. Round 7b (V19) adds a third enumeration with allowances 40, 44, 48, a window of 70 steps and up to 5 earlier events |
| 3 | Round 7, A1.5 | The ns-3 ACK-drop hook was cut: the ns-3 policy files are frozen, so the attack was simulated with the event engine `r7_engine` (checked draw for draw against `r3_event` and `micro_event`), not in ns-3 | the A1 results are SIMULATED by the engine; ns-3 is NOT_RUN for this item |
| 4 | Round 7, documents | `scripts/doc_style_check.py` skips `PREREGISTRATION_V18.md` because the file is frozen at its committed SHA-256 (its wording is not edited after the runs); V19 is not skipped and passes the check | the style tool has not checked the wording of V18 (it may contain words that the rules ban; for example, V18 uses the banned word once for a transmission) |
| 5 | Round 7, B1 | The tag-coverage defect was found by the C benchmark, not by a model: at 2-byte pseudonyms two window entries of one vehicle can share a pseudonym, and a tag that does not cover the counter accepts the earlier entry (199,911 of 200,000 frames resolved). The tag now covers boot and counter as unsent associated data; the models were rerun | the fix is confined to the pseudonym variant (FRAME_LAYOUT.md section 10.3); the ProVerif and Tamarin results quoted are for the fixed design |
| 6 | Round 7b, G0 | The brief's "about 0.7 of a spreading-factor step" belongs to the 0 dBi case (1.85 dB). For the dipole case (4.00 dB) the same arithmetic gives 1.4 steps at the simulators' 2.8 dB per step; the paper uses the computed value | wording and key `r7b.g0.power.extra_margin_sf_steps` |
| 7 | Round 7b, V19 | Control F4 as written (the k = 1 policy violates the unconditional Invariant 2 with at most 3 earlier events) is not met: in the 70-step window the one-event reserve fails from 4 earlier events. The control works at the bound of 4 (k = 1 fails at an allowance of 40, k = 4 does not). The k = 4 policy fails from 5 earlier events (V19 expected 4) | reported as found in `ROUND7B_RESULTS.md`; no check was changed after the run |
| 8 | Round 7b, G3 | The round-7 report called the injective no-framing lemma "not proved". The exact status is a ProVerif trace of two base threads racing on the seen-set, plus the absence of any Tamarin quarantine model; a Tamarin model with an atomic seen-set was added and verifies both forms | the paper says the property holds with an atomic seen-set |
| 9 | Round 7b, V19 | The size of the reserve (four events) was chosen from round-7 data; the registered confirmation uses fresh seeds and unchanged thresholds | confirmation, not a blind test; stated in V19 section 0 and in the paper |
