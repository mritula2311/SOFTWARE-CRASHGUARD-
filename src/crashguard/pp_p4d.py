"""P4d (EXPLORATORY, no hypothesis; docs/02_preregistration/PREREGISTRATION_V4.md section 4): an int8 tiny 1D CNN on the 280-sample accelerometer window against the forest on AP and flash.

The network (about 1.6 thousand weights) is trained on the triggered training windows, seeds 0 to 4, the epoch with the best validation AP is kept, weights are quantised to int8 (symmetric, per tensor; activations are kept in float in this simulation, so the int8 AP is for int8 WEIGHTS only), thresholds come from validation. Flash (ANALYTICAL) = weights at 1 byte + biases at 4 bytes; code is not counted.
``freeze`` writes the settings file; ``eval`` scores the test split once per seed. MEASURED_SOFTWARE for AP and recall; ANALYTICAL for flash.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from crashguard import boot as B
from crashguard import config as C
from crashguard import pp_common as PC
from crashguard import windows_cache as W
from crashguard.detector_extra import frames_full, threshold_for_fpr
from crashguard.s2_dedup import fast_ap

SEEDS = C.SEEDS
EPOCHS, BATCH, LR = 20, 256, 2e-3
SRC = "results/tables/p4d_cnn.csv"


def net():
    import torch.nn as nn

    return nn.Sequential(nn.Conv1d(3, 8, 7, stride=2, padding=3), nn.ReLU(), nn.Conv1d(8, 16, 5, stride=2, padding=2), nn.ReLU(), nn.Conv1d(16, 16, 3, stride=2, padding=1), nn.ReLU(), nn.AdaptiveMaxPool1d(1), nn.Flatten(), nn.Linear(16, 1))


def windows(df: pd.DataFrame, split: str) -> np.ndarray:
    z = W.load(split, dedup=False)
    pos = {int(e): i for i, e in enumerate(z["event_id"])}
    return (z["acc"][[pos[int(e)] for e in df.event_id.to_numpy()]] / C.MPU_RANGE_G).astype(np.float32).transpose(0, 2, 1)


def quantise_int8(model) -> int:
    """Symmetric per-tensor int8 weights (fake quantisation in place). Returns the flash estimate in bytes (weights 1 byte, biases 4 bytes)."""
    import torch

    flash = 0
    for p_name, p in model.named_parameters():
        if p_name.endswith("weight"):
            s = float(p.detach().abs().max()) / 127.0 + 1e-12
            with torch.no_grad():
                p.copy_(torch.round(p / s).clamp(-127, 127) * s)
            flash += p.numel()
        else:
            flash += 4 * p.numel()
    return flash


def predict(model, X: np.ndarray) -> np.ndarray:
    import torch

    model.eval()
    with torch.no_grad():
        return torch.sigmoid(model(torch.tensor(X)).squeeze(1)).numpy()


def freeze() -> None:
    h = PC.freeze("P4d", dict(epochs=EPOCHS, batch=BATCH, lr=LR, seeds=list(SEEDS), net="conv 3-8 (k7,s2), conv 8-16 (k5,s2), conv 16-16 (k3,s2), global max, linear 16-1", quantisation="int8 weights, symmetric per tensor", note="EXPLORATORY; epoch chosen by validation AP; test split not used"))
    print("freeze", h)


def evaluate() -> None:
    import copy

    import torch

    torch.set_num_threads(8)
    fz = PC.sealed_gate("P4d")
    tr, va, te = frames_full()
    Xtr, Xva, Xte = windows(tr, "train"), windows(va[va.triggered], "validation"), windows(te[te.triggered], "test")
    ytr, yva_t = tr.y.to_numpy().astype(np.float32), va[va.triggered].y.to_numpy()
    yv, yt = va.y.to_numpy(), te.y.to_numpy()
    vt, tt = va.triggered.to_numpy(bool), te.triggered.to_numpy(bool)
    flags = pd.read_csv(C.TABLES / "vz_audit_test_near_dup_flags.csv")
    strict = ~te.event_id.isin(set(flags.event_id[flags.flagged_near_duplicate])).to_numpy()
    S_f, S_q, T_f, T_q = [], [], [], []
    flash = 0
    for seed in SEEDS:
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        m = net()
        opt = torch.optim.Adam(m.parameters(), lr=LR)
        best = (-1.0, None)
        for ep in range(EPOCHS):
            m.train()
            perm = rng.permutation(len(Xtr))
            for i in range(0, len(perm), BATCH):
                b = perm[i : i + BATCH]
                opt.zero_grad()
                torch.nn.functional.binary_cross_entropy_with_logits(m(torch.tensor(Xtr[b])).squeeze(1), torch.tensor(ytr[b])).backward()
                opt.step()
            ap = fast_ap(yva_t, predict(m, Xva))
            if ap > best[0]:
                best = (ap, copy.deepcopy(m))
        for tag, mm, S_, T_ in (("float", best[1], S_f, T_f), ("int8", None, S_q, T_q)):
            if tag == "int8":
                mm = copy.deepcopy(best[1])
                flash = quantise_int8(mm)
            sva = np.full(len(va), -1.0)
            sva[vt] = predict(mm, Xva)
            ste = np.full(len(te), -1.0)
            ste[tt] = predict(mm, Xte)
            S_.append(ste)
            T_.append((threshold_for_fpr(yv, sva, 0.01), threshold_for_fpr(yv, sva, 0.05)))
        print("seed", seed, "val AP", round(best[0], 4), flush=True)
    n_par = sum(p.numel() for p in net().parameters())
    E = PC.PEntries("p4d", SRC)
    E.add("freeze_commit", fz, "commit", "commit of the freeze of P4d (EXPLORATORY, no hypothesis)")
    E.add("n_parameters", int(n_par), "parameters")
    E.add("flash_bytes_int8", int(flash), "bytes", "weights at 1 byte + biases at 4 bytes; code not counted; host arithmetic", "ANALYTICAL")
    sel = PC.freeze  # noqa: F841 - keep the import used
    rows = []
    for sname, which in (("dedup", np.ones(len(te), bool)), ("strict", strict)):
        def stat(idx, which=which):
            s_ = idx[which[idx]]
            yy, t_ = yt[s_], tt[s_]
            pos = yy == 1
            out = {}
            for nm, SS, TT in (("float", S_f, T_f), ("int8", S_q, T_q)):
                out[(nm, "ap")] = float(np.mean([fast_ap(yy[t_], s[s_][t_]) for s in SS]))
                out[(nm, "recall_1pct")] = float(np.mean([(s[s_][pos] >= t[0]).mean() for s, t in zip(SS, TT)]))
                out[(nm, "recall_5pct")] = float(np.mean([(s[s_][pos] >= t[1]).mean() for s, t in zip(SS, TT)]))
            return out

        pt = stat(np.arange(len(te)))
        dr = [stat(i) for i in B._idx(len(te), B.N_BOOT, B.SEED)]
        for k, v in pt.items():
            d = np.array([x[k] for x in dr])
            E.ci(f"{sname}.cnn_{k[0]}.{k[1]}", (v, float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))), "AP" if k[1] == "ap" else "fraction", "EXPLORATORY; 5-seed mean; paired bootstrap over test events", d=5)
            rows.append(dict(set=sname, model=f"cnn_{k[0]}", metric=k[1], value=v))
    E.flush()
    pd.DataFrame(rows).to_csv(C.TABLES / "p4d_cnn.csv", index=False)
    PC.time_log("P4d", "EXPLORATORY int8 CNN scored once per seed; freeze commit " + fz[:8])
    print(pd.DataFrame(rows).round(4).to_string())


if __name__ == "__main__":
    {"freeze": freeze, "eval": evaluate}[sys.argv[1]]()
