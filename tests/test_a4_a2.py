"""Tests of the round-4 A2 module and the data builders (PREREGISTRATION_V15 sections 3 and 6)."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pytest

from crashguard import a4_a2 as A2
from crashguard import a4_common as C
from crashguard import r3_t1 as T1

ROOT = Path(__file__).resolve().parents[1]


def synth_segs(n=400, probs=(0.8, 0.5, 0.2), seed=0, flip_after=None):
    rng = np.random.default_rng(seed)
    m = np.zeros(n, np.uint16)
    for g, p in enumerate(probs):
        pg = p
        hit = rng.random(n) < pg
        if flip_after is not None and g == 0:
            hit[flip_after:] = False  # gateway 0 stops hearing the device in the later half
        m |= (hit.astype(np.uint16) << g)
    return [(m, np.arange(n, dtype=float))]


def test_set_mask_and_sequence():
    assert A2.set_mask([2, 0, 5], 1) == 0b100 and A2.set_mask([2, 0, 5], 2) == 0b101 and A2.set_mask([2, 0, 5], 3) == 0b100101
    m = np.array([0b001, 0b010, 0b100, 0, 0b011], np.uint16)
    assert A2.set_sequence(m, 0b001).tolist() == [1, 0, 0, 0, 1]
    assert A2.set_sequence(m, 0b011).tolist() == [1, 1, 0, 0, 1]


def test_ranking_uses_only_the_earlier_half():
    segs = synth_segs(flip_after=200)  # gateway 0 is best in the earlier half and silent in the later half
    rk = A2.ranking(segs)
    assert rk["order"][0] == 0 and rk["n_rank"] == 200 and 0.1 < rk["loss_best"] < 0.3
    segs2 = synth_segs()
    assert A2.ranking(segs2)["order"][:3] == [0, 1, 2]


def test_ranking_ignores_gateways_that_never_heard():
    segs = synth_segs(probs=(0.0, 0.7))
    assert A2.ranking(segs)["order"] == [1]
    assert A2.ranking([(np.zeros(100, np.uint16), np.arange(100.0))])["order"] == []


def test_test_positions_are_in_the_later_half_with_frames_ahead():
    segs = [(np.ones(120, np.uint16), np.arange(120.0)), (np.ones(200, np.uint16), np.arange(200.0))]
    n_rank = (120 + 200) // 2
    pos = A2.test_positions(segs, n_rank)
    assert pos and all(((sum(len(segs[k][0]) for k in range(i)) + j) >= n_rank) and (len(segs[i][0]) - j >= T1.MIN_AHEAD) for i, j in pos)
    assert (0, 0) not in pos and (1, 159) in pos and (1, 40) in pos and (1, 39) not in pos


def test_more_receivers_never_lower_delivery():
    rng = np.random.default_rng(3)
    for k in range(20):
        segs = synth_segs(n=300, probs=tuple(rng.uniform(0.05, 0.9, 4)), seed=k)
        r = A2.device_task((f"d{k}", segs, 60, False))
        if r is None:
            continue
        v = np.array(r["value"])
        assert np.all(np.diff(v) >= -1e-12) and 0.0 <= v.min() and v.max() <= 1.0, v


def test_delivery_counts_only_before_the_deadline():
    r = np.zeros(60, np.uint8)
    assert not A2.z0_delivered(r, 0)
    r[0] = 1
    assert A2.z0_delivered(r, 0)  # first attempt at 1.85 s ends well before 10 s


def test_a2_result_is_zero_without_a_hearing_gateway():
    segs = [(np.zeros(300, np.uint16), np.arange(300.0))]
    assert A2.device_task(("x", segs, 10, False)) is None


# ---------------------------------------------------------------- data builders
def test_gateway_frames_or_copies_and_fill_gaps():
    t = np.array([0.0, 1.0, 1.5, 100.0, 200.0])
    f = np.array([10, 10, 10, 13, 14])
    gw = np.array([0b001, 0b010, 0b001, 0b001, 0b100])
    segs = C.frames_of_device_gw(t, f, gw)
    assert len(segs) == 1
    m = segs[0][0]
    assert m.tolist() == [0b011, 0, 0, 0b001, 0b100]  # copies OR-ed (a repeated bit stays one bit), frames 11 and 12 lost
    assert len(segs[0][1]) == len(m)


def test_gateway_frames_new_segment_on_large_gap_and_reset():
    t = np.arange(4.0) * 100
    f = np.array([5, 300, 301, 2])
    segs = C.frames_of_device_gw(t, f, np.array([1, 1, 1, 1]))
    assert [len(m) for m, _ in segs] == [1, 2, 1]


def test_gateway_builder_matches_round3_union_sequences():
    f = ROOT / "data" / "processed" / "a4_loed_gw.pkl"
    l3 = ROOT / "data" / "processed" / "r3_t1_links.pkl"
    if not (f.exists() and l3.exists()):
        pytest.skip("built data not present")
    d = pickle.loads(f.read_bytes())["links"]
    L3 = pickle.loads(l3.read_bytes())
    for dev in sorted(d)[:150]:
        a, b = d[dev]["segs"], L3[dev]["segs"]
        assert len(a) == len(b)
        for (m, _), (r, _) in zip(a, b):
            assert np.array_equal((m != 0).astype(np.uint8), r)


def test_sniffer_builder_rules_on_a_non_study_site():
    p = ROOT / "data" / "raw" / "a4_sniffer" / "x" / "03_Brno_join_data.csv"
    if not p.exists():
        pytest.skip("sniffer data not present")
    d = C.read_sniffer_site("03_Brno_join")  # a site outside the study set, used only to exercise the reader
    assert set(d.mtype.unique()) <= set(C.UP_TYPES) and (d.fcnt >= 0).all() and (d.dev != 0).all()


# ---------------------------------------------------------------- known answer: round-3 zero-spacing control
def test_known_answer_round3_z0_values():
    held = ROOT / "data" / "processed" / "r3_t1_held.pkl"
    gw = ROOT / "data" / "processed" / "a4_loed_gw.pkl"
    l3 = ROOT / "data" / "processed" / "r3_t1_links.pkl"
    if not (held.exists() and gw.exists() and l3.exists()):
        pytest.skip("round-3 data not present")
    res = {x["dev"]: x for x in pickle.loads(held.read_bytes())["res"]}
    G = pickle.loads(gw.read_bytes())["links"]
    n_checked = 0
    for dev in sorted(res)[:40]:
        segs = G[dev]["segs"]
        r_union = [A2.set_sequence(m, 0x1FF) for m, _ in segs]
        adm = T1.admissible([(r, None) for r in r_union])
        rng0 = T1.seeded("t1s", dev, T1.SEED)
        picks = [adm[rng0.randrange(len(adm))] for _ in range(T1.N_START)]
        v = np.mean([A2.z0_delivered(r_union[si], pos) for si, pos in picks])
        assert v == pytest.approx(res[dev]["deliv"]["Z0"], abs=1e-12), dev
        n_checked += 1
    assert n_checked == 40


def test_band_of_edges():
    assert A2.band_of(0.0) == "L" and A2.band_of(0.0999) == "L" and A2.band_of(0.10) == "M" and A2.band_of(0.3999) == "M" and A2.band_of(0.40) == "H" and A2.band_of(1.0) == "H"


def test_device_value_matches_direct_replay_for_one_set():
    segs = synth_segs(n=300, probs=(0.6, 0.3), seed=5)
    r = A2.device_task(("q", segs, 40, False))
    rk = A2.ranking(segs)
    rng0 = T1.seeded("a2s", "q", A2.SEED)
    adm = A2.test_positions(segs, rk["n_rank"])
    picks = [adm[rng0.randrange(len(adm))] for _ in range(40)]
    seq = A2.set_sequence(segs[0][0], A2.set_mask(rk["order"], 1))
    assert r["value"][0] == pytest.approx(np.mean([A2.z0_delivered(seq, pos) for _si, pos in picks]))
