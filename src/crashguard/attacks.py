"""Attack suite for the alert / ACK design (S7). Simulated in software, not a measurement on the radios."""
from __future__ import annotations

import random
import tempfile
from pathlib import Path

import pandas as pd

from crashguard import config as C
from crashguard import packet as P
from crashguard import verifier as V
from crashguard.results import record_many

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f")  # test key only
OTHER_KEY = bytes(range(32, 64))
NODE = 0xC0FFEE


def _alert(counter: int, event_id: int = 1, **kw) -> P.Alert:
    return P.Alert(node_id=NODE, event_id=event_id, counter=counter, timestamp_ms=123456, severity=2, impact_side=0,
                   peak_g_x100=480, ml_prob_x10000=9100, lat_e7=129000000, lon_e7=800000000, **kw)


def _fresh(d: Path) -> V.BaseVerifier:
    store = d / "counters.json"
    if store.exists():
        store.unlink()
    return V.BaseVerifier(KEY, store)


FLOOD_SF = 7
FLOOD_RATE_PER_S = 20  # replayed packets per second (scenario constant)
FLOOD_S = 120  # flood duration in seconds
BASE_BUDGET_INITIAL_S = 30.0  # airtime budget the base has left when the flood starts (rest used by other traffic)
LEGIT_AT_S = 100  # a genuine alert arrives this many seconds into the flood


def flood(limit: bool) -> dict:
    """Replay one captured alert FLOOD_RATE_PER_S times a second for FLOOD_S seconds and measure the base station's ACK airtime."""
    from crashguard.delivery_sim import retry_interval_s

    interval = retry_interval_s(FLOOD_SF)
    v = V.BaseVerifier(KEY, reack_interval_s=interval if limit else None, budget=V.DutyBudget(initial_s=BASE_BUDGET_INITIAL_S), sf=FLOOD_SF)
    raw = P.encode_alert(_alert(10), KEY)
    v.handle(raw, 0.0)  # the genuine alert; the attacker recorded it
    legit = P.encode_alert(_alert(50, event_id=7), KEY)
    n, legit_dec, counts = FLOOD_RATE_PER_S * FLOOD_S, None, {}
    for i in range(1, n + 1):
        t = i / FLOOD_RATE_PER_S
        if legit_dec is None and t >= LEGIT_AT_S:
            legit_dec = v.handle(legit, t)[0]
        d = v.handle(raw, t)[0]
        counts[d] = counts.get(d, 0) + 1
    reacks = counts.get(V.REACK, 0)
    return dict(replayed=n, reacks=reacks, reack_airtime_s=reacks * v.ack_airtime_s, no_budget=counts.get(V.REACK_NO_BUDGET, 0),
                limited=counts.get(V.REACK_LIMITED, 0), legit=legit_dec, budget_left_s=v.budget.tokens, interval_s=interval)


def run_cases() -> list[dict]:
    """Each case returns expected and observed outcome strings."""
    rng = random.Random(C.SEED)
    out: list[dict] = []

    def case(name: str, expected: str, observed: str, note: str = "") -> None:
        out.append(dict(case=name, expected=expected, observed=observed, match=expected == observed, note=note))

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        raw = P.encode_alert(_alert(10), KEY)
        case("packet length", "97", str(len(raw)))
        case("ACK length", "26", str(len(P.encode_ack(P.Ack(NODE, 1, 10, 1), KEY))))

        v = _fresh(d)
        dec, ack = v.handle(raw)
        case("Valid alert", V.ACCEPT, dec)
        case("Valid alert gets a valid ACK", "True", str(ack is not None and V.node_accepts_ack(ack, KEY, NODE, 1, 10)))

        v = _fresh(d)
        forged = raw[:-8] + bytes(rng.randrange(256) for _ in range(8))
        case("Forged tag", V.REJECT_TAG, v.handle(forged)[0])
        case("Alert signed with the wrong key", V.REJECT_TAG, v.handle(P.encode_alert(_alert(11), OTHER_KEY))[0])

        v = _fresh(d)
        t = bytearray(raw)
        t[18] = 0  # severity set to 'low' after signing
        case("Tampered field (severity)", V.REJECT_TAG, v.handle(bytes(t))[0])
        t = bytearray(raw)
        t[10] ^= 0x01  # counter changed
        case("Tampered field (counter)", V.REJECT_TAG, v.handle(bytes(t))[0])
        sev = P.encode_alert(_alert(12, 6, delta_v_kmh_x100=5200, asi_x100=145), KEY)
        for off, nm in ((38, "delta-V"), (40, "ASI")):
            t = bytearray(sev)
            t[off] ^= 0x10  # severity measure changed after signing
            case(f"Tampered field ({nm}, bytes {off}-{off + 1})", V.REJECT_TAG, v.handle(bytes(t))[0])
        case("Delta-V and ASI fields round-trip in the 97-byte alert", "True", str(len(sev) == 97 and P.decode_alert(sev).delta_v_kmh_x100 == 5200 and P.decode_alert(sev).asi_x100 == 145))

        # Replay, retry and old counters. "reack" = identical ACK sent again, alert not processed again.
        v = _fresh(d)
        _, ack1 = v.handle(raw)
        counter_before = v.base_counter
        dec, ack2 = v.handle(raw)
        case("Replay (same packet again): not processed again, same ACK re-sent", V.REACK, dec,
             "an attacker only gets back the ACK that was already sent; no new alert, no state change")
        case("Replay leaves the base state unchanged", "True", str(v.base_counter == counter_before and ack2 == ack1))

        v = V.BaseVerifier(KEY, d / "strict.json", idempotent=False)
        v.handle(raw)
        case("Strict verifier (before the fix): ACK lost, car retries the same packet", V.REJECT_COUNTER, v.handle(raw)[0],
             "FOUND BY OUR TESTING: the car never gets its ACK; this is why the idempotent re-ACK was added")

        v = _fresh(d)
        _, ack1 = v.handle(raw)  # the ACK is lost on the way back
        dec, ack2 = v.handle(raw)  # the car retries the same packet
        case("ACK lost, car retries same packet: re-ACKed", V.REACK, dec)
        case("The re-ACK is accepted by the car", "True", str(ack2 is not None and V.node_accepts_ack(ack2, KEY, NODE, 1, 10)))

        v = _fresh(d)
        v.handle(P.encode_alert(_alert(20, 2), KEY))
        case("Old counter, different content: rejected", V.REJECT_COUNTER, v.handle(P.encode_alert(_alert(5, 3), KEY))[0])
        case("Same counter, different content (event changed): rejected", V.REJECT_COUNTER, v.handle(P.encode_alert(_alert(20, 9), KEY))[0])

        v = _fresh(d)
        v.handle(raw)
        for k in range(V.RECENT_N):
            v.handle(P.encode_alert(_alert(11 + k, 100 + k), KEY))
        case("Replay of an alert older than the re-ACK window: rejected", V.REJECT_COUNTER, v.handle(raw)[0])

        v = _fresh(d)
        v.handle(raw)
        retry = P.encode_alert(_alert(11, event_id=1), KEY)
        case("Retry of the same event with a fresh counter", V.ACCEPT, v.handle(retry)[0])

        v = _fresh(d)
        case("Forged alert does not advance the counter", "True", str(v.handle(forged)[0] == V.REJECT_TAG and v.handle(raw)[0] == V.ACCEPT))
        case("Wrong length (truncated)", V.REJECT_LENGTH, v.handle(raw[:-1])[0])
        case("Wrong message type (alert with type 2)", V.REJECT_TYPE, v.handle(P.encode_alert(_alert(30, 4, msg_type=P.MSG_ACK), KEY))[0])
        case("Wrong version", V.REJECT_VERSION, v.handle(P.encode_alert(_alert(31, 5, version=9), KEY))[0])
        legit_ack = P.encode_ack(P.Ack(NODE, 1, 10, 1), KEY)
        case("Valid ACK fed to the base as an alert (reflection)", V.REJECT_LENGTH, v.handle(legit_ack)[0])

        # ACK attacks, seen from the node waiting for event 1 / counter 10
        spoof = P.encode_ack(P.Ack(NODE, 1, 10, 1), OTHER_KEY)
        case("Spoofed ACK (attacker key)", "reject", "accept" if V.node_accepts_ack(spoof, KEY, NODE, 1, 10) else "reject")
        rnd = legit_ack[:-8] + bytes(rng.randrange(256) for _ in range(8))
        case("Spoofed ACK (random tag)", "reject", "accept" if V.node_accepts_ack(rnd, KEY, NODE, 1, 10) else "reject")
        case("Old ACK replayed for a later alert", "reject", "accept" if V.node_accepts_ack(legit_ack, KEY, NODE, 2, 11) else "reject")
        case("Genuine ACK for the waiting alert", "accept", "accept" if V.node_accepts_ack(legit_ack, KEY, NODE, 1, 10) else "reject")
        alert_as_ack = raw[: P.ACK_LEN]
        case("Alert bytes presented as an ACK", "reject", "accept" if V.node_accepts_ack(alert_as_ack, KEY, NODE, 1, 10) else "reject")

        # Base reboot
        v = _fresh(d)
        v.handle(raw)
        case("Base reboot, counter persisted: replay not processed again", V.REACK, v.reboot(True).handle(raw)[0])
        v = _fresh(d)
        v.handle(P.encode_alert(_alert(10), KEY))
        v.handle(P.encode_alert(_alert(11, 2), KEY))
        case("Base reboot, counter persisted: older replay rejected", V.REJECT_COUNTER,
             V.BaseVerifier(KEY, d / "counters.json", recent_n=1).handle(raw)[0])
        v = _fresh(d)
        v.handle(raw)
        case("Base reboot, counter lost: replay", V.ACCEPT, v.reboot(False).handle(raw)[0],
             "VULNERABILITY (documented): a recorded alert is accepted again after the counter store is lost")

        # Replay flood against the re-ACK, with and without the limit (one re-ACK per event per retry interval, ACK airtime paid from the duty budget)
        free, lim = flood(False), flood(True)
        case("Replay flood, no limit: the base keeps ACKing until its duty-cycle budget is gone", "budget exhausted",
             "budget exhausted" if free["no_budget"] > 0 else "budget not exhausted")
        case("Replay flood, no limit: a genuine alert arriving during the flood gets no ACK", V.ACCEPT_NO_ACK, str(free["legit"]),
             "the flood starves the legitimate ACK: a denial of service on ACKs")
        case("Replay flood, with limit: at most one re-ACK per retry interval", "True", str(lim["reacks"] <= FLOOD_S / lim["interval_s"] + 1))
        case("Replay flood, with limit: the base never runs out of budget", "True", str(lim["no_budget"] == 0))
        case("Replay flood, with limit: a genuine alert arriving during the flood is ACKed", V.ACCEPT, str(lim["legit"]))
        case("Replay flood, with limit: re-ACK airtime is lower than without the limit", "True", str(lim["reack_airtime_s"] < free["reack_airtime_s"]))
        v = V.BaseVerifier(KEY, reack_interval_s=lim["interval_s"], budget=V.DutyBudget(), sf=FLOOD_SF)
        v.handle(raw, 0.0)
        case("Limit on: a retry inside the retry interval is not re-ACKed", V.REACK_LIMITED, v.handle(raw, lim["interval_s"] / 2)[0])
        case("Limit on: a genuine retry one interval after the ACK is still re-ACKed", V.REACK, v.handle(raw, lim["interval_s"] * 1.01)[0])

        # Added 2026-11-11: exhaustive single-bit and length sweeps, counter exhaustion, shared key
        v = _fresh(d)
        flips = [bytes(b ^ (1 << bit) if i == pos else b for i, b in enumerate(raw)) for pos in range(len(raw)) for bit in range(8)]
        flip_dec = [V.BaseVerifier(KEY).handle(f)[0] for f in flips]
        case("Every single-bit flip of a valid alert is rejected", "True", str(all(x.startswith("reject") for x in flip_dec)),
             "the tag covers the body; the last bytes are the tag itself; all flips tried")
        lengths = [n for n in range(0, 200) if n != P.ALERT_LEN]
        len_dec = [V.BaseVerifier(KEY).handle((raw + bytes(200))[:n])[0] for n in lengths]
        case("Truncated or padded alerts (every other length) are rejected", "True", str(all(x == V.REJECT_LENGTH for x in len_dec)))
        case("All-zero packet of the alert length is rejected", V.REJECT_VERSION, V.BaseVerifier(KEY).handle(bytes(97))[0])
        case("All-ones packet of the alert length is rejected", V.REJECT_VERSION, V.BaseVerifier(KEY).handle(b"\xff" * 97)[0])
        ack_raw = P.encode_ack(P.Ack(NODE, 1, 10, 1), KEY)
        ack_flips = [bytes(b ^ (1 << bit) if i == pos else b for i, b in enumerate(ack_raw)) for pos in range(len(ack_raw)) for bit in range(8)]
        case("Every single-bit flip of a valid ACK is rejected by the node", "True", str(not any(V.node_accepts_ack(f, KEY, NODE, 1, 10) for f in ack_flips)))
        v = _fresh(d)
        v.handle(P.encode_alert(_alert(0xFFFFFFFF, 3), KEY))
        case("Counter exhausted (largest value seen): a node whose counter wraps to 0 is rejected", V.REJECT_COUNTER, v.handle(P.encode_alert(_alert(0, 4), KEY))[0],
             "LIMIT (documented): after the 32-bit counter is used up the key must be rotated; there is no epoch field in this layout")
        v = _fresh(d)
        other = P.Alert(node_id=NODE + 1, event_id=1, counter=1, timestamp_ms=1)
        case("Alert for another node_id signed with the shared key is accepted", V.ACCEPT, v.handle(P.encode_alert(other, KEY))[0],
             "LIMIT (documented): one shared key, so anyone who holds it can sign for any node; there is no per-node key and no key rotation")
    return out


def main() -> None:
    rows = run_cases()
    df = pd.DataFrame(rows)
    C.TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.TABLES / "attacks.csv", index=False)
    src = "results/tables/attacks.csv"
    ent = [dict(name="attacks.cases_total", value=len(df), unit="cases", origin="SIMULATED", source_file=src, notes="software simulation of attacks on the reference verifier"),
           dict(name="attacks.cases_matching_expected", value=int(df.match.sum()), unit="cases", origin="SIMULATED", source_file=src)]
    for i, r in enumerate(df.itertuples()):
        ent.append(dict(name=f"attacks.case{i:02d}.observed", value=r.observed, unit="outcome", origin="SIMULATED", source_file=src, notes=f"{r.case}; expected {r.expected}"))
    ent.append(dict(name="attacks.forgery_probability_per_guess", value=2.0**-64, unit="probability", origin="ANALYTICAL", source_file="src/crashguard/packet.py",
                    notes="8-byte tag: chance that one random tag is valid; assumes HMAC-SHA256 is a secure PRF"))
    fsrc = "src/crashguard/attacks.py"
    for tag, lim in (("no_limit", False), ("with_limit", True)):
        f = flood(lim)
        ent += [dict(name=f"attacks.flood.{tag}.replayed_packets", value=f["replayed"], unit="packets", origin="SIMULATED", source_file=fsrc, notes="same captured alert replayed at a fixed rate"),
                dict(name=f"attacks.flood.{tag}.reacks_sent", value=f["reacks"], unit="ACKs", origin="SIMULATED", source_file=fsrc),
                dict(name=f"attacks.flood.{tag}.reack_airtime_s", value=round(f["reack_airtime_s"], 3), unit="seconds", origin="SIMULATED", source_file=fsrc, notes="base station airtime spent on re-ACKs; ACK airtime from the Semtech formula"),
                dict(name=f"attacks.flood.{tag}.reacks_refused_no_budget", value=f["no_budget"], unit="packets", origin="SIMULATED", source_file=fsrc),
                dict(name=f"attacks.flood.{tag}.reacks_refused_by_limit", value=f["limited"], unit="packets", origin="SIMULATED", source_file=fsrc),
                dict(name=f"attacks.flood.{tag}.genuine_alert_during_flood", value=str(f["legit"]), unit="outcome", origin="SIMULATED", source_file=fsrc),
                dict(name=f"attacks.flood.{tag}.budget_left_s", value=round(f["budget_left_s"], 3), unit="seconds", origin="SIMULATED", source_file=fsrc)]
    ent += [dict(name="attacks.flood.rate_per_s", value=FLOOD_RATE_PER_S, unit="packets/s", origin="SIMULATED", source_file=fsrc, notes="scenario constant"),
            dict(name="attacks.flood.duration_s", value=FLOOD_S, unit="seconds", origin="SIMULATED", source_file=fsrc, notes="scenario constant"),
            dict(name="attacks.flood.base_budget_at_start_s", value=BASE_BUDGET_INITIAL_S, unit="seconds", origin="SIMULATED", source_file=fsrc,
                 notes="airtime budget left at the start; the rest is assumed used by other traffic"),
            dict(name="attacks.flood.retry_interval_s", value=round(flood(True)["interval_s"], 4), unit="seconds", origin="ANALYTICAL", source_file=fsrc,
                 notes="alert airtime + ACK window at SF7; the limit allows one re-ACK per event per interval")]
    record_many(ent)
    make_figure(df)
    print(df[["case", "expected", "observed", "match"]].to_string())


def make_figure(df: pd.DataFrame) -> None:
    import matplotlib.pyplot as plt

    from crashguard.plots import save, style

    style()
    fig, ax = plt.subplots(figsize=(9, 0.35 * len(df) + 1))
    ax.axis("off")
    cells = [[r.case, r.expected, r.observed, "yes" if r.match else "NO"] for r in df.itertuples()]
    tb = ax.table(cellText=cells, colLabels=["Case", "Expected", "Observed", "Match"], loc="center", cellLoc="left", colWidths=[0.55, 0.15, 0.2, 0.1])
    tb.auto_set_font_size(False)
    tb.set_fontsize(8)
    tb.scale(1, 1.3)
    save(fig, "s7_attack_table")


if __name__ == "__main__":
    main()
