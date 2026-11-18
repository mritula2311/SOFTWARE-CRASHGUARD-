"""V4: leakage sensitivity of the headline detector metrics on VZCrash (MEASURED_SOFTWARE).

Three test sets, with the duplicate sets taken from the independent audit of ``vz_audit`` (not from the earlier scan):
  supplied : every supplied test event (24,172 after the 2 events with a raw peak above 16 g are dropped, as in the pipeline);
  exact    : without test events whose full accelerometer array also occurs in train or validation (the independent hash);
  near     : without those and without the test events whose trigger-aligned window equals (T5 rule) a train or validation window.
Models: the 15-tree forest of the headline and the 10-tree depth-9 forest chosen on validation. Training, thresholds (validation F1 maximum; the 1% and 5% system-level false-alarm targets from
validation) and seeds 0 to 4 are those of the headline pipeline; only the evaluated test events differ. Intervals: 1,000 bootstrap resamples of the supplied test events; the same drawn events feed
every set, so the differences are paired. The test split is scored once per model and seed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import SEL, fit, score_all, threshold_for_fpr
from crashguard.jp_common import Entries
from crashguard.models import op_thresholds
from crashguard.s2_dedup import fast_ap, load_frames

OUT = C.TABLES
SRC = "results/tables/vz_leakage.csv"
MODELS = ("rf15", SEL)
SEEDS = C.SEEDS
SETS = ("supplied", "exact", "near")
METS = ("sys_recall", "recall_at_1pct", "recall_at_5pct", "ap", "sys_ap")


def masks(te: pd.DataFrame) -> dict[str, np.ndarray]:
    ex = set(pd.read_csv(OUT / "vz_audit_test_exact_copy_ids.csv").event_id)
    fl = pd.read_csv(OUT / "vz_audit_test_near_dup_flags.csv")
    near = set(fl.event_id[fl.flagged_near_duplicate])
    ids = te.event_id.to_numpy()
    is_ex = np.isin(ids, list(ex))
    is_nr = np.isin(ids, list(near)) | is_ex
    return {"supplied": np.ones(len(te), bool), "exact": ~is_ex, "near": ~is_nr}


def main() -> None:
    tr, va, te = load_frames()
    va_trig = va[va.triggered]
    y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
    M = masks(te)
    E = Entries("vz.v4", SRC)
    for k, m in M.items():
        E.add(f"n_events.{k}", int(m.sum()), "events")
        E.add(f"n_crash.{k}", int(y[m].sum()), "events")
        E.add(f"n_triggered_crash.{k}", int((y[m] & trig[m]).sum()), "events")
    rows = []
    for model in MODELS:
        S_, T_ = [], []
        for seed in SEEDS:
            scorer, _ = fit(model, seed, tr, va_trig)
            s_va = score_all(scorer, va)
            thr_f1, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
            t1, t5 = (threshold_for_fpr(va.y.to_numpy(), s_va, g) for g in (0.01, 0.05))
            S_.append(score_all(scorer, te))
            T_.append((thr_f1, t1, t5))

        def stat(idx: np.ndarray, S_=S_, T_=T_) -> dict:
            out = {}
            for k, m in M.items():
                sel = idx[m[idx]]
                yy, tt = y[sel], trig[sel]
                per = []
                for s, (a, b, c) in zip(S_, T_):
                    ss = s[sel]
                    pos = yy == 1
                    per.append(dict(sys_recall=float((ss[pos] >= a).mean()), recall_at_1pct=float((ss[pos] >= b).mean()), recall_at_5pct=float((ss[pos] >= c).mean()),
                                    ap=fast_ap(yy[tt], ss[tt]), sys_ap=fast_ap(yy, ss)))
                for met in METS:
                    out[(k, met)] = float(np.mean([p[met] for p in per]))
            return out

        point = stat(np.arange(len(te)))
        draws = [stat(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
        for (k, met), v in point.items():
            d = np.array([x[(k, met)] for x in draws])
            lo, hi = float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))
            E.add(f"{model}.{k}.{met}", round(v, 5), "fraction" if "ap" not in met else "AP", notes="mean over seeds 0 to 4; interval is for that mean")
            E.add(f"{model}.{k}.{met}_lo", round(lo, 5), "fraction", "95% bootstrap interval, 1,000 resamples")
            E.add(f"{model}.{k}.{met}_hi", round(hi, 5), "fraction", "95% bootstrap interval, 1,000 resamples")
            rows.append(dict(model=model, set=k, metric=met, value=v, lo=lo, hi=hi))
        for k in ("exact", "near"):
            for met in METS:
                d = np.array([x[("supplied", met)] - x[(k, met)] for x in draws])
                v = point[("supplied", met)] - point[(k, met)]
                lo, hi = float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))
                E.add(f"{model}.diff_supplied_minus_{k}.{met}", round(v, 5), "fraction", notes="paired: same drawn events; positive = the metric is higher with the duplicates in")
                E.add(f"{model}.diff_supplied_minus_{k}.{met}_lo", round(lo, 5), "fraction", "95% bootstrap interval")
                E.add(f"{model}.diff_supplied_minus_{k}.{met}_hi", round(hi, 5), "fraction", "95% bootstrap interval")
                rows.append(dict(model=model, set=f"diff_supplied_minus_{k}", metric=met, value=v, lo=lo, hi=hi))
        print(model, {k: round(point[(k, "sys_recall")], 4) for k in SETS}, flush=True)
    pd.DataFrame(rows).to_csv(OUT / "vz_leakage.csv", index=False)
    E.flush()


if __name__ == "__main__":
    main()
