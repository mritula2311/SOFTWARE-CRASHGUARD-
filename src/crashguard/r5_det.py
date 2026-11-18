"""Detector scores of the frozen R3 family for round 5 (used by L2, L3 and L5; V16 sections 4, 5 and 7).

The detector is the one of ``s6_early`` unchanged: six forests (15 trees, depth 6) trained on the triggered train events at the post-trigger lengths of ``early.LENGTHS_MS``, scored on the
triggered validation and test events. Nothing is tuned here. ``fit_seed`` returns the checkpoint scores and, for the 1,800 ms forest, scores of the train events from a 5-fold cross-fit (a model
that scores its own training events is over-confident; the cross-fit scores are only used to fit L2's combining model on the train split).

A seed's result is cached in ``data/processed/r5_det_seed<seed>.pkl`` (git-ignored). Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold

from crashguard import config as C
from crashguard.detector_extra import frames_full
from crashguard.early import LENGTHS_MS, feature_sets, scatter

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "processed"


def load_frames() -> dict:
    tr, va, te = frames_full()
    d_tr, F_tr = feature_sets("train")
    d_va, F_va = feature_sets("validation")
    d_te, F_te = feature_sets("test", dedup=True)
    return dict(tr=tr, va=va, te=te, d_tr=d_tr, d_va=d_va, d_te=d_te, F_tr=F_tr, F_va=F_va, F_te=F_te)


def fit_seed(seed: int, fr: dict | None = None, force: bool = False) -> dict:
    path = CACHE / f"r5_det_seed{seed}.pkl"
    if path.exists() and not force:
        return pickle.loads(path.read_bytes())
    fr = fr or load_frames()
    ytr = fr["d_tr"]["y"]
    models, Sv, St = [], [], []
    for m in LENGTHS_MS:
        rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
        rf.fit(fr["F_tr"][m].to_numpy(np.float32), ytr)
        rf.set_params(n_jobs=1)
        models.append(rf)
        Sv.append(rf.predict_proba(fr["F_va"][m].to_numpy(np.float32))[:, 1])
        St.append(rf.predict_proba(fr["F_te"][m].to_numpy(np.float32))[:, 1])
    Sv, St = np.stack(Sv, axis=1), np.stack(St, axis=1)
    Xf = fr["F_tr"][LENGTHS_MS[-1]].to_numpy(np.float32)
    oof = np.zeros(len(Xf))
    for k, (a, b) in enumerate(KFold(5, shuffle=True, random_state=seed).split(Xf)):
        rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1).fit(Xf[a], ytr[a])
        rf.set_params(n_jobs=1)
        oof[b] = rf.predict_proba(Xf[b])[:, 1]
    out = dict(seed=seed, Sv=Sv, St=St, oof_tr=oof, ids_tr=np.asarray(fr["d_tr"]["event_id"]), ids_va=np.asarray(fr["d_va"]["event_id"]), ids_te=np.asarray(fr["d_te"]["event_id"]),
               y_tr=np.asarray(ytr), y_va=np.asarray(fr["d_va"]["y"]), y_te=np.asarray(fr["d_te"]["y"]))
    path.write_bytes(pickle.dumps(out))
    return out


def full_scores(frame, ids: np.ndarray, scores: np.ndarray) -> np.ndarray:
    """Score of every event of ``frame`` (all events, -1 where the trigger did not pass)."""
    return scatter(frame, ids, scores)


def frame_for(split: str, fr: dict):
    return {"validation": fr["va"], "test": fr["te"]}[split]


__all__ = ["C", "LENGTHS_MS", "fit_seed", "full_scores", "load_frames"]
