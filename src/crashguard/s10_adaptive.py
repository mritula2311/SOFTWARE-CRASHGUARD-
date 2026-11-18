"""S10 (N25): prevalence-adaptive alert threshold and cancel-window cost model (plan, rules and decision rule: docs/02_preregistration/EXPERIMENTS_EXTRA.md, S10, written before this was run).

Populations of 1,000,000 events are drawn by resampling the de-duplicated test pool (pool bootstrapped, then crashes and non-crashes drawn with replacement), 200 repeats, at prevalences
0.02%, 0.1%, 1% and 16% of the events passed to the detector. These are CONDITIONAL numbers: VZCrash events were pre-selected on the device, and the prevalence among all driving is lower still.
Costs are our assumptions (SIMULATED); the recall, precision and false-alarm counts come from resampling measured scores (MEASURED_SOFTWARE).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from crashguard import config as C
from crashguard.detector_extra import SEL, fit, frames_full, score_all, threshold_for_fpr
from crashguard.models import op_thresholds

PIS = (0.0002, 0.001, 0.01, 0.16)
N_POP = 1_000_000
REPEATS = 200
MODELS = ("rf15", SEL)
SEEDS = C.SEEDS
C_MISS, C_FALSE, P_CANCEL = 1000.0, 1.0, 0.9
RATIOS = (10.0, 100.0, 1000.0, 10000.0)
CANCELS = (0.5, 0.7, 0.9, 0.95)
PPV_TARGETS = (0.10, 0.50)
RULES = ("a", "a1", "a5", "b_known", "b_em", "c_known", "c_em", "d10", "d50")
SRC = "results/tables/s10_adaptive.csv"
EPS = 1e-6


def tag(pi: float) -> str:
    return f"{pi * 100:g}pct".replace(".", "p")


def adjust(q: np.ndarray, pi_dep: float, pi_tr: float) -> np.ndarray:
    """Prior-shift adjusted posterior p' = a q / (a q + b (1 - q)), a = pi_dep / pi_tr, b = (1 - pi_dep) / (1 - pi_tr)."""
    a, b = pi_dep / pi_tr, (1.0 - pi_dep) / (1.0 - pi_tr)
    return a * q / (a * q + b * (1.0 - q))


def q_threshold(theta: float, pi_dep: float, pi_tr: float) -> float:
    """The calibrated-probability threshold that is equivalent to p' >= theta: q >= b theta / (a (1 - theta) + b theta)."""
    a, b = pi_dep / pi_tr, (1.0 - pi_dep) / (1.0 - pi_tr)
    return b * theta / (a * (1.0 - theta) + b * theta)


def cost_theta(c_miss: float, c_false: float, p_cancel: float) -> float:
    """p' threshold of the minimum-expected-cost rule: alarm iff p'/(1 - p') >= c_false (1 - p_cancel) / c_miss."""
    c = c_false * (1.0 - p_cancel) / c_miss
    return c / (1.0 + c)


def em_prior(q: np.ndarray, w: np.ndarray, pi_tr: float, iters: int = 100, tol: float = 1e-10) -> float:
    """EM estimate of the deployment prior (Saerens, Latinne and Decaestecker 2002) from the unlabeled events with calibrated posteriors ``q`` and weights ``w``."""
    pi = pi_tr
    tot = w.sum()
    for _ in range(iters):
        new = float((w * adjust(q, pi, pi_tr)).sum() / tot)
        new = min(max(new, 1e-9), 1 - 1e-9)
        if abs(new - pi) < tol:
            pi = new
            break
        pi = new
    return pi


class Prep:
    """Scores, thresholds and calibration of one (model, seed). All thresholds are chosen on validation only."""

    def __init__(self, model: str, seed: int, tr, va, te):
        va_trig = va[va.triggered]
        scorer, _ = fit(model, seed, tr, va_trig)
        self.s_va, self.s_te = score_all(scorer, va), score_all(scorer, te)
        self.y_va, self.y_te = va.y.to_numpy(), te.y.to_numpy()
        self.trig_te = te.triggered.to_numpy(bool)
        trig_va = va.triggered.to_numpy(bool)
        self.t_a, _ = op_thresholds(self.y_va[trig_va], self.s_va[trig_va])
        self.t_a1, self.t_a5 = threshold_for_fpr(self.y_va, self.s_va, 0.01), threshold_for_fpr(self.y_va, self.s_va, 0.05)
        iso = IsotonicRegression(y_min=EPS, y_max=1 - EPS, out_of_bounds="clip").fit(self.s_va[trig_va], self.y_va[trig_va])
        self.pi_tr = float(self.y_va[trig_va].mean())
        self.q_te = np.where(self.trig_te, iso.predict(np.where(self.trig_te, self.s_te, 0.0)), 0.0)
        # sorted structures of the test pool for cumulative counts
        self.order = np.argsort(-self.s_te, kind="stable")
        self.s_sorted = self.s_te[self.order]
        self.q_sorted = self.q_te[self.order]
        self.rc = float(self.trig_te[self.y_te == 1].mean())
        self.qn = float(self.trig_te[self.y_te == 0].mean())
        # validation curve for the target-precision rule (d)
        cand = np.unique(self.s_va[trig_va])[::-1]
        pos, neg = self.s_va[self.y_va == 1], self.s_va[self.y_va == 0]
        self.val_t = cand
        self.val_r = np.array([(pos >= t).mean() for t in cand])
        self.val_f = np.array([(neg >= t).mean() for t in cand])

    def target_threshold(self, pi: float, target: float) -> float | None:
        ppv = pi * self.val_r / np.maximum(pi * self.val_r + (1.0 - pi) * self.val_f, 1e-300)
        ok = np.flatnonzero(ppv >= target)
        return float(self.val_t[ok[-1]]) if len(ok) else None  # the lowest threshold that still meets the target = the highest recall

    def pi_trig_known(self, pi: float) -> float:
        return pi * self.rc / (pi * self.rc + (1.0 - pi) * self.qn)


def counts_at(cum: np.ndarray, k: int) -> int:
    return int(cum[k - 1]) if k > 0 else 0


def evaluate(P: Prep, cpos_s: np.ndarray, cneg_s: np.ndarray, cum_pos: np.ndarray, cum_neg: np.ndarray, n_pos: int, k: int, p_cancel: float = P_CANCEL, c_miss: float = C_MISS) -> dict:
    tp, fp = counts_at(cum_pos, k), counts_at(cum_neg, k)
    fn = n_pos - tp
    return dict(recall=tp / max(n_pos, 1), ppv=tp / max(tp + fp, 1), fp100k=fp / N_POP * 1e5, cost100k=(fn * c_miss + fp * C_FALSE * (1.0 - p_cancel)) / N_POP * 1e5, alarms=tp + fp)


def k_raw(P: Prep, t: float) -> int:
    return int(np.searchsorted(-P.s_sorted, -t, side="right"))


def k_q(P: Prep, thr_q: float) -> int:
    return int(np.searchsorted(-P.q_sorted, -thr_q, side="right"))


def main() -> None:
    from crashguard.results import record_many

    tr, va, te = frames_full()
    preps = {(m, s): Prep(m, s, tr, va, te) for m in MODELS for s in SEEDS}
    any_p = next(iter(preps.values()))
    y_te = any_p.y_te
    pos_idx, neg_idx = np.flatnonzero(y_te == 1), np.flatnonzero(y_te == 0)
    rng = np.random.default_rng(C.SEED)
    metrics = ("recall", "ppv", "fp100k", "cost100k", "alarms")
    res: dict = {}  # (model, pi, rule, metric) -> array (repeats, seeds)
    em_ratio: dict = {}
    sens: dict = {}
    for rep in range(REPEATS):
        # pool bootstrap, then the population counts, shared by all models and seeds
        pool_pos = np.bincount(rng.integers(0, len(pos_idx), len(pos_idx)), minlength=len(pos_idx)) / len(pos_idx)
        pool_neg = np.bincount(rng.integers(0, len(neg_idx), len(neg_idx)), minlength=len(neg_idx)) / len(neg_idx)
        for pi in PIS:
            n_pos = int(round(pi * N_POP))
            cnt = np.zeros(len(y_te))
            cp = rng.multinomial(n_pos, pool_pos)
            cn = rng.multinomial(N_POP - n_pos, pool_neg)
            cpos, cneg = np.zeros(len(y_te)), np.zeros(len(y_te))
            cpos[pos_idx], cneg[neg_idx] = cp, cn
            cnt = cpos + cneg
            for (m, s), P in preps.items():
                cps, cns = cpos[P.order], cneg[P.order]
                cum_p, cum_n = np.cumsum(cps), np.cumsum(cns)
                out = {}
                out["a"] = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_raw(P, P.t_a))
                out["a1"] = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_raw(P, P.t_a1))
                out["a5"] = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_raw(P, P.t_a5))
                pi_known = P.pi_trig_known(pi)
                w_t = cnt[P.trig_te]
                pi_em = em_prior(P.q_te[P.trig_te], w_t, P.pi_tr)
                em_ratio.setdefault((m, pi), []).append(pi_em / pi_known)
                for ver, pi_dep in (("known", pi_known), ("em", pi_em)):
                    out[f"b_{ver}"] = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_q(P, q_threshold(0.5, pi_dep, P.pi_tr)))
                    out[f"c_{ver}"] = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_q(P, q_threshold(cost_theta(C_MISS, C_FALSE, P_CANCEL), pi_dep, P.pi_tr)))
                for tg, nm in zip(PPV_TARGETS, ("d10", "d50")):
                    t = P.target_threshold(pi, tg)
                    out[nm] = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_raw(P, t)) if t is not None else None
                for rule, d in out.items():
                    for met in metrics:
                        res.setdefault((m, pi, rule, met), np.full((REPEATS, len(SEEDS)), np.nan))[rep, SEEDS.index(s)] = d[met] if d is not None else np.nan
                for ratio in RATIOS:
                    for pc in CANCELS:
                        d = evaluate(P, cps, cns, cum_p, cum_n, n_pos, k_q(P, q_threshold(cost_theta(ratio, C_FALSE, pc), pi_known, P.pi_tr)), p_cancel=pc, c_miss=ratio)
                        for met in metrics:
                            sens.setdefault((m, pi, ratio, pc, met), np.full((REPEATS, len(SEEDS)), np.nan))[rep, SEEDS.index(s)] = d[met]
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="MEASURED_SOFTWARE"):
        ent.append(dict(name=f"s10.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    def summ(a: np.ndarray) -> tuple[float, float, float]:
        v = np.nanmean(a, axis=1)  # mean over seeds within a repeat
        return float(np.nanmean(v)), float(np.nanquantile(v, 0.025)), float(np.nanquantile(v, 0.975))

    add("population_size", N_POP, "events", "events per drawn population")
    add("repeats", REPEATS, "repeats", "population draws per prevalence (pool bootstrapped)")
    add("assumed.c_miss_over_c_false", C_MISS / C_FALSE, "ratio", "ASSUMPTION: no measured cost", "SIMULATED")
    add("assumed.p_cancel", P_CANCEL, "probability", "ASSUMPTION: share of false alarms the driver cancels in time", "SIMULATED")
    unit = {"recall": "fraction", "ppv": "fraction", "fp100k": "per 100,000 events", "cost100k": "C_false per 100,000 events", "alarms": "alarms per population"}
    rows = []
    for (m, pi, rule, met), arr in res.items():
        if np.isnan(arr).all():
            continue
        p, lo, hi = summ(arr)
        origin = "SIMULATED" if met == "cost100k" else "MEASURED_SOFTWARE"
        base = f"{m}.pi{tag(pi)}.{rule}.{met}"
        add(base, round(p, 6), unit[met], "mean over repeats of the seed-mean; resampled populations of the de-duplicated test pool", origin)
        add(base + "_lo", round(lo, 6), unit[met], "95% percentile interval over repeats", origin)
        add(base + "_hi", round(hi, 6), unit[met], "95% percentile interval over repeats", origin)
        rows.append(dict(model=m, prevalence=pi, rule=rule, metric=met, value=p, lo=lo, hi=hi))
    for (m, pi, rule), _ in {(k[0], k[1], k[2]): 0 for k in res}.items():
        if rule == "a":
            continue
        for met in ("ppv", "recall"):
            a, r_ = res[(m, pi, "a", met)], res[(m, pi, rule, met)]
            if np.isnan(r_).all():
                continue
            d = np.nanmean(r_ - a, axis=1)
            add(f"{m}.pi{tag(pi)}.{rule}.d_{met}_vs_a", round(float(np.nanmean(d)), 6), "fraction", "rule minus (a), paired by repeat, mean over seeds", "MEASURED_SOFTWARE")
            add(f"{m}.pi{tag(pi)}.{rule}.d_{met}_vs_a_lo", round(float(np.nanquantile(d, 0.025)), 6), "fraction", "95% percentile interval over repeats")
            add(f"{m}.pi{tag(pi)}.{rule}.d_{met}_vs_a_hi", round(float(np.nanquantile(d, 0.975)), 6), "fraction", "95% percentile interval over repeats")
        dp = np.nanmean(res[(m, pi, rule, "ppv")] - res[(m, pi, "a", "ppv")], axis=1)
        dr = np.nanmean(res[(m, pi, rule, "recall")] - res[(m, pi, "a", "recall")], axis=1)
        if not np.isnan(dp).all():
            ok = bool(np.nanquantile(dp, 0.025) > 0 and np.nanmean(dr) >= -0.05)
            add(f"{m}.pi{tag(pi)}.{rule}.improvement", int(ok), "flag", "decision rule fixed in advance: PPV difference interval above zero AND mean recall no more than 5 points lower than (a)")
    for (m, pi), v in em_ratio.items():
        add(f"{m}.pi{tag(pi)}.em_prior_over_known", round(float(np.mean(v)), 4), "ratio", "EM estimate of the prior among triggered events divided by the expected value (mean over repeats and seeds)")
    for rule in ("d10", "d50"):
        for m in MODELS:
            for pi in PIS:
                share = float(np.isnan(res[(m, pi, rule, "recall")]).mean())
                add(f"{m}.pi{tag(pi)}.{rule}.share_unreachable", round(share, 4), "fraction", "share of (repeat, seed) cells in which no validation threshold reaches the target precision")
    for (m, pi, ratio, pc, met), arr in sens.items():
        p, lo, hi = summ(arr)
        add(f"sens.{m}.pi{tag(pi)}.ratio{ratio:g}.cancel{pc:g}.{met}", round(p, 6), unit[met], "rule (c) with known prevalence; cost assumptions as named", "SIMULATED" if met == "cost100k" else "MEASURED_SOFTWARE")
        add(f"sens.{m}.pi{tag(pi)}.ratio{ratio:g}.cancel{pc:g}.{met}_lo", round(lo, 6), unit[met], "95% percentile interval over repeats", "SIMULATED" if met == "cost100k" else "MEASURED_SOFTWARE")
        add(f"sens.{m}.pi{tag(pi)}.ratio{ratio:g}.cancel{pc:g}.{met}_hi", round(hi, 6), unit[met], "95% percentile interval over repeats", "SIMULATED" if met == "cost100k" else "MEASURED_SOFTWARE")
    # expected PPV-recall curves from the pool (rf15 and the candidate, seed 42-free: seeds 0 to 4 averaged on a common score grid is not meaningful, so seed 0 is plotted)
    curves = []
    for m in MODELS:
        P = preps[(m, SEEDS[0])]
        pos, neg = P.s_te[P.y_te == 1], P.s_te[P.y_te == 0]
        grid = np.unique(np.concatenate([[0.0], P.s_te[P.trig_te]]))
        for t in grid[:: max(len(grid) // 400, 1)]:
            r, f = float((pos >= t).mean()), float((neg >= t).mean())
            for pi in PIS:
                curves.append(dict(model=m, prevalence=pi, threshold=t, recall=r, ppv=pi * r / max(pi * r + (1 - pi) * f, 1e-300)))
    pd.DataFrame(curves).to_csv(C.TABLES / "s10_curves.csv", index=False)
    pd.DataFrame(rows).to_csv(C.TABLES / "s10_adaptive.csv", index=False)
    make_figure(pd.DataFrame(curves), pd.DataFrame(rows))
    record_many(ent, purge_prefixes=("s10.",))
    pd.set_option("display.width", 250)
    d = pd.DataFrame(rows)
    print(d[(d.model == "rf15") & (d.metric.isin(["recall", "ppv", "fp100k"]))].pivot_table(index=["prevalence", "rule"], columns="metric", values="value").round(5).to_string())


def make_figure(curves: pd.DataFrame, rows: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import COLORS, save, style

    style()
    fig, axes = plt.subplots(1, len(PIS), figsize=(13, 3.6), sharey=False)
    for ax, pi in zip(axes, PIS):
        c = curves[(curves.model == "rf15") & (curves.prevalence == pi)]
        ax.plot(c.recall, c.ppv, color=COLORS[0], lw=1.5, label="expected curve (test pool)")
        r = rows[(rows.model == "rf15") & (rows.prevalence == pi)]
        for k, rule in enumerate(("a", "a1", "a5", "b_known", "c_known")):
            x, y = r[(r.rule == rule) & (r.metric == "recall")].value, r[(r.rule == rule) & (r.metric == "ppv")].value
            if len(x) and len(y):
                ax.scatter(x, y, color=COLORS[(k + 1) % len(COLORS)], s=28, label=rule, zorder=3)
        ax.set_xlabel("System recall (fraction of crashes alarmed)")
        ax.set_ylabel("Precision (fraction of alarms that are crashes)")
        ax.set_title(f"prevalence {pi * 100:g}%")
        ax.set_yscale("log")
    axes[0].legend(fontsize=6)
    save(fig, "s10_ppv_recall")


if __name__ == "__main__":
    main()
