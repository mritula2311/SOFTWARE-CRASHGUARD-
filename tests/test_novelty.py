"""The novelty summary must be evidence-only: numbers from results.json, no forbidden words, hardware parts NOT_RUN."""
import re
from pathlib import Path

import pytest

from crashguard import novelty as N
from crashguard import report as R

pytestmark = pytest.mark.skipif(not Path("results/results.json").exists(), reason="needs make all")
NUM = re.compile(r"(?<![A-Za-z_\d.#])\d+(?:\.\d+)?(?:e[+-]?\d+)?")
ALLOWED = {1, 2, 3, 4, 5, 6, 7, 8, 12, 14, 15, 16, 20, 25, 32, 33, 97, 200, 10, 13, 30, 50, 100, 420, 1317, 1.0, 1.1}  # design constants named in the text, plus list numbering


@pytest.fixture(scope="module")
def marked():
    return N.build()


def test_no_hand_typed_numbers_outside_prior_work(marked):
    seg = re.sub(f"{N.P_START}.*?{N.P_END}", " ", marked, flags=re.S)
    seg = re.sub(f"{R.L}[^{R.R_}]*{R.R_}", " ", seg)
    seg = re.sub(r"`[^`]*`", " ", seg)
    seg = re.sub(r"(?m)^\|\s*\d+\s*\|", "|", seg)  # rank column
    seg = re.sub(r"(19|20)\d{2}|\d{4}\.\d{5}|\d,\d{3},\d{3}", " ", seg)  # citation years, arXiv ids, patent numbers
    stray = [t for t in NUM.findall(seg) if float(t) not in ALLOWED]
    assert not stray, sorted(set(stray))


def test_forbidden_words(marked):
    for w in ("first", "novel", "state-of-the-art"):
        assert not re.search(rf"\b{w}\b", marked.lower()), w


def test_statuses_and_hardware_labels(marked):
    for pid in ("HL", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "N10", "N11", "N12", "N13", "SF"):
        assert re.search(rf"### {pid}\. ", marked)
    assert "NOT_RUN" in marked and "SUPPORTED" in marked and "PARTIAL" in marked and "NOT_YET" in marked
    r = R.Res()
    pts = {p.pid: p for p in N.points(r)}
    for pid in ("HL", "N1", "N3", "N4", "N13"):  # hardware-dependent points must not be SUPPORTED
        assert N.status_of(r, pts[pid]) in ("PARTIAL", "NOT_YET")
    assert N.status_of(r, pts["N2"]) == "NOT_YET"


def test_paragraph_length_and_scope():
    text = N.paragraph(R.Res()).replace(R.L, "").replace(R.R_, "")
    n = len(text.split())
    assert 100 <= n <= 130, n
    assert "await hardware" in text


def test_framing(marked):
    assert "Headline contribution" in marked and "Evaluation-rigour contributions" in marked
    assert "independent re-discovery of a known LoRaWAN issue in a custom point-to-point link" in marked
    r = R.Res()
    pts = {p.pid: p for p in N.points(r)}
    assert pts["N11"].group == "breakdown" and pts["N8"].group == "rigour" and pts["N9"].group == "rigour" and pts["HL"].group == "headline"
    ranked = re.search(r"## 3\. Ranked table.*?## 4\.", marked, flags=re.S).group(0)
    assert "N11" not in ranked.split("N11 is not ranked")[1]  # N11 is not a row of the ranked table
    for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
        assert h in marked
    assert not re.search(r"\bE[1-8]\b", marked.split(N.P_END)[1])  # old experiment IDs are gone outside the prior-work record
