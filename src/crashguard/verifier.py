"""Reference base-station verifier (counter persistence, idempotent re-ACK, flood limit) and the node-side ACK check.

Found by our own testing (docs/07_log/DECISIONS.md): with strict anti-replay, a car whose ACK was lost retries the same
packet and the base rejects it as a replay, so the car never gets its ACK. Fix: the base remembers the last
``RECENT_N`` accepted (node_id, event_id, counter) entries with their ACK. An alert that matches one of them exactly
(and has a valid tag) gets the identical ACK again, without being processed a second time.

Side effect of that fix: replayed packets make the base transmit. Mitigation (optional arguments, off by default so the
old behaviour can still be tested): at most one ACK per (node_id, event_id) per ``reack_interval_s`` (the car's retry
interval), and every ACK is paid for from the base station's duty-cycle budget (``DutyBudget``).
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from crashguard import packet as P
from crashguard.lora import DUTY, airtime_ms

ACCEPT = "accept"  # new alert, processed, ACK sent
ACCEPT_NO_ACK = "accept_no_ack"  # new alert, processed, but the base had no duty-cycle budget left for the ACK
REACK = "reack"  # exact repeat of a recent accepted alert: same ACK again, alert NOT processed again
REACK_LIMITED = "reack_limited"  # exact repeat inside the retry interval: no ACK sent
REACK_NO_BUDGET = "reack_no_budget"  # exact repeat, but no duty-cycle budget left: no ACK sent
REJECT_LENGTH, REJECT_VERSION, REJECT_TYPE = "reject_length", "reject_version", "reject_type"
REJECT_TAG, REJECT_COUNTER = "reject_tag", "reject_counter"
RECENT_N = 16  # last accepted alerts kept for re-ACK. Design choice; firmware flash/RAM budget decides the real value


class DutyBudget:
    """Token bucket in seconds of airtime: refills at the duty-cycle rate, capped at ``capacity_s``."""

    def __init__(self, duty: float = DUTY, capacity_s: float = 360.0, initial_s: float | None = None):
        self.duty, self.capacity_s = duty, capacity_s
        self.tokens = capacity_s if initial_s is None else initial_s
        self.t = 0.0
        self.spent_s = 0.0

    def try_spend(self, now: float, seconds: float) -> bool:
        self.tokens = min(self.capacity_s, self.tokens + self.duty * max(0.0, now - self.t))
        self.t = max(self.t, now)
        if self.tokens < seconds:
            return False
        self.tokens -= seconds
        self.spent_s += seconds
        return True


class BaseVerifier:
    """Accept an alert only if length, version, type, tag and counter (> last seen for that node) are right.

    The counter is updated only after the tag has been checked, so forged packets cannot advance it.
    ``store`` is a JSON file standing in for flash; ``None`` keeps everything in RAM only.
    ``idempotent=False`` gives the strict behaviour (every repeat is a replay) for comparison.
    ``reack_interval_s`` and ``budget`` switch on the flood mitigation; ``sf`` sets the ACK airtime.
    """

    def __init__(self, key: bytes, store: Path | None = None, idempotent: bool = True, recent_n: int = RECENT_N,
                 reack_interval_s: float | None = None, budget: DutyBudget | None = None, sf: int = 7):
        self.key, self.store, self.idempotent, self.recent_n = key, store, idempotent, recent_n
        self.reack_interval_s, self.budget = reack_interval_s, budget
        self.ack_airtime_s = airtime_ms(P.ACK_LEN, sf) / 1000.0
        self.last: dict[int, int] = {}
        self.base_counter = 0
        self.recent: OrderedDict[tuple[int, int, int], bytes] = OrderedDict()
        self.last_ack_at: dict[tuple[int, int], float] = {}  # (node_id, event_id) -> time of the last ACK sent
        self.acks_sent = 0
        self.ack_airtime_total_s = 0.0
        if store is not None and store.exists():
            data = json.loads(store.read_text())
            self.last = {int(k): v for k, v in data["last"].items()}
            self.base_counter = data["base_counter"]
            self.recent = OrderedDict((tuple(k), bytes.fromhex(v)) for k, v in data.get("recent", []))
            while len(self.recent) > self.recent_n:
                self.recent.popitem(last=False)

    def _save(self) -> None:
        if self.store is not None:
            self.store.write_text(json.dumps({"last": self.last, "base_counter": self.base_counter,
                                              "recent": [[list(k), v.hex()] for k, v in self.recent.items()]}))

    def _transmit_ack(self, node: int, event: int, now: float) -> bool:
        """Pay for one ACK from the duty-cycle budget (if any). Returns False when the budget is empty."""
        if self.budget is not None and not self.budget.try_spend(now, self.ack_airtime_s):
            return False
        self.acks_sent += 1
        self.ack_airtime_total_s += self.ack_airtime_s
        self.last_ack_at[(node, event)] = now
        return True

    def handle(self, raw: bytes, now: float = 0.0) -> tuple[str, bytes | None]:
        """Returns (decision, ACK bytes or None). ``now`` is the arrival time in seconds."""
        if len(raw) != P.ALERT_LEN:
            return REJECT_LENGTH, None
        if raw[0] != P.VERSION:
            return REJECT_VERSION, None
        if raw[1] != P.MSG_ALERT:
            return REJECT_TYPE, None
        if not P.tag_ok(raw, self.key, P.ALERT_BODY_LEN):
            return REJECT_TAG, None
        a = P.decode_alert(raw)
        key = (a.node_id, a.event_id, a.counter)
        if self.idempotent and key in self.recent:
            last = self.last_ack_at.get((a.node_id, a.event_id))
            if self.reack_interval_s is not None and last is not None and now - last < self.reack_interval_s:
                return REACK_LIMITED, None
            if not self._transmit_ack(a.node_id, a.event_id, now):
                return REACK_NO_BUDGET, None
            return REACK, self.recent[key]
        if a.counter <= self.last.get(a.node_id, -1):
            return REJECT_COUNTER, None
        self.last[a.node_id] = a.counter
        self.base_counter += 1
        ack = P.encode_ack(P.Ack(a.node_id, a.event_id, a.counter, self.base_counter), self.key)
        self.recent[key] = ack
        while len(self.recent) > self.recent_n:
            self.recent.popitem(last=False)
        self._save()
        if not self._transmit_ack(a.node_id, a.event_id, now):
            return ACCEPT_NO_ACK, None
        return ACCEPT, ack

    def reboot(self, counter_persisted: bool) -> BaseVerifier:
        """A new verifier as after a power cycle. With ``counter_persisted=False`` the flash copy is lost."""
        return BaseVerifier(self.key, self.store if counter_persisted else None, self.idempotent, self.recent_n,
                            self.reack_interval_s, None if self.budget is None else DutyBudget(self.budget.duty, self.budget.capacity_s))


def node_accepts_ack(raw: bytes, key: bytes, node_id: int, event_id: int, counter: int) -> bool:
    """Node side: the ACK must be signed and refer to the alert that is waiting for it."""
    if len(raw) != P.ACK_LEN or raw[0] != P.VERSION or raw[1] != P.MSG_ACK:
        return False
    if not P.tag_ok(raw, key, P.ACK_BODY_LEN):
        return False
    a = P.decode_ack(raw)
    return a.node_id == node_id and a.acked_event_id == event_id and a.acked_counter == counter
