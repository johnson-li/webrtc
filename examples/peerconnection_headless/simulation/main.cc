#include <stddef.h>
#include <stdint.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <arpa/inet.h>
#include <sys/un.h>
#include <memory>
#include <utility>
#include <vector>
#include <future>
#include <iostream>
#include "cuda.h"
#include "api/media_stream_interface.h"
#include "api/peer_connection_interface.h"
#include "rtc_base/thread.h"
#include "absl/flags/parse.h"
#include "absl/memory/memory.h"
#include "absl/types/optional.h"
#include "api/audio/audio_mixer.h"
#include "api/audio_codecs/audio_decoder_factory.h"
#include "rtc_base/physical_socket_server.h"
#include "api/task_queue/task_queue_base.h"
#include "api/task_queue/pending_task_safety_flag.h"
#include "api/scoped_refptr.h"
#include "rtc_base/ssl_adapter.h"
#include "api/audio_codecs/audio_encoder_factory.h"
#include "api/audio_codecs/builtin_audio_decoder_factory.h"
#include "api/audio_codecs/builtin_audio_encoder_factory.h"
#include "api/audio_options.h"
#include "api/create_peerconnection_factory.h"
#include "api/rtp_sender_interface.h"
#include "api/task_queue/default_task_queue_factory.h"
#include "api/test/create_frame_generator.h"
#include "api/video_codecs/builtin_video_decoder_factory.h"
#include "api/video_codecs/builtin_video_encoder_factory.h"
#include "api/video_codecs/video_decoder_factory.h"
#include "api/video_codecs/video_encoder_factory.h"
#include "modules/audio_device/include/audio_device.h"
#include "modules/audio_processing/include/audio_processing.h"
#include "modules/video_capture/video_capture.h"
#include "modules/video_capture/video_capture_factory.h"
#include "p2p/base/port_allocator.h"
#include "pc/video_track_source.h"
#include "rtc_base/checks.h"
#include "rtc_base/logging.h"
#include "rtc_base/rtc_certificate_generator.h"
#include "rtc_base/strings/json.h"
#include "test/vcm_capturer.h"
#include "test/frame_generator_capturer.h"
#include "examples/peerconnection_headless/simulation/sender.h"
#include "examples/peerconnection_headless/simulation/receiver.h"
#include "examples/peerconnection_headless/simulation/flag_defs.h"

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
  RTC_INFO << "Start simulation.";
  init_cuda();
  rtc::InitializeSSL();

  const std::string forced_field_trials =
      absl::GetFlag(FLAGS_force_fieldtrials);
  const std::string path = absl::GetFlag(FLAGS_path);
  const std::string dump_path = absl::GetFlag(FLAGS_dump_path);
  const std::string shm_name = absl::GetFlag(FLAGS_shm_name);
  const std::string obs_socket = absl::GetFlag(FLAGS_obs_socket);
  const std::string logging_path = absl::GetFlag(FLAGS_logging_path);
  const int resolution = absl::GetFlag(FLAGS_resolution);
  const int fps = absl::GetFlag(FLAGS_fps);

  if (!logging_path.empty()) {
    LOGGING_PATH = static_cast<char*>(malloc(logging_path.size() + 1));
    strcpy(LOGGING_PATH, logging_path.c_str());
    RTC_TS << "Enable logging on " << LOGGING_PATH;
  }
  if (!shm_name.empty()) {
    SHM_STR = static_cast<char*>(malloc(shm_name.size() + 1));
    strcpy(SHM_STR, shm_name.c_str());
    RTC_TS << "Enable shared memory on " << SHM_STR;
  }
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

  auto thread = rtc::Thread::Create();
  thread->Start();
  auto receiver = rtc::make_ref_counted<Receiver>(thread.get());
  auto sender = rtc::make_ref_counted<Sender>(thread.get(), path, resolution, fps);
  sender->SetRemotePeer(receiver.get());
  receiver->SetRemotePeer(sender.get());
  sender->connect_receiver();
  std::promise<void>().get_future().wait();
  rtc::CleanupSSL();
  return 0;
}