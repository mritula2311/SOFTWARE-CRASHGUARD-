"""Round 5 literature queries for topics 28 to 31 against Crossref (OpenAlex answered HTTP 429 for these topics in the session; Crossref is used as the stated alternative source).

    python -m crashguard.r5_lit_cr          # writes results/tables/r5_lit_crossref.json

Journal articles from 2021-01-01; the title and abstract fields that Crossref holds are searched with a plain-text query (no operators). No key, no personal detail.
"""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "tables" / "r5_lit_crossref.json"
UA = "research-literature-check/1.0"
QUERIES = {
    28: ["rate limiting quarantine compromised vehicle false alerts plausibility check position", "misbehavior detection vehicle position plausibility speed alert flooding"],
    29: ["data leakage overlapping windows accelerometer activity recognition benchmark", "fall detection accelerometer dataset subject-wise split leakage duplicate windows"],
    30: ["smartphone accelerometer orientation alignment vehicle frame gyroscope yaw rate lateral acceleration", "inertial sensor axis sign error handedness calibration vehicle turn detection"],
    31: ["automatic crash notification false dispatch cost response delay decision analysis", "eCall false alarm emergency dispatch cost time"],
}


def get(url: str) -> dict:
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if a == 3:
                return {"error": repr(e)}
            time.sleep(3 * (a + 1))
    return {"error": "unreachable"}


def main() -> None:
    rows = []
    for topic, qs in QUERIES.items():
        for q in qs:
            url = "https://api.crossref.org/works?" + urllib.parse.urlencode({"query.bibliographic": q, "filter": "from-pub-date:2021-01-01,type:journal-article", "rows": 8, "select": "DOI,title,container-title,issued,abstract"})
            d = get(url)
            items = (d.get("message") or {}).get("items", []) if "error" not in d else []
            rows.append(dict(topic=topic, date_run=dt.date.today().isoformat(), database="Crossref API", query=q, status="OK" if "error" not in d else "NOT_RUN", reason=d.get("error", ""),
                             top=[dict(doi=i.get("DOI"), title=(i.get("title") or [""])[0], journal=(i.get("container-title") or [""])[0], year=(i.get("issued", {}).get("date-parts") or [[None]])[0][0], abstract=(i.get("abstract") or "")[:400]) for i in items]))
            print(topic, q[:50], len(items), flush=True)
            time.sleep(1.5)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
