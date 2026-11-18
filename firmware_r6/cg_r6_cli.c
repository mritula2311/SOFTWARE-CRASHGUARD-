/* host known-answer driver: reads "key_hex t1_hex b0 b1 boot" lines, prints the 7-byte micro frame in hex and the verification result */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cg_r6.h"

static int hex(const char *s, uint8_t *out, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        unsigned v;
        if (sscanf(s + 2 * i, "%2x", &v) != 1) return 0;
        out[i] = (uint8_t)v;
    }
    return 1;
}

int main(void)
{
    char k[200], t[40];
    unsigned b0, b1;
    unsigned long boot;
    while (scanf("%199s %39s %u %u %lu", k, t, &b0, &b1, &boot) == 5) {
        uint8_t key[64], t1[8], fr[CG_MICRO_LEN];
        size_t kl = strlen(k) / 2;
        if (!hex(k, key, kl) || !hex(t, t1, 8)) return 2;
        cg_micro_pack(key, kl, t1, (uint8_t)b0, (uint8_t)b1, (uint32_t)boot, fr);
        for (int i = 0; i < CG_MICRO_LEN; i++) printf("%02x", fr[i]);
        printf(" %d", cg_micro_verify(key, kl, t1, fr, (uint32_t)boot));
        fr[6] ^= 1;
        printf(" %d\n", cg_micro_verify(key, kl, t1, fr, (uint32_t)boot));
    }
    return 0;
}
