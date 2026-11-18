"""L5 (docs/02_preregistration/PREREGISTRATION_V16.md section 7): end-to-end deadline-aware choice of the early-exit thresholds (MEASURED_SOFTWARE for the detector plus a link-model label).

    python -m crashguard.r5_l5 delays       # ns-3 delay samples (fresh r3t runs, SF9, shipped sensitivities, extra loss 0.1) for the development and held-out seeds
    python -m crashguard.r5_l5 dev          # development iterations on validation events and development delay distributions
    python -m crashguard.r5_l5 freeze
    python -m crashguard.r5_l5 held         # held-out run, once: HALF0 of the test split and held-out delay distributions; keys r5.l5.*

Time to awareness of a crash event (V16 7.1): the earliest frame that reaches the base. P = provisional alarm of the early-exit rule decided before 1,800 ms (a 14-byte flash, ready at the decision time plus
8 ms); C = confirm alarm of the 1,800 ms forest at its validation threshold (a 97-byte alert ready at 1.808 s). P and C: the earlier arrival; C alone: the alert (single-stage); P without C: the flash is cancelled
(counted as not aware); neither or not triggered: not aware. A frame must reach the base within 10 s of the crash. Not aware or not delivered: the cap of 60 s. The confirm stage and the budget on the final false-alarm
rate are those of R3 and do not change; the co-design chooses only the early-exit thresholds (hi, lo) of ``early.py``, subject to the provisional false-alarm rate on all non-crash validation events being at most the
budget. Delays come from three link models (custom, ns-3, LoED traces), drawn independently per event with common random numbers across arms. Nothing here reads ``data/hardware``.
"""
from __future__ import annotations

import json
import pickle
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from crashguard import packet as P
from crashguard.lora import airtime_ms

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed" / "r5_l5_out"
DEV_EVENTS = ROOT / "data" / "processed" / "r5_l5_dev_events.txt"  # event table of the development ns-3 runs, built from VALIDATION decisions only (review finding 2)
CAP_S, DEADLINE_S = 60.0, 10.0
COMPUTE_S, FINAL_S = 0.008, 1.808
TRIES, PROC_S, MARGIN_S = 4, 0.1, 0.1
SF, P_LOSS = 9, 0.1
NDRAW, SEED, NB = 20, 42, 2000
DEV_NS3_SEEDS, HELD_NS3_SEEDS = range(421, 441), range(601, 641)
LINK_MODELS = ("custom", "ns3", "loed")
A_FLASH, A_ALERT, A_ACK = (airtime_ms(b, SF) / 1000.0 for b in (14, P.ALERT_LEN, P.ACK_LEN))
WIN = PROC_S + A_ACK + MARGIN_S


@dataclass(frozen=True)
class L5Params:
    grid: str = "full"  # development item: "full", "a_hi" (B_LO as in the baseline rule) or "b_lo" (A_HI as in the baseline rule)
    objective: str = "cap"  # development item: "cap" (90th percentile with the cap) or "conditional" (among events that were alerted and delivered)
    alpha: float = 0.01


ITERATIONS = [L5Params(), L5Params(grid="a_hi"), L5Params(grid="b_lo"), L5Params(objective="conditional")]


# ------------------------------------------------------------------------------------------------ delay distributions (seconds from the ready time; inf = not delivered)
def arrival_delays(a_msg: float, p: float, rng: np.random.Generator, n: int) -> np.ndarray:
    """The custom simulator's single-flow link (``ar_r3.arrival``) at SF9: per-direction iid loss ``p``; a try without ACK is repeated after ``a_msg + WIN``; four tries; delay of the first uplink that gets through."""
    out = np.full(n, np.inf)
    t = np.zeros(n)
    alive = np.ones(n, bool)
    for _k in range(TRIES):
        up = rng.random(n) >= p
        dn = rng.random(n) >= p
        hit = alive & up
        out[hit] = t[hit] + a_msg
        alive = alive & ~up & ~(up & dn)
        t = t + a_msg + WIN
    return out


def delays_custom(seed: int, n: int = 20000, p: float = P_LOSS) -> dict:
    rng = np.random.default_rng(seed)
    return dict(flash=arrival_delays(A_FLASH, p, rng, n), alert=arrival_delays(A_ALERT, p, rng, n), label="SIMULATED")


def trace_delay(r: np.ndarray, s: int, a_msg: float) -> float:
    """One message over a measured link: attempt k sees frame s + k (reception 1/0); four tries, a repeat after ``a_msg + WIN``. The delay is that of the earliest received uplink (an acknowledgement
    only stops the repeats and does not change when the first copy arrives, so it is not modelled here)."""
    t = 0.0
    for k in range(TRIES):
        if s + k >= len(r):
            break
        if r[s + k] == 1:
            return t + a_msg
        t += a_msg + WIN
    return float("inf")


def delays_loed(links: dict, half: int, seed: int, n: int = 20000) -> dict:
    """Delay samples over the LoED devices of one half: a device is drawn uniformly, a segment with probability proportional to its length, a start with 40 frames ahead (the V14 rule). The delay of an attempt sequence does not depend on the link's acknowledgement loss."""
    from crashguard.r3_t1_extract import MIN_AHEAD

    devs = [d for d, v in links.items() if v["half"] == half]
    rng = np.random.default_rng(seed)
    fl, al = np.empty(n), np.empty(n)
    for i in range(n):
        v = links[devs[int(rng.integers(0, len(devs)))]]
        segs = [(r, t) for r, t in v["segs"] if len(r) > MIN_AHEAD]
        w = np.array([len(r) - MIN_AHEAD for r, _ in segs], float)
        r = segs[int(rng.choice(len(segs), p=w / w.sum()))][0]
        s = int(rng.integers(0, len(r) - MIN_AHEAD))
        fl[i] = trace_delay(r, s, A_FLASH)
        al[i] = trace_delay(r, s, A_ALERT)
    return dict(flash=fl, alert=al, label="TRACE_DRIVEN", n_devices=len(devs))


def delays_ns3(seeds, d: Path, events: Path | None = None) -> dict:
    """Delay samples from stored ns-3 runs of the policy ``r3t``: flash delay = arrival minus the ready time of the flash (decision time plus 8 ms), alert delay = arrival minus 1.808 s."""
    from crashguard import pp_r3_ns3 as P1

    ev = __import__("pandas").read_csv(events or P1.EVENTS, sep=" ", header=None, names=["E", "F", "y", "tE"])
    fl, al, nrun = [], [], 0
    for s in seeds:
        f = d / f"sf{SF}_shipped_p{P_LOSS:g}_r3t_{s}.txt"
        if not f.exists() or f.stat().st_size == 0:
            continue
        df, _duty, _drop = P1.load(f, ev)
        df = df[df.dropped == 0]
        a = df[(df.E == 1) & (df.tE < 1.8)]
        fl.append(np.where(a.flash >= 0, a.flash - (a.tE + COMPUTE_S), np.inf))
        b = df[df.F == 1]
        al.append(np.where(b.alert >= 0, b.alert - FINAL_S, np.inf))
        nrun += 1
    return dict(flash=np.concatenate(fl), alert=np.concatenate(al), label="SIMULATED", n_runs=nrun)


# ------------------------------------------------------------------------------------------------ time to awareness
def time_to_awareness(prov: np.ndarray, conf: np.ndarray, t_prov_ms: np.ndarray, d_flash: np.ndarray, d_alert: np.ndarray) -> np.ndarray:
    """Time to awareness (s, capped) of crash events: arrays over events; ``d_flash`` and ``d_alert`` are delay draws (events x draws, inf = not delivered)."""
    t_p = (t_prov_ms / 1000.0 + COMPUTE_S)[:, None] + d_flash
    t_p = np.where(t_p <= DEADLINE_S, t_p, np.inf)
    t_c = FINAL_S + d_alert
    t_c = np.where(t_c <= DEADLINE_S, t_c, np.inf)
    P_, C_ = prov[:, None], conf[:, None]
    t = np.where(P_ & C_, np.minimum(t_p, t_c), np.where(C_ & ~P_, t_c, np.inf))
    return np.where(np.isfinite(t), t, CAP_S)


def p90(x: np.ndarray, conditional: bool = False) -> float:
    x = np.asarray(x, float).ravel()
    if conditional:
        x = x[x < CAP_S]
        if not len(x):
            return float("nan")
    return float(np.quantile(x, 0.90))


def sample_draws(delays: dict, n_events: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    i = rng.integers(0, len(delays["flash"]), (n_events, NDRAW))
    j = rng.integers(0, len(delays["alert"]), (n_events, NDRAW))
    return delays["flash"][i], delays["alert"][j]


def reduction_boot(t_base: np.ndarray, t_new: np.ndarray, conditional: bool, seed: int = SEED, nb: int = NB) -> dict:
    """Relative reduction 1 - P90(new) / P90(base) with a paired bootstrap over events (each event brings its ``NDRAW`` draws)."""
    n = len(t_base)
    rng = np.random.default_rng(seed)
    pt = 1.0 - p90(t_new, conditional) / p90(t_base, conditional)
    d = np.empty(nb)
    for b in range(nb):
        i = rng.integers(0, n, n)
        d[b] = 1.0 - p90(t_new[i], conditional) / p90(t_base[i], conditional)
    d = d[np.isfinite(d)]
    return dict(pt=float(pt), lo=float(np.quantile(d, 0.025)), hi=float(np.quantile(d, 0.975)), p=float(((d <= 0).sum() + 1) / (len(d) + 1)), p90_base=p90(t_base, conditional), p90_new=p90(t_new, conditional), n=n)


# ------------------------------------------------------------------------------------------------ operating points
def rule_decisions(S: np.ndarray, hi: np.ndarray, lo: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Provisional alarm and its decision time (ms) of the early-exit rule before 1,800 ms (final threshold +inf: only decisions at the first five checkpoints)."""
    from crashguard.early import early_decisions

    alarm, t = early_decisions(S, hi, lo, np.inf)  # with the final threshold at +inf an alarm can only be decided at a checkpoint before 1,800 ms
    return alarm, t


def candidate_rules(Sv: np.ndarray, yv_trig: np.ndarray, full_v: list, yv_full: np.ndarray, base_rule: dict, grid: str) -> list[dict]:
    """The grid of ``early.py`` (A_HI x B_LO) as (hi, lo) vectors; the subsets of the development items keep one of the two values at the baseline rule's."""
    from crashguard.detector_extra import threshold_for_fpr
    from crashguard.early import A_HI, B_LO

    pos = yv_trig == 1
    out = []
    a_list = A_HI if grid in ("full", "a_hi") else (base_rule["a_hi"],)
    b_list = B_LO if grid in ("full", "b_lo") else (base_rule["b_lo"],)
    for a_hi in a_list:
        if a_hi is None:
            continue
        for b_lo in b_list:
            if b_lo is None:
                continue
            hi = np.array([threshold_for_fpr(yv_full, full_v[k], a_hi) for k in range(5)])
            lo = np.array([np.quantile(Sv[pos, k], b_lo) if b_lo > 0 else Sv[pos, k].min() for k in range(5)])
            out.append(dict(a_hi=a_hi, b_lo=b_lo, hi=hi, lo=lo))
    return out


def choose_point(prm: L5Params, Sv, yv_trig, full_v, yv_full, frame_v, ids_v, base_rule: dict, F_alarm_v: np.ndarray, delays: dict, seed: int) -> dict:
    """On validation: among the candidate rules whose provisional false-alarm rate (all non-crash events) is within the budget, the one with the lowest 90th percentile of the time to awareness."""
    from crashguard.early import scatter

    y = frame_v.y.to_numpy()
    crash = y == 1
    n_neg = int((y == 0).sum())
    allowed = int(np.floor(prm.alpha * n_neg))
    best = None
    d_f, d_a = sample_draws(delays, int(crash.sum()), seed)
    for c in candidate_rules(Sv, yv_trig, full_v, yv_full, base_rule, prm.grid):
        prov_t, t_t = rule_decisions(Sv, c["hi"], c["lo"])
        prov = scatter(frame_v, ids_v, prov_t.astype(float)) > 0.5
        tms = scatter(frame_v, ids_v, t_t)
        if int((prov & (y == 0)).sum()) > allowed:
            continue
        T = time_to_awareness(prov[crash], F_alarm_v[crash], np.maximum(tms[crash], 0.0), d_f, d_a)
        obj = p90(T, prm.objective == "conditional")
        key = (round(obj, 9) if np.isfinite(obj) else 1e9, 0 if c["a_hi"] == base_rule["a_hi"] and c["b_lo"] == base_rule["b_lo"] else 1)
        if best is None or key < best["key"]:
            best = dict(key=key, rule=c, obj=obj)
    return best


# ------------------------------------------------------------------------------------------------ data access
def load_all(seed: int = SEED):
    from crashguard import r5_det as D

    fr = D.load_frames()
    det = D.fit_seed(seed, fr)
    return fr, det


def baseline_rule(fr: dict, det: dict, alpha: float) -> dict:
    from crashguard import r5_l2 as L2

    return L2.baseline_arms(SEED, alpha, fr, det)


def arm_alarms(rule: dict, fr: dict, det: dict, split: str, base: dict) -> dict:
    """Provisional alarm, its decision time and the confirm alarm of an arm on validation or test (all events of the frame)."""
    from crashguard.early import scatter

    frame, ids, S = (fr["va"], det["ids_va"], det["Sv"]) if split == "va" else (fr["te"], det["ids_te"], det["St"])
    prov_t, t_t = rule_decisions(S, rule["hi"], rule["lo"])
    F = (base["F_va"] if split == "va" else base["F_te"]) >= base["thr_f"]
    return dict(prov=scatter(frame, ids, prov_t.astype(float)) > 0.5, tms=np.maximum(scatter(frame, ids, t_t), 0.0), conf=F)


def delays_for(model: str, role: str, links: dict | None = None) -> dict:
    """Delay samples of one link model for the role ``dev`` or ``held``."""
    if model == "custom":
        return delays_custom(4201 if role == "dev" else 4202)
    if model == "ns3":
        return delays_ns3(DEV_NS3_SEEDS if role == "dev" else HELD_NS3_SEEDS, OUT / role, DEV_EVENTS if role == "dev" else None)
    return delays_loed(links, 0 if role == "dev" else 1, 4301 if role == "dev" else 4302)


def _links() -> dict:
    return pickle.loads((ROOT / "data" / "processed" / "r3_t1_links.pkl").read_bytes())


def make_dev_events() -> None:
    """Event table (E F y tE, as ``pp_r3_ns3.make_events``) of the triggered VALIDATION events under the baseline rule at the 1% target: the traffic mix of the development ns-3 runs."""
    from crashguard.early import early_decisions, scatter

    fr, det = load_all()
    base = baseline_rule(fr, det, 0.01)
    va = fr["va"]
    alarm, t = early_decisions(det["Sv"], base["rule"]["hi"], base["rule"]["lo"], base["rule"]["t_f"])
    F = scatter(va, det["ids_va"], det["Sv"][:, -1]) >= base["thr_f"]
    pos = {e: i for i, e in enumerate(va.event_id.to_numpy())}
    with DEV_EVENTS.open("w", newline="\n") as f:
        for k, e in enumerate(det["ids_va"]):
            f.write(f"{int(alarm[k])} {int(F[pos[e]])} {int(det['y_va'][k])} {t[k] / 1000.0:.3f}\n")


def _ns3_runs() -> None:
    from crashguard import pp_r3_ns3 as P1
    from crashguard import r5_l4 as L4

    P1.make_events()
    make_dev_events()
    jobs = []
    for role, seeds in (("dev", DEV_NS3_SEEDS), ("held", HELD_NS3_SEEDS)):
        (OUT / role).mkdir(parents=True, exist_ok=True)
        evf = DEV_EVENTS if role == "dev" else P1.EVENTS
        for s in seeds:
            f = OUT / role / f"sf{SF}_shipped_p{P_LOSS:g}_r3t_{s}.txt"
            a = f"--n={P1.N_VEH} --sf={SF} --p={P_LOSS:g} --radius={P1.RADIUS} --rate={P1.RATE} --duty=0.01 --seed={s} --policy=r3t --events={L4.wsl_path(evf)} --sensShipped=1"
            jobs.append((f, a))
    L4.run_jobs(jobs)


def _dev() -> None:
    from crashguard import r5_common as R5
    from crashguard.early import scatter

    fr, det = load_all()
    links = _links()
    log = []
    dl = {m: delays_for(m, "dev", links) for m in LINK_MODELS}
    for it, prm in enumerate(ITERATIONS):
        base = baseline_rule(fr, det, prm.alpha)
        va = fr["va"]
        crash = va.y.to_numpy() == 1
        e = dict(iteration=it, params=asdict(prm), models={})
        for m in LINK_MODELS:
            full_v = [scatter(va, det["ids_va"], det["Sv"][:, k]) for k in range(6)]
            F_v = base["F_va"] >= base["thr_f"]
            best = choose_point(prm, det["Sv"], det["y_va"], full_v, va.y.to_numpy(), va, det["ids_va"], base["rule"], F_v, dl[m], SEED)
            a_b = arm_alarms(base["rule"], fr, det, "va", base)
            d_f, d_a = sample_draws(dl[m], int(crash.sum()), SEED)
            T_b = time_to_awareness(a_b["prov"][crash], a_b["conf"][crash], a_b["tms"][crash], d_f, d_a)
            cond = prm.objective == "conditional"
            e["models"][m] = dict(val_p90_base=p90(T_b, cond), val_p90_new=best["obj"] if best else float("nan"), val_reduction=1 - best["obj"] / p90(T_b, cond) if best else float("nan"), a_hi=best["rule"]["a_hi"] if best else None, b_lo=best["rule"]["b_lo"] if best else None)
        e["mean_reduction"] = float(np.nanmean([v["val_reduction"] for v in e["models"].values()]))
        log.append(e)
        print(it, asdict(prm), {m: (round(v["val_reduction"], 4), v["a_hi"], v["b_lo"]) for m, v in e["models"].items()}, flush=True)
    (R5.TABLES / "r5_l5_dev_log.json").write_text(json.dumps(log, indent=1, default=float), encoding="utf-8")
    best = max(range(len(log)), key=lambda i: (round(log[i]["mean_reduction"], 9), -i))
    (R5.TABLES / "r5_l5_dev_choice.json").write_text(json.dumps(dict(chosen=best, params=log[best]["params"], rule="V16 7.3: highest mean validation reduction over the link models; ties go to the earlier (smaller) iteration"), indent=1), encoding="utf-8")
    print("chosen iteration", best)


def _freeze() -> None:
    from crashguard import r5_common as R5

    ch = json.loads((R5.TABLES / "r5_l5_dev_choice.json").read_text(encoding="utf-8"))
    d = R5.freeze_entry("l5", ["src/crashguard/r5_l5.py", "src/crashguard/r5_l2.py", "src/crashguard/r5_det.py", "src/crashguard/early.py", "src/crashguard/lora.py", "src/crashguard/packet.py", "src/crashguard/pp_r3_ns3.py", "src/crashguard/r3_t1_extract.py", "src/crashguard/ar_r3.py"], ch["params"],
                        ["data/processed/r5_det_seed42.pkl", "data/processed/r3_t1_links.pkl"])
    print("frozen l5", d["params_sha256"][:16])


def evaluate_model(model: str, prm: L5Params, fr: dict, det: dict, base: dict, links: dict | None, h0: np.ndarray) -> dict:
    """Held-out evaluation of one link model: the point is chosen on validation with the development delays, then compared with the baseline on HALF0 events with the held-out delays."""
    from crashguard.early import scatter

    va, te = fr["va"], fr["te"]
    full_v = [scatter(va, det["ids_va"], det["Sv"][:, k]) for k in range(6)]
    F_v = base["F_va"] >= base["thr_f"]
    dev_d = delays_for(model, "dev", links)
    best = choose_point(prm, det["Sv"], det["y_va"], full_v, va.y.to_numpy(), va, det["ids_va"], base["rule"], F_v, dev_d, SEED)
    held_d = delays_for(model, "held", links)
    crash = (te.y.to_numpy() == 1) & h0
    a_b = arm_alarms(base["rule"], fr, det, "te", base)
    a_n = arm_alarms(best["rule"], fr, det, "te", base)
    d_f, d_a = sample_draws(held_d, int(crash.sum()), SEED)
    T_b = time_to_awareness(a_b["prov"][crash], a_b["conf"][crash], a_b["tms"][crash], d_f, d_a)
    T_n = time_to_awareness(a_n["prov"][crash], a_n["conf"][crash], a_n["tms"][crash], d_f, d_a)
    tied = is_tied(T_b, T_n)
    cond = tied  # V16 7.2: the conditional statistic only when both arms are at the cap (the objective item of 7.3 steers development only)
    out = reduction_boot(T_b, T_n, cond)
    out.update(tied_at_cap=tied, conditional=cond, label=held_d["label"], a_hi=best["rule"]["a_hi"], b_lo=best["rule"]["b_lo"], n_crash=int(crash.sum()), share_aware_base=float((T_b < CAP_S).mean()), share_aware_new=float((T_n < CAP_S).mean()),
               fa_prov_base=float((a_b["prov"] & (te.y.to_numpy() == 0) & h0).sum() / max(int(((te.y.to_numpy() == 0) & h0).sum()), 1)), fa_prov_new=float((a_n["prov"] & (te.y.to_numpy() == 0) & h0).sum() / max(int(((te.y.to_numpy() == 0) & h0).sum()), 1)))
    out["criterion_met"] = criterion_met(out["pt"], out["lo"])
    return out


def criterion_met(pt: float, lo: float) -> bool:
    """H-L5 per link model: reduction of at least 0.10 with a lower 95% limit above 0."""
    return bool(pt >= 0.10 and lo > 0)


def is_tied(t_base: np.ndarray, t_new: np.ndarray) -> bool:
    """The 90th percentile is the cap in both arms (recall below 90%): the conditional statistic is used instead."""
    return bool(p90(t_base) >= CAP_S and p90(t_new) >= CAP_S)


def second_smallest(ps: list[float]) -> float:
    return float(sorted(ps)[1])


def _held() -> None:
    from crashguard import r5_common as R5

    prm = L5Params(**R5.check_frozen("l5"))
    fr, det = load_all()
    links = _links()
    base = baseline_rule(fr, det, prm.alpha)
    R5.ensure_split_hashes(fr["te"].event_id.to_numpy())
    h0 = R5.halves(fr["te"].event_id.to_numpy()) == 0
    rec = R5.Rec("r5.l5.", "src/crashguard/r5_l5.py", "MEASURED_SOFTWARE")
    res = {}
    for m in LINK_MODELS:
        res[m] = evaluate_model(m, prm, fr, det, base, links, h0)
        for k, v in res[m].items():
            if k in ("label",):
                rec.add(f"held.{m}.label", v, "text", "link-model label")
            elif isinstance(v, bool):
                rec.add(f"held.{m}.{k}", int(v), "bool")
            elif isinstance(v, (int, float)):
                rec.add(f"held.{m}.{k}", v, "p" if k == "p" else ("count" if k in ("n", "n_crash") else ("s" if k.startswith("p90") else "fraction")))
    nmet = sum(int(r["criterion_met"]) for r in res.values())
    p2 = second_smallest([r["p"] for r in res.values()])
    rec.add("hL5.n_models_met", nmet, "count", "link models in which the reduction is at least 0.10 with a lower 95% limit above 0")
    rec.add("hL5.criterion_met", int(nmet >= 2), "bool", "at least two of the three link models")
    rec.add("hL5.p", p2, "p", "second smallest of the three one-sided bootstrap p-values (two-of-three rule)")
    rec.write()
    print(json.dumps({m: {k: v for k, v in r.items() if k in ("pt", "lo", "hi", "p", "p90_base", "p90_new", "tied_at_cap", "criterion_met", "a_hi", "b_lo")} for m, r in res.items()}, indent=1, default=float))


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"delays": _ns3_runs, "dev": _dev, "freeze": _freeze, "held": _held}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
