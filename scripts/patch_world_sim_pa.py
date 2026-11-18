"""One-off (V7 block A): add the optional protocol features to src/crashguard/world_sim.py. All of them are off unless ``world["pa"]`` is given.

Kept for the audit trail; idempotent (a second run changes nothing). The test tests/test_pa_sim.py shows that the earlier results are reproduced when ``pa`` is absent.
"""
from pathlib import Path

p = Path("src/crashguard/world_sim.py")
s = p.read_text(encoding="utf-8")
if "V7 release (block A)" in s:
    raise SystemExit("already patched")


def rep(a: str, b: str) -> None:
    global s
    assert a in s, a[:80]
    s = s.replace(a, b, 1)


rep("Original docstring:", "V7 release (block A): optional protocol features under ``world[\"pa\"]`` (OS-DR, OS-DR-N, GS-CA, slotted ALOHA and a slot-probability baseline); all off when ``pa`` is absent (tested to reproduce the earlier results exactly).\n\nOriginal docstring:")
rep("import heapq\nimport math\nimport random", "import hashlib\nimport heapq\nimport math\nimport random")
rep("    Lvl = None\n    if WG:", "    Lvl = None\n    Pos: list[tuple[float, float]] = []\n    if WG:")
rep("            x, y = rad * math.cos(th), rad * math.sin(th)\n", "            x, y = rad * math.cos(th), rad * math.sin(th)\n            Pos.append((x, y))\n")
rep("    dyn = cfg.dyn\n    dk = dyn[\"kind\"] if dyn else None", '''    PA = wd.get("pa")  # V7 block A features (None = the earlier model exactly)
    pa_mode = PA["mode"] if PA else None
    rng_pa = random.Random(f"upa|{cfg.n}|{cfg.sf}|{cfg.burst_cars}|{cfg.label}|{cfg.seed}|{cfg.hour}")
    off_pa = [rng_pa.uniform(-PA.get("eps", 0.005), PA.get("eps", 0.005)) for _ in range(cfg.n)] if PA else []
    cell_nodes: dict = {}
    link_cache: dict = {}
    dyn = cfg.dyn
    dk = dyn["kind"] if dyn else None''')
rep("def new_alert(node: int, t0: float, sev: int, true: int, t_dec: float, kind: str, cancel_after: float | None, pk: int | None = None):",
    "def new_alert(node: int, t0: float, sev: int, true: int, t_dec: float, kind: str, cancel_after: float | None, pk: int | None = None, cell=None):")
rep("flash_acked=False, id=len(alerts) + 1,", "flash_acked=False, cell=cell, suppressed=False, id=len(alerts) + 1,")
rep('''    if cfg.burst:
        for node in rng_arr.sample(range(cfg.n), min(cfg.burst_cars, cfg.n)):
            k = int(crit_idx[rng_arr.randrange(len(crit_idx))]) if len(crit_idx) else 0
            new_alert(node, 600.0 + rng_arr.random() * 10.0, int(ap[k]), int(tp[k]), float(cpool[rng_arr.randrange(len(cpool))]), "crash", None, k)''',
    '''    if cfg.burst:
        bnodes = rng_arr.sample(range(cfg.n), min(cfg.burst_cars, cfg.n))
        cell_nodes["burst"] = bnodes
        for node in bnodes:
            k = int(crit_idx[rng_arr.randrange(len(crit_idx))]) if len(crit_idx) else 0
            new_alert(node, 600.0 + rng_arr.random() * 10.0, int(ap[k]), int(tp[k]), float(cpool[rng_arr.randrange(len(cpool))]), "crash", None, k, "burst")''')
rep("    def try_node(i, now):", '''    def node_link(i: int, j: int, sf: int) -> bool:
        """Can node j decode a frame of node i at spreading factor sf (A-2): path loss and shadowing as for the gateway link; no capture."""
        if i == j:
            return False
        key = (min(i, j), max(i, j), sf)
        if key not in link_cache:
            if not Pos:
                link_cache[key] = True
            else:
                rr = random.Random(f"unn|{cfg.n}|{cfg.label}|{cfg.seed}|{cfg.hour}|{key[0]}|{key[1]}")
                d = max(math.hypot(Pos[i][0] - Pos[j][0], Pos[i][1] - Pos[j][1]), 10.0)
                lv = WG.get("ptx_dbm", 14.0) - WG.get("extra_loss_db", 10.0) - (WG.get("pl0_db", 25.0) + 10.0 * WG.get("n_exp", 3.0) * math.log10(d)) + rr.gauss(0.0, WG.get("sigma_sh_db", 6.0))
                link_cache[key] = lv >= sens[sf]
        return link_cache[key]

    def pa_next_slot(i, a, now):
        """GS-CA, slotted ALOHA and the slot-probability baseline (A-4): the next slot on the GPS epoch grid; the own clock offset shifts the transmission by at most eps."""
        K, guard = int(PA["K"]), PA.get("guard", 0.02)
        slot = air(L_AL, sf0) + guard
        E_s = K * slot
        e0 = math.ceil((now - off_pa[i]) / E_s - 1e-9)
        for e_idx in (e0, e0 + 1):
            if pa_mode == "gsca":
                s_ = int(hashlib.sha256(f"{i}|{a['cell']}|{e_idx}".encode()).hexdigest(), 16) % K
            elif pa_mode == "slot_aloha":
                s_ = rng_pa.randrange(K)
            else:
                u_, acc_ = rng_pa.random(), 0.0
                s_ = K - 1
                for m_, pm_ in enumerate(PA["pvec"]):
                    acc_ += pm_
                    if u_ <= acc_:
                        s_ = m_
                        break
            t_ = e_idx * E_s + s_ * slot + off_pa[i]
            if t_ >= now - 1e-9:
                return t_
        return now

    def pa_gap(a, now, t_end, window):
        """OS-DR retry delay (A1): idle cycles drawn geometrically with per-cycle probability q = min(1, 1/N) (closed-form first order of the renewal model), q = 1 inside the last two cycles before the deadline;
        OS-DR-N divides q by (1 + gamma k), k = distinct same-cell neighbours overheard in the last 10 s."""
        Tc = interval / 0.999
        D = PA.get("D_crit", 10.0) if a["sev"] == 3 else PA.get("D_sev", 30.0)
        q = min(1.0, 1.0 / max(PA.get("N", 1.0), 1.0))
        if pa_mode == "osdr_n":
            hrd = nodes[a["node"]].get("heard", {})
            kk = sum(1 for tt in hrd.values() if now - tt <= 10.0)
            q = q / (1.0 + PA.get("gamma", 0.5) * kk)
        rem = D - (t_end + window - a["arrival"])
        if rem < 2 * Tc:
            q = 1.0
        g = 1 if q >= 1.0 else max(1, math.ceil(math.log(max(rng_pa.random(), 1e-12)) / math.log(1.0 - q)))
        return Tc * (g - 1)

    def try_node(i, now):''')
rep('''            if not win.ok(now, need, cap):
                w = win.wait_until(now, need, cap)
                if w == float("inf"):
                    return
                push(w, "try", i)
                return
            if WLBT and is_fast(a):''', '''            if PA and pa_mode in ("gsca", "slot_aloha", "tamang") and is_fast(a) and a["sev"] == 3 and a["cell"] is not None and kind == "alert":
                st_p = a.get("pa_slot_t")
                if st_p is None or abs(now - st_p) > 1e-6:
                    a["pa_slot_t"] = pa_next_slot(i, a, now)
                    push(a["pa_slot_t"], "try", i)
                    return
            if not win.ok(now, need, cap):
                w = win.wait_until(now, need, cap)
                if w == float("inf"):
                    return
                push(w, "try", i)
                return
            if WLBT and is_fast(a):''')
rep('            a["slot_t"] = None\n            ack_air = air(L_ACK, sf)', '            a["slot_t"] = None\n            a["pa_slot_t"] = None\n            ack_air = air(L_ACK, sf)')
rep('''            a = tx["alert"]
            if tx["kind"] == "cancel":
                continue''', '''            a = tx["alert"]
            if tx["kind"] == "cancel":
                continue
            if PA and pa_mode == "osdr_n" and a is not None and a.get("cell") is not None and tx["kind"] in ("alert", "flash"):
                for j in cell_nodes.get(a["cell"], []):
                    if j != tx["node"] and node_link(tx["node"], j, tx["sf"]) and nodes[j]["free"] <= tx["start"] + 1e-9:
                        nodes[j].setdefault("heard", {})[tx["node"]] = now''')
rep('''            st["ack_sent"] += 1
            reach_dn = (not Lvl) or Lvl[a["node"]][tx["gw"]] >= sens[tx["sf"]]''', '''            st["ack_sent"] += 1
            if PA and pa_mode in ("osdr", "osdr_n") and a.get("cell") is not None:
                for j in cell_nodes.get(a["cell"], []):
                    if j != a["node"] and rng_pa.random() >= cfg.p_down * SF_DECAY ** max(0, tx["sf"] - sf0) and ((not Lvl) or Lvl[j][tx["gw"]] >= sens[tx["sf"]]):
                        push(t_a + ack_air, "ack_heard", (j, a["cell"]))
            reach_dn = (not Lvl) or Lvl[a["node"]][tx["gw"]] >= sens[tx["sf"]]''')
rep('        elif kind == "ack_rx":', '''        elif kind == "ack_heard":
            j, cl = data  # an authenticated gateway ACK for this event cell was decoded by node j: its retries for the cell stop (A1)
            for b in list(nodes[j]["pending"]):
                if b.get("cell") == cl and not b["acked"] and not b["gave_up"] and b["sev"] >= 2:
                    b["suppressed"] = True
                    nodes[j]["pending"].remove(b)
                    st["suppressed"] += 1
                    st["suppressed_unrx"] += int(b["t_rx"] is None)
        elif kind == "ack_rx":''')
rep('''                        a["ready"] = t_end + window + spacing(a) + bo(a["sev"])
                        a["stage"] = "flash" if (S.flash and not a["flash_acked"]) else "alert"''', '''                        a["ready"] = t_end + window + (pa_gap(a, now, t_end, window) if (PA and pa_mode in ("osdr", "osdr_n")) else spacing(a)) + bo(a["sev"])
                        a["stage"] = "flash" if (S.flash and not a["flash_acked"]) else "alert"''')
rep("relay_tx=0, relay_air_s=0.0,", "relay_tx=0, relay_air_s=0.0, suppressed=0, suppressed_unrx=0,")
rep('''    fa = df[df.kind == "fa"]
    out["n_fa_alerts"] = len(fa)''', '''    if "cell" in crash and len(crash):
        crit = crash[crash.true == 3]
        if len(crit):
            ev = [float((g["first"] <= 10).any()) for _, g in crit[crit.cell.notna()].groupby("cell")] + [float(x) for x in (crit[crit.cell.isna()]["first"] <= 10)]
            out["event_reach10_critical"] = float(np.mean(ev)) if ev else np.nan
    out["suppressed_share"] = st["suppressed"] / max(len(df[df.kind == "crash"]), 1)
    fa = df[df.kind == "fa"]
    out["n_fa_alerts"] = len(fa)''')
p.write_text(s, encoding="utf-8", newline="")
print("patched")
