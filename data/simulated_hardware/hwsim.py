"""CrashGuard simulated hardware logs (SIMULATED, not measured). Seeded, stdlib+numpy.
Schemas follow the repository's sensor_logs / protocol_logs files. Every constant below is an
ASSUMPTION (datasheet-typical values recalled, not opened in this session) and is listed in README_SIMULATED.md."""
import json, math, os, hmac, hashlib, csv, sys
import numpy as np
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
SEED = 20261114
rng = np.random.default_rng(SEED)
FS_INT, FS_OUT = 1000, 100            # internal rate, logged rate (Hz)
ACC_LSB, GYR_LSB = 2048.0, 16.4       # MPU6050 +-16 g, +-2000 dps (LSB per unit)
ACC_ND, GYR_ND = 400e-6, 0.005        # noise density g/rtHz, dps/rtHz
DLPF_HZ = 44.0                        # digital low-pass setting
N_OUT = 300
t_int = np.arange(0, 3.0, 1/FS_INT)

def lowpass(x, fc, fs, order=2):
    # simple zero-phase-free causal Butterworth via bilinear biquad cascade (order 2)
    w = math.tan(math.pi*fc/fs); k = 1+math.sqrt(2)*w+w*w
    b0 = w*w/k; b = [b0, 2*b0, b0]; a = [1, 2*(w*w-1)/k, (1-math.sqrt(2)*w+w*w)/k]
    pad = 300; xp = np.concatenate([np.full(pad, x[0]), x]); y = np.zeros_like(xp)
    y[:2] = xp[:2]
    for i in range(2, len(xp)):
        y[i] = b[0]*xp[i] + b[1]*xp[i-1] + b[2]*xp[i-2] - a[1]*y[i-1] - a[2]*y[i-2]
    return y[pad:]

def half_sine(t0, dur, peak):
    x = np.zeros_like(t_int); m = (t_int>=t0)&(t_int<t0+dur)
    x[m] = peak*np.sin(math.pi*(t_int[m]-t0)/dur); return x

def ring(t0, f, zeta, amp):
    x = np.zeros_like(t_int); m = t_int>=t0; tt = t_int[m]-t0
    x[m] = amp*np.exp(-zeta*2*math.pi*f*tt)*np.sin(2*math.pi*f*tt); return x

def sense(acc_true, gyr_true):
    """acc_true (3,N) g incl. gravity, gyr_true (3,N) dps -> logged rows via sensor model."""
    bias_a = rng.normal(0, 0.03, (3,1)); bias_g = rng.normal(0, 0.6, (3,1))
    na = rng.normal(0, ACC_ND*math.sqrt(FS_INT/2), acc_true.shape)
    ng = rng.normal(0, GYR_ND*math.sqrt(FS_INT/2), gyr_true.shape)
    a = np.array([lowpass(acc_true[i]+bias_a[i]+na[i], DLPF_HZ, FS_INT) for i in range(3)])
    g = np.array([lowpass(gyr_true[i]+bias_g[i]+ng[i], DLPF_HZ, FS_INT) for i in range(3)])
    a = np.clip(a, -16, 16); g = np.clip(g, -2000, 2000)
    a = np.round(a*ACC_LSB)/ACC_LSB; g = np.round(g*GYR_LSB)/GYR_LSB      # quantisation
    idx = np.arange(0, N_OUT*10, 10)
    return a[:, idx], g[:, idx], acc_true

def sw420(acc_true):
    """6 vibration switches, thresholds drawn per unit; latched 20 ms; 0.3% chatter."""
    hp = acc_true - np.array([lowpass(acc_true[i], 5, FS_INT) for i in range(3)])
    mag = np.sqrt((hp**2).sum(0)); thr = rng.uniform(1.5, 4.0, 6)
    out = []
    for th in thr:
        s = (mag > th).astype(int)
        s = (np.convolve(s, np.ones(20), 'same') > 0).astype(int)
        s |= (rng.random(len(s)) < 0.0003).astype(int)
        out.append(s[np.arange(0, N_OUT*10, 10)])
    return np.array(out)

def write_event(name, scen, label, side, etype, acc_dyn, gyr_dyn, orient=(0, 0, 1)):
    g0 = np.array(orient, float)[:, None]*np.ones((3, len(t_int)))
    a, g, at = sense(g0+acc_dyn, gyr_dyn)
    s = sw420(g0+acc_dyn)
    rows = [[int(i*10), *[round(float(v), 4) for v in a[:, i]], *[round(float(v), 3) for v in g[:, i]], *[int(v) for v in s[:, i]]] for i in range(N_OUT)]
    d = dict(test_id=name, scenario=scen, true_label=label, impact_side=side, event_type=etype,
             start=dict(device_millis_start=0, wall_clock_iso=None),
             columns=['t_ms','ax_g','ay_g','az_g','gx_dps','gy_dps','gz_dps']+[f'sw420_{k}' for k in range(1,7)],
             data_origin="SIMULATED (hwsim.py, seed %d); not measured hardware" % SEED, rows=rows)
    json.dump(d, open(os.path.join(OUT,'sensor_logs',name+'.json'),'w'))
    dyn = np.sqrt(((a - np.array([[0],[0],[1]]))**2).sum(0))
    jerk = np.abs(np.diff(a, axis=1)).max()*FS_OUT
    return dict(test_id=name, scenario=scen, true_label=label, impact_side=side or '', event_type=etype or '',
                peak_dynamic_g=round(float(dyn.max()),4), peak_jerk_g_per_s=round(float(jerk),3),
                peak_angular_velocity_dps=round(float(np.abs(g).max()),3), sw420_triggered_sensor_count=int((s.sum(1)>0).sum()),
                sw420_trigger_sample_count=int(s.sum()))

AX = {'front':(0,-1),'rear':(0,1),'left':(1,1),'right':(1,-1),'vertical':(2,1)}
def crash_event(side):
    ax_i, sgn = AX[side]; peak = float(np.clip(rng.lognormal(math.log(5.0), 0.45), 2.0, 40))
    dur = rng.uniform(0.012, 0.045); t0 = rng.uniform(0.9, 1.3)
    a = np.zeros((3, len(t_int))); a[ax_i] = sgn*half_sine(t0, dur, peak) + ring(t0+dur, rng.uniform(60,140), 0.08, 0.25*peak)*sgn
    for j in range(3):
        if j != ax_i: a[j] += rng.normal(0, 0.12)*half_sine(t0, dur, peak)  # cross-axis coupling
    g = np.zeros((3, len(t_int)))
    for j in range(3): g[j] = rng.normal(0, 25+4*peak)*half_sine(t0, dur*2, 1)
    return a, g, peak

def noncrash(kind):
    a = np.zeros((3, len(t_int))); g = np.zeros((3, len(t_int))); t0 = rng.uniform(0.8,1.4)
    if kind == 'hand_tap':
        p = rng.uniform(1.0, 3.0); ai = rng.integers(0,3); a[ai] = half_sine(t0, rng.uniform(.008,.02), p)*rng.choice([-1,1]) + ring(t0+.01, 90, .1, .2*p)
    elif kind == 'hard_braking':
        p = rng.uniform(0.35, 0.85); ramp = np.clip((t_int-t0)/0.25,0,1)*np.clip((t0+rng.uniform(1,1.6)-t_int)/0.25,0,1)
        a[0] = -p*ramp; g[1] = 6*ramp
    elif kind == 'lift_and_place':
        a[2] = 0.6*np.sin(2*math.pi*(t_int-t0)/rng.uniform(.9,1.6))*((t_int>t0)&(t_int<t0+1.4)) + half_sine(t0+1.5, .03, rng.uniform(1,2.2))
        g[0] = rng.uniform(15,60)*np.sin(2*math.pi*(t_int-t0)/1.3)*((t_int>t0)&(t_int<t0+1.4))
    elif kind == 'ramp_bump':
        p = rng.uniform(1.8, 4.5); a[2] = half_sine(t0, rng.uniform(.04,.09), p)+ring(t0+.07, 12, .15, .4*p); g[1] = rng.normal(0,40)*half_sine(t0,.1,1)
    elif kind == 'rough_driving':
        for j in range(3):
            n = rng.normal(0, 1, len(t_int)); a[j] = lowpass(n, 35, FS_INT)*rng.uniform(.25,.7)*3
        for _ in range(rng.integers(1,4)): a[2] += half_sine(rng.uniform(.3,2.6), rng.uniform(.02,.06), rng.uniform(1.5,3.2))
    return a, g

def toa_ms(pl, sf=7, bw=125e3, cr=1, pre=8, crc=1, h=0):
    ts = 2**sf/bw; de = 1 if ts > 0.016 else 0
    n = 8+max(math.ceil((8*pl-4*sf+28+16*crc-20*h)/(4*(sf-2*de)))*(cr+4), 0)
    return (pre+4.25+n)*ts*1000

NOISE_FLOOR = -174+10*math.log10(125e3)+6   # dBm, 6 dB receiver noise figure
SNR_LIMIT = -7.5                             # SF7 demodulation limit (dB)
PL1M = 20*math.log10(4*math.pi/(3e8/433e6))  # free-space loss at 1 m
def link(d, wall=False, extra=0.0, ptx=10, n=3.0, sigma=3.5):
    pl = PL1M+10*n*math.log10(max(d,1))+rng.normal(0, sigma)+(12 if wall else 0)+extra+3
    rssi = ptx-pl; snr = rssi-NOISE_FLOOR
    snr_rep = float(np.clip(min(snr, 10+rng.normal(0,1.0)), -20, 10)); rssi = max(rssi, -148.0); return rssi, snr, snr_rep
def p_ok(snr): return 1/(1+math.exp(-(snr-SNR_LIMIT)/0.9))

def run_link(run, d, wall, extra, npk=100):
    ta, tk = toa_ms(97), toa_ms(26); recs = []
    for k in range(npk):
        tx0 = 3000+3000*k; ret = 0; t = tx0; deliv = False; last = None
        while True:
            ru, su, sru = link(d, wall, extra); rd, sd, srd = link(d, wall, extra)
            up = rng.random() < p_ok(su); dn = rng.random() < p_ok(sd); last = (ru, sru, rd, srd)
            if up and dn:
                ack = t+ta+rng.uniform(8,16)+tk; deliv = True; break
            if ret >= 3: ack = None; break
            ret += 1; t += 600+rng.uniform(0,40)
        recs.append(dict(packet_no=k+1, tx_start_ms=tx0, ack_rx_ms=None if ack is None else int(round(ack)),
            rssi_dbm_at_base=round(last[0],1), snr_db_at_base=round(last[1],1), rssi_dbm_at_car=round(last[2],1),
            snr_db_at_car=round(last[3],1), retries=ret, delivered=deliv, crc_error=bool((not deliv) and rng.random()<0.3)))
    return dict(run_id=run, distance_m=d, wall_between=wall, extra_attenuation_db=extra,
        environment="SIMULATED log-distance path (n=3.0, shadowing sigma 3.5 dB, +12 dB wall, emulated extra loss)",
        node_height_m=dict(car=0.5, base=1.5), radio=dict(frequency_mhz=433, sf=7, bw_khz=125, cr='4/5', tx_power_dbm=10),
        ack_timeout_ms=600, max_retries=3, alert_payload_bytes=97, ack_payload_bytes=26,
        time_on_air_ms=dict(alert=round(ta,2), ack=round(tk,2)), noise_floor_dbm=round(NOISE_FLOOR,1),
        data_origin="SIMULATED (hwsim.py, seed %d); not measured RF" % SEED, records=recs)

def h5(n=30):
    med = dict(trigger_rule_us=356, feature_extraction_us=2385, forest_inference_us=899, severity_us=670, hmac_sign_us=781, packet_encode_us=188, ack_verify_us=688)
    recs = [dict(run=i+1, **{k: int(v*rng.lognormal(0, 0.08)) for k, v in med.items()}) for i in range(n)]
    return dict(timer="micros() (required for real test)", runs=n, input="modelled 2.8 s window", records=recs,
        compile_report=dict(flash_used_bytes=None, flash_total_bytes=1310720, static_ram_bytes=None, ram_total_bytes=327680),
        data_origin="SIMULATED: medians carried from the earlier placeholder file, lognormal jitter sigma 0.08; NOT a timing measurement")

def tag(key, msg): return hmac.new(key, msg, hashlib.sha256).digest()[:8]
class Base:
    def __init__(s, key, persist=True): s.key, s.last, s.persist = key, 0, persist
    def rx(s, ctr, body, t, key_ok=True):
        if not hmac.compare_digest(t, tag(s.key, ctr.to_bytes(4,'big')+body)): return 'rejected_bad_tag', False
        if ctr <= s.last: return 'rejected_replay_reacked' if ctr == s.last else 'rejected_replay', ctr == s.last
        s.last = ctr; return 'accepted', True
def h4():
    key = b'shared-demo-key-0001'; wrong = b'attacker-key-000000'; recs = []; vt = lambda: int(632*rng.lognormal(0,.08))
    def case(cid, name, fn):
        for a in range(10): recs.append(dict(case_id=cid, scenario=name, attempt=a+1, how_injected="protocol model executed in software (HMAC-SHA256 truncated to 8 B, monotonic counter); no radio", **fn(a), verify_time_us=vt()))
    body = b'sev=3;lat=13.0;lon=80.2'
    def mk(ctr, k=key, b=body): return ctr, b, tag(k, ctr.to_bytes(4,'big')+b)
    def valid(a): B = Base(key); r, ack = B.rx(*mk(a+1)); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=ack, car_stopped_retrying=ack)
    def forged(a): B = Base(key); r, ack = B.rx(*mk(a+1, wrong)); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=False, car_stopped_retrying=False)
    def tamper(a): B = Base(key); c, b, t = mk(a+1); b2 = bytearray(b); b2[4] ^= 1; r, ack = B.rx(c, bytes(b2), t); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=False, car_stopped_retrying=False)
    def replay(a): B = Base(key); B.rx(*mk(a+5)); B.rx(*mk(a+9)); r, ack = B.rx(*mk(a+5)); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=ack, car_stopped_retrying=ack)
    def spoof(a): ctr = a+1; fake = tag(wrong, b'ACK'+ctr.to_bytes(4,'big')); ok = hmac.compare_digest(fake, tag(key, b'ACK'+ctr.to_bytes(4,'big'))); return dict(base_result='n/a (car-side verify)', ack_sent=False, ack_valid_at_car=ok, car_stopped_retrying=ok)
    def reboot_persist(a): B = Base(key, persist=False); B.rx(*mk(a+9)); B.last = 0 if not B.persist else B.last; r, ack = B.rx(*mk(a+5)); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=ack, car_stopped_retrying=ack)
    def ack_lost(a): B = Base(key); B.rx(*mk(a+1)); r, ack = B.rx(*mk(a+1)); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=True, car_stopped_retrying=True)
    def car_reboot(a): B = Base(key); B.rx(*mk(a+10)); r, ack = B.rx(*mk(1)); return dict(base_result=r, ack_sent=ack, ack_valid_at_car=False, car_stopped_retrying=False)
    def flood(a): B = Base(key); B.rx(*mk(1)); res = [B.rx(*mk(1))[0] for _ in range(20)]; return dict(base_result='%d of 20 rejected' % sum(x.startswith('rejected') for x in res), ack_sent=True, ack_valid_at_car=True, car_stopped_retrying=True)
    for cid, nm, fn in [('S01','valid_alert_control',valid),('S02','forged_tag_wrong_key',forged),('S03','tampered_field_one_byte',tamper),('S04','replayed_old_alert',replay),
        ('S05','spoofed_ack_to_car',spoof),('S06','base_rebooted_mid_retry',reboot_persist),('S07','ack_lost_then_retry',ack_lost),('S08','car_rebooted_counter_state',car_reboot),('S09','replay_flood_20_in_10s',flood)]: case(cid, nm, fn)
    return dict(attempts_per_case=10, scenario_list=[r for r in dict.fromkeys(x['scenario'] for x in recs)], records=recs,
        data_origin="SIMULATED protocol model (executed in software, no radio). S06 models a base that does NOT persist its counter, so an old alert is accepted after reboot; S08 shows a car whose counter restarts being rejected (availability cost)")

def h7(n=100):
    ta, tk = toa_ms(97), toa_ms(26); recs = []
    for i in range(n):
        trig = 10000*(i+1); dec = trig+250+rng.normal(8, 1.5)+4  # 250 ms post-trigger window + compute
        sev = rng.choice(['Moderate','Severe','Critical'], p=[.3,.45,.25]); tx0 = dec+rng.uniform(8,22); ret = 0; t = tx0
        while True:
            up = rng.random() < 0.97; dn = rng.random() < 0.97
            if up and dn: break
            if ret >= 3: break
            ret += 1; t += 600+rng.uniform(0,40)
        ok = up and dn; brx = t+ta; back = brx+rng.uniform(9,15)
        recs.append(dict(event_id='H7-%02d' % (i+1), severity_class_sent=str(sev), t_first_sample_over_trigger_ms=trig, t_decision_ms=int(dec), t_tx_start_ms=int(round(tx0)),
            t_tx_done_ms=int(round(t+ta)), t_ack_rx_ms=int(round(back+tk)) if ok else None, retries=ret, base_rx_ms=int(round(brx)), base_ack_tx_ms=int(round(back)), alert_bytes=97, ack_bytes=26))
    return dict(records=recs, data_origin="SIMULATED; 97 % per-direction delivery assumed (a bench-range value), time-on-air from the LoRa formula")

if __name__ == '__main__':
    for d in ('sensor_logs','protocol_logs'): os.makedirs(os.path.join(OUT,d), exist_ok=True)
    summ = []
    for side in AX:
        for k in range(1, 11):
            a, g, pk = crash_event(side); summ.append(write_event(f'H1-{side}-{k:02d}','impact_side','crash',side,None,a,g))
    for kind in ['hand_tap','hard_braking','lift_and_place','ramp_bump','rough_driving']:
        for k in range(1, 11):
            a, g = noncrash(kind); summ.append(write_event(f'H2-{kind}-{k:02d}','crash_vs_noncrash','non_crash',None,kind,a,g))
    with open(os.path.join(OUT,'event_summary.csv'),'w',newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(summ[0])); w.writeheader(); w.writerows(summ)
    for run, d, wall, extra in [('H3-10m-open',10,False,0),('H3-50m-open',50,False,0),('H3-100m-open',100,False,0),('H3-100m-wall',100,True,0),
                                ('H3-edge-30db',100,True,30),('H3-edge-34db',100,True,34),('H3-edge-38db',100,True,38),('H3-edge-42db',100,True,42)]:
        json.dump(run_link(run,d,wall,extra), open(os.path.join(OUT,'protocol_logs',run+'.json'),'w'))
    json.dump(h5(), open(os.path.join(OUT,'protocol_logs','edge_timing_H5.json'),'w'))
    json.dump(h4(), open(os.path.join(OUT,'protocol_logs','security_H4.json'),'w'))
    json.dump(h7(), open(os.path.join(OUT,'protocol_logs','e2e_latency_H7.json'),'w'))
    print('ok', len(summ), 'events')
