"""The draft email to the VZCrash authors: numbers from results.json, nothing sent, plain wording."""
import re
from pathlib import Path

import pytest

from crashguard import report as R
from crashguard import vzcrash_email as E

pytestmark = pytest.mark.skipif(not Path("results/results.json").exists(), reason="needs make all")
NUM = re.compile(r"(?<![A-Za-z_\d.#])\d+(?:\.\d+)?")
ALLOWED = {1, 2, 3, 4.0, 15, 0.005}  # list numbering, licence version, the near-duplicate tolerance named in the text


def test_email_is_a_draft_with_numbers_from_results():
    m = E.build()
    seg = re.sub(f"{R.L}[^{R.R_}]*{R.R_}", " ", m)
    seg = re.sub(r"`[^`]*`", " ", seg)
    seg = re.sub(r"arXiv \d{4}\.\d{5}", " ", seg)
    stray = [t for t in NUM.findall(seg) if float(t) not in ALLOWED]
    assert not stray, stray
    assert "NOT SENT" in m and "Nothing has been sent" in m
    for w in ("first", "novel", "state-of-the-art"):
        assert not re.search(rf"\b{w}\b", m.lower()), w


def test_attachment_lists_only_ids_and_metadata():
    p = Path("results/tables/vzcrash_duplicate_groups.csv")
    if not p.exists():
        pytest.skip("needs make features")
    head = p.read_text(encoding="utf-8").splitlines()[0]
    assert head == "group_id,event_id,split,class,vehiclesize,n_samples"
