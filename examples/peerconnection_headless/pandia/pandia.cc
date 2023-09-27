#include <sys/socket.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/un.h>
#include "absl/flags/parse.h"
#include "api/test/create_frame_generator.h"
#include "api/test/create_network_emulation_manager.h"
#include "api/test/create_peerconnection_quality_test_fixture.h"
#include "api/test/network_emulation_manager.h"
#include "api/test/peerconnection_quality_test_fixture.h"
#include "api/test/time_controller.h"
#include "call/simulated_network.h"
#include "cuda.h"
#include "examples/peerconnection_headless/pandia/flag_defs.h"

using namespace webrtc;

using PeerConfigurer =
    webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::PeerConfigurer;
using RunParams = webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::RunParams;
using VideoConfig =
    webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::VideoConfig;
using AudioConfig =
    webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::AudioConfig;
using ScreenShareConfig =
    webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::ScreenShareConfig;
using VideoSimulcastConfig =
    webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::VideoSimulcastConfig;
using VideoCodecConfig =
    webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture::VideoCodecConfig;

class MySimulatedNetwork : public SimulatedNetworkInterface {
    public:
  MySimulatedNetwork(const BuiltInNetworkBehaviorConfig& config) {
  }

  void SetConfig(const BuiltInNetworkBehaviorConfig& config) {
  }
  void UpdateConfig(std::function<void(BuiltInNetworkBehaviorConfig*)> config_modifier) {
  }
  void PauseTransmissionUntil(int64_t until_us) {
  }
  bool EnqueuePacket(PacketInFlightInfo packet_info) {
    return false;
  }
//   std::vector<PacketDeliveryInfo> DequeueDeliverablePackets(
//       int64_t receive_time_us) {
//   };
  absl::optional<int64_t> NextDeliveryTimeUs() const {
    return absl::nullopt;
  };

  std::queue<PacketInFlightInfo> capacity_link_;
};


std::unique_ptr<webrtc_pc_e2e::PeerConnectionE2EQualityTestFixture>
CreateTestFixture(const std::string& test_case_name,
                  TimeController& time_controller,
                  std::pair<EmulatedNetworkManagerInterface*,
                            EmulatedNetworkManagerInterface*> network_links,
                  rtc::FunctionView<void(PeerConfigurer*)> alice_configurer,
                  rtc::FunctionView<void(PeerConfigurer*)> bob_configurer) {
  auto fixture = webrtc_pc_e2e::CreatePeerConnectionE2EQualityTestFixture(
      test_case_name, time_controller, nullptr, nullptr);
  fixture->AddPeer(network_links.first->network_dependencies(),
                   alice_configurer);
  fixture->AddPeer(network_links.second->network_dependencies(),
                   bob_configurer);
  return fixture;
}

EmulatedNetworkNode* CreateEmulatedNodeWithConfig(
    NetworkEmulationManager* emulation,
    const BuiltInNetworkBehaviorConfig& config) {
  return emulation->CreateEmulatedNode(
      std::make_unique<SimulatedNetwork>(config));
}

std::pair<EmulatedNetworkManagerInterface*, EmulatedNetworkManagerInterface*>
CreateTwoNetworkLinks(NetworkEmulationManager* emulation,
                      const BuiltInNetworkBehaviorConfig& config) {
  auto* alice_node = CreateEmulatedNodeWithConfig(emulation, config);
  auto* bob_node = CreateEmulatedNodeWithConfig(emulation, config);

  auto* alice_endpoint = emulation->CreateEndpoint(EmulatedEndpointConfig());
  auto* bob_endpoint = emulation->CreateEndpoint(EmulatedEndpointConfig());

  emulation->CreateRoute(alice_endpoint, {alice_node}, bob_endpoint);
  emulation->CreateRoute(bob_endpoint, {bob_node}, alice_endpoint);

  return {
      emulation->CreateEmulatedNetworkManagerInterface({alice_endpoint}),
      emulation->CreateEmulatedNetworkManagerInterface({bob_endpoint}),
  };
}

void init_cuda() {
  cuInit(0);
  int nGpu = 0;
  cuDeviceGetCount(&nGpu);
  auto iGpu = nGpu - 1;
  CUdevice cuDevice = 0;
  cuDeviceGet(&cuDevice, iGpu);
  char szDeviceName[80];
  cuDeviceGetName(szDeviceName, sizeof(szDeviceName), cuDevice);
  RTC_INFO << "GPU in use: #" << iGpu << " " << szDeviceName;
}

int main(int argc, char* argv[]) {
  absl::ParseCommandLine(argc, argv);
  RTC_INFO << "Start pandia.";
  init_cuda();

  const std::string forced_field_trials =
      absl::GetFlag(FLAGS_force_fieldtrials);
  const std::string path = absl::GetFlag(FLAGS_path);
  const std::string dump_path = absl::GetFlag(FLAGS_dump_path);
  const std::string shm_name = absl::GetFlag(FLAGS_shm_name);
  const std::string obs_socket = absl::GetFlag(FLAGS_obs_socket);
  const std::string logging_path = absl::GetFlag(FLAGS_logging_path);
  const int bandwidth = absl::GetFlag(FLAGS_bandwidth);
  const int rtt = absl::GetFlag(FLAGS_rtt);
  const int buffer_size = absl::GetFlag(FLAGS_buffer_size);
  const int resolution = absl::GetFlag(FLAGS_resolution);
  const int fps = absl::GetFlag(FLAGS_fps);
  const int duration = absl::GetFlag(FLAGS_duration);

  LOGGING_PATH = static_cast<char*>(malloc(logging_path.size() + 1));
  strcpy(LOGGING_PATH, logging_path.c_str());
  SHM_STR = static_cast<char*>(malloc(shm_name.size() + 1));
  strcpy(SHM_STR, shm_name.c_str());
  if (!obs_socket.empty()) {
    OBS_SOCKET_FD = socket(AF_UNIX, SOCK_DGRAM, 0);
    int flags = ::fcntl(OBS_SOCKET_FD, F_GETFL);
    ::fcntl(OBS_SOCKET_FD, F_SETFL, flags | O_NONBLOCK);
    struct sockaddr_un server {
      .sun_family = AF_UNIX,
    };
    strncpy(server.sun_path, obs_socket.c_str(), sizeof(server.sun_path) - 1);
    ::connect(OBS_SOCKET_FD, (struct sockaddr *)&server, sizeof(server));
    rtc::ObsProgramStart obs {
      .ts = (uint64_t) TS(),
    };
    auto data = reinterpret_cast<const uint8_t*>(&obs);
    send(OBS_SOCKET_FD, data, sizeof(obs), 0);
    RTC_TS << "Enable observation on " << obs_socket;
  }

  std::unique_ptr<NetworkEmulationManager> network_emulation_manager =
      CreateNetworkEmulationManager();
  BuiltInNetworkBehaviorConfig network_config {
      .queue_length_packets = (size_t)((double) bandwidth * buffer_size / 1450 / 8),
      .queue_delay_ms = rtt / 2,
      .delay_standard_deviation_ms = 0,
      .link_capacity_kbps = bandwidth,
      .loss_percent = 0,
      .allow_reordering = true,
      .avg_burst_loss_length = -1,
  };
    
  std::ostringstream oss;
  oss << path << "/drive_" << resolution << "p.yuv";
  auto filename = oss.str();

  auto fixture = CreateTestFixture(
      "pandia", *network_emulation_manager->time_controller(),
      CreateTwoNetworkLinks(network_emulation_manager.get(), network_config),
      [resolution, filename, fps](PeerConfigurer* alice) {
        VideoConfig video(resolution / 9 * 16, resolution, fps);
        video.stream_label = "sender-video";
        std::unique_ptr<webrtc::test::FrameGeneratorInterface> frame_generator(
            webrtc::test::CreateFromYuvFileFrameGenerator(
                std::vector<std::string>{filename}, resolution / 9 * 16,
                resolution, 1));
        alice->AddVideoConfig(std::move(video), std::move(frame_generator));
        alice->SetVideoCodecs({VideoCodecConfig(cricket::kH264CodecName, {})});
      },
      [](PeerConfigurer* bob) {
        bob->SetVideoCodecs({VideoCodecConfig(cricket::kH264CodecName, {})});
      });
  fixture->Run(RunParams(TimeDelta::Seconds(duration)));
  return 0;
}