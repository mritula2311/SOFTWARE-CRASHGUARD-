"""X4: the bench-log parser on a SYNTHETIC fixture (DUMMY DATA: built here in a temporary folder, never written to results/). Checks clock alignment through the wired sync pulse, micros() wrap, and the table quantities."""
from __future__ import annotations

import csv
import shutil
import subprocess

import pytest

from crashguard import rd_bench as B
from crashguard.lora import airtime_ms

HEADER = ["trial", "role", "event", "t_us", "len", "sf", "rssi", "snr", "extra"]


def _w(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)


def _fixture(tmp_path, car_offset_us=7_000_000, wrap=False):
    """Trial 1: tap above, provisional at +0.05 s, confirm at +1.8 s. Trial 2: tap above, no confirm needed? no: trial 2 is a below-trigger tap with a provisional alert that is retracted (3 cancels)."""
    car, base = [], []
    off = car_offset_us  # the car clock reads (base clock - off)
    # trial 1 (base clock times in us; the car log is shifted by -off)
    T = 100_000_000
    car += [(1, "car", "SYNC", T - off, 0, 0, "", "", ""), (1, "car", "TRIGGER", T + 1_000_000 - off, 0, 0, "", "", "peak_mg=4500"), (1, "car", "PROV_TX_START", T + 1_050_000 - off, 24, 7, "", "", ""), (1, "car", "CONFIRM_TX_START", T + 2_800_000 - off, 97, 7, "", "", "")]
    base += [(1, "base", "SYNC", T, 0, 0, "", "", ""), (1, "base", "PROV_RX", T + 1_100_000, 24, 7, -90.0, 6.0, ""), (1, "base", "CONFIRM_RX", T + 2_950_000, 97, 7, -90.0, 6.0, "")]
    T2 = 200_000_000
    car += [(2, "car", "SYNC", T2 - off, 0, 0, "", "", ""), (2, "car", "TRIGGER", T2 + 500_000 - off, 0, 0, "", "", "peak_mg=3000"), (2, "car", "PROV_TX_START", T2 + 550_000 - off, 24, 7, "", "", "")] + [(2, "car", "CANCEL_TX_START", T2 + 2_000_000 + k * 100_000 - off, 14, 7, "", "", "") for k in range(3)]
    base += [(2, "base", "SYNC", T2, 0, 0, "", "", ""), (2, "base", "PROV_RX", T2 + 600_000, 24, 7, -92.0, 5.0, ""), (2, "base", "CANCEL_RX", T2 + 2_050_000, 14, 7, -92.0, 5.0, "")]
    if wrap:  # shift the car clock so that micros() wraps between the trials
        car = [(a, b, c, (t + 4_294_000_000) % B.WRAP, *rest) for a, b, c, t, *rest in car]
    _w(tmp_path / "car.csv", car)
    _w(tmp_path / "base.csv", base)
    with open(tmp_path / "taps.csv", "w", newline="") as fh:
        fh.write("trial,tap,condition\n1,above,10m\n2,below,10m\n")


def test_clock_alignment_and_table(tmp_path):
    _fixture(tmp_path)
    taps = B.read_taps(tmp_path / "taps.csv")
    rows = B.trial_table(B.read_log(tmp_path / "car.csv"), B.read_log(tmp_path / "base.csv"), taps)
    r1, r2 = rows
    assert r1["valid"] == 1 and r1["prov_rx_after_trigger_s"] == pytest.approx(0.1) and r1["confirm_rx_after_trigger_s"] == pytest.approx(1.95) and r1["confirm_minus_prov_rx_s"] == pytest.approx(1.85)
    a24, a97, a14 = (airtime_ms(b, 7) / 1000 for b in (24, 97, 14))
    assert r1["two_stage_air_s"] == pytest.approx(a24 + a97) and r1["single_stage_air_s"] == pytest.approx(a97)
    assert r2["cancel_sent"] == 1 and r2["two_stage_air_s"] == pytest.approx(a24 + 3 * a14)
    s = B.summary(rows)[0]
    assert s["retractions"] == 1 and s["provisional_sent"] == 2 and s["retraction_share"] == pytest.approx(0.5) and s["earlier_median_s"] == pytest.approx(1.85)


def test_micros_wrap_is_unwrapped(tmp_path):
    _fixture(tmp_path, wrap=True)
    taps = B.read_taps(tmp_path / "taps.csv")
    rows = B.trial_table(B.read_log(tmp_path / "car.csv"), B.read_log(tmp_path / "base.csv"), taps)
    # a wrap on one device between sync and trigger of the same trial would break the offset; here it falls between trials, and the per-trial offset absorbs it
    assert rows[0]["valid"] == 1 and rows[1]["valid"] == 1


def test_missing_sync_is_invalid(tmp_path):
    _fixture(tmp_path)
    car = [r for r in B.read_log(tmp_path / "car.csv") if not (r["trial"] == 2 and r["event"] == "SYNC")]
    rows = B.trial_table(car, B.read_log(tmp_path / "base.csv"), B.read_taps(tmp_path / "taps.csv"))
    assert rows[1]["valid"] == 0


@pytest.mark.skipif(shutil.which("wsl") is None, reason="needs WSL with gcc")
def test_logging_hook_lines_parse(tmp_path):
    """The host stub of the logging hooks prints lines in the format the parser reads."""
    from pathlib import Path

    src = Path("firmware_rd/bench/test_cg_bench_log.c").resolve()
    s = str(src).replace("\\", "/")
    wsrc = "/mnt/" + s[0].lower() + s[2:]
    out = subprocess.run(["wsl", "-d", "Ubuntu", "--", "bash", "-c", f"gcc -std=c99 -o /tmp/tbench_pytest {wsrc} && /tmp/tbench_pytest"], capture_output=True, text=True).stdout
    p = tmp_path / "car.csv"
    p.write_text(out.replace("\r", ""), encoding="utf-8")
    rows = B.read_log(p)
    assert [r["event"] for r in rows][:3] == ["SYNC", "TRIGGER", "PROV_TX_START"] and rows[0]["trial"] == 7 and rows[4]["rssi"] == -91.0
