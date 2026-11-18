"""CV 1 and 7 for D4 and the FRESH-B analysis path: hand-computed airtime ratios, the R3 known answer, and a smoke run of the whole analysis on a tiny grid (the real run happens once, so the code path is exercised first)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from crashguard import rd_d4 as D4
from crashguard.lora import airtime_ms


def test_extra_airtime_hand_case():
    # three triggered events at p = 0 (one try): (E, F) = (1,1), (1,0), (0,1); SF7: alert 97 B, provisional 14 B, cancel 14 B
    E = np.array([True, True, False])
    F = np.array([True, False, True])
    a_al, a_fl = airtime_ms(97, 7) / 1000, airtime_ms(14, 7) / 1000
    s, t = D4.per_event(E, F, 7, 0.0, 14)
    assert s.sum() == pytest.approx(2 * a_al)  # two events with a full-window alarm
    assert t.sum() == pytest.approx((a_fl + a_al) + (a_fl + 3 * a_fl) + a_al)
    assert D4.ratio(s, t) == pytest.approx((5 * a_fl + 2 * a_al) / (2 * a_al) - 1)


def test_exp_tries_hand_cases():
    assert D4.exp_tries(0.0) == pytest.approx(1.0)  # q = 1: one try is enough
    assert D4.exp_tries(1.0) == pytest.approx(4.0)  # q = 0: all four tries are used
    q = 0.5**2
    assert D4.exp_tries(0.5) == pytest.approx(1 + (1 - q) + (1 - q) ** 2 + (1 - q) ** 3)


@pytest.mark.skipif(not Path(D4.EVENTS).exists(), reason="stored test events not present")
def test_known_answer_r3_extra_airtime():
    ev = D4.load_events()
    s, t = D4.per_event(ev["E"], ev["F"], 7, 0.0, 14)
    stored = {e["name"]: e["value"] for e in json.loads(Path("results/results.json").read_text(encoding="utf-8")) if e["name"] in ("ar.r3.a1.air_ratio_p0", "ar.r3.a1.air_ratio_p0.3")}
    assert D4.ratio(s, t) == pytest.approx(stored["ar.r3.a1.air_ratio_p0"], abs=1e-5)  # 0.38038: the earlier published number
    s, t = D4.per_event(ev["E"], ev["F"], 7, 0.3, 14)
    assert D4.ratio(s, t) == pytest.approx(stored["ar.r3.a1.air_ratio_p0.3"], abs=1e-5)


@pytest.mark.skipif(not Path(D4.EVENTS).exists(), reason="stored test events not present")
def test_longer_provisional_frame_cannot_lower_extra_airtime():
    ev = D4.load_events()
    for sf in (7, 9, 12):
        for p in (0.0, 0.3, 0.6):
            r14 = D4.ratio(*D4.per_event(ev["E"], ev["F"], sf, p, 14))
            r24 = D4.ratio(*D4.per_event(ev["E"], ev["F"], sf, p, 24))
            r97 = D4.ratio(*D4.per_event(ev["E"], ev["F"], sf, p, 97))
            assert r14 < r24 < r97  # monotone in the provisional frame length


@pytest.mark.skipif(not Path("data/processed/pa_held.pkl").exists() or not Path("results/tables/rd_frozen_A.json").exists(), reason="data/processed logs not present")
def test_fresh_b_analysis_smoke(tmp_path, monkeypatch):
    from crashguard import rd_dev_b as DB
    from crashguard import rd_eval as E
    from crashguard import rd_fresh_b as FB

    grid = dict(n=[60, 90], p=[0.2], sf=[9], duty=[0.01], b=[20], seed=777, hours=2, d4_losses=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], d4_sfs=[7, 8, 9, 10, 11, 12], freeze_sha256="x")
    gp = tmp_path / "g.json"
    gp.write_text(json.dumps(grid), encoding="utf-8")
    monkeypatch.setattr(FB, "GRID", gp)
    monkeypatch.setattr(FB, "FROZEN", gp)
    cells = E.cells_of(grid)
    res = E.run_grid(cells, E.POLICIES_B, grid["seed"], grid["hours"], DB.params_of({}), workers=2)
    d4 = D4.run_grid(D4.load_events(), grid["d4_sfs"], grid["d4_losses"])
    out = FB.analyse(res, d4, cells, grid, write=False)
    assert set(out["crit"]) == {"D3", "D4a"} and out["crit"]["D4a"] is False  # the arithmetic of section 10.1: a 24-byte provisional frame does not give extra airtime below 25%
    assert set(out["adj"]) == {"D1a", "D1b", "D1c", "D1s", "D2a", "D2b", "D2c", "D3", "D4a", "D4b"} and all(0.0 <= v <= 1.0 for v in out["adj"].values())
