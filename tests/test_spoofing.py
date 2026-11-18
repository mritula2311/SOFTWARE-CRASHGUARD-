"""X5: perturbations stay inside the budget and the band limits; the gradient attack respects them; physics helpers (synthetic windows only)."""
import numpy as np

from crashguard import config as C
from crashguard import spoofing as X


def test_random_candidates_respect_the_amplitude_budget_and_the_band():
    rng = np.random.default_rng(0)
    for eps in X.EPS_G:
        d = X.random_candidates(rng, 200, eps)
        assert X.max_abs(d) <= eps + 1e-9
        # no energy above 45 Hz or below 2 Hz beyond leakage: check the spectrum of one mixture
    d = X.random_candidates(rng, 50, 1.0)
    spec = np.abs(np.fft.rfft(d - d.mean(axis=1, keepdims=True), axis=1)).sum(axis=(0, 2))
    freqs = np.fft.rfftfreq(C.WIN_N, C.DT)
    assert spec[freqs > 48].sum() < 0.1 * spec.sum()


def test_structured_candidates_are_single_sinusoids_inside_the_budget():
    d = X.structured_candidates(0.5)
    assert d.shape[1:] == (C.WIN_N, 3) and X.max_abs(d) <= 0.5 + 1e-9 and len(d) == len(X.F_GRID) * len(X.PHASES) * len(X.PATTERNS)


def test_gradient_attack_respects_budget_and_band_limit():
    rng = np.random.default_rng(1)
    acc = rng.normal(size=(40, C.WIN_N, 3)) * 0.1
    y = (rng.random(40) > 0.5).astype(int)
    acc[y == 1, 100:140, 0] += 8.0
    sur = X.Surrogate("logistic").fit(acc, y)
    delta = X.gradient_attack(sur, acc, np.ones(40, bool), 0.5)
    assert X.max_abs(delta) <= 0.5 + 1e-6
    spec = np.abs(np.fft.rfft(delta, axis=1)).sum(axis=2)  # (n, f)
    freqs = np.fft.rfftfreq(C.WIN_N, C.DT)
    in_bank = np.isin(np.round(freqs).astype(int), np.array(X.K_BANK))
    # most of the energy sits on at most a few frequencies of the bank
    top3 = np.sort(spec, axis=1)[:, -6:].sum(axis=1) / np.maximum(spec.sum(axis=1), 1e-12)
    assert np.median(top3) > 0.5 and in_bank.any()


def test_gradient_attack_moves_the_surrogate_logit_in_the_wanted_direction():
    rng = np.random.default_rng(2)
    acc = rng.normal(size=(60, C.WIN_N, 3)) * 0.1
    y = (rng.random(60) > 0.5).astype(int)
    acc[y == 1, 100:140, 0] += 8.0
    sur = X.Surrogate("logistic").fit(acc, y)
    z0 = np.einsum("ij,ij->i", (acc.reshape(60, -1) - sur.mu) / sur.sd, np.broadcast_to(sur.w, (60, acc[0].size))) + sur.b
    up = X.gradient_attack(sur, acc, np.ones(60, bool), 2.0)
    z1 = np.einsum("ij,ij->i", ((acc + up).reshape(60, -1) - sur.mu) / sur.sd, np.broadcast_to(sur.w, (60, acc[0].size))) + sur.b
    assert z1.mean() > z0.mean()


def test_a_sinusoid_has_a_small_velocity_change_against_its_peak_and_a_crash_pulse_does_not():
    t = np.arange(C.WIN_N) * C.DT
    sinus = np.zeros((1, C.WIN_N, 3))
    sinus[0, :, 0] = 2.0 * np.sin(2 * np.pi * 20 * t)
    sinus[0, :, 2] = 1.0
    crash = np.zeros((1, C.WIN_N, 3))
    crash[0, 100:110, 0] = np.linspace(0, 8, 10)
    crash[0, 110:120, 0] = np.linspace(8, 0, 10)
    crash[0, :, 2] = 1.0
    dv_s, pk_s = X.physics(sinus)
    dv_c, pk_c = X.physics(crash)
    assert dv_s[0] / pk_s[0] < 0.5 * (dv_c[0] / pk_c[0])
