"""Round 7c item 3: recount the hypothesis ledger from the per-hypothesis rows of docs/04_audits/HYPOTHESIS_LEDGER.md and from the result keys, compare with the Totals table and with every place that quotes the totals.

    python scripts/r7c_ledger_recount.py          # prints the comparison; writes keys r7c.ledger.* with --record
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
text = (ROOT / "docs/04_audits/HYPOTHESIS_LEDGER.md").read_text(encoding="utf-8").replace("\r\n", "\n")
R = {e["name"]: e["value"] for e in json.loads((ROOT / "results/results.json").read_text(encoding="utf-8"))}


def cat(verdict: str) -> str:
    v = verdict.upper().replace("_", " ")
    if v.startswith("NOT SUPPORTED") or v.startswith("NOT_SUPPORTED"):
        return "not_supported"
    if "NOT RUN" in v:
        return "not_run"
    if v.startswith("PARTLY") or "PARTLY" in v:
        return "partly"
    if v.startswith("SUPPORTED"):
        return "supported"
    return "other"


rows = collections.defaultdict(list)
sec = text[text.index("\n## Ledger"):]
sec_main = sec[: sec.index("\n## Totals")]
for ln in sec_main.split("\n"):
    c = [x.strip() for x in ln.strip().strip("|").split("|")]
    if ln.startswith("| V") and len(c) >= 9 and re.fullmatch(r"V\d+", c[0]):
        if "counted once, under" in c[8]:  # a re-test of an earlier hypothesis: counted in the earlier version (V13 H-C3 refit, under V5)
            continue
        rows[c[0]].append((c[1], c[4]))
for name, ver, start, stop in (("V18", "V18", "## Round 7 (V18)", "## Round 7b (V19)"), ("V19", "V19", "## Round 7b (V19)", None)):
    part = text[text.index(start):]
    part = part[: part.index(stop)] if stop and stop in part else part
    seen = set()
    for ln in part.split("\n"):
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if ln.startswith("| H-R7") and len(c) >= 5 and c[0] not in seen:
            seen.add(c[0])
            rows[ver].append((c[0], c[4]))
tot_rows = {}
for ln in text[text.index("\n## Totals"):].split("\n"):
    c = [x.strip() for x in ln.strip().strip("|").split("|")]
    if re.fullmatch(r"V\d+|all", c[0] if c else "") and len(c) == 7:
        tot_rows[c[0]] = [int(x) for x in c[1:]]
order = ("preregistered", "run", "supported", "not_supported", "partly", "not_run")
count = {}
for v, rs in rows.items():
    k = collections.Counter(cat(x[1]) for x in rs)
    pre = len(rs)
    run = pre - k["not_run"]
    count[v] = [pre, run, k["supported"], k["not_supported"], k["partly"], k["not_run"]]
    if k["other"]:
        count[v].append(("other", k["other"]))
tot_all = [sum(count[v][i] for v in count) for i in range(6)]
print("versions with rows:", len(count), sorted(count, key=lambda s: int(s[1:])))
print("sum of per-hypothesis rows (all versions):", tot_all)
print("Totals table 'all' row:                  ", tot_rows.get("all"))
bad = []
for v in count:
    t = tot_rows.get(v)
    if t != count[v][:6]:
        bad.append((v, count[v], t))
print("per-version rows differing from the Totals table:")
for b in bad:
    print("  ", b)
key_all = [int(R[f"r7b.ledger.all.{k}"]) for k in order]
print("keys r7b.ledger.all:", key_all, "versions", R["r7b.ledger.all.versions"])
if "--record" in sys.argv:
    from crashguard.results import record_many

    ent = [dict(name=f"r7c.ledger.recount.{k}", value=v, unit="hypotheses", origin="ANALYTICAL", source_file="scripts/r7c_ledger_recount.py", notes="counted from the per-hypothesis rows of HYPOTHESIS_LEDGER.md") for k, v in zip(order, tot_all)]
    ent.append(dict(name="r7c.ledger.recount.versions", value=len(count), unit="versions", origin="ANALYTICAL", source_file="scripts/r7c_ledger_recount.py", notes="versions that have rows"))
    ent.append(dict(name="r7c.ledger.recount.matches_totals_table", value=int(not bad and tot_all == tot_rows.get("all")), unit="flag", origin="ANALYTICAL", source_file="scripts/r7c_ledger_recount.py", notes="per-hypothesis rows equal the Totals table in every version and in total"))
    ent.append(dict(name="r7c.ledger.recount.matches_keys", value=int(tot_all == key_all and len(count) == int(R["r7b.ledger.all.versions"])), unit="flag", origin="ANALYTICAL", source_file="scripts/r7c_ledger_recount.py", notes="per-hypothesis rows equal keys r7b.ledger.all"))
    record_many(ent, purge_prefixes=("r7c.ledger.",))
    print("recorded", len(ent))
