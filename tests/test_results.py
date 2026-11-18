import json

import pytest

from crashguard.results import record


def test_record_writes_origin_and_replaces(tmp_path):
    p = tmp_path / "results.json"
    record("a", 1, "x", "MEASURED_SOFTWARE", "f", path=p)
    record("a", 2, "x", "MEASURED_SOFTWARE", "f", path=p)
    entries = json.loads(p.read_text())
    assert len(entries) == 1 and entries[0]["value"] == 2 and entries[0]["origin"] == "MEASURED_SOFTWARE"


def test_record_rejects_unknown_origin(tmp_path):
    with pytest.raises(ValueError):
        record("a", 1, "x", "TYPICAL", "f", path=tmp_path / "r.json")
