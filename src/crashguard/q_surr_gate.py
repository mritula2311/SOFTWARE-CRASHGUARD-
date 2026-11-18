"""P4 (SIMULATED): realism gate of the VZCrash-style surrogate (docs/02_preregistration/PREREGISTRATION_V7.md section 1.5): a discriminator on summary features, trained on REAL TRAINING windows against surrogate windows and scored on REAL VALIDATION windows
against fresh surrogate windows (point AUC at most 0.60). The other gates (marginals by KS distance, spectra, nearest-neighbour check) are the keys ``f.f2.surrogate.*`` of ``fin_f2``, produced from the same parameters, which are fitted on the TRAINING split only.

    python -m crashguard.q_surr_gate
"""
from __future__ import annotations

import json

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from crashguard import fin_surr as SU
from crashguard import windows_cache as W
from crashguard.fin_common import Entries
from crashguard.ph_gates import auc_ci


def feats(acc: np.ndarray, gyro: np.ndarray) -> np.ndarray:
    s = SU._summ(acc, gyro)
    return np.column_stack([np.log(np.maximum(s["pk"], 1e-3)), np.log1p(s["tpk"]), np.log1p(s["dec"]), s["gratio"], np.log(np.maximum(s["pre_sd"].mean(1), 1e-4)), s["base"], s["ax_share"], s["bands"]])


def main() -> None:
    par = json.load(open("results/surrogate/vzcrash_surrogate_params.json"))
    E = Entries("ph.surrogate", "src/crashguard/q_surr_gate.py")
    tr, va = W.load("train", dedup=False), W.load("validation", dedup=False)
    rng = np.random.default_rng(42)
    n_tr, n_va = min(len(tr["acc"]), 20000), min(len(va["acc"]), 10000)
    it, iv = rng.choice(len(tr["acc"]), n_tr, replace=False), rng.choice(len(va["acc"]), n_va, replace=False)
    Xr, Xv = feats(tr["acc"][it], tr["gyro"][it]), feats(va["acc"][iv], va["gyro"][iv])
    st = SU.sample(par, n_tr, 61_000)
    sv = SU.sample(par, n_va, 62_000)
    Xs, Xsv = feats(st[0], st[1]), feats(sv[0], sv[1])
    clf = HistGradientBoostingClassifier(random_state=42).fit(np.vstack([Xr, Xs]), np.r_[np.ones(n_tr), np.zeros(n_tr)])
    a, lo, hi = auc_ci(clf.predict_proba(Xv)[:, 1], clf.predict_proba(Xsv)[:, 1], n_boot=300)
    E.add("auc", a, "AUC", "SIMULATED", f"discriminator on summary features; trained on real training windows against surrogate, scored on real validation windows against fresh surrogate; 95% bootstrap interval [{lo:.3f}, {hi:.3f}]")
    E.add("auc_lo", lo, "AUC", "SIMULATED")
    E.add("auc_hi", hi, "AUC", "SIMULATED")
    E.add("passed", int(a <= 0.60), "flag", "SIMULATED", "point AUC at most 0.60 (all four surrogate gates are needed to pass: see f.f2.surrogate.features_matched and nn_copies)")
    E.add("n_real_train", n_tr, "windows", "MEASURED_SOFTWARE", "real training windows used by the discriminator")
    E.add("n_real_val", n_va, "windows", "MEASURED_SOFTWARE", "real validation windows scored (held-out)")
    E.write()
    print("surrogate AUC", round(a, 3), round(lo, 3), round(hi, 3))


if __name__ == "__main__":
    main()
