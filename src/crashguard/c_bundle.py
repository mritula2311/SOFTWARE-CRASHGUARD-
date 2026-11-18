"""Build the C equivalence bundle that ``scripts/c_checks.sh`` compiles and runs with gcc on any machine (Linux, WSL, a CI runner). Software only.

``c_bundle/`` (committed, small) holds checks whose INPUTS ARE SYNTHETIC (random feature vectors, vectors that sit exactly on and one float step either side of every split threshold,
synthetic crash pulses with and without gyro rotation, clipped synthetic pulses for the N14 estimator). Expected outputs come from the Python reference (scikit-learn predict_proba,
``severity.severity``, ``saturation.severity_sat``), computed here. ``--real`` builds ``build/c_bundle_real/`` (git-ignored) with the same checks on the real triggered test events, the
VZCrash and NHTSA windows used by the Windows pipeline; those data are never committed.

Every check is described in ``manifest.json``: the C harness source, the headers it includes, the input and expected-output files, the output fields and the pass tolerances.
The pass tolerances are our own choices and are stated here: forest probability 1e-6; severity numeric fields as in ``TOL`` below; discrete fields (class, flags) must agree exactly.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import joblib
import numpy as np

from crashguard import config as C

ROOT = Path("c_bundle")
REAL_ROOT = Path("build/c_bundle_real")
SEV_TOL = {"dv_res_kmh": 1e-3, "asi": 1e-4, "thiv_kmh": 1e-3, "pulse_ms": 0.1, "peak_pulse_g": 1e-4, "tilt_deg": 0.5, "tilt_corrected_deg": 0.5}
SAT_TOL = {"dv_baseline_kmh": 1e-3, "dv_fill_kmh": 1e-3, "dv_fill_corrected_kmh": 1e-3, "asi_fill": 1e-4, "sat_share": 1e-5}
EXACT_SEV = ("severity_class", "rollover", "thiv_hit", "roll_corrected_applied")
EXACT_SAT = ("applied", "saturated")


def _rec(path: Path, arr: np.ndarray, dtype) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.ascontiguousarray(arr, dtype).tofile(path)


def _forest_vectors(header: Path, n_random: int, rng: np.random.Generator) -> np.ndarray:
    """Random vectors in the training range, plus vectors with one feature set to each split threshold and to the float32 neighbours either side of it."""
    import pandas as pd

    from crashguard.c_mirror import parse_header

    tr = pd.read_parquet(C.PROCESSED / "features.parquet", columns=list(C.FEATURES))
    lo, hi = tr.quantile(0.001).to_numpy(), tr.quantile(0.999).to_numpy()
    base = (lo + rng.random((n_random, len(C.FEATURES))) * (hi - lo)).astype(np.float32)
    h = parse_header(header)
    rows = [base]
    for node, f in enumerate(h["feat"]):
        if f < 0:
            continue
        t = np.float32(h["thr"][node])
        for v in (t, np.nextafter(t, np.float32(np.inf)), np.nextafter(t, np.float32(-np.inf))):
            x = base[rng.integers(0, len(base))].copy()
            x[f] = v
            rows.append(x[None, :])
    return np.concatenate(rows).astype(np.float32)


def _synthetic_windows(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic triggered windows (acc, gyro), shapes x amplitudes x durations x directions, some with a gyro rotation large enough to exercise the rollover and tilt code."""
    from crashguard import severity_synth as Y

    acc, gyro = [], []
    for shp in Y.SHAPES:
        for A in (6.0, 12.0, 24.0, 40.0):
            for T in (0.04, 0.08, 0.12, 0.16):
                for theta in (0.0, 35.0, 90.0):
                    a, trig = Y.make_window(shp, A, T, theta, float(C.FS_HZ), rng)
                    if trig < 0:
                        continue
                    g = rng.normal(0.0, 0.02, a.shape)
                    if len(acc) % 7 == 3:  # a rotation about x after the impact
                        g[trig:, 0] += np.linspace(0, 6.0, len(a) - trig)
                    acc.append(a.astype(np.float32))
                    gyro.append(g.astype(np.float32))
    return np.stack(acc), np.stack(gyro)


def _sat_windows(rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    from crashguard import severity_synth as Y

    wins, trigs = [], []
    for shp in Y.SHAPES:
        for A in (20.0, 40.0, 80.0, 150.0):
            for T in (0.04, 0.08, 0.12, 0.16):
                a, trig = Y.make_window(shp, A, T, 0.0, float(C.FS_HZ), rng, clip_g=C.MPU_RANGE_G)
                if trig >= 0:
                    wins.append(a.astype(np.float32))
                    trigs.append(trig)
    return np.stack(wins), np.array(trigs)


def build(root: Path, real: bool) -> dict:
    from crashguard import export_c as EC
    from crashguard import export_severity as ES
    from crashguard import saturation as SAT
    from crashguard.detector_extra import CAND_HEADER, SEL, fit, frames_full
    from crashguard.models import PRIMARY, frames, op_thresholds

    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    rng = np.random.default_rng(C.SEED)
    checks: list[dict] = []

    def add(name: str, kind: str, harness: str, headers: list[Path], rename: dict, inp: np.ndarray, expected: np.ndarray, fields: list[str], tol: dict, exact: list[str], ref: str, extra: dict | None = None):
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "harness.c").write_text(harness, encoding="utf-8")
        for h in headers:
            shutil.copy(h, d / rename.get(h.name, h.name))
        _rec(d / "in.bin", inp, np.float32)
        _rec(d / "expected.bin", expected, np.float64)
        checks.append(dict(name=name, kind=kind, dir=name, n_rows=int(len(expected)), n_out=int(expected.shape[1]) if expected.ndim > 1 else 1, fields=fields, tolerance=tol, exact_fields=exact,
                           reference=ref, real_data=real, **(extra or {})))

    # ---- forests
    bundle = joblib.load(C.PROCESSED / "rf15_seed42.joblib")
    model15 = bundle["model"]
    tr, va, _te_full = frames_full()
    va_trig = va[va.triggered]
    scorer, model10 = fit(SEL, C.SEED, tr, va_trig)
    thr10, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:  # the committed candidate header must be exactly what the current code exports
        fresh = Path(tmp) / "crashguard_rf_candidate.h"
        EC.write_header(model10, fresh, thr_f1=thr10)
        assert fresh.read_text(encoding="utf-8").replace("\r\n", "\n") == CAND_HEADER.read_text(encoding="utf-8").replace("\r\n", "\n"), "firmware_export/crashguard_rf_candidate.h differs from a fresh export"
    for name, header, mdl, thr in (("forest_15x6", EC.HEADER, model15, bundle["thr_f1"]), ("forest_10x9", CAND_HEADER, model10, thr10)):
        if real:
            _, _, te = frames(PRIMARY)
            X = te[te.triggered][list(C.FEATURES)].to_numpy(np.float32)
        else:
            X = _forest_vectors(header, 2000, rng)
        py = mdl.predict_proba(X)[:, 1]
        add(name, "forest", EC.HARNESS, [header], {header.name: "crashguard_rf.h"}, X, py[:, None], ["prob"], {"prob": 1e-6}, [],
            "scikit-learn predict_proba (float64) on float32 inputs", dict(decision_threshold=float(thr)))
    # ---- severity.h
    ES.write_header()
    if real:
        from crashguard.severity_vzcrash import test_windows

        sets = {"vzcrash_test": test_windows()}
        try:
            from crashguard.nhtsa import sensor_windows

            na, ng = sensor_windows()
            if len(na):
                sets["nhtsa"] = (na, ng)
        except Exception:  # noqa: BLE001 - NHTSA data not available: that check is simply not built
            pass
    else:
        sets = {"synthetic": _synthetic_windows(rng)}
    for label, (a, g) in sets.items():
        py = ES.python_severity(a, g)
        rec = np.concatenate([a.reshape(len(a), -1), g.reshape(len(g), -1)], axis=1)
        add(f"severity_{label}", "severity", ES.HARNESS % (C.WIN_N, C.PRE_N), [ES.HEADER], {}, rec, py, list(ES.OUT_FIELDS), SEV_TOL, list(EXACT_SEV), "severity.severity (float64) on the same float32 windows")
    # ---- N14 estimator
    m = json.loads(ES.N14_MODEL.read_text(encoding="utf-8")) if ES.N14_MODEL.exists() else None
    if m is not None and f"{C.MPU_RANGE_G:g}" in m["ranges"]:
        r16 = m["ranges"][f"{C.MPU_RANGE_G:g}"]
        model = dict(family=m["family"], sat_frac=m["sat_frac"], mu=r16["mu"], sd=r16["sd"], w=r16["w"], b=r16["b"])
        if real:
            W, T, _ = ES.sat_windows()
        else:
            W, T = _sat_windows(rng)
        ref = np.array([[SAT.severity_sat(W[i].astype(np.float64), float(C.FS_HZ), int(T[i]), C.MPU_RANGE_G, model)[k] for k in ES.SAT_FIELDS] for i in range(len(W))])
        rec = np.concatenate([W.reshape(len(W), -1).astype(np.float32), T.astype(np.float32)[:, None]], axis=1)
        add("n14_sat_real" if real else "n14_sat_synthetic", "n14", ES.HARNESS_SAT % C.WIN_N, [ES.HEADER], {}, rec, ref, list(ES.SAT_FIELDS), SAT_TOL, list(EXACT_SAT), "saturation.severity_sat (float64)")
    manifest = dict(version=1, real_data=real, n_checks=len(checks), win_n=C.WIN_N, pre_n=C.PRE_N, note="inputs synthetic" if not real else "inputs from the real datasets; do not commit", checks=checks)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def main() -> None:
    real = "--real" in sys.argv
    root = REAL_ROOT if real else ROOT
    man = build(root, real)
    print(f"wrote {root} with {man['n_checks']} checks: " + ", ".join(f"{c['name']} ({c['n_rows']} rows)" for c in man["checks"]))


if __name__ == "__main__":
    main()
