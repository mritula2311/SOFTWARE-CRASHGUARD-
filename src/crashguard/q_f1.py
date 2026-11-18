"""Q1 (EXPLORATORY-REVISED): NHTSA-side reruns with real plus physics-based synthetic training pulses (docs/02_preregistration/PREREGISTRATION_V7.md section 2).

Reuses the training harness of ``fin_f1`` unchanged (same runs: the sealed split and five grouped nested-CV outer folds; same ratios {0, 0.5, 1, 2, 5}; same models, seeds 0 to 4) and swaps only the generator:
``PH-A`` (primary), ``PH-B`` and ``FAM`` (alternatives). The generator is fitted on the TRAIN rows of each run only; pulses that fail a physical check or leave the real joint range are dropped (the share is stored);
only the modes that passed the realism gate of that generator are used. Output: data/processed/q_f1_<gen>_runs.pkl. Selection and scoring are in ``q_eval``.

    python -m crashguard.q_f1 PH-A [run_name|all] [ungated]
"""
from __future__ import annotations

import json
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import fin_f1 as F1
from crashguard import fin_synth as FSY
from crashguard import ph_gen as PG
from crashguard import pp_feat as PF
from crashguard import severity_study as SS
from crashguard.pp_ctx import Ctx

KIND = {"PH-A": "a", "PH-B": "b"}
STATS: list[dict] = []
OVERSHOOT = 1.35
CHECKS = ("integral", "restitution", "energy", "crush", "closing_velocity", "complete")


def _features(sig: dict) -> dict:
    rows = {}
    for rg in F1.RANGES:
        y = SS.sensor_signal(sig, rg, float(F1.FS))
        f = PF.cell_from_signal(y, rg, float(F1.FS))
        f["dv_fill"], f["sat_share"], f["fill_applied"] = PF.fill_of(y, rg, float(F1.FS))
        PF.V.FS = float(F1.FS)
        v = PF.V.features_one(sig, rg)
        for k in PF.V2_DESC + PF.V2_FAM:
            f["v2_" + k] = float(v[k])
        rows[rg] = f
    return rows


def _phys_job(a):
    from crashguard import ph_gates as PGT

    gen, par, mode, n, seed = a
    sigs, diag = PG.make_batch(par, mode, n, seed, KIND[gen], with_diag=True)
    chk = PGT.physical_checks(diag, mode)
    ok = np.all([np.array(chk[k]).astype(bool) for k in CHECKS], axis=0)
    out, n_rng_fail = [], 0
    for i, sig in enumerate(sigs):
        if not ok[i]:
            continue
        d1 = FSY.descriptors(sig)
        if d1 is None or not PG.range_ok(par[mode], d1):
            n_rng_fail += 1
            continue
        out.append((mode, float(d1["dv_kmh"]), _features(sig)))
    return out, dict(mode=mode, n=n, n_phys_fail=int((~ok).sum()), n_range_fail=n_rng_fail)


def _fam_job(a):
    par, mode, seed = a
    sig = FSY.make_pulse(par, mode, seed)
    return mode, SS.reference_dv(sig)[0], _features(sig)


def make_synth_features(gen: str):
    def synth_features(par: dict, modes: list[str], mode_p: list[float], n: int, seed0: int, workers: int = 12):
        rng = np.random.default_rng(seed0)
        ms = rng.choice(len(modes), size=int(np.ceil(n * (OVERSHOOT if gen != "FAM" else 1.0))), p=mode_p)
        if gen == "FAM":
            jobs = [(par, modes[m], seed0 + 1 + k) for k, m in enumerate(ms)]
            with ProcessPoolExecutor(workers) as ex:
                res = list(ex.map(_fam_job, jobs, chunksize=8))
            STATS.append(dict(gen=gen, n_asked=n, n_generated=len(res), n_phys_fail=0, n_range_fail=0))
        else:
            jobs, s = [], seed0
            for mi, mode in enumerate(modes):
                cnt = int((ms == mi).sum())
                for b0 in range(0, cnt, 48):
                    jobs.append((gen, par, mode, min(48, cnt - b0), s))
                    s += 1000
            with ProcessPoolExecutor(workers) as ex:
                parts = list(ex.map(_phys_job, jobs, chunksize=1))
            res = [r for pp, _ in parts for r in pp]
            STATS.append(dict(gen=gen, n_asked=n, n_generated=sum(i["n"] for _, i in parts), n_phys_fail=sum(i["n_phys_fail"] for _, i in parts), n_range_fail=sum(i["n_range_fail"] for _, i in parts), n_kept=len(res)))
            perm = np.random.default_rng(seed0 + 5).permutation(len(res))  # any prefix keeps the mode mix
            res = [res[i] for i in perm][:n]
        out = {}
        for rg in F1.RANGES:
            rows = [r[2][rg] for r in res]
            waves = np.stack([r.pop("wave") for r in rows])
            out[rg] = (pd.DataFrame(rows), waves)
        return out, np.array([r[1] for r in res]), np.array([r[0] for r in res])

    return synth_features


def make_fit(gen: str):
    def fit_params(df: pd.DataFrame, calibrate: bool = True) -> dict:
        if gen == "FAM":
            par = FSY.fit(df.to_dict("records"), df["mode"].tolist())
            return FSY.calibrate(par) if calibrate else par
        return PG.fit(df, KIND[gen], 100, 120)

    return fit_params


def configure(gen: str, ungated: bool = False) -> Path:
    out = C.PROCESSED / f"q_f1_{gen.replace('-', '').lower()}{'_ungated' if ungated else ''}_runs.pkl"
    F1.OUT = out
    F1.FC.fit_params = make_fit(gen)
    F1.synth_features = make_synth_features(gen)
    return out


def main(gen: str, only: str | None = None, ungated: bool = False) -> None:
    """``ungated``: use all four modes although the generator failed the realism gate (EXPLORATORY arm, labelled so in every key and table)."""
    out = configure(gen, ungated)
    cx = Ctx()
    real = pd.read_parquet("data/processed/ph_real_desc.parquet")
    runs = F1.make_runs(cx)
    passed = list(PG.MODES) if ungated else json.load(open(Path("results/synthetic") / f"ph_modes_passed_{gen.replace('-', '').lower()}.json"))
    aug = {}
    for rg in F1.RANGES:
        aug[rg] = pickle.loads((C.PROCESSED / f"f1_aug_all_{rg:g}.pkl").read_bytes())
    done = pickle.loads(out.read_bytes()) if out.exists() else {}
    for run in runs:
        if run["name"] in done or (only and run["name"] != only):
            continue
        n0 = len(STATS)
        done[run["name"]] = F1.run_one(cx, run, aug, real, passed)
        done[run["name"]]["synth_stats"] = STATS[n0:]
        out.write_bytes(pickle.dumps(done))
        print(gen, "run", run["name"], "done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "all" else None, "ungated" in sys.argv)
