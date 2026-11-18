r"""Round 7 P: patch paper/main.tex, paper/references.bib (idempotent). Every number is a macro of paper/generated/numbers_r7.tex (crashguard.r7_paper).

    python scripts/r7_patch_paper.py
"""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "paper"
main = (P / "main.tex").read_text(encoding="utf-8")
CRLF = "\r\n" in main
main = main.replace("\r\n", "\n")

if "numbers_r7.tex" not in main:
    main = main.replace(r"\input{generated/numbers.tex}", "\\input{generated/numbers.tex}\n\\input{generated/numbers_r7.tex}", 1)

C4_TEXT = r"""\textbf{Duty-budget exhaustion and the reserved budget (round 7).} An attacker that suppresses the acknowledgements makes the node spend airtime on retries. The shipped policy caps the flash at four tries and the confirm at four, so one fully suppressed event costs the node \RsevNodeAirSfSeven{} s at SF7 and \RsevNodeAirSfNine{} s at SF9, while the attacker, who only has to jam each 26-byte acknowledgement, spends at most \RsevAttackRatioSfSeven{} of that airtime (ANALYTICAL). Spending a trailing-hour allowance of 1\% takes \RsevNstarOneSfSeven{} such events in one hour at SF7 (one every \RsevGapSfSeven{} s) and \RsevNstarOneSfNine{} at SF9 (\RsevNstarTenSfSeven{} and \RsevNstarTenSfNine{} at 10\%). We did not measure how often a detector produces such a rate, so this is a regime and not a measured attack. Under a per-transmission off-time of 10\% the effect is immediate: the flash retries lock the sub-band and the confirm starts \RsevTtenOldDelaySfSeven{} s late at SF7 and \RsevTtenOldDelaySfNine{} s late at SF9. The reserved policy keeps an airtime reserve of four confirm copies and one micro-confirm, lets only the confirm, micro-confirm and cancel frames spend it, withdraws flash tries when the follow-up is due, and under an off-time admits a flash try only if its off-time ends before the follow-up is due. A bounded enumeration of \RsevFormRuns{} configurations per policy (FORMAL) finds no violation of the reserve rule and no late follow-up while the reserve is intact (\RsevFormCondRuns{} runs), and finds \RsevFormOldCond{} late runs for the shipped policy under the same bound; the guarantee is conditional, and it fails for the reserved policy once \RsevFormMinEarlier{} earlier events have spent the reserve. In the simulation at the load that exhausts the shipped policy at 1\%, the reserve of one event keeps the follow-up on time in \RsevAoneRateOneResSfSeven\%, \RsevAoneRateOneResSfEight\% and \RsevAoneRateOneResSfNine\% of the runs at SF7, SF8 and SF9 (the shipped policy: \RsevAoneRateOneOldSfSeven\%, \RsevAoneRateOneOldSfEight\% and \RsevAoneRateOneOldSfNine\%), so hypothesis H-R7-A1 (99\%) is not supported; it holds in every run at 10\% and under the off-time. A reserve sized for four events gives \RsevPostFourSfSeven\% at each of the three spreading factors (a post-run exploration, outside the preregistered family) and takes \RsevReserveFourShareSfSeven\% of the 1\% allowance at SF7 and \RsevReserveFourShareSfNine\% at SF9. Without an attack the cost is small except in one cell: on the measured traces (SF7, \RsevATwoNDevices{} devices in the high-loss group) delivery falls by \RsevATwoHTenDelta{} percentage points under the 10\% off-time, against a bound of 1, because the time reserve admits \RsevTtenFlashTriesSfSeven{} flash tries instead of four; under the hourly allowance the fall is \RsevATwoHHourDelta{} points, and the median time until an alert arrives does not change (hypothesis H-R7-A2 is not supported). Earlier work on LoRaWAN energy depletion \cite{R7Mikhaylov2019,R7Nafees2020,R7EdaLora2026} concerns battery energy and proposes no reserve for the follow-up frame of an alert; the full text of the attack on confirmed transmission of \cite{R7MacDos2023} was not read.

\textbf{Unlinkable pseudonymous ids (round 7).} In the layout the vehicle id, the boot counter and the alert counter are in clear, so an observer can link all alerts of a vehicle. The design replaces the id by a pseudonym, the leading $L$ bytes of HMAC-SHA256 under the per-vehicle key of a label, the boot counter and the alert counter (the sequential scheme of \cite{R7Pelissier2024} with a keyed function), removes boot and counter from the clear (the base recovers them from the window entry that matches), encrypts the position and payload, and lets the tag cover boot and counter as unsent associated data. The base keeps a window of the next 16 pseudonyms per vehicle, finds the vehicle through a hash index, and applies the boot-counter rule, the seen-set and the per-vehicle quarantine to the resolved id; a frame that does not resolve or fails the tag triggers only cell-level rate limiting. In ProVerif the diff-equivalence holds for two alerts and for an unbounded number of alerts: a network attacker that listens, replays and injects cannot tell two alerts of one vehicle from two alerts of two vehicles. The fixed-id design fails with a trace, and so does a variant that sends the boot counter in clear (FORMAL; H-R7-B3 supported). The earlier lemmas hold with the pseudonym: authenticity, unique ids with the boot counter, micro-confirm binding with the index and no framing by the quarantine counter in ProVerif, and the freshness, anti-replay and reboot lemmas in Tamarin (each run at most \RsevTamExecS{} s; the injective form of the no-framing lemma is not proved). Resolving a frame takes at most \RsevBoneWorstUs{} microseconds in Python and \RsevBoneCUs{} in C for 1,000 vehicles and a window of 16 (MEASURED\_SOFTWARE; H-R7-B1 supported); the frame that follows a reboot costs \RsevBoneResyncMs{} ms (a linear scan). The pseudonym equals an entry of another vehicle's window with probability \RsevBtwoLTwo{} per frame at the 2 bytes of the flash and \RsevBtwoLFour{} at the 4 bytes of the alert, above the bound of $10^{-6}$ (H-R7-B2 is not supported; \RsevBtwoLMeet{} bytes would meet it). The tag decides a collision, so it costs a tag check and not a wrong attribution; without the counter in the tag, two entries of one vehicle with equal pseudonyms desynchronised the window in our C test, which is why the tag covers it. Unlinkable ids do not hide position, timing or the radio fingerprint, and an attacker that holds a vehicle key is outside the model; responders get the position from the base, not from the air. Frame sizes do not change; a 16-byte authentication tag on the alert would add \RsevAeadExtraSfSeven{} ms at SF7 and \RsevAeadExtraSfNine{} ms at SF9. The routine takes \RsevFpText{} bytes of code on the ESP32 target (compile only) and \RsevFpStack{} bytes of stack on its deepest call path. Against \cite{R7Pelissier2024}, which argues unlinkability informally for a passive observer, this adds a formal model with an active attacker and the checks together with replay protection and quarantine.

"""
C5_TEXT = r"""\textbf{Reserve and gating rule (round 7).} The queue above is the shipped policy. With the reserved-budget policy of Section~\ref{sec:c4} the flash is a low-priority frame: under the hourly allowance it is sent only while the reserve stays intact, and under a per-transmission off-time only while its off-time ends before the confirm is due, so the lockout of the previous paragraph cannot delay the confirm. The link-aware gating rule re-derived with the reserve keeps both gates: the load gate does not depend on the reserve, and the lockout gate is enforced by the node for each event (descriptive, H-R7-A3). The spreading factor at which the two-stage alert is enabled stays SF7. Under the off-time the reserve admits \RsevTtenFlashTriesSfSeven{}, \RsevTtenFlashTriesSfEight{} and \RsevTtenFlashTriesSfNine{} flash tries at SF7, SF8 and SF9 and none from SF10.

"""
REL_TEXT = r"""\emph{Privacy and availability (round 7).} \cite{R7Pelissier2022} shows that devices are re-identified across address changes by linking messages. \cite{R7Pelissier2024} proposes resolvable and sequential pseudonyms in place of the device address, with an informal argument against a passive observer, a window of pre-generated pseudonyms and replay handled by the frame counter; it has no formal model and does not discuss misbehaving devices. On availability, \cite{R7Mikhaylov2019} and \cite{R7Nafees2020} show energy depletion by jamming and retransmission, \cite{R7EdaLora2026} adds replay, \cite{R7Dossa2025} measures reactive jamming without a defence, \cite{R7Suciu2019} defends Class B beacons by authenticated preambles, and \cite{R7BlindSpot2025} and \cite{R7MacDos2023} study selective jamming and attacks on confirmed transmission. None of the papers opened gives a reserve for the follow-up frame of an alert. The supplement lists the searches; paywalled items were read at abstract level only.

"""

if "Duty-budget exhaustion and the reserved budget" not in main:
    main = main.replace("\\subsection{C5: two-stage alert}", C4_TEXT + "\\subsection{C5: two-stage alert}", 1)
if "Reserve and gating rule (round 7)" not in main:
    anchor = "\\begin{figure}[t]\\centering\\includegraphics[width=\\columnwidth]{figures/pp_r3.pdf}"
    assert anchor in main
    main = main.replace(anchor, C5_TEXT + anchor, 1)
if "Privacy and availability (round 7)" not in main:
    main = main.replace("\\section{System architecture and methods}", REL_TEXT + "\\section{System architecture and methods}", 1)
old4 = "and a quarantine rule whose per-vehicle counter must follow tag verification."
if old4 in main and "reserved-budget retry policy" not in main:
    main = main.replace(old4, "and a quarantine rule whose per-vehicle counter must follow tag verification; and, added in round 7, a reserved-budget retry policy against acknowledgement suppression (a bounded model check; the preregistered load test is not supported) and a keyed pseudonym id with a symbolic unlinkability proof.", 1)
old5 = "with the detection-side gain measured on real pulses and the airtime cost bounded at spreading factor 7 (SF7) but not at SF9."
if old5 in main and "the reserve and the re-derived gating rule" not in main:
    main = main.replace(old5, old5[:-1] + ", and the reserve and the re-derived gating rule.", 1)


ABS_OLD = "do not transfer to a per-transmission off-time."
if ABS_OLD in main and "Round 7 adds" not in main:
    main = main.replace(ABS_OLD, ABS_OLD + " Round 7 adds a reserved airtime budget against acknowledgement suppression, which a bounded model check supports and a 99\% simulation target does not (not supported at a 1\% allowance), and a keyed pseudonym id with a symbolic unlinkability proof; \RsevSupported{} of \RsevHypotheses{} preregistered round-7 hypotheses are supported.", 1)

(P / "main.tex").write_text(main.replace("\n", "\r\n") if CRLF else main, encoding="utf-8")

bib = (P / "references.bib").read_text(encoding="utf-8")
ENTRIES = r"""
@inproceedings{R7Pelissier2024,
  author = {P{\'e}lissier, Samuel and Aalmoes, Jan and Mishra, Abhishek Kumar and Cunche, Mathieu and Roca, Vincent and Donsez, Didier},
  title = {Privacy-Preserving Pseudonyms for {LoRaWAN}},
  booktitle = {Proceedings of the 17th {ACM} Conference on Security and Privacy in Wireless and Mobile Networks ({WiSec} '24)},
  year = {2024}, pages = {14--19},
  doi = {10.1145/3643833.3656120},
  note = {full text read (HAL copy)}
}

@inproceedings{R7Pelissier2022,
  author = {P{\'e}lissier, Samuel and Cunche, Mathieu and Roca, Vincent and Donsez, Didier},
  title = {Device re-identification in {LoRaWAN} through messages linkage},
  booktitle = {Proceedings of the 15th {ACM} Conference on Security and Privacy in Wireless and Mobile Networks ({WiSec} '22)},
  year = {2022},
  doi = {10.1145/3507657.3528556},
  note = {full text opened (HAL copy)}
}

@misc{R7Dossa2025,
  author = {Dossa, Amavi and Burg, Andreas and Amhoud, El Mehdi},
  title = {Impact of Reactive Jamming Attacks on {LoRaWAN}: a Theoretical and Experimental Study},
  howpublished = {arXiv:2501.18339},
  year = {2025},
  note = {preprint; full text read}
}

@misc{R7Suciu2019,
  author = {Suciu, Ioana and Pacho, Jose Carlos and Bartoli, Andrea and Vilajosana, Xavier},
  title = {Authenticated Preambles for Denial of Service Mitigation in {LPWANs}},
  howpublished = {arXiv:1904.08179},
  year = {2019},
  note = {preprint; full text opened}
}

@inproceedings{R7Mikhaylov2019,
  author = {Mikhaylov, Konstantin and Fujdiak, Radek and Pouttu, Ari and Miroslav, V. and Malina, Lukas and Mlynek, Petr},
  title = {Energy Attack in {LoRaWAN}: Experimental Validation},
  booktitle = {Proceedings of the 14th International Conference on Availability, Reliability and Security ({ARES})},
  year = {2019},
  doi = {10.1145/3339252.3340525},
  note = {abstract read; its attack as summarised in the full text of Dossa et al.}
}

@misc{R7Nafees2020,
  author = {Nafees, M. N. and Saxena, N. and Burnap, P. and Choi, B. J.},
  title = {Impact of Energy Consumption Attacks on {LoRaWAN}-Enabled Devices in Industrial Context},
  howpublished = {ACM, doi 10.1145/3372297.3420022},
  year = {2020},
  note = {abstract read; venue not verified}
}

@article{R7EdaLora2026,
  title = {Energy Depletion Attack for {LoRa}-Based Wireless Sensor Network},
  journal = {{IEEE} Internet of Things Journal},
  year = {2026},
  doi = {10.1109/jiot.2026.3713221},
  note = {abstract read; author names not verified}
}

@article{R7MacDos2023,
  title = {Novel Denial-of-Service Attacks Against {LoRaWAN} on {MAC} Layer},
  journal = {{IEEE} Communications Letters},
  year = {2023},
  doi = {10.1109/lcomm.2023.3322119},
  note = {abstract read; author names not verified; full text not read}
}

@inproceedings{R7BlindSpot2025,
  title = {{BlindSpot}: Efficient Single-Node Selective Jamming for {LoRaWAN}},
  year = {2025},
  doi = {10.1145/3734477.3734724},
  note = {abstract read; venue and author names not verified}
}
"""
if "R7Pelissier2024" not in bib:
    (P / "references.bib").write_text(bib.rstrip("\n") + "\n" + ENTRIES, encoding="utf-8")
print("patched")
