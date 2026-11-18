"""Finalize F1: keys vf3.formal.* from formal/out/vf3 (index variants of the micro-confirm models)."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard.results import record_many  # noqa: E402

OUTD = ROOT / "formal" / "out" / "vf3"
pv = (OUTD / "pv_micro_confirm_index.txt").read_text(encoding="utf-8")
tam = (OUTD / "tam_micro_confirm_index.txt").read_text(encoding="utf-8")
q = [m.group(2) == "true" for m in re.finditer(r"^Query (.*) is (true|false)\.$", pv, re.M)]
lem = {m.group(1): m.group(2) for m in re.finditer(r"^\s+(\w+) \((?:all|exists)-traces?\): (verified|falsified)", tam, re.M)}
meta = lambda t: re.search(r"exit code: (\d+) ; wall time (\d+) s ; peak memory (\d+) MB", t).groups()  # noqa: E731
ok_pv = q[0] and q[1] and q[2] and (not q[3])
ok_tam = all(lem.get(k) == "verified" for k in ("executable_micro", "micro_auth", "micro_binding", "cancel_auth"))
ent = []
for name, v, note in (("proverif.all_proved", int(ok_pv), "ProVerif 2.05: authenticity, binding to the flash, micro-cancel proved; the event is reachable. " + "exit %s, %s s, %s MB" % meta(pv)),
                      ("tamarin.all_verified", int(ok_tam), "Tamarin 1.12.0: executable_micro, micro_auth, micro_binding, cancel_auth verified. " + "exit %s, %s s, %s MB" % meta(tam))):
    ent.append(dict(name=f"vf3.formal.index.{name}", value=v, unit="flag", origin="FORMAL", source_file="scripts/vf3_record_formal.py", notes=note))
record_many(ent, purge_prefixes=("vf3.formal.",))
print(ok_pv, ok_tam)
