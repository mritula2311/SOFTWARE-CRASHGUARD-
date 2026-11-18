"""F1 evaluation (EXPLORATORY-REVISED): H-F1 (original H-P1), H-F1b (original H-P2), H-F1c (original H-P3a) from the runs of ``fin_f1``. Selection of the mixing ratio and of the model uses the REAL validation rows of each run only.
Two schemes: 'sealed' (development / validation / sealed fold, labelled revised after the negative) and 'cv' (grouped, mode-stratified 5-fold nested cross-validation over all 913 real records: the main estimate).
H-F1d (original H-X6 on splits G and O) and H-F1e (original H-X5) are NOT_RUN: the 176-test split machinery was not re-implemented with synthetic training inside the folds in the available time."""
from __future__ import annotations

import pickle

import numpy as np

from crashguard import pp_common as PC
from crashguard.fin_common import Entries
from crashguard.fin_f1 import OUT, RANGES, RATIOS
from crashguard.pp_ctx import Ctx

SRC = "results/tables/f_f1.csv"
SCHEMES = {"sealed": ["sealed"], "cv": [f"cv{k}" for k in range(5)]}


def f1(y, p):
    return PC.macro_f1(y, p)


def pick(R, run, cx, rg, kinds_r):
    pass


def select(Rg: dict, run: dict, cx: Ctx) -> dict:
    va = run["va"]
    yv = cx.y[va]
    cls = PC.cls_of
    cand_base = {"a": cls(Rg["plain_va"]), "b": cls(Rg["b_va"]), "c_0": cls(Rg["c_va_0"])}
    cand_dir = {f"{k}_{r:g}": Rg[f"{k}_va_{r:g}"] for k in ("fd", "fe") for r in RATIOS}
    cand_fair = {"a": cand_base["a"], "b": cand_base["b"], **{f"c_{r:g}": cls(Rg[f"c_va_{r:g}"]) for r in RATIOS}}
    order = lambda n: (0 if n[0] == "a" else 1 if n[0] == "b" else 2, float(n.split("_")[1]) if "_" in n else 0, 0 if n.startswith("fd") else 1)  # noqa: E731

    def best(c):
        return max(c, key=lambda n: (round(f1(yv, c[n]), 9), tuple(-x for x in order(n))))

    return dict(base=best(cand_base), dir0=best({k: v for k, v in cand_dir.items() if k.endswith("_0")}), dirb=best(cand_dir), fair=best(cand_fair))


def test_pred(Rg: dict, name: str) -> np.ndarray:
    cls = PC.cls_of
    if name == "a":
        return cls(Rg["plain_te"])
    if name == "b":
        return cls(Rg["b_te"])
    if name.startswith("c_"):
        return cls(Rg[f"c_te_{name[2:]}"])
    k, r = name.split("_")
    return Rg[f"{k}_te_{r}"]


def p_of(d: np.ndarray, margin: float, above: bool) -> float:
    return PC.p_below(d, margin) if above else PC.p_above(d, margin)


def run_scheme(E: Entries, runs: dict, cx: Ctx, scheme: str, label: str) -> dict:
    names = SCHEMES[scheme]
    out = {}
    pr = []
    for rg in RANGES:
        te = np.concatenate([runs[n]["run"]["te"] for n in names])
        y, grp = cx.y[te], cx.group[te]
        G = PC.GBoot(grp)
        picks = [select(runs[n]["ranges"][rg], runs[n]["run"], cx) for n in names]
        P = {k: np.concatenate([test_pred(runs[n]["ranges"][rg], pk[k]) for n, pk in zip(names, picks)]) for k in ("base", "dir0", "dirb", "fair")}
        for k in ("base", "dir0", "dirb", "fair"):
            for mn, fn in (("macro_f1", PC.macro_f1), ("under_triage", PC.under_triage)):
                pt, lo, hi = G.ci(lambda i, k=k, fn=fn: fn(y[i], P[k][i]))
                for suf, v in (("", pt), ("_lo", lo), ("_hi", hi)):
                    E.add(f"{scheme}.r{rg:g}.{k}.{mn}{suf}", round(v, 4), "fraction", "MEASURED_SOFTWARE", f"{label}; k: base = best of plain, fill + ridge, anchored (real only); dir0 = best direct model at ratio 0; dirb = best direct model and ratio on validation; fair = best baseline with the same synthetic data")
        E.add(f"{scheme}.r{rg:g}.chosen_ratio_dirb", ",".join(sorted({p["dirb"] for p in picks})), "names", "MEASURED_SOFTWARE", "chosen model_ratio per run (validation macro-F1)")

        for tag, a, b in (("hF1", "base", "dirb"), ("control_r0", "base", "dir0"), ("fair", "fair", "dirb")):
            ptm, dm = G.stat(lambda i, a=a, b=b: PC.macro_f1(y[i], P[b][i]) - PC.macro_f1(y[i], P[a][i]))
            ptu, du = G.stat(lambda i, a=a, b=b: PC.under_triage(y[i], P[b][i]) - PC.under_triage(y[i], P[a][i]))
            s_m, s_u = PC.summ(ptm, dm), PC.summ(ptu, du)
            for nm, s in (("macro_f1_diff", s_m), ("under_triage_diff", s_u)):
                for suf, v in zip(("", "_lo", "_hi"), s):
                    E.add(f"{scheme}.r{rg:g}.{tag}.{nm}{suf}", round(float(v), 4), "fraction", "MEASURED_SOFTWARE", f"direct minus base; {label}; grouped paired bootstrap")
            ok = bool(s_m[0] >= 0.03 and s_m[1] > 0 and s_u[0] <= -0.03 and s_u[2] < 0)
            E.add(f"{scheme}.r{rg:g}.{tag}.criterion_range_met", int(ok), "flag", "MEASURED_SOFTWARE", "macro-F1 +0.03 with the interval above zero and under-triage -0.03 with the interval below zero")
            if tag == "hF1":
                pr.append((max(PC.p_below(dm, 0.0), PC.p_above(du, 0.0)), ok))
        # TSTR (train on synthetic only, test on real)
        for k in ("fd", "fe"):
            pt = np.concatenate([runs[n]["ranges"][rg][f"{k}_te_tstr" if k == "fe" else "tstr_fd_te"] for n in names])
            E.add(f"{scheme}.r{rg:g}.tstr.{k}.macro_f1", round(PC.macro_f1(y, pt), 4), "fraction", "MEASURED_SOFTWARE", "TSTR diagnostic: trained on synthetic pulses only, scored on the real test rows; never a result about real crashes")
        ct = np.concatenate([runs[n]["ranges"][rg]["tstr_c_te"] for n in names])
        ref = cx.ref[te]
        E.add(f"{scheme}.r{rg:g}.tstr.anchored.p90_abs_error_pct", round(float(np.quantile(100 * np.abs(ct - ref) / ref, 0.9)), 2), "%", "MEASURED_SOFTWARE", "TSTR diagnostic")
        out[rg] = (P, G, y, te, picks)
    ps = sorted(p for p, _ in pr)
    n_ok = sum(o for _, o in pr)
    E.add(f"{scheme}.hF1.n_ranges_met", n_ok, "ranges", "MEASURED_SOFTWARE", "ranges meeting the original H-P1 criterion")
    E.add(f"{scheme}.hF1.criterion_met", int(n_ok >= 2), "flag", "MEASURED_SOFTWARE", "original criterion: at least two of three ranges (EXPLORATORY-REVISED)")
    E.add(f"{scheme}.hF1.p_raw", round(min(1.0, 2 * ps[1]), 4), "p", "MEASURED_SOFTWARE", "2 x the second-smallest per-range p-value")
    return out


def interval_checks(E: Entries, runs: dict, cx: Ctx, scheme: str, label: str, state: dict) -> None:
    names = SCHEMES[scheme]

    for rg in (16.0,):  # H-F1b and H-F1c are stated at +-16 g, 100 Hz
        te = np.concatenate([runs[n]["run"]["te"] for n in names])
        y, grp, mode, ref = cx.y[te], cx.group[te], cx.mode[te], cx.ref[te]
        G = PC.GBoot(grp)
        lo_l, up_l, ratio_old, retained, errs, cls_c = [], [], [], [], [], []
        for n in names:
            Rg, run = runs[n]["ranges"][rg], runs[n]["run"]
            va, tt = run["va"], run["te"]
            refv = cx.ref[va]
            # ratio r chosen on validation by the p90 absolute relative error of the anchored estimate
            rbest = min(RATIOS, key=lambda r: (round(float(np.quantile(np.abs(Rg[f"c_va_{r:g}"] - refv) / refv, 0.9)), 9), r))
            cv, ct = Rg[f"c_va_{rbest:g}"], Rg[f"c_te_{rbest:g}"]
            ratio = np.sort(refv / np.maximum(cv, 1e-6))
            alpha = max(0.02, 0.10 - float((refv < cv).mean()))
            q = float(ratio[min(int(np.ceil((len(ratio) + 1) * (1 - alpha))) - 1, len(ratio) - 1)])
            lo_l.append(Rg["plain_te"])
            up_l.append(ct * q)
            fv = Rg["b_va"]
            rr = np.sort(np.abs(refv - fv) / np.maximum(fv, 1e-6))
            r90 = float(rr[min(int(np.ceil((len(rr) + 1) * 0.9)) - 1, len(rr) - 1)])
            ratio_old.append(np.full(len(tt), (1 + r90) / max(1 - r90, 0.1)))
            # reliability: ratio chosen by retained p90 error at 70% retention on validation
            def retp90(r):
                s = Rg[f"rel_va_{r:g}"]
                keep = s <= np.quantile(s, 0.70)
                return float(np.quantile(np.abs(Rg[f"c_va_{r:g}"][keep] - refv[keep]) / refv[keep], 0.9))
            rrel = min(RATIOS, key=lambda r: (round(retp90(r), 9), r))
            thr = np.quantile(Rg[f"rel_va_{rrel:g}"], 0.70)
            retained.append(Rg[f"rel_te_{rrel:g}"] <= thr)
            errs.append(100 * np.abs(Rg[f"c_te_{rrel:g}"] - cx.ref[tt]) / cx.ref[tt])
            cls_c.append(PC.cls_of(Rg[f"c_te_{rrel:g}"]))
            E.add(f"{scheme}.hF1b.{n}.ratio_chosen", rbest, "ratio", "MEASURED_SOFTWARE")
            E.add(f"{scheme}.hF1c.{n}.ratio_chosen", rrel, "ratio", "MEASURED_SOFTWARE")
        lo_, up_ = np.concatenate(lo_l), np.concatenate(up_l)
        r_old = np.concatenate(ratio_old)
        cover = ((ref >= lo_) & (ref <= up_)).astype(float)
        r_new = up_ / np.maximum(lo_, 1e-6)
        pole = mode == "pole"
        cov_pt, cov_d = G.stat(lambda i: cover[i].mean())
        pol_pt, pol_d = G.stat(lambda i: cover[i][pole[i]].mean() if pole[i].any() else np.nan)
        red_pt, red_d = G.stat(lambda i: (r_old[i].mean() - r_new[i].mean()) / r_old[i].mean())
        sc, sp, sr = PC.summ(cov_pt, cov_d), PC.summ(pol_pt, pol_d), PC.summ(red_pt, red_d)
        for nm, s in (("coverage", sc), ("coverage_pole", sp), ("width_ratio_reduction", sr)):
            for suf, v in zip(("", "_lo", "_hi"), s):
                E.add(f"{scheme}.hF1b.{nm}{suf}", round(float(v), 4), "fraction", "MEASURED_SOFTWARE", f"{label}; interval [plain, anchored x q], q on REAL validation rows; existing interval: relative residual around fill + ridge")
        E.add(f"{scheme}.hF1b.mean_ratio_new", round(float(r_new.mean()), 3), "ratio", "MEASURED_SOFTWARE")
        E.add(f"{scheme}.hF1b.mean_ratio_existing", round(float(r_old.mean()), 3), "ratio", "MEASURED_SOFTWARE")
        met_c = sc[1] >= 0.85 and (sp[1] >= 0.85 if pole.sum() >= 50 else True)
        met = bool(met_c and red_pt >= 0.20 and sr[1] > 0)
        E.add(f"{scheme}.hF1b.criterion_met", int(met), "flag", "MEASURED_SOFTWARE", "original H-P2 criterion (EXPLORATORY-REVISED)")
        E.add(f"{scheme}.hF1b.p_raw", round(float(max(PC.p_below(cov_d, 0.85), PC.p_below(pol_d[np.isfinite(pol_d)], 0.85) if pole.sum() >= 50 else 0.0, PC.p_below(red_d, 0.20))), 4), "p", "MEASURED_SOFTWARE")
        # H-F1c
        keep, err, cc = np.concatenate(retained), np.concatenate(errs), np.concatenate(cls_c)
        ut = lambda i, m_: PC.under_triage(y[i][m_[i]], cc[i][m_[i]]) if (m_[i] & (y[i] >= 2)).any() else np.nan  # noqa: E731
        allm = np.ones(len(y), bool)
        rt_pt, rt_d = G.stat(lambda i: ut(i, keep) / max(ut(i, allm), 1e-9))
        p90_pt, p90_d = G.stat(lambda i: np.quantile(err[i][keep[i]], 0.9))
        sx, sy = PC.summ(rt_pt, rt_d), PC.summ(p90_pt, p90_d)
        for nm, s in (("under_triage_ratio", sx), ("retained_p90_error_pct", sy)):
            for suf, v in zip(("", "_lo", "_hi"), s):
                E.add(f"{scheme}.hF1c.{nm}{suf}", round(float(v), 3), "ratio" if "ratio" in nm else "%", "MEASURED_SOFTWARE", f"{label}; abstain above the 70th percentile of the score on REAL validation rows")
        E.add(f"{scheme}.hF1c.retained_share", round(float(keep.mean()), 3), "fraction", "MEASURED_SOFTWARE")
        met = bool(rt_pt <= 0.5 and sx[2] < 1 and p90_pt <= 20.0)
        E.add(f"{scheme}.hF1c.criterion_met", int(met), "flag", "MEASURED_SOFTWARE", "original H-P3a criterion (EXPLORATORY-REVISED)")
        E.add(f"{scheme}.hF1c.p_raw", round(float(max(PC.p_above(rt_d, 1.0), PC.p_above(p90_d, 20.0))), 4), "p", "MEASURED_SOFTWARE")


def main() -> None:
    runs = pickle.loads(OUT.read_bytes())
    cx = Ctx()
    E = Entries("f.f1", SRC)
    for scheme, label in (("sealed", "sealed fold, scored once, revised after the negative"), ("cv", "grouped nested cross-validation over all 913 real records (main estimate)")):
        if not all(n in runs for n in SCHEMES[scheme]):
            E.add(f"{scheme}.status", "NOT_RUN: runs missing", "text", "NOT_RUN", "the cross-validation runs of fin_f1 had not finished")
            continue
        st = run_scheme(E, runs, cx, scheme, label)
        interval_checks(E, runs, cx, scheme, label, st)
    for h, why in (("hF1d", "original H-X6 on splits G and O needs the 176-test grouped-split machinery with synthetic training inside the folds; not re-implemented in the available time"),
                   ("hF1e", "original H-X5 (rank correlation of fill + ridge, 176 tests) needs the same machinery; not re-implemented in the available time")):
        E.add(f"{h}.criterion_met", "NOT_RUN", "flag", "NOT_RUN", why)
    E.add("synthetic_modes_used", "frontal_barrier,other", "modes", "SIMULATED", "modes that passed C2 (pole and side failed fidelity and are excluded)")
    E.write()


if __name__ == "__main__":
    main()
