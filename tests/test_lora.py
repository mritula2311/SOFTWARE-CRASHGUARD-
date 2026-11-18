import random

from crashguard import delivery_sim as D
from crashguard.lora import airtime_ms, alerts_per_hour


def test_airtime_97_bytes_sf7_is_about_169_ms():
    assert abs(airtime_ms(97, 7) - 169.0) < 1.0


def test_airtime_grows_with_sf_and_payload():
    a = [airtime_ms(97, sf) for sf in range(7, 13)]
    assert a == sorted(a)
    assert airtime_ms(26, 7) < airtime_ms(97, 7)


def test_low_data_rate_optimisation_only_when_symbol_over_16ms():
    assert airtime_ms(97, 11) > airtime_ms(97, 11, low_dr_opt=False)  # SF11 at 125 kHz: 16.4 ms symbols
    assert airtime_ms(97, 7) == airtime_ms(97, 7, low_dr_opt=False)


def test_alerts_per_hour_matches_budget():
    n = alerts_per_hour(97, 7)
    assert n * airtime_ms(97, 7) / 1000 <= 360 < (n + 1) * airtime_ms(97, 7) / 1000


def test_no_loss_means_every_alert_is_acked():
    for sc in D.SCENARIOS:
        for pol in D.MAX_TRIES:
            s = D.summarise(D.simulate(sc, pol, 0.0, random.Random(1)))
            assert s["acked_all"] == 1.0 and s["received_all"] == 1.0


def test_simulation_is_reproducible_and_terminates_under_heavy_loss():
    sc = D.SCENARIOS[2]
    a = D.summarise(D.simulate(sc, "severity", 0.6, random.Random(5)))
    b = D.summarise(D.simulate(sc, "severity", 0.6, random.Random(5)))
    assert a == b


def test_reack_repairs_lost_acks_that_strict_mode_cannot():
    sc = D.SCENARIOS[0]
    strict = D.summarise(D.simulate(sc, "fixed3", 0.4, random.Random(2), mode="strict_same_counter"))
    reack = D.summarise(D.simulate(sc, "fixed3", 0.4, random.Random(2), mode="reack"))
    assert reack["acked_all"] > strict["acked_all"]

