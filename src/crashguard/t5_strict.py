"""T5: headline results on the standard test set (de-duplicated by the exact-hash and nearest-neighbour rules; primary) and on the set without window-level near-duplicates (SENSITIVITY ANALYSIS, EXPLORATORY).

Matching rule (also in docs/07_log/DECISIONS.md): a triggered test event is a near-duplicate if one train or validation window (trigger-aligned, 2.8 s, trigger level 2 g, per-axis mean removed, axes concatenated) has
correlation above 0.999 AND maximum absolute difference below 0.01 g with it. The flagged ids come from ``dupscan`` (results/tables/s2_neardup_test.csv). The same ids are removed for every trigger level
(the window cache has the 2 g variant only). Thresholds and rules are chosen on the validation split exactly as in the primary analysis; only the evaluated test events differ.
Reported: AP, recall at the 1% and 5% false-alarm targets, the N19 early-exit gain, and the N9 trigger results. MEASURED_SOFTWARE.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import s6_early as S6
from crashguard.detector_extra import fit, frames_full, score_all, threshold_for_fpr
from crashguard.models import fit_scorer, frames, op_thresholds
from crashguard.s2_dedup import fast_ap
from crashguard.split import leaky_test_ids

SRC = "results/tables/t5_strict.csv"
SEEDS = C.SEEDS
TRIG_VARIANTS = ("trig_1.5", "trig_2", "trig_2.5", "trig_3")


def strict_ids() -> set[int]:
    nd = pd.read_csv(C.TABLES / "s2_neardup_test.csv")
    return set(nd.event_id[nd.both & ~nd.leaky])


def main() -> None:
    from crashguard.results import record_many

    drop = strict_ids()
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"t5.{name}", value=value, unit=unit, origin="MEASURED_SOFTWARE", source_file=SRC, notes=notes))

    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    sets = {"std": np.ones(len(te), bool), "strict": ~te.event_id.isin(drop).to_numpy()}
    add("n_events.std", int(sets["std"].sum()), "events", "standard test set: de-duplicated by the exact-hash and nearest-neighbour rules (primary)")
    add("n_events.strict", int(sets["strict"].sum()), "events", "SENSITIVITY: also without window-level near-duplicates")
    add("n_crash.std", int(te.y[sets["std"]].sum()), "events", "crash events")
    add("n_crash.strict", int(te.y[sets["strict"]].sum()), "events", "crash events")
    # ---- AP, recall at the 1% and 5% targets, with 5-seed means and bootstrap intervals (paired over events: both sets from the same drawn events of the standard set)
    y = te.y.to_numpy()
    trig = te.triggered.to_numpy(bool)
    scores, thr = {}, {}
    for seed in SEEDS:
        scorer, _ = fit("rf15", seed, tr, va_trig)
        s = score_all(scorer, te)
        scores[seed] = s
        thr[seed] = {"f1": op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))[0], "t1": threshold_for_fpr(va.y.to_numpy(), score_all(scorer, va), 0.01), "t5": threshold_for_fpr(va.y.to_numpy(), score_all(scorer, va), 0.05)}

    def stat(idx: np.ndarray, which: str) -> dict:
        sel = idx[sets[which][idx]]
        out = {}
        for key in ("f1", "t1", "t5"):
            rec = np.mean([(scores[s][sel][y[sel] == 1] >= thr[s][key]).mean() for s in SEEDS])
            fa = np.mean([(scores[s][sel][y[sel] == 0] >= thr[s][key]).mean() for s in SEEDS])
            out[f"recall_{key}"], out[f"fa_{key}"] = float(rec), float(fa)
        out["ap_model"] = float(np.mean([fast_ap(y[sel][trig[sel]], scores[s][sel][trig[sel]]) for s in SEEDS]))
        out["ap_system"] = float(np.mean([fast_ap(y[sel], scores[s][sel]) for s in SEEDS]))
        return out

    full = np.arange(len(te))
    point = {k: stat(full, k) for k in ("std", "strict")}
    draws = [(stat(i, "std"), stat(i, "strict")) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
    for k in ("std", "strict"):
        for met, v in point[k].items():
            d = np.array([x[0 if k == "std" else 1][met] for x in draws])
            add(f"{k}.{met}", round(v, 5), "fraction" if "ap" not in met else "AP", "mean over seeds 0 to 4 of the validation-chosen operating point (f1 = validation F1 maximum, t1 and t5 = 1% and 5% false-alarm targets); 95% bootstrap interval over test events")
            add(f"{k}.{met}_lo", round(float(np.quantile(d, 0.025)), 5), "fraction", "95% bootstrap interval")
            add(f"{k}.{met}_hi", round(float(np.quantile(d, 0.975)), 5), "fraction", "95% bootstrap interval")
    for met in point["std"]:
        d = np.array([x[0][met] - x[1][met] for x in draws])
        add(f"diff_std_minus_strict.{met}", round(point["std"][met] - point["strict"][met], 5), "fraction", "standard minus strict, paired over the same drawn events")
        add(f"diff_std_minus_strict.{met}_lo", round(float(np.quantile(d, 0.025)), 5), "fraction", "95% bootstrap interval")
        add(f"diff_std_minus_strict.{met}_hi", round(float(np.quantile(d, 0.975)), 5), "fraction", "95% bootstrap interval")
    # ---- N19: early exit and ensemble effect on both sets (arms F and E, 5-seed means)
    d_tr, F_tr = S6.feature_sets("train")
    d_va, F_va = S6.feature_sets("validation")
    d_te, F_te = S6.feature_sets("test", dedup=True)
    for which in ("std", "strict"):
        keep_te = sets[which]
        te_w = te[keep_te].reset_index(drop=True)
        ids = set(te_w.event_id)
        m = np.array([e in ids for e in d_te["event_id"]])
        d_te_w = {k: (v[m] if hasattr(v, "__len__") and len(v) == len(m) else v) for k, v in d_te.items()}
        F_te_w = {ms: f[m].reset_index(drop=True) for ms, f in F_te.items()}
        for alpha, an in ((0.01, "a1"), (0.05, "a5")):
            res = {s: S6.arms_for_seed(s, alpha, F_tr, d_tr["y"], va, te_w, d_va, d_te_w, F_va, F_te_w) for s in SEEDS}
            yt = te_w.y.to_numpy()
            pos_trig = np.isin(te_w.event_id.to_numpy(), d_te_w["event_id"][d_te_w["y"] == 1])
            arrF = np.stack([res[s]["F"] for s in SEEDS], 1)
            arrE = np.stack([res[s]["E"] for s in SEEDS], 1)
            tt = np.stack([res[s]["t_early"] for s in SEEDS], 1)

            def st(i, arrF=arrF, arrE=arrE, tt=tt, yt=yt, pos_trig=pos_trig):
                rF = float(arrF[i][yt[i] == 1].mean())
                rE = float(arrE[i][yt[i] == 1].mean())
                return rE - rF, float(np.nanmean(tt[i][pos_trig[i]])) - 1800.0, rF, rE

            point_ = st(np.arange(len(te_w)))
            dr = np.array([st(i) for i in B._idx(len(te_w), B.N_BOOT, B.SEED)])
            for j, nm in enumerate(("recall_gain_ensemble", "time_diff_ms", "recall_single", "recall_early")):
                add(f"n19.{which}.{an}.{nm}", round(point_[j], 5), "ms" if "time" in nm else "fraction", "mean of seeds 0 to 4; E (six forests, early exit) minus F (single 1,800 ms forest); 95% bootstrap interval over test events")
                add(f"n19.{which}.{an}.{nm}_lo", round(float(np.quantile(dr[:, j], 0.025)), 5), "ms" if "time" in nm else "fraction", "95% bootstrap interval")
                add(f"n19.{which}.{an}.{nm}_hi", round(float(np.quantile(dr[:, j], 0.975)), 5), "ms" if "time" in nm else "fraction", "95% bootstrap interval")
    # ---- N9: trigger rate, model-level and system recall at the validation F1 threshold, by trigger level
    for var in TRIG_VARIANTS:
        trv, vav, tev = frames(var)
        tev = tev.copy()
        for which, keep in (("std", ~tev.event_id.isin(leaky_test_ids()).to_numpy()), ("strict", (~tev.event_id.isin(leaky_test_ids()) & ~tev.event_id.isin(drop)).to_numpy())):
            sub = tev[keep]
            crash = sub[sub.y == 1]
            add(f"n9.{var}.{which}.crash_trigger_rate", round(float(crash.triggered.mean()), 4), "fraction", "share of crash events that pass the trigger")
            recs_m, recs_s = [], []
            for seed in SEEDS:
                scorer, _m = fit_scorer("rf15", seed, list(C.FEATURES), trv, vav)
                thr_ = op_thresholds(vav.y.to_numpy(), scorer(vav))[0]
                tg = sub[sub.triggered.to_numpy(bool)]
                recs_m.append(float((scorer(tg)[tg.y.to_numpy() == 1] >= thr_).mean()))
                sc = np.full(len(sub), -1.0)
                tm = sub.triggered.to_numpy(bool)
                sc[tm] = scorer(sub[tm])
                recs_s.append(float((sc[sub.y.to_numpy() == 1] >= thr_).mean()))
            add(f"n9.{var}.{which}.model_level_recall", round(float(np.mean(recs_m)), 4), "fraction", "triggered crash events only; mean of seeds 0 to 4")
            add(f"n9.{var}.{which}.system_recall", round(float(np.mean(recs_s)), 4), "fraction", "all crash events (an untriggered event is a miss); mean of seeds 0 to 4")
    record_many(ent, purge_prefixes=("t5.",))
    g = {e["name"]: e["value"] for e in ent}
    for k in ("std", "strict"):
        print(k, {m: g[f"t5.{k}.{m}"] for m in ("recall_f1", "recall_t1", "recall_t5", "ap_model", "ap_system")})
    for which in ("std", "strict"):
        print(which, "N19 a1", g[f"t5.n19.{which}.a1.recall_gain_ensemble"], g[f"t5.n19.{which}.a1.time_diff_ms"], "a5", g[f"t5.n19.{which}.a5.recall_gain_ensemble"])
    print({k: v for k, v in g.items() if k.startswith("t5.n9.trig_2.")})


if __name__ == "__main__":
    main()
