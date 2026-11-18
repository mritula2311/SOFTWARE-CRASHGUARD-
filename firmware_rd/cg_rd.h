/* CrashGuard redesign round: firmware decision path (D6). Plain C99, no heap, no floating-point library calls beyond floor/ceil/exp/sqrt-free arithmetic.
 *
 * What is here: LoRa time on air, SHA-256 and HMAC-SHA256, the 97-byte alert frame and its 8-byte tag, the 26-byte ACK tag check, the freshness rule (GTF, time-stamped form), the D1 loss estimate (Beta
 * counters), the D1 lookup table access, the D2 cluster-ACK verification (Ed25519, TweetNaCl) and defer rule, and the D3 slot rule.
 * It mirrors src/crashguard/{lora,packet,ar_r1,rd_policy,rd_d3}.py. The Python functions are the reference: tests/redesign/test_rd_firmware_diff.py checks identical outputs on 10,000 random traces.
 * Doubles are used so that results are bit for bit those of the Python reference (IEEE 754 binary64). On the ESP32 (single-precision FPU) a port would need float or fixed point; that port is NOT_RUN.
 * Not here: the trigger and the severity classifier (firmware_export/severity.h and crashguard_rf.h, checked earlier by scripts/c_checks.sh).
 */
#ifndef CG_RD_H
#define CG_RD_H
#include <stddef.h>
#include <stdint.h>

#define CG_ALERT_LEN 97
#define CG_ALERT_BODY 89
#define CG_ACK_LEN 26
#define CG_ACK_BODY 18
#define CG_TAG_LEN 8
#define CG_SIG_LEN 64
#define CG_CL_HDR 11
#define CG_RING_MAX 512
#define CG_SEEN_MAX 16

/* ---- time on air ------------------------------------------------------------------------------ */
double cg_airtime_ms(int payload_bytes, int sf);
double cg_air_s(int nbytes, int sf);
double cg_round_s(int sf, int nbytes);

/* ---- SHA-256, HMAC ---------------------------------------------------------------------------- */
void cg_sha256(const uint8_t *msg, size_t n, uint8_t out[32]);
void cg_hmac_sha256(const uint8_t *key, size_t klen, const uint8_t *msg, size_t n, uint8_t out[32]);

/* ---- alert and ACK frames --------------------------------------------------------------------- */
typedef struct {
    uint8_t version, msg_type;
    uint32_t node_id, event_id, counter, timestamp_ms;
    uint8_t severity, impact_side;
    uint16_t angle_deg_x10;
    int32_t lat_e7, lon_e7;
    uint16_t peak_g_x100, ml_prob_x10000;
    uint8_t rule_sev, sw_mask, sw_first, rollover;
    uint16_t delta_v_kmh_x100, asi_x100;
    uint8_t reserved[47];
} cg_alert_t;
void cg_encode_alert(const cg_alert_t *a, const uint8_t *key, size_t klen, uint8_t out[CG_ALERT_LEN]);
int cg_tag_ok(const uint8_t *frame, size_t frame_len, size_t body_len, const uint8_t *key, size_t klen); /* 1 = frame_len == body_len + 8 and the tag matches (constant time) */

/* ---- freshness (GTF, time-stamped form): accept iff |field - now| <= W and (field, seq) is not in the ring of the last R accepted entries ---- */
typedef struct {
    int64_t field[CG_RING_MAX], seq[CG_RING_MAX];
    int n, head;
} cg_ring_t;
void cg_ring_init(cg_ring_t *r);
int cg_fresh_accept(cg_ring_t *r, int64_t field, int64_t seq, int64_t now, int W, int R);

/* ---- D1 ---------------------------------------------------------------------------------------- */
typedef struct {
    double n0, l0, forget, a, b;
} cg_beta_t;
void cg_beta_init(cg_beta_t *s, double n0, double l0, double forget);
void cg_beta_update(cg_beta_t *s, int failed);
double cg_beta_mean(const cg_beta_t *s);
int cg_loss_bin(double l_hat);
int cg_load_bin(int n_heard);
int cg_budget_units(double budget_s, double unit_s);

#define CG_J_MAX 8
#define CG_NB_MAX 8
#define CG_NL 8
#define CG_NQ 4
typedef struct {
    int sf0;
    double unit_s;
    int sfs[3];
    int nT[2];             /* time steps of class 2 (Severe) and class 3 (Critical) */
    const uint8_t *A[2];   /* [(J_MAX+1) * nT * NL * NQ * (NB_MAX+1)] action index, 255 = no action */
} cg_d1_t;
int cg_d1_init(cg_d1_t *t, int sf0, const uint8_t *blob, size_t blob_len); /* blob layout of results/firmware: see rd_firmware.write_table */
/* returns 1 and fills gap_s and sf, or 0 when no table-driven attempt fits */
int cg_d1_lookup(const cg_d1_t *t, int cls, int j, double tau_s, double l_hat, int n_heard, double budget_s, double *gap_s, int *sf);
int cg_retry_allowed(double deadline_s, double t_event, double t_start, double airtime);
double cg_defer_until(int cls, double now, double t_event, double ready, double jitter_u, double scale);

enum { CG_IGNORE = 0, CG_STOP = 1, CG_DEFER = 2 };
#ifndef CG_NO_CRYPTO
/* ---- D2: cluster ACK ------------------------------------------------------------------------- */
typedef struct {
    uint8_t pk[32];
    uint8_t seen[CG_SEEN_MAX][CG_SIG_LEN];
    int n, head;
} cg_verifier_t;
enum { CG_R_SHORT = 0, CG_R_BADSIG, CG_R_MALFORMED, CG_R_OTHER_EVENT, CG_R_STALE, CG_R_REPLAY, CG_R_LISTED, CG_R_NOT_LISTED };
void cg_verifier_init(cg_verifier_t *v, const uint8_t pk[32]);
int cg_cluster_check(cg_verifier_t *v, const uint8_t *frame, size_t len, uint16_t my_id, uint32_t my_event, double now_gps_s, int window_s, int *reason);

#endif
/* decision of a vehicle that holds a pending alert when a verified cluster ACK arrives: listed -> stop; not listed -> defer if the overheard rate gate is on and fewer than max_defers defers were made, else nothing */
int cg_d2_decide(int listed, int gate_on, int cdefer, int max_defers);

/* ---- D3 ---------------------------------------------------------------------------------------- */
typedef struct {
    int thr3;
    double m;
    int alt;
} cg_d3_t;
int cg_d3_n_slots(int n_hat, double m, double slot_s);
int cg_d3_slot_index(uint32_t epoch, uint16_t vehicle_id, int s);
int cg_d3_active(const cg_d3_t *p, int n_heard_others, int cls);
int cg_d3_alt_sf(int j, int sf_d1);
int cg_d3_slot_time(const cg_d3_t *p, int n_hat, uint16_t vehicle_id, double t_min, double offset_s, double air_alert_s, double deadline_end, double *out);

#endif
