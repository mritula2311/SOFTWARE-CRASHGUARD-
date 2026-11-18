"""A4: literature queries for round 4 against OpenAlex (journal articles from 2021-01-01, the Part A filter) plus a context search without date or type filter.

    python -m crashguard.a4_lit run                  # writes results/tables/a4_lit_queries.json
    python -m crashguard.a4_lit abstract ID [ID...]  # title, venue, abstract and open-access link of OpenAlex ids

No API key is requested and no personal detail is sent (generic client name).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path

from crashguard.lit_search import BASE, FILTER, _abstract, _get, n_ops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "tables" / "a4_lit_queries.json"
TOPICS: dict[int, list[str]] = {
    14: ["LoRaWAN AND (\"macro-diversity\" OR macrodiversity OR \"gateway diversity\" OR \"receiver diversity\")",
         "LoRaWAN AND (\"multiple gateways\" OR \"multi-gateway\") AND (reliability OR \"packet delivery\")",
         "LoRa AND \"spatial diversity\" AND gateway"],
    15: ["LoRa AND (\"short frame\" OR \"payload size\" OR \"payload reduction\") AND latency",
         "LoRa AND airtime AND (\"short packet\" OR \"short payload\") AND (emergency OR alert)",
         "LoRaWAN AND (\"preamble\" OR \"header\") AND (overhead OR \"short messages\")"],
    16: ["ProVerif AND (LoRa OR LoRaWAN OR \"low-power wide-area\")",
         "LoRaWAN AND (\"join procedure\" OR \"key derivation\") AND (ProVerif OR Tamarin)"],
}


def run() -> None:
    rows = []
    sel = "id,title,publication_year,publication_date,doi,primary_location,open_access,type"
    for topic, qs in TOPICS.items():
        for q in qs:
            assert n_ops(q) <= 5, q
            for scope, flt in (("journal_2021plus", f"{FILTER},title_and_abstract.search:({q})"), ("context_any", f"title_and_abstract.search:({q})")):
                url = f"{BASE}?filter={urllib.parse.quote(flt, safe=':,()')}&per-page=15&select={sel}"
                d = _get(url)
                rec = {"topic": topic, "scope": scope, "date_run": dt.date.today().isoformat(), "database": "OpenAlex API", "query": q, "filters": FILTER if scope == "journal_2021plus" else "none", "operators": n_ops(q)}
                if "error" in d or "results" not in d:
                    rec.update(status="NOT_RUN", reason=str(d.get("error") or d)[:300], count=None, top15=[])
                else:
                    rec.update(status="OK", count=d["meta"]["count"], top15=[
                        {"id": w["id"], "title": w["title"], "year": w["publication_year"], "doi": w.get("doi"), "type": w.get("type"),
                         "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"), "oa": (w.get("open_access") or {}).get("oa_url")} for w in d["results"]])
                rows.append(rec)
                print(topic, scope, rec.get("count"), q[:60], flush=True)
                time.sleep(1.0)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


def abstracts(ids: list[str]) -> None:
    for i in ids:
        i = i.replace("https://openalex.org/", "")
        d = _get(f"{BASE}/{i}?select=id,title,publication_date,doi,authorships,primary_location,abstract_inverted_index,open_access")
        if "error" in d:
            print(i, "ERROR", d["error"])
            continue
        au = "; ".join(a["author"]["display_name"] for a in d.get("authorships", [])[:6])
        src = ((d.get("primary_location") or {}).get("source") or {}).get("display_name")
        print(f"## {d['id']} | {d['title']} | {d['publication_date']} | {src} | {d.get('doi')} | OA={d.get('open_access', {}).get('is_oa')} {d.get('open_access', {}).get('oa_url')}")
        print("authors:", au)
        print("abstract:", _abstract(d.get("abstract_inverted_index"))[:1500])
        print()
        time.sleep(1.0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run()
    elif len(sys.argv) > 2 and sys.argv[1] == "abstract":
        abstracts(sys.argv[2:])
    else:
        print(__doc__)
