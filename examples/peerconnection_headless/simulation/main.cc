#include <stddef.h>
#include <stdint.h>
#include <memory>
#include <utility>
#include <vector>
#include <future>
#include <iostream>
#include "cuda.h"
#include "api/media_stream_interface.h"
#include "api/peer_connection_interface.h"
#include "rtc_base/thread.h"
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
  RTC_INFO << "Start simulation.";
  init_cuda();
  rtc::InitializeSSL();
  auto path = "/home/lix16/Downloads";
  uint32_t width = 1080;
  uint32_t fps = 30;
  auto thread = rtc::Thread::Create();
  thread->Start();
  auto receiver = rtc::make_ref_counted<Receiver>(thread.get());
  auto sender = rtc::make_ref_counted<Sender>(thread.get(), path, width, fps);
  sender->SetRemotePeer(receiver.get());
  receiver->SetRemotePeer(sender.get());
  sender->connect_receiver();
  std::promise<void>().get_future().wait();
  rtc::CleanupSSL();
  return 0;
}