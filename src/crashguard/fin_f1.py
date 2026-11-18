"""F1 (EXPLORATORY-REVISED): NHTSA-side reruns with real plus synthetic training pulses (docs/02_preregistration/PREREGISTRATION_V5.md section F). Training harness.

One RUN = (train rows, validation rows, test rows) of the 913 pooled records. Runs: the sealed split (development, validation, sealed fold) and five grouped, mode-stratified outer folds of nested cross-validation (the inner
validation fold is a group-wise 25% of the outer training rows). Synthetic pulses (passed modes only; generator fitted on the TRAIN rows of the run only; calibrated) train only; validation and test rows are real.
For every range at 100 Hz and every mixing ratio r in {0, 0.5, 1, 2, 5} (synthetic per real training row; r = 0 identical code) the run stores, on validation and test rows, the predictions of: direct GBM (fd), 1D CNN
(fe, seeds 0 to 4), anchored estimator (c), reliability score; plus the real-only baselines a, b and the train-on-synthetic-test-on-real (TSTR) diagnostics. Selection (best r, best model) is done afterwards on the validation rows only.
"""
from __future__ import annotations

import pickle
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from crashguard import config as C
from crashguard import fin_c as FC
from crashguard import fin_synth as G
from crashguard import pp_common as PC
from crashguard import pp_feat as PF
from crashguard import pp_models as PM
from crashguard import severity_study as SS
from crashguard.pp_ctx import Ctx

RATIOS = (0.0, 0.5, 1.0, 2.0, 5.0)
RANGES = (16.0, 32.0, 64.0)
FS = 100
OUT = C.PROCESSED / "f1_runs.pkl"
SEEDS = C.SEEDS


def _syn_job(a):
    par, mode, seed = a
    sig = G.make_pulse(par, mode, seed)
    ref = SS.reference_dv(sig)[0]
    rows = {}
    for rg in RANGES:
        y = SS.sensor_signal(sig, rg, float(FS))
        f = PF.cell_from_signal(y, rg, float(FS))
        f["dv_fill"], f["sat_share"], f["fill_applied"] = PF.fill_of(y, rg, float(FS))
        PF.V.FS = float(FS)
        v = PF.V.features_one(sig, rg)
        for k in PF.V2_DESC + PF.V2_FAM:
            f["v2_" + k] = float(v[k])
        rows[rg] = f
    return mode, ref, rows


def synth_features(par: dict, modes: list[str], mode_p: list[float], n: int, seed0: int, workers: int = 12):
    rng = np.random.default_rng(seed0)
    ms = rng.choice(len(modes), size=n, p=mode_p)
    jobs = [(par, modes[m], seed0 + 1 + k) for k, m in enumerate(ms)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_syn_job, jobs, chunksize=8))
    out = {}
    for rg in RANGES:
        rows = [r[2][rg] for r in res]
        waves = np.stack([r.pop("wave") for r in rows])
        out[rg] = (pd.DataFrame(rows), waves)
    refs = np.array([r[1] for r in res])
    return out, refs, np.array([r[0] for r in res])


def make_runs(cx: Ctx) -> list[dict]:
    """Sealed split plus five nested-CV outer folds."""
    runs = [dict(name="sealed", sid=0, tr=np.flatnonzero(cx.dev), va=np.flatnonzero(cx.val), te=np.flatnonzero(cx.test))]
    sgk = StratifiedGroupKFold(5, shuffle=True, random_state=C.SEED)
    idx = np.arange(len(cx.y))
    for k, (trn, te) in enumerate(sgk.split(idx, cx.mode_idx, cx.group)):
        g = np.unique(cx.group[trn])
        rng = np.random.default_rng(C.SEED + k)
        gv = set(rng.choice(g, size=max(1, int(round(0.25 * len(g)))), replace=False))
        isv = np.array([x in gv for x in cx.group[trn]])
        runs.append(dict(name=f"cv{k}", sid=k + 1, tr=trn[~isv], va=trn[isv], te=te))
    return runs


def _cnn_job(a):
    key, W, M, y, Wv, Mv, yv, seed = a
    return key, PM.train_cnn(W, M, y, Wv, Mv, yv, seed)


def run_one(cx: Ctx, run: dict, aug: dict, par_all: pd.DataFrame, passed: list[str], workers: int = 12) -> dict:
    tr, va, te = run["tr"], run["va"], run["te"]
    n_syn = int(round(max(RATIOS) * len(tr)))
    # generator fitted on the TRAIN rows only
    dd = par_all.iloc[tr]
    par = FC.fit_params(dd)
    use = [m for m in passed if m in par]
    cnt = np.array([(cx.mode[tr] == m).sum() for m in use], float)
    syn, sref, smode = synth_features(par, use, list(cnt / cnt.sum()), n_syn, seed0=1_000_000 + 7919 * run["sid"])
    out = dict(run=run, n_syn=n_syn, used_modes=use, ranges={})
    jobs = []
    for rg in RANGES:
        df, W = cx.cell(rg, FS)
        dfa, Wa, refa, srca = aug[rg]
        m_aug = np.isin(srca, tr)
        sdf, sW = syn[rg]
        R = dict(plain_va=df.dv_plain.to_numpy(float)[va], plain_te=df.dv_plain.to_numpy(float)[te])
        # real-only baselines
        R["b_te"] = PM.RidgeEst().fit(df.iloc[tr], cx.ref[tr], cx.group[tr]).predict(df.iloc[te])
        R["b_va"] = PM.RidgeEst().fit(df.iloc[tr], cx.ref[tr], cx.group[tr]).predict(df.iloc[va])
        for r in RATIOS:
            k = int(round(r * len(tr)))
            dfc = pd.concat([df.iloc[tr], dfa[m_aug], sdf.iloc[:k]], ignore_index=True)
            refc = np.concatenate([cx.ref[tr], refa[m_aug], sref[:k]])
            yc = PC.cls_of(refc)
            m, h = PM.fit_ord(dfc, yc, None, df.iloc[va], cx.y[va], None, False)
            R[f"fd_va_{r:g}"] = PM.cum_to_class(m.predict_cum(df.iloc[va], None))
            R[f"fd_te_{r:g}"] = PM.cum_to_class(m.predict_cum(df.iloc[te], None))
            R[f"fd_hp_{r:g}"] = h
            dfr = pd.concat([df.iloc[tr], sdf.iloc[:k]], ignore_index=True)  # the anchored estimator and the reliability score use real rows (no augmented copies, as the originals) plus synthetic rows
            refr = np.concatenate([cx.ref[tr], sref[:k]])
            ae = PM.AnchoredEst().fit(dfr, refr)
            R[f"c_va_{r:g}"], R[f"c_te_{r:g}"] = ae.predict(df.iloc[va]), ae.predict(df.iloc[te])
            tgt = np.log(np.maximum(refr, 1e-6) / np.maximum(dfr.dv_plain.to_numpy(float), 1e-6))
            rel = PM.Reliability(False).fit(dfr, tgt)
            R[f"rel_va_{r:g}"], R[f"rel_te_{r:g}"] = rel.score(df.iloc[va]), rel.score(df.iloc[te])
            Wc = np.concatenate([W[tr], Wa[m_aug], sW[:k]]).astype(np.float32)
            M0 = np.zeros((len(Wc), 0), np.float32)
            for s in SEEDS:
                jobs.append(((rg, f"{r:g}", s), Wc, M0, yc, W[va], np.zeros((len(va), 0), np.float32), cx.y[va], s))
        # TSTR: synthetic only (all synthetic rows of the run)
        ysyn = PC.cls_of(sref)
        m, _ = PM.fit_ord(sdf, ysyn, None, df.iloc[va], cx.y[va], None, False)
        R["tstr_fd_te"] = PM.cum_to_class(m.predict_cum(df.iloc[te], None))
        R["tstr_c_te"] = PM.AnchoredEst().fit(sdf, sref).predict(df.iloc[te])
        for s in SEEDS:
            jobs.append(((rg, "tstr", s), sW.astype(np.float32), np.zeros((len(sW), 0), np.float32), ysyn, W[va], np.zeros((len(va), 0), np.float32), cx.y[va], s))
        out["ranges"][rg] = R
    with ProcessPoolExecutor(workers) as ex:
        res = dict(ex.map(_cnn_job, jobs, chunksize=1))
    for rg in RANGES:
        df, W = cx.cell(rg, FS)
        R = out["ranges"][rg]
        for key in [f"{r:g}" for r in RATIOS] + ["tstr"]:
            ens = PM.CNNEns([res[(rg, key, s)] for s in SEEDS], False)
            R[f"fe_va_{key}"] = PM.cum_to_class(ens.predict_cum(W[va], None))
            R[f"fe_te_{key}"] = PM.cum_to_class(ens.predict_cum(W[te], None))
            R[f"fe_seedf1_{key}"] = [float(res[(rg, key, s)]["val_macro_f1"]) for s in SEEDS]
    return out


def main(only: str | None = None) -> None:
    cx = Ctx()
    real = pd.read_parquet("data/processed/f_real_desc.parquet")
    runs = make_runs(cx)
    passed = [m for m in G.MODES if m in set(str(x) for x in __import__("json").load(open("results/synthetic/modes_passed.json")))]
    aug = {}
    for rg in RANGES:
        cache = C.PROCESSED / f"f1_aug_all_{rg:g}.pkl"
        if cache.exists():
            aug[rg] = pickle.loads(cache.read_bytes())
        else:
            aug[rg] = PF.augment_cell(np.arange(len(cx.y)), rg, float(FS), 6)
            cache.write_bytes(pickle.dumps(aug[rg]))
    done = pickle.loads(OUT.read_bytes()) if OUT.exists() else {}
    for run in runs:
        if run["name"] in done or (only and run["name"] != only):
            continue
        done[run["name"]] = run_one(cx, run, aug, real, passed)
        OUT.write_bytes(pickle.dumps(done))
        print("run", run["name"], "done", flush=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
