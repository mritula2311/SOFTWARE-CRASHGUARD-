
#include <stdio.h>
#include "severity.h"
int main(int argc, char **argv) {
    FILE *in = fopen(argv[1], "rb"); FILE *out = fopen(argv[2], "wb");
    static float acc[CGS_MAX_N][3];
    float trig_f;
    int n = 280;
    while (fread(acc, sizeof(float), n * 3, in) == (size_t)(n * 3) && fread(&trig_f, sizeof(float), 1, in) == 1) {
        cgs_sat_result_t r;
        float o[7];
        if (cg_severity_sat(acc, 0, n, (int)trig_f, 100.0f, &r)) return 2;
        o[0] = r.dv_baseline_kmh; o[1] = r.dv_fill_kmh; o[2] = r.dv_fill_corrected_kmh; o[3] = r.asi_fill; o[4] = r.sat_share; o[5] = (float)r.applied; o[6] = (float)r.saturated;
        fwrite(o, sizeof(float), 7, out);
    }
    fclose(in); fclose(out); return 0;
}
