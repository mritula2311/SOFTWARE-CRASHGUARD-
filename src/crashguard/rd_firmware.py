"""D6 and CV4: the firmware decision path (C, host build, ``firmware_rd/``) against the Python reference that the simulator uses.

Ops are generated as text lines for the C test harness (``firmware_rd/cg_rd_cli.c``), each paired with the Python reference result. Doubles are compared bit for bit (C99 hex floats). A trace is one
vehicle history: a D1 node-event walk (Beta updates, table lookups, defers, D3 slots, the D2 decision) plus one to three primitive ops (alert frame and tag, tampered tag, freshness sequence, cluster-ACK
frames of several kinds: valid listed, valid not listed, tampered, wrong event, stale, replayed, truncated, malformed but signed, wrong signing key, non-canonical signature).

    python -m crashguard.rd_firmware diff 10000      # CV4: writes results/tables/rd_fw_diff.json and the rd.d6.* keys
    python -m crashguard.rd_firmware replay          # simulator decisions recorded in real runs, replayed through the C path
    python -m crashguard.rd_firmware size            # code and table sizes of the host build (not the ESP32)

Needs WSL with gcc (``firmware_rd/build.sh``). The Python side never imports the C code; the C side is a separate process.
"""
from __future__ import annotations

import json
import math
import random
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

from crashguard import ar_r1 as R1
from crashguard import packet as PK
from crashguard import rd_d3 as D3
from crashguard import rd_policy as RP
from crashguard.lora import airtime_ms

ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "build" / "fw" / "cg_rd_cli"
TAB_DIR = ROOT / "data" / "processed"
FROZEN_A = ROOT / "results" / "tables" / "rd_frozen_A.json"


def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return "/mnt/" + s[0].lower() + s[2:]


def build() -> None:
    subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", f"bash {wsl_path(ROOT / 'firmware_rd' / 'build.sh')}"], check=True, capture_output=True)


def run_cli(lines: list[str]) -> list[str]:
    inp = ("\n".join(lines) + "\n").encode("utf-8")
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", wsl_path(BIN)], input=inp, capture_output=True, check=True).stdout.decode("utf-8").replace("\r", "").split("\n")
    if out and out[-1] == "":
        out = out[:-1]
    if len(out) != len(lines):
        raise RuntimeError(f"C harness returned {len(out)} lines for {len(lines)} commands")
    return out


def hx(x: float) -> str:
    return float(x).hex()


def same_float(a: str, b: str) -> bool:
    try:
        return struct.pack("<d", float.fromhex(a)) == struct.pack("<d", float.fromhex(b))
    except ValueError:
        return False


# ------------------------------------------------------------------------------------------------ the D1 table as a blob for the firmware
def table_blob(tab: RP.D1Table) -> bytes:
    out = bytearray(b"CGD1")
    out += bytes([tab.sf0, 0, 0, 0])
    out += struct.pack("<HH", tab.A[2].shape[1], tab.A[3].shape[1])
    for c in (2, 3):
        a = tab.A[c].astype(np.int16)
        out += np.where(a < 0, 255, a).astype(np.uint8).tobytes(order="C")
    return bytes(out)


def frozen_d1_params() -> RP.D1Params:
    d = json.loads(FROZEN_A.read_text(encoding="utf-8"))["params"]["d1"]
    return RP.D1Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()})


def make_tables(sfs=(8, 9, 10, 11)) -> dict[int, RP.D1Table]:
    p = frozen_d1_params()
    tabs = {}
    for sf in sfs:
        tabs[sf] = RP.D1Table(sf, p)
        (TAB_DIR / f"rd_fw_d1_sf{sf}.bin").write_bytes(table_blob(tabs[sf]))
    return tabs


# ------------------------------------------------------------------------------------------------ op builders: (command line, reference result as a comparable string)
class Gen:
    def __init__(self, seed: int, tabs: dict[int, RP.D1Table]):
        self.rng = random.Random(seed)
        self.tabs = tabs
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        self.sk = Ed25519PrivateKey.from_private_bytes(bytes(self.rng.randrange(256) for _ in range(32)))  # seeded: the run is reproducible byte for byte
        self.pk = self.sk.public_key()
        self.pk_hex = self.pk.public_bytes_raw().hex()
        self.veh_sk = Ed25519PrivateKey.from_private_bytes(bytes(self.rng.randrange(256) for _ in range(32)))  # a vehicle-held key (an attacker holding only a vehicle key)

    # --- D1 node-event walk
    def node_walk(self) -> list[tuple[str, str]]:
        r = self.rng
        sf0 = r.choice(list(self.tabs))
        tab = self.tabs[sf0]
        n0, l0, fg = r.choice([(6.0, 0.3, 0.97), (6.0, 0.4, 0.9), (3.0, 0.2, 1.0)])
        ops: list[tuple[str, str]] = []
        beta = RP.BetaLoss(n0, l0, fg)
        ops.append((f"BETA_RESET {hx(n0)} {hx(l0)} {hx(fg)}", ""))
        for _ in range(r.randint(0, 8)):
            f = r.random() < r.choice([0.2, 0.5, 0.8])
            beta.update(f)
            ops.append((f"BETA {int(f)}", "F:" + hx(beta.mean)))
        c = r.choice([2, 3])
        dl = RP.DEADLINE_S[c]
        tau = dl - r.choice([0.0, 0.3, 1.0])
        j = 0
        used = 0.0
        budget_total = r.choice([0.5, 2.0, 10.0, 50.0, 400.0])
        for _step in range(14):
            n_heard = r.choice([0, 0, 1, 3, 4, 9, 10, 25])
            bud = max(budget_total - used, 0.0) * r.choice([0.3, 0.5, 1.0])
            pick = tab.lookup(c, j, tau, beta.mean, n_heard, bud)
            lh = hx(beta.mean)
            ops.append((f"D1 {sf0} {c} {j} {hx(tau)} {lh} {n_heard} {hx(bud)}", "NONE" if pick is None else f"{hx(pick[0])} {pick[1]}"))
            # bins and budget units
            ops.append((f"BINS {lh} {n_heard} {hx(bud)} {hx(tab.unit_s)}", f"{RP.loss_bin(beta.mean)} {RP.load_bin(n_heard)} {RP.budget_units(bud, tab.unit_s)}"))
            if pick is None:
                break
            gap, sf = pick
            # retry_allowed for the planned transmission
            now = dl - tau
            air = RP.air_s(RP.ALERT_LEN, sf)
            t_start = (dl - air * r.uniform(0.2, 1.6)) if r.random() < 0.4 else now + gap  # boundary cases: the transmission straddles the class deadline
            ops.append((f"RETRYOK {hx(dl)} 0x0.0p+0 {hx(t_start)} {hx(air)}", str(int(RP.retry_allowed(dl, 0.0, t_start, air)))))
            # D3 slot decision
            n_oth = r.choice([0, 1, 2, 3, 5, 12, 25])
            p3 = D3.D3Params(thr3=r.choice([2, 3, 4]), m=r.choice([1.0, 2.0, 3.0]), alt=r.random() < 0.5)
            ops.append((f"D3ACTIVE {p3.thr3} {n_oth} {c}", str(int(D3.active(p3, n_oth, c)))))
            sf_r = D3.alt_sf(j, sf) if p3.alt else sf
            ops.append((f"D3ALT {j} {sf}", str(D3.alt_sf(j, sf))))
            a_air = RP.air_s(RP.ALERT_LEN, sf_r)
            vid = r.randrange(65536)
            off = r.uniform(-D3.EPS_S, D3.EPS_S)
            t_min = now + gap + RP.round_s(sf0)
            dend = dl + r.choice([0.0, 0.0, 3.0])
            st = D3.slot_time(p3, n_oth + 1, vid, t_min, off, a_air, dend)
            ops.append((f"D3TIME {p3.thr3} {hx(p3.m)} {n_oth + 1} {vid} {hx(t_min)} {hx(off)} {hx(a_air)} {hx(dend)}", "NONE" if st is None else hx(st)))
            ops.append((f"D3SLOTS {n_oth + 1} {hx(p3.m)} {hx(a_air + D3.GUARD_S)}", str(D3.n_slots(n_oth + 1, p3.m, a_air + D3.GUARD_S))))
            ops.append((f"D3IDX {r.randrange(10**6)} {vid} {r.randint(2, 12)}", ""))
            ep, s_ = r.randrange(10**6), r.randint(2, 12)
            ops[-1] = (f"D3IDX {ep} {vid} {s_}", str(D3.slot_index(ep, vid, s_)))
            # D2 decision and defer arithmetic
            listed, gate, cdef, mx = r.randint(0, 1), r.randint(0, 1), r.randint(0, 4), 3
            ref = "stop" if listed else ("defer" if (gate and cdef < mx) else "none")
            ops.append((f"D2DEC {listed} {gate} {cdef} {mx}", ref))
            u, sc, rd = r.random(), r.choice([1.0, 2.5, 0.5]), now + gap
            ops.append((f"DEFER {c} {hx(now)} 0x0.0p+0 {hx(rd)} {hx(u)} {hx(sc)}", hx(RP.defer_until(c, now, 0.0, rd, u, sc))))
            # round outcome
            failed = r.random() < r.choice([0.2, 0.5, 0.8])
            beta.update(failed)
            ops.append((f"BETA {int(failed)}", "F:" + hx(beta.mean)))
            if not failed:
                break
            tau -= gap + RP.round_s(sf)
            used += air
            j += 1
            if tau <= 0 and r.random() < 0.7:
                break
        return ops

    # --- primitive ops
    def alert_op(self) -> list[tuple[str, str]]:
        r = self.rng
        key = bytes(r.randrange(256) for _ in range(r.choice([16, 32, 8, 64, 80])))
        a = PK.Alert(node_id=r.randrange(2**32), event_id=r.randrange(2**32), counter=r.randrange(2**32), timestamp_ms=r.randrange(2**32), severity=r.randrange(4), impact_side=r.randrange(5), angle_deg_x10=r.randrange(3600),
                     lat_e7=r.randint(-2**31, 2**31 - 1), lon_e7=r.randint(-2**31, 2**31 - 1), peak_g_x100=r.randrange(65536), ml_prob_x10000=r.randrange(10001), rule_sev=r.randrange(4), sw_mask=r.randrange(256),
                     sw_first=r.randrange(256), rollover=r.randrange(2), delta_v_kmh_x100=r.randrange(65536), asi_x100=r.randrange(65536), reserved=bytes(r.randrange(256) for _ in range(PK.RESERVED_LEN)))
        raw = PK.encode_alert(a, key)
        line = f"ALERT {key.hex()} {a.version} {a.msg_type} {a.node_id} {a.event_id} {a.counter} {a.timestamp_ms} {a.severity} {a.impact_side} {a.angle_deg_x10} {a.lat_e7} {a.lon_e7} {a.peak_g_x100} {a.ml_prob_x10000} {a.rule_sev} {a.sw_mask} {a.sw_first} {a.rollover} {a.delta_v_kmh_x100} {a.asi_x100} {a.reserved.hex()}"
        ops = [(line, raw.hex()), (f"HMAC {key.hex()} {raw[:89].hex()}", PK.hmac.new(key, raw[:89], PK.hashlib.sha256).hexdigest()), (f"TAGOK {key.hex()} {raw.hex()} 89", "1")]
        bad = bytearray(raw)
        pos = r.randrange(97)
        bad[pos] ^= 1 << r.randrange(8)
        ops.append((f"TAGOK {key.hex()} {bytes(bad).hex()} 89", str(int(PK.tag_ok(bytes(bad), key, 89)))))
        ext = raw + bytes([r.randrange(256)])  # a trailing byte: both sides must reject
        ops.append((f"TAGOK {key.hex()} {ext.hex()} 89", str(int(PK.tag_ok(ext, key, 89)))))
        ack = bytes(r.randrange(256) for _ in range(PK.ACK_BODY_LEN))
        ackf = ack + PK.tag(key, ack)
        ops.append((f"TAGOK {key.hex()} {ackf.hex()} 18", "1"))
        badk = bytes(r.randrange(256) for _ in range(16))
        ops.append((f"TAGOK {badk.hex()} {ackf.hex()} 18", str(int(PK.tag_ok(ackf, badk, 18)))))
        return ops

    def fresh_op(self) -> list[tuple[str, str]]:
        r = self.rng
        W, R = r.choice([(2, 2), (5, 4), (10, 8), (10, 256), (30, 3)])
        ops = [("FRESH_RESET", "")]
        base = dict(ring=(), last={})
        now = r.randrange(1000, 2000)
        seen = []
        for _ in range(r.randint(3, 30)):
            now += r.choice([0, 0, 1, 2])
            if seen and r.random() < 0.35:
                field, seq = r.choice(seen)  # replay of an earlier entry
            else:
                field, seq = now + r.randint(-W - 2, W + 2), r.randint(0, 3)
            ok, base = R1.accept("gtf", base, ("ts", field, seq, 0), now, W, R)
            seen.append((field, seq))
            ops.append((f"FRESH {field} {seq} {now} {W} {R}", str(int(ok))))
        return ops

    def cluster_op(self) -> list[tuple[str, str]]:
        r = self.rng
        ver = RP.ClusterAckVerifier(self.pk, ring=16)
        ops = [(f"VER_RESET {self.pk_hex}", "")]
        my_id, my_ev = r.randrange(65536), r.randrange(2**32)
        now = float(r.randrange(10_000, 20_000)) + r.choice([0.0, 0.5])
        window = r.choice([10, 10, 5])
        frames: list[bytes] = []
        for _ in range(r.choice([3, 5, 8, 20])):
            kind = r.choice(["listed", "unlisted", "tamper_body", "tamper_sig", "other_event", "stale", "stale_edge", "replay", "trunc", "wrong_key", "bad_count", "bad_type", "noncanonical", "listed", "unlisted", "short"])
            ids = [r.randrange(65536) for _ in range(r.randint(0, 30))]
            if kind in ("listed",) or r.random() < 0.15:
                ids.append(my_id)
            if kind == "unlisted":
                ids = [i for i in ids if i != my_id]
            ev, fresh = my_ev, int(now) + r.randint(-3, 3)
            if kind == "other_event":
                ev = (my_ev + r.randint(1, 5)) & 0xFFFFFFFF
            if kind == "stale":
                fresh = int(now) - window - r.randint(1, 30)
            if kind == "stale_edge":
                fresh = int(now - window) if now == int(now) else int(math.floor(now - window))
            sk = self.veh_sk if kind == "wrong_key" else self.sk
            try:
                fr = RP.encode_cluster_ack(sk, ev, fresh, ids)
            except ValueError:
                fr = RP.encode_cluster_ack(sk, ev, fresh, ids[:10])
            if kind in ("bad_count", "bad_type"):
                body = bytearray(fr[:-64])
                if kind == "bad_count":
                    body[10] = (body[10] + r.choice([1, 2, 255])) & 0xFF
                else:
                    body[r.choice([0, 1])] ^= r.choice([1, 2, 7])
                fr = bytes(body) + sk.sign(bytes(body))
            if kind == "tamper_body":
                b = bytearray(fr)
                b[r.randrange(len(fr) - 64)] ^= 1 << r.randrange(8)
                fr = bytes(b)
            if kind == "tamper_sig":
                b = bytearray(fr)
                b[len(fr) - 64 + r.randrange(64)] ^= 1 << r.randrange(8)
                fr = bytes(b)
            if kind == "noncanonical":
                L = 2**252 + 27742317777372353535851937790883648493
                s_int = int.from_bytes(fr[-32:], "little") + L
                fr = fr[:-32] + (s_int & ((1 << 256) - 1)).to_bytes(32, "little")
            if kind == "trunc":
                fr = fr[: r.randrange(0, len(fr))]
            if kind == "short":
                fr = fr[: r.randrange(0, 75)]
            if kind == "replay" and frames:
                fr = r.choice(frames)
            frames.append(fr)
            v = ver.check(fr, my_id, my_ev, now, window)
            ops.append((f"CLUSTER {fr.hex() if fr else '00'} {my_id} {my_ev} {hx(now)} {window}", f"{v.action} {v.reason}"))
            if not fr:  # the empty frame cannot be written on a line; skip it for both sides
                ops[-1] = (ops[-1][0].replace("CLUSTER 00", "CLUSTER 00"), f"{v.action} {v.reason}")
        return ops

    def airtime_ops(self) -> list[tuple[str, str]]:
        r = self.rng
        out = []
        for _ in range(3):
            n, sf = r.choice([14, 24, 26, 40, 97, r.randint(1, 255)]), r.randint(7, 12)
            out.append((f"AIR {n} {sf}", hx(airtime_ms(n, sf))))
            out.append((f"ROUND {sf} {n}", hx(RP.round_s(sf, n))))
        return out

    def trace(self) -> list[tuple[str, str]]:
        ops = self.node_walk()
        for _ in range(self.rng.randint(1, 3)):
            ops += self.rng.choice([self.alert_op, self.fresh_op, self.cluster_op, self.airtime_ops])()
        return ops


def compare(ref: str, got: str) -> bool:
    if ref == "":
        return True
    if ref.startswith("F:"):
        return same_float(ref[2:], got)
    if " " in ref and ref.split(" ")[0].startswith("0x") and ref.split(" ")[-1].isdigit():  # "gap_hex sf"
        a, b = ref.split(" "), got.split(" ")
        return len(a) == len(b) == 2 and same_float(a[0], b[0]) and a[1] == b[1]
    if ref.startswith("0x") or ref.startswith("-0x"):
        return same_float(ref, got)
    return ref == got


def run_diff(n_traces: int = 10000, seed: int = 42, tabs: dict | None = None, verbose: bool = True) -> dict:
    tabs = tabs or make_tables()
    gen = Gen(seed, tabs)
    lines: list[str] = []
    refs: list[str] = []
    tid: list[int] = []
    prelude = [f"D1LOAD {sf} {wsl_path(TAB_DIR / f'rd_fw_d1_sf{sf}.bin')}" for sf in tabs]
    for k in range(n_traces):
        for cmd, ref in gen.trace():
            lines.append(cmd)
            refs.append(ref)
            tid.append(k)
    out = run_cli(prelude + lines)
    loads, got = out[: len(prelude)], out[len(prelude) :]
    assert all(x == "1" for x in loads), f"table load failed: {loads}"
    mism: list[dict] = []
    bad_traces = set()
    by_kind: dict[str, list[int]] = {}
    for line, ref, g, k in zip(lines, refs, got, tid):
        kind = line.split(" ")[0]
        c = by_kind.setdefault(kind, [0, 0])
        c[0] += 1
        if not compare(ref, g):
            c[1] += 1
            bad_traces.add(k)
            if len(mism) < 25:
                mism.append(dict(trace=k, cmd=line[:160], reference=ref, firmware=g))
    res = dict(traces=n_traces, ops=len(lines), mismatched_ops=int(sum(v[1] for v in by_kind.values())), mismatched_traces=len(bad_traces), by_command={k: dict(ops=v[0], mismatches=v[1]) for k, v in sorted(by_kind.items())}, first_mismatches=mism, seed=seed)
    if verbose:
        print(json.dumps({k: v for k, v in res.items() if k != "by_command"}, indent=1))
    return res


def run_replay(hours: int = 6) -> dict:
    """Decisions recorded from real simulator runs (D1 lookups, defers, D3 slots, the D2 decision in burst cells) replayed through the C path."""
    from crashguard import rd_dev_b as B
    from crashguard import rd_eval as E
    from crashguard import world_sim as W

    params = B.params_of({})
    cells = [c for c in E.cells_of(B.DEV_B) if (c["n"], c["p"], c["sf"], c["duty"]) in ((180, 0.35, 8, 0.01), (80, 0.55, 10, 0.01), (180, 0.55, 8, 0.002))]
    E._init(params)
    tabs = make_tables((8, 10))
    trace: list = []
    p3 = params["d3"]
    for cell in cells:
        for h in range(hours):
            cfg = E.make_cfg("D3", cell, B.DEV_B["seed"], h)
            cfg.world["rd"]["trace"] = trace
            W.simulate(cfg)
    lines, refs = [], []
    for rec in trace:
        if rec[0] == "d1":
            _k, sf0, c, j, tau, lhat, nh, bud, out = rec
            lines.append(f"D1 {sf0} {c} {j} {hx(tau)} {hx(lhat)} {nh} {hx(bud)}")
            refs.append("NONE" if out is None else f"{hx(out[0])} {out[1]}")
        elif rec[0] == "d2":
            _k, listed, gate, cdef, mx, act = rec
            lines.append(f"D2DEC {listed} {gate} {cdef} {mx}")
            refs.append(act)
        elif rec[0] == "d2defer":
            _k, cls, now, arr, ready, u, scale, du = rec
            lines.append(f"DEFER {cls} {hx(now)} {hx(arr)} {hx(ready)} {hx(u)} {hx(scale)}")
            refs.append("F:" + hx(du))
        elif rec[0] == "d3":
            _k, sf_r, n_oth, node, ready, off, a_air, dend, st = rec
            lines.append(f"D3TIME {p3['thr3']} {hx(p3['m'])} {n_oth + 1} {node} {hx(ready)} {hx(off)} {hx(a_air)} {hx(dend)}")
            refs.append("NONE" if st is None else hx(st))
    prelude = [f"D1LOAD {sf} {wsl_path(TAB_DIR / f'rd_fw_d1_sf{sf}.bin')}" for sf in tabs]
    out = run_cli(prelude + lines)[len(prelude) :]
    kinds: dict[str, list[int]] = {}
    mism = []
    for line, ref, g in zip(lines, refs, out):
        k = line.split(" ")[0]
        e = kinds.setdefault(k, [0, 0])
        e[0] += 1
        ok = compare(ref, g)
        if not ok:
            e[1] += 1
            if len(mism) < 10:
                mism.append(dict(cmd=line[:140], reference=ref, firmware=g))
    return dict(records=len(lines), by_kind={k: dict(ops=v[0], mismatches=v[1]) for k, v in kinds.items()}, mismatches=int(sum(v[1] for v in kinds.values())), first=mism)


def sizes() -> dict:
    """Object sizes of the firmware path compiled with -Os for the HOST (x86-64). Not ESP32 flash or RAM: an Xtensa or RISC-V toolchain is not installed here (NOT_RUN)."""
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", wsl_path(ROOT / "firmware_rd" / "size.sh")], capture_output=True, text=True).stdout.strip().splitlines()
    res = {}
    for name, line in zip(("cg_rd", "tweetnacl"), out):
        t, d, b = (int(x) for x in line.split()[:3])
        res[name] = dict(text=t, data=d, bss=b)
    tabs = make_tables((9,))
    res["d1_table_bytes_one_sf"] = tabs[9].size_bytes()
    res["ring_and_state_bytes"] = dict(verifier=32 + CG_SEEN * 64 + 8, beta=40, freshness_ring_R256=2 * 8 * 256 + 8)
    return res


CG_SEEN = 16


def record_all(n_traces: int = 10000) -> dict:
    from crashguard.rd_common import Rec

    build()
    diff = run_diff(n_traces, verbose=False)
    rep = run_replay()
    sz = sizes()
    (ROOT / "results" / "tables" / "rd_fw_diff.json").write_text(json.dumps(dict(diff=diff, replay=rep, sizes=sz), indent=1), encoding="utf-8")
    rec = Rec("rd.d6.", "src/crashguard/rd_firmware.py", "SIMULATED")
    rec.add("diff.traces", diff["traces"], "traces", "random vehicle histories, seed 42; firmware C (host build, gcc, WSL) against the Python reference")
    rec.add("diff.ops", diff["ops"], "ops", "commands compared (hex-float exact for numbers, byte exact for frames and tags)")
    rec.add("diff.mismatched_ops", diff["mismatched_ops"], "ops", "target 0")
    rec.add("diff.mismatched_traces", diff["mismatched_traces"], "traces", "target 0")
    rec.add("replay.records", rep["records"], "records", "D1 lookups, defers, D3 slots and D2 decisions recorded inside real simulator runs (3 DEV burst cells, 6 hours each, D3 policy) and replayed through the C path")
    rec.add("replay.mismatches", rep["mismatches"], "records", "target 0")
    rec.add("size.host.cg_rd_text_bytes", sz["cg_rd"]["text"], "bytes", "gcc -Os, x86-64 host object (cg_rd.o); NOT the ESP32 build", origin="MEASURED_SOFTWARE")
    rec.add("size.host.tweetnacl_text_bytes", sz["tweetnacl"]["text"], "bytes", "gcc -Os, x86-64 host object (tweetnacl.o, whole library; the firmware path uses only the verification part)", origin="MEASURED_SOFTWARE")
    rec.add("size.d1_table_bytes_per_sf", sz["d1_table_bytes_one_sf"], "bytes", "one byte per entry, one base spreading factor (Severe and Critical tables)", origin="ANALYTICAL")
    rec.add("esp32.flash_ram_size", "NOT_RUN", "n/a", "no Xtensa or RISC-V ESP32 toolchain is installed here", origin="NOT_RUN")
    rec.add("emulator.qemu_run", "NOT_RUN", "n/a", "Espressif QEMU and ESP-IDF not installed here", origin="NOT_RUN")
    rec.write()
    return dict(diff={k: v for k, v in diff.items() if k != "by_command"}, replay=rep, sizes=sz)


if __name__ == "__main__":
    if sys.argv[1] == "all":
        print(json.dumps(record_all(int(sys.argv[2]) if len(sys.argv) > 2 else 10000), indent=1, default=str)[:3000])
    elif sys.argv[1] == "build":
        build()
    elif sys.argv[1] == "diff":
        print(json.dumps(run_diff(int(sys.argv[2]) if len(sys.argv) > 2 else 10000, verbose=False)["mismatched_ops"]))
    elif sys.argv[1] == "replay":
        print(json.dumps(run_replay(), indent=1))
