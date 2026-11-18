"""Consistency gates: a document may not state an attack-case count that differs from results.json, and every results.json entry needs an origin label."""
import json
import re
from pathlib import Path

import pytest

from crashguard.attack_doc import MARK, fill_markers, render
from crashguard.results import ORIGINS

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results" / "results.json"

PATTERNS = [
    re.compile(r"\b(\d+)[- ]case attack"),
    re.compile(r"\b(\d+)\s+(?:simulated\s+|new\s+)?attack cases?\b"),
    re.compile(r"\b(\d+) of (\d+)\s+(?:simulated\s+|attack\s+)?cases\b"),
    re.compile(r"attack suite (?:of|with|has|had) (\d+)\b"),
    re.compile(r"\b(\d+)\s+cases?\s+in\s+the\s+attack suite"),
]


def _files():
    out = [ROOT / "README.md", ROOT / "docs/05_data_code/REPRODUCE.md", ROOT / "docs/07_log/PROGRESS.md"]
    out += [p for p in (ROOT / "docs").rglob("*.md") if "archive" not in p.parts]
    out += list((ROOT / "report").glob("*.md"))
    out += list((ROOT / "src" / "crashguard").glob("*.py"))
    return out


@pytest.mark.skipif(not R.exists(), reason="results.json not built")
def test_attack_count_in_documents_matches_results():
    r = {e["name"]: e["value"] for e in json.loads(R.read_text(encoding="utf-8"))}
    total = r["attacks.cases_total"]
    bad = []
    for p in _files():
        if p.name in ("PROGRESS.md", "PREREGISTRATION_V5.md"):
            continue  # a dated log: old counts there are history, not a claim
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            line = MARK.sub("", line)
            if "{" in line and p.suffix == ".py":
                continue  # an f-string that reads the count from results.json
            for pat in PATTERNS:
                for m in pat.finditer(line):
                    if any(int(g) != total for g in m.groups() if g):
                        bad.append(f"{p.name}:{n}: {m.group(0)!r} (results.json says {total})")
    assert not bad, "\n".join(bad)


@pytest.mark.skipif(not R.exists(), reason="results.json not built")
def test_every_entry_has_an_origin_label():
    entries = json.loads(R.read_text(encoding="utf-8"))
    assert all(e.get("origin") in ORIGINS for e in entries)
    assert all(str(e.get("notes", "")).strip() for e in entries if e["origin"] == "NOT_RUN" or e["value"] == "NOT_RUN")


@pytest.mark.skipif(not R.exists(), reason="results.json not built")
def test_new_round3_keys_have_origin_and_source():
    """Round 3 keys (round 3 prefixes) must each carry a valid origin and a source file."""
    entries = json.loads(R.read_text(encoding="utf-8"))
    new = [e for e in entries if e["name"].split(".")[0] in {"dupscan", "n20c", "n14s", "s5", "s6", "n24", "s10", "s11", "s12", "s13", "ua", "cchecks"}]
    assert all(e["origin"] in ORIGINS and e.get("source_file") for e in new)


def test_marker_is_filled_from_results(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("has <!--n:attacks.cases_total-->1<!--/n--> cases", encoding="utf-8")
    assert fill_markers(f, {"attacks.cases_total": {"value": 48}})
    assert "<!--n:attacks.cases_total-->48<!--/n-->" in f.read_text(encoding="utf-8")


def test_render_lists_every_case():
    import pandas as pd

    df = pd.DataFrame([dict(case="a", expected="x", observed="x", match=True, note=""), dict(case="b|c", expected="y", observed="z", match=False, note="n")])
    r = {"attacks.cases_total": {"value": 2, "origin": "SIMULATED"}, "attacks.cases_matching_expected": {"value": 1}}
    t = render(df, r)
    assert "2 cases, 1 behave as expected" in t and "| 01 | b/c |" in t
