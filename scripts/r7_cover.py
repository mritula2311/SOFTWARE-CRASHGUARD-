"""Round 7 P: fill a round-7 block of paper/cover_letter.md, refresh its hypothesis-count block, and adjust highlight 3 (each highlight at most 85 characters). Numbers come from results/results.json. Idempotent.

    python scripts/r7_cover.py
"""

# ruff: noqa: E402  (the guard below runs before the imports on purpose)
raise SystemExit('r7_cover.py is a one-time script that was already applied in round 7. Running it again would reset the hypothesis counts of the cover letter to 136 in 14 versions. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
P = ROOT / "paper" / "cover_letter.md"
H = ROOT / "paper" / "highlights.md"
t = P.read_text(encoding="utf-8")
crlf = "\r\n" in t
t = t.replace("\r\n", "\n")

pct = lambda x: f"{100 * float(x):.1f}"  # noqa: E731
r7 = (
    "**Round 7.** Two additions to the protocol work; of five preregistered hypotheses, two are supported and three are not. "
    f"(1) An attacker that suppresses acknowledgements makes the node spend airtime on retries. A reserved airtime budget for the confirm or cancel frame was checked in a bounded model "
    f"({int(R['r7.formal.total.reserved.runs']):,} configurations per policy: no late follow-up while the reserve is intact, {int(R['r7.formal.total.old.inv2_violations_conditional']):,} late runs for the shipped policy) and in simulation; "
    f"at the load that exhausts the shipped policy under a 1% allowance the one-event reserve keeps the follow-up on time in {pct(R['r7.a1.sim.H1.sf7.reserved.primary.rate'])}%, {pct(R['r7.a1.sim.H1.sf8.reserved.primary.rate'])}% and {pct(R['r7.a1.sim.H1.sf9.reserved.primary.rate'])}% of runs at SF7, SF8 and SF9, "
    "so the 99% target is not met; a reserve for four events meets it (post-run). The reserve costs "
    f"{abs(100 * R['r7.a2.H.R3.T10.delivery_diff']):.1f} points of delivery in the high-loss trace group under a per-transmission off-time (bound: 1 point). "
    f"(2) A keyed rotating pseudonym replaces the vehicle id; ProVerif proves that two alerts of one vehicle cannot be told from two vehicles (also for unboundedly many alerts), the fixed-id design fails, and the earlier lemmas still hold with the pseudonym. "
    f"Resolution costs at most {1e6 * R['r7.b.hR7_B1.worst_mean_per_frame']:.0f} microseconds per frame; the collision bound of 1e-6 is not met at the frame's 2 or 4 bytes ({R['r7.b.hR7_B2.L2.p_collision_formula']:.3f} and {R['r7.b.hR7_B2.L4.p_collision_formula']:.1e}). "
    "Position, timing and radio fingerprints stay visible; nothing is measured on hardware. "
    f"Related work: the pseudonym idea is from Pélissier et al. (WiSec 2024), who argue unlinkability informally; the energy-depletion attacks on LoRaWAN are prior work. Contributions stay eight."
)
block = "<!-- r7:start -->\n" + r7 + "\n<!-- r7:end -->"
if "<!-- r7:start -->" in t:
    t = re.sub(r"<!-- r7:start -->.*?<!-- r7:end -->", lambda m: block, t, flags=re.S)
else:
    t = t.replace("<!-- r6:end -->", "<!-- r6:end -->\n\n" + block, 1)
led = (f"**Hypotheses.** {int(R['r7.ledger.all.preregistered'])} hypotheses were preregistered in {int(R['r7.ledger.all.versions'])} versions; {int(R['r7.ledger.all.run'])} were run, {int(R['r7.ledger.all.supported'])} are supported, "
       f"{int(R['r7.ledger.all.not_supported'])} not supported, {int(R['r7.ledger.all.partly'])} partly supported and {int(R['r7.ledger.all.not_run'])} not run (one hypothesis of round 7 is descriptive and has no verdict). The ledger lists every row.")
t = re.sub(r"<!-- ledger:start -->.*?<!-- ledger:end -->", lambda m: "<!-- ledger:start -->\n" + led + "\n<!-- ledger:end -->", t, flags=re.S)
P.write_text(t.replace("\n", "\r\n") if crlf else t, encoding="utf-8")

h = H.read_text(encoding="utf-8")
hc = "\r\n" in h
h = h.replace("\r\n", "\n")
new3 = "ACK binding, boot counter and unlinkable ids proved; duty reserve has limits"
line = f"- {new3} ({len(new3)} characters)"
assert len(new3) <= 85
h = re.sub(r"- Shared-key ACKs can be suppressed.*", lambda m: line, h)
H.write_text(h.replace("\n", "\r\n") if hc else h, encoding="utf-8")
print("cover letter and highlights updated;", len(new3), "characters")
