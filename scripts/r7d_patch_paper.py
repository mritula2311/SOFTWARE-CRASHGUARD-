"""Round 7d: R-REACK in the C4 text and the limitations (idempotent). The old and new sentences are written to scripts/r7d_changes.json for the report."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAIRS = [
    (r"whereas a keyless replay of a captured valid frame can still be re-acknowledged unless the re-acknowledgement interval and a downlink budget are set (both are off by default), and the ns-3 gateway model does not check tags.",
     r"whereas a keyless replay of a captured valid frame is re-acknowledged each time and can consume the base's downlink budget unless two limits are on, the re-acknowledgement interval and the downlink budget. We state them as deployment requirement R-REACK, with the values of the replay-flood study: no re-acknowledgement of the same event sooner than the shortest legitimate retry spacing (\RsevdIntervalSeven{} s at SF7, \RsevdIntervalEight{} s at SF8, \RsevdIntervalNine{} s at SF9), and a downlink token bucket that refills at the \RsevdDutyPct\% duty cycle with a capacity of \RsevdCapacity{} s (it started at \RsevdInitial{} s in the study). With the limits off, \RsevdRate{} replays a second for \RsevdDuration{} s of one valid alert at SF7 drew \RsevdOffReacks{} re-acknowledgements and \RsevdOffAirtime{} s of airtime, the budget ran out and a genuine alert at 100 s was accepted but not acknowledged; with them on, \RsevdOnReacks{} and \RsevdOnAirtime{} s, and the genuine alert was acknowledged. The limits stop the starvation but not the waste (the replays still spent \RsevdOnShare\% of the starting budget; a stricter limit was not evaluated). The reference verifier has both limits off by default; a new reference configuration turns them on without touching any frozen file. The ns-3 gateway model does not check tags and has no such limit."),
    (r"and a keyless replay of a valid frame is re-acknowledged unless the base limits it. ",
     r"and a keyless replay of a valid frame is re-acknowledged and consumes downlink budget unless the base meets R-REACK. "),
]


def rw(path, fn):
    b = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in b
    s = fn(b.replace("\r\n", "\n"))
    path.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


def main_tex(s):
    for old, new in PAIRS:
        if new in s:
            continue
        assert old in s, old[:80]
        s = s.replace(old, new, 1)
    (ROOT / "scripts" / "r7d_changes.json").write_text(json.dumps(PAIRS, indent=1), encoding="utf-8")
    return s


rw(ROOT / "paper" / "main.tex", main_tex)
print("ok")
