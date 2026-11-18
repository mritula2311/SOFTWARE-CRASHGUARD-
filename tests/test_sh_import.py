"""S0: the simulated hardware-format files parse, are monotonic at 10 ms, finite, inside +-16 g and carry a SIMULATED data_origin; the manifest matches."""
import json

import pytest

from crashguard import sh_load as L


def test_every_file_parses_and_passes_schema():
    d = L.load_all()
    assert len(d["sensors"]) == 100 and len(d["protocols"]) == 11
    for name, (js, arr) in d["sensors"].items():
        assert "SIMULATED" in js["data_origin"], name
        assert arr["acc"].shape == (300, 3)


def test_manifest_matches_and_detects_change(tmp_path):
    assert L.verify_manifest() == []


def test_checker_rejects_bad_files():
    good = json.loads((L.BASE / "sensor_logs" / "H1-front-01.json").read_text(encoding="utf-8"))
    bad = json.loads(json.dumps(good))
    bad["rows"][5][0] = bad["rows"][4][0]
    with pytest.raises(L.SchemaError):
        L.check_sensor(bad)
    bad = json.loads(json.dumps(good))
    bad["rows"][7][1] = 17.0
    with pytest.raises(L.SchemaError):
        L.check_sensor(bad)
    bad = json.loads(json.dumps(good))
    bad["rows"][7][2] = float("nan")
    with pytest.raises(L.SchemaError):
        L.check_sensor(bad)
    bad = json.loads(json.dumps(good))
    bad["data_origin"] = "measured"
    (L.BASE / "_tmp_check.json").write_text(json.dumps(bad), encoding="utf-8")
    try:
        with pytest.raises(L.SchemaError):
            L.load_json(L.BASE / "_tmp_check.json")
    finally:
        (L.BASE / "_tmp_check.json").unlink()
