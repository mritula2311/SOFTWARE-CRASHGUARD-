"""Hand-written mutation testing of the round-4 modules (V15 section 6): each mutant is one textual change of ``a4_a1.py``, ``a4_a2.py`` or ``a4_common.py`` in a temporary copy of the source tree;
the round-4 tests run against it and the mutant is KILLED if any of them fails. At least 20 mutants and at least 80% killed are required before the freeze.

    python scripts/a4_mutation.py
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
A1 = "src/crashguard/a4_a1.py"
A2 = "src/crashguard/a4_a2.py"
CM = "src/crashguard/a4_common.py"
TESTS = ["tests/test_a4_a1.py", "tests/test_a4_a2.py"]

MUTANTS = [
    ("A101", A1, 'return hmac.new(key, b"P" + body16, hashlib.sha256).digest()[:TAG_LEN]', 'return hmac.new(key, b"" + body16, hashlib.sha256).digest()[:TAG_LEN]', "tag domain prefix removed"),
    ("A102", A1, "if len(raw) != PROV_LEN or raw[1] != MSG_PROV:", "if len(raw) != PROV_LEN:", "provisional type check removed"),
    ("A103", A1, "return hmac.compare_digest(raw[16:], prov_tag(key, raw[:16]))", "return hmac.compare_digest(raw[16:], prov_tag(key, raw[:15]))", "tag covers 15 bytes only"),
    ("A104", A1, "epoch & 0xFFFFFFFF, seq & 0xFF)", "epoch & 0xFFFFFF, seq & 0xFF)", "freshness field narrowed to 3 bytes"),
    ("A105", A1, "int(round(deg * 64.0))", "int(round(deg * 32.0))", "coarse position scale"),
    ("A106", A1, 'acked_event_id=f["epoch"], acked_counter=f["seq"]', 'acked_event_id=f["seq"], acked_counter=f["epoch"]', "ACK names epoch and seq swapped"),
    ("A107", A1, "return a.node_id == node_id and (a.acked_event_id, a.acked_counter) in sent_ids", "return a.node_id == node_id or (a.acked_event_id, a.acked_counter) in sent_ids", "ACK check: and becomes or"),
    ("A108", A1, "if not P.tag_ok(raw_ack, key, P.ACK_LEN - P.TAG_LEN):", "if False:", "ACK tag not verified"),
    ("A109", A1, "if len(raw_ack) != P.ACK_LEN or raw_ack[1] != P.MSG_ACK:", "if len(raw_ack) != P.ACK_LEN:", "ACK type check removed"),
    ("A110", A1, "if t_start + a_prov > t_deadline + 1e-12:", "if t_start + a_prov > t_deadline - 1e-9:", "deadline boundary"),
    ("A111", A1, "if used + a_prov + reserve_tries * a_alert > limit_s + 1e-12:", "if used + a_prov > limit_s + 1e-12:", "confirm reserve ignored"),
    ("A112", A1, "if t_start + a_prov > t_deadline + 1e-12:\n        return \"deadline\"", "if t_start + a_prov > t_deadline + 1e-12:\n        return \"duty\"", "deadline reason mislabelled"),
    ("A113", A1, 'if cfg.exclusive and canc["on"] and t0 >= FINAL_S:', "if False:", "retraction does not withdraw the provisional alert"),
    ("A114", A1, 'if cfg.cap is not None and prov["tries"] >= cfg.cap:', 'if cfg.cap is not None and prov["tries"] > cfg.cap:', "cap off by one"),
    ("A115", A1, 'if (not cfg.after_confirm) and conf["on"] and conf["tries"] >= TRIES3:', 'if (not cfg.after_confirm) and conf["on"] and conf["tries"] >= TRIES3 + 1:', "after-confirm rule never fires"),
    ("A116", A1, 'if got and rng.random() >= p_dl:', 'if got:', "provisional stops without the ACK reaching the car"),
    ("A117", A1, "t_free = end + win + cfg.gap", "t_free = end + cfg.gap", "listen window skipped after a provisional frame"),
    ("A118", A1, 'if st["used"] + a > cfg.limit_s + 1e-12:', 'if st["used"] + a > cfg.limit_s * 3:', "duty guard of the radio loop loosened"),
    ("A119", A1, 'canc["n"] < CANCEL_TX', 'canc["n"] <= CANCEL_TX', "one CANCEL too many"),
    ("A120", A1, 'out["two_d"] = int(y == 1 and math.isfinite(st["prov_arr"]) and st["cancel_rx"] == 0)', 'out["two_d"] = int(y == 1 and math.isfinite(st["prov_arr"]))', "delivery ignores a received CANCEL"),
    ("A121", A1, 'cands.append((max(t_free, conf["ready"]), 0, "conf"))', 'cands.append((t_free, 0, "conf"))', "confirm sent before its ready time"),
    ("A122", A1, 'prov = dict(on=bool(E), ready=te + COMPUTE3, tries=0)', 'prov = dict(on=bool(E), ready=te, tries=0)', "compute time dropped from the ready time"),
    ("A123", A1, "a_prov, a_al, a_ack, a_cn = _air(cfg.prov_len, sf)", "a_prov, a_al, a_ack, a_cn = _air(cfg.prov_len - 10, sf)", "provisional airtime from a wrong length"),
    ("A124", A1, 'stop_prov("ack")', 'stop_prov("cap")', "ACK stop reason mislabelled"),
    ("A125", A1, 'if st["conf_acked"]:', "if False:", "confirm ACK does not stop the provisional repetition (loop branch)"),
    ("A126", A1, "self.sent_ids = {(epoch & 0xFFFFFFFF, seq & 0xFF)}", "self.sent_ids = {(epoch & 0xFFFFFFFF, seq & 0xFF), (0, 0)}", "session accepts an id it never sent"),
    ("B201", A2, "n_rank = n // 2", "n_rank = n // 3", "ranking period length"),
    ("B202", A2, "key=lambda g: (-cnt[g], g)", "key=lambda g: (cnt[g], g)", "ranking order reversed"),
    ("B203", A2, "if cnt[g] > 0]", "if cnt[g] >= 0]", "gateways that never heard the device are ranked"),
    ("B204", A2, "if off + j >= n_rank:", "if off + j > n_rank:", "start boundary off by one"),
    ("B205", A2, "for j in range(0, max(len(m) - T1.MIN_AHEAD, 0)):", "for j in range(0, len(m)):", "frames-ahead rule removed"),
    ("B206", A2, "loss_best = float(1.0 - (cnt[order[0]] / max(n_rank, 1)))", "loss_best = float(cnt[order[0]] / max(n_rank, 1))", "loss rate inverted"),
    ("B207", A2, "mk |= 1 << g", "mk = 1 << g", "receiver set keeps only the last gateway"),
    ("B208", A2, "return ((m & mask) != 0).astype(np.uint8)", "return ((m & mask) == mask).astype(np.uint8)", "set reception requires all gateways"),
    ("B209", A2, "val /= len(picks)", "val /= 1", "device value not normalised"),
    ("B210", A2, "return bool(np.isfinite(t))", "return True", "delivery always true"),
    ("B211", A2, "if lo <= p < hi:", "if lo < p < hi:", "band edge"),
    ("C301", CM, "miss = d - 1", "miss = d", "one lost frame too many per gap"),
    ("C302", CM, "mask = np.bitwise_or.reduceat(gw, starts)", "mask = np.add.reduceat(gw, starts)", "copies of a frame are added, not OR-ed"),
    ("C303", CM, "if d > MAX_GAP:", "if d > MAX_GAP + 1000:", "gap limit loosened"),
]


def run(cwd: Path) -> bool:
    env = {**os.environ, "PYTHONPATH": str(cwd / "src")}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *TESTS], cwd=cwd, env=env, capture_output=True, text=True)
    return r.returncode == 0  # True = all passed = the mutant SURVIVED


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "w"
        shutil.copytree(ROOT / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(ROOT / "tests", work / "tests", ignore=shutil.ignore_patterns("__pycache__", "dummy"))
        try:
            (work / "data").symlink_to(ROOT / "data", target_is_directory=True)
        except OSError:
            pass  # the tests that need built data skip themselves
        assert run(work), "baseline tests fail on the clean copy"
        for mid, f, old, new, desc in MUTANTS:
            p = work / f
            orig = p.read_bytes().decode("utf-8")
            o = old.replace("\n", "\r\n") if "\r\n" in orig else old
            n = new.replace("\n", "\r\n") if "\r\n" in orig else new
            if o not in orig:
                rows.append(dict(id=mid, file=f, description=desc, status="NOT_APPLIED"))
                print(mid, "NOT_APPLIED", flush=True)
                continue
            p.write_bytes(orig.replace(o, n, 1).encode("utf-8"))
            try:
                survived = run(work)
            finally:
                p.write_bytes(orig.encode("utf-8"))
            rows.append(dict(id=mid, file=f, description=desc, status="SURVIVED" if survived else "KILLED"))
            print(mid, rows[-1]["status"], desc, flush=True)
    out = ROOT / "results/tables/a4_mutation.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "file", "description", "status"])
        w.writeheader()
        w.writerows(rows)
    applied = [r for r in rows if r["status"] != "NOT_APPLIED"]
    killed = sum(r["status"] == "KILLED" for r in applied)
    print(f"killed {killed} of {len(applied)} ({killed / len(applied):.0%}); not applied {len(rows) - len(applied)}")
    sys.path.insert(0, str(ROOT / "src"))
    from crashguard.rd_common import Rec

    rec = Rec("a4.cv.mutation.", "scripts/a4_mutation.py", "ANALYTICAL")
    rec.add("mutants", len(applied), "mutants", "hand-written mutants applied to a4_a1.py, a4_a2.py and a4_common.py")
    rec.add("killed", killed, "mutants", "mutants caught by at least one failing test")
    rec.add("killed_share", killed / len(applied), "fraction", "below 0.80 means the tests must be extended before the freeze")
    rec.add("survivors", ",".join(r["id"] for r in applied if r["status"] == "SURVIVED") or "none", "ids", "")
    rec.write()


if __name__ == "__main__":
    main()
