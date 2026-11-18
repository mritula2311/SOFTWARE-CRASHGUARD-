# Round 7d report

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-16 |
| Owner | Mritula S |
| Scope | Report of round 7d: the re-acknowledgement interval and downlink budget as deployment requirement R-REACK, values, reference configuration and changed sentences. |
| Evidence labels used | NOT_RUN |
| Abbreviations | ACK = acknowledgement frame |
<!-- header:end -->

No new experiment, no new hypothesis. Keys `r7d.*` only. Values come from the stored replay-flood study (`attacks.flood.*`); `crashguard.r7d_base` reruns that scenario with the reference configuration and checks that both the limits-off and the limits-on runs equal the stored keys (`r7d.reack.matches_stored_flood_off` and `_on` are 1). This is a regression of the reference code, not a new experiment.

## What was done

1. **R-REACK** written as a deployment requirement in `docs/05_architecture/FRAME_LAYOUT.md` section 12 (re-ACK interval and downlink budget, both required; values; flood results; reading) and in the C4 paragraph of `paper/main.tex`, and in the limitations clause.
2. **Values used:** re-ACK interval = `retry_interval_s(SF)` = alert airtime + 0.1 s + ACK airtime + 0.1 s: 0.43 s at SF7, 0.61 s at SF8, 0.94 s at SF9; downlink budget = token bucket refilling at the 10% duty cycle, capacity 360 s, 30 s at the start of the study.
3. **Limits off:** a replayed valid frame is re-acknowledged each time and consumes the base's downlink budget. In the stored flood (20 replays a second for 120 s, SF7): 679 re-ACKs, 41.9 s of airtime, 1,721 replays found the budget empty, a genuine alert at 100 s was accepted without an ACK.
4. **Limits on:** 266 re-ACKs, 16.4 s, budget left 25.4 s, the genuine alert acknowledged. The limits stop the starvation, not the waste: the replays still spent 55% of the starting budget. A stricter interval was not evaluated (NOT_RUN).
5. **Reference configuration:** `crashguard.r7d_base.reference_base(key, sf)`, a new module. `verifier.py` and every frozen file are unchanged; the default of `BaseVerifier` stays off, so the default does not meet R-REACK. The earlier flood study already built its limited base this way.

## Changed sentences of `paper/main.tex` (old and new)

**1. Old:** whereas a keyless replay of a captured valid frame can still be re-acknowledged unless the re-acknowledgement interval and a downlink budget are set (both are off by default), and the ns-3 gateway model does not check tags.

**New:** whereas a keyless replay of a captured valid frame is re-acknowledged each time and can consume the base's downlink budget unless two limits are on, the re-acknowledgement interval and the downlink budget. We state them as deployment requirement R-REACK, with the values of the replay-flood study: no re-acknowledgement of the same event sooner than the shortest legitimate retry spacing (\RsevdIntervalSeven{} s at SF7, \RsevdIntervalEight{} s at SF8, \RsevdIntervalNine{} s at SF9), and a downlink token bucket that refills at the \RsevdDutyPct\% duty cycle with a capacity of \RsevdCapacity{} s (it started at \RsevdInitial{} s in the study). With the limits off, \RsevdRate{} replays a second for \RsevdDuration{} s of one valid alert at SF7 drew \RsevdOffReacks{} re-acknowledgements and \RsevdOffAirtime{} s of airtime, the budget ran out and a genuine alert at 100 s was accepted but not acknowledged; with them on, \RsevdOnReacks{} and \RsevdOnAirtime{} s, and the genuine alert was acknowledged. The limits stop the starvation but not the waste (the replays still spent \RsevdOnShare\% of the starting budget; a stricter limit was not evaluated). The reference verifier has both limits off by default; a new reference configuration turns them on without touching any frozen file. The ns-3 gateway model does not check tags and has no such limit.

**2. Old:** and a keyless replay of a valid frame is re-acknowledged unless the base limits it. 

**New:** and a keyless replay of a valid frame is re-acknowledged and consumes downlink budget unless the base meets R-REACK. 

## Limits

The ns-3 gateway model and the formal models have no re-ACK limit and are unchanged. The values are those of a simulation of the reference code; there is no base server. The superseded sentence was written by `scripts/r7c_patch_paper.py`; that script is not to be rerun after this change (its idempotence check looks for the old text).

## Checks

Fresh-clone checks and the tag `submit-v6.1`: see `ROUND7C.md` rows D3 and D4.
