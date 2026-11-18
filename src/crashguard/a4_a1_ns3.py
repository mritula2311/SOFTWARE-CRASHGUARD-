"""A1 in ns-3 (docs/02_preregistration/PREREGISTRATION_V15.md section 2): runs of the policy ``r3a`` and the analysis of H-A1a and the ns-3 cells of H-A1c. Keys ``a4.a1.ns3.*``.

    python -m crashguard.a4_a1_ns3 dev <iteration>   # development seeds 101 to 120, SF9, both settings, losses 0 and 0.3; iteration parameters from results/tables/a4_dev_params.json
    python -m crashguard.a4_a1_ns3 run               # held-out: seeds 1 to 60, 16 cells, frozen parameters (results/tables/a4_frozen.json); r3s and r3t outputs of paper-v1 are reused
    python -m crashguard.a4_a1_ns3 analyse           # cluster bootstrap over runs, H-A1a and the ns-3 cells of H-A1c

The ns-3 settings are those of PREREGISTRATION_V13 (60 vehicles in a disc of 1,500 m, 10 events per vehicle-hour, ADR and application backoff off, duty 1%). ns-3 output is SIMULATED.
Runs go through ``wsl`` in the foreground (no detached jobs).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import pp_r3_ns3 as P1
from crashguard import rd_firmware as F

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/a4_a1_ns3.py"
OUT = ROOT / "data" / "processed" / "a4_ns3_out"
OUT_DEV = ROOT / "data" / "processed" / "a4_ns3_dev"
JOBS = ROOT / "data" / "processed" / "a4_ns3_jobs"
FROZEN = ROOT / "results" / "tables" / "a4_frozen.json"
DEV_PARAMS = ROOT / "results" / "tables" / "a4_dev_params.json"
SEEDS = 60
DEV_SEEDS = range(101, 121)
NB, SEED = 2000, 42
WORKERS = 14
LIMIT_AIR = 0.40
MARGIN_DD = -0.01


def args_for(sf: int, sh: int, p: float, pol: str, seed: int, prm: dict | None) -> str:
    a = f"--n={P1.N_VEH} --sf={sf} --p={p:g} --radius={P1.RADIUS} --rate={P1.RATE} --duty=0.01 --seed={seed} --policy={pol} --events={F.wsl_path(P1.EVENTS)} --sensShipped={sh}"
    if pol == "r3a" and prm:
        a += f" --provGap={prm['gap']:g} --reserve={prm['reserve']} --afterConfirm={int(prm['after_confirm'])}"
    return a


def run_jobs(jobs: list[tuple[Path, str]]) -> None:
    JOBS.mkdir(parents=True, exist_ok=True)
    jobs = [(f, a) for f, a in jobs if not (f.exists() and f.stat().st_size > 0)]
    print("ns-3 jobs", len(jobs), flush=True)
    if not jobs:
        return
    (JOBS / "job.sh").write_bytes(P1.JOB_SCRIPT.replace("{NS}", P1.NS_BIN).encode("utf-8"))
    procs = []
    for k in range(WORKERS):
        ch = jobs[k::WORKERS]
        if not ch:
            continue
        jf = JOBS / f"jobs_{k}.txt"
        jf.write_bytes(("\n".join(f"{F.wsl_path(o)}|{a}" for o, a in ch) + "\n").encode("utf-8"))
        procs.append(subprocess.Popen(["wsl", "-d", "Ubuntu", "--", "bash", F.wsl_path(JOBS / "job.sh"), F.wsl_path(jf)]))
    for pr in procs:
        pr.wait()
    print("done", flush=True)


def fn(d: Path, sf: int, st: str, p: float, pol: str, seed: int) -> Path:
    return d / f"sf{sf}_{st}_p{p:g}_{pol}_{seed}.txt"


def dev(it: int) -> None:
    prm = json.loads(DEV_PARAMS.read_text(encoding="utf-8"))[str(it)]
    P1.make_events()
    d = OUT_DEV / f"it{it}"
    d.mkdir(parents=True, exist_ok=True)
    base = OUT_DEV / "base"
    base.mkdir(parents=True, exist_ok=True)
    jobs = []
    for st, sh in P1.SETTINGS.items():
        for p in (0.0, 0.3):
            for s in DEV_SEEDS:
                jobs.append((fn(d, 9, st, p, "r3a", s), args_for(9, sh, p, "r3a", s, prm)))
                for pol in ("r3s", "r3t"):
                    jobs.append((fn(base, 9, st, p, pol, s), args_for(9, sh, p, pol, s, None)))
    run_jobs(jobs)


def run() -> None:
    prm = json.loads(FROZEN.read_text(encoding="utf-8"))["a1"]
    P1.make_events()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = []
    for sf in P1.SFS:
        for st, sh in P1.SETTINGS.items():
            for p in P1.LOSSES:
                for s in range(1, SEEDS + 1):
                    jobs.append((fn(OUT, sf, st, p, "r3a", s), args_for(sf, sh, p, "r3a", s, prm)))
    run_jobs(jobs)


def load_inv(f: Path) -> tuple[int, int]:
    for line in f.read_text().splitlines():
        t = line.split()
        if t and t[0] == "A1INV":
            return int(t[1]), int(t[2])
    return -1, -1


def two_stage_delivered(d: pd.DataFrame, suf: str) -> pd.Series:
    g = lambda c: d[c + suf]  # noqa: E731
    return (g("alert") >= 0) | ((g("E") == 1) & (g("F") == 0) & (g("flash") >= 0) & (g("cancel") == 0)) | ((g("E") == 1) & (g("F") == 1) & (g("flash") >= 0))


def run_stats3(s: pd.DataFrame, t: pd.DataFrame, a: pd.DataFrame) -> dict:
    """Per-run quantities of the three paired runs (same seed, same event table): single stage (s), round-3 two stage (t), A1 (a)."""
    m = s.add_suffix("_s").rename(columns={"k_s": "k"}).merge(t.add_suffix("_t").rename(columns={"k_t": "k"}), on="k").merge(a.add_suffix("_a").rename(columns={"k_a": "k"}), on="k")
    ok = (m.dropped_s == 0) & (m.dropped_t == 0) & (m.dropped_a == 0)
    n_drop = int((~ok).sum())
    m = m[ok]
    cr = m[m.y_s == 1]
    del_s = int(((cr.F_s == 1) & (cr.alert_s >= 0)).sum())
    pv = m[m.E_a == 1]
    return dict(air_s=float(m.air_s.sum()), air_t=float(m.air_t.sum()), air_a=float(m.air_a.sum()), n_cr=int(len(cr)), del_s=del_s,
                del_t=int(two_stage_delivered(cr, "_t").sum()), del_a=int(two_stage_delivered(cr, "_a").sum()),
                n_E=int(len(pv)), prov_a=int((pv.flash_a >= 0).sum()), prov_t=int((m[m.E_t == 1].flash_t >= 0).sum()), n_ev=int(len(s)), n_drop=n_drop)


def boot_cell(runs: list[dict], rng: np.random.Generator) -> dict:
    n = len(runs)
    idx = rng.integers(0, n, (NB, n))
    A = {k: np.array([r[k] for r in runs], float) for k in ("air_s", "air_t", "air_a", "n_cr", "del_t", "del_a", "del_s", "n_E", "prov_a", "prov_t")}
    ratio = A["air_a"][idx].sum(1) / A["air_s"][idx].sum(1) - 1.0
    dd = (A["del_a"][idx].sum(1) - A["del_t"][idx].sum(1)) / A["n_cr"][idx].sum(1)
    ratio_r3 = A["air_t"][idx].sum(1) / A["air_s"][idx].sum(1) - 1.0
    pv = A["prov_a"][idx].sum(1) / A["n_E"][idx].sum(1) - A["prov_t"][idx].sum(1) / A["n_E"][idx].sum(1)
    pt = lambda k: float(A[k].sum())  # noqa: E731
    return dict(n=n, ratio_pt=pt("air_a") / pt("air_s") - 1.0, ratio=ratio, ratio_r3_pt=pt("air_t") / pt("air_s") - 1.0, ratio_r3=ratio_r3,
                dd_pt=(pt("del_a") - pt("del_t")) / pt("n_cr"), dd=dd, prov_diff_pt=pt("prov_a") / pt("n_E") - pt("prov_t") / pt("n_E"), prov_diff=pv,
                deliv_t=pt("del_t") / pt("n_cr"), deliv_a=pt("del_a") / pt("n_cr"), deliv_s=pt("del_s") / pt("n_cr"), prov_a=pt("prov_a") / pt("n_E"), prov_t=pt("prov_t") / pt("n_E"), n_cr=int(pt("n_cr")))


def cell_runs(sf: int, st: str, p: float, d_a: Path, d_b: Path, seeds, ev: pd.DataFrame) -> tuple[list[dict], dict]:
    runs, info = [], dict(bad=0, inv_late=0, inv_duty=0, max_duty=0.0, drop=0, n_ev=0)
    for s in seeds:
        fs, ft, fa = fn(d_b, sf, st, p, "r3s", s), fn(d_b, sf, st, p, "r3t", s), fn(d_a, sf, st, p, "r3a", s)
        if not all(f.exists() and f.stat().st_size > 0 for f in (fs, ft, fa)):
            info["bad"] += 1  # an ns-3 crash (empty output): the seed is dropped for all three policies
            continue
        a_, du1, _ = P1.load(fs, ev)
        b_, du2, _ = P1.load(ft, ev)
        c_, du3, _ = P1.load(fa, ev)
        late, duty = load_inv(fa)
        info["inv_late"] += max(late, 0)
        info["inv_duty"] += max(duty, 0)
        info["inv_missing"] = info.get("inv_missing", 0) + int(late < 0)
        info["max_duty"] = max(info["max_duty"], du1, du2, du3)
        st_ = run_stats3(a_, b_, c_)
        info["drop"] += st_["n_drop"]
        info["n_ev"] += st_["n_ev"]
        runs.append(st_)
    return runs, info


def analyse(d_a: Path = OUT, d_b: Path = P1.OUT, seeds=range(1, SEEDS + 1), cells=None, prefix: str = "a4.a1.ns3.", record: bool = True) -> dict:
    from crashguard.results import record_many

    ev = pd.read_csv(P1.EVENTS, sep=" ", header=None, names=["E", "F", "y", "tE"])
    rng = np.random.default_rng(SEED)
    ent: list[dict] = []

    def add(name, value, unit, notes=""):
        ent.append(dict(name=f"{prefix}{name}", value=round(value, 6) if isinstance(value, float) else value, unit=unit, origin="SIMULATED", source_file=SRC, notes=notes))

    out: dict = dict(cells={})
    cells = cells or [(sf, st, p) for sf in P1.SFS for st in P1.SETTINGS for p in P1.LOSSES]
    a_tests, c_tests = [], []
    for sf, st, p in cells:
        runs, info = cell_runs(sf, st, p, d_a, d_b, seeds, ev)
        cn = f"sf{sf}.{st}.p{p:g}"
        if not runs:
            out["cells"][cn] = None
            if sf == 9:
                a_tests.append((cn, False, 1.0))
            c_tests.append((cn, False, 1.0))
            continue
        c = boot_cell(runs, rng)
        reliable = info["drop"] / max(info["n_ev"], 1) <= P1.MAX_DROP
        out["cells"][cn] = dict(c=c, info=info, reliable=reliable)
        add(f"{cn}.n_runs", len(runs), "runs", "runs used (a seed with an empty output is dropped for all three policies)")
        add(f"{cn}.extra_air_ratio", c["ratio_pt"], "ratio", "A1 two-stage transmit airtime over single-stage airtime minus 1 (ratio of sums over runs)")
        add(f"{cn}.extra_air_ratio_hi", float(np.quantile(c["ratio"], 0.975)), "ratio", "95% cluster bootstrap upper limit over runs, 2,000 resamples, seed 42")
        add(f"{cn}.extra_air_ratio_r3", c["ratio_r3_pt"], "ratio", "the same ratio for the round-3 two-stage alert on the same seeds (paper-v1 outputs)")
        add(f"{cn}.delivery_diff", c["dd_pt"], "fraction", "A1 minus round-3 two-stage event delivery of crash events")
        add(f"{cn}.delivery_diff_lo", float(np.quantile(c["dd"], 0.025)), "fraction", "95% cluster bootstrap lower limit")
        add(f"{cn}.delivery_a1", c["deliv_a"], "fraction", f"A1 event delivery over {c['n_cr']} crash events")
        add(f"{cn}.delivery_r3", c["deliv_t"], "fraction", "round-3 two-stage event delivery, same events")
        add(f"{cn}.prov_delivery_a1", c["prov_a"], "fraction", "share of early-alarm events whose provisional frame is received (descriptive; the ns-3 events are those of the table)")
        add(f"{cn}.prov_delivery_r3", c["prov_t"], "fraction", "same for the 14-byte flash of round 3")
        add(f"{cn}.dropped_share", info["drop"] / max(info["n_ev"], 1), "fraction", "events dropped in at least one of the three runs")
        add(f"{cn}.inv_late", info["inv_late"], "count", "provisional frames that ended after the deadline (must be 0)")
        add(f"{cn}.inv_duty", info["inv_duty"], "count", "provisional frames sent above the duty limit (must be 0)")
        add(f"{cn}.max_phy_airtime_hour_s", round(info["max_duty"], 4), "s", "largest trailing-hour PHY airtime of any vehicle in the cell (limit 36 s)")
        if sf == 9:
            met = bool(np.quantile(c["ratio"], 0.975) < LIMIT_AIR) and reliable
            a_tests.append((cn, met, (int((c["ratio"] >= LIMIT_AIR).sum()) + 1) / (NB + 1)))
        metc = bool(np.quantile(c["dd"], 0.025) >= MARGIN_DD) and reliable
        c_tests.append((cn, metc, (int((c["dd"] < MARGIN_DD).sum()) + 1) / (NB + 1)))
    ha = dict(met=bool(a_tests) and all(m for _n, m, _p in a_tests) and len(a_tests) == 8, p=max([x[2] for x in a_tests] or [1.0]), cells={n: m for n, m, _p in a_tests})
    hc = dict(met=bool(c_tests) and all(m for _n, m, _p in c_tests) and len(c_tests) == 16, p=max([x[2] for x in c_tests] or [1.0]), cells={n: m for n, m, _p in c_tests})
    add("hA1a.criterion_met", int(ha["met"]), "flag", "all eight SF9 cells have an upper 95% limit of the extra airtime below 0.40")
    add("hA1a.p_raw", ha["p"], "p", "largest cell p (share of resamples with the extra airtime at or above 0.40, plus one over resamples plus one)")
    add("hA1c.ns3.criterion_met", int(hc["met"]), "flag", "all sixteen ns-3 cells have a lower 95% limit of (A1 minus round-3 delivery) of at least -0.01")
    add("hA1c.ns3.p_raw", hc["p"], "p", "largest cell p of the ns-3 cells")
    for n, m, p_ in a_tests:
        add(f"hA1a.cell.{n}.met", int(m), "flag", f"extra airtime upper limit below 0.40; cell p {p_:.5f}")
    for n, m, p_ in c_tests:
        add(f"hA1c.cell.{n}.met", int(m), "flag", f"delivery difference lower limit at least -0.01; cell p {p_:.5f}")
    out["hA1a"], out["hA1c_ns3"] = ha, hc
    if record:
        record_many(ent, purge_prefixes=(prefix,))
        (ROOT / "results" / "tables" / "a4_a1_ns3_summary.json").write_text(json.dumps(dict(hA1a=ha, hA1c=hc), indent=1, default=str), encoding="utf-8")
    return out


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dev":
        dev(int(sys.argv[2]))
    elif cmd == "run":
        run()
    elif cmd == "analyse":
        o = analyse()
        print("H-A1a", o["hA1a"]["met"], o["hA1a"]["p"], "H-A1c ns-3", o["hA1c_ns3"]["met"], o["hA1c_ns3"]["p"])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
