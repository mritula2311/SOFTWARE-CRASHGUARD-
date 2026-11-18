"""X7 (docs/02_preregistration/PREREGISTRATION_V3.md): two-part sensor fusion from real parts. MEASURED_SOFTWARE on 176 NHTSA tests (mostly high-speed barrier tests; the sensor chains are software models; no time
synchronisation or mounting error between the two parts is modelled).

Each part is run through its own chain (``sel_study.chain``: datasheet bandwidth, range, rate, resolution, noise); the high-range signal is linearly resampled onto the low-range grid.
(i) Substitution with gain match: clipped low-range samples (within 2% of the range, widened by one sample each side) are replaced by the gain-matched high-range sample.
(ii) Ridge-calibrated blend: the delta-V of (i) times exp of a ridge prediction from [low-range plain delta-V, high-range plain delta-V, clipped share], out-of-fold on split R.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import saturation as SAT
from crashguard import saturation_splits as SPL
from crashguard import severity as S
from crashguard import severity_study as SS
from crashguard.jp_common import Entries
from crashguard.sel_parts import BY_KEY
from crashguard.sel_study import chain

SRC = "results/tables/x7_fusion.csv"
LOW = (("adxl345", 16, 3200), ("mpu6050", 16, 1000), ("lis3dh", 16, 1250), ("kx134", 16, 1600))
HIGH = (("adxl375", 200, 3200), ("h3lis331dl", 200, 1000), ("adxl372", 200, 3200), ("kx134", 64, 1600))
CLIP_FRAC = 0.98
TARGET = 0.80
PP = SPL.sp_params(SPL.RF0)


def tgrid(sig: dict, fs: float) -> np.ndarray:
    t = np.asarray(sig["t"])
    return np.arange(t[0], t[-1], 1.0 / fs)


def fuse_signal(sig: dict, lo: tuple, hi: tuple, seed: int, level: float = CLIP_FRAC, dil: int = 1) -> tuple[np.ndarray, float, dict]:
    pl, rl, fl = BY_KEY[lo[0]], float(lo[1]), float(lo[2])
    ph, rh, fh = BY_KEY[hi[0]], float(hi[1]), float(hi[2])
    yl = chain(sig, pl, rl, fl, seed)
    yh = chain(sig, ph, rh, fh, seed + 7)
    tl, th = tgrid(sig, fl), tgrid(sig, fh)
    yhr = np.stack([np.interp(tl, th, yh[:, k]) for k in range(3)], axis=1)
    out = yl.copy()
    clipped_any = np.zeros(len(yl), bool)
    gains = []
    for a in (0, 1):
        m = np.abs(yl[:, a]) >= level * rl
        for _ in range(dil):
            m = m | np.r_[m[1:], False] | np.r_[False, m[:-1]]
        ok = (~m) & (np.abs(yhr[:, a]) > 0.5)
        g = float((yl[ok, a] * yhr[ok, a]).sum() / max((yhr[ok, a] ** 2).sum(), 1e-9)) if ok.sum() >= 3 else 1.0
        g = g if 0.5 < g < 2.0 else 1.0
        gains.append(g)
        out[m, a] = g * yhr[m, a]
        clipped_any |= m
    return out, fl, dict(yl=yl, yhr=yhr, clip_share=float(clipped_any.mean()), clipped=clipped_any)


def dv_of(y: np.ndarray, fs: float) -> tuple[float, float]:
    w, trig = SS._window(y, fs)
    r = S.severity(w, fs, trig, None, PP)
    return r["dv_res_kmh"], r["pulse_ms"]


def pair_features(tests: list[dict], lo: tuple, hi: tuple, level: float = CLIP_FRAC, dil: int = 1) -> dict:
    n = len(tests)
    dv_sub, dv_low, dv_high, share = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    for i, t in enumerate(tests):
        y, fs, info = fuse_signal(t["sig"], lo, hi, 42 + i, level, dil)
        dv_sub[i] = dv_of(y, fs)[0]
        dv_low[i] = dv_of(info["yl"], fs)[0]
        dv_high[i] = dv_of(info["yhr"], fs)[0]
        w, trig = SS._window(info["yl"], fs)
        pulse = np.arange(max(trig, 0), min(trig + int(0.25 * fs), len(w)))
        share[i] = float(info["clipped"][: len(w)][pulse].mean()) if len(pulse) and len(info["clipped"]) >= len(w) else info["clip_share"]
    return dict(sub=dv_sub, low=dv_low, high=dv_high, share=share)


def blend_oof(f: dict, ref: np.ndarray, groups: np.ndarray, reps: int = 10, folds: int = 5) -> np.ndarray:
    """(reps, n) out-of-fold blend estimates. Ridge on [low, high, share] of the log of reference over substituted delta-V, applied where something was clipped; strength by leave-one-group-out on the training rows."""
    n = len(ref)
    X = np.stack([f["low"], f["high"], f["share"]], axis=1)
    y = np.log(ref / np.maximum(f["sub"], 1e-6))
    app = f["share"] > 0
    ug = sorted(set(groups.tolist()))
    out = np.zeros((reps, n))
    for rep in range(reps):
        rng = np.random.default_rng(C.SEED + rep)
        order = list(rng.permutation(len(ug)))
        fo = {ug[j]: k % folds for k, j in enumerate(order)}
        fold = np.array([fo[g] for g in groups])
        for k in range(folds):
            te, tr = fold == k, fold != k
            use = tr & app
            est = f["sub"][te].copy()
            if use.sum() >= 8:
                best = None
                for a in SPL.ALPHAS:
                    pred = np.zeros(int(use.sum()))
                    gu, Xu, yu = groups[use], X[use], y[use]
                    for g in sorted(set(gu.tolist())):
                        m = gu == g
                        if (~m).sum() >= 4:
                            pred[m] = SAT.RidgeCorrection(a).fit(Xu[~m], yu[~m]).predict(Xu[m])
                    corr = f["sub"][tr].copy()
                    pos = np.flatnonzero(tr)
                    corr[app[tr]] = f["sub"][use] * np.exp(pred)
                    sc = float(np.median(SPL.aerr(corr, ref[tr])))
                    if best is None or (round(sc, 9), -a) < (round(best[0], 9), -best[1]):
                        best = (sc, a)
                    del pos
                rc = SAT.RidgeCorrection(best[1]).fit(X[use], y[use])
                ap_te = app[te]
                if ap_te.any():
                    est[ap_te] = est[ap_te] * np.exp(rc.predict(X[te][ap_te]))
            out[rep, te] = est
    return out


def main() -> None:
    tests = SS.load_tests()
    meta = SPL.meta_of(tests)
    ref, groups = meta.ref.to_numpy(), meta.group_mm.to_numpy()
    n = len(ref)
    D = list(B._gidx(B.group_members(groups), B.N_BOOT, B.SEED))
    cfg = pd.read_csv(C.TABLES / "sel_configs.csv")
    cfg = cfg[cfg.set == "n13"].set_index(["part", "range_g", "odr_hz"])
    E = Entries("x.x7", SRC)
    rows, p_list = [], []

    def stats(e: np.ndarray) -> dict:
        res = {}
        for nm, fn in (("w10", lambda a: float(np.mean(a <= 10.0))), ("median", lambda a: float(np.median(a))), ("p90", lambda a: float(np.quantile(a, 0.9)))):
            if e.ndim == 2:
                f = lambda i, fn=fn: float(np.mean([fn(e[k][i]) for k in range(e.shape[0])]))  # noqa: E731
            else:
                f = lambda i, fn=fn: fn(e[i])  # noqa: E731
            pt = f(np.arange(n))
            d = np.array([f(i) for i in D])
            res[nm] = (pt, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975)), d)
        return res

    for lo in LOW:
        for hi in HIGH:
            fs_ = {"": pair_features(tests, lo, hi), "_wide": pair_features(tests, lo, hi, 0.5, 3)}  # _wide: EXPLORATORY, defined after the preregistered rule gave a poor initial result (docs/07_log/DECISIONS.md)
            alone_lo = cfg.loc[(lo[0], float(lo[1]), lo[2])]
            alone_hi = cfg.loc[(hi[0], float(hi[1]), hi[2])]
            blends = {k: blend_oof(f, ref, groups) for k, f in fs_.items()}
            for rule, est in (("substitution", fs_[""]["sub"]), ("blend", blends[""]), ("substitution_wide", fs_["_wide"]["sub"]), ("blend_wide", blends["_wide"])):
                expl = rule.endswith("_wide")
                err = np.abs(100.0 * (est - ref) / ref) if est.ndim == 1 else np.abs(100.0 * (est - ref[None, :]) / ref[None, :])
                st = stats(err)
                name = f"{lo[0]}_r{lo[1]}_f{lo[2]}+{hi[0]}_r{hi[1]}_f{hi[2]}.{rule}"
                for k in ("w10", "median", "p90"):
                    E.ci(f"{name}.{k}", st[k][:3], "fraction" if k == "w10" else "percent", d=4)
                neither = float(alone_lo.w10_lo) < TARGET and float(alone_hi.w10_lo) < TARGET
                meets = st["w10"][1] >= TARGET
                E.add(f"{name}.neither_part_alone_meets", int(neither), "flag", "lower interval end of each part alone at its configuration (176 tests) is below 0.80")
                E.add(f"{name}.meets", int(meets), "flag", "lower 95% end of the share within 10% is at least 0.80")
                E.add(f"{name}.counts_for_hX7", int(meets and neither and not expl), "flag", "EXPLORATORY rules never count" if expl else "")
                E.add(f"{name}.exploratory", int(expl), "flag")
                E.add(f"{name}.extra_part_count", 1, "parts", "the second part; a count, not a price")
                E.add(f"{name}.extra_reads_per_s", float(hi[2]), "reads/s", "output rate of the second part; a count of bus reads, not a price")
                p = float(max(np.mean(st["w10"][3] < TARGET), 1.0 / (len(st["w10"][3]) + 1)))
                if not expl:
                    p_list.append(p)
                rows.append(dict(low=f"{lo[0]} +-{lo[1]} g {lo[2]} Hz", high=f"{hi[0]} +-{hi[1]} g {hi[2]} Hz", rule=rule, w10=st["w10"][0], w10_lo=st["w10"][1], w10_hi=st["w10"][2], median=st["median"][0], p90=st["p90"][0],
                                 low_alone_w10_lo=float(alone_lo.w10_lo), high_alone_w10_lo=float(alone_hi.w10_lo), meets=meets, neither_alone=neither, counts=meets and neither and not expl, exploratory=expl, p=p))
            print(lo[0], hi[0], flush=True)
    R = pd.DataFrame(rows)
    R.to_csv(C.TABLES / "x7_fusion.csv", index=False)
    cnt = int(R.counts.sum())
    E.add("hX7.n_counting_exploratory_wide", int((R.exploratory & R.meets & R.neither_alone).sum()), "combinations", "EXPLORATORY wide-mask rules that reach 0.80 where neither part alone does")
    p_raw = min(1.0, min(p_list) * len(p_list))
    E.add("hX7.n_pairs_rules", len(p_list), "combinations")
    E.add("hX7.n_counting", cnt, "combinations", "pairs and rules that reach a lower end of 0.80 where neither part alone does")
    E.add("hX7.n_meeting_any", int((R.meets & ~R.exploratory).sum()), "combinations")
    E.add("hX7.p_raw", round(p_raw, 4), "probability", "smallest one-sided bootstrap p over the combinations, times their number (Bonferroni), capped at 1")
    E.add("hX7.criterion_met", int(cnt > 0), "flag")
    E.flush()
    pd.set_option("display.width", 250)
    print(R.round(3).to_string())
    print("H-X7 counting", cnt, "p", p_raw)


if __name__ == "__main__":
    main()
