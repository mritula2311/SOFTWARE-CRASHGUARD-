"""R4: add or refresh the header block of every Markdown document, and write docs/README.md (the index).

Idempotent. Run after any step that regenerates documents (generators overwrite whole files and drop the block):
    python scripts/doc_headers.py            # headers + index
    python scripts/doc_headers.py --check    # exit 1 if any document lacks a current header or the index is stale

The block sits right after the first heading, between `<!-- header:start -->` and `<!-- header:end -->`. The date of an existing block is kept
unless the file is listed in TOUCHED (content revised in this release). A new block takes the date of the last commit that touched the file.
Not given a block: CLAUDE.md (tool configuration), tagged result files under results/ (edited never), the audit package sent to the dataset authors
(release/vzcrash_audit_for_authors/), data/, RESEARCH PAPERS/ and the archived run logs.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from doc_meta import ARCHIVED, CURRENT, FOLDERS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TODAY = "2026-11-14"
RESET = "--reset-dates" in sys.argv
START, END = "<!-- header:start -->", "<!-- header:end -->"
EXEMPT_PREFIX = ("results/", "release/", "data/", "RESEARCH PAPERS/", "docs/archive/logs/", ".venv/", "build/")
EXEMPT_FILES = {"CLAUDE.md"}
LABELS = ("MEASURED_SOFTWARE", "SIMULATED_HW_FORMAT", "TRACE_DRIVEN", "SIMULATED", "FORMAL", "ANALYTICAL", "EMULATED", "HARDWARE", "NOT_RUN")
# files whose content was revised in this release: the block date is today
TOUCHED = {
    "README.md", "CHANGELOG.md", "docs/README.md", "docs/00_overview/PROJECT_STATUS.md", "docs/07_log/CLEANUP_LOG.md", "docs/07_log/PATH_MAP.md",
    "docs/05_data_code/REPRODUCE.md", "docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md", "docs/05_data_code/SYNTHETIC_PROVENANCE.md", "docs/06_references/REFERENCES.md",
    "docs/06_references/REFERENCES_UNVERIFIED.md", "docs/06_references/NOVELTY_SCAN.md", "docs/06_references/LITERATURE_STATUS.md", "docs/06_references/SCOPUS_STRINGS.md",
    "docs/02_preregistration/PREREGISTRATION_V7.md", "docs/03_results/NEGATIVES_REGISTER.md", "docs/00_overview/CLAIMS_FOR_COVER_LETTER.md",
    "docs/03_results/CLAIM_EVIDENCE.md", "docs/07_log/DECISIONS.md", "docs/05_data_code/DATA_AND_CODE_STATEMENT.md",
    "docs/02_preregistration/PREREGISTRATION_V11.md", "docs/03_results/STATUS_REVERIFY.md", "docs/03_results/SIMHW_VARIANTS.md", "docs/03_results/SIMHW_RESULTS.md", "docs/03_results/SIMHW_S4_CASES.md",
    "docs/03_results/COMBINED_VERDICTS.md", "docs/04_audits/COMBINED_CLAIM_AUDIT.md", "docs/05_architecture/ARCHITECTURE.md", "docs/06_references/CHANGES.md", "docs/06_references/LITERATURE_STATUS_RELEASE_V1.md",
}
GLOSSARY = {
    "ACK": "acknowledgement frame", "AI": "artificial intelligence", "AP": "average precision", "ASI": "acceleration severity index", "AUC": "area under the ROC curve",
    "BLE": "Bluetooth Low Energy", "CDS": "Crashworthiness Data System", "CI": "confidence interval", "CNN": "convolutional neural network", "CoAP": "Constrained Application Protocol",
    "CPU": "central processing unit", "CRC": "cyclic redundancy check", "CSV": "comma-separated values", "CV": "cross-validation", "DOI": "digital object identifier",
    "EDR": "event data recorder", "EN": "European standard", "ESP32": "a Wi-Fi microcontroller family (Espressif)", "FPR": "false-positive rate", "GAN": "generative adversarial network",
    "GBM": "gradient boosting machine", "GPS": "Global Positioning System", "GPU": "graphics processing unit", "GSM": "Global System for Mobile communications",
    "HIC": "head injury criterion", "HMAC": "hash-based message authentication code", "HTTP": "Hypertext Transfer Protocol", "I2C": "inter-integrated circuit bus",
    "IEEE": "Institute of Electrical and Electronics Engineers", "IIHS": "Insurance Institute for Highway Safety", "IMU": "inertial measurement unit", "ISO": "International Organization for Standardization",
    "KB": "kilobyte", "LOTO": "leave-one-test-out", "LPWAN": "low-power wide-area network", "LoRa": "long-range radio modulation", "MAC": "message authentication code",
    "MCU": "microcontroller unit", "MDPI": "Multidisciplinary Digital Publishing Institute", "MEMS": "micro-electromechanical system", "ML": "machine learning", "MPU": "motion processing unit (an IMU part family)",
    "MQTT": "Message Queuing Telemetry Transport", "NASS": "National Automotive Sampling System", "NCAP": "New Car Assessment Programme", "NHTSA": "National Highway Traffic Safety Administration",
    "OCR": "optical character recognition", "ODR": "output data rate", "PDF": "Portable Document Format", "PDOF": "principal direction of force", "PNG": "Portable Network Graphics",
    "PPV": "positive predictive value", "PR": "precision-recall", "RAM": "random-access memory", "RF": "random forest", "ROC": "receiver operating characteristic", "RSSI": "received signal strength indicator",
    "SAE": "Society of Automotive Engineers", "SCT": "severity-classified transmission", "SF": "spreading factor (LoRa)", "SHA256": "Secure Hash Algorithm, 256-bit", "SNR": "signal-to-noise ratio",
    "SPI": "serial peripheral interface", "SRAM": "static random-access memory", "SRIHER": "Sri Ramachandra Institute of Higher Education and Research", "TCP": "Transmission Control Protocol",
    "THIV": "theoretical head impact velocity", "TLC": "the TLA+ model checker", "TLS": "Transport Layer Security", "TSTR": "train on synthetic, test on real", "UA-SCT": "uncertainty-aware SCT",
    "URL": "uniform resource locator", "V2V": "vehicle-to-vehicle", "WPC": "Wireless Planning and Coordination wing (India)", "WSL": "Windows Subsystem for Linux",
    "DoT": "Department of Telecommunications (India)", "ECE": "Economic Commission for Europe", "FMVSS": "Federal Motor Vehicle Safety Standards", "ESV": "Enhanced Safety of Vehicles (conference)",
    "PMC": "PubMed Central", "SD": "standard deviation", "IQR": "interquartile range", "TOA": "time on air", "SW": "software", "DUMMY": "synthetic placeholder data (tests only)",
    "GTF": "GPS-time freshness field", "KDF": "key derivation function", "OS-DR": "overhear-and-suppress retries with deadlines", "GS-CA": "GPS-slotted critical alerts", "MIC": "message integrity code (LoRaWAN)",
    "SX1278": "a 433 MHz LoRa radio chip", "SW-420": "a vibration switch module", "MPU6050": "an accelerometer and gyroscope chip", "UTC": "Coordinated Universal Time", "NVS": "non-volatile storage", "IOP": "Institute of Physics",
}


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def doc_files() -> list[str]:
    tracked = set(git("ls-files", "*.md").splitlines())
    new = set(git("ls-files", "--others", "--exclude-standard", "*.md").splitlines())
    out = []
    for f in sorted(tracked | new):
        if f in EXEMPT_FILES or f.startswith(EXEMPT_PREFIX) and f != "docs/archive/logs/README.md":
            continue
        if f.startswith("docs/archive/logs/") and f != "docs/archive/logs/README.md":
            continue
        if (ROOT / f).exists():
            out.append(f)
    return out


def _old_paths() -> dict[str, str]:
    try:
        import reorganise_docs as R
        return {v: k for k, v in R.MAP.items()}
    except Exception:  # the one-off script may be absent later
        return {}


OLD = _old_paths()


def last_commit_date(f: str) -> str:
    """Date of the last commit before this release that touched the file (the old path is used for a moved file)."""
    for path in (f, OLD.get(f, "")):
        if path:
            d = git("log", "-1", "--format=%cs", "--", path).strip()
            if d:
                return d
    return TODAY


def strip_ticks(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", " ", text)


def body_of(text: str) -> str:
    return re.sub(re.escape(START) + r".*?" + re.escape(END), "", text, flags=re.S)


def abbreviations(text: str) -> list[str]:
    t = strip_ticks(body_of(text))
    found = []
    for k in GLOSSARY:
        if re.search(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", t):
            found.append(k)
    # UA-SCT contains SCT; keep both only if SCT appears alone as well
    if "UA-SCT" in found and "SCT" in found and not re.search(r"(?<![\w-])SCT(?![\w-])", re.sub(r"UA-SCT", "", t)):
        found.remove("SCT")
    return sorted(found)


def title_of(text: str, f: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    return m.group(1).strip() if m else Path(f).stem


def existing_date(text: str) -> str | None:
    m = re.search(re.escape(START) + r".*?\|\s*Date\s*\|\s*([0-9-]+)\s*\|.*?" + re.escape(END), text, flags=re.S)
    return m.group(1) if m else None


def render_block(f: str, text: str) -> str:
    arch = ARCHIVED.get(f)
    scope = arch[0] if arch else CURRENT.get(f, "Document next to the code; see the first paragraph.")
    date = TODAY if f in TOUCHED else ((None if RESET else existing_date(text)) or last_commit_date(f))
    labels = [x for x in LABELS if re.search(r"(?<![A-Za-z_])" + x + r"(?![A-Za-z_])", body_of(text))]
    ab = abbreviations(text)
    rows = [("Status", "archived (superseded)" if arch else "current"), ("Date", date), ("Owner", "Mritula S"), ("Scope", scope),
            ("Evidence labels used", ", ".join(labels) if labels else "none (this file reports no result)")]
    if arch:
        rows.append(("Replaced by", f"`{arch[1]}`"))
        rows.append(("Reason", arch[2]))
    if ab:
        rows.append(("Abbreviations", "; ".join(f"{a} = {GLOSSARY[a]}" for a in ab)))
    out = [START, "| Field | Value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows] + [END]
    return "\n".join(out)


def apply(f: str, check: bool) -> bool:
    p = ROOT / f
    text = p.read_text(encoding="utf-8")
    block = render_block(f, text)
    if START in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
    else:
        m = re.search(r"^#\s+.+$", text, flags=re.M)
        if m:
            new = text[:m.end()] + "\n\n" + block + text[m.end():]
        else:
            new = f"# {Path(f).stem}\n\n{block}\n\n{text}"
    if new != text and not check:
        p.write_text(new, encoding="utf-8", newline="")
    return new != text


def _ref(path: str) -> str:
    """A backticked path when the file exists, plain text otherwise (a document that a later block writes)."""
    return f"`{path}`" if (ROOT / path).exists() else f"{path} (not yet written)"


def index_text(files: list[str]) -> str:
    lines = ["# Documentation index", "", START, "| Field | Value |", "|---|---|", "| Status | current |", f"| Date | {TODAY} |", "| Owner | Mritula S |",
             "| Scope | Index of every document in the repository, one line each, and the meaning of the study identifiers. |",
             "| Evidence labels used | none (this file reports no result) |", END, "",
             "Every document starts with a small table: status, date, owner, scope, the evidence labels it uses and the abbreviations it uses. "
             "Evidence labels: MEASURED_SOFTWARE (computed from a dataset), SIMULATED (simulation with stated assumptions), ANALYTICAL (formula), HARDWARE (the author's logs, not read here), NOT_RUN. "
             "Old paths (before 2026-11-13) are mapped in `docs/07_log/PATH_MAP.md`.", ""]
    by = {}
    for f in files:
        if f == "docs/README.md":
            continue
        by.setdefault(next((k for k, _ in FOLDERS if k and (f.startswith(k + "/")) ), "" if "/" not in f else "other"), []).append(f)
    for key, label in FOLDERS:
        fs = by.get(key, [])
        if key == "docs/archive":
            fs = fs + by.get("docs/archive/logs", [])
        if not fs:
            continue
        lines += [f"## {label}", "", "| Document | Scope |", "|---|---|"]
        for f in sorted(fs):
            rel = f if key in ("", "other") else f
            scope = ARCHIVED[f][0] if f in ARCHIVED else CURRENT.get(f, "")
            rel_link = Path(f).relative_to("docs").as_posix() if f.startswith("docs/") and f != "docs/README.md" else ("../" + f if not f.startswith("docs/") else f)
            lines.append(f"| [`{rel}`]({rel_link}) | {scope} |")
        lines.append("")
    lines += ["## Study identifiers", "",
              "| Identifier | Meaning | Defined in |", "|---|---|---|",
              "| N1 to N34 | Candidate contributions (novelty points), numbered in order of appearance | `docs/06_references/NOVELTY.md`, `docs/06_references/NOVELTY_SCAN.md`, `report/novelty_summary.md` |",
              "| H-a to H-c, H-B2 | Hypotheses of the UA-SCT and layers studies | `docs/02_preregistration/PREREGISTRATION.md` |",
              "| S1 to S13, T1 to T17 | Software studies and closing tasks of round 3 | `docs/02_preregistration/EXPERIMENTS.md`, `docs/07_log/TIME_LOG.md` |",
              "| X1 to X8 | Journal-push algorithm studies | `docs/02_preregistration/PREREGISTRATION_V3.md` |",
              "| P1 to P4 | Positive-results push studies | `docs/02_preregistration/PREREGISTRATION_V4.md` |",
              "| B, C, F, G | Finishing-round blocks | `docs/02_preregistration/PREREGISTRATION_V5.md` |",
              "| R, P, Q, A, L, E | Release blocks (cleanup, physics generator, reruns, protocol algorithms, literature, audit) | " + _ref("docs/02_preregistration/PREREGISTRATION_V7.md") + " |",
              "| H1 to H6 | Car (hardware) experiments; not run here | `docs/02_preregistration/EXPERIMENTS.md` |",
              "| `r.`, `ph.`, `q.`, `pa.` | Result-key prefixes of the release (repository, physics generator, reruns, protocol algorithms) | `results/results.json` |", ""]
    return "\n".join(lines)


def main() -> int:
    check = "--check" in sys.argv
    files = doc_files()
    frozen = {"docs/02_preregistration/PREREGISTRATION_V19.md"}  # kept byte-identical to the committed file whose SHA-256 is recorded (round 7b)
    changed = [f for f in files if f != "docs/README.md" and f not in frozen and apply(f, check)]
    idx = ROOT / "docs/README.md"
    new_idx = index_text(files + (["docs/README.md"] if "docs/README.md" not in files else []))
    stale = (not idx.exists()) or idx.read_text(encoding="utf-8") != new_idx
    if stale and not check:
        idx.write_text(new_idx, encoding="utf-8", newline="")
    missing = [f for f in files if f not in CURRENT and f not in ARCHIVED and f != "docs/README.md"]
    if missing:
        print("no registry entry (scope falls back to a generic line):", missing)
    print(f"{len(changed)} documents {'need' if check else 'got'} a header update; index {'stale' if stale else 'current'}")
    return 1 if check and (changed or stale) else 0


if __name__ == "__main__":
    sys.exit(main())
