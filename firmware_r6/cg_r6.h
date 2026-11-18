/* Round 6 (R6-1, R6-4): micro-confirm tag and the forest wrapper of the embedded decision path. Plain C99, no heap.
 * Micro-confirm tag (PREREGISTRATION_V17 section 3): HMAC-SHA256(K_vehicle, "M" || T1 (8 bytes) || byte0 || byte1 || boot counter (4 bytes, big endian))[:5]. */
#ifndef CG_R6_H
#define CG_R6_H
#include <stddef.h>
#include <stdint.h>

#define CG_MICRO_TAG_LEN 5
#define CG_MICRO_LEN 7

void cg_micro_tag(const uint8_t *key, size_t klen, const uint8_t t1[8], uint8_t b0, uint8_t b1, uint32_t boot, uint8_t tag[CG_MICRO_TAG_LEN]);
/* frame: byte0, byte1, tag(5); returns 1 when the tag matches (compared without early exit) */
int cg_micro_verify(const uint8_t *key, size_t klen, const uint8_t t1[8], const uint8_t frame[CG_MICRO_LEN], uint32_t boot);
void cg_micro_pack(const uint8_t *key, size_t klen, const uint8_t t1[8], uint8_t b0, uint8_t b1, uint32_t boot, uint8_t frame[CG_MICRO_LEN]);
/* mean crash probability of the 15-tree forest for 14 features */
float cg_forest(const float f[14]);
#endif
