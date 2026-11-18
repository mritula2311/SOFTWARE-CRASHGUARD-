/* Logging hooks for the two-stage alert bench run (docs/08_hardware/R3_BENCH_PROTOCOL.md). Header only. Plain C99 macros over two functions the sketch provides, so that the same header compiles on the ESP32
 * (Arduino core: micros(), Serial) and on a host for the parser test (tests/redesign/test_rd_bench.py compiles a stub of it).
 *
 * One CSV line per event: trial,role,event,t_us,len,sf,rssi,snr,extra . The role is "car" or "base". t_us is the device's own micros() (32 bit, wraps every 71.6 minutes; the parser unwraps it).
 * The wired GPIO sync pulse of the trial is logged with CG_LOG(SYNC) on both devices when the pulse edge interrupt fires: do the logging in the interrupt handler with the captured micros() value, not later.
 *
 * NOT COMPILED FOR THE ESP32 HERE: no ESP32 toolchain is installed in this environment; the host stub test only checks the line format. Check the sketch on the board before the bench run.
 */
#ifndef CG_BENCH_LOG_H
#define CG_BENCH_LOG_H

/* provided by the sketch: write one formatted line to the serial port, and the 32-bit microsecond clock */
extern void cg_bench_puts(const char *line);
extern unsigned long cg_bench_micros(void);

#define CG_ROLE "car" /* set to "base" in the base sketch */

#include <stdio.h>
static int g_cg_trial = 0;
static void cg_bench_set_trial(int t) { g_cg_trial = t; }
static void cg_bench_line(const char *role, const char *ev, unsigned long t_us, int len, int sf, double rssi, double snr, const char *extra)
{
    char b[160];
    snprintf(b, sizeof b, "%d,%s,%s,%lu,%d,%d,%.1f,%.1f,%s", g_cg_trial, role, ev, t_us, len, sf, rssi, snr, extra ? extra : "");
    cg_bench_puts(b);
}

/* Events of the car node: call at the moment the thing happens; for the TX_START / TX_END pairs call immediately before write and in the TX-done callback. */
#define CG_LOG_SYNC(t_us) cg_bench_line(CG_ROLE, "SYNC", (t_us), 0, 0, 0.0, 0.0, "")
#define CG_LOG_TRIGGER(peak_mg) do { char e_[24]; snprintf(e_, sizeof e_, "peak_mg=%d", (int)(peak_mg)); cg_bench_line(CG_ROLE, "TRIGGER", cg_bench_micros(), 0, 0, 0.0, 0.0, e_); } while (0)
#define CG_LOG_EVT(name, len, sf) cg_bench_line(CG_ROLE, (name), cg_bench_micros(), (len), (sf), 0.0, 0.0, "")
#define CG_LOG_RX(name, len, sf, rssi, snr) cg_bench_line(CG_ROLE, (name), cg_bench_micros(), (len), (sf), (rssi), (snr), "")

/* names used by the parser */
#define EV_PROV_TX_START "PROV_TX_START"
#define EV_PROV_TX_END "PROV_TX_END"
#define EV_PROV_ACK_RX "PROV_ACK_RX"
#define EV_CONFIRM_TX_START "CONFIRM_TX_START"
#define EV_CONFIRM_TX_END "CONFIRM_TX_END"
#define EV_CANCEL_TX_START "CANCEL_TX_START"
#define EV_CANCEL_TX_END "CANCEL_TX_END"
#define EV_FINAL_ACK_RX "FINAL_ACK_RX"
#define EV_ACK_TIMEOUT "ACK_TIMEOUT"
#define EV_PROV_RX "PROV_RX"
#define EV_PROV_ACK_TX_START "PROV_ACK_TX_START"
#define EV_PROV_ACK_TX_END "PROV_ACK_TX_END"
#define EV_CONFIRM_RX "CONFIRM_RX"
#define EV_CANCEL_RX "CANCEL_RX"
#define EV_FINAL_ACK_TX_START "FINAL_ACK_TX_START"
#define EV_FINAL_ACK_TX_END "FINAL_ACK_TX_END"

#endif
