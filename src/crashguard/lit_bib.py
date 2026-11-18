"""Part A3: Crossref metadata and BibTeX for every opened 2021+ journal item.

Reads DOIs from results/tables/lit_abstracts_*.txt (headers written by lit_search) plus EXTRA,
asks Crossref once per DOI (1 s apart, no personal data), and writes
docs/06_references/REFERENCES_2021PLUS.bib and results/tables/lit_crossref.json.
Items whose DOI Crossref does not know are written with a note and the OpenAlex fields only.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse

from crashguard.lit_search import ROOT, _get

EXTRA = [
    "10.1109/tmc.2020.3006905",          # Farha et al. (2020; context, not 2021+)
    "10.1109/jsen.2022.3193504", "10.1109/twc.2021.3136029", "10.1109/tii.2021.3124054",
    "10.1016/j.comcom.2023.12.013", "10.1109/ccnc51644.2023.10060330", "10.1109/jiot.2025.3609239",
    "10.3390/s23104609", "10.11591/eei.v12i4.4662", "10.1038/s41598-025-13465-7",
    "10.1109/jsen.2021.3130120", "10.1109/tii.2021.3075440",
]


def dois() -> list[str]:
    out: list[str] = list(EXTRA)
    for f in sorted((ROOT / "results" / "tables").glob("lit_abstracts_*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                m = re.search(r"https://doi.org/(\S+)", line)
                if m:
                    out.append(m.group(1).lower())
    seen, res = set(), []
    for d in out:
        if d not in seen:
            seen.add(d)
            res.append(d)
    return res


def bibkey(item: dict, doi: str) -> str:
    au = (item.get("author") or [{}])[0].get("family", "anon")
    yr = (item.get("issued", {}).get("date-parts") or [[0]])[0][0]
    au = re.sub(r"[^A-Za-z]", "", au)
    return f"{au}{yr}_{re.sub(r'[^a-z0-9]', '', doi.split('/')[-1])[:8]}"


def main() -> None:
    meta, bib = {}, []
    for d in dois():
        j = _get("https://api.crossref.org/works/" + urllib.parse.quote(d, safe="/"))
        time.sleep(1.0)
        it = j.get("message") if "message" in j else None
        if not it:
            meta[d] = {"status": "NOT_FOUND_IN_CROSSREF", "detail": str(j)[:120]}
            continue
        meta[d] = {"status": "OK", "title": (it.get("title") or [""])[0],
                   "container": (it.get("container-title") or [""])[0],
                   "year": (it.get("issued", {}).get("date-parts") or [[None]])[0][0]}
        au = " and ".join(f"{a.get('family', '')}, {a.get('given', '')}".strip(", ") for a in it.get("author", [])) or "Anon"
        key = bibkey(it, d)
        typ = "article" if it.get("type") == "journal-article" else "inproceedings"
        lines = [f"@{typ}{{{key},", f"  author = {{{au}}},", f"  title = {{{meta[d]['title']}}},",
                 f"  {'journal' if typ == 'article' else 'booktitle'} = {{{meta[d]['container']}}},",
                 f"  year = {{{meta[d]['year']}}},"]
        for k_src, k_bib in (("volume", "volume"), ("issue", "number"), ("page", "pages")):
            if it.get(k_src):
                lines.append(f"  {k_bib} = {{{it[k_src]}}},")
        lines.append(f"  doi = {{{d}}},")
        lines.append("}")
        bib.append("\n".join(lines))
    (ROOT / "results" / "tables" / "lit_crossref.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    (ROOT / "docs" / "06_references" / "REFERENCES_2021PLUS.bib").write_text(
        "% Crossref metadata for items opened in the Part A literature check (2026-11-14)\n\n" + "\n\n".join(bib) + "\n",
        encoding="utf-8")
    print(sum(1 for m in meta.values() if m["status"] == "OK"), "of", len(meta), "found")


if __name__ == "__main__":
    main()
