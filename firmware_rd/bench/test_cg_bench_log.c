/* Host test of the bench logging hooks: prints the header and a few lines in the format that rd_bench.py parses. Build: gcc -o t test_cg_bench_log.c && ./t */
#include <stdio.h>
#include <stdlib.h>

void cg_bench_puts(const char *line) { puts(line); }
unsigned long cg_bench_micros(void) { static unsigned long t = 1000000UL; t += 12345UL; return t; }

#include "cg_bench_log.h"

int main(void)
{
    puts("trial,role,event,t_us,len,sf,rssi,snr,extra");
    cg_bench_set_trial(7);
    CG_LOG_SYNC(5000000UL);
    CG_LOG_TRIGGER(4500);
    CG_LOG_EVT(EV_PROV_TX_START, 24, 7);
    CG_LOG_EVT(EV_PROV_TX_END, 24, 7);
    CG_LOG_RX(EV_PROV_ACK_RX, 26, 7, -91.0, 6.5);
    CG_LOG_EVT(EV_CONFIRM_TX_START, 97, 7);
    return 0;
}
