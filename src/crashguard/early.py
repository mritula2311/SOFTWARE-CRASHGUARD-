"""X3 (N19): early classification (docs/02_preregistration/EXPERIMENTS_EXTRA.md, written before this was run).

The deployed forest (15 trees, depth 6) is trained at post-trigger lengths of 50, 100, 200, 400, 800 and 1,800 ms (the pre-trigger length stays 1.0 s). A sequential early-exit rule
decides at the first checkpoint where the length-specific model is very confident: alarm if the score is at or above hi_k, no alarm if it is below lo_k, otherwise wait; at 1,800 ms
the threshold t_f decides. hi_k, lo_k and t_f are chosen on the validation split only. System level: events the trigger discards count as non-alarms.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard import windows_cache as W
from crashguard.detector_extra import frames_full, threshold_for_fpr

LENGTHS_MS = (50, 100, 200, 400, 800, 1800)
POST_N = tuple(round(m * C.FS_HZ / 1000) for m in LENGTHS_MS)
ALPHAS = (0.01, 0.05)
A_HI = (0.001, 0.0025, 0.005, 0.01)  # early alarm only if the length-specific model alone would have this false-alarm rate or lower on validation
B_LO = (0.0, 0.001, 0.005, 0.01)  # early no-alarm only if the score is below this quantile of the validation crash scores (0 = below every validation crash)
SEEDS = (C.SEED,) + C.SEEDS


def feature_sets(split: str, dedup: bool = True) -> tuple[dict, dict[int, pd.DataFrame]]:
    d = W.load(split, dedup=dedup)
    return d, {m: W.features_of(d["acc"], d["gyro"], n) for m, n in zip(LENGTHS_MS, POST_N)}


def scatter(full: pd.DataFrame, ids: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """Full-length score vector for ALL events of ``full`` (-1 where the trigger did not pass), from scores of the triggered events with these ids."""
    pos = pd.Series(np.arange(len(full)), index=full.event_id.to_numpy())
    out = np.full(len(full), -1.0)
    out[pos.loc[ids].to_numpy()] = scores
    return out


def early_decisions(S: np.ndarray, hi: np.ndarray, lo: np.ndarray, t_final: float) -> tuple[np.ndarray, np.ndarray]:
    """Alarm flag and decision time (ms) of every triggered event. ``S`` (n, 6) scores at the six checkpoints; hi, lo are length-5 arrays for the first five checkpoints."""
    n = len(S)
    alarm, t = np.zeros(n, bool), np.full(n, float(LENGTHS_MS[-1]))
    undecided = np.ones(n, bool)
    for k in range(len(LENGTHS_MS) - 1):
        up = undecided & (S[:, k] >= hi[k])
        down = undecided & ~up & (S[:, k] < lo[k])
        alarm[up], t[up] = True, LENGTHS_MS[k]
        t[down] = LENGTHS_MS[k]
        undecided &= ~(up | down)
    final = undecided & (S[:, -1] >= t_final)
    alarm[final] = True
    return alarm, t


def choose_rule(Sv: np.ndarray, yv_trig: np.ndarray, n_neg_all: int, n_pos_all: int, models_val_full: list[np.ndarray], yv_full: np.ndarray, alpha: float) -> dict:
    """Grid search on VALIDATION: the (a_hi, b_lo) with the highest validation system recall subject to validation system false-alarm rate <= alpha; ties go to the lower mean
    validation decision time of the crash events. t_f is the smallest final threshold that keeps the total false-alarm rate within alpha. Returns the rule and the plain 1,800 ms threshold."""
    allowed = int(np.floor(alpha * n_neg_all))
    t_plain = threshold_for_fpr(yv_full, models_val_full[-1], alpha)
    best = None
    pos, neg = yv_trig == 1, yv_trig == 0
    options = [(None, None)] + [(a, b) for a in A_HI for b in B_LO]
    for a_hi, b_lo in options:
        if a_hi is None:  # no early exit
            hi, lo = np.full(5, np.inf), np.full(5, -np.inf)
        else:
            hi = np.array([threshold_for_fpr(yv_full, models_val_full[k], a_hi) for k in range(5)])
            lo = np.array([np.quantile(Sv[pos, k], b_lo) if b_lo > 0 else Sv[pos, k].min() for k in range(5)])
        early_alarm, early_t = early_decisions(Sv, hi, lo, np.inf)  # final threshold +inf: only early alarms
        decided_early = early_t < LENGTHS_MS[-1]
        a_neg = int((early_alarm & neg).sum())
        if a_neg > allowed:
            continue
        rest = ~decided_early
        k_allow = allowed - a_neg
        neg_sorted = np.sort(Sv[rest & neg, -1])[::-1]
        t_f = float(np.nextafter(neg_sorted[k_allow], np.inf)) if k_allow < len(neg_sorted) else 0.0  # 0.0 = every remaining triggered event alarms (as in threshold_for_fpr)
        alarm, tt = early_decisions(Sv, hi, lo, t_f)
        fa = int((alarm & neg).sum())
        if fa > allowed:
            continue
        rec = float((alarm & pos).sum()) / n_pos_all
        mean_t = float(tt[pos].mean())
        key = (round(rec, 9), -mean_t)
        if best is None or key > best["key"]:
            best = dict(key=key, a_hi=a_hi, b_lo=b_lo, hi=hi, lo=lo, t_f=t_f, val_recall=rec, val_fa=fa / n_neg_all, val_mean_t=mean_t)
    best["t_plain"] = t_plain
    return best


def mcu_cost() -> dict:
    """ANALYTICAL: operations per sample of the incremental feature updates (a reading of ``features.compute_features``), state bytes, and the forest evaluation at each checkpoint."""
    ops = {  # per sample: multiplies, adds, compares, square roots
        "magnitude |a|": (3, 2, 0, 1), "peak |a| and per-axis peaks": (0, 0, 4, 0), "horizontal magnitude and peak": (2, 1, 1, 1), "deviation, energy and rms sums": (1, 2, 0, 0),
        "jerk (difference of |a|)": (0, 1, 2, 0), "time above 2 g": (0, 1, 1, 0), "moment sums for kurtosis (powers 1 to 4)": (3, 4, 0, 0),
        "last 80 samples running sums (quiet ratio)": (2, 4, 0, 0), "gyro magnitude and peak": (3, 2, 1, 1),
    }
    mul = sum(v[0] for v in ops.values())
    add = sum(v[1] for v in ops.values())
    cmp_ = sum(v[2] for v in ops.values())
    sq = sum(v[3] for v in ops.values())
    cyc = mul * 2 + add * 2 + cmp_ * 2 + sq * 30  # ASSUMPTION: cycles per operation on an ESP32 with a single-precision FPU (not measured)
    state_floats = 4 + 1 + 1 + 1 + 1 + 4 + 80 + 2 + 1 + 1
    return dict(mul=mul, add=add, cmp=cmp_, sqrt=sq, cycles_per_sample_assumed=cyc, state_bytes=state_floats * 4, forest_compares_per_checkpoint=15 * 6, checkpoints=len(LENGTHS_MS),
                share_of_sample_period=cyc / (240e6 * C.DT))


def main() -> None:
    from crashguard.results import record_many

    tr, va, te = frames_full()
    d_tr, F_tr = feature_sets("train")
    d_va, F_va = feature_sets("validation")
    d_te, F_te = feature_sets("test", dedup=True)
    assert set(d_va["event_id"]) == set(va[va.triggered].event_id), "cache and feature table disagree on triggered validation events"
    assert set(d_te["event_id"]) == set(te[te.triggered].event_id), "cache and feature table disagree on triggered test events"
    yv_full, yt_full = va.y.to_numpy(), te.y.to_numpy()
    n_neg_v, n_pos_v = int((yv_full == 0).sum()), int((yv_full == 1).sum())
    _n_neg_t, _n_pos_t = int((yt_full == 0).sum()), int((yt_full == 1).sum())
    ent: list[dict] = []
    src = "results/tables/x3_early.csv"

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes=""):
        ent.append(dict(name=f"x3.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    ytr = d_tr["y"]
    rows, per_seed = [], {}
    for seed in SEEDS:
        models = []
        for m in LENGTHS_MS:
            rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
            rf.fit(F_tr[m].to_numpy(np.float32), ytr)
            rf.set_params(n_jobs=1)
            models.append(rf)
        Sv = np.stack([models[i].predict_proba(F_va[m].to_numpy(np.float32))[:, 1] for i, m in enumerate(LENGTHS_MS)], axis=1)
        St = np.stack([models[i].predict_proba(F_te[m].to_numpy(np.float32))[:, 1] for i, m in enumerate(LENGTHS_MS)], axis=1)
        full_v = [scatter(va, d_va["event_id"], Sv[:, k]) for k in range(len(LENGTHS_MS))]
        full_t = [scatter(te, d_te["event_id"], St[:, k]) for k in range(len(LENGTHS_MS))]
        yv_trig, yt_trig = d_va["y"], d_te["y"]
        for alpha in ALPHAS:
            # fixed windows
            for k, m in enumerate(LENGTHS_MS):
                thr = threshold_for_fpr(yv_full, full_v[k], alpha)
                alarm = full_t[k] >= thr
                rows.append(dict(seed=seed, alpha=alpha, method=f"fixed_{m}", recall=float(alarm[yt_full == 1].mean()), fa=float(alarm[yt_full == 0].mean()), time_ms=float(m), time_p95_ms=float(m)))
            rule = choose_rule(Sv, yv_trig, n_neg_v, n_pos_v, full_v, yv_full, alpha)
            alarm_t, tt = early_decisions(St, rule["hi"], rule["lo"], rule["t_f"])
            full_alarm = scatter(te, d_te["event_id"], alarm_t.astype(float)) > 0.5
            pos_trig = yt_trig == 1
            rows.append(dict(seed=seed, alpha=alpha, method="early_exit", recall=float(full_alarm[yt_full == 1].mean()), fa=float(full_alarm[yt_full == 0].mean()),
                             time_ms=float(tt[pos_trig].mean()), time_p95_ms=float(np.quantile(tt[pos_trig], 0.95)), a_hi=rule["a_hi"] if rule["a_hi"] is not None else -1, b_lo=rule["b_lo"] if rule["b_lo"] is not None else -1,
                             alarmed_time_ms=float(tt[pos_trig & alarm_t].mean()) if (pos_trig & alarm_t).any() else float("nan"),
                             alarmed_time_p95_ms=float(np.quantile(tt[pos_trig & alarm_t], 0.95)) if (pos_trig & alarm_t).any() else float("nan")))
            if seed == C.SEED:
                per_seed[alpha] = dict(alarm_early=full_alarm, time_early=tt, trig_pos=pos_trig, alarm_fixed=full_t[-1] >= threshold_for_fpr(yv_full, full_v[-1], alpha), rule=rule)
    R = pd.DataFrame(rows)
    R.to_csv(C.TABLES / "x3_early.csv", index=False)
    add("n_test_events", len(te), "events")
    add("n_test_triggered", int(te.triggered.sum()), "events")
    for (alpha, meth), g in R.groupby(["alpha", "method"]):
        tag = f"a{int(round(alpha * 100))}.{meth}"
        g5 = g[g.seed.isin(C.SEEDS)]
        for col in ("recall", "fa", "time_ms", "time_p95_ms", "alarmed_time_ms", "alarmed_time_p95_ms"):
            if col not in g or g[col].isna().all():
                continue
            add(f"{tag}.{col}.mean", round(float(g5[col].mean()), 5), "fraction" if col in ("recall", "fa") else "ms", notes="mean over seeds 0-4")
            add(f"{tag}.{col}.std", round(float(g5[col].std(ddof=1)), 5), "fraction" if col in ("recall", "fa") else "ms")
            add(f"{tag}.{col}.seed42", round(float(g[g.seed == C.SEED][col].iloc[0]), 5), "fraction" if col in ("recall", "fa") else "ms")
    # paired bootstrap, seed 42, early exit against the fixed 1,800 ms window
    for alpha, p in per_seed.items():
        tag = f"a{int(round(alpha * 100))}.paired"
        arr = np.stack([yt_full, p["alarm_early"].astype(int), p["alarm_fixed"].astype(int)], 1)
        draws_idx = list(B._idx(len(arr), B.N_BOOT, B.SEED))

        def rec(a, col):
            return float(a[a[:, 0] == 1, col].mean())

        dr = np.array([rec(arr[i], 1) - rec(arr[i], 2) for i in draws_idx])
        add(f"{tag}.recall_diff", round(rec(arr, 1) - rec(arr, 2), 5), "fraction", notes="early exit minus fixed 1,800 ms, seed 42, paired bootstrap of test events")
        add(f"{tag}.recall_diff_lo", round(float(np.quantile(dr, 0.025)), 5), "fraction")
        add(f"{tag}.recall_diff_hi", round(float(np.quantile(dr, 0.975)), 5), "fraction")
        tp = p["time_early"][p["trig_pos"]]
        d = B.ci(tp - LENGTHS_MS[-1], np.mean)
        add(f"{tag}.time_diff_ms", round(d[0], 2), "ms", notes="mean decision time of triggered crash events minus 1,800 ms")
        add(f"{tag}.time_diff_ms_lo", round(d[1], 2), "ms")
        add(f"{tag}.time_diff_ms_hi", round(d[2], 2), "ms")
        add(f"{tag}.rule_a_hi", p["rule"]["a_hi"] if p["rule"]["a_hi"] is not None else -1, "fraction", notes="-1 = no early exit chosen")
        add(f"{tag}.rule_b_lo", p["rule"]["b_lo"] if p["rule"]["b_lo"] is not None else -1, "fraction")
        add(f"{tag}.val_recall", round(p["rule"]["val_recall"], 5), "fraction", notes="validation split, used to choose the rule")
        add(f"{tag}.val_mean_time_ms", round(p["rule"]["val_mean_t"], 2), "ms")
    cost = mcu_cost()
    for k, v in cost.items():
        add(f"mcu.{k}", round(float(v), 8) if isinstance(v, float) else int(v), "ops" if k in ("mul", "add", "cmp", "sqrt") else "value", origin="ANALYTICAL", notes="reading of the feature definitions; cycles per operation are an unverified assumption (2 for mul, add and compare, 30 for sqrt)")
    # end-to-end timing (SIMULATED): the alert is ready earlier by the post-trigger time that is no longer needed
    for alpha in per_seed:
        g = R[(R.alpha == alpha) & (R.method == "early_exit") & (R.seed == C.SEED)].iloc[0]
        add(f"timing.a{int(round(alpha * 100))}.mean_time_before_cancel_window_s.fixed", round(C.POST_S + 0.05, 3), "s", origin="SIMULATED", notes="post-trigger window plus the assumed 0.05 s compute time (replay.COMPUTE_S); the cancel window starts after this")
        add(f"timing.a{int(round(alpha * 100))}.mean_time_before_cancel_window_s.early", round(g.alarmed_time_ms / 1000.0 + 0.05, 3), "s", origin="SIMULATED", notes="mean decision time of the crash events that raise an alarm (seed 42) plus the same compute time; unconfirmed by hardware")
    record_many(ent, purge_prefixes=("x3.",))
    pd.set_option("display.width", 200)
    print(R.groupby(["alpha", "method"])[["recall", "fa", "time_ms", "time_p95_ms"]].mean().round(4).to_string())


if __name__ == "__main__":
    main()
