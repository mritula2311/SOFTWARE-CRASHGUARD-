"""EXPLORATORY (docs/02_preregistration/PREREGISTRATION_V4.md section 1, last paragraph): grouped 5-fold cross-validation over all 913 records for models (a) to (d) at 100 Hz, to show the size of the differences with more records than the sealed fold.

Not a hypothesis test and not part of the Holm family. Folds: whole make-and-model groups, seed 42 (10 repeats would be costly; 3 repeats). Hyper-parameters of (d) are fixed (8 leaves, 150 trees) because there is no validation fold to tune on; the ridge strength of (b) is chosen by leave-one-group-out inside each training part. The sealed-fold records are INCLUDED here: this analysis was run after the sealed fold had been scored for P1 and says so.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import pp_models as PM
from crashguard.pp_ctx import Ctx

REPEATS = 3
SRC = "results/tables/p1_cv.csv"


def main() -> None:
    cx = Ctx()
    n = len(cx.y)
    ug = sorted(set(cx.group.tolist()))
    E = PC.PEntries("p1cv", SRC)
    rows = []
    for rg in PC.RANGES:
        df, _ = cx.cell(rg, PC.PRIMARY_RATE)
        preds = {m: np.zeros((REPEATS, n), int) for m in ("a", "b", "c", "d_none", "d_inferred")}
        for rep in range(REPEATS):
            rng = np.random.default_rng(C.SEED + rep)
            fo = {g: k % 5 for k, g in enumerate(rng.permutation(ug))}
            fold = np.array([fo[g] for g in cx.group])
            for f in range(5):
                te, tr = fold == f, fold != f
                trd = df[tr]
                preds["a"][rep, te] = PC.cls_of(df.dv_plain.to_numpy(float)[te])
                preds["b"][rep, te] = PC.cls_of(PM.RidgeEst().fit(trd, cx.ref[tr], cx.group[tr]).predict(df[te]))
                preds["c"][rep, te] = PC.cls_of(PM.AnchoredEst().fit(trd, cx.ref[tr]).predict(df[te]))
                m0 = PM.OrdGBM(8, 150, False).fit(trd, cx.y[tr], None)
                preds["d_none"][rep, te] = PM.cum_to_class(m0.predict_cum(df[te], None))
                idx = np.flatnonzero(tr)
                mi = np.zeros(n, int)
                from sklearn.model_selection import GroupKFold
                for a, b in GroupKFold(5).split(idx, cx.y[idx], cx.group[idx]):
                    mi[idx[b]] = PM.ModeClf().fit(df.iloc[idx[a]], cx.mode_idx[idx[a]]).predict(df.iloc[idx[b]])
                mi[te] = PM.ModeClf().fit(trd, cx.mode_idx[tr]).predict(df[te])
                m1 = PM.OrdGBM(8, 150, True).fit(trd, cx.y[tr], mi[tr])
                preds["d_inferred"][rep, te] = PM.cum_to_class(m1.predict_cum(df[te], mi[te]))
            print(rg, "repeat", rep, flush=True)
        g = PC.GBoot(cx.group)
        y = cx.y
        tag = f"r{rg:g}"
        for m, P in preds.items():
            for k, fn in (("macro_f1", PC.macro_f1), ("under_triage", PC.under_triage), ("over_triage", PC.over_triage)):
                pt, d = g.stat(lambda i, P=P, fn=fn: float(np.mean([fn(y[i], P[r][i]) for r in range(REPEATS)])))
                E.ci(f"{tag}.{m}.{k}", PC.summ(pt, d), "fraction", "EXPLORATORY; mean over 3 repeats of grouped 5-fold cross-validation, all 913 records; grouped bootstrap")
                rows.append(dict(range_g=rg, model=m, metric=k, value=pt, lo=float(np.quantile(d, 0.025)), hi=float(np.quantile(d, 0.975))))
        for ref_m in ("b", "c"):
            for new in ("d_none", "d_inferred"):
                for k, fn in (("macro_f1", PC.macro_f1), ("under_triage", PC.under_triage)):
                    pt, d = g.stat(lambda i, ref_m=ref_m, new=new, fn=fn: float(np.mean([fn(y[i], preds[new][r][i]) - fn(y[i], preds[ref_m][r][i]) for r in range(REPEATS)])))
                    E.ci(f"{tag}.paired.{new}_minus_{ref_m}.{k}", PC.summ(pt, d), "fraction", "EXPLORATORY; paired, same drawn groups")
                    rows.append(dict(range_g=rg, model=f"{new}-{ref_m}", metric=k, value=pt, lo=float(np.quantile(d, 0.025)), hi=float(np.quantile(d, 0.975))))
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "p1_cv.csv", index=False)
    print(pd.DataFrame(rows).round(3).to_string())


if __name__ == "__main__":
    main()
