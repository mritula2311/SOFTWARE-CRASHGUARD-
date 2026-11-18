"""X5 (docs/02_preregistration/PREREGISTRATION_V3.md): does a clipped sensor still rank severity correctly? MEASURED_SOFTWARE on 176 NHTSA tests (mostly high-speed barrier tests; the sensor is a software model).

Spearman correlation of each severity measure with the reference delta-V, class agreement with the classes of the reference delta-V, and (EXPLORATORY) the correlation of each measure with the dummy
injury criteria recorded in the NHTSA metadata. Fitted estimators (fill + ridge, tail-aware) use the out-of-fold predictions of split R (``x_common.oof``); correlations are computed per repeat and averaged. Intervals resample make/model groups.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from crashguard import boot as B
from crashguard import config as C
from crashguard import nhtsa as N
from crashguard import saturation_splits as SPL
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard import spline_restore as SR
from crashguard.jp_common import Entries
from crashguard.x_common import oof

RANGES = (16.0, 32.0, 64.0)
RATES = (100, 200)
SRC = "results/tables/x5_rank.csv"
LIMITS = np.array(C.SEV_DV_KMH)
CRITERIA = {"frontal": ("HIC", "CLIP3M"), "side": ("TTI", "PELVG")}
REF_RHO_MIN = 0.2  # a criterion whose reference correlation is below this is dropped (preregistration)
N_BOOT = B.N_BOOT


def rho(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman correlation along the last axis (ties: average ranks); x may have a leading repeat axis."""
    rx, ry = rankdata(x, axis=-1), rankdata(y, axis=-1)
    rx = rx - rx.mean(-1, keepdims=True)
    ry = ry - ry.mean(-1, keepdims=True)
    return (rx * ry).sum(-1) / np.sqrt((rx * rx).sum(-1) * (ry * ry).sum(-1) + 1e-300)


def kappa_lin(a: np.ndarray, b: np.ndarray, k: int = 4) -> float:
    m = np.zeros((k, k))
    np.add.at(m, (a, b), 1)
    w = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    e = np.outer(m.sum(1), m.sum(0)) / m.sum()
    den = (w * e).sum()
    return float(1 - (w * m).sum() / den) if den > 0 else float("nan")


def draws(groups: np.ndarray, n_boot: int = N_BOOT, seed: int = B.SEED) -> list[np.ndarray]:
    return list(B._gidx(B.group_members(groups), n_boot, seed))


def boot(fn, n: int, D: list[np.ndarray]) -> tuple[float, float, float, np.ndarray]:
    """fn(idx) -> float. Returns (point, lo, hi, draws)."""
    pt = float(fn(np.arange(n)))
    d = np.array([fn(i) for i in D], dtype=float)
    return pt, float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975)), d


def sensor_measures(tests: list[dict]) -> dict:
    """Direct (not fitted) measures at every range and rate: plain, spline, ASI, direction-adjusted plain delta-V, and the plain pieces."""
    out: dict = {}
    pp = SPL.sp_params(SPL.RF0)
    for rg in RANGES:
        for hz in RATES:
            plain, spl, asi, dirv = [], [], [], []
            for t in tests:
                y = SS.sensor_signal(t["sig"], rg, float(hz))
                w, trig = SS._window(y, float(hz))
                r = S.severity(w, float(hz), trig, None, pp)
                plain.append(r["dv_res_kmh"])
                asi.append(r["asi"])
                dirv.append(abs(r["dvx_kmh"]) if t["kind"] == "frontal" else abs(r["dvy_kmh"]))
                spl.append(SR.severity_restored(w, float(hz), trig, rg, 0.5, pp)[0]["dv_res_kmh"])
            out[(rg, hz)] = dict(plain=np.array(plain), spline=np.array(spl), asi=np.array(asi), dirplain=np.array(dirv))
    return out


def criteria_table(tests: list[dict]) -> pd.DataFrame:
    """Driver-seat dummy criteria of the vehicle that was measured (frontal: the moving vehicle; side: the struck vehicle). Values of 0 or 9,000 and above count as missing."""
    rows = []
    for t in tests:
        m = json.loads((N.RAW / f"meta_{t['test_no']}.json").read_text(encoding="utf-8"))
        side = t["kind"] == "side"
        vnos = {v["VEHNO"] for v in m.get("VEHICLE", []) if ((v.get("VEHSPD") or 0) == 0) == side and not any(w in f"{v.get('MAKED', '')} {v.get('MODELD', '')}".upper() for w in N.NOT_VEHICLE)}
        r = {c: np.nan for c in ("HIC", "CLIP3M", "TTI", "PELVG")}
        for o in m.get("OCCUPANT", []):
            if o.get("OCCLOC") == "01" and o.get("VEHNO") in vnos:
                for c in r:
                    v = o.get(c)
                    if v is not None and 0 < float(v) < 9000:
                        r[c] = float(v)
                break
        rows.append(dict(test_no=t["test_no"], kind=t["kind"], **r))
    return pd.DataFrame(rows)


def main() -> None:
    OO = oof()
    tests = SS.load_tests()
    n = OO["n"]
    ref, gmm = OO["ref"], OO["gmm"]
    kinds = np.array([t["kind"] for t in tests])
    REP = OO["R"][16.0]["B"].shape[0]
    D = draws(gmm)
    E = Entries("x.x5", SRC)
    direct = sensor_measures(tests)
    ref_cls = np.digitize(ref, LIMITS)
    ref_asi = np.array([t["ref_asi"] for t in tests])
    rows = []

    def measure_arrays(rg: float, hz: int) -> dict[str, np.ndarray]:
        d = direct[(rg, hz)]
        out = {"plain": np.broadcast_to(d["plain"], (REP, n)), "spline": np.broadcast_to(d["spline"], (REP, n)), "asi": np.broadcast_to(d["asi"], (REP, n)), "dirplain": np.broadcast_to(d["dirplain"], (REP, n))}
        if hz == 100:
            out["plain"], out["spline"] = OO["R"][rg]["B"], OO["R"][rg]["SP"]  # the fold-chosen settings of split R, as in N14
            out["fillridge"], out["tailaware"] = OO["R"][rg]["M+"], OO["R"][rg]["QR"]
        return out

    for rg in RANGES:
        for hz in RATES:
            M = measure_arrays(rg, hz)
            for name, est in M.items():
                f = lambda i, est=est: float(rho(est[:, i], np.broadcast_to(ref[i], (est.shape[0], len(i)))).mean())  # noqa: E731
                pt, lo, hi, _ = boot(f, n, D)
                E.ci(f"r{rg:g}.f{hz}.{name}.rho_ref", (pt, lo, hi), "correlation", "Spearman with the reference delta-V; mean over repeats; make/model groups resampled", d=4)
                row = dict(range_g=rg, rate_hz=hz, measure=name, rho=pt, rho_lo=lo, rho_hi=hi)
                if name != "asi":
                    cls = np.digitize(est, LIMITS)
                    acc = lambda i, cls=cls: float((cls[:, i] == ref_cls[i]).mean())  # noqa: E731
                    kap = lambda i, cls=cls: float(np.nanmean([kappa_lin(cls[r, i], ref_cls[i]) for r in range(0, cls.shape[0], 3)]))  # noqa: E731
                    a_, alo, ahi, _ = boot(acc, n, D)
                    k_, klo, khi, _ = boot(kap, n, D)
                    E.ci(f"r{rg:g}.f{hz}.{name}.class_accuracy", (a_, alo, ahi), "fraction", "share of tests with the class of the reference delta-V", d=4)
                    E.ci(f"r{rg:g}.f{hz}.{name}.class_kappa", (k_, klo, khi), "kappa", "linear-weighted kappa, every third repeat", d=4)
                    row.update(acc=a_, acc_lo=alo, acc_hi=ahi, kappa=k_, kappa_lo=klo, kappa_hi=khi)
                else:
                    ra = lambda i, est=est: float(rho(est[:, i], np.broadcast_to(ref_asi[i], (est.shape[0], len(i)))).mean())  # noqa: E731
                    p2, l2, h2, _ = boot(ra, n, D)
                    E.ci(f"r{rg:g}.f{hz}.asi.rho_refasi", (p2, l2, h2), "correlation", "Spearman of the sensor ASI with the ASI of the unclipped original pulse", d=4)
                rows.append(row)
    # ---- H-X5 (primary): fill + ridge at +-16 g, 100 Hz
    est = OO["R"][16.0]["M+"]
    f = lambda i: float(rho(est[:, i], np.broadcast_to(ref[i], (est.shape[0], len(i)))).mean())  # noqa: E731
    pt, lo, hi, d = boot(f, n, D)
    p_raw = float(max(np.mean(d <= 0.85), 1.0 / (len(d) + 1)))
    E.add("hX5.rho_fillridge", round(pt, 4), "correlation", "primary quantity: Spearman, fill + ridge against the reference delta-V, +-16 g, 100 Hz, split R")
    E.add("hX5.rho_fillridge_lo", round(lo, 4), "correlation")
    E.add("hX5.rho_fillridge_hi", round(hi, 4), "correlation")
    E.add("hX5.p_raw", round(p_raw, 4), "probability", "share of grouped resamples with correlation at or below 0.85; floor 0.001")
    E.add("hX5.criterion_met", int(pt >= 0.90 and lo >= 0.85), "flag", "point estimate at least 0.90 and lower 95% end at least 0.85")
    pl = OO["R"][16.0]["B"]
    fpl = lambda i: float(rho(pl[:, i], np.broadcast_to(ref[i], (pl.shape[0], len(i)))).mean())  # noqa: E731
    E.ci("hX5.rho_plain", boot(fpl, n, D)[:3], "correlation", "baseline for the primary quantity: the plain estimate", d=4)
    # sensitivity: one row per test number (drops the two repeated records found by T13c)
    keep = np.array([i for i, tn in enumerate(OO["test_no"]) if tn not in set(OO["test_no"][:i])])
    f2 = lambda i: float(rho(est[:, keep[i]], np.broadcast_to(ref[keep[i]], (est.shape[0], len(i)))).mean())  # noqa: E731
    D2 = draws(gmm[keep])
    pt2, lo2, hi2, _ = boot(f2, len(keep), D2)
    E.add("hX5.sens_distinct_tests.rho_fillridge", round(pt2, 4), "correlation", f"{len(keep)} distinct test numbers")
    E.add("hX5.sens_distinct_tests.rho_fillridge_lo", round(lo2, 4), "correlation")
    E.add("hX5.sens_distinct_tests.rho_fillridge_hi", round(hi2, 4), "correlation")
    # ---- exploratory: injury criteria
    crit = criteria_table(tests)
    crit.to_csv(C.TABLES / "x5_criteria.csv", index=False)
    inj_rows = []
    for kind, names in CRITERIA.items():
        for c in names:
            ok = (kinds == kind) & crit[c].notna().to_numpy()
            nn = int(ok.sum())
            E.add(f"inj.{kind}.{c}.n", nn, "tests", "tests of this kind with a valid value (above 0 and below 9,000)")
            if nn < 15:
                E.add(f"inj.{kind}.{c}.status", "NOT_RUN", "text", "fewer than 15 tests with a valid value", origin="NOT_RUN")
                continue
            idx = np.flatnonzero(ok)
            yc = crit[c].to_numpy()[idx]
            Dk = draws(gmm[idx])
            fr = lambda i: float(rho(ref[idx][i], yc[i]))  # noqa: E731
            rr, rlo, rhi, _ = boot(fr, nn, Dk)
            fa = lambda i: float(rho(ref_asi[idx][i], yc[i]))  # noqa: E731
            ra_, ralo, rahi, _ = boot(fa, nn, Dk)
            E.ci(f"inj.{kind}.{c}.rho_ref_dv", (rr, rlo, rhi), "correlation", "Spearman of the reference delta-V with the criterion", d=4)
            E.ci(f"inj.{kind}.{c}.rho_ref_asi", (ra_, ralo, rahi), "correlation", "Spearman of the reference ASI with the criterion", d=4)
            kept = rr >= REF_RHO_MIN
            E.add(f"inj.{kind}.{c}.kept", int(kept), "flag", "reference correlation at least 0.2: the comparison is kept; otherwise it is dropped (preregistration)")
            if not kept:
                inj_rows.append(dict(kind=kind, criterion=c, n=nn, rho_ref=rr, kept=0))
                continue
            for rg in RANGES:
                for hz in RATES:
                    for name, est_m in measure_arrays(rg, hz).items():
                        fe = lambda i, est_m=est_m: float(rho(est_m[:, idx][:, i], np.broadcast_to(yc[i], (est_m.shape[0], len(i)))).mean())  # noqa: E731
                        loss = lambda i, est_m=est_m: float(rho(est_m[:, idx][:, i], np.broadcast_to(yc[i], (est_m.shape[0], len(i)))).mean() - rho(ref[idx][i], yc[i]))  # noqa: E731
                        pe, elo, ehi, _ = boot(fe, nn, Dk)
                        pl_, llo, lhi, _ = boot(loss, nn, Dk)
                        E.ci(f"inj.{kind}.{c}.r{rg:g}.f{hz}.{name}.rho", (pe, elo, ehi), "correlation", "Spearman of the estimate with the criterion; mean over repeats", d=4)
                        E.ci(f"inj.{kind}.{c}.r{rg:g}.f{hz}.{name}.loss", (pl_, llo, lhi), "correlation", "estimate's correlation minus the reference delta-V's correlation; a lower end below -0.05 counts against", d=4)
                        E.add(f"inj.{kind}.{c}.r{rg:g}.f{hz}.{name}.counts_against", int(llo < -0.05), "flag")
                        inj_rows.append(dict(kind=kind, criterion=c, n=nn, rho_ref=rr, kept=1, range_g=rg, rate_hz=hz, measure=name, rho=pe, loss=pl_, loss_lo=llo, loss_hi=lhi))
    pd.DataFrame(rows).to_csv(C.TABLES / "x5_rank.csv", index=False)
    pd.DataFrame(inj_rows).to_csv(C.TABLES / "x5_injury.csv", index=False)
    E.flush()
    pd.set_option("display.width", 250)
    d_ = pd.DataFrame(rows)
    print(d_[d_.rate_hz == 100].round(3).to_string())
    print("H-X5", round(pt, 4), round(lo, 4), round(hi, 4), "p", p_raw)
    print(pd.DataFrame(inj_rows).head(12).round(3).to_string() if inj_rows else "no injury rows")


if __name__ == "__main__":
    main()
