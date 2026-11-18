/*
 * X1 calibration scenario for the CrashGuard redesign round (docs/02_preregistration/PREREGISTRATION_V12.md section 8).
 *
 * One gateway at the centre of a disc, N end devices placed uniformly in the disc, one spreading factor, a 97-byte frame (84 bytes of application payload plus the 13-byte LoRaWAN overhead),
 * periodic uplinks with a random start phase, confirmed or unconfirmed (one transmission, no retry). Channel as in the custom simulator (src/crashguard/world_sim.py, docs/03_results/ASSUMPTIONS.md):
 * log-distance path loss with exponent 3 and 25 dB at 1 m, transmit power 14 dBm minus 10 dB vehicle loss, static log-normal shadowing of 6 dB per device, per-packet fading of 2 dB, a 6 dB capture rule
 * between frames of the same spreading factor (the ns-3 GOURSAUD matrix has 6 dB on its diagonal), spreading factors treated as quasi-orthogonal by the ns-3 matrix.
 *
 * Output (one line): sent received (at the gateway, MAC level) and, for confirmed uplinks, the number of devices acknowledgements received.
 *
 *   ns3 run "xsim_calib --nDevices=50 --sf=9 --confirmed=0 --radius=3000 --simTime=3600 --period=30 --seed=1 --sens=ns3|custom"
 */
#include "ns3/core-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-helper.h"
#include "ns3/point-to-point-helper.h"
#include "ns3/propagation-loss-model.h"

#include <cmath>
#include <iostream>
#include <map>

using namespace ns3;
using namespace lorawan;

namespace ns3
{
namespace lorawan
{
extern double g_xsimSensDelta[6]; // local ns-3 change: dB offsets added to the compiled sensitivity tables (V12 11.3)
}
}

NS_LOG_COMPONENT_DEFINE("XsimCalib");

/** Static per-device shadowing plus per-packet fading on top of the log-distance loss (applied on the device side of a link). */
class ShadowFadeLoss : public PropagationLossModel
{
  public:
    static TypeId GetTypeId()
    {
        static TypeId tid = TypeId("ns3::ShadowFadeLoss").SetParent<PropagationLossModel>().SetGroupName("Propagation").AddConstructor<ShadowFadeLoss>();
        return tid;
    }

    ShadowFadeLoss()
    {
        m_shadow = CreateObject<NormalRandomVariable>();
        m_shadow->SetAttribute("Mean", DoubleValue(0.0));
        m_shadow->SetAttribute("Variance", DoubleValue(36.0));
        m_fade = CreateObject<NormalRandomVariable>();
        m_fade->SetAttribute("Mean", DoubleValue(0.0));
        m_fade->SetAttribute("Variance", DoubleValue(4.0));
    }

  private:
    double DoCalcRxPower(double txPowerDbm, Ptr<MobilityModel> a, Ptr<MobilityModel> b) const override
    {
        Ptr<MobilityModel> dev = (a->GetPosition().z < 5.0) ? a : b;  // the gateway is at 15 m, devices at 1.2 m
        auto it = m_cache.find(PeekPointer(dev));
        if (it == m_cache.end())
        {
            it = m_cache.emplace(PeekPointer(dev), m_shadow->GetValue()).first;
        }
        return txPowerDbm - 10.0 + it->second + m_fade->GetValue();  // 10 dB vehicle and body loss on every link, as in the custom simulator (transmit power stays at the ns-3 default of 14 dBm)
    }

    int64_t DoAssignStreams(int64_t stream) override
    {
        m_shadow->SetStream(stream);
        m_fade->SetStream(stream + 1);
        return 2;
    }

    Ptr<NormalRandomVariable> m_shadow;
    Ptr<NormalRandomVariable> m_fade;
    mutable std::map<MobilityModel*, double> m_cache;
};

int
main(int argc, char* argv[])
{
    int nDevices = 50;
    int sf = 9;
    int confirmed = 0;
    double radius = 3000;
    double simTime = 3600;
    double period = 30;
    int seed = 1;
    std::string sens = "ns3";
    int sensShipped = 0;
    CommandLine cmd(__FILE__);
    cmd.AddValue("nDevices", "devices", nDevices);
    cmd.AddValue("sf", "spreading factor 7..12", sf);
    cmd.AddValue("confirmed", "1 = confirmed uplink", confirmed);
    cmd.AddValue("radius", "disc radius (m)", radius);
    cmd.AddValue("simTime", "simulated seconds", simTime);
    cmd.AddValue("period", "uplink period (s)", period);
    cmd.AddValue("seed", "run number", seed);
    cmd.AddValue("sens", "label only (the sensitivity table is compiled in)", sens);
    cmd.AddValue("sensShipped", "1 = ns-3 shipped gateway sensitivities for both directions (setting b of V12 11.3)", sensShipped);
    cmd.Parse(argc, argv);
    if (sensShipped)
    {
        const double d[6] = {-7.0, -6.5, -6.0, -5.5, -5.5, -5.5};
        for (int k = 0; k < 6; k++)
        {
            g_xsimSensDelta[k] = d[k];
        }
    }
    RngSeedManager::SetSeed(12345);
    RngSeedManager::SetRun(seed);

    LoraInterferenceHelper::collisionMatrix = LoraInterferenceHelper::GOURSAUD;

    MobilityHelper mobility;
    mobility.SetPositionAllocator("ns3::UniformDiscPositionAllocator", "rho", DoubleValue(radius), "X", DoubleValue(0.0), "Y", DoubleValue(0.0));
    mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");

    Ptr<LogDistancePropagationLossModel> loss = CreateObject<LogDistancePropagationLossModel>();
    loss->SetPathLossExponent(3.0);
    loss->SetReference(1, 25.0);
    Ptr<ShadowFadeLoss> sh = CreateObject<ShadowFadeLoss>();
    loss->SetNext(sh);
    Ptr<PropagationDelayModel> delay = CreateObject<ConstantSpeedPropagationDelayModel>();
    Ptr<LoraChannel> channel = CreateObject<LoraChannel>(loss, delay);

    LoraPhyHelper phyHelper = LoraPhyHelper();
    phyHelper.SetChannel(channel);
    LorawanMacHelper macHelper = LorawanMacHelper();
    macHelper.SetRegion(LorawanMacHelper::ALOHA);
    LoraHelper helper = LoraHelper();
    helper.EnablePacketTracking();

    NodeContainer endDevices;
    endDevices.Create(nDevices);
    mobility.Install(endDevices);
    for (auto j = endDevices.Begin(); j != endDevices.End(); ++j)
    {
        Ptr<MobilityModel> m = (*j)->GetObject<MobilityModel>();
        Vector p = m->GetPosition();
        p.z = 1.2;
        m->SetPosition(p);
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
    helper.Install(phyHelper, macHelper, gateways);

    // fixed spreading factor: data rate index 12 - sf (DR5 = SF7 ... DR0 = SF12); one transmission, no retry
    for (auto j = endDevices.Begin(); j != endDevices.End(); ++j)
    {
        Ptr<LoraNetDevice> d = DynamicCast<LoraNetDevice>((*j)->GetDevice(0));
        Ptr<ClassAEndDeviceLorawanMac> mac = DynamicCast<ClassAEndDeviceLorawanMac>(d->GetMac());
        mac->SetDataRate(12 - sf);
        mac->SetMaxNumberOfTransmissions(1);
        mac->SetUplinkAdrBit(false);  // no local ADR backoff: otherwise the device changes its data rate after about 96 uplinks without a downlink
        mac->SetFType(confirmed ? LorawanMacHeader::CONFIRMED_DATA_UP : LorawanMacHeader::UNCONFIRMED_DATA_UP);
    }

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
    nsHelper.Install(networkServer);
    ForwarderHelper forHelper = ForwarderHelper();
    forHelper.Install(gateways);

    PeriodicSenderHelper app;
    app.SetPeriod(Seconds(period));
    app.SetPacketSize(84);
    ApplicationContainer apps = app.Install(endDevices);
    apps.Start(Seconds(0));
    apps.Stop(Seconds(simTime));

    Simulator::Stop(Seconds(simTime + 10));
    Simulator::Run();
    Simulator::Destroy();

    LoraPacketTracker& tracker = helper.GetPacketTracker();
    std::cout << "RESULT " << tracker.CountMacPacketsGlobally(Seconds(0), Seconds(simTime + 5)) << std::endl;
    return 0;
}
