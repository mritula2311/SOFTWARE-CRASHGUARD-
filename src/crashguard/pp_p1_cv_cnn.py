"""EXPLORATORY (written after the sealed fold was scored for P1; not part of H-P1 and not Holm-corrected): grouped 5-fold cross-validation over all 913 records of the augmented 1D CNN (no mode input) against fill + ridge,
the anchored estimator and the direct GBM, at 100 Hz. One repeat (the folds of repeat 0 of ``pp_p1_cv``), 3 CNN seeds per fold; the epoch is chosen on 20% of the training groups held out inside each training part; augmentation (6 copies) is applied to the
training records only. Sealed-fold records are included, so this is a pooled re-check, not a new test.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import pp_feat as PF
from crashguard import pp_models as PM
from crashguard.pp_ctx import Ctx

SRC = "results/tables/p1_cv_cnn.csv"
SEEDS = (0, 1, 2)


def _job(a):
    key, W, M, y, Wv, Mv, yv, Wt, seed = a
    r = PM.train_cnn(W, M, y, Wv, Mv, yv, seed)
    ens = PM.CNNEns([r], False)
    return key, ens.predict_cum(Wt, None)


def main() -> None:
    cx = Ctx()
    n = len(cx.y)
    ug = sorted(set(cx.group.tolist()))
    rng = np.random.default_rng(C.SEED)  # the folds of repeat 0 of pp_p1_cv
    fo = {g: k % 5 for k, g in enumerate(rng.permutation(ug))}
    fold = np.array([fo[g] for g in cx.group])
    E = PC.PEntries("p1cvcnn", SRC)
    rows = []
    for rg in PC.RANGES:
        df, W = cx.cell(rg, 100)
        dfa, Wa, refa, src = PF.augment_cell(np.arange(n), rg, 100.0, 6)
        ya = PC.cls_of(refa)
        preds = {m: np.zeros(n, int) for m in ("b", "c", "d_none", "cnn_aug")}
        jobs = []
        for f in range(5):
            te, tr = fold == f, fold != f
            trd = df[tr]
            preds["b"][te] = PC.cls_of(PM.RidgeEst().fit(trd, cx.ref[tr], cx.group[tr]).predict(df[te]))
            preds["c"][te] = PC.cls_of(PM.AnchoredEst().fit(trd, cx.ref[tr]).predict(df[te]))
            preds["d_none"][te] = PM.cum_to_class(PM.OrdGBM(8, 150, False).fit(trd, cx.y[tr], None).predict_cum(df[te], None))
            tg = sorted(set(cx.group[tr].tolist()))
            r2 = np.random.default_rng(C.SEED + 77 + f)
            iv_g = set(np.array(tg)[r2.permutation(len(tg))[: max(1, int(0.2 * len(tg)))]].tolist())
            iva = np.array([g in iv_g for g in cx.group]) & tr
            itr = tr & ~iva
            use_a = np.isin(src, np.flatnonzero(itr))
            Wtr = np.concatenate([W[itr], Wa[use_a]])
            ytr = np.concatenate([cx.y[itr], ya[use_a]])
            Mz = np.zeros((len(Wtr), 0), np.float32)
            for s in SEEDS:
                jobs.append(((f, s), Wtr, Mz, ytr, W[iva], np.zeros((int(iva.sum()), 0), np.float32), cx.y[iva], W[te], s))
        with ProcessPoolExecutor(12) as ex:
            res = dict(ex.map(_job, jobs, chunksize=1))
        for f in range(5):
            te = fold == f
            preds["cnn_aug"][te] = PM.cum_to_class(np.mean([res[(f, s)] for s in SEEDS], axis=0))
        g = PC.GBoot(cx.group)
        tag = f"r{rg:g}"
        for m, P in preds.items():
            for k, fn in (("macro_f1", PC.macro_f1), ("under_triage", PC.under_triage), ("over_triage", PC.over_triage)):
                t = g.ci(lambda i, P=P, fn=fn: fn(cx.y[i], P[i]))
                E.ci(f"{tag}.{m}.{k}", t, "fraction", "EXPLORATORY; grouped 5-fold cross-validation over all 913 records, 100 Hz")
                rows.append(dict(range_g=rg, model=m, metric=k, value=t[0], lo=t[1], hi=t[2]))
        for ref_m in ("b", "c", "d_none"):
            for k, fn in (("macro_f1", PC.macro_f1), ("under_triage", PC.under_triage)):
                t = g.ci(lambda i, ref_m=ref_m, fn=fn: fn(cx.y[i], preds["cnn_aug"][i]) - fn(cx.y[i], preds[ref_m][i]))
                E.ci(f"{tag}.paired.cnn_aug_minus_{ref_m}.{k}", t, "fraction", "EXPLORATORY; paired, same drawn groups")
                rows.append(dict(range_g=rg, model=f"cnn_aug-{ref_m}", metric=k, value=t[0], lo=t[1], hi=t[2]))
        print(rg, "done", flush=True)
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "p1_cv_cnn.csv", index=False)
    print(pd.DataFrame(rows).round(3).to_string())


if __name__ == "__main__":
    main()
