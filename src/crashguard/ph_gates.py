"""Block P integrity gates (docs/02_preregistration/PREREGISTRATION_V7.md section 1): provenance, realism (discriminator, joint tests), physical consistency, negative controls, coverage.

    python -m crashguard.ph_gates fit        # fit PH-A, PH-B and FAM on the DEVELOPMENT fold only; write the parameter files
    python -m crashguard.ph_gates gates      # run every gate on those files; write ph.* keys, tables, SYNTHETIC_PROVENANCE.md and the integrity report

Origin labels: gate numbers computed on synthetic and real data are SIMULATED (synthetic involved); hashes and record counts are MEASURED_SOFTWARE.
Held-out data for the realism gate: the REAL VALIDATION fold. The sealed test fold is never read here.
"""
from __future__ import annotations

import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import f1_score, roc_auc_score

from crashguard import fin_synth as FSY
from crashguard import ph_gen as PG
from crashguard import pp_common as PC
from crashguard import pp_feat as PF
from crashguard import severity_study as SS
from crashguard.fin_common import Entries

OUT = Path("results/synthetic")
SRC = "src/crashguard/ph_gates.py"
GENS = ("PH-A", "PH-B", "FAM")
KIND = {"PH-A": "a", "PH-B": "b"}
RG, FS = 64.0, 100.0
SEED_TRAIN, SEED_HELD, SEED_CHK = 71_000, 72_000, 73_000
AUC_MAX = 0.60
D2_DROP = {"wave"}


def real_desc() -> pd.DataFrame:
    return pd.read_parquet("data/processed/ph_real_desc.parquet")


def id_hash(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def params_path(gen: str) -> Path:
    return OUT / f"ph_params_{gen.replace('-', '').lower()}_dev.json"


# ------------------------------------------------------------------ features of one signal
def _env24(f: dict) -> np.ndarray:
    """Amplitude-normalised horizontal envelope over the pulse (trigger to pulse end of the severity rule), resampled to 24 points: independent of the record length."""
    w = f["wave"][2]
    s0 = int(round(PF.PRE_S * FS))
    e = int(min(max(s0 + round(f["pulse_ms"] * FS / 1000.0), s0 + 2), len(w) - 1))
    h = w[s0 : e + 1].astype(float)
    h = h / max(h.max(), 1e-9)
    return np.interp(np.linspace(0, len(h) - 1, 24), np.arange(len(h)), h)


def sig_features(sig: dict) -> tuple[dict, dict, float] | None:
    """D1 (descriptors at the source rate), D2 (100 Hz, +-64 g estimator features and a 24-point envelope) and the reference delta-V of one record."""
    d1 = FSY.descriptors(sig)
    if d1 is None:
        return None
    y = SS.sensor_signal(sig, RG, FS)
    f = PF.cell_from_signal(y, RG, FS)
    d2 = {k: float(v) for k, v in f.items() if k not in D2_DROP and np.isscalar(v)}
    for i, v in enumerate(_env24(f)):
        d2[f"env{i}"] = float(v)
    return d1, d2, float(d1["dv_kmh"])


def _gen_job(a):
    gen, par, mode, n, seed = a
    if gen == "FAM":
        sigs = [FSY.make_pulse(par, mode, seed + k) for k in range(n)]
        diag = None
    else:
        sigs, diag = PG.make_batch(par, mode, n, seed, KIND[gen], with_diag=True)
    rows = [sig_features(s) for s in sigs]
    chk = None
    if diag is not None:
        chk = physical_checks(diag, mode)
    return [r for r in rows if r is not None], chk, len(sigs)


def physical_checks(diag: dict, mode: str) -> dict:
    s = diag["s"]
    a = diag["clean"]
    kap, v0, e = s["kappa"], s["v0"], s["e"]
    dv_int = a.sum(1) * PG.DT * PG.G0
    dv_exp = kap * (v0 - s["u_end"])
    complete = s["u_end"] < 0.0
    e_real = np.clip(-s["u_end"] / v0, 0, None)
    en_abs = s["work"]
    en_exp = 0.5 * kap * (v0 ** 2 - s["u_end"] ** 2)
    ok = dict(
        integral=np.abs(dv_int - dv_exp) <= 0.05 * np.maximum(dv_exp, 1e-9),
        restitution=np.abs(dv_exp - kap * (1 + e) * v0) <= 0.05 * np.maximum(kap * (1 + e) * v0, 1e-9),
        energy=np.abs(en_abs - en_exp) <= 0.05 * np.maximum(0.5 * kap * v0 ** 2, 1e-9),
        crush=s["zmax"] <= PG.CRUSH_HARD_M[mode],
        closing_velocity=s["mono"] & (s["umax"] <= v0 * (1 + 1e-6)),
        complete=complete,
    )
    return {k: v.astype(int).tolist() for k, v in ok.items()} | {"e_real": e_real.tolist()}


def make_sets(gen: str, par: dict, mode: str, n: int, seed0: int, workers: int = 12, batch: int = 48):
    jobs, k, s = [], 0, seed0
    while k < n:
        m = min(batch, n - k)
        jobs.append((gen, par, mode, m, s))
        k += m
        s += 1000
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(_gen_job, jobs, chunksize=1))
    rows = [r for rr, _, _ in res for r in rr]
    chk = None
    if res and res[0][1] is not None:
        chk = {key: sum((c[key] for _, c, _ in res), []) for key in res[0][1]}
    d1 = pd.DataFrame([r[0] for r in rows])
    d2 = pd.DataFrame([r[1] for r in rows])
    ref = np.array([r[2] for r in rows])
    return d1, d2, ref, chk


def real_features(df: pd.DataFrame, idx: np.ndarray, pool) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    rows = [sig_features(pool[i]["sig"]) for i in idx]
    keep = [k for k, r in enumerate(rows) if r is not None]
    return pd.DataFrame([rows[k][0] for k in keep]), pd.DataFrame([rows[k][1] for k in keep]), np.array([rows[k][2] for k in keep])


D1_COLS = ("peak_g", "duration_ms", "dv_kmh", "asym", "shape", "noise_rel")


def d1_matrix(d1: pd.DataFrame) -> np.ndarray:
    x = d1[list(D1_COLS)].to_numpy(float).copy()
    x[:, [0, 1, 2, 5]] = np.log(np.maximum(x[:, [0, 1, 2, 5]], 1e-6))
    return x


def auc_ci(rs: np.ndarray, ss: np.ndarray, n_boot: int = 2000, seed: int = 42) -> tuple[float, float, float]:
    y = np.r_[np.ones(len(rs)), np.zeros(len(ss))]
    sc = np.r_[rs, ss]
    a = float(roc_auc_score(y, sc))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        r = rng.choice(rs, len(rs))
        s = rng.choice(ss, len(ss))
        bs.append(roc_auc_score(np.r_[np.ones(len(r)), np.zeros(len(s))], np.r_[r, s]))
    return a, float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def discriminator(real_tr: np.ndarray, syn_tr: np.ndarray, real_ho: np.ndarray, syn_ho: np.ndarray) -> tuple[float, float, float]:
    n = min(len(real_tr), len(syn_tr))
    X = np.vstack([real_tr[:n], syn_tr[:n]])
    y = np.r_[np.ones(n), np.zeros(n)]
    clf = HistGradientBoostingClassifier(random_state=42).fit(X, y)
    return auc_ci(clf.predict_proba(real_ho)[:, 1], clf.predict_proba(syn_ho)[:, 1])


def energy_p(a: np.ndarray, b: np.ndarray, mu: np.ndarray, sd: np.ndarray, n_perm: int = 300, seed: int = 42) -> tuple[float, float]:
    a, b = (a - mu) / sd, (b - mu) / sd
    b = b[: max(len(a) * 5, 50)]

    def pd_(x, y):
        return np.sqrt(((x[:, None, :] - y[None, :, :]) ** 2).sum(-1)).mean()

    def stat(x, y):
        return 2 * pd_(x, y) - pd_(x, x) - pd_(y, y)

    s0 = stat(a, b)
    z = np.vstack([a, b])
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_perm):
        p = rng.permutation(len(z))
        cnt += stat(z[p[: len(a)]], z[p[len(a):]]) >= s0
    return float(s0), float((cnt + 1) / (n_perm + 1))


def cmean_cov(x: np.ndarray):
    return x.mean(0), np.cov(x.T) + 1e-9 * np.eye(x.shape[1])


def in_range_share(d1: pd.DataFrame, mu: np.ndarray, cov: np.ndarray) -> float:
    x = np.log(np.maximum(d1[["peak_g", "duration_ms", "dv_kmh"]].to_numpy(float), 1e-6)) - mu
    d2 = np.einsum("ij,jk,ik->i", x, np.linalg.inv(cov), x)
    return float((d2 <= chi2.ppf(0.995, 3)).mean())


# ------------------------------------------------------------------ fit
def fit_all(n_sim: int = 100, maxiter: int = 150) -> None:
    from crashguard import fin_c as FC

    df = real_desc()
    dev = df[df.fold == "dev"].reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for gen in ("PH-A", "PH-B"):
        par = PG.fit(dev, KIND[gen], n_sim, maxiter)
        params_path(gen).write_text(json.dumps(par, default=float), encoding="utf-8")
        print(gen, "fitted", {m: round(par[m]["fit_cost"], 1) for m in PG.MODES if m in par}, flush=True)
    fam = FC.fit_params(dev)
    params_path("FAM").write_text(json.dumps(fam, default=float), encoding="utf-8")
    print("FAM fitted", flush=True)


# ------------------------------------------------------------------ gates
def run_gates() -> None:
    import joblib

    P = joblib.load("data/processed/pp_pool.joblib")
    pool = P["pool"]
    df = real_desc()
    E = Entries("ph", SRC)
    tables = []
    ids = np.array([r["rid"] for r in pool])
    for f in ("dev", "val", "test"):
        E.add(f"provenance.nhtsa_{f}_ids_sha256", id_hash(ids[df.fold.to_numpy() == f]), "sha256", "MEASURED_SOFTWARE", f"SHA-256 of the sorted record identifiers of the {f} fold of the pooled NHTSA records ({int((df.fold == f).sum())} records)")
    summary: dict = {}
    for gen in GENS:
        par = json.loads(params_path(gen).read_text(encoding="utf-8"))
        E.add(f"provenance.{gen}.params_sha256", hashlib.sha256(params_path(gen).read_bytes()).hexdigest(), "sha256", "MEASURED_SOFTWARE", f"parameter file {params_path(gen).name}, fitted to the development fold only")
        summary[gen] = {}
        for mode in PG.MODES:
            if mode not in par:
                continue
            n_dev, n_val = int(((df["mode"] == mode) & (df.fold == "dev")).sum()), int(((df["mode"] == mode) & (df.fold == "val")).sum())
            i_dev = np.flatnonzero(((df["mode"] == mode) & (df.fold == "dev")).to_numpy())
            i_val = np.flatnonzero(((df["mode"] == mode) & (df.fold == "val")).to_numpy())
            r1d, r2d, rrd = real_features(df, i_dev, pool)
            r1v, r2v, rrv = real_features(df, i_val, pool)
            s1t, s2t, srt, _ = make_sets(gen, par, mode, len(r1d), SEED_TRAIN)
            s1h, s2h, srh, chk = make_sets(gen, par, mode, max(5 * len(r1v), 100), SEED_HELD)
            # discriminator
            res = {}
            for name, (rt, st, rh, sh) in {"D1": (d1_matrix(r1d), d1_matrix(s1t), d1_matrix(r1v), d1_matrix(s1h)), "D2": (r2d.to_numpy(float), s2t[r2d.columns].to_numpy(float), r2v.to_numpy(float), s2h[r2d.columns].to_numpy(float))}.items():
                res[name] = discriminator(rt, st, rh, sh)
            auc_max = max(res["D1"][0], res["D2"][0])
            passed = auc_max <= AUC_MAX
            uncertain = max(res["D1"][2], res["D2"][2]) > AUC_MAX
            lx_r = np.log(np.maximum(pd.concat([r1d, r1v])[["peak_g", "duration_ms", "dv_kmh"]].to_numpy(float), 1e-6))
            mu, cov = cmean_cov(np.log(np.maximum(r1d[["peak_g", "duration_ms", "dv_kmh"]].to_numpy(float), 1e-6)))
            lx_s = np.log(np.maximum(s1h[["peak_g", "duration_ms", "dv_kmh"]].to_numpy(float), 1e-6))
            ed, ed_p = energy_p(np.log(np.maximum(r1v[["peak_g", "duration_ms", "dv_kmh"]].to_numpy(float), 1e-6)), lx_s, lx_r.mean(0), lx_r.std(0) + 1e-9)
            frob = float(np.linalg.norm(np.corrcoef(lx_r.T) - np.corrcoef(lx_s.T)))
            share_in = in_range_share(s1h, mu, cov)
            pre = f"{gen}.{mode}"
            for nm, (a, lo, hi) in res.items():
                E.add(f"gate.{pre}.auc_{nm}", a, "AUC", "SIMULATED", f"discriminator {nm}: trained on real development pulses against synthetic, scored on the real validation fold against fresh synthetic pulses; 95% bootstrap interval [{lo:.3f}, {hi:.3f}]")
                E.add(f"gate.{pre}.auc_{nm}_lo", lo, "AUC", "SIMULATED", "lower end of the 95% bootstrap interval")
                E.add(f"gate.{pre}.auc_{nm}_hi", hi, "AUC", "SIMULATED", "upper end of the 95% bootstrap interval")
            E.add(f"gate.{pre}.n_real_dev", n_dev, "records", "MEASURED_SOFTWARE", "real development rows of the mode")
            E.add(f"gate.{pre}.n_real_val", n_val, "records", "MEASURED_SOFTWARE", "real validation rows of the mode (held-out)")
            E.add(f"gate.{pre}.passed", int(passed), "flag", "SIMULATED", f"point AUC of D1 and D2 both at most {AUC_MAX}")
            E.add(f"gate.{pre}.uncertain", int(uncertain), "flag", "SIMULATED", f"the upper end of the 95% interval of D1 or D2 is above {AUC_MAX}")
            E.add(f"gate.{pre}.energy_distance", ed, "dimensionless", "SIMULATED", "energy distance of standardised log (peak, duration, delta-V), real validation against synthetic")
            E.add(f"gate.{pre}.energy_p", ed_p, "p", "SIMULATED", "permutation p-value of the energy distance (300 permutations; reported, not a gate)")
            E.add(f"gate.{pre}.corr_frobenius", frob, "dimensionless", "SIMULATED", "Frobenius norm of the difference of the correlation matrices of log (peak, duration, delta-V), real development and validation against synthetic")
            E.add(f"gate.{pre}.share_in_real_range", share_in, "fraction", "SIMULATED", "share of synthetic pulses inside the 99.5% chi-square ellipsoid of the real development log-descriptors (check vi)")
            # physical checks
            if chk is not None:
                for k in ("integral", "restitution", "energy", "crush", "closing_velocity", "complete"):
                    E.add(f"phys.{pre}.fail_{k}", 1.0 - float(np.mean(chk[k])), "fraction", "SIMULATED", "share of generated pulses failing this physical check (see PREREGISTRATION_V7 1.3)")
                allok = np.all([np.array(chk[k]).astype(bool) for k in ("integral", "restitution", "energy", "crush", "closing_velocity", "complete")], axis=0)
                E.add(f"phys.{pre}.dropped_share", 1.0 - float(allok.mean()), "fraction", "SIMULATED", "share dropped because a check failed; the pulses used for training are generated and then filtered")
            # negative controls on D2 -> class
            y_dev, y_val = PC.cls_of(rrd), PC.cls_of(rrv)
            cols = list(r2d.columns)
            clf = HistGradientBoostingClassifier(random_state=42)
            tstr = float(f1_score(y_val, clf.fit(s2t[cols].to_numpy(float), PC.cls_of(srt)).predict(r2v.to_numpy(float)), average="macro"))
            rr = float(f1_score(y_val, HistGradientBoostingClassifier(random_state=42).fit(r2d.to_numpy(float), y_dev).predict(r2v.to_numpy(float)), average="macro"))
            trts = float(f1_score(PC.cls_of(srh), HistGradientBoostingClassifier(random_state=42).fit(r2d.to_numpy(float), y_dev).predict(s2h[cols].to_numpy(float)), average="macro"))
            ysh = np.random.default_rng(42).permutation(y_dev)
            shuf = float(f1_score(y_val, HistGradientBoostingClassifier(random_state=42).fit(r2d.to_numpy(float), ysh).predict(r2v.to_numpy(float)), average="macro"))
            for nm, v, note in (("tstr_macro_f1", tstr, "train on synthetic, test on real validation rows (macro-F1 of the four delta-V classes)"), ("real_real_macro_f1", rr, "train on real development rows, test on real validation rows (reference)"),
                                ("trts_macro_f1_diagnostic", trts, "train on real, test on synthetic: DIAGNOSTIC ONLY, never a result"), ("shuffled_label_macro_f1", shuf, "labels shuffled within the real training rows; test on real validation rows: the chance-level reference")):
                E.add(f"control.{pre}.{nm}", v, "macro-F1", "MEASURED_SOFTWARE" if nm in ("real_real_macro_f1", "tstr_macro_f1", "shuffled_label_macro_f1") else "SIMULATED", note)
            summary[gen][mode] = dict(n_dev=n_dev, n_val=n_val, auc_D1=res["D1"], auc_D2=res["D2"], passed=bool(passed), uncertain=bool(uncertain), energy_p=ed_p, frob=frob, in_range=share_in, tstr=tstr, real_real=rr, shuf=shuf, trts=trts,
                                     drop=(1.0 - float(allok.mean())) if chk is not None else None, fails=({k: 1.0 - float(np.mean(chk[k])) for k in ("integral", "restitution", "energy", "crush", "closing_velocity", "complete")} if chk is not None else None))
            print(gen, mode, "AUC D1 %.3f D2 %.3f" % (res["D1"][0], res["D2"][0]), "passed" if passed else "FAILED", flush=True)
            tables.append(dict(generator=gen, mode=mode, n_real_dev=n_dev, n_real_val=n_val, auc_D1=res["D1"][0], auc_D1_lo=res["D1"][1], auc_D1_hi=res["D1"][2], auc_D2=res["D2"][0], auc_D2_lo=res["D2"][1], auc_D2_hi=res["D2"][2],
                               passed=int(passed), uncertain=int(uncertain), energy_p=ed_p, corr_frobenius=frob, share_in_range=share_in, tstr_f1=tstr, real_real_f1=rr, shuffled_f1=shuf, trts_f1=trts))
        passed_modes = [m for m in summary[gen] if summary[gen][m]["passed"]]
        cover = int(df["mode"].isin(passed_modes).sum())
        E.add(f"coverage.{gen}.modes_passed", passed_modes, "list", "SIMULATED", "modes that passed the realism gate of this generator")
        E.add(f"coverage.{gen}.share_of_real_records", cover / len(df), "fraction", "MEASURED_SOFTWARE", f"{cover} of {len(df)} pooled real records are in the modes this generator represents")
        json.dump(passed_modes, open(OUT / f"ph_modes_passed_{gen.replace('-', '').lower()}.json", "w"))
    pd.DataFrame(tables).to_csv("results/tables/ph_gates.csv", index=False)
    json.dump(summary, open(OUT / "ph_gate_summary.json", "w"), indent=1, default=float)
    E.write()
    print("gates done")


if __name__ == "__main__":
    {"fit": fit_all, "gates": run_gates}[sys.argv[1]]()
