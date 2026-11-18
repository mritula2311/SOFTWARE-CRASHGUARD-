"""Derive the control models of round 7 from the main ProVerif models (formal/proverif/r7_lemmas_*.pv)."""
from pathlib import Path

D = Path(__file__).resolve().parents[1] / "formal" / "proverif"


def rd(n):
    return (D / n).read_text(encoding="utf-8")


def wr(n, s):
    (D / n).write_text(s, encoding="utf-8")


t = rd("r7_lemmas_alert.pv")
c = t.replace("  new b: bitstring;\n  in(c, e: bitstring);\n  ( SendOne(km, v, b, e, s1) | SendOne(km, v, b, e, s2) ).",
              "  in(c, e: bitstring);\n  ( SendOne(km, v, b0, e, s1) | SendOne(km, v, b0, e, s2) ).").replace("const s1: bitstring.", "const b0: bitstring.\nconst s1: bitstring.")
assert c != t
wr("r7_lemmas_alert_nowrite.pv", "(* Round 7 B2.2 control: the boot counter is not written (every boot starts from the same value b0), otherwise as r7_lemmas_alert.pv. The uniqueness of sent ids (query 1) must FAIL, as in carid_bootctr_nowrite.pv. *)\n" + c)

t = rd("r7_lemmas_micro.pv")
c = t.replace("(tagM, t, x)", "(tagM, x)")
assert c != t
wr("r7_lemmas_micro_control.pv", "(* Round 7 B2.2 control: the micro tag input has no T1 (as r6_micro_confirm_control.pv). Query (i), acceptance implies that the vehicle sent this micro frame for this T1, must FAIL (the frame is no longer bound to its T1). *)\n" + c)

t = rd("r7_lemmas_quarantine.pv")
old = "     if t = mac(kdf(km, v), (tagA, p, kind, a)) then\n     get seen(=v, =a) in 0 else\n     ( insert seen(v, a); if kind = bad then event Strike(v, a) ) )."
assert old in t
c = t.replace(old, "     ( if kind = bad then event Strike(v, a) ) ).")
wr("r7_lemmas_quarantine_control.pv", "(* Round 7 B2.2 control: rule A, the strike is counted when the pseudonym resolves, before the tag and the seen-set are checked. The no-framing query must FAIL (the attacker sends a resolvable pseudonym with a bad flag and a wrong tag). *)\n" + c)
print("controls written")
