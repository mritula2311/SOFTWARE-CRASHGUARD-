import numpy as np
import pandas as pd

from crashguard import saturation_splits as SP
from crashguard.s4_n14 import METHODS5, bin_labels, strata


def test_bin_labels_edges_belong_to_the_upper_bin():
    idx, names = bin_labels(np.array([10.0, 29.99, 30.0, 44.0, 45.0, 59.0, 60.0, 90.0]), (30.0, 45.0, 60.0))
    assert names == ["lt30", "30to45", "45to60", "ge60"]
    assert list(idx) == [0, 0, 1, 1, 2, 2, 3, 3]


def test_strata_counts_and_interval_rule():
    n = 40
    rng = np.random.default_rng(0)
    meta = pd.DataFrame(dict(ref=np.r_[np.full(5, 20.0), np.full(15, 35.0), np.full(20, 70.0)], v=np.full(n, 56.0), group_mm=[f"g{i // 2}" for i in range(n)]))
    E = {rg: {m: rng.random((SP.N_REPEATS, n)) * 30 for m in METHODS5} for rg in SP.RANGES}
    cells = {("ap", rg, "triangle", 0.7, 0.1): np.ones(n, bool) for rg in SP.RANGES}
    out = {(r["scheme"], r["bin"]): r for r in strata(E, cells, meta, dict(M=("triangle", 0.7, 0.1)))}
    assert out[("dv", "lt30")]["n"] == 5 and out[("dv", "30to45")]["n"] == 15 and out[("dv", "ge60")]["n"] == 20
    assert "r16.M+.median_lo" not in out[("dv", "lt30")]  # fewer than 10 tests: no interval
    assert "r16.M+.median_lo" in out[("dv", "30to45")]
    assert out[("dv", "lt30")]["sat16"] == 1.0
    assert sum(r["n"] for (s, _b), r in out.items() if s == "dv") == n
