"""X5 (N21): robustness of the crash detector to a bounded signal added to the accelerometer reading (docs/01_protocol/THREAT_MODEL_SPOOFING.md and docs/02_preregistration/EXPERIMENTS_EXTRA.md, written before this
was run).

SOFTWARE STUDY ON STORED DATASET WINDOWS ONLY. A perturbation is an array added to a stored window in memory; there is no signal generator, no search for a resonance and no
interface to a sensor. Budgets: amplitude epsilon on any axis in {0.1, 0.25, 0.5, 1, 2} g; one to three sinusoids between 2 and 45 Hz.

Attacks on the deployed forest: (R) random search over bounded sinusoid mixtures, (S) structured grid of single sinusoids (frequency x phase x axis pattern), (G) projected-gradient
attack on a logistic or small neural surrogate with a narrow-band projection, then transferred to the forest. Success for goal (a): a non-crash window that passes the trigger is
alarmed; goal (b): a crash window is not alarmed. A black-box search succeeds on a window if ANY of its candidates succeeds (the attacker can query the pipeline).
Defences (parameters from validation only): D1 median filter, D2 delta-V against peak plausibility plus cross-axis share, D3 adversarial training, D4 a minimum physics-based delta-V.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.ndimage import median_filter
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard import windows_cache as W
from crashguard.detector_extra import frames_full
from crashguard.models import op_thresholds

EPS_G = (0.1, 0.25, 0.5, 1.0, 2.0)
N = C.WIN_N
T = np.arange(N) / C.FS_HZ
N_ATTACK = 500  # windows per goal
N_RANDOM = 100
F_GRID = (2, 4, 6, 8, 10, 12, 15, 18, 22, 26, 30, 35, 40, 45)
PHASES = (0.0, np.pi / 2)
PATTERNS = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, -1, 0), (1, 1, 1), (1, -1, 1))
K_BANK = tuple(range(2, 46, 2))  # frequencies of the surrogate attack's sinusoid bank
MAX_BANDS = 3
PGD_STEPS = 30
RECALL_LOSS_MAX = 0.02  # defence parameters: the largest strictness whose validation recall loss is at most this (system level)


# ---------------------------------------------------------------- perturbations (arrays only)
def sinusoids(freqs: np.ndarray, phases: np.ndarray, weights: np.ndarray, dirs: np.ndarray, eps: float) -> np.ndarray:
    """delta[m] = eps * sum_j w_j sin(2 pi f_j t + phi_j) u_j. freqs, phases, weights: (m, J); dirs: (m, J, 3) with max |u| = 1; weights sum to at most 1, so max |delta| <= eps."""
    s = np.sin(2 * np.pi * freqs[:, :, None] * T[None, None, :] + phases[:, :, None])  # (m, J, N)
    return eps * np.einsum("mjn,mjc->mnc", s, weights[:, :, None] * dirs)


def random_candidates(rng: np.random.Generator, m: int, eps: float) -> np.ndarray:
    j = 3
    f = rng.uniform(2.0, 45.0, size=(m, j))
    ph = rng.uniform(0, 2 * np.pi, size=(m, j))
    n_used = rng.integers(1, j + 1, size=m)
    w = rng.dirichlet(np.ones(j), size=m)
    w = np.where(np.arange(j)[None, :] < n_used[:, None], w, 0.0)
    w = w / np.maximum(w.sum(axis=1, keepdims=True), 1e-12)
    d = rng.uniform(-1, 1, size=(m, j, 3))
    d = d / np.maximum(np.abs(d).max(axis=2, keepdims=True), 1e-12)
    return sinusoids(f, ph, w, d, eps)


def structured_candidates(eps: float) -> np.ndarray:
    fs, ps, us = [], [], []
    for f in F_GRID:
        for p in PHASES:
            for u in PATTERNS:
                fs.append([f, 0, 0]), ps.append([p, 0, 0]), us.append([u, (0, 0, 0), (0, 0, 0)])
    m = len(fs)
    w = np.zeros((m, 3))
    w[:, 0] = 1.0
    return sinusoids(np.array(fs, float), np.array(ps, float), w, np.array(us, float), eps)


def max_abs(delta: np.ndarray) -> float:
    return float(np.abs(delta).max())


# ---------------------------------------------------------------- physics helpers
def physics(acc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(maximum horizontal velocity change in km/h over the window, peak horizontal acceleration in g) of baseline-removed windows (n, N, 3). The baseline is the pre-trigger mean."""
    lin = acc[:, :, :2] - acc[:, : C.PRE_N, :2].mean(axis=1, keepdims=True)
    v = np.cumsum(lin, axis=1) * C.DT * C.G0  # m/s, rectangle rule
    v[:, 0] = 0.0
    dv = np.linalg.norm(v, axis=2).max(axis=1) * 3.6
    pk = np.linalg.norm(lin, axis=2).max(axis=1)
    return dv, pk


# ---------------------------------------------------------------- pipelines
class Pipe:
    """acc, gyro windows -> alarm. ``pre`` filters acc; ``extra`` is an optional physics rule applied together with the forest."""

    def __init__(self, name: str, forest: RandomForestClassifier, thr: float, pre=None, extra=None):
        self.name, self.forest, self.thr, self.pre, self.extra = name, forest, thr, pre, extra

    def feats(self, acc: np.ndarray, gyro: np.ndarray) -> pd.DataFrame:
        return W.features_of(self.pre(acc) if self.pre else acc, gyro)

    def score(self, acc: np.ndarray, gyro: np.ndarray) -> np.ndarray:
        return self.forest.predict_proba(self.feats(acc, gyro).to_numpy(np.float32))[:, 1]

    def alarm(self, acc: np.ndarray, gyro: np.ndarray) -> np.ndarray:
        f = self.feats(acc, gyro)
        a = self.forest.predict_proba(f.to_numpy(np.float32))[:, 1] >= self.thr
        if self.extra is not None:
            a &= self.extra(acc, f)
        return a


def fit_forest(F: pd.DataFrame, y: np.ndarray, seed: int = C.SEED) -> RandomForestClassifier:
    rf = RandomForestClassifier(n_estimators=15, max_depth=6, random_state=seed, n_jobs=-1)
    rf.fit(F.to_numpy(np.float32), y)
    rf.set_params(n_jobs=1)
    return rf


def f1_threshold(rf, F_va: pd.DataFrame, y_va: np.ndarray) -> float:
    return op_thresholds(y_va, rf.predict_proba(F_va.to_numpy(np.float32))[:, 1])[0]


# ---------------------------------------------------------------- surrogate attack (gradient)
class Surrogate:
    """Logistic regression or one-hidden-layer network on the standardised flattened accelerometer window; gives the logit and its gradient with respect to the window."""

    def __init__(self, kind: str):
        self.kind = kind

    def fit(self, acc: np.ndarray, y: np.ndarray, seed: int = C.SEED) -> Surrogate:
        X = acc.reshape(len(acc), -1)
        self.mu, self.sd = X.mean(axis=0), X.std(axis=0) + 1e-3
        Z = (X - self.mu) / self.sd
        if self.kind == "logistic":
            m = LogisticRegression(max_iter=300, C=0.05, random_state=seed).fit(Z, y)
            self.w, self.b = m.coef_[0], float(m.intercept_[0])
        else:
            m = MLPClassifier(hidden_layer_sizes=(64,), max_iter=40, early_stopping=True, random_state=seed).fit(Z, y)
            self.w1, self.b1, self.w2, self.b2 = m.coefs_[0], m.intercepts_[0], m.coefs_[1][:, 0], float(m.intercepts_[1][0])
        return self

    def logit_grad(self, acc: np.ndarray) -> np.ndarray:
        """Gradient of the logit with respect to the raw window, shape of ``acc``."""
        Z = (acc.reshape(len(acc), -1) - self.mu) / self.sd
        if self.kind == "logistic":
            g = np.broadcast_to(self.w, Z.shape)
        else:
            h = Z @ self.w1 + self.b1
            g = ((h > 0) * self.w2[None, :]) @ self.w1.T
        return (g / self.sd).reshape(acc.shape)


def bank() -> tuple[np.ndarray, np.ndarray]:
    f = np.array(K_BANK, float)
    S = np.sin(2 * np.pi * f[None, :] * T[:, None])
    Cc = np.cos(2 * np.pi * f[None, :] * T[:, None])
    return S, Cc


def gradient_attack(sur: Surrogate, acc: np.ndarray, goal_up: np.ndarray, eps: float) -> np.ndarray:
    """Projected gradient search for delta (n, N, 3) with at most MAX_BANDS frequencies from the bank and max |delta| <= eps. goal_up True = raise the logit (goal a), False = lower it (goal b)."""
    S, Cc = bank()
    n, k = len(acc), len(K_BANK)
    coef_s, coef_c = np.zeros((n, k, 3)), np.zeros((n, k, 3))
    sign = np.where(goal_up, 1.0, -1.0)[:, None, None]
    delta = np.zeros_like(acc)
    for step in range(PGD_STEPS):
        g = sur.logit_grad(acc + delta) * sign  # ascent direction on the signed logit
        gs = np.einsum("tk,ntc->nkc", S, g)
        gc = np.einsum("tk,ntc->nkc", Cc, g)
        norm = np.maximum(np.maximum(np.abs(gs).max(axis=(1, 2)), np.abs(gc).max(axis=(1, 2))), 1e-12)[:, None, None]
        lr = eps * 0.5 * (1.0 - step / PGD_STEPS)
        coef_s += lr * gs / norm
        coef_c += lr * gc / norm
        energy = (coef_s ** 2 + coef_c ** 2).sum(axis=2)  # (n, k)
        keep = np.argsort(-energy, axis=1)[:, :MAX_BANDS]
        mask = np.zeros((n, k), bool)
        np.put_along_axis(mask, keep, True, axis=1)
        coef_s, coef_c = coef_s * mask[:, :, None], coef_c * mask[:, :, None]
        delta = np.einsum("tk,nkc->ntc", S, coef_s) + np.einsum("tk,nkc->ntc", Cc, coef_c)
        peak = np.abs(delta).max(axis=(1, 2))
        scale = np.minimum(1.0, eps / np.maximum(peak, 1e-12))[:, None, None]
        coef_s, coef_c, delta = coef_s * scale, coef_c * scale, delta * scale
    return delta


# ---------------------------------------------------------------- search attacks
def search_success(pipe: Pipe, acc: np.ndarray, gyro: np.ndarray, cands: np.ndarray, want_alarm: bool) -> np.ndarray:
    """True for a window if any candidate perturbation gives the wanted decision (alarm for goal a, no alarm for goal b)."""
    ok = np.zeros(len(acc), bool)
    for c in cands:
        a = pipe.alarm(acc + c[None], gyro)
        ok |= a if want_alarm else ~a
    return ok


def asr_ci(success: np.ndarray) -> tuple[float, float, float]:
    return B.ci(success.astype(float), np.mean)


def record_net(R: pd.DataFrame | None = None) -> None:
    """Attack success NET of what the pipeline already does without an attack: for goal a, the share of windows that were NOT alarmed before and are alarmed after (among those not alarmed before);
    for goal b, the share of windows that were alarmed before and are missed after (among those alarmed before). Derived from the success rates in results/tables/x5_spoofing.csv."""
    from crashguard.results import record_many

    R = pd.read_csv(C.TABLES / "x5_spoofing.csv") if R is None else R
    ent = []
    for r_ in R[R.attack != "none"].itertuples():
        none = R[(R.goal == r_.goal) & (R.pipeline == r_.pipeline) & (R.eps == r_.eps) & (R.attack == "none")].asr.iloc[0]
        net = (r_.asr - none) / (1.0 - none) if none < 1.0 else float("nan")
        ent.append(dict(name=f"x5.net.{r_.goal}.{r_.pipeline}.eps{r_.eps:g}.{r_.attack}", value=round(float(net), 4), unit="fraction", origin="MEASURED_SOFTWARE", source_file="results/tables/x5_spoofing.csv",
                        notes="(success after attack - success without attack) / (1 - success without attack)"))
    import json

    res = {e["name"]: e["value"] for e in json.loads((C.RESULTS_PATH if hasattr(C, "RESULTS_PATH") else __import__("pathlib").Path("results/results.json")).read_text(encoding="utf-8"))}
    for pk in ("D1_median", "D2_plausibility", "D3_adversarial_training", "D4_physics_ensemble"):
        if f"x5.clean.{pk}.recall" in res:
            ent.append(dict(name=f"x5.clean_recall_loss.{pk}", value=round(float(res["x5.clean.baseline.recall"]) - float(res[f"x5.clean.{pk}.recall"]), 4), unit="fraction", origin="MEASURED_SOFTWARE",
                            source_file="results/tables/x5_spoofing.csv", notes="clean system recall of the baseline minus that of the pipeline"))
    record_many(ent, purge_prefixes=("x5.net.", "x5.clean_recall_loss."))


def main() -> None:
    from crashguard.results import record_many

    rng = np.random.default_rng(C.SEED)
    d_tr, d_va, d_te = W.load("train"), W.load("validation"), W.load("test")
    tr, va, te = frames_full()
    F_tr, F_va, F_te = (W.features_of(d["acc"], d["gyro"]) for d in (d_tr, d_va, d_te))
    y_tr, y_va, y_te = d_tr["y"], d_va["y"], d_te["y"]
    yv_full, yt_full = va.y.to_numpy(), te.y.to_numpy()
    n_pos_v = int((yv_full == 1).sum())
    ent: list[dict] = []
    src = "results/tables/x5_spoofing.csv"

    def add(name, value, unit, origin="MEASURED_SOFTWARE", notes=""):
        ent.append(dict(name=f"x5.{name}", value=value, unit=unit, origin=origin, source_file=src, notes=notes))

    # ---- pipelines
    base = fit_forest(F_tr, y_tr)
    thr0 = f1_threshold(base, F_va, y_va)
    pipes: dict[str, Pipe] = {"baseline": Pipe("baseline", base, thr0)}
    # D1 median filters: choose k on validation F1 of the clean pipeline
    d1 = {}
    for k in (3, 5):
        def flt(a, k=k):
            return median_filter(a, size=(1, k, 1), mode="nearest")
        Fk_tr = W.features_of(flt(d_tr["acc"]), d_tr["gyro"])
        rf = fit_forest(Fk_tr, y_tr)
        Fk_va = W.features_of(flt(d_va["acc"]), d_va["gyro"])
        d1[k] = (Pipe(f"D1_median{k}", rf, f1_threshold(rf, Fk_va, y_va), pre=flt), float(rf.score(Fk_va.to_numpy(np.float32), y_va)))
        add(f"d1.k{k}.val_accuracy", round(d1[k][1], 4), "fraction", notes="validation accuracy of the clean pipeline on triggered windows")
    k_best = max(d1, key=lambda k: d1[k][1])
    pipes["D1_median"] = d1[k_best][0]
    add("d1.chosen_k", k_best, "samples", notes="chosen on validation")
    # clean validation system recall helper
    def sys_recall_val(alarm_trig: np.ndarray) -> float:
        return float((alarm_trig & (y_va == 1)).sum()) / n_pos_v

    rec0 = sys_recall_val(pipes["baseline"].alarm(d_va["acc"], d_va["gyro"]))
    # D2 plausibility: ratio dv/peak and horizontal share from the training crashes
    dv_tr, pk_tr = physics(d_tr["acc"])
    ratio_tr = dv_tr / np.maximum(pk_tr, 1e-6)
    dv_va, pk_va = physics(d_va["acc"])
    ratio_va = dv_va / np.maximum(pk_va, 1e-6)
    hs_tr, hs_va = F_tr["horiz_share"].to_numpy(), F_va["horiz_share"].to_numpy()
    a0_va = pipes["baseline"].alarm(d_va["acc"], d_va["gyro"])
    chosen_q = 0.0
    for q in (0.10, 0.05, 0.02, 0.01, 0.0):
        r_min, h_min = np.quantile(ratio_tr[y_tr == 1], q), np.quantile(hs_tr[y_tr == 1], q)
        rec = sys_recall_val(a0_va & (ratio_va >= r_min) & (hs_va >= h_min))
        if rec0 - rec <= RECALL_LOSS_MAX:
            chosen_q = q
            break
    r_min, h_min = float(np.quantile(ratio_tr[y_tr == 1], chosen_q)), float(np.quantile(hs_tr[y_tr == 1], chosen_q))
    add("d2.quantile", chosen_q, "fraction", notes="quantile of the training crashes used as the lower limit; chosen on validation (recall loss at most 0.02)")
    add("d2.ratio_min_kmh_per_g", round(r_min, 4), "km/h per g")
    add("d2.horiz_share_min", round(h_min, 4), "fraction")

    def d2_rule(acc, f, r_min=r_min, h_min=h_min):
        dv, pk = physics(acc)
        return (dv / np.maximum(pk, 1e-6) >= r_min) & (f["horiz_share"].to_numpy() >= h_min)

    pipes["D2_plausibility"] = Pipe("D2_plausibility", base, thr0, extra=d2_rule)
    # D4 minimum delta-V
    dv_min = 0.0
    for cand in (8.0, 5.0, 3.0, 2.0, 1.0, 0.0):
        rec = sys_recall_val(a0_va & (dv_va >= cand))
        if rec0 - rec <= RECALL_LOSS_MAX:
            dv_min = cand
            break
    add("d4.dv_min_kmh", dv_min, "km/h", notes="chosen on validation (recall loss at most 0.02)")
    pipes["D4_physics_ensemble"] = Pipe("D4_physics_ensemble", base, thr0, extra=lambda acc, f, m=dv_min: physics(acc)[0] >= m)
    # D3 adversarial training: one best-of-search attack per training window against the baseline forest
    sub = rng.choice(len(d_tr["acc"]), size=min(8000, len(d_tr["acc"])), replace=False)
    acc_s, gy_s, y_s = d_tr["acc"][sub], d_tr["gyro"][sub], y_tr[sub]
    adv_acc = acc_s.copy()
    eps_choice = rng.choice(np.array(EPS_G[1:]), size=len(sub))
    for eps in np.unique(eps_choice):
        idx = np.flatnonzero(eps_choice == eps)
        cands = np.concatenate([structured_candidates(float(eps))[::7], random_candidates(rng, 30, float(eps))])
        best = acc_s[idx].copy()
        found = np.zeros(len(idx), bool)
        for c in cands:
            s = base.predict_proba(W.features_of(acc_s[idx] + c[None], gy_s[idx]).to_numpy(np.float32))[:, 1]
            hurt = (s >= thr0) != (y_s[idx] == 1)  # the decision became wrong
            new = hurt & ~found
            best[new] = acc_s[idx][new] + c[None]
            found |= hurt
        adv_acc[idx] = best
    F_adv = pd.concat([F_tr, W.features_of(adv_acc, gy_s)], ignore_index=True)
    y_adv = np.concatenate([y_tr, y_s])
    rf_adv = fit_forest(F_adv, y_adv)
    pipes["D3_adversarial_training"] = Pipe("D3_adversarial_training", rf_adv, f1_threshold(rf_adv, F_va, y_va))
    add("d3.n_attacked_training_windows", int(len(sub)), "windows")

    # ---- clean cost of every pipeline (system level on the de-duplicated test set)
    names = list(pipes)
    for nm, p in pipes.items():
        a = p.alarm(d_te["acc"], d_te["gyro"])
        pos = pd.Series(np.arange(len(te)), index=te.event_id.to_numpy())
        full = np.zeros(len(te), bool)
        full[pos.loc[d_te["event_id"]].to_numpy()] = a
        arr = np.stack([yt_full, full.astype(int)], 1)
        rec = B.ci(arr, lambda x: float(x[x[:, 0] == 1, 1].mean()))
        fa = B.ci(arr, lambda x: float(x[x[:, 0] == 0, 1].mean()))
        for nm2, v in (("recall", rec), ("fa", fa)):
            add(f"clean.{nm}.{nm2}", round(v[0], 4), "fraction", notes="de-duplicated test set, system level, validation threshold")
            add(f"clean.{nm}.{nm2}_lo", round(v[1], 4), "fraction")
            add(f"clean.{nm}.{nm2}_hi", round(v[2], 4), "fraction")

    # ---- attack sets (fixed random sample, seed 42)
    pos_idx = np.flatnonzero(y_te == 1)
    neg_idx = np.flatnonzero(y_te == 0)
    ia = rng.choice(neg_idx, size=min(N_ATTACK, len(neg_idx)), replace=False)  # goal a: non-crash windows
    ib = rng.choice(pos_idx, size=min(N_ATTACK, len(pos_idx)), replace=False)  # goal b: crash windows
    sets = {"a": (d_te["acc"][ia], d_te["gyro"][ia]), "b": (d_te["acc"][ib], d_te["gyro"][ib])}
    add("n_attacked.a", int(len(ia)), "windows")
    add("n_attacked.b", int(len(ib)), "windows")
    # surrogates
    sur = {k: Surrogate(k).fit(d_tr["acc"], y_tr) for k in ("logistic", "mlp")}
    rows = []
    store: dict = {}
    for goal in ("a", "b"):
        acc, gy = sets[goal]
        want_alarm = goal == "a"
        for nm, p in pipes.items():
            clean_alarm = p.alarm(acc, gy)
            clean = clean_alarm if want_alarm else ~clean_alarm  # a: already alarmed (a false alarm); b: already missed
            for eps in EPS_G:
                cands_s = structured_candidates(eps)
                cands_r = random_candidates(rng, N_RANDOM, eps)
                assert max_abs(cands_s) <= eps + 1e-9 and max_abs(cands_r) <= eps + 1e-9
                res = {"none": clean, "random": clean | search_success(p, acc, gy, cands_r, want_alarm), "structured": clean | search_success(p, acc, gy, cands_s, want_alarm)}
                for sk, sm in sur.items():
                    delta = gradient_attack(sm, acc, np.full(len(acc), want_alarm), eps)
                    assert max_abs(delta) <= eps + 1e-6
                    a = p.alarm(acc + delta, gy)
                    res[f"transfer_{sk}"] = clean | (a if want_alarm else ~a)
                res["any"] = np.logical_or.reduce([res[k] for k in res if k != "none"])
                store[(goal, nm, eps)] = res["any"]
                for ak, succ in res.items():
                    pt, lo, hi = asr_ci(succ)
                    rows.append(dict(goal=goal, pipeline=nm, eps=eps, attack=ak, asr=pt, lo=lo, hi=hi, n=len(succ)))
    R = pd.DataFrame(rows)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    R.to_csv(C.TABLES / "x5_spoofing.csv", index=False)
    for r_ in R.itertuples():
        nm = f"asr.{r_.goal}.{r_.pipeline}.eps{r_.eps:g}.{r_.attack}"
        add(nm, round(float(r_.asr), 4), "fraction", notes="share of attacked windows with the wanted decision (a: alarm, b: no alarm); 'none' = no attack")
        add(nm + "_lo", round(float(r_.lo), 4), "fraction")
        add(nm + "_hi", round(float(r_.hi), 4), "fraction")
    # paired difference against the baseline (any attack), same windows, bootstrap over windows
    for goal in ("a", "b"):
        for eps in EPS_G:
            for nm in names[1:]:
                d = B.paired_diff(store[(goal, "baseline", eps)].astype(float), store[(goal, nm, eps)].astype(float), np.mean)
                tag = f"diff.{goal}.{nm}.eps{eps:g}.any"
                add(tag, round(d[0], 4), "fraction", notes="defence minus baseline attack success (any attack), paired over the same windows")
                add(tag + "_lo", round(d[1], 4), "fraction")
                add(tag + "_hi", round(d[2], 4), "fraction")
    record_many(ent, purge_prefixes=("x5.",))
    pd.set_option("display.width", 220)
    record_net(R)
    print(R[R.attack.isin(["none", "any"])].pivot_table(index=["goal", "pipeline", "eps"], columns="attack", values="asr").round(3).to_string())


if __name__ == "__main__":
    import sys

    record_net() if "--net" in sys.argv else main()
