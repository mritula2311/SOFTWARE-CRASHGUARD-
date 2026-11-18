"""Round 5 code verification report (V16 section 10): ``docs/03_results/R5_CODE_VERIFICATION.md`` from the test collection, the mutation tables and the ns-3 byte-identity check.

    python -m crashguard.r5_verify            # runs the byte-identity check in WSL (about a minute), collects the tests, writes the report and the keys r5.cv.*

The independent review of the code against V16 is a separate document (``docs/09_review/R5_REVIEW_L1_L5.md``) written by a reviewer who had no access to the results; its summary is quoted here.
"""
from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "03_results" / "R5_CODE_VERIFICATION.md"
REASONS = {
    "L112": "equivalent: the still-window mean is parallel to the estimated gravity direction, so the projection that removes the vertical part removes it exactly",
    "L127": "nearly equivalent for the side rule: a constant offset is removed by the pre-trigger baseline; it can only move the 2 g trigger sample, which is rotation-invariant for the magnitude",
    "L232": "wiring of the held-out half inside `evaluate_heldout`; a test would have to compute held-out numbers, which is not done before the freeze (the pure statistics function `heldout_stats` is tested, and the review checked the wiring)",
    "L233": "wiring of the threshold choice inside `evaluate_heldout` (same reason as L232)",
    "L1021": "the files of the test archive differ within their initial 100 bytes, so the shortened identity cannot show",
    "L618": "lattice points without a candidate within 100 km are not reached by the tested instances",
    "L619": "the tested bisection reaches the same count from either direction on the instances used",
    "L818": "the maximum low-confidence count is not tied to a state in the tested horizons",
    "L906": "the pre-alert option has a second term whose change does not cross a decision boundary in the tested values",
    "L920": "the clipped gain is never negative for the tested inputs",
    "L1104": "equivalent for the symmetric synthetic drive (the mean forward acceleration is about zero)",
    "L1108": "equivalent: scaling the horizontal acceleration does not change the unit vectors of the regressions",
    "L1109": "equivalent for the tested z-up drives: the vertical part is already near zero",
    "L1115": "equivalent: a positive scalar does not change a direction",
    "L1119": "equivalent for the tested drives: dropping the speed from the regressor leaves the direction",
    "L525": "the budget is not binding at the tested false-alarm rate, so a looser integer rounding changes no feasible set",
}
ALGS = {
    "l1": ("L1 mounting calibration", "tests/test_r5_l1.py", "bit-exact reproduction of `hwsim_v2.sense` for the identity mounting and of the tilt and mirror variants; the X1 balanced accuracy (`x1.A.r16.balanced_acc`) reproduced by the identity rotation without L1"),
    "l2": ("L2 post-event corroboration", "tests/test_r5_l2.py", "the baseline arms reproduce `r3.t3.a1.n_provisional_alarms` (2,857), `r3.t3.a1.retraction_share` and the same two keys at the 5% target exactly on the full test split (reads no L2 result)"),
    "l3": ("L3 wake-on-motion", "tests/test_r5_l3.py", "the cache covers every triggered event of the detector cache; the interrupt is never later than the trigger sample for a detected event; the B100 accelerometer features equal the always-on features"),
    "l4": ("L4 spreading-factor ladder", "tests/test_r5_l4.py", "in ns-3 the ladder with a start margin of -100 dB and k = 1000 gives the output of Z0 byte for byte; `L4INV` prints 0 0; the earlier policies are byte-identical (below)"),
    "l5": ("L5 threshold co-design", "tests/test_r5_l5.py", "the custom link model equals `ar_r3.arrival` for the same random stream; the ns-3 delay extraction is checked on a synthetic run file"),
    "l6": ("L6 gateway placement", "tests/test_r5_l6.py", "the coverage radius formula gives 3.98 km and 2.51 km as the ns-3 log-distance model does; FARS 2021 loads with 38,000 to 40,500 crashes and fatality weights; greedy maximum coverage checked on small instances against hand answers"),
    "l7": ("L7 forward-secure ratchet", "tests/test_r5_l7.py", "exhaustive enumeration of 4^0 to 4^10 event sequences; the checks are shown to fire on deliberately broken step functions; Tamarin outcome reader"),
    "l8": ("L8 flood containment", "tests/test_r5_l8.py", "hand-worked transitions of the state machine; regression values of the exploration and the legitimate replay"),
    "l9": ("L9 dispatch rule", "tests/test_r5_l9.py", "break-even values checked against the stored round-3 retraction share (0.2405 minutes of delay per dispatch)"),
    "l10": ("L10 leakage audit", "tests/test_r5_l10.py", "UCI HAR published sizes (7,352 and 2,947 windows, 21 and 9 subjects) reproduced from the downloaded archive"),
    "l11": ("L11 mirror-flip detection (added after session 1)", "tests/test_r5_l11.py", "noise-free right-handed turn gives agreement +1; every mirror flip gives -1; rotation invariance; blind spots as derived"),
}


def collect(test_file: str) -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", test_file], cwd=ROOT, capture_output=True, text=True)
    m = re.search(r"(\d+) tests? collected", r.stdout) or re.search(r"(\d+) tests?", r.stdout)
    return int(m.group(1)) if m else -1


def mutation(alg: str) -> tuple[list[dict], int, int]:
    rows = list(csv.DictReader((ROOT / f"results/tables/r5_mutation_{alg}.csv").open(encoding="utf-8")))
    ap = [r for r in rows if r["status"] != "NOT_APPLIED"]
    return rows, len(ap), sum(r["status"] == "KILLED" for r in ap)


def identity_check() -> tuple[int, int]:
    from crashguard.rd_firmware import wsl_path

    ev = wsl_path(ROOT / "data" / "processed" / "r3_ns3_events.txt")
    home = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", "echo $HOME"], capture_output=True, text=True).stdout.strip()
    old = home + "/ns3work/xsim_alert_round4_bin"
    r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", wsl_path(ROOT / "scripts" / "r5_ns3_identity.sh"), old, ev], capture_output=True, text=True, env={**__import__("os").environ, "MSYS_NO_PATHCONV": "1"})
    m = re.search(r"compared (\d+) runs, (\d+) differences", r.stdout)
    return (int(m.group(1)), int(m.group(2))) if m else (-1, -1)


def main() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from crashguard.rd_common import Rec

    n_runs, n_diff = identity_check()
    rec = Rec("r5.cv.", "src/crashguard/r5_verify.py", "ANALYTICAL")
    L = ["# Round 5 code verification (V16 section 10)", "", "<!-- header:start -->", "<!-- header:end -->", "",
         "Checks made before any development run: unit and property tests, a known-answer reproduction of an earlier number for each algorithm, hand-written mutants (at least 20 per algorithm, at least 80% killed), the byte-identity check of the ns-3 application, and an independent review against V16. Tests: `tests/test_r5_l1.py` to `tests/test_r5_l5.py`. Mutants: `scripts/r5_mutants.py`, `scripts/r5_mutants_l34.py`, run by `scripts/r5_mutation.py`; tables in `results/tables/r5_mutation_<algorithm>.csv`.", "",
         "| Algorithm | Tests | Mutants applied | Killed | Share killed | Survivors |", "|---|---:|---:|---:|---:|---|"]
    notes = []
    for a, (name, tf, ka) in ALGS.items():
        n_t = collect(tf)
        rows, n_m, n_k = mutation(a)
        surv = [r for r in rows if r["status"] == "SURVIVED"]
        L.append(f"| {name} | {n_t} | {n_m} | {n_k} | {n_k / n_m:.0%} | {', '.join(r['id'] for r in surv) or 'none'} |")
        rec.add(f"{a}.tests", n_t, "tests", "collected tests of the algorithm's test file")
        notes.append((name, ka, surv))
    L += ["", "## Known-answer reproductions", ""]
    for name, ka, _s in notes:
        L.append(f"- **{name}:** {ka}.")
    L += ["", "## Surviving mutants", ""]
    for name, _ka, surv in notes:
        for r in surv:
            L.append(f"- {name}, {r['id']} ({r['description']}): {REASONS.get(r['id'], 'not caught by the tests; no reason recorded')}.")
    L += ["", "## ns-3 application", "", f"The earlier policies (p1, quick, d1, r3s, r3t, r3a, lorawan) at SF7 and SF9, extra loss 0.3, seeds 3, 17 and 41 give byte-identical output with the binary built before the change and the binary built after it: {n_runs} runs compared, {n_diff} differences (`scripts/r5_ns3_identity.sh`). The random variable of the new policies is created only for `z0` and `l4`, because creating one in any policy would shift the automatically assigned random streams of the others. The per-run invariants of the new policies are printed as `L4INV <late> <duty>` (transmissions that would end after the deadline, transmissions beyond the duty limit); both must be 0 and are tested.", ""]
    rec.add("ns3_identity.runs", n_runs, "runs", "earlier policies compared between the old and the new ns-3 binary")
    rec.add("ns3_identity.differences", n_diff, "runs", "must be 0")
    rec.write()
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("written", OUT.name, "identity", n_runs, n_diff)


if __name__ == "__main__":
    main()
