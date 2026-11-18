"""P1 (docs/02_preregistration/PREREGISTRATION_V4.md section 1) and Z1: severity triage as a classification problem, with the sealed fold scored once.

``python -m crashguard.pp_p1 fit``   fits every model on development, selects on validation, writes data/processed/pp_models/p1_*.joblib, the validation table, and the freeze file (committed by ``pp_common.freeze``).
``python -m crashguard.pp_p1 eval``  scores the frozen models on the SEALED fold once (``sealed_gate``) and writes the ``p.p1.*`` keys, tables and the H-P1 verdict inputs.
Model names: a (plain), b (fill + ridge), c (anchored); d, e (direct GBM, CNN), fd, fe (with augmentation); suffix none, oracle (true mode, not deployable), inferred (deployable).
"""
from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor

import joblib
import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import pp_feat as PF
from crashguard import pp_models as PM
from crashguard.pp_ctx import Ctx

CELLS = [(rg, fs) for fs in PC.RATES for rg in PC.RANGES]
MODEL_DIR = C.PROCESSED / "pp_models"
KINDS = ("d", "e", "fd", "fe")
MODEV = ("none", "oracle", "inferred")
BASE = ("a", "b", "c")
DEPLOY = [f"{k}_{m}" for k in KINDS for m in ("none", "inferred")]
SRC = "results/tables/p1_sealed.csv"
NAMES = {"a": "plain", "b": "fill + ridge", "c": "anchored", "d": "direct GBM", "e": "1D CNN", "fd": "direct GBM, augmented", "fe": "1D CNN, augmented"}
COPIES = 6
SEEDS = C.SEEDS


def aug_cache(cx: Ctx, rg: float, fs: int):
    p = C.PROCESSED / f"pp_aug_{rg:g}_{fs}.pkl"
    if p.exists():
        return joblib.load(p)
    r = PF.augment_cell(np.flatnonzero(cx.dev), rg, float(fs), COPIES)
    joblib.dump(r, p)
    return r


def _cnn_job(a):
    key, W, M, y, Wv, Mv, yv, seed = a
    return key, PM.train_cnn(W, M, y, Wv, Mv, yv, seed)


def mode_vec(kind: str, oracle: np.ndarray, inferred: np.ndarray):
    return {"none": None, "oracle": oracle, "inferred": inferred}[kind]


def predict(name: str, obj, df: pd.DataFrame, W: np.ndarray, oracle: np.ndarray, inferred: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    """(predicted class, cumulative probabilities or None) of a fitted model on the rows of ``df``."""
    kind, _, mv = name.partition("_")
    if kind == "a":
        return PC.cls_of(df.dv_plain.to_numpy(float)), None
    if kind in ("b", "c"):
        return PC.cls_of(obj.predict(df)), None
    m = mode_vec(mv, oracle, inferred)
    p = obj.predict_cum(df, m) if kind in ("d", "fd") else obj.predict_cum(W, m)
    return PM.cum_to_class(p), p


def fit_all(cx: Ctx, workers: int = 12) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    out_rows = []
    jobs = []
    store: dict = {}
    for rg, fs in CELLS:
        df, W = cx.cell(rg, fs)
        mi = PM.crossfit_mode(df, cx.mode_idx, cx.group, cx.dev)
        modeclf = PM.ModeClf().fit(df[cx.dev], cx.mode_idx[cx.dev])
        acc_val = float(np.mean(mi[cx.val] == cx.mode_idx[cx.val]))
        models: dict = {}
        hp: dict = {}
        models["a"] = None
        models["b"] = PM.RidgeEst().fit(df[cx.dev], cx.ref[cx.dev], cx.group[cx.dev])
        models["c"] = PM.AnchoredEst().fit(df[cx.dev], cx.ref[cx.dev])
        dfa, Wa, refa, src = aug_cache(cx, rg, fs)
        ya = PC.cls_of(refa)
        for mv in MODEV:
            use = mv != "none"
            tr_m = mode_vec(mv, cx.mode_idx, mi)
            va_m = mode_vec(mv, cx.mode_idx, mi)
            m, h = PM.fit_ord(df[cx.dev], cx.y[cx.dev], None if tr_m is None else tr_m[cx.dev], df[cx.val], cx.y[cx.val], None if va_m is None else va_m[cx.val], use)
            models[f"d_{mv}"], hp[f"d_{mv}"] = m, h
            dfc = pd.concat([df[cx.dev], dfa], ignore_index=True)
            yc = np.concatenate([cx.y[cx.dev], ya])
            mc = None if tr_m is None else np.concatenate([tr_m[cx.dev], tr_m[src]])
            m, h = PM.fit_ord(dfc, yc, mc, df[cx.val], cx.y[cx.val], None if va_m is None else va_m[cx.val], use)
            models[f"fd_{mv}"], hp[f"fd_{mv}"] = m, h
            # CNN jobs (5 seeds), plain and augmented
            Mtr = PM.onehot(tr_m) if use else np.zeros((len(df), 0), np.float32)
            for kind, Wtr, ytr, Mt in (("e", W[cx.dev], cx.y[cx.dev], Mtr[cx.dev]), ("fe", np.concatenate([W[cx.dev], Wa]), np.concatenate([cx.y[cx.dev], ya]), np.concatenate([Mtr[cx.dev], Mtr[src]]))):
                for s in SEEDS:
                    jobs.append(((rg, fs, f"{kind}_{mv}", s), Wtr, Mt, ytr, W[cx.val], Mtr[cx.val], cx.y[cx.val], s))
        store[(rg, fs)] = dict(models=models, hp=hp, modeclf=modeclf, mode_val_acc=acc_val)
        print("cell", rg, fs, "fitted (GBM, estimators); mode val acc", round(acc_val, 3), flush=True)
    print(len(jobs), "CNN runs", flush=True)
    with ProcessPoolExecutor(workers) as ex:
        res = dict(ex.map(_cnn_job, jobs, chunksize=1))
    for (rg, fs), s in store.items():
        for kind in ("e", "fe"):
            for mv in MODEV:
                runs = [res[(rg, fs, f"{kind}_{mv}", sd)] for sd in SEEDS]
                s["models"][f"{kind}_{mv}"] = PM.CNNEns(runs, mv != "none")
                s["hp"][f"{kind}_{mv}"] = dict(epochs=[r["epoch"] for r in runs], seed_val_macro_f1=[r["val_macro_f1"] for r in runs])
    # validation table and selection
    sel = {}
    for (rg, fs), s in store.items():
        df, W = cx.cell(rg, fs)
        mi = PM.crossfit_mode(df, cx.mode_idx, cx.group, cx.dev)
        vm = {}
        for name, obj in s["models"].items():
            pr, _ = predict(name, obj, df[cx.val], W[cx.val], cx.mode_idx[cx.val], mi[cx.val])
            f = PC.macro_f1(cx.y[cx.val], pr)
            vm[name] = f
            out_rows.append(dict(range_g=rg, rate_hz=fs, model=name, val_macro_f1=f, val_under_triage=PC.under_triage(cx.y[cx.val], pr), val_over_triage=PC.over_triage(cx.y[cx.val], pr)))
        order = [n for n in BASE] + DEPLOY  # ties go to the earlier (simpler) name
        best_base = max(BASE, key=lambda n: (round(vm[n], 9), -BASE.index(n)))
        best_dir = max(DEPLOY, key=lambda n: (round(vm[n], 9), -order.index(n)))
        sel[f"{rg:g}_{fs}"] = dict(best_base=best_base, best_direct=best_dir, val_macro_f1=vm, hyper=s["hp"], mode_val_acc=s["mode_val_acc"])
        joblib.dump(dict(models=s["models"], modeclf=s["modeclf"]), MODEL_DIR / f"p1_{rg:g}_{fs}.joblib")
        print(rg, fs, "best base", best_base, round(vm[best_base], 3), "best direct", best_dir, round(vm[best_dir], 3), flush=True)
    pd.DataFrame(out_rows).to_csv(C.TABLES / "p1_validation.csv", index=False)
    files = [MODEL_DIR / f"p1_{rg:g}_{fs}.joblib" for rg, fs in CELLS]
    h = PC.freeze("P1", dict(selection=sel, note="models fitted on development; hyper-parameters, best baseline and best deployable direct model per cell chosen on validation macro-F1; sealed fold not used"), files)
    print("freeze", h)


def metrics_row(y, p, g: PC.GBoot) -> dict:
    out = {}
    for k, fn in PC.TRIAGE.items():
        out[k] = g.ci(lambda i, fn=fn: fn(y[i], p[i]))
    return out


def eval_sealed(cx: Ctx) -> None:
    import json

    fz = json.loads((PC.FREEZE_DIR / "p_freeze_P1.json").read_text(encoding="utf-8"))
    for rg, fs in CELLS:  # the frozen files must be the committed ones
        f = MODEL_DIR / f"p1_{rg:g}_{fs}.joblib"
        assert PC.sha256_file(f) == fz["model_files"][str(f)], f"model file changed after the freeze: {f}"
    h = PC.sealed_gate("P1")
    E = PC.PEntries("p1", SRC)
    E.add("freeze_commit", h, "commit", "commit of the freeze of P1 (models and settings fixed before the sealed fold was scored)")
    te = cx.test
    y, grp = cx.y[te], cx.group[te]
    g = PC.GBoot(grp)
    rows, per_mode = [], []
    verdict = {}
    for rg, fs in CELLS:
        z = joblib.load(MODEL_DIR / f"p1_{rg:g}_{fs}.joblib")
        df, W = cx.cell(rg, fs)
        mi = z["modeclf"].predict(df)
        mode_acc = PC.GBoot(cx.group[te]).ci(lambda i: float(np.mean(mi[te][i] == cx.mode_idx[te][i])))
        bacc = PC.balanced_acc(cx.mode_idx[te], mi[te], 4)
        tag = f"r{rg:g}.f{fs}"
        E.ci(f"{tag}.mode.accuracy", mode_acc, "fraction", "mode classifier (Z1), sealed fold")
        E.add(f"{tag}.mode.balanced_accuracy", round(bacc, 4), "fraction", "mode classifier (Z1), sealed fold")
        cm = pd.crosstab(pd.Series(cx.mode[te], name="true"), pd.Series(np.array(PC.MODES)[mi[te]], name="inferred"))
        cm.to_csv(C.TABLES / f"p1_mode_confusion_r{rg:g}_f{fs}.csv")
        sel = fz["selection"][f"{rg:g}_{fs}"]
        preds = {}
        for name, obj in z["models"].items():
            pr, _ = predict(name, obj, df[te], W[te], cx.mode_idx[te], mi[te])
            preds[name] = pr
            m = metrics_row(y, pr, g)
            for k, t in m.items():
                E.ci(f"{tag}.{name}.{k}", t, "fraction")
                rows.append(dict(range_g=rg, rate_hz=fs, model=name, metric=k, value=t[0], lo=t[1], hi=t[2]))
            for mo in PC.MODES:
                mk = cx.mode[te] == mo
                if mk.sum():
                    per_mode.append(dict(range_g=rg, rate_hz=fs, model=name, mode=mo, n=int(mk.sum()), accuracy=float(np.mean(pr[mk] == y[mk])), under_triage=PC.under_triage(y[mk], pr[mk]), over_triage=PC.over_triage(y[mk], pr[mk])))
        bb, bd = sel["best_base"], sel["best_direct"]
        E.add(f"{tag}.selected.best_base", bb, "model", "chosen on validation macro-F1")
        E.add(f"{tag}.selected.best_direct", bd, "model", "deployable direct model chosen on validation macro-F1")
        pf, df_ = g.stat(lambda i: PC.macro_f1(y[i], preds[bd][i]) - PC.macro_f1(y[i], preds[bb][i]))
        pu, du = g.stat(lambda i: PC.under_triage(y[i], preds[bd][i]) - PC.under_triage(y[i], preds[bb][i]))
        E.ci(f"{tag}.paired.macro_f1_direct_minus_base", PC.summ(pf, df_), "fraction", "best deployable direct model minus best of (a) to (c), sealed fold, grouped paired bootstrap")
        E.ci(f"{tag}.paired.under_triage_direct_minus_base", PC.summ(pu, du), "fraction", "negative = the direct model under-triages less")
        # oracle-mode variants, labelled
        bo = max([f"{k}_oracle" for k in KINDS], key=lambda n: sel["val_macro_f1"][n])
        po, do = g.stat(lambda i: PC.macro_f1(y[i], preds[bo][i]) - PC.macro_f1(y[i], preds[bb][i]))
        E.ci(f"{tag}.paired.macro_f1_oracle_direct_minus_base", PC.summ(po, do), "fraction", f"ORACLE mode (true crash mode, not available to a node); model {bo}")
        pv, dv = g.stat(lambda i: PC.under_triage(y[i], preds[bo][i]) - PC.under_triage(y[i], preds[bb][i]))
        E.ci(f"{tag}.paired.under_triage_oracle_direct_minus_base", PC.summ(pv, dv), "fraction", f"ORACLE mode; model {bo}")
        p_f = PC.p_below(df_, 0.0)
        p_u = PC.p_above(du, 0.0)
        ok = pf >= 0.03 and np.quantile(df_, 0.025) > 0 and pu <= -0.03 and np.quantile(du, 0.975) < 0
        E.add(f"{tag}.criterion_met", int(ok), "flag", "macro-F1 gain at least 0.03 with the interval above zero AND under-triage lower by at least 0.03 with the interval below zero")
        verdict[(rg, fs)] = dict(ok=bool(ok), p=max(p_f, p_u), pf=p_f, pu=p_u)
    pd.DataFrame(rows).to_csv(C.TABLES / "p1_sealed.csv", index=False)
    pd.DataFrame(per_mode).to_csv(C.TABLES / "p1_sealed_by_mode.csv", index=False)
    prim = [verdict[(rg, PC.PRIMARY_RATE)] for rg in PC.RANGES]
    ps = sorted(v["p"] for v in prim)
    n_ok = sum(v["ok"] for v in prim)
    E.add("hP1.n_ranges_meeting_criterion", n_ok, "ranges", "of +-16, +-32, +-64 g at 100 Hz")
    E.add("hP1.criterion_met", int(n_ok >= 2), "flag", "at least two of three ranges (100 Hz)")
    E.add("hP1.p_raw", round(min(1.0, 2 * ps[1]), 4), "probability", "min(1, 2 x the second-smallest per-range p-value); per-range p = larger of the two one-sided bootstrap p-values (margin 0); floor 0.001")
    for (rg, fs), v in verdict.items():
        E.add(f"hP1.r{rg:g}.f{fs}.p", round(v["p"], 4), "probability")
    E.flush()
    PC.time_log("P1 sealed", "sealed fold scored once for P1; freeze commit " + h[:8])
    print("H-P1 ranges meeting criterion:", n_ok, "p", min(1.0, 2 * ps[1]))


if __name__ == "__main__":
    cx = Ctx()
    {"fit": lambda: fit_all(cx), "eval": lambda: eval_sealed(cx)}[sys.argv[1]]()
