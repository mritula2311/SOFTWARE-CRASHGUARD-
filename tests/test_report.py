"""Every number in the report must come from results.json (PRD FR8); wording rules from CLAUDE.md."""
import re
from pathlib import Path

import pytest

from crashguard import report as R

RESULTS = Path("results/results.json")
pytestmark = pytest.mark.skipif(not RESULTS.exists(), reason="needs make all")

# Design constants and level labels that are written in the text on purpose (specs, config, loss levels).
DESIGN_CONSTANTS = {0, 1, 2, 3, 4, 5, 6, 9, 10, 13, 14, 15, 16, 26, 30, 42, 60, 97, 100, 200, 1.0, 1.8, 2.8, 1.5, 2.0, 2.5, 3.0, 0.95, 433, 1600, 169, 8, 32766, 20, 50, 7, 420, 24, 32, 40, 56, 64, 260, 250, 0.5, 1.4, 1.9, 12, 13, 1.5, 2.8, 80, 49, 563, 9, 3, 90, 95, 563.7, 1317, 6050, 38, 39, 41, 42, 0.1, 0.25, 208, 214, 36, 62, 400, 800, 1800, 97.5, 500, 1000, 2000, 2015, 2017, 2018, 350, 571.208, 571.214, 600}
NUM = re.compile(r"(?<![A-Za-z_\d.])\d+(?:\.\d+)?(?:e[+-]?\d+)?")


@pytest.fixture(scope="module")
def marked():
    return R.build()


def test_no_hand_typed_numbers(marked):
    seg = re.sub(f"{R.L}[^{R.R_}]*{R.R_}", " ", marked)
    seg = re.sub(r"`[^`]*`", " ", seg)  # file names and commands
    seg = re.sub(r"(Figure|Table|Section)\s+\d+", " ", seg)
    seg = re.sub(r"(?m)^#+ \d+\.", " ", seg)
    seg = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", seg)
    stray = [t for t in NUM.findall(seg) if float(t) not in DESIGN_CONSTANTS]
    assert not stray, f"numbers not taken from results.json: {sorted(set(stray))}"


def test_marked_numbers_exist_in_results(marked):
    res = R.Res()
    values = [e["value"] for e in res.r.values() if isinstance(e["value"], (int, float)) and not isinstance(e["value"], bool)]
    bad = []
    for tok in re.findall(f"{R.L}([^{R.R_}]*){R.R_}", marked):
        if tok == "NOT_RUN":
            continue
        t = float(tok)
        dec = len(tok.split(".")[1]) if "." in tok and "e" not in tok else 0
        tol = 0.0061 * abs(t) if "e" in tok else 0.5 * 10 ** -dec + 1e-12
        if not any(abs(v - t) <= tol for v in values):
            bad.append(tok)
    assert not bad, bad[:10]


def test_forbidden_words_and_sections(marked):
    low = marked.lower()
    for w in ("first", "novel", "state-of-the-art"):
        assert not re.search(rf"\b{w}\b", low), w
    for h in ("What was run", "Tables", "Figures", "What these results do and do not show", "Still needed from hardware"):
        assert h in marked


def test_not_run_items_are_labelled(marked):
    assert "NOT_RUN" in marked and "not yet measured" in marked
