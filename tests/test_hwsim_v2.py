"""S1: the variant generator is deterministic and each fault does what it says."""
import json
from pathlib import Path

import numpy as np

from crashguard import hwsim_v2 as H
from crashguard import sh_load as L


def _first(tmp_path, name):
    H.generate(name, tmp_path)
    return tmp_path / name


def test_deterministic_and_schema(tmp_path):
    a = H.generate("V00_base", tmp_path / "a")
    b = H.generate("V00_base", tmp_path / "b")
    assert a["sha256"] == b["sha256"]
    for p in sorted((tmp_path / "a" / "V00_base" / "sensor_logs").glob("*.json"))[:20]:
        L.check_sensor(L.load_json(p), p.name)
    assert a["n_sensor_events"] == 200


def test_flip_and_tilt_and_rate(tmp_path):
    base = json.loads((_first(tmp_path, "V00_base") / "sensor_logs" / "H1-front-01.json").read_text())
    fx = json.loads((_first(tmp_path, "F_x") / "sensor_logs" / "H1-front-01.json").read_text())
    # same seed index differs, so compare the sign of the impact axis over all front events instead
    def mean_x(d):
        a = np.array([r[1] for r in d["rows"]])
        return a[np.abs(a - np.median(a)).argmax()] - np.median(a)
    assert mean_x(base) < 0 < mean_x(fx)
    t30 = json.loads((_first(tmp_path, "T_x30") / "sensor_logs" / "H1-front-02.json").read_text())
    rows = np.array(t30["rows"])
    assert abs(rows[:20, 3].mean() - np.cos(np.radians(30))) < 0.06 and abs(abs(rows[:20, 2].mean()) - np.sin(np.radians(30))) < 0.06  # gravity rotated
    r10 = json.loads((_first(tmp_path, "S_10Hz") / "sensor_logs" / "H1-front-02.json").read_text())
    assert len(r10["rows"]) == 30 and r10["rate_hz"] == 10
    drop = json.loads((_first(tmp_path, "S_drop05") / "sensor_logs" / "H2-hand_tap-01.json").read_text())
    assert len(drop["rows"]) <= 300


def test_radio_variants(tmp_path):
    d = _first(tmp_path, "L_30")
    run = json.loads((d / "protocol_logs" / "H3-10m-open.json").read_text())
    ok = np.mean([r["retries"] == 0 and r["delivered"] for r in run["records"]])
    assert 0.35 < ok < 0.75  # 0.7 x 0.7 = 0.49 expected first-try delivery at 10 m
    d0 = _first(tmp_path, "L_0")
    run0 = json.loads((d0 / "protocol_logs" / "H3-10m-open.json").read_text())
    assert all(r["delivered"] for r in run0["records"])
    assert Path(d / "variant.json").exists()
