"""L2 (docs/02_preregistration/PREREGISTRATION_V16.md section 4): post-event state corroboration of the confirm stage (MEASURED_SOFTWARE).

    python -m crashguard.r5_l2 build        # post-event features of every triggered VZCrash event -> data/processed/r5_l2_post.parquet
    python -m crashguard.r5_l2 dev          # development iterations (at most 5) on train (fit) and validation (thresholds, selection)
    python -m crashguard.r5_l2 freeze       # hash sources and the chosen parameters
    python -m crashguard.r5_l2 held         # held-out run, once, on HALF1 of the test split; keys r5.l2.*

The provisional alert and the early-exit stage are those of R3 (``early.py``, unchanged); L2 only replaces the confirm or cancel decision made at 1.8 s after the trigger by a decision after a
further window of ``W`` seconds. Features come from the raw event (100 Hz acceleration in g, 100 Hz gyro in deg/s, 1 Hz GPS speed in km/h; GPS sample j of k is placed at j (n/100)/k seconds, an
assumption stated in V16). Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import config as C

ROOT = Path(__file__).resolve().parents[2]
POST = ROOT / "data" / "processed" / "r5_l2_post.parquet"
FS = 100
FULL_N = 180  # samples after the trigger that the full window holds (1.8 s)
WS = (1, 2, 3)
FEATS = ["s_F", "drop", "rel_drop", "speed_pre", "gyro_mean", "quiet", "orient", "log_rot_energy", "gps_missing"]
SEED, NB = 42, 2000


@dataclass(frozen=True)
class L2Params:
    w: int = 2  # development item: corroboration window after the full window (s), 1 to 3
    model: str = "logistic"  # development item: "logistic" or "tree"
    class_weight: str = "none"  # development item: "none" or "balanced"
    alpha: float = 0.01


ITERATIONS = [L2Params(), L2Params(w=1), L2Params(w=3), L2Params(model="tree"), L2Params(class_weight="balanced")]


# ------------------------------------------------------------------------------------------------ features of one event
def _cut(x: np.ndarray, lo: int, hi: int) -> np.ndarray:
    """Samples lo to hi (exclusive) with edge repetition outside the event."""
    return x[np.clip(np.arange(lo, hi), 0, len(x) - 1)]


def gps_times(n: int, k: int) -> np.ndarray:
    """Time (s) of the GPS samples: sample j of k at j (n / 100) / k seconds (V16 section 4.1)."""
    return np.arange(k) * (n / FS) / k


def speed_features(gps: np.ndarray, n: int, i0: int, end_idx: int) -> dict:
    """Speed before the trigger (median of the GPS samples of the 3 s before it, else the nearest earlier sample), speed at the sample nearest the end of the window, and the drop (km/h)."""
    k = len(gps)
    if k < 2 or not np.isfinite(gps).all():
        return dict(speed_pre=np.nan, drop=np.nan, rel_drop=np.nan, gps_missing=1.0)
    t = gps_times(n, k)
    t_tr, t_end = i0 / FS, end_idx / FS
    inw = (t >= t_tr - 3.0) & (t <= t_tr)
    if inw.any():
        pre = float(np.median(gps[inw]))
    else:
        before = np.flatnonzero(t <= t_tr)
        pre = float(gps[before[-1]] if len(before) else gps[0])
    post = float(gps[int(np.argmin(np.abs(t - t_end)))])
    return dict(speed_pre=pre, drop=pre - post, rel_drop=float(np.clip((pre - post) / max(pre, 1.0), -2.0, 2.0)), gps_missing=0.0)


def angle_deg(u: np.ndarray, v: np.ndarray) -> float:
    c = float(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12), -1.0, 1.0))
    return math.degrees(math.acos(c))


def post_features(acc: np.ndarray, gyro: np.ndarray, gps: np.ndarray, i0: int, w: int) -> dict:
    """Post-event features of one event for a window of ``w`` seconds that starts at the end of the full window (V16 4.1). ``acc`` and ``gyro`` are the clipped event signals (n, 3)."""
    n = len(acc)
    end = i0 + FULL_N
    we = end + w * FS
    pre_vec = _cut(acc, i0 - FS, i0).mean(axis=0)
    win_a, win_g = _cut(acc, end, we), _cut(gyro, end, we)
    last_a = win_a[-FS:]
    quiet = float((np.abs(np.linalg.norm(last_a, axis=1) - 1.0) < 0.05).mean())
    orient = angle_deg(pre_vec, win_a[-FS // 2 :].mean(axis=0))
    gy_all = _cut(gyro, i0, we)
    energy = float((np.linalg.norm(gy_all, axis=1) ** 2).sum() / FS)
    out = dict(gyro_mean=float(np.linalg.norm(win_g, axis=1).mean()), quiet=quiet, orient=orient, log_rot_energy=math.log1p(energy), pad_after=float(we > n))
    out.update(speed_features(gps, n, i0, we))
    return out


# ------------------------------------------------------------------------------------------------ cache of the features of every triggered event
def _shard(path_str: str) -> list[dict]:
    from crashguard import features as F
    from crashguard.data import iter_events

    rows = []
    for split, eid, label, _vs, _hd, acc, gyro, gps in iter_events(Path(path_str)):
        n = len(acc)
        if n < 2:
            continue
        raw_peak = float(np.linalg.norm(acc, axis=1).max())
        if not np.isfinite(raw_peak) or raw_peak > C.MPU_RANGE_G:
            continue  # dropped by the pipeline (peak above the sensor range)
        a = np.clip(acc, -C.MPU_RANGE_G, C.MPU_RANGE_G)
        hit = np.flatnonzero(np.linalg.norm(a, axis=1) > C.TRIGGER_G)
        if not len(hit):
            continue
        i0 = int(hit[0])
        g = np.clip(F._align_gyro(gyro, n), -C.MPU_GYRO_RANGE_DPS, C.MPU_GYRO_RANGE_DPS)
        rec = dict(event_id=int(eid), split=split, label=int(label), n=n, i0=i0)
        for w in WS:
            for k, v in post_features(a, g, np.asarray(gps, float), i0, w).items():
                rec[f"{k}_w{w}"] = v
        rows.append(rec)
    return rows


def build(workers: int | None = None) -> None:
    import os

    files = sorted((C.RAW_DIR / "data").glob("*.parquet"))
    workers = workers or min(8, os.cpu_count() or 1)
    with ProcessPoolExecutor(workers) as ex:
        parts = list(ex.map(_shard, [str(f) for f in files]))
    df = pd.DataFrame([r for p in parts for r in p])
    POST.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(POST)
    print("post-event features", len(df), "events")


def load_post() -> pd.DataFrame:
    return pd.read_parquet(POST).set_index("event_id")


def design(post: pd.DataFrame, ids: np.ndarray, s_f: np.ndarray, w: int, fill: dict | None = None) -> tuple[np.ndarray, dict]:
    """Feature matrix (rows follow ``ids``). Missing GPS values are replaced by ``fill`` (train medians) and flagged in ``gps_missing``."""
    p = post.loc[ids]
    cols = {"s_F": s_f}
    for k in ("drop", "rel_drop", "speed_pre", "gyro_mean", "quiet", "orient", "log_rot_energy", "gps_missing"):
        cols[k] = p[f"{k}_w{w}"].to_numpy(float)
    X = pd.DataFrame(cols)[FEATS]
    if fill is None:
        fill = {k: float(np.nanmedian(X[k].to_numpy())) for k in FEATS}
    for k in FEATS:
        X[k] = X[k].fillna(fill[k])
    return X.to_numpy(float), fill


def fit_model(X: np.ndarray, y: np.ndarray, prm: L2Params, seed: int = SEED):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.tree import DecisionTreeClassifier

    cw = "balanced" if prm.class_weight == "balanced" else None
    if prm.model == "logistic":
        m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, class_weight=cw, random_state=seed))
    else:
        m = DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, class_weight=cw, random_state=seed)
    return m.fit(X, y)


# ------------------------------------------------------------------------------------------------ operating points and statistics
def recall_at(y: np.ndarray, s: np.ndarray, thr: float) -> float:
    return float(((s >= thr) & (y == 1)).sum() / max(int((y == 1).sum()), 1))


def thr_for_recall(y: np.ndarray, s: np.ndarray, target: float) -> float:
    """Largest threshold whose system recall (all crash events, scores of untriggered events are -1) is at least ``target`` (V16 4.2: the smallest false-alarm rate at the baseline's recall)."""
    pos = np.sort(s[(y == 1) & (s >= 0)])[::-1]
    n_pos = int((y == 1).sum())
    need = int(math.ceil(target * n_pos - 1e-9))
    if need <= 0:
        return float(np.nextafter(pos[0], np.inf)) if len(pos) else 1.0
    if need > len(pos):
        return 0.0
    return float(pos[need - 1])


def rel_reduction_boot(base: np.ndarray, new: np.ndarray, seed: int = SEED, nb: int = NB) -> dict:
    """Relative reduction 1 - mean(new) / mean(base) of two paired 0/1 arrays, paired bootstrap over events (the same resampled events for both)."""
    base, new = np.asarray(base, float), np.asarray(new, float)
    if not len(base) or base.mean() == 0:
        return dict(pt=float("nan"), lo=float("nan"), hi=float("nan"), p=1.0, base_rate=float(base.mean()) if len(base) else float("nan"), new_rate=float(new.mean()) if len(new) else float("nan"), n=int(len(base)))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(base), (nb, len(base)))
    mb, mn = base[idx].mean(1), new[idx].mean(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        d = 1.0 - mn / mb
    d = d[np.isfinite(d)]
    pt = float(1.0 - new.mean() / base.mean()) if base.mean() > 0 else float("nan")
    return dict(pt=pt, lo=float(np.quantile(d, 0.025)), hi=float(np.quantile(d, 0.975)), p=float(((d <= 0).sum() + 1) / (len(d) + 1)), base_rate=float(base.mean()), new_rate=float(new.mean()), n=int(len(base)))


def diff_boot(d: np.ndarray, seed: int = SEED, nb: int = NB) -> dict:
    """Mean of a paired per-event difference with a 95% interval and the one-sided p of H0: mean <= 0."""
    d = np.asarray(d, float)
    if not len(d):
        return dict(pt=float("nan"), lo=float("nan"), hi=float("nan"), p=1.0, n=0)
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), (nb, len(d)))].mean(1)
    return dict(pt=float(d.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), p=float(((m <= 0).sum() + 1) / (nb + 1)), n=int(len(d)))


def baseline_arms(seed: int, alpha: float, fr: dict, det: dict) -> dict:
    """The R3 arms on the validation and test frames exactly as ``s6_early.arms_for_seed``: F (single forest at 1,800 ms), E (early exit), with their thresholds."""
    from crashguard.detector_extra import threshold_for_fpr
    from crashguard.early import choose_rule, early_decisions, scatter

    va, te, d_va, d_te = fr["va"], fr["te"], fr["d_va"], fr["d_te"]
    Sv, St = det["Sv"], det["St"]
    yv_full = va.y.to_numpy()
    n_neg_v, n_pos_v = int((yv_full == 0).sum()), int((yv_full == 1).sum())
    full_v = [scatter(va, d_va["event_id"], Sv[:, k]) for k in range(Sv.shape[1])]
    rule = choose_rule(Sv, d_va["y"], n_neg_v, n_pos_v, full_v, yv_full, alpha)
    thr_f = threshold_for_fpr(yv_full, full_v[-1], alpha)
    alarm_t, tt = early_decisions(St, rule["hi"], rule["lo"], rule["t_f"])
    return dict(thr_f=thr_f, rule=rule, F_va=full_v[-1], F_te=scatter(te, d_te["event_id"], St[:, -1]), E_te=scatter(te, d_te["event_id"], alarm_t.astype(float)) > 0.5, t_early=tt)


def l2_scores(post: pd.DataFrame, det: dict, fr: dict, prm: L2Params, seed: int = SEED, which: tuple = ("va", "te")) -> dict:
    """Fit the combining model on the triggered train events (cross-fitted detector scores) and score the triggered events of the splits in ``which`` (development passes only "va");
    scores of all events (-1 untriggered)."""
    from crashguard.early import scatter

    ids_tr = det["ids_tr"]
    Xtr, fill = design(post, ids_tr, det["oof_tr"], prm.w)
    m = fit_model(Xtr, det["y_tr"], prm, seed)
    out = {}
    for split, frame, ids, S in (("va", fr["va"], det["ids_va"], det["Sv"]), ("te", fr["te"], det["ids_te"], det["St"])):
        if split not in which:
            continue
        X, _ = design(post, ids, S[:, -1], prm.w, fill)
        s = m.predict_proba(X)[:, 1]
        out[split] = scatter(frame, ids, s)
    return out


# ------------------------------------------------------------------------------------------------ development and held-out runs
def dev_iteration(prm: L2Params, post: pd.DataFrame, det: dict, fr: dict, base: dict) -> dict:
    """Validation only: baseline recall, L2 threshold at that recall, near-miss false-alarm rates (all near-miss validation events)."""
    va = fr["va"]
    y = va.y.to_numpy()
    nm = va.label.to_numpy() == 1
    s2 = l2_scores(post, det, fr, prm, which=("va",))["va"]
    r_base = recall_at(y, base["F_va"], base["thr_f"])
    t2 = thr_for_recall(y, s2, r_base)
    far_base = float((base["F_va"][nm] >= base["thr_f"]).mean())
    far_l2 = float((s2[nm] >= t2).mean())
    return dict(params=asdict(prm), val_recall_base=r_base, val_recall_l2=recall_at(y, s2, t2), val_far_nm_base=far_base, val_far_nm_l2=far_l2, val_rel_reduction=1 - far_l2 / far_base if far_base > 0 else float("nan"), thr_l2=t2)


def _setup(seed: int = SEED):
    from crashguard import r5_det as D

    fr = D.load_frames()
    det = D.fit_seed(seed, fr)
    post = load_post()
    return fr, det, post


def _dev() -> None:
    from crashguard import r5_common as R5

    fr, det, post = _setup()
    base = baseline_arms(SEED, 0.01, fr, det)
    log = []
    for it, prm in enumerate(ITERATIONS):
        e = dev_iteration(prm, post, det, fr, base)
        e["iteration"] = it
        log.append(e)
        print(it, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.items() if k != "params"}, e["params"], flush=True)
    (R5.TABLES / "r5_l2_dev_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    best = max(range(len(log)), key=lambda i: (round(log[i]["val_rel_reduction"], 9), -log[i]["params"]["w"], -i))
    (R5.TABLES / "r5_l2_dev_choice.json").write_text(json.dumps(dict(chosen=best, params=log[best]["params"], rule="V16 4.3: lowest validation near-miss false-alarm rate at the baseline's validation recall; ties go to the smaller window"), indent=1), encoding="utf-8")
    print("chosen iteration", best)


def _freeze() -> None:
    from crashguard import r5_common as R5

    ch = json.loads((R5.TABLES / "r5_l2_dev_choice.json").read_text(encoding="utf-8"))
    d = R5.freeze_entry("l2", ["src/crashguard/r5_l2.py", "src/crashguard/r5_det.py", "src/crashguard/early.py", "src/crashguard/detector_extra.py", "src/crashguard/windows_cache.py", "src/crashguard/features.py", "src/crashguard/config.py"], ch["params"],
                        ["data/processed/r5_det_seed42.pkl", "data/processed/r5_l2_post.parquet"])
    print("frozen l2", d["params_sha256"][:16])


def evaluate_heldout(prm: L2Params, fr: dict, det: dict, post: pd.DataFrame, seed: int = SEED) -> dict:
    """Held-out statistics on HALF1 of the test split for H-L2a and H-L2b (V16 4.2)."""
    from crashguard import r5_common as R5
    from crashguard.detector_extra import threshold_for_fpr

    va, te = fr["va"], fr["te"]
    yv, yt = va.y.to_numpy(), te.y.to_numpy()
    R5.ensure_split_hashes(te.event_id.to_numpy())
    h1 = R5.halves(te.event_id.to_numpy()) == 1
    base = baseline_arms(seed, prm.alpha, fr, det)
    s = l2_scores(post, det, fr, prm, seed)
    # operating points chosen on validation only
    r_base_v = recall_at(yv, base["F_va"], base["thr_f"])
    t_a = thr_for_recall(yv, s["va"], r_base_v)
    t_b = threshold_for_fpr(yv, s["va"], prm.alpha)
    F_base = base["F_te"] >= base["thr_f"]
    out = heldout_stats(F_base, s["te"] >= t_a, s["te"] >= t_b, base["E_te"], yt, te.label.to_numpy(), h1, seed)
    out.update(t_a=t_a, t_b=t_b, thr_base=base["thr_f"], val_recall_base=r_base_v, delay_s=prm.w)
    return out


def heldout_stats(F_base: np.ndarray, F_a: np.ndarray, F_b: np.ndarray, E: np.ndarray, y: np.ndarray, label: np.ndarray, h1: np.ndarray, seed: int = SEED) -> dict:
    """The statistics of H-L2a and H-L2b on the events selected by ``h1`` (pure function of the decisions; V16 4.2). ``F_base``, ``F_a``, ``F_b``: final alarms of the baseline confirm stage, of
    L2 at the equal-recall threshold and of L2 at the equal-budget threshold; ``E``: provisional alarms (early exit); ``y``: crash flag; ``label``: 1 = near miss."""
    nm = (label == 1) & h1
    crash = (y == 1) & h1
    out = dict(n_half1=int(h1.sum()), n_crash=int(crash.sum()), n_nearmiss=int(nm.sum()))
    out["a"] = rel_reduction_boot(F_base[nm], F_a[nm], seed)
    out["a"].update(recall_base=float(F_base[crash].mean()), recall_l2=float(F_a[crash].mean()))
    out["a"]["criterion_met"] = bool(out["a"]["pt"] >= 0.25 and out["a"]["lo"] > 0 and out["a"]["recall_l2"] >= out["a"]["recall_base"] - 0.01)
    Eh = E & h1
    retr_base = (Eh & ~F_base)[Eh].astype(float)
    retr_b = (Eh & ~F_b)[Eh].astype(float)
    fall = diff_boot(retr_base - retr_b, seed)
    out["b"] = dict(fall, retr_share_base=float(retr_base.mean()), retr_share_l2=float(retr_b.mean()), n_prov=int(Eh.sum()), recall_base=float(F_base[crash].mean()), recall_l2=float(F_b[crash].mean()),
                    fa_base=float(F_base[(y == 0) & h1].mean()), fa_l2=float(F_b[(y == 0) & h1].mean()))
    out["b"]["criterion_met"] = bool(out["b"]["pt"] >= 0.03 and out["b"]["lo"] > 0 and out["b"]["recall_l2"] >= out["b"]["recall_base"] - 0.01)
    out["b"]["rescued"] = int((Eh & ~F_base & F_b).sum())  # provisional alerts that the baseline retracts and L2 confirms
    out["b"]["cancelled_more"] = int((Eh & F_base & ~F_b).sum())  # provisional alerts that the baseline confirms and L2 cancels
    return out


def _held() -> None:
    from crashguard import r5_common as R5

    prm = L2Params(**R5.check_frozen("l2"))
    fr, det, post = _setup()
    ho = evaluate_heldout(prm, fr, det, post)
    rec = R5.Rec("r5.l2.", "src/crashguard/r5_l2.py", "MEASURED_SOFTWARE")
    rec.add("held.n_half1_events", ho["n_half1"], "events", "HALF1 of the de-duplicated test split (hash rule of V16 2.1)")
    rec.add("held.n_crash", ho["n_crash"], "events")
    rec.add("held.n_nearmiss", ho["n_nearmiss"], "events")
    rec.add("held.window_s", prm.w, "s", "corroboration window after the full window; the confirm frame leaves this much later than in R3 (the provisional alert is unchanged)")
    for tag, d in (("hL2a", ho["a"]), ("hL2b", ho["b"])):
        for k, v in d.items():
            if k in ("criterion_met",):
                rec.add(f"held.{tag}.{k}", int(v), "bool")
            elif isinstance(v, (int, float)):
                rec.add(f"held.{tag}.{k}", v, "fraction" if k not in ("n", "n_prov", "rescued", "cancelled_more", "p") else ("p" if k == "p" else "count"))
    rec.add("hL2a.p", ho["a"]["p"], "p", "one-sided paired bootstrap p of H0: relative reduction of the near-miss false-alarm rate at most 0")
    rec.add("hL2b.p", ho["b"]["p"], "p", "one-sided paired bootstrap p of H0: fall of the retraction share at most 0")
    rec.add("hL2a.criterion_met", int(ho["a"]["criterion_met"]), "bool", "point reduction at least 0.25, lower 95% limit above 0, held-out recall within 0.01 of the baseline")
    rec.add("hL2b.criterion_met", int(ho["b"]["criterion_met"]), "bool", "point fall at least 0.03, lower 95% limit above 0, recall within 0.01 of the baseline")
    rec.write()
    print(json.dumps(ho, indent=1, default=float))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"build": build, "dev": _dev, "freeze": _freeze, "held": _held}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
