"""Build paper/references.bib: entries for the keys cited in paper/main.tex and paper/supplement.tex.

Keys that come from the Crossref metadata of the Part A check are copied from docs/06_references/REFERENCES_2021PLUS.bib; the other keys are written here from fields that were read in documents that were opened
(docs/06_references/REFERENCES.md and LITERATURE_STATUS.md); a field that was not read is left out or marked in a note. Fails if a cited key has no entry.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_BIB = ROOT / "docs" / "06_references" / "REFERENCES_2021PLUS.bib"
VF_BIB = ROOT / "docs" / "06_references" / "REFERENCES_VF.bib"  # final verification run: Crossref-built entries; takes precedence over MANUAL and SRC_BIB
OUT = ROOT / "paper" / "references.bib"
REFS_MANUAL = ROOT / "paper" / "refs_manual.bib"  # hand-added entries (fars, geonames, gsr347, round-7 entries); takes precedence over every other source

MANUAL = r"""
@misc{vzcrash,
  title = {{VZCrash}: A Large-Scale {IMU} Dataset of Ego-Vehicle Crashes},
  author = {{VZCrash authors}},
  year = {2026},
  note = {arXiv:2606.06074; dataset card on Hugging Face (vzc-research-chapter/VZCrash), licence CC BY-NC 4.0; full author list not verified},
  url = {https://arxiv.org/abs/2606.06074},
}

@misc{nhtsa,
  title = {Vehicle Crash Test Database},
  author = {{National Highway Traffic Safety Administration}},
  year = {2026},
  note = {public API, catalogue fetched 2026-11-12},
}

@misc{loed,
  title = {{LoED}: The {LoRaWAN} at the Edge Dataset},
  author = {Bhatia, Lavanya and Breza, Michael and Marfievici, Ramona and McCann, Julie A.},
  year = {2020},
  note = {DATA '20; arXiv:2010.14211; Zenodo record 4121430; CC BY 4.0},
  url = {https://arxiv.org/abs/2010.14211},
}

@article{brno,
  title = {Measurements of {LoRaWAN} Technology in Urban Scenarios: A Data Descriptor},
  journal = {Data},
  year = {2021},
  volume = {6},
  number = {6},
  pages = {62},
  note = {Zenodo record 6228358; author list not verified},
}

@misc{wusk,
  title = {Evaluation of Vehicle-Based Crash Severity Metrics (delta-{V}, {ASI}, {OLC} against dummy injury criteria in frontal {NCAP} tests)},
  author = {Wusk, G. and Gabler, H. C.},
  note = {25th ESV Conference, paper 25-0407; title as listed in a TRID record, paper content read from the PDF; year, DOI and given names not verified},
}

@misc{choir,
  title = {{CHOIR}: groupwise and weighted conformal prediction with risk control for ordinal injury severity},
  author = {Rafe and Das},
  year = {2026},
  note = {arXiv:2609.11592; abstract opened},
  url = {https://arxiv.org/abs/2609.11592},
}

@inproceedings{tamang2023,
  title = {Fast Transmission of Massive Concurrent Alarm Messages in {LoRaWAN}},
  author = {Tamang and Heusse and Abrardo and Duda},
  booktitle = {Proc. ACM MSWiM},
  year = {2023},
  doi = {10.1145/3616388.3617542},
  note = {given names not verified},
}

@inproceedings{nessa2020,
  title = {Adaptive Latency Reduction in {LoRa} for Mission Critical Communications in Mines},
  author = {Nessa and Hussain and Fernando},
  booktitle = {Proc. IEEE CNS},
  year = {2020},
  doi = {10.1109/cns48642.2020.9162318},
}

@misc{khan2019,
  title = {A Model for Reliable Uplink Transmissions in {LoRaWAN}},
  author = {Khan and Jurdak and Portmann},
  year = {2019},
  note = {DCOSS 2019, arXiv:2009.09397; given names not verified},
  url = {https://arxiv.org/abs/2009.09397},
}

@inproceedings{Carneiro2023,
  title = {A Crash Response System using {LoRa}-based {V2X} Communications},
  author = {Carneiro and Batista and Hirata Junior and Ullah},
  booktitle = {Proc. IEEE/IFIP NOMS},
  year = {2023},
  doi = {10.1109/NOMS56928.2023.10154409},
  note = {record opened; abstract not read},
}

@inproceedings{wesemeyer2020,
  title = {Extensive Security Verification of the {LoRaWAN} Key-Establishment: Insecurities \& Patches},
  author = {Wesemeyer and Boureanu and Smith and Treharne},
  booktitle = {Proc. IEEE EuroS\&P},
  year = {2020},
  doi = {10.1109/EuroSP48549.2020.00034},
  note = {record read on Xplore (title, authors, venue, DOI)},
}

@inproceedings{dong2024,
  title = {A Security Verification Framework for the {LoRaWAN} Protocol with Application in the Manufacturing Industry},
  author = {Dong and Zhu and Chen and Ge},
  booktitle = {Proc. ISSRE},
  year = {2024},
  pages = {535--546},
  doi = {10.1109/ISSRE62328.2024.00057},
  note = {ECNU record; given names not verified},
}

@misc{tamarin,
  title = {The {Tamarin} prover, version 1.12.0, with {Maude} 3.5.1},
  author = {{Tamarin team}},
  year = {2026},
  url = {https://tamarin-prover.com},
  note = {tool versions used in this study},
}

@misc{ns3lorawan,
  title = {{ns-3} 3.48 with the {lorawan} module (signetlabdei), commit e45b4af},
  author = {{ns-3 project} and {Signet Lab, University of Padova}},
  year = {2026},
  note = {local changes listed in the supplement},
}
"""


def main() -> int:
    cited: set[str] = set()
    for f in ("main.tex", "supplement.tex"):
        p = ROOT / "paper" / f
        if p.exists():
            for m in re.finditer(r"\\cite\{([^}]*)\}", p.read_text(encoding="utf-8")):
                cited.update(k.strip() for k in m.group(1).split(","))
    src = SRC_BIB.read_text(encoding="utf-8")
    entries = {m.group(2): m.group(0) for m in re.finditer(r"@(\w+)\{([^,]+),.*?\n\}\n", src, flags=re.S)}
    manual = {m.group(2): m.group(0) for m in re.finditer(r"@(\w+)\{([^,]+),.*?\n\}\n", MANUAL + "\n", flags=re.S)}
    vf_text = (VF_BIB.read_text(encoding="utf-8") + "\n") if VF_BIB.exists() else ""
    vf = {m.group(2): m.group(0) for m in re.finditer(r"@(\w+)\{([^,]+),.*?\n\}\n", vf_text, flags=re.S)}
    rm_text = (REFS_MANUAL.read_text(encoding="utf-8") + "\n") if REFS_MANUAL.exists() else ""
    rm = {m.group(2): m.group(0) for m in re.finditer(r"@(\w+)\{([^,]+),.*?\n\}\n", rm_text, flags=re.S)}
    missing = sorted(k for k in cited if k not in entries and k not in manual and k not in vf and k not in rm)
    out = ["% generated by scripts/pp_make_bib.py; only keys cited in main.tex and supplement.tex"]
    for k in sorted(cited):
        if k in rm:
            out.append(rm[k].rstrip())
        elif k in vf:
            out.append(vf[k].rstrip())
        elif k in manual:
            out.append(manual[k].rstrip())
        elif k in entries:
            out.append(entries[k].rstrip())
    text = ("\n\n".join(out) + "\n").replace("&amp;", "\\&")
    for ch, tex in {"®": "\\textregistered{}", "ü": '{\\"u}', "ı": "{\\i}", "ş": "{\\c{s}}"}.items():
        text = text.replace(ch, tex)
    OUT.write_text(text, encoding="utf-8")
    print("cited", len(cited), "written", len(out) - 1, "missing", missing)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
