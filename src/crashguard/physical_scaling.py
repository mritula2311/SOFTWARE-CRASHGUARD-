"""X7 (N23): scale-model transfer by physical scaling of VZCrash events (docs/02_preregistration/EXPERIMENTS_EXTRA.md, written before this was run).

Every de-duplicated test event is transformed as x'(t) = b + a * (x(t / tau) - b), where b is the per-axis median of the event (the gravity part, kept) and the time axis is
stretched by tau (tau < 1 shortens the event) and resampled at 100 Hz. For tau < 1 a zero-phase 4th-order 45 Hz low-pass is applied before decimation (an unfiltered variant is also
run). The sensor model then clips at the range, the first sample above the trigger starts the window (so the trigger moves with a), and the 14 features are recomputed. The deployed
models (all features and the five scale-free features) were trained on unscaled data and are applied unchanged, with the validation threshold. The gyro is only resampled in time
(its amplitude is not scaled; an assumption). This is a plausibility check; it cannot predict performance on a car.
"""
from __future__ import annotations


import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score

from crashguard import config as C
from crashguard import features as F
from crashguard.detector_extra import frames_full
from crashguard.models import op_thresholds
from crashguard.split import leaky_test_ids

AMPS = (0.25, 0.5, 1.0, 2.0, 4.0)
TAUS = (0.25, 0.5, 1.0, 2.0)
LP_HZ = 45.0
SEEDS = (C.SEED,) + C.SEEDS
CHUNK = 1000
FS = float(C.FS_HZ)


def resample_time(x: np.ndarray, tau: float, antialias: bool) -> np.ndarray:
    """y(t) = x(t / tau) on a 100 Hz grid, with edge values held outside the record. x: (n, k)."""
    n = len(x)
    if tau == 1.0:
        return x
    n_new = max(int(round(n * tau)), 2)
    t_new = np.arange(n_new) / FS
    src = np.clip(t_new / tau * FS, 0, n - 1)
    if tau < 1.0 and antialias:  # compress in time: filter on a fine grid, then decimate
        up = 8
        t_fine = np.arange(n_new * up) / (FS * up)
        src_f = np.clip(t_fine / tau * FS, 0, n - 1)
        fine = np.stack([np.interp(src_f, np.arange(n), x[:, k]) for k in range(x.shape[1])], axis=1)
        fine = sosfiltfilt(butter(4, LP_HZ, fs=FS * up, output="sos"), fine, axis=0)
        return fine[::up]
    return np.stack([np.interp(src, np.arange(n), x[:, k]) for k in range(x.shape[1])], axis=1)


def transform_event(acc: np.ndarray, gyro: np.ndarray, a: float, tau: float, antialias: bool = True) -> tuple[np.ndarray, np.ndarray]:
    b = np.median(acc, axis=0)
    lin = resample_time(acc - b, tau, antialias)
    g = F._align_gyro(gyro, len(acc))
    g = resample_time(g, tau, antialias)
    return b + a * lin, g


def window_of(acc: np.ndarray, gyro: np.ndarray) -> tuple[np.ndarray, np.ndarray] | None:
    """Clip to the sensor range, find the trigger, cut the firmware-style window; None if the trigger never fires."""
    x = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
    g = np.clip(gyro, -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
    mag = np.linalg.norm(x, axis=1)
    hit = np.flatnonzero(mag > C.TRIGGER_G)
    if len(hit) == 0:
        return None
    s = int(hit[0]) - C.PRE_N
    return F._cut(x, s, C.WIN_N), F._cut(g, s, C.WIN_N)


def load_test_events() -> list[tuple[int, int, np.ndarray, np.ndarray]]:
    """(event_id, label, acc, gyro) of the de-duplicated test events that the original pipeline keeps (raw peak not above the sensor range)."""
    from crashguard.data import iter_events

    leaky = leaky_test_ids()
    out = []
    for path in sorted((C.RAW_DIR / "data").glob("test-*.parquet")):
        for _s, eid, label, _vs, _hd, acc, gyro, _gps in iter_events(path):
            if eid in leaky or len(acc) < 2:
                continue
            if float(np.linalg.norm(acc, axis=1).max()) > C.MPU_RANGE_G:
                continue
            out.append((eid, label, acc.astype(np.float64), gyro.astype(np.float64)))
    return out


def feature_grid(events: list, amps=AMPS, taus=TAUS, antialias: bool = True) -> dict[tuple[float, float], pd.DataFrame]:
    """Features of every event under every (a, tau): rows for triggered events only (columns event_id, label, features); untriggered events are counted separately."""
    store: dict = {(a, t): dict(ids=[], labels=[], acc=[], gyro=[], n_untrig=0) for a in amps for t in taus}
    out: dict = {}
    parts: dict = {(a, t): [] for a in amps for t in taus}
    for start in range(0, len(events), CHUNK):
        chunk = events[start : start + CHUNK]
        for k in store:
            store[k].update(ids=[], labels=[], acc=[], gyro=[])
        for eid, label, acc, gyro in chunk:
            for tau in taus:
                cache = None
                for a in amps:
                    if cache is None:
                        b = np.median(acc, axis=0)
                        lin = resample_time(acc - b, tau, antialias)
                        g = resample_time(F._align_gyro(gyro, len(acc)), tau, antialias)
                        cache = (b, lin, g)
                    b, lin, g = cache
                    w = window_of(b + a * lin, g)
                    if w is None:
                        store[(a, tau)]["n_untrig"] += 1
                        continue
                    s = store[(a, tau)]
                    s["ids"].append(eid), s["labels"].append(label), s["acc"].append(w[0]), s["gyro"].append(w[1])
        for k, s in store.items():
            if s["ids"]:
                fv = F.compute_features(np.stack(s["acc"]), np.stack(s["gyro"]))
                parts[k].append(pd.DataFrame(fv, columns=list(C.FEATURES)).assign(event_id=s["ids"], label=s["labels"]))
    for k, p in parts.items():
        out[k] = pd.concat(p, ignore_index=True) if p else pd.DataFrame(columns=list(C.FEATURES) + ["event_id", "label"])
    return out


def invariance_table(events: list) -> pd.DataFrame:
    """Median relative change of each feature when only the amplitude (a = 2) or only the time scale (tau = 2) changes, on triggered windows at the unscaled setting."""
    rows = []
    sub = events[:3000]
    base = feature_grid(sub, amps=(1.0,), taus=(1.0,))[(1.0, 1.0)].set_index("event_id")
    for name, a, tau in (("amplitude x2", 2.0, 1.0), ("time scale x2", 1.0, 2.0)):
        cur = feature_grid(sub, amps=(a,), taus=(tau,))[(a, tau)].set_index("event_id")
        common = base.index.intersection(cur.index)
        for f in C.FEATURES:
            x0, x1 = base.loc[common, f].to_numpy(float), cur.loc[common, f].to_numpy(float)
            ok = np.abs(x0) > 1e-6
            rows.append(dict(change=name, feature=f, n=int(ok.sum()), median_rel_change=float(np.median(np.abs(x1[ok] - x0[ok]) / np.abs(x0[ok]))) if ok.any() else float("nan")))
    return pd.DataFrame(rows)


def main() -> None:
    from crashguard.results import record_many

    tr, va, te = frames_full()
    events = load_test_events()
    y_ev = np.array([int(e[1] == 0) for e in events])
    idx = {e[0]: i for i, e in enumerate(events)}
    n_pos, n_neg = int(y_ev.sum()), int((y_ev == 0).sum())
    ent: list[dict] = []
    src = "results/tables/x7_scaling.csv"

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes=""):
        ent.append(dict(name=f"x7.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    add("n_events", len(events), "events", notes="de-duplicated test events whose raw peak is within the sensor range")
    grids = {"filtered": feature_grid(events, antialias=True), "unfiltered": feature_grid(events, antialias=False)}
    cols_all, cols_sf = list(C.FEATURES), list(C.SCALE_FREE)
    va_trig = va[va.triggered]
    rows = []
    for seed in SEEDS:
        models = {}
        for nm, cols in (("all", cols_all), ("scale_free", cols_sf)):
            rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
            rf.fit(tr[cols].to_numpy(np.float32), tr.y.to_numpy())
            rf.set_params(n_jobs=1)
            thr, _ = op_thresholds(va_trig.y.to_numpy(), rf.predict_proba(va_trig[cols].to_numpy(np.float32))[:, 1])
            models[nm] = (rf, cols, thr)
        for variant, grid in grids.items():
            if variant == "unfiltered" and seed != C.SEED:
                continue
            for (a, tau), f in grid.items():
                y_trig = (f.label.to_numpy() == 0).astype(int)
                for nm, (rf, cols, thr) in models.items():
                    if len(f):
                        s = rf.predict_proba(f[cols].to_numpy(np.float32))[:, 1]
                    else:
                        s = np.zeros(0)
                    alarm = s >= thr
                    tp, fp = int((alarm & (y_trig == 1)).sum()), int((alarm & (y_trig == 0)).sum())
                    # system AP: untriggered events are score -1 (never alarm)
                    full_scores = np.full(len(events), -1.0)
                    if len(f):
                        full_scores[[idx[e] for e in f.event_id]] = s
                    ap = float(average_precision_score(y_ev, full_scores))
                    dur = f.dur_above.to_numpy(float)
                    crash_dur = dur[y_trig == 1]
                    rows.append(dict(seed=seed, variant=variant, a=a, tau=tau, model=nm, recall=tp / n_pos, fa=fp / n_neg, sys_ap=ap, trig_rate_crash=float((y_trig == 1).sum() / n_pos),
                                     trig_rate_noncrash=float((y_trig == 0).sum() / n_neg), short_pulse_share=float((crash_dur < 40.0).mean()) if len(crash_dur) else float("nan"),
                                     median_dur_ms=float(np.median(crash_dur)) if len(crash_dur) else float("nan")))
    R = pd.DataFrame(rows)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    R.to_csv(C.TABLES / "x7_scaling.csv", index=False)
    inv = invariance_table(events)
    inv.to_csv(C.TABLES / "x7_invariance.csv", index=False)
    for (variant, a, tau, nm), g in R.groupby(["variant", "a", "tau", "model"]):
        tag = f"{variant}.a{a:g}.tau{tau:g}.{nm}"
        g5 = g[g.seed.isin(C.SEEDS)] if variant == "filtered" else g
        for col, unit in (("recall", "fraction"), ("fa", "fraction"), ("sys_ap", "score"), ("trig_rate_crash", "fraction"), ("trig_rate_noncrash", "fraction"), ("short_pulse_share", "fraction"), ("median_dur_ms", "ms")):
            v = g5[col].to_numpy(float)
            add(f"{tag}.{col}.mean", round(float(np.nanmean(v)), 5), unit, notes="mean over seeds 0-4" if variant == "filtered" else "seed 42 only")
            if len(v) > 1:
                add(f"{tag}.{col}.std", round(float(np.nanstd(v, ddof=1)), 5), unit)
            add(f"{tag}.{col}.seed42", round(float(g[g.seed == C.SEED][col].iloc[0]), 5), unit)
    for r_ in inv.itertuples():
        add(f"invariance.{r_.change.replace(' ', '_')}.{r_.feature}", round(float(r_.median_rel_change), 5) if r_.median_rel_change == r_.median_rel_change else "NOT_RUN", "fraction", notes="median relative change of the feature over triggered test windows")
    add("n_pos", n_pos, "events")
    add("n_neg", n_neg, "events")
    record_many(ent, purge_prefixes=("x7.",))
    pd.set_option("display.width", 220)
    f1 = R[(R.variant == "filtered") & (R.seed == C.SEED)]
    print(f1.pivot_table(index=["a", "tau"], columns="model", values=["recall", "fa", "sys_ap"]).round(3).to_string())
    print(inv.pivot(index="feature", columns="change", values="median_rel_change").round(3).to_string())


if __name__ == "__main__":
    main()
