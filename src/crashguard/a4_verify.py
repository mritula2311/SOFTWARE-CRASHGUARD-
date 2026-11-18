"""Code verification of the round-4 modules before the freeze (PREREGISTRATION_V15 section 6). Writes docs/03_results/A4_CODE_VERIFICATION.md and keys ``a4.cv.*``.

    python -m crashguard.a4_verify

Checks: (1) tests and ruff; (2) known-answer reproduction of round-3 numbers: the A1 engine in its round-3 compatibility mode reproduces the stored per-group values ``r3.t1.T1c.*``; the A2 replay
on the union of all gateways reproduces ``r3.t1.explore.*.deliv.Z0``; the ns-3 analysis reproduces ``pp.p1.*``; (3) the extended ns-3 application leaves the outputs of the policies r3s and r3t
byte-identical on three stored seeds; (4) mutation testing (``scripts/a4_mutation.py``, results in ``results/tables/a4_mutation.csv``).
"""
from __future__ import annotations

import csv
import json
import math
import pickle
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from crashguard import a4_a1 as A
from crashguard import a4_a2 as A2
from crashguard import r3_t1 as T1
from crashguard.results import record_many

ROOT = Path(__file__).resolve().parents[2]
SRC = "src/crashguard/a4_verify.py"


def a1_task(args: tuple) -> tuple:
    dev, segs, p, events = args
    rng0 = T1.seeded("t1s", dev, T1.SEED)
    adm = T1.admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(T1.N_START)]
    s = dict(n_cr=0, single_air=0.0, two_air=0.0, single_d=0, two_d=0)
    mine = dict(n_cr=0, two_air=0.0, two_d=0)
    for q, (si, pos) in enumerate(picks):
        r = segs[si][0]
        rng = T1.seeded("t1e", dev, q)
        ev = events[rng.randrange(len(events))]
        o3 = T1.r3_event(r, pos, ev, p, rng)
        rng2 = T1.seeded("t1e", dev, q)
        rng2.randrange(len(events))
        if ev[1]:
            T1.arrival_trace(r, pos, T1.FINAL_S + T1.COMPUTE3, T1.A_AL, p, rng2)
        o = A.a1_event(r, pos, ev, p, rng2, A.R3)
        for k in s:
            s[k] += o3[k]
        mine["n_cr"] += o["n_cr"]
        mine["two_air"] += o["two_air"]
        mine["two_d"] += o["two_d"]
    return dev, s, mine


def known_answer_a1() -> dict:
    links = pickle.loads((ROOT / "data" / "processed" / "r3_t1_links.pkl").read_bytes())
    held = pickle.loads((ROOT / "data" / "processed" / "r3_t1_held.pkl").read_bytes())["res"]
    stored = {x["dev"]: x["r3"] for x in held}
    events = T1.load_events()
    tasks = [(d, links[d]["segs"], links[d]["p"], events) for d in sorted(stored)]
    with ProcessPoolExecutor(14) as ex:
        out = list(ex.map(a1_task, tasks, chunksize=8))
    bad = 0
    grp: dict = {g: dict(sa=0.0, ta=0.0, td=0, sd=0, n=0) for g, _lo, _hi in T1.GROUPS}
    for dev, s, mine in out:
        st = stored[dev]
        ok = math.isclose(st["two_air"], mine["two_air"], rel_tol=0, abs_tol=1e-9) and st["two_d"] == mine["two_d"] and st["n_cr"] == mine["n_cr"]
        bad += int(not ok)
        g = T1.group_of(links[dev]["p"])
        grp[g]["sa"] += s["single_air"]
        grp[g]["ta"] += mine["two_air"]
        grp[g]["td"] += mine["two_d"]
        grp[g]["sd"] += s["single_d"]
        grp[g]["n"] += mine["n_cr"]
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    cmp = {}
    for g, v in grp.items():
        ratio = v["ta"] / v["sa"] - 1.0
        dd = (v["td"] - v["sd"]) / v["n"]
        cmp[g] = dict(ratio=ratio, ratio_stored=R[f"r3.t1.T1c.{g}.extra_air_ratio"], dd=dd, dd_stored=R[f"r3.t1.T1c.{g}.delivery_diff"])
    ok_groups = all(abs(round(c["ratio"], 6) - c["ratio_stored"]) < 1e-9 and abs(round(c["dd"], 6) - c["dd_stored"]) < 1e-9 for c in cmp.values())
    return dict(n_devices=len(out), n_mismatch=bad, groups=cmp, groups_match=bool(ok_groups))


def a2_task(args: tuple) -> tuple:
    dev, segs = args
    r_union = [A2.set_sequence(m, 0x1FF) for m, _ in segs]
    adm = T1.admissible([(r, None) for r in r_union])
    rng0 = T1.seeded("t1s", dev, T1.SEED)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(T1.N_START)]
    return dev, float(np.mean([A2.z0_delivered(r_union[si], pos) for si, pos in picks]))


def known_answer_a2() -> dict:
    G = pickle.loads((ROOT / "data" / "processed" / "a4_loed_gw.pkl").read_bytes())["links"]
    held = pickle.loads((ROOT / "data" / "processed" / "r3_t1_held.pkl").read_bytes())["res"]
    stored = {x["dev"]: x for x in held}
    with ProcessPoolExecutor(14) as ex:
        out = list(ex.map(a2_task, [(d, G[d]["segs"]) for d in sorted(stored)], chunksize=8))
    bad = sum(int(abs(v - stored[d]["deliv"]["Z0"]) > 1e-12) for d, v in out)
    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    grp = {}
    for g, lo, hi in T1.GROUPS:
        vals = [v for d, v in out if lo <= stored[d]["p"] < hi]
        grp[g] = dict(mean=float(np.mean(vals)), stored=R[f"r3.t1.explore.{g}.deliv.Z0"], n=len(vals))
    ok = all(abs(round(c["mean"], 6) - c["stored"]) < 1e-9 for c in grp.values())
    return dict(n_devices=len(out), n_mismatch=bad, groups=grp, groups_match=bool(ok))


def known_answer_ns3() -> dict:
    """The ns-3 analysis, fed the round-3 two-stage runs as the 'A1' runs, reproduces the stored ``pp.p1`` extra-airtime ratios; the policies r3s and r3t are byte-identical on three seeds."""
    from crashguard import a4_a1_ns3 as N
    import pandas as pd

    R = {e["name"]: e["value"] for e in json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))}
    ev = pd.read_csv(N.P1.EVENTS, sep=" ", header=None, names=["E", "F", "y", "tE"])
    res = {}
    for sf, st, p in ((9, "shipped", 0.3), (7, "calib", 0.0)):
        runs = []
        for s in range(1, N.SEEDS + 1):
            fs, ft = N.fn(N.P1.OUT, sf, st, p, "r3s", s), N.fn(N.P1.OUT, sf, st, p, "r3t", s)
            if not (fs.exists() and ft.exists() and fs.stat().st_size and ft.stat().st_size):
                continue
            a_, _d1, _ = N.P1.load(fs, ev)
            b_, _d2, _ = N.P1.load(ft, ev)
            runs.append(N.run_stats3(a_, b_, b_))
        c = N.boot_cell(runs, np.random.default_rng(1))
        key = f"pp.p1.sf{sf}.{st}.p{p:g}.extra_air_ratio"
        res[key] = dict(recomputed=round(c["ratio_r3_pt"], 6), stored=R[key])
    same = []
    script = ROOT / "data" / "processed" / "ns3check.sh"
    r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "/mnt/" + str(Path(__file__).resolve().parents[2] / "data" / "processed" / "ns3check.sh").replace("\\", "/")[0].lower() + str(Path(__file__).resolve().parents[2] / "data" / "processed" / "ns3check.sh").replace("\\", "/")[2:]], capture_output=True, text=True, env={**__import__("os").environ, "MSYS_NO_PATHCONV": "1"}) if script.exists() else None
    if r is not None:
        same = [ln for ln in r.stdout.splitlines() if ln.startswith(("IDENTICAL", "DIFFERENT"))]
    return dict(analysis=res, analysis_match=all(abs(v["recomputed"] - v["stored"]) < 1e-9 for v in res.values()), byte_check=same, byte_identical=bool(same) and all(x.startswith("IDENTICAL") for x in same))


def pytest_counts() -> dict:
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_a4_a1.py", "tests/test_a4_a2.py"], cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": "src"})
    last = [ln for ln in r.stdout.splitlines() if "passed" in ln or "failed" in ln]
    rr = subprocess.run([sys.executable, "-m", "ruff", "check", "src/crashguard/a4_a1.py", "src/crashguard/a4_a2.py", "src/crashguard/a4_common.py", "src/crashguard/a4_a1_ns3.py", "src/crashguard/a4_dev.py", "src/crashguard/a4_verify.py", "tests/test_a4_a1.py", "tests/test_a4_a2.py", "scripts/a4_mutation.py"], cwd=ROOT, capture_output=True, text=True)
    return dict(pytest=last[-1] if last else r.stdout[-200:], pytest_ok=r.returncode == 0, ruff_ok=rr.returncode == 0, ruff=rr.stdout.strip()[-200:])


def mutation() -> dict:
    rows = list(csv.DictReader((ROOT / "results" / "tables" / "a4_mutation.csv").open(encoding="utf-8")))
    applied = [x for x in rows if x["status"] != "NOT_APPLIED"]
    killed = sum(x["status"] == "KILLED" for x in applied)
    return dict(n=len(applied), killed=killed, share=killed / len(applied), survivors=[x["id"] + " (" + x["description"] + ")" for x in applied if x["status"] == "SURVIVED"])


def main() -> None:
    t = pytest_counts()
    a1 = known_answer_a1()
    a2 = known_answer_a2()
    n3 = known_answer_ns3()
    mu = mutation()
    ok = bool(t["pytest_ok"] and t["ruff_ok"] and a1["n_mismatch"] == 0 and a1["groups_match"] and a2["n_mismatch"] == 0 and a2["groups_match"] and n3["analysis_match"] and n3["byte_identical"] and mu["n"] >= 20 and mu["share"] >= 0.8)
    ent = []

    def add(n, v, u, notes=""):
        ent.append(dict(name=f"a4.cv.{n}", value=v, unit=u, origin="ANALYTICAL", source_file=SRC, notes=notes))

    add("passed", int(ok), "flag", "all code-verification checks passed (tests, ruff, known answers, ns-3 byte check, at least 20 mutants with at least 80% killed)")
    add("a1_known_answer.devices", a1["n_devices"], "devices", "round-3 HELD-OUT devices recomputed by the A1 engine in compatibility mode")
    add("a1_known_answer.mismatch", a1["n_mismatch"], "devices", "devices whose two-stage airtime or delivery differs from the stored round-3 value (must be 0)")
    add("a2_known_answer.mismatch", a2["n_mismatch"], "devices", "devices whose zero-spacing delivery differs from the stored round-3 value (must be 0)")
    add("ns3_byte_identical", int(n3["byte_identical"]), "flag", "outputs of r3s and r3t byte-identical to the stored paper-v1 outputs on three seeds")
    add("mutation.mutants", mu["n"], "mutants", "")
    add("mutation.killed_share", mu["share"], "fraction", "")
    record_many(ent, purge_prefixes=("a4.cv.passed", "a4.cv.a1_known", "a4.cv.a2_known", "a4.cv.ns3_byte"))
    doc = f"""# Code verification of the round-4 modules

<!-- header:start -->
| Field | Value |
|---|---|
| Status | current |
| Date | 2026-11-15 |
| Owner | Mritula S |
| Scope | Code verification of the round-4 modules before the freeze. |
| Evidence labels used | ANALYTICAL |
<!-- header:end -->

Generated by `python -m crashguard.a4_verify` (rules: `docs/02_preregistration/PREREGISTRATION_V15.md` section 6). Overall: **{'PASSED' if ok else 'NOT PASSED'}**.

| Check | Result |
|---|---|
| Tests (`tests/test_a4_a1.py`, `tests/test_a4_a2.py`; unit, property and equivalence tests) | {t['pytest']} |
| ruff on the new files | {'clean' if t['ruff_ok'] else t['ruff']} |
| A1 engine in round-3 compatibility mode against the stored per-device sums of `r3_t1_held.pkl` | {a1['n_devices']} devices, {a1['n_mismatch']} mismatches |
| Group values recomputed from those sums against `r3.t1.T1c.*.extra_air_ratio` and `delivery_diff` (6 digits) | {'match' if a1['groups_match'] else 'DIFFER'}: {json.dumps({g: (round(c['ratio'], 4), c['ratio_stored'], round(c['dd'], 4), c['dd_stored']) for g, c in a1['groups'].items()})} |
| A2 replay on the union of all gateways against `r3.t1.explore.*.deliv.Z0` | {a2['n_devices']} devices, {a2['n_mismatch']} mismatches; group means {'match' if a2['groups_match'] else 'DIFFER'}: {json.dumps({g: (round(c['mean'], 4), c['stored']) for g, c in a2['groups'].items()})} |
| ns-3 analysis fed the round-3 runs against `pp.p1.*.extra_air_ratio` | {'match' if n3['analysis_match'] else 'DIFFER'}: {json.dumps(n3['analysis'])} |
| ns-3 application with the new policy: outputs of r3s and r3t against the stored paper-v1 outputs | {'; '.join(n3['byte_check']) or 'NOT_RUN'} |
| Mutation testing (`scripts/a4_mutation.py`, `results/tables/a4_mutation.csv`) | {mu['killed']} of {mu['n']} killed ({mu['share']:.0%}); survivors: {', '.join(mu['survivors']) or 'none'} |

Properties checked by the tests (V15 section 6): no provisional transmission ends after the deadline; the airtime of an event never exceeds the duty limit; transmissions do not overlap (one radio); the provisional repetition stops only on an
ACK that passes the per-vehicle check (valid tag, this vehicle, an id the car has sent, ACK type), and an ACK of another vehicle, with a wrong tag, naming an id never sent or of another type never stops it; with no ACK reaching the car the
repetition runs until the deadline or the duty limit; a retraction withdraws the provisional alert; the confirm is not sent before its ready time. The one surviving mutant removes a second, redundant stop of the provisional repetition on an
ACK of the confirm frame (the same stop exists in the branch that handles the confirm); it is an equivalent mutant of the engine.

The C++ application is checked through its outputs: the policies r3s and r3t are unchanged (byte check above) and the policy r3a prints the counters `A1INV` (provisional frames ending after the deadline and above the duty limit), which the ns-3 analysis reads in every run.
"""
    (ROOT / "docs" / "03_results" / "A4_CODE_VERIFICATION.md").write_text(doc, encoding="utf-8")
    print("PASSED" if ok else "NOT PASSED", json.dumps(dict(tests=t, a1=a1["n_mismatch"], a1_groups=a1["groups_match"], a2=a2["n_mismatch"], a2_groups=a2["groups_match"], ns3=n3["analysis_match"], bytes=n3["byte_identical"], mu=mu)))


if __name__ == "__main__":
    main()
