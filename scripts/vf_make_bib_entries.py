"""V5 and V9: write docs/06_references/REFERENCES_VF.bib from Crossref records (authors with given names, title, venue, volume, issue, pages, year) plus a few web and data records.

    python scripts/vf_make_bib_entries.py

Entries for DOIs are built only from the Crossref record (nothing typed by hand except the key and the entry type). Records that have no DOI are written from the fields read at the page named in `note`.
scripts/pp_make_bib.py gives this file precedence over its own manual entries.
"""
from __future__ import annotations

import html
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vf_crossref as X  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "06_references" / "REFERENCES_VF.bib"

ACC = {"́": "'", "̀": "`", "̂": "^", "̈": '"', "̃": "~", "̌": "v ", "̧": "c ", "̊": "r "}


def tex(s: str) -> str:
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", "", s).replace("‐", "-").replace("‑", "-").replace("–", "--").replace("’", "'").replace("“", "``").replace("”", "''")
    out = []
    for ch in unicodedata.normalize("NFD", s):
        if unicodedata.combining(ch):
            m = ACC.get(ch)
            if m and out:
                base = out.pop()
                out.append("{\\" + m + base + "}" if m[-1] == " " else "{\\" + m + "{" + base + "}}")
            continue
        out.append(ch)
    s = "".join(out).replace("&", "\\&").replace("_", "\\_").replace("#", "\\#")
    return s.replace("ø", "{\\o}")


def authors(m: dict) -> str:
    out = []
    for a in m.get("author", []):
        if "family" in a:
            fam, giv = tex(a["family"]), tex(a.get("given", ""))
            out.append(f"{fam}, {giv}" if giv else fam)
        else:
            out.append("{" + tex(a.get("name", "?")) + "}")
    return " and ".join(out)


def entry(key: str, doi: str, typ: str, extra: dict | None = None, note: str = "") -> str:
    m = X.fetch(doi)
    if not m:
        raise SystemExit(f"{doi} not found in Crossref")
    s = X.summary(m)
    y = s["print_year"] or s["online_year"] or s["year"]
    f = {"author": authors(m), "title": "{" + tex(s["title"]) + "}"}
    venue = tex(s["venue"])
    if typ == "article":
        f["journal"] = venue
    elif typ == "inproceedings":
        f["booktitle"] = venue
    elif typ == "incollection":
        f["booktitle"] = venue
    f["year"] = str(y)
    if s["volume"]:
        f["volume"] = s["volume"]
    if s["issue"]:
        f["number"] = s["issue"]
    if s["pages"]:
        f["pages"] = str(s["pages"]).replace("-", "--") if "-" in str(s["pages"]) and "--" not in str(s["pages"]) else str(s["pages"])
    f["doi"] = m["DOI"]
    if extra:
        f.update(extra)
    if note:
        f["note"] = note
    body = ",\n".join(f"  {k} = {{{v}}}" if k not in ("year",) else f"  {k} = {{{v}}}" for k, v in f.items())
    return f"@{typ}{{{key},\n{body},\n}}\n"


# (key, DOI, type, extra fields, note)
DOI_ENTRIES = [
    ("Manuel2021_sn", "10.1007/s42452-021-04377-y", "article", None, ""),
    ("Manuel2022_access", "10.1109/ACCESS.2022.3178437", "article", None, ""),
    ("Alkhaiwani2023_su", "10.3390/su15108314", "article", None, ""),
    ("Abdelhady2026_access", "10.1109/ACCESS.2026.3660731", "article", None, ""),
    ("Kagai2026_telecom", "10.3390/telecom7050123", "article", None, ""),
    ("Kumar2026_access", "10.1109/ACCESS.2026.3712035", "article", None, ""),
    ("Yang2026_bioeng", "10.3390/bioengineering13090965", "article", None, ""),
    ("Marciano2024_me", "10.1109/me61309.2024.10789689", "inproceedings", None, ""),
    ("Jabbari2022_tii", "10.1109/tii.2021.3075440", "article", None, "first published online 2021"),
    ("Vinodhini2025_dac5692", "10.1002/dac.5692", "article", None, "first published online 2023"),
    ("Hetz2026_trip", "10.1016/j.trip.2026.102109", "article", None, ""),
    ("Jameian2021_rsn", "10.1049/rsn2.12045", "article", None, ""),
    ("Liu2022_isprs", "10.5194/isprs-archives-XLIII-B1-2022-227-2022", "article", None, ""),
    ("Meier2013_tamarin", "10.1007/978-3-642-39799-8_48", "inproceedings", None, ""),
    ("Blanchet2016_proverif", "10.1561/3300000004", "article", None, ""),
    ("Magrin2017_ns3lora", "10.1109/icc.2017.7996384", "inproceedings", None, "the ns-3 lorawan module is described here"),
    ("Riley2010_ns3", "10.1007/978-3-642-12331-3_2", "incollection", None, ""),
    ("Sucerquia2017_sisfall", "10.3390/s17010198", "article", None, ""),
    ("Carneiro2023", "10.1109/NOMS56928.2023.10154409", "inproceedings", None, "record read; abstract not read"),
    ("dong2024", "10.1109/ISSRE62328.2024.00057", "inproceedings", None, ""),
    ("tamang2023", "10.1145/3616388.3617542", "inproceedings", None, ""),
    ("nessa2020", "10.1109/cns48642.2020.9162318", "inproceedings", None, "abstract read; full text not available to this study"),
    ("wesemeyer2020", "10.1109/EuroSP48549.2020.00034", "inproceedings", None, ""),
    ("khan2019", "10.1109/DCOSS.2019.00042", "inproceedings", None, "arXiv:2009.09397"),
    ("loed_data20", "10.1145/3419016.3431491", "inproceedings", None, "data descriptor of the LoED dataset"),
    ("brno", "10.3390/data6060062", "article", None, "Zenodo record 6228358"),
    ("Dima2017_iop", "10.1088/1757-899x/252/1/012007", "article", None, ""),
]

MANUAL = r"""
@misc{vzcrash,
  author = {Bianconcini, Tommaso and Pi{\~n}eiro Monteagudo, Henrique and Pjetri, Aurel and Trinci, Tomaso and Taccari, Leonardo},
  title = {{VZCrash}: A Large-Scale {IMU} Dataset of Ego-Vehicle Crashes},
  year = {2026},
  eprint = {2606.06074},
  archiveprefix = {arXiv},
  note = {Dataset card: Hugging Face, vzc-research-chapter/VZCrash, revision 42e1482d005c0e545379d6cfa4939486c9fe4249, licence CC BY-NC 4.0 (gated); accessed 2026-11-15},
  url = {https://arxiv.org/abs/2606.06074},
}

@misc{choir,
  author = {Rafe, Amir and Das, Subasish},
  title = {{CHOIR}: heterogeneity-aware conformal prediction for crash injury severity across driver safety strata},
  year = {2026},
  eprint = {2609.11592},
  archiveprefix = {arXiv},
  note = {abstract read},
  url = {https://arxiv.org/abs/2609.11592},
}

@misc{loed,
  author = {Bhatia, Laksh and Breza, Michael and Marfievici, Ramona and McCann, Julie A.},
  title = {{LoED}: The {LoRaWAN} at the Edge Dataset},
  year = {2020},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.4121430},
  note = {Record 4121430, licence CC BY 4.0; file LoED\_LoRaWAN\_at\_edge\_dataset.zip, SHA-256 8960cc3a..., accessed 2026-11-14},
  url = {https://zenodo.org/records/4121430},
}

@misc{sniffer,
  author = {Povalac, Ales and Kral, Jan},
  title = {{LoRaWAN} Traffic Analysis Dataset},
  year = {2023},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.7919213},
  note = {Version v1, 10 May 2023, licence CC BY 4.0; file csv.zip, SHA-256 25a092ff..., accessed 2026-11-15},
  url = {https://zenodo.org/records/7919213},
}

@misc{sisfall_zenodo,
  title = {{SisFall} (copy deposited on Zenodo, record 22212281, no creators listed on the record)},
  year = {2026},
  publisher = {Zenodo},
  doi = {10.5281/zenodo.22212281},
  note = {Licence CC BY 4.0 as stated on the record; file SisFall.zip, SHA-256 dd0f9cf1..., accessed 2026-11-15; the original dataset is Sucerquia et al. 2017},
  url = {https://zenodo.org/records/22212281},
}

@misc{ucihar,
  author = {Reyes-Ortiz, Jorge and Anguita, Davide},
  title = {Human Activity Recognition Using Smartphones},
  year = {2013},
  publisher = {UCI Machine Learning Repository},
  doi = {10.24432/C54S4K},
  note = {Licence CC BY 4.0 as recorded in V16 section 15.1; file uci\_har.zip, SHA-256 c00b8030..., accessed 2026-11-15},
  url = {https://archive.ics.uci.edu/dataset/240},
}

@misc{nhtsa,
  author = {{National Highway Traffic Safety Administration}},
  title = {Vehicle Crash Test Database (public {NRD} API)},
  year = {2026},
  note = {US government work, public; catalogue and pulses downloaded 2026-11-12},
  url = {https://www.nhtsa.gov/research-data/research-testing-databases},
}

@misc{fars,
  author = {{National Highway Traffic Safety Administration}},
  title = {Fatality Analysis Reporting System ({FARS}), national CSV files 2019 to 2022},
  year = {2026},
  note = {US government work, public; files fars2019.zip to fars2022.zip (SHA-256 prefixes 0974abb9, b2806902, 743c19a1, 989448d7), accessed 2026-11-15},
  url = {https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars},
}

@misc{geonames,
  author = {{GeoNames}},
  title = {{GeoNames} gazetteer, cities15000},
  year = {2026},
  note = {Licence CC BY 4.0; file cities15000.zip, SHA-256 ce7a4055..., accessed 2026-11-15},
  url = {https://download.geonames.org/export/dump/},
}

@misc{tamarin,
  author = {{Tamarin Team}},
  title = {The {Tamarin} prover, version 1.12.0, with {Maude} 3.5.1},
  year = {2026},
  note = {tool versions used in this study},
  url = {https://tamarin-prover.com},
}

@misc{proverif,
  author = {Blanchet, Bruno and Cheval, Vincent and Sylvestre, Marc},
  title = {{ProVerif} 2.05: Cryptographic Protocol Verifier},
  year = {2026},
  note = {authors as printed in the tool banner of version 2.05; built from the source archive (SHA-256 4871f53c...)},
  url = {https://bblanche.gitlabpages.inria.fr/proverif/},
}

@misc{ns3lorawan,
  author = {{ns-3 project} and {SIGNET Lab, University of Padova}},
  title = {{ns-3} 3.48 with the {lorawan} module, commit e45b4af, and a local patch},
  year = {2026},
  note = {local patch: xsim/ns3/patches/lorawan-v0.3.7-2-ge45b4af-local.patch in the repository},
}

@misc{wusk,
  author = {Wusk, G. and Gabler, H. C.},
  title = {Evaluation of Vehicle-Based Crash Severity Metrics ({$\Delta V$}, {ASI}, {OLC} against dummy injury criteria in frontal {NCAP} tests)},
  note = {25th ESV Conference, paper 25-0407; title as listed in a TRID record, content read from the PDF; year, DOI and given names not verified},
}
"""


def main() -> None:
    out = ["% generated by scripts/vf_make_bib_entries.py (Crossref records for the DOI entries; see the note field of the others)", ""]
    for key, doi, typ, extra, note in DOI_ENTRIES:
        out.append(entry(key, doi, typ, extra, note))
    out.append(MANUAL.strip() + "\n")
    OUT.write_text("\n".join(out), encoding="utf-8")
    print("entries", len(DOI_ENTRIES), "+ manual", len(re.findall(r"^@", MANUAL, re.M)))


if __name__ == "__main__":
    main()
