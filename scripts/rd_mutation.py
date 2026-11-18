"""CV 5: hand-written mutation testing of the redesign policy module and the security modules (a mutmut-style check without the tool: mutmut does not run on Windows).

Each mutant is one textual change (flipped comparison, off-by-one, skipped check, swapped branch). The file is patched in a temporary copy of the source tree, the tests that cover the module are run
in a subprocess, and the mutant is KILLED if any of them fails. Results go to results/tables/rd_mutation.csv and keys ``rd.cv.mutation.*``. Below 80% killed means the tests are extended first.

    python scripts/rd_mutation.py
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
POL = "src/crashguard/rd_policy.py"
VER = "src/crashguard/verifier.py"
PKT = "src/crashguard/packet.py"
T_POL = ["tests/redesign/test_rd_policy.py"]
T_SEC = ["tests/test_packet_attacks.py", "tests/test_security_properties.py", "tests/redesign/test_rd_security.py"]

MUTANTS = [
    # (id, file, old, new, tests, description)
    ("M01", POL, "return deadline_s - (now - t_event)", "return deadline_s + (now - t_event)", T_POL, "time left: sign of elapsed time"),
    ("M02", POL, "return t_start + airtime <= t_event + deadline_s + 1e-12", "return t_start + airtime < t_event + deadline_s - 1e-3", T_POL, "retry allowed: strict comparison"),
    ("M03", POL, "return t_start + airtime <= t_event + deadline_s + 1e-12", "return t_start <= t_event + deadline_s + 1e-12", T_POL, "retry allowed: airtime ignored"),
    ("M04", POL, "        if failed:\n            self.a += 1.0\n        else:\n            self.b += 1.0", "        if failed:\n            self.b += 1.0\n        else:\n            self.a += 1.0", T_POL, "Beta update: failure and success swapped"),
    ("M05", POL, "self.a = a0 + (self.a - a0) * self.forget", "self.a = a0 + (self.a - a0)", T_POL, "Beta forgetting skipped on a"),
    ("M06", POL, "return self.a / (self.a + self.b)", "return self.b / (self.a + self.b)", T_POL, "Beta mean inverted"),
    ("M07", POL, "return int(np.searchsorted(L_EDGES, l_hat, side=\"right\"))", "return int(np.searchsorted(L_EDGES, l_hat, side=\"left\"))", T_POL, "loss bin edge side"),
    ("M08", POL, "return int(np.searchsorted(LOAD_EDGES, n_heard, side=\"right\"))", "return int(np.searchsorted(LOAD_EDGES, n_heard, side=\"left\"))", T_POL, "load bin edge side"),
    ("M09", POL, "math.floor(budget_s / unit_s + 1e-9)", "math.ceil(budget_s / unit_s + 1e-9)", T_POL, "budget units rounded up"),
    ("M10", POL, "        if tau_s <= 0:\n            return None", "        if tau_s < -1e9:\n            return None", T_POL, "lookup: no time left check removed"),
    ("M11", POL, "A[c][min(j, J_MAX), t,", "A[c][0, t,", T_POL, "lookup ignores the number of failed attempts"),
    ("M12", POL, "if g + a_tx > tau + 1e-12:", "if a_tx > tau + 1e-12:", T_POL, "DP feasibility ignores the gap"),
    ("M13", POL, "units = int(math.ceil(a_tx / self.unit_s - 1e-9))", "units = int(math.floor(a_tx / self.unit_s - 1e-9))", T_POL, "DP budget charge rounded down"),
    ("M14", POL, "coll = 0.0 if (delta > 0 or j == 0) else rho * math.exp(-g / P.g0)", "coll = 0.0", T_POL, "DP crowd term removed"),
    ("M15", POL, "G2 = np.minimum.accumulate(G[:, ::-1], axis=1)[:, ::-1]  # suffix minimum over time left", "G2 = G  # suffix minimum over time left", T_POL, "monotone projection over time removed"),
    ("M16", POL, "G2 = np.minimum.accumulate(G2, axis=2)  # prefix minimum over loss bins", "G2 = G2  # prefix minimum over loss bins", T_POL, "monotone projection over loss removed"),
    ("M17", POL, "return struct.calcsize(_HDR) + 2 * m + sig_len", "return struct.calcsize(_HDR) + m + sig_len", T_POL, "cluster ACK length: one byte per id"),
    ("M18", POL, "            self.pk.verify(sig, body)", "            pass", T_POL, "signature not verified"),
    ("M19", POL, "if ev != (my_event & 0xFFFFFFFF):", "if ev == (my_event & 0xFFFFFFFF):", T_POL, "event id check inverted"),
    ("M20", POL, "if abs(now_gps_s - fresh) > window_s:", "if now_gps_s - fresh > window_s:", T_POL, "freshness window one-sided"),
    ("M21", POL, "        if sig in self.seen:\n            return ClusterVerdict(\"ignore\", \"replay\")", "        if False:\n            return ClusterVerdict(\"ignore\", \"replay\")", T_POL, "replay check removed"),
    ("M22", POL, "        self.seen.append(sig)\n", "", T_POL, "processed frames not remembered"),
    ("M23", POL, "return ClusterVerdict(\"stop\", \"listed\") if (my_id & 0xFFFF) in ids else ClusterVerdict(\"defer\", \"not_listed\")", "return ClusterVerdict(\"stop\", \"listed\") if (my_id & 0xFFFF) not in ids else ClusterVerdict(\"defer\", \"not_listed\")", T_POL, "listing test inverted"),
    ("M24", POL, "if typ != MSG_CLUSTER_ACK or ver != 1 or len(body) != hl + 2 * m:", "if typ != MSG_CLUSTER_ACK or ver != 1:", T_POL, "length consistency check removed"),
    ("M25", POL, "            self.pending, self.verified_ack = False, True", "            self.pending, self.verified_ack = True, True", T_POL, "vehicle does not stop on a verified listing"),
    ("M26", POL, "        elif v.action == \"defer\":\n            self.defers += 1  # the vehicle stays pending", "        elif v.action == \"defer\":\n            self.defers += 1\n            self.pending = False", T_POL, "a defer becomes a stop"),
    ("M27", POL, "return max(ready, now + DEFER_S[cls] * scale * (0.5 + 0.5 * jitter_u))", "return now + DEFER_S[cls] * scale * (1.0 + 0.5 * jitter_u)", T_POL, "defer interval unbounded above and may lower ready"),
    ("M28", VER, "if not P.tag_ok(raw, self.key, P.ALERT_BODY_LEN):\n            return REJECT_TAG, None", "if False:\n            return REJECT_TAG, None", T_SEC, "base verifier: tag check skipped"),
    ("M29", VER, "if a.counter <= self.last.get(a.node_id, -1):", "if a.counter < self.last.get(a.node_id, -1):", T_SEC, "base verifier: replay counter off by one"),
    ("M30", VER, "return a.node_id == node_id and a.acked_event_id == event_id and a.acked_counter == counter", "return a.node_id == node_id and a.acked_event_id == event_id", T_SEC, "node: ACK counter not checked"),
    ("M31", PKT, "return hmac.compare_digest(raw[body_len:], tag(key, raw[:body_len]))", "return True", T_SEC, "tag comparison always true"),
]


def run(tests: list[str], cwd: Path) -> bool:
    env = {**os.environ, "PYTHONPATH": str(cwd / "src")}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode == 0  # True = all passed = the mutant SURVIVED


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "dummy"))
        # the baseline must pass on the unmutated copy
        for tests in (T_POL, T_SEC):
            assert run(tests, work), f"baseline tests fail on the clean copy: {tests}"
        for mid, f, old, new, tests, desc in MUTANTS:
            p = work / f
            orig = p.read_text(encoding="utf-8")
            if old not in orig:
                rows.append(dict(id=mid, file=f, description=desc, status="NOT_APPLIED"))
                print(mid, "NOT_APPLIED")
                continue
            p.write_text(orig.replace(old, new, 1), encoding="utf-8")
            try:
                survived = run(tests, work)
            finally:
                p.write_text(orig, encoding="utf-8")
            rows.append(dict(id=mid, file=f, description=desc, status="SURVIVED" if survived else "KILLED"))
            print(mid, rows[-1]["status"], desc)
    out = ROOT / "results/tables/rd_mutation.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "file", "description", "status"])
        w.writeheader()
        w.writerows(rows)
    applied = [r for r in rows if r["status"] != "NOT_APPLIED"]
    killed = sum(r["status"] == "KILLED" for r in applied)
    print(f"killed {killed} of {len(applied)} ({killed / len(applied):.0%}); not applied {len(rows) - len(applied)}")
    sys.path.insert(0, str(ROOT / "src"))
    from crashguard.rd_common import Rec

    rec = Rec("rd.cv.mutation.", "scripts/rd_mutation.py", "ANALYTICAL")
    rec.add("mutants", len(applied), "mutants", "hand-written mutants applied to rd_policy.py, verifier.py and packet.py")
    rec.add("killed", killed, "mutants", "mutants caught by at least one failing test")
    rec.add("killed_share", killed / len(applied), "fraction", "below 0.80 means the tests must be extended before evaluation")
    rec.add("survivors", ",".join(r["id"] for r in applied if r["status"] == "SURVIVED") or "none", "ids", "")
    rec.write()


if __name__ == "__main__":
    main()
