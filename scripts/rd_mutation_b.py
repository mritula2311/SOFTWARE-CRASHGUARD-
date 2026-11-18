"""CV 5, session 2: hand-written mutants of the D3 module (rd_d3.py), of its simulator integration (world_sim.py) and of the firmware C path (cg_rd.c). mutmut does not run on Windows.

Python mutants: a test of tests/redesign/test_rd_d3.py must fail. C mutants: the differential test (600 random traces) must report a mismatch (a compile error also counts as killed).
Results: results/tables/rd_mutation_b.csv and keys rd.cv.mutation_b.*. Below 80% killed means the tests are extended before the evaluation.

    python scripts/rd_mutation_b.py
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
D3 = "src/crashguard/rd_d3.py"
WS = "src/crashguard/world_sim.py"
CC = "firmware_rd/cg_rd.c"
T_D3 = ["tests/redesign/test_rd_d3.py"]

PY = [
    ("D01", D3, "math.ceil(n_hat / m - 1e-9)", "math.floor(n_hat / m - 1e-9)", "slot count rounded down"),
    ("D02", D3, "min(max(2, math.ceil(n_hat / m - 1e-9)), s_cap)", "min(max(1, math.ceil(n_hat / m - 1e-9)), s_cap)", "one slot allowed"),
    ("D03", D3, "int(math.floor(EPOCH_CAP_S / slot_s + 1e-9))", "int(math.ceil(EPOCH_CAP_S / slot_s + 1e-9))", "epoch cap rounded up"),
    ("D04", D3, "s_cap = max(2, min(S_MAX,", "s_cap = max(1, min(S_MAX,", "cap floor of two slots removed"),
    ("D05", D3, 'struct.pack("<IH", epoch & 0xFFFFFFFF, vehicle_id & 0xFFFF)', 'struct.pack("<IH", vehicle_id & 0xFFFFFFFF, epoch & 0xFFFF)', "hash inputs swapped"),
    ("D06", D3, 'int.from_bytes(h, "big") % s', 'int.from_bytes(h, "little") % s', "hash byte order"),
    ("D07", D3, "return cls == 3 and n_heard_others >= p.thr3", "return cls >= 2 and n_heard_others >= p.thr3", "active for Severe too"),
    ("D08", D3, "return cls == 3 and n_heard_others >= p.thr3", "return cls == 3 and n_heard_others > p.thr3", "threshold off by one"),
    ("D09", D3, "(j % 2 == 0 and j >= 2)", "(j % 2 == 1)", "alternation on odd retries"),
    ("D10", D3, "return min(12, sf_d1 + 1) if", "return (sf_d1 + 1) if", "spreading factor cap removed"),
    ("D11", D3, "slot = air_alert_s + GUARD_S\n    s = n_slots", "slot = air_alert_s\n    s = n_slots", "guard removed"),
    ("D12", D3, "ep = s * slot\n", "ep = slot\n", "epoch is one slot"),
    ("D13", D3, "e0 = int(math.floor((t_min - offset_s) / ep + 1e-12))", "e0 = int(math.ceil((t_min - offset_s) / ep + 1e-12))", "first epoch rounded up"),
    ("D14", D3, "for e in (e0, e0 + 1, e0 + 2):", "for e in (e0,):", "only one epoch examined"),
    ("D15", D3, "        if t >= t_min - 1e-12:\n            return t if", "        if True:\n            return t if", "slot before t_min accepted"),
    ("D16", D3, "return t if t + air_alert_s <= deadline_end + 1e-12 else None", "return t", "deadline check removed"),
    ("D17", D3, "slot_index(e, vehicle_id, s) * slot + offset_s", "slot_index(e, vehicle_id, s) * slot", "clock offset dropped"),
    ("D18", D3, "(t_min - offset_s) / ep", "t_min / ep", "offset ignored in epoch index"),
    ("D19", D3, "GUARD_S = 0.02", "GUARD_S = 0.0", "guard constant zero"),
    ("D20", D3, "EPOCH_CAP_S = 5.0", "EPOCH_CAP_S = 50.0", "epoch cap 50 s"),
    ("D21", D3, "slot_index(e, vehicle_id, s) * slot + offset_s", "slot_index(e, vehicle_id, s) * ep + offset_s", "slot index times epoch"),
    ("D22", D3, "if t >= t_min - 1e-12:", "if t >= t_min + 1e-12:", "boundary slot excluded"),
    ("W01", WS, 'D3.slot_time(d3, n_oth + 1, a["node"],', 'D3.slot_time(d3, n_oth, a["node"],', "burst estimate without the vehicle itself"),
    ("W02", WS, '                                        a["ready"] = st_\n', '                                        a["ready"] = a["ready"]\n', "slot time not applied"),
    ("W03", WS, 'if D3.active(d3, n_oth, a["sev"]):', "if True:", "D3 always active"),
    ("W04", WS, 'if j_ != tx["node"] and nodes[j_]["pending"] and', 'if nodes[j_]["pending"] and', "a vehicle hears itself"),
    ("W05", WS, 'sf_r = D3.alt_sf(a["rounds"], pick[1]) if d3.alt else pick[1]', "sf_r = pick[1]", "alternation never applied"),
]

C = [
    ("C01", CC, "int de = (t_sym > 16.0) ? 1 : 0;", "int de = (t_sym > 32.0) ? 1 : 0;", "low data rate optimisation threshold"),
    ("C02", CC, "int np = (int)q * 5;", "int np = (int)q * 4;", "coding rate"),
    ("C03", CC, "return cg_air_s(nbytes, sf) + 0.1 + cg_air_s(CG_ACK_LEN, sf) + 0.1;", "return cg_air_s(nbytes, sf) + 0.1 + cg_air_s(CG_ACK_LEN, sf);", "round margin dropped"),
    ("C04", CC, "for (i = 0; i < CG_TAG_LEN; i++) diff |= (uint8_t)(mac[i] ^ frame[body_len + i]);", "for (i = 0; i < CG_TAG_LEN - 1; i++) diff |= (uint8_t)(mac[i] ^ frame[body_len + i]);", "last tag byte not compared"),
    ("C05", CC, "if (d > W) return 0;", "if (d >= W) return 0;", "freshness boundary"),
    ("C06", CC, "if (r->field[i] == field && r->seq[i] == seq) return 0;", "if (r->field[i] == field) return 0;", "ring compares the field only"),
    ("C07", CC, "s->a = a0 + (s->a - a0) * s->forget;", "s->a = a0 + (s->a - a0);", "forgetting skipped"),
    ("C08", CC, "if (failed) s->a += 1.0; else s->b += 1.0;", "if (failed) s->b += 1.0; else s->a += 1.0;", "failure and success swapped"),
    ("C09", CC, "for (i = 0; i < 7; i++) if (E[i] <= l) n++;", "for (i = 0; i < 7; i++) if (E[i] < l) n++;", "loss bin edge"),
    ("C10", CC, "for (i = 0; i < 3; i++) if (E[i] <= n) k++;", "for (i = 0; i < 3; i++) if (E[i] < n) k++;", "load bin edge"),
    ("C11", CC, "double f = floor(budget_s / unit_s + 1e-9);", "double f = ceil(budget_s / unit_s + 1e-9);", "budget rounded up"),
    ("C12", CC, "if (tau_s <= 0) return 0;", "if (tau_s < -1e9) return 0;", "no-time-left check removed"),
    ("C13", CC, "tt = (int)floor(tau_s / dt + 1e-9);", "tt = (int)ceil(tau_s / dt + 1e-9);", "time step rounded up"),
    ("C14", CC, "return t_start + airtime <= t_event + deadline_s + 1e-12;", "return t_start <= t_event + deadline_s + 1e-12;", "airtime ignored"),
    ("C15", CC, "v = now + d * scale * (0.5 + 0.5 * jitter_u);", "v = now + d * scale * (1.0 + 0.5 * jitter_u);", "defer interval"),
    ("C16", CC, "if (!s_below_L(sm + 32) || crypto_sign_open", "if (crypto_sign_open", "non-canonical signature accepted"),
    ("C17", CC, "if (ev != my_event) { *reason = CG_R_OTHER_EVENT; return CG_IGNORE; }", "", "event id not checked"),
    ("C18", CC, "if (d > (double)window_s) { *reason = CG_R_STALE; return CG_IGNORE; }", "", "freshness not checked"),
    ("C19", CC, "if (memcmp(v->seen[i], frame + body_len, CG_SIG_LEN) == 0) { *reason = CG_R_REPLAY; return CG_IGNORE; }", "if (0) { *reason = CG_R_REPLAY; return CG_IGNORE; }", "replay ring not consulted"),
    ("C20", CC, "if (get16(frame + CG_CL_HDR + 2 * i) == my_id) { *reason = CG_R_LISTED; return CG_STOP; }", "if (get16(frame + CG_CL_HDR + 2 * i) != my_id) { *reason = CG_R_LISTED; return CG_STOP; }", "listing test inverted"),
    ("C21", CC, "if (typ != 4 || ver != 1 || body_len != (size_t)(CG_CL_HDR + 2 * m))", "if (typ != 4 || ver != 1)", "length consistency not checked"),
    ("C22", CC, "return (gate_on && cdefer < max_defers) ? CG_DEFER : CG_IGNORE;", "return (gate_on) ? CG_DEFER : CG_IGNORE;", "defer bound removed"),
    ("C23", CC, "int s_cap = (int)floor(5.0 / slot_s + 1e-9), s, want;", "int s_cap = (int)floor(50.0 / slot_s + 1e-9), s, want;", "D3 epoch cap"),
    ("C24", CC, "return (j % 2 == 0 && j >= 2) ?", "return (j % 2 == 1) ?", "D3 alternation parity"),
    ("C25", CC, "if (t + air_alert_s <= deadline_end + 1e-12) { *out = t; return 1; }", "{ *out = t; return 1; }", "D3 deadline check removed"),
    ("C26", CC, "uint8_t k[64], ipad[64 + 600], opad[64 + 32], inner[32];", "uint8_t k[64], ipad[64 + 600], opad[64 + 32], inner[32]; (void)0;", "equivalent mutant (no change of behaviour)"),
]

TABS = None


def run_py(tests: list[str], cwd: Path) -> bool:
    env = {**os.environ, "PYTHONPATH": str(cwd / "src")}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode == 0  # True = mutant SURVIVED


def wsl(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return "/mnt/" + s[0].lower() + s[2:]


def run_c(work: Path) -> str:
    """Compile the mutated C (in a space-free directory inside the repository, because the temporary directory path contains a space) and compare it with the Python reference on random traces.
    Returns 'SURVIVED' (no mismatch), 'KILLED' (a mismatch) or 'COMPILE_ERROR' (not counted as killed)."""
    mdir = ROOT / "build" / "mutc"
    shutil.rmtree(mdir, ignore_errors=True)
    shutil.copytree(work / "firmware_rd", mdir)
    out_bin = mdir / "mut_cli"
    cmd = f"cd {wsl(mdir)} && gcc -std=c99 -O2 -ffp-contract=off -w -o {wsl(out_bin)} cg_rd.c cg_rd_cli.c cg_stubs.c tweetnacl.c -lm"
    r = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", cmd], capture_output=True, text=True)
    if r.returncode != 0:
        return "COMPILE_ERROR"
    from crashguard import rd_firmware as F

    F.BIN = out_bin
    try:
        return "SURVIVED" if F.run_diff(600, seed=5, tabs=TABS, verbose=False)["mismatched_ops"] == 0 else "KILLED"
    except Exception as e:  # a crash of the mutated binary (for example a missing output line) is a detected difference
        return "KILLED" if "returned" in str(e) else "COMPILE_ERROR"


def apply(work: Path, f: str, old: str, new: str):
    p = work / f
    orig = p.read_bytes().decode("utf-8")
    norm = orig.replace("\r\n", "\n")
    if old not in norm:
        return None, orig
    p.write_bytes(norm.replace(old, new, 1).encode("utf-8"))
    return p, orig


def main() -> None:
    global TABS
    sys.path.insert(0, str(ROOT / "src"))
    from crashguard import rd_firmware as F

    TABS = F.make_tables()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "dummy"))
        shutil.copytree(ROOT / "firmware_rd", work / "firmware_rd")
        (work / "data").mkdir()
        for d in (("data", "processed"), ("results",)):  # junctions (no privilege needed): large pickles and results.json are read in place
            subprocess.run(["cmd", "/c", "mklink", "/J", str(work.joinpath(*d)), str(ROOT.joinpath(*d))], check=True, capture_output=True)
        assert run_py(T_D3, work), "baseline tests fail on the clean copy"
        assert run_c(work) == "SURVIVED", "the clean C build does not match the reference"
        for mid, f, old, new, desc in PY + C:
            p, orig = apply(work, f, old, new)
            if p is None:
                rows.append(dict(id=mid, file=f, description=desc, status="NOT_APPLIED"))
                print(mid, "NOT_APPLIED")
                continue
            try:
                status = ("SURVIVED" if run_py(T_D3, work) else "KILLED") if f.endswith(".py") else run_c(work)
            finally:
                p.write_bytes(orig.encode("utf-8"))
            rows.append(dict(id=mid, file=f, description=desc, status=status))
            print(mid, rows[-1]["status"], desc, flush=True)
    out = ROOT / "results/tables/rd_mutation_b.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "file", "description", "status"])
        w.writeheader()
        w.writerows(rows)
    applied = [r for r in rows if r["status"] not in ("NOT_APPLIED", "COMPILE_ERROR")]
    killed = sum(r["status"] == "KILLED" for r in applied)
    print(f"killed {killed} of {len(applied)} ({killed / len(applied):.0%}); not applied {len(rows) - len(applied)}")
    from crashguard.rd_common import Rec

    rec = Rec("rd.cv.mutation_b.", "scripts/rd_mutation_b.py", "ANALYTICAL")
    rec.add("mutants", len(applied), "mutants", "hand-written mutants of rd_d3.py, its world_sim integration and the firmware C path (cg_rd.c); C26 is an equivalent mutant by design")
    rec.add("killed", killed, "mutants", "mutants caught by a failing test or a differential mismatch (or a compile error)")
    rec.add("killed_share", killed / len(applied), "fraction", "below 0.80 means the tests must be extended before evaluation")
    rec.add("survivors", ",".join(r["id"] for r in applied if r["status"] == "SURVIVED") or "none", "ids", "")
    rec.write()


if __name__ == "__main__":
    main()
