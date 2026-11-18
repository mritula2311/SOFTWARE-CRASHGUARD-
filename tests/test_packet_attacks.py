from crashguard import packet as P
from crashguard.attacks import KEY, NODE, run_cases


def test_alert_is_97_bytes_and_roundtrips():
    a = P.Alert(node_id=NODE, event_id=7, counter=3, timestamp_ms=99, severity=3, impact_side=2, angle_deg_x10=1805,
                lat_e7=-123, lon_e7=456, peak_g_x100=1234, ml_prob_x10000=9999, rule_sev=3, sw_mask=0b10101, sw_first=2, rollover=1,
                delta_v_kmh_x100=4521, asi_x100=187)
    raw = P.encode_alert(a, KEY)
    assert len(raw) == 97
    assert P.decode_alert(raw) == a
    assert P.tag_ok(raw, KEY, P.ALERT_BODY_LEN)


def test_tag_covers_bytes_0_to_88():
    raw = P.encode_alert(P.Alert(node_id=1, event_id=1, counter=1, timestamp_ms=1), KEY)
    for i in (0, 10, 18, 38, 40, 50, 88):
        t = bytearray(raw)
        t[i] ^= 1
        assert not P.tag_ok(bytes(t), KEY, P.ALERT_BODY_LEN)


def test_ack_is_26_bytes():
    assert len(P.encode_ack(P.Ack(1, 2, 3, 4), KEY)) == 26


def test_attack_suite_matches_expected_outcomes():
    rows = run_cases()
    assert all(r["match"] for r in rows), [r["case"] for r in rows if not r["match"]]
    lost = next(r for r in rows if r["case"].startswith("Base reboot, counter lost"))
    assert lost["observed"] == "accept"  # documented vulnerability, not hidden


def test_lost_ack_retry_is_re_acked_but_old_counters_are_not():
    from crashguard import verifier as V

    v = V.BaseVerifier(KEY)
    raw = P.encode_alert(P.Alert(node_id=NODE, event_id=1, counter=10, timestamp_ms=1), KEY)
    d1, ack1 = v.handle(raw)
    bc = v.base_counter
    d2, ack2 = v.handle(raw)  # ACK was lost, the car retries the same packet
    assert (d1, d2) == (V.ACCEPT, V.REACK) and ack1 == ack2 and v.base_counter == bc
    assert V.node_accepts_ack(ack2, KEY, NODE, 1, 10)
    assert v.handle(P.encode_alert(P.Alert(node_id=NODE, event_id=2, counter=10, timestamp_ms=1), KEY))[0] == V.REJECT_COUNTER
    strict = V.BaseVerifier(KEY, idempotent=False)
    strict.handle(raw)
    assert strict.handle(raw)[0] == V.REJECT_COUNTER  # the failure that was found



def test_flood_limit_saves_airtime_and_protects_genuine_acks():
    from crashguard.attacks import flood

    free, lim = flood(False), flood(True)
    assert free["no_budget"] > 0 and free["legit"] == "accept_no_ack"
    assert lim["no_budget"] == 0 and lim["legit"] == "accept"
    assert lim["reack_airtime_s"] < free["reack_airtime_s"]
