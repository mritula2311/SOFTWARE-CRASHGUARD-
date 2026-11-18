"""Round 5 literature queries against OpenAlex (journal articles from 2021-01-01, the Part A filter) plus a context search without date or type filter.

    python -m crashguard.r5_lit run [topic ...]      # writes results/tables/r5_lit_queries.json (topics 21 to 25 are L1 to L5)
    python -m crashguard.r5_lit abstract ID [ID...]  # title, venue, abstract and open-access link of OpenAlex ids

No API key is requested and no personal detail is sent (generic client name). Same helper functions as ``a4_lit``.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.parse
from pathlib import Path

from crashguard.a4_lit import abstracts
from crashguard.lit_search import BASE, FILTER, _get, n_ops

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "tables" / "r5_lit_queries.json"
TOPICS: dict[int, list[str]] = {
    21: ["smartphone AND \"orientation\" AND (crash OR accident) AND detection",
         "gravity AND (smartphone OR accelerometer) AND (calibration OR alignment) AND vehicle",
         "accelerometer AND (\"coordinate system\" OR \"reorientation\") AND (vehicle OR driving)"],
    22: ["(crash OR accident) AND detection AND \"false alarm\" AND (\"post-crash\" OR \"post-impact\")",
         "\"accident detection\" AND smartphone AND (\"speed drop\" OR stationary) AND verification",
         "(\"two-stage\" OR confirmation) AND accident AND detection AND vehicle"],
    23: ["(\"wake-up\" OR \"wake-on-motion\") AND accelerometer AND energy AND (crash OR impact)",
         "(\"pre-trigger\" OR \"pre-event\") AND accelerometer AND buffer AND (impact OR fall)",
         "MPU6050 AND (\"motion interrupt\" OR \"power consumption\") AND detection"],
    24: ["LoRa AND \"spreading factor\" AND retransmission AND (deadline OR latency)",
         "LoRaWAN AND \"spreading factor\" AND (escalation OR fallback OR increase) AND reliability",
         "LoRaWAN AND ADR AND retransmission AND (\"time-critical\" OR \"low latency\" OR alarm)"],
    25: ["(\"cross-layer\" OR \"co-design\") AND detection AND (LoRa OR wireless) AND \"false alarm\"",
         "(\"time to awareness\" OR \"notification time\") AND (crash OR accident) AND (IoT OR LoRa)",
         "(\"detection threshold\" OR \"decision threshold\") AND \"network delay\" AND \"end-to-end\""],
    26: ["LoRaWAN AND \"gateway placement\" AND (optimization OR optimisation) AND coverage",
         "(\"gateway placement\" OR \"gateway deployment\") AND (crash OR accident OR \"traffic accident\") AND coverage",
         "LoRa AND \"gateway placement\" AND (demand OR \"weighted\" OR hotspot)"],
    27: ["(\"forward secrecy\" OR \"forward secure\") AND (LoRaWAN OR LoRa) AND (\"key\" OR ratchet)",
         "\"hash chain\" AND (LoRaWAN OR \"low-power wide-area\") AND (\"key update\" OR \"session key\")",
         "Tamarin AND (LoRaWAN OR \"forward secrecy\") AND verification"],
    28: ["(spoofing OR flooding) AND \"false alerts\" AND (rate AND limiting) AND IoT",
         "(quarantine OR \"trust score\") AND \"compromised node\" AND alert AND vehicle",
         "\"plausibility check\" AND (position OR GPS) AND vehicle AND misbehavior"],
    29: ["(leakage OR duplicate) AND benchmark AND (accelerometer OR \"activity recognition\")",
         "\"fall detection\" AND (\"subject-wise\" OR leakage) AND accelerometer",
         "(\"activity recognition\" OR \"fall detection\") AND \"overlapping windows\" AND leakage"],
    30: ["(IMU OR smartphone) AND orientation AND (\"yaw rate\" OR gyroscope) AND vehicle",
         "(\"coordinate frame\" OR mounting) AND (\"lateral acceleration\" OR centripetal) AND gyroscope",
         "(\"sign error\" OR handedness OR \"axis flip\") AND (IMU OR accelerometer) AND calibration"],
    31: ["(\"false dispatch\" OR \"false alarm\") AND (ambulance OR emergency) AND cost AND delay",
         "(\"automatic crash notification\" OR eCall) AND dispatch AND (\"false\" OR cost)"],
}


def run(topics: list[int]) -> None:
    rows = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    rows = [r for r in rows if r["topic"] not in topics]
    sel = "id,title,publication_year,publication_date,doi,primary_location,open_access,type"
    for topic in topics:
        for q in TOPICS[topic]:
            assert n_ops(q) <= 5, (n_ops(q), q)
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
                print(topic, scope, rec.get("count"), rec.get("reason", "")[:80], q[:60], flush=True)
                time.sleep(2.5)
    OUT.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "abstract":
        abstracts(sys.argv[2:])
    else:
        run([int(a) for a in sys.argv[2:]] or sorted(TOPICS))
