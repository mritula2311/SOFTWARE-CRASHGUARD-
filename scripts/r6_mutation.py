"""Hand-written mutation testing of the round-6 modules (V17 section 1, rule 5): one textual change of one module in a temporary copy of src and tests; a mutant is KILLED if a test fails.
At least 20 mutants per algorithm and at least 80% killed are required before the freeze.

    python scripts/r6_mutation.py r2        -> results/tables/r6_mutation_r2.csv
"""
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
F = "src/crashguard/r6_seq.py"
C = "src/crashguard/r6_common.py"
R2 = [
    ("S01", F, "return np.unique(np.quantile(scores, np.linspace(0, 1, nbins + 1)[1:-1]))", "return np.unique(np.quantile(scores, np.linspace(0, 1, nbins + 1)[:-1]))", "bin edges include the minimum"),
    ("S02", F, "c1 = np.bincount(np.searchsorted(edges, s_pos, side=\"right\"), minlength=nb) + smooth", "c1 = np.bincount(np.searchsorted(edges, s_pos, side=\"left\"), minlength=nb) + smooth", "bin side for crash scores"),
    ("S03", F, "c0 = np.bincount(np.searchsorted(edges, s_neg, side=\"right\"), minlength=nb) + smooth", "c0 = np.bincount(np.searchsorted(edges, s_neg, side=\"right\"), minlength=nb) + 2 * smooth", "smoothing differs between classes"),
    ("S04", F, "return np.log(c1 / c1.sum()) - np.log(c0 / c0.sum())", "return np.log(c1 / c1.sum()) + np.log(c0 / c0.sum())", "ratio becomes a product"),
    ("S05", F, "return np.log(c1 / c1.sum()) - np.log(c0 / c0.sum())", "return np.log(c1) - np.log(c0)", "counts not normalised"),
    ("S06", F, "acc = acc + tables[k][np.searchsorted(edges[k], S[:, k], side=\"right\")]", "acc = tables[k][np.searchsorted(edges[k], S[:, k], side=\"right\")]", "no accumulation over checkpoints"),
    ("S07", F, "acc = acc + tables[k][np.searchsorted(edges[k], S[:, k], side=\"right\")]", "acc = acc + tables[k][np.searchsorted(edges[k], S[:, k], side=\"left\")]", "bin side in the running sum"),
    ("S08", F, "    for k in range(NCHK):\n        acc = acc +", "    for k in range(NCHK - 1):\n        acc = acc +", "last checkpoint skipped"),
    ("S09", F, "up = undecided & (L[:, k] >= A)", "up = undecided & (L[:, k] > A)", "upper threshold exclusive"),
    ("S10", F, "down = undecided & ~up & (L[:, k] <= B)", "down = undecided & ~up & (L[:, k] < B)", "lower threshold exclusive"),
    ("S11", F, "t[down] = LENGTHS[k]", "t[down] = LENGTHS[0]", "stop time is always 50 ms"),
    ("S12", F, "alarm[up], t[up] = True, LENGTHS[k]", "alarm[up], t[up] = True, LENGTHS[k + 1]", "decision time off by one checkpoint"),
    ("S13", F, "undecided &= ~(up | down)", "undecided &= ~up", "a stopped event stays undecided"),
    ("S14", F, "alarm, t = np.zeros(n, bool), np.full(n, float(LENGTHS[-1]))", "alarm, t = np.ones(n, bool), np.full(n, float(LENGTHS[-1]))", "every event alarms by default"),
    ("S15", F, "return float((alarm & (t < LENGTHS[-1]) & neg).sum()) / n_neg_all", "return float((alarm & (t <= LENGTHS[-1]) & neg).sum()) / n_neg_all", "the 1,800 ms alarms counted as provisional"),
    ("S16", F, "return float((alarm & (t < LENGTHS[-1]) & neg).sum()) / n_neg_all", "return float((alarm & (t < LENGTHS[-1]) & neg).sum()) / max(1, int(neg.sum()))", "false-alarm denominator"),
    ("S17", F, "if B >= A:\n                continue", "if B > A:\n                continue", "B equal to A allowed"),
    ("S18", F, "if abs(fa - fa_target) > fa_tol:", "if fa - fa_target > fa_tol:", "one-sided false-alarm match"),
    ("S19", F, "key = (-mt, A)", "key = (mt, A)", "slowest pair preferred"),
    ("S20", F, "sel = alarm & pos & (t < LENGTHS[-1])", "sel = alarm & neg & (t < LENGTHS[-1])", "decision time taken over non-crash events"),
    ("S21", F, "return float(1.0 - full_alarm[prov].mean()) if prov.any() else float(\"nan\")", "return float(full_alarm[prov].mean()) if prov.any() else float(\"nan\")", "retraction share inverted"),
    ("S22", F, "a_p=float(((d_a <= 200.0) | np.isnan(d_a)).sum() + 1) / (n_boot + 1)", "a_p=float(((d_a <= 100.0) | np.isnan(d_a)).sum() + 1) / (n_boot + 1)", "null margin 100 ms"),
    ("S23", F, "a_lo=float(np.nanquantile(d_a, 0.025))", "a_lo=float(np.nanquantile(d_a, 0.5))", "lower limit is the median"),
    ("S24", F, "b_p=float((d_b >= 0.02).sum() + 1) / (n_boot + 1)", "b_p=float((d_b <= 0.02).sum() + 1) / (n_boot + 1)", "direction of the retraction test"),
    ("S25", F, "both = prov_f & prov_s & pos\n    d_a", "both = prov_f & pos\n    d_a", "events that alarm under only one rule included"),
    ("S26", F, "d_a[i] = float((t_f[ix][bb] - t_s[ix][bb]).mean()) if bb.any() else np.nan", "d_a[i] = float((t_s[ix][bb] - t_f[ix][bb]).mean()) if bb.any() else np.nan", "sign of the time difference"),
    ("S27", C, "return int(hashlib.sha256((\"r6|\" + str(int(event_id))).encode()).hexdigest(), 16) % 2", "return int(hashlib.sha256((\"r5|\" + str(int(event_id))).encode()).hexdigest(), 16) % 2", "round-5 prefix in the half rule"),
    ("S29", F, "sel = sel & ref[1]", "sel = sel | ref[1]", "paired selection includes events without a fixed-rule alarm"),
    ("S30", F, "-float((ref[0][sel] - t[sel]).mean())", "-float((t[sel] - ref[0][sel]).mean())", "paired objective sign"),
    ("S31", F, "if ref is not None:\n                sel = sel & ref[1]", "if False:\n                sel = sel & ref[1]", "paired selection switched off"),
    ("S28", F, "rng = np.random.default_rng(seed)\n    n = len(t_f)", "rng = np.random.default_rng(seed + 1)\n    n = len(t_f)", "bootstrap seed"),
]
M1 = "src/crashguard/r6_micro.py"
R1 = [
    ("M01", M1, "a = (cr.alert >= 0) & (cr.alert <= deadline)", "a = (cr.alert > 0) & (cr.alert <= deadline)", "a confirm arrival at time 0 not counted"),
    ("M02", M1, "& f & (cr.cancel == 0)", "& f & (cr.cancel == 1)", "cancelled flash counts as delivered"),
    ("M03", M1, "f = (cr.flash >= 0) & (cr.flash <= deadline)", "f = (cr.flash >= 1) & (cr.flash <= deadline)", "flash arrival threshold"),
    ("M04", M1, "(x.dropped_t == 0) & (x.dropped_m == 0)]", "(x.dropped_t == 0)]", "events dropped only in the micro run kept"),
    ("M05", M1, "cr = x[x.y_s == 1]", "cr = x[x.y_s == 0]", "non-crash events used as crash events"),
    ("M06", M1, "air_m=float(x.air_m.sum())", "air_m=float(x.air_t.sum())", "micro airtime taken from the R3 run"),
    ("M07", M1, "del_t=two_stage_delivered(crt, deadline), del_m=two_stage_delivered(crm, deadline)", "del_t=two_stage_delivered(crm, deadline), del_m=two_stage_delivered(crt, deadline)", "delivery swapped"),
    ("M08", M1, "| (t.dropped == 1) | (m.dropped == 1))", "| (t.dropped == 1))", "drop count misses the micro run"),
    ("M09", M1, 'ratio_s = A["air_m"][idx].sum(1) / A["air_s"][idx].sum(1) - 1.0', 'ratio_s = A["air_m"][idx].sum(1) / A["air_t"][idx].sum(1) - 1.0', "extra airtime against the wrong reference"),
    ("M10", M1, 'ratio_t = A["air_m"][idx].sum(1) / A["air_t"][idx].sum(1)', 'ratio_t = A["air_m"][idx].sum(1) / A["air_s"][idx].sum(1)', "ratio to R3 uses the single-stage total"),
    ("M11", M1, 'dd = (A["del_m"][idx].sum(1) - A["del_t"][idx].sum(1))', 'dd = (A["del_t"][idx].sum(1) - A["del_m"][idx].sum(1))', "sign of the delivery difference"),
    ("M12", M1, 'dd_pt=float((A["del_m"].sum() - A["del_t"].sum())', 'dd_pt=float((A["del_m"].sum() + A["del_t"].sum())', "point delivery difference is a sum"),
    ("M13", M1, "idx = rng.integers(0, n, (nb, n))", "idx = rng.integers(0, max(1, n - 1), (nb, n))", "last run never resampled"),
    ("M14", M1, "return hi <= LIMIT_A,", "return hi < LIMIT_A,", "upper limit exactly 0.40 fails"),
    ("M15", M1, 'np.quantile(c["ratio_s"], 0.975)', 'np.quantile(c["ratio_s"], 0.95)', "upper limit is the 95th percentile"),
    ("M16", M1, '(c["ratio_s"] >= LIMIT_A)', '(c["ratio_s"] > LIMIT_A)', "p-value excludes resamples at 0.40"),
    ("M17", M1, "return lo >= LIMIT_B,", "return lo > LIMIT_B,", "lower limit exactly -0.01 fails"),
    ("M18", M1, 'np.quantile(c["dd"], 0.025)', 'np.quantile(c["dd"], 0.05)', "lower limit is the 5th percentile"),
    ("M19", M1, '(c["dd"] < LIMIT_B)', '(c["dd"] <= LIMIT_B)', "p-value includes resamples at the margin"),
    ("M20", M1, "        if r[s + k]:\n            if arr == math.inf:", "        if not r[s + k]:\n            if arr == math.inf:", "reception test inverted"),
    ("M21", M1, "return arr, k + 1, True", "return arr, k, True", "tries off by one"),
    ("M22", M1, "return arr, tries, False", "return arr, tries, True", "unacknowledged stage reported as acknowledged"),
    ("M23", M1, "a_c = a_micro if acked else A_AL", "a_c = a_micro", "micro-confirm without an acknowledged flash"),
    ("M24", M1, "a_x = a_micro if acked else A_FL", "a_x = A_FL", "micro-cancel never used"),
    ("M25", M1, 'out["two_air"] = A_FL * n_f + a_c * n_c', 'out["two_air"] = A_FL * n_f + a_c', "confirm tries not counted"),
    ("M26", M1, 'out["two_air"] = A_FL * n_f + CANCEL_TX * a_x', 'out["two_air"] = A_FL * n_f + a_x', "cancel repeats not counted"),
    ("M27", M1, "    if F_:  # the single-stage reference", "    if False:  # the single-stage reference", "single-stage draws not consumed"),
    ("M28", M1, "k0 = s + n_f", "k0 = s", "confirm replay starts at the flash frame"),
    ("M29", M1, "HELD_SEEDS = range(1, 61)", "HELD_SEEDS = range(1, 60)", "59 held-out seeds"),
    ("M30", M1, "DEV_SEEDS = range(101, 121)", "DEV_SEEDS = range(100, 121)", "development seeds overlap nothing but change"),
    ("M31", M1, '(f" --pend={pend:g}" if pend is not None else "")', '""', "pending lifetime not passed"),
    ("M33", M1, "(cr.alert <= deadline)", "(cr.alert <= deadline + 100)", "confirm deadline widened"),
    ("M34", M1, "(cr.flash <= deadline)", "(cr.flash <= deadline + 100)", "flash deadline widened"),
    ("M35", M1, "ratio_pd = (A[\"air_m\"][idx].sum(1) / A[\"del_m\"][idx].sum(1))", "ratio_pd = (A[\"air_m\"][idx].sum(1) / A[\"del_t\"][idx].sum(1))", "per-delivered airtime uses the R3 delivery count"),
    ("M32", M1, 'tag = f"_pend{pend:g}" if pend is not None else ""', 'tag = ""', "file name without the lifetime"),
]
ALGS = {"r2": (["tests/test_r6_seq.py"], R2), "r1": (["tests/test_r6_micro.py"], R1)}


def run(cwd: Path, tests: list[str]) -> bool:
    env = {**os.environ, "PYTHONPATH": str(cwd / "src") + os.pathsep + os.environ.get("EXTRA_PATH", "")}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode == 0  # True: all tests passed, the mutant SURVIVED


def main() -> None:
    for alg in sys.argv[1:] or list(ALGS):
        tests, mutants = ALGS[alg]
        rows = []
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "w"
            shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "dummy"))
            (work / "results").mkdir()
            if not run(work, tests):
                sys.exit("the tests fail on the clean copy")
            for mid, f, old, new, desc in mutants:
                p = work / f
                orig = p.read_text(encoding="utf-8")
                if orig.count(old) != 1:
                    rows.append((mid, f, desc, "INVALID"))
                    continue
                p.write_text(orig.replace(old, new), encoding="utf-8")
                survived = run(work, tests)
                p.write_text(orig, encoding="utf-8")
                rows.append((mid, f, desc, "SURVIVED" if survived else "KILLED"))
                print(mid, rows[-1][-1], flush=True)
        out = ROOT / "results" / "tables" / f"r6_mutation_{alg}.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "file", "description", "status"])
            w.writerows(rows)
        valid = [r for r in rows if r[3] != "INVALID"]
        killed = sum(r[3] == "KILLED" for r in valid)
        print(f"{alg}: {killed} of {len(valid)} killed ({100 * killed / max(1, len(valid)):.0f}%), invalid {len(rows) - len(valid)}")


if __name__ == "__main__":
    main()
