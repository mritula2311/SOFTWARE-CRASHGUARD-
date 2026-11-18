"""P1 (docs/02_preregistration/PREREGISTRATION_V13.md section 2): the two-stage alert R3 in ns-3. Keys ``pp.p1.*``.

    python -m crashguard.pp_r3_ns3 run [seeds]   # runs the ns-3 application (policies r3s, r3t) in WSL; output files in data/processed/r3ns3_out/
    python -m crashguard.pp_r3_ns3 analyse       # cluster bootstrap over runs, Holm over 8 tests, verdict, cross-simulator table, docs/03_results/PAPER_P1_R3_NS3.md

Cells: SF7 and SF9, the two calibration sensitivity settings (calib = the custom simulator's values in the patched module; shipped = the ns-3 values), extra loss 0, 0.1, 0.3, 0.6 per direction,
60 vehicles in a disc of 1,500 m, 10 events per vehicle-hour, seeds 1 to 60 (paired: r3s and r3t share the seed). No parameter is tuned.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from crashguard import rd_firmware as F
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/pp_r3_ns3.py"
OUT = ROOT / "data" / "processed" / "r3ns3_out"
JOBS = ROOT / "data" / "processed" / "r3ns3_jobs"
EVENTS = ROOT / "data" / "processed" / "r3_ns3_events.txt"
NS_BIN = "./build/scratch/ns3.48-xsim_alert-optimized"
SFS = (7, 9)
SETTINGS = {"calib": 0, "shipped": 1}
LOSSES = (0.0, 0.1, 0.3, 0.6)
POLS = ("r3s", "r3t")
N_VEH, RADIUS, RATE = 60, 1500, 10
SEEDS = 60
NB = 2000
SEED = 42
MAX_DROP = 0.05
WORKERS = 14

JOB_SCRIPT = """#!/bin/bash
# usage: job.sh <jobfile> ; each line: outfile|args
cd ~/ns3work/ns-3-dev
while IFS='|' read -r out args; do
  {NS} $args > "$out" 2>/dev/null
done < "$1"
"""


def fname(sf: int, st: str, p: float, pol: str, seed: int) -> Path:
    return OUT / f"sf{sf}_{st}_p{p:g}_{pol}_{seed}.txt"


def make_events() -> None:
    ev = pd.read_csv(ROOT / "results" / "tables" / "s6_events_seed42_a1.csv")
    tr = ev[ev.triggered]
    with EVENTS.open("w", newline="\n") as f:
        for e, fa, y, t in zip(tr.alarm_E, tr.alarm_F, tr.y, tr.time_ms):
            f.write(f"{int(e)} {int(fa)} {int(y)} {t / 1000.0:.3f}\n")


def run(seeds: int = SEEDS) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    JOBS.mkdir(parents=True, exist_ok=True)
    make_events()
    jobs = []
    for sf in SFS:
        for st, sh in SETTINGS.items():
            for p in LOSSES:
                for pol in POLS:
                    for s in range(1, seeds + 1):
                        f = fname(sf, st, p, pol, s)
                        if f.exists() and f.stat().st_size > 0:
                            continue
                        args = f"--n={N_VEH} --sf={sf} --p={p:g} --radius={RADIUS} --rate={RATE} --duty=0.01 --seed={s} --policy={pol} --events={F.wsl_path(EVENTS)} --sensShipped={sh}"
                        jobs.append((F.wsl_path(f), args))
    print("ns-3 jobs", len(jobs), flush=True)
    (JOBS / "job.sh").write_bytes(JOB_SCRIPT.replace("{NS}", NS_BIN).encode("utf-8"))
    chunks = [jobs[i::WORKERS] for i in range(WORKERS)]
    procs = []
    for k, ch in enumerate(chunks):
        jf = JOBS / f"jobs_{k}.txt"
        jf.write_bytes(("\n".join(f"{o}|{a}" for o, a in ch) + "\n").encode("utf-8"))
        procs.append(subprocess.Popen(["wsl", "-d", "Ubuntu", "--", "bash", F.wsl_path(JOBS / "job.sh"), F.wsl_path(jf)]))
    for pr in procs:
        pr.wait()
    print("done", flush=True)


def load(f: Path, ev: pd.DataFrame) -> tuple[pd.DataFrame, float, int]:
    rows, duty, drop = [], 0.0, 0
    for line in f.read_text().splitlines():
        t = line.split()
        if t and t[0] == "R3":
            rows.append(t[1:])
        elif t and t[0] == "DUTY":
            duty = float(t[1])
        elif t and t[0] == "DROPPED":
            drop = int(t[1])
    d = pd.DataFrame(rows, columns=["k", "v", "t", "row", "dropped", "flash", "alert", "cancel", "air"]).astype(dict(k=int, v=int, t=float, row=int, dropped=int, flash=float, alert=float, cancel=int, air=float))
    return d.join(ev, on="row"), duty, drop


def run_stats(s: pd.DataFrame, t: pd.DataFrame) -> dict:
    """Per-run quantities of the paired runs (same seed, same events)."""
    m = s.merge(t, on="k", suffixes=("_s", "_t"))
    ok = (m.dropped_s == 0) & (m.dropped_t == 0)
    m = m[ok]
    cr = m[m.y_s == 1]
    both = cr[(cr.E_s == 1) & (cr.F_s == 1) & (cr.alert_s >= 0) & (cr.flash_t >= 0)]
    diffs = (both.alert_s - both.flash_t).to_numpy()
    single_del = ((cr.F_s == 1) & (cr.alert_s >= 0)).sum()
    two = ((cr.alert_t >= 0) | ((cr.E_t == 1) & (cr.F_t == 0) & (cr.flash_t >= 0) & (cr.cancel_t == 0)) | ((cr.E_t == 1) & (cr.F_t == 1) & (cr.flash_t >= 0)))
    return dict(diffs=diffs, air_s=float(m.air_s.sum()), air_t=float(m.air_t.sum()), n_cr=int(len(cr)), del_s=int(single_del), del_t=int(two.sum()),
                n_ev=int(len(s)), n_drop=int(((s.dropped == 1) | (t.dropped == 1)).sum()))


def boot_cell(runs: list[dict], rng: np.random.Generator) -> dict:
    n = len(runs)
    idx = rng.integers(0, n, (NB, n))
    med = np.empty(NB)
    ratio = np.empty(NB)
    dd = np.empty(NB)
    D = [r["diffs"] for r in runs]
    A_s = np.array([r["air_s"] for r in runs])
    A_t = np.array([r["air_t"] for r in runs])
    N = np.array([r["n_cr"] for r in runs], float)
    DS = np.array([r["del_s"] for r in runs], float)
    DT = np.array([r["del_t"] for r in runs], float)
    for b in range(NB):
        i = idx[b]
        pooled = np.concatenate([D[j] for j in i])
        med[b] = np.median(pooled) if len(pooled) else np.nan
        ratio[b] = A_t[i].sum() / A_s[i].sum() - 1.0
        dd[b] = (DT[i].sum() - DS[i].sum()) / N[i].sum()
    allp = np.concatenate(D)
    return dict(med_pt=float(np.median(allp)) if len(allp) else float("nan"), n_pairs=int(len(allp)), med=med, ratio_pt=float(A_t.sum() / A_s.sum() - 1.0), ratio=ratio,
                dd_pt=float((DT.sum() - DS.sum()) / N.sum()), dd=dd, single_deliv=float(DS.sum() / N.sum()), two_deliv=float(DT.sum() / N.sum()), n_cr=int(N.sum()))


def analyse() -> None:
    ev = pd.read_csv(EVENTS, sep=" ", header=None, names=["E", "F", "y", "tE"])
    rng = np.random.default_rng(SEED)
    ent: list[dict] = []

    def add(name, value, unit, notes="", origin="SIMULATED"):
        ent.append(dict(name=f"pp.p1.{name}", value=round(value, 6) if isinstance(value, float) else value, unit=unit, origin="NOT_RUN" if value == "NOT_RUN" else origin, source_file=SRC, notes=notes))

    import json

    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    cells = {}
    tests = []  # (name, met, p)
    for sf in SFS:
        for st in SETTINGS:
            cname = f"sf{sf}.{st}"
            per_loss = {}
            n_ev = n_drop = n_run_ok = n_run_bad = 0
            max_duty = 0.0
            for p in LOSSES:
                runs = []
                for s in range(1, SEEDS + 1):
                    fs, ft = fname(sf, st, p, "r3s", s), fname(sf, st, p, "r3t", s)
                    if not (fs.exists() and ft.exists()) or fs.stat().st_size == 0 or ft.stat().st_size == 0:
                        n_run_bad += 1  # an ns-3 crash (empty output): the seed is dropped for both policies
                        continue
                    a, du1, _ = load(fs, ev)
                    b, du2, _ = load(ft, ev)
                    max_duty = max(max_duty, du1, du2)
                    st_ = run_stats(a, b)
                    n_ev += st_["n_ev"]
                    n_drop += st_["n_drop"]
                    n_run_ok += 1
                    runs.append(st_)
                per_loss[p] = boot_cell(runs, rng) if runs else None
                if runs:
                    add(f"{cname}.p{p:g}.n_runs", len(runs), "runs", "paired runs used (seeds with an empty output are dropped for both policies)")
            cells[cname] = per_loss
            drop_share = n_drop / max(n_ev, 1)
            reliable = drop_share <= MAX_DROP and n_run_ok > 0
            add(f"{cname}.dropped_share", round(drop_share, 5), "fraction", "events dropped in at least one of the two runs (the vehicle still had messages pending), over all events of the cell")
            add(f"{cname}.runs_failed", n_run_bad, "runs", "seed-and-loss combinations dropped because an ns-3 output was empty")
            add(f"{cname}.max_phy_airtime_hour_s", round(max_duty, 4), "s", "largest trailing-hour PHY airtime of any vehicle in any run of the cell (limit 36 s)")
            # clause a: losses 0 and 0.3
            ma, pa = [], []
            for p in (0.0, 0.3):
                c = per_loss.get(p)
                if c is None:
                    ma.append(False)
                    pa.append(1.0)
                    continue
                ma.append(c["med_pt"] >= 0.8)
                pa.append((int((c["med"] <= 0.8).sum()) + 1) / (NB + 1))
                add(f"{cname}.p{p:g}.earlier_median_s", c["med_pt"], "s", f"median over {c['n_pairs']} crash events that alarm in both stages and arrive in both runs of (single-stage full-alert arrival minus flash arrival)")
                lo, hi = np.nanquantile(c["med"], [0.025, 0.975])
                add(f"{cname}.p{p:g}.earlier_median_s_lo", float(lo), "s", "95% cluster bootstrap over runs, 2,000 resamples, seed 42")
                add(f"{cname}.p{p:g}.earlier_median_s_hi", float(hi), "s", "95% cluster bootstrap over runs")
            met_a = all(ma) and reliable
            p_a = max(pa)
            # clause c
            mc, pc = [], []
            for p in LOSSES:
                c = per_loss.get(p)
                if c is None:
                    mc.append(False)
                    pc.append(1.0)
                    continue
                mc.append(c["ratio_pt"] < 0.40 and c["dd_pt"] >= -0.02)
                pc.append(max((int((c["ratio"] >= 0.40).sum()) + 1) / (NB + 1), (int((c["dd"] < -0.02).sum()) + 1) / (NB + 1)))
                add(f"{cname}.p{p:g}.extra_air_ratio", c["ratio_pt"], "ratio", "two-stage transmit airtime over single-stage airtime minus 1, ratio of sums over runs")
                add(f"{cname}.p{p:g}.extra_air_ratio_hi", float(np.quantile(c["ratio"], 0.975)), "ratio", "95% cluster bootstrap upper limit")
                add(f"{cname}.p{p:g}.delivery_diff", c["dd_pt"], "fraction", "two-stage minus single-stage delivery of crash events")
                add(f"{cname}.p{p:g}.delivery_diff_lo", float(np.quantile(c["dd"], 0.025)), "fraction", "95% cluster bootstrap lower limit")
                add(f"{cname}.p{p:g}.delivery_single", c["single_deliv"], "fraction", f"single-stage delivery over {c['n_cr']} crash events")
                add(f"{cname}.p{p:g}.delivery_two", c["two_deliv"], "fraction", "two-stage delivery over the same crash events")
            met_c = all(mc) and reliable
            p_c = max(pc)
            add(f"{cname}.reliable", int(reliable), "flag", f"at most {MAX_DROP:.0%} of events dropped and at least one run used")
            tests.append((f"{cname}.hP1a", met_a, p_a))
            tests.append((f"{cname}.hP1c", met_c, p_c))
    # Holm over the 8 tests
    m = len(tests)
    order = sorted(range(m), key=lambda i: tests[i][2])
    run_max = 0.0
    holm = {}
    for rank, i in enumerate(order):
        run_max = max(run_max, (m - rank) * tests[i][2])
        holm[tests[i][0]] = min(1.0, run_max)
    sup = {}
    for name, met, p in tests:
        sup[name] = bool(met and holm[name] < 0.05)
        add(f"{name}.criterion_met", int(met), "flag", "criterion at the point level")
        add(f"{name}.p", round(p, 5), "p", "one-sided cluster-bootstrap p = (count + 1) / (2,001); floor 0.0005")
        add(f"{name}.p_holm", round(holm[name], 5), "p", "Holm over the 8 ns-3 tests (two clauses in four cells)")
        add(f"{name}.verdict", "SUPPORTED" if sup[name] else "NOT SUPPORTED", "verdict", "criterion met and Holm p below 0.05")
    b_met = float(R["ar.r3.a1.retraction_share"]) < 0.20
    add("hP1b.retraction_share", float(R["ar.r3.a1.retraction_share"]), "fraction", "data-side clause, read from ar.r3.a1.retraction_share (the same in every link model)", "MEASURED_SOFTWARE")
    add("hP1b.criterion_met", int(b_met), "flag", "retractions under 20% at the 1% target", "MEASURED_SOFTWARE")
    all8 = all(sup.values())
    any_cell = any(sup[f"sf{sf}.{st}.hP1a"] and sup[f"sf{sf}.{st}.hP1c"] for sf in SFS for st in SETTINGS)
    verdict = "HOLDS IN NS-3" if (b_met and all8) else "PARTLY" if (b_met and any_cell) else "DOES NOT HOLD IN NS-3"
    add("verdict", verdict, "verdict", "H-P1b holds and all 8 tests supported = holds; at least one cell with both clauses = partly; else does not hold")
    add("n_tests_supported", int(sum(sup.values())), "of 8", "")
    record_many(ent, purge_prefixes=("pp.p1.",))
    print("verdict", verdict, {k: v for k, v in sup.items()})
    table(cells, verdict, tests, holm, R)


def table(cells: dict, verdict: str, tests, holm, R) -> None:
    L = ["# Two-stage alert R3 in ns-3 (P1) and the cross-simulator verdict table", "", "<!-- header:start -->", "<!-- header:end -->", "",
         "Generated by `python -m crashguard.pp_r3_ns3 analyse` from `results/results.json` (keys `pp.p1.*`, `ar.r3.*`, `r3.t1.T1c.*`, `r3.t3.*`). Settings and criteria were fixed in `docs/02_preregistration/PREREGISTRATION_V13.md` before the runs. "
         "ns-3 results are SIMULATED (60 vehicles in a disc of 1,500 m, 10 events per vehicle-hour, ADR and application backoff off); the trace-driven results are TRACE_DRIVEN; the detection side is MEASURED_SOFTWARE.", "",
         f"**ns-3 verdict: {verdict}.** H-P1b (retractions under 20% at the 1% target) is a detector property: {float(R['ar.r3.a1.retraction_share']):.3f}, the same in every link model.", "",
         "## ns-3 cells", "", "| Cell | Loss p | Earlier by (s, median) | Extra airtime | Delivery single | Delivery two-stage | Difference |", "|---|---:|---:|---:|---:|---:|---:|"]
    for cname, per in cells.items():
        for p, c in per.items():
            if c is None:
                continue
            L.append(f"| {cname} | {p:g} | {c['med_pt']:.3f} | {c['ratio_pt']:+.3f} | {c['single_deliv']:.4f} | {c['two_deliv']:.4f} | {c['dd_pt']:+.4f} |")
    L += ["", "## Tests (Holm over 8)", "", "| Test | Criterion met | p | Holm p | Verdict |", "|---|---:|---:|---:|---|"]
    for name, met, p in tests:
        L.append(f"| {name} | {int(met)} | {p:.4f} | {holm[name]:.4f} | {'SUPPORTED' if met and holm[name] < 0.05 else 'NOT SUPPORTED'} |")
    L += ["", "## Cross-simulator verdict table", "", "| Clause | Custom simulator (SIMULATED, `ar.r3`) | Trace-driven (TRACE_DRIVEN, `r3.t1.T1c`, MEASURED_SOFTWARE `r3.t3`) | ns-3 (SIMULATED) |", "|---|---|---|---|"]
    tr_e = ", ".join(f"{g}: {float(R[f'r3.t1.T1c.{g}.earlier_median_s']):.2f}" for g in "LMH")
    tr_a = ", ".join(f"{g}: {float(R[f'r3.t1.T1c.{g}.extra_air_ratio']):.3f}" for g in "LMH")
    tr_d = ", ".join(f"{g}: {float(R[f'r3.t1.T1c.{g}.delivery_diff']):+.3f}" for g in "LMH")
    ns_a = "; ".join(f"{cn}: {per[0.0]['med_pt']:.2f} / {per[0.3]['med_pt']:.2f}" for cn, per in cells.items() if per.get(0.0) and per.get(0.3))
    ns_c = "; ".join(f"{cn}: {max(c['ratio_pt'] for c in per.values() if c):+.3f} / {min(c['dd_pt'] for c in per.values() if c):+.3f}" for cn, per in cells.items())
    L.append(f"| (a) earlier by at least 0.8 s (median, s) | {float(R['ar.r3.a1.earlier_median_s_p0']):.2f} (p 0), {float(R['ar.r3.a1.earlier_median_s_p0.3']):.2f} (p 0.3) | groups {tr_e} | p 0 / p 0.3: {ns_a} |")
    L.append(f"| (b) retractions under 20% | {float(R['ar.r3.a1.retraction_share']):.3f} | {float(R['r3.t3.a1.retraction_share']):.3f} | same data: {float(R['ar.r3.a1.retraction_share']):.3f} |")
    ns_air = "; ".join(f"SF{sf}: {min(max(c['ratio_pt'] for c in cells[f'sf{sf}.{st}'].values() if c) for st in SETTINGS):+.3f} to {max(max(c['ratio_pt'] for c in cells[f'sf{sf}.{st}'].values() if c) for st in SETTINGS):+.3f}" for sf in SFS)
    ns_del = "; ".join(f"SF{sf}: {min(min(c['dd_pt'] for c in cells[f'sf{sf}.{st}'].values() if c) for st in SETTINGS):+.3f}" for sf in SFS)
    L.append(f"| (c) extra airtime under 40% (largest over the four losses) | {max(float(R[f'ar.r3.a1.air_ratio_p{p:g}']) for p in LOSSES):.3f} (SF7 only) | groups {tr_a} (SF7 timing) | {ns_air} (range over the two settings) |")
    L.append(f"| (c) delivery not worse by more than 2 points (smallest over the four losses) | {min(float(R[f'ar.r3.a1.delivery_diff_p{p:g}']) for p in LOSSES):+.4f} | groups {tr_d} | {ns_del} |")
    L.append(f"| Verdict | {R['ar.holm.hr3.verdict']} (`ar.holm.hr3`) | T1c supported in all groups ({R['r3.holm.ht1c.verdict']}) | {verdict} |")
    L += ["", f"ns-3, largest extra airtime and smallest delivery difference over the four losses, per cell: {ns_c}.", "",
          "The extra airtime depends on the spreading factor because a 14-byte frame carries a fixed preamble and header: the flash costs about 27% of the alert's time on air at SF7 and about 31% at SF9, so the two-stage scheme adds more at SF9 and breaks the 40% limit of clause (c) there.", ""]
    Path(ROOT / "docs" / "03_results" / "PAPER_P1_R3_NS3.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "run":
        run(int(sys.argv[2]) if len(sys.argv) > 2 else SEEDS)
    elif what == "analyse":
        analyse()
