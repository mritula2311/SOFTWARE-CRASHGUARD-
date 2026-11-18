"""Z0 (docs/02_preregistration/PREREGISTRATION_V4.md): the pooled NHTSA records and the sealed split.

Pool = the 176 tests of N13/N14 without the two duplicated channels (tests 3668 and 3904 each appear twice with different vehicle labels; the row whose label is not the struck vehicle is dropped after checking that
the two signals are identical) plus the 739 held-out records of T13a. Modes: frontal barrier (0 degrees, 116 tests), side (impactor at 270 degrees, the original side tests), pole (vehicle into pole, any angle) and
other (every other configuration of T13a). Groups = make and the leading word of the model (a conservative merge of variants such as COROLLA and COROLLA HYBRID; DECISIONS.md). Split: development 60%, validation
20%, SEALED test 20% by records, whole groups together, stratified by the primary mode of the group, seed 42.

Run: ``python -m crashguard.pp_pool`` writes data/processed/pp_pool.joblib (signals, git-ignored) and docs/05_data_code/SEALED_SPLIT.md (group hashes, counts).
"""
from __future__ import annotations

import hashlib
from collections import Counter

import joblib
import numpy as np
import pandas as pd

from crashguard import config as C
from crashguard import severity_study as SS
from crashguard import t13_heldout as H

CACHE = C.PROCESSED / "pp_pool.joblib"
SEED = 42
FRACS = (0.6, 0.2, 0.2)
FOLDS = ("dev", "val", "test")
DUP = {3668: "IIHS", 3904: "OTHER"}  # test -> make label of the row that duplicates the struck vehicle's channel


def group_key(make: str, model: str) -> str:
    mk = " ".join(str(make).upper().split())
    md = " ".join(str(model).upper().split())
    return f"{mk}|{md.split(' ')[0] if md else ''}"


def mode_of(t: dict) -> str:
    if t.get("kind") == "frontal":
        return "frontal_barrier"
    if t.get("kind") == "side":
        return "side"
    m = t["mode"]
    return "pole" if m.startswith("VEHICLE INTO POLE") else "other"


def build_pool() -> tuple[list[dict], dict]:
    old = SS.load_tests()
    cnt: dict = dict(n_original=len(old))
    drop = []
    for tn, lab in DUP.items():
        rows = [i for i, t in enumerate(old) if t["test_no"] == tn]
        bad = [i for i in rows if old[i]["group"].upper().startswith(lab)]
        good = [i for i in rows if i not in bad]
        assert len(rows) == 2 and len(bad) == 1 and len(good) == 1, (tn, rows, bad)
        a, b = old[bad[0]]["sig"]["acc"], old[good[0]]["sig"]["acc"]
        assert a.shape == b.shape and float(np.abs(np.asarray(a) - np.asarray(b)).max()) == 0.0, f"test {tn}: the two signals differ"
        drop += bad
    old = [t for i, t in enumerate(old) if i not in drop]
    cnt["n_original_after_dedup"] = len(old)
    new, c2 = H.build_set()
    cnt.update({f"t13a_{k}": v for k, v in c2.items()})
    pool = []
    for t in old:
        mk, md = t["group"].split("|")[:2]
        pool.append(dict(rid=f"{t['test_no']}-{t['kind']}", test_no=t["test_no"], src="original", mode=mode_of(t), mode_raw=t["kind"], group=group_key(mk, md), group_full=t["group"], v=t["v"], ref=float(t["ref_dv"]), sig=t["sig"]))
    for t in new:
        mk, md = t["group"].split("|")[:2]
        pool.append(dict(rid=f"{t['test_no']}-{t['vrole']}", test_no=t["test_no"], src="t13a", mode=mode_of(t), mode_raw=t["mode"], group=group_key(mk, md), group_full=t["group"], v=t["v"], ref=float(t["ref_dv"]), sig=t["sig"]))
    assert len({p["rid"] for p in pool}) == len(pool), "record ids are not unique"
    cnt["n_pool"] = len(pool)
    return pool, cnt


def assign_folds(pool: list[dict]) -> dict[str, str]:
    """group -> fold. Groups of one primary mode are shuffled (seed 42) and cut at 60% and 80% of that stratum's records."""
    by_g: dict[str, list[int]] = {}
    for i, p in enumerate(pool):
        by_g.setdefault(p["group"], []).append(i)
    order = {m: i for i, m in enumerate(("side", "frontal_barrier", "other", "pole"))}  # rarest mode wins ties
    prim = {}
    for g, idx in by_g.items():
        c = Counter(pool[i]["mode"] for i in idx)
        prim[g] = sorted(c, key=lambda m: (-c[m], order[m]))[0]
    rng = np.random.default_rng(SEED)
    fold_of: dict[str, str] = {}
    for m in ("side", "frontal_barrier", "other", "pole"):
        gs = sorted(g for g in by_g if prim[g] == m)
        gs = [gs[j] for j in rng.permutation(len(gs))]
        n_rec = sum(len(by_g[g]) for g in gs)
        cum = 0
        for g in gs:
            mid = cum + len(by_g[g]) / 2.0
            fold_of[g] = "dev" if mid < FRACS[0] * n_rec else ("val" if mid < (FRACS[0] + FRACS[1]) * n_rec else "test")
            cum += len(by_g[g])
    return fold_of


def load() -> dict:
    """Pooled records (with signals) and the fold of each: dict(pool=list, fold=np.array of 'dev'/'val'/'test'). Builds and caches on the initial call."""
    if CACHE.exists():
        return joblib.load(CACHE)
    pool, cnt = build_pool()
    fo = assign_folds(pool)
    d = dict(pool=pool, fold=np.array([fo[p["group"]] for p in pool]), counts=cnt)
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    joblib.dump(d, CACHE)
    return d


def table(d: dict) -> pd.DataFrame:
    return pd.DataFrame(dict(rid=[p["rid"] for p in d["pool"]], test_no=[p["test_no"] for p in d["pool"]], src=[p["src"] for p in d["pool"]], mode=[p["mode"] for p in d["pool"]],
                             group=[p["group"] for p in d["pool"]], v=[p["v"] for p in d["pool"]], ref=[p["ref"] for p in d["pool"]], fold=d["fold"]))


def h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def write_doc(d: dict) -> None:
    T = table(d)
    T["cls"] = [C.SEV_NAMES[i] for i in np.searchsorted(np.array(C.SEV_DV_KMH), T.ref, side="right")]
    L = ["# Sealed split of the pooled NHTSA records (Z0)", "",
         "Written before any model of the positive-results push was fitted (see `docs/02_preregistration/PREREGISTRATION_V4.md`). **The SEALED fold is scored once per hypothesis**, after the model and its settings are frozen in a commit; "
         "every scoring is logged in `results/tables/p_sealed_access.csv` (hypothesis, time, freeze commit).", "",
         "## What is pooled", "",
         f"- The {d['counts']['n_original']} rows of the N13/N14 set, minus the two duplicated rows of tests 3668 and 3904 (same channel loaded twice under a wrong vehicle label; the signals were checked to be identical) = {d['counts']['n_original_after_dedup']} records.",
         f"- The {d['counts']['t13a_n_used']} held-out records of T13a (`t13.heldout.*`; selection rules in `docs/07_log/DECISIONS.md`).",
         f"- **{len(T)} records in {T.group.nunique()} make-and-model groups.** Reference delta-V is the N13 reference; classes use the limits 24, 40 and 56 km/h (Low, Moderate, Severe, Critical).", "",
         "Modes: frontal barrier = the original frontal tests (barrier at 0 degrees); side = the original left-side tests (impactor at 270 degrees); pole = vehicle into pole at any angle; other = every other configuration of T13a "
         "(oblique barrier, vehicle into vehicle, impactor at another angle). The mode is the crash configuration of the test record; a deployed node does not know it (Z1).", "",
         "Group key = make and the leading word of the model name (upper case), a conservative merge of variants of one vehicle (for example COROLLA and COROLLA HYBRID go to one group). "
         "Split: groups are shuffled with seed 42 inside the stratum of their primary mode and cut at 60% and 80% of the stratum's records; all records of a group are in one fold.", "",
         "## Records by fold and mode", ""]
    ct = pd.crosstab(T["fold"].map(dict(zip(FOLDS, ("development", "validation", "SEALED test")))), T["mode"]).reindex(["development", "validation", "SEALED test"])[list(("frontal_barrier", "pole", "side", "other"))]
    ct["all"] = ct.sum(axis=1)
    ct.loc["all"] = ct.sum()
    L += ["| fold | frontal barrier | pole | side | other | all |", "|---|---|---|---|---|---|"] + [f"| {i} | " + " | ".join(str(int(v)) for v in r) + " |" for i, r in ct.iterrows()] + ["", "## Records by fold and class", ""]
    cc = pd.crosstab(T["fold"].map(dict(zip(FOLDS, ("development", "validation", "SEALED test")))), T["cls"]).reindex(["development", "validation", "SEALED test"])[list(C.SEV_NAMES)]
    L += ["| fold | " + " | ".join(C.SEV_NAMES) + " |", "|---|---|---|---|---|"] + [f"| {i} | " + " | ".join(str(int(v)) for v in r) + " |" for i, r in cc.iterrows()] + ["", "## Groups by fold", ""]
    for f, nm in zip(FOLDS, ("development", "validation", "SEALED test")):
        gs = sorted(T[T.fold == f].group.unique())
        L += [f"- **{nm}**: {len(gs)} groups, {int((T.fold == f).sum())} records. Digest of the sorted group keys (SHA-256 of the keys joined by newlines): `{h(chr(10).join(gs))}`"]
    L += ["", "To check a fold, rebuild the group keys with `crashguard.pp_pool.group_key` and compare the digest and the per-group hashes below (SHA-256 of the key, leading 12 hex characters).", ""]
    for f, nm in zip(FOLDS, ("development", "validation", "SEALED test")):
        gs = sorted(T[T.fold == f].group.unique())
        L += [f"### {nm} group hashes ({len(gs)})", "", " ".join(h(g)[:12] for g in sorted(gs, key=lambda g: h(g))), ""]
    L += ["## Sealed-fold scorings", "", "The log is `results/tables/p_sealed_access.csv`; each row names the hypothesis, the time and the commit of the freeze that fixed its model and settings. The table is filled by `crashguard.pp_common.sealed_gate` and copied here by `crashguard.pp_docs`.", ""]
    open("docs/05_data_code/SEALED_SPLIT.md", "w", encoding="utf-8").write("\n".join(L))


def main() -> None:
    d = load()
    T = table(d)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    T.drop(columns=["ref"]).to_csv(C.TABLES / "p_pool_folds.csv", index=False)  # fold assignment without labels
    write_doc(d)
    print(d["counts"])
    print(pd.crosstab(T.fold, T["mode"]))
    print(T.groupby("fold").group.nunique())


if __name__ == "__main__":
    main()
