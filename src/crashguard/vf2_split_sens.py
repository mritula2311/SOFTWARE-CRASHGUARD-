"""D7.4: split sensitivity of the frozen 15-tree forest on VZCrash (DESCRIPTIVE; no hypothesis; keys ``vf2.split.*``).

Three of the four versions already exist in the audit (``vz_leakage``, keys ``vz.v4.rf15.*``): the test set as supplied, with exact copies removed, with exact copies and identical windows removed. They are only read here.
The fourth is ILLUSTRATIVE: a naive random re-split of the TRAIN and VALIDATION events of the supplied release (the test split is not read), 70/15/15 by event drawn at random, the same forest (15 trees), the same
operating points (validation threshold at the F1 maximum, 1% and 5% false-alarm targets on all non-crash events of the pseudo-validation part) and seeds 0 to 4, evaluated on the pseudo-test part.
The pooled train and validation events already hold the cross-split duplicate groups of the release, so the re-split spreads them at random over the three parts instead of keeping the supplied split.
It is not a vehicle-grouped split: VZCrash has no vehicle or trip id, so such a split cannot be built (DATASET_FACTS.md; DECISIONS.md 2026-11-15).

    python -m crashguard.vf2_split_sens
"""
from __future__ import annotations

import numpy as np

from crashguard import boot as B
from crashguard import config as C
from crashguard.detector_extra import fit, score_all, threshold_for_fpr
from crashguard.models import PRIMARY, op_thresholds
from crashguard.results import record_many
from crashguard.s2_dedup import fast_ap
from crashguard.split import load_variant

SRC = "src/crashguard/vf2_split_sens.py"
FRACTIONS = (0.70, 0.15, 0.15)
METS = ("sys_recall", "recall_at_1pct", "recall_at_5pct", "ap", "sys_ap")


def random_split(n: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Random permutation of n events into pseudo-train, pseudo-validation and pseudo-test (70/15/15)."""
    p = np.random.default_rng(1000 + seed).permutation(n)
    a, b = int(round(FRACTIONS[0] * n)), int(round((FRACTIONS[0] + FRACTIONS[1]) * n))
    return p[:a], p[a:b], p[b:]


def stats(y: np.ndarray, trig: np.ndarray, s: np.ndarray, thr: tuple) -> dict:
    pos = y == 1
    f1, t1, t5 = thr
    return dict(sys_recall=float((s[pos] >= f1).mean()), recall_at_1pct=float((s[pos] >= t1).mean()), recall_at_5pct=float((s[pos] >= t5).mean()), ap=fast_ap(y[trig], s[trig]), sys_ap=fast_ap(y, s))


def main() -> None:
    df = load_variant(PRIMARY)
    df["triggered"] = df.triggered.fillna(False).astype(bool)
    pool = df[df.split.isin(["train", "validation"])].reset_index(drop=True)
    ent: list[dict] = []

    def add(name, v, unit, note=""):
        ent.append(dict(name=f"vf2.split.{name}", value=(round(v, 5) if isinstance(v, float) else v), unit=unit, origin="MEASURED_SOFTWARE", source_file=SRC, notes=note))

    per, Sall, parts = [], [], []
    for seed in C.SEEDS:
        i_tr, i_va, i_te = random_split(len(pool), seed)
        tr, va, te = pool.iloc[i_tr], pool.iloc[i_va], pool.iloc[i_te].reset_index(drop=True)
        tr = tr[tr.triggered]
        va_trig = va[va.triggered]
        scorer, _ = fit("rf15", seed, tr, va_trig)
        s_va = score_all(scorer, va)
        thr_f1, _ = op_thresholds(va_trig.y.to_numpy(), scorer(va_trig))
        t1, t5 = (threshold_for_fpr(va.y.to_numpy(), s_va, g) for g in (0.01, 0.05))
        s_te = score_all(scorer, te)
        y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
        per.append(stats(y, trig, s_te, (thr_f1, t1, t5)))
        Sall.append((y, trig, s_te, (thr_f1, t1, t5)))
        parts.append((len(tr), len(va), len(te), int(y.sum())))
        print("seed", seed, {k: round(v, 4) for k, v in per[-1].items()}, flush=True)
    for m in METS:
        add(f"naive_random.{m}", float(np.mean([p[m] for p in per])), "fraction" if "ap" not in m else "AP", "ILLUSTRATIVE naive random re-split of the supplied train and validation events (test split not read), mean over seeds 0 to 4")
    # bootstrap over pseudo-test events (same seed and count as the audit), per seed then averaged
    rng_idx = [list(B._idx(len(s[0]), B.N_BOOT, B.SEED)) for s in Sall]
    for m in ("sys_recall", "recall_at_1pct"):
        d = []
        for b in range(B.N_BOOT):
            d.append(float(np.mean([stats(y[ix[b]], trig[ix[b]], s[ix[b]], thr)[m] for (y, trig, s, thr), ix in zip(Sall, rng_idx)])))
        add(f"naive_random.{m}_lo", float(np.quantile(d, 0.025)), "fraction", "95% bootstrap interval over pseudo-test events (1,000 resamples)")
        add(f"naive_random.{m}_hi", float(np.quantile(d, 0.975)), "fraction", "95% bootstrap interval over pseudo-test events (1,000 resamples)")
    add("naive_random.n_pool", int(len(pool)), "events", "train and validation events of the supplied release")
    add("naive_random.n_pseudo_test_mean", float(np.mean([p[2] for p in parts])), "events", "events in the pseudo-test part (mean over seeds)")
    add("naive_random.n_pseudo_test_crash_mean", float(np.mean([p[3] for p in parts])), "events", "crash events in the pseudo-test part (mean over seeds)")
    record_many(ent, purge_prefixes=("vf2.split.",))
    print({e["name"]: e["value"] for e in ent})


if __name__ == "__main__":
    main()
