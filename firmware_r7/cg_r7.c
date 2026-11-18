#include "cg_r7.h"
#include "../firmware_rd/cg_rd.h"

void cg_r7_pseudonym(const uint8_t key[32], uint32_t boot, uint32_t ctr, int L, uint8_t *out)
{
    uint8_t msg[9], h[32];
    int i;
    msg[0] = 'P';
    for (i = 0; i < 4; i++)
    {
        msg[1 + i] = (uint8_t)(boot >> (24 - 8 * i));
        msg[5 + i] = (uint8_t)(ctr >> (24 - 8 * i));
    }
    cg_hmac_sha256(key, 32, msg, 9, h);
    for (i = 0; i < L && i < CG_R7_MAX_L; i++)
    {
        out[i] = h[i];
    }
}
