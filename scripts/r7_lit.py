"""Round 7 L0 literature queries: OpenAlex, Crossref, DOAJ, arXiv (2018 onward), IEEE Xplore open page (record the block, no bypass).

    python scripts/r7_lit.py   # writes results/tables/r7_lit_queries.json

No key, no personal detail, generic client name.
"""
import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "tables" / "r7_lit_queries.json"
UA = "research-literature-check/1.0"
A = ["ACK spoofing", "acknowledgement jamming", "selective jamming", "energy depletion", "battery exhaustion",
     "duty cycle denial of service", "retransmission attack", "airtime exhaustion", "regulatory duty cycle attack"]
B = ["pseudonym", "DevAddr privacy", "device de-anonymization", "unlinkability ProVerif IoT",
     "vehicle alert unlinkability", "pseudonym accountability revocation LPWAN"]
QUERIES = [("A", f"LoRaWAN {q}") for q in A] + [("A", f"LoRa {q}") for q in A[:4]] + \
          [("B", f"LoRaWAN {B[0]}"), ("B", f"LoRaWAN {B[1]}"), ("B", f"{B[2]} LoRaWAN")] + [("B", q) for q in B[3:]]


def get(url, text=False):
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
                b = r.read().decode("utf-8", "replace")
                return b if text else json.loads(b)
        except Exception as e:  # noqa: BLE001
            err = repr(e)
            if "418" in err or "403" in err:
                return {"error": err}
            time.sleep(3)
    return {"error": err}


def main():
    rows = []
    for topic, q in QUERIES:
        qq = urllib.parse.quote(q)
        today = dt.date.today().isoformat()
        srcs = {
            "OpenAlex": (f"https://api.openalex.org/works?search={qq}&filter=from_publication_date:2018-01-01&per-page=10&select=id,title,publication_year,doi,open_access", "oa"),
            "Crossref": (f"https://api.crossref.org/works?query={qq}&filter=from-pub-date:2018&rows=10&select=DOI,title,issued,container-title", "cr"),
            "DOAJ": (f"https://doaj.org/api/search/articles/{qq}?pageSize=10", "doaj"),
            "arXiv": (f"https://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(chr(34) + q + chr(34))}&max_results=10", "arx"),
        }
        for db, (url, kind) in srcs.items():
            rec = {"topic": topic, "query": q, "database": db, "date": today, "filter": "2018 onward"}
            if kind == "arx":
                t = get(url, text=True)
                if isinstance(t, dict):
                    rec.update(status="NOT_RUN", reason=t["error"], count=None, top=[])
                else:
                    import re
                    ents = re.findall(r"<entry>.*?</entry>", t, re.S)
                    tot = re.search(r"totalResults[^>]*>(\d+)<", t)
                    top = []
                    for e in ents:
                        ti = re.search(r"<title>(.*?)</title>", e, re.S).group(1).split()
                        yr = re.search(r"<published>(\d{4})", e).group(1)
                        idn = re.search(r"<id>(.*?)</id>", e).group(1)
                        if int(yr) >= 2018:
                            top.append({"title": " ".join(ti), "year": yr, "id": idn})
                    rec.update(status="OK", count=int(tot.group(1)) if tot else None, top=top)
            else:
                d = get(url)
                if "error" in d:
                    rec.update(status="NOT_RUN", reason=d["error"][:200], count=None, top=[])
                elif kind == "oa":
                    rec.update(status="OK", count=d["meta"]["count"], top=[{"title": w["title"], "year": w["publication_year"], "doi": w.get("doi"), "oa": (w.get("open_access") or {}).get("oa_url")} for w in d["results"]])
                elif kind == "cr":
                    m = d["message"]
                    rec.update(status="OK", count=m["total-results"], top=[{"title": (w.get("title") or [""])[0], "year": (w.get("issued", {}).get("date-parts") or [[None]])[0][0], "doi": w["DOI"]} for w in m["items"]])
                else:
                    rec.update(status="OK", count=d.get("total"), top=[{"title": r["bibjson"].get("title"), "year": r["bibjson"].get("year"), "doi": next((i["id"] for i in r["bibjson"].get("identifier", []) if i["type"] == "doi"), None)} for r in d.get("results", []) if int(r["bibjson"].get("year") or 0) >= 2018])
            rows.append(rec)
            print(topic, db, rec.get("count"), rec.get("reason", "")[:60], q, flush=True)
            time.sleep(3)
        ieee = get(f"https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={qq}", text=True)
        rows.append({"topic": topic, "query": q, "database": "IEEE Xplore open page", "date": today,
                     "status": "NOT_RUN" if isinstance(ieee, dict) else "OK-page-only", "reason": ieee["error"][:120] if isinstance(ieee, dict) else "page shell (results load by script)", "count": None, "top": []})
        time.sleep(1)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
