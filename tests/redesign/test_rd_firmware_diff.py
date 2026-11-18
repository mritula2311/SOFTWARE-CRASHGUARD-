"""CV 1 and 4 for the firmware decision path (D6): known answers of the C primitives and the differential test of the C path against the Python reference (hex-float exact)."""
from __future__ import annotations

import hashlib
import hmac
import shutil

import pytest

from crashguard import rd_firmware as F
from crashguard import rd_policy as RP
from crashguard.lora import airtime_ms

pytestmark = pytest.mark.skipif(shutil.which("wsl") is None, reason="needs WSL with gcc for the host build")


@pytest.fixture(scope="module")
def cli():
    F.build()
    return F.run_cli


def test_sha256_and_hmac_known_answers(cli):
    out = cli(["SHA 616263", "HMAC 6b6579 616263", "HMAC " + "aa" * 20 + " " + "dd" * 50, "SHA " + ""])  # the empty message is passed as no token
    assert out[0] == hashlib.sha256(b"abc").hexdigest() == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert out[1] == hmac.new(b"key", b"abc", hashlib.sha256).hexdigest()
    assert out[2] == "773ea91e36800e46854db8ebd09181a72959098b3ef8c122d9635514ced565fe"  # RFC 4231 test case 3
    assert out[3] == hashlib.sha256(b"").hexdigest()


def test_airtime_hand_cases(cli):
    got = cli(["AIR 97 7", "AIR 24 7", "AIR 97 12", "AIR 14 9"])
    for line, (n, sf) in zip(got, ((97, 7), (24, 7), (97, 12), (14, 9))):
        assert F.same_float(line, airtime_ms(n, sf).hex())
    assert abs(airtime_ms(97, 7) - 169.0) < 1.0  # the documented value


def test_bins_hand_cases(cli):
    out = cli(["BINS 0x1.999999999999ap-4 0 0x0.0p+0 0x1.0p+0", "BINS 0x1.0p-1 10 0x1.0p+3 0x1.0p+0", "BINS 0x1.0p-2 3 0x1.0p+8 0x1.0p+0"])
    assert out[0] == f"{RP.loss_bin(0.1)} {RP.load_bin(0)} 0" == "1 0 0"  # loss exactly at the first edge falls in bin 1
    assert out[1] == f"{RP.loss_bin(0.5)} {RP.load_bin(10)} {RP.budget_units(8.0, 1.0)}" == "4 3 8"
    assert out[2].split()[2] == "8"  # the budget is capped at 8 units


def test_noncanonical_signature_rejected_by_both(cli):
    g = F.Gen(7, F.make_tables((9,)))
    ver = RP.ClusterAckVerifier(g.pk)
    fr = RP.encode_cluster_ack(g.sk, 5, 100, [1, 2])
    L = 2**252 + 27742317777372353535851937790883648493
    s_int = int.from_bytes(fr[-32:], "little") + L
    bad = fr[:-32] + (s_int & ((1 << 256) - 1)).to_bytes(32, "little")
    v = ver.check(bad, 1, 5, 100.0)
    out = cli([f"VER_RESET {g.pk_hex}", f"CLUSTER {bad.hex()} 1 5 {float(100).hex()} 10"])
    assert v.action == "ignore" and out[1] == "ignore bad_signature"


def test_differential_1000_traces(cli):
    r = F.run_diff(1000, seed=11, verbose=False)
    assert r["mismatched_ops"] == 0, r["first_mismatches"]
    assert r["by_command"]["CLUSTER"]["ops"] > 1000 and r["by_command"]["D1"]["ops"] > 500


def test_replay_of_simulator_decisions(cli):
    r = F.run_replay(hours=2)
    assert r["mismatches"] == 0 and r["records"] > 500, r
