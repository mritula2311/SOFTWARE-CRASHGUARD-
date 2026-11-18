/* Round 7 H-R7-B1: resolution time of the pseudonym at the base, C build of the routine of src/crashguard/r7_pseudo.py (hash index on the pseudonym, tag check per candidate, window advance).
 * usage: cg_r7_bench vehicles window L frames reps    prints one line per repetition: mean seconds per frame. "vector" prints the pseudonym of a fixed key for the cross check with Python. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "cg_r7.h"
#include "../firmware_rd/cg_rd.h"

typedef struct { uint32_t key; int32_t veh; uint32_t ctr; int used; } ent_t;
static ent_t *tab; static size_t tabn;
static uint8_t (*keys)[32]; static uint32_t *last_c, *top_c;
static int Lg, mg;

static uint32_t pkey(const uint8_t *p) { uint32_t k = 0; for (int i = 0; i < Lg; i++) k = (k << 8) | p[i]; return k; }
static void put(uint32_t key, int veh, uint32_t ctr)
{
    size_t h = ((uint64_t)key * 2654435761u) & (tabn - 1);
    while (tab[h].used) h = (h + 1) & (tabn - 1);
    tab[h].used = 1; tab[h].key = key; tab[h].veh = veh; tab[h].ctr = ctr;
}
static void extend(int v, uint32_t upto)
{
    uint8_t p[8];
    for (uint32_t c = top_c[v] + 1; c <= upto; c++) { cg_r7_pseudonym(keys[v], 1, c, Lg, p); put(pkey(p), v, c); }
    if (upto > top_c[v]) top_c[v] = upto;
}
static int resolve(const uint8_t *frame, size_t n)
{
    uint32_t key = pkey(frame + 1);
    size_t h = ((uint64_t)key * 2654435761u) & (tabn - 1);
    while (tab[h].used)
    {
        ent_t *e = &tab[h];
        if (e->key == key && e->ctr > last_c[e->veh])
        {
            uint8_t t[32], m[256];
            memcpy(m, frame, n - 8); m[n - 8] = 0; m[n - 7] = 0; m[n - 6] = 0; m[n - 5] = 1; /* boot = 1 (big endian) */
            m[n - 4] = (uint8_t)(e->ctr >> 24); m[n - 3] = (uint8_t)(e->ctr >> 16); m[n - 2] = (uint8_t)(e->ctr >> 8); m[n - 1] = (uint8_t)e->ctr;
            cg_hmac_sha256(keys[e->veh], 32, m, n, t);
            if (memcmp(t, frame + n - 8, 8) == 0) { last_c[e->veh] = e->ctr; extend(e->veh, e->ctr + mg); return e->veh; }
        }
        h = (h + 1) & (tabn - 1);
    }
    return -1;
}
static double now(void) { struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts); return ts.tv_sec + ts.tv_nsec * 1e-9; }

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "vector") == 0)
    {
        uint8_t k[32], p[8];
        for (int i = 0; i < 32; i++) k[i] = (uint8_t)i;
        cg_r7_pseudonym(k, 7, 9, 4, p);
        printf("%02x%02x%02x%02x\n", p[0], p[1], p[2], p[3]);
        return 0;
    }
    int n = atoi(argv[1]); mg = atoi(argv[2]); Lg = atoi(argv[3]); int frames = atoi(argv[4]), reps = atoi(argv[5]);
    keys = malloc((size_t)n * 32); last_c = calloc(n, 4); top_c = calloc(n, 4);
    uint32_t *ctr = calloc(n, 4);
    srand(42);
    for (int v = 0; v < n; v++) for (int i = 0; i < 32; i++) keys[v][i] = (uint8_t)rand();
    size_t flen = 1 + Lg + 8 + 8;
    uint8_t *fr = malloc((size_t)frames * flen); int *who = malloc((size_t)frames * sizeof(int));
    for (int i = 0; i < frames; i++)
    {
        int v = rand() % n; who[i] = v;
        ctr[v] += 1 + ((rand() % 10 == 0) ? 1 + rand() % (mg - 1) : 0);
        uint8_t *f = fr + (size_t)i * flen, t[32];
        f[0] = 1; cg_r7_pseudonym(keys[v], 1, ctr[v], Lg, f + 1);
        for (int j = 0; j < 8; j++) f[1 + Lg + j] = (uint8_t)rand();
        { uint8_t m[256]; memcpy(m, f, flen - 8); m[flen - 8] = 0; m[flen - 7] = 0; m[flen - 6] = 0; m[flen - 5] = 1; m[flen - 4] = (uint8_t)(ctr[v] >> 24); m[flen - 3] = (uint8_t)(ctr[v] >> 16); m[flen - 2] = (uint8_t)(ctr[v] >> 8); m[flen - 1] = (uint8_t)ctr[v];
          cg_hmac_sha256(keys[v], 32, m, flen, t); memcpy(f + flen - 8, t, 8); }
    }
    for (int r = 0; r < reps; r++)
    {
        tabn = 1; while (tabn < (size_t)(n * mg + frames) * 2) tabn <<= 1;
        free(tab); tab = calloc(tabn, sizeof(ent_t));
        memset(last_c, 0, (size_t)n * 4); memset(top_c, 0, (size_t)n * 4);
        for (int v = 0; v < n; v++) extend(v, mg);
        int ok = 0; double t0 = now();
        for (int i = 0; i < frames; i++) ok += (resolve(fr + (size_t)i * flen, flen) == who[i]);
        printf("%.9e %d\n", (now() - t0) / frames, ok);
    }
    return 0;
}
