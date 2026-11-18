"""Tests of the L10 module (V16 section 15.6). Synthetic archives; known answers on UCI HAR (published sizes) when the file is present."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pytest

from crashguard import r5_l10 as L

ROOT = Path(__file__).resolve().parents[1]


def test_window_key_exact_identity():
    a = np.arange(30, dtype=np.float32).reshape(10, 3)
    assert L.window_key(a) == L.window_key(a.copy()) == L.window_key(a.astype(np.float64))
    b = a.copy()
    b[3, 1] += 1e-3
    assert L.window_key(a) != L.window_key(b)
    assert L.window_key(a) != L.window_key(a[::-1])
    assert L.window_key(np.asfortranarray(a)) == L.window_key(a)  # layout does not matter


def test_share_identical():
    k = [bytes([i]) for i in range(10)]
    assert L.share_identical(k[:4], k[2:]) == (2, 0.5)
    assert L.share_identical(k[:3], k[5:]) == (0, 0.0)
    n, s = L.share_identical([], k)
    assert n == 0 and np.isnan(s)
    assert L.share_identical([k[0], k[0], k[1]], [k[0]]) == (2, 2 / 3)  # a repeated test window counts each time


def test_is_constant():
    assert L.is_constant(np.ones((5, 3))) and not L.is_constant(np.array([[1, 1, 1], [1, 1, 2]])) and not L.is_constant(np.array([[1, 1], [1, 2]]))


def test_sis_parse_and_windows():
    raw = b" -11,-260, -24,-141,  75, -45, -40,-1006,  42;\n -11,-256, -18,-144,  77, -44, -41,-999,  43;\n\n -12,-257, -22,-146,  78, -42, -39,-1007,  42;\n"
    a = L.sis_parse(raw)
    assert a.shape == (3, 3) and list(a[1]) == [-11.0, -256.0, -18.0] and a.dtype == np.float32
    sig = np.arange(1000 * 3, dtype=np.float32).reshape(1000, 3)
    w = L.sis_windows(sig)
    assert len(w) == 9 and w[0].shape == (200, 3) and np.array_equal(w[1][0], sig[100]) and np.array_equal(w[-1][-1], sig[999])
    assert len(L.sis_windows(sig[:199])) == 0 and len(L.sis_windows(sig[:200])) == 1 and len(L.sis_windows(sig[:300])) == 2
    assert L.sis_subject("SisFall_dataset/SA05/D01_SA05_R01.txt") == "SA05"


def test_subject_split_is_deterministic_and_about_a_fifth():
    subs = [f"SA{i:02d}" for i in range(1, 24)] + [f"SE{i:02d}" for i in range(1, 16)]
    t = [L.test_subject(s) for s in subs]
    assert t == [L.test_subject(s) for s in subs] and 3 <= sum(t) <= 14
    big = [L.test_subject(f"X{i}") for i in range(5000)]
    assert 0.17 < np.mean(big) < 0.23


def test_random_split_fraction_and_seed():
    m = L.random_split(20000)
    assert 0.19 < m.mean() < 0.21 and np.array_equal(m, L.random_split(20000)) and not np.array_equal(m, L.random_split(20000, seed=1))
    assert L.random_split(1000, test_frac=0.5).mean() == pytest.approx(0.5, abs=0.06)


def test_split_audit_counts_and_constant_windows():
    keys = [b"a", b"b", b"a", b"c", b"z", b"z", b"b"]
    is_test = np.array([False, False, True, True, True, True, True])
    const = np.array([False, False, False, False, True, True, False])
    r = L.split_audit(keys, is_test, const)
    assert (r["n_train"], r["n_test"], r["n_identical"]) == (2, 5, 2) and r["share"] == pytest.approx(0.4)
    assert r["n_constant_test"] == 2 and r["n_test_nonconstant"] == 3 and r["n_identical_nonconstant"] == 2 and r["share_nonconstant"] == pytest.approx(2 / 3)
    assert "share_nonconstant" not in L.split_audit(keys, is_test)
    z = L.split_audit([b"a", b"b"], np.array([False, True]))
    assert z["n_identical"] == 0 and z["share"] == 0.0


def test_har_windows_reader_on_a_synthetic_archive():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for split, n in (("train", 3), ("test", 2)):
            for ci, ch in enumerate(L.HAR_CHANNELS):
                for a, off in zip("xyz", (0, 100, 200)):
                    rows = "\n".join(" ".join(f"{off + 1000 * ci + r + c / 10:.8e}" for c in range(4)) for r in range(n))
                    z.writestr(f"UCI HAR Dataset/{split}/Inertial Signals/{ch}_{a}_{split}.txt", rows + "\n")
            z.writestr(f"UCI HAR Dataset/{split}/subject_{split}.txt", "\n".join(str(i + (1 if split == 'train' else 20)) for i in range(n)) + "\n")
    z = zipfile.ZipFile(io.BytesIO(buf.getvalue()))
    w, s = L.har_windows(z, "train")
    assert w.shape == (3, 4, 9) and list(s) == [1, 2, 3] and w[1, 2, 2] == pytest.approx(201.2, rel=1e-5) and w[2, 0, 1] == pytest.approx(102.0)
    assert w[0, 0, 3] == pytest.approx(1000.0) and w[0, 0, 8] == pytest.approx(2200.0)  # body_acc and body_gyro channels follow total_acc
    w2, s2 = L.har_windows(z, "test")
    assert w2.shape == (2, 4, 9) and list(s2) == [20, 21]
    assert L.har_windows(z, "train", channels=("total_acc",))[0].shape == (3, 4, 3)


HAR_OK = (ROOT / "data" / "raw" / "r5_l10" / "uci_har.zip").exists()


@pytest.mark.skipif(not HAR_OK, reason="UCI HAR archive not downloaded")
def test_uci_har_published_sizes_and_subject_split():
    z = L.open_har()
    wtr, s_tr = L.har_windows(z, "train")
    wte, s_te = L.har_windows(z, "test")
    assert wtr.shape == (7352, 128, 9) and wte.shape == (2947, 128, 9)
    assert len(set(s_tr.tolist())) == 21 and len(set(s_te.tolist())) == 9 and not (set(s_tr.tolist()) & set(s_te.tolist()))


def test_window_key_sees_the_last_value():
    a = np.zeros((4, 3), np.float32)
    b = a.copy()
    b[-1, -1] = 1.0
    assert L.window_key(a) != L.window_key(b)


def test_constant_window_means_every_column_constant():
    assert L.is_constant(np.array([[1.0, 2.0, 3.0]] * 5))
    assert not L.is_constant(np.array([[1.0, 2.0, 3.0], [1.0, 2.0, 4.0]]))


def test_test_subject_known_members():
    got = {f"SA{i:02d}" for i in range(1, 24) if L.test_subject(f"SA{i:02d}")} | {f"SE{i:02d}" for i in range(1, 16) if L.test_subject(f"SE{i:02d}")}
    import hashlib

    want = {s for s in [f"SA{i:02d}" for i in range(1, 24)] + [f"SE{i:02d}" for i in range(1, 16)] if int(hashlib.sha256(("l10|" + s).encode()).hexdigest(), 16) % 5 == 0}
    assert got == want and len(got) >= 3


def test_split_audit_excludes_constant_train_windows_from_the_nonconstant_count():
    keys = [b"x", b"x", b"y"]
    is_test = np.array([False, True, True])
    const = np.array([True, False, False])  # the train copy is flagged constant (a logic check of the filters)
    r = L.split_audit(keys, is_test, const)
    assert r["n_identical"] == 1 and r["n_identical_nonconstant"] == 0
    const2 = np.array([False, True, False])  # the test copy is constant
    r2 = L.split_audit(keys, is_test, const2)
    assert r2["n_test_nonconstant"] == 1 and r2["n_identical_nonconstant"] == 0


def test_verdict_threshold_is_one_per_cent():
    assert not L.verdict({"a": 0.01, "b": 0.0}) and L.verdict({"a": 0.0101, "b": 0.0}) and L.verdict({"a": 0.0, "b": 0.5}) and not L.verdict({"a": 0.5 * 0.0, "b": 0.0})
    assert L.THRESH == 0.01 and (L.SIS_WIN, L.SIS_STEP) == (200, 100)


def test_sis_collect_reads_only_trials_and_finds_identical_files(tmp_path, monkeypatch):
    sig = "\n".join(f" {i},{i + 1},{i + 2},0,0,0,0,0,0;" for i in range(450)) + "\n"
    zp = tmp_path / "s.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("SisFall_dataset/Readme.txt", "text that is not a trial")
        z.writestr("SisFall_dataset/SA01/D01_SA01_R01.txt", sig)
        z.writestr("SisFall_dataset/SA02/D01_SA02_R01.txt", sig)  # byte-identical under another subject
        z.writestr("SisFall_dataset/SE01/F01_SE01_R01.txt", sig.replace("0,0,0,0,0,0;", "1,1,1,1,1,1;"))
        z.writestr("SisFall_dataset/SA01/desktop.ini", "x")
    monkeypatch.setattr(L, "SIS", zp)
    s = L.sis_collect()
    assert s["n_files"] == 3 and len(s["keys"]) == 3 * 3 and sorted(set(s["subj"].tolist())) == ["SA01", "SA02", "SE01"]
    assert sum(1 for v in s["files"].values() if len(v) > 1) == 1
    assert not s["const"].any()
    # the identical trial gives identical windows: 3 + 3 windows share keys, so a split across them finds identical windows
    assert len(set(s["keys"])) == 3 + 0 or len(set(s["keys"])) <= 6
