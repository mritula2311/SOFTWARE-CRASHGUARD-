"""Round 7b G1.3, G2.3, G3, G5: paper text (idempotent). Rewrites the A claim (the attack class is known), reports k = 1 and k = 4, the quarantine lemma status, and the design notes."""

# ruff: noqa: E402  (the guard below runs before the imports on purpose)
raise SystemExit('r7b_patch_paper.py is a one-time script that was already applied in round 7b. Running it again would append the round-7b block to the cover letter a second time. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rw(path: Path, fn) -> None:
    b = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in b
    s = fn(b.replace("\r\n", "\n"))
    path.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


def sub(s: str, old: str, new: str) -> str:
    assert old in s, old[:70]
    return s.replace(old, new, 1)


A_PARA_START = r"\textbf{Duty-budget exhaustion and the reserved budget (round 7)."
RELATED_OLD = r"On availability, \cite{R7Mikhaylov2019} and \cite{R7Nafees2020} show energy depletion by jamming and retransmission, \cite{R7EdaLora2026} adds replay, \cite{R7Dossa2025} measures reactive jamming without a defence, \cite{R7Suciu2019} defends Class B beacons by authenticated preambles, and \cite{R7BlindSpot2025} and \cite{R7MacDos2023} study selective jamming and attacks on confirmed transmission. None of the papers opened gives a reserve for the follow-up frame of an alert."
RELATED_NEW = r"On availability, the attack class is known. \cite{R7Mikhaylov2019} and \cite{R7Nafees2020} show energy depletion by jamming and retransmission, \cite{R7EdaLora2026} adds replay, \cite{R7Dossa2025} measures reactive jamming without a defence, \cite{R7Suciu2019} defends Class B beacons by authenticated preambles, \cite{R7BlindSpot2025} studies selective jamming, and \cite{R7MacDos2023} propose two denial-of-service attacks on the confirmed transmission of LoRaWAN that rely on its Aloha access and its duty-cycle limit (we read the abstract only: the mechanism, whether it drains the duty budget through suppressed acknowledgements, and whether it has a defence are not known to us; the full text is closed access). We treat acknowledgement suppression against a duty budget as a known class and claim none of it. None of the papers opened gives a reserve for the follow-up frame of a two-stage alert."


def main_tex(s: str) -> str:
    if "RsevbFourRateSfSeven" in s:
        return s
    s = sub(s, r"\input{generated/numbers_r7b.tex}", "\\input{generated/numbers_r7b.tex}")  # present after G0.2
    s = sub(s, RELATED_OLD, RELATED_NEW)
    # abstract
    old = r"Round 7 adds a reserved airtime budget against acknowledgement suppression, which a bounded model check supports and a 99\% simulation target does not (not supported at a 1\% allowance), and a keyed pseudonym id with a symbolic unlinkability proof; \RsevSupported{} of \RsevHypotheses{} preregistered round-7 hypotheses are supported."
    new = r"Round 7 adds a reserved airtime budget for the follow-up frame of the two-stage alert against acknowledgement suppression, a known attack class. The reserve for one event failed its preregistered 99\% target at a 1\% allowance; a reserve for four events, preregistered afterwards and tested on fresh seeds, meets it, at a benign delivery cost in the high-loss group under a per-transmission off-time that exceeds the 1-point bound. Round 7 also adds a keyed pseudonym id with a symbolic unlinkability proof."
    s = sub(s, old, new)
    # contributions
    old = r"added in round 7, a reserved-budget retry policy against acknowledgement suppression (a bounded model check; the preregistered load test is not supported) and a keyed pseudonym id with a symbolic unlinkability proof."
    new = r"added in rounds 7 and 7b, a reserved-budget retry policy for the follow-up frame of a two-stage alert (the attack class is known; the contribution is the defence, a bounded model check with a control, and preregistered results: the one-event reserve failed, the four-event reserve passed on fresh seeds) and a keyed pseudonym id with a symbolic unlinkability proof."
    s = sub(s, old, new)
    # C4 paragraph: replace from the start to the end of that line
    i = s.index(A_PARA_START)
    j = s.index("\n", i)
    newpara = (
        r"\textbf{Duty-budget exhaustion and the reserved budget (rounds 7 and 7b).} An attacker that suppresses the acknowledgements makes the node spend airtime on retries. This attack class is known: energy-depletion and denial-of-service attacks on LoRaWAN, including attacks on confirmed transmission that rely on the duty-cycle limit \cite{R7Mikhaylov2019,R7Nafees2020,R7EdaLora2026,R7MacDos2023}, are prior work, and we do not claim the attack. What this paper adds is the defence for a two-stage alert, a bounded model check with a control, and preregistered results under India's rules (the 10\% duty cycle is the main deployment regime; the 1\% allowance is the stricter case). "
        r"The shipped policy caps the flash at four tries and the confirm at four, so one fully suppressed event costs the node \RsevNodeAirSfSeven{} s at SF7 and \RsevNodeAirSfNine{} s at SF9, while the attacker, who only has to jam each 26-byte acknowledgement, spends at most \RsevAttackRatioSfSeven{} of that airtime (ANALYTICAL). Spending a trailing-hour allowance of 1\% takes \RsevNstarOneSfSeven{} such events in one hour at SF7 (one every \RsevGapSfSeven{} s) and \RsevNstarOneSfNine{} at SF9 (\RsevNstarTenSfSeven{} and \RsevNstarTenSfNine{} at 10\%). We did not measure how often a detector produces such a rate, so this is a regime and not a measured attack. Under a per-transmission off-time of 10\% the effect is immediate: the flash retries lock the sub-band and the confirm starts \RsevTtenOldDelaySfSeven{} s late at SF7 and \RsevTtenOldDelaySfNine{} s late at SF9. "
        r"The reserved policy keeps an airtime reserve, lets only the confirm, micro-confirm and cancel frames spend it, withdraws flash tries when the follow-up is due, and under an off-time admits a flash try only if its off-time ends before the follow-up is due. "
        r"\emph{Registration V18 (k = 1).} The reserve for one event (four confirm copies and one micro-confirm) was preregistered with a 99\% target. In the simulation at the load that exhausts the shipped policy at 1\%, it keeps the follow-up on time in \RsevAoneRateOneResSfSeven\%, \RsevAoneRateOneResSfEight\% and \RsevAoneRateOneResSfNine\% of the runs at SF7, SF8 and SF9 (the shipped policy: \RsevAoneRateOneOldSfSeven\%, \RsevAoneRateOneOldSfEight\% and \RsevAoneRateOneOldSfNine\%), so hypothesis H-R7-A1 is not supported; it holds in every run at 10\% and under the off-time. Earlier follow-ups spend the reserve. "
        r"\emph{Registration V19 (k = 4).} After that run, a post-run sweep showed that a reserve for four events reaches 100\%. Because this size was chosen from the round-7 data, we preregistered it (V19) and tested it on fresh seeds, with the thresholds of V18 unchanged; this is a confirmation and not a blind test. H-R7b-1 is supported: the follow-up is on time in at least \RsevbWorstLower\% of runs (lower 95\% limit) in all \RsevbCellsFeasible{} cells (SF7 to SF9; the 1\% and 10\% allowances and the 10\% off-time; p = \RsevbPOne{}), and at the 1\% allowance the reserve for one, two, three and four events gives \RsevbOneRateSfSeven, \RsevbTwoRateSfSeven, \RsevbThreeRateSfSeven and \RsevbFourRateSfSeven\% at SF7 (descriptive). The reserve for four events takes \RsevReserveFourShareSfSeven\% of the 1\% allowance at SF7 and \RsevReserveFourShareSfNine\% at SF9. H-R7b-2 is not supported: without an attack, delivery on the measured traces falls by \RsevbBenignHTenDelta{} percentage points in the high-loss group under the 10\% off-time (\RsevbBenignFailCells{} of \RsevbBenignCells{} cells, both schemes), against a bound of 1, because the time reserve admits \RsevTtenFlashTriesSfSeven{} flash tries instead of four; under the hourly allowance the fall is \RsevbBenignHHourDelta{} points, and the median time to an alert stays within the 10\% bound in every cell. The fall does not change with the size of the reserve (descriptive curve for one to four events), because the replay runs each event with a fresh duty state; a cost that grows with the reserve under sustained load was not run. "
        r"\emph{Bounded model check.} An enumeration with up to five earlier events (FORMAL, bounded; the abstraction has a window of 70 steps and three allowances) finds no violation of the reserve rule and no late follow-up while the reserve is intact for the reserves of one and four events, and \RsevbFormOldCond{} late runs for the shipped policy; the guarantee is conditional on the reserve being intact: the reserve for one event fails with \RsevbFormMOneFirst{} earlier events, and the reserve for four events with \RsevbFormMFourFirst{}. An earlier enumeration with a window of 30 steps and at most two earlier events (the bounds of the V18 run, after a first attempt with a window of 10 steps that was too short to show a limit) found the one-event reserve failing with \RsevFormMinEarlier{} earlier events. The models are abstractions of the queue, not of the radio."
    )
    s = s[:i] + newpara + s[j:]
    # quarantine / pseudonym lemma status
    old = r"the freshness, anti-replay and reboot lemmas in Tamarin (each run at most \RsevTamExecS{} s; the injective form of the no-framing lemma is not proved)."
    new = r"the freshness, anti-replay and reboot lemmas in Tamarin (each run at most \RsevTamExecS{} s). For the quarantine, ProVerif proves the non-injective no-framing form and reports the injective form false with a trace of two base threads that both read the seen-set before either inserts; a Tamarin model in which the seen-set check and insert are one step verifies both forms, and the controls without a seen-set and with a strike before the tag check fail as expected. So the quarantine rule keeps its no-framing property with pseudonyms if the base applies the seen-set atomically, and not otherwise (a separate small model; the window advance and reboots are not in it)."
    s = sub(s, old, new)
    # pseudonym design notes (G5)
    old = r"the frame that follows a reboot costs \RsevBoneResyncMs{} ms (a linear scan)."
    new = r"the frame that follows a reboot costs \RsevBoneResyncMs{} ms (a linear scan; a table of the pseudonyms of the next three boot values for every vehicle would turn it into a lookup: \RsevbRebootEntries{} entries and about \RsevbRebootBytes{} bytes for 1,000 vehicles, rebuilt for one vehicle after each match; a design note, ANALYTICAL, not implemented)."
    s = sub(s, old, new)
    old = r"The tag decides a collision, so it costs a tag check and not a wrong attribution;"
    new = r"The tag decides a collision, so it costs one extra tag check and not a wrong attribution; at 5 bytes the probability is \RsevbCollFive{} per frame, below the bound, and the extra byte adds \RsevbExtraByteAckSeven{} ms to the acknowledgement at SF7 and \RsevbExtraByteAckNine{} ms at SF9 (none to the 97-byte alert at SF7 to SF9; ANALYTICAL; the verdict of H-R7-B2 is unchanged);"
    s = sub(s, old, new)
    # negative-results rows after the V18 A2 row
    marker = r"V18 & Pseudonym collisions (H-R7-B2)"
    rows = (r"V19 & Reserve for four events under ACK suppression (H-R7b-1) & follow-up on time in at least 99\% of runs, every cell, fresh seeds & lower limit \RsevbWorstLower\% in \RsevbCellsFeasible{} cells (SIMULATED); supported & chosen from round-7 data, so a confirmation and not a blind test\\" "\n"
            r"V19 & Benign cost of the four-event reserve (H-R7b-2) & delivery down at most 1 point and median time up at most 10\% on the traces, fresh start points & down \RsevbBenignHTenDelta{} points in the high-loss group under a 10\% off-time (TRACE\_DRIVEN); not supported & the time reserve does not depend on the size of the reserve\\" "\n")
    s = sub(s, marker, rows + marker)
    return s


def cover(s: str) -> str:
    if "round 7b" in s:
        return s
    s = s.rstrip("\n")
    return s + "\n\n**Round 7b.** The attack of round 7 (acknowledgement suppression against a duty budget) is a known class; the abstract of Chen, Ben-Othman and Mokdad (IEEE Communications Letters 2023) describes denial-of-service attacks on confirmed transmission that use the duty-cycle limit, and the paper claims the defence, the bounded model check and the preregistered results, not the attack. The reserve for one event failed its 99% target at a 1% allowance; a reserve for four events, preregistered afterwards (V19) and tested on fresh seeds, meets it in all nine cells, and its benign delivery cost in the high-loss trace group under a per-transmission off-time (2.4 points) exceeds the 1-point bound. The quarantine lemma with pseudonyms holds in its injective form only if the base applies the seen-set atomically (Tamarin model; ProVerif reports a race). Transmit power: the conservative reading is used, so the link results are an optimistic bound on margin by up to 4 dB.\n"


def highlights(s: str) -> str:
    return s.replace("duty reserve has limits", "four-event duty reserve tested") if "duty reserve has limits" in s else s


rw(ROOT / "paper" / "main.tex", main_tex)
rw(ROOT / "paper" / "cover_letter.md", cover)
rw(ROOT / "paper" / "highlights.md", highlights)
print("ok")
