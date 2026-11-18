"""P4b and P4c (docs/02_preregistration/PREREGISTRATION_V4.md section 4) on VZCrash. MEASURED_SOFTWARE.

P4b: augmentation of crash training windows (time shift, amplitude scaling, noise) and merging of identical training windows, against standard training of the 15-tree depth-6 forest; recall at the 1% target on the strict test set.
P4c: variants V0 to V5 for the false-alarm guarantee under vehicle-size shift; leave-one-category-out is primary. ``freeze`` writes the freeze files (no model file: everything is rebuilt from seeds 0 to 4); ``eval`` scores the test split.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import windows_cache as W
from crashguard.conformal import conformal_threshold, empirical_threshold
from crashguard.detector_extra import frames_full, threshold_for_fpr
from crashguard.s2_dedup import fast_ap
from crashguard.vz_leakage import masks
from crashguard.x3_groupaware import train_groups

SEEDS = C.SEEDS
COLS = list(C.FEATURES)
CATS = ("Light", "Medium", "Heavy", "Unknown")
COPIES = 2


# ---------------- P4b ----------------
def augment(acc: np.ndarray, gyro: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    n, L, _ = acc.shape
    sh = rng.integers(-10, 11, size=n)
    idx = np.clip(np.arange(L)[None, :] - sh[:, None], 0, L - 1)
    a = np.exp(rng.uniform(np.log(0.8), np.log(1.25), size=n))[:, None, None]
    sig = rng.uniform(0.01, 0.05, size=n)[:, None, None]
    ar = np.take_along_axis(acc, idx[:, :, None], axis=1) * a
    gr = np.take_along_axis(gyro, idx[:, :, None], axis=1) * a
    ar = np.clip(ar, -C.MPU_RANGE_G, C.MPU_RANGE_G) + rng.normal(0.0, 1.0, size=ar.shape) * sig
    return np.clip(ar, -C.MPU_RANGE_G, C.MPU_RANGE_G).astype(np.float32), gr.astype(np.float32)


def train_sets(tr: pd.DataFrame, seed: int) -> dict:
    """name -> (X, y) for standard, merge, aug, aug_merge."""
    gid, _size = train_groups(tr)
    first = np.zeros(len(tr), bool)
    seen: set = set()
    for i, g in enumerate(gid):
        if g not in seen:
            seen.add(g)
            first[i] = True
    z = W.load("train", dedup=False)
    pos = {int(e): i for i, e in enumerate(z["event_id"])}
    rows = np.array([pos[int(e)] for e in tr.event_id.to_numpy()])
    acc, gyro = z["acc"][rows], z["gyro"][rows]
    y = tr.y.to_numpy()
    X = tr[COLS].to_numpy(np.float32)
    rng = np.random.default_rng(seed)
    out = {"standard": (X, y), "merge": (X[first], y[first])}
    for name, keep in (("aug", np.ones(len(tr), bool)), ("aug_merge", first)):
        crash = keep & (y == 1)
        a_all, g_all = [], []
        for _ in range(COPIES):
            a2, g2 = augment(acc[crash], gyro[crash], rng)
            a_all.append(a2)
            g_all.append(g2)
        fa = W.features_of(np.concatenate(a_all), np.concatenate(g_all))[COLS].to_numpy(np.float32)
        Xb, yb = (X[keep], y[keep]) if name == "aug_merge" else (X, y)
        out[name] = (np.concatenate([Xb, fa]), np.concatenate([yb, np.ones(len(fa), int)]))
    return out


def p4b(stage: str) -> None:
    VARS = ("standard", "merge", "aug", "aug_merge")
    if stage == "freeze":
        h = PC.freeze("P4b", dict(variants=VARS, primary="aug_merge", copies=COPIES, forest="RandomForest(15 trees, depth 6)", seeds=list(SEEDS), note="settings fixed by the preregistration; the test split is not used"))
        print("freeze", h)
        return
    fz = PC.sealed_gate("P4b")
    tr, va, te = frames_full()
    va_trig = va[va.triggered]
    M = masks(te)
    sets = {"strict": M["near"], "dedup": np.ones(len(te), bool)}  # frames_full already holds the de-duplicated test events
    y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
    S_, T_ = {v: [] for v in VARS}, {v: [] for v in VARS}
    for seed in SEEDS:
        ts = train_sets(tr, seed)
        for v in VARS:
            X, yy = ts[v]
            m = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1).fit(X, yy)
            m.set_params(n_jobs=1)
            sva = np.full(len(va), -1.0)
            sva[va.triggered.to_numpy(bool)] = m.predict_proba(va_trig[COLS].to_numpy(np.float32))[:, 1]
            ste = np.full(len(te), -1.0)
            ste[trig] = m.predict_proba(te[trig][COLS].to_numpy(np.float32))[:, 1]
            S_[v].append(ste)
            T_[v].append((threshold_for_fpr(va.y.to_numpy(), sva, 0.01), threshold_for_fpr(va.y.to_numpy(), sva, 0.05)))
        print("seed", seed, {v: len(ts[v][1]) for v in VARS}, flush=True)

    def stat(idx: np.ndarray) -> dict:
        out = {}
        for sn, m_ in sets.items():
            sel = idx[m_[idx]]
            yy, tt = y[sel], trig[sel]
            pos = yy == 1
            for v in VARS:
                per = [(float((s[sel][pos] >= a).mean()), float((s[sel][pos] >= b).mean()), fast_ap(yy[tt], s[sel][tt])) for s, (a, b) in zip(S_[v], T_[v])]
                for k, mn in enumerate(("recall_at_1pct", "recall_at_5pct", "ap")):
                    out[(sn, v, mn)] = float(np.mean([p[k] for p in per]))
        return out

    E = PC.PEntries("p4b", "results/tables/p4b_augmentation.csv")
    E.add("freeze_commit", fz, "commit", "commit of the freeze of P4b")
    point = stat(np.arange(len(te)))
    dr = [stat(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
    rows = []
    for sn, m_ in sets.items():
        E.add(f"n_events.{sn}", int(m_.sum()), "events")
    for (sn, v, mn), val in point.items():
        d = np.array([x[(sn, v, mn)] for x in dr])
        E.ci(f"{sn}.{v}.{mn}", (val, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "AP" if mn == "ap" else "fraction", d=5)
    for sn in sets:
        for v in VARS[1:]:
            for mn in ("recall_at_1pct", "recall_at_5pct", "ap"):
                d = np.array([x[(sn, v, mn)] - x[(sn, "standard", mn)] for x in dr])
                pt = point[(sn, v, mn)] - point[(sn, "standard", mn)]
                lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
                lab = "" if v == "aug_merge" else "EXPLORATORY: "
                E.ci(f"{sn}.diff_{v}_minus_standard.{mn}", (pt, lo, hi), "fraction", lab + "positive = the variant is higher; paired bootstrap over test events, 5-seed mean", d=5)
                rows.append(dict(set=sn, variant=v, metric=mn, diff=pt, lo=lo, hi=hi))
                if (sn, v, mn) == ("strict", "aug_merge", "recall_at_1pct"):
                    E.add("hP4b.gain", round(pt, 5), "fraction", "recall at the 1% target, strict set, augmented and merged minus standard")
                    E.add("hP4b.gain_lo", round(lo, 5), "fraction")
                    E.add("hP4b.gain_hi", round(hi, 5), "fraction")
                    E.add("hP4b.p_raw", round(float(max(np.mean(d <= 0.02), 1.0 / (len(d) + 1))), 4), "probability", "share of resamples with gain at or below 0.02; floor 0.001")
                    E.add("hP4b.criterion_met", int(pt >= 0.02 and lo > 0), "flag", "gain at least 0.02 with the interval above zero")
                    print("H-P4b", round(pt, 5), round(lo, 5), round(hi, 5))
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "p4b_augmentation.csv", index=False)
    PC.time_log("P4b", "test split scored once per model and seed; freeze commit " + fz[:8])


# ---------------- P4c ----------------
def thr_v4(groups: list[np.ndarray], alpha: float) -> float:
    """Smallest lambda with mean over groups of (n_g R_g + 1) / (n_g + 1) <= alpha, R_g = share of group scores strictly above lambda (alarm if score > lambda)."""
    srt = [np.sort(g) for g in groups]
    cand = np.unique(np.concatenate(srt))
    risk = np.zeros(len(cand))
    for s in srt:
        n = len(s)
        cnt = n - np.searchsorted(s, cand, side="right")
        risk += (cnt + 1.0) / (n + 1.0)
    risk /= len(srt)
    ok = np.flatnonzero(risk <= alpha)
    return float(cand[ok[0]]) if ok.size else float("inf")


def cv_pvalue(cal: list[np.ndarray], test: list[np.ndarray]) -> np.ndarray:
    """CV+ conformal p-values: cal[k] = scores of the calibration negatives of group k from model k; test[k] = scores of the test events from model k."""
    n = sum(len(c) for c in cal)
    cnt = np.zeros(len(test[0]))
    for c, t in zip(cal, test):
        s = np.sort(c)
        cnt += len(s) - np.searchsorted(s, t, side="left")  # calibration scores >= test score
    return (1.0 + cnt) / (n + 1.0)


def fit_rf(tr: pd.DataFrame, seed: int, exclude: tuple = ()) -> RandomForestClassifier:
    m = tr[~tr.vehiclesize.isin(exclude)]
    r = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1).fit(m[COLS].to_numpy(np.float32), m.y.to_numpy())
    r.set_params(n_jobs=1)
    return r


def score_df(m, df: pd.DataFrame) -> np.ndarray:
    s = np.full(len(df), -1.0)
    t = df.triggered.to_numpy(bool)
    s[t] = m.predict_proba(df[t][COLS].to_numpy(np.float32))[:, 1]
    return s


VARS_C = ("V0", "V1", "V2", "V3", "V4", "V5")
ALPHAS = (0.01, 0.05)


def p4c(stage: str) -> None:
    if stage == "freeze":
        h = PC.freeze("P4c", dict(variants=VARS_C, alphas=list(ALPHAS), groups="vehicle-size categories", primary="leave-one-category-out, pooled", seeds=list(SEEDS), note="settings fixed by the preregistration; the test split is not used"))
        print("freeze", h)
        return
    fz = PC.sealed_gate("P4c")
    tr, va, te = frames_full()
    yv, yt = va.y.to_numpy(), te.y.to_numpy()
    cv, ct = va.vehiclesize.to_numpy(), te.vehiclesize.to_numpy()
    # alarms[(scheme, variant, alpha)][seed] -> bool array over test events
    alarms: dict = {}

    def put(scheme, v, a, arr):
        alarms.setdefault((scheme, v, a), []).append(arr)

    for seed in SEEDS:
        full = fit_rf(tr, seed)
        sv, st = score_df(full, va), score_df(full, te)
        neg = yv == 0
        # ----- leave-one-category-out (primary)
        for a in ALPHAS:
            arr = {v: np.zeros(len(te), bool) for v in VARS_C}
            for c in CATS:
                others = [k for k in CATS if k != c]
                cal = {k: sv[neg & (cv == k)] for k in others}
                pool = np.concatenate(list(cal.values()))
                tm = ct == c
                arr["V0"][tm] = st[tm] >= empirical_threshold(pool, a)
                t1 = conformal_threshold(pool, a)
                arr["V1"][tm] = st[tm] > t1
                arr["V2"][tm] = st[tm] > t1  # no calibration data of the held-out group: falls back to the pooled threshold
                arr["V4"][tm] = st[tm] > thr_v4(list(cal.values()), a)
                arr["V5"][tm] = st[tm] > max(conformal_threshold(cal[k], a) for k in others)
                # V3: models without c and without k
                cals, tests = [], []
                for k in others:
                    mk = fit_rf(tr, seed, exclude=(c, k))
                    s_k = score_df(mk, va)
                    cals.append(s_k[neg & (cv == k)])
                    tests.append(score_df(mk, te)[tm])
                arr["V3"][tm] = cv_pvalue(cals, tests) <= a
            for v in VARS_C:
                put("loco", v, a, arr[v])
        # ----- supplied test split (secondary): calibration on all validation categories
        for a in ALPHAS:
            cal = {k: sv[neg & (cv == k)] for k in CATS}
            pool = np.concatenate(list(cal.values()))
            put("supplied", "V0", a, st >= empirical_threshold(pool, a))
            put("supplied", "V1", a, st > conformal_threshold(pool, a))
            thr2 = {k: conformal_threshold(cal[k], a) for k in CATS}
            put("supplied", "V2", a, np.array([s > thr2[c] for s, c in zip(st, ct)]))
            put("supplied", "V4", a, st > thr_v4(list(cal.values()), a))
            put("supplied", "V5", a, st > max(thr2.values()))
        print("seed", seed, flush=True)
    # bootstrap: events resampled within vehicle-size category
    members = [np.flatnonzero(ct == c) for c in CATS]
    rng = np.random.default_rng(B.SEED)
    draws = [np.concatenate([m[rng.integers(0, len(m), len(m))] for m in members]) for _ in range(B.N_BOOT)]
    posm, negm = yt == 1, yt == 0
    E = PC.PEntries("p4c", "results/tables/p4c_guarantee.csv")
    E.add("freeze_commit", fz, "commit", "commit of the freeze of P4c")
    rows = []
    res = {}
    def fa_of(A, i):
        return float(A[:, i][:, negm[i]].mean())

    def rc_of(A, i):
        return float(A[:, i][:, posm[i]].mean())

    full = np.arange(len(te))
    for scheme in ("loco", "supplied"):
        for a in ALPHAS:
            A0 = np.stack(alarms[(scheme, "V0", a)])
            for v in VARS_C:
                if (scheme, v, a) not in alarms:
                    continue
                A = np.stack(alarms[(scheme, v, a)])  # (seeds, n)
                pf, df_ = fa_of(A, full), np.array([fa_of(A, i) for i in draws])
                pr, dr_ = rc_of(A, full), np.array([rc_of(A, i) for i in draws])
                g0 = np.array([rc_of(A, i) - rc_of(A0, i) for i in draws])
                pg = rc_of(A, full) - rc_of(A0, full)
                tag = f"{scheme}.a{int(a * 100)}.{v}"
                E.ci(f"{tag}.false_alarm_rate", (pf, float(np.quantile(df_, 0.025)), float(np.quantile(df_, 0.975))), "fraction", "all non-crash test events; 5-seed mean; events resampled within vehicle-size category", d=5)
                E.ci(f"{tag}.recall", (pr, float(np.quantile(dr_, 0.025)), float(np.quantile(dr_, 0.975))), "fraction", d=5)
                E.ci(f"{tag}.recall_gain_over_V0", (pg, float(np.quantile(g0, 0.025)), float(np.quantile(g0, 0.975))), "fraction", "against the lowest threshold that meets the rate on the same calibration set", d=5)
                if scheme == "loco" or v != "V3":
                    res[(scheme, v, a, "draws")] = (pf, df_, pg, g0)
                    for c in CATS:
                        m = (ct == c) & negm
                        E.add(f"{tag}.false_alarm_rate.{c}", round(float(A[:, m].mean()), 5), "fraction", f"held-out category {c}" if scheme == "loco" else f"category {c}")
                rows.append(dict(scheme=scheme, alpha=a, variant=v, fa=pf, fa_hi=float(np.quantile(df_, 0.975)), recall=pr, gain=pg, gain_lo=float(np.quantile(g0, 0.025)), gain_hi=float(np.quantile(g0, 0.975))))
    # H-P4c: primary = loco
    best_p, met = 1.0, []
    for v in ("V1", "V2", "V3", "V4", "V5"):
        ok, ps = True, []
        for a in ALPHAS:
            pf, df_, pg, g0 = res[("loco", v, a, "draws")]
            fa_ok = float(np.quantile(df_, 0.975)) <= a + 0.01
            gain_ok = pg >= 0.02
            ok &= fa_ok and gain_ok
            ps.append(max(PC.p_above(df_, a + 0.01), PC.p_below(g0, 0.02)))
            E.add(f"hP4c.{v}.a{int(a * 100)}.fa_upper_condition", int(fa_ok), "flag", "95% upper end of the false-alarm rate at most alpha + 0.01")
            E.add(f"hP4c.{v}.a{int(a * 100)}.gain_condition", int(gain_ok), "flag", "recall at least 0.02 above V0")
        E.add(f"hP4c.{v}.criterion_met", int(ok), "flag")
        met.append(ok)
        best_p = min(best_p, max(ps))
    E.add("hP4c.criterion_met", int(any(met)), "flag", "some variant meets both conditions at both targets (leave-one-category-out)")
    E.add("hP4c.p_raw", round(min(1.0, 5 * best_p), 4), "probability", "smallest per-variant p-value times 5 (choice among V1 to V5), capped at 1")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "p4c_guarantee.csv", index=False)
    PC.time_log("P4c", "test split scored once per model and seed; freeze commit " + fz[:8])
    print(pd.DataFrame(rows).round(4).to_string())


if __name__ == "__main__":
    which, stage = sys.argv[1], sys.argv[2]
    {"p4b": p4b, "p4c": p4c}[which](stage)
