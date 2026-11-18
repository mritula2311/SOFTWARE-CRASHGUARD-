"""Models of P1 to P3 (docs/02_preregistration/PREREGISTRATION_V4.md, sections 0 to 3). Every model is fitted on development rows only and exposes ``predict_*`` on the feature frame of any rows.

Feature frames are the per-cell frames of ``pp_feat`` (one row per pooled record). Classes are module-level so fitted models can be pickled and scored later (the freeze/sealed-gate protocol).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.model_selection import GroupKFold

from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard.pp_common import MODES, macro_f1
from crashguard.pp_feat import DESC_D, MODE_FEATS, MONO, V2_DESC, V2_FAM

GB = dict(n_estimators=100, max_depth=2, learning_rate=0.05, subsample=0.8, random_state=C.SEED)
LEAVES, TREES = (4, 8), (50, 150, 300)


def onehot(mode_idx: np.ndarray) -> np.ndarray:
    m = np.zeros((len(mode_idx), len(MODES)), np.float32)
    m[np.arange(len(mode_idx)), np.asarray(mode_idx, int)] = 1.0
    return m


# ---- mode classifier (Z1) ----
class ModeClf:
    def __init__(self, seed: int = C.SEED):
        self.m = RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample", random_state=seed, n_jobs=1)

    def fit(self, df: pd.DataFrame, y: np.ndarray) -> ModeClf:
        self.m.fit(df[MODE_FEATS].to_numpy(float), y)
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return self.m.predict(df[MODE_FEATS].to_numpy(float)).astype(int)


def crossfit_mode(df: pd.DataFrame, y: np.ndarray, groups: np.ndarray, dev: np.ndarray, seed: int = C.SEED) -> np.ndarray:
    """Inferred mode of every row: out-of-fold (grouped 5-fold inside development) for development rows, the full-development classifier for the others."""
    out = np.zeros(len(df), int)
    idx = np.flatnonzero(dev)
    for tr, te in GroupKFold(5).split(idx, y[idx], groups[idx]):
        out[idx[te]] = ModeClf(seed).fit(df.iloc[idx[tr]], y[idx[tr]]).predict(df.iloc[idx[te]])
    full = ModeClf(seed).fit(df.iloc[idx], y[idx])
    out[~dev] = full.predict(df[~dev])
    return out


# ---- (a), (b), (c): estimators of delta-V ----
class RidgeEst:
    """(b) fill + ridge: N14 settings; ridge strength by leave-one-group-out inside the rows given to ``fit``."""

    def fit(self, df: pd.DataFrame, ref: np.ndarray, groups: np.ndarray) -> RidgeEst:
        X, m, ap = self._x(df), df.dv_fill.to_numpy(float), df.fill_applied.to_numpy(bool)
        y = np.log(ref / np.maximum(m, 1e-6))
        use = ap
        if use.sum() >= 4:
            self.alpha, self.corr = SP._alpha_and_fit(X[use], y[use], groups[use], m, ref, ap, "group")
        else:
            self.alpha, self.corr = float("nan"), None
        return self

    @staticmethod
    def _x(df: pd.DataFrame) -> np.ndarray:
        return np.stack([df.dv_plain.to_numpy(float), df.sat_share.to_numpy(float), df.pulse_ms.to_numpy(float)], axis=1)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        m, ap = df.dv_fill.to_numpy(float).copy(), df.fill_applied.to_numpy(bool)
        if self.corr is not None and ap.any():
            m[ap] = m[ap] * self.corr.factor(self._x(df)[ap])
        return m


def anchor_x(df: pd.DataFrame) -> np.ndarray:
    return np.concatenate([df[["dv_plain", "sat_share", "pulse_ms"]].to_numpy(float), df[["v2_" + k for k in V2_DESC]].to_numpy(float), df[["v2_" + k for k in V2_FAM]].to_numpy(float),
                           df[["dv_plain", "pulse_ms"]].to_numpy(float)], axis=1)


class AnchoredEst:
    """(c) X6: dv_plain x exp(max(0, g(x))), g = boosting of max(0, log(reference / plain)); never below the plain estimate."""

    def fit(self, df: pd.DataFrame, ref: np.ndarray) -> AnchoredEst:
        plain = np.maximum(df.dv_plain.to_numpy(float), 1e-6)
        self.g = GradientBoostingRegressor(loss="squared_error", **GB).fit(anchor_x(df), np.maximum(0.0, np.log(ref / plain)))
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        return df.dv_plain.to_numpy(float) * np.exp(np.maximum(0.0, self.g.predict(anchor_x(df))))


# ---- (d): direct ordinal gradient boosting ----
class OrdGBM:
    """Three cumulative binary LightGBM models (y > Low, y > Moderate, y > Severe) with non-decreasing constraints on the physics-supported descriptors; optional mode one-hot input."""

    def __init__(self, leaves: int, trees: int, use_mode: bool):
        self.leaves, self.trees, self.use_mode = leaves, trees, use_mode

    def _x(self, df: pd.DataFrame, mode_idx: np.ndarray | None) -> np.ndarray:
        X = df[DESC_D].to_numpy(np.float32)
        return np.concatenate([X, onehot(mode_idx)], axis=1) if self.use_mode else X

    def fit(self, df: pd.DataFrame, y: np.ndarray, mode_idx: np.ndarray | None) -> OrdGBM:
        X = self._x(df, mode_idx)
        mc = [1 if c in MONO else 0 for c in DESC_D] + ([0] * len(MODES) if self.use_mode else [])
        self.ms = []
        for k in range(3):
            m = LGBMClassifier(objective="binary", n_estimators=self.trees, num_leaves=self.leaves, learning_rate=0.05, min_child_samples=10, reg_lambda=1.0, random_state=C.SEED, n_jobs=1,
                               deterministic=True, force_row_wise=True, verbosity=-1, monotone_constraints=mc, monotone_constraints_method="basic")
            self.ms.append(m.fit(X, (y > k).astype(int)))
        return self

    def predict_cum(self, df: pd.DataFrame, mode_idx: np.ndarray | None) -> np.ndarray:
        X = self._x(df, mode_idx)
        p = np.stack([m.predict_proba(X)[:, 1] for m in self.ms], axis=1)
        return np.minimum.accumulate(p, axis=1)


def cum_to_class(p: np.ndarray) -> np.ndarray:
    return (np.minimum.accumulate(p, axis=1) >= 0.5).sum(axis=1)


def fit_ord(df, y, mode_idx, df_val, y_val, mode_val, use_mode: bool, sample_df=None) -> tuple[OrdGBM, dict]:
    """Hyper-parameters on validation macro-F1 (leaves x trees grid; ties: fewer trees, then fewer leaves)."""
    best = None
    for t in TREES:
        for lv in LEAVES:
            m = OrdGBM(lv, t, use_mode).fit(df, y, mode_idx)
            f = macro_f1(y_val, cum_to_class(m.predict_cum(df_val, mode_val)))
            if best is None or f > best[0] + 1e-12:
                best = (f, m, dict(leaves=lv, trees=t, val_macro_f1=f))
    return best[1], best[2]


# ---- (e): 1D CNN ----
def _net(n_mode: int):
    import torch.nn as nn

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.c1, self.c2, self.c3 = nn.Conv1d(3, 16, 5, padding=2), nn.Conv1d(16, 32, 5, stride=2, padding=2), nn.Conv1d(32, 32, 3, padding=1)
            self.fc1, self.fc2 = nn.Linear(64 + n_mode, 32), nn.Linear(32, 3)
            self.act = nn.ReLU()

        def forward(self, x, m=None):
            import torch

            x = self.act(self.c3(self.act(self.c2(self.act(self.c1(x))))))
            z = torch.cat([x.max(dim=2).values, x.mean(dim=2)] + ([m] if m is not None and m.shape[1] else []), dim=1)
            return self.fc2(self.act(self.fc1(z)))

    return Net()


def train_cnn(W, M, y, Wv, Mv, yv, seed: int, epochs: int = 150) -> dict:
    """One seed: Adam 1e-3, batch 32, at most ``epochs`` epochs, the epoch with the best validation macro-F1 (ties: the earlier). Returns the state dict and the validation curve."""
    import torch

    torch.set_num_threads(1)
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    net = _net(M.shape[1])
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    Wt, Mt = torch.tensor(W), torch.tensor(M)
    Yt = torch.tensor(np.stack([(y > k) for k in range(3)], axis=1).astype(np.float32))
    Wvt, Mvt = torch.tensor(Wv), torch.tensor(Mv)
    lossf = torch.nn.BCEWithLogitsLoss()
    best, curve = (-1.0, None, 0), []
    for ep in range(epochs):
        net.train()
        perm = rng.permutation(len(W))
        for i in range(0, len(W), 32):
            b = perm[i : i + 32]
            opt.zero_grad()
            lossf(net(Wt[b], Mt[b]), Yt[b]).backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            p = torch.sigmoid(net(Wvt, Mvt)).numpy()
        f = macro_f1(yv, cum_to_class(p))
        curve.append(f)
        if f > best[0] + 1e-12:
            best = (f, {k: v.clone() for k, v in net.state_dict().items()}, ep + 1)
    return dict(state=best[1], val_macro_f1=best[0], epoch=best[2], n_mode=M.shape[1])


class CNNEns:
    """Average of the cumulative probabilities of the seeds' networks."""

    def __init__(self, runs: list[dict], use_mode: bool):
        self.runs, self.use_mode = runs, use_mode

    def predict_cum(self, waves: np.ndarray, mode_idx: np.ndarray | None) -> np.ndarray:
        import torch

        torch.set_num_threads(1)
        M = onehot(mode_idx) if self.use_mode else np.zeros((len(waves), 0), np.float32)
        out = []
        for r in self.runs:
            net = _net(r["n_mode"])
            net.load_state_dict(r["state"])
            net.eval()
            with torch.no_grad():
                out.append(torch.sigmoid(net(torch.tensor(waves), torch.tensor(M))).numpy())
        return np.minimum.accumulate(np.mean(out, axis=0), axis=1)


# ---- reliability score (P3a) ----
class Reliability:
    """Gradient-boosted regression of log(reference / plain) on the descriptors of (d), optionally plus class-probability features."""

    def __init__(self, extra: bool):
        self.extra = extra

    def _x(self, df: pd.DataFrame, pe: np.ndarray | None) -> np.ndarray:
        X = df[DESC_D].to_numpy(float)
        if self.extra:
            X = np.concatenate([X, pe], axis=1)
        return X

    def fit(self, df, target, pe=None) -> Reliability:
        self.g = GradientBoostingRegressor(loss="squared_error", **GB).fit(self._x(df, pe), target)
        return self

    def score(self, df, pe=None) -> np.ndarray:
        return self.g.predict(self._x(df, pe))


def prob_feats(p_cum: np.ndarray) -> np.ndarray:
    """Maximum class probability and entropy from cumulative probabilities."""
    c = np.concatenate([np.ones((len(p_cum), 1)), p_cum, np.zeros((len(p_cum), 1))], axis=1)
    pr = np.clip(c[:, :-1] - c[:, 1:], 1e-9, 1.0)
    pr = pr / pr.sum(axis=1, keepdims=True)
    return np.stack([pr.max(axis=1), -(pr * np.log(pr)).sum(axis=1)], axis=1)
