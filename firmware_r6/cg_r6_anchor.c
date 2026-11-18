/* link anchor for the footprint build only: keeps the decision-path functions that an application would call (not a product main) */
#include "cg_r6.h"
#include "../firmware_rd/cg_rd.h"

volatile float cg_sink_f;
volatile int cg_sink_i;

void cg_anchor(const uint8_t *key, size_t klen, const uint8_t t1[8], const float f[14], cg_ring_t *ring)
{
    uint8_t fr[CG_MICRO_LEN], big[CG_ALERT_LEN];
    cg_alert_t a = {0};
    cg_sink_f = cg_forest(f);
    cg_micro_pack(key, klen, t1, 0, 0, 1, fr);
    cg_sink_i = cg_micro_verify(key, klen, t1, fr, 1);
    cg_encode_alert(&a, key, klen, big);
    cg_sink_i += cg_tag_ok(big, CG_ALERT_LEN, CG_ALERT_BODY, key, klen);
    cg_sink_i += cg_fresh_accept(ring, 1, 1, 1, 1, 1);
}

int main(void)
{
    return 0;
}
