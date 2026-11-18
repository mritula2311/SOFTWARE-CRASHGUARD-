import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from crashguard.merge_c_checks import default_label, entries, merge
from crashguard.results import ORIGINS

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "c_bundle"

DOC = dict(platform="Linux-6.6-x86_64", system="Linux", compiler="gcc", compiler_version="gcc (Ubuntu 13.3.0) 13.3.0", all_ran=True, all_passed=False, checks=[
    dict(bundle="c_bundle_real", name="forest_10x9", ran=True, passes=True, n_rows=5, decision_mismatches=0, fields={"prob": dict(max_abs_diff=1.4e-7, tolerance=1e-6, passes=True)}),
    dict(bundle="c_bundle", name="n14_sat_synthetic", ran=True, passes=False, n_rows=48, fields={"applied": dict(max_abs_diff=0.0, mismatches=0, passes=True), "dv_fill_kmh": dict(max_abs_diff=9.05, tolerance=1e-3, passes=False)}),
    dict(bundle="c_bundle", name="severity_synthetic", ran=False, passes=False, reason="compile failed: no compiler")])


def test_label_comes_from_system_and_compiler():
    assert default_label(DOC) == "linux_gcc"


def test_entries_have_origin_platform_and_reasons():
    ent = entries(DOC, "linux_gcc")
    assert all(e["origin"] in ORIGINS and e["source_file"] for e in ent)
    by = {e["name"]: e for e in ent}
    assert by["cchecks.linux_gcc.c_bundle_real.forest_10x9.max_abs_diff.prob"]["origin"] == "MEASURED_SOFTWARE"
    assert "Linux-6.6" in by["cchecks.linux_gcc.c_bundle_real.forest_10x9.max_abs_diff.prob"]["notes"]
    assert by["cchecks.linux_gcc.c_bundle.n14_sat_synthetic.passes"]["value"] is False
    nr = by["cchecks.linux_gcc.c_bundle.severity_synthetic.max_abs_diff"]
    assert nr["origin"] == "NOT_RUN" and nr["value"] == "NOT_RUN" and "compile failed" in nr["notes"]


def test_merge_replaces_an_earlier_import_and_leaves_other_keys(tmp_path):
    res = tmp_path / "results.json"
    res.write_text(json.dumps([dict(name="export.max_abs_diff", value="NOT_RUN", unit="p", origin="NOT_RUN", source_file="x", notes="blocked"),
                               dict(name="cchecks.linux_gcc.stale", value=1, unit="x", origin="MEASURED_SOFTWARE", source_file="x", notes="")]), encoding="utf-8")
    j = tmp_path / "c.json"
    j.write_text(json.dumps(DOC), encoding="utf-8")
    merge(j, results=res)
    names = {e["name"]: e for e in json.loads(res.read_text(encoding="utf-8"))}
    assert "cchecks.linux_gcc.stale" not in names
    assert names["export.max_abs_diff"]["value"] == "NOT_RUN"  # Windows rows are not touched
    assert names["cchecks.linux_gcc.all_passed"]["value"] is False


def test_committed_bundle_files_match_the_manifest():
    man = json.loads((BUNDLE / "manifest.json").read_text(encoding="utf-8"))
    assert {c["name"] for c in man["checks"]} >= {"forest_15x6", "forest_10x9", "severity_synthetic", "n14_sat_synthetic"}
    for c in man["checks"]:
        d = BUNDLE / c["dir"]
        assert (d / "harness.c").exists()
        assert (d / "expected.bin").stat().st_size == c["n_rows"] * c["n_out"] * 8
        assert (d / "in.bin").stat().st_size % (c["n_rows"] * 4) == 0
        assert not c["real_data"]


@pytest.mark.skipif(shutil.which("gcc") is None or shutil.which("bash") is None, reason="needs gcc and bash")
def test_script_runs_the_committed_bundle_with_gcc(tmp_path):
    out = tmp_path / "c.json"
    subprocess.run(["bash", "scripts/c_checks.sh", str(out)], cwd=ROOT, check=False, capture_output=True)
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["all_ran"]
    forests = [c for c in doc["checks"] if c["name"].startswith("forest")]
    assert forests and all(c["passes"] for c in forests)


def test_compare_script_flags_a_difference(tmp_path):
    import array

    d = tmp_path / "b" / "chk"
    d.mkdir(parents=True)
    exp = array.array("d", [0.1, 0.2, 0.3])
    (d / "expected.bin").write_bytes(exp.tobytes())
    (tmp_path / "b" / "manifest.json").write_text(json.dumps(dict(checks=[dict(name="chk", dir="chk", n_rows=3, n_out=1, fields=["prob"], tolerance={"prob": 1e-6}, exact_fields=[], decision_threshold=0.25)])), encoding="utf-8")
    good = tmp_path / "good.out"
    good.write_bytes(np.array([0.1, 0.2, 0.3], np.float32).tobytes())
    bad = tmp_path / "bad.out"
    bad.write_bytes(np.array([0.1, 0.2, 0.31], np.float32).tobytes())
    run = lambda p: json.loads(subprocess.run([sys.executable, str(ROOT / "scripts" / "c_compare.py"), str(tmp_path / "b"), "chk", str(p)], capture_output=True, text=True).stdout)  # noqa: E731
    assert run(good)["passes"] and not run(bad)["passes"]
    assert run(good)["decision_mismatches"] == 0
