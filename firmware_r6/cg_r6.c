#include "cg_r6.h"
#include "../firmware_rd/cg_rd.h"
#include "../firmware_export/crashguard_rf.h"

void cg_micro_tag(const uint8_t *key, size_t klen, const uint8_t t1[8], uint8_t b0, uint8_t b1, uint32_t boot, uint8_t tag[CG_MICRO_TAG_LEN])
{
    uint8_t m[15], mac[32];
    m[0] = 'M';
    for (int i = 0; i < 8; i++) m[1 + i] = t1[i];
    m[9] = b0;
    m[10] = b1;
    m[11] = (uint8_t)(boot >> 24);
    m[12] = (uint8_t)(boot >> 16);
    m[13] = (uint8_t)(boot >> 8);
    m[14] = (uint8_t)boot;
    cg_hmac_sha256(key, klen, m, sizeof m, mac);
    for (int i = 0; i < CG_MICRO_TAG_LEN; i++) tag[i] = mac[i];
}

void cg_micro_pack(const uint8_t *key, size_t klen, const uint8_t t1[8], uint8_t b0, uint8_t b1, uint32_t boot, uint8_t frame[CG_MICRO_LEN])
{
    frame[0] = b0;
    frame[1] = b1;
    cg_micro_tag(key, klen, t1, b0, b1, boot, frame + 2);
}

int cg_micro_verify(const uint8_t *key, size_t klen, const uint8_t t1[8], const uint8_t frame[CG_MICRO_LEN], uint32_t boot)
{
    uint8_t tag[CG_MICRO_TAG_LEN];
    uint8_t d = 0;
    cg_micro_tag(key, klen, t1, frame[0], frame[1], boot, tag);
    for (int i = 0; i < CG_MICRO_TAG_LEN; i++) d |= (uint8_t)(tag[i] ^ frame[2 + i]);
    return d == 0;
}

float cg_forest(const float f[14])
{
    return predict_prob(f);
}
