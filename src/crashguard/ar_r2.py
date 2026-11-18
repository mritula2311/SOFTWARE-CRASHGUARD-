"""R2 (H-R2a, H-R2b): security-airtime co-design. Frame length and tag length against time on air (ANALYTICAL), forgery effort (ANALYTICAL) and burst delivery (SIMULATED).

Design and criteria: docs/02_preregistration/PREREGISTRATION_V11.md section 4, R2. Frames of 24, 32, 40, 56, 97 bytes (total on-air bytes including the tag) and tags of 4, 6, 7, 8, 12 bytes; feasible if
frame minus tag is at least 16 bytes. Delivery: the burst simulator of Block A (`world_sim`, policy P4+lbt, the best earlier policy of `pa_design.json`), metric `reach10_critical`, with the alert length set to
the frame length (the flash and the ACK scale with the tag as in `fin_g.lens`). DESIGN grid: the 16 burst cells of `pa_sim.DESIGN_A` (b = 20), 20 hours per cell, seed 16000 + h. HELD-OUT grid: the 16 burst
cells of `pa_sim.HELD_A` (b = 30), 30 hours per cell, seed 18000 + h. The candidate among {24/8, 32/7, 32/8, 40/7, 40/8} is chosen on the design grid. Keys ``ar.r2.*``.

    python -m crashguard.ar_r2
"""
from __future__ import annotations

import functools
import math

import numpy as np
import pandas as pd
from scipy.stats import binom

from crashguard import fin_g as G
from crashguard import fin_sim as FS
from crashguard import pa_sim as A
from crashguard import s11_sct as S11
from crashguard.lora import airtime_ms
from crashguard.results import record_many

SRC = "src/crashguard/ar_r2.py"
S11.n16_params = functools.lru_cache(maxsize=None)(S11.n16_params)  # make_cfg re-reads the 35 MB results.json on every call otherwise
FRAMES = (24, 32, 40, 56, 97)
TAGS = (4, 6, 7, 8, 12)
MIN_FIELDS = 16
CAND = ((24, 8), (32, 7), (32, 8), (40, 7), (40, 8))
BASE_FRAME = (97, 8)
DES_HOURS, HELD_HOURS = 20, 30


def feasible() -> list[tuple[int, int]]:
    return [(f, t) for f in FRAMES for t in TAGS if f - t >= MIN_FIELDS]


def forgery(t: int) -> tuple[float, float]:
    """log2 attempts for success probability 1e-6, and log2 expected attempts (ANALYTICAL, as E2)."""
    return 8 * t + math.log2(1e-6), 8 * t - 1.0


def over(f: int, t: int) -> dict:
    return dict(alert_len=f, flash_len=max(14 - 8 + t, 6), ack_len=26 - 8 + t)


def jobs_for(g: dict, frames: list, hours: int, pools, t, kind: str = "P4+lbt") -> list:
    spec = dict(kind=kind)
    out = []
    for cell in A.cells(g):
        if cell["b"] <= 1:
            continue
        w = A.spec_world(spec, cell)
        for fr in frames:
            for h in range(hours):
                c = G.cfg_for(A.spec_pol(spec), cell, g["seed"], h, pools, t, f"r2_{cell['name']}", w, None, over(*fr))
                out.append((c, dict(cell=cell["name"], n=cell["n"], p=cell["p"], sf=cell["sf"], duty=cell["duty"], b=cell["b"], pol=f"{fr[0]}/{fr[1]}", hour=h)))
    return out


def cell_stats(R: pd.DataFrame, names: list[str], a: str, b: str, metric: str = "reach10_critical") -> list[dict]:
    out = []
    for nm in names:
        sub = R[R.cell == nm]
        pa = sub[sub.pol == a].sort_values("hour")[metric].to_numpy(float)
        pb = sub[sub.pol == b].sort_values("hour")[metric].to_numpy(float)
        m = ~(np.isnan(pa) | np.isnan(pb))
        out.append(dict(cell=nm, **FS.boot_diff(pb[m] - pa[m], 0.05)))
    return out


def main() -> None:
    import json

    pools = A.pools_real()
    t = FS.tuned()
    des = json.loads((A.OUT / "pa_design.json").read_text(encoding="utf-8"))
    assert des["best_earlier"] == "P4+lbt"
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"ar.r2.{name}", value=value, unit=unit, origin=origin, source_file=SRC, notes=notes))

    # analytical table
    for f, tg in feasible():
        lo, ex = forgery(tg)
        for sf in (7, 8, 9, 10):
            add(f"table.f{f}_t{tg}.airtime_ms_sf{sf}", round(airtime_ms(f, sf), 2), "ms", "LoRa time on air, 125 kHz, CR 4/5 (lora.airtime_ms)", "ANALYTICAL")
        add(f"table.f{f}_t{tg}.log2_attempts_1e6", round(lo, 2), "log2", "forgery attempts for success probability 1e-6 (truncated HMAC, secret key)", "ANALYTICAL")
        add(f"table.f{f}_t{tg}.log2_expected_attempts", round(ex, 2), "log2", "expected forgery attempts", "ANALYTICAL")
    # design grid: candidate choice
    frames = [BASE_FRAME, *CAND]
    Rd = FS.run_jobs(jobs_for(A.DESIGN_A, frames, DES_HOURS, pools, t))
    dnames = sorted(Rd.cell.unique())
    gains = {}
    for c in CAND:
        st = cell_stats(Rd, dnames, f"{BASE_FRAME[0]}/{BASE_FRAME[1]}", f"{c[0]}/{c[1]}")
        gains[c] = float(np.mean([s["pt"] for s in st]))
        add(f"design.{c[0]}_{c[1]}.mean_gain_reach10_critical", round(gains[c], 5), "fraction", "mean over the 16 design burst cells of (frame minus 97/8), paired by hour, P4+lbt")
    chosen = max(gains, key=gains.get)
    add("design.chosen", f"{chosen[0]}/{chosen[1]}", "frame/tag", "candidate with the largest mean gain on the design grid")
    # held-out: all feasible frames
    allf = feasible()
    Rh = FS.run_jobs(jobs_for(A.HELD_A, allf, HELD_HOURS, pools, t))
    # context: Tamang-style slots at 97/8 and the best earlier policy are in pa_held; run Tamang at 97/8 here with the same seeds
    spec_t = dict(kind="tamang", k_cap=des["tamang_k_cap"])
    Rt = []
    for cell in A.cells(A.HELD_A):
        if cell["b"] <= 1:
            continue
        w = A.spec_world(spec_t, cell)
        for h in range(HELD_HOURS):
            c = G.cfg_for(A.spec_pol(spec_t), cell, A.HELD_A["seed"], h, pools, t, f"r2_{cell['name']}", w, None, over(*BASE_FRAME))
            Rt.append((c, dict(cell=cell["name"], n=cell["n"], p=cell["p"], sf=cell["sf"], duty=cell["duty"], b=cell["b"], pol="tamang_97/8", hour=h)))
    Rtam = FS.run_jobs(Rt)
    hnames = sorted(Rh.cell.unique())
    Rh.to_csv("results/tables/ar_r2_held.csv", index=False)
    base = f"{BASE_FRAME[0]}/{BASE_FRAME[1]}"
    per_frame = {}
    for f, tg in allf:
        nm = f"{f}/{tg}"
        sub = Rh[Rh.pol == nm]
        st = cell_stats(Rh, hnames, base, nm) if nm != base else None
        mean_reach = float(sub.reach10_critical.mean())
        sf_mean_air = float(np.mean([airtime_ms(f, int(s)) for s in sub.sf]))
        lo, ex = forgery(tg)
        per_frame[nm] = dict(reach=mean_reach, air=sf_mean_air, forg=lo, stats=st)
        add(f"held.{f}_{tg}.reach10_critical_mean", round(mean_reach, 5), "fraction", "mean over the 16 held-out burst cells and 30 hours, P4+lbt")
        add(f"held.{f}_{tg}.airtime_ms_mean", round(sf_mean_air, 2), "ms", "mean time on air over the cells' spreading factors", "ANALYTICAL")
        if st:
            add(f"held.{f}_{tg}.gain_vs_97_8.mean", round(float(np.mean([s["pt"] for s in st])), 5), "fraction", "mean over cells of (frame minus 97/8), paired by hour")
            add(f"held.{f}_{tg}.gain_vs_97_8.cells_gain5", int(sum(FS.gains(s, 0.05) for s in st)), "cells", "cells with point gain >= 0.05 and the paired 95% interval above zero")
            add(f"held.{f}_{tg}.gain_vs_97_8.cells_lose2", int(sum(FS.loses(s) for s in st)), "cells", "cells with point loss of more than 0.02")
    tam = float(Rtam.reach10_critical.mean())
    add("held.tamang_97_8.reach10_critical_mean", round(tam, 5), "fraction", "context: Tamang-style slots at 97/8, K from the design of Block A (oracle burst size)")
    # H-R2a
    stc = per_frame[f"{chosen[0]}/{chosen[1]}"]["stats"]
    n_gain = int(sum(FS.gains(s, 0.05) for s in stc))
    p_a = float(binom.sf(n_gain - 1, 16, 0.5))
    add("hR2a.chosen_frame", f"{chosen[0]}/{chosen[1]}", "frame/tag", "chosen on the design grid")
    add("hR2a.cells_gain5_of_16", n_gain, "cells", "held-out burst cells where the chosen frame gains >= 5 points over 97/8 (paired interval above zero)")
    add("hR2a.mean_gain", round(float(np.mean([s["pt"] for s in stc])), 5), "fraction", "mean gain over the 16 held-out cells")
    add("hR2a.criterion_met", int(n_gain >= 8), "flag", "at least 8 of 16 cells")
    add("hR2a.p_raw", round(p_a, 6), "p", "exact binomial P(X >= cells; 16, 0.5)")
    # H-R2b: a frame with tag >= 8 that dominates 97/8 (shorter time on air, delivery not worse by more than 0.01, forgery effort at least equal)
    dom = []
    for nm, v in per_frame.items():
        f, tg = (int(x) for x in nm.split("/"))
        if nm == base or tg < 8 or v["stats"] is None:
            continue
        mean_gain = float(np.mean([s["pt"] for s in v["stats"]]))
        pooled = np.concatenate([Rh[(Rh.pol == nm) & (Rh.cell == c)].sort_values("hour").reach10_critical.to_numpy(float) - Rh[(Rh.pol == base) & (Rh.cell == c)].sort_values("hour").reach10_critical.to_numpy(float) for c in hnames])
        pooled = pooled[~np.isnan(pooled)]
        rng = np.random.default_rng(42)
        lo_ = float(np.quantile(pooled[rng.integers(0, len(pooled), (1000, len(pooled)))].mean(axis=1), 0.025))
        if v["air"] < per_frame[base]["air"] and v["forg"] >= per_frame[base]["forg"] and lo_ >= -0.01:
            dom.append((nm, mean_gain, lo_))
        add(f"held.{f}_{tg}.dominates_97_8", int(nm in [d[0] for d in dom]), "flag", f"pooled paired difference lower bound {lo_:.4f}; dominates if airtime shorter, forgery effort at least equal and the lower bound >= -0.01")
    add("hR2b.dominating_frames", ", ".join(d[0] for d in dom) or "none", "frames", "frames with tag >= 8 that dominate 97/8 on the held-out grid")
    add("hR2b.criterion_met", int(len(dom) > 0), "flag", "97/8 is dominated by at least one frame with tag >= 8")
    add("hR2b.p_raw", 0.0 if dom else 1.0, "p", "0 if met, 1 if not (a Pareto statement)")
    # Pareto set among tags >= 7
    pts = [(nm, v["forg"], v["air"], v["reach"]) for nm, v in per_frame.items() if int(nm.split("/")[1]) >= 7]
    pareto = []
    for a in pts:
        dominated = any((b[1] >= a[1] and b[2] <= a[2] and b[3] >= a[3]) and (b[1] > a[1] or b[2] < a[2] or b[3] > a[3]) for b in pts if b is not a)
        if not dominated:
            pareto.append(a[0])
    add("hR2b.pareto_set_tag_ge7", ", ".join(pareto), "frames", "point-estimate Pareto set (forgery effort, time on air, mean delivery) among frames with tag >= 7; for the plot and the reading only")
    record_many(ent, purge_prefixes=("ar.r2.",))
    print("chosen", chosen, gains)
    print("n_gain", n_gain, "p", p_a, "dom", dom, "pareto", pareto, "tamang", tam, "base", per_frame[base]["reach"])
    print({nm: round(v["reach"], 3) for nm, v in per_frame.items()})


if __name__ == "__main__":
    main()
