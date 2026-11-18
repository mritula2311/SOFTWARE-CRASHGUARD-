"""P4a (docs/02_preregistration/PREREGISTRATION_V4.md section 4): memory-accuracy Pareto of the VZCrash forest.

``sweep``: trees 2 to 10, depth 3 to 9, top-k features (k = 4, 6, 8, 10, 14; ranked on the training split), float and 16-bit thresholds and leaves, 5 seeds. Validation AP and the flash and RAM estimates
only; the configuration is chosen on validation by the preregistered rule and frozen. ``eval``: test scoring of every configuration (Pareto figure), H-P4a on the selected one, measured code size with gcc
(host x86-64, -Os) if usable. Flash and RAM are ANALYTICAL (host arithmetic) unless stated.
"""
from __future__ import annotations

import itertools
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from crashguard import boot as B
from crashguard import config as C
from crashguard import pp_common as PC
from crashguard.detector_extra import frames_full, threshold_for_fpr
from crashguard.s2_dedup import fast_ap
from crashguard.x1_fixedpoint import predict as trav
from crashguard.x1_fixedpoint import quantise

SEEDS = C.SEEDS
TREES, DEPTHS, KS = range(2, 11), range(3, 10), (4, 6, 8, 10, 14)
SRC = "results/tables/p4a_sweep.csv"
NODE_BYTES = {"float": 9, "q16": 7}
WINDOW_BUFFER_BYTES = 280 * 3 * 2
REF = dict(trees=10, depth=9, k=14, q="float")
MARGIN = 0.005


def ram_bytes(k: int) -> int:
    return 4 * k + 4 + 16


def ranking(tr: pd.DataFrame) -> list[str]:
    cols = list(C.FEATURES)
    imp = np.zeros(len(cols))
    for s in SEEDS:
        m = RandomForestClassifier(n_estimators=10, max_depth=9, random_state=s, n_jobs=4).fit(tr[cols].to_numpy(np.float32), tr.y.to_numpy())
        imp += m.feature_importances_
    return [cols[i] for i in np.argsort(-imp, kind="stable")]


_G: dict = {}


def _init(rank: list[str]) -> None:
    tr, va, te = frames_full()
    _G.update(tr=tr, va=va, te=te, rank=rank, with_test=False)


def _one(args) -> list[dict]:
    trees, depth, k, with_test = args
    tr, va, te, rank = _G["tr"], _G["va"], _G["te"], _G["rank"]
    cols = rank[:k]
    Xtr = tr[cols].to_numpy(np.float32)
    lo, hi = Xtr.min(0).astype(np.float64), Xtr.max(0).astype(np.float64)
    vt, tt_ = va.triggered.to_numpy(bool), te.triggered.to_numpy(bool)
    out = []
    per = {"float": [], "q16": []}
    for seed in SEEDS:
        m = RandomForestClassifier(n_estimators=trees, max_depth=depth, random_state=seed, n_jobs=1).fit(Xtr, tr.y.to_numpy())
        nodes = int(sum(e.tree_.node_count for e in m.estimators_))
        q = quantise(m, lo, hi, 16)
        res = {"nodes": nodes}
        for flav in ("float", "q16"):
            Xv = va[cols].to_numpy(np.float32)[vt]
            pv = m.predict_proba(Xv)[:, 1] if flav == "float" else trav(q, Xv.astype(np.float64))
            res[flav] = dict(val_ap=fast_ap(va.y.to_numpy()[vt], pv))
            if with_test:
                sva = np.full(len(va), -1.0)
                sva[vt] = pv
                Xt = te[cols].to_numpy(np.float32)[tt_]
                pt = m.predict_proba(Xt)[:, 1] if flav == "float" else trav(q, Xt.astype(np.float64))
                ste = np.full(len(te), -1.0)
                ste[tt_] = pt
                res[flav].update(t1=threshold_for_fpr(va.y.to_numpy(), sva, 0.01), t5=threshold_for_fpr(va.y.to_numpy(), sva, 0.05), scores=ste)
        per_seed = res
        for flav in ("float", "q16"):
            per[flav].append(per_seed[flav])
        per.setdefault("nodes", []).append(nodes)
    nodes_m = float(np.mean(per["nodes"]))
    for flav in ("float", "q16"):
        rec = dict(trees=trees, depth=depth, k=k, q=flav, nodes=nodes_m, flash_bytes=nodes_m * NODE_BYTES[flav], ram_bytes=ram_bytes(k), val_ap=float(np.mean([r["val_ap"] for r in per[flav]])))
        if with_test:
            rec["_scores"] = [r["scores"] for r in per[flav]]
            rec["_thr"] = [(r["t1"], r["t5"]) for r in per[flav]]
        out.append(rec)
    return out


def run_configs(cfgs: list[tuple], with_test: bool, rank: list[str], workers: int = int(__import__("os").environ.get("PP_WORKERS", 12))) -> list[dict]:
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(rank,)) as ex:
        res = list(ex.map(_one, [(*c, with_test) for c in cfgs], chunksize=2))
    return [r for rr in res for r in rr]


def select(tab: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    ref = tab[(tab.trees == REF["trees"]) & (tab.depth == REF["depth"]) & (tab.k == REF["k"]) & (tab.q == REF["q"])].iloc[0]
    ok = tab[tab.val_ap >= ref.val_ap - MARGIN]
    best = ok.sort_values(["flash_bytes", "ram_bytes", "trees"]).iloc[0]
    return ref, best


def sweep() -> None:
    tr, _va, _te = frames_full()
    rank = ranking(tr)
    cfgs = list(itertools.product(TREES, DEPTHS, KS))
    rows = run_configs(cfgs, False, rank)
    tab = pd.DataFrame(rows)
    tab.to_csv(C.TABLES / "p4a_sweep_validation.csv", index=False)
    ref, best = select(tab)
    print(ref.to_dict(), best.to_dict())
    h = PC.freeze("P4a", dict(rank=rank, reference=dict(trees=int(ref.trees), depth=int(ref.depth), k=int(ref.k), q=ref.q, flash=float(ref.flash_bytes), val_ap=float(ref.val_ap)),
                              selected=dict(trees=int(best.trees), depth=int(best.depth), k=int(best.k), q=best.q, flash=float(best.flash_bytes), val_ap=float(best.val_ap)), margin=MARGIN))
    print("freeze", h)


# ---- measured code size (host gcc) ----
def c_source(m: RandomForestClassifier, cols_idx: list[int], lo: np.ndarray, hi: np.ndarray, flav: str) -> str:
    """Node tables (uint8 feature, float32 or int16 threshold/leaf, int16 children) and a generic traversal; same layout as the analytical estimate (9 or 7 bytes per node)."""
    feat, thr, left, right, roots = [], [], [], [], []
    levels = 65535
    for est in m.estimators_:
        t = est.tree_
        base = len(feat)
        roots.append(base)
        for i in range(t.node_count):
            if t.children_left[i] == -1:
                p = float(t.value[i, 0, 1] / t.value[i, 0].sum())
                feat.append(255)
                thr.append(p if flav == "float" else int(round(p * 32767)))
                left.append(0)
                right.append(0)
            else:
                f = int(t.feature[i])
                v = float(t.threshold[i])
                if flav != "float":
                    span = max(hi[f] - lo[f], 1e-12)
                    v = int(np.clip(round((v - lo[f]) / span * levels), 0, levels)) - 32768
                feat.append(f)
                thr.append(v)
                left.append(base + int(t.children_left[i]))
                right.append(base + int(t.children_right[i]))
    ty = "float" if flav == "float" else "int16_t"
    fmt = (lambda v: (lambda t: t + ("" if any(c in t for c in ".eE") else ".0") + "f")(f"{v:.9g}")) if flav == "float" else (lambda v: str(int(v)))
    s = ["#include <stdint.h>", f"static const uint8_t F[{len(feat)}]={{{','.join(map(str, feat))}}};", f"static const {ty} T[{len(feat)}]={{{','.join(fmt(v) for v in thr)}}};",
         f"static const int16_t L[{len(feat)}]={{{','.join(map(str, left))}}};", f"static const int16_t R[{len(feat)}]={{{','.join(map(str, right))}}};", f"static const int16_t ROOT[{len(roots)}]={{{','.join(map(str, roots))}}};"]
    if flav == "float":
        s.append(f"float predict(const float*x){{float a=0;for(int k=0;k<{len(roots)};k++){{int n=ROOT[k];while(F[n]!=255)n=x[F[n]]<=T[n]?L[n]:R[n];a+=T[n];}}return a/{len(roots)};}}")
    else:
        s.append(f"float predict(const int16_t*x){{int32_t a=0;for(int k=0;k<{len(roots)};k++){{int n=ROOT[k];while(F[n]!=255)n=x[F[n]]<=T[n]?L[n]:R[n];a+=T[n];}}return (float)a/({len(roots)}*32767.0f);}}")
    return "\n".join(s) + "\n"


def measure_size(src: str) -> dict:
    d = Path("build/p4a_size").resolve()
    d.mkdir(parents=True, exist_ok=True)
    (d / "f.c").write_text(src)
    wd = subprocess.run(["wsl", "wslpath", "-a", str(d).replace("\\", "/")], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(["wsl", "bash", "-lc", f"cd '{wd}' && gcc -Os -ffunction-sections -fdata-sections -c f.c -o f.o && size -A f.o"], capture_output=True, text=True)
    if r.returncode != 0:
        return dict(error=(r.stderr or r.stdout)[:200])
    sec = {}
    for ln in r.stdout.splitlines():
        p = ln.split()
        if len(p) >= 2 and p[0].startswith("."):
            sec[p[0]] = int(p[1])
    total = sum(v for k, v in sec.items() if k.startswith((".text", ".rodata", ".data")))
    return dict(sections=sec, bytes=total)


def size_stage() -> None:
    """Measured host code size of the frozen selected and reference configurations (no test data involved). Replaces the NOT_RUN size keys of the eval stage, whose temporary-directory path failed under WSL."""
    import json as _j

    fz = _j.loads((PC.FREEZE_DIR / "p_freeze_P4a.json").read_text(encoding="utf-8"))
    rank, sel, ref = fz["rank"], fz["selected"], fz["reference"]
    tr, _va, _te = frames_full()
    cols_all = list(C.FEATURES)
    E = PC.PEntries("p4a", SRC)
    for nm, key in (("selected", sel), ("reference", ref)):
        cols = rank[: key["k"]]
        Xtr = tr[cols].to_numpy(np.float32)
        m = RandomForestClassifier(n_estimators=key["trees"], max_depth=key["depth"], random_state=0, n_jobs=1).fit(Xtr, tr.y.to_numpy())
        res = measure_size(c_source(m, [cols_all.index(c) for c in cols], Xtr.min(0).astype(float), Xtr.max(0).astype(float), key["q"]))
        if "bytes" in res:
            E.add(f"{nm}.measured_bytes_host_x86_64_Os", res["bytes"], "bytes", "gcc 13.3 -Os under WSL2, host x86-64: text + rodata + data of the node tables and the traversal, seed 0 forest; NOT an ESP32 size. Sections: " + str(res["sections"]), "MEASURED_SOFTWARE")
            E.add(f"{nm}.nodes_seed0", int(sum(e.tree_.node_count for e in m.estimators_)), "nodes", "the forest whose size was measured")
        else:
            E.not_run(f"{nm}.measured_bytes_host_x86_64_Os", "bytes", "gcc under WSL2 failed: " + res["error"])
    # presentational fix: a point value is not an interval
    for k in ("p.p4a.dedup.ap_reference_lo", "p.p4a.dedup.ap_reference_hi", "p.p4a.strict.ap_reference_lo", "p.p4a.strict.ap_reference_hi"):
        pass
    from crashguard.results import RESULTS_PATH
    allr = _j.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    allr = [e for e in allr if e["name"] not in {"p.p4a.dedup.ap_reference_lo", "p.p4a.dedup.ap_reference_hi", "p.p4a.strict.ap_reference_lo", "p.p4a.strict.ap_reference_hi"}]
    RESULTS_PATH.write_text(_j.dumps(allr, indent=2), encoding="utf-8")
    E.flush(purge=("p.p4a.selected.measured_bytes", "p.p4a.reference.measured_bytes", "p.p4a.selected.nodes_seed0", "p.p4a.reference.nodes_seed0"))


def eval_stage() -> None:
    fz = json.loads((PC.FREEZE_DIR / "p_freeze_P4a.json").read_text(encoding="utf-8"))
    h = PC.sealed_gate("P4a")
    rank = fz["rank"]
    sel, ref = fz["selected"], fz["reference"]
    tr, va, te = frames_full()
    flags = pd.read_csv(C.TABLES / "vz_audit_test_near_dup_flags.csv")
    near = set(flags.event_id[flags.flagged_near_duplicate])
    sets = {"dedup": np.ones(len(te), bool), "strict": ~te.event_id.isin(near).to_numpy()}
    y, trig = te.y.to_numpy(), te.triggered.to_numpy(bool)
    cfgs = list(itertools.product(TREES, DEPTHS, KS))
    rows = run_configs(cfgs, True, rank)
    E = PC.PEntries("p4a", SRC)
    E.add("freeze_commit", h, "commit", "commit of the freeze of P4a")
    keep, tab_rows = {}, []
    for r in rows:
        sc, thr = r.pop("_scores"), r.pop("_thr")
        pos = y == 1
        ap = np.mean([fast_ap(y[trig], s[trig]) for s in sc])
        rec1 = np.mean([float((s[pos] >= t[0]).mean()) for s, t in zip(sc, thr)])
        rec5 = np.mean([float((s[pos] >= t[1]).mean()) for s, t in zip(sc, thr)])
        tab_rows.append(dict(**r, test_ap=float(ap), test_recall_1pct=float(rec1), test_recall_5pct=float(rec5)))
        key = (r["trees"], r["depth"], r["k"], r["q"])
        if key in {(sel["trees"], sel["depth"], sel["k"], sel["q"]), (ref["trees"], ref["depth"], ref["k"], ref["q"])}:
            keep[key] = (sc, thr)
    T = pd.DataFrame(tab_rows)
    T.to_csv(C.TABLES / "p4a_sweep.csv", index=False)
    ks, kr = (sel["trees"], sel["depth"], sel["k"], sel["q"]), (ref["trees"], ref["depth"], ref["k"], ref["q"])
    for nm, key in (("selected", ks), ("reference", kr)):
        r = T[(T.trees == key[0]) & (T.depth == key[1]) & (T.k == key[2]) & (T.q == key[3])].iloc[0]
        E.add(f"{nm}.config", f"trees {key[0]}, depth {key[1]}, k {key[2]}, {key[3]}", "config")
        E.add(f"{nm}.flash_bytes", round(float(r.flash_bytes), 1), "bytes", "nodes x bytes per node (9 float32, 7 for 16-bit), seed mean; host arithmetic", "ANALYTICAL")
        E.add(f"{nm}.ram_bytes", int(r.ram_bytes), "bytes", f"4 per feature + 4 + 16 loop state; plus a configuration-independent window buffer of {WINDOW_BUFFER_BYTES} bytes", "ANALYTICAL")
        E.add(f"{nm}.nodes", round(float(r.nodes), 1), "nodes")
        E.add(f"{nm}.val_ap", round(float(r.val_ap), 5), "AP", "validation, 5-seed mean")
    E.add("flash_ratio_selected_over_reference", round(float(T[(T.trees == ks[0]) & (T.depth == ks[1]) & (T.k == ks[2]) & (T.q == ks[3])].flash_bytes.iloc[0] / T[(T.trees == kr[0]) & (T.depth == kr[1]) & (T.k == kr[2]) & (T.q == kr[3])].flash_bytes.iloc[0]), 4), "ratio", "", "ANALYTICAL")
    E.add("n_configurations", int(len(T)), "configurations", "trees 2 to 10 x depth 3 to 9 x k in {4, 6, 8, 10, 14} x {float, 16-bit}")
    # paired bootstrap over test events, 5-seed mean
    for sname, which in sets.items():
        def stat(idx: np.ndarray, which=which) -> tuple[float, float]:
            sel_i = idx[which[idx]]
            yy, tt = y[sel_i], trig[sel_i]
            a = np.mean([fast_ap(yy[tt], s[sel_i][tt]) for s in keep[kr][0]])
            b = np.mean([fast_ap(yy[tt], s[sel_i][tt]) for s in keep[ks][0]])
            return a, b
        pt = stat(np.arange(len(te)))
        d = np.array([(lambda ab: ab[0] - ab[1])(stat(i)) for i in B._idx(len(te), B.N_BOOT, B.SEED)])
        loss = pt[0] - pt[1]
        E.add(f"{sname}.ap_reference", round(pt[0], 5), "AP", "5-seed mean")
        E.add(f"{sname}.ap_selected", round(pt[1], 5), "AP", "5-seed mean")
        E.ci(f"{sname}.ap_loss", (loss, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "AP", "reference minus selected; paired bootstrap over test events", d=5)
        if sname == "dedup":
            hi = float(np.quantile(d, 0.975))
            ok = (E.items and True) and hi <= 0.01
            fr = float(T[(T.trees == ks[0]) & (T.depth == ks[1]) & (T.k == ks[2]) & (T.q == ks[3])].flash_bytes.iloc[0] / T[(T.trees == kr[0]) & (T.depth == kr[1]) & (T.k == kr[2]) & (T.q == kr[3])].flash_bytes.iloc[0])
            E.add("hP4a.flash_condition_met", int(fr <= 0.5), "flag", "selected flash at most half of the reference", "ANALYTICAL")
            E.add("hP4a.ap_condition_met", int(hi <= 0.01), "flag", "upper 95% bound of the AP loss at most 0.01")
            E.add("hP4a.criterion_met", int(ok and fr <= 0.5), "flag")
            E.add("hP4a.p_raw", round(PC.p_above(d, 0.01), 4), "probability", "share of resamples with AP loss at or above 0.01; floor 0.001")
            print("H-P4a loss", round(loss, 5), "hi", round(hi, 5), "flash ratio", round(fr, 3))
    # recall at the targets for the two
    for nm, key in (("selected", ks), ("reference", kr)):
        sc, thr = keep[key]
        pos = y == 1
        E.add(f"{nm}.test_recall_1pct", round(float(np.mean([(s[pos] >= t[0]).mean() for s, t in zip(sc, thr)])), 4), "fraction", "de-duplicated test set, 5-seed mean")
        E.add(f"{nm}.test_recall_5pct", round(float(np.mean([(s[pos] >= t[1]).mean() for s, t in zip(sc, thr)])), 4), "fraction")
    E.not_run("measured_bytes_esp32", "bytes", "no microcontroller cross compiler and no emlearn were available in this environment; only the host (x86-64) size and the analytical estimate are given")
    E.flush()
    PC.time_log("P4a", "test scoring done once for the sweep; freeze commit " + h[:8])


if __name__ == "__main__":
    {"sweep": sweep, "eval": eval_stage, "size": size_stage}[sys.argv[1]]()
