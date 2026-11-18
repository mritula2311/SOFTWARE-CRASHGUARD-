"""X3 (docs/02_preregistration/PREREGISTRATION_V3.md): group-aware training against near-duplicate windows (VZCrash). MEASURED_SOFTWARE.

Near-duplicate groups among the TRAINING windows are groups of identical 280-sample trigger-aligned windows (the V1 audit found that every flagged test window equals its training window sample for sample).
Variants of the 15-tree forest of the headline: standard (weight 1), down-weight (weight 1 / group size; primary), merge (one window per group; EXPLORATORY). Thresholds come from the unchanged validation split.
Primary: recall at the 1% system-level false-alarm target on the strict test set, 5-seed mean, paired bootstrap over supplied test events (the same drawn events feed every variant).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import score_all, threshold_for_fpr
from crashguard.jp_common import Entries
from crashguard.models import op_thresholds
from crashguard.s2_dedup import fast_ap, load_frames
from crashguard.vz_audit import load as load_v1
from crashguard.vz_leakage import masks

SRC = "results/tables/x3_groupaware.csv"
SEEDS = C.SEEDS
VARIANTS = ("standard", "downweight", "merge")
METS = ("recall_at_1pct", "recall_at_5pct", "sys_recall", "ap")


def train_groups(tr: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(group id, group size) of every training row, from identical windows in the V1 cache."""
    ev, W = load_v1()
    own = W["train_owner"]
    ids = ev.event_id.to_numpy()[own]
    keep = ~(ev.raw_peak_mag.to_numpy()[own] > 16.0)
    h = {int(i): hashlib.sha1(w.tobytes()).hexdigest() for i, w, k in zip(ids, W["train"], keep) if k}
    codes = {}
    gid = np.array([codes.setdefault(h.get(int(e), f"single{e}"), len(codes)) for e in tr.event_id.to_numpy()])
    size = pd.Series(gid).map(pd.Series(gid).value_counts()).to_numpy()
    return gid, size


def main() -> None:
    tr, va, te = load_frames()
    va_trig = va[va.triggered]
    cols = list(C.FEATURES)
    gid, size = train_groups(tr)
    E = Entries("x.x3", SRC)
    E.add("train.n_windows", int(len(tr)), "windows")
    E.add("train.n_groups", int(len(set(gid.tolist()))), "groups")
    E.add("train.share_in_duplicate_group", round(float((size > 1).mean()), 4), "fraction", "training windows that share a window with at least one other training window")
    E.add("train.max_group_size", int(size.max()), "windows")
    first = np.zeros(len(tr), bool)
    seen: set[int] = set()
    for i, g in enumerate(gid):
        if g not in seen:
            seen.add(g)
            first[i] = True
    weights = {"standard": np.ones(len(tr)), "downweight": 1.0 / size, "merge": first.astype(float)}
    M = masks(te)
    sets = {"strict": M["near"], "dedup": ~te.leaky.to_numpy(bool), "supplied": M["supplied"]}
    y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
    Xtr = tr[cols].to_numpy(np.float32)
    S_, T_ = {v: [] for v in VARIANTS}, {v: [] for v in VARIANTS}
    for seed in SEEDS:
        for v in VARIANTS:
            m = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
            keep = weights[v] > 0
            m.fit(Xtr[keep], tr.y.to_numpy()[keep], sample_weight=weights[v][keep])
            m.set_params(n_jobs=1)
            sc = lambda d, m=m: m.predict_proba(d[cols].to_numpy(np.float32))[:, 1]  # noqa: E731
            sva = score_all(sc, va)
            thr_f1, _ = op_thresholds(va_trig.y.to_numpy(), sc(va_trig))
            S_[v].append(score_all(sc, te))
            T_[v].append((thr_f1, threshold_for_fpr(va.y.to_numpy(), sva, 0.01), threshold_for_fpr(va.y.to_numpy(), sva, 0.05)))
        print("seed", seed, flush=True)

    def stat(idx: np.ndarray) -> dict:
        out = {}
        for sn, m_ in sets.items():
            sel = idx[m_[idx]]
            yy, tt = y[sel], trig[sel]
            pos = yy == 1
            for v in VARIANTS:
                per = []
                for s, (a, b, c) in zip(S_[v], T_[v]):
                    ss = s[sel]
                    per.append((float((ss[pos] >= b).mean()), float((ss[pos] >= c).mean()), float((ss[pos] >= a).mean()), fast_ap(yy[tt], ss[tt])))
                for k, mn in enumerate(METS):
                    out[(sn, v, mn)] = float(np.mean([p[k] for p in per]))
        return out

    point = stat(np.arange(len(te)))
    dr = [stat(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
    for sn, m_ in sets.items():
        E.add(f"n_events.{sn}", int(m_.sum()), "events")
    rows = []
    for (sn, v, mn), val in point.items():
        d = np.array([x[(sn, v, mn)] for x in dr])
        E.ci(f"{sn}.{v}.{mn}", (val, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "AP" if mn == "ap" else "fraction", d=5)
    for sn in sets:
        for v in ("downweight", "merge"):
            for mn in METS:
                d = np.array([x[(sn, v, mn)] - x[(sn, "standard", mn)] for x in dr])
                pt = point[(sn, v, mn)] - point[(sn, "standard", mn)]
                lo, hi = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
                E.ci(f"{sn}.diff_{v}_minus_standard.{mn}", (pt, lo, hi), "fraction", "positive = the group-aware variant is higher", d=5)
                rows.append(dict(set=sn, variant=v, metric=mn, diff=pt, lo=lo, hi=hi))
                if (sn, v, mn) == ("strict", "downweight", "recall_at_1pct"):
                    p_raw = float(max(np.mean(d <= 0.0), 1.0 / (len(d) + 1)))
                    crit = pt >= 0.01 and lo > 0
                    E.add("hX3.gain", round(pt, 5), "fraction", "recall at the 1% target, strict set, down-weight minus standard")
                    E.add("hX3.gain_lo", round(lo, 5), "fraction")
                    E.add("hX3.gain_hi", round(hi, 5), "fraction")
                    E.add("hX3.p_raw", round(p_raw, 4), "probability", "share of resamples with gain at or below 0; floor 0.001")
                    E.add("hX3.criterion_met", int(crit), "flag", "gain at least 1 point with the interval above zero")
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "x3_groupaware.csv", index=False)
    print(pd.DataFrame(rows).round(4).to_string())
    print("share dup", float((size > 1).mean()), "groups", len(set(gid.tolist())), "of", len(tr))


if __name__ == "__main__":
    main()
