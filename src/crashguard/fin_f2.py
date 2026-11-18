"""F2 (EXPLORATORY-REVISED): VZCrash-side reruns with real plus surrogate training windows (docs/02_preregistration/PREREGISTRATION_V5.md section F). Surrogate windows (``fin_surr``) train only; validation, thresholds and every reported
test metric use real events. Mixing ratio r (surrogate per real training window) from {0, 0.5, 1, 2, 5} is chosen on the real validation split (AP of triggered events, 5-seed mean); r = 0 is the control with identical code.
Hypotheses run here: H-F2a (original H-P4b), H-F2b (original H-X3), H-F2d (original H-X1, AP clause). H-F2c, H-F2e, H-F2f are NOT_RUN (reasons in the preregistration addendum and DECISIONS).
The main estimate is the supplied-split test result (de-duplicated primary, strict sensitivity), scored once per model and seed after r was chosen on validation; grouped nested cross-validation is NOT_RUN on this side (no vehicle identifier)."""
from __future__ import annotations

import datetime as dt
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from scipy.stats import ks_2samp
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard import fin_surr as SU
from crashguard import windows_cache as W
from crashguard import x1_fixedpoint as X1
from crashguard.detector_extra import frames_full, threshold_for_fpr
from crashguard.fin_common import Entries
from crashguard.s2_dedup import fast_ap
from crashguard.vz_leakage import masks
from crashguard.x3_groupaware import train_groups

RATIOS = (0.0, 0.5, 1.0, 2.0, 5.0)
SEEDS = C.SEEDS
COLS = list(C.FEATURES)
OUT = Path("results/surrogate")
SRC = "results/tables/f_f2.csv"
CHUNK = 1000


def _feat_job(a):
    par, n, seed = a
    acc, gyro, y = SU.sample(par, n, seed)
    return W.features_of(acc, gyro)[COLS].to_numpy(np.float32), y


def surrogate_features(par: dict, n: int, seed0: int = 5_000_000, workers: int = 12):
    jobs = [(par, min(CHUNK, n - k * CHUNK), seed0 + k) for k in range((n + CHUNK - 1) // CHUNK)]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_feat_job, jobs))
    return np.concatenate([r[0] for r in res]), np.concatenate([r[1] for r in res])


def real_train_windows(tr: pd.DataFrame):
    z = W.load("train", dedup=False)
    pos = {int(e): i for i, e in enumerate(z["event_id"])}
    rows = np.array([pos[int(e)] for e in tr.event_id.to_numpy()])
    return z["acc"][rows], z["gyro"][rows]


def ds32(acc: np.ndarray) -> np.ndarray:
    r = np.linalg.norm(acc, axis=2)
    return np.stack([c.mean(1) for c in np.array_split(r, 32, axis=1)], axis=1).astype(np.float32)


def validate(par: dict, tr: pd.DataFrame, acc: np.ndarray, gyro: np.ndarray, E: Entries) -> None:
    """Marginals against the real training windows (two-sample KS per feature and class) and the nearest-neighbour check."""
    sa, sg, sy = SU.sample(par, 3000, 4_000_000)
    fs = W.features_of(sa, sg)
    y = tr.y.to_numpy()
    ok = {}
    for c, name in ((1, "crash"), (0, "noncrash")):
        for k in COLS:
            d = ks_2samp(tr[k][y == c], fs[k][sy == c]).statistic
            E.add(f"surrogate.ks.{name}.{k}", round(float(d), 4), "statistic", "SIMULATED", "two-sample KS, 3,000 surrogate windows against the real training windows; matched if at most 0.20")
            ok[(name, k)] = d <= 0.20
    E.add("surrogate.features_matched", int(sum(ok.values())), "of 28", "SIMULATED", "class x feature pairs with KS at most 0.20 (the validated marginals; the others are not matched)")
    # spectra: mean power in the five bands of the post-trigger resultant, real against surrogate (relative difference)
    def bands(a):
        res = np.linalg.norm(a[:, SU.PRE:] - a[:, : SU.PRE - 5].mean(1, keepdims=True), axis=2)
        F = np.abs(np.fft.rfft(res - res.mean(1, keepdims=True), axis=1)) ** 2
        fr = np.fft.rfftfreq(res.shape[1], 1 / SU.FS)
        b = np.stack([F[:, (fr >= lo) & (fr < hi)].sum(1) for lo, hi in SU.BANDS], axis=1)
        return (b / b.sum(1, keepdims=True)).mean(0)
    br, bs = bands(acc[y == 1][:3000]), bands(sa[sy == 1])
    for i, (lo, hi) in enumerate(SU.BANDS):
        E.add(f"surrogate.band_share.crash.{lo:g}_{hi:g}Hz.real", round(float(br[i]), 4), "fraction", "MEASURED_SOFTWARE", "mean share of post-trigger resultant spectral power")
        E.add(f"surrogate.band_share.crash.{lo:g}_{hi:g}Hz.surrogate", round(float(bs[i]), 4), "fraction", "SIMULATED")
    # nearest neighbour: each surrogate window against all real training windows (L-infinity on 32 bins of |a|), and real-to-real
    Xr = ds32(acc)
    tree = cKDTree(Xr)
    dsyn = tree.query(ds32(sa), k=1, p=np.inf, workers=-1)[0]
    idx = np.random.default_rng(42).choice(len(Xr), 3000, replace=False)
    dreal = tree.query(Xr[idx], k=2, p=np.inf, workers=-1)[0][:, 1]
    p1 = float(np.quantile(dreal, 0.01))
    for nm, v in (("min", dsyn.min()), ("p01", np.quantile(dsyn, 0.01)), ("median", np.median(dsyn))):
        E.add(f"surrogate.nn_surrogate_to_real.{nm}", round(float(v), 5), "g", "SIMULATED", "L-infinity distance of the 32-bin |a| vector to the nearest real training window")
    for nm, v in (("min", dreal.min()), ("p01", p1), ("median", np.median(dreal))):
        E.add(f"surrogate.nn_real_to_real.{nm}", round(float(v), 5), "g", "MEASURED_SOFTWARE", "same, real window to its nearest other real window (3,000 windows)")
    E.add("surrogate.nn_copies", int((dsyn <= p1).sum()), "windows", "SIMULATED", "surrogate windows at or below the 1st percentile of real-to-real distances (treated as copies and counted; none is dropped from the 3,000 checked)")


def fit_rf(X, y, seed, trees=15, depth=6, w=None):
    m = RandomForestClassifier(n_estimators=trees, max_depth=depth, random_state=seed, n_jobs=-1).fit(X, y, sample_weight=w)
    m.set_params(n_jobs=1)
    return m


def main() -> None:
    tr, va, te = frames_full()
    acc, gyro = real_train_windows(tr)
    y_tr = tr.y.to_numpy()
    OUT.mkdir(parents=True, exist_ok=True)
    par = SU.fit(acc, gyro, y_tr)
    json.dump(par, open(OUT / "vzcrash_surrogate_params.json", "w"), indent=1)
    (OUT / "README.md").write_text("""# VZCrash-style surrogate windows (parameters only)

VZCrash is released under CC BY-NC 4.0 (Hugging Face `vzc-research-chapter/VZCrash`, revision 42e1482d005c0e545379d6cfa4939486c9fe4249; author reply 2026-11-12). The fitted parameters in this folder are therefore released under CC BY-NC 4.0 with attribution to the VZCrash authors (Bianconcini et al., arXiv 2606.06074). Code: Apache-2.0 (`crashguard/fin_surr.py`).
Only summary parameters are released (class share; per class means and covariances of transformed summary statistics; axis-share means). No record, window or hash is stored. The generator matches only the marginals that were validated (`f.f2.surrogate.ks.*` in `results/results.json`); the others are not matched. Detector scores on surrogate windows are not comparable with scores on real data. The surrogate is not unbiased and is not a substitute for VZCrash.
""", encoding="utf-8")
    E = Entries("f.f2", SRC)
    E.add("origin_note", "EXPLORATORY-REVISED: revised after the negative; surrogate windows train only", "text", "SIMULATED")
    validate(par, tr, acc, gyro, E)
    n_max = int(round(max(RATIOS) * len(tr)))
    Xs, ys = surrogate_features(par, n_max)
    E.add("surrogate.n_windows", int(n_max), "windows", "SIMULATED", "largest surrogate set (ratio 5)")
    Xtr = tr[COLS].to_numpy(np.float32)
    gid, _ = train_groups(tr)
    _, inv, cnt = np.unique(gid, return_inverse=True, return_counts=True)
    w_real = 1.0 / cnt[inv]
    yv, trig_v = va.y.to_numpy(), va.triggered.to_numpy(bool)

    def train(kind: str, r: float, seed: int, trees=15, depth=6):
        k = int(round(r * len(tr)))
        X = np.concatenate([Xtr, Xs[:k]])
        y = np.concatenate([y_tr, ys[:k]])
        w = np.concatenate([w_real, np.ones(k)]) if kind == "gw" else None
        return fit_rf(X, y, seed, trees, depth, w)

    def score(m, df):
        s = np.full(len(df), -1.0)
        t = df.triggered.to_numpy(bool)
        s[t] = m.predict_proba(df[t][COLS].to_numpy(np.float32))[:, 1]
        return s

    # ---- selection of r on the REAL validation split (before any test event is scored)
    sel = {}
    for kind, trees, depth in (("std", 15, 6), ("gw", 15, 6), ("x1", 10, 9)):
        ap = {}
        for r in RATIOS:
            aps = []
            for s in SEEDS:
                m = train("gw" if kind == "gw" else "std", r, s, trees, depth)
                sv = score(m, va)
                aps.append(fast_ap(yv[trig_v], sv[trig_v]))
            ap[r] = float(np.mean(aps))
            E.add(f"val_ap.{kind}.r{r:g}", round(ap[r], 5), "AP", "MEASURED_SOFTWARE", "5-seed mean AP of triggered REAL validation events (the selection criterion)")
        best = max(RATIOS, key=lambda r: (round(ap[r], 6), -r))
        sel[kind] = best
        E.add(f"best_ratio.{kind}", best, "ratio", "MEASURED_SOFTWARE", "chosen on the real validation split; ties go to the smaller ratio")
    log = Path("results/tables/f_scored_log.csv")
    pd.DataFrame([dict(item="VZCrash test split (de-duplicated, strict)", scored_at=dt.datetime.now().isoformat(timespec="seconds"), ratios_chosen=json.dumps(sel), note="revised after the negative; r chosen on validation before scoring")]).to_csv(log, mode="a", header=not log.exists(), index=False)
    # ---- test scoring (once per model and seed)
    M = masks(te)
    sets = {"strict": M["near"], "dedup": np.ones(len(te), bool)}
    y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
    variants = {"std_r0": ("std", 0.0, 15, 6), "std_best": ("std", sel["std"], 15, 6), "gw_r0": ("gw", 0.0, 15, 6), "gw_best": ("gw", sel["gw"], 15, 6),
                "x1_float_r0": ("std", 0.0, 10, 9), "x1_float_best": ("std", sel["x1"], 10, 9)}
    S_, T_ = {v: [] for v in variants}, {v: [] for v in variants}
    Q_, QT_ = {"x1_q16_r0": [], "x1_q16_best": []}, {"x1_q16_r0": [], "x1_q16_best": []}
    for s in SEEDS:
        for v, (kind, r, trees, depth) in variants.items():
            m = train(kind, r, s, trees, depth)
            sva, ste = score(m, va), score(m, te)
            S_[v].append(ste)
            T_[v].append((threshold_for_fpr(yv, sva, 0.01), threshold_for_fpr(yv, sva, 0.05)))
            if v.startswith("x1_float"):
                k = int(round(r * len(tr)))
                Xfit = np.concatenate([Xtr, Xs[:k]])
                lo, hi = Xfit.min(0), Xfit.max(0)
                q = X1.quantise(m, lo, hi, 16)
                qv = np.full(len(va), -1.0)
                qv[trig_v] = X1.predict(q, va[trig_v][COLS].to_numpy(np.float32))
                qt = np.full(len(te), -1.0)
                qt[trig] = X1.predict(q, te[trig][COLS].to_numpy(np.float32))
                key = v.replace("float", "q16")
                Q_[key].append(qt)
                QT_[key].append((threshold_for_fpr(yv, qv, 0.01), threshold_for_fpr(yv, qv, 0.05)))
        print("seed", s, flush=True)
    # TSTR: surrogate only (as many windows as the real training set), tested on real events
    tstr = []
    for s in SEEDS:
        k = len(tr)
        m = fit_rf(Xs[:k], ys[:k], s)
        tstr.append(score(m, te))

    def stat(idx: np.ndarray) -> dict:
        out = {}
        for sn, msk in sets.items():
            sel_ = idx[msk[idx]]
            yy, tt = y[sel_], trig[sel_]
            pos = yy == 1
            for v in list(variants) + list(Q_):
                S = S_[v] if v in S_ else Q_[v]
                T = T_[v] if v in T_ else QT_[v]
                per = [(float((s[sel_][pos] >= a).mean()), float((s[sel_][pos] >= b).mean()), fast_ap(yy[tt], s[sel_][tt])) for s, (a, b) in zip(S, T)]
                for k, mn in enumerate(("recall_at_1pct", "recall_at_5pct", "ap")):
                    out[(sn, v, mn)] = float(np.mean([p[k] for p in per]))
            per = [fast_ap(yy[tt], s[sel_][tt]) for s in tstr]
            out[(sn, "tstr", "ap")] = float(np.mean(per))
        return out

    point = stat(np.arange(len(te)))
    dr = [stat(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
    for (sn, v, mn), val in point.items():
        d = np.array([x[(sn, v, mn)] for x in dr])
        for suf, x in (("", val), ("_lo", np.quantile(d, 0.025)), ("_hi", np.quantile(d, 0.975))):
            E.add(f"test.{sn}.{v}.{mn}{suf}", round(float(x), 5), "AP" if mn == "ap" else "fraction", "MEASURED_SOFTWARE", "5-seed mean, paired bootstrap over test events" if not suf else "95% interval")

    def diff(sn, a, b, mn):
        d = np.array([x[(sn, b, mn)] - x[(sn, a, mn)] for x in dr])
        pt = point[(sn, b, mn)] - point[(sn, a, mn)]
        return pt, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975)), d

    # H-F2a: best-r standard training minus real-only standard training, recall at 1%, strict set (original H-P4b margin 0.02)
    for tag, a, b, margin in (("hF2a", "std_r0", "std_best", 0.02), ("hF2b", "std_r0", "gw_best", 0.01)):
        pt, lo, hi, d = diff("strict", a, b, "recall_at_1pct")
        E.add(f"{tag}.gain", round(pt, 5), "fraction", "MEASURED_SOFTWARE", f"{b} minus {a}, recall at the 1% target, strict set (EXPLORATORY-REVISED)")
        E.add(f"{tag}.gain_lo", round(lo, 5), "fraction", "MEASURED_SOFTWARE", "95% interval")
        E.add(f"{tag}.gain_hi", round(hi, 5), "fraction", "MEASURED_SOFTWARE", "95% interval")
        E.add(f"{tag}.criterion_met", int(pt >= margin and lo > 0), "flag", "MEASURED_SOFTWARE", f"gain at least {margin} with the interval above zero (original criterion)")
        E.add(f"{tag}.p_raw", round(float(max(np.mean(d <= margin), 0.001)), 4), "p", "MEASURED_SOFTWARE", f"share of resamples at or below {margin}")
    for tag, a, b in (("control_gw_r0_minus_std_r0", "std_r0", "gw_r0"), ("gw_best_minus_gw_r0", "gw_r0", "gw_best")):
        pt, lo, hi, _ = diff("strict", a, b, "recall_at_1pct")
        E.add(f"{tag}.recall_at_1pct", round(pt, 5), "fraction", "MEASURED_SOFTWARE", "strict set; the real-only rerun of X3 and the effect of surrogate windows inside group-aware training")
        E.add(f"{tag}.recall_at_1pct_lo", round(lo, 5), "fraction", "MEASURED_SOFTWARE", "95% interval")
        E.add(f"{tag}.recall_at_1pct_hi", round(hi, 5), "fraction", "MEASURED_SOFTWARE", "95% interval")
    # H-F2d: AP clause of H-X1 (float minus 16-bit, dedup set, upper end at most 0.005) with the best r; the flash clause is arithmetic
    for tag, fl, q in (("r0", "x1_float_r0", "x1_q16_r0"), ("best", "x1_float_best", "x1_q16_best")):
        pt, lo, hi, d = diff("dedup", q, fl, "ap")
        E.add(f"hF2d.ap_loss_{tag}", round(pt, 5), "AP", "MEASURED_SOFTWARE", "float AP minus 16-bit AP, de-duplicated set")
        E.add(f"hF2d.ap_loss_{tag}_hi", round(hi, 5), "AP", "MEASURED_SOFTWARE", "upper end of the 95% interval; the AP clause needs at most 0.005")
        if tag == "best":
            E.add("hF2d.ap_clause_met", int(hi <= 0.005), "flag", "MEASURED_SOFTWARE")
            E.add("hF2d.flash_clause_met", 0, "flag", "ANALYTICAL", "16-bit thresholds cut the primary-layout flash estimate by 22.2% (7 of 9 bytes per node), below 30%, whatever the training data")
            E.add("hF2d.criterion_met", 0, "flag", "MEASURED_SOFTWARE", "both clauses are required")
            E.add("hF2d.p_raw", round(float(max(np.mean(d >= 0.005), 0.001)), 4), "p", "MEASURED_SOFTWARE", "p-value of the statistical (AP) clause, as in the original")
    for r, why in (("hF2c", "trigger cascade: surrogate windows are trigger-aligned and cannot train or test a trigger (preregistered NOT_RUN)"),
                   ("hF2e", "sequential rule: the six length-specific forests of N19 were not retrained with surrogate windows in the available time"),
                   ("hF2f", "leave-one-category-out calibration variants V0 to V5 were not re-implemented for a model trained with surrogate windows in the available time")):
        E.add(f"{r}.criterion_met", "NOT_RUN", "flag", "NOT_RUN", why)
    E.add("nested_cv", "NOT_RUN", "text", "NOT_RUN", "VZCrash has no vehicle identifier; grouped nested cross-validation over real records was not run on this side; the supplied-split test result is the estimate")
    E.write()
    print("selected ratios", sel)


if __name__ == "__main__":
    main()
