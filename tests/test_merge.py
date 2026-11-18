"""Merge schema and behaviour. Uses synthetic DUMMY files only; results/ must stay untouched."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "dummy"))
spec = importlib.util.spec_from_file_location("ingest_hardware", ROOT / "merge" / "ingest_hardware.py")
ih = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ih)
import make_dummy  # noqa: E402

RESULTS = ROOT / "results" / "results.json"
HAVE_TRAINING_DATA = (ROOT / "data" / "processed" / "features.parquet").exists()


def test_missing_hw_events_gives_not_run_for_every_experiment(tmp_path):
    s = ih.analyse(tmp_path, tmp_path / "out", dummy=True)
    names = {i["name"]: i for i in s.items}
    for e in ih.EXPERIMENTS:
        assert names[f"hw.{e}"]["origin"] == "NOT_RUN" and names[f"hw.{e}"]["value"] == "NOT_RUN"


def test_wrong_schema_is_rejected(tmp_path):
    (tmp_path / "hw_events.csv").write_text("event_id,experiment\n1,E1\n")
    df, why = ih.load(tmp_path, "hw_events.csv")
    assert df is None and "missing columns" in why


@pytest.mark.skipif(not HAVE_TRAINING_DATA, reason="needs make features")
def test_dummy_run_produces_all_experiments_and_leaves_results_alone(tmp_path):
    before = RESULTS.read_bytes() if RESULTS.exists() else b""
    make_dummy.make(tmp_path)
    out = tmp_path / "out"
    s = ih.analyse(tmp_path, out, dummy=True)
    names = [i["name"] for i in s.items]
    for prefix in ("hw.H1.", "hw.H2.rule.", "hw.H3.", "hw.H4.", "hw.H5.", "hw.H2.transfer.all.", "hw.H6."):
        assert any(n.startswith(prefix) for n in names), prefix
    assert (out / "dummy_results.json").exists()
    assert (out / "h1_direction_confusion.png").exists()
    assert (RESULTS.read_bytes() if RESULTS.exists() else b"") == before
    att = {i["name"]: i["value"] for i in s.items}
    assert att["hw.H4.cases_matching_expected"] == 17  # 18 dummy rows, one deliberate mismatch


def test_old_experiment_ids_are_mapped_and_severity_is_not_analysed(tmp_path):
    make_dummy.make(tmp_path)
    ev = ih.pd.read_csv(tmp_path / "hw_events.csv")
    ev["experiment"] = ev.experiment.replace({"H1": "E1", "H2": "E2", "H3": "E4"})
    ev.to_csv(tmp_path / "hw_events.csv", index=False)
    s = ih.analyse(tmp_path, tmp_path / "out", dummy=True)
    names = [i["name"] for i in s.items]
    assert any(n.startswith("hw.H1.") for n in names) and any(n.startswith("hw.H3.") for n in names)
    assert not any(n.startswith("hw.E") for n in names)
