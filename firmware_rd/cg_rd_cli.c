/* Line-command test harness for the firmware decision path (host build). Reads commands on stdin, writes one result line per command. Doubles travel as C99 hex floats (%a) so that the comparison with the
 * Python reference is exact. Used by tests/redesign/test_rd_firmware_diff.py and by the ns-3 application is NOT this file (the ns-3 application includes cg_rd.c directly). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cg_rd.h"

static int unhex(const char *s, uint8_t *out, size_t max)
{
    size_t n = strlen(s) / 2, i;
    if (n > max) n = max;
    for (i = 0; i < n; i++) {
        unsigned v = 0;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) v = 0;
        out[i] = (uint8_t)v;
    }
    return (int)n;
}

static void hexout(const uint8_t *p, size_t n)
{
    size_t i;
    for (i = 0; i < n; i++) printf("%02x", p[i]);
    printf("\n");
}

static cg_d1_t d1[13];
static uint8_t *blobs[13];
static cg_beta_t beta;
static cg_ring_t ring;
static cg_verifier_t ver;

int main(void)
{
    static char line[4096];
    while (fgets(line, sizeof line, stdin)) {
        char *tok[40];
        int nt = 0;
        char *p = strtok(line, " \r\n");
        while (p && nt < 40) { tok[nt++] = p; p = strtok(NULL, " \r\n"); }
        if (nt == 0) continue;
        { int k; for (k = nt; k < 40; k++) tok[k] = (char *)"0"; } /* missing tokens read as 0 instead of uninitialised pointers */
        if (!strcmp(tok[0], "AIR")) {
            printf("%a\n", cg_airtime_ms(atoi(tok[1]), atoi(tok[2])));
        } else if (!strcmp(tok[0], "ROUND")) {
            printf("%a\n", cg_round_s(atoi(tok[1]), atoi(tok[2])));
        } else if (!strcmp(tok[0], "HMAC")) {
            static uint8_t key[256], msg[600];
            uint8_t out[32];
            int kl = unhex(tok[1], key, sizeof key), ml = unhex(tok[2], msg, sizeof msg);
            cg_hmac_sha256(key, (size_t)kl, msg, (size_t)ml, out);
            hexout(out, 32);
        } else if (!strcmp(tok[0], "SHA")) {
            static uint8_t msg[600];
            uint8_t out[32];
            int ml = unhex(tok[1], msg, sizeof msg);
            cg_sha256(msg, (size_t)ml, out);
            hexout(out, 32);
        } else if (!strcmp(tok[0], "ALERT")) { /* ALERT keyhex version type node event counter ts sev side angle lat lon peak ml rule swmask swfirst roll dv asi reservedhex */
            cg_alert_t a;
            static uint8_t key[256];
            uint8_t out[CG_ALERT_LEN];
            int kl = unhex(tok[1], key, sizeof key);
            memset(&a, 0, sizeof a);
            a.version = (uint8_t)atoi(tok[2]); a.msg_type = (uint8_t)atoi(tok[3]);
            a.node_id = (uint32_t)strtoul(tok[4], 0, 10); a.event_id = (uint32_t)strtoul(tok[5], 0, 10); a.counter = (uint32_t)strtoul(tok[6], 0, 10); a.timestamp_ms = (uint32_t)strtoul(tok[7], 0, 10);
            a.severity = (uint8_t)atoi(tok[8]); a.impact_side = (uint8_t)atoi(tok[9]); a.angle_deg_x10 = (uint16_t)atoi(tok[10]);
            a.lat_e7 = (int32_t)strtol(tok[11], 0, 10); a.lon_e7 = (int32_t)strtol(tok[12], 0, 10);
            a.peak_g_x100 = (uint16_t)atoi(tok[13]); a.ml_prob_x10000 = (uint16_t)atoi(tok[14]);
            a.rule_sev = (uint8_t)atoi(tok[15]); a.sw_mask = (uint8_t)atoi(tok[16]); a.sw_first = (uint8_t)atoi(tok[17]); a.rollover = (uint8_t)atoi(tok[18]);
            a.delta_v_kmh_x100 = (uint16_t)atoi(tok[19]); a.asi_x100 = (uint16_t)atoi(tok[20]);
            unhex(tok[21], a.reserved, 47);
            cg_encode_alert(&a, key, (size_t)kl, out);
            hexout(out, CG_ALERT_LEN);
        } else if (!strcmp(tok[0], "TAGOK")) { /* TAGOK keyhex framehex bodylen */
            static uint8_t key[256], fr[600];
            int kl = unhex(tok[1], key, sizeof key), fl = unhex(tok[2], fr, sizeof fr);
            int bl = atoi(tok[3]);
            printf("%d\n", cg_tag_ok(fr, (size_t)fl, (size_t)bl, key, (size_t)kl));
        } else if (!strcmp(tok[0], "FRESH_RESET")) {
            cg_ring_init(&ring);
            puts("OK");
        } else if (!strcmp(tok[0], "FRESH")) { /* FRESH field seq now W R */
            printf("%d\n", cg_fresh_accept(&ring, atoll(tok[1]), atoll(tok[2]), atoll(tok[3]), atoi(tok[4]), atoi(tok[5])));
        } else if (!strcmp(tok[0], "BETA_RESET")) {
            cg_beta_init(&beta, strtod(tok[1], 0), strtod(tok[2], 0), strtod(tok[3], 0));
            puts("OK");
        } else if (!strcmp(tok[0], "BETA")) {
            cg_beta_update(&beta, atoi(tok[1]));
            printf("%a\n", cg_beta_mean(&beta));
        } else if (!strcmp(tok[0], "BINS")) { /* BINS lhat nheard budget unit */
            printf("%d %d %d\n", cg_loss_bin(strtod(tok[1], 0)), cg_load_bin(atoi(tok[2])), cg_budget_units(strtod(tok[3], 0), strtod(tok[4], 0)));
        } else if (!strcmp(tok[0], "D1LOAD")) { /* D1LOAD sf path */
            int sf = atoi(tok[1]);
            FILE *f = fopen(tok[2], "rb");
            long n;
            if (!f) { printf("ERR open\n"); continue; }
            fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
            free(blobs[sf]);
            blobs[sf] = (uint8_t *)malloc((size_t)n);
            if (fread(blobs[sf], 1, (size_t)n, f) != (size_t)n) { printf("ERR read\n"); fclose(f); continue; }
            fclose(f);
            printf("%d\n", cg_d1_init(&d1[sf], sf, blobs[sf], (size_t)n));
        } else if (!strcmp(tok[0], "D1")) { /* D1 sf cls j tau lhat nheard budget */
            double gap;
            int sf;
            if (cg_d1_lookup(&d1[atoi(tok[1])], atoi(tok[2]), atoi(tok[3]), strtod(tok[4], 0), strtod(tok[5], 0), atoi(tok[6]), strtod(tok[7], 0), &gap, &sf)) printf("%a %d\n", gap, sf);
            else printf("NONE\n");
        } else if (!strcmp(tok[0], "VER_RESET")) {
            uint8_t pk[32];
            unhex(tok[1], pk, 32);
            cg_verifier_init(&ver, pk);
            puts("OK");
        } else if (!strcmp(tok[0], "CLUSTER")) { /* CLUSTER framehex myid myevent now window */
            static uint8_t fr[2048];
            int fl = unhex(tok[1], fr, sizeof fr), reason = 0, act;
            static const char *R[8] = {"short", "bad_signature", "malformed", "other_event", "stale", "replay", "listed", "not_listed"};
            static const char *A[3] = {"ignore", "stop", "defer"};
            act = cg_cluster_check(&ver, fr, (size_t)fl, (uint16_t)atoi(tok[2]), (uint32_t)strtoul(tok[3], 0, 10), strtod(tok[4], 0), atoi(tok[5]), &reason);
            printf("%s %s\n", A[act], R[reason]);
        } else if (!strcmp(tok[0], "DEFER")) { /* DEFER cls now t_event ready u scale */
            printf("%a\n", cg_defer_until(atoi(tok[1]), strtod(tok[2], 0), strtod(tok[3], 0), strtod(tok[4], 0), strtod(tok[5], 0), strtod(tok[6], 0)));
        } else if (!strcmp(tok[0], "RETRYOK")) {
            printf("%d\n", cg_retry_allowed(strtod(tok[1], 0), strtod(tok[2], 0), strtod(tok[3], 0), strtod(tok[4], 0)));
        } else if (!strcmp(tok[0], "D2DEC")) { /* D2DEC listed gate cdefer max */
            static const char *A[3] = {"none", "stop", "defer"};
            printf("%s\n", A[cg_d2_decide(atoi(tok[1]), atoi(tok[2]), atoi(tok[3]), atoi(tok[4]))]);
        } else if (!strcmp(tok[0], "D3SLOTS")) { /* D3SLOTS n_hat m slot */
            printf("%d\n", cg_d3_n_slots(atoi(tok[1]), strtod(tok[2], 0), strtod(tok[3], 0)));
        } else if (!strcmp(tok[0], "D3IDX")) { /* D3IDX epoch id s */
            printf("%d\n", cg_d3_slot_index((uint32_t)strtoul(tok[1], 0, 10), (uint16_t)atoi(tok[2]), atoi(tok[3])));
        } else if (!strcmp(tok[0], "D3ALT")) {
            printf("%d\n", cg_d3_alt_sf(atoi(tok[1]), atoi(tok[2])));
        } else if (!strcmp(tok[0], "D3TIME")) { /* D3TIME thr3 m n_hat id t_min off air deadline_end */
            cg_d3_t pr;
            double out;
            pr.thr3 = atoi(tok[1]); pr.m = strtod(tok[2], 0); pr.alt = 1;
            if (cg_d3_slot_time(&pr, atoi(tok[3]), (uint16_t)atoi(tok[4]), strtod(tok[5], 0), strtod(tok[6], 0), strtod(tok[7], 0), strtod(tok[8], 0), &out)) printf("%a\n", out);
            else printf("NONE\n");
        } else if (!strcmp(tok[0], "D3ACTIVE")) {
            cg_d3_t pr;
            pr.thr3 = atoi(tok[1]); pr.m = 1.0; pr.alt = 1;
            printf("%d\n", cg_d3_active(&pr, atoi(tok[2]), atoi(tok[3])));
        } else {
            printf("ERR unknown\n");
        }
        fflush(stdout);
    }
    return 0;
}
