"""Part A: literature queries against OpenAlex (journal articles from 2021-01-01).

Records, for every query: date, database, exact query and filters, result count and the 15 most
relevant titles (year, journal, DOI). No API key is requested and no personal detail is sent.
Usage:  python -m crashguard.lit_search run      (writes results/tables/lit_queries.json)
        python -m crashguard.lit_search abstract ID [ID ...]   (prints title + abstract of OpenAlex ids)
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "tables" / "lit_queries.json"
BASE = "https://api.openalex.org/works"
FILTER = "from_publication_date:2021-01-01,primary_location.source.type:journal"
UA = "research-literature-check/1.0"

# topic number -> list of (query text, number of boolean operators)
TOPICS: dict[int, list[str]] = {
    1: ["LoRa AND (crash OR accident) AND (alert OR notification)",
        "LPWAN AND (accident OR crash) AND detection"],
    2: ["LoRa AND retransmission AND (emergency OR critical)",
        "LoRaWAN AND (deadline OR latency) AND (confirmed OR acknowledgment)",
        "LoRaWAN AND \"adaptive data rate\" AND latency"],
    3: ["(eCall OR \"automatic crash notification\") AND severity",
        "\"next generation eCall\" OR \"minimum set of data\"",
        "crash AND notification AND (provisional OR \"two-stage\" OR early)"],
    4: ["LoRaWAN AND (replay OR counter) AND (authentication OR acknowledgment)",
        "LoRa AND \"key derivation\" AND device"],
    5: ["(LoRa OR LoRaWAN) AND (Tamarin OR ProVerif OR UPPAAL)",
        "LoRaWAN AND (\"formal verification\" OR \"model checking\")",
        "LoRaWAN AND (AVISPA OR \"timed automata\")"],
    6: ["LoRa AND (overhearing OR cooperative) AND acknowledgment",
        "LoRaWAN AND (\"aggregated acknowledgment\" OR \"group acknowledgment\")"],
    7: ["LoRaWAN AND (trace-driven OR \"real-world traces\" OR \"measurement dataset\")",
        "\"LoRaWAN at the Edge\" OR LoED",
        "LoRaWAN AND dataset AND (\"frame counter\" OR \"packet loss\")"],
    8: ["(ns-3 OR FLoRa OR LoRaSim) AND LoRa AND (validation OR measurements)",
        "LoRaWAN AND simulator AND \"real deployment\""],
    9: ["accelerometer AND (saturation OR clipping) AND (impact OR crash)",
        "\"delta-V\" AND accelerometer AND (estimation OR crash)",
        "crash AND accelerometer AND (\"sampling rate\" OR \"measurement range\")"],
    10: ["(leakage OR duplicate) AND (crash OR \"fall detection\" OR \"activity recognition\") AND dataset",
         "(\"data leakage\" OR \"subject-wise\") AND (\"activity recognition\" OR \"fall detection\") AND validation"],
    11: ["(crash OR accident) AND detection AND (TinyML OR \"decision tree\") AND embedded"],
    12: ["\"crash pulse\" AND (synthetic OR generation)",
         "vehicle AND crash AND (\"lumped parameter\" OR \"spring-mass\") AND pulse"],
    13: ["IoT AND (supercapacitor OR \"backup power\") AND (emergency OR alert) AND transmission",
         "\"last gasp\" AND (IoT OR LoRa OR LPWAN)"],
}


def n_ops(q: str) -> int:
    return sum(q.count(w) for w in (" AND ", " OR ", " NOT "))


def _get(url: str) -> dict:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                return {"error": repr(e)}
            time.sleep(3 * (attempt + 1))
    return {"error": "unreachable"}


def run() -> None:
    rows = []
    for topic, qs in TOPICS.items():
        for q in qs:
            assert n_ops(q) <= 5, q
            flt = f"{FILTER},title_and_abstract.search:({q})"
            sel = "id,title,publication_year,publication_date,doi,primary_location"
            url = f"{BASE}?filter={urllib.parse.quote(flt, safe=':,()')}&per-page=15&select={sel}"
            d = _get(url)
            rec = {"topic": topic, "date_run": dt.date.today().isoformat(), "database": "OpenAlex API",
                   "query": q, "filters": FILTER, "operators": n_ops(q)}
            if "error" in d or "results" not in d:
                rec.update(status="NOT_RUN", reason=str(d.get("error") or d.get("message") or d)[:300],
                           count=None, top15=[])
            else:
                rec.update(status="OK", count=d["meta"]["count"], top15=[
                    {"id": w["id"], "title": w["title"], "year": w["publication_year"], "doi": w.get("doi"),
                     "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name")}
                    for w in d["results"]])
            rows.append(rec)
            print(topic, rec.get("count"), q[:70], flush=True)
            time.sleep(1.0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


def _abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = {}
    for w, ps in inv.items():
        for p in ps:
            pos[p] = w
    return " ".join(pos[i] for i in sorted(pos))


def abstracts(ids: list[str]) -> None:
    for i in ids:
        i = i.replace("https://openalex.org/", "")
        d = _get(f"{BASE}/{i}?select=id,title,publication_date,doi,authorships,primary_location,abstract_inverted_index,open_access")
        if "error" in d:
            print(i, "ERROR", d["error"])
            continue
        au = "; ".join(a["author"]["display_name"] for a in d.get("authorships", [])[:8])
        src = ((d.get("primary_location") or {}).get("source") or {}).get("display_name")
        print(f"## {d['id']} | {d['title']} | {d['publication_date']} | {src} | {d.get('doi')} | OA={d.get('open_access', {}).get('is_oa')}")
        print("authors:", au)
        print("abstract:", _abstract(d.get("abstract_inverted_index"))[:1800])
        print()
        time.sleep(1.0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run()
    elif len(sys.argv) > 2 and sys.argv[1] == "abstract":
        abstracts(sys.argv[2:])
    else:
        print(__doc__)
