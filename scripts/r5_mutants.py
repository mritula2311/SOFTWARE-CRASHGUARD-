"""Mutant lists of the round-5 modules (used by ``r5_mutation.py``). Each entry: (id, file, old text, new text, description). ``old`` must occur exactly in the file."""
from __future__ import annotations

L1 = "src/crashguard/r5_l1.py"

L1_MUTANTS = [
    ("L101", L1, "bad = ((gn >= p.g_still) | (np.abs(mag - 1.0) >= p.a_still)).astype(int)", "bad = ((gn >= p.g_still) & (np.abs(mag - 1.0) >= p.a_still)).astype(int)", "stillness: or becomes and"),
    ("L102", L1, "bad = ((gn >= p.g_still)", "bad = ((gn > p.g_still)", "gyro limit boundary"),
    ("L103", L1, "(np.abs(mag - 1.0) >= p.a_still)", "(np.abs(mag - 1.0) >= 10 * p.a_still)", "bias gate loosened tenfold"),
    ("L104", L1, "return st[((cb[st + L] - cb[st]) == 0) & (sd < p.sd_still)]", "return st[((cb[st + L] - cb[st]) == 0)]", "standard deviation test dropped"),
    ("L105", L1, "n, L = len(acc), int(round(p.still_s * fs))", "n, L = len(acc), int(round(p.still_s * fs)) - 100", "still window too short"),
    ("L106", L1, "if abs(dv[i]) >= p.a_min:", "if abs(dv[i]) > p.a_min:", "speed-change threshold exclusive"),
    ("L107", L1, "if gps_t[j + 1] - gps_t[i] >= p.seg_min_s - 1e-9:", "if gps_t[j + 1] - gps_t[i] >= p.seg_min_s - 1.5:", "segment length minimum loosened"),
    ("L108", L1, "and int(np.sign(dv[j + 1])) == s:", "and int(np.sign(dv[j + 1])) != s:", "segment run continues across a sign change"),
    ("L109", L1, "x_hat = sgn * h / np.linalg.norm(h)", "x_hat = h / np.linalg.norm(h)", "speed-change sign dropped"),
    ("L110", L1, "y_hat = np.cross(z_hat, x_hat)", "y_hat = np.cross(x_hat, z_hat)", "lateral axis sign"),
    ("L111", L1, "horiz = dyn - np.outer(dyn @ z_hat, z_hat)", "horiz = dyn", "vertical part not removed"),
    ("L112", L1, "dyn = acc[sel] - m_still", "dyn = acc[sel]", "gravity not subtracted in the segment"),
    ("L113", L1, "if np.linalg.norm(h) < p.h_min_g:", "if False:", "horizontal minimum dropped"),
    ("L114", L1, "if abs(float((gyro[sel] @ z_hat).mean())) >= p.straight_dps:", "if False:", "straight-line check dropped"),
    ("L115", L1, "z_hat = m_still / np.linalg.norm(m_still)", "z_hat = m_still", "gravity direction not normalised"),
    ("L116", L1, "return acc @ R_hat.T", "return acc @ R_hat", "rotation applied transposed"),
    ("L117", L1, "return math.degrees(math.acos(c))", "return math.degrees(math.asin(c))", "gravity angle formula"),
    ("L118", L1, "return gravity_angle_deg(z_hat, acc_window) > p.ang_stale", "return gravity_angle_deg(z_hat, acc_window) < p.ang_stale", "stale test inverted"),
    ("L119", L1, "spec = R @ (g0 + acc_dyn)", "spec = g0 + R @ acc_dyn", "gravity not rotated with the mounting"),
    ("L120", L1, "gyr = R @ gyr_dyn", "gyr = gyr_dyn", "gyro not rotated"),
    ("L121", L1, "a[0] = sgn * b * ramp", "a[0] = -sgn * b * ramp", "calibration drive acceleration sign"),
    ("L122", L1, "speed = v0 + sgn * b * G_MS2 * np.cumsum(ramp) / H.FS_INT", "speed = v0 + b * G_MS2 * np.cumsum(ramp) / H.FS_INT", "GPS speed sign"),
    ("L123", L1, "if rng.random() < 0.25:", "if False:", "no upside-down rotations in the random family"),
    ("L124", L1, "tilt = float(rng.uniform(0.0, 30.0))", "tilt = float(rng.uniform(0.0, 60.0))", "tilt range doubled"),
    ("L125", L1, "pred(to_vehicle(w, est[\"R_hat\"])) if est[\"ok\"]", "pred(w) if est[\"ok\"]", "NHTSA window not rotated"),
    ("L126", L1, "return float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975))", "return float(np.quantile(m, 0.5)), float(np.quantile(m, 0.975))", "bootstrap lower limit"),
    ("L127", L1, "y = SS.sensor_signal(sig, range_g, FS) + (R @ np.array([0, 0, N.GRAVITY_Z_G]) - np.array([0, 0, N.GRAVITY_Z_G]))", "y = SS.sensor_signal(sig, range_g, FS)", "rotated gravity not added in the NHTSA part"),
    ("L128", L1, "rows.append(dict(test_no=t[\"test_no\"], group_mm=t[\"group_mm\"], truth=t[\"truth\"], kind=t[\"kind\"], rot=k, pred_raw=raw, pred_l1=l1, est_ok=bool(est[\"ok\"])))", "rows.append(dict(test_no=t[\"test_no\"], group_mm=t[\"group_mm\"], truth=t[\"truth\"], kind=t[\"kind\"], rot=k, pred_raw=l1, pred_l1=raw, est_ok=bool(est[\"ok\"])))", "raw and L1 columns swapped"),
]

L2 = "src/crashguard/r5_l2.py"

L2_MUTANTS = [
    ("L201", L2, "return x[np.clip(np.arange(lo, hi), 0, len(x) - 1)]", "return x[np.arange(lo, hi) % len(x)]", "edge repetition replaced by wrap-around"),
    ("L202", L2, "return np.arange(k) * (n / FS) / k", "return np.arange(k) * (n / FS)", "GPS sample times not spread over the event"),
    ("L203", L2, "inw = (t >= t_tr - 3.0) & (t <= t_tr)", "inw = (t >= t_tr - 6.0) & (t <= t_tr)", "pre-trigger speed window doubled"),
    ("L204", L2, "inw = (t >= t_tr - 3.0) & (t <= t_tr)", "inw = (t >= t_tr - 3.0) & (t <= t_tr + 5.0)", "pre-trigger speed window reaches past the trigger"),
    ("L205", L2, "drop=pre - post,", "drop=post - pre,", "speed drop sign"),
    ("L206", L2, "max(pre, 1.0)", "max(pre, 0.1)", "relative drop denominator floor"),
    ("L207", L2, "-2.0, 2.0)), gps_missing=0.0)", "-1.0, 1.0)), gps_missing=0.0)", "relative drop clip"),
    ("L208", L2, "if k < 2 or not np.isfinite(gps).all():", "if k < 2:", "missing GPS values not detected"),
    ("L209", L2, "int(np.argmin(np.abs(t - t_end)))", "int(np.argmax(np.abs(t - t_end)))", "speed sample nearest the end of the window"),
    ("L210", L2, "end = i0 + FULL_N", "end = i0 + FULL_N - 50", "window starts before the end of the full window"),
    ("L211", L2, "we = end + w * FS", "we = end + FS", "window length ignores w"),
    ("L212", L2, "pre_vec = _cut(acc, i0 - FS, i0).mean(axis=0)", "pre_vec = _cut(acc, i0 - FS // 2, i0).mean(axis=0)", "pre-trigger reference window halved"),
    ("L213", L2, "last_a = win_a[-FS:]", "last_a = win_a[-FS // 2 :]", "quiet share over half a second"),
    ("L214", L2, "< 0.05).mean())", "< 0.5).mean())", "quiet tolerance loosened"),
    ("L215", L2, "orient = angle_deg(pre_vec, win_a[-FS // 2 :].mean(axis=0))", "orient = angle_deg(pre_vec, win_a[: FS // 2].mean(axis=0))", "orientation taken at the start of the window"),
    ("L216", L2, "energy = float((np.linalg.norm(gy_all, axis=1) ** 2).sum() / FS)", "energy = float((np.linalg.norm(gy_all, axis=1) ** 2).sum())", "energy not scaled by the sample time"),
    ("L217", L2, "gy_all = _cut(gyro, i0, we)", "gy_all = _cut(gyro, end, we)", "rotation energy from the end of the full window only"),
    ("L218", L2, "X[k] = X[k].fillna(fill[k])", "X[k] = X[k].fillna(0.0)", "missing values filled with zero"),
    ("L219", L2, "fill = {k: float(np.nanmedian(X[k].to_numpy())) for k in FEATS}", "fill = {k: float(np.nanmean(X[k].to_numpy())) for k in FEATS}", "fill by the mean"),
    ("L220", L2, "cw = \"balanced\" if prm.class_weight == \"balanced\" else None", "cw = None", "class weight ignored"),
    ("L221", L2, "need = int(math.ceil(target * n_pos - 1e-9))", "need = int(target * n_pos)", "recall target rounded down"),
    ("L222", L2, "return float(pos[need - 1])", "return float(pos[need])", "threshold one score too low"),
    ("L223", L2, "d = 1.0 - mn / mb", "d = mn / mb", "relative reduction inverted"),
    ("L224", L2, "p=float(((d <= 0).sum() + 1) / (len(d) + 1))", "p=float(((d >= 0).sum() + 1) / (len(d) + 1))", "bootstrap p direction"),
    ("L225", L2, "return dict(pt=float(d.mean()), lo=float(np.quantile(m, 0.025))", "return dict(pt=float(d.mean()), lo=float(np.quantile(m, 0.5))", "lower limit of the fall"),
    ("L226", L2, "nm = (label == 1) & h1", "nm = (label == 1)", "near-miss events of both halves"),
    ("L227", L2, "Eh = E & h1", "Eh = E", "provisional alarms of both halves"),
    ("L228", L2, "out[\"a\"][\"criterion_met\"] = bool(out[\"a\"][\"pt\"] >= 0.25 and out[\"a\"][\"lo\"] > 0 and", "out[\"a\"][\"criterion_met\"] = bool(out[\"a\"][\"pt\"] >= 0.25 and", "lower limit not required for H-L2a"),
    ("L229", L2, "out[\"a\"][\"recall_l2\"] >= out[\"a\"][\"recall_base\"] - 0.01)", "True)", "recall condition dropped for H-L2a"),
    ("L230", L2, "out[\"b\"][\"pt\"] >= 0.03 and", "out[\"b\"][\"pt\"] >= 0.003 and", "H-L2b margin of 3 points reduced"),
    ("L231", L2, "retr_b = (Eh & ~F_b)[Eh].astype(float)", "retr_b = (Eh & ~F_base)[Eh].astype(float)", "L2 retractions taken from the baseline"),
    ("L232", L2, "h1 = R5.halves(te.event_id.to_numpy()) == 1", "h1 = R5.halves(te.event_id.to_numpy()) == 0", "wrong half"),
    ("L233", L2, "t_b = threshold_for_fpr(yv, s[\"va\"], prm.alpha)", "t_b = threshold_for_fpr(yv, s[\"va\"], prm.alpha * 2)", "equal-budget threshold at twice the budget"),
]

from r5_mutants_l34 import L3_MUTANTS, L4_MUTANTS, L5_MUTANTS  # noqa: E402
from r5_mutants_s2 import L6_MUTANTS, L10_MUTANTS, L11_MUTANTS  # noqa: E402
from r5_mutants_s2b import L7_MUTANTS, L8_MUTANTS, L9_MUTANTS  # noqa: E402

ALGS = {
    "l1": (["tests/test_r5_l1.py"], L1_MUTANTS),
    "l2": (["tests/test_r5_l2.py"], L2_MUTANTS),
    "l3": (["tests/test_r5_l3.py"], L3_MUTANTS),
    "l4": (["tests/test_r5_l4.py"], L4_MUTANTS),
    "l5": (["tests/test_r5_l5.py"], L5_MUTANTS),
    "l6": (["tests/test_r5_l6.py"], L6_MUTANTS),
    "l10": (["tests/test_r5_l10.py"], L10_MUTANTS),
    "l11": (["tests/test_r5_l11.py"], L11_MUTANTS),
    "l7": (["tests/test_r5_l7.py"], L7_MUTANTS),
    "l8": (["tests/test_r5_l8.py"], L8_MUTANTS),
    "l9": (["tests/test_r5_l9.py"], L9_MUTANTS),
}
