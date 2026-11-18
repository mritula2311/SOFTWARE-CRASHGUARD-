"""Round 7c K2 and K3 (code reading and a behavioural check of the reference base; no experiment). Keys r7c.k2.* and r7c.k3.* (ANALYTICAL).

K2: does the base send an ACK only after the tag verifies? Forged frames (right length, version and type, wrong tag) are fed to every handler that can return an ACK (``BaseVerifier.handle``,
``SctBase.handle_short``, ``SctBase.handle_alert``); the check is that no ACK is returned, no state changes and the base counter does not move. A valid replay is also fed, to state what it costs.
K3: no SisFall data file is tracked, in the history of any ref, or in any release archive.

    python scripts/r7c_k_checks.py
"""
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from crashguard import packet as P  # noqa: E402
from crashguard import sct_protocol as S  # noqa: E402
from crashguard import verifier as V  # noqa: E402
from crashguard.results import record_many  # noqa: E402

key = bytes(range(32))
other = bytes(range(1, 33))
SRC = "scripts/r7c_k_checks.py"
ent: list[dict] = []


def add(name, v, unit, note=""):
    ent.append(dict(name=name, value=v, unit=unit, origin="ANALYTICAL", source_file=SRC, notes=note))


# ---- K2
alert = P.Alert(node_id=7, event_id=1, counter=5, timestamp_ms=1000)
forged = P.encode_alert(alert, other)  # tag under a key the base does not hold
valid = P.encode_alert(alert, key)
b = V.BaseVerifier(key, reack_interval_s=None, budget=None)
n_forged = 200
acks = 0
for _ in range(n_forged):
    d, ack = b.handle(forged)
    acks += ack is not None
state_ok = b.last == {} and b.base_counter == 0 and b.acks_sent == 0
add("r7c.k2.verifier.forged_frames", n_forged, "frames", "BaseVerifier.handle, right length, version, type; tag under another key")
add("r7c.k2.verifier.acks_for_forged", acks, "ACKs", "0 means no ACK is sent before the tag verifies")
add("r7c.k2.verifier.state_unchanged", int(state_ok), "flag", "counters, base counter and ACK count did not move")
d1, a1 = b.handle(valid)
d2, a2 = b.handle(valid)  # a replay of a captured valid frame by a node without the key
add("r7c.k2.verifier.replay_of_valid_frame_gets_reack", int(a2 is not None), "flag", "a keyless replay of a captured VALID frame is re-acknowledged unless reack_interval_s or a duty budget is set (both default to off)")
b2 = V.BaseVerifier(key, reack_interval_s=30.0, budget=V.DutyBudget(0.01, 36.0))
b2.handle(valid, now=0.0)
n_reack = sum(b2.handle(valid, now=1.0 + i)[1] is not None for i in range(50))
add("r7c.k2.verifier.reacks_with_limit_on_50_replays", n_reack, "ACKs", "with reack_interval_s = 30 s and a 1% budget, 50 replays at one per second get one re-ACK (at the end of the interval)")

sb = S.SctBase(key)
fl_forged = S.encode_short(S.Short(node_id=7, counter=3, severity=1, msg_type=S.MSG_FLASH), other)
n_ack = sum(sb.handle_short(fl_forged)[1] is not None for _ in range(n_forged))
add("r7c.k2.sct_short.acks_for_forged", n_ack, "ACKs", "SctBase.handle_short (flash and cancel), tag under another key")
n_ack = sum(sb.handle_alert(forged)[1] is not None for _ in range(n_forged))
add("r7c.k2.sct_alert.acks_for_forged", n_ack, "ACKs", "SctBase.handle_alert, tag under another key")
add("r7c.k2.sct_state_unchanged", int(sb.last_flash == {} and sb.last_alert == {} and sb.base_counter == 0), "flag")
# the micro frame: lookup only returns a verdict (no ACK path)
from crashguard import frame_layout as FL  # noqa: E402

add("r7c.k2.micro_lookup_returns_bool_only", int(FL.micro_lookup.__annotations__.get("return") in (bool, "bool")), "flag", "micro_lookup returns a verdict and has no ACK path; a failed tag is a reject")
src = (ROOT / "src/crashguard/verifier.py").read_text(encoding="utf-8")
hb = src[src.index("    def handle(self, raw"):src.index("    def reboot")]
add("r7c.k2.verifier.tag_check_before_any_ack_or_state_in_source", int(hb.index("P.tag_ok(raw, self.key, P.ALERT_BODY_LEN)") < hb.index("self.last[a.node_id] = a.counter") < hb.index("return ACCEPT, ack")), "flag", "order of statements in BaseVerifier.handle: tag check, then the counter update, then the ACK is returned")
add("r7c.k2.ns3_models_tag", 0, "flag", "the ns-3 gateway application has no tag check: it acknowledges every received confirmed frame, so the simulations do not model keyless nodes")
add("r7c.k2.cell_level_rate_limiting_implemented", 0, "flag", "cell-level rate limiting of failed-tag frames is a design of the quarantine model (R6-3b, r5_l8); the reference verifier only rejects")

# ---- K3
tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
pat = re.compile(r"sisfall|[DF]\d\d_S[AE]\d\d_R\d\d", re.I)
n_tracked = sum(1 for f in tracked if pat.search(f) and f.startswith(("data/", "results/", "tests/", "c_bundle/")) or re.search(r"[DF]\d\d_S[AE]\d\d_R\d\d", f))
hist = subprocess.run(["git", "log", "--all", "--name-only", "--pretty=format:"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
n_hist = len({f for f in hist if re.search(r"sisfall.*\.(zip|txt|csv|npz|npy|parquet|pkl)$|[DF]\d\d_S[AE]\d\d_R\d\d", f, re.I)})
n_zip = 0
for z in sorted((ROOT / "release").glob("*.zip")):
    n_zip += sum(1 for n in zipfile.ZipFile(z).namelist() if re.search(r"sisfall.*\.(zip|txt|csv|npz|npy|parquet|pkl)$|[DF]\d\d_S[AE]\d\d_R\d\d", n, re.I))
local = (ROOT / "data/raw/r5_l10/sisfall.zip").exists()
add("r7c.k3.tracked_sisfall_data_files", n_tracked, "files", "git ls-files: data files or trial files of SisFall")
add("r7c.k3.history_sisfall_data_files", n_hist, "files", "git log --all --name-only: any path that ever was a SisFall data file")
add("r7c.k3.release_zip_sisfall_data_files", n_zip, "files", "every release/*.zip")
add("r7c.k3.local_ignored_copy_present", int(local), "flag", "data/raw/r5_l10/sisfall.zip is on the author's disk, untracked and git-ignored (data/raw is ignored); it is not in the repository, its history or any release archive")
record_many(ent, purge_prefixes=("r7c.k2.", "r7c.k3."))
for e in ent:
    print(e["name"], e["value"])
