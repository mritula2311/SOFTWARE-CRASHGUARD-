"""L10 (docs/02_preregistration/PREREGISTRATION_V16.md section 15.6): cross-benchmark duplicate and leakage audit (MEASURED_SOFTWARE).

    python -m crashguard.r5_l10 run        # audits UCI HAR (published subject split) and SisFall (random window split and subject split); keys r5.l10.*

The window-identity rule of C1 is applied in kind: two windows are identical if the bytes of their float32 arrays are identical. Nothing is tuned; the splits and seeds are fixed in V16 section 15.6.
Raw archives are untrusted data and are read as text or bytes only. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1].parent
HAR = ROOT / "data" / "raw" / "r5_l10" / "uci_har.zip"
SIS = ROOT / "data" / "raw" / "r5_l10" / "sisfall.zip"
SEED = 42
SIS_WIN, SIS_STEP = 200, 100
TEST_FRAC = 0.20
THRESH = 0.01
EXPECTED = {"data/raw/r5_l10/uci_har.zip": "c00b8030", "data/raw/r5_l10/sisfall.zip": "dd0f9cf1"}  # V16 15.1


def window_key(w: np.ndarray) -> bytes:
    """Exact identity of a window: md5 of its float32 bytes."""
    return hashlib.md5(np.ascontiguousarray(w, np.float32).tobytes()).digest()


def keys_of(windows: np.ndarray) -> list[bytes]:
    return [window_key(w) for w in windows]


def share_identical(test_keys: list[bytes], train_keys: list[bytes]) -> tuple[int, float]:
    """Number and share of the test windows whose key occurs among the train windows."""
    s = set(train_keys)
    n = sum(k in s for k in test_keys)
    return n, (n / len(test_keys) if test_keys else float("nan"))


def is_constant(w: np.ndarray) -> bool:
    return bool(np.all(np.asarray(w) == np.asarray(w)[0]))


def read_matrix(raw: bytes) -> np.ndarray:
    return pd.read_csv(io.BytesIO(raw), sep=r"\s+", header=None).to_numpy(np.float32)


HAR_CHANNELS = ("total_acc", "body_acc", "body_gyro")


def har_windows(z: zipfile.ZipFile, split: str, channels: tuple = HAR_CHANNELS) -> tuple[np.ndarray, np.ndarray]:
    """(windows (n, 128, 3 x channels) of the Inertial Signals, subject id per window) of the published split ``train`` or ``test``; identity is judged on all nine channels (V16 15.6)."""
    base = "UCI HAR Dataset/" + split + "/"
    ax = [read_matrix(z.read(f"{base}Inertial Signals/{c}_{a}_{split}.txt")) for c in channels for a in "xyz"]
    subj = np.loadtxt(io.BytesIO(z.read(f"{base}subject_{split}.txt")), dtype=int)
    return np.stack(ax, axis=2), subj


def open_har() -> zipfile.ZipFile:
    outer = zipfile.ZipFile(HAR)
    return zipfile.ZipFile(io.BytesIO(outer.read("UCI HAR Dataset.zip")))


def sis_parse(raw: bytes) -> np.ndarray:
    """First three columns (ADXL345, raw counts) of a SisFall trial."""
    rows = [ln.strip().rstrip(";").split(",") for ln in raw.decode("latin1").splitlines() if ln.strip()]
    return np.array([[float(x) for x in r[:3]] for r in rows if len(r) >= 3], np.float32)


def sis_windows(sig: np.ndarray, win: int = SIS_WIN, step: int = SIS_STEP) -> list[np.ndarray]:
    return [sig[i : i + win] for i in range(0, len(sig) - win + 1, step)]


def sis_subject(name: str) -> str:
    return name.split("/")[-2]


def test_subject(subject: str) -> bool:
    """Subject split: sha256("l10|" + subject) mod 5 == 0 is the test group (about 20%)."""
    return int(hashlib.sha256(("l10|" + subject).encode()).hexdigest(), 16) % 5 == 0


def sis_collect() -> dict:
    z = zipfile.ZipFile(SIS)
    names = [n for n in z.namelist() if n.endswith(".txt") and "/S" in n and n.split("/")[-1][0] in "DF"]
    keys, subj, con, files = [], [], [], {}
    for n in sorted(names):
        raw = z.read(n)
        files.setdefault(hashlib.md5(raw).hexdigest(), set()).add(sis_subject(n))
        for w in sis_windows(sis_parse(raw)):
            keys.append(window_key(w))
            subj.append(sis_subject(n))
            con.append(is_constant(w))
    return dict(keys=keys, subj=np.array(subj), const=np.array(con), files=files, n_files=len(names))


def random_split(n: int, seed: int = SEED, test_frac: float = TEST_FRAC) -> np.ndarray:
    """True = test window (random window split, the common protocol)."""
    return np.random.default_rng(seed).random(n) < test_frac


def split_audit(keys: list[bytes], is_test: np.ndarray, const: np.ndarray | None = None) -> dict:
    tr = [k for k, t in zip(keys, is_test) if not t]
    te = [k for k, t in zip(keys, is_test) if t]
    n, sh = share_identical(te, tr)
    out = dict(n_train=len(tr), n_test=len(te), n_identical=n, share=sh)
    if const is not None:
        c_te = const[is_test]
        te_nc = [k for k, c in zip(te, c_te) if not c]
        tr_nc = [k for k, c in zip(tr, const[~is_test]) if not c]
        n2, sh2 = share_identical(te_nc, tr_nc)
        out.update(n_test_nonconstant=len(te_nc), n_identical_nonconstant=n2, share_nonconstant=sh2, n_constant_test=int(c_te.sum()))
    return out


def verdict(shares: dict) -> bool:
    """H-L10a: at least one benchmark has more than 1% of its test windows identical to a window of another split."""
    return any(v > THRESH for v in shares.values())


def run() -> None:
    from crashguard import r5_common as R5
    from crashguard import r5_guard as G

    G.verify("l10", "r5.l10.hL10")
    G.check_data(EXPECTED)
    rec = R5.Rec("r5.l10.", "src/crashguard/r5_l10.py", "MEASURED_SOFTWARE")
    z = open_har()
    wtr, str_ = har_windows(z, "train")
    wte, ste = har_windows(z, "test")
    ktr, kte = keys_of(wtr), keys_of(wte)
    n, sh = share_identical(kte, ktr)
    n_in = len(ktr) - len(set(ktr))
    rec.add("har.n_train_windows", len(ktr), "windows", "published split, 128-sample windows of total acceleration")
    rec.add("har.n_test_windows", len(kte), "windows")
    rec.add("har.n_test_identical_to_train", n, "windows", "exact float32 identity")
    rec.add("har.share_test_identical", sh, "fraction")
    rec.add("har.n_duplicate_windows_within_train", n_in, "windows", "exact duplicates inside the train split (not across splits)")
    both = sorted(set(str_.tolist()) & set(ste.tolist()))
    rec.add("har.n_subjects_train", len(set(str_.tolist())), "subjects")
    rec.add("har.n_subjects_test", len(set(ste.tolist())), "subjects")
    rec.add("har.n_subjects_in_both", len(both), "subjects", "subject leakage of the published split")
    s = sis_collect()
    keys = s["keys"]
    rec.add("sisfall.n_files", s["n_files"], "files", "D and F trials of the SA and SE subjects")
    rec.add("sisfall.n_windows", len(keys), "windows", "200-sample windows, step 100, first three columns")
    dup_files = sum(1 for v in s["files"].values() if len(v) > 1)
    rec.add("sisfall.n_files_identical_across_subjects", dup_files, "files", "byte-identical trials found under more than one subject")
    ra = split_audit(keys, random_split(len(keys)), s["const"])
    for k, v in ra.items():
        rec.add(f"sisfall.random.{k}", v, "fraction" if k.startswith("share") else "windows", "random window split 80/20, seed 42 (the common protocol, stated)" if k == "share" else "")
    test_mask = np.array([test_subject(x) for x in s["subj"]])
    sa = split_audit(keys, test_mask, s["const"])
    for k, v in sa.items():
        rec.add(f"sisfall.subject.{k}", v, "fraction" if k.startswith("share") else "windows", "subject split by hash, about 20% of subjects" if k == "share" else "")
    shares = {"har": sh, "sisfall_random": ra["share"]}
    met = verdict(shares)
    rec.add("hL10a.criterion_met", int(met), "bool", "at least one benchmark has more than 1% of its test windows identical to a window of another split (HAR published split; SisFall random window split); the share over all test windows is the primary figure, the share over non-constant windows is reported next to it")
    rec.add("hL10a.max_share", float(max(shares.values())), "fraction")
    rec.add("hL10a.n_benchmarks", 2, "benchmarks")
    rec.add("hL10b.criterion_met", "NOT_RUN", "text", "no baseline is reproduced: it is run only where leakage above 1% is found (V16 15.6)" if not met else "leakage found; the baseline run is not implemented in this session", origin="NOT_RUN")
    rec.write()
    print(json.dumps({k: (round(v, 6) if isinstance(v, float) else v) for k, v in dict(har=sh, har_n=n, sis_random=ra["share"], sis_random_nc=ra.get("share_nonconstant"), sis_subject=sa["share"], subj_both=len(both), dup_files=dup_files).items()}, indent=1))


def freeze() -> None:
    from crashguard import r5_guard as G

    d = G.freeze("l10", ["src/crashguard/r5_l10.py"], dict(win=SIS_WIN, step=SIS_STEP, seed=SEED, test_frac=TEST_FRAC, thresh=THRESH, har_channels=list(HAR_CHANNELS)), list(EXPECTED), "r5.l10.hL10")
    print("frozen l10", d["params_sha256"][:16])


def main() -> None:
    {"freeze": freeze, "run": run}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()


if __name__ == "__main__":
    main()
