"""D3 and D6: fill the marked blocks of paper/cover_letter.md from results/results.json (so that no number of the cover letter is typed by hand).

    python scripts/vf2_cover.py
Blocks: <!-- r6:start --> ... <!-- r6:end --> (round 6 paragraph), <!-- ledger:start --> ... <!-- ledger:end --> (counts by round).
"""

# ruff: noqa: E402  (the guard below runs before the imports on purpose)
raise SystemExit('vf2_cover.py is a one-time script that was already applied in the delta verification run. Running it again would overwrite the cover-letter blocks with older counts. Refusing to run (guard added in round 7e, before submission). Its code is kept for the audit trail; read it, do not rerun it.')  # one-time script guard

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
P = ROOT / "paper" / "cover_letter.md"


def k(key):
    return R[key]


cells = [n[: -len(".air_over_r3")] for n in R if n.startswith("r6.r1.ns3.") and n.endswith(".air_over_r3")]
lo = min(k(c + ".air_over_r3") for c in cells)
hi = max(k(c + ".air_over_r3") for c in cells)
pd = max(k(c + ".air_per_delivered_over_r3") for c in cells if ".sf9." in c)
gap = max(abs(k(c + ".delivery_diff")) for c in cells)
r6 = (f"**Round 6.** An 8-byte micro-confirm that replaces the 97-byte confirm after an acknowledged provisional frame uses {lo:.2f} to {hi:.2f} of the two-stage alert's airtime in the {len(cells)} ns-3 cells "
      f"(at most {pd:.2f} per delivered alert at SF9), with delivery within {gap:.4f} of it in those cells; the trace groups give a zero difference by construction and are not evidence for delivery. "
      f"The simulated frame has {int(k('r6.r1.ns3.params.frame_bytes'))} bytes against the 8-byte design, which stays within the evaluated size (at SF7 it costs the airtime of the 14-byte flash, so the saving is against the 97-byte confirm only), "
      f"and its extra airtime against the single-stage alert, which is negative, is not offered as a gain: the 40% criterion was nearly automatic. "
      f"Its authenticity, binding and cancel lemmas are proved in ProVerif and Tamarin in symbolic models, and a hash ratchet is proved in ProVerif within {int(k('r6.f.h3a.ratchet_steps_bound'))} ratchet steps. "
      f"A quarantine rule that counts frames per claimed identifier before verification is shown attackable by an attacker without a key with {int(k('r6.f3b.A_count_before_verification.shortest_attack_frames'))} frames in a bounded model; "
      f"the fix is two counters, and the rule that counts after verification holds by construction. "
      f"A sequential early-exit rule decides {k('r6.r2.hR6_2.a_pt'):.1f} ms earlier and raises withdrawn provisional alerts by {100 * k('r6.r2.hR6_2.b_pt'):.1f} points; it is not supported, and the preregistration quoted the fixed rule's mean decision time wrongly "
      f"(720 to 780 ms against {k('r6.r2.held.mean_time_fixed_ms'):.0f} ms), which is disclosed. "
      f"The decision path was built for the target as build artifacts: {int(k('r6.fp.rodata.forest_bytes')):,} bytes of forest data, {int(k('r6.fp.image.flash_total_bytes')):,} bytes of linked flash (including unused functions) and a {int(k('r6.fp.stack.micro_verify_chain_bytes')):,}-byte stack chain; "
      f"instruction counts, timing and energy are NOT_RUN. The supplement gives the byte layout of every frame and a table of {int(k('vf2.layout.abstraction_rows'))} abstractions between the layout, the formal models and ns-3. "
      f"The Indian 433 MHz rules (G.S.R. 347(E), 2022) allow 10 mW e.r.p. at a duty cycle of at most 10%, with the observation interval not stated; the evaluation used a stricter 1% hourly allowance, and a deployed node would need type approval. "
      f"A duty-lockout condition shows that the stored two-stage results, produced under an hourly airtime allowance, do not transfer to a region that enforces a per-transmission off-time on one sub-band.")
groups = [("V1 to V5", ["V1", "V2", "V3", "V4", "V5"]), ("V7, V11 to V13", ["V7", "V11", "V12", "V13"]), ("round 3 (V14)", ["V14"]), ("round 4 (V15)", ["V15"]), ("round 5 (V16)", ["V16"]), ("round 6 (V17)", ["V17"])]
parts = []
for name, vs in groups:
    run = sum(k(f"r6.ledger.{v}.run") for v in vs)
    sup = sum(k(f"r6.ledger.{v}.supported") for v in vs)
    ns = sum(k(f"r6.ledger.{v}.not_supported") for v in vs)
    parts.append(f"{name}: {run} run, {sup} supported, {ns} not supported")
led = (f"**Hypotheses.** {int(k('r6.ledger.all.preregistered'))} hypotheses were preregistered in {int(k('r6.ledger.all.versions'))} versions; {int(k('r6.ledger.all.run'))} were run, {int(k('r6.ledger.all.supported'))} are supported, "
       f"{int(k('r6.ledger.all.not_supported'))} not supported, {int(k('r6.ledger.all.partly'))} partly supported and {int(k('r6.ledger.all.not_run'))} not run. By round: " + "; ".join(parts)
       + f". {int(k('r6.ledger.all.confirmatory_rows'))} hypotheses sit in a stated Holm family (each version has its own; the families are never merged), of which {int(k('r6.ledger.all.confirmatory_supported'))} are supported.")
s = P.read_text(encoding="utf-8")
for tag, text in (("r6", r6), ("ledger", led)):
    pat = re.compile(r"<!-- %s:start -->.*?<!-- %s:end -->" % (tag, tag), re.S)
    assert pat.search(s), tag
    s = pat.sub(lambda m: f"<!-- {tag}:start -->\n{text}\n<!-- {tag}:end -->", s)
P.write_text(s, encoding="utf-8")
print("cover letter blocks written")
