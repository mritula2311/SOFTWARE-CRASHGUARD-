"""V9: Crossref metadata for DOIs.

    python scripts/vf_crossref.py fetch DOI [DOI ...]      # print title, authors, year, venue, volume, issue, pages
    python scripts/vf_crossref.py check paper/references.bib   # compare every entry that has a doi with Crossref; table to docs/04_audits/REFERENCE_CHECK_VF.md

No e-mail address or key is sent. A DOI that Crossref does not know is reported as 'not found' (the publisher page must then be checked by hand).
"""
from __future__ import annotations

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "processed" / "vf_crossref_cache.json"


def fetch(doi: str) -> dict | None:
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    key = doi.lower()
    if key in cache:
        return cache[key]
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
    req = urllib.request.Request(url, headers={"User-Agent": "crashguard-reference-check/1.0"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=40))["message"]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            d = None
        else:
            raise
    cache[key] = d
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    time.sleep(0.3)
    return d


def year_of(m: dict) -> int | None:
    for k in ("published-print", "published-online", "published", "issued"):
        if m.get(k, {}).get("date-parts") and m[k]["date-parts"][0] and m[k]["date-parts"][0][0]:
            return m[k]["date-parts"][0][0]
    return None


def summary(m: dict) -> dict:
    au = [f"{a.get('family', a.get('name', '?'))}, {a.get('given', '')}".strip(", ") for a in m.get("author", [])]
    return dict(title=re.sub(r"<[^>]+>", "", (m.get("title") or [""])[0]), authors=au, year=year_of(m), print_year=(m.get("published-print", {}).get("date-parts") or [[None]])[0][0],
                online_year=(m.get("published-online", {}).get("date-parts") or [[None]])[0][0], venue=(m.get("container-title") or [""])[0], volume=m.get("volume"), issue=m.get("issue"), pages=m.get("page") or m.get("article-number"), type=m.get("type"), publisher=m.get("publisher"))


def parse_bib(text: str) -> list[dict]:
    out = []
    for m in re.finditer(r"@(\w+)\{([^,]+),", text):
        i, depth, k = m.end(), 1, m.end()
        while depth and k < len(text):
            depth += (text[k] == "{") - (text[k] == "}")
            k += 1
        body = text[i:k - 1]
        f = {}
        for fm in re.finditer(r"(\w+)\s*=\s*", body):
            pos = fm.end()
            if pos >= len(body):
                continue
            if body[pos] == "{":
                d, q = 1, pos + 1
                while d and q < len(body):
                    d += (body[q] == "{") - (body[q] == "}")
                    q += 1
                val = body[pos + 1:q - 1]
            else:
                val = re.match(r"[^,]*", body[pos:]).group(0)
            f.setdefault(fm.group(1).lower(), re.sub(r"\s+", " ", val.strip()))
        f["type"], f["key"] = m.group(1), m.group(2)
        out.append(f)
    return out


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\\[\"'`^~cv]\s*", "", s)
    s = s.replace("\\i", "i")
    s = re.sub(r"[{}\\$]", "", s)
    s = s.replace("‐", "-").replace("‑", "-")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main() -> None:
    if sys.argv[1] == "fetch":
        for doi in sys.argv[2:]:
            m = fetch(doi)
            print(doi, json.dumps(summary(m), ensure_ascii=False) if m else "NOT FOUND")
        return
    entries = parse_bib(Path(sys.argv[2]).read_text(encoding="utf-8"))
    rows, nfix = [], 0
    for e in entries:
        doi = e.get("doi")
        if not doi:
            rows.append((e["key"], "no DOI", "-", "-", "checked by hand or a record URL (see reference_status.txt)"))
            continue
        m = fetch(doi)
        if not m:
            rows.append((e["key"], doi, "not a Crossref DOI" if doi.startswith(("10.5281", "10.24432")) else "NOT FOUND in Crossref", "-", "DataCite or Zenodo record read (reference_status.txt)" if doi.startswith(("10.5281", "10.24432")) else "publisher page must be opened"))
            continue
        s = summary(m)
        probs = []
        if norm(e.get("title", ""))[:60] != norm(s["title"])[:60]:
            probs.append(f"title: bib '{e.get('title', '')[:60]}' / Crossref '{s['title'][:60]}'")
        yrs = {y for y in (s["year"], s["print_year"], s["online_year"]) if y}
        if e.get("year") and int(e["year"]) not in yrs:
            probs.append(f"year: bib {e['year']} / Crossref {sorted(yrs)}")
        fam = [a.split(",")[0] for a in s["authors"]]
        bibauth = e.get("author", "")
        if fam and norm(fam[0]) not in norm(bibauth):
            probs.append(f"lead author: Crossref {fam[0]} not in bib '{bibauth[:50]}'")
        if len(fam) != len([a for a in re.split(r"\s+and\s+", bibauth) if a.strip()]) and e["type"] != "misc":
            probs.append(f"author count: bib {len([a for a in re.split(r'\s+and\s+', bibauth) if a.strip()])} / Crossref {len(fam)}")
        if e.get("volume") and s["volume"] and str(e["volume"]) != str(s["volume"]):
            probs.append(f"volume: bib {e['volume']} / Crossref {s['volume']}")
        if e.get("number") and s["issue"] and str(e["number"]) != str(s["issue"]):
            probs.append(f"issue: bib {e['number']} / Crossref {s['issue']}")
        if e.get("pages") and s["pages"] and norm(e["pages"].replace("--", "-")) != norm(str(s["pages"]).replace("--", "-")):
            probs.append(f"pages: bib {e['pages']} / Crossref {s['pages']}")
        ven = e.get("journal") or e.get("booktitle") or ""
        if s["venue"] and ven and norm(ven)[:15] != norm(s["venue"])[:15] and not (norm(ven) in norm(s["venue"]) or norm(s["venue"]) in norm(ven)):
            probs.append(f"venue: bib '{ven[:40]}' / Crossref '{s['venue'][:50]}'")
        nfix += bool(probs)
        rows.append((e["key"], doi, "OK" if not probs else "MISMATCH", "; ".join(probs), f"{s['venue'][:50]} {s['volume'] or ''} {s['year']}"))
    out = ["# Reference check against Crossref (V9)", "",
           "<!-- header:start -->", "| Field | Value |", "|---|---|", "| Status | current |", "| Date | 2026-11-15 |", "| Owner | Mritula S |",
           "| Scope | Every DOI of `paper/references.bib` looked up in Crossref; title, year, lead author, author count, volume, issue, pages and venue compared (generated by scripts/vf_crossref.py). |",
           "| Evidence labels used | none (this file reports no result) |", "| Abbreviations | DOI = digital object identifier |", "<!-- header:end -->", "",
           f"Entries: {len(entries)}; with a DOI: {sum(1 for r in rows if r[1] not in ('no DOI',))}; mismatches: {nfix}.", "",
           "| Key | DOI | Result | Differences | Crossref venue and year |", "|---|---|---|---|---|"]
    out += [f"| {k} | {d} | {r} | {x} | {v} |" for k, d, r, x, v in rows]
    (ROOT / "docs/04_audits/REFERENCE_CHECK_VF.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(entries)} entries, {nfix} mismatches")
    for k, d, r, x, v in rows:
        if r != "OK":
            print(k, "|", r, "|", x)


if __name__ == "__main__":
    main()
