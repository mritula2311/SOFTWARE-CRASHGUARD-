"""S6: N19, separate the ensemble effect from the early exit (arms and wording rule: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S6, written before this was run).

Arms at the same false-alarm target (1% and 5%), thresholds and rules chosen on validation only, test = the de-duplicated test split, seeds 42 and 0 to 4:
  F   single 1,800 ms forest, decision at 1,800 ms
  A   the same single forest scored on the window truncated at each event's early-exit time (isolates the early exit); threshold from validation with the same truncation
  E   six length-specific forests with the sequential early-exit rule
  E'  the same six forests and rule, every decision released at 1,800 ms (isolates the ensemble); its alarms equal those of E by construction
Time is the mean decision time (ms) of the triggered crash events. SIMULATED timing only in the sense that the decision time is read from the window length; no ESP32 timing.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import frames_full, threshold_for_fpr
from crashguard.early import ALPHAS, LENGTHS_MS, choose_rule, early_decisions, feature_sets, scatter

SEEDS = (C.SEED,) + C.SEEDS
ARMS = ("F", "A", "E", "Ep")
SRC = "results/tables/s6_early.csv"


def truncated_scores(model, feats: dict, times: np.ndarray) -> np.ndarray:
    """Scores of ``model`` on the feature rows of each event at its own decision time ``times`` (ms, one of LENGTHS_MS)."""
    s = np.zeros(len(times))
    for m in LENGTHS_MS:
        mask = times == m
        if mask.any():
            s[mask] = model.predict_proba(feats[m].to_numpy(np.float32)[mask])[:, 1]
    return s


def arms_for_seed(seed: int, alpha: float, tr_feats, ytr, va, te, d_va, d_te, F_va, F_te) -> dict:
    models = []
    for m in LENGTHS_MS:
        rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
        rf.fit(tr_feats[m].to_numpy(np.float32), ytr)
        rf.set_params(n_jobs=1)
        models.append(rf)
    Sv = np.stack([models[i].predict_proba(F_va[m].to_numpy(np.float32))[:, 1] for i, m in enumerate(LENGTHS_MS)], axis=1)
    St = np.stack([models[i].predict_proba(F_te[m].to_numpy(np.float32))[:, 1] for i, m in enumerate(LENGTHS_MS)], axis=1)
    yv_full, _yt_full = va.y.to_numpy(), te.y.to_numpy()
    n_neg_v, n_pos_v = int((yv_full == 0).sum()), int((yv_full == 1).sum())
    full_v = [scatter(va, d_va["event_id"], Sv[:, k]) for k in range(len(LENGTHS_MS))]
    full_t = [scatter(te, d_te["event_id"], St[:, k]) for k in range(len(LENGTHS_MS))]
    rule = choose_rule(Sv, d_va["y"], n_neg_v, n_pos_v, full_v, yv_full, alpha)
    alarm_v, tv = early_decisions(Sv, rule["hi"], rule["lo"], rule["t_f"])
    alarm_t, tt = early_decisions(St, rule["hi"], rule["lo"], rule["t_f"])
    # F
    thr_f = threshold_for_fpr(yv_full, full_v[-1], alpha)
    a_F = full_t[-1] >= thr_f
    # A: the 1,800 ms forest on windows truncated at each event's early-exit time
    sA_v = scatter(va, d_va["event_id"], truncated_scores(models[-1], F_va, tv))
    sA_t = scatter(te, d_te["event_id"], truncated_scores(models[-1], F_te, tt))
    thr_a = threshold_for_fpr(yv_full, sA_v, alpha)
    a_A = sA_t >= thr_a
    # E (and E')
    a_E = scatter(te, d_te["event_id"], alarm_t.astype(float)) > 0.5
    time_full = np.full(len(te), np.nan)
    pos = {e: i for i, e in enumerate(te.event_id.to_numpy())}
    idx = np.array([pos[e] for e in d_te["event_id"]])
    time_full[idx] = tt
    return dict(F=a_F, A=a_A, E=a_E, Ep=a_E.copy(), t_early=time_full, rule=rule, thr_f=thr_f, thr_a=thr_a)


def main() -> None:
    import pandas as pd

    from crashguard.results import record_many

    tr, va, te = frames_full()
    d_tr, F_tr = feature_sets("train")
    d_va, F_va = feature_sets("validation")
    d_te, F_te = feature_sets("test", dedup=True)
    yt = te.y.to_numpy()
    trig_pos = np.zeros(len(te), bool)
    pos = {e: i for i, e in enumerate(te.event_id.to_numpy())}
    for e, y in zip(d_te["event_id"], d_te["y"]):
        trig_pos[pos[e]] = bool(y == 1)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"s6.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    rows = []
    for alpha in ALPHAS:
        a = f"a{int(round(alpha * 100))}"
        res = {seed: arms_for_seed(seed, alpha, F_tr, d_tr["y"], va, te, d_va, d_te, F_va, F_te) for seed in SEEDS}
        assert all((r["E"] == r["Ep"]).all() for r in res.values()), "E' must have the alarms of E by construction"
        draws = list(B._idx(len(te), B.N_BOOT, B.SEED))
        for tag, seeds in (("seed42", (C.SEED,)), ("mean5", C.SEEDS)):
            A_ = {arm: np.stack([res[s][arm] for s in seeds], axis=1) for arm in ARMS}  # (n, n_seeds) bool
            T = np.stack([res[s]["t_early"] for s in seeds], axis=1)

            def stats(i) -> dict:
                out = {}
                for arm in ARMS:
                    out[f"{arm}.recall"] = float(A_[arm][i][yt[i] == 1].mean())
                    out[f"{arm}.fa"] = float(A_[arm][i][yt[i] == 0].mean())
                m = trig_pos[i]
                t_early = float(np.nanmean(T[i][m]))
                out["F.time"], out["Ep.time"] = 1800.0, 1800.0
                out["A.time"], out["E.time"] = t_early, t_early
                out["d.A_minus_F.recall"] = out["A.recall"] - out["F.recall"]
                out["d.Ep_minus_F.recall"] = out["Ep.recall"] - out["F.recall"]
                out["d.E_minus_Ep.recall"] = out["E.recall"] - out["Ep.recall"]
                out["d.E_minus_F.recall"] = out["E.recall"] - out["F.recall"]
                out["d.A_minus_F.time"] = out["A.time"] - out["F.time"]
                out["d.E_minus_Ep.time"] = out["E.time"] - out["Ep.time"]
                return out

            point = stats(np.arange(len(te)))
            dr = [stats(i) for i in draws]
            for k, v in point.items():
                d = np.array([x[k] for x in dr])
                lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
                unit = "ms" if k.endswith("time") else "fraction"
                note = ("seed 42 only" if tag == "seed42" else "mean over seeds 0 to 4; interval is for that mean") + "; paired bootstrap of test events, 1,000 resamples; differences use the same drawn events"
                add(f"{a}.{tag}.{k}", round(v, 5), unit, note)
                add(f"{a}.{tag}.{k}_lo", round(lo, 5), unit, "95% bootstrap interval")
                add(f"{a}.{tag}.{k}_hi", round(hi, 5), unit, "95% bootstrap interval")
                rows.append(dict(alpha=alpha, tag=tag, stat=k, value=v, lo=lo, hi=hi))
        # per-event decisions of seed 42 (arm E), used by the S11 simulation as the early-exit decision-time distribution
        r42 = res[C.SEED]
        trig_ids = set(d_te["event_id"])
        pd.DataFrame(dict(event_id=te.event_id.to_numpy(), y=te.y.to_numpy(), triggered=te.event_id.isin(trig_ids).to_numpy(), alarm_E=r42["E"], alarm_F=r42["F"], time_ms=r42["t_early"])).to_csv(C.TABLES / f"s6_events_seed42_{a}.csv", index=False)
        add(f"{a}.n_test_events", len(te), "events", "de-duplicated test split")
        add(f"{a}.n_triggered_crash", int(trig_pos.sum()), "events", "triggered crash events, the events the decision time is averaged over")
        add(f"{a}.ep_alarms_equal_e", 1, "flag", "E' has the alarms of E by construction (asserted in the code)")
    pd.DataFrame(rows).to_csv(C.TABLES / "s6_early.csv", index=False)
    record_many(ent, purge_prefixes=("s6.",))
    for alpha in ALPHAS:
        a = f"a{int(round(alpha * 100))}"
        for tag in ("seed42", "mean5"):
            print(a, tag, {k: [round(next(r["value"] for r in rows if r["alpha"] == alpha and r["tag"] == tag and r["stat"] == k), 4)] for k in ("F.recall", "A.recall", "E.recall", "d.A_minus_F.recall", "d.Ep_minus_F.recall", "d.A_minus_F.time")})


if __name__ == "__main__":
    main()
