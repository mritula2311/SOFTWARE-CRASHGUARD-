
#include <stdio.h>
#include "severity.h"
int main(int argc, char **argv) {
    FILE *in = fopen(argv[1], "rb"); FILE *out = fopen(argv[2], "wb");
    static float acc[CGS_MAX_N][3], gyro[CGS_MAX_N][3];
    int n = 280, trig = 100;
    while (fread(acc, sizeof(float), n * 3, in) == (size_t)(n * 3) && fread(gyro, sizeof(float), n * 3, in) == (size_t)(n * 3)) {
        cgs_result_t r;
        float o[16];
        if (cg_severity(acc, gyro, n, trig, 100.0f, &r)) return 2;
        o[0] = r.dvx_kmh; o[1] = r.dvy_kmh; o[2] = r.dv_res_kmh; o[3] = r.asi; o[4] = r.thiv_kmh; o[5] = r.pulse_ms; o[6] = r.peak_pulse_g;
        o[7] = r.mean_pulse_g; o[8] = r.roll_deg; o[9] = r.pitch_deg; o[10] = (float)r.severity_class; o[11] = (float)r.rollover; o[12] = (float)r.thiv_hit;
        o[13] = r.tilt_deg; o[14] = r.tilt_corrected_deg; o[15] = (float)r.roll_corrected_applied;
        fwrite(o, sizeof(float), 16, out);
    }
    fclose(in); fclose(out); return 0;
}
