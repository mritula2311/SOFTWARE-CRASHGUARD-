"""C export equivalence on a small forest trained on random data (unit test only, no results are produced)."""
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from crashguard.export_c import c_predict, find_compiler, forest_arrays, write_header


def _forest():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(2000, 14)).astype(np.float32)
    y = (X[:, 0] + 0.5 * X[:, 3] + rng.normal(scale=0.5, size=2000) > 0).astype(int)
    m = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=0).fit(X, y)
    return m, X


def test_thresholds_never_above_sklearn():
    m, _ = _forest()
    a = forest_arrays(m)
    i = 0
    for est in m.estimators_:
        t = est.tree_
        for k in range(t.node_count):
            if t.children_left[k] != -1:
                assert float(a["thr"][i]) <= t.threshold[k]
            i += 1


@pytest.mark.skipif(find_compiler() is None, reason="no C compiler available")
def test_c_matches_python(tmp_path):
    m, X = _forest()
    h = tmp_path / "crashguard_rf.h"
    write_header(m, h)
    try:
        c, _ = c_predict(h, X)
    except RuntimeError as err:
        if "could not be run" in str(err):
            pytest.skip(str(err))  # OS policy blocked the program; make export reports the measured result
        raise
    assert np.abs(c - m.predict_proba(X)[:, 1]).max() <= 1e-6
