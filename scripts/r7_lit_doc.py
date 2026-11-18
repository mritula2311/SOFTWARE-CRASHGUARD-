"""Append the query tables to docs/01_literature/R7_PRIOR_ART.md (from the two JSON files)."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
P = R / "docs/01_literature/R7_PRIOR_ART.md"
txt = P.read_text(encoding="utf-8").split("## 4. Queries run")[0] + "## 4. Queries run\n\n"
for name, f in (("Initial pass", "r7_lit_queries.json"), ("Second pass", "r7_lit_queries2.json")):
    rows = json.loads((R / "results/tables" / f).read_text(encoding="utf-8"))
    txt += f"### {name}\n\n| Topic | Query | Database | Date | Hits | Status |\n|---|---|---|---|---:|---|\n"
    for x in rows:
        st = x.get("status") or ("NOT_RUN" if x.get("error") else "OK")
        c = x.get("count")
        txt += f"| {x['topic']} | {x['query']} | {x['database']} | {x['date']} | {'' if c is None else c} | {st}{(' (' + (x.get('reason') or x.get('error') or '')[:40] + ')') if st == 'NOT_RUN' else ''} |\n"
    txt += "\n"
P.write_text(txt, encoding="utf-8")
