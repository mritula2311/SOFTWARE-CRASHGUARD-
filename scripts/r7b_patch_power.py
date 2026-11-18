"""Round 7b G0.2: transmit-power wording (idempotent). Conservative reading: the 10 dB extra loss is path margin, so a compliant dipole node transmits at most 10 dBm."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def rw(path: Path, fn) -> None:
    b = path.read_bytes().decode("utf-8")
    crlf = "\r\n" in b
    s = fn(b.replace("\r\n", "\n"))
    path.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))


def main_tex(s: str) -> str:
    if "RsevbPowerMaxDipole" in s:
        return s
    s = s.replace(r"\input{generated/numbers_r7.tex}", "\\input{generated/numbers_r7.tex}\n\\input{generated/numbers_r7b.tex}", 1)
    a = r"14 dBm transmit power with a 10 dB extra loss in the link budget (the radiated power must stay within 10 mW e.r.p.~\cite{gsr347})"
    assert a in s
    s = s.replace(a, r"14 dBm transmit power with a 10 dB extra loss in the link budget. We read the 10 dB as path margin, not as transmit-side loss: a compliant dipole node radiates at most \RsevbPowerMaxDipole{} dBm (10 mW e.r.p.~\cite{gsr347}), so the stored link results assume up to \RsevbPowerExtraDb{} dB more margin than such a node has, about \RsevbPowerSfSteps{} spreading-factor steps, and are an optimistic bound on link margin. The protocol, security and duty-cycle results do not depend on transmit power", 1)
    b = r"The simulations use 14 dBm with a 10 dB extra loss: if that loss is transmit-side the radiated power is \IndiaErpLumped{} dBm, inside the 10 mW limit; if the radio delivers 14 dBm to a 0 dBi antenna, the limit needs a reduction of \IndiaReduceZero{} dB, which lowers the link margin by the same amount (about \IndiaSfStep{} of a spreading-factor step; an analytical note, not simulated)."
    assert b in s
    s = s.replace(b, r"The simulations use 14 dBm with a 10 dB extra loss. We take the conservative reading, that the 10 dB is path margin: a dipole node then has to transmit at most \RsevbPowerMaxDipole{} dBm, which removes up to \RsevbPowerExtraDb{} dB of margin (about \RsevbPowerSfSteps{} spreading-factor steps at the simulators' sensitivity step; ANALYTICAL, no simulation was rerun at the lower power). The link results are therefore an optimistic bound on margin; the protocol, security and duty-cycle results do not use transmit power.", 1)
    c = r"\textbf{Regulation.} "
    assert c in s
    s = s.replace(c, r"\textbf{Transmit power.} The stored link results assume 14 dBm; a compliant dipole node transmits at most \RsevbPowerMaxDipole{} dBm, so they are optimistic on margin by up to \RsevbPowerExtraDb{} dB. " + c, 1)
    return s


def assumptions(s: str) -> str:
    if "r7b G0.2" in s:
        return s
    row = "| Transmit power | 14.0 dBm | assumption | same |"
    assert row in s
    return s.replace(row, row + "\n| Transmit power, reading of the 10 dB extra loss (r7b G0.2) | the author chose the conservative reading: the 10 dB is path margin, so a compliant dipole node transmits at most 10 dBm; the stored results at 14 dBm assume up to 4.00 dB more margin (about 1.4 spreading-factor steps at 2.8 dB per step) | assumption, ANALYTICAL note | link results (who is in range, delivery): optimistic bound on margin; protocol, security and duty-cycle results: none |", 1)


def placeholders(s: str) -> str:
    lines = s.split("\n")
    out = [ln for ln in lines if not ln.startswith("| India 433 MHz power assumption |")]
    t = "\n".join(out)
    if "Resolved in round 7b" not in t:
        t = t.replace("Resolved in the finalize run and removed from this list:", "Resolved in round 7b (G0.2) and removed from this list: the transmit power (the author chose the conservative reading: the 10 dB is path margin and a compliant dipole node transmits at most 10 dBm). Resolved in the finalize run and removed from this list:", 1)
    return t


rw(ROOT / "paper" / "main.tex", main_tex)
rw(ROOT / "docs" / "03_results" / "ASSUMPTIONS.md", assumptions)
rw(ROOT / "paper" / "PLACEHOLDERS.md", placeholders)
print("ok")
