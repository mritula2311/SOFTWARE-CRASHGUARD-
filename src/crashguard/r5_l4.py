"""L4 (docs/02_preregistration/PREREGISTRATION_V16.md section 6): deadline-optimal spreading-factor ladder (SIMULATED and ANALYTICAL).

    python -m crashguard.r5_l4 analytic     # analytical attempt counts and the planner (keys r5.l4.analytic.*)
    python -m crashguard.r5_l4 dev0         # development seeds 401 to 420: Z0 and quick on all 30 cells (defines the edge cells)
    python -m crashguard.r5_l4 dev <it>     # development iteration of the ladder (k, M0) on the edge cells
    python -m crashguard.r5_l4 freeze
    python -m crashguard.r5_l4 held         # held-out seeds 501 to 540, once, all 30 cells; keys r5.l4.ns3.*

Policies run in the ns-3 application (``xsim/ns3/xsim_alert.cc``, policies ``z0`` and ``l4``; the earlier policies are byte-identical, see ``scripts/r5_ns3_identity.sh``). Output is SIMULATED. The start
spreading factor uses a link-margin estimate that equals the true margin plus a Gaussian error of 2 dB (V16 section 0 point 6). Real traces cannot change the spreading factor: no trace result is claimed.
Runs go through ``wsl`` in the foreground (no detached jobs).
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from crashguard import lora

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed" / "r5_l4_out"
JOBS = ROOT / "data" / "processed" / "r5_l4_jobs"
NS_BIN = "./build/scratch/ns3.48-xsim_alert-optimized"
RADII = (1000, 1500, 2000, 2500, 3000)
SETTINGS = {"calib": 0, "shipped": 1}
LOSSES = (0.0, 0.1, 0.3)
N_VEH, RATE, DUTY = 60, 10, 0.01
DEV_SEEDS, HELD_SEEDS = range(401, 421), range(501, 541)
SEED, NB = 42, 2000
EDGE_LO, EDGE_HI = 0.30, 0.95
DEADLINE_S, T_FIRST, RX_S, MAX_TRIES, ALERT_LEN = 10.0, 0.35, 0.32, 12, 97
SENS_DBM = (-123.0, -126.0, -129.0, -132.0, -134.5, -137.0)
SIGMA_DB = 2.0
WORKERS = 14
JOB_SCRIPT = """#!/bin/bash
# usage: job.sh <jobfile> ; each line: outfile|args
cd ~/ns3work/ns-3-dev
while IFS='|' read -r out args; do
  {NS} $args > "$out" 2>/dev/null
done < "$1"
"""


@dataclass(frozen=True)
class L4Params:
    k: int = 2  # development item: failed rounds per spreading-factor step
    m0: float = 3.0  # development item: required estimated margin (dB) at the start spreading factor
    err: float = 2.0  # error of the margin estimate (dB), an assumption (V16 section 0)


ITERATIONS = [L4Params(), L4Params(k=1), L4Params(k=3), L4Params(m0=0.0), L4Params(m0=6.0)]


# ------------------------------------------------------------------------------------------------ analytical part
def air_s(sf: int, nbytes: int = ALERT_LEN) -> float:
    return lora.airtime_ms(nbytes, sf) / 1000.0


def sf_at_round(s0: int, k: int, r: int) -> int:
    """Spreading factor of the attempt after ``r`` failed rounds: one step up after every ``k`` rounds, at most SF12."""
    return min(12, s0 + r // k)


def attempt_schedule(s0: int, k: int, deadline: float = DEADLINE_S, t_first: float = T_FIRST, max_tries: int = MAX_TRIES, limit_air_s: float | None = None) -> list[tuple[float, int]]:
    """Planned attempts (start time after the crash, spreading factor) of the ladder with zero spacing: each attempt starts when the previous receive windows end (airtime + 0.32 s), and only attempts that
    end by the deadline are planned, at most ``max_tries``, within the airtime budget ``limit_air_s`` (the duty limit)."""
    out, t, used = [], t_first, 0.0
    for r in range(max_tries):
        sf = sf_at_round(s0, k, r)
        a = air_s(sf)
        if t + a > deadline + 1e-12:
            break
        if limit_air_s is not None and used + a > limit_air_s + 1e-12:
            break
        out.append((t, sf))
        used += a
        t += a + RX_S
    return out


def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def uplink_success(margin7_db: float, p: float, sf: int, sf_base: int = 7, sigma: float = SIGMA_DB) -> float:
    """Probability that one uplink is received: the margin at SF ``sf`` is the margin at the base SF plus the sensitivity gain; fading of ``sigma`` dB per packet; the extra loss p is scaled by 0.7 per step above the base."""
    m = margin7_db + (SENS_DBM[0] - SENS_DBM[min(5, max(0, sf - 7))])
    return float((1.0 - p * 0.7 ** max(0, sf - sf_base)) * phi(m / sigma))


def expected_delivery(margin7_db: float, p: float, s0: int, k: int, **kw) -> float:
    """Expected delivery within the deadline of the planned ladder: one minus the product of the failure probabilities of the planned uplinks (the schedule before the initial success does not depend on any
    acknowledgement). Collisions are not modelled."""
    q = 1.0
    for _t, sf in attempt_schedule(s0, k, **kw):
        q *= 1.0 - uplink_success(margin7_db, p, sf)
    return 1.0 - q


def plan(margin7_db: float, p: float, ks: tuple = (1, 2, 3), **kw) -> tuple[int, int, float]:
    """(start SF, k, expected delivery) that maximises the expected delivery within the deadline; ties go to the lower start SF, then the smaller k."""
    best = None
    for s0 in range(7, 13):
        for k in ks:
            e = expected_delivery(margin7_db, p, s0, k, **kw)
            if best is None or e > best[2] + 1e-12:
                best = (s0, k, e)
    return best  # type: ignore[return-value]


def start_sf_from_margin(est_margin7_db: float, m0: float, sf_base: int = 7) -> int:
    """The rule of the ns-3 policy: the lowest SF at or above the base whose estimated margin is at least ``m0`` (SF12 if none)."""
    for s in range(sf_base, 13):
        if est_margin7_db + (SENS_DBM[0] - SENS_DBM[s - 7]) >= m0:
            return s
    return 12


# ------------------------------------------------------------------------------------------------ ns-3 runs
def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return "/mnt/" + s[0].lower() + s[2:]


def args_for(radius: int, sh: int, p: float, pol: str, seed: int, prm: L4Params | None) -> str:
    a = f"--n={N_VEH} --sf=7 --p={p:g} --radius={radius} --rate={RATE} --duty={DUTY:g} --seed={seed} --policy={pol} --sensShipped={sh}"
    if pol == "l4" and prm:
        a += f" --l4k={prm.k} --l4m0={prm.m0:g} --l4err={prm.err:g}"
    return a


def fname(d: Path, radius: int, st: str, p: float, pol: str, seed: int) -> Path:
    return d / f"r{radius}_{st}_p{p:g}_{pol}_{seed}.txt"


def run_jobs(jobs: list[tuple[Path, str]]) -> None:
    JOBS.mkdir(parents=True, exist_ok=True)
    jobs = [(f, a) for f, a in jobs if not (f.exists() and f.stat().st_size > 0)]
    print("ns-3 jobs", len(jobs), flush=True)
    if not jobs:
        return
    (JOBS / "job.sh").write_bytes(JOB_SCRIPT.replace("{NS}", NS_BIN).encode("utf-8"))
    procs = []
    for k in range(WORKERS):
        ch = jobs[k::WORKERS]
        if not ch:
            continue
        jf = JOBS / f"jobs_{k}.txt"
        jf.write_bytes(("\n".join(f"{wsl_path(o)}|{a}" for o, a in ch) + "\n").encode("utf-8"))
        procs.append(subprocess.Popen(["wsl", "-d", "Ubuntu", "--", "bash", wsl_path(JOBS / "job.sh"), wsl_path(jf)]))
    for pr in procs:
        pr.wait()
    print("done", flush=True)


def load_run(f: Path) -> dict | None:
    """Per-run result: delivery within 10 s over the events that were not dropped, and the invariants. None for an empty output (an ns-3 crash)."""
    if not f.exists() or f.stat().st_size == 0:
        return None
    delays, inv, dropped, duty = [], (0, 0), 0, (0.0, 1.0)
    for line in f.read_text().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == "EV":
            d = float(t[3])
            if d == -2.0:
                dropped += 1
            else:
                delays.append(d)
        elif t[0] == "L4INV":
            inv = (int(t[1]), int(t[2]))
        elif t[0] == "DUTY":
            duty = (float(t[1]), float(t[2]))
        elif t[0] == "DROPPED":
            dropped = max(dropped, int(t[1]))
    d = np.array(delays)
    if not len(d):
        return None
    return dict(deliv=float(((d >= 0) & (d <= DEADLINE_S)).mean()), n=int(len(d)), inv=(inv[0], inv[1] + int(duty[0] > duty[1] + 1e-6)), dropped=dropped)


def cell_runs(d: Path, radius: int, st: str, p: float, pols: tuple, seeds) -> dict:
    """Paired runs: seeds for which every policy of ``pols`` has an output (a crashed run is dropped for all)."""
    got = {pol: {s: load_run(fname(d, radius, st, p, pol, s)) for s in seeds} for pol in pols}
    ok = [s for s in seeds if all(got[pol][s] is not None for pol in pols)]
    return dict(seeds=ok, **{pol: np.array([got[pol][s]["deliv"] for s in ok]) for pol in pols}, inv=[got[pol][s]["inv"] for pol in pols if pol in ("z0", "l4") for s in ok], n_dropped=len(seeds) - len(ok))


def cells() -> list[tuple[int, str, float]]:
    return [(r, st, p) for r in RADII for st in SETTINGS for p in LOSSES]


# ------------------------------------------------------------------------------------------------ statistics
def paired_boot_mean(diffs: np.ndarray, seed: int = SEED, nb: int = NB) -> dict:
    """Mean of per-run paired differences with a 95% interval over runs; one-sided p of H0: mean <= 0."""
    diffs = np.asarray(diffs, float)
    rng = np.random.default_rng(seed)
    m = diffs[rng.integers(0, len(diffs), (nb, len(diffs)))].mean(1)
    return dict(pt=float(diffs.mean()), lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), p=float(((m <= 0).sum() + 1) / (nb + 1)), n=int(len(diffs)))


def pooled_edge_boot(cell_diffs: dict, seed: int = SEED, nb: int = NB) -> dict:
    """Mean over the edge cells of the cell mean difference. ``cell_diffs`` maps a cell to an array indexed by seed position (NaN where the run was dropped); seeds are resampled jointly across the cells
    (cluster bootstrap over runs) and a dropped run is ignored in its cell only."""
    M = np.stack([np.asarray(v, float) for v in cell_diffs.values()])  # (cells, seeds)
    n = M.shape[1]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, (nb, n))
    m = np.nanmean(np.stack([np.nanmean(M[:, i], axis=1) for i in idx]), axis=1)
    pt = float(np.nanmean(np.nanmean(M, axis=1)))
    return dict(pt=pt, lo=float(np.quantile(m, 0.025)), hi=float(np.quantile(m, 0.975)), p=float(((m <= 0).sum() + 1) / (nb + 1)), n_cells=len(M), n_runs=int(n))


def edge_cells(dev_z0: dict) -> list[tuple]:
    return [c for c, v in dev_z0.items() if EDGE_LO <= v <= EDGE_HI]


# ------------------------------------------------------------------------------------------------ drivers
def _dev0() -> None:
    from crashguard import r5_common as R5

    OUT_D = OUT / "dev"
    OUT_D.mkdir(parents=True, exist_ok=True)
    jobs = [(fname(OUT_D, r, st, p, pol, s), args_for(r, SETTINGS[st], p, pol, s, None)) for (r, st, p) in cells() for pol in ("z0", "quick") for s in DEV_SEEDS]
    run_jobs(jobs)
    z0 = {}
    for (r, st, p) in cells():
        cr = cell_runs(OUT_D, r, st, p, ("z0", "quick"), DEV_SEEDS)
        z0[(r, st, p)] = float(cr["z0"].mean()) if len(cr["z0"]) else float("nan")
    ec = edge_cells(z0)
    (R5.TABLES / "r5_l4_dev_cells.json").write_text(json.dumps(dict(z0={f"{k[0]}|{k[1]}|{k[2]}": v for k, v in z0.items()}, edge=[f"{k[0]}|{k[1]}|{k[2]}" for k in ec], rule="V16 6.2: Z0 delivery within 10 s on the development seeds between 0.30 and 0.95"), indent=1), encoding="utf-8")
    print("edge cells", len(ec), "of", len(z0))


def _edge_from_file() -> list[tuple]:
    from crashguard import r5_common as R5

    d = json.loads((R5.TABLES / "r5_l4_dev_cells.json").read_text(encoding="utf-8"))
    return [(int(a), b, float(c)) for a, b, c in (x.split("|") for x in d["edge"])]


def _dev(it: int) -> None:
    from crashguard import r5_common as R5

    prm = ITERATIONS[it]
    OUT_D = OUT / "dev" / f"it{it}"
    OUT_D.mkdir(parents=True, exist_ok=True)
    ec = _edge_from_file()
    base = OUT / "dev"
    run_jobs([(fname(OUT_D, r, st, p, "l4", s), args_for(r, SETTINGS[st], p, "l4", s, prm)) for (r, st, p) in ec for s in DEV_SEEDS])
    diffs, worst = {}, 0.0
    for (r, st, p) in ec:
        a = {s: load_run(fname(OUT_D, r, st, p, "l4", s)) for s in DEV_SEEDS}
        b = {s: load_run(fname(base, r, st, p, "z0", s)) for s in DEV_SEEDS}
        ok = [s for s in DEV_SEEDS if a[s] is not None and b[s] is not None]
        d = np.array([a[s]["deliv"] - b[s]["deliv"] for s in ok])
        diffs[(r, st, p)] = d
        worst = min(worst, float(d.mean()))
    mean_edge = float(np.mean([v.mean() for v in diffs.values()]))
    log_p = R5.TABLES / "r5_l4_dev_log.json"
    log = json.loads(log_p.read_text(encoding="utf-8")) if log_p.exists() else {}
    log[str(it)] = dict(params=asdict(prm), mean_edge_gain=mean_edge, worst_edge_cell=worst, n_edge_cells=len(ec))
    log_p.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(it, asdict(prm), "mean gain over edge cells", round(mean_edge, 4), "worst cell", round(worst, 4))


def _freeze() -> None:
    from crashguard import r5_common as R5

    log = json.loads((R5.TABLES / "r5_l4_dev_log.json").read_text(encoding="utf-8"))
    best = max(log, key=lambda i: (round(log[i]["mean_edge_gain"], 9), -log[i]["params"]["k"], -int(i)))
    d = R5.freeze_entry("l4", ["src/crashguard/r5_l4.py", "xsim/ns3/xsim_alert.cc", "src/crashguard/lora.py"], log[best]["params"], ["results/tables/r5_l4_dev_cells.json"])
    (R5.TABLES / "r5_l4_dev_choice.json").write_text(json.dumps(dict(chosen=int(best), params=log[best]["params"], rule="V16 6.3: highest mean development gain over the edge cells; ties go to the smaller k"), indent=1), encoding="utf-8")
    print("chosen iteration", best, "frozen", d["params_sha256"][:16])


def _held() -> None:
    from crashguard import r5_common as R5

    prm = L4Params(**R5.check_frozen("l4"))
    OUT_H = OUT / "held"
    OUT_H.mkdir(parents=True, exist_ok=True)
    jobs = []
    for (r, st, p) in cells():
        for s in HELD_SEEDS:
            jobs.append((fname(OUT_H, r, st, p, "z0", s), args_for(r, SETTINGS[st], p, "z0", s, None)))
            jobs.append((fname(OUT_H, r, st, p, "l4", s), args_for(r, SETTINGS[st], p, "l4", s, prm)))
            jobs.append((fname(OUT_H, r, st, p, "quick", s), args_for(r, SETTINGS[st], p, "quick", s, None)))
    run_jobs(jobs)
    ec = _edge_from_file()
    rec = R5.Rec("r5.l4.ns3.", "src/crashguard/r5_l4.py", "SIMULATED")
    cell_d, cell_lo, inv_bad, n_runs_total, n_drop = {}, {}, 0, 0, 0
    for (r, st, p) in cells():
        cr = cell_runs(OUT_H, r, st, p, ("z0", "l4", "quick"), HELD_SEEDS)
        d = cr["l4"] - cr["z0"]
        b = paired_boot_mean(d)
        full = np.full(len(HELD_SEEDS), np.nan)
        for sd, v in zip(cr["seeds"], d):
            full[list(HELD_SEEDS).index(sd)] = v
        cell_d[(r, st, p)] = full
        cell_lo[(r, st, p)] = b["lo"]
        inv_bad += int(sum(a + c for a, c in cr["inv"]))
        n_runs_total += len(cr["seeds"])
        n_drop += cr["n_dropped"]
        key = f"cell.r{r}.{st}.p{p:g}"
        rec.add(f"{key}.z0", float(cr["z0"].mean()), "fraction", "delivery within 10 s, Z0 (SF7, zero spacing)")
        rec.add(f"{key}.l4", float(cr["l4"].mean()), "fraction", "delivery within 10 s, ladder")
        rec.add(f"{key}.quick", float(cr["quick"].mean()), "fraction", "descriptive baseline: the repository's quick policy")
        rec.add(f"{key}.diff", b["pt"], "fraction", "ladder minus Z0, paired by seed")
        rec.add(f"{key}.diff_lo", b["lo"], "fraction", "95% bootstrap interval over runs")
        rec.add(f"{key}.diff_hi", b["hi"], "fraction")
        rec.add(f"{key}.n_runs", len(cr["seeds"]), "runs", "paired runs (an empty output drops the seed for all policies)")
    pooled = pooled_edge_boot({c: cell_d[c] for c in ec})
    worst_ok = all(v >= -0.01 for v in cell_lo.values())
    met = bool(pooled["pt"] >= 0.03 and pooled["lo"] > 0 and worst_ok)
    rec.add("edge.n_cells", len(ec), "cells", "cells whose development Z0 delivery lies between 0.30 and 0.95")
    rec.add("edge.mean_diff", pooled["pt"], "fraction", "mean over the edge cells of ladder minus Z0")
    rec.add("edge.mean_diff_lo", pooled["lo"], "fraction", "95% interval, runs resampled jointly across the edge cells")
    rec.add("edge.mean_diff_hi", pooled["hi"], "fraction")
    rec.add("edge.worst_cell_lo", float(min(cell_lo.values())), "fraction", "smallest lower limit over all 30 cells")
    rec.add("invariant.violations", inv_bad, "count", "transmissions ending after the deadline or beyond the duty limit (must be 0)")
    rec.add("runs.paired_total", n_runs_total, "runs")
    rec.add("runs.dropped_total", n_drop, "runs", "seeds dropped because an output was empty")
    rec.add("hL4.ns3.criterion_met", int(met), "bool", "mean edge gain at least 0.03 with lower limit above 0 and no cell with a lower limit below -0.01")
    rec.add("hL4.ns3.p", pooled["p"], "p", "one-sided cluster-bootstrap p of H0: mean edge gain at most 0")
    rec.add("hL4.custom.criterion_met", "NOT_RUN", "text", "the custom-simulator part is not run in this session; H-L4 is therefore ns-3 only and goes to the supplement (V16 6.2, G0 rule 4)", origin="NOT_RUN")
    rec.write()
    print(json.dumps(dict(pooled=pooled, worst_lo=min(cell_lo.values()), met=met, inv_bad=inv_bad, n_edge=len(ec)), indent=1, default=float))


def _analytic() -> None:
    from crashguard import r5_common as R5

    rec = R5.Rec("r5.l4.analytic.", "src/crashguard/r5_l4.py", "ANALYTICAL")
    for sf in range(7, 13):
        rec.add(f"air_s.sf{sf}", air_s(sf), "s", "time on air of the 97-byte alert (lora.airtime_ms)")
        n = len(attempt_schedule(sf, 99))
        rec.add(f"attempts_fixed.sf{sf}", n, "attempts", "attempts that end within 10 s at a fixed SF with zero spacing (first send at 0.35 s, 0.32 s receive windows, at most 12)")
    for k in (1, 2, 3):
        rec.add(f"attempts_ladder.k{k}", len(attempt_schedule(7, k)), "attempts", "attempts of the ladder started at SF7 (at most 12)")
    for m in (-6.0, -3.0, 0.0, 3.0):
        s0, k, e = plan(m, 0.1)
        rec.add(f"plan.margin{m:+g}.start_sf", s0, "SF", f"planner optimum at an SF7 margin of {m:+g} dB and extra loss 0.1")
        rec.add(f"plan.margin{m:+g}.k", k, "rounds")
        rec.add(f"plan.margin{m:+g}.expected_delivery", e, "fraction", "collisions not modelled")
    rec.write()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dev":
        _dev(int(sys.argv[2]))
    else:
        {"analytic": _analytic, "dev0": _dev0, "freeze": _freeze, "held": _held}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
