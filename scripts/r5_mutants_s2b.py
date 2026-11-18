"""Mutant lists of L7, L8 and L9 (used by ``r5_mutants.py``). Each entry: (id, file, old text, new text, description)."""
from __future__ import annotations

L7 = "src/crashguard/r5_l7.py"
L8 = "src/crashguard/r5_l8.py"
L9 = "src/crashguard/r5_l9.py"

L7_MUTANTS = [
    ("L701", L7, "ok = b <= c <= b + w", "ok = b <= c < b + w", "window edge exclusive"),
    ("L703", L7, "b2 = c\n", "b2 = c + 1\n", "base advances past the accepted index"),
    ("L704", L7, 'if ev == "A":\n        return c + 1, b2, True', 'if ev == "A":\n        return c, b2, True', "car does not ratchet on a received ACK"),
    ("L705", L7, "return c, b, False  # a rejected", "return c + 1, b + 1, False  # a rejected", "rejection changes the state"),
    ("L706", L7, 'if ev == "B":\n        return c + 1, b, None', 'if ev == "B":\n        return c, b, None', "boot does not ratchet"),
    ("L707", L7, 'if ev == "B":\n        return c + 1, b, None', 'if ev == "B":\n        return c + 2, b, None', "boot ratchets twice"),
    ("L708", L7, "return c, b2, True", "return c + 1, b2, True", "lost ACK still ratchets the car"),
    ("L709", L7, "W = 8", "W = 4", "window"),
    ("L710", L7, "MAX_BOOTS = 3", "MAX_BOOTS = 9", "boots allowed in the claim"),
    ("L711", L7, "nxt = b <= c <= b + w", "nxt = b <= c <= b + w + 1", "next-alert test off by one"),
    ("L712", L7, 'if b > c:\n                    v["base_ahead"] += 1', 'if b > c + 1:\n                    v["base_ahead"] += 1', "base-ahead check loosened"),
    ("L713", L7, 'if r["gap"] > r["boots"] + 1:', 'if r["gap"] > r["boots"] + 5:', "gap bound loosened"),
    ("L714", L7, "if a != (b0 <= c0 <= b0 + w):", "if a != (b0 <= c0 <= b0 + w + 1):", "accept check loosened"),
    ("L715", L7, 'if r["boots"] <= max_boots:', 'if r["boots"] < max_boots:', "boot count boundary"),
    ("L716", L7, 'if r["gap"] > w:\n                n_over += 1', 'if r["gap"] > w + 1:\n                n_over += 1', "window-exceeding count"),
    ("L717", L7, "for ln in range(max_len + 1):", "for ln in range(max_len):", "longest sequences left out"),
    ("L718", L7, 'EVENTS = ("L", "A", "K", "B")', 'EVENTS = ("L", "A", "B")', "lost-ACK event left out"),
    ("L719", L7, "hash_resync_max=W", "hash_resync_max=W + 1", "cost: resync hash steps"),
    ("L720", L7, "car_state_bytes=32 + 4", "car_state_bytes=32", "cost: state bytes"),
    ("L721", L7, '("wellformedness_failed:" if wf else "")', '("")', "wellformedness failure ignored"),
    ("L722", L7, '("timeout" if "exit code: 124" in t else "unknown")', '("verified" if "exit code: 124" in t else "unknown")', "timeout counted as verified"),
]

L8_MUTANTS = [
    ("L801", L8, "over = (hc >= R_HC) or (last_hc == slot)", "over = (hc > R_HC) or (last_hc == slot)", "rate limit off by one"),
    ("L802", L8, "over = (hc >= R_HC) or (last_hc == slot)", "over = (hc >= R_HC)", "spacing rule dropped"),
    ("L803", L8, "over = (hc >= R_HC) or (last_hc == slot)", "over = (last_hc == slot)", "rate limit dropped"),
    ("L804", L8, 'if kind != "ok" or over:', "if over:", "plausibility check dropped"),
    ("L805", L8, "quar = strikes >= STRIKES_TO_QUARANTINE", "quar = strikes >= STRIKES_TO_QUARANTINE + 1", "quarantine needs three strikes"),
    ("L806", L8, "STRIKES_TO_QUARANTINE = 2", "STRIKES_TO_QUARANTINE = 1", "one strike quarantines"),
    ("L807", L8, "if last_q < 0 or slot - last_q >= QUAR_GAP:", "if True:", "quarantine forwards every alert"),
    ("L808", L8, "if last_q < 0 or slot - last_q >= QUAR_GAP:", "if last_q < 0 or slot - last_q > QUAR_GAP:", "quarantine gap boundary"),
    ("L809", L8, 'return (hc, last_hc, strikes, quar, slot), "low"', 'return (hc + 1, last_hc, strikes, quar, slot), "high"', "quarantine forwards high confidence"),
    ("L810", L8, 'return (hc + 1, slot, strikes, quar, last_q), "high"', 'return (hc, slot, strikes, quar, last_q), "high"', "high forward not counted"),
    ("L811", L8, 'return (hc + 1, slot, strikes, quar, last_q), "high"', 'return (hc + 1, last_hc, strikes, quar, last_q), "high"', "last forward slot not updated"),
    ("L812", L8, "R_HC = 6", "R_HC = 7", "bound R"),
    ("L813", L8, "MAX_PER_SLOT = 4", "MAX_PER_SLOT = 2", "alerts per slot"),
    ("L814", L8, "HORIZON = 60", "HORIZON = 30", "horizon"),
    ("L815", L8, 'KINDS = ("ok", "implausible", "repeat")', 'KINDS = ("ok", "implausible")', "attack kinds"),
    ("L816", L8, "for n in range(1, max_per_slot + 1):", "for n in range(1, max_per_slot):", "longest slot pattern left out"),
    ("L817", L8, "for slot in range(horizon):", "for slot in range(horizon - 1):", "last slot not explored"),
    ("L818", L8, "if s not in nxt or low > nxt[s]:", "if s not in nxt:", "worst low-confidence count not kept"),
    ("L819", L8, "max_hc = max(max_hc, s[0])", "max_hc = max(max_hc, 0)", "high-confidence maximum not tracked"),
    ("L820", L8, "slots = np.sort(rng.integers(0, HORIZON, n))", "slots = np.sort(rng.integers(0, HORIZON, n) // 2 * 2)", "legitimate alerts on even slots only"),
    ("L821", L8, 'st, cls = process(st, int(s), "ok")', 'st, cls = process(st, int(s), "repeat")', "legitimate alerts treated as repeated positions"),
    ("L822", L8, "quarantined += int(st[3])", "quarantined += int(st[2] > 0)", "strike counted as quarantine"),
    ("L823", L8, "n = int(rng.poisson(rate_per_hour))", "n = int(rng.poisson(rate_per_hour * 2))", "rate doubled"),
]

L9_MUTANTS = [
    ("L901", L9, "a = (1.0 - r) * g_min / r", "a = g_min / r", "retraction complement dropped"),
    ("L902", L9, "a = (1.0 - r) * g_min / r", "a = (1.0 - r) * g_min", "division by r dropped"),
    ("L903", L9, "pre_vs_act=a * (1.0 - phi) / (1.0 - f_pre)", "pre_vs_act=a * (1.0 - phi)", "pre vs act denominator"),
    ("L904", L9, "pre_vs_wait=a * phi / f_pre", "pre_vs_wait=a * phi", "pre vs wait denominator"),
    ("L905", L9, "F_PRE, PHI = 0.1, 0.5", "F_PRE, PHI = 0.5, 0.1", "assumptions swapped"),
    ("L906", L9, '"pre": f_pre * r * rho + (1.0 - r) * (1.0 - phi) * g_min}', '"pre": f_pre * r * rho + (1.0 - r) * phi * g_min}', "pre-alert time loss"),
    ("L907", L9, "return min(sorted(cost), key=lambda k: cost[k])", "return max(sorted(cost), key=lambda k: cost[k])", "worst option chosen"),
    ("L908", L9, "return (hi - lo) / (2.0 * 1.96)", "return (hi - lo) / 2.0", "standard deviation from the interval"),
    ("L909", L9, "0.0) / 60000.0", "0.0) / 1000.0", "time unit"),
    ("L910", L9, "rr = np.clip(rng.normal(r, sd_from_interval(r_lo, r_hi), nb), 1e-6, 1 - 1e-6)", "rr = np.full(nb, r)", "retraction share not resampled"),
    ("L911", L9, "return {k: (float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))) for k, v in t.items()}", "return {k: (float(np.quantile(v, 0.5)), float(np.quantile(v, 0.975))) for k, v in t.items()}", "interval lower limit"),
    ("L912", L9, "SEED, NB = 42, 2000", "SEED, NB = 43, 2000", "seed"),
    ("L913", L9, "pre_vs_act=a * (1.0 - phi) / (1.0 - f_pre)", "pre_vs_act=a * phi / (1.0 - f_pre)", "pre vs act uses phi instead of 1 - phi"),
    ("L914", L9, "return dict(act_vs_wait=a,", "return dict(act_vs_wait=a * 2,", "act vs wait scaled"),
    ("L915", L9, "g_min: float, f_pre: float = F_PRE, phi: float = PHI) -> dict:", "g_min: float, f_pre: float = F_PRE, phi: float = 0.4) -> dict:", "default phi"),
    ("L916", L9, "g_min: float, f_pre: float = F_PRE, phi: float = PHI) -> str:", "g_min: float, f_pre: float = F_PRE, phi: float = 0.9) -> str:", "default phi in the option choice"),
    ("L917", L9, '"wait": (1.0 - r) * g_min,', '"wait": r * g_min,', "wait cost"),
    ("L918", L9, '"act": r * rho,', '"act": (1.0 - r) * rho,', "act cost"),
    ("L919", L9, "f_pre * r * rho + (1.0 - r)", "f_pre * rho + (1.0 - r)", "pre-alert dispatch cost without r"),
    ("L920", L9, "gg = np.maximum(rng.normal(g_ms, sd_from_interval(g_lo, g_hi), nb), 0.0)", "gg = rng.normal(g_ms, sd_from_interval(g_lo, g_hi), nb)", "negative gain allowed"),
]
