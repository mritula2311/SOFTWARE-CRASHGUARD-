# ruff: noqa: E401, E701, E702
"""Round 7 L0 second pass: targeted queries for the two stop rules (OpenAlex, Crossref, arXiv unquoted)."""
import datetime as dt, json, re, time, urllib.parse, urllib.request
from pathlib import Path
OUT = Path(__file__).resolve().parents[1] / "results" / "tables" / "r7_lit_queries2.json"
UA = {"User-Agent": "research-literature-check/1.0"}
Q = [("A", "reserved airtime duty cycle emergency alert LoRa"), ("A", "duty cycle budget reserve priority retransmission LoRaWAN"),
     ("A", "confirmed uplink acknowledgement drop attack LoRaWAN duty cycle"), ("A", "LoRaWAN downlink acknowledgement jamming retransmission energy duty-cycle exhaustion"),
     ("B", "formal verification unlinkability LoRaWAN identifier ProVerif"), ("B", "LPWAN identifier privacy formal proof replay protection accountability"),
     ("B", "LoRaWAN anonymity Tamarin ProVerif privacy DevAddr"), ("B", "unlinkable pseudonym vehicle emergency alert accountability revocation formal")]
def get(u, text=False):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as r:
            b = r.read().decode("utf-8", "replace"); return b if text else json.loads(b)
    except Exception as e:
        return {"error": repr(e)}
rows = []
for t, q in Q:
    qq = urllib.parse.quote(q); today = dt.date.today().isoformat()
    d = get(f"https://api.openalex.org/works?search={qq}&filter=from_publication_date:2018-01-01&per-page=8&select=id,title,publication_year,doi")
    rows.append({"topic": t, "query": q, "database": "OpenAlex", "date": today, "count": d.get("meta", {}).get("count"), "error": d.get("error"),
                 "top": [{"title": w["title"], "year": w["publication_year"], "doi": w.get("doi")} for w in d.get("results", [])]})
    time.sleep(3)
    d = get(f"https://api.crossref.org/works?query={qq}&filter=from-pub-date:2018&rows=8&select=DOI,title,issued")
    m = d.get("message", {})
    rows.append({"topic": t, "query": q, "database": "Crossref", "date": today, "count": m.get("total-results"), "error": d.get("error"),
                 "top": [{"title": (w.get("title") or [""])[0], "year": (w.get("issued", {}).get("date-parts") or [[None]])[0][0], "doi": w["DOI"]} for w in m.get("items", [])]})
    time.sleep(3)
    s = get("https://export.arxiv.org/api/query?search_query=all:" + urllib.parse.quote(" AND all:".join(q.split()[:5])) + "&max_results=8", True)
    if isinstance(s, dict): rows.append({"topic": t, "query": q, "database": "arXiv", "date": today, "count": None, "error": s["error"], "top": []})
    else:
        top = [{"title": " ".join(re.search(r"<title>(.*?)</title>", e, re.S).group(1).split()), "year": re.search(r"<published>(\d{4})", e).group(1), "id": re.search(r"<id>(.*?)</id>", e).group(1)} for e in re.findall(r"<entry>.*?</entry>", s, re.S)]
        n = re.search(r"totalResults[^>]*>(\d+)<", s)
        rows.append({"topic": t, "query": q, "database": "arXiv", "date": today, "count": int(n.group(1)) if n else None, "error": None, "top": [x for x in top if int(x["year"]) >= 2018]})
    time.sleep(3)
    print(t, q, flush=True)
OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
