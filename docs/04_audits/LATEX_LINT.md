# LaTeX lint, compile check and journal-format check (V11.1 to V11.3)

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-14 |
| Owner | Mritula S |
| Scope | Compile check with a user-level TeX engine, likely Overleaf errors in order, and the journal format check with source and date. |
| Evidence labels used | none (this file reports no result) |
| Abbreviations | AI = artificial intelligence; ESP32 = a Wi-Fi microcontroller family (Espressif); GPS = Global Positioning System; IEEE = Institute of Electrical and Electronics Engineers; KB = kilobyte; LoRa = long-range radio modulation; MAC = message authentication code; NHTSA = National Highway Traffic Safety Administration; PDF = Portable Document Format; PNG = Portable Network Graphics; SF = spreading factor (LoRa) |
<!-- header:end -->

## Compile check (V11.2)

A user-level TeX engine was used: Tectonic 0.15.0 (a single executable, no root needed), downloaded on 2026-11-15 and kept outside the repository. `scripts/vf_shim_compile.py` copies `paper/` to a work folder and compiles it.

- `ieeeaccess.cls` (template version 2026-05-13, downloaded from the IEEE Access author page) cannot be run by Tectonic: it is an XeTeX engine and the class uses pdfTeX primitives (error at `ieeeaccess.cls:281`). The Access class was therefore NOT compiled here.
- `main.tex` was compiled with the class IEEEtran (journal option, two columns, Times) and shims for the Access-only commands (`\history`, `\doi`, `\tfootnote`, `\corresp`, `\titlepgskip`, `\EOD`, `\address`, `\authorrefmark`). Result: 0 errors, 0 undefined references or citations, 5 overfull boxes (each under 8 pt), **12 pages** with 8 figures and 5 tables. This is an ESTIMATE of the Access page count (IEEE Access has a different font and margin set); the template's own limit guidance is under 20 pages.
- `supplement.tex` (article class) compiled as it is: 0 errors, 0 undefined references or citations, 154 pages (the generated tables give about 1,000 overfull-box warnings, which Overleaf shows as warnings, not errors).

## Likely Overleaf errors, in order of likelihood

| Rank | Place | Problem | Fix |
|---|---|---|---|
| 1 | `main.tex` line 4 | the Overleaf copy of `ieeeaccess.cls` may be older than the 2026-05-13 template; the sample in the template zip sets `\titlepgskip=-21pt` where `main.tex` uses `-15pt` | upload the class from the current template next to `main.tex`; adjust `\titlepgskip` if the title page is cut |
| 2 | `main.tex` lines 7 to 12 | `\usepackage{booktabs}` and `\usepackage{url}` are not in the template's package list; they are standard and expected to load | none needed; remove them only if a package clash is reported |
| 3 | `\begin{keywords}` | the class defines the `keywords` environment (line 630 of the class); the template says to list keywords in alphabetical order, which the paper now does | none |
| 4 | figures `figures/*.pdf` | all 8 main-text figure files exist (`pp_arch`, `vf_audit`, `pp_heat`, `pp_p4a`, `vf_proto`, `pp_r3`, `vf_sim`, `vf_deploy`); upload the whole `paper/` folder so the relative paths resolve | keep the folder structure |
| 5 | `figure*` and `table*` floats | wide floats may move to the next page in a two-column class; the text refers to them by label only | accept the float placement or change `[t]` to `[!t]` |
| 6 | `references.bib` | 50 entries, 0 non-ASCII characters (accents are written as LaTeX macros), `\&` escaped; `IEEEtran.bst` is provided by the template | none |
| 7 | the abstract | uses macros (`\SevTests{}` and the others) from `paper/generated/numbers.tex`; if a macro is undefined the compile stops with a clear message | upload `paper/generated/numbers.tex` with the paper |
| 8 | `\EOD` | defined in the class | none |

## Journal format check (V11.3), source and date

Source: https://ieeeaccess.ieee.org/authors/submission-guidelines/ (opened 2026-11-15).

| Requirement stated on the page | Paper | Match |
|---|---|---|
| Double-column, single-spaced, IEEE Access template; a LaTeX or Word source and a PDF that match exactly | `ieeeaccess` class; the PDF must be made on Overleaf | to do by the author |
| Keywords: minimum 3, maximum 10 | 6 | yes |
| Page count under 20 pages for readability | 12 (estimate) | yes |
| File size at most 40 MB | figures are PDF and PNG of 20 to 150 KB each | yes |
| Define acronyms when they appear in the body, even if defined in the abstract | acronyms in the body were defined where they appear in this run (LoRa, SF, MAC, ECIES, DOAJ, TRID, UCI HAR, ESP32, NHTSA, LoED, FARS, UPPAAL, GPS) | yes |
| Biographies for all authors below the references; ORCID for the submitting author | not in the manuscript | listed in `paper/PLACEHOLDERS.md` |
| AI-generated text disclosed in the acknowledgements; each section with such text cites the AI system | draft disclosure written; the author must list the sections and add the citation | listed in `paper/PLACEHOLDERS.md` |
| Abstract length, figure formats and resolution, reference style, data and code policy | not stated on the page | not checked against a stated rule: abstract is 247 words, figures are PDF and PNG at 300 dpi, references use IEEEtran |

The abstract limit of 250 words, the two-column format and the IEEEtran style are the template's usual values; they were not found on the guidelines page and are not claimed as requirements.
