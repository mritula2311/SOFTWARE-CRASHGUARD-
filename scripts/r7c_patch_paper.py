"""Round 7c L and K: paper text (idempotent). Every replaced sentence is logged to docs/04_audits/ROUND7C_REPORT.md by scripts/r7c_changes.py from the OLD and NEW pairs defined here."""

# ruff: noqa: E402  (the guard below runs before the imports on purpose)
raise SystemExit('r7c_patch_paper.py is a one-time script that was already applied in round 7c. Running it again would stop with an assertion error, because the sentence it looks for was replaced in round 7d. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
THESIS = (ROOT / "scripts" / "r7c_thesis_sentence.txt").read_text(encoding="utf-8").strip() if (ROOT / "scripts" / "r7c_thesis_sentence.txt").exists() else ""

RULE = (r"Where a paragraph says that nothing was found, it means: no work found in the sources checked (IEEE Xplore, OpenAlex, Crossref, DOAJ, publisher pages; "
        r"Google Scholar blocked automated queries and was not searched).")

PAIRS = [
    # L1 introduction
    (r"Of these, one was read in full and one in abstract; they describe prototypes and demonstrations; the full text does not study an authenticated acknowledgement or a duty budget, and the abstract mentions no delivery statistics, security analysis or formal check. The other two were read at record level only. LoRa security work, in turn, is mostly not about crash alerts.",
     r"Of these, one was read in full and three in abstract (the publisher page of one was blocked to scripts); they describe prototypes, simulations and field tests. Carneiro et al. evaluate packet delivery ratio, coverage and latency in ns-3, so delivery statistics exist for LoRa crash alerting. In the text read, none states an authenticated acknowledgement, a security analysis or a formal check, and none studies a duty budget; we found no such work in the sources checked (see Section~\ref{sec:related}). LoRa security work, in turn, is mostly not about crash alerts."),
    # L6 absence rule, search paragraph
    (r"Where a paragraph says that nothing was found, it means: no open-access journal article from 2021 onwards was found in the sources checked (DOAJ, OpenAlex, Crossref and the publisher pages opened; Google Scholar and Scopus not searched).",
     RULE),
    (r"No journal article from 2021 onwards was found in the sources checked that audits duplicates in a crash-pulse benchmark.",
     r"We found no work in the sources checked that audits duplicates in a crash-pulse benchmark."),
    (r"In the sources checked no journal article gives the range and rate that crash delta-V needs,",
     r"We found no work in the sources checked that gives the range and rate that crash delta-V needs,"),
    (r"No journal article was found on provisional-then-confirmed crash alerts.",
     r"We found no work in the sources checked on provisional-then-confirmed crash alerts."),
    (r"no replay of retry policies on public traces was found.",
     r"we found no work in the sources checked that replays retry policies on public traces."),
    (r"We found no work in the sources checked on provisional-then-confirmed crash alerts.",
     r"An automatic crash-alert unit for vehicle classes outside the Indian AIS-140 mandate reports drop-test and road-course sensitivity over a GSM link \cite{Thangamani2026_icces}, and a LoRa vehicle-to-vehicle system broadcasts explicit event-termination packets to end channel occupancy after an event report \cite{AlShammaa2025_jcomss}. We found no work in the sources checked on provisional-then-confirmed crash alerts."),
    # L2 formal verification
    (r"Formal analyses cover LoRaWAN key establishment \cite{wesemeyer2020}, the protocol in a process-algebra tool \cite{dong2024}, user authentication for critical applications \cite{Jabbari2022_tii} and hash-chain key management \cite{Hakeem2021_s2117583}.",
     r"LoRa and LoRaWAN protocols have been formally analysed: key establishment in Tamarin \cite{wesemeyer2020}, the protocol in a process-algebra tool \cite{dong2024}, a user authentication protocol with a real-or-random proof and ProVerif and AVISPA checks \cite{Jabbari2022_tii}, and hash-chain key management \cite{Hakeem2021_s2117583}. Those analyses cover key establishment and authentication. The formal claims of this paper cover crash-alert frames only: the acknowledgement binding, freshness, reboot, quarantine, the two-stage confirm and unlinkability with accountability."),
    # L3 related work, availability
    (r"\cite{R7BlindSpot2025} studies selective jamming, and \cite{R7MacDos2023} propose two denial-of-service attacks on the confirmed transmission of LoRaWAN that rely on its Aloha access and its duty-cycle limit (we read the abstract only: the mechanism, whether it drains the duty budget through suppressed acknowledgements, and whether it has a defence are not known to us; the full text is closed access). We treat acknowledgement suppression against a duty budget as a known class and claim none of it. None of the papers opened gives a reserve for the follow-up frame of a two-stage alert.",
     r"\cite{R7BlindSpot2025} studies selective jamming, and Chen et al.~\cite{R7MacDos2023} propose two denial-of-service attacks on the confirmed transmission of LoRaWAN that exploit its Aloha access and its duty-cycle limit (we read the abstract of Chen et al. only: it gives no mechanism and the paper is closed access; the abstract of \cite{Kumar2026_siml} treats the same class as rogue nodes that use up the gateway's downlink airtime with confirmed uplinks, which we did not verify in the Chen text). \cite{R7EdaLora2026} forces retransmissions by jamming and replay to deplete the energy of the end device. On the defence side, \cite{Kumar2026_siml} detects rogue nodes and limits acknowledgements at the gateway. The thesis of Chen \cite{ChenThesis2024} (we read its Chapter VII) describes the same attack family: confirmed uplinks sent at a high rate to use up the gateway's downlink duty, a MAC-command variant that forces the acknowledgements to SF12, and a variant with a malicious application server; it counters them with a threshold and outlier detector and a graded denylist that finally blocks the acknowledgement to the detected nodes. These attacks aim at the gateway's downlink; the attack here aims at the node's uplink budget through suppressed acknowledgements, and the reserve is a node-side defence. These attacks and defences are known, and we claim none of them. This paper contributes the node-side reserved budget for the follow-up frame of a two-stage alert, a bounded model check with a control, and preregistered results under India's rules. We found no work in the sources checked that reserves node airtime for the follow-up frame of an alert."),
    # K2 ACK only after verification: one C4 sentence after the attack-class sentence
    (r"and we do not claim the attack. What this paper adds is",
     r"and we do not claim the attack. Nodes without keys cannot use up the base's downlink duty budget with confirmed frames, as in that attack class: in the reference base a frame whose tag fails gets no acknowledgement and is rejected before any state changes (cell-level rate limiting is the design for such frames), whereas a keyless replay of a captured valid frame can still be re-acknowledged unless the re-acknowledgement interval and a downlink budget are set (both are off by default), and the ns-3 gateway model does not check tags. What this paper adds is"),
    # K3 SisFall
    (r"the SisFall file is a Zenodo copy whose licence is the one stated on its record.",
     r"SisFall is available from its authors \cite{Sucerquia2017_sisfall}; it is not redistributed with this artefact because no data licence is stated (a Zenodo copy states CC BY 4.0 but names no creators, so we did not rely on it; see \texttt{scripts/fetch\_sisfall.md})."),
]
# threats to validity: one clause for K2
THREAT_OLD = r"\textbf{Regulation.} "
THREAT_NEW = r"\textbf{Base behaviour.} Acknowledgement only after the tag verifies, and an atomic seen-set check and insert, are properties of the reference base code and design requirements for a base server; no base server exists, the ns-3 gateway acknowledges every received frame, and a keyless replay of a valid frame is re-acknowledged unless the base limits it. "


def rw(path, fn):
    b = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in b
    s = fn(b.replace("\r\n", "\n"))
    path.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


def main_tex(s):
    done = []
    for old, new in PAIRS:
        done.append((old, new))  # the full list is always written, so the report has every pair
        if new in s:
            continue
        assert old in s, old[:80]
        s = s.replace(old, new, 1)
    if THREAT_NEW not in s:
        assert THREAT_OLD in s
        s = s.replace(THREAT_OLD, THREAT_NEW + THREAT_OLD, 1)
    done.append((THREAT_OLD, THREAT_NEW + THREAT_OLD))
    if done:
        (ROOT / "scripts" / "r7c_changes.json").write_text(json.dumps(done, indent=1), encoding="utf-8")
    return s


rw(ROOT / "paper" / "main.tex", main_tex)
print("ok")
