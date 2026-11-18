"""A1: attempt-maximising short provisional alert (docs/02_preregistration/PREREGISTRATION_V15.md section 2).

    python -m crashguard.a4_a1 dev [iteration]   # development run on the LoED DEVELOPMENT devices (a logged iteration, at most five)
    python -m crashguard.a4_a1 held              # held-out run on the fresh sniffer links (once, after the freeze)
    python -m crashguard.a4_a1 analyse           # H-A1b and the trace cells of H-A1c, keys ``a4.a1.trace.*``

Contents: (1) the 24-byte provisional frame and its ACK check; (2) the provisional repetition rule as pure functions (so that the properties can be tested); (3) a trace engine in two
modes: the round-3 compatibility mode (stages on independent timelines, 4 tries, no deadline) which reproduces ``r3_t1.r3_event`` exactly, and the A1 mode (one radio, interleaved,
repetition until a verified ACK, the 10 s deadline or the duty limit). Link model: attempt k of the node sees frame s + k of the link (V14 rule); the ACK of a received frame reaches the
car with probability 1 - p_dl, p_dl being the link's own loss rate (V14 rule).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import pickle
import random
import struct
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from crashguard import packet as P
from crashguard import r3_t1 as T1
from crashguard.ar_r4 import kdf
from crashguard.lora import airtime_ms

ROOT = Path(__file__).resolve().parents[2]
PROV_LEN = 24
MSG_PROV = 4
TAG_LEN = 8
_PROV_FMT = "<BBIBhhIB"  # version, msg_type, node_id, flags, lat, lon, epoch, seq: 16 bytes, then the 8-byte tag
DEADLINE = 10.0
LIMIT_S = 0.01 * 3600.0
COMPUTE3 = T1.COMPUTE3
FINAL_S = T1.FINAL_S
TRIES3 = T1.TRIES3
CANCEL_TX = T1.CANCEL_TX
CANCEL_GAP = 0.3  # spacing of the three CANCEL frames (xsim_alert.cc R3_CANCEL_GAP)
PROC, MARGIN = T1.PROC, T1.MARGIN


# ------------------------------------------------------------------------------------------------ (1) frame
def coarse(deg: float) -> int:
    """Coarse position: units of 1/64 degree (about 1.7 km), clipped to i16."""
    return max(-32768, min(32767, int(round(deg * 64.0))))


def prov_tag(key: bytes, body16: bytes) -> bytes:
    return hmac.new(key, b"P" + body16, hashlib.sha256).digest()[:TAG_LEN]


def encode_prov(key: bytes, node_id: int, lat_deg: float, lon_deg: float, epoch: int, seq: int, flags: int = 0b001, version: int = P.VERSION) -> bytes:
    body = struct.pack(_PROV_FMT, version, MSG_PROV, node_id, flags, coarse(lat_deg), coarse(lon_deg), epoch & 0xFFFFFFFF, seq & 0xFF)
    raw = body + prov_tag(key, body)
    assert len(raw) == PROV_LEN
    return raw


def decode_prov(raw: bytes) -> dict:
    if len(raw) != PROV_LEN:
        raise ValueError(f"provisional frame must be {PROV_LEN} bytes, got {len(raw)}")
    v, t, node, fl, la, lo, ep, sq = struct.unpack_from(_PROV_FMT, raw)
    return dict(version=v, msg_type=t, node_id=node, flags=fl, lat=la, lon=lo, epoch=ep, seq=sq)


def verify_prov(raw: bytes, key: bytes) -> bool:
    """Base side: a provisional frame is valid only with its own type, length and per-vehicle tag over the domain-separated body."""
    if len(raw) != PROV_LEN or raw[1] != MSG_PROV:
        return False
    return hmac.compare_digest(raw[16:], prov_tag(key, raw[:16]))


def ack_for(master: bytes, raw_prov: bytes, base_counter: int = 1) -> bytes:
    """Base side: the existing 26-byte ACK naming the vehicle; the acknowledged id (epoch, seq) goes in the event-id and counter fields; the key is the per-vehicle key."""
    f = decode_prov(raw_prov)
    return P.encode_ack(P.Ack(node_id=f["node_id"], acked_event_id=f["epoch"], acked_counter=f["seq"], base_counter=base_counter), kdf(master, f["node_id"]))


def ack_stops(raw_ack: bytes, key: bytes, node_id: int, sent_ids: set[tuple[int, int]]) -> bool:
    """Car side: an ACK stops the repetition only if it is a well-formed ACK of this vehicle, carries a valid per-vehicle tag and names an id the car has sent (provisional or confirm)."""
    if len(raw_ack) != P.ACK_LEN or raw_ack[1] != P.MSG_ACK:
        return False
    if not P.tag_ok(raw_ack, key, P.ACK_LEN - P.TAG_LEN):
        return False
    a = P.decode_ack(raw_ack)
    return a.node_id == node_id and (a.acked_event_id, a.acked_counter) in sent_ids


class ProvSession:
    """Car side of one provisional alert with real frames: the repetition stops only on an ACK that passes ``ack_stops`` (per-vehicle tag, this vehicle, an id the car has sent)."""

    def __init__(self, master: bytes, node_id: int, lat: float, lon: float, epoch: int, seq: int):
        self.key = kdf(master, node_id)
        self.node_id = node_id
        self.frame = encode_prov(self.key, node_id, lat, lon, epoch, seq)
        self.sent_ids = {(epoch & 0xFFFFFFFF, seq & 0xFF)}
        self.stopped = False

    def on_ack(self, raw_ack: bytes) -> bool:
        if ack_stops(raw_ack, self.key, self.node_id, self.sent_ids):
            self.stopped = True
        return self.stopped


# ------------------------------------------------------------------------------------------------ (2) repetition rule
def prov_allowed(t_start: float, a_prov: float, a_alert: float, used: float, t_deadline: float = DEADLINE, limit_s: float = LIMIT_S, reserve_tries: int = 4) -> str:
    """'ok', or the reason to stop: 'deadline' (the frame would end after the deadline) or 'duty' (the sliding-hour airtime plus this frame plus the reserve for the confirm would exceed the limit)."""
    if t_start + a_prov > t_deadline + 1e-12:
        return "deadline"
    if used + a_prov + reserve_tries * a_alert > limit_s + 1e-12:
        return "duty"
    return "ok"


@dataclass(frozen=True)
class Cfg:
    sf: int = 7
    prov_len: int = PROV_LEN
    gap: float = 0.0            # development item 1: gap between two provisional attempts (s)
    reserve: int = 4            # development item 2: confirm reserve, in 97-byte airtimes
    after_confirm: bool = True  # development item 3: provisional repeats continue after the confirm used its tries
    cap: int | None = None      # None = no cap (A1); 4 = the round-3 flash
    exclusive: bool = True      # one radio, interleaved (A1); False = the round-3 trace model (stage timelines are independent)
    limit_s: float = LIMIT_S
    deadline: float = DEADLINE


A1 = Cfg()
R3 = Cfg(prov_len=14, cap=4, exclusive=False, deadline=math.inf)  # the round-3 compatibility mode


class Inv:
    late = 0
    duty = 0
    overrun = 0
    ack_free_stop = 0

    @classmethod
    def reset(cls):
        cls.late = cls.duty = cls.overrun = cls.ack_free_stop = 0


# ------------------------------------------------------------------------------------------------ (3) engine
def _air(n: int, sf: int) -> float:
    return airtime_ms(n, sf) / 1000.0


def a1_event(r: np.ndarray, s: int, ev: tuple, p_dl: float, rng: random.Random, cfg: Cfg = A1, used0: float = 0.0, log: list | None = None) -> dict:
    """One event on one link. ev = (E, F, y, t_early_s). Returns per-event quantities for the group statistics.

    items: 'prov' (24-byte frame, repeated), 'conf' (97-byte alert, at most 4 tries), 'cancel' (three 14-byte frames, unconfirmed).
    """
    E, F, y, te = ev
    sf = cfg.sf
    a_prov, a_al, a_ack, a_cn = _air(cfg.prov_len, sf), _air(P.ALERT_LEN, sf), _air(P.ACK_LEN, sf), _air(14, sf)
    win = PROC + a_ack + MARGIN
    st = dict(idx=s, used=used0, air=0.0, prov_arr=math.inf, prov_tx=0, conf_arr=math.inf, conf_tx=0, cancel_rx=0, cancel_tx=0, prov_stop=None, conf_acked=False, prov_acked=False)
    # state of the items
    prov = dict(on=bool(E), ready=te + COMPUTE3, tries=0)
    conf = dict(on=bool(F), ready=FINAL_S + COMPUTE3, tries=0)
    canc = dict(on=bool(E and not F), n=0)

    def stop_prov(why):
        if prov["on"]:
            prov["on"] = False
            st["prov_stop"] = why

    def run(items: tuple, t_free: float) -> float:
        while True:
            cands = []
            if "conf" in items and conf["on"] and not st["conf_acked"] and conf["tries"] < TRIES3:
                cands.append((max(t_free, conf["ready"]), 0, "conf"))
            if "cancel" in items and canc["on"] and canc["n"] < CANCEL_TX:
                cands.append((max(t_free, FINAL_S + CANCEL_GAP * canc["n"]), 0, "cancel"))
            if "prov" in items and prov["on"]:
                cands.append((max(t_free, prov["ready"]), 1, "prov"))
            if not cands:
                return t_free
            t0, _pri, kind = min(cands)
            if st["idx"] >= len(r):
                Inv.overrun += 1
                return t_free
            if kind == "prov":
                if cfg.exclusive and canc["on"] and t0 >= FINAL_S:  # retraction decided: the provisional alert is withdrawn
                    stop_prov("retracted")
                    continue
                if cfg.cap is not None and prov["tries"] >= cfg.cap:
                    stop_prov("cap")
                    continue
                if st["conf_acked"]:
                    stop_prov("confirm_acked")
                    continue
                if (not cfg.after_confirm) and conf["on"] and conf["tries"] >= TRIES3:
                    stop_prov("confirm_done")
                    continue
                why = prov_allowed(t0, a_prov, a_al, st["used"], cfg.deadline, cfg.limit_s, cfg.reserve) if math.isfinite(cfg.deadline) else "ok"
                if why != "ok":
                    stop_prov(why)
                    continue
                a = a_prov
            elif kind == "conf":
                a = a_al
            else:
                a = a_cn
            if st["used"] + a > cfg.limit_s + 1e-12:
                Inv.duty += 1
                if kind == "prov":
                    stop_prov("duty")
                else:
                    (conf if kind == "conf" else canc)["on"] = False
                continue
            end = t0 + a
            st["used"] += a
            st["air"] += a
            got = bool(r[st["idx"]])
            st["idx"] += 1
            if log is not None:
                log.append((kind, t0, a, got))
            acked = False
            if kind == "prov":
                prov["tries"] += 1
                st["prov_tx"] += 1
                if end > DEADLINE + 1e-9 and math.isfinite(cfg.deadline):
                    Inv.late += 1
                if got and st["prov_arr"] == math.inf and end <= DEADLINE + 1e-9:
                    st["prov_arr"] = end
                if got and rng.random() >= p_dl:
                    acked = True
                    st["prov_acked"] = True
                    stop_prov("ack")
                t_free = end + win + cfg.gap
            elif kind == "conf":
                conf["tries"] += 1
                st["conf_tx"] += 1
                if got and st["conf_arr"] == math.inf and end <= DEADLINE + 1e-9:
                    st["conf_arr"] = end
                if got and rng.random() >= p_dl:
                    acked = True
                    st["conf_acked"] = True
                    conf["on"] = False
                    if cfg.exclusive:
                        stop_prov("confirm_acked")
                t_free = end + win
            else:
                canc["n"] += 1
                st["cancel_tx"] += 1
                if got:
                    st["cancel_rx"] += 1
                t_free = end  # unconfirmed: no listen window
            del acked

    if cfg.exclusive:
        run(("prov", "conf", "cancel"), 0.0)
    else:  # round-3 trace model: the stages are separate timelines; frames are consumed in the order flash, then confirm or cancel
        run(("prov",), 0.0)
        run(("conf", "cancel"), 0.0)
    out = dict(n_cr=int(y == 1), two_air=st["air"], prov_arr=st["prov_arr"], conf_arr=st["conf_arr"], prov_tx=st["prov_tx"], conf_tx=st["conf_tx"], cancel_tx=st["cancel_tx"],
               prov_stop=st["prov_stop"], is_E=bool(E), used=st["used"])
    arrived = math.isfinite(st["prov_arr"]) or math.isfinite(st["conf_arr"])
    if E and not F:
        out["two_d"] = int(y == 1 and math.isfinite(st["prov_arr"]) and st["cancel_rx"] == 0)
    else:
        out["two_d"] = int(y == 1 and arrived)
    out["diff"] = None
    return out


# ------------------------------------------------------------------------------------------------ run over links
def link_task(args: tuple) -> dict:
    """One link: 300 start points (V14 rule), R3 (round-3 compatibility mode) and A1 on the same start points, events and ACK draws. Single-stage values come from ``r3_t1.r3_event``."""
    dev, segs, p_loss, n_start, events, cfg_a1, cfgs = args
    Inv.reset()
    rng0 = T1.seeded("t1s", dev, T1.SEED)
    adm = T1.admissible(segs)
    picks = [adm[rng0.randrange(len(adm))] for _ in range(n_start)]
    acc = {k: dict(n_E=0, prov_ok=0, n_cr=0, two_d=0, two_air=0.0, prov_tx=0, single_d=0, single_air=0.0) for k in ("R3", "A1") + tuple(cfgs)}
    for q, (si, pos) in enumerate(picks):
        r = segs[si][0]
        rng = T1.seeded("t1e", dev, q)
        ev = events[rng.randrange(len(events))]
        o3 = T1.r3_event(r, pos, ev, p_loss, T1.seeded("t1e2", dev, q))  # round-3 single-stage and two-stage numbers (frozen code)
        for name, cfg in (("R3", R3), ("A1", cfg_a1)) + tuple(cfgs.items()):
            o = a1_event(r, pos, ev, p_loss, T1.seeded("a4", dev, q, name), cfg)
            a = acc[name]
            a["n_cr"] += o["n_cr"]
            a["two_d"] += o["two_d"]
            a["two_air"] += o["two_air"]
            a["prov_tx"] += o["prov_tx"]
            if o["is_E"]:
                a["n_E"] += 1
                a["prov_ok"] += int(math.isfinite(o["prov_arr"]) and o["prov_arr"] <= DEADLINE + 1e-9)
            a["single_d"] += o3["single_d"]
            a["single_air"] += o3["single_air"]
    return dict(dev=dev, p=p_loss, n=len(picks), acc=acc, inv=dict(late=Inv.late, duty=Inv.duty, overrun=Inv.overrun))


def load_events() -> list[tuple]:
    return T1.load_events()


def run(links: dict, sel: list[str], n_start: int, out: Path, cfg_a1: Cfg, extra: dict | None = None, workers: int = 14) -> dict:
    events = load_events()
    tasks = [(d, links[d]["segs"], links[d]["p"], n_start, events, cfg_a1, extra or {}) for d in sel]
    with ProcessPoolExecutor(workers) as ex:
        res = list(ex.map(link_task, tasks, chunksize=8))
    inv = {k: sum(x["inv"][k] for x in res) for k in ("late", "duty", "overrun")}
    pickle.dump(dict(res=res, inv=inv, n_start=n_start, cfg=cfg_a1), out.open("wb"))
    print("links", len(res), "invariants", inv, flush=True)
    return dict(res=res, inv=inv)


def frozen_cfg() -> Cfg:
    f = ROOT / "results" / "tables" / "a4_frozen.json"
    if not f.exists():
        raise SystemExit("not frozen: results/tables/a4_frozen.json is missing")
    p = json.loads(f.read_text(encoding="utf-8"))["a1"]
    return Cfg(gap=p["gap"], reserve=p["reserve"], after_confirm=p["after_confirm"])


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dev":
        from crashguard.a4_dev import dev_a1

        dev_a1(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    elif cmd in ("held", "analyse"):
        from crashguard.a4_analyse import held_a1

        held_a1(cmd)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()


__all__ = ["A1", "R3", "Cfg", "a1_event", "encode_prov", "decode_prov", "verify_prov", "ack_for", "ack_stops", "prov_allowed", "replace"]
