/* Round 7 B1: rotating pseudonym of the vehicle id (docs/02_preregistration/PREREGISTRATION_V18.md section 3.1).
 * p = trunc_L(HMAC-SHA256(k_v, "P" || boot (u32 big endian) || ctr (u32 big endian))). Uses cg_hmac_sha256 of firmware_rd/cg_rd.c. Plain C99, no heap.
 * src/crashguard/r7_pseudo.py is the reference; tests/test_r7_pseudo.py checks equal output. */
#ifndef CG_R7_H
#define CG_R7_H
#include <stddef.h>
#include <stdint.h>

#define CG_R7_MAX_L 8
void cg_r7_pseudonym(const uint8_t key[32], uint32_t boot, uint32_t ctr, int L, uint8_t *out);
#endif
