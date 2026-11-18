"""X8 (docs/02_preregistration/PREREGISTRATION_V3.md): sequential decision with error control against the N19 early-exit rule (VZCrash). MEASURED_SOFTWARE.

The six length-specific 15-tree forests of N19 give p_k at 50, 100, 200, 400, 800 and 1,800 ms. Sequential statistic S_k = sum over checkpoints of (logit p_j - logit pi), pi = validation crash share among
triggered events. Alarm at the earliest checkpoint with S_k >= h_k, no alarm with S_k <= -c, otherwise wait; at 1,800 ms the score of the 1,800 ms forest against t_f decides. (shape of h_k, level h, c, t_f) are
chosen on VALIDATION so that the system false-alarm rate is at most the target (1% or 5% of ALL non-crash events), with the smallest mean decision time of validation crashes among the grid points whose
validation recall is not below that of the early-exit rule (the largest recall if none). Comparators: the early-exit rule (``early.choose_rule``) and the single 1,800 ms forest. Seeds 0 to 4.
Arms of S6: F (single forest), A (the single forest scored on the window truncated at each event's decision time), E (six forests with the rule); E minus F splits into E minus A (ensemble) and A minus F (early exit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import frames_full, threshold_for_fpr
from crashguard.early import ALPHAS, LENGTHS_MS, choose_rule, early_decisions, feature_sets, scatter
from crashguard.jp_common import Entries

SRC = "results/tables/x8_sequential.csv"
SEEDS = C.SEEDS
SHAPES = {"flat": np.ones(5), "rising": np.array([0.6, 0.7, 0.8, 0.9, 1.0]), "falling": np.array([1.0, 0.9, 0.8, 0.7, 0.6])}
H_LEVELS = (2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 24.0)
C_LEVELS = (2.0, 4.0, 8.0, 16.0)
EPS = 1e-3


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def seq_decisions(S: np.ndarray, pi: float, hs: np.ndarray, c: float, t_final: float) -> tuple[np.ndarray, np.ndarray]:
    cum = np.cumsum(logit(S[:, :5]) - logit(np.array(pi)), axis=1)
    n = len(S)
    alarm, t = np.zeros(n, bool), np.full(n, float(LENGTHS_MS[-1]))
    und = np.ones(n, bool)
    for k in range(5):
        up = und & (cum[:, k] >= hs[k])
        down = und & ~up & (cum[:, k] <= -c)
        alarm[up], t[up] = True, LENGTHS_MS[k]
        t[down] = LENGTHS_MS[k]
        und &= ~(up | down)
    alarm[und & (S[:, -1] >= t_final)] = True
    return alarm, t


def choose_seq(Sv: np.ndarray, yv_trig: np.ndarray, n_neg: int, yv_full: np.ndarray, alpha: float, rec_floor: float, n_pos_all: int) -> dict:
    allowed = int(np.floor(alpha * n_neg))
    pi = float(yv_trig.mean())
    pos, neg = yv_trig == 1, yv_trig == 0
    cands = []
    for shape, w in SHAPES.items():
        for h in H_LEVELS:
            for c in C_LEVELS:
                hs = h * w
                early_alarm, early_t = seq_decisions(Sv, pi, hs, c, np.inf)
                a_neg = int((early_alarm & neg).sum())
                if a_neg > allowed:
                    continue
                rest = early_t >= LENGTHS_MS[-1]
                k_allow = allowed - a_neg
                ns = np.sort(Sv[rest & neg, -1])[::-1]
                t_f = float(np.nextafter(ns[k_allow], np.inf)) if k_allow < len(ns) else 0.0
                alarm, tt = seq_decisions(Sv, pi, hs, c, t_f)
                if int((alarm & neg).sum()) > allowed:
                    continue
                rec = float((alarm & pos).sum()) / n_pos_all
                cands.append(dict(shape=shape, h=h, c=c, hs=hs, t_f=t_f, val_recall=rec, val_mean_t=float(tt[pos].mean()), pi=pi))
    ok = [x for x in cands if x["val_recall"] >= rec_floor - 1e-12]
    if ok:
        return min(ok, key=lambda x: (round(x["val_mean_t"], 6), -x["val_recall"]))
    return max(cands, key=lambda x: (round(x["val_recall"], 9), -x["val_mean_t"])) if cands else dict(shape="none", h=np.inf, c=np.inf, hs=np.full(5, np.inf), t_f=0.0, val_recall=0.0, val_mean_t=float(LENGTHS_MS[-1]), pi=pi)


def main() -> None:
    tr, va, te = frames_full()
    d_tr, F_tr = feature_sets("train")
    d_va, F_va = feature_sets("validation")
    d_te, F_te = feature_sets("test", dedup=True)
    yv_full, yt_full = va.y.to_numpy(), te.y.to_numpy()
    n_neg_v, n_pos_v = int((yv_full == 0).sum()), int((yv_full == 1).sum())
    flags = pd.read_csv(C.TABLES / "vz_audit_test_near_dup_flags.csv")
    near = set(flags.event_id[flags.flagged_near_duplicate])
    sets = {"dedup": np.ones(len(te), bool), "strict": ~te.event_id.isin(near).to_numpy()}
    pos_te = scatter(te, d_te["event_id"], d_te["y"].astype(float)) > 0.5
    trig_te = te.triggered.to_numpy(bool)
    R: dict = {a: {k: [] for k in ("E_alarm", "E_t", "Q_alarm", "Q_t", "F_alarm", "A_alarm_E", "A_alarm_Q")} for a in ALPHAS}
    info = []
    for seed in SEEDS:
        models = []
        for m in LENGTHS_MS:
            rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
            rf.fit(F_tr[m].to_numpy(np.float32), d_tr["y"])
            rf.set_params(n_jobs=1)
            models.append(rf)
        Sv = np.stack([models[i].predict_proba(F_va[m].to_numpy(np.float32))[:, 1] for i, m in enumerate(LENGTHS_MS)], axis=1)
        St = np.stack([models[i].predict_proba(F_te[m].to_numpy(np.float32))[:, 1] for i, m in enumerate(LENGTHS_MS)], axis=1)
        SvA = np.stack([models[-1].predict_proba(F_va[m].to_numpy(np.float32))[:, 1] for m in LENGTHS_MS], axis=1)  # single forest on truncated windows
        StA = np.stack([models[-1].predict_proba(F_te[m].to_numpy(np.float32))[:, 1] for m in LENGTHS_MS], axis=1)
        full_v = [scatter(va, d_va["event_id"], Sv[:, k]) for k in range(6)]
        for alpha in ALPHAS:
            rule = choose_rule(Sv, d_va["y"], n_neg_v, n_pos_v, full_v, yv_full, alpha)
            seq = choose_seq(Sv, d_va["y"], n_neg_v, yv_full, alpha, rule["val_recall"], n_pos_v)
            a_e, t_e = early_decisions(St, rule["hi"], rule["lo"], rule["t_f"])
            a_q, t_q = seq_decisions(St, seq["pi"], seq["hs"], seq["c"], seq["t_f"])
            # arm F
            thr_f = threshold_for_fpr(yv_full, full_v[-1], alpha)
            a_f = scatter(te, d_te["event_id"], St[:, -1]) >= thr_f
            # arm A for each rule: single forest scored at each event's own decision time; threshold from validation with the same truncation
            out = {}
            for nm, tt_ in (("E", t_e), ("Q", t_q)):
                if nm == "E":
                    _a_v, tv = early_decisions(Sv, rule["hi"], rule["lo"], rule["t_f"])
                else:
                    _a_v, tv = seq_decisions(Sv, seq["pi"], seq["hs"], seq["c"], seq["t_f"])
                kv = np.array([LENGTHS_MS.index(int(x)) for x in tv])
                kt = np.array([LENGTHS_MS.index(int(x)) for x in tt_])
                sv_a = scatter(va, d_va["event_id"], SvA[np.arange(len(kv)), kv])
                st_a = scatter(te, d_te["event_id"], StA[np.arange(len(kt)), kt])
                out[nm] = st_a >= threshold_for_fpr(yv_full, sv_a, alpha)
            R[alpha]["E_alarm"].append(scatter(te, d_te["event_id"], a_e.astype(float)) > 0.5)
            R[alpha]["Q_alarm"].append(scatter(te, d_te["event_id"], a_q.astype(float)) > 0.5)
            R[alpha]["E_t"].append(scatter(te, d_te["event_id"], t_e))
            R[alpha]["Q_t"].append(scatter(te, d_te["event_id"], t_q))
            R[alpha]["F_alarm"].append(a_f)
            R[alpha]["A_alarm_E"].append(out["E"])
            R[alpha]["A_alarm_Q"].append(out["Q"])
            info.append(dict(seed=seed, alpha=alpha, shape=seq["shape"], h=seq["h"], c=seq["c"], val_recall_seq=seq["val_recall"], val_recall_early=rule["val_recall"], val_t_seq=seq["val_mean_t"], val_t_early=rule["val_mean_t"]))
        print("seed", seed, flush=True)
    E = Entries("x.x8", SRC)
    pd.DataFrame(info).to_csv(C.TABLES / "x8_sequential_choices.csv", index=False)
    for r in info:
        E.add(f"choice.a{int(round(r['alpha'] * 100))}.seed{r['seed']}.shape", r["shape"], "text", "chosen on validation")
        E.add(f"choice.a{int(round(r['alpha'] * 100))}.seed{r['seed']}.h", float(r["h"]), "log-odds")
        E.add(f"choice.a{int(round(r['alpha'] * 100))}.seed{r['seed']}.c", float(r["c"]), "log-odds")
    rows = []
    DR: dict = {}
    for alpha in ALPHAS:
        tag = f"a{int(round(alpha * 100))}"
        for sname, mask in sets.items():
            def st_(idx: np.ndarray, alpha=alpha, mask=mask) -> dict:
                sel = idx[mask[idx]]
                pos = pos_te[sel]
                posn = yt_full[sel] == 1
                tp = pos & trig_te[sel]
                out = {}
                for arm in ("E", "Q"):
                    out[f"{arm}_recall"] = float(np.mean([a[sel][posn].mean() for a in R[alpha][f"{arm}_alarm"]]))
                    out[f"{arm}_fa"] = float(np.mean([a[sel][yt_full[sel] == 0].mean() for a in R[alpha][f"{arm}_alarm"]]))
                    out[f"{arm}_mediant"] = float(np.mean([np.median(t[sel][tp]) for t in R[alpha][f"{arm}_t"]]))
                    out[f"{arm}_meant"] = float(np.mean([np.mean(t[sel][tp]) for t in R[alpha][f"{arm}_t"]]))
                    out[f"A{arm}_recall"] = float(np.mean([a[sel][posn].mean() for a in R[alpha][f"A_alarm_{arm}"]]))
                out["F_recall"] = float(np.mean([a[sel][posn].mean() for a in R[alpha]["F_alarm"]]))
                out["F_fa"] = float(np.mean([a[sel][yt_full[sel] == 0].mean() for a in R[alpha]["F_alarm"]]))
                return out
            point = st_(np.arange(len(te)))
            dr = [st_(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
            for k, v in point.items():
                d = np.array([x[k] for x in dr])
                E.ci(f"{tag}.{sname}.{k}", (v, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "ms" if k.endswith(("mediant", "meant")) else "fraction", d=5)
            diffs = {"time_early_minus_seq_median": ("E_mediant", "Q_mediant", +1), "recall_seq_minus_early": ("Q_recall", "E_recall", +1), "seq_recall_minus_F": ("Q_recall", "F_recall", +1), "early_recall_minus_F": ("E_recall", "F_recall", +1),
                     "seq_minus_A_seq": ("Q_recall", "AQ_recall", +1), "A_seq_minus_F": ("AQ_recall", "F_recall", +1), "early_minus_A_early": ("E_recall", "AE_recall", +1), "A_early_minus_F": ("AE_recall", "F_recall", +1)}
            for nm, (a_, b_, _s) in diffs.items():
                d = np.array([x[a_] - x[b_] for x in dr])
                pt = point[a_] - point[b_]
                lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
                E.ci(f"{tag}.{sname}.diff.{nm}", (pt, lo, hi), "ms" if nm.startswith("time") else "fraction", "positive = the minuend is larger", d=5)
                rows.append(dict(alpha=alpha, set=sname, diff=nm, value=pt, lo=lo, hi=hi))
                DR[(alpha, sname, nm)] = d
    # H-X8: primary at both targets on the de-duplicated set; the criterion must hold at both
    ok_all, ps = [], []
    for alpha in ALPHAS:
        tag = f"a{int(round(alpha * 100))}"
        dt = [r for r in rows if r["alpha"] == alpha and r["set"] == "dedup" and r["diff"] == "time_early_minus_seq_median"][0]
        dr_ = [r for r in rows if r["alpha"] == alpha and r["set"] == "dedup" and r["diff"] == "recall_seq_minus_early"][0]
        ok = dt["value"] >= 100.0 and dt["lo"] > 0 and not (dr_["hi"] < 0)
        ok_all.append(ok)
        ps.append(dt)
        E.add(f"hX8.{tag}.time_gain_ms", round(dt["value"], 3), "ms", "median decision time of the early-exit rule minus that of the sequential rule, de-duplicated set")
        E.add(f"hX8.{tag}.time_gain_lo", round(dt["lo"], 3), "ms")
        E.add(f"hX8.{tag}.time_gain_hi", round(dt["hi"], 3), "ms")
        E.add(f"hX8.{tag}.recall_diff", round(dr_["value"], 5), "fraction", "sequential minus early-exit recall")
        E.add(f"hX8.{tag}.recall_diff_hi", round(dr_["hi"], 5), "fraction")
        E.add(f"hX8.{tag}.criterion_met", int(ok), "flag")
    p_raw = max(float(max(np.mean(DR[(a, "dedup", "time_early_minus_seq_median")] <= 0.0), 1.0 / (B.N_BOOT + 1))) for a in ALPHAS)
    E.add("hX8.p_raw", round(p_raw, 4), "probability", "the larger of the two targets' shares of resamples with a median time gain at or below 0; floor 0.001")
    E.add("hX8.criterion_met", int(all(ok_all)), "flag", "both targets")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "x8_sequential.csv", index=False)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rows).round(4).to_string())
    print(pd.DataFrame(info).to_string())


if __name__ == "__main__":
    main()
