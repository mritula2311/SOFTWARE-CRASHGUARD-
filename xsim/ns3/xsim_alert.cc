/*
 * X1.3 cross-simulator scenario S-X for the CrashGuard redesign round (docs/02_preregistration/PREREGISTRATION_V12.md addendum B, section 10.4).
 *
 * One gateway at the centre of a disc of 3,000 m, n vehicles, 97-byte confirmed alerts (84-byte payload + 13 bytes of LoRaWAN overhead), 16-byte unconfirmed heartbeats every 600 s (+-10%), Critical crash events
 * (Poisson at 0.1 per vehicle-hour plus an optional burst of b vehicles at 600 s to 610 s), extra loss p per direction scaled by 0.7 per spreading-factor step above the base, a per-vehicle trailing-hour airtime
 * budget. Channel and sensitivities as in xsim_calib.cc (same as the custom simulator). One invocation = one simulated hour (3,600 s of events, 60 s of horizon).
 *
 * Policies (application level on top of the ns-3 class A end-device MAC with MaxNumbTx = 1):
 *   p1       severity table: hold 5 s (the cancel window), then an immediate retry after every failed round, 12 tries, fixed spreading factor (no flash frame)
 *   quick    hold 0, retry gap 0.3 s, spreading factor + 1 after two failed rounds, 12 tries (no flash frame)
 *   d1       the frozen D1 policy: Beta loss estimate, lookup table (the firmware-path C code in cg_rd.c, compiled here as C++), load index = gateway ACKs overheard in the last 10 s
 *   lorawan  standard LoRaWAN confirmed uplink: the module's own retransmissions (NbTrans = --nbtrans, ACK timeout U(1,3) s), RX1 at 1 s and RX2 at 2 s, no application policy; --adr 1 switches ADR on
 * Receive-window delays: p1, quick and d1 use RX1 = 0.1 s and RX2 = 0.2 s (the custom simulator's 0.1 s processing delay; a local change of the ns-3 source, see docs/03_results/XSIM_BUILD.md); lorawan keeps 1 s and 2 s.
 *
 * Output: lines "EV <vehicle> <t_crash> <delay_s or -1> <burst 0|1>" for every crash event, "DUTY <max trailing-hour airtime of any vehicle (s)> <limit (s)>", "DROPPED <events of a vehicle that still had an alert>".
 */
#include "ns3/core-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/propagation-loss-model.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <deque>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <tuple>
#include <vector>

#define CG_NO_CRYPTO 1
#include "cg_rd.c"

using namespace ns3;
using namespace lorawan;

namespace ns3
{
namespace lorawan
{
extern double g_xsimRx1;
extern double g_xsimRx2;
extern double g_xsimSensDelta[6];
} // namespace lorawan
} // namespace ns3

NS_LOG_COMPONENT_DEFINE("XsimAlert");

static const double SENS_DBM[6] = {-123.0, -126.0, -129.0, -132.0, -134.5, -137.0}; // SF7..SF12, the custom simulator's values (also compiled into the patched ns-3 tables)
static double g_p = 0.0;
static int g_sf0 = 9;
static std::vector<int> g_curSf;                    // spreading factor of the transmission in progress, by node id of the end devices (0..n-1)
static std::map<const MobilityModel*, int> g_idxOf; // mobility model -> vehicle index
static std::vector<double> g_shadow;
static Ptr<UniformRandomVariable> g_lossRv;

/** Path loss is applied by the chained ns-3 model; this adds shadowing (fixed per vehicle), fading (2 dB per packet), the 10 dB vehicle loss and the extra loss p (per direction, 0.7 per SF step). */
class XLoss : public PropagationLossModel
{
  public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("ns3::XLoss").SetParent<PropagationLossModel>().SetGroupName("Propagation").AddConstructor<XLoss>();
        return tid;
    }

    XLoss()
    {
        m_fade = CreateObject<NormalRandomVariable>();
        m_fade->SetAttribute("Mean", DoubleValue(0.0));
        m_fade->SetAttribute("Variance", DoubleValue(4.0));
    }

  private:
    double DoCalcRxPower(double txPowerDbm, Ptr<MobilityModel> a, Ptr<MobilityModel> b) const override
    {
        Ptr<MobilityModel> dev = (a->GetPosition().z < 5.0) ? a : b;
        auto it = g_idxOf.find(PeekPointer(dev));
        int idx = (it == g_idxOf.end()) ? -1 : it->second;
        double sh = (idx >= 0) ? g_shadow[idx] : 0.0;
        double scale = 1.0;
        if (idx >= 0)
        {
            int d = g_curSf[idx] - g_sf0;
            scale = std::pow(0.7, std::max(0, d));
        }
        if (g_p > 0.0 && g_lossRv->GetValue() < g_p * scale)
        {
            return -300.0;
        }
        return txPowerDbm - 10.0 + sh + m_fade->GetValue();
    }

    int64_t DoAssignStreams(int64_t stream) override
    {
        m_fade->SetStream(stream);
        return 1;
    }

    Ptr<NormalRandomVariable> m_fade;
};

enum Policy { P1, QUICK, D1, LORAWAN, NESSA, R3S, R3T, R3A, Z0, L4, R6M };

struct R3Msg
{
    int kind;      // 0 flash, 1 full alert, 2 cancel
    double ready;  // absolute time at which the message may be sent
    int bytes;     // frame length including the 13 bytes of LoRaWAN overhead
    bool confirmed;
    int tries;
};

struct Veh
{
    Ptr<Node> node;
    Ptr<ClassAEndDeviceLorawanMac> mac;
    double x = 0, y = 0;
    bool linkOk = false;
    double busyUntil = 0.0;
    bool active = false;
    double tCrash = 0.0, tRx = -1.0;
    bool burst = false;
    int rounds = 0, tries = 0, sf = 9;
    double lvl = 0.0; // received level of the link at the gateway at the base spreading factor sensitivity scale (dBm, no fading), used by the L4 start-SF estimate
    int startSf = 7;  // L4: the spreading factor the ladder starts at
    bool demoted = false;
    cg_beta_t beta;
    std::deque<std::pair<double, double>> txlog; // application-level log (start, airtime) for the budget
    std::vector<std::pair<double, double>> phylog; // every transmission seen at the PHY (start, airtime), independent scan
    uint32_t addr = 0;
    // R3 (two-stage alert) state, used only by the policies r3s and r3t
    std::deque<R3Msg> q;
    int curEv = -1, curKind = -1;
    bool awaiting = false;
    bool hasConfirm = false; // A1: the event has a confirm frame
    double flashAckT = -1e9; // R6M: time of that acknowledgement (s)
    bool flashAcked = false; // R6M: the provisional frame of the event was acknowledged, so the base holds it in its pending table
};

struct AckRec
{
    double tEnd;
    int dest;
    int id;
    int sf;
};

static std::vector<Veh> g_v;
static std::vector<AckRec> g_acks;
static Policy g_pol = P1;
static double g_limit = 0.0, g_simEnd = 0.0;
static int g_nbTrans = 8, g_dropped = 0;
static cg_d1_t g_d1;
static std::vector<uint8_t> g_blob;
static double g_pDown = 0.0;
static std::map<uint32_t, int> g_addrToIdx;
static Ptr<UniformRandomVariable> g_polRv;
static int g_run = 1;
static double g_nK = 2.0, g_nA = 1.0; // Nessa-style parameters (frozen on the DEV grid of the custom simulator, V12 11.1)
// L4 (V16 section 6; policies z0 and l4): zero-spacing control at a fixed SF, and the SF ladder (start SF from a link-margin estimate, one step up after every g_l4k failed rounds)
static double g_l4M0 = 3.0, g_l4Err = 2.0;
static int g_l4k = 2, g_l4Late = 0, g_l4Duty = 0;
static Ptr<NormalRandomVariable> g_l4Rv;

struct Ev
{
    int v;
    double t;
    bool burst;
    double delay;
};
static std::vector<Ev> g_ev;

static double Used(const Veh& v, double now)
{
    double u = 0.0;
    for (auto& e : v.txlog)
    {
        if (e.first > now - 3600.0 + 1e-9)
        {
            u += e.second;
        }
    }
    return u;
}

static double WaitUntil(const Veh& v, double now, double need)
{
    double t = now;
    std::vector<std::pair<double, double>> l(v.txlog.begin(), v.txlog.end());
    for (size_t i = 0; i <= l.size(); i++)
    {
        double u = 0.0;
        for (auto& e : l)
        {
            if (e.first > t - 3600.0 + 1e-9)
            {
                u += e.second;
            }
        }
        if (u + need <= g_limit + 1e-12)
        {
            return t;
        }
        // the next time an entry leaves the window
        double nxt = 1e18;
        for (auto& e : l)
        {
            if (e.first > t - 3600.0 + 1e-9)
            {
                nxt = std::min(nxt, e.first + 3600.0 + 1e-6);
            }
        }
        t = nxt;
    }
    return 1e18;
}

static double U01(uint64_t a, uint64_t b)
{
    uint64_t z = a * 0x9E3779B97F4A7C15ULL + b * 0xBF58476D1CE4E5B9ULL + (uint64_t)g_run * 0x94D049BB133111EBULL;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    z ^= z >> 31;
    return (double)(z >> 11) / 9007199254740992.0;
}

static int NHeard(int j, double now)
{
    int n = 0;
    for (int k = (int)g_acks.size() - 1; k >= 0; k--)
    {
        const AckRec& a = g_acks[k];
        if (a.tEnd < now - 10.0)
        {
            break;
        }
        if (a.tEnd > now || a.dest == j || !g_v[j].linkOk)
        {
            continue;
        }
        double decay = std::pow(0.7, std::max(0, a.sf - g_sf0));
        if (U01(a.id, j) >= g_pDown * decay)
        {
            n++;
        }
    }
    return n;
}

static bool g_trace = false;
#define TR(...) do { if (g_trace) { std::fprintf(stderr, __VA_ARGS__); std::fputc('\n', stderr); } } while (0)
static void TrySend(int i);

static void Schedule(int i, double t)
{
    double now = Simulator::Now().GetSeconds();
    Simulator::Schedule(Seconds(std::max(t, now) - now), &TrySend, i);
}

static void TrySend(int i)
{
    Veh& v = g_v[i];
    double now = Simulator::Now().GetSeconds();
    if (!v.active)
    {
        return;
    }
    if (now < v.busyUntil - 1e-12)
    {
        Schedule(i, v.busyUntil);
        return;
    }
    double air = cg_air_s(CG_ALERT_LEN, v.sf);
    double w = WaitUntil(v, now, air);
    if (w > now + 1e-12)
    {
        if (w > 1e17)
        {
            return;
        }
        Schedule(i, w);
        return;
    }
    if ((g_pol == Z0 || g_pol == L4) && now + air > v.tCrash + 10.0 + 1e-9)
    {
        v.active = false; // the next transmission would end after the 10 s deadline: the alert is over (V16 section 6.1)
        return;
    }
    g_curSf[i] = v.sf;
    v.mac->SetDataRate(12 - v.sf);
    v.mac->SetFType(LorawanMacHeader::CONFIRMED_DATA_UP);
    v.mac->SetMaxNumberOfTransmissions(g_pol == LORAWAN ? g_nbTrans : 1);
    v.txlog.emplace_back(now, air);
    v.tries++;
    v.busyUntil = now + air + g_xsimRx2 + 0.12;
    v.mac->Send(Create<Packet>(84));
}

static void Retry(int i, double gap, int sf)
{
    Veh& v = g_v[i];
    v.sf = sf;
    Schedule(i, Simulator::Now().GetSeconds() + gap);
}

// ---------------------------------------------------------------------------------------------- R3 (two-stage alert), policies r3s (single stage) and r3t (two stage)
struct R3Row
{
    bool E, F;
    int y;
    double tE;
};
struct R3Ev
{
    int v = -1;
    double t = 0.0;
    int row = -1;
    int dropped = 0;
    double flashRx = -1.0, alertRx = -1.0;
    int cancelRx = 0;
    double air = 0.0;
};
static std::vector<R3Row> g_rows;
static std::vector<R3Ev> g_r3ev;
static bool g_r3 = false;
static const double R3_FINAL_S = 1.808; // 1.8 s window plus 8 ms compute (ar_r3.py)
static const double R3_COMPUTE_S = 0.008;
static const int R3_TRIES = 4;
static int g_r6Micro = 0, g_r6Full = 0; // R6M: confirm and cancel frames sent as micro frames, and sent in full (no acknowledged flash, or its pending entry has expired)
static double g_pend = 30.0; // R6M: pending-table lifetime at the base (s); after it the node sends the full confirm
// R6M (policy r6m, PREREGISTRATION_V17 section 3): micro-confirm and micro-cancel after an acknowledged provisional frame. The design frame has 7 bytes; the LoRaWAN module carries at least its
// 13-byte header, so the simulation sends 13 bytes (a conservative airtime: the 7-byte frame is shorter). Without an acknowledged provisional frame the full confirm or the 14-byte cancel of R3 is sent.
static const int R6_MICRO_BYTES = 13;
static const double R3_CANCEL_GAP = 0.3;
// A1 (policy r3a, PREREGISTRATION_V15 section 2): 24-byte provisional frame, repeated until an ACK, the 10 s deadline or the duty limit; a ready confirm or CANCEL takes the radio first
static const int A1_PROV_BYTES = 24;
static double g_provGap = 0.0;      // development item: gap between provisional attempts (s)
static int g_reserve = 4;           // development item: reserve for the confirm, in 97-byte airtimes
static int g_afterConfirm = 1;      // development item: repeats continue after the confirm used its tries
static int g_a1Late = 0, g_a1Duty = 0; // invariants printed at the end (must be 0)
static void R3Next(int i);

static void R3Next(int i)
{
    Veh& v = g_v[i];
    double now = Simulator::Now().GetSeconds();
    if (v.q.empty())
    {
        v.active = false;
        v.awaiting = false;
        return;
    }
    if (g_pol == R3A)
    {
        // a ready confirm or CANCEL takes the radio before the next provisional repeat; the provisional alert is withdrawn once a CANCEL is due
        size_t sel = v.q.size();
        bool cancelDue = false;
        for (size_t j = 0; j < v.q.size(); j++)
        {
            if (v.q[j].kind == 2 && v.q[j].ready <= now + 1e-8)
            {
                cancelDue = true;
            }
        }
        if (cancelDue)
        {
            for (size_t j = v.q.size(); j-- > 0;)
            {
                if (v.q[j].kind == 0)
                {
                    v.q.erase(v.q.begin() + j);
                }
            }
            if (v.q.empty())
            {
                v.active = false;
                v.awaiting = false;
                return;
            }
        }
        for (size_t j = 0; j < v.q.size(); j++)
        {
            if (v.q[j].kind != 0 && v.q[j].ready <= now + 1e-8)
            {
                sel = j;
                break;
            }
        }
        if (sel == v.q.size())
        {
            for (size_t j = 0; j < v.q.size(); j++)
            {
                if (v.q[j].kind == 0)
                {
                    sel = j;
                    break;
                }
            }
        }
        if (sel == v.q.size())
        {
            sel = 0;
            for (size_t j = 1; j < v.q.size(); j++)
            {
                if (v.q[j].ready < v.q[sel].ready)
                {
                    sel = j;
                }
            }
        }
        if (sel != 0)
        {
            std::rotate(v.q.begin(), v.q.begin() + sel, v.q.begin() + sel + 1);
        }
    }
    R3Msg& m = v.q.front();
    if (g_pol == R6M && (m.kind == 1 || m.kind == 2))
    {
        // decided at every entry (a wait for the duty limit can re-enter): a micro frame only while the base holds the pending entry; otherwise the full confirm (97 bytes) or cancel (14 bytes) of R3
        bool micro = v.flashAcked && (now - v.flashAckT) <= g_pend;
        m.bytes = micro ? R6_MICRO_BYTES : (m.kind == 1 ? CG_ALERT_LEN : 14);
    }
    TR("r3next %d %.4f kind %d tries %d q %d", i, now, m.kind, m.tries, (int)v.q.size());
    double t0 = std::max(std::max(now, m.ready), v.busyUntil);
    if (t0 > now + 1e-8) // ns-3 time has 1 ns resolution: a smaller gap would be scheduled as zero and loop
    {
        Simulator::Schedule(Seconds(t0 - now) + NanoSeconds(1), &R3Next, i);
        return;
    }
    double air = cg_air_s(m.bytes, v.sf);
    if (g_pol == R3A && m.kind == 0)
    {
        bool confirmPending = false;
        for (auto& c : v.q)
        {
            confirmPending = confirmPending || (c.kind == 1);
        }
        double tStart = std::max(now, v.busyUntil);
        bool stop = (tStart + air > v.tCrash + 10.0 + 1e-12)                                        // would end after the deadline
                    || (Used(v, now) + air + g_reserve * cg_air_s(CG_ALERT_LEN, v.sf) > g_limit + 1e-12) // sliding-hour airtime plus reserve for the confirm
                    || (!g_afterConfirm && v.hasConfirm && !confirmPending);                          // repeats do not continue after the confirm is done
        if (stop)
        {
            v.q.pop_front();
            R3Next(i);
            return;
        }
    }
    double w = WaitUntil(v, now, air);
    if (w > now + 1e-8)
    {
        if (w > 1e17)
        {
            v.q.pop_front();
            R3Next(i);
            return;
        }
        Simulator::Schedule(Seconds(w - now) + NanoSeconds(1), &R3Next, i);
        return;
    }
    g_curSf[i] = v.sf;
    v.mac->SetDataRate(12 - v.sf);
    v.mac->SetFType(m.confirmed ? LorawanMacHeader::CONFIRMED_DATA_UP : LorawanMacHeader::UNCONFIRMED_DATA_UP);
    v.mac->SetMaxNumberOfTransmissions(1);
    if (g_pol == R3A && m.kind == 0)
    {
        if (now + air > v.tCrash + 10.0 + 1e-9)
        {
            g_a1Late++;
        }
        if (Used(v, now) + air > g_limit + 1e-9)
        {
            g_a1Duty++;
        }
    }
    v.txlog.emplace_back(now, air);
    m.tries++;
    v.curKind = m.kind;
    v.busyUntil = now + air + g_xsimRx2 + 0.12;
    bool conf = m.confirmed;
    int bytes = m.bytes;
    if (g_pol == R6M && (m.kind == 1 || m.kind == 2))
    {
        if (bytes == R6_MICRO_BYTES)
        {
            g_r6Micro++;
        }
        else
        {
            g_r6Full++;
        }
    }
    if (!conf)
    {
        v.q.pop_front();
        v.awaiting = false;
        Simulator::Schedule(Seconds(v.busyUntil - now) + NanoSeconds(1), &R3Next, i);
    }
    else
    {
        v.awaiting = true;
    }
    v.mac->Send(Create<Packet>(bytes - 13));
}

static void R3Outcome(int i, bool ack)
{
    Veh& v = g_v[i];
    if (!v.active || !v.awaiting || v.q.empty())
    {
        return;
    }
    v.awaiting = false;
    R3Msg& m = v.q.front();
    TR("r3outcome %d %d kind %d tries %d", i, (int)ack, m.kind, m.tries);
    if (ack && m.kind == 0)
    {
        v.flashAcked = true;
        v.flashAckT = Simulator::Now().GetSeconds();
    }
    if (g_pol == R3A)
    {
        int kind = m.kind;
        if (ack || (kind != 0 && m.tries >= R3_TRIES))
        {
            v.q.pop_front();
        }
        if (ack && kind == 1) // the ACK of the confirm names the vehicle's alert: the provisional repetition ends
        {
            for (size_t j = v.q.size(); j-- > 0;)
            {
                if (v.q[j].kind == 0)
                {
                    v.q.erase(v.q.begin() + j);
                }
            }
        }
        Simulator::Schedule(Seconds(kind == 0 ? g_provGap : 0.0) + NanoSeconds(1), &R3Next, i);
        return;
    }
    if (ack || m.tries >= R3_TRIES)
    {
        v.q.pop_front();
    }
    Simulator::ScheduleNow(&R3Next, i); // never send from inside the MAC's outcome callback (re-entrancy)
}

static void R3Crash(int i, double t, int k)
{
    Veh& v = g_v[i];
    R3Ev& e = g_r3ev[k];
    e.v = i;
    e.t = t;
    if (v.active)
    {
        e.dropped = 1;
        g_dropped++;
        return;
    }
    size_t row = (size_t)(U01((uint64_t)k, 777) * (double)g_rows.size()) % g_rows.size();
    e.row = (int)row;
    const R3Row& r = g_rows[row];
    bool two = (g_pol == R3T || g_pol == R3A || g_pol == R6M);
    v.hasConfirm = r.F;
    v.flashAcked = false;
    v.q.clear();
    if (two && r.E)
    {
        v.q.push_back({0, t + r.tE + R3_COMPUTE_S, g_pol == R3A ? A1_PROV_BYTES : 14, true, 0});
    }
    if (r.F)
    {
        v.q.push_back({1, t + R3_FINAL_S, CG_ALERT_LEN, true, 0});
    }
    else if (two && r.E)
    {
        for (int c = 0; c < 3; c++)
        {
            v.q.push_back({2, t + R3_FINAL_S + R3_CANCEL_GAP * c, 14, false, 0});
        }
    }
    if (v.q.empty())
    {
        return; // nothing to send for this event
    }
    v.active = true;
    v.tCrash = t;
    v.curEv = k;
    v.sf = g_sf0;
    v.awaiting = false;
    R3Next(i);
}

static void OnOutcome(int i, uint8_t txCount, bool ack, Time firstAttempt, Ptr<Packet> pkt)
{
    if (g_r3)
    {
        R3Outcome(i, ack);
        return;
    }
    TR("outcome %d %d pktnull=%d active=%d tx=%d", i, (int)ack, (int)(pkt == nullptr), (int)g_v[i].active, (int)txCount);
    Veh& v = g_v[i];
    double now = Simulator::Now().GetSeconds();
    if (!v.active || (pkt && pkt->GetSize() < 50)) // pkt can be null when the MAC has already cleared its context
    {
        return; // a heartbeat or an alert that is over
    }
    if (g_pol == D1)
    {
        cg_beta_update(&v.beta, ack ? 0 : 1);
    }
    if (ack || g_pol == LORAWAN)
    {
        v.active = false;
        TR("outcome done %d", i);
        return;
    }
    v.rounds++;
    if (v.tries >= 12)
    {
        v.active = false;
        return;
    }
    if (g_pol == P1)
    {
        Retry(i, 0.0, g_sf0);
    }
    else if (g_pol == QUICK)
    {
        Retry(i, 0.3, v.rounds >= 2 ? std::min(12, g_sf0 + 1) : g_sf0);
    }
    else if (g_pol == Z0)
    {
        Retry(i, 0.0, g_sf0);
    }
    else if (g_pol == L4)
    {
        Retry(i, 0.0, std::min(12, v.startSf + v.rounds / g_l4k));
    }
    else if (g_pol == NESSA)
    { // ADDED-AFTER-SESSION-1: ACK timeout from the airtime of the alert, doubling per stage, a redundant copy after the first retransmission of each stage, SF + 1 per stage
        double t0 = g_nK * cg_air_s(CG_ALERT_LEN, g_sf0);
        int nDone = v.tries;
        double gap;
        if (nDone % 2 == 0)
        {
            gap = g_nA * g_polRv->GetValue();
        }
        else
        {
            int stg = (nDone - 1) / 2;
            double ub = t0 * std::pow(2.0, stg);
            double lb = (stg >= 1) ? t0 * std::pow(2.0, stg - 1) : t0 / 2.0;
            gap = std::max(0.0, lb + (ub - lb) * g_polRv->GetValue() - (g_xsimRx2 + 0.1)); // the timeout is measured from the end of the transmission; the outcome arrives about RX2 + 0.1 s later
        }
        Retry(i, gap, std::min(12, g_sf0 + std::max(0, (nDone - 1) / 2)));
    }
    else
    {
        double tau = 10.0 - (now - v.tCrash);
        double gap = 0;
        int sf = g_sf0;
        double bud = 0.5 * std::max(g_limit - Used(v, now), 0.0);
        if (!v.demoted && cg_d1_lookup(&g_d1, 3, v.rounds, tau, cg_beta_mean(&v.beta), NHeard(i, now), bud, &gap, &sf))
        {
            Retry(i, gap, sf);
        }
        else
        {
            v.demoted = true;
            Retry(i, 4.0 * std::pow(2.0, std::max(v.tries - 1, 0)) * (1.0 + 0.5 * g_polRv->GetValue()), g_sf0);
        }
    }
}

static void OnCrash(int i, double t, bool burst, int evIdx)
{
    Veh& v = g_v[i];
    v.active = true;
    v.tCrash = t;
    v.tRx = -1.0;
    v.burst = burst;
    v.rounds = 0;
    v.tries = 0;
    v.demoted = false;
    v.sf = g_sf0;
    if (g_pol == L4)
    {
        double e = g_l4Rv->GetValue();
        int s = g_sf0;
        for (; s <= 12; s++)
        {
            double sens = SENS_DBM[std::min(5, std::max(0, s - 7))] + g_xsimSensDelta[std::min(5, std::max(0, s - 7))];
            if (v.lvl + e - sens >= g_l4M0)
            {
                break;
            }
        }
        v.startSf = std::min(12, s);
        v.sf = v.startSf;
    }
    double hold = (g_pol == P1) ? 5.0 : 0.0;
    double now = Simulator::Now().GetSeconds();
    if (g_pol == D1)
    {
        double gap = 0;
        int sf = g_sf0;
        double bud = 0.5 * std::max(g_limit - Used(v, now), 0.0);
        if (cg_d1_lookup(&g_d1, 3, 0, 10.0 - (now - t), cg_beta_mean(&v.beta), NHeard(i, now), bud, &gap, &sf))
        {
            v.sf = sf;
        }
    }
    g_ev[evIdx].delay = -1.0;
    Schedule(i, t + 0.3 + 0.05 + hold);
}

static std::vector<int> g_curEv;

static void OnGwRx(Ptr<const Packet> packet, uint32_t)
{
    TR("gwrx %.3f", Simulator::Now().GetSeconds());
    Ptr<Packet> p = packet->Copy();
    LorawanMacHeader mh;
    p->RemoveHeader(mh);
    if (!mh.IsUplink())
    {
        return;
    }
    LoraFrameHeader fh;
    fh.SetAsUplink();
    p->RemoveHeader(fh);
    auto it = g_addrToIdx.find(fh.GetAddress().Get());
    if (g_r3)
    {
        if (it == g_addrToIdx.end())
        {
            return;
        }
        Veh& rv = g_v[it->second];
        if (!rv.active || rv.curEv < 0)
        {
            return;
        }
        R3Ev& re = g_r3ev[rv.curEv];
        double rel = Simulator::Now().GetSeconds() - rv.tCrash;
        if (rv.curKind == 0 && re.flashRx < 0)
        {
            re.flashRx = rel;
        }
        else if (rv.curKind == 1 && re.alertRx < 0)
        {
            re.alertRx = rel;
        }
        else if (rv.curKind == 2)
        {
            re.cancelRx++;
        }
        return;
    }
    if (it == g_addrToIdx.end() || p->GetSize() < 50)
    {
        return; // heartbeat or unknown
    }
    Veh& v = g_v[it->second];
    double now = Simulator::Now().GetSeconds();
    if (v.active && v.tRx < 0)
    {
        v.tRx = now;
        int e = g_curEv[it->second];
        if (e >= 0)
        {
            g_ev[e].delay = now - v.tCrash;
        }
    }
}

static void OnGwTx(Ptr<const Packet> packet, uint32_t)
{
    TR("gwtx %.3f", Simulator::Now().GetSeconds());
    Ptr<Packet> p = packet->Copy();
    LorawanMacHeader mh;
    p->RemoveHeader(mh);
    LoraFrameHeader fh;
    fh.SetAsDownlink();
    p->RemoveHeader(fh);
    auto it = g_addrToIdx.find(fh.GetAddress().Get());
    double now = Simulator::Now().GetSeconds();
    int dest = (it == g_addrToIdx.end()) ? -1 : it->second;
    int sf = (dest >= 0) ? g_curSf[dest] : g_sf0;
    static int idc = 0;
    g_acks.push_back({now + cg_air_s((int)packet->GetSize(), sf), dest, ++idc, sf});
}

static void OnEdTx(int i, Ptr<const Packet> packet, uint32_t)
{
    TR("edtx %d %.3f", i, Simulator::Now().GetSeconds());
    g_v[i].phylog.emplace_back(Simulator::Now().GetSeconds(), cg_air_s((int)packet->GetSize(), g_curSf[i]));
    if ((g_pol == Z0 || g_pol == L4) && g_v[i].active && packet->GetSize() >= 50)
    {
        // independent PHY-level invariants of the alert (V16 section 10): the transmission as it goes on the air must end by the deadline and the trailing-hour airtime must stay within the limit
        double now = Simulator::Now().GetSeconds();
        double air = cg_air_s((int)packet->GetSize(), g_curSf[i]);
        if (now + air > g_v[i].tCrash + 10.0 + 1e-6)
        {
            g_l4Late++;
        }
        double u = 0.0;
        for (auto& e : g_v[i].phylog)
        {
            if (e.first > now - 3600.0 + 1e-9)
            {
                u += e.second;
            }
        }
        if (u > g_limit + 1e-6)
        {
            g_l4Duty++;
        }
    }
    if (g_r3 && g_v[i].active && g_v[i].curEv >= 0)
    {
        g_r3ev[g_v[i].curEv].air += cg_air_s((int)packet->GetSize(), g_curSf[i]);
    }
}

static void Heartbeat(int i)
{
    Veh& v = g_v[i];
    double now = Simulator::Now().GetSeconds();
    if (now >= 3600.0)
    {
        return;
    }
    Simulator::Schedule(Seconds(600.0 * (0.9 + 0.2 * g_polRv->GetValue())), &Heartbeat, i);
    double air = cg_air_s(16, g_sf0);
    if (v.active || now < v.busyUntil || WaitUntil(v, now, air) > now + 1e-12)
    {
        return; // skipped, as in the custom simulator (busy, a fast alert pending, or no budget)
    }
    g_curSf[i] = g_sf0;
    v.mac->SetDataRate(12 - g_sf0);
    v.mac->SetFType(LorawanMacHeader::UNCONFIRMED_DATA_UP);
    v.mac->SetMaxNumberOfTransmissions(1);
    v.txlog.emplace_back(now, air);
    v.busyUntil = now + air + g_xsimRx2 + 0.12;
    v.mac->Send(Create<Packet>(3));
}

int main(int argc, char* argv[])
{
    int n = 100, sf = 9, burst = 1, seed = 1, adr = 0, nbTrans = 8, sensShipped = 0;
    double p = 0.3, duty = 0.01, radius = 3000.0, rate = 0.1;
    std::string policy = "d1", table = "d1_sf9.bin", events = "";
    CommandLine cmd(__FILE__);
    cmd.AddValue("n", "vehicles", n);
    cmd.AddValue("sf", "base spreading factor", sf);
    cmd.AddValue("p", "extra loss per direction", p);
    cmd.AddValue("duty", "duty limit (share of an hour)", duty);
    cmd.AddValue("b", "burst size (1 = no burst)", burst);
    cmd.AddValue("seed", "run number", seed);
    cmd.AddValue("policy", "p1 | quick | d1 | lorawan", policy);
    cmd.AddValue("table", "D1 table file (CGD1 blob)", table);
    cmd.AddValue("adr", "ADR on (lorawan policy)", adr);
    cmd.AddValue("nbtrans", "NbTrans of the lorawan policy", nbTrans);
    cmd.AddValue("trace", "debug trace to stderr", g_trace);
    cmd.AddValue("nessaK", "Nessa-style timeout factor k", g_nK);
    cmd.AddValue("nessaA", "Nessa-style redundant-copy spacing A (s)", g_nA);
    cmd.AddValue("radius", "disc radius (m)", radius);
    cmd.AddValue("rate", "crash events per vehicle-hour", rate);
    cmd.AddValue("events", "R3 event table (lines: E F y tE_s)", events);
    cmd.AddValue("provGap", "A1: gap between provisional attempts (s)", g_provGap);
    cmd.AddValue("reserve", "A1: confirm reserve in 97-byte airtimes", g_reserve);
    cmd.AddValue("afterConfirm", "A1: provisional repeats continue after the confirm used its tries", g_afterConfirm);
    cmd.AddValue("l4k", "L4: failed rounds per spreading-factor step", g_l4k);
    cmd.AddValue("l4m0", "L4: required link margin (dB) at the start spreading factor", g_l4M0);
    cmd.AddValue("pend", "R6M: pending-table lifetime (s)", g_pend);
    cmd.AddValue("l4err", "L4: standard deviation (dB) of the link-margin estimate error", g_l4Err);
    cmd.AddValue("sensShipped", "1 = ns-3 shipped gateway sensitivities for both directions", sensShipped);
    cmd.Parse(argc, argv);
    g_p = p;
    g_pDown = p;
    g_sf0 = sf;
    g_limit = duty * 3600.0;
    g_run = seed;
    g_nbTrans = nbTrans;
    g_pol = (policy == "p1") ? P1 : (policy == "quick") ? QUICK : (policy == "lorawan") ? LORAWAN : (policy == "nessa") ? NESSA : (policy == "r3s") ? R3S : (policy == "r3t") ? R3T : (policy == "r3a") ? R3A : (policy == "z0") ? Z0 : (policy == "l4") ? L4 : (policy == "r6m") ? R6M : D1;
    g_r3 = (g_pol == R3S || g_pol == R3T || g_pol == R3A || g_pol == R6M);
    if (g_r3)
    {
        std::ifstream ef(events);
        int e_, f_, y_;
        double te_;
        while (ef >> e_ >> f_ >> y_ >> te_)
        {
            g_rows.push_back({e_ != 0, f_ != 0, y_, te_});
        }
        if (g_rows.empty())
        {
            std::cerr << "no R3 events" << std::endl;
            return 2;
        }
    }
    if (sensShipped)
    {
        const double d[6] = {-7.0, -6.5, -6.0, -5.5, -5.5, -5.5};
        for (int k = 0; k < 6; k++)
        {
            g_xsimSensDelta[k] = d[k];
        }
    }
    RngSeedManager::SetSeed(24680);
    RngSeedManager::SetRun(seed);
    // the receive-window delays of the protocol under test (the custom simulator's 0.1 s processing delay, or the LoRaWAN class A values)
    g_xsimRx1 = (g_pol == LORAWAN) ? 1.0 : 0.1;
    g_xsimRx2 = (g_pol == LORAWAN) ? 2.0 : 0.2;
    if (g_pol == D1)
    {
        std::ifstream f(table, std::ios::binary);
        g_blob.assign(std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>());
        if (!cg_d1_init(&g_d1, sf, g_blob.data(), g_blob.size()))
        {
            std::cerr << "bad D1 table" << std::endl;
            return 2;
        }
    }
    LoraInterferenceHelper::collisionMatrix = LoraInterferenceHelper::GOURSAUD;
    g_curSf.assign(n, sf);
    g_shadow.assign(n, 0.0);
    g_lossRv = CreateObject<UniformRandomVariable>();
    g_lossRv->SetStream(5000);
    g_polRv = CreateObject<UniformRandomVariable>();
    g_polRv->SetStream(5001);
    if (g_pol == L4 || g_pol == Z0) // created only for these two policies (creating a random variable consumes an automatic stream index and would shift the streams of the other policies; z0 creates it too so that z0 and l4 runs of one seed share all other streams)
    {
        g_l4Rv = CreateObject<NormalRandomVariable>();
        g_l4Rv->SetAttribute("Mean", DoubleValue(0.0));
        g_l4Rv->SetAttribute("Variance", DoubleValue(g_l4Err * g_l4Err));
        g_l4Rv->SetStream(6001);
    }
    Ptr<UniformRandomVariable> rvArr = CreateObject<UniformRandomVariable>();
    rvArr->SetStream(5002);
    Ptr<NormalRandomVariable> rvSh = CreateObject<NormalRandomVariable>();
    rvSh->SetAttribute("Mean", DoubleValue(0.0));
    rvSh->SetAttribute("Variance", DoubleValue(36.0));
    rvSh->SetStream(5003);
    for (int i = 0; i < n; i++)
    {
        g_shadow[i] = rvSh->GetValue();
    }

    MobilityHelper mobility;
    mobility.SetPositionAllocator("ns3::UniformDiscPositionAllocator", "rho", DoubleValue(radius), "X", DoubleValue(0.0), "Y", DoubleValue(0.0));
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    Ptr<LogDistancePropagationLossModel> loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetPathLossExponent(3.0);
    loss->SetReference(1, 25.0);
    Ptr<XLoss> xl = CreateObject<XLoss>();
    xl->AssignStreams(5004);
    loss->SetNext(xl);
    Ptr<PropagationDelayModel> delay = CreateObject<ConstantSpeedPropagationDelayModel>();
    Ptr<LoraChannel> channel = CreateObject<LoraChannel>(loss, delay);
    LoraPhyHelper phyHelper = LoraPhyHelper();
    phyHelper.SetChannel(channel);
    LorawanMacHelper macHelper = LorawanMacHelper();
    macHelper.SetRegion(LorawanMacHelper::ALOHA);
    LoraHelper helper = LoraHelper();

    NodeContainer endDevices;
    endDevices.Create(n);
    mobility.Install(endDevices);
    g_v.resize(n);
    for (int i = 0; i < n; i++)
    {
        Ptr<MobilityModel> m = endDevices.Get(i)->GetObject<MobilityModel>();
        Vector pos = m->GetPosition();
        pos.z = 1.2;
        m->SetPosition(pos);
        g_idxOf[PeekPointer(m)] = i;
        g_v[i].x = pos.x;
        g_v[i].y = pos.y;
        double d = std::max(std::hypot(pos.x, pos.y), 10.0);
        double lvl = 14.0 - 10.0 - (25.0 + 30.0 * std::log10(d)) + g_shadow[i];
        g_v[i].lvl = lvl;
        g_v[i].linkOk = lvl >= SENS_DBM[std::min(5, std::max(0, sf - 7))] + g_xsimSensDelta[std::min(5, std::max(0, sf - 7))];
        cg_beta_init(&g_v[i].beta, 6.0, 0.3, 0.97);
    }
    Ptr<LoraDeviceAddressGenerator> addrGen = CreateObject<LoraDeviceAddressGenerator>(54, 1864);
    macHelper.SetAddressGenerator(addrGen);
    phyHelper.SetDeviceType(LoraPhyHelper::ED);
    macHelper.SetDeviceType(LorawanMacHelper::ED_A);
    NetDeviceContainer edDevs = helper.Install(phyHelper, macHelper, endDevices);
    NodeContainer gateways;
    gateways.Create(1);
    Ptr<ListPositionAllocator> alloc = CreateObject<ListPositionAllocator>();
    alloc->Add(Vector(0.0, 0.0, 15.0));
    mobility.SetPositionAllocator(alloc);
    mobility.Install(gateways);
    phyHelper.SetDeviceType(LoraPhyHelper::GW);
    macHelper.SetDeviceType(LorawanMacHelper::GW);
    NetDeviceContainer gwDevs = helper.Install(phyHelper, macHelper, gateways);

    g_curEv.assign(n, -1);
    for (int i = 0; i < n; i++)
    {
        Ptr<LoraNetDevice> d = DynamicCast<LoraNetDevice>(endDevices.Get(i)->GetDevice(0));
        Ptr<ClassAEndDeviceLorawanMac> mac = DynamicCast<ClassAEndDeviceLorawanMac>(d->GetMac());
        mac->SetUplinkAdrBit(g_pol == LORAWAN && adr);
        mac->SetDataRate(12 - sf);
        g_v[i].node = endDevices.Get(i);
        g_v[i].mac = mac;
        g_v[i].addr = mac->GetDeviceAddress().Get();
        g_addrToIdx[g_v[i].addr] = i;
        mac->TraceConnectWithoutContext("ConfirmedTransmissionOutcome", MakeBoundCallback(&OnOutcome, i));
        d->GetPhy()->TraceConnectWithoutContext("StartSending", MakeBoundCallback(&OnEdTx, i));
    }
    Ptr<LoraNetDevice> gd = DynamicCast<LoraNetDevice>(gwDevs.Get(0));
    gd->GetPhy()->TraceConnectWithoutContext("ReceivedPacket", MakeCallback(&OnGwRx));
    gd->GetPhy()->TraceConnectWithoutContext("StartSending", MakeCallback(&OnGwTx));

    Ptr<Node> networkServer = CreateObject<Node>();
    PointToPointHelper p2p;
    p2p.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
    p2p.SetChannelAttribute("Delay", StringValue("2ms"));
    P2PGwRegistration_t gwRegistration;
    for (auto gw = gateways.Begin(); gw != gateways.End(); ++gw)
    {
        auto container = p2p.Install(networkServer, *gw);
        auto serverP2PNetDev = DynamicCast<PointToPointNetDevice>(container.Get(0));
        gwRegistration.emplace_back(serverP2PNetDev, *gw);
    }
    NetworkServerHelper nsHelper = NetworkServerHelper();
    nsHelper.SetGatewaysP2P(gwRegistration);
    nsHelper.SetEndDevices(endDevices);
    if (g_pol == LORAWAN && adr)
    {
        nsHelper.EnableAdr(true);
    }
    nsHelper.Install(networkServer);
    ForwarderHelper forHelper = ForwarderHelper();
    forHelper.Install(gateways);

    // arrivals (policy independent: a dedicated stream)
    double lam = n * rate / 3600.0, t = 0.0;
    std::vector<std::tuple<double, int, bool>> arr;
    while (lam > 0)
    {
        t += -std::log(1.0 - rvArr->GetValue()) / lam;
        if (t >= 3600.0)
        {
            break;
        }
        arr.emplace_back(t, (int)(rvArr->GetValue() * n) % n, false);
    }
    if (burst > 1)
    {
        std::vector<int> ids(n);
        for (int i = 0; i < n; i++)
        {
            ids[i] = i;
        }
        for (int k = 0; k < std::min(burst, n); k++)
        {
            int j = k + (int)(rvArr->GetValue() * (n - k)) % (n - k);
            std::swap(ids[k], ids[j]);
            arr.emplace_back(600.0 + rvArr->GetValue() * 10.0, ids[k], true);
        }
    }
    std::sort(arr.begin(), arr.end());
    g_ev.resize(arr.size());
    g_r3ev.assign(arr.size(), R3Ev());
    for (size_t k = 0; k < arr.size(); k++)
    {
        double tt = std::get<0>(arr[k]);
        int vi = std::get<1>(arr[k]);
        bool bu = std::get<2>(arr[k]);
        g_ev[k] = {vi, tt, bu, -1.0};
        Simulator::Schedule(Seconds(tt), [=]() {
            if (g_r3)
            {
                R3Crash(vi, tt, (int)k);
                return;
            }
            if (g_v[vi].active && !g_v[vi].demoted)
            { // an alert in its long backoff tail (demoted) gives way to a new crash event; an alert still in its retry rounds blocks it (the custom simulator keeps several alerts per vehicle)
                g_dropped++;
                g_ev[k].delay = -2.0;
                return;
            }
            g_curEv[vi] = (int)k;
            OnCrash(vi, tt, bu, (int)k);
        });
    }
    for (int i = 0; i < n; i++)
    {
        double hb0 = rvArr->GetValue() * 600.0; // drawn in every policy so that the stream of the arrivals is the same
        if (!g_r3)
        {
            Simulator::Schedule(Seconds(hb0), &Heartbeat, i);
        }
    }
    g_simEnd = 3600.0 + 60.0;
    Simulator::Stop(Seconds(g_simEnd));
    Simulator::Run();
    Simulator::Destroy();

    for (auto& e : g_ev)
    {
        if (!g_r3)
        {
            std::printf("EV %d %.6f %.6f %d\n", e.v, e.t, e.delay, e.burst ? 1 : 0);
        }
    }
    for (size_t k = 0; g_r3 && k < g_r3ev.size(); k++)
    {
        const R3Ev& e = g_r3ev[k];
        std::printf("R3 %zu %d %.6f %d %d %.6f %.6f %d %.6f\n", k, e.v, e.t, e.row, e.dropped, e.flashRx, e.alertRx, e.cancelRx, e.air);
    }
    double mx = 0.0;
    for (auto& v : g_v)
    {
        auto l = v.phylog;
        std::sort(l.begin(), l.end());
        size_t j = 0;
        double tot = 0.0;
        for (size_t k = 0; k < l.size(); k++)
        {
            tot += l[k].second;
            while (l[j].first <= l[k].first - 3600.0 + 1e-9)
            {
                tot -= l[j].second;
                j++;
            }
            mx = std::max(mx, tot);
        }
    }
    if (g_pol == R3A)
    {
        std::printf("A1INV %d %d\n", g_a1Late, g_a1Duty);
    }
    if (g_pol == Z0 || g_pol == L4)
    {
        std::printf("L4INV %d %d\n", g_l4Late, g_l4Duty);
    }
    if (g_pol == R6M)
    {
        std::printf("R6M %d %d\n", g_r6Micro, g_r6Full);
    }
    std::printf("DUTY %.6f %.6f\n", mx, g_limit);
    std::printf("DROPPED %d\n", g_dropped);
    return 0;
}
