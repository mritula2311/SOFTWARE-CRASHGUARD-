"""Study D (docs/02_preregistration/PREREGISTRATION_V2.md section 2): clip-onset early severity flag. MEASURED_SOFTWARE on 176 NHTSA crash tests (mostly high-speed barrier tests; not representative of all real crashes).
Prefix ``v2.d.``. Every flagger is a stand-alone rule with a flag time (ms after the trigger) or no flag; reference severity class from the reference delta-V and ASI of the unclipped record.

The inner grouped cross-validation of the preregistration reduces to an evaluation on the whole training set: the rules have no fitted parameters other than the grid pair, so pooling inner validation folds is
the same as scoring every training test once (recorded in docs/07_log/DECISIONS.md).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation_splits as SP
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard import ua_core as U
from crashguard.v2_a_study import gdraws, pval_le
from crashguard.v2_common import Entries

RANGES = SP.RANGES
RATES = (100, 200)
QS = (0.7, 0.8, 0.9, 0.98)
T_ON = tuple(range(10, 310, 10))
T_PK = (50, 100, 150, 200, 300)
G_PK = (2.0, 3.0, 4.0, 6.0, 8.0, 12.0)
SEVERE_LIMIT_KMH = 40.0
INNER_OVER = 0.05
PARAMS = SP.sp_params(0.1)
SRC = "results/tables/v2_d_metrics.csv"
INF = float("inf")


def features(tests: list[dict], rg: float, fs: int) -> dict:
    n = len(tests)
    out = dict(pulse_ms=np.zeros(n), onset={q: np.full(n, INF) for q in QS}, rise={q: np.zeros(n) for q in QS}, t_run=np.full(n, INF), peak={T: np.zeros(n) for T in T_PK}, clips=np.zeros(n, bool))
    dt = 1.0 / fs
    for i, t in enumerate(tests):
        y = SS.sensor_signal(t["sig"], rg, float(fs))
        w, trig = SS._window(y, float(fs))
        a = S.remove_baseline(w, trig)
        h = np.hypot(a[:, 0], a[:, 1])
        e = S.pulse_end(h, trig, float(fs), PARAMS)
        out["pulse_ms"][i] = (e - trig) * dt * 1000.0
        raw = np.maximum(np.abs(w[:, 0]), np.abs(w[:, 1]))
        for q in QS:
            hit = np.flatnonzero(raw[trig : e + 1] >= q * rg)
            if len(hit):
                j = int(hit[0])
                out["onset"][q][i] = j * dt * 1000.0
                k0 = max(j - 3, 0)
                out["rise"][q][i] = (h[trig + j] - h[trig + k0]) / max((j - k0) * dt, dt)
        out["clips"][i] = bool((raw[trig : e + 1] >= SP_CLIP * rg).any())
        if e > trig:
            v = S.trapz_cumulative(a[trig : e + 1, :2] * C.G0, dt)
            res = np.hypot(v[:, 0], v[:, 1]) * 3.6
            hit = np.flatnonzero(res >= SEVERE_LIMIT_KMH)
            if len(hit):
                out["t_run"][i] = float(hit[0]) * dt * 1000.0
        for T in T_PK:
            m = int(round(T * fs / 1000.0))
            out["peak"][T][i] = float(h[trig : trig + m + 1].max())
    return out


SP_CLIP = 0.7


def pick_onset(fe: dict, tr: np.ndarray, sev: np.ndarray) -> tuple[float, int]:
    cands = []
    nsev, nnon = max(int((tr & sev).sum()), 1), max(int((tr & ~sev).sum()), 1)
    for q in QS:
        on = fe["onset"][q]
        for T in T_ON:
            fl = on <= T
            det = float((fl & tr & sev).sum()) / nsev
            ov = float((fl & tr & ~sev).sum()) / nnon
            cands.append((q, T, det, ov))
    ok = [c for c in cands if c[3] <= INNER_OVER]
    if ok:
        best = sorted(ok, key=lambda c: (-c[2], c[1], -c[0]))[0]
    else:
        best = sorted(cands, key=lambda c: (c[3], -c[2], c[1], -c[0]))[0]
    return best[0], int(best[1])


def pick_peak(fe: dict, tr: np.ndarray, sev: np.ndarray, rg: float) -> tuple[int, float]:
    cands = []
    nsev, nnon = max(int((tr & sev).sum()), 1), max(int((tr & ~sev).sum()), 1)
    for T in T_PK:
        for g in G_PK:
            if g >= rg:
                continue
            fl = fe["peak"][T] >= g
            cands.append((T, g, float((fl & tr & sev).sum()) / nsev, float((fl & tr & ~sev).sum()) / nnon))
    ok = [c for c in cands if c[3] <= INNER_OVER]
    if ok:
        best = sorted(ok, key=lambda c: (-c[2], c[0], -c[1]))[0]
    elif cands:
        best = sorted(cands, key=lambda c: (c[3], -c[2], c[0], -c[1]))[0]
    else:
        return T_PK[0], INF
    return int(best[0]), float(best[1])


def main() -> None:
    tests = SS.load_tests()
    meta = SP.meta_of(tests)
    n = len(meta)
    gmm = meta.group_mm.to_numpy()
    core = U.build()
    refc = U.ref_classes(core)
    sev = refc >= 2
    cls_full = {rg: U.point_classes(core, rg) for rg in RANGES}  # (5 repeats, n), -1 outside the test rows
    ent = Entries("v2.d", SRC, "MEASURED_SOFTWARE")
    held_G = np.array([t["role"] == "heldout" for t in tests])
    held_O, held_A = SP.split_O(meta), SP.split_by(meta, "group_mm")
    ug = sorted(set(gmm.tolist()))
    REP, NF = SP.N_REPEATS, SP.N_FOLDS
    rows = []
    pvals: dict[str, float] = {}
    ent.add("n_severe_or_critical", int(sev.sum()), "tests", "reference class 2 or 3")
    ent.add("n_nonsevere", int((~sev).sum()), "tests")
    for fs in RATES:
        for rg in RANGES:
            fe = features(tests, rg, fs)
            tag = f"r{rg:g}.f{fs}"
            ent.add(f"{tag}.share_never_clip", round(float((~fe["clips"]).mean()), 4), "fraction", "tests with no sample at 0.7 of the range inside the pulse (no early flag possible)")
            ent.add(f"{tag}.share_never_clip_severe", round(float((~fe["clips"][sev]).mean()), 4), "fraction", "among reference Severe or Critical tests")
            # flag arrays per split: per test (n,) mean over repeats of flagged, and time saved
            res = {}
            for sp in ("R", "G", "A", "O"):
                if sp == "R":
                    flag = {k: np.zeros((REP, n)) for k in ("D2", "PK")}
                    tflag = {k: np.full((REP, n), np.nan) for k in ("D2", "PK")}
                    chosen = []
                    for rep in range(REP):
                        rng_ = np.random.default_rng(C.SEED + rep)
                        order = list(rng_.permutation(len(ug)))
                        fold_of = {ug[j]: k % NF for k, j in enumerate(order)}
                        fold = np.array([fold_of[g] for g in gmm])
                        for f in range(NF):
                            te, tr = fold == f, fold != f
                            q, T = pick_onset(fe, tr, sev)
                            Tp, Gp = pick_peak(fe, tr, sev, rg)
                            chosen.append((q, T, Tp, Gp))
                            on = fe["onset"][q]
                            flag["D2"][rep, te] = (on <= T)[te]
                            tflag["D2"][rep, te] = np.where(on <= T, on, np.nan)[te]
                            pk = fe["peak"][Tp] >= Gp
                            flag["PK"][rep, te] = pk[te]
                            tflag["PK"][rep, te] = np.where(pk, float(Tp), np.nan)[te]
                    res[sp] = dict(flag={k: v.mean(0) for k, v in flag.items()}, tflag={k: np.nanmean(np.where(np.isnan(v), np.nan, v), axis=0) if np.isfinite(v).any() else np.full(n, np.nan) for k, v in tflag.items()},
                                   groups=gmm, held=np.ones(n, bool), chosen=chosen)
                else:
                    held = {"G": held_G, "A": held_A, "O": held_O}[sp]
                    q, T = pick_onset(fe, ~held, sev)
                    Tp, Gp = pick_peak(fe, ~held, sev, rg)
                    on = fe["onset"][q]
                    res[sp] = dict(flag=dict(D2=(on <= T).astype(float), PK=(fe["peak"][Tp] >= Gp).astype(float)), tflag=dict(D2=np.where(on <= T, on, np.nan), PK=np.where(fe["peak"][Tp] >= Gp, float(Tp), np.nan)),
                                   groups=gmm, held=held, chosen=[(q, T, Tp, Gp)])
                r_ = res[sp]
                held = r_["held"]
                # comparator (ii): running plain delta-V reaches the Severe limit; (i): full-pulse class of the earlier estimator
                ii_flag = np.isfinite(fe["t_run"]).astype(float)
                ii_t = np.where(np.isfinite(fe["t_run"]), fe["t_run"], np.nan)
                cf = cls_full[rg]
                i_flag = np.array([float(np.mean((cf[:, j][cf[:, j] >= 0] >= 2))) if (cf[:, j] >= 0).any() else np.nan for j in range(n)])
                full_t = fe["pulse_ms"]
                rules = {"D2": (r_["flag"]["D2"], r_["tflag"]["D2"]), "PK": (r_["flag"]["PK"], r_["tflag"]["PK"]), "II": (ii_flag, ii_t), "I": (i_flag, full_t.copy())}
                for rn, (fl, tf) in rules.items():
                    s_h, n_h = held & sev, held & ~sev
                    det = fl[s_h]
                    ov = fl[n_h]
                    tsave = np.where(np.isfinite(tf), full_t - tf, np.nan)
                    gh = gmm
                    _pt, dr = gdraws(gh[s_h], lambda i, a=det: float(np.nanmean(a[i])))
                    ent.ci(f"{sp}.{tag}.{rn}.detection", (float(np.nanmean(det)), float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "fraction", "reference Severe or Critical tests flagged (1 minus under-triage)", d=4)
                    _pt, dr = gdraws(gh[n_h], lambda i, a=ov: float(np.nanmean(a[i])))
                    ent.ci(f"{sp}.{tag}.{rn}.over_triage", (float(np.nanmean(ov)), float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "fraction", "reference Low or Moderate tests flagged", d=4)
                    tp = det > 0
                    ts = np.where(tp, tsave[s_h], np.nan)
                    if np.isfinite(ts).any():
                        _pt, dr = gdraws(gh[s_h], lambda i, a=ts: float(np.nanmedian(a[i])) if np.isfinite(a[i]).any() else np.nan)
                        ent.ci(f"{sp}.{tag}.{rn}.median_time_saved_ms", (float(np.nanmedian(ts)), float(np.nanquantile(dr, 0.025)), float(np.nanquantile(dr, 0.975))), "ms", "full-pulse decision time minus flag time, flagged Severe or Critical tests", d=1)
                    rows.append(dict(split=sp, range_g=rg, fs=fs, rule=rn, detection=float(np.nanmean(det)), over_triage=float(np.nanmean(ov)), median_saved_ms=float(np.nanmedian(ts)) if np.isfinite(ts).any() else np.nan))
                # paired difference of under-triage: D2 minus II and D2 minus I
                s_h = held & sev
                for other, (fo, _t) in (("II", rules["II"]), ("I", rules["I"])):
                    a = (1.0 - r_["flag"]["D2"])[s_h]
                    b = (1.0 - fo)[s_h]
                    pt, dr = gdraws(gmm[s_h], lambda i, a=a, b=b: float(np.nanmean(a[i] - b[i])))
                    ent.ci(f"{sp}.{tag}.under_triage_D2_minus_{other}", (pt, float(np.quantile(dr, 0.025)), float(np.quantile(dr, 0.975))), "fraction", "positive = the clip-onset flag misses more Severe or Critical tests", d=4)
                if sp == "R":
                    ch = pd.DataFrame(r_["chosen"], columns=["q", "T_on", "T_pk", "G_pk"])
                    ent.add(f"{sp}.{tag}.chosen_q_mode", float(ch.q.mode().iloc[0]), "share of range")
                    ent.add(f"{sp}.{tag}.chosen_T_on_median", float(ch.T_on.median()), "ms")
            # hypotheses at the primary cell
            if rg == 16.0 and fs == 100:
                r_ = res["R"]
                det = r_["flag"]["D2"]
                s_h, n_h = sev, ~sev
                tsave = np.where(np.isfinite(r_["tflag"]["D2"]), fe["pulse_ms"] - r_["tflag"]["D2"], np.nan)
                ts = np.where(det > 0, tsave, np.nan)[s_h]
                med = lambda i: float(np.nanmedian(ts[i])) if np.isfinite(ts[i]).any() else np.nan  # noqa: E731
                pt, dr = gdraws(gmm[s_h], med)
                ent.add("hD1.median_time_saved_ms", round(pt, 1), "ms", "primary cell: +-16 g, 100 Hz, split R")
                ent.add("hD1.median_time_saved_ms_lo", round(float(np.nanquantile(dr, 0.025)), 1), "ms")
                ent.add("hD1.median_time_saved_ms_hi", round(float(np.nanquantile(dr, 0.975)), 1), "ms")
                p_time = float(max(np.nanmean(dr < 100.0), 1.0 / (len(dr) + 1)))
                a_ = (1.0 - r_["flag"]["D2"])[s_h]
                b_ = (1.0 - np.isfinite(fe["t_run"]).astype(float))[s_h]
                ptu, dru = gdraws(gmm[s_h], lambda i: float(np.nanmean(a_[i] - b_[i])))
                lo_u = float(np.quantile(dru, 0.025))
                ent.ci("hD1.under_triage_D2_minus_analogue", (ptu, lo_u, float(np.quantile(dru, 0.975))), "fraction", "positive = D2 misses more than the running-integral analogue", d=4)
                not_worse = not (lo_u > 0.0)
                ent.add("hD1.p_raw", round(p_time, 4), "probability", "median time saved below 100 ms")
                ent.add("hD1.criterion_met", int(pt >= 100.0 and float(np.nanquantile(dr, 0.025)) >= 100.0 and not_worse), "flag", "median saved at least 100 ms with the lower interval end at least 100, and the under-triage interval not entirely above zero")
                pvals["H-D1"] = p_time
                ov = r_["flag"]["D2"][n_h]
                pto, dro = gdraws(gmm[n_h], lambda i: float(np.nanmean(ov[i])))
                ent.ci("hD2.over_triage", (pto, float(np.quantile(dro, 0.025)), float(np.quantile(dro, 0.975))), "fraction", "primary cell, split R", d=4)
                p_ov = pval_le(-dro, -0.10)
                p_ov = float(max(np.mean(dro >= 0.10), 1.0 / (len(dro) + 1)))
                ent.add("hD2.p_raw", round(p_ov, 4), "probability", "over-triage at or above 0.10")
                ent.add("hD2.criterion_met", int(pto < 0.10), "flag", "point over-triage below 0.10 on split R")
                pvals["H-D2"] = p_ov
    ent.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "v2_d_metrics.csv", index=False)
    pd.DataFrame([dict(h=k, p=v) for k, v in pvals.items()]).to_csv(C.TABLES / "v2_d_pvalues.csv", index=False)
    d = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(d[(d.split == "R")].round(3).to_string())
    print(pvals)


if __name__ == "__main__":
    B.N_BOOT
    main()
