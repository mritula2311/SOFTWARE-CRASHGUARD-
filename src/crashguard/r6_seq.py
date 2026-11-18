"""R6-2 (docs/02_preregistration/PREREGISTRATION_V17.md section 4): sequential early exit (SPRT-style) on the frozen per-length forests.

    python -m crashguard.r6_seq dev <iteration 1..5>    # development on VALIDATION only; appends to results/tables/r6_seq_dev_log.json
    python -m crashguard.r6_seq freeze                  # freeze the chosen configuration by hash (results/tables/r6_frozen.json)
    python -m crashguard.r6_seq held                    # held-out run, made once, on HALF1 of the hash 'r6|id' of the de-duplicated VZCrash test events; keys r6.r2.*

Rule: at checkpoints 50, 100, 200, 400 and 800 ms the running log-likelihood ratio S_m (class-conditional score histograms of the per-length forests, estimated on the validation split) is compared with an upper
threshold A (send the provisional frame) and a lower threshold B (stop: no provisional frame); events not decided by 800 ms go to the 1,800 ms decision unchanged. Reference: the fixed early-exit rule of
``crashguard.early`` at the same provisional false-alarm rate on validation. Scores are the stored per-length scores of ``r5_det`` (seed 42). NHTSA timing check: NOT_RUN (cut order of V17 section 11).
"""
from __future__ import annotations

import json
import sys

import numpy as np

from crashguard import r6_common as C6

LENGTHS = (50, 100, 200, 400, 800, 1800)
NCHK = 5  # checkpoints with an early decision
DEFAULT = dict(nbins=20, smooth=1.0, a_step=0.25, b_step=0.5, a_max=12.0, b_min=-8.0, fa_tol=0.001)


# ----------------------------------------------------------------------------- pure core (mutated in the tests)
def bin_edges(scores: np.ndarray, nbins: int) -> np.ndarray:
    """Equal-count bin edges of one checkpoint's pooled scores (interior edges, nbins - 1 of them)."""
    return np.unique(np.quantile(scores, np.linspace(0, 1, nbins + 1)[1:-1]))


def llr_table(s_pos: np.ndarray, s_neg: np.ndarray, edges: np.ndarray, smooth: float) -> np.ndarray:
    """log f1 / f0 per bin with add-``smooth`` smoothing; bins are the intervals between ``edges`` (len(edges) + 1 bins)."""
    nb = len(edges) + 1
    c1 = np.bincount(np.searchsorted(edges, s_pos, side="right"), minlength=nb) + smooth
    c0 = np.bincount(np.searchsorted(edges, s_neg, side="right"), minlength=nb) + smooth
    return np.log(c1 / c1.sum()) - np.log(c0 / c0.sum())


def running_llr(S: np.ndarray, edges: list[np.ndarray], tables: list[np.ndarray]) -> np.ndarray:
    """Cumulative log-likelihood ratio at checkpoints 0 .. NCHK - 1 (shape n x NCHK)."""
    out = np.zeros((len(S), NCHK))
    acc = np.zeros(len(S))
    for k in range(NCHK):
        acc = acc + tables[k][np.searchsorted(edges[k], S[:, k], side="right")]
        out[:, k] = acc
    return out


def seq_decisions(L: np.ndarray, A: float, B: float) -> tuple[np.ndarray, np.ndarray]:
    """Provisional alarm flag and decision time (ms; 1800 for an event with no early decision) of each event."""
    n = len(L)
    alarm, t = np.zeros(n, bool), np.full(n, float(LENGTHS[-1]))
    undecided = np.ones(n, bool)
    for k in range(NCHK):
        up = undecided & (L[:, k] >= A)
        down = undecided & ~up & (L[:, k] <= B)
        alarm[up], t[up] = True, LENGTHS[k]
        t[down] = LENGTHS[k]
        undecided &= ~(up | down)
    return alarm, t


def provisional_fa(alarm: np.ndarray, t: np.ndarray, neg: np.ndarray, n_neg_all: int) -> float:
    """Share of all non-crash events (the trigger discards some) with a provisional alarm (an early alarm, t < 1800 ms)."""
    return float((alarm & (t < LENGTHS[-1]) & neg).sum()) / n_neg_all


def select_AB(L: np.ndarray, pos: np.ndarray, neg: np.ndarray, n_neg_all: int, fa_target: float, a_grid: np.ndarray, b_grid: np.ndarray, fa_tol: float, ref: tuple | None = None) -> dict | None:
    """Among (A, B) with |provisional false-alarm rate - target| <= fa_tol, the pair with the smallest mean decision time of the crash events that alarm early; ties: the larger A.
    With ``ref = (t_fixed, prov_fixed)`` (iteration 4 of the development log) the objective is the paired one of H-R6-2a: the largest mean of (fixed time - sequential time) over crash events with a provisional
    alarm under both rules, so a pair cannot win by alarming fewer, earlier events only."""
    best = None
    for A in a_grid:
        for B in b_grid:
            if B >= A:
                continue
            alarm, t = seq_decisions(L, A, B)
            fa = provisional_fa(alarm, t, neg, n_neg_all)
            if abs(fa - fa_target) > fa_tol:
                continue
            sel = alarm & pos & (t < LENGTHS[-1])
            if ref is not None:
                sel = sel & ref[1]
            if not sel.any():
                continue
            mt = float(t[sel].mean()) if ref is None else -float((ref[0][sel] - t[sel]).mean())
            key = (-mt, A)
            if best is None or key > best["key"]:
                best = dict(key=key, A=float(A), B=float(B), fa=fa, mean_t=mt, n_alarm_pos=int(sel.sum()))
    return best


def retraction_share(prov: np.ndarray, full_alarm: np.ndarray) -> float:
    """Share of provisional alarms that the full window does not confirm."""
    return float(1.0 - full_alarm[prov].mean()) if prov.any() else float("nan")


def boot_stats(t_f: np.ndarray, t_s: np.ndarray, prov_f: np.ndarray, prov_s: np.ndarray, pos: np.ndarray, full_alarm: np.ndarray, n_boot: int = 2000, seed: int = 42) -> dict:
    """Bootstrap over events: (a) mean of (fixed time - sequential time) among crash events with a provisional alarm under both rules; (b) retraction share of the sequential rule minus the fixed rule's."""
    rng = np.random.default_rng(seed)
    n = len(t_f)
    both = prov_f & prov_s & pos
    d_a = np.empty(n_boot)
    d_b = np.empty(n_boot)
    for i in range(n_boot):
        ix = rng.integers(0, n, n)
        bb = both[ix]
        d_a[i] = float((t_f[ix][bb] - t_s[ix][bb]).mean()) if bb.any() else np.nan
        d_b[i] = retraction_share(prov_s[ix], full_alarm[ix]) - retraction_share(prov_f[ix], full_alarm[ix])
    pt_a = float((t_f[both] - t_s[both]).mean())
    pt_b = retraction_share(prov_s, full_alarm) - retraction_share(prov_f, full_alarm)
    return dict(a_pt=pt_a, a_lo=float(np.nanquantile(d_a, 0.025)), a_hi=float(np.nanquantile(d_a, 0.975)), a_p=float(((d_a <= 200.0) | np.isnan(d_a)).sum() + 1) / (n_boot + 1),
                b_pt=pt_b, b_lo=float(np.nanquantile(d_b, 0.025)), b_hi=float(np.nanquantile(d_b, 0.975)), b_p=float((d_b >= 0.02).sum() + 1) / (n_boot + 1), n_both=int(both.sum()))


# ----------------------------------------------------------------------------- data wiring
def load(with_test: bool = True) -> dict:
    from crashguard.detector_extra import threshold_for_fpr
    from crashguard.early import choose_rule, early_decisions, scatter
    from crashguard.r5_det import fit_seed, load_frames

    fr = load_frames()
    det = fit_seed(42, fr)
    va, te = fr["va"], fr["te"]
    Sv = det["Sv"]
    d_va, d_te = fr["d_va"], fr["d_te"]
    yv_full = va.y.to_numpy()
    n_neg_v, n_pos_v = int((yv_full == 0).sum()), int((yv_full == 1).sum())
    full_v = [scatter(va, d_va["event_id"], Sv[:, k]) for k in range(len(LENGTHS))]
    rule = choose_rule(Sv, d_va["y"], n_neg_v, n_pos_v, full_v, yv_full, 0.01)
    thr_f = threshold_for_fpr(yv_full, full_v[-1], 0.01)
    alarm_fv, tv_f = early_decisions(Sv, rule["hi"], rule["lo"], rule["t_f"])
    out = dict(thr_full=thr_f, Sv=Sv, yv=np.asarray(d_va["y"]), n_neg_v=n_neg_v, n_pos_v=n_pos_v, alarm_fv=alarm_fv, tv_f=tv_f)
    if with_test:  # only the held-out run builds the test objects
        St = det["St"]
        full_t = [scatter(te, d_te["event_id"], St[:, k]) for k in range(len(LENGTHS))]
        pos_idx = {e: i for i, e in enumerate(te.event_id.to_numpy())}
        idx_t = np.array([pos_idx[e] for e in d_te["event_id"]])
        alarm_ft, tt_f = early_decisions(St, rule["hi"], rule["lo"], rule["t_f"])
        out.update(St=St, yt=np.asarray(d_te["y"]), ids_te=np.asarray(d_te["event_id"]), n_neg_t=int((te.y.to_numpy() == 0).sum()), full_alarm_t=(full_t[-1] >= thr_f)[idx_t], alarm_ft=alarm_ft, tt_f=tt_f)
    return out


def fit_tables(D: dict, prm: dict) -> tuple[list, list]:
    pos, neg = D["yv"] == 1, D["yv"] == 0
    edges = [bin_edges(D["Sv"][:, k], prm["nbins"]) for k in range(NCHK)]
    tables = [llr_table(D["Sv"][pos, k], D["Sv"][neg, k], edges[k], prm["smooth"]) for k in range(NCHK)]
    return edges, tables


def dev_run(prm: dict) -> dict:
    D = load(with_test=False)
    edges, tables = fit_tables(D, prm)
    Lv = running_llr(D["Sv"], edges, tables)
    pos, neg = D["yv"] == 1, D["yv"] == 0
    fa_fixed = provisional_fa(D["alarm_fv"], D["tv_f"], neg, D["n_neg_v"])
    a_grid = np.arange(0.5, prm["a_max"] + 1e-9, prm["a_step"])
    b_grid = np.arange(prm["b_min"], 0.5, prm["b_step"])
    prov_f = D["alarm_fv"] & (D["tv_f"] < LENGTHS[-1])
    best = select_AB(Lv, pos, neg, D["n_neg_v"], fa_fixed, a_grid, b_grid, prm["fa_tol"], ref=(D["tv_f"], prov_f) if prm.get("paired") else None)
    sel_f = prov_f & pos
    out = dict(params=prm, fa_fixed_val=fa_fixed, fixed_mean_t_val=float(D["tv_f"][sel_f].mean()), fixed_median_t_val=float(np.median(D["tv_f"][sel_f])), n_alarm_pos_fixed=int(sel_f.sum()),
               n_bins=[len(e) + 1 for e in fit_tables(D, prm)[0]], best=None if best is None else {k: v for k, v in best.items() if k != "key"})
    if best is not None:  # validation versions of the two tested statistics (in-sample for both rules)
        alarm_s, t_s = seq_decisions(Lv, best["A"], best["B"])
        prov_s = alarm_s & (t_s < LENGTHS[-1])
        both = prov_f & prov_s & pos
        fa_v = (full_alarm_from_scores(D["Sv"][:, -1], D))
        out["val_paired_diff_ms"] = float((D["tv_f"][both] - t_s[both]).mean()) if both.any() else None
        out["val_n_both"] = int(both.sum())
        out["val_retraction_fixed"] = retraction_share(prov_f, fa_v)
        out["val_retraction_seq"] = retraction_share(prov_s, fa_v)
    return out


def full_alarm_from_scores(s_full: np.ndarray, D: dict) -> np.ndarray:
    """Full-window (1,800 ms) alarm at the plain 1% threshold of the fixed rule: the 'final' threshold of the rule is not this one, the plain threshold is stored by ``load`` as ``thr_full``."""
    return s_full >= D["thr_full"]


def main() -> None:
    mode = sys.argv[1]
    log = C6.ROOT / "results" / "tables" / "r6_seq_dev_log.json"
    if mode == "dev":
        it = int(sys.argv[2])
        assert 1 <= it <= 5, "at most five development iterations"
        prm = {**DEFAULT, **json.loads(sys.argv[3] if len(sys.argv) > 3 else "{}")}
        cur = json.loads(log.read_text(encoding="utf-8")) if log.exists() else []
        assert len(cur) < 5, "five development iterations are already logged"
        r = dev_run(prm)
        cur.append(dict(iteration=it, **r))
        log.write_text(json.dumps(cur, indent=1), encoding="utf-8")
        print(json.dumps(r, indent=1))
    elif mode == "freeze":
        cur = json.loads(log.read_text(encoding="utf-8"))
        chosen = [e for e in cur if e["iteration"] == int(sys.argv[2])]
        assert len(chosen) == 1, "the iteration label must occur exactly once in the development log"
        chosen = chosen[0]
        prm = dict(chosen["params"], A=chosen["best"]["A"], B=chosen["best"]["B"], iteration=chosen["iteration"])
        C6.freeze_entry("r2", ["src/crashguard/r6_seq.py", "src/crashguard/r5_det.py", "src/crashguard/early.py", "src/crashguard/detector_extra.py", "src/crashguard/windows_cache.py", "src/crashguard/config.py", "data/processed/r5_det_seed42.pkl"], prm, "r6.r2.")
        print("frozen", prm)
    elif mode == "held":
        from crashguard.results import record_many

        prm = C6.check_frozen("r2", "r6.r2.")
        D = load()
        edges, tables = fit_tables(D, prm)
        Lt = running_llr(D["St"], edges, tables)
        half = np.array([C6.half6(e) for e in D["ids_te"]]) == 1
        pos, neg = (D["yt"] == 1)[half], (D["yt"] == 0)[half]
        alarm_s, t_s = seq_decisions(Lt[half], prm["A"], prm["B"])
        alarm_f, t_f = D["alarm_ft"][half], D["tt_f"][half]
        prov_f, prov_s = alarm_f & (t_f < LENGTHS[-1]), alarm_s & (t_s < LENGTHS[-1])
        fa = D["full_alarm_t"][half]
        st = boot_stats(t_f, t_s, prov_f, prov_s, pos, fa)
        src = "src/crashguard/r6_seq.py"
        sel_f, sel_s = prov_f & pos, prov_s & pos
        ent = []

        def add(name, v, unit, note=""):
            ent.append(dict(name=f"r6.r2.{name}", value=(round(v, 6) if isinstance(v, float) else v), unit=unit, origin="MEASURED_SOFTWARE", source_file=src, notes=note))

        add("held.n_events", int(half.sum()), "events", "triggered test events of HALF1 of the hash r6|id (previously evaluated by other hypotheses; V17 section 2)")
        add("held.n_crash", int(pos.sum()), "events")
        add("held.mean_time_fixed_ms", float(t_f[sel_f].mean()), "ms", "crash events with a provisional alarm under the fixed rule")
        add("held.mean_time_seq_ms", float(t_s[sel_s].mean()), "ms", "crash events with a provisional alarm under the sequential rule")
        add("held.median_time_fixed_ms", float(np.median(t_f[sel_f])), "ms")
        add("held.median_time_seq_ms", float(np.median(t_s[sel_s])), "ms", "bounded below by 50 ms; not tested")
        add("held.n_prov_fixed", int(prov_f.sum()), "events")
        add("held.n_prov_seq", int(prov_s.sum()), "events")
        add("held.n_noncrash_prov_fixed", int((prov_f & neg).sum()), "events", "non-crash events with a provisional alarm in the half")
        add("held.n_noncrash_prov_seq", int((prov_s & neg).sum()), "events")
        n_neg_half = int(neg.sum())
        add("held.n_noncrash", n_neg_half, "events", "triggered non-crash events of the half (denominator of the provisional false-alarm rates below)")
        add("held.prov_fa_fixed", float((prov_f & neg).sum()) / max(1, n_neg_half), "fraction", "among triggered non-crash events of the half")
        add("held.prov_fa_seq", float((prov_s & neg).sum()) / max(1, n_neg_half), "fraction", "H-R6-2b is stated at the same rate on validation; the held-out rates are reported, not forced equal")
        fin_s = alarm_s | ((t_s >= LENGTHS[-1]) & fa)  # the sequential rule: early alarm, or the 1,800 ms decision when no early decision was made
        add("held.recall_fixed", float(alarm_f[pos].mean()), "fraction", "triggered crash events of the half with a final alarm")
        add("held.recall_seq", float(fin_s[pos].mean()), "fraction", "same definition; a stop is final")
        add("held.retraction_fixed", retraction_share(prov_f, fa), "fraction")
        add("held.retraction_seq", retraction_share(prov_s, fa), "fraction")
        for k, v in st.items():
            add(f"hR6_2.{k}", v, "ms" if k.startswith("a_") and k != "a_p" else "value")
        okA = st["a_lo"] >= 200.0
        okB = st["b_hi"] <= 0.02
        add("hR6_2a.criterion_met", int(okA), "flag", "lower 95% limit of the mean difference (fixed minus sequential) at least 200 ms")
        add("hR6_2b.criterion_met", int(okB), "flag", "upper 95% limit of the retraction difference at most 0.02")
        add("hR6_2a.p", st["a_p"], "p-value")
        add("hR6_2b.p", st["b_p"], "p-value")
        add("params.A", prm["A"], "LLR")
        add("params.B", prm["B"], "LLR")
        add("params.nbins", prm["nbins"], "bins")
        record_many(ent, purge_prefixes=("r6.r2.",))
        print({e["name"]: e["value"] for e in ent})


if __name__ == "__main__":
    main()
