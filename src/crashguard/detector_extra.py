"""Phase 3 detector studies on the de-duplicated VZCrash test split (MEASURED_SOFTWARE).

1. Operating point: the decision threshold is chosen on VALIDATION only to meet a target false-alarm rate on non-crash events (system level: false alarms
   divided by ALL non-crash validation events, including those the trigger discarded). Test recall and the achieved false-alarm rate are then reported once.
2. Calibration: reliability bins, Brier score and expected calibration error (10 uniform bins) per probability model.
3. Bootstrap 95% intervals (1,000 resamples of test events) for the headline detector metrics.
4. Trigger sweep: system recall with intervals per trigger level, and the crash events that fall below each trigger by vehicle size category.
5. Deployment candidate: the 10-tree depth-9 forest chosen on validation, exported to C with an equivalence test. The deployed header is not replaced.

The trigger passes the pre-selected VZCrash events a second time (the events were triggered on the device before release), so these numbers do not apply to
continuous driving.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score

from crashguard import boot as B
from crashguard import config as C
from crashguard.models import ALL_SEEDS, MODEL_NAMES, PRIMARY, fit_scorer, op_thresholds
from crashguard.results import record_many
from crashguard.split import leaky_test_ids, load_variant

TARGET_FPR = (0.01, 0.05)
SEL = "rfsel"  # the random forest chosen on validation in the depth sweep (read from results.json)
NAMES = {**MODEL_NAMES, SEL: "RF chosen on validation"}
CAL_MODELS = ("rf15", SEL, "rf200", "gbt", "lr")
ALL_MODELS = ("rf15", SEL, "rf200", "gbt", "lr", "rule")
SRC = "results/tables/detector_operating_points.csv"


def selected_config(path: Path = Path("results/results.json")) -> tuple[int, int]:
    r = {e["name"]: e["value"] for e in json.loads(path.read_text(encoding="utf-8"))}
    return int(r["s4b.recommended.trees"]), int(r["s4b.recommended.depth"])


def frames_full(variant: str = PRIMARY):
    """(train triggered, validation ALL events, test ALL events de-duplicated). All events carry ``triggered``."""
    df = load_variant(variant)
    df["triggered"] = df.triggered.fillna(False).astype(bool)
    tr = df[(df.split == "train") & df.triggered]
    va = df[df.split == "validation"]
    te = df[(df.split == "test") & ~df.event_id.isin(leaky_test_ids())]
    return tr, va, te


def fit(name: str, seed: int, tr: pd.DataFrame, va_trig: pd.DataFrame):
    cols = list(C.FEATURES)
    if name == SEL:
        t, d = selected_config()
        m = RandomForestClassifier(n_estimators=t, max_depth=d, random_state=seed, n_jobs=-1)
        m.fit(tr[cols].to_numpy(np.float32), tr.y.to_numpy())
        m.set_params(n_jobs=1)  # deterministic summation order in predict_proba
        return (lambda x: m.predict_proba(x[cols].to_numpy(np.float32))[:, 1]), m
    return fit_scorer(name, seed, cols, tr, va_trig)


def score_all(scorer, df: pd.DataFrame) -> np.ndarray:
    """Score of every event; -1 for events the trigger did not pass (always predicted negative)."""
    s = np.full(len(df), -1.0)
    trig = df.triggered.to_numpy(bool)
    if trig.any():
        s[trig] = scorer(df[trig])
    return s


def threshold_for_fpr(y: np.ndarray, s: np.ndarray, target: float) -> float:
    """Smallest threshold whose false-alarm rate on ALL non-crash events is at most ``target`` (scores of untriggered events are -1, never alarms)."""
    neg = np.sort(s[(y == 0) & (s >= 0)])[::-1]
    n_neg = int((y == 0).sum())
    allowed = int(np.floor(target * n_neg))
    if allowed >= len(neg):
        return 0.0
    # alarms are scores >= thr; allow at most `allowed` negative alarms: thr just above the (allowed+1)-th largest negative score
    return float(np.nextafter(neg[allowed], np.inf))


def sys_rates(y: np.ndarray, s: np.ndarray, thr: float) -> dict:
    pred = s >= thr
    tp, fp = int((pred & (y == 1)).sum()), int((pred & (y == 0)).sum())
    return dict(recall=tp / max(int((y == 1).sum()), 1), fpr=fp / max(int((y == 0).sum()), 1), precision=tp / (tp + fp) if tp + fp else float("nan"))


def _recall_stat(a: np.ndarray) -> float:
    return float(a[a[:, 0] == 1, 1].mean())


def _fpr_stat(a: np.ndarray) -> float:
    return float(a[a[:, 0] == 0, 1].mean())


def operating_points(models=ALL_MODELS, seeds=ALL_SEEDS) -> tuple[pd.DataFrame, dict]:
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    rows, keep = [], {}
    for name in models:
        for seed in seeds:
            scorer, _m = fit(name, seed, tr, va_trig)
            s_va, s_te = score_all(scorer, va), score_all(scorer, te)
            for tgt in TARGET_FPR:
                thr = threshold_for_fpr(va.y.to_numpy(), s_va, tgt)
                v = sys_rates(va.y.to_numpy(), s_va, thr)
                t = sys_rates(te.y.to_numpy(), s_te, thr)
                rows.append(dict(model=name, seed=seed, target_fpr=tgt, threshold=thr, val_recall=v["recall"], val_fpr=v["fpr"], test_recall=t["recall"], test_fpr=t["fpr"],
                                 test_precision=t["precision"]))
                if seed == C.SEED:
                    keep[(name, tgt)] = (te.y.to_numpy(), (s_te >= thr).astype(int))
    return pd.DataFrame(rows), keep


def calibration(models=CAL_MODELS, seed: int = C.SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    tr, va, te = frames_full()
    tt = te[te.triggered]
    bins, rows = [], []
    for name in models:
        scorer, _ = fit(name, seed, tr, va[va.triggered])
        s, y = scorer(tt), tt.y.to_numpy()
        edges = np.linspace(0, 1, 11)
        b = np.clip(np.digitize(s, edges[1:-1]), 0, 9)
        ece_parts = []
        for k in range(10):
            m = b == k
            if m.any():
                bins.append(dict(model=name, bin=k, n=int(m.sum()), mean_predicted=float(s[m].mean()), fraction_positive=float(y[m].mean())))
                ece_parts.append((m.sum(), abs(s[m].mean() - y[m].mean())))
        sum(n * d for n, d in ece_parts) / len(s)
        pack = np.stack([y, s], axis=1)

        def brier(a):
            return float(np.mean((a[:, 1] - a[:, 0]) ** 2))

        def ece_stat(a):
            bb = np.clip(np.digitize(a[:, 1], edges[1:-1]), 0, 9)
            tot = 0.0
            for k in range(10):
                m = bb == k
                if m.any():
                    tot += m.sum() * abs(a[m, 1].mean() - a[m, 0].mean())
            return tot / len(a)

        bp, bl, bh = B.ci(pack, brier)
        ep, el, eh = B.ci(pack, ece_stat)
        rows.append(dict(model=name, brier=bp, brier_lo=bl, brier_hi=bh, ece=ep, ece_lo=el, ece_hi=eh, n=len(s)))
    return pd.DataFrame(rows), pd.DataFrame(bins)


def headline_ci(seed: int = C.SEED) -> pd.DataFrame:
    """AP (model level, triggered events), system AP, and system recall and false-alarm rate at the validation F1 threshold, with 95% intervals."""
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    rows = []
    for name in ("rf15", SEL, "rule", "rf200", "gbt", "lr"):
        scorer, _ = fit(name, seed, tr, va_trig)
        thr, _t95 = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
        s = score_all(scorer, te)
        y = te.y.to_numpy()
        trig = te.triggered.to_numpy(bool)
        pred = (s >= thr).astype(int)
        rec = B.ci(np.stack([y, pred], 1), _recall_stat)
        fpr = B.ci(np.stack([y, pred], 1), _fpr_stat)
        ap_m = B.ci(np.stack([y[trig], s[trig]], 1), lambda a: float(average_precision_score(a[:, 0], a[:, 1])))
        ap_s = B.ci(np.stack([y, s], 1), lambda a: float(average_precision_score(a[:, 0], a[:, 1])))
        rows.append(dict(model=name, thr_f1=thr, ap=ap_m[0], ap_lo=ap_m[1], ap_hi=ap_m[2], sys_ap=ap_s[0], sys_ap_lo=ap_s[1], sys_ap_hi=ap_s[2],
                         sys_recall=rec[0], sys_recall_lo=rec[1], sys_recall_hi=rec[2], sys_fpr=fpr[0], sys_fpr_lo=fpr[1], sys_fpr_hi=fpr[2], n_test=len(te), n_triggered=int(trig.sum())))
    return pd.DataFrame(rows)


def _mean_recall_stat(a: np.ndarray) -> float:
    """a = [y, pred_seed0, pred_seed1, ...]: recall averaged over the seed columns."""
    return float(a[a[:, 0] == 1, 1:].mean())


def _mean_fpr_stat(a: np.ndarray) -> float:
    return float(a[a[:, 0] == 0, 1:].mean())


def headline_ci_seedmean(name: str = "rf15", seeds=C.SEEDS) -> dict:
    """System recall and false-alarm rate at the validation-F1 threshold, as the MEAN over ``seeds``, with a 95% bootstrap interval FOR THAT MEAN.

    Each resample draws test events (rows) with replacement and recomputes the seed-mean of recall and of false-alarm rate on the drawn events, so the interval
    describes the 5-seed mean and not one seed. (The seed-42 table ``headline_ci`` has its own interval for seed 42.)
    """
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    y = te.y.to_numpy()
    cols = []
    for seed in seeds:
        scorer, _ = fit(name, seed, tr, va_trig)
        thr, _t95 = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
        cols.append((score_all(scorer, te) >= thr).astype(int))
    arr = np.column_stack([y] + cols)
    rec, fpr = B.ci(arr, _mean_recall_stat), B.ci(arr, _mean_fpr_stat)
    return dict(sys_recall=rec[0], sys_recall_lo=rec[1], sys_recall_hi=rec[2], sys_fpr=fpr[0], sys_fpr_lo=fpr[1], sys_fpr_hi=fpr[2], n_seeds=len(seeds), n_test=len(te))


def trigger_ci(seed: int = C.SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """System recall and AP with intervals per trigger level (RF 15 trees, seed 42) and crashes below each trigger by vehicle-size category."""
    rows, miss = [], []
    for g in C.TRIGGER_SWEEP_G:
        var = f"trig_{g:g}"
        tr, va, te = frames_full(var)
        va_trig = va[va.triggered]
        scorer, _ = fit("rf15", seed, tr, va_trig)
        thr, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
        s = score_all(scorer, te)
        y = te.y.to_numpy()
        pred = (s >= thr).astype(int)
        trig = te.triggered.to_numpy(bool)
        rec = B.ci(np.stack([y, pred], 1), _recall_stat)
        fpr = B.ci(np.stack([y, pred], 1), _fpr_stat)
        ap_s = B.ci(np.stack([y, s], 1), lambda a: float(average_precision_score(a[:, 0], a[:, 1])))
        crash_trig = B.ci(trig[y == 1].astype(float), np.mean)
        rows.append(dict(trigger_g=g, sys_recall=rec[0], sys_recall_lo=rec[1], sys_recall_hi=rec[2], sys_fpr=fpr[0], sys_fpr_lo=fpr[1], sys_fpr_hi=fpr[2],
                         sys_ap=ap_s[0], sys_ap_lo=ap_s[1], sys_ap_hi=ap_s[2], crash_pass_trigger=crash_trig[0], crash_pass_trigger_lo=crash_trig[1], crash_pass_trigger_hi=crash_trig[2]))
        for cat, d in te[te.y == 1].groupby("vehiclesize"):
            m = (~d.triggered.to_numpy(bool)).astype(float)
            p, lo, hi = B.ci(m, np.mean)
            miss.append(dict(trigger_g=g, vehiclesize=cat, crashes=len(d), below_trigger=int(m.sum()), share=p, share_lo=lo, share_hi=hi))
    return pd.DataFrame(rows), pd.DataFrame(miss)


CAND_HEADER = Path("firmware_export/crashguard_rf_candidate.h")


def deployment_candidate(seed: int = C.SEED) -> list[dict]:
    """Export the validation-selected forest to C and compare it with scikit-learn on every triggered test event (supplied test split, as for the deployed model)."""
    from crashguard.export_c import c_predict, write_header

    tr, va, _ = frames_full()
    va_trig = va[va.triggered]
    scorer, model = fit(SEL, seed, tr, va_trig)
    thr, thr95 = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
    info = write_header(model, CAND_HEADER, thr_f1=thr)
    df = load_variant(PRIMARY)
    df["triggered"] = df.triggered.fillna(False).astype(bool)
    te = df[(df.split == "test") & df.triggered]
    X = te[list(C.FEATURES)].to_numpy(np.float32)
    py = model.predict_proba(X)[:, 1]
    src = str(CAND_HEADER)
    ent = [dict(name="candidate.trees", value=info["trees"], unit="trees", origin="MEASURED_SOFTWARE", source_file=src, notes="chosen on validation in the depth sweep"),
           dict(name="candidate.nodes", value=info["nodes"], unit="nodes", origin="MEASURED_SOFTWARE", source_file=src),
           dict(name="candidate.bytes_est", value=info["bytes_est"], unit="bytes", origin="ANALYTICAL", source_file=src, notes=f"nodes x {C.NODE_BYTES} bytes; host estimate"),
           dict(name="candidate.threshold_f1", value=round(float(thr), 6), unit="probability", origin="MEASURED_SOFTWARE", source_file=src, notes="validation, maximum F1"),
           dict(name="candidate.test_rows", value=int(len(X)), unit="events", origin="MEASURED_SOFTWARE", source_file=src, notes="triggered events of the supplied test split")]
    try:
        with tempfile.TemporaryDirectory() as tmp:  # the harness includes crashguard_rf.h, so give the candidate that name in a private folder
            hdr = Path(tmp) / "crashguard_rf.h"
            shutil.copy(CAND_HEADER, hdr)
            c, cc = c_predict(hdr, X)
        diff = float(np.abs(c.astype(np.float64) - py).max())
        agree = float(((c >= thr) == (py >= thr)).mean())
        ent += [dict(name="candidate.max_abs_diff", value=diff, unit="probability", origin="MEASURED_SOFTWARE", source_file=src, notes=f"C ({cc}) against scikit-learn on the triggered test set"),
                dict(name="candidate.decision_agreement", value=agree, unit="fraction", origin="MEASURED_SOFTWARE", source_file=src),
                dict(name="candidate.equivalence_passes", value=bool(diff <= 1e-6), unit="bool", origin="MEASURED_SOFTWARE", source_file=src, notes="threshold 1e-6")]
    except RuntimeError as err:
        ent.append(dict(name="candidate.max_abs_diff", value="NOT_RUN", unit="probability", origin="NOT_RUN", source_file=src, notes=str(err)[:200]))
    return ent


def figures(cal_bins: pd.DataFrame, op: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.plot([0, 1], [0, 1], "k--", lw=0.8, label="perfect")
    for i, (m, g) in enumerate(cal_bins.groupby("model", sort=False)):
        ax.plot(g.mean_predicted, g.fraction_positive, "o-", ms=3, color=COLORS[i], label=NAMES[m])
    ax.set_xlabel("Mean predicted crash probability")
    ax.set_ylabel("Fraction of triggered test events that are crashes")
    ax.legend(fontsize=7)
    ax.set_title("Reliability, de-duplicated test, seed 42", fontsize=9)
    save(fig, "detector_reliability")
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, tgt in enumerate(TARGET_FPR):
        g = op[op.target_fpr == tgt].groupby("model", sort=False).test_recall.agg(["mean", "std"]).reindex(list(ALL_MODELS))
        ax.bar(np.arange(len(g)) + (i - 0.5) * 0.38, g["mean"], 0.38, yerr=g["std"], color=COLORS[i], capsize=2, label=f"false-alarm rate fixed at {tgt:.0%} on validation")
    ax.set_xticks(range(len(ALL_MODELS)), [NAMES[m].replace(" chosen on validation", " sel.") for m in ALL_MODELS], rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("System recall on the test set")
    ax.legend(fontsize=7)
    save(fig, "detector_operating_points")


def main() -> None:
    C.TABLES.mkdir(parents=True, exist_ok=True)
    ent: list[dict] = []

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes="", src=SRC):
        ent.append(dict(name=f"detector.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    op, keep = operating_points()
    op.to_csv(C.TABLES / "detector_operating_points.csv", index=False)
    for (name, tgt), (y, pred) in keep.items():
        rec = B.ci(np.stack([y, pred], 1), _recall_stat)
        fpr = B.ci(np.stack([y, pred], 1), _fpr_stat)
        for lab, v in (("recall", rec), ("fpr", fpr)):
            add(f"op.t{int(tgt * 100)}.{name}.seed42.{lab}", round(v[0], 4), "fraction", notes="de-duplicated test set, threshold chosen on validation to meet the target system-level false-alarm rate")
            add(f"op.t{int(tgt * 100)}.{name}.seed42.{lab}_lo", round(v[1], 4), "fraction")
            add(f"op.t{int(tgt * 100)}.{name}.seed42.{lab}_hi", round(v[2], 4), "fraction")
    for (name, tgt), g in op[op.seed.isin(C.SEEDS)].groupby(["model", "target_fpr"]):
        for col in ("test_recall", "test_fpr", "val_fpr", "val_recall", "test_precision"):
            add(f"op.t{int(tgt * 100)}.{name}.{col}.mean", round(float(g[col].mean()), 4), "fraction", notes="mean over seeds 0-4")
            add(f"op.t{int(tgt * 100)}.{name}.{col}.std", round(float(g[col].std(ddof=1)), 4), "fraction")

    cal, bins = calibration()
    cal.to_csv(C.TABLES / "detector_calibration.csv", index=False)
    bins.to_csv(C.TABLES / "detector_reliability_bins.csv", index=False)
    for r in cal.itertuples():
        for k in ("brier", "brier_lo", "brier_hi", "ece", "ece_lo", "ece_hi"):
            add(f"cal.{r.model}.{k}", round(float(getattr(r, k)), 5), "score", src="results/tables/detector_calibration.csv", notes="de-duplicated test, triggered events, seed 42; 10 uniform bins")

    h = headline_ci()
    h.to_csv(C.TABLES / "detector_headline_ci.csv", index=False)
    for r in h.itertuples():
        for k in ("ap", "ap_lo", "ap_hi", "sys_ap", "sys_ap_lo", "sys_ap_hi", "sys_recall", "sys_recall_lo", "sys_recall_hi", "sys_fpr", "sys_fpr_lo", "sys_fpr_hi", "thr_f1"):
            add(f"head.{r.model}.{k}", round(float(getattr(r, k)), 4), "score", src="results/tables/detector_headline_ci.csv", notes="seed 42, de-duplicated test, 1,000 bootstrap resamples of test events, threshold from validation (maximum F1)")
        add(f"head.{r.model}.n_test", int(r.n_test), "events", src="results/tables/detector_headline_ci.csv")
        add(f"head.{r.model}.n_triggered", int(r.n_triggered), "events", src="results/tables/detector_headline_ci.csv")

    h5 = headline_ci_seedmean()
    for k, v in h5.items():
        add(f"head5.rf15.{k}", round(float(v), 4) if isinstance(v, float) else int(v), "fraction" if k.startswith("sys") else "count", src="results/tables/detector_headline_ci.csv",
            notes="MEAN over seeds 0-4 (validation-F1 threshold per seed); the interval is a 95% bootstrap of test events for that seed-mean (1,000 resamples)")

    tg, miss = trigger_ci()
    tg.to_csv(C.TABLES / "detector_trigger_ci.csv", index=False)
    miss.to_csv(C.TABLES / "detector_trigger_missed_by_size.csv", index=False)
    for r in tg.itertuples():
        for k in tg.columns:
            if k != "trigger_g":
                add(f"trig.{r.trigger_g:g}.{k}", round(float(getattr(r, k)), 4), "fraction", src="results/tables/detector_trigger_ci.csv", notes="RF 15 trees, seed 42, de-duplicated test")
    for r in miss.itertuples():
        for k in ("crashes", "below_trigger", "share", "share_lo", "share_hi"):
            add(f"trigmiss.{r.trigger_g:g}.{r.vehiclesize}.{k}", round(float(getattr(r, k)), 4) if k.startswith("share") else int(getattr(r, k)), "fraction" if k.startswith("share") else "events",
                src="results/tables/detector_trigger_missed_by_size.csv", notes="crash events that never pass the trigger, by VZCrash vehicle-size category")

    ent += deployment_candidate()
    record_many(ent, purge_prefixes=("detector.", "candidate."))
    figures(bins, op)
    print(h.round(4).to_string())
    print(tg.round(4).to_string())


if __name__ == "__main__":
    main()
