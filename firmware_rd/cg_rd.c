/* CrashGuard redesign round: firmware decision path (D6). See cg_rd.h. Mirrors the Python reference in src/crashguard. */
#include "cg_rd.h"

#include <math.h>
#include <string.h>

#ifndef CG_NO_CRYPTO
#include "tweetnacl.h"
#endif

/* ================================================================================== time on air */
double cg_airtime_ms(int payload_bytes, int sf)
{
    double t_sym = (double)(1 << sf) / 125000.0 * 1000.0;
    int de = (t_sym > 16.0) ? 1 : 0;
    int num = 8 * payload_bytes - 4 * sf + 28 + 16;
    double q = ceil((double)num / (double)(4 * (sf - 2 * de)));
    int np = (int)q * 5;
    if (np < 0) np = 0;
    np += 8;
    return (8 + 4.25) * t_sym + (double)np * t_sym;
}

double cg_air_s(int nbytes, int sf) { return cg_airtime_ms(nbytes, sf) / 1000.0; }

double cg_round_s(int sf, int nbytes)
{
    return cg_air_s(nbytes, sf) + 0.1 + cg_air_s(CG_ACK_LEN, sf) + 0.1;
}

/* ================================================================================== SHA-256 */
static const uint32_t K256[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};

#define ROR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

static void sha_block(uint32_t h[8], const uint8_t *p)
{
    uint32_t w[64], a, b, c, d, e, f, g, hh, t1, t2;
    int i;
    for (i = 0; i < 16; i++) w[i] = ((uint32_t)p[4 * i] << 24) | ((uint32_t)p[4 * i + 1] << 16) | ((uint32_t)p[4 * i + 2] << 8) | (uint32_t)p[4 * i + 3];
    for (i = 16; i < 64; i++) {
        uint32_t s0 = ROR(w[i - 15], 7) ^ ROR(w[i - 15], 18) ^ (w[i - 15] >> 3);
        uint32_t s1 = ROR(w[i - 2], 17) ^ ROR(w[i - 2], 19) ^ (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }
    a = h[0]; b = h[1]; c = h[2]; d = h[3]; e = h[4]; f = h[5]; g = h[6]; hh = h[7];
    for (i = 0; i < 64; i++) {
        t1 = hh + (ROR(e, 6) ^ ROR(e, 11) ^ ROR(e, 25)) + ((e & f) ^ (~e & g)) + K256[i] + w[i];
        t2 = (ROR(a, 2) ^ ROR(a, 13) ^ ROR(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
        hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
}

void cg_sha256(const uint8_t *msg, size_t n, uint8_t out[32])
{
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    uint8_t blk[128];
    size_t i, full = n / 64, rem = n % 64;
    uint64_t bits = (uint64_t)n * 8;
    for (i = 0; i < full; i++) sha_block(h, msg + 64 * i);
    memset(blk, 0, sizeof blk);
    memcpy(blk, msg + 64 * full, rem);
    blk[rem] = 0x80;
    {
        size_t tot = (rem < 56) ? 64 : 128;
        for (i = 0; i < 8; i++) blk[tot - 1 - i] = (uint8_t)(bits >> (8 * i));
        sha_block(h, blk);
        if (tot == 128) sha_block(h, blk + 64);
    }
    for (i = 0; i < 8; i++) {
        out[4 * i] = (uint8_t)(h[i] >> 24); out[4 * i + 1] = (uint8_t)(h[i] >> 16); out[4 * i + 2] = (uint8_t)(h[i] >> 8); out[4 * i + 3] = (uint8_t)h[i];
    }
}

void cg_hmac_sha256(const uint8_t *key, size_t klen, const uint8_t *msg, size_t n, uint8_t out[32])
{
    uint8_t k[64], ipad[64 + 600], opad[64 + 32], inner[32];
    size_t i;
    memset(k, 0, 64);
    if (klen > 64) cg_sha256(key, klen, k); else memcpy(k, key, klen);
    if (n > 600) { memset(out, 0xA5, 32); return; } /* frames are at most 255 bytes; callers also reject such lengths (cg_tag_ok), so this is not a fail-open path */
    for (i = 0; i < 64; i++) { ipad[i] = k[i] ^ 0x36; opad[i] = k[i] ^ 0x5c; }
    memcpy(ipad + 64, msg, n);
    cg_sha256(ipad, 64 + n, inner);
    memcpy(opad + 64, inner, 32);
    cg_sha256(opad, 64 + 32, out);
}

/* ================================================================================== frames */
static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }

void cg_encode_alert(const cg_alert_t *a, const uint8_t *key, size_t klen, uint8_t out[CG_ALERT_LEN])
{
    uint8_t mac[32];
    uint8_t *p = out;
    *p++ = a->version; *p++ = a->msg_type;
    put32(p, a->node_id); p += 4; put32(p, a->event_id); p += 4; put32(p, a->counter); p += 4; put32(p, a->timestamp_ms); p += 4;
    *p++ = a->severity; *p++ = a->impact_side;
    put16(p, a->angle_deg_x10); p += 2; put32(p, (uint32_t)a->lat_e7); p += 4; put32(p, (uint32_t)a->lon_e7); p += 4;
    put16(p, a->peak_g_x100); p += 2; put16(p, a->ml_prob_x10000); p += 2;
    *p++ = a->rule_sev; *p++ = a->sw_mask; *p++ = a->sw_first; *p++ = a->rollover;
    put16(p, a->delta_v_kmh_x100); p += 2; put16(p, a->asi_x100); p += 2;
    memcpy(p, a->reserved, 47); p += 47;
    cg_hmac_sha256(key, klen, out, CG_ALERT_BODY, mac);
    memcpy(out + CG_ALERT_BODY, mac, CG_TAG_LEN);
}

int cg_tag_ok(const uint8_t *frame, size_t frame_len, size_t body_len, const uint8_t *key, size_t klen)
{
    uint8_t mac[32];
    uint8_t diff = 0;
    int i;
    if (body_len > 600 || frame_len != body_len + CG_TAG_LEN) return 0; /* exact length, as the Python reference (trailing bytes are rejected) */
    cg_hmac_sha256(key, klen, frame, body_len, mac);
    for (i = 0; i < CG_TAG_LEN; i++) diff |= (uint8_t)(mac[i] ^ frame[body_len + i]);
    return diff == 0;
}

/* ================================================================================== freshness */
void cg_ring_init(cg_ring_t *r) { memset(r, 0, sizeof *r); }

int cg_fresh_accept(cg_ring_t *r, int64_t field, int64_t seq, int64_t now, int W, int R)
{
    int i;
    int64_t d = field - now;
    if (R < 1 || R > CG_RING_MAX) return 0; /* outside the ring size: reject (the Python reference is only defined for R >= 1) */
    if (d < 0) d = -d;
    if (d > W) return 0;
    for (i = 0; i < r->n; i++)
        if (r->field[i] == field && r->seq[i] == seq) return 0;
    /* ring of the last R accepted entries (oldest dropped): the Python reference keeps ring[-R:] */
    if (r->n < R) {
        r->field[r->n] = field; r->seq[r->n] = seq; r->n++;
    } else {
        memmove(r->field, r->field + 1, (size_t)(R - 1) * sizeof(int64_t));
        memmove(r->seq, r->seq + 1, (size_t)(R - 1) * sizeof(int64_t));
        r->field[R - 1] = field; r->seq[R - 1] = seq; r->n = R;
    }
    return 1;
}

/* ================================================================================== D1 */
void cg_beta_init(cg_beta_t *s, double n0, double l0, double forget)
{
    s->n0 = n0; s->l0 = l0; s->forget = forget;
    s->a = n0 * l0; s->b = n0 * (1.0 - l0);
}

void cg_beta_update(cg_beta_t *s, int failed)
{
    double a0 = s->n0 * s->l0, b0 = s->n0 * (1.0 - s->l0);
    s->a = a0 + (s->a - a0) * s->forget;
    s->b = b0 + (s->b - b0) * s->forget;
    if (failed) s->a += 1.0; else s->b += 1.0;
}

double cg_beta_mean(const cg_beta_t *s) { return s->a / (s->a + s->b); }

int cg_loss_bin(double l)
{
    static const double E[7] = {0.10, 0.20, 0.30, 0.40, 0.55, 0.70, 0.85};
    int i, n = 0;
    for (i = 0; i < 7; i++) if (E[i] <= l) n++;
    return n;
}

int cg_load_bin(int n)
{
    static const int E[3] = {1, 4, 10};
    int i, k = 0;
    for (i = 0; i < 3; i++) if (E[i] <= n) k++;
    return k;
}

int cg_budget_units(double budget_s, double unit_s)
{
    double f = floor(budget_s / unit_s + 1e-9);
    if (f > (double)CG_NB_MAX) f = (double)CG_NB_MAX;
    if (f < 0.0) f = 0.0;
    return (int)f;
}

int cg_d1_init(cg_d1_t *t, int sf0, const uint8_t *blob, size_t blob_len)
{
    size_t per = (size_t)(CG_J_MAX + 1) * CG_NL * CG_NQ * (CG_NB_MAX + 1);
    size_t n2, n3;
    int k;
    if (blob_len < 12 || memcmp(blob, "CGD1", 4) != 0) return 0;
    if (blob[4] != sf0) return 0;
    t->sf0 = sf0;
    t->nT[0] = (int)get16(blob + 8);
    t->nT[1] = (int)get16(blob + 10);
    n2 = per * (size_t)t->nT[0]; n3 = per * (size_t)t->nT[1];
    if (blob_len != 12 + n2 + n3) return 0;
    t->A[0] = blob + 12; t->A[1] = blob + 12 + n2;
    t->unit_s = cg_air_s(CG_ALERT_LEN, sf0);
    for (k = 0; k < 3; k++) t->sfs[k] = (sf0 + k < 12) ? sf0 + k : 12;
    return 1;
}

int cg_d1_lookup(const cg_d1_t *t, int cls, int j, double tau_s, double l_hat, int n_heard, double budget_s, double *gap_s, int *sf)
{
    static const double GAPS[6] = {0.0, 0.25, 0.5, 1.0, 2.0, 3.5};
    double dt = (cls == 2) ? 1.0 : 0.25;
    int ci = (cls == 2) ? 0 : 1, tt, nT = t->nT[ci], jj = (j < CG_J_MAX) ? j : CG_J_MAX, ai;
    size_t idx;
    if (tau_s <= 0) return 0;
    tt = (int)floor(tau_s / dt + 1e-9);
    if (tt > nT - 1) tt = nT - 1;
    idx = ((((size_t)jj * (size_t)nT + (size_t)tt) * CG_NL + (size_t)cg_loss_bin(l_hat)) * CG_NQ + (size_t)cg_load_bin(n_heard)) * (CG_NB_MAX + 1) + (size_t)cg_budget_units(budget_s, t->unit_s);
    ai = t->A[ci][idx];
    if (ai == 255) return 0;
    *gap_s = GAPS[ai / 3];
    *sf = t->sfs[ai % 3];
    return 1;
}

int cg_retry_allowed(double deadline_s, double t_event, double t_start, double airtime)
{
    return t_start + airtime <= t_event + deadline_s + 1e-12;
}

double cg_defer_until(int cls, double now, double t_event, double ready, double jitter_u, double scale)
{
    double d = (cls == 2) ? 4.0 : 1.0, v;
    (void)t_event;
    v = now + d * scale * (0.5 + 0.5 * jitter_u);
    return (ready > v) ? ready : v;
}

#ifndef CG_NO_CRYPTO
/* ================================================================================== D2 */
void cg_verifier_init(cg_verifier_t *v, const uint8_t pk[32])
{
    memset(v, 0, sizeof *v);
    memcpy(v->pk, pk, 32);
}

/* Ed25519 group order L, little endian; a signature with S >= L is rejected (strict verification, as the Python reference's OpenSSL backend does) */
static int s_below_L(const uint8_t *s)
{
    static const uint8_t L[32] = {0xed, 0xd3, 0xf5, 0x5c, 0x1a, 0x63, 0x12, 0x58, 0xd6, 0x9c, 0xf7, 0xa2, 0xde, 0xf9, 0xde, 0x14, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x10};
    int i;
    for (i = 31; i >= 0; i--) {
        if (s[i] < L[i]) return 1;
        if (s[i] > L[i]) return 0;
    }
    return 0;
}

int cg_cluster_check(cg_verifier_t *v, const uint8_t *frame, size_t len, uint16_t my_id, uint32_t my_event, double now_gps_s, int window_s, int *reason)
{
    uint8_t sm[64 + 600], mbuf[64 + 600];
    unsigned long long mlen = 0;
    size_t body_len, i;
    uint32_t ev, fresh;
    int typ, ver, m;
    double d;
    if (len < (size_t)(CG_CL_HDR + CG_SIG_LEN)) { *reason = CG_R_SHORT; return CG_IGNORE; }
    if (len > 255) { *reason = CG_R_MALFORMED; return CG_IGNORE; } /* longer than a LoRa frame */
    body_len = len - CG_SIG_LEN;
    memcpy(sm, frame + body_len, CG_SIG_LEN); /* tweetnacl wants signature || message */
    memcpy(sm + CG_SIG_LEN, frame, body_len);
    if (!s_below_L(sm + 32) || crypto_sign_open(mbuf, &mlen, sm, (unsigned long long)len, v->pk) != 0) { *reason = CG_R_BADSIG; return CG_IGNORE; }
    typ = frame[0]; ver = frame[1]; ev = get32(frame + 2); fresh = get32(frame + 6); m = frame[10];
    if (typ != 4 || ver != 1 || body_len != (size_t)(CG_CL_HDR + 2 * m)) { *reason = CG_R_MALFORMED; return CG_IGNORE; }
    if (ev != my_event) { *reason = CG_R_OTHER_EVENT; return CG_IGNORE; }
    d = now_gps_s - (double)fresh;
    if (d < 0) d = -d;
    if (d > (double)window_s) { *reason = CG_R_STALE; return CG_IGNORE; }
    for (i = 0; i < (size_t)v->n; i++)
        if (memcmp(v->seen[i], frame + body_len, CG_SIG_LEN) == 0) { *reason = CG_R_REPLAY; return CG_IGNORE; }
    if (v->n < CG_SEEN_MAX) {
        memcpy(v->seen[v->n++], frame + body_len, CG_SIG_LEN);
    } else {
        memcpy(v->seen[v->head], frame + body_len, CG_SIG_LEN);
        v->head = (v->head + 1) % CG_SEEN_MAX;
    }
    for (i = 0; i < (size_t)m; i++)
        if (get16(frame + CG_CL_HDR + 2 * i) == my_id) { *reason = CG_R_LISTED; return CG_STOP; }
    *reason = CG_R_NOT_LISTED;
    return CG_DEFER;
}

#endif /* CG_NO_CRYPTO: the ns-3 application compiles only the D1 part */

int cg_d2_decide(int listed, int gate_on, int cdefer, int max_defers)
{
    if (listed) return CG_STOP;
    return (gate_on && cdefer < max_defers) ? CG_DEFER : CG_IGNORE;
}

/* ================================================================================== D3 */
int cg_d3_n_slots(int n_hat, double m, double slot_s)
{
    int s_cap = (int)floor(5.0 / slot_s + 1e-9), s, want;
    if (s_cap > 12) s_cap = 12;
    if (s_cap < 2) s_cap = 2;
    want = (int)ceil((double)n_hat / m - 1e-9);
    if (want < 2) want = 2;
    s = (want < s_cap) ? want : s_cap;
    return s;
}

int cg_d3_slot_index(uint32_t epoch, uint16_t vehicle_id, int s)
{
    uint8_t buf[6], h[32];
    unsigned long r = 0;
    int i;
    put32(buf, epoch); put16(buf + 4, vehicle_id);
    cg_sha256(buf, 6, h);
    for (i = 0; i < 32; i++) r = (r * 256UL + h[i]) % (unsigned long)s;
    return (int)r;
}

int cg_d3_active(const cg_d3_t *p, int n_heard_others, int cls) { return cls == 3 && n_heard_others >= p->thr3; }

int cg_d3_alt_sf(int j, int sf_d1) { return (j % 2 == 0 && j >= 2) ? ((sf_d1 + 1 < 12) ? sf_d1 + 1 : 12) : sf_d1; }

int cg_d3_slot_time(const cg_d3_t *p, int n_hat, uint16_t vehicle_id, double t_min, double offset_s, double air_alert_s, double deadline_end, double *out)
{
    double slot = air_alert_s + 0.02, ep;
    int s = cg_d3_n_slots(n_hat, p->m, slot), k;
    long long e0;
    ep = s * slot;
    e0 = (long long)floor((t_min - offset_s) / ep + 1e-12);
    for (k = 0; k < 3; k++) {
        long long e = e0 + k;
        double t = (double)e * ep + (double)cg_d3_slot_index((uint32_t)(e & 0xFFFFFFFFLL), vehicle_id, s) * slot + offset_s;
        if (t >= t_min - 1e-12) {
            if (t + air_alert_s <= deadline_end + 1e-12) { *out = t; return 1; }
            return 0;
        }
    }
    return 0;
}
