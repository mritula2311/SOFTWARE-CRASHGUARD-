r"""Round 7 P (second patch, idempotent): ledger row, negative-results rows and wording in paper/main.tex."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "paper" / "main.tex"
raw = P.read_bytes().decode("utf-8")
crlf = "\r\n" in raw
t = raw.replace("\r\n", "\n")

row = r"Round 6 (V17) & \LgFPre{} & \LgFRun{} & \LgFSupp{} & \LgFNot{} & \LgFPartly{} & \LgFNotRun{}\\" + "\n"
new_row = r"Round 7 (V18) & \LgGPre{} & \LgGRun{} & \LgGSupp{} & \LgGNot{} & \LgGPartly{} & \LgGNotRun{}\\" + "\\midrule\n"
if "Round 7 (V18)" not in t:
    assert row.rstrip("\n") + "\\midrule\n" in t
    t = t.replace(row.rstrip("\n") + "\\midrule\n", row + new_row, 1)
t = t.replace("(V1 to V17, with addenda)", "(V1 to V18, with addenda; H-R7-A3 of V18 is descriptive and has no verdict)")

neg = (
    r"V18 & Reserved airtime budget under ACK suppression (H-R7-A1) & follow-up within D\_max in at least 99\% of runs at the load that exhausts the shipped policy & \RsevAoneRateOneResSfSeven\%, \RsevAoneRateOneResSfEight\% and \RsevAoneRateOneResSfNine\% at SF7, SF8, SF9 under a 1\% allowance (SIMULATED); every run at 10\% and under the off-time & earlier follow-ups spend the reserve; a reserve for four events restores 100\% (post-run, not in the family)\\" + "\n"
    r"V18 & Benign cost of the reserve (H-R7-A2) & delivery down at most 1 point on the measured traces & down \RsevATwoHTenDelta{} points in the high-loss group under a 10\% off-time (TRACE\_DRIVEN); median time unchanged & the time reserve admits \RsevTtenFlashTriesSfSeven{} flash tries instead of four at SF7\\" + "\n"
    r"V18 & Pseudonym collisions (H-R7-B2) & collision probability at most $10^{-6}$ per frame at 1,000 vehicles and a window of 16 & \RsevBtwoLTwo{} at 2 bytes and \RsevBtwoLFour{} at 4 bytes (ANALYTICAL) & the bound needs \RsevBtwoLMeet{} bytes; the tag decides a collision\\" + "\n"
)
anchor = "V16 & Mirror-flip detection (L11, own family)"
if "V18 & Reserved airtime budget" not in t:
    assert anchor in t
    t = t.replace(anchor, neg + anchor, 1)
P.write_bytes((t.replace("\n", "\r\n") if crlf else t).encode("utf-8"))
print("patched")
