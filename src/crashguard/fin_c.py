"""Block C: synthetic stress-test pulses (SIMULATED; docs/02_preregistration/PREREGISTRATION_V5.md section C; assumptions in docs/05_data_code/SYNTHETIC_ASSUMPTIONS.md). C1 generator and fixed file, C2 fidelity, C3 use (N13 sensor-range grid) and the
assumption-dependent extension. Every figure and table from synthetic pulses: 'synthetic stress test, assumptions in SYNTHETIC_ASSUMPTIONS.md'."""
from __future__ import annotations

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from crashguard import boot as B
from crashguard import fin_synth as G
from crashguard import pp_b2 as B2
from crashguard import severity_study as SS
from crashguard.fin_common import Entries
from crashguard.sel_parts import PARTS

OUT = Path("results/synthetic")
SRC = "src/crashguard/fin_c.py"
CAPTION = "synthetic stress test, assumptions in SYNTHETIC_ASSUMPTIONS.md"
N_FID, N_GRID, N_SENS = 1000, 1000, 300
D_MAX = 0.20
SEED0_FIXED, SEED0_FID, SEED0_GRID, SEED0_SENS = 42, 500_000, 100_000, 200_000
VARIANTS = {"base": {}, "shift0.2": dict(shift=0.2), "shift0.4": dict(shift=0.4), "shift0.6": dict(shift=0.6), "fam_halfsine_heavy": dict(fam_p=(0.5, 0.25, 0.25)), "fam_multipeak_heavy": dict(fam_p=(0.25, 0.25, 0.5)),
            "dur-20%": dict(dur_scale=0.8), "dur+20%": dict(dur_scale=1.2), "rho-0.2": dict(rho_shift=-0.2), "rho+0.2": dict(rho_shift=0.2), "noise_x0.5": dict(noise_scale=0.5), "noise_x2": dict(noise_scale=2.0), "pre0.05": dict(pre_s=0.05)}
_W: dict = {}


def real_desc() -> pd.DataFrame:
    """Descriptors of the 913 real pooled pulses (built once from ``pp_pool.joblib``)."""
    f = Path("data/processed/f_real_desc.parquet")
    if not f.exists():
        import joblib

        P = joblib.load("data/processed/pp_pool.joblib")
        df = pd.DataFrame([G.descriptors(r["sig"], r["ref"]) or {} for r in P["pool"]])
        df["mode"] = [r["mode"] for r in P["pool"]]
        df["fold"] = P["fold"]
        df.to_parquet(f)
    return pd.read_parquet(f)


def fit_params(df: pd.DataFrame, calibrate: bool = True) -> dict:
    par = G.fit(df.to_dict("records"), df["mode"].tolist())
    return G.calibrate(par) if calibrate else par


def _init(par):
    _W["par"] = par
    _W["cfgs"] = B2.configs()
    _W["parts"] = {p.key: p for p in PARTS}


def _grid_job(a):
    from crashguard import sel_study as SEL

    mode, seed, ovr = a
    sig = G.make_pulse(_W["par"], mode, seed, ovr)
    ref = SS.reference_dv(sig)[0]
    err = []
    for k, rg, odr in _W["cfgs"]:
        dv = SEL.part_dv(sig, _W["parts"][k], rg, odr, 42 + seed % 1000, True)
        err.append(100.0 * abs(dv - ref) / max(ref, 1e-9))
    return mode, np.array(err) <= B2.TOL


def grid(par: dict, modes: list[str], n: int, seed0: int, ovr: dict | None, workers: int = 12) -> dict:
    jobs = [(m, seed0 + k, ovr) for m in modes for k in range(n)]
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(par,)) as ex:
        res = list(ex.map(_grid_job, jobs, chunksize=4))
    out = {}
    cfgs = B2.configs()
    for m in modes:
        F = np.stack([f for mm, f in res if mm == m]).astype(float)
        rng = np.random.default_rng(42)
        idx = rng.integers(0, len(F), (B.N_BOOT, len(F)))
        boot = np.stack([F[i].mean(0) for i in idx])
        lo = np.quantile(boot, 0.025, axis=0)
        out[m] = pd.DataFrame([dict(part=k, range_g=rg, odr_hz=odr, share=float(F[:, c].mean()), lo=float(lo[c])) for c, (k, rg, odr) in enumerate(cfgs)])
    return out


def smallest(tab: pd.DataFrame):
    ok = tab[tab.lo >= 0.80].sort_values(["range_g", "odr_hz", "part"])
    return None if ok.empty else (float(ok.iloc[0].range_g), ok.iloc[0].part, int(ok.iloc[0].odr_hz))


def ladder() -> list[float]:
    return sorted({float(r) for p in PARTS for r in p.study_ranges})


def real_smallest(mode: str, R: dict):
    v = R.get(f"p.b2.{mode}.smallest.config")
    if not v or v == "NOT_RUN":
        return None
    return float(v.split("+-")[1].split(" g")[0])


def fidelity(par: dict, df: pd.DataFrame, E: Entries) -> list[str]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    passed = []
    fig, axs = plt.subplots(len(G.MODES), len(G.DESC), figsize=(16, 10))
    labels = {"peak_g": "peak resultant (g)", "duration_ms": "duration at 10% of peak (ms)", "dv_kmh": "delta-V (km/h)", "asym": "time of peak / duration (1)", "shape": "area / (peak x duration) (1)"}
    for i, m in enumerate(G.MODES):
        S = pd.DataFrame([s for s in (G.descriptors(G.make_pulse(par, m, SEED0_FID + k)) for k in range(N_FID)) if s])
        real = df[df["mode"] == m]
        ok = True
        for j, d in enumerate(G.DESC):
            ks = ks_2samp(real[d], S[d])
            E.add(f"fidelity.{m}.{d}.ks_D", round(float(ks.statistic), 4), "statistic", "SIMULATED", f"two-sample KS, real n={len(real)} against synthetic n={len(S)} ({CAPTION}); in-sample fit")
            E.add(f"fidelity.{m}.{d}.ks_p", float(ks.pvalue), "p", "SIMULATED", "reported, not used for the decision")
            E.add(f"fidelity.{m}.{d}.real_median", round(float(real[d].median()), 4), "", "MEASURED_SOFTWARE", "real pooled NHTSA records of the mode")
            E.add(f"fidelity.{m}.{d}.synthetic_median", round(float(S[d].median()), 4), "", "SIMULATED", CAPTION)
            ok &= bool(ks.statistic <= D_MAX)
            ax = axs[i, j]
            for x, lab, c in ((np.sort(real[d]), "real", "#0072B2"), (np.sort(S[d]), "synthetic", "#D55E00")):
                ax.step(x, np.arange(1, len(x) + 1) / len(x), where="post", label=lab, color=c)
            ax.set_xlabel(labels[d], fontsize=8)
            ax.set_ylabel(f"{m}: ECDF" if j == 0 else "ECDF", fontsize=8)
            ax.set_title(f"KS D = {ks.statistic:.2f}", fontsize=8)
            if i == 0 and j == 0:
                ax.legend(fontsize=7)
        E.add(f"fidelity.{m}.passes", int(ok), "flag", "SIMULATED", f"all five KS statistics at most {D_MAX}")
        if ok:
            passed.append(m)
    fig.suptitle(f"Real against synthetic pulse descriptors per mode ({CAPTION})", fontsize=10)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"c_fig_fidelity.{ext}", dpi=300)
    plt.close(fig)
    return passed


def fixed_file(par: dict, df: pd.DataFrame) -> None:
    n = len(df)
    cnt = {m: int(round(5000 * (df["mode"] == m).sum() / n)) for m in G.MODES}
    cnt["pole"] += 5000 - sum(cnt.values())
    rows, wav = [], []
    k = 0
    for m in G.MODES:
        for _ in range(cnt[m]):
            sig = G.make_pulse(par, m, SEED0_FIXED + k)
            d = G.descriptors(sig) or {}
            rows.append(dict(k=k, seed=SEED0_FIXED + k, mode=m, family=sig["family"], **{c: d.get(c) for c in G.DESC}, ux=d.get("ux"), uy=d.get("uy")))
            wav.append(sig["acc"][::5, :2].astype(np.float16))  # 10 kHz to 2 kHz by taking every fifth sample (not filtered); for plots and checks
            k += 1
    pd.DataFrame(rows).to_csv(OUT / "synthetic_pulses_5000_params.csv", index=False)
    Path("release/synthetic_pulses").mkdir(parents=True, exist_ok=True)
    np.savez_compressed("release/synthetic_pulses/synthetic_pulses_5000_2kHz.npz", acc_xy_g=np.stack(wav), fs_hz=2000.0, note=CAPTION)


def main() -> None:
    R = {e["name"]: e["value"] for e in json.loads(open("results/results.json", encoding="utf-8").read())}
    OUT.mkdir(parents=True, exist_ok=True)
    df = real_desc()
    par = fit_params(df)
    json.dump(par, open(OUT / "generator_params_all913.json", "w"), indent=1)
    E = Entries("f.c", SRC)
    E.add("generator.n_records_fit", int(len(df)), "records", "MEASURED_SOFTWARE", "all 913 pooled NHTSA records (C-block fit; in-sample)")
    passed = fidelity(par, df, E)
    E.add("fidelity.modes_passed", ",".join(passed) or "none", "modes", "SIMULATED", CAPTION)
    json.dump(passed, open(OUT / "modes_passed.json", "w"))
    fixed_file(par, df)
    E.add("fixed_file.n", 5000, "pulses", "SIMULATED", "results/synthetic/synthetic_pulses_5000_params.csv (+ release/synthetic_pulses/*.npz); regenerated exactly by fin_synth.make_pulse with seeds 42 + k")
    lad = ladder()
    E.add("ladder", ",".join(f"{x:g}" for x in lad), "g", "ANALYTICAL", "sorted union of study ranges of the eight parts (one rung = one range step)")
    hc3 = {}
    if passed:
        T = grid(par, passed, N_GRID, SEED0_GRID, None)
        for m in passed:
            T[m].to_csv(OUT / f"c_grid_{m}.csv", index=False)
            s = smallest(T[m])
            rs = real_smallest(m, R)
            E.add(f"grid.{m}.synthetic_smallest_range", s[0] if s else "NOT_RUN", "g", "SIMULATED" if s else "NOT_RUN", f"smallest range with lower interval end >= 0.80 (1,000 synthetic pulses; {CAPTION})")
            if s:
                E.add(f"grid.{m}.synthetic_smallest_config", f"{s[1]} +-{s[0]:g} g at {s[2]} Hz", "config", "SIMULATED", CAPTION)
            E.add(f"grid.{m}.real_smallest_range", rs if rs else "NOT_RUN", "g", "MEASURED_SOFTWARE" if rs else "NOT_RUN", "p.b2.* of the positive-results push")
            if s and rs:
                step = abs(lad.index(s[0]) - lad.index(rs))
                E.add(f"grid.{m}.step_difference", step, "rungs", "SIMULATED", "difference on the ladder of ranges")
                hc3[m] = step
        overlap = [m for m in ("frontal_barrier", "pole") if m in passed]
        E.add("hC3.overlapping_modes_passed", ",".join(overlap) or "none", "modes", "SIMULATED")
        if overlap and all(m in hc3 for m in overlap):
            met = all(hc3[m] <= 1 for m in overlap)
            E.add("hC3.criterion_met", int(met), "flag", "SIMULATED", "smallest synthetic range within one range step of the real result for every overlapping mode that passed fidelity")
            E.add("hC3.p_raw", 0.001 if met else 1.0, "p", "SIMULATED", "preregistered convention for an agreement criterion")
        else:
            E.add("hC3.criterion_met", "NOT_RUN", "flag", "NOT_RUN", "no overlapping mode passed fidelity, or the real or synthetic result is missing")
        for name, ovr in VARIANTS.items():
            Tv = grid(par, passed, N_SENS, SEED0_SENS, ovr)
            for m in passed:
                s = smallest(Tv[m])
                E.add(f"sens.{name}.{m}.smallest_range", s[0] if s else "NOT_RUN", "g", "SIMULATED" if s else "NOT_RUN", f"EXPLORATORY, assumption-dependent; 300 pulses per mode; {CAPTION}")
            print(name, {m: smallest(Tv[m]) for m in passed}, flush=True)
    else:
        E.add("hC3.criterion_met", "NOT_RUN", "flag", "NOT_RUN", "no mode passed fidelity")
    E.write()
    print("passed", passed, hc3)


if __name__ == "__main__":
    main()
