"""Determinism check of the sealed results: reload the frozen model files (sha256 checked against the freeze files) and recompute the point values of P1 (every model, every cell) and the coverage of P2 from them,
then compare with the stored ``p.`` keys. It writes nothing to results.json and no decision depends on it; it shows that the stored numbers follow from the frozen files.
"""
from __future__ import annotations

import json

import joblib
import numpy as np

from crashguard import pp_common as PC
from crashguard import pp_p2 as P2
from crashguard.pp_ctx import Ctx
from crashguard.pp_p1 import CELLS, MODEL_DIR, predict

R = {e["name"]: e["value"] for e in json.load(open("results/results.json", encoding="utf-8"))}


def main() -> None:
    cx = Ctx()
    te = cx.test
    fz1 = json.load(open(PC.FREEZE_DIR / "p_freeze_P1.json"))
    n, bad, worst = 0, 0, 0.0
    for f, h in fz1["model_files"].items():
        assert PC.sha256_file(f) == h, f
    for rg, fs in CELLS:
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{fs}.joblib")
        df, W = cx.cell(rg, fs)
        mi = z["modeclf"].predict(df)
        for name, obj in z["models"].items():
            pr, _ = predict(name, obj, df[te], W[te], cx.mode_idx[te], mi[te])
            for k, fn in PC.TRIAGE.items():
                got = fn(cx.y[te], pr)
                want = float(R[f"p.p1.r{rg:g}.f{fs}.{name}.{k}"])
                n += 1
                d = abs(got - want)
                worst = max(worst, d)
                bad += d > 1e-4  # stored values are rounded to 4 decimals
    fz2 = json.load(open(PC.FREEZE_DIR / "p_freeze_P2.json"))
    idx = np.flatnonzero(te)
    for rg, fs in CELLS:
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{fs}.joblib")
        df, _ = cx.cell(rg, fs)
        iv = P2.intervals(cx, df, z, fz2["calibration"][f"{rg:g}_{fs}"], idx)
        lo, hi = iv["global"]
        cov = float(((cx.ref[idx] >= lo) & (cx.ref[idx] <= hi)).mean())
        want = float(R[f"p.p2.r{rg:g}.f{fs}.global.coverage"])
        n += 1
        worst = max(worst, abs(cov - want))
        bad += abs(cov - want) > 1e-4
    print(f"{n} stored sealed values recomputed from the frozen files; {bad} differ by more than 1e-4; largest difference {worst:.2e}")


if __name__ == "__main__":
    main()
