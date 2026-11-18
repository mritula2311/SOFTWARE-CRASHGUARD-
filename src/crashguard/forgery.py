"""Forgery and counter analysis (ANALYTICAL). No simulation: every number follows from a formula and the LoRa airtime.

- Tag: HMAC-SHA256 truncated to 8 bytes (64 bits). A blind forgery (random tag) is accepted with probability 2^-64 per attempt, so the expected number of
  attempts to get one forged alert accepted is 2^64, and a 50% chance needs ln(2) x 2^64 attempts. This assumes the key is secret and HMAC-SHA256 behaves as a
  pseudo-random function; it says nothing about key theft (one key is shared by both nodes).
- Attack rate: the attacker sends 97 B packets back to back at the airtime of the chosen spreading factor (the airtime limit of the channel, no duty-cycle
  restriction), or limited to the 10% duty cycle. Each attempt costs one packet; the base answers nothing to a bad tag.
- Counter: 32 bits, one value per transmitted alert. Wrap time follows from the fastest honest alert rate (the duty-cycle limit) and from a stated slower rate.
- Replay flood and counter rollover limits are written next to the numbers (docs/01_protocol/PACKET_FORMAT.md).
"""
from __future__ import annotations

import math

from crashguard.lora import DUTY, airtime_ms
from crashguard.packet import ALERT_LEN
from crashguard.results import record_many

TAG_BITS = 64
SECONDS_PER_YEAR = 365.25 * 24 * 3600
SRC = "src/crashguard/forgery.py"


def rows() -> list[dict]:
    out = []
    for sf in (7, 9, 12):
        air_s = airtime_ms(ALERT_LEN, sf) / 1000.0
        full_rate = 1.0 / air_s  # packets per second, channel always busy
        duty_rate = DUTY / air_s  # packets per second at the duty-cycle limit
        for lab, rate in (("airtime_limit", full_rate), ("duty_limited", duty_rate)):
            exp_s = 2.0**TAG_BITS / rate
            out.append(dict(sf=sf, attacker=lab, airtime_ms=air_s * 1000.0, packets_per_s=rate, expected_attempts=2.0**TAG_BITS,
                            expected_years=exp_s / SECONDS_PER_YEAR, half_chance_years=math.log(2) * exp_s / SECONDS_PER_YEAR))
    return out


def counter_rows() -> list[dict]:
    out = []
    for sf in (7, 12):
        air_s = airtime_ms(ALERT_LEN, sf) / 1000.0
        per_hour = 3600.0 * DUTY / air_s  # most alerts a node may send per hour at the duty-cycle limit (no ACK traffic counted)
        out.append(dict(sf=sf, basis="duty_limit_alerts_per_hour", alerts_per_hour=per_hour, wrap_years=2.0**32 / per_hour / (24 * 365.25)))
    out.append(dict(sf=0, basis="one_alert_per_minute", alerts_per_hour=60.0, wrap_years=2.0**32 / 60.0 / (24 * 365.25)))
    out.append(dict(sf=0, basis="one_alert_per_day", alerts_per_hour=1.0 / 24.0, wrap_years=2.0**32 / (1.0 / 24.0) / (24 * 365.25)))
    return out


def main() -> None:
    ent = []
    ent.append(dict(name="forgery.tag_bits", value=TAG_BITS, unit="bits", origin="ANALYTICAL", source_file=SRC, notes="HMAC-SHA256 truncated to 8 bytes"))
    ent.append(dict(name="forgery.p_per_attempt", value=2.0**-TAG_BITS, unit="probability", origin="ANALYTICAL", source_file=SRC, notes="2^-64: one blind forgery attempt"))
    ent.append(dict(name="forgery.expected_attempts", value=2.0**TAG_BITS, unit="attempts", origin="ANALYTICAL", source_file=SRC, notes="2^64 attempts for one expected success"))
    for r in rows():
        for k, unit in (("airtime_ms", "ms"), ("packets_per_s", "packets/s"), ("expected_years", "years"), ("half_chance_years", "years")):
            ent.append(dict(name=f"forgery.sf{r['sf']}.{r['attacker']}.{k}", value=float(r[k]), unit=unit, origin="ANALYTICAL", source_file=SRC,
                            notes="97 B packets back to back (airtime_limit) or at the 10% duty cycle (duty_limited); key assumed secret"))
    for r in counter_rows():
        tag = f"sf{r['sf']}" if r["sf"] else "slow"
        ent.append(dict(name=f"counter.wrap_years.{r['basis']}.{tag}", value=float(r["wrap_years"]), unit="years", origin="ANALYTICAL", source_file=SRC,
                        notes="2^32 counter values at the stated alert rate; the counter advances once per new alert"))
        ent.append(dict(name=f"counter.alerts_per_hour.{r['basis']}.{tag}", value=float(r["alerts_per_hour"]), unit="alerts/h", origin="ANALYTICAL", source_file=SRC))
    ent.append(dict(name="counter.values", value=2.0**32, unit="values", origin="ANALYTICAL", source_file=SRC, notes="32-bit counter"))
    record_many(ent)
    for r in rows():
        print(r)
    for r in counter_rows():
        print(r)


if __name__ == "__main__":
    main()
