"""T11: additional designed test cases for the alert, flash, CANCEL and ACK rules (SIMULATED). Written to probe edges that the original 48 cases were not built around: counter wrap of the 16-bit flash counter,
a bounded brute force of the 8-byte tag, ACKs that arrive late, duplicate and early CANCEL, a short-id collision and message-type confusion. These are DESIGNED TEST CASES, not independent attackers.
The expected outcome of every case is written here BEFORE the run; where the expected outcome documents a known weakness (CANCEL before its alert; short-id collision) the case is expected to show it.
The pass count of the new cases is reported separately from the 48 original cases.
"""
from __future__ import annotations

import random

import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard import sct_protocol as T
from crashguard import verifier as V
from crashguard.attacks import KEY, NODE

SRC = "results/tables/attacks_extra.csv"
BRUTE_TRIES = 200_000


def _alert(counter: int, event: int = 1, node: int = NODE) -> bytes:
    return P.encode_alert(P.Alert(node_id=node, event_id=event, counter=counter, timestamp_ms=1, severity=3), KEY)


def _short(counter: int, kind: int = T.MSG_FLASH, node: int = NODE, sev: int = 3) -> bytes:
    return T.encode_short(T.Short(node, counter, sev, 0, kind), KEY)


def run_cases() -> list[dict]:
    rows: list[dict] = []

    def case(cid: str, name: str, category: str, expected: str, observed: str, note: str = "") -> None:
        rows.append(dict(id=cid, case=name, category=category, expected=expected, observed=observed, match=expected == observed, note=note))

    # X01 flash counter wrap: the 16-bit counter wraps while the 32-bit counter keeps rising
    b = T.SctBase(KEY)
    b.last_flash[NODE & 0xFFFF] = 65535
    case("X01", "Flash with the 16-bit counter wrapped to 0 after counter 65535", "counter rollover", T.ACCEPT_FLASH, b.handle_short(_short(65536))[0], "reconstructed as 65536, above the last accepted flash")
    # X02 replay of an old flash whose 16-bit counter value is reused after 65,536 events
    b = T.SctBase(KEY)
    b.last_flash[NODE & 0xFFFF] = 70000
    case("X02", "Replay of an old flash (true counter 5) after the counter passed 65,536", "counter rollover", T.REJECT_COUNTER, b.handle_short(_short(5))[0], "reconstructed value is not above the last accepted flash")
    # X03 bounded brute force of the 8-byte tag on an alert (200,000 random tags)
    rng = random.Random(C.SEED)
    body = _alert(7)[: P.ALERT_BODY_LEN]
    base = V.BaseVerifier(KEY)
    accepted = sum(1 for _ in range(BRUTE_TRIES) if base.handle(body + rng.randbytes(8))[0] == V.ACCEPT)
    case("X03", f"Random 8-byte tags on a valid alert body ({BRUTE_TRIES:,} tries, bounded budget)", "tag forgery", "0 accepted", f"{accepted} accepted", f"success probability per try 2^-64 (ANALYTICAL); expected successes about {BRUTE_TRIES / 2.0 ** 64:.1e}")
    # X04 ACKs that arrive late
    ack = P.encode_ack(P.Ack(NODE, 1, 10, 1), KEY)
    case("X04a", "Valid ACK arrives late, after the car retried, while it still waits for that alert", "delayed delivery", "accept", "accept" if V.node_accepts_ack(ack, KEY, NODE, 1, 10) else "reject")
    case("X04b", "Valid ACK of alert 1 arrives after the car moved on to alert 2", "delayed delivery", "reject", "accept" if V.node_accepts_ack(ack, KEY, NODE, 2, 11) else "reject")
    # X05 duplicate CANCEL
    b = T.SctBase(KEY)
    b.handle_short(_short(30))
    r1, r2 = b.handle_short(_short(30, T.MSG_CANCEL))[0], b.handle_short(_short(30, T.MSG_CANCEL))[0]
    case("X05", "The same CANCEL delivered twice", "CANCEL", "cancelled,cancelled", f"{r1},{r2}", "idempotent: the second copy changes nothing")
    # X06 CANCEL arrives before its alert (reordering): KNOWN WEAKNESS, expected to show it
    b = T.SctBase(KEY)
    d1 = b.handle_short(_short(40, T.MSG_CANCEL))[0]
    b.handle_alert(_alert(40))
    cancelled = (NODE & 0xFFFF, 40) in b.cancelled
    case("X06", "CANCEL arrives before the alert it cancels", "CANCEL", f"{T.REJECT_UNKNOWN}; event not cancelled", f"{d1}; event {'cancelled' if cancelled else 'not cancelled'}", "KNOWN WEAKNESS documented by the model check: the early CANCEL is refused and the late alert stays active")
    # X07 short-id collision between two nodes (different node ids, same low 16 bits)
    b = T.SctBase(KEY)
    b.handle_short(_short(50, node=0x0001C0FF))
    d = b.handle_short(_short(10, node=0x0002C0FF))[0]
    case("X07", "Flash of a second node whose short id equals the first node's (counter 10 against 50)", "identity", T.REJECT_COUNTER, d, "KNOWN LIMIT: the 16-bit short id must be unique in the fleet; a collision refuses the second node")
    # X08 message-type confusion between flash and alert
    b = T.SctBase(KEY)
    d_a = b.handle_alert(_short(60))[0]
    d_s = b.handle_short(_alert(60))[0]
    case("X08", "A 14-byte flash given to the alert handler and a 97-byte alert given to the flash handler", "type confusion", f"{T.REJECT_LENGTH},{T.REJECT_LENGTH}", f"{d_a},{d_s}")
    # X09 the ACK of a flash presented to a node that waits for its alert
    flash_ack = P.encode_ack(P.Ack(NODE, T.FLASH_EVENT_ID, 70, 1), KEY)
    case("X09", "A valid ACK of the flash (event id 0xFFFFFFFF) presented to a node waiting for the alert of event 1", "ACK", "reject", "accept" if V.node_accepts_ack(flash_ack, KEY, NODE, 1, 70) else "reject")
    return rows


def main() -> None:
    from crashguard.results import record_many

    rows = run_cases()
    df = pd.DataFrame(rows)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.TABLES / "attacks_extra.csv", index=False)
    ent = [dict(name="attacks_x.cases_total", value=len(df), unit="cases", origin="SIMULATED", source_file=SRC, notes="additional DESIGNED TEST CASES (not independent attackers); the 48 original cases are counted separately in attacks.cases_total"),
           dict(name="attacks_x.cases_matching_expected", value=int(df.match.sum()), unit="cases", origin="SIMULATED", source_file=SRC, notes="expected outcomes were written before the run; known weaknesses are expected to show")]
    for r in df.itertuples():
        ent.append(dict(name=f"attacks_x.{r.id}.observed", value=r.observed, unit="outcome", origin="SIMULATED", source_file=SRC, notes=f"{r.case}; expected {r.expected}"))
    ent.append(dict(name="attacks_x.brute_force.tries", value=BRUTE_TRIES, unit="tags", origin="SIMULATED", source_file=SRC, notes="random 8-byte tags tried against the reference verifier"))
    ent.append(dict(name="attacks_x.brute_force.expected_successes", value=BRUTE_TRIES / 2.0 ** 64, unit="count", origin="ANALYTICAL", source_file=SRC, notes="tries x 2^-64, assuming HMAC-SHA256 is a secure PRF"))
    record_many(ent, purge_prefixes=("attacks_x.",))
    print(df[["id", "category", "expected", "observed", "match"]].to_string())


if __name__ == "__main__":
    main()
