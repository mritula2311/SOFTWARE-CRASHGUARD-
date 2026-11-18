"""Tests of the positive-results push (docs/02_preregistration/PREREGISTRATION_V4.md)."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from crashguard import pp_common as PC

ROOT = Path(__file__).resolve().parents[1]


def test_class_limits():
    assert list(PC.cls_of([0, 23.99, 24, 39.9, 40, 55.9, 56, 400])) == [0, 0, 1, 1, 2, 2, 3, 3]


def test_triage_definitions():
    y = np.array([0, 1, 2, 2, 3, 3])
    p = np.array([1, 1, 1, 2, 3, 0])
    assert PC.under_triage(y, p) == pytest.approx(2 / 4)  # true Severe or Critical predicted lower: indices 2 and 5
    assert PC.over_triage(y, p) == pytest.approx(1 / 2)  # true Low predicted Moderate
    assert PC.mis_triage(y, p) == pytest.approx(2 / 4)  # predicted below Severe: indices 2 and 5
    assert PC.escalation(np.array([0, 1, 1]), np.array([2, 3, 0])) == pytest.approx(2 / 3)
    assert PC.macro_f1(np.array([0, 1]), np.array([0, 1])) == 1.0


def test_split_is_by_group_and_covers_all():
    T = pd.read_csv(ROOT / "results/tables/p_pool_folds.csv")
    assert len(T) == 913
    assert (T.groupby("group").fold.nunique() == 1).all()
    assert set(T.fold) == {"dev", "val", "test"}
    assert set(T["mode"]) == set(PC.MODES)


def test_sealed_split_digest_matches_document():
    T = pd.read_csv(ROOT / "results/tables/p_pool_folds.csv")
    doc = (ROOT / "docs/05_data_code/SEALED_SPLIT.md").read_text(encoding="utf-8")
    for f in ("dev", "val", "test"):
        gs = sorted(T[T.fold == f].group.unique())
        assert hashlib.sha256("\n".join(gs).encode()).hexdigest() in doc


def test_group_key_merges_variants():
    from crashguard.pp_pool import group_key

    assert group_key("TOYOTA", "COROLLA HYBRID") == group_key("toyota", "Corolla") == "TOYOTA|COROLLA"


def test_conformal_quantile():
    from crashguard.pp_p2 import cq

    s = np.arange(1, 10).astype(float)  # n = 9, alpha 0.2: k = ceil(10 * 0.8) = 8
    assert cq(s, 0.2) == 8.0
    assert cq(s, 0.05) == float("inf")


def test_p4c_helpers():
    from crashguard.pp_p4bc import cv_pvalue, thr_v4

    g = [np.linspace(0, 1, 100), np.linspace(0, 1, 100)]
    t = thr_v4(g, 0.05)
    assert 0.9 < t <= 1.0
    p = cv_pvalue([np.array([0.1, 0.2, 0.3])], [np.array([0.0, 0.25, 1.0])])
    assert list(p) == [1.0, (1 + 1) / 4, 1 / 4]


def test_holm():
    from crashguard.pp_verdicts import holm

    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_sealed_gate_allows_one_scoring(tmp_path, monkeypatch):
    monkeypatch.setattr(PC, "ACCESS_LOG", tmp_path / "log.csv")
    monkeypatch.setattr(PC, "FREEZE_DIR", tmp_path)
    (tmp_path / "p_freeze_T.json").write_text("{}")
    monkeypatch.setattr(PC, "git", lambda *a: "" if a[0] == "status" else "abc123")
    assert PC.sealed_gate("T") == "abc123"
    with pytest.raises(RuntimeError):
        PC.sealed_gate("T")
    assert PC.sealed_gate("T", deviation="reason") == "abc123"


def test_keys_must_start_with_p():
    E = PC.PEntries("x", "f")
    E.items.append(dict(name="t1.bad", value=1, unit="u", origin="MEASURED_SOFTWARE", source_file="f", notes=""))
    with pytest.raises(ValueError):
        E.flush()


def test_stretch_scales_time_and_amplitude():
    from crashguard.pp_feat import stretch

    t = np.arange(0, 0.2, 1e-4)
    acc = np.stack([np.sin(np.pi * t / 0.1) * (t < 0.1), 0 * t, 0 * t], axis=1)
    s = stretch(dict(t=t, acc=acc, fs0=1e4, peak_g=1.0), 1.5, 2.0)
    assert abs(s["acc"][:, 0].max() - 2.0) < 0.02
    assert abs(len(s["t"]) - 1.5 * len(t)) <= 2
    # integral (delta-V) scales with amplitude x duration
    assert abs(s["acc"][:, 0].sum() / acc[:, 0].sum() - 3.0) < 0.05


def test_audit_windows_finds_copies(tmp_path):
    import sys

    sys.path.insert(0, str(ROOT / "crashclip"))
    from audit_windows import exact_groups, near_duplicates

    rng = np.random.default_rng(0)
    W = rng.normal(size=(10, 40, 3)).astype(np.float32)
    W[7] = W[2]
    W[8] = W[3] + 0.001
    splits = np.array(["train"] * 5 + ["test"] * 5)
    g = exact_groups(W, splits)
    assert len(g) == 1 and g.n_splits.iloc[0] == 2
    assert (3, 8) in near_duplicates(W, splits)


def test_evaluate_runs(tmp_path):
    import sys

    sys.path.insert(0, str(ROOT / "crashclip"))
    if not (ROOT / "crashclip/records.csv").exists():
        pytest.skip("records.csv not generated yet")
    from evaluate import evaluate

    rec = pd.read_csv(ROOT / "crashclip/records.csv")
    pred = rec[rec.fold == "test"][["rid"]].assign(pred_class=rec[rec.fold == "test"].ref_class.to_numpy())
    r = evaluate(pred, "test")
    assert r[(r.scope == "all") & (r.metric == "macro_f1")].value.iloc[0] == 1.0


def test_no_forbidden_words_in_new_documents():
    pat = re.compile(r"\b(first|novel|state[- ]of[- ]the[- ]art)\b", re.I)
    for f in ("docs/02_preregistration/PREREGISTRATION_V4.md", "docs/05_data_code/SEALED_SPLIT.md", "crashclip/README.md", "docs/05_data_code/REPRODUCE_FINISH.md"):
        p = ROOT / f
        if p.exists():
            bad = [ln for ln in p.read_text(encoding="utf-8").splitlines() if pat.search(ln)]
            assert not bad, (f, bad[:2])


def test_models_are_deterministic():
    from crashguard import pp_models as PM

    rng = np.random.default_rng(1)
    W = rng.normal(size=(64, 3, 50)).astype(np.float32)
    y = rng.integers(0, 4, 64)
    M = np.zeros((64, 0), np.float32)
    a = PM.train_cnn(W, M, y, W, M, y, 3, epochs=3)
    b = PM.train_cnn(W, M, y, W, M, y, 3, epochs=3)
    assert all(bool((a["state"][k] == b["state"][k]).all()) for k in a["state"])
    df = pd.DataFrame(rng.normal(size=(64, len(PM.DESC_D))), columns=PM.DESC_D)
    p1 = PM.OrdGBM(4, 20, False).fit(df, y, None).predict_cum(df, None)
    p2 = PM.OrdGBM(4, 20, False).fit(df, y, None).predict_cum(df, None)
    assert np.array_equal(p1, p2)


def test_cum_to_class_is_monotone():
    from crashguard.pp_models import cum_to_class

    assert list(cum_to_class(np.array([[0.9, 0.2, 0.9], [0.4, 0.9, 0.9], [0.9, 0.9, 0.6]]))) == [1, 0, 3]
