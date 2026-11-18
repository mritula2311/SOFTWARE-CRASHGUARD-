
#include <stdio.h>
#include <stdlib.h>
#include "crashguard_rf.h"
int main(int argc, char **argv) {
    FILE *in = fopen(argv[1], "rb"); FILE *out = fopen(argv[2], "wb");
    float f[CG_N_FEATURES];
    while (fread(f, sizeof(float), CG_N_FEATURES, in) == CG_N_FEATURES) {
        float p = predict_prob(f);
        fwrite(&p, sizeof(float), 1, out);
    }
    fclose(in); fclose(out); return 0;
}
